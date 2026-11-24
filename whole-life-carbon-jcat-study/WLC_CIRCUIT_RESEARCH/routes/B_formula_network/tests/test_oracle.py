"""Kernel netlists vs the frozen oracles (refcalc primary, msp/unified second) on scenarios S and M of the
frozen generator's standard benchmark. Run with
    PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0 python3 -B -m unittest discover -s <route>/tests -v
No network. Fictional data only. ~1 min."""
import os
import sys
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "code"))
import oracle_io as O  # noqa: E402

RUNS = SUMMARY = None


def setUpModule():
    global RUNS, SUMMARY
    import route_b_experiments as X
    RUNS = [X.run_scenario(s, log=lambda *a: None) for s in O.representative_scenarios(("S", "M"))]
    SUMMARY = X.summarise(RUNS)


class TestFrozen(unittest.TestCase):
    def test_frozen_and_clean(self):
        trees = O.setup()["baseline"].assert_frozen()
        self.assertEqual(trees["refcalc"], "8976efea85c313e5e723fadf12382e02b3202913")
        self.assertEqual(O.pycache_dirs(), [])


class TestKernels(unittest.TestCase):
    TOL = 1e-9
    REQUIRED = ["B4-02 [P1 pieces]", "B5-01 [P1 pieces]", "B6-03 [P1 pieces]", "B6-03 [P1 pieces, integrator]",
                "B7-04 [P1 pieces]", "B7-04 [P1 pieces, integrator]", "B3-01 [P1 pieces]", "B1-03 [P1 pieces]",
                "B1-02 [P1 cells]", "B1-04 [P1 jump pieces]", "B1-02 [raw S/H automaton]", "B1-03 [raw S/H automaton]",
                "B1-04 [raw S/H automaton]", "B2-01 [gain x year cells]", "B4-01 n_events [raw comparator bank]",
                "SUM-03 [gain + summing node]", "SUM-06 [gain 0.001]", "SUM-05 [external digital division]",
                "A13-01 [DC source]", "C1-01 [DC source]", "C4-01 [DC source]", "X-14 [DC source]"]

    def test_each_kernel_within_tolerance(self):
        for k in self.REQUIRED:
            with self.subTest(kernel=k):
                d = SUMMARY[k]
                self.assertGreater(d["n"], 40)
                self.assertEqual(d["n_fail"], 0)
                self.assertLessEqual(d["max_rel_ref_asserted"], self.TOL)

    def test_grid_has_boundary_points(self):
        for run in RUNS:
            labels = {l for _, l in run["grid"]}
            self.assertTrue({"contract", "band_in", "band_out", "knife"} <= labels)

    def test_automaton_matches_refcalc_inside_band_where_interval_form_does_not(self):
        rows = [r for run in RUNS for r in run["rows"] if r["label"] == "band_in" and r["scenario"].endswith("seed102")]
        sh = {r["T"]: r["rel_ref"] for r in rows if r["kernel"] == "B1-04 [raw S/H automaton]"}
        iv = {r["T"]: r["rel_ref"] for r in rows if r["kernel"] == "B1-04 [msp interval]"}
        self.assertTrue(all(v <= 1e-12 for v in sh.values()))
        self.assertGreater(max(iv.values()), 1e-3)     # known deviation of the interval form (03 3.4), observed

    def test_late_reset_ablation_is_a_counterexample(self):
        rows = [r for run in RUNS for r in run["rows"] if r["kernel"] == "B1-04 [raw S/H, no late reset]"]
        self.assertGreater(max(r["rel_ref"] for r in rows), 1e-2)


if __name__ == "__main__":
    unittest.main()
