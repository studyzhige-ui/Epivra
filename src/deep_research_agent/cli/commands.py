"""Deep Research 命令行入口。

一次研究要花几十分钟，中间还必须由人批准一份研究合同，所以交互不是"一条命令跑到底"，
而是：

    提交问题 → 读审批卡 → 批准 → 继续（可随时中断）→ 取报告

状态全部在数据库里，命令行自己不持有任何状态。中断后重新执行 ``continue`` 就接着跑，
已完成的付费调用只回放、不重发。

用法::

    deep-research new            # 交互式提交（语言、来源授权、厂商都会问）
    deep-research list
    deep-research show   <任务号>
    deep-research approve <任务号>
    deep-research continue <任务号>
    deep-research report <任务号> [-o 文件]
"""

from __future__ import annotations

import argparse
import getpass
import sys
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path

import aiosqlite

from ..application import load_environment, render_role_models
from ..config import load_config
from ..providers import search_credentials
from ..providers.llm import LLM_PROVIDERS
from ..service import Event, ResearchService, Task

#: Where a user's studies and configuration live when the command is installed.
from .paths import config_file as config_path

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


# ------------------------------------------------------------------ 欢迎与自检


BANNER = """\
  ╭──────────────────────────────────────────────────────────────╮
  │  Deep Research Agent                                         │
  ╰──────────────────────────────────────────────────────────────╯

  把一个开放的研究问题，做成一份每条重要事实都能回溯到来源原文的报告。

  它不会先动手再解释：先给你一份研究方案——研究什么、看哪些证据、交付
  什么、哪些边界一改就得重新批准——你批准之后，才开始花钱检索。
  证据不足时它会如实说「不足」，而不是把话说满。
"""


def _readiness(environ: Mapping[str, str]) -> tuple[list[str], list[str]]:
    """``(就绪, 缺失)``：影响能否开工的条件，用用户能照做的话写。"""

    ready: list[str] = []
    missing: list[str] = []

    vendors = [spec.name for spec in LLM_PROVIDERS if spec.api_key(environ)]
    if vendors:
        ready.append(f"模型厂商：{'、'.join(vendors)}")
    else:
        names = "、".join(spec.key_env_var for spec in LLM_PROVIDERS)
        missing.append(
            "没有任何模型厂商的密钥。研究无法开始。\n"
            f"      在项目根目录建一个 .env 文件，写入其中任意一个：{names}"
        )

    keyed = [
        name
        for name, env_var in sorted(search_credentials().items())
        if environ.get(env_var, "").strip()
    ]
    if keyed:
        ready.append(f"网页搜索：{'、'.join(keyed)}（另有 DuckDuckGo 兜底）")
    else:
        ready.append("网页搜索：仅 DuckDuckGo（无需密钥）")
        missing.append(
            "没有付费搜索厂商的密钥，检索质量会明显下降但仍能运行。\n"
            "      想提升的话，在 .env 里加 TAVILY_API_KEY 之类的任意一个。"
        )
    ready.append("学术索引：arXiv、Crossref、PubMed（都不需要密钥）")
    return ready, missing


