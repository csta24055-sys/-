"""V2 verifier regression tests on snapshot 80ec2de (fast subset). Run from this directory:
    CF_SNAPSHOT=<B2 snapshot>/whole-life-carbon-jcat-study/WLC_CIRCUIT_RESEARCH/circuit_first \\
    PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0 math7-py -B -m unittest -v test_v2
The frozen oracle (tstudy/refcalc) is imported only here and in ../code/v2_*.py.
DEFECT tests assert that a defect is still reproducible (they fail once it is fixed)."""
import json
import os
import sys
import unittest
from fractions import Fraction as F

sys.dont_write_bytecode = True
CODE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "code")
sys.path.insert(0, CODE)
from common import SNAP  # noqa: E402

STUDY = "/home/user/-/whole-life-carbon-jcat-study"
sys.path.insert(0, os.path.join(STUDY, "10_TRANSFORM_STUDY", "research_code"))
from tstudy import baseline, scenarios  # noqa: E402

baseline.assert_frozen()
sys.path.insert(0, SNAP)
from model_building import simulate_building  # noqa: E402
import v2_crossbar  # noqa: E402
import v2_d1_probe as probe  # noqa: E402


class V1FixesHold(unittest.TestCase):
    def test_falling_comparator_both_engines(self):
        for case, exp in (("gated_fall", "1"), ("gated_rise", "2"), ("touch_above", "3"), ("touch_below", "0")):
            for kind in ("sim", "hybrid"):
                self.assertEqual(probe.run_engine(kind, probe.build(case)).get("charge"), exp, (case, kind))

    def test_chattering_reported_not_hung(self):
        self.assertIn("does not terminate", probe.run_engine("hybrid", probe.build("self_feedback")).get("error", ""))


class Crossbar(unittest.TestCase):
    def test_independent_crossbar_solution_matches_taps(self):
        d = json.load(open(os.path.join(SNAP, "results", "stageB_netlists_E1.json")))
        v, info = v2_crossbar.solve(d["crossbar"])
        self.assertEqual(info["unknown_after_propagation"], 0)
        self.assertEqual(info["kcl_max_residual"], "0")
        core = {e["name"]: e for e in d["core"]}
        for name, t in d["taps"].items():
            self.assertEqual(F(core[t["core_source"]]["V"]) if "/" not in core[t["core_source"]]["V"] else
                             F(*map(int, core[t["core_source"]]["V"].split("/"))), v[t["crossbar_node"]], name)


class Oracle(unittest.TestCase):
    def test_edge_rebuild_within_period_three_T(self):
        scn = dict(scenarios.edge_set())["rebuild_within_period"]
        Ts = [16.000001, 33.3, 60.000001]
        out = simulate_building(scn, Ts, "original")
        for T in Ts:
            res = baseline.run_reference(scenarios.with_period(scn, T))
            self.assertLess(abs(float(out["by_T"][F(T)]["C"]) - res["SUM-03"]["value"]) / abs(res["SUM-03"]["value"]), 1e-9)

    def test_DEFECT_recovery_rate_one_crashes(self):
        scn = dict(scenarios.edge_set())["recovery_extremes"]
        self.assertEqual(scenarios.valid_domain(scn), [])
        with self.assertRaises(ZeroDivisionError):
            simulate_building(scn, [1], "original")


if __name__ == "__main__":
    unittest.main()
