"""A Contract must survive the round trip through durable storage.

The reporting path re-loads the Contract from the artifact store rather than
receiving the object, so an encoding mismatch between what the Architect writes
and what a later role reads is invisible until the handoff -- which is exactly
where it was found live. These tests pin the round trip at every layer.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import aiosqlite

from deep_research_agent.approval import approval_card
from deep_research_agent.artifact_store import SqliteArtifactStore
from deep_research_agent.content_store import SqliteContentStore
from deep_research_agent.context import load_contract
from deep_research_agent.contract import ResearchContract, build_contract

BODY = """\
# 本地疫苗推荐证据评估

## 研究目标

为县级疾控团队判断是否可以制定本地推荐。

## 重点问题

- Q1. 目前是否有足够证据支持制定本地推荐？
- Q2. 已上市疫苗的效力证据强度如何？
- Q3. 本地供应与报销状况如何？

## 范围与排除

时点为 2026 年 8 月。

## 研究方式

优先监管标签与官方记录。

## 交付内容

中文决策简报，包含证据强度和本地适用性。
"""

LEGACY_BODY = """\
## 目的与用途

为县级疾控团队判断是否可以制定本地推荐。

## 问题模型

### Q1. 目前是否有足够证据支持制定本地推荐？

## 范围与定义

时点为 2026 年 8 月。

## 证据与分析方法

优先监管标签与官方记录。

## 交付与保证

中文决策简报。

## 自适应边界与已知限制

本地供应数据可能不完整。
"""


class RoundTripTest(unittest.IsolatedAsyncioTestCase):
    def contract(self) -> ResearchContract:
        return build_contract(
            BODY,
            supports={"Q2": ("Q1",), "Q3": ("Q2",)},
        )

    def test_encode_decode_preserves_everything_prose_cannot_carry(self) -> None:
        original = self.contract()
        restored = ResearchContract.decode(original.encode())

        self.assertEqual(original.body_markdown, restored.body_markdown)
        self.assertEqual(original.labels, restored.labels)
        # The support graph is the one part the markdown cannot express.
        self.assertEqual(("Q2",), restored.question_model.get("Q3").supports)

    def test_an_old_pack_member_is_accepted_but_not_re_emitted(self) -> None:
        old_body = json.loads(self.contract().encode())
        old_body["packs"] = ["domain.medicine@1.0.0"]

        restored = ResearchContract.decode(json.dumps(old_body, ensure_ascii=False))

        self.assertEqual(("Q1", "Q2", "Q3"), restored.labels)
        self.assertNotIn("packs", json.loads(restored.encode()))

    def test_a_legacy_six_section_contract_remains_readable(self) -> None:
        payload = {
            "markdown": LEGACY_BODY,
            "supports": {},
            "language": "zh",
        }

        restored = ResearchContract.decode(json.dumps(payload, ensure_ascii=False))
        card = approval_card(restored)

        self.assertEqual(("Q1",), restored.labels)
        self.assertEqual("", restored.title)
        self.assertEqual(LEGACY_BODY.strip(), card)
        self.assertNotIn("开始研究", card)

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
        self.assertEqual(("Q2",), restored.question_model.get("Q3").supports)


if __name__ == "__main__":
    unittest.main()
