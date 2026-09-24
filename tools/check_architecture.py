"""Reject unregistered modules and imports against the implemented dependency graph."""

from __future__ import annotations

import ast
from pathlib import Path

LAYERS = (
    ("domain", frozenset({"__init__", "domain"})),
    (
        "infrastructure",
        frozenset(
            {
                "storage",
                "local_security",
                "platform_paths",
                "components",
                "diagnostics",
                "prompts",
                "context",
                "workspace",
                "adapters",
                "model_catalog",
                "model_discovery",
                "models",
                "native_models",
                "scheduling",
                "agent_runtime",
                "usage",
                "web_providers",
                "public_sources",
                "document_parser",
                "materials",
                "review",
                "research",
                "writing",
                "citations",
                "markdown_rules",
                "calculation",
                "analysis",
                "sandbox_windows",
                "native_analysis",
                "mcp_client",
            }
        ),
    ),
    ("execution", frozenset({"harness", "analysis_runtime"})),
    (
        "application",
        frozenset(
            {
                "application",
                "host",
                "cli",
                "terminal",
                "locale",
                "cli_settings",
                "mcp_server",
                "mcp_tools",
                "webui",
                "desktop",
                "presentation",
                "report_export",
            }
        ),
    ),
)
ALLOWED = {
    "platform_paths": set(),
    "components": {"local_security", "platform_paths", "native_analysis", "analysis"},
    "desktop": {"host", "cli_settings", "components", "local_security", "platform_paths", "webui"},
    "report_export": {"markdown_rules"},
    "presentation": {"domain", "citations", "research", "writing", "usage"},
    "locale": set(),
    "webui": {
        "components",
        "platform_paths",
        "analysis",
        "report_export",
        "locale",
        "host",
        "cli_settings",
        "model_catalog",
        "model_discovery",
        "models",
        "web_providers",
    },
    "mcp_client": {"domain", "local_security"},
    "mcp_tools": {"domain", "harness", "workspace", "mcp_client"},
    "mcp_server": {"host", "locale"},
    "cli": {
        "report_export",
        "locale",
        "host",
        "terminal",
        "cli_settings",
        "model_catalog",
        "web_providers",
        "webui",
    },
    "terminal": {"locale"},
    "cli_settings": {"adapters", "local_security", "model_catalog", "web_providers"},
    "host": {
        "native_analysis",
        "agent_runtime",
        "components",
        "platform_paths",
        "local_security",
        "presentation",
        "locale",
        "mcp_client",
        "usage",
        "analysis_runtime",
        "analysis",
        "web_providers",
        "application",
        "adapters",
        "storage",
        "scheduling",
        "workspace",
        "models",
        "model_catalog",
    },
    "model_catalog": set(),
    "model_discovery": {"model_catalog"},
    "models": {"adapters", "model_catalog", "native_models"},
    "native_models": {"adapters", "domain"},
    "materials": {"domain", "document_parser", "platform_paths"},
    "document_parser": set(),
    "web_providers": {"adapters", "domain"},
    "public_sources": {"adapters"},
    "scheduling": set(),
    "agent_runtime": set(),
    "adapters": {"domain", "local_security"},
    "__init__": set(),
    "domain": set(),
    "prompts": set(),
    "storage": {"domain", "usage", "citations", "review", "local_security", "writing"},
    "local_security": set(),
    "diagnostics": {"domain", "review"},
    "citations": {"markdown_rules"},
    "markdown_rules": set(),
    "usage": set(),
    "context": {"domain"},
    "research": {"domain"},
    "writing": {"domain", "research", "citations", "context", "review"},
    "review": {"domain"},
    "calculation": set(),
    "workspace": {"domain", "storage", "materials", "analysis"},
    "analysis": {"platform_paths"},
    "sandbox_windows": {"local_security"},
    "native_analysis": {"analysis", "local_security", "sandbox_windows"},
    "analysis_runtime": {"native_analysis", "analysis", "domain", "storage", "workspace", "scheduling"},
    "harness": {
        "analysis_runtime",
        "research",
        "writing",
        "calculation",
        "citations",
        "domain",
        "prompts",
        "storage",
        "context",
        "workspace",
        "scheduling",
        "review",
    },
    "application": {
        "agent_runtime",
        "public_sources",
        "scheduling",
        "mcp_tools",
        "web_providers",
        "domain",
        "harness",
        "storage",
        "adapters",
        "workspace",
        "models",
        "usage",
    },
}
FORBIDDEN = {"claude_agent_sdk", "codex_sdk", "langgraph"}
IO_MODULES = {"os", "pathlib", "sqlite3", "httpx", "aiohttp", "socket", "subprocess"}


def check(package: Path) -> list[str]:
    registered = set().union(*(names for _, names in LAYERS))
    errors = []
    found = set()
    for path in package.rglob("*.py"):
        name = ".".join(path.relative_to(package).with_suffix("").parts)
        found.add(name)
        if name not in registered:
            errors.append(f"{name}: module not registered in LAYERS")
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            modules = []
            local = []
            if isinstance(node, ast.Import):
                modules = [a.name for a in node.names]
                local = [m.split(".")[1] for m in modules if m.startswith("epivra.")]
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                modules = [module]
                if node.level:
                    local = (
                        [module.split(".")[0]]
                        if module
                        else [alias.name for alias in node.names]
                    )
                elif module.startswith("epivra."):
                    local = [module.split(".")[1]]
                elif module == "epivra":
                    local = [alias.name for alias in node.names]
            for dependency in local:
                if dependency not in ALLOWED[name]:
                    errors.append(f"{name}: forbidden local dependency {dependency}")
            for module in modules:
                if module.split(".")[0] in FORBIDDEN:
                    errors.append(f"{name}: provider-owned execution dependency")
                if name in {"domain", "prompts"} and module.split(".")[0] in IO_MODULES:
                    errors.append(f"{name}: research/domain module imports I/O")
    for missing in registered - found:
        errors.append(f"{missing}: registered module missing")
    return errors


if __name__ == "__main__":
    failures = check(Path(__file__).resolve().parents[1] / "src/epivra")
    for failure in failures:
        print(failure)
    print("architecture FAILED" if failures else "architecture OK")
    raise SystemExit(bool(failures))
