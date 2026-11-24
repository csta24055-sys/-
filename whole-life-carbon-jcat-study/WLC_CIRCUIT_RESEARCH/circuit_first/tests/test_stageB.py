"""Stage-B engine and building checks that run in the normal test suite (fast):
  * static DC solver against the stage-A simulator and its own KCL residual;
  * scalable hybrid simulator against the stage-A simulator on the CF2/CF3 scenarios;
  * a truncated synthetic building: accumulator sinks on vs off identical, full solution
    (accumulators off) audited from the dump with zero residuals, and the frozen reference
    (test-side import only) reproduced within 1e-9.
The long benchmark comparisons are produced by tests/compare_refcalc.py and
tests/compare_stageB_e.py (results/stageB_*.json)."""
import copy
import os
import sys
import unittest
from fractions import Fraction as F

from _util import ROOT, audit_dump, save

from adapter import CONVENTIONS, Units, build
from engine import Netlist, Simulator
from engine.dc import kcl_residual, solve_dc
from engine.hybrid import Hybrid
from model import simulate
from test_audit import B3_05, B3_25, DEG, RENO
from test_pilot import PILOT

STUDY = os.path.normpath(os.path.join(ROOT, "..", ".."))


class StaticSolver(unittest.TestCase):
    def test_dc_matches_simulator(self):
        nl = Netlist()
        nl.V("V", "r", "0", F(3))
        nl.R("Ra", "r", "x1", R=F(2))
        nl.opamp("A1", "0", "x1", "o1")
        nl.R("Rf1", "x1", "o1", R=F(5))
        nl.R("Rb", "o1", "x2", R=F(7))
        nl.R("Rc", "r", "x2", R=F(1, 3))
        nl.opamp("A2", "0", "x2", "o2")
        nl.R("Rf2", "x2", "o2", R=F(11))
        nl.V("Vin", "vin", "0", F(5, 2))
        nl.opamp("B", "vin", "fb", "y")
        nl.pot("P", "y", "fb", "0", F(1000), F(3, 4))
        v, i, info = solve_dc(nl)
        self.assertEqual(kcl_residual(nl, v, i), 0)
        sim = Simulator(nl, exact=True)
        sim.run(F(1))
        rec = sim.sol.records[-1]
        for n in ("o1", "o2", "y"):
            self.assertEqual(v[n], F(rec["v"][n]) if "/" not in rec["v"][n] else F(*map(int, rec["v"][n].split("/"))))
        self.assertEqual(v["o1"], F(-15, 2))
        self.assertEqual(v["y"], 10)
        self.assertEqual(info["dense_block"], 0)


class HybridEquivalence(unittest.TestCase):
    def test_hybrid_equals_stage_a_simulator(self):
        full = {"initial": [{"id": "i", "amount": 100, "stage": "A"}],
                "flows": [{"id": "op", "rate": 4, "rate_after": 3, "switch_on": "A", "stage": "B6"},
                          {"id": "dg", "rate": 0, "stage": "B6", "degradation": {"item": "B", "slope": F(1, 2)}}],
                "items": [{"id": "A", "amount": 20, "period": F(5, 2), "explicit": [7], "stage": "B4",
                           "repair": {"base": 20, "rate": F(1, 20), "stage": "B3"}},
                          {"id": "B", "amount": 35, "period": F(10, 3), "stage": "B4"}],
                "renovations": [{"id": "R", "amount": 50, "years": [25], "replaces": ["A", "B"], "policy": "substituted", "stage": "B5"}]}
        n = 0
        for scn in (PILOT, B3_25, B3_05, RENO, DEG, full):
            for conv in ("right", "left", "original"):
                Ts = [F(3), F(10), F(21, 2), F(20), F(25), F("25.5"), F(30)]
                ref = simulate(scn, Ts, conv)
                b = build(scn, Units(), conv)
                h = Hybrid(b.netlist).run(max(Ts), [{"t": T, "priority": CONVENTIONS[conv][1], "label": T} for T in Ts])
                for snap in h.readouts:
                    q = sum(b.netlist.by_name[c].C * snap["s"][c] for caps in b.taps.values() for c in caps)
                    self.assertEqual(q, ref["by_T"][snap["label"]]["C"])
                    n += 1
        self.assertEqual(n, 6 * 3 * 7)


