"""Opt-in paid model/tool smoke test; production prompts, resumable original ledger."""

import argparse
import asyncio
import json
from pathlib import Path

from deep_research_agent.adapters import credentials
from deep_research_agent.analysis import settings
from deep_research_agent.harness import Harness
from deep_research_agent.models import create_model, freeze_model_settings
from deep_research_agent.storage import Store
from deep_research_agent.workspace import Workspace

TASK = (
    "根据所提供的 UCI Iris 数据制作一份简短中文描述性分析说明，附可复用的分组统计 CSV 和 PNG 图。"
    "原件无表头，依次为萼片长、萼片宽、花瓣长、花瓣宽（厘米）、物种。"
    "检查记录数及缺失情况，比较各物种的平均萼片长度；解释数据能支持什么、不能支持什么。"
    "只使用所提供的资料，不需要网络研究。"
)


async def run(root, output):
    store = Store(output / "state.db")
    study = "analysis-model-smoke"
    api = None
    try:
        if not store.list(study, "direction"):
            policy = freeze_model_settings(
                {"provider": "deepseek", "network": False, "analysis": await settings()}
            )
            c = store.create(study, TASK, policy)
            plan = store.put(study, "plan", {"text": TASK}, (c.direction,))
            c = store.command(study, "approve", c.ref, "approve", {"plan": plan.ref})
            lead = store.work(
                study, c.ref, "lead", "受控沙箱联调，协调任务由测试驱动器安排。"
            )
            source = Workspace(store).upload(
                study, "iris.csv", (root / "evals/analysis/iris.csv").read_bytes()
            )
            store.work(study, c.ref, "investigator", TASK, (source.ref,), lead.ref)
        c = store.control(study)
        policy = store.get(study, c.direction).body["policy"]
        model, api = create_model(policy, credentials(root / ".env"))
        harness = Harness(store, model)
        work = next(
            a for a in store.list(study, "work") if a.body["role"] == "investigator"
        )
        # A smoke-test call budget, never a production research termination rule.
        for _ in range(20):
            if harness.finished(study, work.ref):
                break
            if harness.waiting(study, work.ref):
                raise RuntimeError(
                    "Model requested clarification; inspect original artifacts"
                )
            await harness.step(study, work.ref)
            print(
                json.dumps(
                    {
                        "steps": len(store.list(study, "step")),
                        "analyses": len(store.list(study, "analysis_result")),
                    }
                ),
                flush=True,
            )
        if not harness.finished(study, work.ref):
            raise RuntimeError(
                "Smoke-test call budget reached; retained ledger can be resumed"
            )
        workspace = Workspace(store)
        exported = []
        for result in store.list(study, "analysis_result"):
            for item in result.body["files"]:
                destination = output / "outputs" / result.ref / item["name"]
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(workspace.original(study, item["ref"]))
                exported.append(str(destination.relative_to(output)))
        finding = harness._steps(study, "work_result", work.ref)[-1]
        record = {
            "model": policy["model"],
            "finding": finding.body,
            "analyses": [a.body for a in store.list(study, "analysis_result")],
            "usage": store.usage_records(study),
            "files": exported,
            "scope": "real investigator/tool smoke test, not full research acceptance",
        }
        (output / "result.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print("Completed; original artifacts and usage retained.", flush=True)
    finally:
        if api:
            await api.close()
        store.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    asyncio.run(run(Path(__file__).resolve().parents[1], args.output))
