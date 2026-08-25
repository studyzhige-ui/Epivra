"""Protocol and adapter tests for the local MCP product entry."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

from mcp import Client, StdioServerParameters

from deep_research_agent.mcp_server import McpAdapter, build_server
from deep_research_agent.service import Event, Task


class _FakeAdapter:
    """Protocol fixture: behaviour stays mocked, MCP serialization stays real."""

    def __init__(self) -> None:
        self.started: tuple[str, str] | None = None

    async def list(self) -> list[dict[str, Any]]:
        return [{"task_id": "t_one", "state": "awaiting_approval"}]

    async def start(
        self, task_id: str, plan_id: str, *, listen  # noqa: ANN001
    ) -> dict[str, Any]:
        self.started = (task_id, plan_id)
        listen(Event("wave_started", "正在检索公开来源"))
        return {
            "task_id": task_id,
            "state": "published",
            "plan": {"plan_id": plan_id, "version": 1},
        }


class McpProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def test_tool_surface_and_annotations_are_explicit(self) -> None:
        server = build_server(_FakeAdapter())  # type: ignore[arg-type]
        async with Client(server, raise_exceptions=True) as client:
            result = await client.list_tools()

        tools = {tool.name: tool for tool in result.tools}
        self.assertEqual(
            {
                "adjust_research_direction",
                "answer_research_clarification",
                "continue_research",
                "create_research",
                "delete_research",
                "get_research",
                "get_research_report",
                "list_research",
                "retry_research_planning",
                "start_research",
            },
            set(tools),
        )
        self.assertTrue(tools["get_research"].annotations.read_only_hint)
        self.assertTrue(tools["list_research"].annotations.read_only_hint)
        self.assertTrue(tools["get_research_report"].annotations.read_only_hint)
        self.assertTrue(tools["delete_research"].annotations.destructive_hint)
        self.assertFalse(tools["start_research"].annotations.read_only_hint)
        self.assertNotIn("ctx", tools["start_research"].input_schema["properties"])
        self.assertEqual(
            ["task_id", "plan_id"],
            tools["start_research"].input_schema["required"],
        )

    async def test_calls_return_structured_output_and_preserve_exact_plan(self) -> None:
        adapter = _FakeAdapter()
        server = build_server(adapter)  # type: ignore[arg-type]
        progress: list[Any] = []

        async def record_progress(
            current: float, total: float | None, message: str | None
        ) -> None:
            progress.append((current, total, message))

        async with Client(server, raise_exceptions=True) as client:
            listed = await client.call_tool("list_research", {})
            started = await client.call_tool(
                "start_research",
                {"task_id": "t_one", "plan_id": "plan_exact"},
                progress_callback=record_progress,
            )

        self.assertFalse(listed.is_error)
        self.assertEqual(
            [{"task_id": "t_one", "state": "awaiting_approval"}],
            listed.structured_content["result"],
        )
        self.assertFalse(started.is_error)
        self.assertEqual(("t_one", "plan_exact"), adapter.started)
        self.assertEqual("published", started.structured_content["state"])
        self.assertTrue(progress)

    async def test_real_stdio_entrypoint_handshake(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            parameters = StdioServerParameters(
                command=sys.executable,
                args=[
                    "-m",
                    "deep_research_agent.mcp_server",
                    "--database",
                    str(Path(directory) / "tasks.sqlite3"),
                ],
                cwd=Path.cwd(),
            )
            async with Client(parameters, raise_exceptions=True) as client:
                tools = await client.list_tools()
                listed = await client.call_tool("list_research", {})

        self.assertEqual(10, len(tools.tools))
        self.assertFalse(listed.is_error)
        self.assertEqual([], listed.structured_content["result"])


class McpAdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_empty_database_lists_no_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            adapter = McpAdapter(Path(directory) / "tasks.sqlite3")
            self.assertEqual([], await adapter.list())

    def test_task_projection_is_serialized_without_new_state_rules(self) -> None:
        task = Task(
            task_id="t_one",
            request="研究一个主题",
            language="zh",
            source_access=("public_web",),
            state="awaiting_approval",
            plan_id="plan_exact",
            plan_version=2,
        )
        # Exercise the adapter through the protocol-independent serializer by
        # importing it only inside this narrow white-box test.
        from deep_research_agent.mcp_server import _task_payload

        payload = _task_payload(task)
        self.assertEqual("awaiting_approval", payload["state"])
        self.assertEqual(
            {"plan_id": "plan_exact", "version": 2}, payload["plan"]
        )
        self.assertEqual(list(task.allowed_actions), payload["allowed_actions"])


if __name__ == "__main__":
    unittest.main()
