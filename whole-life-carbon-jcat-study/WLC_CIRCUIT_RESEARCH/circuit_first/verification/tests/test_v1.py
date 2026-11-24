"""V1 verifier regression tests (fast subset). Run from this directory with
    PYTHONDONTWRITEBYTECODE=1 math7-py -B -m unittest -v test_v1
The full evidence is produced by ../code/run_*.py scripts (see ../STATUS.md).
Tests marked DEFECT assert that a defect found in snapshot 4c5f375 is still reproducible;
they are expected to start failing once the builder fixes it (then update the verdict)."""
import os
import sys
import unittest
from fractions import Fraction as F

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "code"))

from common import builder  # noqa: E402
from ledger import total  # noqa: E402
from vsim import VSim, readout_C  # noqa: E402

model, adapter = builder()
PILOT = {"initial": [{"id": "init", "amount": 100, "stage": "A1-A3"}],
         "flows": [{"id": "op", "rate": 4, "stage": "B6"}],
         "items": [{"id": "A", "amount": 20, "period": 10, "stage": "B4"},
                   {"id": "B", "amount": 35, "period": 20, "stage": "B4"}]}


class Ledger(unittest.TestCase):
    def test_contract_values(self):
        for conv, vals in (("right", [160, 255, 315, 410]), ("left", [140, 200, 295, 355]),
                           ("original", [140, 200, 295, 355])):
            self.assertEqual([total(PILOT, T, conv)[0] for T in (10, 20, 30, 40)], vals)


class PilotBlackBox(unittest.TestCase):
    def test_07_points_three_conventions(self):
        pts = ["0", "1", "9.999999", "10", "10.000001", "19.999999", "20", "20.000001", "30", "40", "60"]
        for conv in ("right", "left", "original"):
            Ts = [F(p) for p in pts if not (conv != "right" and p == "0")]
            r = model.simulate(PILOT, Ts, conv)
            for T in Ts:
                C, st = total(PILOT, T, conv)
                self.assertEqual(r["by_T"][T]["C"], C, (conv, T))
                self.assertEqual(r["by_T"][T]["stages"], {k: v for k, v in st.items()}, (conv, T))


class IndependentSimulator(unittest.TestCase):
    def test_pilot_netlist_resimulated(self):
        for conv, prio, vals in (("right", 100, [160, 255, 315, 410]), ("original", 0, [140, 200, 295, 355])):
            b = adapter.build(PILOT, adapter.Units(), conv)
            s = VSim(b.netlist.to_json()).run(40, [(T, prio, T) for T in (10, 20, 30, 40)])
            self.assertEqual([readout_C(s, sn)[0] for sn in s.snaps], vals)


class Defects(unittest.TestCase):
    def test_DEFECT_falling_comparator_not_applied(self):
        from engine import Netlist, Simulator
        nl = Netlist()
        nl.V("V1", "rail", "0", F(1)); nl.V("Vn", "railn", "0", F(-1))
        nl.R("Gr", "railn", "x", G=F(1)); nl.opamp("A", "0", "x", "o"); nl.C("Cr", "x", "o", F(1))
        nl.comparator("K", "rail", "o", "en")
        nl.R("Gb", "rail", "s", G=F(1)); nl.switch("S", "s", "xb", "en")
        nl.opamp("B", "0", "xb", "ob"); nl.C("Cb", "xb", "ob", F(1))
        sim = Simulator(nl, exact=True, record=False)
        sim.run(F(3))
        self.assertEqual(sim.s[sim.sidx["Cb"]], 3)            # engine (wrong): should be 1
        vs = VSim(nl.to_json()).run(3)
        self.assertEqual(vs.u[vs.net.cidx["Cb"]], 1)          # verifier simulator (correct)

    def test_DEFECT_signed_inputs_silently_dropped(self):
        scn = {"initial": [{"id": "i", "amount": 100, "stage": "A"}, {"id": "credit", "amount": -15, "stage": "D"}],
               "flows": [{"id": "op", "rate": 4, "stage": "B6"}, {"id": "export", "rate": -1, "stage": "B6"}]}
        r = model.simulate(scn, [F(10)], "right")
        self.assertEqual(r["by_T"][F(10)]["C"], 140)          # circuit drops the signed rows, no error
        self.assertEqual(total(scn, 10, "right")[0], 115)

    def test_DEFECT_group_repair_stage_from_first_row(self):
        scn = {"items": [{"id": "A", "amount": 1, "period": 5, "stage": "B4", "repair": {"base": 10, "rate": F(1, 10), "stage": "B3"}},
                         {"id": "E", "amount": 1, "period": 5, "stage": "B4", "repair": {"base": 20, "rate": F(1, 10), "stage": "B3eq"}}]}
        st = model.simulate(scn, [F(12)], "right")["by_T"][F(12)]["stages"]
        self.assertEqual(st, {"B4": 4, "B3": 30})              # ledger: B3 = 10, B3eq = 20

    def test_DEFECT_topology_depends_on_convention(self):
        n_right = len(adapter.build(PILOT, adapter.Units(), "right").netlist.elements)
        n_orig = len(adapter.build(PILOT, adapter.Units(), "original").netlist.elements)
        self.assertEqual((n_right, n_orig), (53, 55))         # divider only instantiated when rho != 0


if __name__ == "__main__":
    unittest.main()
