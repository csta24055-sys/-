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
    RUNS = [X.run_scenario(s, log=lambda *a: None)
            for s in O.representative_scenarios(("S", "M")) + O.out_of_sample_scenarios()]
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

    # measured magnitudes (deterministic floats; recorded in results/points.json). Tolerance: relative 1e-6.
    # scenario suffix -> (msp interval B1-04 max rel in band_in, ablation B1-04 max rel, ablation B1-02 max rel)
    MEASURED = {"seed102": (0.031246940616269075, 0.03145563853488225, 0.03269157785511787),
                "seed659283900": (0.002668299017858878, 0.046251665148593656, 0.007283005256158638),
                "seed101": (0.0, 0.0, 0.0), "seed697085186": (0.0, 0.0, 0.0)}

    def _max(self, sid, kernel, labels=None):
        vals = [r["rel_ref"] for run in RUNS for r in run["rows"] if r["scenario"].endswith(sid) and r["kernel"] == kernel
                and (labels is None or r["label"] in labels)]
        self.assertTrue(vals)
        return max(vals)

    def _close(self, got, want):
        self.assertLessEqual(abs(got - want), 1e-6 * abs(want) + 1e-15, (got, want))

    def test_out_of_sample_scenarios_present(self):
        ids = [run["scenario"] for run in RUNS]
        self.assertIn("SYN-S-hospital-M-T60-seed659283900", ids)
        self.assertIn("SYN-RC-warehouse-S-T75-seed697085186", ids)

    def test_band_magnitudes_automaton_vs_interval_form(self):
        for sid, (iv, _, _) in self.MEASURED.items():
            with self.subTest(scenario=sid):
                self.assertEqual(self._max(sid, "B1-04 [raw S/H automaton]", {"band_in"}), 0.0)
                self._close(self._max(sid, "B1-04 [msp interval]", {"band_in"}), iv)
                # at T = tau(1+1e-9) = sw(tau) the interval form agrees again: the deviating set is the OPEN band (K, sw)
                self.assertLessEqual(self._max(sid, "B1-04 [msp interval]", {"knife"}), 1e-15)

    def test_late_reset_ablation_magnitudes(self):
        for sid, (_, a4, a2) in self.MEASURED.items():
            with self.subTest(scenario=sid):
                self._close(self._max(sid, "B1-04 [raw S/H, no late reset]"), a4)
                self._close(self._max(sid, "B1-02 [raw S/H, no late reset]"), a2)

if __name__ == "__main__":
    unittest.main()
