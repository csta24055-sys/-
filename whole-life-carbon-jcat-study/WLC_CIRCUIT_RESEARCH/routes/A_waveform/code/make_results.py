"""Regenerate results/points.json and results/benchmark.json (stdlib only, no network).
  PYTHONDONTWRITEBYTECODE=1 python3 -B code/make_results.py
"""
import json, os, platform, random, statistics, sys, time, tracemalloc
from fractions import Fraction as F
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import p0_oracle as O
import circuit_a as C

OUT = os.path.join(HERE, "..", "results")
D = F(1, 10**12)


def dec(x):
    """exact decimal string if terminating, else 'num/den'"""
    x = F(x); d = x.denominator; a = b = 0
    while d % 2 == 0: d //= 2; a += 1
    while d % 5 == 0: d //= 5; b += 1
    if d != 1:
        return f"{x.numerator}/{x.denominator}"
    k = max(a, b); n = x * 10**k
    s = str(abs(n.numerator)).rjust(k + 1, "0")
    out = (s[:-k] + "." + s[-k:]).rstrip("0").rstrip(".") if k else s
    return ("-" if x < 0 else "") + out


def frac(v):
    v = F(v); return f"{v.numerator}/{v.denominator}"


def points():
    rows = []
    ts = [F(t) for t in O.CONTRACT_POINTS + O.KNIFE_POINTS + [O.KNIFE_EDGE_UNDEFINED]]
    ts += [F(t) + d for t in (10, 20, 30, 40, 60) for d in (-D, D)]
    ts.append(F(10) / (1 - O.EPS))
    for conv in O.CONVENTIONS:
        reals = [("oracle", lambda t, c=conv: O.g_p0(t, c), (0, 0, 0, 0)),
                 ("R1", C.p0_r1(conv).G, C.p0_r1(conv).states()),
                 ("R2", C.p0_r2(conv).G, C.p0_r2(conv).states()),
                 ("R3", C.R3(conv).G, C.R3(conv).states())]
        if conv != O.ORIG:
            reals.append(("R3k", C.R3k(conv).G, C.R3k(conv).states()))
        r3i = C.R3i([(F(1, 2), 20), (1, 55)], conv=conv)
        reals.append(("R3i", r3i.G, r3i.states()))
        for name, g, st in reals:
            for t in ts:
                rows.append({"case": "P0", "convention": conv, "t": dec(t), "value": frac(g(t)),
                             "realization": name, "states": list(st)})
    for t in [F(x) for x in O.CONTRACT_POINTS + O.KNIFE_POINTS + ["20.00000001"]] + [F(20) / (1 - O.EPS)]:
        for pol in ("substitute", "additional"):
            c = C.p1_r1(pol, O.ORIG)
            rows.append({"case": f"P1-{pol}", "convention": O.ORIG, "t": dec(t), "value": frac(c.G(t)),
                         "realization": "R1", "states": list(c.states()), "oracle": frac(O.g_p1(t, O.ORIG, pol))})
    for conv in (O.RIGHT, O.LEFT):
        for t in [F(x) for x in O.CONTRACT_POINTS] + [F(x) for x in ("7", "17", "27")]:
            for pol in ("substitute", "additional"):
                c = C.p1_r1(pol, conv)
                rows.append({"case": f"P1-{pol}", "convention": conv, "t": dec(t), "value": frac(c.G(t)),
                             "realization": "R1", "states": list(c.states()), "oracle": frac(O.g_p1(t, conv, pol))})
            c = C.p2_r1(conv)
            rows.append({"case": "P2", "convention": conv, "t": dec(t), "value": frac(c.G(t)),
                         "realization": "R1", "states": list(c.states()), "oracle": frac(O.g_p2(t, conv))})
            c = C.px_r1(conv)
            rows.append({"case": "Px", "convention": conv, "t": dec(t), "value": frac(c.G(t)),
                         "realization": "R1", "states": list(c.states()), "oracle": frac(O.g_px(t, conv))})
            c3 = C.R3i([(F(7, 20), 20), (F(17, 20), 20), (1, 35)], conv=conv)
            rows.append({"case": "Px", "convention": conv, "t": dec(t), "value": frac(c3.G(t)),
                         "realization": "R3i-single-clock", "states": list(c3.states()),
                         "oracle": frac(O.g_px(t, conv))})
    mism = []
    oracle_p0 = {(r["convention"], r["t"]): r["value"] for r in rows if r["case"] == "P0" and r["realization"] == "oracle"}
    for r in rows:
        ref = r.get("oracle") or oracle_p0.get((r["convention"], r["t"]))
        if ref != r["value"]:
            mism.append(r)
    flt = {conv: O.g_p0_float(float(O.KNIFE_EDGE_UNDEFINED), conv) for conv in O.CONVENTIONS}
    return rows, mism, flt


def bench(n=2000, reps=5, seed=20261124):
    rng = random.Random(seed)
    pts = [F(rng.randrange(0, 60 * 10**6), 10**6) for _ in range(n)]
    fpts = [float(p) for p in pts]
    cands = {
        "closed_form_Fraction": lambda: [O.g_p0(t) for t in pts],
        "closed_form_float": lambda: [O.g_p0_float(t) for t in fpts],
        "R1_event_driven_Fraction": (lambda c=C.p0_r1(): [c.G(t) for t in pts]),
        "R2_impulse_free_Fraction": (lambda c=C.p0_r2(): [c.G(t) for t in pts]),
        "R3_single_clock_Fraction": (lambda c=C.R3(): [c.G(t) for t in pts]),
    }
    res = {}
    for name, fn in cands.items():
        times = []
        for _ in range(reps):
            t0 = time.perf_counter(); fn(); times.append(time.perf_counter() - t0)
        tracemalloc.start(); fn(); peak = tracemalloc.get_traced_memory()[1]; tracemalloc.stop()
        res[name] = {"median_s": statistics.median(times), "min_s": min(times), "reps": reps,
                     "per_point_us": statistics.median(times) / n * 1e6, "tracemalloc_peak_bytes": peak}
    c = C.p0_r1()
    segs = [c.run(t)["ops"]["segments"] for t in pts]
    res["R1_ops"] = {"mean_segments_per_point": sum(segs) / n, "max_segments": max(segs)}
    agree = all(C.p0_r1().G(t) == O.g_p0(t) for t in pts[:500])
    return {"n_points": n, "seed": seed, "python": platform.python_version(),
            "machine": platform.machine(), "platform": platform.platform(), "results": res,
            "R1_equals_oracle_first500": agree}


if __name__ == "__main__":
    rows, mism, flt = points()
    with open(os.path.join(OUT, "points.json"), "w") as f:
        json.dump({"source_commit": "e4121d6 (D pass 1 fixes)", "units": "kgCO2e (illustrative), t in years",
                   "rows": rows, "n_rows": len(rows), "n_mismatch_vs_oracle": len(mism),
                   "float_at_knife_edge_10.00000001": flt,
                   "exact_at_knife_edge_10.00000001": {c: frac(O.g_p0(F(O.KNIFE_EDGE_UNDEFINED), c)) for c in O.CONVENTIONS}},
                  f, indent=1)
    print("points rows", len(rows), "mismatches", len(mism))
    print("knife-edge 10.00000001 float:", flt)
    b = bench()
    with open(os.path.join(OUT, "benchmark.json"), "w") as f:
        json.dump(b, f, indent=1)
    print(json.dumps(b, indent=1))
