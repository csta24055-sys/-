"""Brute-force check of closed_forms.py (D2, D3, D5, D6) against literal loops written from refcalc/base.py conventions."""
import math, random, itertools
from fastcalc import closed_forms as cf
from refcalc import base
from types import SimpleNamespace as NS

rnd = random.Random(20261111)
def rel(a, b):
    return 0.0 if a == b else abs(a - b) / max(abs(a), abs(b), 1e-300)

# ---------- D2 renewal_count, D3 skip weight ----------
Ts = [0.3, 0.999999999, 1.0, 1.0000000001, 1.5, 2.0, 7.0, 10.0, 30.0, 42.5, 59.999999, 59.9999999999, 60.0, 60.00000001, 62.5, 99.9, 100.0, 120.0]
cs = [0.01, 0.1, 0.25, 0.3, 1/3, 0.5, 0.75, 0.9, 0.999999999, 0.9999999995, 1.0, 1.0000000005, 1.000000001, 1.0000001, 1.1, 1.25, 1.5, 2.0, 2.5,
      3.0, 3.3, 3.5, 7.0, 10.0, 12.5, 15.0, 20.0, 29.999999999, 30.0, 33.3, 59.99999999, 60.0, 61.0, 1e9]
worst_n = 0; worst_skip = 0.0; bad = []
def check(T, c):
    global worst_n, worst_skip
    ev = base.periodic_events(T, c)
    n = cf.renewal_count(T, c)
    if n != len(ev): bad.append(("count", T, c, n, len(ev)))
    w = base.year_weights(T)
    S = {base.event_year(t) for t in ev}
    brute = sum(w[y] for y in S)
    got = cf.skip_weight_periodic(T, c, n)
    d = abs(brute - got)
    if d > 1e-9 * max(1.0, T): bad.append(("skip", T, c, got, brute))
    worst_skip = max(worst_skip, d)
    # T - skip against literal 'years' accumulation
    years = sum(w[y] for y in range(1, len(w)) if y not in S)
    if abs(years - (T - got)) > 1e-9 * max(1.0, T): bad.append(("years", T, c, T - got, years))
k = 0
for T in Ts:
    for c in cs:
        check(T, c); k += 1
for _ in range(200000):
    T = rnd.choice([rnd.uniform(0.05, 130.0), float(rnd.randint(1, 120)), rnd.randint(1, 240) / 2.0, rnd.randint(1, 1200) / 10.0])
    c = rnd.choice([rnd.uniform(0.02, 70.0), float(rnd.randint(1, 60)), rnd.randint(1, 240) / 4.0, rnd.randint(1, 600) / 10.0, T / rnd.randint(1, 12),
                    T / rnd.randint(1, 12) * (1 + rnd.choice([-1, 1]) * 10 ** rnd.uniform(-12, -8))])
    check(T, c); k += 1
print(f"D2/D3 periodic: {k} (T,c) pairs, mismatches {len(bad)}, worst |skip weight diff| {worst_skip:.2e}")
for b in bad[:10]: print("   ", b)

# explicit lists
bad2 = []; k2 = 0
for _ in range(50000):
    T = rnd.choice([rnd.uniform(0.3, 100.0), float(rnd.randint(1, 100)), rnd.randint(1, 200) / 2.0])
    years = [rnd.choice([rnd.uniform(-2, T + 5), float(rnd.randint(0, int(T) + 2)), T, T * (1 - 1e-10), 0, 0.5]) for _ in range(rnd.randint(0, 8))]
    ev = base.explicit_events(T, years)
    w = base.year_weights(T)
    S = {base.event_year(t) for t in ev}
    brute = sum(w[y] for y in S)
    got = cf.skip_weight_events(T, [float(t) for t in years if t > 0 and cf.inside(t, T)])
    k2 += 1
    if abs(brute - got) > 1e-9 * max(1.0, T): bad2.append((T, years, got, brute))
print(f"D3 explicit lists: {k2} cases, mismatches {len(bad2)}")
for b in bad2[:5]: print("   ", b)

# ---------- D5 linear weighted sum ----------
bad3 = []; worst3 = 0.0; k3 = 0
for _ in range(100000):
    T = rnd.choice([rnd.uniform(0.05, 130.0), float(rnd.randint(1, 120)), rnd.randint(1, 240) / 2.0])
    b = rnd.uniform(0, 1e6); s = rnd.choice([0.0, rnd.uniform(-1e4, 1e4)])
    w = base.year_weights(T); Y = len(w) - 1
    brute = sum(w[k + 1] * (b + s * k) for k in range(Y))
    got = cf.linear_weighted_sum(T, b, s)
    e = abs(brute - got) / max(abs(brute), 1.0); worst3 = max(worst3, e); k3 += 1
    if e > 1e-9: bad3.append((T, b, s, got, brute))
