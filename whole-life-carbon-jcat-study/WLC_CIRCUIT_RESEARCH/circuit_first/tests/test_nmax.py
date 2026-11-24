"""N_max identical-netlist test (architecture section 4(b)) for the stage-A cell family:
one netlist for all variants; variants differ only in values and static configuration
switches; results equal the compact per-variant netlists."""
import unittest
from fractions import Fraction as F

from _util import save

from adapter import CONVENTIONS, Units
from adapter_nmax import build_padded, topology_key
from engine.hybrid import Hybrid
from model import simulate

DIMS = {"init": 2, "flow": 2, "item": 4, "clock": 3, "bus": 3}
VARIANTS = {
    "pilot": {"initial": [{"id": "i", "amount": 100, "stage": "A1-A3"}], "flows": [{"id": "op", "rate": 4, "stage": "B6"}],
              "items": [{"id": "A", "amount": 20, "period": 10, "stage": "B4"}, {"id": "B", "amount": 35, "period": 20, "stage": "B4"}]},
    "equal_periods": {"initial": [{"id": "i", "amount": 100, "stage": "A1-A3"}], "flows": [{"id": "op", "rate": 4, "stage": "B6"}],
                      "items": [{"id": "A", "amount": 20, "period": 10, "stage": "B4"}, {"id": "B", "amount": 35, "period": 10, "stage": "B4"}]},
    "signed_three_clocks": {"initial": [{"id": "i", "amount": 70, "stage": "A1-A3"}, {"id": "c", "amount": -5, "stage": "B4"}],
                            "flows": [{"id": "op", "rate": 3, "stage": "B6"}, {"id": "ex", "rate": F(-1, 2), "stage": "B6"}],
                            "items": [{"id": "A", "amount": 20, "period": F(7, 2), "stage": "B4"},
                                      {"id": "B", "amount": -4, "period": 6, "stage": "B4"},
                                      {"id": "C", "amount": 9, "period": F(10, 3), "stage": "A1-A3"},
                                      {"id": "D", "amount": 1, "period": F(7, 2), "stage": "B6"}]},
    "minimal": {"items": [{"id": "A", "amount": 2, "period": 1, "stage": "B4"}]},
}


class NMax(unittest.TestCase):
    def test_same_netlist_and_same_results(self):
        Ts = [F(1), F(7), F(10), F(20), F(21), F(30)]
        topo, rows = None, {}
        for conv in ("right", "original"):
            eps, prio = CONVENTIONS[conv]
            for name, scn in VARIANTS.items():
                B, stage_of, L = build_padded(scn, Units(), conv, DIMS)
                key = topology_key(B.nl)
                if topo is None:
                    topo = key
                self.assertEqual(key, topo, name)
                h = Hybrid(B.nl).run(max(Ts), [{"t": T, "priority": prio, "label": T} for T in Ts])
                ref = simulate(scn, Ts, conv)
                for snap in h.readouts:
                    T = snap["label"]
                    got = sum(snap["s"][f"bus.s{k}.C"] for k in range(DIMS["bus"]))
                    self.assertEqual(got, ref["by_T"][T]["C"], (conv, name, T))
                    for st, slot in stage_of.items():
                        self.assertEqual(snap["s"][f"bus.{slot}.C"], ref["by_T"][T]["stages"].get(st, 0), (conv, name, T, st))
                rows[f"{conv}/{name}"] = {"elements": len(B.nl.elements),
                                          "C": {str(T): str(ref["by_T"][T]["C"]) for T in Ts}}
        save("nmax_same_netlist.json", {"dims": DIMS, "elements_in_template": len(topo), "variants": rows,
                                        "identical_topology": True})


if __name__ == "__main__":
    unittest.main()
