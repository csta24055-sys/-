"""Gate tests with fault injection.

A small synthetic project that satisfies every gate is built in a temporary directory.
Each test then breaks exactly one thing and asserts that the gate no longer passes.
Passing these tests says the GATE behaves; it says nothing about the research itself.
"""
from __future__ import annotations
import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'tests'))
import build_status  # noqa: E402
import research_gates as g  # noqa: E402
import fixture_factory as ff  # noqa: E402


def rows(p: Path) -> tuple[list[str], list[dict]]:
    with p.open(encoding='utf-8-sig', newline='') as f:
        r = csv.DictReader(f)
        return list(r.fieldnames), list(r)


def save(p: Path, fields: list[str], data: list[dict]) -> None:
    with p.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        w.writeheader()
        w.writerows(data)


def failed(result: dict, stage: str) -> list[str]:
    return [c['detail'] for c in result['steps'][stage]['checks'] if not c['pass']]


class FaultInjection(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = ff.build(Path(self._tmp.name))
        self.reg = self.root / 'registry'

    def tearDown(self):
        self._tmp.cleanup()

    def assess(self, refresh_status: bool = True) -> dict:
        if refresh_status:  # an honest recomputation of the status ledgers after the change
            build_status.compute(self.reg, write_files=True)
        return g.assess(self.root, scope=ff.SCOPE)

    def test_00_consistent_fixture_passes_every_gate(self):
        res = self.assess()
        self.assertEqual(res['research_status'], 'COMPLETE', {k: failed(res, k) for k in res['steps']})
        self.assertTrue(all(s['state'] == 'PASS' for s in res['steps'].values()))

    def test_deleting_one_topic_fails_scope_lock(self):
        f, data = rows(self.reg / 'research_axes.csv')
        save(self.reg / 'research_axes.csv', f, data[:-1])
        res = self.assess()
        self.assertEqual(res['steps']['S0']['state'], 'FAIL')
        self.assertNotEqual(res['research_status'], 'COMPLETE')

    def test_deleting_one_legacy_query_candidate_fails_scope_lock(self):
        f, data = rows(self.reg / 'search_queries_candidates.csv')
        save(self.reg / 'search_queries_candidates.csv', f, data[1:])
        self.assertEqual(self.assess()['steps']['S0']['state'], 'FAIL')

    def test_one_unexecuted_legacy_query_fails_collection(self):
        f, data = rows(self.reg / 'search_log.csv')
        save(self.reg / 'search_log.csv', f, [r for r in data if r['suggestion_id'] != 'AXIS_02_T01_Q4'])
        res = self.assess()
        self.assertEqual(res['steps']['S1']['state'], 'FAIL')
        self.assertTrue(any('legacy queries handled' in x for x in failed(res, 'S1')))
        self.assertEqual(res['legacy_queries'].get('NOT_EXECUTED'), 1)

    def test_legacy_query_executed_with_altered_wording_does_not_count(self):
        f, data = rows(self.reg / 'search_log.csv')
        for r in data:
            if r['suggestion_id'] == 'AXIS_02_T01_Q4':
                r['query'] = 'beta survey improved wording'
        save(self.reg / 'search_log.csv', f, data)
        self.assertEqual(self.assess()['legacy_queries'].get('NOT_EXECUTED'), 1)

    def test_self_reported_search_without_transcript_does_not_count(self):
        f, data = rows(self.reg / 'search_log.csv')
        for r in data:
            if r['suggestion_id'] == 'AXIS_01_T01_Q1':
                r['verified_by'] = 'SELF_REPORT'
        save(self.reg / 'search_log.csv', f, data)
        self.assertEqual(self.assess()['legacy_queries'].get('NOT_EXECUTED'), 1)

    def test_writing_done_into_status_file_does_not_pass(self):
        f, data = rows(self.reg / 'search_log.csv')
        save(self.reg / 'search_log.csv', f, [r for r in data if r['suggestion_id'] != 'AXIS_02_T01_Q4'])
        build_status.compute(self.reg, write_files=True)
        f2, st = rows(self.reg / 'query_execution_status.csv')
        for r in st:
            r['state'] = 'EXECUTED'
        save(self.reg / 'query_execution_status.csv', f2, st)
        res = self.assess(refresh_status=False)
        self.assertEqual(res['steps']['S0']['state'], 'FAIL')  # hand-edited status file is detected
        self.assertTrue(any('legacy queries handled' in x for x in failed(res, 'S1')))  # and the recomputation still fails

    def test_one_unexplored_competitor_fails_collection(self):
        p = self.reg / 'competitor_units.jsonl'
        p.write_text(p.read_text(encoding='utf-8').splitlines()[0] + '\n', encoding='utf-8')
        f, data = rows(self.reg / 'search_log.csv')
        save(self.reg / 'search_log.csv', f, [r for r in data if r['unit_id'] != 'C002'])
        res = self.assess()
        self.assertTrue(any('competitor candidates explored' in x for x in failed(res, 'S1')))

    def test_priority_competitor_without_vendor_source_blocks_competitor_audit(self):
        f, data = rows(self.reg / 'source_topic_map.csv')
        save(self.reg / 'source_topic_map.csv', f, [r for r in data if r['unit_id'] != 'C001'])
        res = self.assess()
        self.assertTrue(any('highest-priority candidates' in x for x in failed(res, 'S4')))
        self.assertNotEqual(res['research_status'], 'COMPLETE')

    def test_removing_a_source_quote_fails_review(self):
        f, data = rows(self.reg / 'source_evidence.csv')
        data[0]['quote'] = ''
        save(self.reg / 'source_evidence.csv', f, data)
        res = self.assess()
        self.assertEqual(res['steps']['S2']['state'], 'FAIL')

    def test_removing_a_source_row_breaks_the_topic_that_relied_on_it(self):
        f, data = rows(self.reg / 'source_evidence.csv')
        save(self.reg / 'source_evidence.csv', f, data[1:])
        res = self.assess()
        self.assertTrue(any('missing from the ledger' in x for x in failed(res, 'S1')))
        self.assertNotEqual(res['research_status'], 'COMPLETE')

    def test_unreviewed_source_fails_review(self):
        f, data = rows(self.reg / 'source_evidence.csv')
        data[2]['review_state'] = 'S2_PENDING'
        save(self.reg / 'source_evidence.csv', f, data)
        self.assertEqual(self.assess()['steps']['S2']['state'], 'FAIL')

    def test_wrong_independent_origin_count_fails_review(self):
        p = self.root / 'research' / 'SOURCE_DEPENDENCY_AUDIT.md'
        p.write_text(p.read_text(encoding='utf-8').replace('INDEPENDENT_ORIGINS = 11', 'INDEPENDENT_ORIGINS = 99'), encoding='utf-8')
        res = self.assess()
        self.assertTrue(any('independent-origin count' in x for x in failed(res, 'S2')))

    def test_counting_one_origin_twice_fails_review(self):
        fs, src = rows(self.reg / 'source_evidence.csv')
        src[1]['origin_group_id'] = src[0]['origin_group_id']  # two sources really share one origin ...
        save(self.reg / 'source_evidence.csv', fs, src)
        res = self.assess()  # ... but the dependency ledger still lists them as two canonical origins
        self.assertTrue(any('independent-origin count' in x for x in failed(res, 'S2')))

    def test_unmeasured_own_app_metric_marked_observed_fails_calculations(self):
        f, data = rows(self.reg / 'calculation_inventory.csv')
        data[0]['target'] = '当アプリの継続率'
        save(self.reg / 'calculation_inventory.csv', f, data)
        (self.root / 'research' / 'quant_outputs.json').write_text(json.dumps({'inventory_digest': g.inventory_digest(data)}), encoding='utf-8')
        self.assertTrue(any('terminal state' in x for x in failed(self.assess(), 'S5')))

    def test_observed_with_assumed_inputs_fails_calculations(self):
        f, data = rows(self.reg / 'calculation_inventory.csv')
        data[1]['inputs_assumed'] = 'conversion=5%'
        save(self.reg / 'calculation_inventory.csv', f, data)
        (self.root / 'research' / 'quant_outputs.json').write_text(json.dumps({'inventory_digest': g.inventory_digest(data)}), encoding='utf-8')
        self.assertTrue(any('terminal state' in x for x in failed(self.assess(), 'S5')))

    def test_number_without_verified_source_fails_calculations(self):
        f, data = rows(self.reg / 'quant_results.csv')
        data[0]['source_ids'] = 'FICTITIOUS'
        save(self.reg / 'quant_results.csv', f, data)
        self.assertTrue(any('traceable' in x for x in failed(self.assess(), 'S5')))

    def test_unidentifiable_row_with_a_number_fails_calculations(self):
        f, data = rows(self.reg / 'calculation_inventory.csv')
        data[2].update(status='NON_IDENTIFIABLE', category='NON_IDENTIFIABLE', result='50%')
        save(self.reg / 'calculation_inventory.csv', f, data)
        (self.root / 'research' / 'quant_outputs.json').write_text(json.dumps({'inventory_digest': g.inventory_digest(data)}), encoding='utf-8')
        self.assertTrue(any('terminal state' in x for x in failed(self.assess(), 'S5')))

    def test_stale_recalculation_output_fails_calculations(self):
        f, data = rows(self.reg / 'calculation_inventory.csv')
        data[0]['result'] = '0.9'
        save(self.reg / 'calculation_inventory.csv', f, data)
        self.assertTrue(any('recalculation output' in x for x in failed(self.assess(), 'S5')))

    def test_topic_without_calculation_fails_calculations(self):
        f, data = rows(self.reg / 'calculation_inventory.csv')
        save(self.reg / 'calculation_inventory.csv', f, data[:-1])
        self.assertTrue(any('at least one calculation id' in x for x in failed(self.assess(), 'S5')))

    def test_missing_axis_synthesis_fails_integration(self):
        (self.root / 'research' / 'axis_synthesis' / 'AXIS_02.md').unlink()
        self.assertEqual(self.assess()['steps']['S6']['state'], 'FAIL')

    def test_later_stage_cannot_pass_while_an_earlier_one_fails(self):
        f, data = rows(self.reg / 'source_evidence.csv')
        data[0]['review_state'] = 'S2_PENDING'
        save(self.reg / 'source_evidence.csv', f, data)
        res = self.assess()
        seen_fail = False
        for key, _ in g.STEPS:
            st = res['steps'][key]['state']
            if st != 'PASS':
                seen_fail = True
            self.assertFalse(seen_fail and st == 'PASS', f'{key} passed after an earlier failure')
        self.assertNotEqual(res['research_status'], 'COMPLETE')

    def test_formal_deliverable_before_gates_pass_is_a_violation(self):
        f, data = rows(self.reg / 'search_log.csv')
        save(self.reg / 'search_log.csv', f, [r for r in data if r['suggestion_id'] != 'AXIS_02_T01_Q4'])
        res = self.assess()  # deliverables still present while S1 fails
        self.assertTrue(res['formal_deliverable_violation'])
        self.assertTrue(any('before S0-S8 pass' in x for x in failed(res, 'S9')))

    def test_empty_project_passes_nothing(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            for child in ('registry', 'research', 'deliverables', 'reference_images'):
                (p / child).mkdir()
            res = g.assess(p)
            self.assertNotEqual(res['research_status'], 'COMPLETE')
            self.assertFalse(any(s['state'] == 'PASS' for s in res['steps'].values()))


class LiveProject(unittest.TestCase):
    def test_live_state_is_internally_consistent(self):
        res = g.assess(ROOT)
        if res['research_status'] == 'COMPLETE':
            self.assertTrue(all(s['state'] == 'PASS' for s in res['steps'].values()))
        seen_fail = False
        for key, _ in g.STEPS:
            if res['steps'][key]['state'] != 'PASS':
                seen_fail = True
            else:
                self.assertFalse(seen_fail)

    def test_scope_is_locked_in_the_live_registry(self):
        self.assertEqual(len(g.read_csv(ROOT / 'registry' / 'research_axes.csv')), g.FULL_SCOPE['topics'])
        self.assertEqual(len(g.read_csv(ROOT / 'registry' / 'search_queries_candidates.csv')), g.FULL_SCOPE['legacy'])
        self.assertEqual(len(g.read_csv(ROOT / 'registry' / 'competitor_candidates.csv')), g.FULL_SCOPE['competitors'])

    def test_no_formal_deliverable_while_incomplete(self):
        res = g.assess(ROOT)
        self.assertFalse(res['formal_deliverable_violation'])

    def test_helpers(self):
        self.assertFalse(g.nonempty('UNKNOWN'))
        self.assertTrue(g.nonempty('S001'))
        manifest = json.loads((ROOT / 'research' / 'research_manifest.json').read_text(encoding='utf-8'))
        self.assertFalse(manifest['product_implementation_allowed'])
        self.assertTrue(manifest['research_must_stop_after_report'])


if __name__ == '__main__':
    unittest.main()
