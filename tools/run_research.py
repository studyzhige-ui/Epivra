"""Run one stress fixture end to end, zero-pack, from commission to export.

A **harness over the product**, not a second implementation of it.  It collects a
fixture, hands it to :class:`~deep_research_agent.service.ResearchService`, and
renders what came back; every governance decision belongs to the service.

That distinction was the whole problem with the previous version.  This file used
to carry its own `_govern`, `_report`, `_commit_memory` and Architect call --
roughly two hundred lines shadowing `service.py`, whose opening line reads "An
interface must not reimplement governance."  The two had already drifted:

* a non-publishing outcome was reported as ``halted`` here and derived as
  ``paused`` there, and the Phase 1e terminal states were recorded by *this* file;
* the stall rule was `wave.stalled()` here and an inline copy there, each with its
  own tolerance constant;
* the runaway ceiling was ``--max-waves`` here and ``RUNAWAY_WAVE_GUARD`` there,
  the same number written twice;
* execution configuration was never frozen here, so a fixture database could not
  say which models produced it.

Everything a calibration run needs -- the pre-registered assertions, the terminal
state, the published file -- is presentation, and that is all this file does now.

``--max-waves`` is gone with the duplicate constant it configured.  The ceiling is
runaway protection rather than a research budget (§10.6), so one value belongs to
the runtime; no observed run has approached it.

Usage::

    python tools/run_research.py --fixture sparse-evidence --approve
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path

import aiosqlite

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "evals"))

import fixtures as fixture_set  # noqa: E402

from deep_research_agent.application import (  # noqa: E402
    load_environment,
    render_role_models,
)
from deep_research_agent.config import load_config  # noqa: E402
from deep_research_agent.service import (  # noqa: E402
    EXPECTED_FAILURES,
    Event,
    ResearchService,
)

#: Event kinds worth a line on a calibration run's console.  Anything else is
#: progress detail the log does not need.
_QUIET: frozenset[str] = frozenset({"contract_proposed", "plan_revised"})


def report(event: Event) -> None:
    """Render one service event.  The service decides what happens; this shows it."""

    if event.kind in _QUIET:
        return
    print(f"[{event.kind}] {event.message}")


async def run(args: argparse.Namespace) -> int:
    fixture = fixture_set.get(args.fixture)
    environ = load_environment(ROOT / ".env")
    config = load_config(environ)

    print(f"\n=== {fixture.fixture_id} ({fixture.domain} × {fixture.genre}) ===")
    print(f"压测：{fixture.stresses}\n")
    print(render_role_models(config))

    database = Path(args.database)
    database.parent.mkdir(parents=True, exist_ok=True)
    connection = await aiosqlite.connect(database)
    try:
        service = ResearchService(
            connection=connection,
            environ=environ,
            config=config,
            corpus_root=Path(args.corpus) if args.corpus else None,
        )
        await service.setup()

        task = await service.open_task(
            fixture.request,
            language="zh",
            source_access=fixture.source_access,  # type: ignore[arg-type]
            created_at=datetime.now(UTC).isoformat(timespec="seconds"),
            listen=report,
        )
        print(f"\n[task] {task.task_id}")
        print(f"[配置] {await service.execution_summary(task.task_id)}")

        if task.state == "clarification_requested":
            # A commission too vague to plan earns one question.  For a fixture
            # built to be vague that is the *correct* terminal state, so it is
            # reported as one rather than treated as a crash.
            print(f"\n[architect] 提出澄清问题，未提交方案：\n  {task.clarification_question}")
            print(f"  为何会改变方案：{task.clarification_why}")
            return _verdict(fixture, task.state)

        print("\n" + await service.approval_card(task.task_id))

        if not args.approve:
            print("\n（未传 --approve，停在审批点。）")
            return _verdict(fixture, task.state)

        await service.approve(task.task_id, task.plan_id)
        print(f"\n[approved] {task.plan_id}")
        print(f"[providers] {', '.join(config.search_providers)}")

        try:
            state = await service.advance(task.task_id, listen=report)
        except EXPECTED_FAILURES as error:
            # Reported rather than raised: a provider outage is a fact about the
            # run, and the pre-registered assertions still deserve printing.
            print(f"\n[failed] {type(error).__name__}: {error}")
            return _verdict(fixture, (await service.task(task.task_id)).state)

        if state == "published":
            output = (
                Path(args.output)
                if args.output
                else ROOT / ".deep-research-agent" / f"{fixture.fixture_id}.md"
            )
            published = await service.report(task.task_id)
            assert published is not None
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(published, encoding="utf-8")
            print(f"[written] {output}")

        return _verdict(fixture, state)
    finally:
        await connection.close()


def _verdict(fixture: fixture_set.Fixture, state: str) -> int:
    """Print the pre-registered assertions, then the state that was reached.

    In this order on purpose: the judgement must not be reconstructed from the
    report that was just produced.  Every terminal state is a legitimate result --
    which one was *correct* is the fixture's question, not the runner's -- so the
    exit code means "reached a terminal state", not "published".
    """

    print(f"\n--- 判定依据（先于本次运行写定）---\n{fixture.render()}")
    print(f"\n本次终局：{state}")
    return 0


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
    parser.add_argument(
        "--corpus",
        default="",
        help="用户本地资料库根目录（需要 Contract 授权 user_files 或 local_only）",
    )
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args(argv)

    if args.list or not args.fixture:
        for fixture in fixture_set.FIXTURES:
            print(f"{fixture.fixture_id:<26} {fixture.domain} × {fixture.genre}")
        return 0
    return asyncio.run(run(args))


if __name__ == "__main__":
    sys.exit(main())
