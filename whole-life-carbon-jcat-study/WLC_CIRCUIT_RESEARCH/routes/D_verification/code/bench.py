"""D checklist 7 / gate 4: benchmark on a COMMON point set (contract 11 points + 1e5
uniform random rationals k/1e6 in [0,60], seed 20261124), P0, right convention.

(a) closed form Sigma/floor          (Fraction and float)
(b) knot cumulative sum + bisect     (Fraction and float)
(c) event-driven hybrid circuit      (D's own clock-integrator implementation, Fraction;
                                      per-query from t=0 and one sorted sweep)
(d) fixed-step integration           (float; clocks and accumulator stepped with dt,
                                      events detected at step ends; dt=1e-2,1e-3,1e-4; sorted sweep)

Op counts come from instrumented copies run once (+,-,*,/,//,compare, min each = 1 op);
timings are medians of 5 perf_counter runs of the UNinstrumented code; memory is the
tracemalloc peak of one run. stdlib only.

Run: PYTHONDONTWRITEBYTECODE=1 python3 -B code/bench.py
"""
import bisect, json, math, os, platform, random, statistics, sys, time, tracemalloc
from fractions import Fraction as F
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import oracle_d as O  # noqa: E402

OUT = os.path.join(HERE, "..", "results")
SEED, N = 20261124, 100000
KNOTS = [F(10 * k) for k in range(1, 7)]
CUM, _c = [], F(0)
for k in KNOTS:
    _c += 20 + (35 if k % 20 == 0 else 0)
    CUM.append(_c)
KNOTS_F = [float(k) for k in KNOTS]
CUM_F = [float(c) for c in CUM]


def points():
    rng = random.Random(SEED)
    pts = [F(t) for t in O.CONTRACT_POINTS] + [F(rng.randrange(0, 60 * 10**6 + 1), 10**6) for _ in range(N)]
    return pts


