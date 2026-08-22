"""CLI interface language, kept deliberately small.

Two things are separate and must stay separate: the language of the *interface*
and the language of the *report*.  A user may read a Chinese interface and ask
for an English deliverable, or the reverse.  Conflating them would make the
choice of report language a choice about the whole tool.

This is a message catalogue, not an i18n framework.  Adding gettext, extraction
tooling and locale directories to translate one command-line surface would cost
more than it returns; a dict keyed by message id is auditable at a glance and a
missing key fails loudly in tests rather than silently showing English to a
Chinese user.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Final

#: Interface languages this CLI speaks.  ``code`` is what gets persisted.
CLI_LANGUAGES: Final[tuple[tuple[str, str], ...]] = (
    ("zh-CN", "简体中文"),
    ("en", "English"),
)

DEFAULT_CLI_LANGUAGE: Final[str] = "zh-CN"

#: message id -> {language code: template}
_CATALOGUE: Final[Mapping[str, Mapping[str, str]]] = {
    # --- brand ------------------------------------------------------------
    "brand.name": {"zh-CN": "Deep Research", "en": "Deep Research"},
    # --- readiness --------------------------------------------------------
    "ready.prefix": {"zh-CN": "已就绪", "en": "Ready"},
    "ready.unconfigured": {
        "zh-CN": "还没有配置模型，配置之后才能开始研究",
        "en": "No model configured yet; research cannot start until one is",
    },
    "ready.investigator": {"zh-CN": "调查模型", "en": "Investigator model"},
    "ready.other_roles": {"zh-CN": "其他角色", "en": "Other roles"},
    # --- home -------------------------------------------------------------
    "home.prompt": {
        "zh-CN": "今天想研究点什么？",
        "en": "What would you like to research today?",
    },
    "home.prompt_hint": {
        "zh-CN": "给我一个主题，我们开始。",
        "en": "Give me a topic and we'll begin.",
    },
    "home.configure_first": {"zh-CN": "先配置模型", "en": "configure a model first"},
    "home.awaiting_one": {
        "zh-CN": "1 项研究正在等待你的决定",
        "en": "1 research plan is waiting for your decision",
    },
    "home.awaiting_many": {
        "zh-CN": "{count} 项研究正在等待你的决定",
        "en": "{count} research plans are waiting for your decision",
    },
    "home.recent_done": {"zh-CN": "最近完成", "en": "Recently completed"},
    "home.clarification_waiting": {
        "zh-CN": "有一项研究需要你补充一个信息",
        "en": "One research needs one more thing from you",
    },
    # --- actions ----------------------------------------------------------
    "action.configure": {"zh-CN": "配置模型与搜索", "en": "Configure models and search"},
    "action.review_approve": {"zh-CN": "查看并批准", "en": "Review and approve"},
    "action.new_research": {"zh-CN": "开始新的研究", "en": "Start a new research"},
    "action.all_research": {"zh-CN": "查看全部研究", "en": "View all research"},
    "action.settings": {"zh-CN": "设置", "en": "Settings"},
    "action.exit": {"zh-CN": "退出", "en": "Exit"},
    "action.back": {"zh-CN": "返回", "en": "Back"},
    "action.back_workspace": {"zh-CN": "返回 Workspace", "en": "Back to workspace"},
    "action.resume": {"zh-CN": "继续研究", "en": "Resume research"},
    "action.read_report": {"zh-CN": "阅读报告", "en": "Read the report"},
    "action.export_report": {"zh-CN": "导出 Markdown", "en": "Export Markdown"},
    "action.view_plan": {"zh-CN": "查看研究方案", "en": "View the research plan"},
    "action.approve_start": {"zh-CN": "批准并开始研究", "en": "Approve and start"},
    "action.request_changes": {"zh-CN": "提出修改", "en": "Request changes"},
    "action.answer_clarification": {"zh-CN": "回答这个问题", "en": "Answer the question"},
    "action.replan": {"zh-CN": "重新生成研究方案", "en": "Draft the plan again"},
    "action.save_for_later": {"zh-CN": "稍后处理", "en": "Review later"},
    "action.delete_running": {
        "zh-CN": "取消并删除研究",
        "en": "Cancel and delete this research",
    },
    "action.delete_done": {"zh-CN": "删除研究", "en": "Delete this research"},
    "action.use_these": {"zh-CN": "使用这些设置", "en": "Use these settings"},
    "action.change": {"zh-CN": "修改设置", "en": "Change settings"},
    "action.reenter": {"zh-CN": "重新输入", "en": "Re-enter"},
    "action.change_investigator": {
        "zh-CN": "修改 Investigator 模型",
        "en": "Change the Investigator model",
    },
    "action.change_other_roles": {
        "zh-CN": "修改其他角色模型",
        "en": "Change the model for the other roles",
    },
    "action.manage_vendors": {"zh-CN": "管理模型厂商", "en": "Manage model providers"},
    "action.manage_search": {"zh-CN": "管理网页搜索", "en": "Manage web search"},
    "action.back_settings": {"zh-CN": "返回设置", "en": "Back to settings"},
    "action.skip_for_now": {"zh-CN": "暂时跳过", "en": "Skip for now"},
    # --- setup ------------------------------------------------------------
    "setup.choose_cli_language": {
        "zh-CN": "界面语言 / Interface language",
        "en": "Interface language / 界面语言",
    },
    "setup.need_model": {
        "zh-CN": "开始之前需要配置一个模型。",
        "en": "Configure one model provider before you begin.",
    },
    "setup.choose_provider": {"zh-CN": "模型厂商", "en": "Model provider"},
    "setup.enter_key": {
        "zh-CN": "粘贴 {provider} 的 API 密钥",
        "en": "Paste the {provider} API key",
    },
    "setup.key_hidden": {
        "zh-CN": "输入不会显示。粘贴后按 Enter。",
        "en": "Nothing is echoed. Paste, then Enter.",
    },
    "setup.key_empty": {
        "zh-CN": "没有读到任何内容——密钥不能为空。",
        "en": "Nothing was entered; the key cannot be empty.",
    },
    "setup.has_key": {"zh-CN": "已保存密钥", "en": "key saved"},
    "setup.no_catalogue": {
        "zh-CN": "无法从 {provider} 取得模型列表：{reason}",
        "en": "Could not read the model list from {provider}: {reason}",
    },
    "setup.choose_model": {"zh-CN": "请选择模型", "en": "Choose a model"},
    "setup.type_model": {"zh-CN": "手动输入模型 id", "en": "Type a model id"},
    "setup.model_id_prompt": {
        "zh-CN": "模型 id（照抄厂商文档里的名字）",
        "en": "Model id (exactly as the vendor documents it)",
    },
    "setup.validating": {"zh-CN": "正在验证密钥…", "en": "Validating the key…"},
    "setup.invalid": {
        "zh-CN": "{provider} 验证失败：{reason}",
        "en": "{provider} validation failed: {reason}",
    },
    "setup.search_optional": {
        "zh-CN": "网页搜索可以提高研究质量，但不是必需的。",
        "en": "Web search improves quality but is not required.",
    },
    "setup.configure_search": {"zh-CN": "配置搜索", "en": "Configure search"},
    "setup.section_models": {"zh-CN": "模型", "en": "Models"},
    "setup.section_search": {"zh-CN": "搜索", "en": "Search"},
    "setup.unset": {"zh-CN": "未设置", "en": "not set"},
    "setup.no_search_keys": {
        "zh-CN": "只有 DuckDuckGo（无需密钥）",
        "en": "DuckDuckGo only (no key needed)",
    },
    "setup.investigator_hint": {
        "zh-CN": (
            "Investigator 在研究过程中需要处理大量搜索来源并进行初步分析，"
            "通常建议使用速度快、成本较低的模型。"
        ),
        "en": (
            "The Investigator handles many sources and makes frequent calls, so a "
            "fast, cheaper model is usually the better fit."
        ),
    },
    "setup.investigator_model": {
        "zh-CN": "Investigator 模型",
        "en": "Investigator model",
    },
    "setup.other_roles_model": {
        "zh-CN": "其他角色模型",
        "en": "Model for the other roles",
    },
    "setup.other_roles_hint": {
        "zh-CN": "用于 Architect、Lead、Curator、Analyst、Author、Reviewer。",
        "en": "Used by Architect, Lead, Curator, Analyst, Author and Reviewer.",
    },
    "setup.loading_models": {
        "zh-CN": "正在获取 {provider} 的可用模型…",
        "en": "Fetching available models from {provider}…",
    },
    # --- research settings ------------------------------------------------
    "cfg.title": {"zh-CN": "研究设置", "en": "Research settings"},
    "cfg.report_language": {"zh-CN": "报告语言", "en": "Report language"},
    "cfg.sources": {"zh-CN": "来源", "en": "Sources"},
    "cfg.model": {"zh-CN": "模型", "en": "Models"},
    "cfg.web_search": {"zh-CN": "网页搜索", "en": "Web search"},
    "cfg.academic": {"zh-CN": "学术索引", "en": "Academic indexes"},
    "cfg.corpus": {"zh-CN": "本地资料目录", "en": "Local corpus directory"},
    # --- source access ----------------------------------------------------
    "access.public_web": {"zh-CN": "公开网络", "en": "Public web"},
    "access.user_files": {
        "zh-CN": "公开网络 + 我的本地资料",
        "en": "Public web + my local files",
    },
    "access.local_only": {
        "zh-CN": "只用我的本地资料（完全不联网）",
        "en": "Local files only (never goes online)",
    },
    # --- new research -----------------------------------------------------
    "new.title": {"zh-CN": "新的研究委托", "en": "New research"},
    "new.generating": {"zh-CN": "正在生成研究方案…", "en": "Drafting the research plan…"},
    "new.not_started": {
        "zh-CN": "正式检索尚未开始。",
        "en": "No searching has started yet.",
    },
    "new.after_approve_costs": {
        "zh-CN": "批准后将开始模型和搜索调用。",
        "en": "Approving starts model and search calls.",
    },
    "clarify.title": {"zh-CN": "还需要确认一点", "en": "One thing to confirm"},
    "clarify.label": {"zh-CN": "待澄清", "en": "Open question"},
    "clarify.why": {
        "zh-CN": "为什么这会改变方案：{why}",
        "en": "Why this changes the plan: {why}",
    },
    "clarify.prompt": {"zh-CN": "你的回答", "en": "Your answer"},
    "clarify.working": {
        "zh-CN": "收到，正在继续整理研究方案…",
        "en": "Got it — working the plan out…",
    },
    "clarify.another": {
        "zh-CN": "还有一个问题需要你确认",
        "en": "One more thing to confirm",
    },
    "clarify.resolved": {"zh-CN": "研究方案已生成", "en": "The research plan is ready"},
    "plan.revise_prompt": {
        "zh-CN": "希望怎么调整这份研究方案？",
        "en": "What should change about this research plan?",
    },
    "plan.revising": {
        "zh-CN": "正在根据你的意见调整研究方案…",
        "en": "Revising the research plan from your instructions…",
    },
    # --- plan -------------------------------------------------------------
    "plan.read_these": {
        "zh-CN": "重点看：核心问题 Q1、默认假设、不支持的用途。",
        "en": "Look closely at: the core question Q1, the default assumptions, and the excluded uses.",
    },
    "plan.approved": {"zh-CN": "研究方案已批准", "en": "Research plan approved"},
    "plan.title": {"zh-CN": "研究方案", "en": "Research plan"},
    "plan.label": {"zh-CN": "方案版本", "en": "Plan version"},
    "plan.version": {
        "zh-CN": "研究方案 · 第 {version} 版",
        "en": "Research plan · version {version}",
    },
    # --- run --------------------------------------------------------------
    "run.stage.baseline": {"zh-CN": "建立研究基线", "en": "Establish the baseline"},
    "run.stage.breadth": {"zh-CN": "广度检索", "en": "Breadth search"},
    "run.stage.focus": {"zh-CN": "针对性调查", "en": "Focused investigation"},
    "run.stage.analysis": {"zh-CN": "分析", "en": "Analysis"},
    "run.stage.writing": {"zh-CN": "写作", "en": "Writing"},
    "run.stage.review": {"zh-CN": "独立审查", "en": "Independent review"},
    "run.current": {"zh-CN": "当前", "en": "Now"},
    "run.collected": {"zh-CN": "已收集", "en": "Collected"},
    "run.materials": {"zh-CN": "{count} 份素材", "en": "{count} materials"},
    "run.sources": {"zh-CN": "{count} 个来源", "en": "{count} sources"},
    # --- interrupt --------------------------------------------------------
    "interrupt.paused": {"zh-CN": "研究已安全暂停。", "en": "Research paused safely."},
    "interrupt.explain": {
        "zh-CN": "已完成的工作和素材都已经保存，继续时不会重新执行已完成的步骤。",
        "en": "Everything already done is saved; resuming does not repeat completed steps.",
    },
    "interrupt.on_exit": {
        "zh-CN": "研究已暂停。下次运行 deep-research 可以直接继续。",
        "en": "Research paused. Run deep-research again to continue.",
    },
    # --- completion -------------------------------------------------------
    "done.title": {"zh-CN": "研究完成", "en": "Research complete"},
    "done.report_chars": {"zh-CN": "报告", "en": "Report"},
    "done.cited": {"zh-CN": "引用素材", "en": "Cited materials"},
    "done.chars": {"zh-CN": "{count:,} 字符", "en": "{count:,} characters"},
    # --- task states ------------------------------------------------------
    "state.clarification_requested": {"zh-CN": "待澄清", "en": "Needs clarification"},
    "state.awaiting_approval": {"zh-CN": "等待批准", "en": "Awaiting approval"},
    "state.researching": {"zh-CN": "研究中", "en": "Researching"},
    "state.published": {"zh-CN": "已完成", "en": "Completed"},
    "state.paused": {"zh-CN": "已暂停", "en": "Paused"},
    # --- lists / detail ---------------------------------------------------
    "list.title": {"zh-CN": "我的研究", "en": "My research"},
    "list.empty": {"zh-CN": "还没有任何研究。", "en": "No research yet."},
    "detail.status": {"zh-CN": "状态", "en": "Status"},
    "detail.task_id": {"zh-CN": "任务标识", "en": "Task ID"},
    # --- destructive ------------------------------------------------------
    "delete.confirm_title": {
        "zh-CN": "永久取消这项研究？",
        "en": "Permanently cancel this research?",
    },
    "delete.confirm_body": {
        "zh-CN": "已经完成的研究工作和收集的素材都会被删除。删除后无法继续。",
        "en": "All work done and evidence collected will be deleted. This cannot be undone.",
    },
    "delete.keep": {"zh-CN": "保留研究", "en": "Keep it"},
    "delete.confirm": {"zh-CN": "永久取消并删除", "en": "Delete permanently"},
    "delete.done": {"zh-CN": "研究已删除。", "en": "Research deleted."},
    # --- receipts ---------------------------------------------------------
    # One line per completed action, carried onto the page the user lands on.
    # The selection that produced it is gone; the state it changed is in view.
    "receipt.investigator_updated": {
        "zh-CN": "Investigator 模型已更新",
        "en": "Investigator model updated",
    },
    "receipt.other_roles_updated": {
        "zh-CN": "其他角色模型已更新",
        "en": "Model for the other roles updated",
    },
    "receipt.vendor_added": {
        "zh-CN": "{provider} 连接成功",
        "en": "{provider} connected",
    },
    "receipt.search_added": {
        "zh-CN": "{provider} 连接成功",
        "en": "{provider} connected",
    },
    "receipt.plan_revised": {
        "zh-CN": "已生成第 {version} 版研究方案",
        "en": "Research plan version {version} is ready",
    },
    "receipt.defaults_saved": {
        "zh-CN": "研究默认值已保存",
        "en": "Research defaults saved",
    },
    "receipt.language_saved": {"zh-CN": "界面语言已保存", "en": "Interface language saved"},
    # --- settings page ----------------------------------------------------
    "settings.title": {"zh-CN": "设置", "en": "Settings"},
    "settings.cli_language": {"zh-CN": "界面语言", "en": "Interface language"},
    "settings.providers": {"zh-CN": "模型与搜索", "en": "Models and search"},
    "settings.defaults": {"zh-CN": "研究默认值", "en": "Research defaults"},
    # --- doctor -----------------------------------------------------------
    # --- generic ----------------------------------------------------------
    "generic.goodbye": {"zh-CN": "再见。", "en": "Goodbye."},
    "generic.yes": {"zh-CN": "是", "en": "Yes"},
    "generic.other": {"zh-CN": "其他（手动输入）", "en": "Other (type it)"},
    "generic.path_not_dir": {
        "zh-CN": "这个路径不是一个存在的目录。",
        "en": "That path is not an existing directory.",
    },
    "generic.export_path": {"zh-CN": "导出到哪个文件？", "en": "Export to which file?"},
    "generic.exported": {
        "zh-CN": "已写入 {path}（{count:,} 字符）",
        "en": "Written to {path} ({count:,} characters)",
    },
    "generic.overwrite": {
        "zh-CN": "{path} 已存在，覆盖它？",
        "en": "{path} exists. Overwrite it?",
    },
    "generic.no_report": {
        "zh-CN": "这项研究还没有报告。",
        "en": "This research has no report yet.",
    },
}


class Translator:
    """Renders message ids in one interface language.

    A missing id raises rather than falling back silently: a half-translated
    interface is worse than a loud failure, and the test suite asserts every id
    exists in every language.
    """

    __slots__ = ("language",)

    def __init__(self, language: str = DEFAULT_CLI_LANGUAGE) -> None:
        self.language = language if language in dict(CLI_LANGUAGES) else DEFAULT_CLI_LANGUAGE

    def __call__(self, message_id: str, **values: Any) -> str:
        entry = _CATALOGUE.get(message_id)
        if entry is None:
            raise KeyError(f"unknown message id {message_id!r}")
        template = entry.get(self.language) or entry[DEFAULT_CLI_LANGUAGE]
        return template.format(**values) if values else template


def message_ids() -> tuple[str, ...]:
    return tuple(_CATALOGUE)


def catalogue() -> Mapping[str, Mapping[str, str]]:
    return _CATALOGUE


__all__ = [
    "CLI_LANGUAGES",
    "DEFAULT_CLI_LANGUAGE",
    "Translator",
    "catalogue",
    "message_ids",
]
