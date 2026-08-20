"""Deep Research 命令行入口。

一次研究要花几十分钟，中间还必须由人批准一份研究合同，所以交互不是"一条命令跑到底"，
而是：

    提交问题 → 读审批卡 → 批准 → 继续（可随时中断）→ 取报告

状态全部在数据库里，命令行自己不持有任何状态。中断后重新执行 ``continue`` 就接着跑，
已完成的付费调用只回放、不重发。

用法::

    python tools/research.py new            # 交互式提交（语言、来源授权、厂商都会问）
    python tools/research.py list
    python tools/research.py show   <任务号>
    python tools/research.py approve <任务号>
    python tools/research.py continue <任务号>
    python tools/research.py report <任务号> [-o 文件]
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path

import aiosqlite

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from deep_research_agent.application import (  # noqa: E402
    load_environment,
    render_role_models,
)
from deep_research_agent.config import load_config  # noqa: E402
from deep_research_agent.providers import search_credentials  # noqa: E402
from deep_research_agent.providers.llm import LLM_PROVIDERS  # noqa: E402
from deep_research_agent.service import Event, ResearchService, Task  # noqa: E402

DEFAULT_DATABASE = ROOT / ".deep-research-agent" / "tasks.sqlite3"

LANGUAGES: tuple[tuple[str, str], ...] = (
    ("zh", "中文"),
    ("en", "English"),
    ("ja", "日本語"),
    ("ko", "한국어"),
    ("de", "Deutsch"),
    ("fr", "Français"),
    ("es", "Español"),
)

ACCESS_CHOICES: tuple[tuple[str, str, str], ...] = (
    ("public_web", "公开网络", "联网检索与抓取公开来源"),
    ("user_files", "公开网络 + 我的本地资料", "两者都用；需要指定资料目录"),
    ("local_only", "只用我的本地资料（完全不联网）", "课题不会发给任何搜索厂商"),
)

ACADEMIC_CHOICES: tuple[tuple[str, str], ...] = (
    ("arxiv", "arXiv（预印本）"),
    ("crossref", "Crossref（DOI / 版本记录）"),
    ("pubmed", "PubMed（生物医学）"),
)


# ------------------------------------------------------------------ 交互原语


def _ask(prompt: str, default: str = "") -> str:
    suffix = f"（默认 {default}）" if default else ""
    value = input(f"{prompt}{suffix}：").strip()
    return value or default


def _choose(
    title: str, options: Sequence[tuple[str, str]], *, default: int = 1
) -> str:
    """Single choice from a numbered list.  Returns the chosen key."""

    print(f"\n{title}")
    for index, (_key, label) in enumerate(options, start=1):
        mark = " ←默认" if index == default else ""
        print(f"  {index}. {label}{mark}")
    while True:
        raw = input(f"请选择 1-{len(options)}（回车用默认）：").strip()
        if not raw:
            return options[default - 1][0]
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1][0]
        print("  请输入列表里的编号。")


def _choose_many(
    title: str, options: Sequence[tuple[str, str, bool]], *, note: str = ""
) -> tuple[str, ...]:
    """Multiple choice.  ``options`` is ``(key, label, preselected)``."""

    print(f"\n{title}")
    if note:
        print(f"  {note}")
    for index, (_key, label, preselected) in enumerate(options, start=1):
        print(f"  {index}. {label}{' ←已选' if preselected else ''}")
    raw = input("用逗号分隔编号，回车保留已选：").strip()
    if not raw:
        return tuple(key for key, _label, pre in options if pre)
    picked: list[str] = []
    for piece in raw.replace("，", ",").split(","):
        piece = piece.strip()
        if piece.isdigit() and 1 <= int(piece) <= len(options):
            key = options[int(piece) - 1][0]
            if key not in picked:
                picked.append(key)
    return tuple(picked)


# ----------------------------------------------------------- 厂商可用性


def _model_vendor_options(environ: Mapping[str, str]) -> list[tuple[str, str]]:
    """Vendors with a usable credential first; the rest shown but marked."""

    ready: list[tuple[str, str]] = []
    missing: list[tuple[str, str]] = []
    for spec in sorted(LLM_PROVIDERS, key=lambda item: item.name):
        if spec.api_key(environ):
            ready.append((spec.name, f"{spec.name}（密钥就绪）"))
        else:
            missing.append((spec.name, f"{spec.name}（缺少 {spec.key_env_var}）"))
    return ready + missing


def _search_options(environ: Mapping[str, str]) -> list[tuple[str, str, bool]]:
    options: list[tuple[str, str, bool]] = []
    for name, env_var in sorted(search_credentials().items()):
        has_key = bool(environ.get(env_var, "").strip())
        label = f"{name}（{'密钥就绪' if has_key else '缺少 ' + env_var + '，会被跳过'}）"
        options.append((name, label, has_key))
    options.append(("duckduckgo", "duckduckgo（无需密钥，兜底）", True))
    return options


# ------------------------------------------------------------------- 渲染


def _render(event: Event) -> None:
    if event.kind == "contract_proposed":
        print("\n" + event.message)
    elif event.kind == "clarification_requested":
        print("\n需要你先澄清一个问题才能定方案：")
        print(f"  {event.message}")
        print(f"  为什么这会改变方案：{event.detail.get('why', '')}")
    elif event.kind == "wave_started":
        print(f"\n[第 {event.detail.get('round')} 批] {event.message}")
        for focus in event.detail.get("assignments", ()):
            print(f"    · {focus}")
    elif event.kind == "wave_finished":
        print(f"  → {event.message}")
    elif event.kind == "review":
        print(f"  [独立审查] {event.message}")
        for finding in event.detail.get("findings", ()):
            print(f"      - {str(finding).splitlines()[0]}")
    else:
        print(f"\n{event.message}")


def _render_task(task: Task) -> str:
    state = {
        "clarification_requested": "待澄清",
        "awaiting_approval": "待审批",
        "researching": "可开始",
        "published": "已发布",
        "halted": "已停止",
        "paused": "已暂停",
    }.get(task.state, task.state)
    request = task.request if len(task.request) <= 42 else task.request[:41] + "…"
    return (
        f"{task.task_id}  {state:<6} {task.language:<3} "
        f"素材 {task.materials:>4}  {request}"
    )


# ------------------------------------------------------------------- 命令


async def _service(args: argparse.Namespace, environ: Mapping[str, str]):  # noqa: ANN202
    database = Path(args.database)
    database.parent.mkdir(parents=True, exist_ok=True)
    connection = await aiosqlite.connect(database)
    service = ResearchService(
        connection=connection,
        environ=environ,
        corpus_root=Path(args.corpus) if getattr(args, "corpus", "") else None,
    )
    await service.setup()
    return connection, service


async def cmd_new(args: argparse.Namespace) -> int:
    environ = dict(load_environment(ROOT / ".env"))

    print("=== 新的研究委托 ===")
    request = args.request or _ask("\n你想研究什么？请尽量具体")
    if not request:
        print("没有收到研究问题。")
        return 2

    language = _choose(
        "报告用什么语言交付？（来源原文与引文保持原语言，不翻译）",
        [(code, label) for code, label in LANGUAGES] + [("other", "其他（手动输入）")],
    )
    if language == "other":
        language = _ask("请输入语言代码或名称", "en")

    access_key = _choose(
        "允许用哪些来源？",
        [(key, f"{label} —— {hint}") for key, label, hint in ACCESS_CHOICES],
    )
    source_access = (
        ("public_web",)
        if access_key == "public_web"
        else ("public_web", "user_files")
        if access_key == "user_files"
        else ("local_only",)
    )
    corpus = ""
    if access_key in ("user_files", "local_only"):
        while True:
            corpus = _ask("本地资料目录的路径")
            if corpus and Path(corpus).expanduser().is_dir():
                break
            print("  这个路径不是一个存在的目录。")
        args.corpus = corpus

    vendor = _choose(
        "用哪家模型厂商？",
        _model_vendor_options(environ),
    )
    environ["DEEP_RESEARCH_LLM_PROVIDER"] = vendor

    if access_key != "local_only":
        chosen = _choose_many(
            "用哪些网页搜索厂商？",
            _search_options(environ),
            note="缺少密钥的会被自动跳过；每次检索会并发问所有选中的。",
        )
        if chosen:
            environ["DEEP_RESEARCH_SEARCH_PROVIDERS"] = ",".join(chosen)
        academic = _choose_many(
            "用哪些学术索引？（全部无需密钥）",
            [(key, label, True) for key, label in ACADEMIC_CHOICES],
        )
        for key, flag in (
            ("arxiv", "ARXIV_SEARCH"),
            ("crossref", "CROSSREF_SEARCH"),
            ("pubmed", "PUBMED_SEARCH"),
        ):
            environ[f"DEEP_RESEARCH_{flag}"] = "true" if key in academic else "false"
    else:
        print("\n（只用本地资料，不会配置任何搜索厂商。）")

    try:
        config = load_config(environ)
    except Exception as error:  # noqa: BLE001 - shown to the user as-is
        print(f"\n配置无法使用：{error}")
        return 2
    print("\n角色 → 模型：")
    print(render_role_models(config))

    connection, service = await _service(args, environ)
    try:
        task = await service.open_task(
            request,
            language=language,
            source_access=source_access,  # type: ignore[arg-type]
            created_at=datetime.now(UTC).isoformat(timespec="seconds"),
            listen=_render,
        )
        print(f"\n任务号：{task.task_id}")
        if task.state == "clarification_requested":
            print("补充说明后用 `new` 重新提交即可。")
            return 0
        print(
            "请阅读上面的研究合同。同意就执行：\n"
            f"  python tools/research.py approve {task.task_id}"
        )
        return 0
    finally:
        await connection.close()


async def cmd_list(args: argparse.Namespace) -> int:
    connection, service = await _service(args, load_environment(ROOT / ".env"))
    try:
        tasks = await service.tasks()
        if not tasks:
            print("还没有任何研究任务。")
            return 0
        for task in tasks:
            print(_render_task(task))
        return 0
    finally:
        await connection.close()


async def cmd_show(args: argparse.Namespace) -> int:
    connection, service = await _service(args, load_environment(ROOT / ".env"))
    try:
        task = await service.task(args.task_id)
        print(_render_task(task))
        if task.state == "awaiting_approval":
            print("\n" + await service.approval_card(args.task_id))
        return 0
    finally:
        await connection.close()


async def cmd_approve(args: argparse.Namespace) -> int:
    connection, service = await _service(args, load_environment(ROOT / ".env"))
    try:
        await service.approve(args.task_id, note=args.note)
        print(f"已批准 {args.task_id}。")
        if not args.no_run:
            print("开始研究（可以随时 Ctrl-C，之后用 continue 接着跑）。\n")
            state = await service.advance(args.task_id, listen=_render)
            print(f"\n当前状态：{state}")
        return 0
    finally:
        await connection.close()


async def cmd_continue(args: argparse.Namespace) -> int:
    connection, service = await _service(args, load_environment(ROOT / ".env"))
    try:
        state = await service.advance(args.task_id, listen=_render)
        print(f"\n当前状态：{state}")
        return 0
    finally:
        await connection.close()


async def cmd_report(args: argparse.Namespace) -> int:
    connection, service = await _service(args, load_environment(ROOT / ".env"))
    try:
        report = await service.report(args.task_id)
        if report is None:
            print("这个任务还没有发布报告。")
            return 1
        if args.output:
            path = Path(args.output)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(report, encoding="utf-8")
            print(f"已写入 {path}（{len(report):,} 字符）")
        else:
            print(report)
        return 0
    finally:
        await connection.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(DEFAULT_DATABASE))
    sub = parser.add_subparsers(dest="command", required=True)

    new = sub.add_parser("new", help="提交一个新的研究委托（交互式）")
    new.add_argument("request", nargs="?", default="")
    new.add_argument("--corpus", default="")
    new.set_defaults(run=cmd_new)

    listing = sub.add_parser("list", help="列出所有任务")
    listing.set_defaults(run=cmd_list)

    show = sub.add_parser("show", help="查看任务状态，待审批时打印合同")
    show.add_argument("task_id")
    show.set_defaults(run=cmd_show)

    approve = sub.add_parser("approve", help="批准合同并开始研究")
    approve.add_argument("task_id")
    approve.add_argument("--note", default="")
    approve.add_argument("--corpus", default="")
    approve.add_argument("--no-run", action="store_true", help="只批准，不立即开始")
    approve.set_defaults(run=cmd_approve)

    resume = sub.add_parser("continue", help="继续一个已批准的任务")
    resume.add_argument("task_id")
    resume.add_argument("--corpus", default="")
    resume.set_defaults(run=cmd_continue)

    report = sub.add_parser("report", help="取出已发布的报告")
    report.add_argument("task_id")
    report.add_argument("-o", "--output", default="")
    report.set_defaults(run=cmd_report)

    args = parser.parse_args(argv)
    try:
        return asyncio.run(args.run(args))
    except KeyboardInterrupt:
        print("\n已中断。产物都已落库，用 continue 接着跑即可。")
        return 130
    except ValueError as error:
        # Wrong task number, unapproved task, missing corpus root: all things the
        # user can fix, so they get a sentence rather than a traceback.
        print(f"\n无法执行：{error}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
