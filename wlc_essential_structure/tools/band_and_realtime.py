"""(g) Two explicit re-tests required by the brief, with the five-family evaluator (five_families.py):

1. The thin band (K, sw(K)) of chapter 17: refrigerant changes at an integer time K. The reconstruction is evaluated
   inside the band (T = next float above K, K(1+5e-11), K(1+3e-10)) and outside it (K(1+3e-8)) against the frozen
   reference. Expected: mismatches may appear only inside the band (that is the known limitation, not a new result).
2. Study period T versus real time t: for one scenario and a fixed T*, the real-time cumulative M_T*(t) (initial at
   t=0, rates and events as they occur, terminal amounts only at t=T*) is compared with the study-period function
   C(t). C(T*) = M_T*(T*) must hold; for t < T* the gap is the terminal part Z(t) (TH-4), so C is not a cumulative.

Usage: python3 -B tools/band_and_realtime.py <foundation_checkout> <out_dir>
"""
import csv
import json
import math
import os
import sys
from fractions import Fraction

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import five_families as ff  # noqa: E402
from run_reconstruction import COMP, DIRECT, same, shape_of, to_kernel  # noqa: E402


def values(can, kern, T):
    inc = {s: int(bool(v)) for s, v in can.inc.items()}
    V = {u: ff.f3_value(kern[u], T) for u in DIRECT}
    comp = [(s, u, sg, (inc.get("B2", 0) if b == "B2" else b)) for s, u, sg, b in COMP]
    S, C = ff.f5_aggregate(V, comp, inc)
    return V, C, comp, inc


def main(fnd, out):
    code = os.path.join(fnd, "whole-life-carbon-jcat-study", "17_WHOLE_BUILDING_TIME_THEORY", "code")
    sys.path.insert(0, code)
    import canon                                    # noqa: E402
    from checks import sets_unified                # noqa: E402
    from tstudy import baseline, scenarios          # noqa: E402
    baseline.assert_frozen()
    baseline.load()
    from synth import population                    # noqa: E402
    os.makedirs(out, exist_ok=True)
    rows, demo = [], None
    sets = sets_unified.build(["dev_edge", "dev_design", "new_special"])
    for name, cases in sets.items():
        for n, (label, scn, periods) in enumerate(cases[:40]):
            devs = [d for d in scn.refrigerants if d.change_years]
            sysm = canon.make_system(scn, population.BASELINES)
            can = canon.build(sysm)
            kern = {u: [to_kernel(t) for t in can.unit_terms.get(u, [])] for u in DIRECT}
            if demo is None and name == "dev_design":
                demo = (label, can, kern)
            if not devs:
                continue
            Ks = sorted({int(y) for d in devs for y in d.change_years if 1 <= int(y) < can.H})[:3]
            for K in Ks:
                for rel in ("next", 5e-11, 3e-10, 3e-8):
                    T = math.nextafter(float(K), math.inf) if rel == "next" else K * (1.0 + rel)
                    cur = scenarios.with_period(scn, T)
                    ref = baseline.run_reference(cur)
                    V, C, _, _ = values(can, kern, T)
                    inside = T < K / (1.0 - ff.EPS)
                    row = dict(set=name, label=label, K=K, rel_offset=str(rel), T=T, inside_band=inside,
                               in_old_valid_domain=not scenarios.valid_domain(cur))
                    for u in ("B1-02", "B1-03", "B1-04"):
                        row[u + "_ok"] = same(float(V[u]), ref[u]["value"])
                        row[u + "_rel"] = abs(float(V[u]) - ref[u]["value"]) / max(abs(ref[u]["value"]), 1e-300)
                    row["SUM-03_ok"] = same(float(C), ref["SUM-03"]["value"])
                    row["SUM-03_rel"] = abs(float(C) - ref["SUM-03"]["value"]) / max(abs(ref["SUM-03"]["value"]), 1e-300)
                    rows.append(row)
        if len(rows) >= 48:
            break
    summ = dict(n_tests=len(rows),
                inside_band=dict(n=sum(r["inside_band"] for r in rows),
                                 sum03_mismatch=sum(r["inside_band"] and not r["SUM-03_ok"] for r in rows),
                                 unit_mismatch=sum(r["inside_band"] and not all(r[u + "_ok"] for u in ("B1-02", "B1-03", "B1-04")) for r in rows)),
                outside_band=dict(n=sum(not r["inside_band"] for r in rows),
                                  sum03_mismatch=sum((not r["inside_band"]) and not r["SUM-03_ok"] for r in rows),
                                  unit_mismatch=sum((not r["inside_band"]) and not all(r[u + "_ok"] for u in ("B1-02", "B1-03", "B1-04")) for r in rows)),
                distinct_scenario_K=len({(r["label"], r["K"]) for r in rows}),
                scenario_K_with_any_mismatch=len({(r["label"], r["K"]) for r in rows if not (r["SUM-03_ok"] and r["B1-04_ok"] and r["B1-02_ok"])}))
    json.dump(dict(summary=summ, rows=rows), open(os.path.join(out, "band_test.json"), "w"), ensure_ascii=False, indent=1)
    print("BAND", json.dumps(summ, ensure_ascii=False))
    # ---- 2. study period vs real time ---------------------------------------------------------------------------
    label, can, kern = demo
    H = can.H
    Tstar = float(min(H, 60))
    _, CT, comp, inc = values(can, kern, Tstar)
    terminal_kernels, other_kernels = [], []
    for st, u, sg, b in comp:
        if not inc.get(st, 0) or not b:
            continue
        for t, k in zip(can.unit_terms.get(u, []), kern[u]):
            sh = shape_of(u, t.kind)[0]
            kk = ff.Kernel(k.a * sg * b, k.s, k.l, k.g, k.lo, k.hi)
            (terminal_kernels if sh.startswith("TERMINAL") else other_kernels).append(kk)
    grid = [x / 4 for x in range(1, int(Tstar * 4) + 1)]
    series = []
    for t in grid:
        Ct = values(can, kern, t)[1]
        Zt = ff.f3_value(terminal_kernels, t)
        Mt = ff.f3_value(other_kernels, t) + (ff.f3_value(terminal_kernels, Tstar) if t >= Tstar else 0)
        series.append(dict(t=t, C_of_T=float(Ct), realtime_cumulative_for_Tstar=float(Mt), terminal_Z_of_t=float(Zt),
                           identity_C_eq_nonterminal_plus_Z=(Ct == ff.f3_value(other_kernels, t) + Zt)))
    with open(os.path.join(out, "realtime_vs_T.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(series[0]))
        w.writeheader()
        w.writerows(series)
    rt = dict(scenario=label, H=H, Tstar=Tstar, C_Tstar=float(CT), M_Tstar_at_Tstar=series[-1]["realtime_cumulative_for_Tstar"],
              equal_at_Tstar=(abs(float(CT) - series[-1]["realtime_cumulative_for_Tstar"]) <= 1e-9 * abs(float(CT))),
              identity_holds_all_points=all(s["identity_C_eq_nonterminal_plus_Z"] for s in series),
              max_gap_before_Tstar=max(abs(s["C_of_T"] - s["realtime_cumulative_for_Tstar"]) for s in series[:-1]),
              gap_equals_Z_before_Tstar=all(abs((s["C_of_T"] - s["realtime_cumulative_for_Tstar"]) - s["terminal_Z_of_t"]) <= 1e-9 * max(1.0, abs(s["C_of_T"])) for s in series[:-1]))
    json.dump(rt, open(os.path.join(out, "realtime_vs_T.json"), "w"), ensure_ascii=False, indent=1)
    print("REALTIME", json.dumps(rt, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