print(f"D5 linear_weighted_sum: {k3} cases, mismatches {len(bad3)}, worst rel diff {worst3:.2e}")

# ---------- D5 grid segments + moments ----------
def mk_grid(kind):
    if kind == "CONSTANT":
        return NS(kind=kind, start=rnd.choice([None, rnd.uniform(0, 1)]), floor=None, annual_decline=None, steps=None)
    if kind == "LINEAR_DECLINE_TO_FLOOR":
        start = rnd.uniform(0.0, 1.0)
        floor = rnd.choice([0.0, start, rnd.uniform(0, start), rnd.uniform(0, 1.2)])
        d = rnd.choice([0.0, rnd.uniform(0, 0.05), rnd.uniform(0, 2.0), -0.01, (start - floor) / rnd.randint(1, 80) if start > floor else 0.01, 1e-12, 0.01, 0.005])
        return NS(kind=kind, start=start, floor=floor, annual_decline=d, steps=None)
    if kind == "STEPWISE":
        n = rnd.randint(0, 6)
        idx = sorted(rnd.sample(range(0, 140), n)) if n else []
        if idx and rnd.random() < 0.7: idx[0] = 0
        if idx and rnd.random() < 0.1: rnd.shuffle(idx)
        if len(idx) > 1 and rnd.random() < 0.1: idx[1] = idx[0]
        return NS(kind=kind, start=None, floor=None, annual_decline=None, steps=[NS(from_index=i, value=rnd.uniform(0, 1)) for i in idx])
    return NS(kind="TABLE", start=None, floor=None, annual_decline=None, steps=None)
bad4 = []; worst4 = 0.0; k4 = 0; wf = 0; mism_wf = 0
for _ in range(120000):
    T = rnd.choice([rnd.uniform(0.05, 130.0), float(rnd.randint(1, 120)), rnd.randint(1, 240) / 2.0])
    Y = math.ceil(T)
    g = mk_grid(rnd.choice(["CONSTANT", "LINEAR_DECLINE_TO_FLOOR", "STEPWISE", "TABLE"]))
    g.table = [rnd.uniform(0, 1) for _ in range(Y)]
    seg = cf.grid_segments(g, Y)
    well = base.grid_well_formed(g)
    if (seg is not None) != well:
        mism_wf += 1; bad4.append(("wellformed", g.kind, vars(g))); continue
    vals = base.grid_values(g, Y)
    w = base.year_weights(T)
    Gb = sum(w[k + 1] * vals[k] for k in range(Y)); Hb = sum(w[k + 1] * k * vals[k] for k in range(Y))
    G, H = cf.segment_moments(seg, T) if seg is not None else cf.table_moments(g.table, T)
    if seg is not None:
        wf += 1
        exp = []
        for a, b, al, be in seg: exp.extend(al + be * k for k in range(a, b))
        if len(exp) != Y or any(abs(x - y) > 1e-12 * max(abs(x), abs(y), 1e-300) for x, y in zip(exp, vals)):
            bad4.append(("series", T, g.kind, g.start, g.floor, g.annual_decline))
    e = max(abs(G - Gb) / max(abs(Gb), 1e-3), abs(H - Hb) / max(abs(Hb), 1e-3)); worst4 = max(worst4, e); k4 += 1
    if e > 1e-9: bad4.append(("moments", T, g.kind, G, Gb, H, Hb, getattr(g, "start", None), g.floor, g.annual_decline))
print(f"D5 grid: {k4} cases ({wf} well-formed descriptors), mismatches {len(bad4)}, worst rel diff of G/H {worst4:.2e}")
for b in bad4[:8]: print("   ", b)

