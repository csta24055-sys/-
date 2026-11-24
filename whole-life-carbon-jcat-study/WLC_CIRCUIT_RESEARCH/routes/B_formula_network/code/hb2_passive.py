"""H-B2 numeric ILLUSTRATION (not a proof; the proof sketch is in claims.md, status [H] pending route D).

Scope (corrected after route D pass 2): LUMPED, LINEAR, TIME-INVARIANT RC networks whose independent sources
are real-analytic on (0, inf) (e.g. DC switched on at T=0). Their responses are real-analytic for T>0 and
cannot coincide with a kernel that has a kink (year cell w_0, knot T=1) or a jump (atom theta(T;1)) on any
interval containing the knot. This is NOT a physical impossibility: time-varying passive networks (an ideal
switch closed on (k, k+1] between a DC current source and a capacitor), nonlinear passive networks (ideal-diode
clipper) and a switch + charged capacitor reproduce kinks/jumps exactly. Class labels in MAPPING.csv are
relative to the grammar G.

Fitted family: c0 + c1*T + sum_i c_i exp(-lambda_i T), unconstrained real c, fixed lambda grid. It contains the
responses of LTI RC networks with DC voltage/current sources whose poles are 0 (incl. the double root s=0 that
gives the ramp c*T of a DC current source into a capacitor) or lie on the fixed lambda grid. It is NOT a
superset of all LTI RC responses (other poles, repeated poles T*exp(-lambda T), sinusoidal sources): this is an
illustration of the analytic obstruction, not a bound over all LTI networks. For the jump the sup error of ANY
continuous function is >= J/2 = 0.5 (elementary bound, valid for every LTI response); for the kink the error
shrinks with the order (it tends to 0 as the order grows, Muentz-type density) but is never 0 at finite order
(identity theorem). Floating point (numpy lstsq, ill-conditioned for many terms): [F] illustration only.
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
    A = np.column_stack([np.ones_like(T), T] + [np.exp(-l * T) for l in lams])   # 1, ramp (s=0 double root), exps
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
    out["basis"] = "1, T, exp(-lambda_i T) with lambda_i = logspace(-1, 2, n)"
    return out


def main():
    res = run()
    with open(os.path.join(ROUTE, "results", "hb2_illustration.json"), "w") as f:
        json.dump(res, f, indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
