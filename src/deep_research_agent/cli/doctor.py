"""``deep-research doctor``: the one subcommand that is not the product.

The workspace is for *using* Deep Research; this is for finding out why it will
not work.  That is a different job with a different shape -- one shot, no
navigation, output that is meant to be read, pasted into an issue, or piped -- so
it stays a command while the research workflow does not.

It answers two questions:

* **Can research start at all?**  A model vendor's key must be present, and that
  is the only hard requirement -- search degrades to keyless providers rather
  than failing.
* **Do the configured credentials actually work?**  Only with ``--live``, because
  proving a search key costs one query of the user's quota.  A key that is merely
  present is not a key that works, and the alternative is discovering that an
  hour into a study the user has already paid for.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from ..application import load_environment
from ..providers import search_credentials
from ..providers.llm import LLM_PROVIDERS
from ..providers.validation import (
    validate_llm_credentials,
    validate_search_credentials,
)
from . import theme
from .paths import config_file


@dataclass(frozen=True, slots=True)
class Readiness:
    """What is configured, what is not, and whether that blocks research.

    ``can_start`` is a field rather than something a caller re-derives by
    inspecting the message text.  The previous version sniffed for a substring in
    a human-readable line, which tied the exit code to the wording.
    """

    ready: tuple[str, ...]
    missing: tuple[str, ...]
    can_start: bool


def readiness(environ: Mapping[str, str]) -> Readiness:
    """Assess the installation in terms a user can act on."""

    ready: list[str] = []
    missing: list[str] = []

    vendors = [spec.name for spec in LLM_PROVIDERS if spec.api_key(environ)]
    if vendors:
        ready.append(f"模型厂商：{'、'.join(vendors)}")
    else:
        names = "、".join(spec.key_env_var for spec in LLM_PROVIDERS)
        missing.append(
            "没有任何模型厂商的密钥。研究无法开始。\n"
            f"      运行 deep-research 会引导你配置，或在 .env 写入其中任意一个："
            f"{names}"
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
    return Readiness(tuple(ready), tuple(missing), can_start=bool(vendors))


async def revalidate(environ: Mapping[str, str], console) -> int:  # noqa: ANN001
    """Prove every configured credential against its vendor.  Returns failures.

    Model vendors are checked with a model-listing call, which authenticates
    without running inference.  A search vendor exposes no such endpoint, so it
    costs one query of its quota -- which is why this is a flag and not the
    default.
    """

    console.print()
    theme.dim(console, "正在验证已配置的厂商（搜索厂商各消耗 1 次查询额度）…")
    failures = 0

    for spec in sorted(LLM_PROVIDERS, key=lambda item: item.name):
        key = spec.api_key(environ)
        if not key:
            continue
        result = await validate_llm_credentials(spec, key)
        if result.ok:
            theme.status_line(
                console,
                theme.GLYPH["done"],
                f"{spec.name}：可用，{len(result.models)} 个模型可选",
            )
        else:
            failures += 1
            theme.status_line(
                console, theme.GLYPH["blocked"], f"{spec.name}：{result.reason}"
            )

    for name, env_var in sorted(search_credentials().items()):
        key = environ.get(env_var, "").strip()
        if not key:
            continue
        result = await validate_search_credentials(name, key)
        if result.ok:
            theme.status_line(console, theme.GLYPH["done"], f"{name}：可用")
        else:
            failures += 1
            theme.status_line(
                console, theme.GLYPH["blocked"], f"{name}：{result.reason}"
            )
    return failures


async def run(args: argparse.Namespace) -> int:
    """Report the environment.  Exit 1 when something blocks research."""

    console = theme.console()
    environ = load_environment(config_file())
    report = readiness(environ)

    theme.header(console, name="Deep Research · doctor")
    for line in report.ready:
        theme.status_line(console, theme.GLYPH["done"], line)
    for line in report.missing:
        theme.status_line(console, theme.GLYPH["warn"], line)

    database = Path(args.database)
    theme.status_line(
        console,
        theme.GLYPH["done"] if database.is_file() else theme.GLYPH["info"],
        f"任务库：{database}"
        if database.is_file()
        else f"任务库还未创建，第一次研究时会建在 {database}",
    )

    env_file = config_file()
    console.print()
    if env_file.is_file():
        theme.status_line(console, theme.GLYPH["done"], f"读到配置文件 {env_file}")
    else:
        theme.status_line(
            console,
            theme.GLYPH["warn"],
            f"没有 {env_file}；密钥只能来自系统环境变量",
        )

    if not report.can_start:
        console.print()
        theme.dim(console, "结论：还不能开始研究。运行 deep-research 配置一个模型厂商。")
        return 1

    if getattr(args, "live", False):
        failures = await revalidate(environ, console)
        console.print()
        if failures:
            theme.dim(
                console, f"结论：{failures} 个厂商验证不通过，上面每一条都写了原因。"
            )
            return 1
        theme.dim(console, "结论：每个已配置的厂商都验证通过。")
        return 0

    console.print()
    theme.dim(console, "结论：可以开始。运行 deep-research 进入工作区。")
    theme.dim(console, "想真的调一次厂商接口确认密钥有效：deep-research doctor --live")
    return 0


__all__ = ["Readiness", "readiness", "revalidate", "run"]
