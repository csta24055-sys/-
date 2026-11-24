"""G4 benchmark: direct Sigma / knot baselines vs the composed circuit paths, same point sets, one machine.

Phi (P0, right convention): 11 contract points + N uniform rationals k/1e6 in [0,60) (seed 20261124).
  (a) closed form Fraction 100+4t+20*floor(t/10)+35*floor(t/20)     (a') same in float
  (b) knots + bisect over cumulative jumps, Fraction
  (c) route D rational ledger oracle, per query
  (d) integration hybrid, charge realization, ONE sorted sweep      (d') joule realization
  (e) integration hybrid, per query from t=0 (random access), on a subset
Psi (EV9, 0 < T <= 60 in domain, M random T, seed 20261125):
  (p) composed circuit (B netlists + summing node), one sorted sweep over all T
  (p1) composed circuit, fresh sweep per T (random access), on a subset
  (q) msp interval/knot form unified.System.at(T) per T (built once)
  (r) refcalc per T (row-by-row reference)
  (s) canon KF exact knot form per T (built once)
Timing: time.perf_counter, median of REPS runs; memory: tracemalloc peak of one separate run.
Run: PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0 python3 -B code/bench_int.py
"""
from __future__ import annotations

import bisect
import math
import random
import statistics
import sys
import time
import tracemalloc
from fractions import Fraction as F

import int_common as IC
import phi_hybrid as PH
import psi_compose as PS

REPS = 5


def timed(fn, reps=REPS):
    ts = []
    for _ in range(reps):
        t0 = time.perf_counter()
        fn()
        ts.append(time.perf_counter() - t0)
    return statistics.median(ts)


def peak(fn):
    tracemalloc.start()
    fn()
    p = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    return p


