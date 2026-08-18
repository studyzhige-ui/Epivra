"""A Contract must survive the round trip through durable storage.

The reporting path re-loads the Contract from the artifact store rather than
receiving the object, so an encoding mismatch between what the Architect writes
and what a later role reads is invisible until the handoff -- which is exactly
where it was found live. These tests pin the round trip at every layer.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import aiosqlite

from deep_research_agent.artifact_store import SqliteArtifactStore
from deep_research_agent.content_store import SqliteContentStore
from deep_research_agent.context import load_contract
from deep_research_agent.contract import ResearchContract, build_contract

BODY = """\
## 目的与用途

为县级疾控团队判断是否可以制定本地推荐。

## 问题模型

### Q1. 目前是否有足够证据支持制定本地推荐？
### Q2. 已上市疫苗的效力证据强度如何？
### Q3. 本地供应与报销状况如何？

## 范围与定义

时点为 2026 年 8 月。

## 证据与分析方法

优先监管标签与官方记录。

## 交付与保证

决策简报，独立审查。

## 自适应边界与已知限制

查询顺序由 Lead 自适应。
"""


class RoundTripTest(unittest.IsolatedAsyncioTestCase):
    def contract(self) -> ResearchContract:
        return build_contract(
            BODY,
            supports={"Q2": ("Q1",), "Q3": ("Q2",)},
            pack_refs=("domain.medicine@1.0.0",),
        )

    def test_encode_decode_preserves_everything_prose_cannot_carry(self) -> None:
        original = self.contract()
        restored = ResearchContract.decode(original.encode())

        self.assertEqual(original.body_markdown, restored.body_markdown)
        self.assertEqual(original.labels, restored.labels)
        self.assertEqual(original.pack_refs, restored.pack_refs)
        # The support graph is the one part the markdown cannot express.
        self.assertEqual(("Q2",), restored.question_model.get("Q3").supports)

    def test_encoding_is_stable(self) -> None:
        original = self.contract()
        self.assertEqual(original.encode(), ResearchContract.decode(original.encode()).encode())

    async def test_a_stored_contract_reloads_through_load_contract(self) -> None:
        """The bug found live: the reporting path re-reads from the store."""

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "task.sqlite3"
            connection = await aiosqlite.connect(path)
            try:
                content = SqliteContentStore(connection)
                await content.setup()
                store = SqliteArtifactStore(connection, content, task_id="t1")
                await store.setup()

                original = self.contract()
                await store.put(
                    kind="research_contract", body=original.encode()
                )
                restored = await load_contract(store)
            finally:
                await connection.close()

        self.assertEqual(original.labels, restored.labels)
        self.assertEqual(original.pack_refs, restored.pack_refs)
        self.assertEqual(("Q2",), restored.question_model.get("Q3").supports)


if __name__ == "__main__":
    unittest.main()
