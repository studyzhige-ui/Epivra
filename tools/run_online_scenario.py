"""Opt-in end-to-end integration scenario with an explicitly test-approved plan."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from deep_research_agent.adapters import credentials
from deep_research_agent.application import online_service
from deep_research_agent.storage import Store


async def main():
    root = Path(__file__).resolve().parents[1]
    store = Store(root / ".deep-research-agent" / "online-scenario.db")
    study = "official-tool-protocol"
    try:
        store.control(study)
    except ValueError:
        store.create(
            study,
            "技术联调研究：仅核查 DeepSeek 官方文档，简短回答：思考模式工具调用后是否需回传 reasoning_content？"
            "使用网络搜索发现官方页面，提取并阅读原文后写一段有官方 URL 引用和适用限制的中文说明。"
            "这是小型接口验证，不需要委托调查分支。",
            {"network": True},
        )
    service, clients = online_service(store, study, credentials(root / ".env"))
    try:
        await service.run(study)
        c = store.control(study)
        if not c.approved:
            plans = store.list(study, "plan")
            if plans:
                store.command(
                    study,
                    "test-scenario-approval",
                    c.ref,
                    "approve",
                    {"plan": plans[-1].ref},
                )
                await service.run(study)
        published = store.list(study, "publication")
        result = {
            "published": bool(published),
            "errors": service.errors,
            "sources": len(store.list(study, "source")),
            "steps": len(store.list(study, "step")),
            "unknown": len(store.unsettled(study)),
        }
        if published:
            report = store.get(study, published[-1].body["report"])
            output = root / ".deep-research-agent" / "online-scenario-report.md"
            output.write_text(report.body["text"], encoding="utf-8")
            result["report_path"] = str(output)
        print(json.dumps(result, ensure_ascii=False))
    finally:
        await service.close()
        for client in clients:
            await client.close()
        store.close()


if __name__ == "__main__":
    asyncio.run(main())
