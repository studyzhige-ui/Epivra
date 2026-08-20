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
import sys
from pathlib import Path

import aiosqlite

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "evals"))

import fixtures as fixture_set  # noqa: E402

from deep_research_agent.agents import AgentProtocolError, invoke_agent  # noqa: E402
from deep_research_agent.agents import architect as architect_agent  # noqa: E402
from deep_research_agent.agents import lead as lead_agent  # noqa: E402
from deep_research_agent.application import (  # noqa: E402
    build_runtimes,
    load_environment,
    render_role_models,
)
from deep_research_agent.approval import (  # noqa: E402
    ApprovalBody,
    approval_card,
    approved_contract,
    record_decision,
)
from deep_research_agent.artifact_store import SqliteArtifactStore  # noqa: E402
from deep_research_agent.artifacts import Provenance  # noqa: E402
from deep_research_agent.config import load_config  # noqa: E402
from deep_research_agent.content_store import SqliteContentStore  # noqa: E402
from deep_research_agent.context import (  # noqa: E402
    latest_body,
    lead_context,
    load_evidence,
)
from deep_research_agent.contract import CommissionBody, ResearchContract  # noqa: E402
from deep_research_agent.operations import SqliteOperationLedger  # noqa: E402
from deep_research_agent.providers import build_search_providers  # noqa: E402
from deep_research_agent.providers.reader import PublicHttpReader  # noqa: E402
from deep_research_agent.reporting import RoleRuntime, run_reporting  # noqa: E402
from deep_research_agent.tools import TransparentSearchBroker  # noqa: E402
from deep_research_agent.wave import run_wave  # noqa: E402


async def run(args: argparse.Namespace) -> int:
    fixture = fixture_set.get(args.fixture)
    environ = load_environment(ROOT / ".env")
    config = load_config(environ)

    print(f"\n=== {fixture.fixture_id} ({fixture.domain} × {fixture.genre}) ===")
    print(f"压测：{fixture.stresses}\n")
    print(render_role_models(config))
    runtimes = build_runtimes(environ, config=config)

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
        if contract is None:
            print(f"\n--- 判定依据（先于本次运行写定）---\n{fixture.render()}")
            print("\n本次终局：clarification_requested")
            return 0
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

        kind = await _govern(
            store,
            ledger,
            runtimes,
            contract=approved,
            broker=broker,
            reader=reader,
            max_waves=args.max_waves,
            source_access=fixture.source_access,
            output=(
                Path(args.output)
                if args.output
                else ROOT / ".deep-research-agent" / f"{fixture.fixture_id}.md"
            ),
        )
        # All three terminal states are legitimate ends to a stress run, so the
        # exit code means "reached a terminal state", not "published".  Which
        # state was *correct* is decided against the pre-registered assertions
        # below -- printed after the run so the judgement is not reconstructed
        # from the report that was just produced.
        print(f"\n--- 判定依据（先于本次运行写定）---\n{fixture.render()}")
        print(f"\n本次终局：{kind}")
        return 0
    finally:
        await connection.close()


