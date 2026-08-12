from __future__ import annotations

import json
import unittest
from collections.abc import Mapping, Sequence
from dataclasses import asdict, is_dataclass
from typing import Any

import deep_research_agent.researcher as researcher_runtime
from deep_research_agent.checkpoint import memory_checkpointer
from deep_research_agent.content_store import ContentIntegrityError, InMemoryContentStore
from deep_research_agent.model import (
    DurableBodyPage,
    MessageCapacityError,
    ModelReply,
    ModelToolCall,
    ToolSpec,
    compact_tool_loop_messages,
    durable_tool_observation,
    prepare_durable_tool_loop_messages,
    serialized_model_request_chars,
    serialized_messages_chars,
)
from deep_research_agent.planner import AgenticPlanner, PlannerRuntimeError
from deep_research_agent.researcher import (
    ControlledResearcher,
    researcher_output_from_subgraph,
    researcher_subgraph_input,
)
from deep_research_agent.roles import PlannerContext, ResearcherContext
from deep_research_agent.state import (
    BodyRef,
    JournalEntry,
    ResearchContract,
    ResearchTask,
    SourceDocument,
)
from deep_research_agent.tools import (
    ProviderInfo,
    ProviderResult,
    ReadResult,
    TransparentSearchBroker,
)


def tool_call(call_id: str, name: str, arguments: Mapping[str, Any]) -> ModelReply:
    return ModelReply(
        tool_calls=(
            ModelToolCall(call_id, name, json.dumps(arguments, ensure_ascii=False)),
        )
    )


class HugeSearchProvider:
    provider_id = "huge-search"

    async def describe(self) -> ProviderInfo:
        return ProviderInfo(self.provider_id, ("search", "raw_content"))

    async def search(self, *, query: str, intent: str, source_kind: str):
        return tuple(
            ProviderResult(
                title=f"Result {index}",
                url=f"https://example.test/{index}",
                snippet="bounded discovery snippet",
                content=(f"result-{index}-" + "x" * 12_000),
            )
            for index in range(8)
        )


class RecallProvider:
    provider_id = "recall-search"

    def __init__(self, *, snippet_only_first: bool = False) -> None:
        self.search_calls = 0
        self.describe_calls = 0
        self.snippet_only_first = snippet_only_first

    async def describe(self) -> ProviderInfo:
        self.describe_calls += 1
        return ProviderInfo(self.provider_id, ("search", "raw_content"))

    async def search(self, *, query: str, intent: str, source_kind: str):
        self.search_calls += 1
        marker = "EARLY_SENTINEL" if self.search_calls == 1 else "later"
        content = f"{marker} " + "x" * 6_000
        if self.search_calls == 1 and self.snippet_only_first:
            content = ""
        return (
            ProviderResult(
                title=f"Result {self.search_calls}",
                url=f"https://example.test/recall/{self.search_calls}",
                snippet=f"{marker} snippet",
                content=content,
            ),
        )


class HugeReader:
    def __init__(self, content: str) -> None:
        self.content = content

    async def read(self, url: str) -> ReadResult:
        return ReadResult("Huge source", url, self.content)


class CapacityPlannerModel:
    def __init__(self, limit: int, searches: int = 6) -> None:
        self.limit = limit
        self.searches = searches
        self.presearch_calls = 0
        self.messages: list[list[dict[str, Any]]] = []

    async def complete(
        self,
        messages: Sequence[Mapping[str, Any]],
        *,
        json_output: bool = False,
        tools: Sequence[ToolSpec] = (),
        tool_choice: str | None = None,
    ) -> ModelReply:
        self.assert_bounded(
            messages,
            json_output=json_output,
            tools=tools,
            tool_choice=tool_choice,
        )
        self.messages.append([dict(message) for message in messages])
        if json_output:
            return ModelReply(
                content=json.dumps(
                    {
                        "status": "plan_ready",
                        "research_contract": "Research the current primary sources.",
                        "approval_card": "Review the current primary sources.",
                        "guide_refs": [],
                    }
                )
            )
        self.presearch_calls += 1
        if self.presearch_calls <= self.searches:
            return tool_call(
                f"search-{self.presearch_calls}",
                "search",
                {
                    "query": f"current evidence {self.presearch_calls}",
                    "intent": "make the plan current",
                },
            )
        return tool_call(
            "finish",
            "finish_presearch",
            {"summary": "Bounded current presearch is sufficient for planning."},
        )

    def assert_bounded(
        self,
        messages: Sequence[Mapping[str, Any]],
        *,
        json_output: bool,
        tools: Sequence[ToolSpec],
        tool_choice: str | None,
    ) -> None:
        size = serialized_model_request_chars(
            messages,
            json_output=json_output,
            tools=tools,
            tool_choice=tool_choice,  # type: ignore[arg-type]
        )
        if size > self.limit:
            raise AssertionError(f"model received {size} chars above {self.limit}")


