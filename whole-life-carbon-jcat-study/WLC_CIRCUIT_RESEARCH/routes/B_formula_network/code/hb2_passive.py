"""H-B2 numeric ILLUSTRATION (not a proof; the proof sketch is in claims.md, status [H] pending route D).

Claim illustrated: a lumped passive LTI RC network driven by sources that are analytic in T (DC switched on
at T=0) has, for T>0, a response y(T) = c0 + sum_i c_i exp(-lambda_i T) with lambda_i > 0 (an exponential
polynomial, real-analytic). It cannot coincide with a kernel that has a kink (year cell w_0, knot T=1) or a
jump (atom theta(T;1)) on any interval containing the knot.

Here we fit the LARGER family {c0 + sum_i c_i exp(-lambda_i T)} with unconstrained real c_i (every passive
RC response is in it) on [0, 2] by least squares, for growing numbers of fixed time constants, and report the
sup error on a dense grid. For the jump the sup error of ANY continuous function is >= J/2 = 0.5 (elementary
bound); for the kink the error shrinks with the order but never reaches 0 (identity theorem). Floating point
(numpy lstsq, ill-conditioned for many terms): this is [F] illustration only.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROUTE = os.path.dirname(HERE)


def fit(target, n_terms: int, T):
    lams = np.logspace(-1, 2, n_terms) if n_terms else np.array([])
    A = np.column_stack([np.ones_like(T)] + [np.exp(-l * T) for l in lams])
    c, *_ = np.linalg.lstsq(A, target, rcond=None)
    y = A @ c
    err = np.abs(y - target)
    near = np.abs(T - 1.0) <= 0.05
    return {"n_exponentials": int(n_terms), "sup_error": float(err.max()), "rms_error": float(np.sqrt(np.mean(err ** 2))),
            "sup_error_near_knot": float(err[near].max()), "sup_error_away_from_knot": float(err[~near].max())}


def run():
    T = np.linspace(0.0, 2.0, 4001)
    kink = np.clip(T, 0.0, 1.0)                      # w_0(T): knot at T=1 (slope 1 -> 0)
    jump = (T > 1.0).astype(float)                   # atom: jump of 1 at T=1 (the side convention is irrelevant)
    out = {"interval": [0.0, 2.0], "grid_points": int(T.size), "kink_w0": [], "jump_atom": []}
    for n in (1, 2, 4, 8, 16, 24):
        out["kink_w0"].append(fit(kink, n, T))
        out["jump_atom"].append(fit(jump, n, T))
    out["jump_lower_bound_any_continuous"] = 0.5
    return out


def main():
    res = run()
    with open(os.path.join(ROUTE, "results", "hb2_illustration.json"), "w") as f:
        json.dump(res, f, indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
