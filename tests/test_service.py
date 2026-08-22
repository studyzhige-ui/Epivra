"""The application service, tested with scripted models -- no provider calls.

The properties worth pinning are the ones every interface will depend on:

* state is *derived* from the store, never held by a caller, so two interfaces
  looking at the same database agree;
* one database holds many studies, which is what makes "list my tasks" work;
* research cannot start before the user approves the Contract they read;
* ``local_only`` leaves no network client in existence at all, rather than a
  client that is politely asked not to be used.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import aiosqlite

import deep_research_agent.service as service_module
from deep_research_agent.config import ROLES
from deep_research_agent.contract import CommissionBody
from deep_research_agent.model import ModelReply, ModelToolCall
from deep_research_agent.operations import ExecutionIdentity
from deep_research_agent.reporting import RoleRuntime
from deep_research_agent.service import (
    Event,
    ResearchService,
    new_task_id,
)

CONTRACT_BODY = """\
## 目的与用途

为工程团队判断协同编辑算法选型。不支持具体实现方案。

## 问题模型

Q1. CRDT 与 OT 在核心机制上的本质差异是什么，各自适合什么场景？

## 范围与定义

对象：两类算法的机制层面。默认假设：不评测具体实现的性能。

## 证据与分析方法

以一手论文与官方文档为主，主动寻找反例与失败案例。

## 交付与保证

面向工程团队的技术说明，需引用可追溯来源，接受独立审查。

## 自适应边界与已知限制

