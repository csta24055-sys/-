"""G4 integration tests. Oracles are NOT the composed code:
  Phi : hand values written as literals (07 S5, architecture S1.2 as re-confirmed by A/D) and route D's rational
        event-ledger oracle (oracle_d.G); route A's published oracle rows (data).
  Psi : refcalc (frozen 09 reference) on evaluation_set EV2/EV9 (unused by every route), canon/timechar (frozen ch.17).
Run: PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0 python3 -B -m unittest discover -s tests -v
     (from WLC_CIRCUIT_RESEARCH/integration)
"""
import os
import sys
import unittest
from fractions import Fraction as F

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "code"))

import int_common as IC  # noqa: E402
import phi_hybrid as PH  # noqa: E402
import run_integration as RI  # noqa: E402


class TestPhiHandValues(unittest.TestCase):
    def test_p0_contract_right(self):
        for real in PH.REALIZATIONS:
            h = PH.Hybrid(PH.pilot("P0"), "right", real)
            got = h.run([10, 20, 30, 40, 60, 0, 1])
            self.assertEqual([got[F(t)] for t in (0, 1, 10, 20, 30, 40, 60)], [100, 104, 160, 255, 315, 410, 565])

    def test_three_conventions_at_10_and_knife(self):
        v = {c: PH.G("P0", F("10"), c) for c in PH.CONVENTIONS}
        self.assertEqual(v, {"right": 160, "left": 140, "orig": 140})
        v = {c: PH.G("P0", F("10.000000005"), c) for c in PH.CONVENTIONS}
        self.assertEqual(v, {"right": F("160.00000002"), "left": F("160.00000002"), "orig": F("140.00000002")})
        # closed band: at T = 10/(1-eps) orig still excludes the event
        t = F(10) / (1 - PH.EPS)
        self.assertEqual(PH.G("P0", t, "orig") + 20, PH.G("P0", t, "right"))

    def test_p1_p2_values(self):
        self.assertEqual([PH.G("P1", t, "right", "substitute") for t in (20, 40)], [250, 405])
        self.assertEqual([PH.G("P1", t, "right", "additional") for t in (20, 40)], [305, 460])
        self.assertEqual([PH.G("P1", 20, "left", p) for p in ("substitute", "additional")], [200, 200])
        self.assertEqual([PH.G("P2", t) for t in (10, 20, 30, 40, 60)], [160, 245, 295, 380, 515])

    def test_orig_undefined_for_p2_px(self):
        for case in ("P2", "Px"):
            with self.assertRaises(ValueError):
                PH.Hybrid(PH.pilot(case), "orig")

    def test_scale_invariance_and_capacitor_energy_is_not_carbon(self):
        outs = []
        for g, c in ((1, 1), (5, 2)):
            h = PH.Hybrid(PH.pilot("P0"), "right", "charge", gamma=g, C_cap=c)
            outs.append((h.G(40), h.capacitor_view()[1]))
        self.assertEqual(outs[0][0], outs[1][0])
        self.assertNotEqual(outs[0][1], outs[1][1])

    def test_joule_realization_units_and_kappa(self):
        self.assertEqual(F(3) * F(2) ** 2 * 5, 60)          # 07: R=3 ohm, I=2 A, t=5 s -> 60 J
        a = PH.Hybrid(PH.pilot("P2"), "right", "joule", R=3, kappa=F(1, 3)).G(30)
        b = PH.Hybrid(PH.pilot("P2"), "right", "joule", R=7, kappa=F(2, 9)).G(30)
        self.assertEqual(a, b)
        self.assertEqual(a, 295)

    def test_set_rule_order_free(self):
        vals = set()
        for order in (("AC", "PIPE"), ("PIPE", "AC")):
            for pol in ("substitute", "additional"):
                sp = PH.pilot("P1", pol)
                sp.clocks = {k: sp.clocks[k] for k in order}
                vals.add((pol, PH.Hybrid(sp, "right", "charge").G(20)))
        self.assertEqual(vals, {("substitute", 250), ("additional", 305)})

    def test_noncoincident_renovation_restarts_clocks(self):
        # P1' (integration-declared): renovation at 15 restarts AC (next 25) and pipe (next 35); nothing superseded
        h = PH.Hybrid(PH.pilot("P1", "substitute", tau_R=F(15)), "right", "charge")
        h.run([40])
        self.assertEqual([(t, k) for t, k, _ in h.ledger if t <= 40],
                         [(10, "AC"), (15, "RENOV"), (25, "AC"), (35, "AC"), (35, "PIPE")])


