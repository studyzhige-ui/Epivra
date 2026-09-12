"""Explicit local Docker checks on a public snapshot. No model/search API calls."""

import argparse
import asyncio
import csv
import io
import json
import tempfile
import uuid
from pathlib import Path

from deep_research_agent.analysis import DockerSandbox, settings
from deep_research_agent.domain import Call, Reply, identity
from deep_research_agent.harness import Harness
from deep_research_agent.storage import Store
from deep_research_agent.workspace import Workspace

ANALYZE = """
import pandas as pd
import matplotlib.pyplot as plt
data=pd.read_csv('/inputs/data/iris.csv', header=None,
    names=['sepal_length','sepal_width','petal_length','petal_width','species'])
summary=data.groupby('species').agg(n=('sepal_length','size'),mean=('sepal_length','mean'))
summary.to_csv('/outputs/summary.csv')
summary['mean'].plot.bar(ylabel='Mean sepal length (cm)', title='Iris sample descriptive means')
plt.tight_layout();plt.savefig('/outputs/means.png')
print(summary.to_json())
print('Descriptive sample comparison; not a causal or population claim.')
"""
WRITE = """
import pandas as pd
summary=pd.read_csv('/inputs/data/summary.csv')
text='# Iris sample summary\\n\\n'
text+='| Species | n | Mean sepal length (cm) |\\n|---|---:|---:|\\n'
for row in summary.itertuples(index=False):
    text+=f'| {row.species} | {row.n} | {row.mean:.3f} |\\n'
text+='\\nThese are descriptive statistics for the supplied sample, not causal estimates.\\n'
open('/outputs/table.md','w').write(text)
print('Formatted existing calculated results without changing their values.')
"""
BOUNDARIES = """
import os, socket, pathlib
assert os.getuid()!=0
assert not any(k.endswith('API_KEY') for k in os.environ)
assert not pathlib.Path('/var/run/docker.sock').exists()
for path in ['/inputs/prohibited.txt', '/prohibited.txt']:
    try: open(path,'w').write('no')
    except OSError: pass
    else: raise AssertionError('write escaped boundary')
try: socket.create_connection(('1.1.1.1',53),timeout=1)
except OSError: pass
else: raise AssertionError('network escaped boundary')
pathlib.Path('/outputs/link').symlink_to('/etc/passwd')
open('/outputs/chart(1).txt','w').write('Allowed portable filename')
print('isolation checks passed')
"""


class FixtureModel:
    identity = "analysis-engineering-probe"
    call = None

    async def complete(self, request):
        return Reply("", (self.call,)).to_json()


async def probe(output):
    config = await settings()
    output.mkdir(parents=True, exist_ok=True)
    store = Store(output / "state.db")
    model = FixtureModel()
    harness = Harness(store, model)
    study = uuid.uuid4().hex
    try:
        c = store.create(
            study,
            "Describe the supplied Iris sample and produce a reusable table/chart",
            {"analysis": config},
        )
        plan = store.put(
            study,
            "plan",
            {"text": "Offline engineering fixture approval"},
            (c.direction,),
        )
        c = store.command(study, "approve", c.ref, "approve", {"plan": plan.ref})
        lead = store.work(study, c.ref, "lead", "Coordinate")
        raw = Path("evals/analysis/iris.csv").read_bytes()
        source = Workspace(store).upload(study, "iris.csv", raw)
        investigator = store.work(
            study,
            c.ref,
            "investigator",
            "Describe group means",
            (source.ref,),
            lead.ref,
        )

        async def execute(work, name, args):
            model.call = Call(name, args)
            await harness.step(study, work.ref)

        await execute(
            investigator,
            "run_analysis",
            {
                "purpose": "Describe Iris groups",
                "code": ANALYZE,
                "inputs": [{"name": "iris.csv", "ref": source.ref}],
            },
        )
        first = store.list(study, "analysis_result")[-1]
        assert first.body["status"] == "succeeded", store.get(
            study, first.body["log"]
        ).body
        by_name = {f["name"]: f["ref"] for f in first.body["files"]}
        summary = Workspace(store).original(study, by_name["summary.csv"]).decode()
        data = [row for row in csv.reader(io.StringIO(raw.decode())) if row]
        assert len(data) == 150
        for row in csv.DictReader(io.StringIO(summary)):
            group = [float(r[0]) for r in data if r[-1] == row["species"]]
            assert int(row["n"]) == len(group) == 50
            assert abs(float(row["mean"]) - sum(group) / len(group)) < 1e-10
        await execute(
            investigator,
            "finish_work",
            {
                "text": "Descriptive means computed from the supplied snapshot; use the original outputs.",
                "refs": [source.ref, *by_name.values()],
            },
        )
        finding = store.list(study, "work_result")[-1]
        writer = store.work(
            study,
            c.ref,
            "writer",
            "Format the existing table",
            (finding.ref,),
            lead.ref,
        )
        await execute(
            writer,
            "run_analysis",
            {
                "purpose": "Format existing results",
                "code": WRITE,
                "inputs": [{"name": "summary.csv", "ref": by_name["summary.csv"]}],
            },
        )
        second = store.list(study, "analysis_result")[-1]
        assert second.body["status"] == "succeeded", store.get(
            study, second.body["log"]
        ).body
        table = second.body["files"][0]["ref"]
        text = Workspace(store).original(study, table).decode()
        await execute(
            writer,
            "draft_report",
            {
                "text": text,
                "evidence": [source.ref, by_name["summary.csv"], table],
                "handoff": "Exact calculated files retained; scripted integration check only.",
            },
        )
        report = store.list(study, "report")[-1]
        assert by_name["summary.csv"] in report.body["evidence"]
        for name, ref in [*by_name.items(), ("table.md", table)]:
            (output / name).write_bytes(Workspace(store).original(study, ref))
        print("Public dataset statistics, plot and writer handoff: passed", flush=True)

        sandbox = DockerSandbox()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            for label, code, override in [
                ("isolation", BOUNDARIES, {}),
                ("timeout", "import time; time.sleep(20)", {"timeout": 1}),
                ("syntax", "this is not valid Python", {}),
            ]:
                job = identity(study, label)
                (path / "analysis.py").write_text(code, encoding="utf-8")
                cfg = {**config, **override}
                try:
                    result = await sandbox.run(job, path, cfg, True, lambda: None)
                    if label == "isolation":
                        assert result["status"] == "succeeded", result
                        assert any("non-regular" in item for item in result["issues"])
                        assert result["files"][0]["name"] == "chart(1).txt"
                        # A fresh executor reads the stopped container's exact original output.
                        replay = await DockerSandbox().run(
                            job, path, cfg, False, lambda: None
                        )
                        assert replay == result
                    else:
                        assert result["status"] == (
                            "timeout" if label == "timeout" else "failed"
                        ), result
                    print(label + ": passed", flush=True)
                finally:
                    await sandbox.cleanup(job)
        result = {
            "study": study,
            "image": config["image"],
            "checks": [
                "statistics",
                "plot",
                "handoff",
                "isolation",
                "recovery",
                "timeout",
                "syntax",
            ],
            "model_calls": 0,
            "scope": "scripted engineering validation, not semantic research benchmark",
        }
        (output / "validation.json").write_text(
            json.dumps(result, indent=2), encoding="utf-8"
        )
    finally:
        store.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output", type=Path, default=Path(".deep-research-agent/analysis-probe")
    )
    asyncio.run(probe(parser.parse_args().output))