class CandidatePagingModel:
    def __init__(self, limit: int, inspect_turns: int = 7) -> None:
        self.limit = limit
        self.inspect_turns = inspect_turns
        self.calls = 0
        self.candidate_id = ""
        self.messages: list[list[dict[str, Any]]] = []

    async def complete(
        self,
        messages: Sequence[Mapping[str, Any]],
        *,
        json_output: bool = False,
        tools: Sequence[ToolSpec] = (),
        tool_choice: str | None = None,
    ) -> ModelReply:
        size = serialized_model_request_chars(
            messages,
            json_output=json_output,
            tools=tools,
            tool_choice=tool_choice,  # type: ignore[arg-type]
        )
        if size > self.limit:
            raise AssertionError(f"model received {size} chars above {self.limit}")
        self.calls += 1
        self.messages.append([dict(message) for message in messages])
        if self.calls == 1:
            return tool_call(
                "read", "read_source", {"url": "https://example.test/huge"}
            )
        observation = json.loads(str(messages[-1]["content"]))
        if self.calls == 2:
            self.candidate_id = observation["candidate_id"]
        if self.calls <= self.inspect_turns + 1:
            page = observation.get("candidate", observation)
            return tool_call(
                f"inspect-{self.calls}",
                "inspect_candidate",
                {
                    "candidate_id": self.candidate_id,
                    "offset": page["next_offset"],
                },
            )
        if self.calls == self.inspect_turns + 2:
            return tool_call(
                "save", "save_source", {"candidate_id": self.candidate_id}
            )
        return tool_call(
            "finish", "finish_turn", {"summary": "The full candidate was saved."}
        )


class StatelessPlannerRecallModel:
    def __init__(self, limit: int, provider: RecallProvider) -> None:
        self.limit = limit
        self.provider = provider
        self.messages: list[list[dict[str, Any]]] = []
        self.finalizer_saw_sentinel = False
        self.early_search_was_compacted = False
        self.recalled_snippet_only = False

    async def complete(
        self,
        messages: Sequence[Mapping[str, Any]],
        *,
        json_output: bool = False,
        tools: Sequence[ToolSpec] = (),
        tool_choice: str | None = None,
    ) -> ModelReply:
        size = serialized_model_request_chars(
            messages,
            json_output=json_output,
            tools=tools,
            tool_choice=tool_choice,  # type: ignore[arg-type]
        )
        if size > self.limit:
            raise AssertionError(f"model received {size} chars above {self.limit}")
        self.messages.append([dict(message) for message in messages])
        if json_output:
            self.finalizer_saw_sentinel = "EARLY_SENTINEL" in str(messages[-1])
            return ModelReply(
                content=json.dumps(
                    {
                        "status": "plan_ready",
                        "research_contract": "Use recalled current information.",
                        "approval_card": "Review recalled current information.",
                        "guide_refs": [],
                    }
                )
            )
        last = messages[-1]
        call_id = str(last.get("tool_call_id", ""))
        if not call_id:
            return tool_call("search-1", "search", {"query": "q1", "intent": "current"})
        observation = json.loads(str(last["content"]))
        if call_id.startswith("search-"):
            if self.provider.search_calls < 8:
                next_index = self.provider.search_calls + 1
                return tool_call(
                    f"search-{next_index}",
                    "search",
                    {"query": f"q{next_index}", "intent": "current"},
                )
            self.early_search_was_compacted = not any(
                message.get("tool_call_id") == "search-1" for message in messages
            )
            return tool_call("trace", "inspect_presearch_trace", {"offset": 0})
        if call_id == "trace":
            candidate_id = observation["presearch_trace"][0]["candidate_ids"][0]
            return tool_call(
                "candidate",
                "inspect_presearch_candidate",
                {"candidate_id": candidate_id, "offset": 0},
            )
        if call_id == "candidate":
            candidate = observation["candidate"]
            self.recalled_snippet_only = (
                not candidate["content"] and "EARLY_SENTINEL" in candidate["snippet"]
            )
            recalled = candidate["content"] or candidate["snippet"]
            marker = recalled.split()[0]
            return tool_call(
                "finish",
                "finish_presearch",
                {"summary": f"Recalled provisional fact: {marker}."},
            )
        raise AssertionError(call_id)


