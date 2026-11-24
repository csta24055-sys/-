"""Bench (WLC-agnostic): the resistor cross term that is lost when calculations are split
(15_FLEXIBLE_REORDERING_CONTRACT.md section 5; architecture 5.6(7)).

Two currents through ONE shared resistor dissipate (i1+i2)^2 R t, not i1^2 R t + i2^2 R t: the
difference is the cross term 2 i1 i2 R t. Through SEPARATE resistors heat is additive. Pulsed
variant: rectangular pulses switched by comparators on a ramp; cross term = 2 i1 i2 R * overlap
= 2 sqrt(E1 E2) * rho, rho = overlap / sqrt(w1 w2), E_k = i_k^2 R w_k; 0 when the pulses do not
overlap. All references are closed forms written in this file; heat is the engine's own
per-element energy meter (time integral of v*i). Last test: the stage-A model datapath is built
so that no resistor carries the sum of two independent sources (heat is metered per branch
before any sum), shown structurally and by additivity of the pilot's datapath heat.
"""
import unittest
from fractions import Fraction as F

from _util import audit_dump, save

from engine import Netlist, Simulator
from engine.netlist import OpAmp, Resistor


def dc_net(i1, i2, R, shared):
    nl = Netlist()
    if shared:
        nl.I("I1", "0", "x", i1)
        nl.I("I2", "0", "x", i2)
        nl.R("R", "x", "0", R=R)
    else:
        nl.I("I1", "0", "x1", i1)
        nl.I("I2", "0", "x2", i2)
        nl.R("R1", "x1", "0", R=R)
        nl.R("R2", "x2", "0", R=R)
    return nl


def pulse_net(pulses, R, shared):
    """pulses: [(amplitude, t_on, t_off)]. A unit ramp v_r = t (1 A into 1 F) drives two
    comparators per pulse; en = on AND NOT off routes the source into the load, otherwise to
    ground (make-before-break pair, complementary control)."""
    nl = Netlist()
    nl.I("Iramp", "0", "r", F(1))
    nl.C("Cramp", "r", "0", F(1))
    for k, (amp, ton, toff) in enumerate(pulses, 1):
        nl.V(f"Von{k}", f"von{k}", "0", ton)
        nl.V(f"Voff{k}", f"voff{k}", "0", toff)
        nl.comparator(f"cmp_on{k}", "r", f"von{k}", f"on{k}")
        nl.comparator(f"cmp_off{k}", "r", f"voff{k}", f"off{k}")
        nl.gate(f"n{k}", "NOT", [f"off{k}"], f"noff{k}")
        nl.gate(f"g{k}", "AND", [f"on{k}", f"noff{k}"], f"en{k}")
        nl.I(f"I{k}", "0", f"a{k}", amp)
        load = "x" if shared else f"x{k}"
        nl.switch(f"S{k}", f"a{k}", load, f"en{k}")
        nl.switch(f"S{k}g", f"a{k}", "0", f"en{k}", invert=True)
    if shared:
        nl.R("R", "x", "0", R=R)
    else:
        for k in range(1, len(pulses) + 1):
            nl.R(f"R{k}", f"x{k}", "0", R=R)
    return nl


def heat(sim, names):
    return sum((sim.sol.meters_cont[n] + (sim.sol.meters_jump[n] or 0) for n in names), F(0))


