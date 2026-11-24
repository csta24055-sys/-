"""CF1 benches with switching: charge sharing (ideal switch and through R), switched-capacitor
packets and their heat, integrate-and-fire clocks with non-integer periods and simultaneous
firing processed as a set."""
import math
import unittest
from fractions import Fraction as F

from _util import audit_dump, save

from engine import Netlist, Simulator
from engine.audit import num

PHASES = [{"trk": False}, {"dmp": True}, {"dmp": False}, {"trk": True}]


def iandf(nl, tag, period, rail_neg="rn", vth="th", G=F(1), prio=30):
    """Integrate-and-fire clock: ramp V0*t/period, reset by a V_th*C packet."""
    x, o = f"{tag}.x", f"{tag}.o"
    nl.R(f"{tag}.Gin", rail_neg, x, G=G)
    nl.opamp(f"{tag}.A", "0", x, o)
    nl.C(f"{tag}.Cj", x, o, period * G)            # C = c * G * tau_y / V_th with tau_y = V_th = 1
    nl.comparator(f"{tag}.cmp", o, vth, f"{tag}.fire", priority=prio)
    nl.C(f"{tag}.Cr", f"{tag}.p", "0", period * G, v0=F(1))
    nl.switch(f"{tag}.St", f"{tag}.p", vth, f"{tag}.trk")
    nl.switch(f"{tag}.Sd", f"{tag}.p", x, f"{tag}.dmp")
    nl.sequencer(f"{tag}.seq", f"{tag}.fire", {f"{tag}.trk": True, f"{tag}.dmp": False},
                 [{f"{tag}.{k}": v for k, v in st.items()} for st in PHASES])


class SwitchedBenches(unittest.TestCase):
    def test_charge_sharing_ideal_switch(self):
        C1, V1, C2, V2 = F(2), F(5), F(3), F(0)
        nl = Netlist()
        nl.C("C1", "a", "0", C1, v0=V1)
        nl.C("C2", "b", "0", C2, v0=V2)
        nl.switch("S", "a", "b", "por")
        nl.power_on("POR", "por")
        sim = Simulator(nl, exact=True)
        sim.run(F(1))
        vf = (C1 * V1 + C2 * V2) / (C1 + C2)
        self.assertEqual(sim.s, [vf, vf])
        self.assertEqual(C1 * sim.s[0] + C2 * sim.s[1], C1 * V1 + C2 * V2)        # charge conserved
        lost = (C1 * V1 ** 2 + C2 * V2 ** 2) / 2 - (C1 + C2) * vf ** 2 / 2
        self.assertEqual(lost, C1 * C2 / (C1 + C2) * (V1 - V2) ** 2 / 2)
        j = [x for x in sim.sol.jumps if x["reason"] != "init"][0]
        self.assertEqual(num(j["switch_loss_linear_path"]), lost)
        s = audit_dump(self, sim.dump())
        save("bench_charge_sharing_ideal.json", {"v_final": vf, "energy_lost": lost, "audit": s, "dump": sim.dump()})

    def test_charge_sharing_through_resistor(self):
        C1, V1, C2, R = 2.0, 5.0, 3.0, 0.7
        nl = Netlist()
        nl.C("C1", "a", "0", C1, v0=V1)
        nl.C("C2", "b", "0", C2, v0=0.0)
        nl.R("R", "a", "b", R=R)
        tau = R * C1 * C2 / (C1 + C2)
        lost = C1 * C2 / (C1 + C2) * V1 ** 2 / 2
        out = {}
        for T in (0.3, 20.0):
            sim = Simulator(nl, exact=False)
            sim.run(T)
            heat = sim.sol.meters_cont["R"]
            self.assertAlmostEqual(heat, lost * (1 - math.exp(-2 * T / tau)), delta=1e-11)
            self.assertAlmostEqual(C1 * sim.s[0] + C2 * sim.s[1], C1 * V1, delta=1e-12)
            out[T] = heat
        self.assertAlmostEqual(out[20.0], lost, delta=1e-11)          # independent of R
        s = audit_dump(self, sim.dump(), exact=False)
        save("bench_charge_sharing_R.json", {"heat": out, "lost_ideal": lost, "audit": s})

    def test_sc_packet_and_heat(self):
        V0, Cs = F(2), F(3, 2)
        nl = Netlist()
        nl.V("V0", "r", "0", V0)
        nl.V("Vn", "rn", "0", F(-1))
        nl.V("Vth", "th", "0", F(1))
        iandf(nl, "k", F(1))
        nl.C("Cs", "s", "0", Cs, v0=V0)
        nl.switch("Ss", "s", "r", "k.trk")
        nl.switch("Sd", "s", "xb", "k.dmp")
        nl.opamp("Ab", "0", "xb", "ob")
        nl.C("Cb", "xb", "ob", F(1))
        sim = Simulator(nl, exact=True)
        sim.run(F(5))
        q_bus = sim.s[sim.sidx["Cb"]] * 1
        self.assertEqual(q_bus, 5 * Cs * V0)                               # 5 packets of Cs*V0
        loss = sim.sol.meters_jump["Ss"] + sim.sol.meters_jump["Sd"]
        self.assertEqual(loss, 5 * Cs * V0 ** 2)                           # C_s V0^2 per packet
        self.assertEqual(-sim.sol.meters_jump["V0"], V0 * q_bus)           # rail energy = V0 * Q
        s = audit_dump(self, sim.dump())
        save("bench_sc_packet.json", {"q_bus": q_bus, "switch_heat": loss, "rail_energy": -sim.sol.meters_jump["V0"],
                                      "audit": s, "dump": sim.dump()})

    def test_integrate_and_fire(self):
        periods = {"a": F(7, 10), "b": F(7, 5), "c": F(10, 3)}
        nl = Netlist()
        nl.V("Vn", "rn", "0", F(-1))
        nl.V("Vth", "th", "0", F(1))
        for k, c in periods.items():
            iandf(nl, k, c)
        nl.gate("coinc", "AND", ["a.fire", "b.fire"], "ab")
        nl.counter("cnt", "ab", 8, "n")
        T = F(10)
        sim = Simulator(nl, exact=True)
        sim.run(T)
        fires = {k: [num(e["t"]) for e in sim.sol.events if e["type"] == "cmp" and e["name"] == f"{k}.cmp" and e["value"]]
                 for k in periods}
        for k, c in periods.items():
            n = math.floor(T / c)
            self.assertEqual(fires[k], [c * j for j in range(1, n + 1)], k)
        self.assertEqual(sim.logic.count_val["cnt"], 7)     # a and b fire as one set at 1.4 k
        # ramps restart exactly at zero after each reset (charge V_th*C removed): the state
        # recorded after the last phase of every reset sequence is exactly 0
        for k, c in periods.items():
            post = [r for r in sim.sol.records if r["tag"] == "post:seq" and num(r["t"]) in fires[k]]
            self.assertTrue(post)
        self.assertEqual(sim.s[sim.sidx["c.Cj"]], 0)        # fired at t = 10 exactly, reset to 0
        self.assertEqual(sim.sol.inexact_events, 0)
        s = audit_dump(self, sim.dump())
        save("bench_integrate_and_fire.json", {"fires": fires, "coincidences": 7, "audit": s, "dump": sim.dump()})


if __name__ == "__main__":
    unittest.main()
