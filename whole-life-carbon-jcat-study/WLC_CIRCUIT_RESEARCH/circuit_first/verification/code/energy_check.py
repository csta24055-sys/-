"""V1 energy accounting with the verifier's own simulator (pilot and CF3-full netlists).

* Tellegen check: sum over all elements of continuous absorbed energy = 0 (exact).
* Every impulsive (switching) loss computed as -(exact V-source work V*Q + op-amp output work
  on the linear path + change of capacitor energy) must be >= 0.
* Data-path Joule claim (architecture 3(ii), builder D8): data-path heat (flow-resistor heat +
  losses of the data packets) equals V0 * Q_total for the single-rail pilot; it must FAIL
  when amplitudes are voltages / packets are negative (CF3 full).
"""
from __future__ import annotations

from fractions import Fraction as Fr

from common import builder, fstr, save
from vsim import VSim, num, readout_C

model, adapter = builder()

PILOT = {"initial": [{"id": "init", "amount": 100, "stage": "A1-A3"}],
         "flows": [{"id": "op", "rate": 4, "stage": "B6"}],
         "items": [{"id": "A", "amount": 20, "period": 10, "stage": "B4"},
                   {"id": "B", "amount": 35, "period": 20, "stage": "B4"}]}
FULL = {"initial": [{"id": "i", "amount": 100, "stage": "A"}],
        "flows": [{"id": "op", "rate": 4, "rate_after": 3, "switch_on": "A", "stage": "B6"},
                  {"id": "dg", "rate": 0, "stage": "B6", "degradation": {"item": "B", "slope": Fr(1, 2)}}],
        "items": [{"id": "A", "amount": 20, "period": Fr(5, 2), "explicit": [7], "stage": "B4",
                   "repair": {"base": 20, "rate": Fr(1, 20), "stage": "B3"}},
                  {"id": "B", "amount": 35, "period": Fr(10, 3), "stage": "B4"}],
        "renovations": [{"id": "R", "amount": 50, "years": [25], "replaces": ["A", "B"], "policy": "substituted", "stage": "B5"}]}


def is_data(name):
    return name.startswith(("pk.", "bus.", "fl.", "rail.V0")) or ".yc." in name or ".rp." in name or name.startswith("age.")


def analyse(scn, conv, Ts, prio):
    b = adapter.build(scn, adapter.Units(), conv)
    s = VSim(b.netlist.to_json()).run(max(Ts), [(T, prio, T) for T in Ts])
    V0 = Fr(1)
    rows = {}
    neg_losses = [j for j in s.jumps if j.get("impulsive_loss") is not None and j["impulsive_loss"] < 0]
    unknown = sum(1 for j in s.jumps if j.get("impulsive_loss") is None)
    for snap in s.snaps:
        C, st = readout_C(s, snap)
        heat = snap["heat"]
        tell = sum(heat.values(), Fr(0))
        js = s.jumps[:snap["n_jumps"]]
        loss_data = Fr(0)
        for j in js:
            w_src = sum((num(s.net.by[k]["V"]) * q for k, q in j["Q"].items()
                         if s.net.by[k]["kind"] == "V" and k == "rail.V0"), Fr(0))
            w_oa = sum((w for k, w in j.get("W_oa_by", {}).items() if is_data(k)), Fr(0))
            de = sum((w for k, w in j.get("dE_C_by", {}).items() if is_data(k)), Fr(0))
            loss_data += -(w_src + w_oa + de)
        r_heat = sum((v for k, v in heat.items() if k in b.datapath and s.net.by[k]["kind"] == "R"), Fr(0))
        dp = r_heat + loss_data
        rows[fstr(snap["t"])] = {"C": fstr(C), "tellegen_sum_continuous": fstr(tell),
                                 "datapath_heat": fstr(dp), "V0_Q": fstr(V0 * C), "equal": dp == V0 * C}
    return {"rows": rows, "negative_impulsive_losses": len(neg_losses), "impulsive_loss_undetermined": unknown,
            "jumps": len(s.jumps)}


def main():
    out = {"pilot_right": analyse(PILOT, "right", [Fr(1, 2), Fr(10), Fr(20), Fr(333, 10), Fr(40)], 100),
           "full_original": analyse(FULL, "original", [Fr(12), Fr(30)], 0)}
    save("energy_check.json", out)
    return out


if __name__ == "__main__":
    import json
    print(json.dumps(main(), indent=1, default=str))
