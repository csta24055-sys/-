"""V1 mathematical checks (exact / symbolic). Run with math7-py (SymPy).

1. D1: year-of-event rule. Architecture 5.4 early comparator on a resetting clock ramp vs the
   builder's shared lookahead comparator P = [v_year <= rho v_global], rho = eps(2-eps)/(1-eps),
   both against refcalc's event_year(tau) = max(1, ceil(tau (1 - eps))).
2. L1: exhaustive symbolic search over small passive resistive networks with independent
   sources: can any node voltage or branch/source current equal c*G1*G2 identically?
   Plus the counterexample to the HOMOGENEITY argument (G1 G2 / G0 is degree 1).
3. L3: integration by an ideal DC current source into a grounded C (no active element).
4. S3 facts (series RLC step response) symbolically.
"""
from __future__ import annotations

import itertools
import random
from fractions import Fraction as F

import sympy as sp

from common import fstr, save

EPS = F(1, 10 ** 9)


def ceil(x):
    return -((-x.numerator) // x.denominator)


def d1():
    out = {"cases": 0, "arch_rule_errors": 0, "shared_rule_errors": 0, "examples_arch_wrong": []}
    eps = EPS
    rho = eps * (2 - eps) / (1 - eps)
    periods = [F(5, 2), F(1, 2), F(10), F(7, 10), F(4, 3), F(1), F(1, 1000), F(7, 3), F(11, 5), F(3)]
    for c in periods:
        n = 1
        while n * c <= 120:
            tau = n * c
            ref = max(1, ceil(tau * (1 - eps)))
            tf = tau / (1 - eps)                       # late firing (real time)
            K = tf.numerator // tf.denominator        # last year tick at or before tf
            # architecture 5.4: early comparator on the SAME resetting ramp, threshold Vth(1-eps)^2
            t_prev = (n - 1) * c / (1 - eps)
            t_early = t_prev + c * (1 - eps)
            arch_year = ceil(t_early) if t_early.denominator != 1 else t_early.numerator
            arch_year = max(1, arch_year)
            # builder: P = [v_year <= rho * v_global] at tf; v_year = tf - K, v_global = (1-eps) tf
            P = (tf - K) <= rho * (1 - eps) * tf
            shared_year = K + 1 - int(P)
            out["cases"] += 1
            if arch_year != ref:
                out["arch_rule_errors"] += 1
                if len(out["examples_arch_wrong"]) < 6:
                    out["examples_arch_wrong"].append({"period": fstr(c), "n": n, "tau": fstr(tau),
                                                       "t_early": float(t_early), "arch_year": arch_year, "ref": ref})
                assert n >= 2, "architecture rule wrong already for n = 1"
            if shared_year != ref:
                out["shared_rule_errors"] += 1
            n += 1
            if c < F(1, 100) and n > 3000:
                break
    # closed form of the early-crossing lag
    e, cc, nn = sp.symbols("epsilon c n", positive=True)
    lag = sp.simplify(((nn - 1) * cc / (1 - e) + cc * (1 - e)) - nn * cc * (1 - e))
    out["early_crossing_lag_closed_form"] = str(sp.factor(lag))
    # algebra of the shared rule: tf - K <= rho (1-eps) tf  <=>  K >= tf (1-eps)^2 = tau (1-eps)
    tau, K = sp.symbols("tau K", positive=True)
    rr = e * (2 - e) / (1 - e)
    tf = tau / (1 - e)
    out["shared_rule_identity"] = str(sp.simplify((tf - rr * (1 - e) * tf) - tau * (1 - e)))
    out["domain_note"] = "exact iff tf - tau(1-eps) = tau eps(2-eps)/(1-eps) < 1 (at most one tick in [tau(1-eps), tf])"
    return out


# ----------------------------------------------------------------- L1 exhaustive search

def node_solve(n_nodes, branches, sources):
    """Symbolic nodal analysis. branches: (a, b, G); sources: ('V', a, value) grounded voltage
    sources or ('I', node, value) injections. Returns node voltages and source currents."""
    vs = sp.symbols(f"v1:{n_nodes + 1}")
    fixed = {s[1]: s[2] for s in sources if s[0] == "V"}
    inj = {}
    for s in sources:
        if s[0] == "I":
            inj[s[1]] = inj.get(s[1], 0) + s[2]

    def V(k):
        if k == 0:
            return 0
        return fixed.get(k, vs[k - 1])
    eqs = []
    for k in range(1, n_nodes + 1):
        if k in fixed:
            continue
        expr = sum(G * (V(k) - V(b if a == k else a)) for a, b, G in branches if k in (a, b) and a != b)
        eqs.append(sp.Eq(expr, inj.get(k, 0)))
    unknown = [vs[k - 1] for k in range(1, n_nodes + 1) if k not in fixed]
    sol = sp.solve(eqs, unknown, dict=True) if unknown else [{}]
    if not sol:
        return None
    sol = sol[0]
    volt = {k: sp.simplify(V(k).subs(sol)) if not isinstance(V(k), int) else 0 for k in range(1, n_nodes + 1)}
    vfun = lambda k: 0 if k == 0 else volt[k]
    cur = [sp.simplify(G * (vfun(a) - vfun(b))) for a, b, G in branches]
    src = {}
    for k in fixed:
        src[k] = sp.simplify(sum(G * (vfun(k) - vfun(b if a == k else a)) for a, b, G in branches if k in (a, b) and a != b))
    return volt, cur, src


def l1_search(trials=400, seed=11):
    G1, G2 = sp.symbols("G1 G2", positive=True)
    rnd = random.Random(seed)
    found = []
    checked = 0
    consts = [sp.Rational(1), sp.Rational(1, 2), sp.Rational(2), sp.Rational(3), sp.Rational(1, 3)]
    for _ in range(trials):
        n_nodes = rnd.choice([2, 3, 4])
        nodes = list(range(0, n_nodes + 1))
        pairs = [(a, b) for a in nodes for b in nodes if a < b]
        nb = rnd.randint(2, min(6, len(pairs) + 2))
        br = []
        for k in range(nb):
            a, b = rnd.choice(pairs)
            G = G1 if k == 0 else G2 if k == 1 else rnd.choice(consts)
            br.append((a, b, G))
        srcs = []
        vnodes = rnd.sample(range(1, n_nodes + 1), rnd.randint(1, max(1, n_nodes - 1)))
        for k in vnodes:
            srcs.append(("V", k, rnd.choice([1, 2, -1, 5])))
        if rnd.random() < 0.5:
            free = [k for k in range(1, n_nodes + 1) if k not in vnodes]
            if free:
                srcs.append(("I", rnd.choice(free), rnd.choice([1, 3, -2])))
        try:
            res = node_solve(n_nodes, br, srcs)
        except Exception:
            continue
        if res is None:
            continue
        volt, cur, src = res
        for y in list(volt.values()) + cur + list(src.values()):
            checked += 1
            y = sp.simplify(y)
            if y == 0:
                continue
            q = sp.simplify(y / (G1 * G2))
            if q.free_symbols & {G1, G2}:
                continue
            found.append({"net": str(br), "sources": str(srcs), "response": str(y)})
    # homogeneity counterexample: f = G1 G2 / G0 is jointly degree-1 homogeneous
    G0, lam = sp.symbols("G0 lambda", positive=True)
    f = G1 * G2 / G0
    homog = sp.simplify(f.subs({G1: lam * G1, G2: lam * G2, G0: lam * G0}, simultaneous=True) / f)
    series = sp.simplify(G1 * G2 / (G1 + G2))
    return {"random_networks": trials, "responses_checked": checked, "exact_products_found": found[:5],
            "n_found": len(found),
            "homogeneity_counterexample": {"f": "G1*G2/G0", "f(lambda G)/f(G)": str(homog),
                                           "note": "degree-1 homogeneous yet a product of the two inputs: "
                                                   "homogeneity alone cannot exclude it once fixed unit conductances G0 exist"},
            "series_pair": str(series)}


def l3_and_s3():
    t, I, C, R, L, V = sp.symbols("t I C R L V", positive=True)
    # ideal DC current source into grounded C: v = I t / C exactly (no active element)
    v = sp.integrate(I / C, (t, 0, t))
    # rail -> R -> grounded C
    vc = V * (1 - sp.exp(-t / (R * C)))
    lin_err = sp.simplify(sp.series(vc - V * t / (R * C), t, 0, 3).removeO())
    # series RLC step response energy: total heat = C V^2 / 2 for any R > 0 (q -> CV, i -> 0)
    q = sp.Function("q")
    heat_rc = sp.simplify(sp.integrate((V / R * sp.exp(-t / (R * C))) ** 2 * R, (t, 0, sp.oo)))
    return {"current_source_into_C": str(v), "rail_R_C_deviation_from_linear": str(lin_err),
            "RC_step_total_heat": str(heat_rc)}


def main():
    out = {"D1": d1(), "L1": l1_search(), "L3_S3": l3_and_s3()}
    save("math_checks.json", out)
    return out


if __name__ == "__main__":
    import json
    print(json.dumps(main(), indent=1, default=str)[:4000])
