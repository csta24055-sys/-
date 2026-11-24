"""V1: re-simulate netlists of FRESH scenarios (built by the builder's adapter) with the
verifier's own simulator and compare with the verifier's ledger (netlist sufficiency)."""
from fractions import Fraction as F

from common import builder, fstr, save
from ledger import total
from vsim import VSim, readout_C

model, adapter = builder()
CASES = {
    "quad_simultaneous_original": ({"initial": [{"id": "i", "amount": 50, "stage": "A"}],
                                    "flows": [{"id": "op", "rate": 2, "stage": "B6"}],
                                    "items": [{"id": "d", "amount": 7, "period": 6, "stage": "B4",
                                               "repair": {"base": 10, "rate": F(1, 10), "stage": "B3"}},
                                              {"id": "a", "amount": 2, "period": 2, "stage": "B4"},
                                              {"id": "c", "amount": 4, "period": 4, "stage": "B4"},
                                              {"id": "b", "amount": 3, "period": 3, "stage": "B4"}]},
                                   "original", [F(12), F(49, 2), F(25)]),
    "repair_explicit_renovation_left": ({"items": [{"id": "A", "amount": 1, "period": 3, "explicit": [F(7, 2), 8], "stage": "B4",
                                                    "repair": {"base": 10, "rate": F(1, 10), "stage": "B3"}},
                                                   {"id": "B", "amount": 1, "period": 3, "stage": "B4",
                                                    "repair": {"base": 30, "rate": F(1, 30), "stage": "B3"}}],
                                         "renovations": [{"id": "R", "amount": 9, "years": [11], "replaces": ["B"],
                                                          "policy": "substituted", "stage": "B5"}]},
                                        "left", [F(8), F(23, 2), F(15)]),
    "degradation_eff_original": ({"flows": [{"id": "op", "rate": 4, "rate_after": 3, "switch_on": "A", "stage": "B6",
                                             "degradation": {"item": "A", "slope": F(1, 2)}}],
                                  "items": [{"id": "A", "amount": 20, "period": 10, "explicit": [7], "stage": "B4"}]},
                                 "original", [F(10), F(23, 2), F(30)]),
}


def main():
    out = {}
    for name, (scn, conv, Ts) in CASES.items():
        b = adapter.build(scn, adapter.Units(), conv)
        prio = 100 if conv == "right" else 0
        s = VSim(b.netlist.to_json()).run(max(Ts), [(T, prio, T) for T in Ts])
        rows = []
        for snap in s.snaps:
            C, st = readout_C(s, snap)
            L, _ = total(scn, snap["t"], conv)
            eng = model.simulate(scn, [snap["t"]], conv)["by_T"][snap["t"]]["C"]
            rows.append({"T": fstr(snap["t"]), "vsim": fstr(C), "ledger": fstr(L), "engine": fstr(eng),
                         "all_equal": C == L == eng})
        out[name] = {"rows": rows, "pass": all(r["all_equal"] for r in rows), "vsim_modes": s.n_modes}
    save("vsim_fresh.json", out)
    return out


if __name__ == "__main__":
    import json
    print(json.dumps(main(), indent=1))