def phi_bench(n=20000, n_rand_access=2000):
    rng = random.Random(20261124)
    pts = [F(s) for s in ("0", "1", "9.999999", "10", "10.000001", "19.999999", "20", "20.000001", "30", "40", "60")]
    pts += [F(rng.randrange(0, 60 * 10**6), 10**6) for _ in range(n)]
    fpts = [float(p) for p in pts]
    OD = IC.route_d_oracle()

    def closed(t):
        return 100 + 4 * t + 20 * (t // 10) + 35 * (t // 20)
    knots = [F(0)] + [F(10 * k) for k in range(1, 7)]
    jumps = [F(0)]
    for k in range(1, 7):
        jumps.append(jumps[-1] + 20 + (35 if k % 2 == 0 else 0))

    def knot(t):
        i = bisect.bisect_right(knots, t) - 1
        return 100 + 4 * t + jumps[i]
    ref = [closed(t) for t in pts]
    sweep_c = PH.Hybrid(PH.pilot("P0"), "right", "charge")
    sweep_j = PH.Hybrid(PH.pilot("P0"), "right", "joule")
    methods = {
        "(a) closed form Fraction": (lambda: [closed(t) for t in pts], len(pts)),
        "(a') closed form float": (lambda: [100 + 4 * t + 20 * math.floor(t / 10) + 35 * math.floor(t / 20) for t in fpts], len(pts)),
        "(b) knots+bisect Fraction": (lambda: [knot(t) for t in pts], len(pts)),
        "(c) route D ledger oracle per query": (lambda: [OD.G("P0", t) for t in pts[:n_rand_access]], n_rand_access),
        "(d) hybrid charge, one sorted sweep": (lambda: sweep_c.run(pts), len(pts)),
        "(d') hybrid joule, one sorted sweep": (lambda: sweep_j.run(pts), len(pts)),
        "(e) hybrid charge, per query from t=0": (lambda: [PH.Hybrid(PH.pilot("P0"), "right", "charge").G(t) for t in pts[:n_rand_access]], n_rand_access),
    }
    rows = {}
    for name, (fn, npts) in methods.items():
        sec = timed(fn, 3 if "(c)" in name or "(e)" in name else REPS)
        rows[name] = {"us_per_point": 1e6 * sec / npts, "n_points": npts, "tracemalloc_peak_bytes": peak(fn)}
    # correctness on the same points
    rc, rj = sweep_c.run(pts), sweep_j.run(pts)
    float_err = max(abs(100 + 4 * f + 20 * math.floor(f / 10) + 35 * math.floor(f / 20) - float(r)) for f, r in zip(fpts, ref))
    rows["(d) hybrid charge, one sorted sweep"].update({"exact_vs_closed": all(rc[t] == r for t, r in zip(pts, ref)),
                                                        "ops": dict(sweep_c.ops), "state_tuple": sweep_c.state_tuple()})
    rows["(d') hybrid joule, one sorted sweep"].update({"exact_vs_closed": all(rj[t] == r for t, r in zip(pts, ref)),
                                                        "ops": dict(sweep_j.ops), "state_tuple": sweep_j.state_tuple()})
    rows["(a') closed form float"]["max_abs_err_kg"] = float_err
    rows["(a) closed form Fraction"]["state_tuple"] = (0, 0, 0, 0)
    rows["(b) knots+bisect Fraction"]["state_tuple"] = (0, 0, 0, len(knots))
    one = PH.Hybrid(PH.pilot("P0"), "right", "charge")
    one.G(F(59))
    rows["(e) hybrid charge, per query from t=0"]["ops_at_t=59"] = dict(one.ops)
    return {"n_points": len(pts), "rows": rows}


def psi_bench(n=200, n_rand_access=10):
    fz = IC.frozen()
    canon, tc, population = IC.canon_modules()
    scn = IC.psi_scenario("EV9")
    rng = random.Random(20261125)
    Ts = sorted({round(rng.uniform(0.01, 60.0), 6) for _ in range(n)})
    Ts = [T for T in Ts if not IC.domain_violations(scn, T)]
    rows = {}
    pc = PS.PsiComposed(scn)
    sec = timed(lambda: pc.sweep(Ts), 3)
    rows["(p) composed circuit, one sorted sweep"] = {"ms_per_T": 1e3 * sec / len(Ts), "tracemalloc_peak_bytes": peak(lambda: pc.sweep(Ts)),
                                                      "netlists": pc.netcounts}
    sub = Ts[:: max(1, len(Ts) // n_rand_access)][:n_rand_access]
    sec = timed(lambda: [PS.PsiComposed(scn).sweep([T]) for T in sub], 1)
    rows["(p1) composed circuit, fresh build+sweep per T"] = {"ms_per_T": 1e3 * sec / len(sub), "n_T": len(sub)}
    sy = fz["unified"].System(scn)
    sec = timed(lambda: [sy.at(T)["SUM-03"]["value"] for T in Ts], 3)
    rows["(q) msp unified.System.at per T (built once)"] = {"ms_per_T": 1e3 * sec / len(Ts),
                                                            "tracemalloc_peak_bytes": peak(lambda: [sy.at(T) for T in Ts[:20]])}
    sec = timed(lambda: [IC.refcalc_at(scn, T)["SUM-03"]["value"] for T in sub], 1)
    rows["(r) refcalc per T"] = {"ms_per_T": 1e3 * sec / len(sub), "n_T": len(sub)}
    t0 = time.perf_counter()
    can = canon.build(canon.make_system(scn, population.BASELINES))
    kf = tc.KF(can)
    build_s = time.perf_counter() - t0
    sec = timed(lambda: [kf(T) for T in Ts], 3)
    rows["(s) canon KF exact knot form per T (built once)"] = {"ms_per_T": 1e3 * sec / len(Ts), "build_seconds": build_s,
                                                               "n_terms": len(can.terms)}
    res = pc.sweep(Ts)
    rows["agreement"] = {"max_rel_composed_vs_msp": max(IC.rel(res[T]["total"], sy.at(T)["SUM-03"]["value"]) for T in Ts),
                         "max_rel_composed_vs_canon": max(IC.rel(res[T]["total"], kf(T)) for T in Ts)}
    return {"scenario": scn.meta.scenario_id, "n_T": len(Ts), "rows": rows}


def main():
    t0 = time.perf_counter()
    fz = IC.frozen()
    out = {"phi": phi_bench(), "psi": psi_bench()}
    out["meta"] = {**IC.provenance(), "frozen_trees": fz["trees"], "seconds": time.perf_counter() - t0,
                   "reps": REPS, "pycache_after": IC.pycache_dirs()}
    IC.dump("benchmark.json", out)
    for side in ("phi", "psi"):
        for k, v in out[side]["rows"].items():
            print(side, k, {kk: vv for kk, vv in v.items() if kk != "netlists"})
    return 1 if out["meta"]["pycache_after"] else 0


if __name__ == "__main__":
    sys.exit(main())
