"""Presentation language only; never rewrite research content or protocol values."""

import argparse
import json
import os
import re
from contextvars import ContextVar
from pathlib import Path

LANGUAGES = ("zh-CN", "en")
_language = ContextVar("epivra_language", default="zh-CN")
MESSAGES = json.loads(
    (Path(__file__).parent / "web/messages.json").read_text(encoding="utf-8")
)


def current_language():
    return _language.get()


def set_language(language=None):
    language = language or os.environ.get("EPIVRA_LANG", "zh-CN")
    if language not in LANGUAGES:
        raise ValueError("Language must be zh-CN or en")
    _language.set(language)
    return language


def configure(argv=None):
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "--lang", choices=LANGUAGES, default=os.environ.get("EPIVRA_LANG", "zh-CN")
    )
    return set_language(parser.parse_known_args(argv)[0].lang)


def tr(message, *values, language=None):
    template = (
        MESSAGES.get(message, message)
        if (language or _language.get()) == "en"
        else message
    )
    return (
        re.sub(r"\{(\d+)\}", lambda match: str(values[int(match[1])]), template)
        if values
        else template
    )
