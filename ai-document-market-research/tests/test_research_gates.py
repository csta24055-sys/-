"""Negative tests: no fake market research can be marked as completed.

The first block checks the pristine package state and only applies while no
research has been logged. Once real searches exist, those assertions are skipped
(the live ledger is then covered by tests/test_live_ledger.py) and the negative
tests keep running against temporary directories.
"""
from pathlib import Path
import csv
import json
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import research_gates as g

RESEARCH_STARTED=bool(g.read_csv(ROOT/'registry'/'search_log.csv'))

class ResearchGatesTests(unittest.TestCase):
    @unittest.skipIf(RESEARCH_STARTED,'pristine-state check; research has started')
    def test_initial_zip_must_be_incomplete(self):
        result=g.assess(ROOT)
        self.assertEqual(result['research_status'],'INCOMPLETE')
        self.assertNotEqual(result['steps']['S1']['state'],'PASS')
        self.assertNotEqual(result['steps']['S8']['state'],'PASS')
        self.assertEqual(result['accepted_rows'],0)

    def test_fabricated_quant_result_without_evidence_does_not_pass(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)
            for child in ('registry','research','deliverables','reference_images'): (p/child).mkdir()
            with (p/'registry'/'quant_results.csv').open('w',newline='',encoding='utf-8') as f:
                w=csv.DictWriter(f,['result_id','metric','segment','geography','period','estimate','unit','sample_n','model_id','source_ids','evidence_category']);w.writeheader()
                w.writerow({'result_id':'Q1','metric':'conversion','segment':'all','geography':'JP','period':'2026','estimate':'99','unit':'%','sample_n':'1000','source_ids':'FICTITIOUS','evidence_category':'OBSERVED'})
            res=g.assess(p)
            self.assertEqual(res['admissible_quant_results'],0)
            self.assertNotEqual(res['steps']['S5']['state'],'PASS')

    def test_empty_project_passes_nothing(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)
            for child in ('registry','research','deliverables','reference_images'): (p/child).mkdir()
            res=g.assess(p)
            self.assertEqual(res['research_status'],'INCOMPLETE')
            self.assertFalse(any(s['state']=='PASS' for s in res['steps'].values()))

    def test_later_stage_cannot_pass_before_earlier_stage(self):
        res=g.assess(ROOT)
        seen_non_pass=False
        for key,_ in g.STEPS:
            if res['steps'][key]['state']!='PASS': seen_non_pass=True
            elif seen_non_pass: self.fail(f'{key} is PASS after an earlier stage that is not PASS')

    @unittest.skipIf(RESEARCH_STARTED,'pristine-state check; research has started')
    def test_unverified_competitor_cannot_count(self):
        res=g.assess(ROOT)
        self.assertEqual(res['verified_competitors'],0)

    def test_source_with_unknown_is_not_real_evidence(self):
        self.assertFalse(g.nonempty('UNKNOWN'))
        self.assertFalse(g.nonempty(''))
        self.assertTrue(g.nonempty('SOURCE-0001'))

    def test_required_topic_id_uniqueness(self):
        rows=g.read_csv(ROOT/'registry'/'research_axes.csv')
        self.assertEqual(len(rows),325)
        self.assertEqual(len({r['topic_id'] for r in rows}),325)
        self.assertEqual(len({r['axis_id'] for r in rows}),32)

    def test_manifest_explicit_no_implementation(self):
        manifest=json.loads((ROOT/'research'/'research_manifest.json').read_text(encoding='utf-8'))
        self.assertFalse(manifest['product_implementation_allowed'])
        self.assertTrue(manifest['research_must_stop_after_report'])

if __name__=='__main__':unittest.main()