class StatelessResearcherRecallModel:
    def __init__(self, limit: int, provider: RecallProvider) -> None:
        self.limit = limit
        self.provider = provider
        self.search_was_compacted = False

    async def complete(
        self,
        messages: Sequence[Mapping[str, Any]],
        *,
        json_output: bool = False,
        tools: Sequence[ToolSpec] = (),
        tool_choice: str | None = None,
    ) -> ModelReply:
        size = serialized_model_request_chars(
            messages,
            tools=tools,
            tool_choice=tool_choice,  # type: ignore[arg-type]
        )
        if size > self.limit:
            raise AssertionError(f"model received {size} chars above {self.limit}")
        last = messages[-1]
        call_id = str(last.get("tool_call_id", ""))
        if not call_id:
            return tool_call("search", "search", {"query": "primary", "intent": "fact"})
        observation = json.loads(str(last["content"]))
        if call_id == "search" or call_id.startswith("providers-"):
            if self.provider.describe_calls < 40:
                return tool_call(
                    f"providers-{self.provider.describe_calls}",
                    "inspect_providers",
                    {},
                )
            self.search_was_compacted = not any(
                message.get("tool_call_id") == "search" for message in messages
            )
            return tool_call("index", "inspect_candidates", {"offset": 0})
        if call_id == "index":
            candidate_id = observation["candidates"][0]["candidate_id"]
            return tool_call("save", "save_source", {"candidate_id": candidate_id})
        if call_id == "save":
            return tool_call("finish", "finish_turn", {"summary": "Recovered index."})
        raise AssertionError(call_id)


class InspectionModel:
    def __init__(self, limit: int, source_id: str) -> None:
        self.limit = limit
        self.source_id = source_id
        self.calls = 0
        self.observations: list[dict[str, Any]] = []

    async def complete(
        self,
        messages: Sequence[Mapping[str, Any]],
        *,
        json_output: bool = False,
        tools: Sequence[ToolSpec] = (),
        tool_choice: str | None = None,
    ) -> ModelReply:
        self.assert_bounded(messages, tools=tools, tool_choice=tool_choice)
        self.calls += 1
        if self.calls > 1:
            self.observations.append(json.loads(str(messages[-1]["content"])))
        if self.calls == 1:
            return tool_call("source", "inspect_source", {"source_id": self.source_id})
        if self.calls == 2:
            return tool_call("history", "inspect_research_history", {})
        if self.calls == 3:
            return tool_call(
                "history-entry",
                "inspect_research_history",
                {"entry_index": 0, "offset": 0},
            )
        if self.calls == 4:
            return tool_call("trace", "inspect_search_trace", {})
        if self.calls == 5:
            return tool_call(
                "trace-entry",
                "inspect_search_trace",
                {"entry_index": 0, "offset": 0},
            )
        return tool_call("finish", "finish_turn", {"summary": "Inspected."})

    def assert_bounded(
        self,
        messages: Sequence[Mapping[str, Any]],
        *,
        tools: Sequence[ToolSpec],
        tool_choice: str | None,
    ) -> None:
        size = serialized_model_request_chars(
            messages,
            tools=tools,
            tool_choice=tool_choice,  # type: ignore[arg-type]
        )
        if size > self.limit:
            raise AssertionError(f"model received {size} chars above {self.limit}")


