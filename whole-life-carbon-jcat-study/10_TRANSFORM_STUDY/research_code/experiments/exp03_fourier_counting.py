"""EXP-03 (exploration): Fourier representation of the event-counting function.

The renewal emission is  B4(T) = sum_c U_c * N(T, c) + (explicit event lists),  where U_c is the
emission of one renewal summed over the rows with period c and N(T, c) = #{n >= 1 : n*c < T} is a
step function (for x = T/c not an integer N = floor(x); at an integer x the event at T itself is
not counted, N = x - 1).

Fourier series of the floor function (x not an integer):
    floor(x) = x - 1/2 + (1/pi) * sum_{m>=1} sin(2 pi m x) / m
Variants measured here (all are APPROXIMATIONS unless stated):
    smooth       N ~ max(0, x - 1/2)                      (no oscillatory term)
    smooth_unclipped  N ~ x - 1/2                         (unbiased for a uniformly distributed phase, may be negative)
    old_minus1   N ~ max(0, x - 1)                        (the continuous form of the earlier study, for comparison)
    dirichlet_M  x - 1/2 + (1/pi) sum_{m<=M} sin(2 pi m x)/m
    fejer_M      the same with Fejer factors (1 - m/(M+1))      (no Gibbs overshoot)
    lanczos_M    the same with Lanczos sigma factors sinc(m/(M+1))
    shifted_*    the series evaluated at x - d, d = 1/(2(M+1)): a re-design that respects
                 "an event at T is not counted" (the left limit) within the resolution of the series
    lattice      EXACT on an integer time lattice: for integer T and integer c,
                 N = floor((T-1)/c) = (T-1)/c - frac, frac = (c-1)/(2c) - (1/(2c)) sum_{m=1}^{c-1} cot(pi m/c) sin(2 pi m (T-1)/c)
                 (finite discrete Fourier sum with c-1 terms; measured only on pairs where it applies)
The error is measured on the B4 stage value and, propagated through the stage vector, on the
whole-life total SUM-03, against the frozen reference.

Run from research_code:  python3 -B -m experiments.exp03_fourier_counting [n_scenarios] [max_size]
"""
from __future__ import annotations

import json
import math
import os
import sys
import time

sys.dont_write_bytecode = True

import numpy as np

from tstudy import baseline, metrics, rampstep as rs, scenarios

HORIZON = 120.0
HARMONICS = (1, 2, 4, 8, 16, 64, 256)


def classes(scn, res):
    """Renewal emission per period class, explicit atoms, from one reference run at the horizon."""
    H = scn.boundary.study_period
    b4 = res["B4-02"]
    per: dict[float, float] = {}
    explicit: list[tuple[float, float]] = []
    for i, row in enumerate(scn.materials):
        ev = rs.periodic_times(H, row.refresh_cycle)
        if ev:
            per[float(row.refresh_cycle)] = per.get(float(row.refresh_cycle), 0.0) + b4["by_item_material"][i] / len(ev)
    for j, eq in enumerate(scn.equipment):
        if eq.replacement_event_list is not None:
            ev = rs.explicit_times(H, eq.replacement_event_list)
            if ev:
                u = b4["by_item_equipment"][j] / len(ev)
                explicit += [(u, tau) for tau in ev]
        else:
            ev = rs.periodic_times(H, eq.service_life)
            if ev:
                per[float(eq.service_life)] = per.get(float(eq.service_life), 0.0) + b4["by_item_equipment"][j] / len(ev)
    return per, explicit


def n_exact(T: float, c: float) -> int:
    return len(rs.periodic_times(T, c))


def series(x: np.ndarray, M: int, kind: str) -> np.ndarray:
    """Partial Fourier sum of floor(x) for an array of arguments."""
    m = np.arange(1, M + 1, dtype=float)
    if kind == "dirichlet":
        sigma = np.ones(M)
    elif kind == "fejer":
        sigma = 1.0 - m / (M + 1.0)
    else:
        z = np.pi * m / (M + 1.0)
        sigma = np.sin(z) / z
    s = (np.sin(2.0 * np.pi * np.outer(x, m)) * (sigma / m)).sum(axis=1)
    return x - 0.5 + s / np.pi


def n_lattice(T: int, c: int) -> float:
    n = T - 1
    s = 0.0
    for m in range(1, c):
        s += math.cos(math.pi * m / c) / math.sin(math.pi * m / c) * math.sin(2.0 * math.pi * m * n / c)
    frac = 0.0 if n % c == 0 else (c - 1) / (2.0 * c) - s / (2.0 * c) + 0.5 / c
    # {n/c} = 1/2 - 1/(2c) ... written out: for n not a multiple of c, n mod c = c*(1/2 + sawtooth(n/c)),
    # sawtooth(n/c) = -(1/(2c)) * sum cot(pi m/c) sin(2 pi m n/c)
    if n % c != 0:
        frac = 0.5 - s / (2.0 * c)
    return n / c - frac


def variants() -> list[str]:
    out = ["smooth", "smooth_unclipped", "old_minus1"]
    for M in HARMONICS:
        for kind in ("dirichlet", "fejer", "lanczos"):
            out += [f"{kind}_{M}", f"shifted_{kind}_{M}"]
    return out


