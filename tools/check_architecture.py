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
                "prompts",
                "context",
                "workspace",
                "adapters",
                "model_catalog",
                "models",
                "native_models",
                "scheduling",
                "usage",
                "web_providers",
                "document_parser",
                "materials",
                "review",
                "calculation",
                "analysis",
            }
        ),
    ),
    ("execution", frozenset({"harness", "analysis_runtime"})),
    (
        "application",
        frozenset({"application", "host", "cli", "terminal", "cli_settings"}),
    ),
)
ALLOWED = {
    "cli": {"host", "terminal", "cli_settings", "model_catalog", "web_providers"},
    "terminal": set(),
    "cli_settings": {"adapters", "model_catalog", "web_providers"},
    "host": {
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
    "models": {"adapters", "model_catalog", "native_models"},
    "native_models": {"adapters", "domain"},
    "materials": {"domain", "document_parser"},
    "document_parser": set(),
    "web_providers": {"adapters", "domain"},
    "scheduling": set(),
    "adapters": {"domain"},
    "__init__": set(),
    "domain": set(),
    "prompts": set(),
    "storage": {"domain", "usage"},
    "usage": set(),
    "context": {"domain"},
    "review": {"domain"},
    "calculation": set(),
    "workspace": {"domain", "storage", "materials", "analysis"},
    "analysis": set(),
    "analysis_runtime": {"analysis", "domain", "storage", "workspace", "scheduling"},
    "harness": {
        "analysis_runtime",
        "calculation",
        "domain",
        "prompts",
        "storage",
        "context",
        "workspace",
        "scheduling",
        "review",
    },
    "application": {
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
                local = [
                    m.split(".")[1]
                    for m in modules
                    if m.startswith("deep_research_agent.")
                ]
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                modules = [module]
                if node.level:
                    local = (
                        [module.split(".")[0]]
                        if module
                        else [alias.name for alias in node.names]
                    )
                elif module.startswith("deep_research_agent."):
                    local = [module.split(".")[1]]
                elif module == "deep_research_agent":
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
    failures = check(Path(__file__).resolve().parents[1] / "src/deep_research_agent")
    for failure in failures:
        print(failure)
    print("architecture FAILED" if failures else "architecture OK")
    raise SystemExit(bool(failures))