def _welcome(environ: Mapping[str, str], *, database: Path) -> None:
    print(BANNER)
    ready, missing = _readiness(environ)
    print("  当前环境")
    for line in ready:
        print(f"    ✓ {line}")
    for line in missing:
        print(f"    ! {line}")
    if database.is_file():
        print(f"    ✓ 任务库：{database}")
    else:
        print(f"    · 任务库还未创建，第一次提交时会自动建在 {database}")


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
    environ = dict(load_environment(config_path()))
    _ready, missing = _readiness(environ)
    blocking = [line for line in missing if "无法开始" in line]
    if blocking:
        print(BANNER)
        for line in blocking:
            print(f"  ! {line}")
        print("\n  配好密钥后再执行一次就行。")
        return 2

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

    # Everything the user chose, in one place, before the first paid call.  The
    # Architect call is cheap; the research that follows is not, so the summary
    # sits here rather than after the Contract is already written.
    print("\n────────── 请确认 ──────────")
    print(f"  研究问题：{request}")
    print(f"  交付语言：{language}")
    print(f"  来源授权：{'、'.join(source_access)}" + (f"（{corpus}）" if corpus else ""))
    print(f"  模型厂商：{vendor}")
    if access_key != "local_only":
        print(f"  网页搜索：{'、'.join(config.search_providers)}")
        print(f"  学术索引：{'、'.join(config.academic_providers) or '（不使用）'}")
    print("\n  角色 → 模型：")
    print(render_role_models(config))
    print(
        "\n  接下来只做一件事：由 Architect 写出研究方案交给你审批"
        "（一次模型调用，很便宜）。\n"
        "  真正花钱的检索要等你批准之后才开始。"
    )
    if _ask("\n继续吗？(y/n)", "y").casefold() not in ("y", "yes", "是"):
        print("已取消，什么都没有发生。")
        return 0

    connection, service = await _service(args, environ)
    try:
        print("\n正在生成研究方案…（通常 30–90 秒）")
        task = await service.open_task(
            request,
            language=language,
            source_access=source_access,  # type: ignore[arg-type]
            created_at=datetime.now(UTC).isoformat(timespec="seconds"),
            listen=_render,
        )
        print(f"\n任务号：{task.task_id}")
        if task.state == "clarification_requested":
            print(
                "这个委托太模糊，无法定出一个方案——上面那个问题的两种答案会导向"
                "两份完全不同的研究。\n"
                "把答案补进问题里，再执行一次 `deep-research new` 就行。"
            )
            return 0
        print(
            "上面就是研究方案。请读一遍，特别看这三处：\n"
            "  · 核心问题 Q1 —— 报告最后必须回答它，写错了后面全跑偏\n"
            "  · 默认假设   —— 它替你做的决定，不同意就改问题重新提交\n"
            "  · 不支持的用途 —— 这份报告不能拿去做什么\n\n"
            "同意就执行（之后开始真正花钱的检索）：\n"
            f"  deep-research approve {task.task_id}\n"
            "不同意就直接换个说法重新 `deep-research new`，这个任务留着不影响。"
        )
        return 0
    finally:
        await connection.close()


async def cmd_list(args: argparse.Namespace) -> int:
    connection, service = await _service(args, load_environment(config_path()))
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
    connection, service = await _service(args, load_environment(config_path()))
    try:
        task = await service.task(args.task_id)
        print(_render_task(task))
        if task.state == "awaiting_approval":
            print("\n" + await service.approval_card(args.task_id))
        return 0
    finally:
        await connection.close()


async def cmd_approve(args: argparse.Namespace) -> int:
    connection, service = await _service(args, load_environment(config_path()))
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
    connection, service = await _service(args, load_environment(config_path()))
    try:
        state = await service.advance(args.task_id, listen=_render)
        print(f"\n当前状态：{state}")
        return 0
    finally:
        await connection.close()


async def cmd_report(args: argparse.Namespace) -> int:
    connection, service = await _service(args, load_environment(config_path()))
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


def _secret(prompt: str) -> str:
    """Read a credential without echoing it, falling back if the tty cannot.

    A key pasted into a terminal ends up in shell history and scrollback, so it
    is read through getpass where possible.  Some environments have no usable
    tty; there the visible prompt is better than refusing to configure at all.
    """

    try:
        value = getpass.getpass(f"{prompt}：")
    except (EOFError, getpass.GetPassWarning, OSError):
        value = input(f"{prompt}（注意：输入会显示）：")
    return value.strip()