def approx_n(name: str, T: float, c: np.ndarray) -> np.ndarray:
    x = T / c
    if name == "smooth":
        return np.maximum(0.0, x - 0.5)
    if name == "smooth_unclipped":
        return x - 0.5
    if name == "old_minus1":
        return np.maximum(0.0, x - 1.0)
    shifted = name.startswith("shifted_")
    kind, M = name.replace("shifted_", "").rsplit("_", 1)
    M = int(M)
    if shifted:
        x = x - 0.5 / (M + 1.0)
    return np.where(x > 0.0, np.maximum(0.0, series(x, M, kind)), 0.0)


def main(argv) -> int:
    n = int(argv[1]) if len(argv) > 1 else 40
    max_size = argv[2] if len(argv) > 2 else "M"
    trees = baseline.assert_frozen()
    sets = {"design": scenarios.design_set(n, max_size), "evaluation": scenarios.evaluation_set(n, max_size)}
    names = variants()
    stats = {}
    exact_check = metrics.ErrorStats("B4 from classes (exact)")
    lattice = {"B4": metrics.ErrorStats("B4 lattice"), "n_pairs": 0}
    n_pairs = 0
    n_classes: list[int] = []
    t0 = time.time()
    for set_name, scns in sets.items():
        for scn in scns:
            top = scenarios.with_period(scn, HORIZON)
            if scenarios.valid_domain(top):
                continue
            per, explicit = classes(top, baseline.run_reference(top, ["B4-02"]))
            n_classes.append(len(per))
            for T in sorted(set(scenarios.SWEEP_PERIODS) | {scn.boundary.study_period}):
                cur = scenarios.with_period(scn, T)
                if scenarios.valid_domain(cur):
                    continue
                ref = baseline.run_reference(cur)
                b4_ref = ref["B4-02"]["value"]
                stage = ref["X-02"]["by_stage"]
                inc = cur.boundary.included_lifecycle_stages
                if "B4" not in stage:
                    continue
                n_pairs += 1
                sid = cur.meta.scenario_id
                ex = math.fsum(u for u, tau in explicit if tau < T * (1.0 - rs.EPS))
                exact = ex + math.fsum(U * n_exact(T, c) for c, U in per.items())
                exact_check.add(exact, b4_ref, sid)
                c_arr = np.array(list(per.keys()), dtype=float)
                u_arr = np.array(list(per.values()), dtype=float)
                for name in names:
                    b4 = ex + (float(u_arr @ approx_n(name, T, c_arr)) if len(c_arr) else 0.0)
                    tot = metrics.propagate_stage_change(stage, inc, {"B4": b4})["SUM-03"]
                    stats.setdefault(f"{set_name}|B4|{name}", metrics.ErrorStats(name)).add(b4, b4_ref, sid)
                    stats.setdefault(f"{set_name}|SUM-03|{name}", metrics.ErrorStats(name)).add(tot, ref["SUM-03"]["value"], sid)
                if float(T).is_integer() and per and all(float(c).is_integer() and c <= 400 for c in per):
                    b4 = ex + math.fsum(U * n_lattice(int(T), int(c)) for c, U in per.items())
                    lattice["B4"].add(b4, b4_ref, sid)
                    lattice["n_pairs"] += 1
    out = {
        "experiment": "EXP-03", "title": "Fourier representation of the event-counting function (renewals, stage B4)",
        "evidence_level": "N (numerical, exploration); approximations unless marked exact", "checked_by": "author only",
        "data_statement": "fictional scenarios of the frozen generator; independent concept model; says nothing about real buildings",
        "frozen_trees": trees, "n_scenarios": {k: len(v) for k, v in sets.items()}, "n_scenario_period_pairs": n_pairs,
        "period_classes_per_scenario": {"min": min(n_classes), "max": max(n_classes), "mean": sum(n_classes) / len(n_classes)},
        "exact_class_form": exact_check.summary(),
        "lattice_exact_form": {"n_pairs_where_it_applies": lattice["n_pairs"], "B4": lattice["B4"].summary()},
        "stats": {k: s.summary() for k, s in sorted(stats.items())}, "seconds": round(time.time() - t0, 1),
    }
    dest = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "03_ROUTES", "experiments")
    os.makedirs(dest, exist_ok=True)
    with open(os.path.join(dest, "EXP-03_fourier_counting.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("pairs", n_pairs, "classes", out["period_classes_per_scenario"], "seconds", out["seconds"])
    print("exact class form max_abs", exact_check.summary()["max_abs"])
    print("lattice exact form", lattice["n_pairs"], lattice["B4"].summary()["max_abs"])
    print(f"{'variant':28s} {'B4 mean':>9s} {'B4 p95':>9s} {'B4 max':>9s} | {'tot mean':>9s} {'tot p95':>9s} {'tot max':>9s}")
    for name in names:
        b = stats[f"evaluation|B4|{name}"].summary()
        t = stats[f"evaluation|SUM-03|{name}"].summary()
        print(f"{name:28s} {b['mean_signed']*100:9.3f} {b['p95_abs']*100:9.3f} {b['max_abs']*100:9.3f} | "
              f"{t['mean_signed']*100:9.4f} {t['p95_abs']*100:9.4f} {t['max_abs']*100:9.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
