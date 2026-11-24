"""H-B3: refrigerant terminal residual R(T) (B1-04) and leak B1-02 -- continuous RC discharge versus
sample-hold + reset, executed against refcalc.

Variants (all from RAW device inputs of the frozen generator's scenario; fictional data):
  SH     exact hybrid automaton of grammar.RefrigerantCircuit (S/H per cell, linear in-cell leak, late reset)
  RC-b   same S/H cell structure and resets, but the in-cell decay is a continuous RC discharge with
         exp(-1/RC) = q = 1 - r  (matches the model at whole years by construction, not inside a cell)
  RC-a   a "physical" RC: continuous discharge m0*q^(T - t_reset) with the reset switch closing at the
         comparator time of each counted event (no year-cell structure at all)
Top-up devices hold m0 (no discharge) in every variant.
"""
from __future__ import annotations

import json
import math
import os
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import grammar as G  # noqa: E402
import oracle_io as O  # noqa: E402


class RCCellCircuit(G.RefrigerantCircuit):
    """RC-b: replaces the linear in-cell integrator by an RC discharge (same S/H and resets)."""

    def _L(self, d, T):
        if d.topup:
            return d.L_last + d.i * (T - d.t_last)
        q = 1.0 - d.r
        return d.m_hold * (1.0 - q ** (T - d.K))


def rc_physical_b104(scn, H: int, Ts) -> dict:
    """RC-a: v(T) = m0 * q^(T - t_last_reset); reset at sw(tau) of each counted event."""
    out = {}
    devs = []
    for dev in scn.refrigerants:
        if not (G._nonneg(dev.charge_mass_kg) and G._nonneg(dev.gwp) and G._ratio(dev.annual_leak_rate)):
            continue
        if not G._ratio(dev.end_of_life_recovery_rate):
            continue
        sws = [G.switch_point(t) for t in G.device_event_table(dev, float(H))]
        devs.append((dev, sws))
    for T in Ts:
        s = 0.0
        for dev, sws in devs:
            if dev.top_up:
                v = dev.charge_mass_kg
            else:
                last = max([t for t in sws if t <= T], default=0.0)
                v = dev.charge_mass_kg * (1.0 - dev.annual_leak_rate) ** (T - last)
            s += v * (1.0 - dev.end_of_life_recovery_rate) * dev.gwp
        out[T] = s
    return out


def single_device_scenario(scn):
    """A fictional derived scenario: only the first refrigerant device without top-up (rows of materials and
    equipment dropped; B1-02/B1-04 depend only on the refrigerant rows)."""
    import copy
    out = copy.deepcopy(scn)
    out.refrigerants = [next(d for d in scn.refrigerants if not d.top_up)]
    out.materials, out.equipment = [], []
    out.meta.scenario_id = scn.meta.scenario_id + "/single-no-topup-device"
    return out


def run(scenario: str = "M", step: float = 0.25, T_max: float = 60.0, single: bool = False) -> dict:
    m = O.setup()
    scn = O.representative_scenarios((scenario,))[0]
    if single:
        scn = single_device_scenario(scn)
    H = 130
    Ts = [round(step * i, 10) for i in range(1, int(T_max / step) + 1)]
    extra = []
    for dev in scn.refrigerants:
        if not dev.top_up:
            for tau in G.device_event_table(dev, float(H)):
                if tau < T_max:
                    extra += [tau, tau * (1 + 2e-9), tau + 0.5 if tau + 0.5 <= T_max else tau]
    Ts = sorted(set(Ts) | set(extra))
    ref = {}
    for T in Ts:
        r = m["baseline"].run_reference(m["scenarios"].with_period(scn, T), ["B1-02", "B1-04"])
        ref[T] = (r["B1-02"]["value"], r["B1-04"]["value"])
    sh = G.RefrigerantCircuit(scn, H).sweep(Ts)
    rcb = RCCellCircuit(scn, H).sweep(Ts)
    rca = rc_physical_b104(scn, H, Ts)

    def stats(get, idx):
        errs_int, errs_frac = [], []
        worst = (0.0, None)
        for T in Ts:
            y = ref[T][idx]
            e = abs(get(T) - y) / abs(y) if y else abs(get(T))
            (errs_int if T == round(T) else errs_frac).append(e)
            if e > worst[0]:
                worst = (e, T)
        return {"max_rel_integer_T": max(errs_int) if errs_int else None, "max_rel_fractional_T": max(errs_frac),
                "worst": {"rel": worst[0], "T": worst[1]}, "n_integer": len(errs_int), "n_fractional": len(errs_frac)}

    res = {
        "scenario": scn.meta.scenario_id, "n_T": len(Ts), "step": step, "T_max": T_max,
        "n_devices": len(scn.refrigerants), "n_no_topup": sum(1 for d in scn.refrigerants if not d.top_up),
        "B1-04": {"SH": stats(lambda T: sh[T]["B1-04"], 1), "RC-b (RC in cell, S/H resets)": stats(lambda T: rcb[T]["B1-04"], 1),
                  "RC-a (physical RC, reset at event)": stats(lambda T: rca[T], 1)},
        "B1-02": {"SH": stats(lambda T: sh[T]["B1-02"], 0), "RC-b (RC in cell, S/H resets)": stats(lambda T: rcb[T]["B1-02"], 0)},
    }
    # one illustrative device trace (first no-top-up device), values per unit charge
    dev = next(d for d in scn.refrigerants if not d.top_up)
    q = 1.0 - dev.annual_leak_rate
    res["single_device_illustration"] = {
        "r": dev.annual_leak_rate, "q": q, "RC_time_constant_years": -1.0 / math.log(q),
        "in_cell_at_half_year": {"linear(model)": 1.0 - dev.annual_leak_rate / 2.0, "RC": q ** 0.5,
                                 "rel_diff": (q ** 0.5 - (1.0 - dev.annual_leak_rate / 2.0)) / (1.0 - dev.annual_leak_rate / 2.0)},
        "at_whole_year": {"linear(model)": q, "RC": q ** 1.0},
    }
    return res


def main():
    res = {"whole_scenario": run(), "single_device": run(single=True)}
    path = os.path.join(O.ROUTE, "results", "hb3_refrigerant.json")
    with open(path, "w") as f:
        json.dump(res, f, indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
