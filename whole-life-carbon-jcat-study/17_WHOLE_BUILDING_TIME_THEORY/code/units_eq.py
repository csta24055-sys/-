"""Stage 1, completeness review finding (a): equations for the T-dependent outputs that are NOT terms of C(T), checked
against the reference calculation (floating point, relative 1e-9 unless stated).

  X-11   value(T) = c * G(T),  G(T) = sum_k gamma_k w_k(T)  (gamma_k = grid factor of year cell k, from X-06 at T = H);
         checked: the ratio value(T) / G(T) is the same constant c for every T of the scenario (both index alignments tried).
  X-07   series_y = sum of the kernel terms of year cell y-1 (events by their year cell k = max(1, ceil(tau(1-eps))) - 1),
         series_0 = initial constants, end terms Z(T) in the last year Y = ceil(T); cumulative_y = running sum; value = C(T).
         Also compared with the real-time measure of TH-4 binned by (y-1, y] (events at sw(tau)): the two allocations
         differ exactly when an integer-time event tau = K is counted (cell year K versus sw(K) in year K+1).
  counts X-08 by_cycle[c].count = #{n >= 1 : fl(n c) < fl(T fl(1 - eps))};  B4-01 events_j(T) = the elements of
         events_j(H) with tau < fl(T fl(1 - eps)), n_events = sum_j len;  arithmetic lists events_j(H)[n-1] = fl(n tau_1);
         zero-amplitude events (in the lists but not knots of C) are counted.

Usage (from this folder): python3 -B units_eq.py <out.json> [set ...] [--max-scenarios N]
"""
import json
import math
import random
import sys
import time
from fractions import Fraction

sys.dont_write_bytecode = True
import canon                                   # noqa: E402
import timechar as tc                          # noqa: E402
from checks import sets_unified                # noqa: E402
from tstudy import baseline, scenarios         # noqa: E402

D = 1.0 - canon.EPS


def rel(a, b):
    return abs(a - b) / max(abs(a), abs(b), 1.0)


def g_of(gam, T, off):
    return sum(gam[k + off] * min(max(T - k, 0.0), 1.0) for k in range(int(math.ceil(T))) if k + off < len(gam))


def cell_of(g):
    """Year cell of an event (chapter 11): k = max(1, ceil(tau (1 - eps))) - 1."""
    return max(1, math.ceil(g * D)) - 1


def bins(can, T, Y):
    """Two annual allocations of C(T): (1) by the year cell of each term (the model's bookkeeping: year 0 = initial
    constants, year k+1 = cell k and the events of cell k, the last year Y also the end terms Z(T)); (2) the real-time
    measure of TH-4 binned by (y-1, y] (events at their switch point sw(tau), end terms in year Y)."""
    cb, sb = [Fraction(0)] * (Y + 1), [Fraction(0)] * (Y + 1)
    for t in can.terms:
        v = t.amp * t.h(T)
        if v == 0:
            continue
        if t.unit in tc.TERMINAL_UNITS:
            cb[Y] += v; sb[Y] += v
        elif t.kind == "const":
            cb[0] += v; sb[0] += v
        elif t.kind == "cell":
            cb[int(t.start) + 1] += v; sb[int(t.start) + 1] += v
        elif t.kind == "density":
            for k in range(Y):
                w = t.amp * Fraction(min(max(T - k, 0.0), 1.0))
                cb[k + 1] += w; sb[k + 1] += w
        elif t.kind == "atom":
            cb[cell_of(t.gate) + 1] += v
            sb[min(Y, max(1, math.ceil(tc.tswitch(t.gate))))] += v
        elif t.kind == "gcell":
            cb[int(t.start) + 1] += v
            sw = tc.tswitch(t.gate)
            sb[min(Y, int(t.start) + 1 if sw < t.start + t.length else max(1, math.ceil(sw)))] += v
        else:
            raise ValueError(t.kind)
    return cb, sb


def n_integer_events(can, T):
    return sum(1 for t in can.terms if t.kind in ("atom", "gcell") and t.unit not in tc.TERMINAL_UNITS
               and float(t.gate).is_integer() and t.amp * t.h(T) != 0)


