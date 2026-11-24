"""Regression tests for the independent verifier's V2 findings (V2-D1 ... V2-D5), against the
frozen oracle (test-side import only)."""
import copy
import os
import sys
import unittest
from fractions import Fraction as F

from _util import ROOT, save

STUDY = os.path.normpath(os.path.join(ROOT, "..", ".."))
sys.path.insert(0, os.path.join(STUDY, "10_TRANSFORM_STUDY", "research_code"))
from tstudy import baseline, scenarios  # noqa: E402

baseline.assert_frozen()
from model_building import simulate_building  # noqa: E402

TOL = 1e-9


def rel(a, b):
    a, b = float(a), float(b)
    return abs(a - b) / abs(b) if b else abs(a)


def ref_stages(scn, T):
    return baseline.run_reference(scenarios.with_period(scn, T))["X-02"]["by_stage"]


class V2Fixes(unittest.TestCase):
    def test_D1_recovery_rate_one(self):
        scn = dict(scenarios.edge_set())["recovery_extremes"]
        Ts = [7.5, 33.3]
        r = simulate_building(scn, Ts, "original")
        for T in Ts:
            ref = ref_stages(scn, T)
            for st, v in ref.items():
                self.assertLessEqual(rel(r["by_T"][F(T)]["stages"].get(st, 0), v), TOL, (T, st))

    def test_D2_stepwise_grid_and_D4_mdac_msb(self):
        """STEPWISE grid steps switch by comparators (no Python bit decoding); a point T > 128
        exercises the MDAC MSB (kills mutant 'MDAC MSB weight +1')."""
        scn = dict(scenarios.edge_set())["linear_trend_profiles"]
        Ts = [33.3, 129.5]
        good = simulate_building(scn, Ts, "original", ("OP",))
        bad = simulate_building(scn, Ts, "original", ("OP",), mutations=("mdac_msb_plus1",))
        for T in Ts:
            ref = ref_stages(scn, T)
            for st in ("B2", "B6", "B7"):
                self.assertLessEqual(rel(good["by_T"][F(T)]["stages"][st], ref[st]), TOL, (T, st))
        self.assertGreater(max(rel(bad["by_T"][F(129.5)]["stages"][st], ref_stages(scn, 129.5)[st])
                               for st in ("B6", "B7")), TOL)
        self.assertEqual(good["kinds"]["grid"], "STEPWISE")
        dec = [e for e in good["core"].nl.elements if e.name.startswith("gr.L") and e.kind == "CMP"]
        self.assertTrue(dec)

    def test_D3_no_dangling_mutation_input(self):
        scn = scenarios.benchmark()[0]
        r = simulate_building(scn, [1], "original", ("REF",))
        for e in r["core"].nl.elements:
            if getattr(e, "inputs", None):
                self.assertFalse(any(x.endswith(".hs3") for x in e.inputs), e.name)

    def test_D4_b5_base_includes_A4(self):
        scn = scenarios.evaluation_set(10)[0]        # MAJOR_REFURBISHMENT, cycle 82
        T = 99.9
        good = simulate_building(scn, [T], "original", ("AC", "EV"))
        bad = simulate_building(scn, [T], "original", ("AC", "EV"), mutations=("b5_without_A4",))
        ref = ref_stages(scn, T)
        self.assertGreater(ref["B5"], 0)
        self.assertLessEqual(rel(good["by_T"][F(T)]["stages"]["B5"], ref["B5"]), TOL)
        self.assertGreater(rel(bad["by_T"][F(T)]["stages"]["B5"], ref["B5"]), TOL)

    def test_D4_epd_validity_inclusive(self):
        scn = copy.deepcopy(scenarios.benchmark()[0])
        row = next(r for r in scn.materials if r.epd is not None and scn.factors[r.epd.factor_id].valid_until)
        scn.project.assessment_date = scn.factors[row.epd.factor_id].valid_until   # equality case
        good = simulate_building(scn, [1], "original", ("AC",))
        bad = simulate_building(scn, [1], "original", ("AC",), mutations=("epd_strict",))
        ref = ref_stages(scn, 1)
        self.assertLessEqual(rel(good["by_T"][F(1)]["stages"]["A1-A3"], ref["A1-A3"]), TOL)
        self.assertGreater(rel(bad["by_T"][F(1)]["stages"]["A1-A3"], ref["A1-A3"]), TOL)

    def test_D5_duplicate_years(self):
        scn = copy.deepcopy(scenarios.benchmark()[0])
        eq = next(e for e in scn.equipment if e.replacement_event_list)
        y = eq.replacement_event_list[0]
        eq.replacement_event_list = [y, y] + eq.replacement_event_list[1:]
        Ts = [F(y) - F(1, 2), F(y) + F(1, 2), F(55)]
        r = simulate_building(scn, Ts, "original", ("AC", "EV"))
        rows = {}
        for T in Ts:
            res = baseline.run_reference(scenarios.with_period(scn, float(T)))
            for st in ("B3", "B4"):
                self.assertLessEqual(rel(r["by_T"][T]["stages"][st], res["X-02"]["by_stage"][st]), TOL, (T, st))
            rows[str(T)] = {"B4": float(r["by_T"][T]["stages"]["B4"]), "ref": res["X-02"]["by_stage"]["B4"],
                            "events_ref": res["B4-01"]["n_events"]}
        dev = copy.deepcopy(scenarios.benchmark()[0])
        d = next(x for x in dev.refrigerants if x.change_years)
        d.change_years = [d.change_years[0]] + list(d.change_years)
        with self.assertRaises(ValueError):
            simulate_building(dev, [1], "original", ("REF",))
        save("v2_D5_duplicates.json", rows)


if __name__ == "__main__":
    unittest.main()
