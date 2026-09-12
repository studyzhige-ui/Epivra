"""Offline browser fixture. Seeds display facts; does NOT evaluate research quality.

Run from the worktree, then launch deep-research-web with the printed temp root.
Stop with Host.shutdown against that temporary root. Never loads account keys.
"""

import asyncio
import json
import tempfile
from pathlib import Path

from deep_research_agent import cli_settings
from deep_research_agent.host import Host
from deep_research_agent.workspace import Workspace


async def main():
    with tempfile.TemporaryDirectory(prefix="dr-web-fixture-") as directory:
        root = Path(directory)
        cli_settings.save_key(root, "DEEPSEEK_API_KEY", "offline-browser-fixture")
        cli_settings.save(
            root, {"provider": "deepseek", "model": "deepseek-flash", "parser": "light"}
        )
        material = root / "公开样例.txt"
        material.write_text(
            "甲方案试点30天，服务120人；乙方案试点14天，服务70人。不同时间窗口不能直接比较总量。",
            encoding="utf-8",
        )
        host = Host(root)

        def seed_strategy(study):
            c = host.store.control(study)
            if not c.approved and not any(
                c.direction in p.parents for p in host.store.list(study, "plan")
            ):
                host.store.put(
                    study,
                    "plan",
                    {
                        "text": "## 研究目标\n比较资料中的方案，明确适用条件与不确定性。\n\n## 研究方法\n1. 阅读原始资料，核对口径与时间范围。\n2. 分析差异，区分事实与推断。\n3. 撰写建议，并独立核查依据。",
                        "brief": {
                            "subject": "本地资料中的方案比较",
                            "given_context": ["原件由用户提供"],
                            "questions": ["方案的适用条件是什么？"],
                            "material_scope": {
                                "mode": "case_materials",
                                "basis": "用户选定的资料",
                            },
                        },
                    },
                    (c.direction,),
                )

        # Deliberate fixture projection: production Host control/upload/download,
        # but no provider initialization or pretend semantic model results.
        host.start_study = seed_strategy
        c = host.store.create(
            "completed-example",
            "社区服务方案比较：试点结果与下一步建议（界面样例）",
            {"provider": "deepseek", "model": "deepseek-flash"},
        )
        source = await Workspace(host.store).upload_async(
            "completed-example", c.ref, material.name, material.read_bytes()
        )
        seed_strategy("completed-example")
        plan = host.store.list("completed-example", "plan")[-1]
        c = host.store.command(
            "completed-example",
            "fixture-approval",
            c.ref,
            "approve",
            {"plan": plan.ref},
        )
        report = host.store.put(
            "completed-example",
            "report",
            {
                "text": "# 社区服务方案比较\n\n> 界面验证样例，不代表实际研究结果。\n\n## 主要发现\n\n两项试点的**观察窗口不同**，服务总人数不能直接当作效果排名。\n\n| 方案 | 试点时间 | 服务人数 |\n|---|---:|---:|\n| 甲 | 30天 | 120人 |\n| 乙 | 14天 | 70人 |\n\n## 下一步建议\n\n- 统一统计窗口与服务定义。\n- 补充成本、满意度和人员投入，再决定扩展方案。\n\n## 呈现边界样例\n\n<script>window.fixtureXSS=true</script>\n\n[不可执行链接](javascript:alert(1))\n\n![远端图片不会自动加载](https://example.invalid/tracking.png)",
                "evidence": [source.ref],
            },
            (c.direction, source.ref),
        )
        host.store._put(
            "completed-example",
            "publication",
            {"report": report.ref},
            (c.direction, report.ref),
        )
        pointer = Path.cwd() / ".deep-research-agent/web-fixture.json"
        pointer.parent.mkdir(parents=True, exist_ok=True)
        pointer.write_text(
            json.dumps({"root": str(root), "file": str(material)}, ensure_ascii=False),
            encoding="utf-8",
        )
        print(
            json.dumps({"root": str(root), "file": str(material)}, ensure_ascii=False),
            flush=True,
        )
        await host.serve()


if __name__ == "__main__":
    asyncio.run(main())