async def _propose_contract(
    store: SqliteArtifactStore,
    ledger: SqliteOperationLedger,
    runtimes: dict[str, RoleRuntime],
    commission: CommissionBody,
    commission_ref: str,
) -> ResearchContract | None:
    """Turn the commission into a Contract candidate, or return None.

    ``None`` means the Architect asked a scope question instead, which is a
    legitimate terminal state -- for a commission as vague as "研究一下 AI 芯片
    市场" it is the *correct* one.  Treating it as a crash would have scored the
    honest answer as a failure on the one fixture built to reward it.
    """

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
    if action.name == "ask_scope_question":
        print("\n[architect] 提出澄清问题，未提交合同：")
        print(f"  问题：{action.arguments['question']}")
        print(f"  为何会改变方案：{action.arguments['why_it_changes_the_plan']}")
        return None

    contract = architect_agent.contract_from_action(
        action.arguments, language=commission.language
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
    output: Path,
) -> str:
    """Let the Lead govern until it commissions a report or asks for a human.

    Returns which terminal state the run reached -- ``published``, ``halted``, or
    ``paused``.  All three are legitimate; deciding whether the *right* one was
    reached is the fixture's job, not the runner's.
    """

    latest_outcome = ""
    for round_index in range(1, max_waves + 2):
        evidence = await load_evidence(store)
        synthesis = await latest_body(store, "synthesis")
        memory = await latest_body(store, "research_memory")
        previous_memory = (
            lead_agent.MemoryBody.decode(memory[1]) if memory else None
        )

        try:
            action = await invoke_agent(
                lead_agent.SPEC,
                lead_context(
                    contract,
                    evidence,
                    synthesis=synthesis[1] if synthesis else "",
                    memory=previous_memory.render() if previous_memory else "",
                    latest_outcome=latest_outcome,
                ),
                model=runtimes["lead"].model,
                ledger=ledger,
                task_id=store.task_id,
                execution=runtimes["lead"].execution,
                validate=lead_agent.make_validator(contract),
            )
        except AgentProtocolError as error:
            # A role that cannot produce a valid action is a recoverable pause,
            # which is what ARCHITECTURE §8.2 already requires -- letting it
            # escape here threw away a task that was substantively finished.
            # Every artifact is already committed, so the honest terminal state
            # is "paused", and a later run resumes from the same store.
            print(f"\n[lead #{round_index}] 协议暂停：{error}")
            print(
                f"已保全 {len(evidence.materials)} 份素材"
                f"{'与一份综合' if synthesis else ''}；重跑同一数据库即可继续。"
            )
            return "paused"
        await _commit_memory(store, action.arguments, previous_memory)
        print(f"\n[lead #{round_index}] {action.name}")

        if action.name == "commission_report":
            return await _report(
                store, ledger, runtimes, arguments=action.arguments, output=output
            )

        if action.name != "commission_wave":
            print(f"暂停：{action.arguments}")
            return "paused"

        if round_index > max_waves:
            print(f"已达 --max-waves={max_waves}，暂停等待人工判断。")
            return "paused"

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
    return "paused"


async def _report(
    store: SqliteArtifactStore,
    ledger: SqliteOperationLedger,
    runtimes: dict[str, RoleRuntime],
    *,
    arguments,  # noqa: ANN001
    output: Path,
) -> str:
    """Run the reporting transaction and record what it actually produced.

    Review rounds are printed because they are the observable that matters for
    calibration: a first-pass approval and an approval after one bounded
    revision are very different signals about the Author.
    """

    outcome = await run_reporting(
        store,
        ledger,
        runtimes,
        report_brief=str(arguments["report_brief"]),
        stop_rationale=str(arguments["stop_rationale"]),
    )

    for index, review in enumerate(outcome.reviews, start=1):
        verdict = "批准" if review.approved else "阻断"
        print(f"  [review {index}] {verdict}（{len(review.findings)} 项阻断）")
        for finding in review.findings:
            print(f"    - {finding.splitlines()[0]}")

    # A transaction that stopped is a legitimate result, but it is not a
    # publication; reporting it as one would hide the exact failure this matrix
    # exists to detect.
    if not outcome.published:
        print(f"\nOUTCOME: halted — {outcome.halted_reason}")
        return "halted"

    assert outcome.rendered is not None
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(outcome.rendered.markdown, encoding="utf-8")
    print(
        f"\nOUTCOME: published {outcome.publication_ref}\n"
        f"  正文 {len(outcome.rendered.markdown):,} 字符，"
        f"参考 {len(outcome.rendered.references)} 条，"
        f"引用素材 {len(outcome.rendered.used_material_refs)} 份\n"
        f"  写入 {output}"
    )
    return "published"


async def _commit_memory(
    store: SqliteArtifactStore,
    arguments,  # noqa: ANN001
    previous: lead_agent.MemoryBody | None,
) -> None:
    body = lead_agent.memory_after(arguments, previous)
    await store.put(
        kind="research_memory",
        body=body.encode(),
        provenance=Provenance(producer="lead"),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", default="")
    parser.add_argument("--database", default=".deep-research-agent/stress.sqlite3")
    parser.add_argument(
        "--output",
        default="",
        help="发布报告的写入路径（默认 .deep-research-agent/<fixture>.md）",
    )
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