class InvalidOffsetModel:
    def __init__(self) -> None:
        self.calls = 0
        self.candidate_id = ""
        self.error: dict[str, Any] = {}

    async def complete(
        self,
        messages: Sequence[Mapping[str, Any]],
        *,
        json_output: bool = False,
        tools: Sequence[ToolSpec] = (),
        tool_choice: str | None = None,
    ) -> ModelReply:
        self.calls += 1
        if self.calls == 1:
            return tool_call(
                "read", "read_source", {"url": "https://example.test/source"}
            )
        observation = json.loads(str(messages[-1]["content"]))
        if self.calls == 2:
            self.candidate_id = observation["candidate_id"]
            return tool_call(
                "bad-offset",
                "inspect_candidate",
                {"candidate_id": self.candidate_id, "offset": True},
            )
        self.error = observation
        return tool_call("finish", "finish_turn", {"summary": "Rejected offset."})


class NeverCalledModel:
    def __init__(self) -> None:
        self.called = False

    async def complete(
        self,
        messages: Sequence[Mapping[str, Any]],
        *,
        json_output: bool = False,
        tools: Sequence[ToolSpec] = (),
        tool_choice: str | None = None,
    ) -> ModelReply:
        self.called = True
        raise AssertionError("fixed oversized context must fail before model.complete")


def researcher_context(
    *,
    journal: tuple[JournalEntry, ...] = (),
    sources: Mapping[str, SourceDocument] | None = None,
    trace: tuple[str, ...] = (),
) -> ResearcherContext:
    return ResearcherContext(
        task=ResearchTask("capacity", "Research the focused question."),
        contract=ResearchContract("Use current primary sources.", approved=True),
        guide_text="Prefer direct and authoritative evidence.",
        branch_journal=journal,
        relevant_sources=sources or {},
        search_trace=trace,
    )


