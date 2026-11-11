"""EXP-04 (exploration): proper orthogonal decomposition (POD / SVD) of the T-curves.

Snapshot matrix: one row per fictional scenario of the DESIGN set, one column per study period
T = 1..120; entry = whole-life total SUM-03(T) per m2 of gross floor area. (The curves come from
the knot spectrum of EXP-02, i.e. from one reference run per scenario; EXP-02 checks that form
against the reference.) The right singular vectors are "time modes".

Measured on the disjoint EVALUATION set (out of sample) and on the design set (in sample):
  projection   the best approximation of a curve in the span of the first r modes
               (needs the whole curve; a lower bound for any method that uses these modes)
  gappy        r coefficients fitted from the curve at r sample periods (chosen by pivoted QR of
               the modes); predicts all other periods from r reference evaluations
Error of a curve = max over T of |approx(T) - exact(T)| / exact(T) (and the value at T = 60).
These are APPROXIMATIONS; the modes depend on the fictional generator (its service lives, its
profiles), so nothing here transfers to real buildings.

Run from research_code:  python3 -B -m experiments.exp04_pod_time_curves [n_scenarios] [max_size]
"""
from __future__ import annotations

import json
import math
import os
import sys
import time

sys.dont_write_bytecode = True

import numpy as np

from experiments.exp01_rampstep_sweep import CONST_UNITS, HORIZON, T_UNITS, assemble
from experiments.exp02_knot_spectrum import stage_values
from tstudy import baseline, metrics, scenarios
from tstudy.knots import KnotSpectrum

GRID = [float(t) for t in range(1, 121)]
RANKS = (1, 2, 3, 4, 6, 8, 12, 16, 24, 32)


def curve(scn) -> np.ndarray | None:
    top = scenarios.with_period(scn, HORIZON)
    if scenarios.valid_domain(top) or len(top.operation.grid.table) < math.ceil(HORIZON):
        return None
    area = scn.project.gross_floor_area
    if area is None or not area > 0.0:
        return None
    res = baseline.run_reference(top)
    P = assemble(top, res)
    K = {u: KnotSpectrum(P[u]) for u in T_UNITS}
    const = {u: res[u]["value"] for u in CONST_UNITS}
    inc = list(scn.boundary.included_lifecycle_stages)
    out = []
    for T in GRID:
        v = {u: K[u].value(T) for u in T_UNITS}
        out.append(metrics.propagate_stage_change(stage_values(v, const, inc), inc, {})["SUM-03"] / area)
    return np.array(out)


def pivot_columns(A: np.ndarray, r: int) -> list[int]:
    """Greedy column pivoting (modified Gram-Schmidt) of an r x m matrix: r well-conditioned columns."""
    R = A.astype(float).copy()
    chosen: list[int] = []
    for _ in range(r):
        norms = (R ** 2).sum(axis=0)
        norms[chosen] = -1.0
        j = int(norms.argmax())
        chosen.append(j)
        q = R[:, j] / np.linalg.norm(R[:, j])
        R = R - np.outer(q, q @ R)
    return chosen


def rel_errors(approx: np.ndarray, exact: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    rel = np.abs(approx - exact) / np.abs(exact)
    return rel.max(axis=1), rel[:, 59]


def summarise(x: np.ndarray) -> dict:
    return {"mean": float(x.mean()), "p95": float(np.percentile(x, 95)), "max": float(x.max())}


def main(argv) -> int:
    n = int(argv[1]) if len(argv) > 1 else 60
    max_size = argv[2] if len(argv) > 2 else "M"
    trees = baseline.assert_frozen()
    t0 = time.time()
    D = [c for c in (curve(s) for s in scenarios.design_set(n, max_size)) if c is not None]
    E = [c for c in (curve(s) for s in scenarios.evaluation_set(n, max_size)) if c is not None]
    X, Z = np.vstack(D), np.vstack(E)
    U, S, Vt = np.linalg.svd(X, full_matrices=False)
    energy = (S ** 2) / (S ** 2).sum()
    rows = []
    for r in RANKS:
        if r > len(S):
            break
        V = Vt[:r].T                                   # 120 x r time modes
        row = {"rank": r, "singular_value_ratio": float(S[r - 1] / S[0]), "energy_captured": float(energy[:r].sum())}
        for name, M in (("design_in_sample", X), ("evaluation_out_of_sample", Z)):
            proj = M @ V @ V.T
            mx, at60 = rel_errors(proj, M)
            row[f"projection|{name}"] = {"max_over_T": summarise(mx), "at_T60": summarise(at60)}
        pts = sorted(pivot_columns(V.T, r))
        A = V[pts, :]
        for name, M in (("design_in_sample", X), ("evaluation_out_of_sample", Z)):
            coef = np.linalg.lstsq(A, M[:, pts].T, rcond=None)[0]
            approx = (V @ coef).T
            mx, at60 = rel_errors(approx, M)
            row[f"gappy|{name}"] = {"max_over_T": summarise(mx), "at_T60": summarise(at60)}
        row["gappy_sample_periods"] = [GRID[p] for p in pts]
        rows.append(row)
    out = {
        "experiment": "EXP-04", "title": "POD / SVD of whole-life total curves over the study period",
        "evidence_level": "N (numerical, exploration); approximation", "checked_by": "author only",
        "data_statement": "fictional scenarios of the frozen generator; independent concept model; the modes depend on the generator and say nothing about real buildings",
        "frozen_trees": trees, "n_design": len(D), "n_evaluation": len(E), "grid": [GRID[0], GRID[-1], len(GRID)],
        "quantity": "SUM-03(T) / gross floor area", "ranks": rows, "seconds": round(time.time() - t0, 1),
    }
    dest = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "03_ROUTES", "experiments")
    os.makedirs(dest, exist_ok=True)
    with open(os.path.join(dest, "EXP-04_pod_time_curves.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("design", len(D), "evaluation", len(E), "seconds", out["seconds"])
    print(f"{'r':>3s} {'sv ratio':>9s} | proj out: {'p95':>8s} {'max':>8s} | gappy out: {'p95':>8s} {'max':>8s} | gappy in: {'p95':>8s} {'max':>8s}")
    for row in rows:
        po, go, gi = row["projection|evaluation_out_of_sample"]["max_over_T"], row["gappy|evaluation_out_of_sample"]["max_over_T"], row["gappy|design_in_sample"]["max_over_T"]
        print(f"{row['rank']:3d} {row['singular_value_ratio']:9.2e} |           {po['p95']*100:8.3f} {po['max']*100:8.3f} |            "
              f"{go['p95']*100:8.3f} {go['max']*100:8.3f} |           {gi['p95']*100:8.3f} {gi['max']*100:8.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
