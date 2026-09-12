"""Friendly client of the single local host; the UI owns no research state."""

import argparse
import asyncio
import sys
import uuid
from pathlib import Path

from prompt_toolkit.patch_stdout import patch_stdout

from . import cli_settings, host
from .model_catalog import OFFICIAL_PROVIDERS
from .terminal import Terminal
from .web_providers import CONNECTIONS, READERS, SEARCH

LABELS = {
    "openai": "OpenAI",
    "claude": "Claude",
    "gemini": "Gemini",
    "grok": "Grok",
    "deepseek": "DeepSeek",
    "qwen": "通义千问",
    "kimi": "Kimi",
    "glm": "智谱 GLM",
    "doubao": "豆包",
    "minimax": "MiniMax",
    "hunyuan": "腾讯混元",
    "ernie": "百度文心",
}
ROLES = {
    "lead": "研究负责人",
    "investigator": "调查",
    "synthesizer": "综合",
    "writer": "写作",
    "reviewer": "核查",
}


def stage(s):
    if s.get("cancelled"):
        return "已取消"
    if s.get("published"):
        return "已完成"
    if s.get("error"):
        return "需要处理"
    if s.get("paused"):
        return "已暂停"
    if not s.get("approved"):
        return "策略待审批" if s.get("plans") else "正在准备策略"
    return "研究中" if s.get("running") else "等待接续"


def strategy(plan):
    lines = [plan["text"]]
    brief = plan.get("brief", {})
    labels = {
        "subject": "研究对象",
        "given_context": "已知背景",
        "questions": "研究问题",
        "material_scope": "资料范围",
    }
    if brief:
        lines.append("\n## 研究范围与前提")
    for key, value in brief.items():
        if isinstance(value, dict):
            modes = {
                "case_materials": "针对本案例的资料",
                "library": "待检索的资料库",
                "unspecified": "尚未指定",
            }
            value = (
                modes.get(value.get("mode"), value.get("mode", ""))
                + "；依据："
                + value.get("basis", "")
            )
        elif isinstance(value, list):
            value = "；".join(map(str, value))
        lines.append(f"- {labels.get(key, key)}：{value}")
    return "\n".join(lines)


