"""Run one stress fixture end to end, zero-pack, from commission to export.

This is the whole system in one command: an Architect turns the commission into
a Contract, the operator approves it, the Lead governs waves of investigation and
curation, and the reporting transaction writes, reviews, and publishes.

Zero-pack is the point.  The baseline has to produce an honest report on an
arbitrary topic before any domain pack is allowed to exist, otherwise packs
become the place architecture debt hides.

Usage::

    python tools/run_research.py --fixture sparse-evidence --approve
"""

from __future__ import annotations

import argparse
import asyncio
import os
import re
import sys
from pathlib import Path

import aiosqlite

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "evals"))

import fixtures as fixture_set  # noqa: E402

from deep_research_agent.agents import architect as architect_agent  # noqa: E402
from deep_research_agent.agents import invoke_agent  # noqa: E402
from deep_research_agent.agents import lead as lead_agent  # noqa: E402
from deep_research_agent.approval import (  # noqa: E402
    ApprovalBody,
    approval_card,
    approved_contract,
    record_decision,
)
from deep_research_agent.artifact_store import SqliteArtifactStore  # noqa: E402
from deep_research_agent.artifacts import Provenance  # noqa: E402
from deep_research_agent.config import Role, load_config  # noqa: E402
from deep_research_agent.content_store import SqliteContentStore  # noqa: E402
from deep_research_agent.context import (  # noqa: E402
    latest_body,
    lead_context,
    load_evidence,
)
from deep_research_agent.contract import CommissionBody, ResearchContract  # noqa: E402
from deep_research_agent.model import OpenAICompatibleClient  # noqa: E402
from deep_research_agent.operations import (  # noqa: E402
    ExecutionIdentity,
    SqliteOperationLedger,
)
from deep_research_agent.providers import build_search_providers  # noqa: E402
from deep_research_agent.providers.reader import PublicHttpReader  # noqa: E402
from deep_research_agent.reporting import RoleRuntime, run_reporting  # noqa: E402
from deep_research_agent.tools import TransparentSearchBroker  # noqa: E402
from deep_research_agent.wave import run_wave  # noqa: E402

ALL_ROLES: tuple[Role, ...] = (
    "architect",
    "lead",
    "investigator",
    "curator",
    "analyst",
    "author",
    "reviewer",
)


def load_env(path: Path) -> dict[str, str]:
    values = dict(os.environ)
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^\s*([A-Z_][A-Z0-9_]*)\s*=\s*(.*)$", line)
        if match:
            values[match.group(1)] = match.group(2).strip()
    return values


def build_runtimes(environ: dict[str, str]) -> dict[str, RoleRuntime]:
    config = load_config(environ)
    runtimes: dict[str, RoleRuntime] = {}
    print("角色 → 模型：")
    for role in ALL_ROLES:
        chosen = config.model_for(role)
        runtimes[role] = RoleRuntime(
            model=OpenAICompatibleClient(
                chosen.api_key(environ),
                model=chosen.model_id,
                api_base=chosen.api_base,
            ),
            execution=ExecutionIdentity(
                provider=chosen.provider.name,
                endpoint=chosen.api_base,
                model_id=chosen.model_id,
            ),
        )
        print(f"  {role:<13} {chosen.tier:<10} {chosen.model_id}")
    return runtimes


async def run(args: argparse.Namespace) -> int:
    fixture = fixture_set.get(args.fixture)
    environ = load_env(ROOT / ".env")
    config = load_config(environ)

    print(f"\n=== {fixture.fixture_id} ({fixture.domain} × {fixture.genre}) ===")
    print(f"压测：{fixture.stresses}\n")
    runtimes = build_runtimes(environ)

    database = Path(args.database)
    database.parent.mkdir(parents=True, exist_ok=True)
    connection = await aiosqlite.connect(database)
    try:
        content = SqliteContentStore(connection)
        await content.setup()
        store = SqliteArtifactStore(connection, content, task_id=fixture.fixture_id)
        await store.setup()
        ledger = SqliteOperationLedger(connection, content)
        await ledger.setup()

        commission = CommissionBody(
            request=fixture.request,
            source_access=fixture.source_access,  # type: ignore[arg-type]
        )
        commission_ref = await store.put(
            kind="commission",
            body=commission.encode(),
            provenance=Provenance(producer="user"),
        )
        print(f"\n[commission] {commission_ref.artifact_id}")

        contract = await _propose_contract(
            store, ledger, runtimes, commission, commission_ref.artifact_id
        )
        print("\n" + approval_card(contract))

        if not args.approve:
            print("\n（未传 --approve，停在审批点。）")
            return 0

        view = await store.active_view()
        head = view.head("research_contract") or ""
        await record_decision(store, head, ApprovalBody(decision="approved"))
        _head, approved = await approved_contract(store)
        print(f"\n[approved] {head}")

        providers = build_search_providers(
            config.search_providers,
            config.academic_providers,
            environ=environ,
            ncbi_api_key=config.ncbi_api_key,
            contact_email=config.contact_email,
        )
        broker = TransparentSearchBroker(providers)
        reader = PublicHttpReader()
        print(f"[providers] {', '.join(p.provider_id for p in providers)}")

        await _govern(
            store,
            ledger,
            runtimes,
            contract=approved,
            broker=broker,
            reader=reader,
            max_waves=args.max_waves,
            source_access=fixture.source_access,
        )
        return 0
    finally:
        await connection.close()