def main(outp, names, max_scn):
    baseline.assert_frozen()
    baseline.load()
    from synth import population
    sets = sets_unified.build(names or ["dev_design", "dev_edge", "rep_boundary", "rep_evaluation", "rep_constructed"])
    rng = random.Random(1711)
    out = dict(x11=dict(n_scn=0, n_T=0, const_bad=0, zero_G=0, alignment={}, examples=[]),
               x07=dict(n_T=0, value_vs_C_bad=0, len_ok=0, len_bad=0, cum_bad=0, series_bad=0, series_bad_examples=[], max_rel=0.0,
                        th4_binning_differs=0, th4_differs_with_integer_events=0, th4_differs_without_integer_events=0),
               counts=dict(n_T=0, x08_cycles=0, x08_bad=0, b401_lists=0, b401_bad=0, b401_n_bad=0, arithmetic=0, non_arithmetic=0,
                           zero_amplitude_event_times=0, b4_knot_times=0, examples=[]))
    t0 = time.time()
    for name, cases in sets.items():
        if name in sets_unified.OUTSIDE_DOMAIN:
            continue
        for label, scn, periods in cases[:max_scn]:
            sysm = canon.make_system(scn, population.BASELINES)
            can = canon.build(sysm, T_probe=float(periods[0]) if periods else None)
            H = can.H
            refH = baseline.run_reference(scenarios.with_period(scn, float(H)))
            gam = refH["X-06"]["by_year"]
            evH = refH["B4-01"]["events"]

            Ts = sorted(set([float(p) for p in periods] + [round(rng.uniform(0.6, H - 0.4), 3) for _ in range(3)]))
            ratios = {0: [], 1: []}
            b4_gates = {t.gate for t in can.terms if t.stage == "B4"}
            out["counts"]["b4_knot_times"] += len(b4_gates)
            allH = {x for lst in evH for x in lst}
            out["counts"]["zero_amplitude_event_times"] += len(allH - b4_gates)
            for lst in evH:
                if len(lst) >= 2:
                    ar = all(lst[n] == (n + 1) * lst[0] for n in range(len(lst)))
                    out["counts"]["arithmetic" if ar else "non_arithmetic"] += 1
            out["x11"]["n_scn"] += 1
            for T in Ts:
                cur = scenarios.with_period(scn, T)
                if scenarios.valid_domain(cur):
                    continue
                ref = baseline.run_reference(cur)
                # X-11
                v = ref["X-11"]["value"]
                if v is not None:
                    out["x11"]["n_T"] += 1
                    for off in (0, 1):
                        G = g_of(gam, T, off)
                        if G == 0:
                            out["x11"]["zero_G"] += 1
                        else:
                            ratios[off].append(v / G)
                # X-07 vs TH-4
                C = float(sum((t.amp * t.h(T) for t in can.terms), Fraction(0)))
                x7 = ref["X-07"]
                out["x07"]["n_T"] += 1
                out["x07"]["value_vs_C_bad"] += rel(x7["value"], C) > 1e-9
                Y = int(math.ceil(T))
                by = x7["by_year"]
                if len(by) == Y + 1:
                    out["x07"]["len_ok"] += 1
                else:
                    out["x07"]["len_bad"] += 1
                cellb, swb = bins(can, T, Y)
                tol = 1e-9 * max(abs(C), 1.0)
                bad_cell = [y for y in range(Y + 1) if abs(by[y] - float(cellb[y])) > tol]
                bad_sw = [y for y in range(Y + 1) if abs(by[y] - float(swb[y])) > tol]
                out["x07"]["max_rel"] = max(out["x07"]["max_rel"], max(abs(by[y] - float(cellb[y])) for y in range(Y + 1)) / max(abs(C), 1.0))
                out["x07"]["series_bad"] += bool(bad_cell)
                out["x07"]["th4_binning_differs"] += bool(bad_sw)
                ni = n_integer_events(can, T)
                out["x07"]["th4_differs_with_integer_events"] += bool(bad_sw) and ni > 0
                out["x07"]["th4_differs_without_integer_events"] += bool(bad_sw) and ni == 0
                if bad_cell and len(out["x07"]["series_bad_examples"]) < 12:
                    y = bad_cell[0]
                    out["x07"]["series_bad_examples"].append(dict(label=label, T=T, years=bad_cell[:6], ref=by[y], cell=float(cellb[y])))
                cum = x7["cumulative"]
                out["x07"]["cum_bad"] += any(rel(cum[i], sum(by[:i + 1])) > 1e-9 for i in range(len(cum)))
                # counts
                out["counts"]["n_T"] += 1
                thr = T * D
                for c, row in ref["X-08"]["by_cycle"].items():
                    cv = float(c)
                    n = 0
                    while (n + 1) * cv < thr:
                        n += 1
                    out["counts"]["x08_cycles"] += 1
                    if row["count"] != n:
                        out["counts"]["x08_bad"] += 1
                        if len(out["counts"]["examples"]) < 8:
                            out["counts"]["examples"].append(("X-08", label, T, c, row["count"], n))
                evT = ref["B4-01"]["events"]
                tot = 0
                for j, lst in enumerate(evT):
                    want = [x for x in evH[j] if x < thr]
                    out["counts"]["b401_lists"] += 1
                    tot += len(want)
                    if list(lst) != want:
                        out["counts"]["b401_bad"] += 1
                        if len(out["counts"]["examples"]) < 8:
                            out["counts"]["examples"].append(("B4-01", label, T, j, lst[:4], want[:4]))
                out["counts"]["b401_n_bad"] += ref["B4-01"]["n_events"] != tot
            for off in (0, 1):
                r = ratios[off]
                ok = bool(r) and all(rel(x, r[0]) <= 1e-12 for x in r)
                out["x11"]["alignment"].setdefault(str(off), [0, 0])[0 if ok else 1] += 1
            print("[%-14s] %-44s x07 bad %d  x08 bad %d  b401 bad %d  %.0f s" % (name, label[:44], out["x07"]["series_bad"],
                  out["counts"]["x08_bad"], out["counts"]["b401_bad"], time.time() - t0), flush=True)
    json.dump(out, open(outp, "w"), indent=1, default=str)


if __name__ == "__main__":
    a = sys.argv[1:]
    mx = 10 ** 9
    if "--max-scenarios" in a:
        i = a.index("--max-scenarios"); mx = int(a[i + 1]); del a[i:i + 2]
    main(a[0], a[1:], mx)
