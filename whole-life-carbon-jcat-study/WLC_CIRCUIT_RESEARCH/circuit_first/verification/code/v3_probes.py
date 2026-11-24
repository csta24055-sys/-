"""V3 probes on snapshot 96df403 (V2-defect confirmations), each variant vs the frozen refcalc:
  * complement (pot) sites at their endpoints: facility-management ratio rho in {0, 1}, unquantified
    cost ratio r in {0, 1}, waste rate w in {0, 0.999999}, recovery rate eta in {0, 1};
  * duplicate / same-year explicit events: equipment [y, y]; refrigerant change years [5.2, 5.7]
    (two events in one study year), [5, 6], and the duplicate [5, 5] (D24 says: rejected);
  * D3: every boolean signal read by the full S core is produced by some element.
Usage: python3 -B v3_probes.py
"""
from __future__ import annotations

import copy
import json
import os
import sys
import time
from fractions import Fraction as Fr

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from common import SNAP, save  # noqa: E402
import v2_oracle as o  # noqa: E402  (asserts the frozen oracle; imports the snapshot model)

STAGES = o.STAGES
TS = [5.5, 6.000001, 7.25, 33.3, 60.000001]


def compare(scn, Ts=TS):
    Ts = [T for T in Ts if not o.scenarios.valid_domain(o.scenarios.with_period(scn, T)) and not o.in_band(scn, T)]
    if not Ts:
        return {"status": "no valid T", "why": o.scenarios.valid_domain(o.scenarios.with_period(scn, TS[0]))[:2]}
    try:
        out = o.simulate_building(scn, Ts, "original")
    except Exception as e:  # noqa
        return {"status": "CRASH/REJECT", "error": f"{type(e).__name__}: {str(e)[:160]}", "T": Ts}
    mx = 0.0
    worst = None
    for T in Ts:
        res = o.baseline.run_reference(o.scenarios.with_period(scn, T))
        st = res["X-02"]["by_stage"]
        got = out["by_T"][Fr(T)]
        for s in STAGES:
            if s in st:
                e = o.rel(got["stages"].get(s, 0), st[s])
                if e > mx:
                    mx, worst = e, (T, s)
        e = o.rel(got["C"], res["SUM-03"]["value"])
        if e > mx:
            mx, worst = e, (T, "C")
    return {"status": "PASS" if mx <= 1e-9 else "FAIL", "max_rel": mx, "worst": worst, "T": Ts}


def main():
    edge = dict(o.scenarios.edge_set())
    base = edge["top_up_none"]
    out = {}

    def run(name, mutate, src=base):
        s = copy.deepcopy(src)
        mutate(s)
        why = o.scenarios.valid_domain(s)
        t0 = time.time()
        r = compare(s)
        r["valid_domain_at_given_T"] = why[:2]
        r["seconds"] = round(time.time() - t0, 1)
        out[name] = r
        print(name, json.dumps(r, default=str)[:300], flush=True)

    for v in (0.0, 1.0):
        run(f"rho={v}", lambda s, v=v: setattr(s.operation, "facility_management_ratio", v))
    for v in (0.0, 1.0):
        def f(s, v=v):
            for m in s.materials:
                m.unquantified_cost_ratio = v
        run(f"unquantified_ratio={v}", f)
    for v in (0.0, 0.999999):
        def f(s, v=v):
            for m in s.materials:
                m.waste_rate = v
        run(f"waste_rate={v}", f)
    for v in (0.0, 1.0):
        def f(s, v=v):
            for d in s.refrigerants:
                d.end_of_life_recovery_rate = v
        run(f"recovery={v}", f)
    for yrs in ([5.2, 5.7], [5.0, 6.0], [5.0, 5.0], [2.5, 2.5, 7.0]):
        def f(s, yrs=yrs):
            s.refrigerants[0].change_years = list(yrs)
            s.refrigerants[0].service_life = None
        run(f"refrigerant_change_years={yrs}", f)
    for yrs in ([14.0, 14.0], [5.2, 5.7]):
        def f(s, yrs=yrs):
            s.equipment[0].replacement_event_list = list(yrs)
        run(f"equipment_events={yrs}", f)
    # D3: dangling boolean inputs in the full S core
    S = o.scenarios.benchmark()[0]
    out_S = o.simulate_building(S, [Fr(1, 2)], "original")
    nl = out_S["core"].nl
    made, used = set(), set()
    for e in nl.digital():
        k = e.kind
        if k in ("CMP", "GATE", "POR"):
            made.add(e.out)
        elif k in ("SR", "DFF"):
            made.add(e.q)
        elif k == "CNT":
            made |= {f"{e.prefix}{i}" for i in range(e.nbits)}
        elif k == "SEQ":
            made |= set(e.idle) | {x for st in e.steps for x in st}
        if k == "GATE":
            used |= set(e.inputs)
        elif k == "SR":
            used |= {e.set, e.reset}
        elif k == "DFF":
            used |= {e.d, e.clk}
        elif k == "CNT":
            used.add(e.clk)
        elif k == "SEQ":
            used.add(e.trigger)
    for e in nl.analog():
        if e.kind == "SW":
            used.add(e.ctrl)
    dangling = sorted(used - made - {"ONE", "ZERO", "rd", "CFG1", "CFG0"})
    out["D3_dangling_signals_S_core"] = dangling[:20]
    out["D3_n_dangling"] = len(dangling)
    print("dangling", len(dangling), dangling[:10])
    save("v3_probes.json", out)


if __name__ == "__main__":
    main()