async def _propose_contract(
    store: SqliteArtifactStore,
    ledger: SqliteOperationLedger,
    runtimes: dict[str, RoleRuntime],
    commission: CommissionBody,
    commission_ref: str,
) -> ResearchContract:
    """Turn the commission into a Contract candidate the user can approve."""

    from deep_research_agent.context import RoleContext

    body = architect_agent.architect_context_body(
        commission.request,
        source_access=commission.source_access,
        language=commission.language,
        constraints=commission.constraints,
        pack_menu="（本次运行不启用任何能力包。）",
    )
    action = await invoke_agent(
        architect_agent.SPEC,
        RoleContext(
            role="architect",
            purpose="把用户委托转化为可审批的研究合同",
            body=body,
            input_refs=(commission_ref,),
        ),
        model=runtimes["architect"].model,
        ledger=ledger,
        task_id=store.task_id,
        execution=runtimes["architect"].execution,
        validate=architect_agent.make_validator(None),
    )
    if action.name != "propose_contract":
        raise SystemExit(f"architect asked for input instead: {action.arguments}")

    from deep_research_agent.contract import build_contract

    supports = {
        str(item["label"]): tuple(str(x) for x in item.get("supports", ()))
        for item in action.arguments.get("question_supports", ()) or ()
    }
    contract = build_contract(
        str(action.arguments["contract_markdown"]),
        supports=supports,
        pack_refs=(),
    )
    await store.put(
        kind="research_contract",
        body=contract.encode(),
        parent_refs=(commission_ref,),
        provenance=Provenance(producer="architect"),
    )
    return contract


async def _govern(
    store: SqliteArtifactStore,
    ledger: SqliteOperationLedger,
    runtimes: dict[str, RoleRuntime],
    *,
    contract: ResearchContract,
    broker,  # noqa: ANN001
    reader,  # noqa: ANN001
    max_waves: int,
    source_access,  # noqa: ANN001
) -> None:
    """Let the Lead govern until it commissions a report or asks for a human."""

    latest_outcome = ""
    for round_index in range(1, max_waves + 2):
        evidence = await load_evidence(store)
        synthesis = await latest_body(store, "synthesis")
        memory = await latest_body(store, "research_memory")

        action = await invoke_agent(
            lead_agent.SPEC,
            lead_context(
                contract,
                evidence,
                synthesis=synthesis[1] if synthesis else "",
                memory=(
                    lead_agent.MemoryBody.decode(memory[1]).render() if memory else ""
                ),
                latest_outcome=latest_outcome,
            ),
            model=runtimes["lead"].model,
            ledger=ledger,
            task_id=store.task_id,
            execution=runtimes["lead"].execution,
            validate=lead_agent.make_validator(contract),
        )
        await _commit_memory(store, action.arguments)
        print(f"\n[lead #{round_index}] {action.name}")

        if action.name == "commission_report":
            outcome = await run_reporting(
                store,
                ledger,
                runtimes,
                report_brief=str(action.arguments["report_brief"]),
                stop_rationale=str(action.arguments["stop_rationale"]),
            )
            print(f"[published] {outcome.publication_ref}")
            return

        if action.name != "commission_wave":
            print(f"暂停：{action.arguments}")
            return

        if round_index > max_waves:
            print(f"已达 --max-waves={max_waves}，暂停等待人工判断。")
            return

        drafts = lead_agent.parse_assignments(
            contract, action.arguments["assignments"]
        )
        print(f"  intent: {action.arguments['wave_intent']}")
        for draft in drafts:
            print(f"  - [{','.join(draft.question_labels)}] {draft.focus}")

        wave = await run_wave(
            store,
            ledger,
            runtimes,
            contract=contract,
            wave_intent=str(action.arguments["wave_intent"]),
            assignments=drafts,
            broker=broker,
            reader=reader,
            source_access=source_access,
        )
        latest_outcome = wave.render()
        print(
            f"  → 新增素材 {len(wave.new_material_refs)}，"
            f"Analyst {'运行' if wave.analyst_ran else '未运行'}"
        )


async def _commit_memory(store: SqliteArtifactStore, arguments) -> None:  # noqa: ANN001
    snapshot = arguments.get("memory_snapshot") or {}
    body = lead_agent.MemoryBody.from_snapshot(snapshot)
    await store.put(
        kind="research_memory",
        body=body.encode(),
        provenance=Provenance(producer="lead"),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", default="")
    parser.add_argument("--database", default=".deep-research-agent/stress.sqlite3")
    parser.add_argument("--approve", action="store_true")
    parser.add_argument("--max-waves", type=int, default=2)
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args(argv)

    if args.list or not args.fixture:
        for fixture in fixture_set.FIXTURES:
            print(f"{fixture.fixture_id:<26} {fixture.domain} × {fixture.genre}")
        return 0
    return asyncio.run(run(args))


if __name__ == "__main__":
    sys.exit(main())