# ---------------- (a) closed form
def a_frac(t):
    return 100 + 4 * t + 20 * (t // 10) + 35 * (t // 20)


def a_float(t):
    return 100.0 + 4.0 * t + 20.0 * math.floor(t / 10.0) + 35.0 * math.floor(t / 20.0)


# ---------------- (b) knots + bisect
def b_frac(t):
    k = bisect.bisect_right(KNOTS, t)
    return 100 + 4 * t + (CUM[k - 1] if k else 0)


def b_float(t):
    k = bisect.bisect_right(KNOTS_F, t)
    return 100.0 + 4.0 * t + (CUM_F[k - 1] if k else 0.0)


# ---------------- (c) D's own event-driven hybrid circuit (clock integrators)
def c_query(t):
    now, Q, xa, xp = F(0), F(100), F(0), F(0)
    while True:
        da, dp = 10 - xa, 20 - xp           # time to thresholds (clocks in years)
        dt = da if da < dp else dp
        if now + dt <= t:
            Q += 4 * dt; xa += dt; xp += dt; now += dt
            if xa == 10:
                Q += 20; xa = F(0)
            if xp == 20:
                Q += 35; xp = F(0)
        else:
            return Q + 4 * (t - now)


def c_sweep(ts):
    order = sorted(range(len(ts)), key=ts.__getitem__)
    out = [None] * len(ts)
    now, Q, xa, xp = F(0), F(100), F(0), F(0)
    for i in order:
        t = ts[i]
        while True:
            da, dp = 10 - xa, 20 - xp
            dt = da if da < dp else dp
            if now + dt <= t:
                Q += 4 * dt; xa += dt; xp += dt; now += dt
                if xa == 10:
                    Q += 20; xa = F(0)
                if xp == 20:
                    Q += 35; xp = F(0)
            else:
                break
        Q += 4 * (t - now); xa += t - now; xp += t - now; now = t
        out[i] = Q
    return out


# ---------------- (d) fixed-step integration (float, sorted sweep)
def d_sweep(tf, dt):
    order = sorted(range(len(tf)), key=tf.__getitem__)
    out = [None] * len(tf)
    s, Q, xa, xp = 0.0, 100.0, 0.0, 0.0
    for i in order:
        t = tf[i]
        while s + dt <= t:
            s += dt; Q += 4.0 * dt; xa += dt; xp += dt
            if xa >= 10.0:
                Q += 20.0; xa -= 10.0
            if xp >= 20.0:
                Q += 35.0; xp -= 20.0
        out[i] = Q + 4.0 * (t - s)            # linear interpolation inside the last step
    return out


# ---------------- instrumented op counts (one pass, averaged)
def ops_counts(pts):
    n = len(pts)
    oc = {}
    oc["a_closed_form"] = 9          # 2 //, 3 *, 3 +, (t/10, t/20 inside //) -> 2 div+floor, 3 mul, 3 add, ~1 cmp-free

    oc["b_knots_bisect"] = math.ceil(math.log2(len(KNOTS) + 1)) + 4   # 3 cmp (bisect over 6 knots) + 1 mul + 2 add + 1 index
    # (c): count per query segments: each segment = 2 sub + 1 cmp(min) + 1 add + 1 cmp + 4 (3 add, 1 mul) + 2 cmp
    seg_ops, tot = 11, 0
    segs_total = 0
    for t in pts:
        now, xa, xp = F(0), F(0), F(0)
        segs = 1
        while True:
            da, dp = 10 - xa, 20 - xp
            dt = min(da, dp)
            if now + dt <= t:
                xa += dt; xp += dt; now += dt; segs += 1
                if xa == 10: xa = F(0)
                if xp == 20: xp = F(0)
            else:
                break
        segs_total += segs
        tot += segs * seg_ops + 3
    oc["c_hybrid_per_query"] = round(tot / n, 2)
    oc["c_hybrid_mean_segments_per_query"] = round(segs_total / n, 3)
    oc["c_hybrid_sorted_sweep(total ops / n)"] = round((6 * seg_ops + 6 * n) / n + math.log2(n), 2)  # + sort ~ log2 n cmp
    for dt in (1e-2, 1e-3, 1e-4):
        steps = int(60 / dt)
        oc[f"d_fixed_step_dt={dt}_sweep(total ops / n)"] = round((steps * 9 + 5 * n) / n + math.log2(n), 2)
        oc[f"d_fixed_step_dt={dt}_per_query(ops, t=60)"] = steps * 9
    return oc


def timeit(fn, reps=5):
    ts = []
    for _ in range(reps):
        t0 = time.perf_counter(); fn(); ts.append(time.perf_counter() - t0)
    tracemalloc.start(); fn(); peak = tracemalloc.get_traced_memory()[1]; tracemalloc.stop()
    return {"median_s": statistics.median(ts), "min_s": min(ts), "reps": reps, "tracemalloc_peak_bytes": peak}


def main(reps=5):
    pts = points()
    tf = [float(t) for t in pts]
    exact = [O.G("P0", t) for t in pts]            # independent oracle (ledger sweep)
    exactf = [float(v) for v in exact]
    # correctness first
    corr = {
        "a_frac==oracle": all(a_frac(t) == e for t, e in zip(pts, exact)),
        "b_frac==oracle": all(b_frac(t) == e for t, e in zip(pts, exact)),
        "c_query==oracle": all(c_query(t) == e for t, e in zip(pts, exact)),
        "c_sweep==oracle": c_sweep(pts) == exact,
        "a_float_max_abs_err": max(abs(a_float(t) - e) for t, e in zip(tf, exactf)),
        "b_float_max_abs_err": max(abs(b_float(t) - e) for t, e in zip(tf, exactf)),
    }
    fixed = {}
    for dt in (1e-2, 1e-3, 1e-4):
        out = d_sweep(tf, dt)
        errs = [abs(o - e) for o, e in zip(out, exactf)]
        cp = {ts: {"value": out[i], "exact": exactf[i], "err": errs[i]} for i, ts in enumerate(O.CONTRACT_POINTS)}
        big = sum(1 for e in errs if e > 1.0)
        fixed[str(dt)] = {"max_abs_err_all": max(errs), "n_points_err_gt_1kg": big,
                          "max_abs_err_excluding_err_gt_1kg": max(e for e in errs if e <= 1.0),
                          "contract_points": cp,
                          "boundary_note": "an event is detected at the first step end with clock>=period: late by <dt "
                                           "(or one step early/late from float accumulation); queries inside that lag "
                                           "are off by the full event charge (20 or 55 kg)"}
    timings = {
        "a_closed_form_Fraction": timeit(lambda: [a_frac(t) for t in pts], reps),
        "a_closed_form_float": timeit(lambda: [a_float(t) for t in tf], reps),
        "b_knots_bisect_Fraction": timeit(lambda: [b_frac(t) for t in pts], reps),
        "b_knots_bisect_float": timeit(lambda: [b_float(t) for t in tf], reps),
        "c_hybrid_per_query_Fraction": timeit(lambda: [c_query(t) for t in pts], reps),
        "c_hybrid_sorted_sweep_Fraction": timeit(lambda: c_sweep(pts), reps),
        "oracle_d_ledger_sweep_Fraction(reference, not a contender)": timeit(lambda: [O.G("P0", t) for t in pts[:10000]], 3),
    }
    for dt in (1e-2, 1e-3, 1e-4):
        timings[f"d_fixed_step_float_dt={dt}_sorted_sweep"] = timeit(lambda dt=dt: d_sweep(tf, dt), reps)
    for k, v in timings.items():
        n = 10000 if k.startswith("oracle_d") else len(pts)
        v["per_point_us"] = v["median_s"] / n * 1e6
    states = {"a_closed_form": [0, 0, 0, 0], "b_knots_bisect_H60": [0, 0, 0, 6],
              "c_hybrid": [3, 0, 2, 0], "d_fixed_step": [3, 0, 2, 0],
              "note": "(continuous, discrete/counters, comparator thresholds, external table entries); simulator time "
                      "not counted; closed form keeps no state but needs floor; knots table grows with horizon H"}
    res = {"env": {"python": sys.version.split()[0], "implementation": platform.python_implementation(),
                   "machine": platform.machine(), "platform": platform.platform(), "seed": SEED,
                   "n_points": len(pts), "point_set": "11 contract points + 1e5 uniform k/1e6 in [0,60]"},
           "correctness": corr, "fixed_step_errors": fixed, "op_counts_per_query": ops_counts(pts),
           "timings": timings, "states": states}
    best_circuit = min(timings["c_hybrid_per_query_Fraction"]["median_s"], timings["c_hybrid_sorted_sweep_Fraction"]["median_s"])
    res["verdict"] = {
        "closed_form_Fraction_vs_best_hybrid_speed_ratio": best_circuit / timings["a_closed_form_Fraction"]["median_s"],
        "knots_Fraction_vs_closed_form_Fraction": timings["b_knots_bisect_Fraction"]["median_s"] / timings["a_closed_form_Fraction"]["median_s"],
        "circuit_speed_gain": best_circuit < min(timings["a_closed_form_Fraction"]["median_s"], timings["b_knots_bisect_Fraction"]["median_s"]),
    }
    os.makedirs(OUT, exist_ok=True)
    json.dump(res, open(os.path.join(OUT, "benchmark.json"), "w"), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 5)
