from __future__ import annotations

import unittest
from collections.abc import Mapping, Sequence
from pathlib import Path
from tempfile import TemporaryDirectory

from deep_research_agent.guides import GuideCatalog, GuideFormatError
from deep_research_agent.llm_roles import (
    CuratorExecutor,
    EditorExecutor,
    SupervisorExecutor,
    SynthesizerExecutor,
    ValidatorExecutor,
    WriterExecutor,
)
from deep_research_agent.model import ModelReply, ToolSpec
from deep_research_agent.planner import AgenticPlanner
from deep_research_agent.researcher import ControlledResearcher
from deep_research_agent.runtime import (
    DEFAULT_PLANNER_TURN_LIMIT,
    DEFAULT_RESEARCHER_TURN_LIMIT,
    build_environment_runtime,
    build_role_executors,
    builtin_guide_root,
)
from deep_research_agent.tools import ReadResult, TransparentSearchBroker


class NeverCalledModel:
    async def complete(
        self,
        messages: Sequence[Mapping[str, object]],
        *,
        json_output: bool = False,
        tools: Sequence[ToolSpec] = (),
        tool_choice: str | None = None,
    ) -> ModelReply:
        raise AssertionError("composition must not invoke a model")


class NeverCalledReader:
    async def read(self, url: str) -> ReadResult:
        raise AssertionError("composition must not read a source")


class RuntimeCompositionTest(unittest.TestCase):
    def test_only_planner_and_researcher_receive_external_tools(self) -> None:
        catalog = GuideCatalog()
        roles = build_role_executors(
            NeverCalledModel(),
            TransparentSearchBroker([]),
            NeverCalledReader(),
            guide_catalog=catalog,
        )

        self.assertIsInstance(roles.planner, AgenticPlanner)
        self.assertIsInstance(roles.researcher, ControlledResearcher)
        self.assertIs(roles.planner.guide_catalog, catalog)
        self.assertIsNone(DEFAULT_PLANNER_TURN_LIMIT)
        self.assertIsNone(DEFAULT_RESEARCHER_TURN_LIMIT)
        self.assertIsNone(roles.planner.runtime_turn_limit)
        self.assertIsNone(roles.researcher.runtime_turn_limit)
        self.assertIsInstance(roles.supervisor, SupervisorExecutor)
        self.assertIsInstance(roles.curator, CuratorExecutor)
        self.assertIsInstance(roles.synthesizer, SynthesizerExecutor)
        self.assertIsInstance(roles.writer, WriterExecutor)
        self.assertIsInstance(roles.editor, EditorExecutor)
        first = roles.validator_factory()
        second = roles.validator_factory()
        self.assertIsInstance(first, ValidatorExecutor)
        self.assertIsInstance(second, ValidatorExecutor)
        self.assertIsNot(first, second)

        custom = build_role_executors(
            NeverCalledModel(),
            TransparentSearchBroker([]),
            NeverCalledReader(),
            planner_turn_limit=12,
            researcher_turn_limit=34,
            role_max_payload_chars=12_345,
        )
        self.assertEqual(12, custom.planner.runtime_turn_limit)
        self.assertEqual(34, custom.researcher.runtime_turn_limit)
        self.assertEqual(12_345, custom.planner.max_payload_chars)
        self.assertEqual(12_345, custom.researcher.max_payload_chars)

    def test_builtin_guide_root_is_available_without_current_directory_rules(self) -> None:
        catalog = GuideCatalog.discover(builtin_guide_root())

        self.assertGreaterEqual(len(catalog), 2)

    def test_environment_loads_guides_before_composing_external_runtime(self) -> None:
        with TemporaryDirectory() as directory:
            guide = Path(directory) / "broken" / "GUIDE.md"
            guide.parent.mkdir()
            guide.write_text("not valid guide front matter", encoding="utf-8")

            with self.assertRaises(GuideFormatError):
                build_environment_runtime(
                    guide_root=directory,
                    model=NeverCalledModel(),
                    reader=NeverCalledReader(),
                )


if __name__ == "__main__":
    unittest.main()