# ---------- D5 two-point guard: is the clamp really inactive in every year when both end points are >= 0 ? ----------
bad5 = []; worst5 = 0.0; k5 = 0; guard_pass = 0; tiny_neg = 0
for _ in range(200000):
    T = rnd.choice([rnd.uniform(0.05, 130.0), float(rnd.randint(1, 120)), rnd.randint(1, 240) / 2.0])
    Y = math.ceil(T); w = base.year_weights(T)
    def prof():
        b = rnd.choice([0.0, rnd.uniform(0, 1e6), rnd.uniform(0, 10)])
        s = rnd.choice([0.0, rnd.uniform(-1e4, 1e4), -b / max(Y - 1, 1), -b / max(Y - 1, 1) * (1 + 1e-15), b * 0.1])
        return b, s
    (cb, cs_), (gb, gs), (xb, xs) = prof(), prof(), prof()
    if rnd.random() < 0.2: gb, gs = cb, cs_          # generation equals consumption exactly
    if rnd.random() < 0.1: xb, xs = 0.0, 0.0
    cg = rnd.choice([1.0, 1000.0, 0.001, 3.6]); cx = rnd.choice([1.0, 1000.0, 0.001])
    B = cb - (gb * cg - xb * cx); S = cs_ - (gs * cg - xs * cx)
    if not (B >= 0.0 and B + S * (Y - 1) >= 0.0): continue
    guard_pass += 1
    gvals = [rnd.uniform(0.0, 1.0) for _ in range(Y)]
    raw = [(cb + cs_ * k) - ((gb + gs * k) * cg - (xb + xs * k) * cx) for k in range(Y)]
    if min(raw) < 0.0: tiny_neg += 1
    brute = sum(w[k + 1] * max(0.0, raw[k]) * gvals[k] for k in range(Y))
    G, H = cf.table_moments(gvals, T)
    got = B * G + S * H
    scale = sum(w[k + 1] * (abs(cb + cs_ * k) + abs((gb + gs * k) * cg) + abs((xb + xs * k) * cx)) * gvals[k] for k in range(Y))
    e_rel = abs(got - brute) / max(abs(brute), 1e-300) if brute != got else 0.0
    e_scaled = abs(got - brute) / max(scale, 1e-300)
    k5 += 1
    if e_scaled > 1e-9: bad5.append((T, cb, cs_, gb, gs, xb, xs, cg, cx, got, brute))
    worst5 = max(worst5, e_scaled)
print(f"D5 two-point guard: {guard_pass} cases pass the guard; in {tiny_neg} of them some year is (rounding) negative; "
      f"mismatches beyond 1e-9 of the gross terms: {len(bad5)}; worst diff relative to gross terms {worst5:.2e}")
for b in bad5[:5]: print("   ", b)

# ---------- D6 refrigerant charge cycles ----------
def brute_ref(T, rate, top_up, ev_years):
    w = base.year_weights(T); Y = len(w) - 1
    cnt = {}
    for y in ev_years: cnt[y] = cnt.get(y, 0) + 1
    m = 1.0; leaked = 0.0; before = []
    for y in range(1, Y + 1):
        leak = m * rate * w[y]; leaked += leak
        if not top_up: m -= leak
        for _ in range(cnt.get(y, 0)):
            before.append(m); m = 1.0
    return leaked, before, m
bad6 = []; worst6 = 0.0; k6 = 0
for _ in range(150000):
    T = rnd.choice([rnd.uniform(0.05, 130.0), float(rnd.randint(1, 120)), rnd.randint(1, 240) / 2.0, 0.5, 1.5, 59.999999])
    rate = rnd.choice([0.0, 1.0, rnd.uniform(0, 1), rnd.uniform(0, 0.1), 1e-12, 1e-17, 0.999999, 0.5])
    top = rnd.random() < 0.3
    if rnd.random() < 0.5:
        life = rnd.choice([rnd.uniform(0.1, 70), 0.25, 0.5, 1.0, 1.5, 10.0, 15.0, T, T / 2, T / 3])
        ev = [base.event_year(t) for t in base.periodic_events(T, life)]
        ev2 = [cf.event_year(k * life) for k in range(1, cf.renewal_count(T, life) + 1)]
    else:
        years = [rnd.choice([rnd.uniform(-1, T + 2), float(rnd.randint(0, int(T) + 1)), T - 1e-7, math.ceil(T) - 0.5]) for _ in range(rnd.randint(0, 7))]
        ev = [base.event_year(t) for t in sorted(base.explicit_events(T, years))]
        ev2 = [cf.event_year(t) for t in sorted(float(t) for t in years if t > 0 and cf.inside(t, T))]
    assert ev == ev2
    lb, bb, mb = brute_ref(T, rate, top, ev)
    lg, bg, mg = cf.refrigerant_fractions(T, rate, top, ev2)
    k6 += 1
    errs = [abs(lb - lg) / max(abs(lb), 1e-300) if lb != lg else 0.0, abs(mb - mg)]
    if len(bb) != len(bg): bad6.append(("len", T, rate, top, ev)); continue
    errs += [abs(x - y) for x, y in zip(bb, bg)]
    e = max(errs); worst6 = max(worst6, e)
    if e > 1e-9: bad6.append((T, rate, top, ev, (lb, lg), (mb, mg), bb[:3], bg[:3]))
print(f"D6 refrigerant_fractions: {k6} cases, mismatches {len(bad6)}, worst diff {worst6:.2e}")
for b in bad6[:8]: print("   ", b)
