"""One bounded causal test of assignment anchoring through the real writer Harness.

No private provider response is exported; expected statements stay evaluator-only.
The candidate changes one writer paragraph in this evaluation process only.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import epivra.harness as runtime
from epivra.domain import identity
from epivra.models import create_model, freeze_model_settings
from epivra.storage import Store
from evals.task_authority_probe import CASES, ORDER, candidate_writer, validate_request
from tools.run_live_eval import collect, save


def seed(store, index, case_id, assignment):
    case = CASES[case_id]
    study = f'trial-{index}'
    policy = freeze_model_settings({'provider': 'deepseek', 'model': 'deepseek-flash', 'network': False, 'stream_model': True, 'as_of_date': '2026-09-20'})
    control = store.create(study, case['task'], policy)
    plan = store.put(study, 'plan', {'text': '依据已给定资料回答原问题，保留成立条件。'}, (control.direction,))
    control = store.command(study, 'approve', control.ref, 'approve', {'plan': plan.ref})
    owner = store.work(study, control.ref, 'lead', 'Coordinate the approved task')
    source = store.put(study, 'source', {'text': case['source'], 'origin': 'provided-record.txt', 'coverage': 'complete'})
    investigator = store.work(study, control.ref, 'investigator', 'Read the complete provided record', (source.ref,), owner.ref)
    finding = store.put(study, 'work_result', {'text': case['source'], 'refs': [source.ref], 'producer': investigator.ref}, (investigator.ref, source.ref))
    writer = store.work(study, control.ref, 'writer', case[assignment], (finding.ref,), owner.ref)
    return study, writer, policy


async def run(root, run_id):
    request = validate_request(json.loads((root / 'evals/root-cause-request.json').read_text(encoding='utf-8')))
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', run_id) or os.environ.get('GITHUB_RUN_ATTEMPT', '1') != '1':
        raise ValueError('inspect prior evidence; never blindly repeat paid attempts')
    candidate = candidate_writer()  # Reject a drifted starting prompt before credentials.
    folder = root / '.epivra' / ('authority-' + run_id)
    output = root / 'artifacts/task-authority'
    if folder.exists() or output.exists():
        raise ValueError('fresh run directory required')
    key = os.environ.get('DEEPSEEK_API_KEY', '').strip()
    if not key:
        raise ValueError('missing model credential')
    folder.mkdir(parents=True)
    output.mkdir(parents=True)
    store = Store(folder / 'research.db')
    summary = {'request': request, 'code': os.environ.get('GITHUB_SHA'), 'started_at': time.time(), 'results': [], 'semantic_acceptance': 'pending_independent_review', 'scope': 'synthetic work-task intervention, not full research latency'}
    save(output / 'experiment.json', {'cases': CASES, 'order': ORDER, 'baseline_writer': runtime.ROLES['writer'], 'candidate_writer': candidate, 'case_hash': identity(CASES), 'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
    stop_at = time.monotonic() + 540
    try:
        for index, (case_id, assignment, arm) in enumerate(ORDER):
            if time.monotonic() >= stop_at:
                break
            study, writer, policy = seed(store, index, case_id, assignment)
            model, api = create_model(policy, {'DEEPSEEK_API_KEY': key})
            harness = runtime.Harness(store, model)
            started = time.perf_counter()
            steps, error = 0, None
            roles = {**runtime.ROLES, 'writer': candidate} if arm == 'candidate' else dict(runtime.ROLES)
            try:
                with patch.object(runtime, 'ROLES', roles):
                    while steps < 4 and time.monotonic() < stop_at and not harness.finished(study, writer.ref):
                        if harness.waiting(study, writer.ref):
                            break
                        await harness.step(study, writer.ref)
                        steps += 1
            except Exception as exc:
                error = type(exc).__name__
            finally:
                await api.close()
            reports = store.list(study, 'report')
            observations = harness._steps(study, 'observation', writer.ref)
            summary['results'].append({'study': study, 'case': case_id, 'assignment': assignment, 'arm': arm, 'steps': steps, 'complete': harness.finished(study, writer.ref), 'report': reports[-1].ref if reports else None, 'tool_failures': sum(bool(x.body.get('failure')) for x in observations), 'tools': [x.body.get('tool') for x in observations], 'elapsed_seconds': time.perf_counter() - started, 'error_type': error})
            save(output / 'summary.json', summary, (key,))
            if store.unsettled(study):
                break
    finally:
        store.close()
        projection = collect(folder / 'research.db')
        for field, name in [('artifacts', 'public-artifacts.json'), ('windows', 'window-manifest.json'), ('calls', 'calls.json')]:
            save(output / name, projection[field], (key,))
        summary.update(usage=projection['usage'], unknown_operations=projection['unknown_operations'], elapsed_seconds=time.time()-summary['started_at'])
        summary['execution_pass'] = len(summary['results']) == len(ORDER) and all(r['complete'] and not r['error_type'] for r in summary['results']) and not summary['unknown_operations']
        save(output / 'summary.json', summary, (key,))
        save(output / 'artifact-manifest.json', {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir() if p.name != 'artifact-manifest.json'})
    print(json.dumps({'complete': summary['execution_pass'], 'trials': len(summary['results']), 'unknown': summary['unknown_operations']}))
    return 0 if summary['execution_pass'] else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    try:
        status = asyncio.run(run(Path(__file__).resolve().parents[1], args.run_id))
    except Exception as exc:
        print(json.dumps({'error_type': type(exc).__name__}))
        status = 1
    raise SystemExit(status)
