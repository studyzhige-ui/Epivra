"""Friendly client of the single local host; the UI owns no research state."""

import argparse
import asyncio
import sys
import uuid
from pathlib import Path

from prompt_toolkit.patch_stdout import patch_stdout

from . import cli_settings, host
from .locale import LANGUAGES, configure, set_language, tr
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
        return tr("已取消")
    if s.get("published"):
        return tr("已完成")
    if s.get("error"):
        return tr("需要处理")
    if s.get("paused"):
        return tr("已暂停")
    if not s.get("approved"):
        return tr("策略待审批") if s.get("plans") else tr("正在准备策略")
    return tr("研究中") if s.get("running") else tr("等待接续")


def strategy(plan):
    lines = [plan["text"]]
    brief = plan.get("brief", {})
    labels = {
        "subject": tr("研究对象"),
        "given_context": tr("已知背景"),
        "questions": tr("研究问题"),
        "material_scope": tr("资料范围"),
    }
    if brief:
        lines.append(tr("\n## 研究范围与前提"))
    for key, value in brief.items():
        if isinstance(value, dict):
            modes = {
                "case_materials": tr("针对本案例的资料"),
                "library": tr("待检索的资料库"),
                "unspecified": tr("尚未指定"),
            }
            value = (
                modes.get(value.get("mode"), value.get("mode", ""))
                + tr("；依据：")
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
                "Conflict": tr("状态已变化，请刷新并重新确认。"),
                "ValueError": tr("操作未完成，请检查配置、路径或当前研究状态。"),
                "NotAllowed": tr("当前状态不允许此操作，请先暂停研究。"),
            }
            raise ValueError(
                messages.get(result["error"], tr("操作未完成：") + result["error"])
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
                tr("连接与默认设置"),
                [
                    ("model", tr("研究模型")),
                    ("search", tr("搜索与网页读取")),
                    ("parser", tr("本地解析")),
                    ("analysis", tr("数据分析沙箱")),
                    ("mcp", tr("MCP 外部连接")),
                    ("language", "简体中文 / English"),
                ],
            )
            if choice is None:
                return
            if choice == "language":
                language = await self.ui.choose(
                    "简体中文 / English", [("zh-CN", "简体中文"), ("en", "English")]
                )
                if language:
                    set_language(language)
                continue
            keys = cli_settings.configured(self.root)
            if choice == "model":
                provider = await self.ui.choose(
                    tr("模型厂商"),
                    [
                        (
                            k,
                            tr(LABELS.get(k, k))
                            + (tr(" · 已配置密钥") if v.credential_env in keys else ""),
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
                    tr("替换此厂商的密钥？")
                ):
                    key = await self.ui.text(tr("API Key（输入隐藏）"), secret=True)
                    if not key:
                        continue
                    overridden = cli_settings.save_key(
                        self.root, spec.credential_env, key
                    )
                    self.ui.show(
                        tr("密钥已保存，尚未进行付费联通测试。")
                        + (tr(" 当前环境变量会优先于该文件。") if overridden else "")
                    )
                model = await self.ui.text(tr("模型名称"), spec.default_model.id)
                if not model:
                    continue
                region = spec.default_region
                if len(spec.endpoints) > 1:
                    region = await self.ui.choose(
                        tr("账户地区"), [(r, r) for r, _ in spec.endpoints]
                    )
                    if region is None:
                        continue
                update = {"provider": provider, "model": model, "region": region}
                if model != spec.default_model.id:
                    self.ui.show(tr("此模型不在已核验预设中，请按官方文档填写容量。"))
                    for field, label in [
                        ("context_tokens", tr("上下文容量 tokens")),
                        ("max_tokens", tr("输出额度 tokens")),
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
                    tr("配置连接"), [(n, n) for n in CONNECTIONS]
                )
                if provider is None:
                    continue
                key = (
                    (
                        await self.ui.text(
                            tr("API Key（输入隐藏，留空不修改）"), secret=True
                        )
                    )
                    if CONNECTIONS[provider][1]
                    else None
                )
                if key:
                    cli_settings.save_key(self.root, CONNECTIONS[provider][1], key)
                if provider in SEARCH:
                    defaults["search_provider"] = provider
                if provider in READERS:
                    defaults["reader_provider"] = provider
            elif choice == "mcp":
                names = (await self.call("mcp_connections"))["servers"]
                if not names:
                    self.ui.show(
                        tr(
                            "请先在工作目录的 mcp-servers.json 配置连接和工具授权，格式见 docs/USAGE.md。"
                        )
                    )
                    continue
                enabled = defaults.get("mcp_servers", [])
                name = await self.ui.choose(
                    tr("MCP 连接（用于新研究）"),
                    [(n, n + (tr(" · 已启用") if n in enabled else "")) for n in names],
                )
                if name is None:
                    continue
                if name in enabled:
                    defaults["mcp_servers"] = [n for n in enabled if n != name]
                elif await self.ui.confirm(
                    tr(
                        "连接并启用该 MCP？将启动配置的本地程序或访问远端；工具权限以配置文件为准。"
                    )
                ):
                    catalog = await self.call("mcp_discover", name=name)
                    self.ui.show(
                        tr(
                            "已连接 · 发现 {0} 个工具、{1} 个资源；仅配置中授权的能力会提供给研究角色。",
                            len(catalog["tools"]),
                            len(catalog["resources"]),
                        )
                    )
                    defaults["mcp_servers"] = [*enabled, name]
            elif choice == "parser":
                mode = await self.ui.choose(
                    tr("解析方式"),
                    [
                        ("auto", tr("自动")),
                        ("light", tr("轻量解析")),
                        ("docling", tr("Docling 本地解析")),
                    ],
                )
                if mode is None:
                    continue
                defaults["parser"] = mode
                if mode == "docling":
                    self.ui.show(tr("选择已安装的 Docling 模型文件夹。"))
                    path = await self.ui.path(directory=True)
                    if path is None:
                        continue
                    defaults["docling_models"] = str(path)
            else:
                defaults["analysis"] = await self.ui.confirm(
                    tr("默认启用 Docker 数据分析？需要已经构建本地镜像。")
                )
            cli_settings.save(self.root, defaults)
            self.ui.show(tr("默认设置已保存，只应用于新研究。"))

    async def new(self):
        defaults = cli_settings.load(self.root)
        provider = defaults.get("provider", "deepseek")
        if OFFICIAL_PROVIDERS[provider].credential_env not in cli_settings.configured(
            self.root
        ):
            self.ui.show(tr("先配置一个研究模型，再创建研究。"))
            await self.configure()
            return
        text = await self.ui.text(tr("你希望研究什么？（用途、问题或期望成果）"))
        if not text:
            return
        scope = await self.ui.choose(
            tr("资料范围"),
            [
                ("web", tr("公开网络")),
                ("local", tr("仅使用本地资料")),
                ("both", tr("网络与本地资料")),
            ],
        )
        if scope is None:
            return
        files, roots = [], []
        if scope != "web":
            while True:
                action = await self.ui.choose(
                    tr("添加资料"),
                    [
                        ("file", tr("选择文件")),
                        ("folder", tr("授权文件夹")),
                        ("remove", tr("移除已选资料")),
                        ("done", tr("完成选择")),
                    ],
                )
                if action is None:
                    return
                if action == "remove":
                    selected = await self.ui.choose(
                        tr("移除哪项资料？"),
                        [(str(p), str(p)) for p in [*files, *roots]],
                    )
                    if selected:
                        files = [p for p in files if str(p) != selected]
                        roots = [p for p in roots if str(p) != selected]
                    continue
                if action == "done":
                    if files or roots:
                        break
                    self.ui.show(tr("请至少选择一份资料或一个文件夹。"))
                    continue
                path = await self.ui.path(directory=action == "folder")
                if path is None:
                    continue
                if not (path.is_dir() if action == "folder" else path.is_file()):
                    self.ui.show(tr("所选路径不存在或类型不符。"))
                    continue
                target = roots if action == "folder" else files
                if path not in target:
                    target.append(path)
                self.ui.show(tr("已选择：") + str(path))
        self.ui.show(
            tr(
                "\n研究：{0}\n模型：{1} / {2}\n联网：{3}",
                text,
                provider,
                defaults.get("model", OFFICIAL_PROVIDERS[provider].default_model.id),
                tr("是") if scope != "local" else tr("否"),
            )
        )
        for path in files:
            self.ui.show(tr("导入文件：") + str(path))
        for path in roots:
            self.ui.show(tr("授权读取文件夹及子目录：") + str(path))
        if not await self.ui.confirm(
            tr("生成初始策略？这一步将调用模型，正式研究仍需审批策略。")
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
                self.ui.show(tr("正在导入：") + path.name)
                imported = await self.call(
                    "import_file",
                    study=study,
                    expected=status["control"],
                    path=str(path),
                )
                self.ui.show(
                    tr(
                        "已导入 · {0} 字符 · {1}",
                        imported["characters"],
                        imported["coverage"],
                    )
                )
                for issue in imported.get("issues", []):
                    self.ui.show(str(issue))
            await self.command(study, status, "resume")
        except (ValueError, OSError, TimeoutError):
            self.ui.show(tr("研究已保留为暂停草稿，可从研究列表补充资料后继续。"))
            raise
        await self.study(study)

    async def study(self, study):
        while True:
            status = await self.call("status", study=study)
            self.ui.show(
                tr(
                    "\n{0}\n{1} · 资料 {2} 份",
                    status.get("request", tr("研究")),
                    stage(status),
                    status.get("source_count", 0),
                )
            )
            if status.get("approved"):
                elapsed = (status.get("timing") or {}).get("elapsed_seconds")
                duration = (
                    tr(
                        "{0}小时 {1}分 {2}秒",
                        int(elapsed // 3600),
                        int(elapsed // 60) % 60,
                        int(elapsed) % 60,
                    )
                    if elapsed is not None
                    else tr("未记录")
                )
                self.ui.show(tr("研究耗时：{0}", duration))
                self.ui.show(
                    tr("从首次批准策略到交付的总经过时间，包含暂停、等待与离线时间。")
                )
            if status.get("error"):
                self.ui.show(
                    tr(
                        "连续重复相同错误且没有进展，已停止自动尝试。请检查失败步骤，调整方法或补充资料后再恢复。"
                    )
                    if status["error"] == "RepeatedFailure"
                    else tr("阻断：")
                    + status["error"]
                    + tr("。可暂停后检查连接设置，更新密钥后重新载入。")
                )
            options = [("watch", tr("查看进度"))]
            if (
                status.get("plans")
                and not status.get("approved")
                and not status.get("cancelled")
            ):
                options.insert(0, ("approve", tr("阅读并审批研究策略")))
            if status.get("published"):
                options.insert(0, ("report", tr("阅读与导出报告")))
            if not status.get("cancelled"):
                if not status.get("published"):
                    options += [
                        (
                            "resume" if status.get("paused") else "pause",
                            tr("继续研究") if status.get("paused") else tr("暂停研究"),
                        ),
                    ]
                options += [("steer", tr("调整研究方向"))]
                if status.get("paused") and not status.get("running"):
                    options += [
                        ("upload", tr("补充资料文件")),
                        ("reload", tr("重新载入密钥")),
                    ]
                if not status.get("published"):
                    options += [("cancel", tr("取消研究"))]
            options += [
                (
                    "delete",
                    tr("删除研究")
                    if status.get("published") or status.get("cancelled")
                    else tr("终止并删除"),
                )
            ]
            options += [("files", tr("导出计算文件")), ("usage", tr("查看用量"))]
            action = await self.ui.choose(tr("下一步"), options)
            if action is None:
                return
            if action == "delete":
                if await self.ui.confirm(
                    tr(
                        "删除将终止此研究并永久清除其报告、资料副本和过程记录。用户原文件、已导出文件及其他研究不受影响。已提交的外部调用可能仍产生费用。确认删除？"
                    )
                ):
                    await self.call(
                        "delete",
                        study=study,
                        expected=status["control"],
                        confirmed=True,
                    )
                    return
            elif action == "approve":
                plan = status["plans"][-1]
                self.ui.page(strategy(plan["body"]))
                if await self.ui.confirm(tr("按上面这份策略开始研究？")):
                    await self.command(study, status, "approve", {"plan": plan["ref"]})
                    if status["paused"]:
                        self.ui.show(
                            tr("策略已审批，研究仍暂停；选择继续研究开始执行。")
                        )
            elif action in {"pause", "resume"}:
                await self.command(study, status, action)
            elif action == "cancel":
                if await self.ui.confirm(tr("取消后不能恢复此研究，确认取消？")):
                    await self.command(study, status, "cancel")
            elif action == "steer":
                text = await self.ui.text(
                    tr("新的研究需求（保留仍需满足的要求）"), status.get("request", "")
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
                        tr(
                            "已导入：{0} · {1} 字符",
                            result["coverage"],
                            result["characters"],
                        )
                    )
            elif action == "reload":
                await self.configure()
                await self.call("reload", study=study)
                self.ui.show(tr("密钥已重新载入。研究配置不变，选择继续研究以接续。"))
            elif action == "usage":
                groups = status.get("usage", [])
                if not groups:
                    self.ui.show(tr("暂无调用用量。"))
                for group in groups:
                    self.ui.show(
                        tr(
                            "{0} / {1} · {2} 次调用 · 未知结果 {3} 次",
                            group["resource"],
                            group["model"] or group.get("tool") or tr("工具调用"),
                            group["calls"],
                            group["unresolved_calls"],
                        )
                    )
                    labels = {
                        "input_tokens": tr("输入 tokens"),
                        "output_tokens": tr("输出 tokens"),
                        "total_tokens": tr("总 tokens"),
                        "cache_read_tokens": tr("缓存命中 tokens"),
                        "cache_write_tokens": tr("缓存写入 tokens"),
                        "reasoning_tokens": tr("推理 tokens（子项）"),
                        "search_credits": tr("服务 credits"),
                        "reader_tokens": tr("读取 tokens"),
                        "cost_usd": tr("供应商费用参考（USD）"),
                    }
                    for field, label in labels.items():
                        value = group["totals"].get(field)
                        if field == "total_tokens" and any(
                            group["totals"].get(k) is not None
                            for k in ("input_tokens", "output_tokens")
                        ):
                            continue
                        if value is not None:
                            self.ui.show(f"  {label}：{value}")
                            reported = group["reported_calls"][field]
                            if reported < group["calls"]:
                                self.ui.show(
                                    tr(
                                        "已返回用量：{0}/{1} 次调用",
                                        reported,
                                        group["calls"],
                                    )
                                )
                    if not any(v is not None for v in group["totals"].values()):
                        self.ui.show(tr("此接口未返回计量数据，仅记录调用次数。"))
            elif action == "report":
                report = await self.call("report", study=study)
                if not report.get("text"):
                    self.ui.show(tr("当前方向尚无已发布报告，正在刷新状态。"))
                    continue
                self.ui.page(report["text"])
                if await self.ui.confirm(tr("将报告保存为 Markdown？")):
                    path = await self.ui.path(save=True)
                    if path:
                        with path.open("x", encoding="utf-8") as file:
                            file.write(report["text"])
                        self.ui.show(tr("已保存：") + str(path))
            elif action == "files":
                files = [f for a in status.get("analyses", []) for f in a["files"]]
                ref = await self.ui.choose(
                    tr("计算文件"), [(f["ref"], f["name"]) for f in files]
                )
                if ref:
                    path = await self.ui.path(save=True)
                    if path:
                        await self.call(
                            "export", study=study, source=ref, destination=str(path)
                        )
                        self.ui.show(tr("已保存：") + str(path))
            elif action == "watch":
                with patch_stdout():
                    await self.watch(study)

    async def watch(self, study):
        self.ui.show(tr("进度自动刷新。按 Enter 返回，后台研究继续。"))
        prompt = asyncio.create_task(self.ui.text(tr("Enter 返回")))
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
                        tr(
                            "{0} · 资料 {1} 份 · 已分配工作 {2} 项",
                            snapshot[0],
                            snapshot[1],
                            snapshot[2],
                        )
                    )
                    for work in status.get("work", [])[
                        (previous[2] if previous else 0) :
                    ]:
                        self.ui.show(
                            f"  {tr(ROLES.get(work['role'], work['role']))}：{work['task'][:150]}"
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
        self.ui.show(
            tr(
                "Epivra\n自主研究工作台 · 从问题到洞见\n确认策略后自主研究，可暂停或调整方向；退出界面后后台任务继续"
            )
        )
        while True:
            try:
                action = await self.ui.choose(
                    tr("工作台"),
                    [
                        ("new", tr("新建研究")),
                        ("list", tr("我的研究")),
                        ("settings", tr("连接与设置")),
                    ],
                    back=tr("退出"),
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
                        self.ui.show(tr("还没有研究，可以新建一个。"))
                        continue
                    study = await self.ui.choose(
                        tr("我的研究"),
                        [
                            (s["study"], f"{stage(s)} · {s['request'][:70]}")
                            for s in studies
                        ],
                    )
                    if study:
                        await self.study(study)
            except (ValueError, OSError, TimeoutError) as exc:
                if isinstance(exc, FileExistsError):
                    self.ui.show(tr("目标文件已存在，请选择另一个名称。"))
                elif isinstance(exc, TimeoutError):
                    self.ui.show(
                        tr(
                            "等待响应超时，操作可能仍在后台执行。请刷新状态，不要重复创建研究。"
                        )
                    )
                else:
                    self.ui.show(
                        str(exc)
                        if isinstance(exc, ValueError)
                        else tr("无法访问文件或宿主，请检查路径和宿主状态。")
                    )


def main():
    configure()
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--lang", choices=LANGUAGES)
    args, remaining = parser.parse_known_args()
    if remaining and remaining[0] == "web":
        from . import webui

        webui.main(
            [
                "--root",
                str(args.root),
                *(["--lang", args.lang] if args.lang else []),
                *remaining[1:],
            ]
        )
        return
    if remaining and remaining != ["ui"]:
        if "--help" in remaining:
            print(
                tr(
                    "无参数或 ui：终端工作台；web：本地浏览器工作台。以下子命令保留 JSON 自动化接口。\n"
                )
            )
        host.main()
        return
    if not sys.stdin.isatty():
        print(tr("交互工作台需要终端。自动化请使用 epivra --help 中的子命令。"))
        return
    root = args.root.resolve()

    async def launch():
        await host.start(root)
        await Workbench(root).run()

    try:
        asyncio.run(launch())
    except (KeyboardInterrupt, EOFError):
        print(tr("\n已离开工作台，后台研究继续。"))
    except (OSError, ValueError, RuntimeError):
        print(tr("无法启动工作台，请检查工作目录与 .epivra/host.log。"))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
