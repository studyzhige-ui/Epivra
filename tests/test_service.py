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
from deep_research_agent.agents import architect as architect_module
from deep_research_agent.approval import (
    ApprovalBody,
    ApprovalError,
    StaleClarificationError,
    StalePlanError,
    approved_contract,
    record_decision,
)
from deep_research_agent.config import ROLES, ConfigError
from deep_research_agent.contract import CommissionBody
from deep_research_agent.model import (
    ModelAuthError,
    ModelReply,
    ModelToolCall,
)
from deep_research_agent.operations import ExecutionIdentity
from deep_research_agent.reporting import RoleRuntime
from deep_research_agent.service import (
    Event,
    ResearchService,
    new_task_id,
)
from deep_research_agent.sources import (
    ArtifactValidationError,
    MaterialBody,
    SourceAnchor,
    SourceSnapshotBody,
    locate_quote,
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

SYNTHESIS = (
    "## Q1 机制差异\n\nCRDT 用可交换的数据类型换取无中心排序；OT 用变换函数换取更小的"
    "元数据，代价是通常需要服务器排序。\n\n## 冲突与不可比\n\n公开材料只覆盖机制层面，"
    "没有同一负载下的对照实现，因此不能给出性能排序。\n\n## Evidence Frontier\n\n"
    "缺少同一负载下的对照实现；若出现，将改变适用场景的判断。"
)


def _call(name: str, **arguments: object) -> ModelToolCall:
    return ModelToolCall(
        call_id=f"toolu_{name}",
        name=name,
        arguments=json.dumps(arguments, ensure_ascii=False),
    )


class ScriptedModel:
    """Replies in order, and records the prompt each call was given.

    ``prompts`` is what makes "the Architect was told X" testable at all: the
    invariants worth pinning here are about the body a role receives, and a mock
    that only counts calls cannot see a section going missing.  A queued
    ``Exception`` is raised instead of returned, so a provider that fails part-way
    through a sequence -- the case every recovery path exists for -- needs no
    second stand-in class.
    """

    def __init__(self, *replies: ModelReply | Exception) -> None:
        self._replies: list[ModelReply | Exception] = list(replies)
        self.calls = 0
        self.prompts: list[str] = []

    async def complete(self, messages, **kwargs):  # noqa: ANN001, ANN201
        self.calls += 1
        self.prompts.append("\n".join(str(item) for item in messages))
        if not self._replies:
            raise AssertionError("scripted model ran out of replies")
        reply = self._replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


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

    def _use(self, *replies: ModelReply | Exception) -> ScriptedModel:
        """Run the whole service against a scripted model.

        Substituting the composition root rather than a private cache is what
        keeps this suite provider-free while still exercising the real path: the
        service resolves each task's frozen configuration and then asks
        ``build_runtimes`` to bind it, so ``self.bound`` records the configuration
        every task was actually bound with.

        One model object serves the whole test, which is also why a queued
        exception is the honest way to script a provider failure: the transports
        are cached per task, so a *replacement* model would not be picked up until
        credentials are rebound -- and the failures worth testing do not wait for
        that.
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
        with self.assertRaisesRegex(ApprovalError, "awaiting user approval"):
            await self.service.advance(task.task_id)

    async def test_approval_binds_and_changes_the_state(self) -> None:
        self._use(_architect_reply())
        task = await self._open()
        await self.service.approve(task.task_id, task.plan_id)
        self.assertEqual("researching", (await self.service.task(task.task_id)).state)

    async def test_a_clarification_leaves_no_contract_to_approve(self) -> None:
        self._use(_clarify_reply())
        events: list[Event] = []
        task = await self._open(listen=events.append)
        self.assertEqual("clarification_requested", task.state)
        self.assertEqual(["clarification_requested"], [e.kind for e in events])
        with self.assertRaisesRegex(ValueError, "no Contract"):
            await self.service.approve(task.task_id, "")

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
    """The permission must remove the capability, not request restraint.

    What is authorised is the Commission's own answer.  These pass a Commission
    rather than a bare tuple because the service asks it, instead of re-deciding
    from the access list -- two readings of one permission is how they drift.
    """

    def _commission(self, *access: str) -> CommissionBody:
        return CommissionBody(request="调研某个课题。", source_access=access)  # type: ignore[arg-type]

    async def test_local_only_builds_no_network_client_at_all(self) -> None:
        broker, reader = self.service._broker(  # noqa: SLF001
            self._commission("local_only"), self.service.config
        )
        self.assertIsNone(broker)
        self.assertIsNone(reader)

    async def test_public_web_builds_a_broker_and_a_reader(self) -> None:
        broker, reader = self.service._broker(  # noqa: SLF001
            self._commission("public_web"), self.service.config
        )
        self.assertIsNotNone(broker)
        self.assertIsNotNone(reader)

    async def test_local_access_without_a_corpus_root_is_refused(self) -> None:
        """And refused in a class an interface expects, not as a bare ValueError.

        A granted folder that has since been deleted is the user's setting failing
        to hold.  The workspace reports the ones it knows by name; a bare
        ``ValueError`` is what a bug in this program raises, and the boundary can
        no longer tell those two apart if a real refusal wears the same class.
        """

        with self.assertRaisesRegex(ConfigError, "no corpus root"):
            self.service._local_reader(  # noqa: SLF001
                self._commission("public_web", "user_files"), None
            )
        self.assertIn(ConfigError, service_module.EXPECTED_FAILURES)

    async def test_a_corpus_root_that_no_longer_exists_is_reported_not_fatal(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as corpus:
            missing = Path(corpus) / "moved-away"
        with self.assertRaises(ConfigError):
            self.service._local_reader(  # noqa: SLF001
                self._commission("public_web", "user_files"), missing
            )

    async def test_a_corpus_root_yields_a_local_reader(self) -> None:
        with tempfile.TemporaryDirectory() as corpus:
            (Path(corpus) / "note.md").write_text("内容", encoding="utf-8")
            self.assertIsNotNone(
                self.service._local_reader(  # noqa: SLF001
                    self._commission("public_web", "user_files"), Path(corpus)
                )
            )

    async def test_public_web_alone_never_builds_a_local_reader(self) -> None:
        self.assertIsNone(
            self.service._local_reader(  # noqa: SLF001
                self._commission("public_web"), Path(".")
            )
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
        await later.approve(task.task_id, task.plan_id)
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


class PlanLifecycleTest(ServiceFixture):
    """A plan may iterate; the study it belongs to may not.

    The defect these exist for: "revise" used to concatenate the user's
    instruction onto the request and open a *new* task, so adjusting a plan twice
    left three studies and two abandoned plans, and the Architect was handed an
    ever-longer brief instead of "here is your plan, change this".
    """

    def _revised(self, marker: str) -> ModelReply:
        """A distinct Contract body, so each version has its own identity."""

        return ModelReply(
            tool_calls=(
                _call(
                    "propose_contract",
                    contract_markdown=CONTRACT_BODY.replace(
                        "不评测具体实现的性能。", f"不评测具体实现的性能。{marker}"
                    ),
                ),
            )
        )

    async def test_the_first_plan_is_version_one_and_approvable(self) -> None:
        self._use(_architect_reply())
        task = await self._open()
        self.assertEqual(1, task.plan_version)
        self.assertTrue(task.plan_id.startswith("ctr_"))

        await self.service.approve(task.task_id, task.plan_id)
        _ref, approved = await approved_contract(
            self.service._store(task.task_id)  # noqa: SLF001
        )
        self.assertIn("CRDT", approved.body_markdown)

    async def test_a_revision_keeps_the_same_task_and_adds_a_version(self) -> None:
        """Invariant 1: revision does not create a new Research Task."""

        self._use(_architect_reply(), self._revised("聚焦已商业化实现。"))
        task = await self._open()

        revised = await self.service.request_revision(
            task.task_id, task.plan_id, "聚焦已经商业化的实现，不要融资历史。"
        )

        self.assertEqual(task.task_id, revised.task_id)
        self.assertEqual(2, revised.plan_version)
        self.assertNotEqual(task.plan_id, revised.plan_id)
        self.assertEqual("awaiting_approval", revised.state)
        self.assertEqual(1, len(await self.service.tasks()))

    async def test_the_architect_is_given_the_previous_plan_and_the_instruction(
        self,
    ) -> None:
        """Invariant: a revision is "change this plan", not "here is a new brief"."""

        model = self._use(_architect_reply(), self._revised("只看中美市场。"))
        task = await self._open()
        await self.service.request_revision(
            task.task_id, task.plan_id, "中美市场详细，欧洲简要。"
        )

        revision_prompt = model.prompts[-1]
        self.assertIn("上一份候选", revision_prompt)
        self.assertIn("用户要求的修改", revision_prompt)
        self.assertIn("中美市场详细，欧洲简要。", revision_prompt)
        self.assertIn("用户原始委托", revision_prompt)

    async def test_a_revision_is_given_the_clarifications_already_answered(
        self,
    ) -> None:
        """Every plan version sees the whole exchange, revisions included.

        It did not, and the asymmetry was silent: the first draft was told "for
        procurement, not education" and the second was not, so a revision could
        undo an answer the user had already given.
        """

        model = self._use(
            _clarify_reply(), _architect_reply(), self._revised("只看中美市场。")
        )
        asked = await self._open()
        planned = await self.service.answer_clarification(
            asked.task_id, asked.clarification_id, "为采购选型。"
        )
        await self.service.request_revision(
            planned.task_id, planned.plan_id, "中美市场详细，欧洲简要。"
        )

        revision_prompt = model.prompts[-1]
        self.assertIn("为采购选型。", revision_prompt)
        self.assertIn("这份研究是为选型还是为科普？", revision_prompt)
        self.assertIn("上一份候选", revision_prompt)

    async def test_the_revised_plan_descends_from_the_answers_too(self) -> None:
        """What the Architect reads and what the artifact records must agree."""

        self._use(
            _clarify_reply(), _architect_reply(), self._revised("只看中美市场。")
        )
        asked = await self._open()
        planned = await self.service.answer_clarification(
            asked.task_id, asked.clarification_id, "为采购选型。"
        )
        revised = await self.service.request_revision(
            planned.task_id, planned.plan_id, "中美市场详细。"
        )

        store = self.service._store(revised.task_id)  # noqa: SLF001
        parents = set((await store.get(revised.plan_id)).parent_refs)
        self.assertIn(asked.clarification_id, parents)
        self.assertIn(planned.plan_id, parents)

    async def test_three_versions_and_the_approved_one_is_the_last(self) -> None:
        """Invariant 8: only the approved plan becomes the execution contract."""

        self._use(
            _architect_reply(),
            self._revised("第二版：只看中美。"),
            self._revised("第三版：加入开源实现。"),
        )
        task = await self._open()
        second = await self.service.request_revision(
            task.task_id, task.plan_id, "只看中美市场。"
        )
        third = await self.service.request_revision(
            second.task_id, second.plan_id, "补上开源实现。"
        )
        self.assertEqual(3, third.plan_version)
        self.assertEqual(task.task_id, third.task_id)

        await self.service.approve(third.task_id, third.plan_id)
        history = await self.service.plan_history(task.task_id)
        self.assertEqual([1, 2, 3], [item.version for item in history])
        self.assertEqual(
            ["revision_requested", "revision_requested", "approved"],
            [item.decision for item in history],
        )
        self.assertEqual(third.plan_id, next(i.plan_id for i in history if i.approved))

    async def test_the_original_request_survives_every_revision(self) -> None:
        """Invariant 2: the Commission is not rewritten by a revision."""

        original = "调研 AI Agent 行业，包括主要公司、技术路线和未来趋势。"
        self._use(
            _architect_reply(),
            self._revised("第二版。"),
            self._revised("第三版。"),
        )
        task = await self._open(original)
        second = await self.service.request_revision(
            task.task_id, task.plan_id, "只看已商业化产品。"
        )
        third = await self.service.request_revision(
            second.task_id, second.plan_id, "去掉融资历史。"
        )
        self.assertEqual(original, third.request)
        self.assertEqual(original, (await self.service.task(task.task_id)).request)

    async def test_a_revision_needs_an_instruction(self) -> None:
        """Invariant 5: "change something" is not a request."""

        self._use(_architect_reply())
        task = await self._open()
        for empty in ("", "   ", "\n"):
            with self.subTest(instruction=empty):
                with self.assertRaisesRegex(
                    ArtifactValidationError, "what to change"
                ):
                    await self.service.request_revision(
                        task.task_id, task.plan_id, empty
                    )

    async def test_approving_a_superseded_plan_is_refused(self) -> None:
        """Invariant 6: a reply to the old screen must not approve the new plan."""

        self._use(_architect_reply(), self._revised("第二版。"))
        first = await self._open()
        stale_plan = first.plan_id
        await self.service.request_revision(
            first.task_id, stale_plan, "换个角度。"
        )

        with self.assertRaises(StalePlanError):
            await self.service.approve(first.task_id, stale_plan)
        self.assertEqual(
            "awaiting_approval", (await self.service.task(first.task_id)).state
        )

    async def test_revising_a_superseded_plan_is_refused(self) -> None:
        """Invariant 7: same guard, other direction."""

        self._use(_architect_reply(), self._revised("第二版。"))
        first = await self._open()
        stale_plan = first.plan_id
        await self.service.request_revision(first.task_id, stale_plan, "换个角度。")

        with self.assertRaises(StalePlanError):
            await self.service.request_revision(
                first.task_id, stale_plan, "再换一次。"
            )

    async def test_an_approved_plan_cannot_then_be_revised(self) -> None:
        self._use(_architect_reply())
        task = await self._open()
        await self.service.approve(task.task_id, task.plan_id)
        with self.assertRaisesRegex(ApprovalError, "已经批准"):
            await self.service.request_revision(
                task.task_id, task.plan_id, "再改一下。"
            )

    async def test_approving_twice_is_not_an_error(self) -> None:
        self._use(_architect_reply())
        task = await self._open()
        await self.service.approve(task.task_id, task.plan_id)
        await self.service.approve(task.task_id, task.plan_id)
        history = await self.service.plan_history(task.task_id)
        self.assertEqual(1, len(history))
        self.assertTrue(history[0].approved)

    async def test_an_interrupted_revision_resumes_from_the_recorded_request(
        self,
    ) -> None:
        """The instruction is committed before the Architect is called.

        So a crash between the two does not lose it: calling again with nothing
        new answers the request already on record.
        """

        self._use(_architect_reply(), self._revised("第二版。"))
        task = await self._open()
        store = self.service._store(task.task_id)  # noqa: SLF001
        await record_decision(
            store,
            task.plan_id,
            ApprovalBody(
                decision="revision_requested", revision_note="记录在案的要求。"
            ),
        )

        revised = await self.service.request_revision(task.task_id, task.plan_id, "")
        self.assertEqual(2, revised.plan_version)
        history = await self.service.plan_history(task.task_id)
        self.assertEqual("记录在案的要求。", history[0].revision_note)

    async def test_saying_something_new_supersedes_the_pending_request(self) -> None:
        """Otherwise the user's newest instruction would be silently discarded.

        Which also traps the study: if the Architect answers a revision with a
        scope question rather than a plan, replaying the recorded request would
        return that same question forever.
        """

        self._use(_architect_reply(), self._revised("第二版。"))
        task = await self._open()
        store = self.service._store(task.task_id)  # noqa: SLF001
        await record_decision(
            store,
            task.plan_id,
            ApprovalBody(decision="revision_requested", revision_note="先前的要求。"),
        )

        revised = await self.service.request_revision(
            task.task_id, task.plan_id, "改主意了：只看中国市场。"
        )

        self.assertEqual(2, revised.plan_version)
        history = await self.service.plan_history(task.task_id)
        self.assertEqual("改主意了：只看中国市场。", history[0].revision_note)

    async def test_the_plan_history_is_the_provenance_of_the_decision(self) -> None:
        """Item: revision history must be persisted, not held in the interface."""

        self._use(_architect_reply(), self._revised("第二版。"))
        task = await self._open()
        await self.service.request_revision(
            task.task_id, task.plan_id, "把欧洲市场删掉。"
        )

        # A second service over the same database answers identically.
        other = ResearchService(
            connection=self._connection, environ={"DEEPSEEK_API_KEY": "k"}
        )
        await other.setup()
        history = await other.plan_history(task.task_id)
        self.assertEqual(2, len(history))
        self.assertEqual("把欧洲市场删掉。", history[0].revision_note)
        self.assertEqual("", history[1].decision)

    async def test_a_revised_plan_records_what_it_came_from(self) -> None:
        """Lineage, in the artifact graph rather than a parallel version table."""

        self._use(_architect_reply(), self._revised("第二版。"))
        task = await self._open()
        revised = await self.service.request_revision(
            task.task_id, task.plan_id, "换个角度。"
        )

        store = self.service._store(task.task_id)  # noqa: SLF001
        envelope = await store.get(revised.plan_id)
        self.assertIn(task.plan_id, envelope.parent_refs)
        receipt = next(ref for ref in envelope.parent_refs if ref.startswith("apr_"))
        body = ApprovalBody.decode(await store.body(receipt))
        self.assertEqual("revision_requested", body.decision)
        self.assertEqual("换个角度。", body.revision_note)

    async def test_a_legacy_plan_without_revision_metadata_still_works(self) -> None:
        """Invariant: an existing awaiting-approval task stays usable.

        A task written before plan versions existed has one Contract and no
        receipts, which is exactly Plan v1 -- so it reads, approves and continues
        without a migration.
        """

        self._use(_architect_reply(), self._revised("第二版。"))
        task = await self._open()

        service = ResearchService(
            connection=self._connection, environ={"DEEPSEEK_API_KEY": "k"}
        )
        await service.setup()

        seen = await service.task(task.task_id)
        self.assertEqual(1, seen.plan_version)
        self.assertEqual("awaiting_approval", seen.state)

        revised = await service.request_revision(
            seen.task_id, seen.plan_id, "缩小到中国市场。"
        )
        self.assertEqual(2, revised.plan_version)
        await service.approve(revised.task_id, revised.plan_id)
        self.assertEqual("researching", (await service.task(task.task_id)).state)


class ClarificationLifecycleTest(ServiceFixture):
    """Scoping a study is a conversation, and it stays one study.

    Answering used to concatenate the reply onto the request and call open_task,
    which derives task identity from the Commission -- so one question produced
    two studies and stranded the first at ``clarification_requested`` forever.
    """

    def _question(self, text: str, why: str = "两者需要完全不同的证据。") -> ModelReply:
        return ModelReply(
            tool_calls=(
                _call("ask_scope_question", question=text, why_it_changes_the_plan=why),
            )
        )

    async def test_a_question_is_committed_and_survives_a_new_service(self) -> None:
        """Invariant 6: the question is an artifact, not a line in one session."""

        self._use(self._question("这份研究是为选型还是为科普？"))
        task = await self._open()
        self.assertEqual("clarification_requested", task.state)
        self.assertTrue(task.clarification_id.startswith("clq_"))
        self.assertEqual("这份研究是为选型还是为科普？", task.clarification_question)

        other = ResearchService(
            connection=self._connection, environ={"DEEPSEEK_API_KEY": "k"}
        )
        await other.setup()
        seen = await other.task(task.task_id)
        self.assertEqual(task.clarification_id, seen.clarification_id)
        self.assertEqual(task.clarification_question, seen.clarification_question)

    async def test_answering_keeps_the_same_task_and_reaches_a_plan(self) -> None:
        """Invariants 1 and 9: one task, and the outcome is that task's Plan v1."""

        self._use(self._question("为选型还是科普？"), _architect_reply())
        task = await self._open()

        resolved = await self.service.answer_clarification(
            task.task_id, task.clarification_id, "为选型。"
        )

        self.assertEqual(task.task_id, resolved.task_id)
        self.assertEqual("awaiting_approval", resolved.state)
        self.assertEqual(1, resolved.plan_version)
        self.assertEqual(1, len(await self.service.tasks()))

    async def test_two_rounds_of_clarification_stay_one_task(self) -> None:
        """Invariant 2, and invariant 8: the second question is a new question."""

        self._use(
            self._question("为选型还是科普？"),
            self._question("要覆盖哪些市场？"),
            _architect_reply(),
        )
        task = await self._open()
        second = await self.service.answer_clarification(
            task.task_id, task.clarification_id, "为选型。"
        )
        self.assertEqual("clarification_requested", second.state)
        self.assertEqual("要覆盖哪些市场？", second.clarification_question)
        self.assertNotEqual(task.clarification_id, second.clarification_id)

        resolved = await self.service.answer_clarification(
            second.task_id, second.clarification_id, "中国和美国。"
        )
        self.assertEqual(task.task_id, resolved.task_id)
        self.assertEqual("awaiting_approval", resolved.state)
        self.assertEqual(1, len(await self.service.tasks()))

        history = await self.service.clarification_history(task.task_id)
        self.assertEqual(
            [("为选型还是科普？", "为选型。"), ("要覆盖哪些市场？", "中国和美国。")],
            [(item.question, item.answer) for item in history],
        )

    async def test_the_original_request_survives_every_answer(self) -> None:
        """Invariant 3: the Commission is what the user asked, unchanged."""

        original = "调研 AI Agent 行业。"
        self._use(
            self._question("为选型还是科普？"),
            self._question("要覆盖哪些市场？"),
            _architect_reply(),
        )
        task = await self._open(original)
        second = await self.service.answer_clarification(
            task.task_id, task.clarification_id, "为选型。"
        )
        resolved = await self.service.answer_clarification(
            second.task_id, second.clarification_id, "中国和美国。"
        )
        self.assertEqual(original, resolved.request)
        self.assertEqual(original, (await self.service.task(task.task_id)).request)

    async def test_the_architect_sees_the_original_request_and_the_exchange(
        self,
    ) -> None:
        """Invariant 7, verified against the real prompt rather than a mock call."""

        model = self._use(
            self._question("为选型还是科普？"),
            self._question("要覆盖哪些市场？"),
            _architect_reply(),
        )
        task = await self._open("调研 AI Agent 行业。")
        second = await self.service.answer_clarification(
            task.task_id, task.clarification_id, "为选型。"
        )
        await self.service.answer_clarification(
            second.task_id, second.clarification_id, "中国和美国。"
        )

        final_prompt = model.prompts[-1]
        self.assertIn("用户原始委托", final_prompt)
        self.assertIn("调研 AI Agent 行业。", final_prompt)
        self.assertIn("澄清问题与用户的回答", final_prompt)
        self.assertIn("Q1. 为选型还是科普？", final_prompt)
        self.assertIn("A1. 为选型。", final_prompt)
        self.assertIn("Q2. 要覆盖哪些市场？", final_prompt)
        self.assertIn("A2. 中国和美国。", final_prompt)
        # The answer must not have been glued onto the request.
        self.assertNotIn("调研 AI Agent 行业。\n\n为选型。", final_prompt)

    async def test_the_second_call_is_not_a_replay_of_the_first_question(self) -> None:
        """The ledger keys on input refs, so the answered exchange must be one.

        Without it the Architect's first answer would replay forever and the study
        could never leave clarification -- the same trap the revision path hit.
        """

        model = self._use(self._question("为选型还是科普？"), _architect_reply())
        task = await self._open()
        await self.service.answer_clarification(
            task.task_id, task.clarification_id, "为选型。"
        )
        self.assertEqual(2, model.calls, "the Architect must be asked again")

    async def test_an_answer_needs_content(self) -> None:
        self._use(self._question("为选型还是科普？"))
        task = await self._open()
        for empty in ("", "   "):
            with self.subTest(answer=empty):
                with self.assertRaises(ArtifactValidationError):
                    await self.service.answer_clarification(
                        task.task_id, task.clarification_id, empty
                    )

    async def test_answering_a_superseded_question_is_refused(self) -> None:
        """Invariant 5: an answer to the old question is not the new one's answer."""

        self._use(
            self._question("为选型还是科普？"),
            self._question("要覆盖哪些市场？"),
            _architect_reply(),
        )
        task = await self._open()
        stale = task.clarification_id
        await self.service.answer_clarification(task.task_id, stale, "为选型。")

        with self.assertRaises(StaleClarificationError):
            await self.service.answer_clarification(task.task_id, stale, "中国和美国。")

    async def test_answering_when_nothing_is_open_is_refused(self) -> None:
        self._use(_architect_reply())
        task = await self._open()
        with self.assertRaisesRegex(ApprovalError, "没有待回答的问题"):
            await self.service.answer_clarification(task.task_id, "", "随便说点什么。")

    async def test_the_plan_records_the_exchange_that_shaped_it(self) -> None:
        """Lineage: Plan v1 descends from the Commission *and* the answers."""

        self._use(self._question("为选型还是科普？"), _architect_reply())
        task = await self._open()
        resolved = await self.service.answer_clarification(
            task.task_id, task.clarification_id, "为选型。"
        )

        store = self.service._store(task.task_id)  # noqa: SLF001
        envelope = await store.get(resolved.plan_id)
        self.assertIn(task.clarification_id, envelope.parent_refs)
        self.assertTrue(
            any(ref.startswith("cms_") for ref in envelope.parent_refs),
            "the Commission stays the plan's ancestor",
        )

    async def test_clarification_does_not_change_the_execution_snapshot(self) -> None:
        """Invariant 10: answering a question is not a configuration change."""

        self._use(self._question("为选型还是科普？"), _architect_reply())
        task = await self._open()
        before = await self.service.execution(task.task_id)

        await self.service.answer_clarification(
            task.task_id, task.clarification_id, "为选型。"
        )

        after = await self.service.execution(task.task_id)
        self.assertTrue(after.frozen)
        self.assertEqual(
            before.config.model_for("architect").model_id,
            after.config.model_for("architect").model_id,
        )
        self.assertEqual(before.config.search_providers, after.config.search_providers)

    async def test_clarification_flows_into_the_plan_lifecycle(self) -> None:
        """The join: one task from first question through to an approved plan."""

        self._use(
            self._question("为选型还是科普？"),
            _architect_reply(),
            ModelReply(
                tool_calls=(
                    _call(
                        "propose_contract",
                        contract_markdown=CONTRACT_BODY.replace(
                            "不评测具体实现的性能。", "不评测具体实现的性能。只看中美。"
                        ),
                    ),
                )
            ),
        )
        task = await self._open()
        planned = await self.service.answer_clarification(
            task.task_id, task.clarification_id, "为选型。"
        )
        revised = await self.service.request_revision(
            planned.task_id, planned.plan_id, "只看中美市场。"
        )
        await self.service.approve(revised.task_id, revised.plan_id)

        final = await self.service.task(task.task_id)
        self.assertEqual(task.task_id, final.task_id)
        self.assertEqual("researching", final.state)
        self.assertEqual(2, final.plan_version)
        self.assertEqual(1, len(await self.service.tasks()))
        self.assertEqual(
            1, len(await self.service.clarification_history(task.task_id))
        )

    async def test_a_legacy_clarification_task_is_still_readable(self) -> None:
        """An old task has no clarification artifact at all.

        It reads, it reports the state honestly, and it has no open question to
        answer -- which is the truth about it, since the question was never
        recorded anywhere.  Nothing about it becomes unreadable or crashes.
        """

        self._use(_clarify_reply())
        task = await self._open()
        store = self.service._store(task.task_id)  # noqa: SLF001
        view = await store.active_view()
        # Simulate the pre-clarification-artifact shape by removing the record.
        for ref in view.active("clarification"):
            await self._connection.execute(
                "DELETE FROM artifacts WHERE task_id = ? AND artifact_id = ?",
                (task.task_id, ref),
            )
        await self._connection.commit()

        legacy = await self.service.task(task.task_id)
        self.assertEqual("clarification_requested", legacy.state)
        self.assertEqual("", legacy.clarification_id)
        self.assertEqual((), await self.service.clarification_history(task.task_id))
        self.assertTrue(await self.service.delete_research(task.task_id))


class PlanningFailureTest(ServiceFixture):
    """A plan the Architect never produced must not strand the study.

    The failure is ordinary: a provider outage, an expired key, an exhausted
    quota.  What made it serious was that the resulting task had a Commission and
    nothing else -- no plan to approve, no question to answer, nothing to
    continue -- so deleting it and retyping the request was the only way out.
    """

    def _failing(self) -> ScriptedModel:
        """A provider that refuses every call before running it.

        An expired key, which is a failure the ledger can safely mark retryable
        because nothing was billed.  ``ModelUnavailableError`` deliberately is not
        retryable -- a read timeout may have been billed -- so recovering from that
        one needs ``tools/reconcile.py`` and a human judgment.
        """

        return self._use(
            *[ModelAuthError("model authentication failed with HTTP 401")] * 4
        )

    async def test_a_failed_plan_leaves_a_task_with_no_open_question(self) -> None:
        self._failing()
        with self.assertRaises(ModelAuthError):
            await self._open()

        tasks = await self.service.tasks()
        self.assertEqual(1, len(tasks))
        stranded = tasks[0]
        self.assertEqual("clarification_requested", stranded.state)
        self.assertEqual("", stranded.plan_id)
        self.assertEqual("", stranded.clarification_id)

    async def test_replan_recovers_the_task_once_the_provider_returns(self) -> None:
        self._failing()
        with self.assertRaises(ModelAuthError):
            await self._open()
        stranded = (await self.service.tasks())[0]

        # The user fixes the key.  Rebinding is what drops the transports bound to
        # the old one; the task's frozen *configuration* is untouched by it.
        self._use(_architect_reply())
        self.service.rebind_credentials({"DEEPSEEK_API_KEY": "fixed"})
        recovered = await self.service.replan(stranded.task_id)

        self.assertEqual(stranded.task_id, recovered.task_id)
        self.assertEqual("awaiting_approval", recovered.state)
        self.assertEqual(1, recovered.plan_version)
        self.assertEqual(1, len(await self.service.tasks()))

    async def test_replan_on_a_planned_task_costs_nothing(self) -> None:
        model = self._use(_architect_reply())
        task = await self._open()
        again = await self.service.replan(task.task_id)
        self.assertEqual(task.plan_id, again.plan_id)
        self.assertEqual(1, model.calls, "proposing is idempotent")

    async def test_replan_still_reaches_a_clarification(self) -> None:
        """Retrying may legitimately produce a question rather than a plan."""

        self._use(
            ModelReply(
                tool_calls=(
                    _call(
                        "ask_scope_question",
                        question="为选型还是科普？",
                        why_it_changes_the_plan="证据完全不同。",
                    ),
                )
            )
        )
        task = await self._open()
        self.assertTrue(task.clarification_id)
        again = await self.service.replan(task.task_id)
        self.assertEqual("clarification_requested", again.state)
        self.assertEqual(task.clarification_id, again.clarification_id)

    async def test_replan_does_not_lose_what_the_user_already_answered(self) -> None:
        """The worst shape for this: answered, *then* the planning call failed.

        The answer is committed and the plan is not, so retrying has to rebuild the
        context from the store rather than from anything a caller kept.  If it did
        not, the retry would plan from the bare commission -- and the user would be
        asked the same question again, or get a plan that ignores their answer.
        """

        model = self._use(
            _clarify_reply(),
            ModelAuthError("model authentication failed with HTTP 401"),
            _architect_reply(),
        )
        asked = await self._open()

        with self.assertRaises(ModelAuthError):
            await self.service.answer_clarification(
                asked.task_id, asked.clarification_id, "为采购选型。"
            )
        stranded = await self.service.task(asked.task_id)
        self.assertEqual("clarification_requested", stranded.state)
        self.assertEqual("", stranded.plan_id)

        recovered = await self.service.replan(asked.task_id)

        self.assertEqual("awaiting_approval", recovered.state)
        self.assertEqual(asked.task_id, recovered.task_id)
        replan_prompt = model.prompts[-1]
        self.assertIn("比较 CRDT 与 OT。", replan_prompt)
        self.assertIn("这份研究是为选型还是为科普？", replan_prompt)
        self.assertIn("为采购选型。", replan_prompt)
        # And the answer is part of what the plan descends from, not only of what
        # the model was shown.
        store = self.service._store(recovered.task_id)  # noqa: SLF001
        self.assertIn(
            asked.clarification_id,
            (await store.get(recovered.plan_id)).parent_refs,
        )


class ArchitectContextTest(ServiceFixture):
    """Three paths reach the Architect; exactly one builds its context.

    Plan v1, a revision and a replan differ only in what they add to the same
    body.  When each built its own, the difference was invisible: the revision
    silently lacked the clarification history, and neither call site read as
    wrong -- each looked complete on its own.
    """

    def test_only_one_place_in_the_package_builds_that_context(self) -> None:
        package = Path(service_module.__file__).parent
        callers = sorted(
            path.relative_to(package).as_posix()
            for path in package.rglob("*.py")
            if "architect_context_body(" in path.read_text(encoding="utf-8")
            and path.name != "architect.py"
        )
        self.assertEqual(["service.py"], callers)
        self.assertEqual(
            1,
            (package / "service.py")
            .read_text(encoding="utf-8")
            .count("architect_context_body("),
        )

    async def test_all_three_paths_go_through_the_one_builder(self) -> None:
        """Recorded at the builder itself, so no path can reach the model past it."""

        built: list[str] = []
        original = architect_module.architect_context_body

        def recording(*args: object, **kwargs: object) -> str:
            built.append("revision" if kwargs.get("revision_note") else "plan")
            return original(*args, **kwargs)  # type: ignore[arg-type]

        self._use(
            _clarify_reply(),
            _architect_reply(),
            ModelReply(
                tool_calls=(
                    _call(
                        "propose_contract",
                        contract_markdown=CONTRACT_BODY.replace(
                            "不评测具体实现的性能。", "不评测具体实现的性能。只看中美。"
                        ),
                    ),
                )
            ),
        )
        patcher = mock.patch.object(
            architect_module, "architect_context_body", recording
        )
        patcher.start()
        self.addCleanup(patcher.stop)

        asked = await self._open()
        self.assertEqual(["plan"], built)

        # Replanning while a question is open must not reach the Architect at all:
        # planning waits for the user, not for the model.
        await self.service.replan(asked.task_id)
        self.assertEqual(["plan"], built)

        planned = await self.service.answer_clarification(
            asked.task_id, asked.clarification_id, "为采购选型。"
        )
        await self.service.request_revision(
            planned.task_id, planned.plan_id, "只看中美市场。"
        )
        self.assertEqual(["plan", "plan", "revision"], built)


class ReviewHaltTest(ServiceFixture):
    """Review's final refusal is its own state, and it is derived.

    ``advance()`` used to return ``"halted"`` while ``TaskState`` did not list it
    and ``task()`` could not produce it: the interface had no glyph and no label
    for the one value the run actually returned, and reopening the database
    reported the study as merely paused.  Two accounts of one truth, disagreeing.
    """

    SOURCE_TEXT = (
        "CRDT merges concurrent edits without a central server, while OT requires "
        "a transformation function and, in most deployments, a server that orders "
        "operations before broadcasting them."
    )
    QUOTE = "CRDT merges concurrent edits without a central server"

    async def _seed_evidence(self, task_id: str) -> None:
        """Give the task one citable Material, so a report can be written."""

        store = self.service._store(task_id)  # noqa: SLF001
        text_ref = await self.service._content.put(self.SOURCE_TEXT)  # noqa: SLF001
        source = await store.put(
            kind="source_snapshot",
            body=SourceSnapshotBody(
                url="https://example.org/crdt-vs-ot",
                title="CRDT and OT compared",
                text_ref=text_ref,
                fetched_at="2026-08-20",
            ).encode(),
        )
        material = MaterialBody.create(
            content="CRDT 不需要中心服务器即可合并并发编辑；OT 通常需要服务器排序。",
            boundaries="仅机制层面；不含性能数据。",
            anchors=(
                SourceAnchor(
                    source_ref=source.artifact_id,
                    exact_quote=self.QUOTE,
                    locator=locate_quote(self.SOURCE_TEXT, self.QUOTE),
                ),
            ),
        )
        await store.put(
            kind="material",
            body=material.encode(),
            parent_refs=material.source_refs,
        )

    def _blocking(self) -> ModelReply:
        return ModelReply(
            tool_calls=(
                _call(
                    "block_report",
                    findings=[
                        {
                            "location": "执行摘要",
                            "problem": "结论强度超出机制层面证据允许的范围。",
                            "impact": "读者会把机制差异当成全场景优劣结论。",
                            "acceptance_condition": "把结论限定到机制层面。",
                        }
                    ],
                ),
            )
        )

    async def _halt(self) -> str:
        """Drive one study to a report that review refuses twice."""

        report = (
            "# CRDT 与 OT 的机制差异\n\n## 执行摘要\n\n"
            "两者的本质差异在于是否需要中心服务器排序 [[cite:h1]]。\n\n"
            "## 局限\n\n本报告不覆盖性能。\n"
        )
        self._use(
            _architect_reply(),
            ModelReply(
                tool_calls=(
                    _call(
                        "commission_report",
                        report_brief="面向工程团队的机制对比说明。",
                        stop_rationale="公开证据已覆盖机制层面，达到当前能力边界。",
                    ),
                )
            ),
            ModelReply(
                tool_calls=(
                    _call("publish_synthesis", synthesis_markdown=SYNTHESIS * 2),
                )
            ),
            ModelReply(tool_calls=(_call("submit_report", report_markdown=report),)),
            self._blocking(),
            ModelReply(
                tool_calls=(
                    _call(
                        "submit_revised_report",
                        report_markdown=report,
                        finding_dispositions=[
                            {"finding_index": 1, "response": "已限定到机制层面。"}
                        ],
                    ),
                )
            ),
            self._blocking(),
        )
        task = await self._open()
        await self._seed_evidence(task.task_id)
        await self.service.approve(task.task_id, task.plan_id)
        return task.task_id

    async def test_a_final_block_is_halted_and_advance_agrees_with_task(self) -> None:
        task_id = await self._halt()
        events: list[Event] = []

        state = await self.service.advance(task_id, listen=events.append)

        self.assertEqual("halted", state)
        self.assertEqual("halted", (await self.service.task(task_id)).state)
        self.assertEqual("halted", events[-1].kind)
        self.assertIn("未发布", events[-1].message)

    async def test_halted_survives_a_new_service_over_the_same_database(self) -> None:
        """Nothing was stored, so reopening has to reach the same conclusion."""

        task_id = await self._halt()
        await self.service.advance(task_id)

        another = ResearchService(
            connection=self._connection, environ={"DEEPSEEK_API_KEY": "test-key"}
        )
        await another.setup()
        self.assertEqual("halted", (await another.task(task_id)).state)

    async def test_halted_is_not_paused(self) -> None:
        """The two must never collapse: only one of them can be finished by resuming."""

        task_id = await self._halt()
        # Approved, with evidence already gathered and no report yet: continuing
        # is all this study needs.
        self.assertEqual("paused", (await self.service.task(task_id)).state)

        await self.service.advance(task_id)

        # Review has now refused twice, which is a different situation and says so.
        self.assertEqual("halted", (await self.service.task(task_id)).state)


class GovernancePauseTest(ServiceFixture):
    """Every exit from governance must report the state the store derives.

    ``_report`` already read the state back, and its comment said why: it is the
    only way ``advance()`` and ``task()`` cannot disagree about the same study.  The
    four governance exits returned a hardcoded ``"paused"`` instead, so a study
    that stopped before gathering any evidence announced itself as paused and then
    reported itself as researching -- two accounts of one truth, which is precisely
    what ``ReviewHaltTest`` was written to stamp out for ``halted``.
    """

    def _prose_only(self) -> ModelReply:
        """A Lead reply with no tool call: it cannot act, so governance pauses."""

        return ModelReply(content="我认为应该继续检索，但没有提交动作。")

    async def test_advance_and_task_agree_when_nothing_was_gathered(self) -> None:
        self._use(_architect_reply(), self._prose_only(), self._prose_only())
        task = await self._open()
        await self.service.approve(task.task_id, task.plan_id)

        returned = await self.service.advance(task.task_id)
        derived = (await self.service.task(task.task_id)).state

        self.assertEqual(derived, returned)

    async def test_the_announced_event_names_the_derived_state(self) -> None:
        """An interface keys off the event kind, so it must match too."""

        self._use(_architect_reply(), self._prose_only(), self._prose_only())
        task = await self._open()
        await self.service.approve(task.task_id, task.plan_id)

        events: list[Event] = []
        state = await self.service.advance(task.task_id, listen=events.append)

        self.assertEqual(state, events[-1].kind)

    async def test_a_lead_asking_for_a_human_agrees_too(self) -> None:
        self._use(
            _architect_reply(),
            ModelReply(
                tool_calls=(
                    _call(
                        "request_user_input",
                        question="需要你确认适用的司法辖区。",
                        reason="不同辖区会导致完全不同的证据集合。",
                    ),
                )
            ),
        )
        task = await self._open()
        await self.service.approve(task.task_id, task.plan_id)

        returned = await self.service.advance(task.task_id)
        self.assertEqual((await self.service.task(task.task_id)).state, returned)


class FrozenOperationTest(ServiceFixture):
    """A frozen operation is its own state, and it is derived like the others.

    ARCHITECTURE §8.1 always listed ``needs_reconciliation``, but ``TaskState`` did
    not and nothing asked the ledger -- so a study with a frozen operation reported
    ``researching`` and the interface kept offering to continue, which could only
    raise the same frozen error.  The ledger already knew; nobody read it.
    """

    async def _freeze(self) -> str:
        """Drive one study into a frozen operation the way a real one gets there."""

        self._use(_architect_reply(), TimeoutError("no answer came back"))
        task = await self._open()
        await self.service.approve(task.task_id, task.plan_id)
        with self.assertRaises(TimeoutError):
            await self.service.advance(task.task_id)
        return task.task_id

    async def test_the_state_says_a_human_is_needed(self) -> None:
        task_id = await self._freeze()
        self.assertEqual(
            "needs_reconciliation", (await self.service.task(task_id)).state
        )

    async def test_it_is_not_offered_as_something_to_continue(self) -> None:
        """The whole point: resuming cannot work, so it must not be suggested."""

        from deep_research_agent.cli.workspace import CONTINUABLE

        task_id = await self._freeze()
        state = (await self.service.task(task_id)).state
        self.assertNotIn(state, CONTINUABLE)

    async def test_it_survives_reopening_the_database(self) -> None:
        """Derived from the ledger, so a second service reaches the same answer."""

        task_id = await self._freeze()
        other = ResearchService(
            connection=self._connection, environ={"DEEPSEEK_API_KEY": "k"}
        )
        await other.setup()
        self.assertEqual("needs_reconciliation", (await other.task(task_id)).state)

    async def test_a_published_study_is_not_dragged_back_by_a_stray_freeze(
        self,
    ) -> None:
        """Publication is terminal; a frozen operation cannot un-publish it."""

        task_id = await self._freeze()
        store = self.service._store(task_id)  # noqa: SLF001
        report = await store.put(kind="report", body="# 报告\n\n正文。\n")
        await store.put(
            kind="publication_receipt",
            body="# 报告\n\n正文。\n",
            parent_refs=(report.artifact_id,),
        )
        self.assertEqual("published", (await self.service.task(task_id)).state)


class TaskOrderTest(ServiceFixture):
    async def test_the_newest_study_is_listed_first(self) -> None:
        """Ordering by task_id sorted by hash, so the list was arbitrary."""

        self._use(_architect_reply(), _architect_reply(), _architect_reply())
        first = await self._open("第一个课题。", created_at="2026-08-20T00:00:00+00:00")
        second = await self._open("第二个课题。", created_at="2026-08-21T00:00:00+00:00")
        third = await self._open("第三个课题。", created_at="2026-08-22T00:00:00+00:00")

        listed = [task.task_id for task in await self.service.tasks()]
        self.assertEqual([third.task_id, second.task_id, first.task_id], listed)


if __name__ == "__main__":
    unittest.main()
