from __future__ import annotations

import json
import unittest
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from typing import Any, TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

import deep_research_agent.researcher as researcher_runtime
from deep_research_agent.checkpoint import memory_checkpointer
from deep_research_agent.content_store import (
    InMemoryContentStore,
    hydrate_source,
)
from deep_research_agent.model import ModelReply, ModelToolCall, ToolSpec
from deep_research_agent.researcher import (
    RESEARCHER_TOOL_SPECS,
    ControlledResearcher,
    ResearcherRuntimeError,
    build_researcher_subgraph,
    researcher_output_from_subgraph,
    researcher_subgraph_input,
)
from deep_research_agent.roles import (
    ResearcherContext,
    ResearcherOutput,
    RoleContractError,
    validate_researcher_output,
)
from deep_research_agent.state import (
    BodyRef,
    BranchHandoff,
    JournalEntry,
    ResearchContract,
    ResearchTask,
    SourceDocument,
    locate_quote,
    merge_source_corpus,
)
from deep_research_agent.tools import (
    ProviderInfo,
    ProviderResult,
    ReadResult,
    SearchResult,
    TransparentSearchBroker,
)


def tool_call(call_id: str, name: str, arguments: Mapping[str, Any]) -> ModelReply:
    return ModelReply(
        tool_calls=(
            ModelToolCall(call_id, name, json.dumps(arguments, ensure_ascii=False)),
        )
    )


class FakeProvider:
    provider_id = "mock-search"

    def __init__(self) -> None:
        self.search_calls = 0
        self.requests: list[tuple[str, str, str]] = []

    async def describe(self) -> ProviderInfo:
        return ProviderInfo(self.provider_id, ("search", "raw_content"))

    async def search(self, *, query: str, intent: str, source_kind: str):
        self.search_calls += 1
        self.requests.append((query, intent, source_kind))
        return (
            ProviderResult(
                title="Official evidence",
                url="https://evidence.example/report",
                snippet="summary only",
                content="The measured value was 42 in 2026.",
            ),
        )


class FakeReader:
    def __init__(self) -> None:
        self.urls: list[str] = []

    async def read(self, url: str) -> ReadResult:
        self.urls.append(url)
        return ReadResult("Read title", url, "Full text acquired by the reader.")


class StatefulModel:
    def __init__(self, mode: str) -> None:
        self.mode = mode
        self.calls = 0
        self.messages: list[list[Mapping[str, Any]]] = []
        self.tool_sets: list[tuple[ToolSpec, ...]] = []

    async def complete(
        self,
        messages: Sequence[Mapping[str, Any]],
        *,
        json_output: bool = False,
        tools: Sequence[ToolSpec] = (),
        tool_choice: str | None = None,
    ) -> ModelReply:
        self.calls += 1
        self.messages.append([dict(item) for item in messages])
        self.tool_sets.append(tuple(tools))
        if self.mode == "full":
            return self._full(messages)
        if self.mode == "read":
            return self._read(messages)
        if self.mode == "untrusted":
            if self.calls == 1:
                return tool_call("bad-save", "save_source", {"candidate_id": "fake"})
            return tool_call("finish", "finish_turn", {"summary": "No source saved."})
        if self.mode == "extra":
            if self.calls == 1:
                return tool_call(
                    "bad-search",
                    "search",
                    {"query": "q", "intent": "discover", "unexpected": "x"},
                )
            return tool_call("finish", "finish_turn", {"summary": "Rejected."})
        if self.mode == "unanchored":
            if self.calls == 1:
                return tool_call(
                    "journal",
                    "journal",
                    {"kind": "finding", "content": "Unsupported external fact."},
                )
            return tool_call(
                "finish", "finish_turn", {"summary": "Unsupported note rejected."}
            )
        raise AssertionError(self.mode)

    def _full(self, messages: Sequence[Mapping[str, Any]]) -> ModelReply:
        if self.calls == 1:
            return tool_call(
                "search-1",
                "search",
                {"query": "official 2026", "intent": "fact", "source_kind": "web"},
            )
        result = json.loads(str(messages[-1]["content"]))
        if self.calls == 2:
            candidate_id = result["results"][0]["candidate_id"]
            return tool_call(
                "save-1", "save_source", {"candidate_id": candidate_id}
            )
        if self.calls == 3:
            return tool_call(
                "journal-1",
                "journal",
                {
                    "kind": "finding",
                    "content": "The source reports a value of 42.",
                    "anchors": [
                        {
                            "source_id": result["source_id"],
                            "exact_quote": "value was 42",
                        }
                    ],
                },
            )
        return tool_call(
            "finish",
            "finish_turn",
            {
                "summary": "Saved and journaled the directly relevant source.",
                "unresolved": ["Independent corroboration remains useful."],
            },
        )

    def _read(self, messages: Sequence[Mapping[str, Any]]) -> ModelReply:
        if self.calls == 1:
            return tool_call(
                "read-1", "read_source", {"url": "https://reader.example/paper"}
            )
        result = json.loads(str(messages[-1]["content"]))
        if self.calls == 2:
            return tool_call(
                "save-1",
                "save_source",
                {"candidate_id": result["candidate_id"]},
            )
        return tool_call("finish", "finish_turn", {"summary": "Reader source saved."})


