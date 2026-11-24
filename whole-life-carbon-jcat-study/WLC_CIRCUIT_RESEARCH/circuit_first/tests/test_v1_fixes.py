"""Regression tests for the independent verifier's V1 findings (V1-D1 ... V1-D7).
Expected values are independent closed forms / ledgers written here."""
import math
import unittest
from fractions import Fraction as F

from _util import audit_dump, save

from adapter import Units, build
from engine import Netlist, Simulator
from engine.hybrid import Hybrid
from model import hiddenness, netlist_signature, simulate
from test_cf3 import EPS, inside, schedule, year_of
from test_pilot import PILOT


def gated(falling):
    """Ramp o = t; comparator en = [1 - o >= 0] (falling) or [o - 1 >= 0] (rising) closes a switch
    that feeds an integrator from a 1 V rail through 1 S."""
    nl = Netlist()
    nl.V("V1", "rail", "0", F(1))
    nl.V("Vn", "railn", "0", F(-1))
    nl.R("Gr", "railn", "x", G=F(1))
    nl.opamp("A", "0", "x", "o")
    nl.C("Cr", "x", "o", F(1))
    if falling:
        nl.comparator("K", "rail", "o", "en")
    else:
        nl.comparator("K", "o", "rail", "en")
    nl.R("Gb", "rail", "s", G=F(1))
    nl.switch("S", "s", "xb", "en")
    nl.opamp("B", "0", "xb", "ob")
    nl.C("Cb", "xb", "ob", F(1))
    return nl


