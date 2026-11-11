"""EXP-02: the knot spectrum (truncated-power form) of the use stage - exactness, size, speed.

For each scenario: ONE reference run at the horizon -> pieces (EXP-01) -> knot spectra of the
nine T-dependent units. Then the 14 stage values and the three totals at every T of a dense
sweep come from prefix sums (two binary searches per unit). Compared with a fresh reference
run at each T. Also recorded: number of knots against number of input rows, and run times
(same machine, same language; a reference value only, not a statement about other tools).

Run from research_code:  python3 -B -m experiments.exp02_knot_spectrum [n_scenarios] [max_size] [with_L]
"""
from __future__ import annotations

import json
import math
import os
import sys
import time

sys.dont_write_bytecode = True

from experiments.exp01_rampstep_sweep import CONST_UNITS, HORIZON, STAGES, T_UNITS, assemble
from tstudy import baseline, metrics, scenarios
from tstudy.knots import KnotSpectrum

DENSE = [0.5, 1.0, 1.5] + [float(t) for t in range(2, 121)] + [7.5, 12.25, 33.3, 42.5, 59.9, 60.1, 62.5, 99.9, 119.99]


def stage_values(v, const, included):
    full = {
        "A1-A3": const["A13-01"] + const["A13-03"] + const["A13-04"] + const["X-01"],
        "A4": const["A4-01"] + const["A4-02"], "A5": const["A5-04"],
        "B1": v["B1-02"] + v["B1-03"] + v["B1-04"], "B2": v["B2-01"], "B3": v["B3-01"], "B4": v["B4-02"],
        "B5": v["B5-01"], "B6": v["B6-03"] - v["B2-01"], "B7": v["B7-04"],
        "C1": const["C1-01"], "C2": const["C2-01"], "C3": const["C3-01"] + const["X-14"], "C4": const["C4-01"],
    }
    inc = set(included)
    by_stage = {s: full[s] for s in STAGES if s in inc}
    if "B6" in inc and "B2" not in inc:
        by_stage["B6"] = v["B6-03"]
    return by_stage


def main(argv) -> int:
    n = int(argv[1]) if len(argv) > 1 else 20
    max_size = argv[2] if len(argv) > 2 else "M"
    with_l = len(argv) > 3 and argv[3] == "L"
    trees = baseline.assert_frozen()
    bench = scenarios.benchmark()
    sets = {"benchmark": bench if with_l else bench[:2], "design": scenarios.design_set(n, max_size),
            "evaluation": scenarios.evaluation_set(n, max_size), "edge": [s for _, s in scenarios.edge_set()]}
    stats: dict[str, metrics.ErrorStats] = {}
    sizes = []
    excluded = []
    n_pairs = 0
    t_ref = t_ks = t_asm = 0.0
    for set_name, scns in sets.items():
        for scn in scns:
            top = scenarios.with_period(scn, HORIZON)
            why = scenarios.valid_domain(top)
            if why or len(top.operation.grid.table) < math.ceil(HORIZON):
                excluded.append((top.meta.scenario_id, why or ["year tables shorter than the horizon"]))
                continue
            t = time.perf_counter()
            res_top = baseline.run_reference(top)
            t_one_ref = time.perf_counter() - t
            t = time.perf_counter()
            P = assemble(top, res_top)
            K = {u: KnotSpectrum(P[u]) for u in T_UNITS}
            const = {u: res_top[u]["value"] for u in CONST_UNITS}
            t_asm += time.perf_counter() - t
            rows = len(scn.materials) + len(scn.equipment) + len(scn.refrigerants)
            sizes.append({"scenario": scn.meta.scenario_id, "set": set_name, "size_class": scn.meta.size_class,
                          "input_rows": rows, "pieces": sum(len(P[u]) for u in T_UNITS),
                          "knots": sum(K[u].n_knots for u in T_UNITS),
                          "distinct_knot_times": len({k for u in T_UNITS for k in K[u].ev_keys} | {k for u in T_UNITS for k in K[u].la_keys}),
                          "reference_seconds_one_T": t_one_ref})
            periods = DENSE if set_name == "benchmark" else sorted(set(scenarios.SWEEP_PERIODS) | {scn.boundary.study_period})
            for T in periods:
                cur = scenarios.with_period(scn, T)
                if scenarios.valid_domain(cur):
                    excluded.append((cur.meta.scenario_id, scenarios.valid_domain(cur)))
                    continue
                t = time.perf_counter()
                ref = baseline.run_reference(cur)
                t_ref += time.perf_counter() - t
                t = time.perf_counter()
                v = {u: K[u].value(T) for u in T_UNITS}
                by_stage = stage_values(v, const, cur.boundary.included_lifecycle_stages)
                tot = metrics.propagate_stage_change(by_stage, list(cur.boundary.included_lifecycle_stages), {})
                t_ks += time.perf_counter() - t
                n_pairs += 1
                sid = cur.meta.scenario_id
                for u in T_UNITS:
                    stats.setdefault(f"{set_name}|unit|{u}", metrics.ErrorStats(u)).add(v[u], ref[u]["value"], sid)
                for s, x in ref["X-02"]["by_stage"].items():
                    stats.setdefault(f"{set_name}|stage|{s}", metrics.ErrorStats(s)).add(by_stage[s], x, sid)
                for k in ("SUM-01", "SUM-02", "SUM-03"):
                    stats.setdefault(f"{set_name}|total|{k}", metrics.ErrorStats(k)).add(tot[k], ref[k]["value"], sid)
    summ = {k: s.summary() for k, s in sorted(stats.items())}
    worst = max((s["max_abs"] or 0.0) for s in summ.values())
    out = {
        "experiment": "EXP-02", "title": "knot spectrum (truncated-power form) of the use stage",
        "evidence_level": "N (numerical, exploration)", "checked_by": "author only",
        "data_statement": "fictional scenarios of the frozen generator; independent concept model; says nothing about real buildings",
        "frozen_trees": trees, "horizon": HORIZON, "amplitudes": "row amplitudes from ONE reference run at the horizon",
        "n_scenarios": {k: len(v) for k, v in sets.items()}, "n_scenario_period_pairs": n_pairs, "excluded": excluded,
        "max_abs_rel_error_over_all_quantities": worst,
        "max_abs_when_reference_is_zero": max(s["max_abs_when_ref_zero"] for s in summ.values()),
        "time_reference_all_pairs_s": t_ref, "time_knot_evaluation_all_pairs_s": t_ks, "time_assembly_s": t_asm,
        "note_on_times": "same machine and language; the assembly time excludes the one reference run it starts from",
        "sizes": sizes, "stats": summ,
    }
    dest = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "03_ROUTES", "experiments")
    os.makedirs(dest, exist_ok=True)
    with open(os.path.join(dest, "EXP-02_knot_spectrum.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("pairs", n_pairs, "excluded", len(excluded), "max rel err", worst, "max abs at ref 0", out["max_abs_when_reference_is_zero"])
    print("time: reference %.2fs, knot evaluation %.4fs, assembly %.2fs" % (t_ref, t_ks, t_asm))
    for s in sizes[:3]:
        print(s)
    by = {}
    for s in sizes:
        by.setdefault(s["size_class"], []).append((s["input_rows"], s["knots"], s["distinct_knot_times"]))
    for k, v in by.items():
        print(k, "n", len(v), "rows", sum(a for a, _, _ in v) / len(v), "knots", sum(b for _, b, _ in v) / len(v),
              "distinct knot times", sum(c for _, _, c in v) / len(v))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