def context() -> ResearcherContext:
    return ResearcherContext(
        task=ResearchTask("branch-a", "Find the primary measurement."),
        contract=ResearchContract("Answer from current primary sources.", approved=True),
        guide_text="Prefer direct official evidence.",
        branch_journal=(),
        relevant_sources={},
    )


class ControlledResearcherTest(unittest.IsolatedAsyncioTestCase):
    def test_checkpoint_candidate_identity_covers_content_provenance(self) -> None:
        candidate = researcher_runtime._candidate_from_search(
            SearchResult(
                title="Source",
                url="https://example.test/source",
                content="complete body",
                provider_ids=("discoverer",),
                content_provider_ids=("content-provider",),
            ),
            BodyRef.from_content("complete body"),
        )
        checkpoint_value = researcher_runtime._candidate_value(candidate)
        checkpoint_value["content_provider_ids"] = ["tampered-provider"]

        with self.assertRaisesRegex(
            ResearcherRuntimeError, "identity is inconsistent"
        ):
            researcher_runtime._candidate_from_value(checkpoint_value)

    def test_shared_output_contract_rejects_unanchored_external_finding(self) -> None:
        task = ResearchTask("branch-a", "Investigate the assigned question.")
        output = ResearcherOutput(
            sources={},
            journal=(
                JournalEntry(
                    "finding", "Unsupported external claim.", branch_id="branch-a"
                ),
            ),
            handoff=BranchHandoff("branch-a", "Finished."),
        )

        with self.assertRaisesRegex(RoleContractError, "SourceAnchor"):
            validate_researcher_output(output, task, {})

    async def test_search_content_can_be_saved_journaled_and_handed_off(self) -> None:
        provider = FakeProvider()
        model = StatefulModel("full")
        content_store = InMemoryContentStore()
        researcher = ControlledResearcher(
            model,
            TransparentSearchBroker([provider]),
            FakeReader(),
            content_store=content_store,
        )

        output = await researcher(context())

        self.assertEqual(1, len(output.sources))
        source = next(iter(output.sources.values()))
        self.assertEqual(
            "The measured value was 42 in 2026.",
            await content_store.get(source.body_ref),
        )
        self.assertEqual("search", source.metadata["acquired_via"])
        self.assertEqual("mock-search", source.metadata["discovered_by"])
        self.assertEqual("mock-search", source.metadata["content_from"])
        self.assertNotIn("search_providers", source.metadata)
        search_observation = json.loads(str(model.messages[1][-1]["content"]))
        self.assertEqual(
            ["mock-search"], search_observation["results"][0]["provider_ids"]
        )
        self.assertEqual(
            ["mock-search"],
            search_observation["results"][0]["content_provider_ids"],
        )
        self.assertEqual("branch-a", output.journal[0].branch_id)
        self.assertEqual("value was 42", output.journal[0].anchors[0].exact_quote)
        self.assertEqual("branch-a", output.handoff.branch_id)
        self.assertEqual(1, provider.search_calls)
        self.assertEqual([("official 2026", "fact", "web")], provider.requests)
        self.assertTrue(
            all(
                tuple(spec.name for spec in specs)
                == (
                    "inspect_providers",
                    "inspect_candidates",
                    "inspect_source",
                    "inspect_candidate",
                    "inspect_search_trace",
                    "inspect_research_history",
                    "search",
                    "read_source",
                    "save_source",
                    "journal",
                    "finish_turn",
                )
                for specs in model.tool_sets
            )
        )

    async def test_reader_result_enters_same_private_candidate_registry(self) -> None:
        reader = FakeReader()
        content_store = InMemoryContentStore()
        output = await ControlledResearcher(
            StatefulModel("read"),
            TransparentSearchBroker([]),
            reader,
            content_store=content_store,
        )(context())

        self.assertEqual(["https://reader.example/paper"], reader.urls)
        self.assertEqual(1, len(output.sources))
        source = next(iter(output.sources.values()))
        self.assertEqual("reader", source.metadata["acquired_via"])
        self.assertNotIn("discovered_by", source.metadata)
        self.assertNotIn("content_from", source.metadata)

    async def test_parallel_duplicate_saves_union_provenance_idempotently(
        self,
    ) -> None:
        alpha = FakeProvider()
        alpha.provider_id = "alpha"
        beta = FakeProvider()
        beta.provider_id = "beta"
        first = await ControlledResearcher(
            StatefulModel("full"),
            TransparentSearchBroker([alpha]),
            FakeReader(),
            content_store=InMemoryContentStore(),
        )(context())
        second = await ControlledResearcher(
            StatefulModel("full"),
            TransparentSearchBroker([beta]),
            FakeReader(),
            content_store=InMemoryContentStore(),
        )(context())

        merged = merge_source_corpus(first.sources, second.sources)
        repeated = merge_source_corpus(merged, first.sources)
        source = next(iter(merged.values()))

        self.assertEqual(merged, repeated)
        self.assertEqual("alpha | beta", source.metadata["discovered_by"])
        self.assertEqual("alpha | beta", source.metadata["content_from"])

    async def test_model_cannot_save_a_candidate_it_did_not_acquire(self) -> None:
        model = StatefulModel("untrusted")
        output = await ControlledResearcher(
            model,
            TransparentSearchBroker([]),
            FakeReader(),
            content_store=InMemoryContentStore(),
        )(context())

        self.assertEqual({}, output.sources)
        tool_error = json.loads(str(model.messages[1][-1]["content"]))
        self.assertFalse(tool_error["ok"])
        self.assertEqual(
            "unknown_candidate_or_source", tool_error["error"]["type"]
        )

    async def test_extra_arguments_are_rejected_before_search_execution(self) -> None:
        provider = FakeProvider()
        model = StatefulModel("extra")
        output = await ControlledResearcher(
            model,
            TransparentSearchBroker([provider]),
            FakeReader(),
            content_store=InMemoryContentStore(),
        )(context())

        self.assertEqual("Rejected.", output.handoff.summary)
        self.assertEqual(0, provider.search_calls)
        tool_error = json.loads(str(model.messages[1][-1]["content"]))
        self.assertEqual("invalid_arguments", tool_error["error"]["type"])

    async def test_external_findings_require_a_saved_source_anchor(self) -> None:
        model = StatefulModel("unanchored")

        output = await ControlledResearcher(
            model,
            TransparentSearchBroker([]),
            FakeReader(),
            content_store=InMemoryContentStore(),
        )(context())

        self.assertEqual((), output.journal)
        tool_error = json.loads(str(model.messages[1][-1]["content"]))
        self.assertEqual("invalid_arguments", tool_error["error"]["type"])

    async def test_task_relevant_source_is_available_on_demand(self) -> None:
        content_store = InMemoryContentStore()
        body = "Private surrounding text. Exact prior evidence."
        source = SourceDocument.create(
            title="Existing source",
            url="https://existing.example/source",
            body_ref=await content_store.put(body),
        )
        hydrated = await hydrate_source(source, content_store)
        entry = JournalEntry(
            "finding",
            "Prior branch finding.",
            anchors=(locate_quote(hydrated, "Exact prior evidence."),),
            branch_id="branch-a",
        )

        class InspectModel:
            def __init__(self) -> None:
                self.calls = 0
                self.messages: list[list[Mapping[str, Any]]] = []

            async def complete(
                self,
                messages: Sequence[Mapping[str, Any]],
                *,
                json_output: bool = False,
                tools: Sequence[ToolSpec] = (),
                tool_choice: str | None = None,
            ) -> ModelReply:
                self.calls += 1
                self.messages.append([dict(item) for item in messages])
                if self.calls == 1:
                    return tool_call(
                        "source", "inspect_source", {"source_id": source.source_id}
                    )
                if self.calls == 2:
                    return tool_call("history", "inspect_research_history", {})
                if self.calls == 3:
                    return tool_call("providers", "inspect_providers", {})
                if self.calls == 4:
                    return tool_call("trace", "inspect_search_trace", {})
                return tool_call(
                    "finish", "finish_turn", {"summary": "Prior source inspected."}
                )

        model = InspectModel()
        focused_context = ResearcherContext(
            task=ResearchTask("branch-a", "Continue the prior branch."),
            contract=ResearchContract("Use relevant prior evidence.", approved=True),
            guide_text="",
            branch_journal=(entry,),
            relevant_sources={source.source_id: source},
        )

        output = await ControlledResearcher(
            model,
            TransparentSearchBroker([]),
            FakeReader(),
            content_store=content_store,
        )(focused_context)

        initial_context = str(model.messages[0][-1]["content"])
        inspected = json.loads(str(model.messages[1][-1]["content"]))
        history = json.loads(str(model.messages[2][-1]["content"]))
        self.assertNotIn("Private surrounding text", initial_context)
        self.assertEqual(body, inspected["source"]["content"])
        self.assertEqual(
            "Prior branch finding.", history["research_history"][0]["preview"]
        )
        self.assertEqual("Prior source inspected.", output.handoff.summary)

    async def test_trace_and_complete_journal_entry_are_losslessly_pageable(
        self,
    ) -> None:
        exact_quote = "ANCHOR_START|" + "q" * 9_000 + "|ANCHOR_END"
        content_store = InMemoryContentStore()
        source = SourceDocument.create(
            title="Long anchored source",
            url="https://example.test/long-anchor",
            body_ref=await content_store.put(
                "prefix\n" + exact_quote + "\nsuffix"
            ),
        )
        hydrated = await hydrate_source(source, content_store)
        early_entry = JournalEntry(
            "finding",
            "EARLY_CONTENT|" + "j" * 25_000 + "|CONTENT_END",
            anchors=(locate_quote(hydrated, exact_quote),),
            branch_id="branch-a",
        )
        focused_context = ResearcherContext(
            task=ResearchTask("branch-a", "Recover exact prior records."),
            contract=ResearchContract("Use the exact prior record.", approved=True),
            guide_text="",
            branch_journal=(
                early_entry,
                JournalEntry("next_step", "Later entry.", branch_id="branch-a"),
            ),
            relevant_sources={source.source_id: source},
            search_trace=(
                "EARLY_TRACE|" + "t" * 30_000 + "|TRACE_END",
                "Later trace.",
            ),
        )
        researcher = ControlledResearcher(
            StatefulModel("untrusted"),
            TransparentSearchBroker([]),
            FakeReader(),
            content_store=content_store,
            max_payload_chars=12_000,
        )

        async def inspect(
            name: str, arguments: Mapping[str, Any]
        ) -> Mapping[str, Any]:
            result = await researcher._execute(
                ModelToolCall(
                    "inspect", name, json.dumps(arguments, ensure_ascii=False)
                ),
                context=focused_context,
                candidates={},
                saved={},
                journal=[],
                search_trace=list(focused_context.search_trace),
                content_store=content_store,
            )
            self.assertIsInstance(result, Mapping)
            return result  # type: ignore[return-value]

        trace_index = await inspect("inspect_search_trace", {})
        trace_metadata = trace_index["search_trace"][0]
        self.assertEqual(
            {"entry_index", "preview", "total_chars"}, set(trace_metadata)
        )
        self.assertEqual(0, trace_metadata["entry_index"])
        self.assertEqual(
            len(focused_context.search_trace[0]), trace_metadata["total_chars"]
        )

        history_index = await inspect("inspect_research_history", {})
        history_metadata = history_index["research_history"][0]
        self.assertEqual(
            {"entry_index", "metadata", "preview", "total_chars"},
            set(history_metadata),
        )
        self.assertEqual(0, history_metadata["entry_index"])
        self.assertEqual(1, history_metadata["metadata"]["anchor_count"])

        trace_chunks: list[str] = []
        offset = 0
        while True:
            result = await inspect(
                "inspect_search_trace", {"entry_index": 0, "offset": offset}
            )
            page = result["search_trace_entry"]
            self.assertEqual(offset, page["offset"])
            trace_chunks.append(page["content"])
            if page["next_offset"] is None:
                break
            offset = page["next_offset"]
        self.assertGreater(len(trace_chunks), 1)
        self.assertEqual(focused_context.search_trace[0], "".join(trace_chunks))

        history_chunks: list[str] = []
        offset = 0
        while True:
            result = await inspect(
                "inspect_research_history", {"entry_index": 0, "offset": offset}
            )
            page = result["research_history_entry"]
            self.assertEqual("json", page["encoding"])
            self.assertEqual(offset, page["offset"])
            history_chunks.append(page["content"])
            if page["next_offset"] is None:
                break
            offset = page["next_offset"]
        serialized_entry = "".join(history_chunks)
        expected_entry = json.dumps(
            asdict(early_entry),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        self.assertGreater(len(history_chunks), 1)
        self.assertEqual(expected_entry, serialized_entry)
        recovered_entry = json.loads(serialized_entry)
        self.assertEqual(exact_quote, recovered_entry["anchors"][0]["exact_quote"])
        self.assertEqual(asdict(early_entry.anchors[0].locator), recovered_entry["anchors"][0]["locator"])

    async def test_compiled_subgraph_checkpoints_model_and_tool_turns(self) -> None:
        content_store = InMemoryContentStore()
        graph = build_researcher_subgraph(
            StatefulModel("full"),
            TransparentSearchBroker([FakeProvider()]),
            FakeReader(),
            content_store=content_store,
            checkpointer=memory_checkpointer(),
        )
        config = {"configurable": {"thread_id": "researcher-checkpoints"}}

        state = await graph.ainvoke(researcher_subgraph_input(context()), config)
        output = researcher_output_from_subgraph(state)
        snapshots = [snapshot async for snapshot in graph.aget_state_history(config)]

        self.assertEqual(1, len(output.sources))
        checkpoint_candidate = next(iter(state["candidates"].values()))
        self.assertEqual(["mock-search"], checkpoint_candidate["provider_ids"])
        self.assertEqual(
            ["mock-search"], checkpoint_candidate["content_provider_ids"]
        )
        self.assertNotIn("content", checkpoint_candidate)
        self.assertEqual(
            len("The measured value was 42 in 2026."),
            checkpoint_candidate["body_ref"]["char_count"],
        )
        self.assertGreaterEqual(len(snapshots), 8)
        observed_nodes = {
            task.name for snapshot in snapshots for task in snapshot.tasks
        }
        self.assertTrue({"model", "tools"}.issubset(observed_nodes))

    async def test_parent_graph_inherits_child_tool_checkpoints(self) -> None:
        class ParentState(TypedDict, total=False):
            question: str
            summary: str

        saver = memory_checkpointer()
        content_store = InMemoryContentStore()
        child = build_researcher_subgraph(
            StatefulModel("full"),
            TransparentSearchBroker([FakeProvider()]),
            FakeReader(),
            content_store=content_store,
        )

        async def researcher_node(
            state: ParentState, config: RunnableConfig
        ) -> ParentState:
            child_state = await child.ainvoke(
                researcher_subgraph_input(context()), config
            )
            output = researcher_output_from_subgraph(child_state)
            return {"summary": output.handoff.summary}

        parent_builder = StateGraph(ParentState)
        parent_builder.add_node("researcher", researcher_node)
        parent_builder.add_edge(START, "researcher")
        parent_builder.add_edge("researcher", END)
        parent = parent_builder.compile(checkpointer=saver)
        config = {"configurable": {"thread_id": "parent-child-checkpoints"}}

        result = await parent.ainvoke({"question": "test"}, config)
        checkpoints = [item async for item in saver.alist(None)]
        namespaces = {
            str(item.config.get("configurable", {}).get("checkpoint_ns", ""))
            for item in checkpoints
        }

        self.assertIn("Saved and journaled", result["summary"])
        self.assertTrue(any(namespace for namespace in namespaces), namespaces)

    async def test_safety_limit_is_an_error_not_research_completion(self) -> None:
        class LoopingModel:
            async def complete(
                self,
                messages: Sequence[Mapping[str, Any]],
                *,
                json_output: bool = False,
                tools: Sequence[ToolSpec] = (),
                tool_choice: str | None = None,
            ) -> ModelReply:
                return ModelReply(content="continue")

        researcher = ControlledResearcher(
            LoopingModel(),
            TransparentSearchBroker([]),
            FakeReader(),
            content_store=InMemoryContentStore(),
            runtime_turn_limit=2,
        )

        with self.assertRaisesRegex(
            ResearcherRuntimeError, "research completion was not inferred"
        ):
            await researcher(context())

    def test_every_declared_schema_rejects_additional_properties(self) -> None:
        self.assertEqual(
            {
                "inspect_providers",
                "inspect_candidates",
                "inspect_source",
                "inspect_candidate",
                "inspect_search_trace",
                "inspect_research_history",
                "search",
                "read_source",
                "save_source",
                "journal",
                "finish_turn",
            },
            {spec.name for spec in RESEARCHER_TOOL_SPECS},
        )
        for spec in RESEARCHER_TOOL_SPECS:
            self.assertFalse(spec.parameters["additionalProperties"])
        inspection_schemas = {
            spec.name: spec.parameters
            for spec in RESEARCHER_TOOL_SPECS
            if spec.name
            in {"inspect_search_trace", "inspect_research_history"}
        }
        for schema in inspection_schemas.values():
            self.assertEqual(
                {"offset", "entry_index"}, set(schema["properties"])
            )
        journal = next(
            spec for spec in RESEARCHER_TOOL_SPECS if spec.name == "journal"
        )
        anchor_schema = journal.parameters["properties"]["anchors"]["items"]
        self.assertFalse(anchor_schema["additionalProperties"])
        search = next(
            spec for spec in RESEARCHER_TOOL_SPECS if spec.name == "search"
        )
        self.assertEqual(
            ["web", "news"],
            search.parameters["properties"]["source_kind"]["enum"],
        )


if __name__ == "__main__":
    unittest.main()
