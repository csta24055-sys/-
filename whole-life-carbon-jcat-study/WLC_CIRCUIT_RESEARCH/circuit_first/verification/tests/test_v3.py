"""V3 verifier regression tests on snapshot 96df403 (fast subset). Run from this directory:
    CF_SNAPSHOT=<C snapshot>/whole-life-carbon-jcat-study/WLC_CIRCUIT_RESEARCH/circuit_first \\
    PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0 math7-py -B -m unittest -v test_v3
"""
import copy
import os
import sys
import unittest
from fractions import Fraction as F

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "code"))
import v3_crossbar as xb  # noqa: E402  (asserts the frozen oracle, imports the snapshot)
import v2_crossbar  # noqa: E402


class ReducedCrossbar(unittest.TestCase):
    def test_E1_independent_solution_equals_stageB_taps(self):
        r = xb.audit("E1", xb.scenarios.evaluation_set(10)[1])
        self.assertEqual(r["solve"]["unknown_after_propagation"], 0)
        self.assertEqual(r["solve"]["kcl_max_residual"], "0")
        self.assertEqual(r["vs_B2_stageB_taps"]["mismatch"], [])
        self.assertEqual(r["vs_B2_stageB_taps"]["common"], 232)
        self.assertEqual(r["n_bad_sources"], 0)


class V2Defects(unittest.TestCase):
    def test_recovery_rate_one_runs_and_matches(self):
        from model_building import simulate_building
        scn = dict(xb.scenarios.edge_set())["recovery_extremes"]
        out = simulate_building(scn, [33.3], "original")
        ref = xb.baseline.run_reference(xb.scenarios.with_period(scn, 33.3))["SUM-03"]["value"]
        self.assertLess(abs(float(out["by_T"][F(33.3)]["C"]) - ref) / ref, 1e-9)

    def test_refrigerant_duplicate_change_year_rejected(self):
        from model_building import simulate_building
        s = copy.deepcopy(dict(xb.scenarios.edge_set())["top_up_none"])
        s.refrigerants[0].change_years, s.refrigerants[0].service_life = [5.0, 5.0], None
        self.assertEqual(xb.scenarios.valid_domain(s), [])          # inside the formal source domain
        with self.assertRaises(ValueError):
            simulate_building(s, [6.000001], "original")


if __name__ == "__main__":
    unittest.main()
