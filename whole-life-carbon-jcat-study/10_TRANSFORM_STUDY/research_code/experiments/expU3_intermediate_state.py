"""EXP-U3: an intermediate coefficient against the internal state of the reference calculation.

The start-of-year refrigerant mass u[d, k] of the unified system (eight sum-product steps, column ``b1.u8``)
is not a public output. The reference keeps, per device, the mass just before every change event and the mass
at the end of the study period (private key ``_state`` of B1-02). This experiment derives the same two
quantities from ``b1.u8`` and compares them device by device.

    before an event in the year cell k (first event of the cell):  u[d,k] * (1 - [no top-up] * r * w_k(T))
    end of the period (T in the cell K, no event of the cell before T):  u[d,K] * (1 - [no top-up] * r * (T - K))

Run from ``research_code``:  PYTHONDONTWRITEBYTECODE=1 python3 -B -m experiments.expU3_intermediate_state
Writes ``11_UNIFIED_SYSTEM/results/expU3_intermediate_state.json``. The reference is read for comparison only.
"""
import json
import math
import os
import sys

sys.dont_write_bytecode = True

from specs.physical import DY
from tstudy import baseline, scenarios, unified

OUT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "11_UNIFIED_SYSTEM", "results",
                                    "expU3_intermediate_state.json"))
EPS = 1e-9


def main():
    baseline.assert_frozen(); baseline.load()
    scns = scenarios.evaluation_set(30) + [s for _, s in scenarios.edge_set()]
    n_before = n_end = n_dev = 0
    worst_before = worst_end = 0.0
    zero_bad = 0
    for scn in scns:
        if not scn.refrigerants:
            continue
        sysm = unified.System(scn, with_base=False)
        par, k, u = sysm.v(DY, "_parent"), sysm.v(DY, "k"), sysm.v(DY, "b1.u8")
        p, tau1 = sysm.v(DY, "b1.p"), sysm.eng.col(DY, "b1.tau1").v
        H = int(sysm.H)
        for T in (scn.boundary.study_period, 62.5, 33.3):
            cur = scenarios.with_period(scn, T)
            if scenarios.valid_domain(cur):
                continue
            state = baseline.run_reference(cur, ["B1-02"])["B1-02"]["_state"]
            K = math.ceil(T) - 1
            for d, dev in enumerate(scn.refrigerants):
                st = state[d]
                if st is None:
                    continue
                n_dev += 1
                r = 0.0 if dev.top_up else dev.annual_leak_rate
                row = lambda kk: d * H + kk
                assert int(par[row(0)]) == d and int(k[row(K)]) == K
                seen = {}
                for y, m in st["before_events"]:                       # the first event of a year sees the mass after the leak of that year
                    if y in seen:
                        continue
                    seen[y] = True
                    w = min(1.0, T - (y - 1))
                    cand = u[row(y - 1)] * (1.0 - r * w)
                    n_before += 1
                    if m:
                        worst_before = max(worst_before, abs(cand - m) / abs(m))
                    elif cand != 0.0:
                        zero_bad += 1
                reset = bool(p[row(K)]) and tau1[row(K)] < T * (1.0 - EPS)
                cand = dev.charge_mass_kg if reset else u[row(K)] * (1.0 - r * (T - K))
                n_end += 1
                if st["end"]:
                    worst_end = max(worst_end, abs(cand - st["end"]) / abs(st["end"]))
                elif cand != 0.0:
                    zero_bad += 1
    doc = {"experiment": "EXP-U3", "scenarios": len(scns), "device_period_pairs": n_dev, "masses_before_an_event_compared": n_before,
           "end_masses_compared": n_end, "max_rel_difference_before_event": worst_before, "max_rel_difference_end": worst_end,
           "non_zero_where_reference_is_zero": zero_bad}
    print(doc)
    with open(OUT, "w") as f:
        json.dump(doc, f, indent=1)


if __name__ == "__main__":
    main()