async def cmd_delete(args: argparse.Namespace) -> int:
    """Delete a study and everything it produced.  Irreversible.

    Command mode is scriptable, so the confirmation reads from stdin only when a
    terminal is attached; ``--yes`` is the way an automated caller opts in. A
    destructive default would make `deep-research delete` in a loop catastrophic.
    """

    connection, service = await _service(args, load_environment(config_path()))
    try:
        task = await service.task(args.task_id)
        if not args.yes:
            if not sys.stdin.isatty():
                print(
                    "拒绝在非交互环境下删除。加 --yes 明确确认。",
                    file=sys.stderr,
                )
                return 2
            print(f"\n将要永久删除：{task.request[:60]}")
            print("已经完成的研究工作和收集的素材都会被删除。删除后无法继续。")
            if input("输入 delete 确认：").strip().casefold() != "delete":
                print("已取消，什么都没有删除。")
                return 1
        removed = await service.delete_research(args.task_id)
        print("研究已删除。" if removed else "没有找到这项研究。")
        return 0 if removed else 1
    finally:
        await connection.close()


async def cmd_init(args: argparse.Namespace) -> int:
    """交互式写出配置文件，不需要用户手改 .env。"""

    print(BANNER)
    target = Path(args.config) if args.config else config_path()
    if target.is_file() and not args.force:
        print(f"  配置文件已存在：{target}")
        print("  想重新配置就加 --force（会覆盖），或直接编辑该文件。")
        return 1

    print("  下面配置两件事：一个模型厂商的密钥（必需），一个搜索厂商的密钥（可选）。")
    print(f"  会写入 {target}\n")

    vendor = _choose(
        "用哪家模型厂商？",
        [
            (spec.name, f"{spec.name}（密钥变量 {spec.key_env_var}）")
            for spec in sorted(LLM_PROVIDERS, key=lambda item: item.name)
        ],
    )
    spec = next(item for item in LLM_PROVIDERS if item.name == vendor)
    while True:
        key = _secret(f"粘贴 {vendor} 的 API 密钥")
        if key:
            break
        print("  密钥不能为空——没有它无法开始研究。")

    lines = [
        "# Deep Research Agent 配置。这个文件包含密钥，不要提交到 git。",
        f"{spec.key_env_var}={key}",
        f"DEEP_RESEARCH_LLM_PROVIDER={vendor}",
    ]

    print(
        "\n搜索厂商是可选的。不配也能跑（DuckDuckGo 兜底 + arXiv/Crossref/PubMed），"
        "但检索质量会明显下降。"
    )
    credentials = sorted(search_credentials().items())
    search = _choose(
        "配一个网页搜索厂商吗？",
        [("", "先跳过，以后再说")]
        + [(name, f"{name}（密钥变量 {env_var}）") for name, env_var in credentials],
    )
    if search:
        env_var = dict(credentials)[search]
        value = _secret(f"粘贴 {search} 的 API 密钥")
        if value:
            lines.append(f"{env_var}={value}")
            lines.append(f"DEEP_RESEARCH_SEARCH_PROVIDERS={search}")
        else:
            print("  没有输入，跳过。")

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    # 0600 where the platform supports it: the file holds credentials.
    try:
        target.chmod(0o600)
    except OSError:
        pass

    print(f"\n  ✓ 已写入 {target}")
    print("  下一步：deep-research doctor  确认环境，然后 deep-research new 开始。")
    return 0


async def cmd_doctor(args: argparse.Namespace) -> int:

    environ = load_environment(config_path())
    database = Path(args.database)
    _welcome(environ, database=database)

    env_file = config_path()
    print()
    if env_file.is_file():
        print(f"  ✓ 读到配置文件 {env_file}")
    else:
        print(f"  ! 没有 {env_file}；密钥只能来自系统环境变量")

    _ready, missing = _readiness(environ)
    if any("无法开始" in line for line in missing):
        print("\n  结论：还不能开始研究。补上模型厂商密钥即可。")
        return 1
    print("\n  结论：可以开始。执行 `deep-research new`")
    return 0