class CrossTerm(unittest.TestCase):
    def test_dc_shared_vs_separate(self):
        R, T = F(3), F(7, 2)
        rows = []
        for i1, i2 in ((F(2), F(5)), (F(2), F(-5)), (F(1, 3), F(1, 3))):
            sh = Simulator(dc_net(i1, i2, R, True), exact=True)
            sh.run(T)
            sp = Simulator(dc_net(i1, i2, R, False), exact=True)
            sp.run(T)
            E_sh, E_sp = heat(sh, ["R"]), heat(sp, ["R1", "R2"])
            self.assertEqual(E_sh, (i1 + i2) ** 2 * R * T)                         # closed form, shared
            self.assertEqual(E_sp, i1 ** 2 * R * T + i2 ** 2 * R * T)              # additive, separate
            self.assertEqual(E_sh - E_sp, 2 * i1 * i2 * R * T)                     # the cross term
            self.assertNotEqual(E_sh, E_sp)
            audit_dump(self, sh.dump())
            audit_dump(self, sp.dump())
            rows.append({"i1": i1, "i2": i2, "R": R, "T": T, "E_shared": E_sh, "E_separate": E_sp,
                         "cross_term": E_sh - E_sp, "closed_form_cross": 2 * i1 * i2 * R * T})
        save("bench_crossterm_dc.json", {"rows": rows, "dump_shared_last": sh.dump(), "dump_separate_last": sp.dump()})

    def test_pulsed_overlap_and_disjoint(self):
        R, T = F(2), F(8)
        i1, i2 = F(3), F(4)
        cases = {"overlap": [(i1, F(1), F(3)), (i2, F(2), F(5))],
                 "simultaneous": [(i1, F(2), F(4)), (i2, F(2), F(4))],
                 "disjoint": [(i1, F(1), F(3)), (i2, F(4), F(6))],
                 "touching": [(i1, F(1), F(3)), (i2, F(3), F(5))]}
        out = {}
        for name, ps in cases.items():
            sh = Simulator(pulse_net(ps, R, True), exact=True)
            sh.run(T)
            sp = Simulator(pulse_net(ps, R, False), exact=True)
            sp.run(T)
            E_sh, E_sp = heat(sh, ["R"]), heat(sp, ["R1", "R2"])
            (a1, on1, off1), (a2, on2, off2) = ps
            w1, w2 = off1 - on1, off2 - on2
            ov = max(F(0), min(off1, off2) - max(on1, on2))
            E1, E2 = a1 ** 2 * R * w1, a2 ** 2 * R * w2
            self.assertEqual(E_sp, E1 + E2)
            self.assertEqual(E_sh, E1 + E2 + 2 * a1 * a2 * R * ov)
            # 2 sqrt(E1 E2) rho with rho = ov / sqrt(w1 w2): squared form keeps exact arithmetic
            cross = E_sh - E_sp
            self.assertEqual(cross ** 2, 4 * E1 * E2 * ov ** 2 / (w1 * w2))
            self.assertEqual(cross == 0, ov == 0)
            self.assertEqual(heat(sh, [f"S{k}" for k in (1, 2)] + [f"S{k}g" for k in (1, 2)]), 0)
            audit_dump(self, sh.dump())
            out[name] = {"pulses": ps, "E_shared": E_sh, "E_separate": E_sp, "E1": E1, "E2": E2,
                         "overlap": ov, "cross_term": cross, "closed_form": 2 * a1 * a2 * R * ov}
        save("bench_crossterm_pulsed.json", {"R": R, "T": T, "cases": out,
                                               "dump_overlap_shared": Simulator(pulse_net(cases["overlap"], R, True), exact=True).dump()})

    def test_model_datapath_not_exposed(self):
        """Stage-A model: every datapath resistor runs from a fixed rail to an op-amp virtual
        ground (one source each); sums happen as charge on integrator capacitors, never as a
        current through a resistor. Hence datapath heat is additive over input subsets."""
        from model import simulate
        from test_pilot import PILOT
        r = simulate(PILOT, [40], "right")
        nl, dp = r["built"].netlist, r["built"].datapath
        vg = {e.inn for e in nl.elements if isinstance(e, OpAmp) and e.inp == "0"}
        rails = {"rail", "railn"}
        for name in dp:
            e = nl.by_name[name]
            ends = set(e.nodes())
            if isinstance(e, Resistor):
                self.assertEqual(len(ends & rails), 1, name)
                self.assertEqual(len(ends & vg), 1, name)
            else:                                   # packet switch: own packet node <-> rail or virtual ground
                self.assertEqual(len([n for n in ends if n.endswith(".a") or n.endswith(".b")]), 1, name)
                self.assertTrue(ends & (rails | vg), name)
        for e in nl.elements:                       # no resistor between two summing nodes
            if isinstance(e, Resistor):
                self.assertLessEqual(len(set(e.nodes()) & vg), 1, e.name)
        parts = [{"initial": PILOT["initial"], "flows": [], "items": []},
                 {"initial": [], "flows": PILOT["flows"], "items": []},
                 {"initial": [], "flows": [], "items": PILOT["items"]}]
        hp, cp = [], []
        for p in parts:
            rp = simulate(p, [40], "right")
            hp.append(rp["by_T"][F(40)]["datapath_heat"])
            cp.append(rp["by_T"][F(40)]["C"])
        whole = r["by_T"][F(40)]
        self.assertEqual(whole["datapath_heat"], sum(hp))
        self.assertEqual(whole["C"], sum(cp))
        save("bench_crossterm_model.json", {"datapath": sorted(dp), "virtual_grounds": sorted(vg),
                                            "heat_whole": whole["datapath_heat"], "heat_parts": hp,
                                            "C_whole": whole["C"], "C_parts": cp})


if __name__ == "__main__":
    unittest.main()