class ToolLoopCapacityTest(unittest.IsolatedAsyncioTestCase):
    async def test_missing_durable_body_page_fails_before_model_render(self) -> None:
        body = "body that is deliberately absent"
        ref = BodyRef.from_content(body)
        durable = durable_tool_observation(
            "inspect",
            {"candidate": {"content": body, "offset": 0}},
            (DurableBodyPage(("candidate", "content"), ref, 0),),
        )

        with self.assertRaisesRegex(ContentIntegrityError, "is missing"):
            await prepare_durable_tool_loop_messages(
                [
                    {"role": "system", "content": "system"},
                    {"role": "user", "content": "task"},
                    {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "inspect",
                                "type": "function",
                                "function": {
                                    "name": "inspect_candidate",
                                    "arguments": "{}",
                                },
                            }
                        ],
                    },
                    durable,
                ],
                InMemoryContentStore(),
                inspect_hint="inspect_candidate",
            )

    def test_compaction_drops_only_old_complete_interactions(self) -> None:
        messages = [
            {"role": "system", "content": "system"},
            {"role": "user", "content": "initial"},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "old",
                        "type": "function",
                        "function": {"name": "search", "arguments": "x" * 800},
                    }
                ],
            },
            {"role": "tool", "tool_call_id": "old", "content": "x" * 800},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "recent",
                        "type": "function",
                        "function": {"name": "inspect", "arguments": "{}"},
                    }
                ],
            },
            {"role": "tool", "tool_call_id": "recent", "content": "latest"},
        ]

        compacted = compact_tool_loop_messages(
            messages, max_payload_chars=900, inspect_hint="inspect_candidate"
        )

        serialized = json.dumps(compacted, ensure_ascii=False)
        self.assertLessEqual(serialized_messages_chars(compacted), 900)
        self.assertEqual(messages[:2], compacted[:2])
        self.assertNotIn('"old"', serialized)
        self.assertIn('"recent"', serialized)
        self.assertIn("inspect_candidate", serialized)

    def test_fixed_context_overflow_is_explicit(self) -> None:
        with self.assertRaisesRegex(MessageCapacityError, "fixed tool-loop context"):
            compact_tool_loop_messages(
                [
                    {"role": "system", "content": "s" * 1_000},
                    {"role": "user", "content": "u" * 1_000},
                ],
                max_payload_chars=100,
                inspect_hint="inspect",
            )

    async def test_planner_search_previews_and_history_stay_bounded(self) -> None:
        limit = 18_000
        model = CapacityPlannerModel(limit)
        planner = AgenticPlanner(
            model,
            TransparentSearchBroker([HugeSearchProvider()]),
            HugeReader("reader" * 20_000),
            content_store=InMemoryContentStore(),
            max_payload_chars=limit,
        )

        output = await planner(PlannerContext(question="Plan current research."))

        self.assertIsNotNone(output.contract)
        tool_observations = [
            json.loads(str(message["content"]))
            for call in model.messages
            for message in call
            if message.get("role") == "tool"
            and message.get("tool_call_id", "").startswith("search-")
        ]
        self.assertTrue(tool_observations)
        first = tool_observations[0]["results"][0]
        self.assertLess(len(first["content"]), 12_000)
        self.assertTrue(first["content_truncated"])
        self.assertEqual("inspect_presearch_candidate", first["recheck"]["tool"])
        self.assertTrue(
            any(
                "Earlier complete tool interactions were omitted"
                in str(message.get("content", ""))
                for call in model.messages
                for message in call
            )
        )

    async def test_planner_recalls_early_presearch_after_compaction(self) -> None:
        limit = 18_000
        provider = RecallProvider(snippet_only_first=True)
        model = StatelessPlannerRecallModel(limit, provider)

        output = await AgenticPlanner(
            model,
            TransparentSearchBroker([provider]),
            HugeReader("unused"),
            content_store=InMemoryContentStore(),
            max_payload_chars=limit,
        )(PlannerContext(question="Plan with current facts."))

        self.assertIsNotNone(output.contract)
        self.assertTrue(model.finalizer_saw_sentinel)
        self.assertTrue(model.early_search_was_compacted)
        self.assertTrue(model.recalled_snippet_only)
        self.assertTrue(
            any(
                "Earlier complete tool interactions were omitted"
                in str(message.get("content", ""))
                for call in model.messages
                for message in call
            )
        )

    async def test_researcher_pages_huge_candidate_but_saves_full_content(self) -> None:
        limit = 12_000
        sentinel = "FULL_BODY_ONLY_SENTINEL"
        content = "0123456789" * 5_000 + sentinel
        model = CandidatePagingModel(limit)
        content_store = InMemoryContentStore()
        researcher = ControlledResearcher(
            model,
            TransparentSearchBroker([]),
            HugeReader(content),
            content_store=content_store,
            max_payload_chars=limit,
        )

        graph = researcher.as_subgraph(
            content_store=content_store,
            checkpointer=memory_checkpointer(),
        )
        state = await graph.ainvoke(
            researcher_subgraph_input(researcher_context()),
            {"configurable": {"thread_id": "content-ref-capacity"}},
        )
        output = researcher_output_from_subgraph(state)

        source = next(iter(output.sources.values()))
        stored_content = await content_store.get(source.body_ref)
        self.assertEqual(len(content), len(stored_content))
        self.assertEqual(content, stored_content)
        serialized_state = json.dumps(
            state,
            ensure_ascii=False,
            default=lambda value: (
                asdict(value)
                if is_dataclass(value)
                else (_ for _ in ()).throw(TypeError(type(value).__name__))
            ),
        )
        self.assertNotIn(sentinel, serialized_state)
        checkpoint_candidate = next(iter(state["candidates"].values()))
        self.assertNotIn("content", checkpoint_candidate)

        candidate = researcher_runtime._candidate_from_value(
            checkpoint_candidate
        )
        chunks: list[str] = []
        offset = 0
        while True:
            result = await researcher._execute(
                ModelToolCall(
                    "page",
                    "inspect_candidate",
                    json.dumps(
                        {
                            "candidate_id": candidate.candidate_id,
                            "offset": offset,
                        }
                    ),
                ),
                context=researcher_context(),
                candidates={candidate.candidate_id: candidate},
                saved=dict(output.sources),
                journal=[],
                search_trace=[],
                content_store=content_store,
            )
            page = result["candidate"]
            chunks.append(page["content"])
            if page["next_offset"] is None:
                break
            offset = page["next_offset"]
        self.assertGreater(len(chunks), 1)
        self.assertEqual(content, "".join(chunks))
        self.assertTrue(
            any(
                "Earlier complete tool interactions were omitted"
                in str(message.get("content", ""))
                for call in model.messages
                for message in call
            )
        )
        first_read = json.loads(str(model.messages[1][-1]["content"]))
        self.assertTrue(first_read["content_truncated"])
        self.assertEqual("inspect_candidate", first_read["recheck"]["tool"])

    async def test_researcher_can_rediscover_compacted_candidate_id(self) -> None:
        limit = 14_000
        provider = RecallProvider()
        model = StatelessResearcherRecallModel(limit, provider)
        content_store = InMemoryContentStore()

        output = await ControlledResearcher(
            model,
            TransparentSearchBroker([provider]),
            HugeReader("unused"),
            content_store=content_store,
            max_payload_chars=limit,
        )(researcher_context())

        source = next(iter(output.sources.values()))
        self.assertIn("EARLY_SENTINEL", await content_store.get(source.body_ref))
        self.assertTrue(model.search_was_compacted)

    async def test_source_history_and_trace_inspection_are_bounded(self) -> None:
        limit = 12_000
        content_store = InMemoryContentStore()
        source = SourceDocument.create(
            title="Existing source",
            url="https://example.test/existing",
            body_ref=await content_store.put("source" * 20_000),
        )
        journal = tuple(
            JournalEntry(
                "next_step",
                f"entry-{index}-" + '"\\\n' * 7_000,
                branch_id="capacity",
            )
            for index in range(3)
        )
        trace = tuple(
            f"trace-{index}-" + '"\\\n' * 4_000 for index in range(4)
        )
        model = InspectionModel(limit, source.source_id)

        await ControlledResearcher(
            model,
            TransparentSearchBroker([]),
            HugeReader("unused"),
            content_store=content_store,
            max_payload_chars=limit,
        )(
            researcher_context(
                journal=journal,
                sources={source.source_id: source},
                trace=trace,
            )
        )

        (
            source_page,
            history_index,
            history_page,
            trace_index,
            trace_page,
        ) = model.observations[:5]
        self.assertTrue(source_page["source"]["content_truncated"])
        self.assertIsNotNone(source_page["source"]["next_offset"])
        history_metadata = history_index["research_history"][0]
        self.assertEqual(0, history_metadata["entry_index"])
        self.assertLess(len(history_metadata["preview"]), 20_000)
        self.assertEqual(1, history_index["next_offset"])
        self.assertTrue(
            history_page["research_history_entry"]["content_truncated"]
        )
        self.assertIsNotNone(
            history_page["research_history_entry"]["next_offset"]
        )
        trace_metadata = trace_index["search_trace"][0]
        self.assertEqual(0, trace_metadata["entry_index"])
        self.assertLess(len(trace_metadata["preview"]), 10_000)
        self.assertIsNotNone(trace_index["next_offset"])
        self.assertTrue(trace_page["search_trace_entry"]["content_truncated"])
        self.assertIsNotNone(trace_page["search_trace_entry"]["next_offset"])

    async def test_paging_arguments_are_checked_at_runtime(self) -> None:
        model = InvalidOffsetModel()

        await ControlledResearcher(
            model,
            TransparentSearchBroker([]),
            HugeReader("short source"),
            content_store=InMemoryContentStore(),
        )(researcher_context())

        self.assertFalse(model.error["ok"])
        self.assertEqual("invalid_arguments", model.error["error"]["type"])

    async def test_oversized_initial_planner_context_never_reaches_model(self) -> None:
        model = NeverCalledModel()
        planner = AgenticPlanner(
            model,
            TransparentSearchBroker([]),
            HugeReader("unused"),
            content_store=InMemoryContentStore(),
            max_payload_chars=1_000,
        )

        with self.assertRaisesRegex(PlannerRuntimeError, "fixed tool-loop context"):
            await planner(PlannerContext(question="q" * 20_000))
        self.assertFalse(model.called)

    async def test_oversized_finalizer_context_never_reaches_model(self) -> None:
        class OversizedSubgraph:
            async def ainvoke(self, value: object, config: object):
                return {
                    "presearch_note": "summary-" + "s" * 8_000,
                    "inspected_guides": {"large@1.0.0": "g" * 8_000},
                }

        model = NeverCalledModel()
        planner = AgenticPlanner(
            model,
            TransparentSearchBroker([]),
            HugeReader("unused"),
            content_store=InMemoryContentStore(),
            max_payload_chars=4_000,
        )

        with self.assertRaisesRegex(PlannerRuntimeError, "finalizer context"):
            await planner.run_with_subgraph(
                PlannerContext(question="small"), OversizedSubgraph(), None
            )
        self.assertFalse(model.called)


if __name__ == "__main__":
    unittest.main()