class V1Fixes(unittest.TestCase):
    def test_D1_gated_integrator_both_directions(self):
        # closed form: falling gate is on during [0, 1) -> charge 1; rising gate on during [1, 3] -> 2
        res = {}
        for falling, exp in ((True, 1), (False, 2)):
            s = Simulator(gated(falling), exact=True)
            s.run(F(3))
            h = Hybrid(gated(falling), record=True, record_jumps=True).run(F(3))
            self.assertEqual(s.s[s.sidx["Cb"]], exp)
            self.assertEqual(h.state("Cb"), exp)
            ev = [(e["t"], e["value"]) for e in s.sol.events if e["type"] == "cmp"]
            self.assertEqual(ev, [("0", True), ("1", False)] if falling else [("1", True)])
            audit_dump(self, s.dump())
            res["falling" if falling else "rising"] = {"charge": str(exp), "events": ev}
        save("bench_gated_integrator.json", res)

    def test_D2_signed_inputs(self):
        scn = {"initial": [{"id": "i", "amount": 100, "stage": "A"}, {"id": "credit", "amount": -15, "stage": "D"}],
               "flows": [{"id": "op", "rate": 4, "stage": "B6"}, {"id": "export", "rate": -1, "stage": "B6"}],
               "items": [{"id": "X", "amount": -5, "period": 4, "stage": "B4"}]}
        for conv in ("right", "original"):
            r = simulate(scn, [F(10), F(12)], conv)
            for T in (F(10), F(12)):
                n = sum(1 for k in range(1, 10) if inside(F(4 * k), T, conv))
                self.assertEqual(r["by_T"][T]["C"], 100 - 15 + 3 * T - 5 * n, (conv, T))
        bad = {"items": [{"id": "A", "amount": 1, "period": 5, "stage": "B4", "repair": {"base": -10, "rate": F(1, 10), "stage": "B3"}}]}
        with self.assertRaises(ValueError):
            simulate(bad, [F(1)], "right")
        bad2 = {"flows": [{"id": "d", "rate": 0, "stage": "B6", "degradation": {"item": "A", "slope": -1}}],
                "items": [{"id": "A", "amount": 1, "period": 5, "stage": "B4"}]}
        with self.assertRaises(ValueError):
            simulate(bad2, [F(1)], "right")

    def test_D3_mixed_stage_repair_group(self):
        scn = {"items": [{"id": "A", "amount": 1, "period": 5, "stage": "B4", "repair": {"base": 10, "rate": F(1, 10), "stage": "B3"}},
                         {"id": "E", "amount": 1, "period": 5, "stage": "B4", "repair": {"base": 20, "rate": F(1, 10), "stage": "B3eq"}}]}
        st = simulate(scn, [F(12)], "right")["by_T"][F(12)]["stages"]
        self.assertEqual(st, {"B4": 4, "B3": 10, "B3eq": 20})
        st2 = simulate(scn, [F(12)], "original")["by_T"][F(12)]["stages"]
        self.assertEqual(st2, {"B4": 4, "B3": 10, "B3eq": 20})

    def test_D4_same_netlist_across_conventions_and_merging(self):
        nets = {c: build(PILOT, Units(), c).netlist for c in ("right", "left", "original")}
        counts = {c: len(n.elements) for c, n in nets.items()}
        self.assertEqual(len(set(counts.values())), 1, counts)
        sigs = {c: netlist_signature(n) for c, n in nets.items()}
        same = dict(PILOT, items=[{"id": "A", "amount": 20, "period": 10, "stage": "B4"},
                                  {"id": "B", "amount": 35, "period": 10, "stage": "B4"}])
        sigs["equal_periods"] = netlist_signature(build(same, Units(), "right").netlist)
        self.assertEqual(len(set(sigs.values())), 1)
        save("v1_D4_signatures.json", {"element_counts": counts, "equal_periods_elements": len(build(same, Units(), "right").netlist.elements),
                                       "signature_size": len(sigs["right"]), "signatures_equal": True})

    def test_D6_narrow_count_and_census(self):
        h = hiddenness(simulate(PILOT, [40], "right")["built"])
        self.assertEqual(h["W_out"], 0)
        self.assertLess(h["W_in"], h["W_in_broad"])
        c = h["control_not_counted_in_h"]
        self.assertGreater(c["sequencer_phase_steps"], 0)
        save("v1_D6_hiddenness_pilot.json", {k: (str(v) if isinstance(v, F) else v) for k, v in h.items()})

    def test_D7_ramps_exactly_zero_after_reset(self):
        r = simulate(PILOT, [60], "original", record=True)
        sim = r["sim"]
        fires = {}
        for e in sim.sol.events:
            if e["type"] == "cmp" and e["value"] and e["name"].endswith(".late"):
                fires.setdefault(e["name"].split(".clk")[0], []).append(e["t"])
        checked = 0
        # after every completed instant with a firing the clock capacitor holds exactly zero charge
        for g, ts in fires.items():
            for t in ts:
                posts = [x for x in sim.sol.records if x["t"] == t and x["tag"] == "post:seq"]
                self.assertTrue(posts)
                self.assertEqual(posts[-1]["s"][f"{g}.clk.C"], "0")
                checked += 1
        self.assertEqual(checked, 6 + 3 - 2)      # A: 10..50, B: 20, 40 (60/(1-eps) > 60)

    def test_D7_full_scenario_value_right(self):
        scn = {"initial": [{"id": "i", "amount": 100, "stage": "A"}],
               "flows": [{"id": "op", "rate": 4, "rate_after": 3, "switch_on": "A", "stage": "B6"},
                         {"id": "dg", "rate": 0, "stage": "B6", "degradation": {"item": "B", "slope": F(1, 2)}}],
               "items": [{"id": "A", "amount": 20, "period": F(5, 2), "explicit": [7], "stage": "B4",
                          "repair": {"base": 20, "rate": F(1, 20), "stage": "B3"}},
                         {"id": "B", "amount": 35, "period": F(10, 3), "stage": "B4"}],
               "renovations": [{"id": "R", "amount": 50, "years": [25], "replaces": ["A", "B"], "policy": "substituted", "stage": "B5"}]}
        T = F(30)
        pkA, renA = schedule(F(5, 2), [7], "restart", subs=[25])
        pkB, renB = schedule(F(10, 3), [], "restart", subs=[25])
        first = min(renA)
        op = 4 * first + 3 * (T - first)
        pts = [F(0)] + [x for x in renB if x < T] + [T]
        deg = sum((F(1, 2) * (b - a) ** 2 / 2 for a, b in zip(pts[:-1], pts[1:])), F(0))
        skip = {math.ceil(t) for t in renA if t <= T}
        rep = sum(1 for y in range(1, 31) if y not in skip)
        exp = 100 + op + deg + 20 * sum(1 for p in pkA if p <= T) + 35 * sum(1 for p in pkB if p <= T) + 50 + rep
        r = simulate(scn, [T], "right")
        self.assertEqual(r["by_T"][T]["C"], exp)
        self.assertEqual(r["by_T"][T]["stages"]["B3"], rep)

    def test_D7_substituted_renovation_counts_as_renewal(self):
        """Kills mutant M18: a substituting renovation renews the item (repair year excluded,
        age reset, efficiency switch), even when it is the only renewal in that year."""
        scn = {"flows": [{"id": "op", "rate": 4, "rate_after": 3, "switch_on": "A", "stage": "B6"},
                         {"id": "dg", "rate": 0, "stage": "B7", "degradation": {"item": "A", "slope": 1}}],
               "items": [{"id": "A", "amount": 20, "period": 30, "stage": "B4",
                          "repair": {"base": 10, "rate": F(1, 10), "stage": "B3"}}],
               "renovations": [{"id": "R", "amount": 50, "years": [F(51, 2)], "replaces": ["A"], "policy": "substituted", "stage": "B5"}]}
        T = F(28)
        r = simulate(scn, [T], "right")["by_T"][T]["stages"]
        self.assertEqual(r["B3"], 28 - 1)                                   # year 26 excluded
        self.assertEqual(r["B6"], 4 * F(51, 2) + 3 * (T - F(51, 2)))        # switched at 25.5
        self.assertEqual(r["B7"], F(51, 2) ** 2 / 2 + (T - F(51, 2)) ** 2 / 2)   # age reset at 25.5
        self.assertEqual(r["B4"], 0)
        self.assertEqual(r["B5"], 50)

    def test_D7_explicit_event_at_band_edge(self):
        """Kills mutant M04b (rho = 2 eps): event at tau = 10/(1-eps) belongs to year
        ceil(tau(1-eps)) = 10 exactly at the edge."""
        tau = F(10) / (1 - EPS)
        scn = {"items": [{"id": "A", "amount": 1, "explicit": [tau], "stage": "B4",
                          "repair": {"base": 10, "rate": F(1, 10), "stage": "B3"}}]}
        r = simulate(scn, [F(21, 2)], "original")
        self.assertEqual(year_of(tau, "original"), 10)
        self.assertEqual([e["year"] for e in r["group_events"]["g0"]], [10])
        self.assertEqual(r["by_T"][F(21, 2)]["stages"]["B3"], 9 + F(1, 2))


if __name__ == "__main__":
    unittest.main()
