"""V2: hybrid.py (accumulators on/off) vs sim.py vs the verifier's vsim on stage-A netlists of the
verifier's choice (fresh scenarios of V1), snapshot 80ec2de. Compares all capacitor states at
every readout."""
from __future__ import annotations

import json
import os
import sys
from fractions import Fraction as F

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from common import SNAP, save, fstr  # noqa: E402
from vsim import VSim  # noqa: E402

sys.path.insert(0, SNAP)
from adapter import Units, build  # noqa: E402
from engine import Simulator  # noqa: E402
from engine.hybrid import Hybrid  # noqa: E402

CASES = {
    "quad_original": ({"initial": [{"id": "i", "amount": 50, "stage": "A"}], "flows": [{"id": "op", "rate": 2, "stage": "B6"}],
                       "items": [{"id": "d", "amount": 7, "period": 6, "stage": "B4", "repair": {"base": 10, "rate": F(1, 10), "stage": "B3"}},
                                 {"id": "a", "amount": 2, "period": 2, "stage": "B4"}, {"id": "c", "amount": 4, "period": 4, "stage": "B4"},
                                 {"id": "b", "amount": 3, "period": 3, "stage": "B4"}]}, "original", [F(12), F(49, 2), F(25)]),
    "repair_explicit_reno_left": ({"items": [{"id": "A", "amount": 1, "period": 3, "explicit": [F(7, 2), 8], "stage": "B4",
                                              "repair": {"base": 10, "rate": F(1, 10), "stage": "B3"}},
                                             {"id": "B", "amount": 1, "period": 3, "stage": "B4", "repair": {"base": 30, "rate": F(1, 30), "stage": "B3"}}],
                                   "renovations": [{"id": "R", "amount": 9, "years": [11], "replaces": ["B"], "policy": "substituted", "stage": "B5"}]},
                                  "left", [F(8), F(23, 2), F(15)]),
    "signed_right": ({"initial": [{"id": "i", "amount": 100, "stage": "A"}, {"id": "c", "amount": -15, "stage": "D"}],
                      "flows": [{"id": "op", "rate": 4, "stage": "B6"}, {"id": "x", "rate": -1, "stage": "B6"}],
                      "items": [{"id": "A", "amount": 20, "period": F(7, 3), "stage": "B4"}]}, "right", [F(7), F(7, 3), F(20)]),
}


def main():
    out = {}
    for name, (scn, conv, Ts) in CASES.items():
        b = build(scn, Units(), conv)
        prio = 100 if conv == "right" else 0
        caps = [e.name for e in b.netlist.elements if e.kind == "C"]
        s = Simulator(b.netlist, exact=True, record=False)
        s.run(max(Ts), [(T, prio, T) for T in Ts])
        ref = {r["label"]: {c: r["s"][c] for c in caps} for r in s.sol.readouts}
        res = {}
        for acc in (True, False):
            b2 = build(scn, Units(), conv)
            h = Hybrid(b2.netlist, accumulators=acc).run(max(Ts), [{"t": T, "priority": prio, "label": T, "caps": caps} for T in Ts])
            res[f"hybrid_acc_{acc}"] = sum(1 for r in h.readouts for c in caps if r["s"][c] != ref[r["label"]][c])
        v = VSim(build(scn, Units(), conv).netlist.to_json()).run(max(Ts), [(T, prio, T) for T in Ts])
        res["vsim"] = sum(1 for sn in v.snaps for c in caps if sn["u"][c] != ref[sn["label"]][c])
        out[name] = {"capacitors": len(caps), "readouts": len(Ts), "state_mismatches_vs_sim": res}
        print(name, out[name], flush=True)
    save("v2_hybrid_vs_sim.json", out)


if __name__ == "__main__":
    main()
