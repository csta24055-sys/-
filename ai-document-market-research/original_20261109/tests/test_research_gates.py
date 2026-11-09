"""Negative tests: no fake market research can be marked as completed."""
from pathlib import Path
import csv
import json
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import research_gates as g

class ResearchGatesTests(unittest.TestCase):
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

    def test_unverified_competitor_cannot_count(self):
        res=g.assess(ROOT)
        self.assertEqual(res['verified_competitors'],0)

    def test_source_with_unknown_is_not_real_evidence(self):
        self.assertFalse(g.nonempty('UNKNOWN'))
        self.assertFalse(g.nonempty(''))
        self.assertTrue(g.nonempty('SOURCE-0001'))

    def test_required_topic_id_uniqueness(self):
        rows=g.read_csv(ROOT/'registry'/'research_axes.csv')
        self.assertEqual(len(rows),224)
        self.assertEqual(len({r['topic_id'] for r in rows}),224)
        self.assertEqual(len({r['axis_id'] for r in rows}),28)

    def test_manifest_explicit_no_implementation(self):
        manifest=json.loads((ROOT/'research'/'research_manifest.json').read_text(encoding='utf-8'))
        self.assertFalse(manifest['product_implementation_allowed'])
        self.assertTrue(manifest['research_must_stop_after_report'])

if __name__=='__main__':unittest.main()