class TestPhiVsIndependentOracles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.res = RI.phi_check(n_random=300)

    def test_zero_mismatch_vs_route_D_ledger(self):
        self.assertEqual(self.res["total_mismatch"], 0, self.res["mismatches"][:3])
        self.assertGreaterEqual(len(self.res["cases"]), 19)

    def test_route_A_published_rows(self):
        a = self.res["A_points_rows_compared"]
        self.assertGreater(a["n"], 500)
        self.assertEqual(a["mismatch"], 0)

    def test_state_tuples(self):
        t = {(r["case"], r["conv"]): (tuple(r["state_tuple_charge"]), tuple(r["state_tuple_joule"])) for r in self.res["cases"]}
        self.assertEqual(t[("P0", "right")], ((3, 0, 2, 0), (4, 0, 2, 0)))
        self.assertEqual(t[("P1-substitute", "right")], ((3, 0, 3, 1), (4, 0, 3, 1)))
        self.assertEqual(t[("P2", "right")], ((3, 1, 2, 0), (4, 1, 2, 0)))


class TestX2Link(unittest.TestCase):
    def test_phi_orig_equals_B_theta_eps_netlist(self):
        r = RI.x2_link()
        self.assertLessEqual(r["max_rel"], 1e-15)
        self.assertGreaterEqual(len(r["rows"]), 15)


class TestPsiComposition(unittest.TestCase):
    T_SMALL = [0.5, 9.999999, 10.0, 10.000001, 20.0, 29.5, 47.9, 99.0]

    def test_ev9_and_ev2_vs_refcalc(self):
        r = RI.psi_check(("EV9", "EV2"), self.T_SMALL)
        for c in r["cases"]:
            self.assertEqual(c["T_skipped_domain"], [], c["scenario"])
            self.assertEqual(c["n_direct_units"], 21)
            self.assertEqual(c["n_comp_rows"], 22)
            self.assertTrue(c["stage_keys_equal_refcalc"])
            self.assertLessEqual(max(c["max_rel"].values()), 1e-9, c["max_rel"])
            self.assertEqual(c["refrigerant_unexpected"], [])
            n = c["control_naive_21_sources"]
            self.assertGreater(n["min_rel_err_vs_SUM03"], 1e-9)            # the naive 21-source sum is wrong ...
            self.assertLessEqual(n["max_rel(naive-C, B2-01)"], 1e-9)        # ... by exactly B2-01

    def test_beta_iota_b2_without_b2(self):
        r = RI.psi_check(("EV9-noB2",), [5.3, 30.0])
        c = r["cases"][0]
        self.assertNotIn("B2", c["included_stages"])
        self.assertLessEqual(max(c["max_rel"].values()), 1e-9)

    def test_integrator_cell_netlist_variant(self):
        r = RI.psi_check(("EV9",), [5.3, 12.25], "integrator")
        self.assertLessEqual(r["max_rel_overall"], 1e-9)


class TestX5Bridge(unittest.TestCase):
    def test_identity_on_ev9(self):
        r = RI.x5_bridge("EV9", (5.3, 47.9))
        self.assertTrue(r["B1_included"])
        self.assertEqual(len(r["rows"]), 2)
        for row in r["rows"]:
            self.assertTrue(row["C-M==Z (exact)"])
            self.assertTrue(row["Z!=0"])
            self.assertTrue(row["dC/dT!=rho"])
            self.assertTrue(row["dC/dT==rho+Z' (exact, forward difference on one affine piece)"])
            self.assertLessEqual(row["rel(C_composed, C_canon)"], 1e-12)
        # at 47.9 an atom of M lies within 1e-6 to the right, so the step must have been reduced
        self.assertNotEqual(r["rows"][1]["h_used"], "1/1000000")


class TestHygiene(unittest.TestCase):
    def test_frozen_and_no_pycache(self):
        trees = IC.frozen()["trees"]
        self.assertEqual(trees["refcalc"], "8976efea85c313e5e723fadf12382e02b3202913")
        self.assertEqual(IC.pycache_dirs(), [])


if __name__ == "__main__":
    unittest.main()