class Workbench:
    def __init__(self, root, ui=None, send=None):
        self.root = root
        self.ui = ui or Terminal()
        self.send = send or host.send

    async def call(self, action, **fields):
        result = await self.send(self.root, {"action": action, **fields})
        if result.get("error") and action not in {"status"}:
            messages = {
                "Conflict": "状态已变化，请刷新并重新确认。",
                "ValueError": "操作未完成，请检查配置、路径或当前研究状态。",
                "NotAllowed": "当前状态不允许此操作，请先暂停研究。",
            }
            raise ValueError(
                messages.get(result["error"], "操作未完成：" + result["error"])
            )
        return result

    async def command(self, study, status, command, payload=None):
        return await self.call(
            "control",
            study=study,
            expected=status["control"],
            command=command,
            payload=payload or {},
            command_id=uuid.uuid4().hex,
        )

    async def configure(self):
        defaults = cli_settings.load(self.root)
        while True:
            choice = await self.ui.choose(
                "连接与默认设置",
                [
                    ("model", "研究模型"),
                    ("search", "搜索与网页读取"),
                    ("parser", "本地解析"),
                    ("analysis", "数据分析沙箱"),
                ],
            )
            if choice is None:
                return
            keys = cli_settings.configured(self.root)
            if choice == "model":
                provider = await self.ui.choose(
                    "模型厂商",
                    [
                        (
                            k,
                            LABELS.get(k, k)
                            + (" · 已配置密钥" if v.credential_env in keys else ""),
                        )
                        for k, v in sorted(
                            OFFICIAL_PROVIDERS.items(),
                            key=lambda item: item[1].credential_env not in keys,
                        )
                    ],
                )
                if provider is None:
                    continue
                spec = OFFICIAL_PROVIDERS[provider]
                if spec.credential_env not in keys or await self.ui.confirm(
                    "替换此厂商的密钥？"
                ):
                    key = await self.ui.text("API Key（输入隐藏）", secret=True)
                    if not key:
                        continue
                    overridden = cli_settings.save_key(
                        self.root, spec.credential_env, key
                    )
                    self.ui.show(
                        "密钥已保存，尚未进行付费联通测试。"
                        + (" 当前环境变量会优先于该文件。" if overridden else "")
                    )
                model = await self.ui.text("模型名称", spec.default_model.id)
                if not model:
                    continue
                region = spec.default_region
                if len(spec.endpoints) > 1:
                    region = await self.ui.choose(
                        "账户地区", [(r, r) for r, _ in spec.endpoints]
                    )
                    if region is None:
                        continue
                update = {"provider": provider, "model": model, "region": region}
                if model != spec.default_model.id:
                    self.ui.show("此模型不在已核验预设中，请按官方文档填写容量。")
                    for field, label in [
                        ("context_tokens", "上下文容量 tokens"),
                        ("max_tokens", "输出额度 tokens"),
                    ]:
                        value = await self.ui.text(label)
                        if not value:
                            return
                        update[field] = int(value)
                for field in ("context_tokens", "max_tokens"):
                    defaults.pop(field, None)
                defaults.update(update)
            elif choice == "search":
                provider = await self.ui.choose(
                    "配置连接", [(n, n) for n in CONNECTIONS]
                )
                if provider is None:
                    continue
                key = (
                    (await self.ui.text("API Key（输入隐藏，留空不修改）", secret=True))
                    if CONNECTIONS[provider][1]
                    else None
                )
                if key:
                    cli_settings.save_key(self.root, CONNECTIONS[provider][1], key)
                if provider in SEARCH:
                    defaults["search_provider"] = provider
                if provider in READERS:
                    defaults["reader_provider"] = provider
            elif choice == "parser":
                mode = await self.ui.choose(
                    "解析方式",
                    [
                        ("auto", "自动"),
                        ("light", "轻量解析"),
                        ("docling", "Docling 本地解析"),
                    ],
                )
                if mode is None:
                    continue
                defaults["parser"] = mode
                if mode == "docling":
                    self.ui.show("选择已安装的 Docling 模型文件夹。")
                    path = await self.ui.path(directory=True)
                    if path is None:
                        continue
                    defaults["docling_models"] = str(path)
            else:
                defaults["analysis"] = await self.ui.confirm(
                    "默认启用 Docker 数据分析？需要已经构建本地镜像。"
                )
            cli_settings.save(self.root, defaults)
            self.ui.show("默认设置已保存，只应用于新研究。")

    async def new(self):
        defaults = cli_settings.load(self.root)
        provider = defaults.get("provider", "deepseek")
        if OFFICIAL_PROVIDERS[provider].credential_env not in cli_settings.configured(
            self.root
        ):
            self.ui.show("先配置一个研究模型，再创建研究。")
            await self.configure()
            return
        text = await self.ui.text("你希望研究什么？（用途、问题或期望成果）")
        if not text:
            return
        scope = await self.ui.choose(
            "资料范围",
            [
                ("web", "公开网络"),
                ("local", "仅使用本地资料"),
                ("both", "网络与本地资料"),
            ],
        )
        if scope is None:
            return
        files, roots = [], []
        if scope != "web":
            while True:
                action = await self.ui.choose(
                    "添加资料",
                    [
                        ("file", "选择文件"),
                        ("folder", "授权文件夹"),
                        ("remove", "移除已选资料"),
                        ("done", "完成选择"),
                    ],
                )
                if action is None:
                    return
                if action == "remove":
                    selected = await self.ui.choose(
                        "移除哪项资料？", [(str(p), str(p)) for p in [*files, *roots]]
                    )
                    if selected:
                        files = [p for p in files if str(p) != selected]
                        roots = [p for p in roots if str(p) != selected]
                    continue
                if action == "done":
                    if files or roots:
                        break
                    self.ui.show("请至少选择一份资料或一个文件夹。")
                    continue
                path = await self.ui.path(directory=action == "folder")
                if path is None:
                    continue
                if not (path.is_dir() if action == "folder" else path.is_file()):
                    self.ui.show("所选路径不存在或类型不符。")
                    continue
                target = roots if action == "folder" else files
                if path not in target:
                    target.append(path)
                self.ui.show("已选择：" + str(path))
        self.ui.show(
            f"\n研究：{text}\n模型：{provider} / {defaults.get('model', OFFICIAL_PROVIDERS[provider].default_model.id)}\n联网：{'是' if scope != 'local' else '否'}"
        )
        for path in files:
            self.ui.show("导入文件：" + str(path))
        for path in roots:
            self.ui.show("授权读取文件夹及子目录：" + str(path))
        if not await self.ui.confirm(
            "生成初始策略？这一步将调用模型，正式研究仍需审批策略。"
        ):
            return
        result = await self.call(
            "create",
            **defaults,
            request=text,
            web=scope != "local",
            local_roots=[str(p) for p in roots],
            draft=True,
        )
        study = result["study"]
        status = await self.call("status", study=study)
        try:
            for path in files:
                self.ui.show("正在导入：" + path.name)
                imported = await self.call(
                    "import_file",
                    study=study,
                    expected=status["control"],
                    path=str(path),
                )
                self.ui.show(
                    f"已导入 · {imported['characters']} 字符 · {imported['coverage']}"
                )
                for issue in imported.get("issues", []):
                    self.ui.show(str(issue))
            await self.command(study, status, "resume")
        except (ValueError, OSError, TimeoutError):
            self.ui.show("研究已保留为暂停草稿，可从研究列表补充资料后继续。")
            raise
        await self.study(study)

    async def study(self, study):
        while True:
            status = await self.call("status", study=study)
            self.ui.show(
                f"\n{status.get('request', '研究')}\n{stage(status)} · 资料 {status.get('source_count', 0)} 份"
            )
            if status.get("error"):
                self.ui.show(
                    "阻断："
                    + status["error"]
                    + "。可暂停后检查连接设置，更新密钥后重新载入。"
                )
            options = [("watch", "查看进度")]
            if (
                status.get("plans")
                and not status.get("approved")
                and not status.get("cancelled")
            ):
                options.insert(0, ("approve", "阅读并审批研究策略"))
            if status.get("published"):
                options.insert(0, ("report", "阅读与导出报告"))
            if not status.get("cancelled"):
                options += [
                    (
                        "resume" if status.get("paused") else "pause",
                        "继续研究" if status.get("paused") else "暂停研究",
                    ),
                    ("steer", "调整研究方向"),
                ]
                if status.get("paused") and not status.get("running"):
                    options += [("upload", "补充资料文件"), ("reload", "重新载入密钥")]
                options += [("cancel", "取消研究")]
            options += [("files", "导出计算文件"), ("usage", "查看用量")]
            action = await self.ui.choose("下一步", options)
            if action is None:
                return
            if action == "approve":
                plan = status["plans"][-1]
                self.ui.page(strategy(plan["body"]))
                if await self.ui.confirm("按上面这份策略开始研究？"):
                    await self.command(study, status, "approve", {"plan": plan["ref"]})
                    if status["paused"]:
                        self.ui.show("策略已审批，研究仍暂停；选择继续研究开始执行。")
            elif action in {"pause", "resume"}:
                await self.command(study, status, action)
            elif action == "cancel":
                if await self.ui.confirm("取消后不能恢复此研究，确认取消？"):
                    await self.command(study, status, "cancel")
            elif action == "steer":
                text = await self.ui.text(
                    "新的研究需求（保留仍需满足的要求）", status.get("request", "")
                )
                if text:
                    await self.command(study, status, "steer", {"request": text})
            elif action == "upload":
                path = await self.ui.path()
                if path:
                    result = await self.call(
                        "import_file",
                        study=study,
                        expected=status["control"],
                        path=str(path),
                    )
                    self.ui.show(
                        f"已导入：{result['coverage']} · {result['characters']} 字符"
                    )
            elif action == "reload":
                await self.configure()
                await self.call("reload", study=study)
                self.ui.show("密钥已重新载入。研究配置不变，选择继续研究以接续。")
            elif action == "usage":
                groups = status.get("usage", [])
                if not groups:
                    self.ui.show("暂无调用用量。")
                for group in groups:
                    self.ui.show(
                        f"{group['resource']} / {group['model'] or '搜索'} · {group['calls']} 次调用 · 未知结果 {group['unresolved_calls']} 次"
                    )
                    labels = {
                        "input_tokens": "输入 tokens",
                        "output_tokens": "输出 tokens",
                        "cache_read_tokens": "缓存命中 tokens",
                        "search_credits": "搜索 credits",
                    }
                    for field, label in labels.items():
                        value = group["totals"].get(field)
                        self.ui.show(
                            f"  {label}：{value if value is not None else '未报告'}"
                        )
            elif action == "report":
                report = await self.call("report", study=study)
                if not report.get("text"):
                    self.ui.show("当前方向尚无已发布报告，正在刷新状态。")
                    continue
                self.ui.page(report["text"])
                if await self.ui.confirm("将报告保存为 Markdown？"):
                    path = await self.ui.path(save=True)
                    if path:
                        with path.open("x", encoding="utf-8") as file:
                            file.write(report["text"])
                        self.ui.show("已保存：" + str(path))
            elif action == "files":
                files = [f for a in status.get("analyses", []) for f in a["files"]]
                ref = await self.ui.choose(
                    "计算文件", [(f["ref"], f["name"]) for f in files]
                )
                if ref:
                    path = await self.ui.path(save=True)
                    if path:
                        await self.call(
                            "export", study=study, source=ref, destination=str(path)
                        )
                        self.ui.show("已保存：" + str(path))
            elif action == "watch":
                with patch_stdout():
                    await self.watch(study)

    async def watch(self, study):
        self.ui.show("进度自动刷新。按 Enter 返回，后台研究继续。")
        prompt = asyncio.create_task(self.ui.text("Enter 返回"))
        previous = None
        try:
            while not prompt.done():
                status = await self.call("status", study=study)
                snapshot = (
                    stage(status),
                    status.get("source_count"),
                    len(status.get("work", [])),
                )
                if snapshot != previous:
                    self.ui.show(
                        f"{snapshot[0]} · 资料 {snapshot[1]} 份 · 已分配工作 {snapshot[2]} 项"
                    )
                    for work in status.get("work", [])[
                        (previous[2] if previous else 0) :
                    ]:
                        self.ui.show(
                            f"  {ROLES.get(work['role'], work['role'])}：{work['task'][:150]}"
                        )
                    previous = snapshot
                if (
                    status.get("published")
                    or status.get("error")
                    or (status.get("plans") and not status.get("approved"))
                ):
                    return
                await asyncio.wait({prompt}, timeout=2)
        finally:
            prompt.cancel()
            await asyncio.gather(prompt, return_exceptions=True)

    async def run(self):
        self.ui.show("Deep Research\n研究工作台 · 退出界面后后台任务继续")
        while True:
            try:
                action = await self.ui.choose(
                    "工作台",
                    [
                        ("new", "新建研究"),
                        ("list", "我的研究"),
                        ("settings", "连接与设置"),
                    ],
                    back="退出",
                )
                if action is None:
                    return
                if action == "settings":
                    await self.configure()
                elif action == "new":
                    await self.new()
                else:
                    studies = (await self.call("overview"))["studies"]
                    if not studies:
                        self.ui.show("还没有研究，可以新建一个。")
                        continue
                    study = await self.ui.choose(
                        "我的研究",
                        [
                            (s["study"], f"{stage(s)} · {s['request'][:70]}")
                            for s in studies
                        ],
                    )
                    if study:
                        await self.study(study)
            except (ValueError, OSError, TimeoutError) as exc:
                if isinstance(exc, FileExistsError):
                    self.ui.show("目标文件已存在，请选择另一个名称。")
                elif isinstance(exc, TimeoutError):
                    self.ui.show(
                        "等待响应超时，操作可能仍在后台执行。请刷新状态，不要重复创建研究。"
                    )
                else:
                    self.ui.show(
                        str(exc)
                        if isinstance(exc, ValueError)
                        else "无法访问文件或宿主，请检查路径和宿主状态。"
                    )


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args, remaining = parser.parse_known_args()
    if remaining and remaining != ["ui"]:
        if "--help" in remaining:
            print("无参数或 ui：打开交互工作台。以下子命令保留 JSON 自动化接口。\n")
        host.main()
        return
    if not sys.stdin.isatty():
        print("交互工作台需要终端。自动化请使用 deep-research --help 中的子命令。")
        return
    root = args.root.resolve()

    async def launch():
        await host.start(root)
        await Workbench(root).run()

    try:
        asyncio.run(launch())
    except (KeyboardInterrupt, EOFError):
        print("\n已离开工作台，后台研究继续。")
    except (OSError, ValueError, RuntimeError):
        print("无法启动工作台，请检查工作目录与 .deep-research-agent/host.log。")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
