"""Tests of the synthetic scenario foundation (stdlib unittest).

Run:  cd research_code && python3 -m unittest tests.test_synth -v
"""
import json
import math
import unittest

import synth
from synth import model, population


class SynthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = synth.make_scenario(11, "SRC", "hospital", "S")

    def test_input_coverage(self):
        cov = model.check_input_coverage()
        self.assertEqual(cov["total"], 124)
        self.assertEqual(cov["mapped_to_attribute"] + cov["metadata_only"], 124)

    def test_deterministic(self):
        again = synth.make_scenario(11, "SRC", "hospital", "S")
        self.assertEqual(json.dumps(synth.to_dict(self.s), sort_keys=True),
                         json.dumps(synth.to_dict(again), sort_keys=True))
        other = synth.make_scenario(12, "SRC", "hospital", "S")
        self.assertNotEqual(synth.to_dict(self.s)["materials"], synth.to_dict(other)["materials"])

    def test_json_round_trip(self):
        data = json.loads(json.dumps(synth.to_dict(self.s)))
        self.assertEqual(synth.to_dict(synth.from_dict(data)), synth.to_dict(self.s))

    def test_clean_scenario_is_consistent(self):
        s = self.s
        self.assertEqual(s.meta.source_tag, "SYNTHETIC_FICTIONAL")
        for f in s.factors.values():
            self.assertEqual(f.source_tag, "SYNTHETIC_FICTIONAL")
            co2e = sum(s.gwp[g] * f.gas_amounts[g] for g in s.gases)
            self.assertTrue(math.isclose(co2e, f.value, rel_tol=1e-9, abs_tol=1e-12), f.factor_id)
        for row in s.materials:
            self.assertTrue(math.isclose(sum(r.fraction for r in row.end_of_life.routes), 1.0, abs_tol=1e-12))
            if row.composition is not None:
                self.assertIsNone(row.factor_id)
                self.assertTrue(math.isclose(sum(c.mass_fraction for c in row.composition), 1.0, abs_tol=1e-12))
        need = math.ceil(s.boundary.study_period)
        for _, profile in model.annual_profiles(s):
            self.assertGreaterEqual(len(profile.table), max(need, model.YEAR_TABLE_MIN_LENGTH))
        self.assertGreaterEqual(len(s.operation.grid.table), max(need, model.YEAR_TABLE_MIN_LENGTH))
        self.assertEqual(s.meta.injected_defects, [])

    def test_descriptors_match_tables(self):
        for kind in model.PROFILE_KINDS:
            s = synth.make_scenario(3, "S", "office", "S", profile_kind=kind, n_materials=5, n_equipment=2)
            for _, p in model.annual_profiles(s):
                if p.kind == "CONSTANT":
                    self.assertTrue(all(v == p.base for v in p.table))
                elif p.kind == "LINEAR_TREND":
                    self.assertTrue(all(math.isclose(v, p.base + p.slope * k, rel_tol=1e-12, abs_tol=1e-9)
                                        for k, v in enumerate(p.table)))
        for kind in model.GRID_KINDS:
            g = synth.make_scenario(3, "S", "office", "S", grid_kind=kind, n_materials=5, n_equipment=2).operation.grid
            self.assertEqual(g.kind, kind)
            if kind == "CONSTANT":
                self.assertTrue(all(v == g.start for v in g.table))
            elif kind == "LINEAR_DECLINE_TO_FLOOR":
                self.assertTrue(all(math.isclose(v, max(g.floor, g.start - g.annual_decline * k), rel_tol=1e-12)
                                    for k, v in enumerate(g.table)))
            elif kind == "STEPWISE":
                for k, v in enumerate(g.table):
                    self.assertEqual(v, [st.value for st in g.steps if st.from_index <= k][-1])

    def test_dirty_scenario_lists_defects(self):
        d = synth.make_scenario(11, "SRC", "hospital", "S", dirty=True)
        kinds = {x.kind for x in d.meta.injected_defects}
        area = {"NON_POSITIVE_AREA", "AREA_BREAKDOWN_MISMATCH"}  # one of the two per scenario
        self.assertEqual(kinds | area, set(model.DEFECT_KINDS))
        self.assertEqual(len(kinds & area), 1)
        forced = synth.make_scenario(11, "SRC", "hospital", "S", dirty=True, defect_kinds=["NON_POSITIVE_AREA"])
        self.assertEqual({x.kind for x in forced.meta.injected_defects}, {"NON_POSITIVE_AREA"})

    def test_populations(self):
        sizes = [(s.meta.size_class, len(s.materials)) for s in population.standard_benchmark()]
        self.assertEqual(sizes, [("S", 200), ("M", 2000), ("L", 20000)])
        pop = list(population.verification_population(24, 5, max_size="S"))
        self.assertEqual({(p.meta.structure, p.meta.use) for p in pop},
                         {(a, b) for a in model.STRUCTURES for b in model.USES})
        names = [n for n, _ in population.edge_cases()]
        self.assertEqual(len(names), len(set(names)))
        self.assertGreaterEqual(len(names), 30)


if __name__ == "__main__":
    unittest.main()
