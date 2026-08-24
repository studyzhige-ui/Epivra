"""Composition root: bind configuration to the transport each role will use.

Every entry point needs the same three steps -- read the operator's
environment, resolve each role to a model, and build the transport that
model's vendor actually speaks.  Doing it in one place is what stops a second
entry point from quietly disagreeing with the first about a provider.

That is not hypothetical.  Both driver scripts were constructing
``OpenAICompatibleClient`` directly, so :func:`build_chat_model` -- the only
code that reads a provider's declared protocol -- was never reached from a real
run.  An operator selecting Anthropic would have had OpenAI-shaped requests
posted to the Messages API and seen an opaque 404, with a correct native
transport sitting unused in the tree.  A duplicated bootstrap is how a
capability gets tested and never actually used.
"""

from __future__ import annotations

import os
import re
from collections.abc import Mapping, Sequence
from pathlib import Path

from .config import ROLES, Role, RuntimeConfig, load_config
from .model import STREAMING_THRESHOLD_TOKENS
from .operations import ExecutionIdentity
from .providers import build_chat_model
from .reporting import RoleRuntime

#: ``KEY=value`` lines, ignoring comments, blanks, and indentation.
_ASSIGNMENT = re.compile(r"^\s*([A-Z_][A-Z0-9_]*)\s*=\s*(.*)$")


def load_environment(path: Path) -> dict[str, str]:
    """Overlay a ``.env`` file onto the process environment.

    The file wins over the ambient environment so that pointing a run at a
    different key file does what the operator plainly meant, rather than
    silently keeping whatever was exported in the shell.
    """

    values = dict(os.environ)
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        match = _ASSIGNMENT.match(line)
        if match:
            values[match.group(1)] = match.group(2).strip()
    return values


def build_runtimes(
    environ: Mapping[str, str],
    *,
    roles: Sequence[Role] = ROLES,
    config: RuntimeConfig | None = None,
) -> dict[str, RoleRuntime]:
    """Bind each role to the model its tier resolves to.

    The execution identity records provider, endpoint, model id **and the limits
    the call runs under**, because the operation ledger keys replay on them: the
    same request against a different model is different work, and replaying one as
    the other would attribute a verdict to a model that never produced it.  The
    limits are there for the same reason plus one more -- it is what makes a
    capacity failure escapable.  Raising an output ceiling to unblock a truncated
    report has to open a *new* operation, or the fix would replay the failure it
    was meant to repair (see §8.2).

    Streaming and the output ceiling are decided together here rather than in the
    transports.  They are one decision: a ceiling above the safe threshold is only
    safe when the response streams, and the transports refuse the unsafe pairing
    rather than silently downgrading it.
    """

    resolved = config or load_config(environ)
    runtimes: dict[str, RoleRuntime] = {}
    for role in roles:
        chosen = resolved.model_for(role)
        limits = chosen.limits
        runtimes[role] = RoleRuntime(
            model=build_chat_model(
                chosen.provider,
                chosen.model_id,
                api_key=chosen.api_key(environ),
                max_output_tokens=limits.output,
                stream=limits.output > STREAMING_THRESHOLD_TOKENS,
                effort=chosen.effort,
            ),
            execution=ExecutionIdentity(
                provider=chosen.provider.name,
                endpoint=chosen.api_base,
                model_id=chosen.model_id,
                # Named "ceiling" rather than "*_tokens": the ledger bars any
                # field whose name contains "token" as credential-like, and that
                # guard is worth more than the tidier name.
                limits={
                    "context_ceiling": str(limits.context),
                    "output_ceiling": str(limits.output),
                    "effort": chosen.effort,
                },
            ),
            context_limit=limits.context,
        )
    return runtimes


def render_role_models(config: RuntimeConfig, roles: Sequence[Role] = ROLES) -> str:
    """A readable account of which model every role is about to use."""

    lines = ["角色 → 模型："]
    for role in roles:
        chosen = config.model_for(role)
        lines.append(
            f"  {role:<13} {chosen.tier:<10} "
            f"{chosen.provider.name}/{chosen.model_id}"
        )
    return "\n".join(lines)


__all__ = [
    "build_runtimes",
    "load_environment",
    "render_role_models",
]
