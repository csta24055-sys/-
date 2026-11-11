"""Tests of the unified model: agreement with the reference and the mechanisms it claims to use.

Run:  cd research_code && python3 -m unittest tests.test_engine -v
"""
import copy
import unittest

import synth
from common.compare import compare
from fastcalc import engine
from refcalc import registry
from synth import population

registry.load_all()
SMALL = {"n_materials": 40, "n_equipment": 12, "n_refrigerants": 4}


def agree(testcase, scn, detail=True):
    ref = registry.run_all(scn)
    got = engine.evaluate(scn, detail=detail)
    scale = abs(ref["SUM-03"]["value"]) or 1.0
    for uid in ref:
        c = compare(ref[uid], got.get(uid, {}), floor=1e-9 * scale, ignore_missing=not detail)
        testcase.assertTrue(c.within(1e-9) and (not detail or not c.extra), (uid, c.worst_path, c.mismatches[:2], c.missing[:2], c.extra[:2]))
    return ref, got


class EngineTests(unittest.TestCase):
    def test_agrees_with_reference(self):
        for name, scn in population.edge_cases():
            with self.subTest(case=name):
                agree(self, scn, True)
                agree(self, scn, False)

    def test_totals_mode_multiplies_no_factor_per_row_and_runs_no_year_loop(self):
        """The mechanisms the unified model claims, counted."""
        scn = synth.make_scenario(5, "RC", "office", "S", 60.0, profile_kind="LINEAR_TREND",
                                  grid_kind="LINEAR_DECLINE_TO_FLOOR", n_materials=400, n_equipment=120, n_refrigerants=10)
        res = engine.evaluate(scn, detail=False)
        st = res["_stats"]
        self.assertEqual(st["row_factor_products"], 0)        # factors are applied to summed activities only
        self.assertEqual(st["year_loop_iterations"], 0)       # every year sum is a closed form here
        self.assertEqual(st["event_lists_built"], 0)          # renewal counts come from the count function
        A = engine.aggregate(scn, False)
        distinct = len({tuple((c.factor_id, c.mass_fraction) for c in row.composition) for row in scn.materials if row.composition})
        self.assertEqual(st["recipes_computed"], distinct)    # one composite factor per distinct composition
        self.assertLess(st["factor_resolutions"], res["SYS-02"]["n_checked"])
        n_lines = sum(len(t) for t in res["_tables"].values())
        self.assertLess(n_lines, 6 * len(scn.factors))        # the tables hold factor keys, not rows
        self.assertLess(len(A.groups), len(scn.materials) + len(scn.equipment))
        full = engine.evaluate(scn, detail=True)["_stats"]
        self.assertEqual(full["row_factor_products"], len(scn.materials) + len(scn.equipment))
        self.assertGreater(full["year_loop_iterations"], 0)   # the yearly series still need one value per year

    def test_table_inputs_fall_back_to_a_year_scan(self):
        scn = synth.make_scenario(5, "RC", "office", "S", 60.0, profile_kind="TABLE", grid_kind="TABLE", **SMALL)
        st = engine.evaluate(scn, detail=False)["_stats"]
        self.assertGreater(st["year_loop_iterations"], 0)
        agree(self, scn, False)

    def test_sweep_from_one_aggregation(self):
        scn = synth.make_scenario(6, "S", "retail", "S", 60.0, **SMALL)
        periods = (25.0, 60.0, 62.5, 99.9)
        got = engine.sweep(scn, periods)
        for T in periods:
            other = copy.deepcopy(scn)
            other.boundary.study_period = T
            ref = registry.run_all(other)
            for uid in ("X-02", "SUM-03", "B4-02", "B3-01", "B1-02", "B6-03"):
                c = compare(ref[uid], got[T][uid], floor=1e-9 * abs(ref["SUM-03"]["value"]), ignore_missing=True)
                self.assertTrue(c.within(1e-9), (T, uid, c.worst_path))

    def test_baseline_needs_no_hidden_state(self):
        scn = synth.make_scenario(8, "RC", "office", "S", 60.0, **SMALL)
        base = population.attach_baseline(scn)
        first = engine.evaluate(scn, detail=False)["SUM-08"]
        for row in base.materials:
            row.quantity *= 2.0
        ref = registry.run_all(scn, ids=["SUM-08"])["SUM-08"]
        again = engine.evaluate(scn, detail=False)["SUM-08"]   # nothing was cached: the edit is seen
        self.assertTrue(compare(ref, again).within(1e-9))
        self.assertNotEqual(first["baseline"], again["baseline"])
        held = {}
        a = engine.evaluate(scn, detail=False, baseline_totals=held)["SUM-08"]
        b = engine.evaluate(scn, detail=False, baseline_totals=held)["SUM-08"]
        self.assertEqual(a, b)
        self.assertEqual(len(held), 1)

    def test_scenario_that_is_its_own_baseline(self):
        scn = synth.make_scenario(9, "RC", "office", "S", 60.0, **SMALL)
        population.BASELINES[scn.meta.scenario_id] = scn
        scn.boundary.baseline_scenario = scn.meta.scenario_id
        res = engine.evaluate(scn, detail=False)["SUM-08"]
        self.assertEqual(res["status"], "COMPARED")
        self.assertEqual(res["delta"], 0.0)

    def test_invalid_study_period_is_refused(self):
        for bad in (0.0, -5.0, float("nan"), float("inf")):
            scn = synth.make_scenario(9, "RC", "office", "S", 60.0, **SMALL)
            scn.boundary.study_period = bad
            with self.assertRaises(ValueError):
                engine.evaluate(scn)
            with self.assertRaises(ValueError):
                registry.run_all(scn)


if __name__ == "__main__":
    unittest.main()
