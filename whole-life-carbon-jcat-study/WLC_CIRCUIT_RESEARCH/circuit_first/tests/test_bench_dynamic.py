"""CF1 benches with dynamics: RC charge / resistor heat, constant-current integration,
AC resistor energy, ideal-diode half wave, series RLC (S3), scale invariance.
Analytic references are closed forms written here, not produced by the engine."""
import math
import unittest
from fractions import Fraction as F

from _util import audit_dump, save

from engine import Netlist, Simulator
from engine.audit import num


def last_rec_at(sim, t, tag="arrive"):
    for r in sim.sol.records:
        if r["tag"] == tag and abs(float(num(r["t"])) - t) < 1e-12:
            return r
    raise KeyError(t)


class DynamicBenches(unittest.TestCase):
    def test_rc_charge_and_heat(self):
        V, R, C = 5.0, 2.0, 0.5
        tau = R * C
        nl = Netlist()
        nl.V("Vs", "a", "0", V)
        nl.R("R", "a", "c", R=R)
        nl.C("C", "c", "0", C, v0=0.0)
        out = {}
        for T in (0.7, 5.0, 40.0):
            sim = Simulator(nl, exact=False)
            sim.run(T)
            vc = sim.s[0]
            heat = sim.sol.meters_cont["R"]
            src = -sim.sol.meters_cont["Vs"]
            a_vc = V * (1 - math.exp(-T / tau))
            a_heat = 0.5 * C * V * V * (1 - math.exp(-2 * T / tau))
            a_src = C * V * V * (1 - math.exp(-T / tau))
            self.assertAlmostEqual(vc, a_vc, delta=1e-12 * V)
            self.assertAlmostEqual(heat, a_heat, delta=1e-12 * C * V * V)
            self.assertAlmostEqual(src, a_src, delta=1e-12 * C * V * V)
            self.assertAlmostEqual(src, heat + 0.5 * C * vc * vc, delta=1e-12)
            out[T] = {"v_C": vc, "heat": heat, "analytic_heat": a_heat, "src": src}
            s = audit_dump(self, sim.dump(), exact=False)
        # t -> infinity: resistor heat = C V^2 / 2 independent of R
        self.assertAlmostEqual(out[40.0]["heat"], 0.5 * C * V * V, delta=1e-12)
        save("bench_rc_charge.json", {"results": out, "audit_last": s, "dump_last": sim.dump()})

    def test_constant_current_integration(self):
        nl = Netlist()
        nl.I("I", "0", "c", F(2))
        nl.C("C", "c", "0", F(4))
        sim = Simulator(nl, exact=True)
        sim.run(F(3))
        self.assertEqual(sim.s[0], F(2) * 3 / 4)
        self.assertEqual(sim.sol.meters_cont["C"], F(4) * F(3, 2) ** 2 / 2)
        self.assertEqual(-sim.sol.meters_cont["I"], F(2) ** 2 * 9 / (2 * 4))   # I^2 t^2 / 2C
        s = audit_dump(self, sim.dump())
        save("bench_const_current.json", {"v": "3/2", "E": "9/2", "audit": s, "dump": sim.dump()})

    def test_ac_resistor_energy(self):
        # lossless LC tank -> i_L = V sqrt(C/L) sin(wt); CCCS copies it into R
        Vc0, Ct, Lt, R = 1.0, 1.0, 0.25, 3.0
        w = 1 / math.sqrt(Lt * Ct)
        Iamp = Vc0 * math.sqrt(Ct / Lt)
        nl = Netlist()
        nl.C("Ct", "n", "0", Ct, v0=Vc0)
        nl.L("Lt", "n", "m", Lt, i0=0.0)
        nl.V("Am", "m", "0", 0.0)                 # ammeter
        nl.add(__import__("engine").CCCS("F", "0", "r", "Am", 1.0))
        nl.R("R", "r", "0", R=R)
        res = {}
        for T in (0.3, 1.0, math.pi, 7.77):
            sim = Simulator(nl, exact=False)
            sim.run(T)
            E = sim.sol.meters_cont["R"]
            Irms2 = Iamp ** 2 / 2
            a = Irms2 * R * (T - math.sin(2 * w * T) / (2 * w))
            self.assertAlmostEqual(E, a, delta=1e-10)
            # tank energy conserved
            self.assertAlmostEqual(0.5 * Ct * sim.s[0] ** 2 + 0.5 * Lt * sim.s[1] ** 2, 0.5 * Ct * Vc0 ** 2, delta=1e-12)
            res[T] = {"E_R": E, "analytic": a}
        s = audit_dump(self, sim.dump(), exact=False)
        save("bench_ac_energy.json", {"results": res, "audit": s, "dump": sim.dump()})

    def test_diode_half_wave(self):
        Vc0, Ct, Lt, R = 1.0, 1.0, 0.25, 2.0
        w = 2.0
        nl = Netlist()
        nl.C("Ct", "n", "0", Ct, v0=Vc0)          # v = cos(2t)
        nl.L("Lt", "n", "0", Lt)
        nl.opamp("Buf", "n", "s", "s")            # unity follower
        nl.diode("D", "s", "k")
        nl.R("R", "k", "0", R=R)
        T = 2 * math.pi                            # two periods
        sim = Simulator(nl, exact=False, scan_step=0.01)
        sim.run(T)
        E = sim.sol.meters_cont["R"]
        a = 2 * (math.pi / 4) / R                            # per period P/4 with P = pi
        self.assertAlmostEqual(E, a, delta=1e-9)
        flips = [e for e in sim.sol.events if e["type"] == "diode"]
        # conduction ends at pi/4, restarts at 3pi/4, ... (cos crosses zero)
        times = [float(num(e["t"])) for e in flips]
        expect = [math.pi / 4 + k * math.pi / 2 for k in range(4)]
        self.assertEqual(len(times), 4)
        for x, y in zip(times, expect):
            self.assertAlmostEqual(x, y, delta=1e-9)
        s = audit_dump(self, sim.dump(), exact=False, tol=1e-8)
        save("bench_diode_half_wave.json", {"E_R": E, "analytic": a, "diode_events": times, "audit": s, "dump": sim.dump()})

    def test_series_rlc(self):
        V, R, L, C = 1.0, 1.0, 1.0, 0.25
        a = R / (2 * L)
        wd = math.sqrt(1 / (L * C) - a * a)
        nl = Netlist()
        nl.V("Vs", "p", "0", V)
        nl.R("R", "p", "q", R=R)
        nl.L("L", "q", "r", L)
        nl.C("C", "r", "0", C)
        res = {}
        for T in (0.5, 2.0, 9.0):
            sim = Simulator(nl, exact=False)
            sim.run(T)
            qc = C * sim.s[sim.sidx["C"]]
            aq = C * V * (1 - math.exp(-a * T) * (math.cos(wd * T) + a / wd * math.sin(wd * T)))
            self.assertAlmostEqual(qc, aq, delta=1e-12)
            i = sim.s[sim.sidx["L"]]
            heat = sim.sol.meters_cont["R"]
            self.assertAlmostEqual(V * qc, heat + qc * qc / (2 * C) + 0.5 * L * i * i, delta=1e-12)
            res[T] = {"q": qc, "analytic_q": aq, "heat": heat}
        # S3 refutation facts: bounded charge (q -> CV), heat of a step -> C V^2 / 2
        sim = Simulator(nl, exact=False)
        sim.run(60.0)
        self.assertAlmostEqual(C * sim.s[sim.sidx["C"]], C * V, delta=1e-12)
        self.assertAlmostEqual(sim.sol.meters_cont["R"], 0.5 * C * V * V, delta=1e-12)
        s = audit_dump(self, sim.dump(), exact=False)
        save("bench_series_rlc.json", {"results": res, "q_inf": C * V, "heat_inf": 0.5 * C * V * V, "audit": s, "dump": sim.dump()})

    def test_scale_invariance(self):
        """Impedance scaling (R k, C/k, L k): voltages unchanged, currents / k.
        Time scaling (C k, L k): waveforms at k t equal the originals at t, energies x k."""
        def run(Rk, Ck, Lk, T):
            nl = Netlist()
            nl.V("Vs", "p", "0", 1.0)
            nl.R("R", "p", "q", R=1.0 * Rk)
            nl.L("L", "q", "r", 1.0 * Lk)
            nl.C("C", "r", "0", 0.25 * Ck)
            sim = Simulator(nl, exact=False)
            sim.run(T)
            return sim.s[sim.sidx["C"]], sim.s[sim.sidx["L"]], sim.sol.meters_cont["R"]
        v0, i0, e0 = run(1, 1, 1, 1.3)
        k = 7.0
        v1, i1, e1 = run(k, 1 / k, k, 1.3)
        self.assertAlmostEqual(v1, v0, delta=1e-12)
        self.assertAlmostEqual(i1, i0 / k, delta=1e-12)
        self.assertAlmostEqual(e1, e0 / k, delta=1e-12)
        v2, i2, e2 = run(1, k, k, 1.3 * k)
        self.assertAlmostEqual(v2, v0, delta=1e-11)     # voltage at k t equals original at t
        self.assertAlmostEqual(i2, i0, delta=1e-11)     # current unchanged
        self.assertAlmostEqual(e2, k * e0, delta=1e-10)  # heat integral stretched by k
        save("bench_scale_invariance.json", {"base": [v0, i0, e0], "impedance_k": [v1, i1, e1], "time_k": [v2, i2, e2], "k": k})


if __name__ == "__main__":
    unittest.main()
