"""CF1 benches: resistive / op-amp networks and the homogeneity lemma L1 (exact arithmetic)."""
import unittest
from fractions import Fraction as F

from _util import audit_dump, save

from engine import Netlist, Simulator


def solve(nl, t=1):
    sim = Simulator(nl, exact=True)
    sim.run(F(t))
    return sim, sim.sol.records[-1]


def v(rec, n):
    from engine.audit import num
    return num(rec["v"][n])


def i(rec, n):
    from engine.audit import num
    return num(rec["i"][n])


class StaticBenches(unittest.TestCase):
    def test_divider_and_parallel(self):
        nl = Netlist()
        nl.V("V1", "a", "0", F(12))
        nl.R("R1", "a", "m", R=F(5))
        nl.R("R2", "m", "0", R=F(7))
        nl.I("I1", "0", "p", F(3))           # 3 A injected into node p
        nl.R("G1", "p", "0", G=F(1, 2))
        nl.R("G2", "p", "0", G=F(1, 4))
        sim, rec = solve(nl)
        # analytic: divider v_m = V R2/(R1+R2); parallel v_p = I/(G1+G2)
        self.assertEqual(v(rec, "m"), F(12) * 7 / 12)
        self.assertEqual(v(rec, "p"), F(3) / (F(1, 2) + F(1, 4)))
        self.assertEqual(i(rec, "G1") + i(rec, "G2"), 3)
        s = audit_dump(self, sim.dump())
        save("bench_divider_parallel.json", {"analytic": {"v_m": "7", "v_p": "4"}, "audit": s, "dump": sim.dump()})

    def test_joule_constant_current(self):
        # R = 3 ohm, I = 2 A, t = 5 s -> P = 12 W, E = 60 J (metered integral of i^2 R)
        nl = Netlist()
        nl.I("I1", "0", "a", F(2))
        nl.R("R", "a", "0", R=F(3))
        sim = Simulator(nl, exact=True)
        sim.run(F(5))
        rec = sim.sol.records[0]
        p = i(rec, "R") ** 2 * F(3)
        self.assertEqual(p, 12)
        self.assertEqual(sim.sol.meters_cont["R"], 60)
        self.assertEqual(sim.sol.meters_cont["I1"], -60)   # source delivers 60 J
        s = audit_dump(self, sim.dump())
        save("bench_joule_R3_I2_t5.json", {"analytic": {"P_W": 12, "E_J": 60}, "metered_E": "60", "audit": s, "dump": sim.dump()})

    def test_inverting_summer_and_feedback(self):
        nl = Netlist()
        nl.V("V1", "s1", "0", F(2))
        nl.V("V2", "s2", "0", F(-3))
        nl.R("G1", "s1", "x", G=F(1))
        nl.R("G2", "s2", "x", G=F(1, 2))
        nl.opamp("A", "0", "x", "o")
        nl.R("Rf", "x", "o", R=F(4))
        # x = in + w x  -> x = in/(1-w): non-inverting stage with pot feedback (1-w) to inn
        w = F(3, 4)
        nl.V("Vin", "vin", "0", F(5, 2))
        nl.opamp("B", "vin", "fb", "y")
        nl.pot("P", "y", "fb", "0", F(1000), w)
        sim, rec = solve(nl)
        self.assertEqual(v(rec, "o"), -4 * (F(1) * 2 + F(1, 2) * -3))
        self.assertEqual(v(rec, "y"), F(5, 2) / (1 - w))
        s = audit_dump(self, sim.dump())
        save("bench_summer_feedback.json", {"analytic": {"v_o": "-2", "v_y": "10"}, "audit": s, "dump": sim.dump()})

    def _ladder(self, lam=1, mu=1, current_driven=False):
        nl = Netlist()
        if current_driven:
            nl.I("S1", "0", "a", mu * F(2))
        else:
            nl.V("S1", "a", "0", mu * F(9))
        nl.V("S2", "d", "0", mu * F(-4))
        G = {"Ga": F(1, 3), "Gb": F(2, 5), "Gc": F(1, 7), "Gd": F(3, 2), "Ge": F(5, 11)}
        nl.R("Ga", "a", "b", G=lam * G["Ga"])
        nl.R("Gb", "b", "0", G=lam * G["Gb"])
        nl.R("Gc", "b", "c", G=lam * G["Gc"])
        nl.R("Gd", "c", "0", G=lam * G["Gd"])
        nl.R("Ge", "c", "d", G=lam * G["Ge"])
        sim, rec = solve(nl)
        return {k: i(rec, k) for k in G}, {n: v(rec, n) for n in "abc"}

    def test_L1_homogeneity_only(self):
        """Homogeneity check ONLY (not a proof of lemma L1): voltage-source drive scales every
        current by lam when all G are scaled by lam; sources enter linearly. Degree-1 homogeneity
        does not by itself exclude products G1*G2/G0 (verifier V1: argument gap); L1 stays [H]."""
        base_i, base_v = self._ladder()
        lam = F(3)
        i3, v3 = self._ladder(lam=lam)
        for k in base_i:
            self.assertEqual(i3[k], lam * base_i[k])
        for n in base_v:
            self.assertEqual(v3[n], base_v[n])
        mu = F(-5, 2)
        im, _ = self._ladder(mu=mu)
        for k in base_i:
            self.assertEqual(im[k], mu * base_i[k])
        # pure current-source drive: currents invariant, voltages scale by 1/lam
        def idrive(lam):
            nl = Netlist()
            nl.I("S", "0", "a", F(2))
            nl.R("Ga", "a", "b", G=lam * F(1, 3))
            nl.R("Gb", "b", "0", G=lam * F(2, 5))
            nl.R("Gc", "a", "0", G=lam * F(1, 7))
            _, rec = solve(nl)
            return {k: i(rec, k) for k in ("Ga", "Gb", "Gc")}, v(rec, "a")
        ci1, va1 = idrive(F(1))
        ci3, va3 = idrive(lam)
        self.assertEqual(ci1, ci3)
        self.assertEqual(va3, va1 / lam)
        # Explicit two-conductance product test: series G1, G2 from V: i = V G1 G2/(G1+G2)
        def series_current(G1, G2):
            nl = Netlist()
            nl.V("V", "a", "0", F(1))
            nl.R("G1", "a", "m", G=G1)
            nl.R("G2", "m", "0", G=G2)
            _, rec = solve(nl)
            return i(rec, "G1")
        g1, g2 = F(2), F(5)
        f1 = series_current(g1, g2)
        f2 = series_current(2 * g1, 2 * g2)
        self.assertEqual(f2, 2 * f1)          # degree 1
        self.assertNotEqual(f2, 4 * f1)       # a bilinear product G1*G2 would give 4x
        # a product of two inputs needs a source as one factor (Ohm: i = G * V)
        nl = Netlist()
        nl.V("V", "a", "0", F(7))
        nl.R("G", "a", "0", G=F(3))
        _, rec = solve(nl)
        self.assertEqual(i(rec, "G"), 21)
        save("bench_L1_homogeneity.json", {
            "currents_base": base_i, "currents_lam3": i3, "currents_mu": im,
            "series_f(G)": f1, "series_f(2G)": f2,
            "claim": "voltage-source drive: currents homogeneous of degree 1 in the conductances; product of two conductance-coded inputs impossible in a passive network"})


if __name__ == "__main__":
    unittest.main()
