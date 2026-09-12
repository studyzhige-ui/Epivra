"""Installation defaults and credential editing, never research state."""

import json
import os
import tempfile
from pathlib import Path

from .adapters import credentials
from .model_catalog import OFFICIAL_PROVIDERS
from .web_providers import CONNECTIONS


def load(root):
    path = root / ".deep-research-agent/cli-settings.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=".settings-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as file:
            file.write(text)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def save(root, values):
    write(
        root / ".deep-research-agent/cli-settings.json",
        json.dumps(values, ensure_ascii=False, indent=2) + "\n",
    )


def configured(root):
    return {key for key, value in credentials(root / ".env").items() if value.strip()}


def save_key(root, name, value):
    allowed = {spec.credential_env for spec in OFFICIAL_PROVIDERS.values()} | {
        v[1] for v in CONNECTIONS.values()
    }
    if name not in allowed or not value or any(c in value for c in "\r\n\x00\"'"):
        raise ValueError("invalid credential")
    path = root / ".env"
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    lines = [line for line in lines if line.split("=", 1)[0].strip() != name]
    write(path, "\n".join([*lines, f"{name}={value}"]) + "\n")
    return name in os.environ
