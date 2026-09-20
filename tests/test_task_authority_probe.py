"""Causal variable isolation and bounded evaluation admission, offline only."""
import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import epivra.harness as runtime
from epivra.storage import Store
from evals.task_authority_probe import (
    CASES,
    NEW,
    OLD,
    ORDER,
    candidate_writer,
    validate_request,
)
from tools.run_task_authority_probe import run, seed


class TaskAuthorityTests(unittest.TestCase):
    def test_full_factorial_same_cases_without_repeats(self):
        expected = {(c, a, p) for c in CASES for a in ('neutral', 'anchored') for p in ('baseline', 'candidate')}
        self.assertEqual(expected, set(ORDER))
        self.assertEqual(len(expected), len(ORDER))

    def test_candidate_is_one_exact_replacement_not_runtime_mutation(self):
        baseline = dict(runtime.ROLES)
        candidate = candidate_writer()
        self.assertEqual(baseline, runtime.ROLES)
        self.assertEqual(baseline['writer'], candidate.replace(NEW, OLD))

    def test_only_preregistered_request(self):
        request = {'version': 1, 'request_id': 'task-authority-20260920-01'}
        self.assertEqual(request, validate_request(request))
        for change in ({'version': True}, {'cases': ['benchmark10']}, {'request_id': '../escape'}):
            with self.assertRaises(ValueError):
                validate_request({**request, **change})

    def test_same_original_request_and_source_only_task_is_intervened(self):
        with tempfile.TemporaryDirectory() as name:
            store = Store(Path(name) / 's.db')
            try:
                for case_id, case in CASES.items():
                    rows = []
                    for index, assignment in enumerate(('neutral', 'anchored')):
                        study, work, _ = seed(store, 2 * list(CASES).index(case_id) + index, case_id, assignment)
                        h = runtime.Harness(store, type('Offline', (), {'identity': 'no-network'})())
                        request = h._request(study, work)
                        self.assertEqual(case['task'], request['direction']['request'])
                        self.assertEqual(case[assignment], request['task'])
                        self.assertNotIn('constraints', json.dumps(request))
                        rows.append(store.list(study, 'source')[0].body)
                    self.assertEqual(rows[0], rows[1])
            finally:
                store.close()

    def test_no_paid_rerun_before_credentials(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            (root / 'evals').mkdir()
            (root / 'evals/root-cause-request.json').write_text(json.dumps({'version': 1, 'request_id': 'task-authority-20260920-01'}))
            with patch.dict('os.environ', {'GITHUB_RUN_ATTEMPT': '2'}), patch('tools.run_task_authority_probe.candidate_writer', side_effect=AssertionError('too late')):
                with self.assertRaisesRegex(ValueError, 'prior evidence'):
                    asyncio.run(run(root, 'test'))


if __name__ == '__main__':
    unittest.main()