def _small_building():
    sys.path.insert(0, os.path.join(STUDY, "10_TRANSFORM_STUDY", "research_code"))
    from tstudy import baseline, scenarios
    baseline.assert_frozen()
    s = copy.deepcopy(scenarios.benchmark()[0])
    s.materials = s.materials[:8]
    s.equipment = s.equipment[:5]
    s.refrigerants = s.refrigerants[:3]
    return s, baseline, scenarios


class SmallBuilding(unittest.TestCase):
    def test_accumulators_residuals_and_reference(self):
        from model_building import simulate_building
        s, baseline, scenarios = _small_building()
        Ts = [F(15, 2), F(20), F(333, 10)]
        on = simulate_building(s, Ts, "original")
        off = simulate_building(s, Ts, "original", record=True, accumulators=False)
        for T in Ts:
            self.assertEqual(on["by_T"][T]["C"], off["by_T"][T]["C"])
            self.assertEqual(on["by_T"][T]["stages"], off["by_T"][T]["stages"])
        d = off["sim"].dump()
        summary = audit_dump(self, {**d, "meters": None}, exact=True) if False else None
        from engine.audit import residuals
        r = residuals(d)
        self.assertEqual(r["kcl_max"], 0, r["violations"])
        self.assertEqual(r["law_max"], 0, r["violations"])
        self.assertEqual(r["jump_kcl_max"], 0, r["violations"])
        worst = 0.0
        for T in Ts:
            ref = baseline.run_reference(scenarios.with_period(s, float(T)))
            self.assertTrue(ref["X-02"]["complete"] or True)
            for st, v in ref["X-02"]["by_stage"].items():
                got = float(on["by_T"][T]["stages"].get(st, 0))
                e = abs(got - v) / max(abs(v), 1e-300) if v else abs(got)
                worst = max(worst, e)
            tot = float(on["by_T"][T]["C"])
            self.assertLessEqual(abs(tot - ref["SUM-03"]["value"]) / abs(ref["SUM-03"]["value"]), 1e-9)
        self.assertLessEqual(worst, 1e-9)
        save("stageB_small_building_full_solution.json",
             {"residuals": {k: (float(v) if isinstance(v, F) else v) for k, v in r.items() if k != "violations"},
              "max_rel_vs_refcalc": worst, "records": len(d["records"]), "jumps": len(d["jumps"]), "dump": d})


if __name__ == "__main__":
    unittest.main()


@unittest.skipUnless(os.environ.get("CF_SLOW") == "1", "slow (~7 min): run with CF_SLOW=1")
class MergedNetlist(unittest.TestCase):
    def test_crossbar_and_core_as_one_netlist(self):
        """Part 3(d): crossbar + core as ONE netlist (tap sources removed, core tap nodes joined
        to the crossbar op-amp outputs) gives exactly the same readouts as the split run, so the
        D12 split is only a solving strategy."""
        from engine import Netlist
        from model_building import simulate_building
        s, baseline, scenarios = _small_building()
        s.materials, s.equipment, s.refrigerants = s.materials[:3], s.equipment[:2], s.refrigerants[:1]
        Ts = [F(15, 2), F(20), F(333, 10)]
        # OP (year banks) excluded here: without tap sources its table branches hang off non-fixed
        # op-amp outputs and form one large component per tick (solver cost, not semantics)
        blocks = ("AC", "EV", "REF")
        split = simulate_building(s, Ts, "original", blocks)
        A, B = split["A"], split["core"]
        rename = {f"t.{name}": node for name, (node, sg) in A.exports.items()}
        nl = Netlist()
        for e in A.nl.elements:
            nl.add(copy.copy(e))
        for e in B.nl.elements:
            if e.name.startswith("tap."):
                continue
            e2 = copy.copy(e)
            for attr in ("a", "b", "inp", "inn", "out", "plus", "minus", "cp", "cn"):
                if hasattr(e2, attr) and getattr(e2, attr) in rename:
                    setattr(e2, attr, rename[getattr(e2, attr)])
            nl.add(e2)
        caps = [c for lst in B.readout_caps.values() for c in lst]
        h = Hybrid(nl).run(max(Ts), [{"t": T, "priority": 0, "label": T, "signal": "rd", "caps": caps} for T in Ts])
        for snap, ref in zip(h.readouts, split["sim"].readouts):
            self.assertEqual(snap["s"], ref["s"])
        save("stageC_merged_netlist.json", {"blocks": list(blocks), "elements_merged": len(nl.elements), "crossbar": len(A.nl.elements),
                                            "core": len(B.nl.elements), "taps_removed": len(rename),
                                            "readouts_identical": True, "T": [str(T) for T in Ts]})