Lead 可调整检索顺序；改变 Q1 需重新审批。已知限制：无公开可比性能数据。
"""


def _call(name: str, **arguments: object) -> ModelToolCall:
    return ModelToolCall(
        call_id=f"toolu_{name}",
        name=name,
        arguments=json.dumps(arguments, ensure_ascii=False),
    )


class ScriptedModel:
    def __init__(self, *replies: ModelReply) -> None:
        self._replies = list(replies)
        self.calls = 0

    async def complete(self, messages, **kwargs):  # noqa: ANN001, ANN201
        self.calls += 1
        if not self._replies:
            raise AssertionError("scripted model ran out of replies")
        return self._replies.pop(0)


def _architect_reply() -> ModelReply:
    return ModelReply(
        tool_calls=(_call("propose_contract", contract_markdown=CONTRACT_BODY),)
    )


def _clarify_reply() -> ModelReply:
    return ModelReply(
        tool_calls=(
            _call(
                "ask_scope_question",
                question="这份研究是为选型还是为科普？",
                why_it_changes_the_plan="两者需要完全不同的证据与结构，无法同时满足。",
            ),
        )
    )


class ServiceFixture(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._directory = tempfile.TemporaryDirectory()
        self.path = Path(self._directory.name) / "tasks.sqlite3"
        self._connection = await aiosqlite.connect(self.path)
        self.service = ResearchService(
            connection=self._connection,
            environ={"DEEPSEEK_API_KEY": "test-key"},
        )
        await self.service.setup()

    async def asyncTearDown(self) -> None:
        await self._connection.close()
        self._directory.cleanup()

    def _use(self, *replies: ModelReply) -> ScriptedModel:
        """Run the whole service against a scripted model.

        Substituting the composition root rather than a private cache is what
        keeps this suite provider-free while still exercising the real path: the
        service resolves each task's frozen configuration and then asks
        ``build_runtimes`` to bind it, so ``self.bound`` records the configuration
        every task was actually bound with.
        """

        model = ScriptedModel(*replies)
        execution = ExecutionIdentity(provider="scripted", model_id="test")
        runtimes = {
            role: RoleRuntime(model=model, execution=execution) for role in ROLES
        }
        self.bound: list[object] = []

        def build(environ, *, config=None, roles=ROLES):  # noqa: ANN001, ANN202
            self.bound.append(config)
            return dict(runtimes)

        patcher = mock.patch.object(service_module, "build_runtimes", build)
        patcher.start()
        self.addCleanup(patcher.stop)
        return model

    async def _open(self, request: str = "比较 CRDT 与 OT。", **kwargs):  # noqa: ANN003, ANN202
        kwargs.setdefault("language", "zh")
        kwargs.setdefault("source_access", ("public_web",))
        kwargs.setdefault("created_at", "2026-08-20T00:00:00+00:00")
        return await self.service.open_task(request, **kwargs)


class LifecycleTest(ServiceFixture):
    async def test_a_new_task_waits_for_approval(self) -> None:
        self._use(_architect_reply())
        task = await self._open()
        self.assertEqual("awaiting_approval", task.state)
        self.assertTrue(task.task_id.startswith("t_"))
        self.assertIn("CRDT", task.request)

    async def test_state_is_derived_from_the_store_not_remembered(self) -> None:
        """A second service over the same file must agree without being told."""

        self._use(_architect_reply())
        task = await self._open()

        other = ResearchService(
            connection=self._connection, environ={"DEEPSEEK_API_KEY": "k"}
        )
        await other.setup()
        self.assertEqual("awaiting_approval", (await other.task(task.task_id)).state)

    async def test_research_cannot_start_before_approval(self) -> None:
        self._use(_architect_reply())
        task = await self._open()
        with self.assertRaisesRegex(ValueError, "has not been approved"):
            await self.service.advance(task.task_id)

    async def test_approval_binds_and_changes_the_state(self) -> None:
        self._use(_architect_reply())
        task = await self._open()
        await self.service.approve(task.task_id)
        self.assertEqual("researching", (await self.service.task(task.task_id)).state)

    async def test_a_clarification_leaves_no_contract_to_approve(self) -> None:
        self._use(_clarify_reply())
        events: list[Event] = []
        task = await self._open(listen=events.append)
        self.assertEqual("clarification_requested", task.state)
        self.assertEqual(["clarification_requested"], [e.kind for e in events])
        with self.assertRaisesRegex(ValueError, "no Contract"):
            await self.service.approve(task.task_id)

    async def test_the_approval_card_is_what_the_user_reads(self) -> None:
        self._use(_architect_reply())
        task = await self._open()
        card = await self.service.approval_card(task.task_id)
        self.assertIn("问题结构", card)
        self.assertIn("批准并开始研究", card)

    async def test_reopening_the_same_commission_does_not_re_ask_the_architect(
        self,
    ) -> None:
        """Resuming must not pay the Architect again for a Contract it wrote."""

        model = self._use(_architect_reply())
        first = await self._open()
        second = await self._open()
        self.assertEqual(first.task_id, second.task_id)
        self.assertEqual(1, model.calls)

    async def test_an_unknown_task_is_refused_clearly(self) -> None:
        with self.assertRaisesRegex(ValueError, "does not exist"):
            await self.service.task("t_missing")


class MultiTaskTest(ServiceFixture):
    async def test_one_database_holds_many_independent_studies(self) -> None:
        self._use(_architect_reply(), _architect_reply())
        first = await self._open("比较 CRDT 与 OT。")
        second = await self._open(
            "评估远程办公与离职率的证据。",
            created_at="2026-08-20T01:00:00+00:00",
        )
        self.assertNotEqual(first.task_id, second.task_id)

        listed = {task.task_id for task in await self.service.tasks()}
        self.assertEqual({first.task_id, second.task_id}, listed)

    async def test_the_same_question_asked_later_starts_a_second_study(self) -> None:
        self._use(_architect_reply(), _architect_reply())
        first = await self._open()
        again = await self._open(created_at="2026-08-21T00:00:00+00:00")
        self.assertNotEqual(first.task_id, again.task_id)

    async def test_no_report_before_publication(self) -> None:
        self._use(_architect_reply())
        task = await self._open()
        self.assertIsNone(await self.service.report(task.task_id))


class SourceAccessTest(ServiceFixture):
    """The permission must remove the capability, not request restraint."""

    async def test_local_only_builds_no_network_client_at_all(self) -> None:
        broker, reader = self.service._broker(  # noqa: SLF001
            ("local_only",), self.service.config
        )
        self.assertIsNone(broker)
        self.assertIsNone(reader)

    async def test_public_web_builds_a_broker_and_a_reader(self) -> None:
        broker, reader = self.service._broker(  # noqa: SLF001
            ("public_web",), self.service.config
        )
        self.assertIsNotNone(broker)
        self.assertIsNotNone(reader)

    async def test_local_access_without_a_corpus_root_is_refused(self) -> None:
        with self.assertRaisesRegex(ValueError, "no corpus root"):
            self.service._local_reader(("public_web", "user_files"), None)  # noqa: SLF001

    async def test_a_corpus_root_yields_a_local_reader(self) -> None:
        with tempfile.TemporaryDirectory() as corpus:
            (Path(corpus) / "note.md").write_text("内容", encoding="utf-8")
            self.assertIsNotNone(
                self.service._local_reader(  # noqa: SLF001
                    ("public_web", "user_files"), Path(corpus)
                )
            )

    async def test_public_web_alone_never_builds_a_local_reader(self) -> None:
        self.assertIsNone(
            self.service._local_reader(("public_web",), Path("."))  # noqa: SLF001
        )


class ExecutionSnapshotTest(ServiceFixture):
    """A study must keep the configuration it was created with.

    The failure this prevents: a user changes their default model on Tuesday and
    Monday's half-finished study silently continues on it, so the published report
    cites evidence gathered by one model and synthesised by another with nothing
    recording the switch.

    ``self.bound`` collects the RuntimeConfig each task was bound with, which is
    the only thing that actually answers "which model ran".
    """

    async def _service_with(self, environ: dict[str, str]) -> ResearchService:
        """A second service over the same database, as a later run would be."""

        service = ResearchService(connection=self._connection, environ=environ)
        await service.setup()
        return service

    def _model(self, index: int, role: str = "lead") -> str:
        config = self.bound[index]
        assert config is not None
        return config.model_for(role).model_id

    async def test_a_task_keeps_configuration_a_after_the_default_becomes_b(
        self,
    ) -> None:
        self._use(_architect_reply(), _architect_reply())
        # (1) create with configuration A
        self.service.rebind_credentials(
            {
                "DEEPSEEK_API_KEY": "k",
                "DEEP_RESEARCH_REASONING_MODEL": "model-a",
            }
        )
        task = await self._open()
        self.assertEqual("model-a", self._model(0))

        # (2) global defaults become B, in a fresh process
        later = await self._service_with(
            {"DEEPSEEK_API_KEY": "k", "DEEP_RESEARCH_REASONING_MODEL": "model-b"}
        )
        # (3) approve and continue the existing task
        await later.approve(task.task_id)
        execution = await later.execution(task.task_id)
        # (4) still configuration A
        self.assertTrue(execution.frozen)
        self.assertEqual("model-a", execution.config.model_for("lead").model_id)

        # (5) a task created now uses B
        fresh = await later.open_task(
            "另一个课题。",
            language="zh",
            source_access=("public_web",),
            created_at="2026-08-22T00:00:00+00:00",
        )
        self.assertEqual(
            "model-b",
            (await later.execution(fresh.task_id)).config.model_for("lead").model_id,
        )

    async def test_the_investigator_tier_is_frozen_independently(self) -> None:
        """The two user-facing choices are two tiers; both must be pinned."""

        self._use(_architect_reply())
        self.service.rebind_credentials(
            {
                "DEEPSEEK_API_KEY": "k",
                "DEEP_RESEARCH_REASONING_MODEL": "slow-a",
                "DEEP_RESEARCH_INVESTIGATOR_MODEL": "fast-a",
            }
        )
        task = await self._open()

        later = await self._service_with(
            {
                "DEEPSEEK_API_KEY": "k",
                "DEEP_RESEARCH_REASONING_MODEL": "slow-b",
                "DEEP_RESEARCH_INVESTIGATOR_MODEL": "fast-b",
            }
        )
        config = (await later.execution(task.task_id)).config
        self.assertEqual("slow-a", config.model_for("lead").model_id)
        self.assertEqual("fast-a", config.model_for("investigator").model_id)

    async def test_enabled_search_providers_are_frozen_too(self) -> None:
        """Which sources a study consulted is part of what it is."""

        self._use(_architect_reply())
        self.service.rebind_credentials(
            {
                "DEEPSEEK_API_KEY": "k",
                "DEEP_RESEARCH_SEARCH_PROVIDERS": "tavily",
                "DEEP_RESEARCH_PUBMED_SEARCH": "false",
            }
        )
        task = await self._open()

        later = await self._service_with(
            {
                "DEEPSEEK_API_KEY": "k",
                "DEEP_RESEARCH_SEARCH_PROVIDERS": "exa,brave",
                "DEEP_RESEARCH_PUBMED_SEARCH": "true",
            }
        )
        config = (await later.execution(task.task_id)).config
        self.assertEqual(("tavily", "duckduckgo"), config.search_providers)
        self.assertNotIn("pubmed", config.academic_providers)

    async def test_a_rotated_credential_is_not_frozen(self) -> None:
        """Keys are secrets that rotate; freezing one would strand the task."""

        self._use(_architect_reply())
        task = await self._open()
        snapshot_payload = (
            await self._connection.execute_fetchall(
                "SELECT payload FROM execution_snapshots WHERE task_id = ?",
                (task.task_id,),
            )
        )[0][0]
        self.assertNotIn("test-key", str(snapshot_payload))

        later = await self._service_with({"DEEPSEEK_API_KEY": "rotated-key"})
        self.assertTrue((await later.execution(task.task_id)).frozen)

    async def test_reopening_the_same_commission_does_not_refreeze(self) -> None:
        """Insert-only: the first run's configuration is the task's for good."""

        self._use(_architect_reply())
        self.service.rebind_credentials(
            {
                "DEEPSEEK_API_KEY": "k",
                "DEEP_RESEARCH_REASONING_MODEL": "model-a",
            }
        )
        task = await self._open()

        self.service.rebind_credentials(
            {"DEEPSEEK_API_KEY": "k", "DEEP_RESEARCH_REASONING_MODEL": "model-b"}
        )
        again = await self._open()
        self.assertEqual(task.task_id, again.task_id)
        self.assertEqual(
            "model-a",
            (await self.service.execution(task.task_id)).config.model_for(
                "lead"
            ).model_id,
        )

    async def test_rotating_a_key_does_not_change_a_frozen_model(self) -> None:
        self._use(_architect_reply())
        self.service.rebind_credentials(
            {
                "DEEPSEEK_API_KEY": "k",
                "DEEP_RESEARCH_REASONING_MODEL": "model-a",
            }
        )
        task = await self._open()
        await self.service.execution(task.task_id)

        self.service.rebind_credentials(
            {"DEEPSEEK_API_KEY": "new", "DEEP_RESEARCH_REASONING_MODEL": "model-b"}
        )
        self.assertEqual(
            "model-a",
            (await self.service.execution(task.task_id)).config.model_for(
                "lead"
            ).model_id,
        )

    async def test_two_tasks_in_one_database_run_on_their_own_models(self) -> None:
        """The binding is per task, which is why it cannot be service-wide."""

        self._use(_architect_reply(), _architect_reply())
        self.service.rebind_credentials(
            {
                "DEEPSEEK_API_KEY": "k",
                "DEEP_RESEARCH_REASONING_MODEL": "model-a",
            }
        )
        first = await self._open("第一个课题。")

        self.service.rebind_credentials(
            {"DEEPSEEK_API_KEY": "k", "DEEP_RESEARCH_REASONING_MODEL": "model-b"}
        )
        second = await self._open(
            "第二个课题。", created_at="2026-08-21T00:00:00+00:00"
        )

        self.assertEqual(
            "model-a",
            (await self.service.execution(first.task_id)).config.model_for(
                "lead"
            ).model_id,
        )
        self.assertEqual(
            "model-b",
            (await self.service.execution(second.task_id)).config.model_for(
                "lead"
            ).model_id,
        )

    async def test_deleting_a_study_removes_its_snapshot(self) -> None:
        self._use(_architect_reply())
        task = await self._open()
        await self.service.delete_research(task.task_id)
        rows = await self._connection.execute_fetchall(
            "SELECT COUNT(*) FROM execution_snapshots WHERE task_id = ?",
            (task.task_id,),
        )
        self.assertEqual(0, int(rows[0][0]))

    async def test_the_interface_can_show_which_models_a_task_is_bound_to(
        self,
    ) -> None:
        self._use(_architect_reply())
        self.service.rebind_credentials(
            {
                "DEEPSEEK_API_KEY": "k",
                "DEEP_RESEARCH_REASONING_MODEL": "model-a",
                "DEEP_RESEARCH_INVESTIGATOR_MODEL": "fast-a",
            }
        )
        task = await self._open()
        summary = await self.service.execution_summary(task.task_id)
        self.assertIn("model-a", summary)
        self.assertIn("fast-a", summary)


class LegacyTaskTest(ServiceFixture):
    """A task written before snapshots existed must stay resumable.

    The fallback is the current configuration -- there is nothing else to use --
    and the service says so rather than presenting it as a restored snapshot,
    naming any role whose model differs from what the ledger shows it called.
    """

    async def _legacy(self) -> str:
        """Create a task and then remove its snapshot, as an old database has."""

        self._use(_architect_reply())
        self.service.rebind_credentials(
            {
                "DEEPSEEK_API_KEY": "k",
                "DEEP_RESEARCH_REASONING_MODEL": "model-a",
            }
        )
        task = await self._open()
        await self._connection.execute(
            "DELETE FROM execution_snapshots WHERE task_id = ?", (task.task_id,)
        )
        await self._connection.commit()
        self.service._executions.clear()  # noqa: SLF001 - simulating a new process
        return task.task_id

    async def test_a_legacy_task_is_still_readable_and_resumable(self) -> None:
        task_id = await self._legacy()
        self.assertEqual("awaiting_approval", (await self.service.task(task_id)).state)
        execution = await self.service.execution(task_id)
        self.assertFalse(execution.frozen)
        self.assertEqual("model-a", execution.config.model_for("lead").model_id)

    async def test_the_fallback_is_announced_not_silent(self) -> None:
        task_id = await self._legacy()
        events: list[Event] = []
        await self.service.execution(task_id, listen=events.append)
        kinds = [event.kind for event in events]
        self.assertIn("configuration_not_frozen", kinds)

    async def test_the_warning_names_a_model_that_changed(self) -> None:
        """The whole risk of the fallback is a model the study never used."""

        task_id = await self._legacy()
        self.service.rebind_credentials(
            {"DEEPSEEK_API_KEY": "k", "DEEP_RESEARCH_REASONING_MODEL": "model-b"}
        )
        events: list[Event] = []
        await self.service.execution(task_id, listen=events.append)
        warning = next(e for e in events if e.kind == "configuration_not_frozen")
        # The scripted architect ran under model_id "test"; the fallback would
        # use model-b, so the difference must be reported.
        self.assertTrue(warning.detail["models_changed"])
        self.assertIn("architect", " ".join(warning.detail["models_changed"]))

    async def test_a_corrupt_snapshot_degrades_to_the_fallback(self) -> None:
        """An unreadable row must not make a study permanently unresumable."""

        self._use(_architect_reply())
        task = await self._open()
        await self._connection.execute(
            "UPDATE execution_snapshots SET payload = ? WHERE task_id = ?",
            ("{ not json", task.task_id),
        )
        await self._connection.commit()
        self.service._executions.clear()  # noqa: SLF001 - simulating a new process
        self.assertFalse((await self.service.execution(task.task_id)).frozen)

    async def test_the_summary_says_when_nothing_was_frozen(self) -> None:
        task_id = await self._legacy()
        self.assertIn("未冻结", await self.service.execution_summary(task_id))


class TaskIdentityTest(unittest.TestCase):
    def _commission(self, request: str) -> CommissionBody:
        return CommissionBody(request=request, source_access=("public_web",))

    def test_identity_is_stable_for_the_same_commission_and_instant(self) -> None:
        stamp = "2026-08-20T00:00:00+00:00"
        first = new_task_id(self._commission("同一个问题"), created_at=stamp)
        second = new_task_id(self._commission("同一个问题"), created_at=stamp)
        self.assertEqual(first, second)

    def test_a_different_question_gets_a_different_task(self) -> None:
        stamp = "2026-08-20T00:00:00+00:00"
        self.assertNotEqual(
            new_task_id(self._commission("问题甲"), created_at=stamp),
            new_task_id(self._commission("问题乙"), created_at=stamp),
        )

    def test_the_language_choice_is_part_of_the_task(self) -> None:
        stamp = "2026-08-20T00:00:00+00:00"
        english = CommissionBody(
            request="same", source_access=("public_web",), language="en"
        )
        chinese = CommissionBody(
            request="same", source_access=("public_web",), language="zh"
        )
        self.assertNotEqual(
            new_task_id(english, created_at=stamp),
            new_task_id(chinese, created_at=stamp),
        )


if __name__ == "__main__":
    unittest.main()
