"""Structure tests for the research scope.

The image checks need the eight user-supplied reference images, which are kept
out of Git because this repository is public. When they are absent (fresh
clone) those checks are skipped instead of failing.
"""
import unittest,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import scope_audit,research_gates

IMAGES_PRESENT=len(list((ROOT/'reference_images').glob('IMG_*')))==8
RESEARCH_STARTED=bool(research_gates.read_csv(ROOT/'registry'/'search_log.csv'))

class ScopeAuditTests(unittest.TestCase):
 def test_structure_and_preservation(self):
  x=scope_audit.audit()
  if IMAGES_PRESENT: self.assertTrue(x['PASS'],x)
  self.assertEqual((x['axes'],x['topics'],x['initial_search_plans'],x['competitor_candidates']),(32,325,325,80))
  self.assertTrue(x['original_competitors_all_preserved'])
  self.assertTrue(x['original_topic_ids_all_preserved'])
  self.assertEqual((x['topic_duplicates'],x['competitor_id_duplicates'],x['plan_id_duplicates']),(0,0,0))
 @unittest.skipIf(RESEARCH_STARTED,'pristine-state check; research has started')
 def test_unexecuted_research_is_not_completed(self):
  x=scope_audit.audit();self.assertTrue(x['research_is_unperformed'])
  y=research_gates.assess(ROOT)
  self.assertEqual(y['research_status'],'INCOMPLETE')
  self.assertEqual(y['accepted_rows'],0)
  self.assertEqual(y['verified_competitors'],0)
  self.assertNotEqual(y['steps']['S4']['state'],'PASS')
 def test_prohibited_regeneration_guard(self):
  self.assertTrue(scope_audit.audit()['app_implementation_forbidden'])
  for x in ('build_research_inventory.py','create_search_queue.py'):
   self.assertIn('DEPRECATED',(ROOT/'scripts'/x).read_text(encoding='utf-8'))
 @unittest.skipUnless(IMAGES_PRESENT,'reference images are not stored in Git (public repository)')
 def test_image_hashes(self):
  self.assertEqual(scope_audit.audit()['image_hash_mismatches'],[])
