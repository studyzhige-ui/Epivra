"""What one task runs with, frozen when the task is created.

``config.load_config`` answers "how is this installation configured **now**".
That is the wrong question for a study that spans days: a user who changes their
default model on Tuesday must not find Monday's half-finished research quietly
continuing on a different model.  Evidence gathered by one model and synthesised
by another, with nothing recording the switch, is exactly the kind of second
account of truth this architecture exists to prevent -- and the resulting report
would cite work no single configuration ever produced.

So a task freezes its execution configuration once, at creation, and every later
``advance`` rebuilds *that* configuration rather than reading the current
defaults.  Changing global settings affects new tasks only.

What is frozen is the **resolved** binding -- provider name, model id, tier per
role -- not the environment variables it came from.  Freezing the variables would
leave the task exposed to a later change in the provider registry's tier
defaults, which is the same silent substitution by a slower route.

What is deliberately *not* frozen:

* **Credentials.**  They are secrets, they rotate, and they say nothing about
  what ran.  A rotated key must not strand a task.
* **Anything the Commission already carries** -- the request, report language,
  source access and constraints are immutable artifacts already.

Tasks created before this table existed have no row.  They fall back to the
current configuration, and the service says so rather than pretending the
fallback is a restored snapshot.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import get_args

import aiosqlite

from .config import RoleModel, RuntimeConfig
from .providers.llm import ModelTier, resolve_llm_provider

_TIERS: frozenset[str] = frozenset(get_args(ModelTier))


@dataclass(frozen=True, slots=True)
class RoleBinding:
    """One role's resolved model, in terms that survive a restart."""

    provider: str
    model_id: str
    tier: str


@dataclass(frozen=True, slots=True)
class ExecutionSnapshot:
    """The frozen execution configuration of one task."""

    role_models: Mapping[str, RoleBinding]
    search_providers: tuple[str, ...] = ()
    academic_providers: tuple[str, ...] = ()
    corpus_root: str = ""
    frozen_at: str = ""

    def to_config(self, live: RuntimeConfig) -> RuntimeConfig:
        """Rebuild the runtime configuration this task was created with.

        ``live`` supplies only what a snapshot must not hold: the credential for
        the NCBI index, the operator contact address, and any role added to the
        system after this task was frozen.  Everything that decides *what runs*
        comes from the snapshot.
        """

        role_models = dict(live.role_models)
        for role, binding in self.role_models.items():
            if role not in role_models:
                # A role this installation no longer has.  Ignoring it is right:
                # there is nothing to bind, and refusing to resume a task over a
                # role that will never be invoked would be a pointless block.
                continue
            existing = role_models[role]
            tier = binding.tier if binding.tier in _TIERS else existing.tier
            role_models[role] = RoleModel(
                role=existing.role,
                provider=resolve_llm_provider(binding.provider),
                model_id=binding.model_id,
                tier=tier,  # type: ignore[arg-type]
            )
        return RuntimeConfig(
            role_models=role_models,
            search_providers=self.search_providers,
            academic_providers=self.academic_providers,
            contact_email=live.contact_email,
            ncbi_api_key=live.ncbi_api_key,
        )

    def render(self) -> str:
        """The two bindings a user chose, in the order the interface asks them."""

        parts = []
        for role in ("lead", "investigator"):
            binding = self.role_models.get(role)
            if binding is not None:
                parts.append(f"{binding.provider}/{binding.model_id}")
        return " / ".join(parts)

    def encode(self) -> str:
        return json.dumps(
            {
                "roles": {
                    role: {
                        "provider": binding.provider,
                        "model_id": binding.model_id,
                        "tier": binding.tier,
                    }
                    for role, binding in sorted(self.role_models.items())
                },
                "search_providers": list(self.search_providers),
                "academic_providers": list(self.academic_providers),
                "corpus_root": self.corpus_root,
                "frozen_at": self.frozen_at,
            },
            ensure_ascii=False,
            sort_keys=True,
        )

    @classmethod
    def decode(cls, payload: str) -> ExecutionSnapshot:
        raw = json.loads(payload)
        roles = raw.get("roles") or {}
        return cls(
            role_models={
                str(role): RoleBinding(
                    provider=str(entry.get("provider", "")),
                    model_id=str(entry.get("model_id", "")),
                    tier=str(entry.get("tier", "")),
                )
                for role, entry in roles.items()
                if isinstance(entry, Mapping)
            },
            search_providers=tuple(str(item) for item in raw.get("search_providers", ())),
            academic_providers=tuple(
                str(item) for item in raw.get("academic_providers", ())
            ),
            corpus_root=str(raw.get("corpus_root", "")),
            frozen_at=str(raw.get("frozen_at", "")),
        )


def capture(
    config: RuntimeConfig, *, corpus_root: Path | None = None, frozen_at: str = ""
) -> ExecutionSnapshot:
    """Freeze the configuration a task is about to start with."""

    return ExecutionSnapshot(
        role_models={
            role: RoleBinding(
                provider=chosen.provider.name,
                model_id=chosen.model_id,
                tier=chosen.tier,
            )
            for role, chosen in config.role_models.items()
        },
        search_providers=tuple(config.search_providers),
        academic_providers=tuple(config.academic_providers),
        corpus_root="" if corpus_root is None else str(corpus_root),
        frozen_at=frozen_at,
    )


async def setup(connection: aiosqlite.Connection) -> None:
    """Create the table.  Existing databases simply have no rows yet."""

    await connection.execute(
        """
        CREATE TABLE IF NOT EXISTS execution_snapshots (
            task_id TEXT PRIMARY KEY,
            frozen_at TEXT NOT NULL DEFAULT '',
            payload TEXT NOT NULL
        )
        """
    )
    await connection.commit()


async def freeze(
    connection: aiosqlite.Connection, task_id: str, snapshot: ExecutionSnapshot
) -> ExecutionSnapshot:
    """Write the snapshot once and return whatever the task is bound to.

    Insert-only.  Opening the same commission twice must not rewrite the first
    run's configuration, so the stored row always wins over the caller's.
    """

    await connection.execute(
        """
        INSERT INTO execution_snapshots(task_id, frozen_at, payload)
        VALUES (?, ?, ?)
        ON CONFLICT(task_id) DO NOTHING
        """,
        (task_id, snapshot.frozen_at, snapshot.encode()),
    )
    await connection.commit()
    stored = await load(connection, task_id)
    return stored if stored is not None else snapshot


async def load(
    connection: aiosqlite.Connection, task_id: str
) -> ExecutionSnapshot | None:
    """The task's frozen configuration, or None for a task created before this."""

    rows = await connection.execute_fetchall(
        "SELECT payload FROM execution_snapshots WHERE task_id = ?", (task_id,)
    )
    if not rows:
        return None
    try:
        return ExecutionSnapshot.decode(str(rows[0][0]))
    except (json.JSONDecodeError, TypeError, ValueError):
        # A corrupt row must not make a study unresumable; the caller treats a
        # missing snapshot as "not frozen" and says so.
        return None


__all__ = [
    "ExecutionSnapshot",
    "RoleBinding",
    "capture",
    "freeze",
    "load",
    "setup",
]
