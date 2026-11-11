"""Part 4: closed forms against naive loops written independently by the verifier."""
import math
import random
import sys
from types import SimpleNamespace as NS

from fastcalc import closed_forms as cf

rng = random.Random(int(sys.argv[1]) if len(sys.argv) > 1 else 90210)
N = int(sys.argv[2]) if len(sys.argv) > 2 else 200000


# ----- naive definitions (written from refcalc/base.py conventions, not copied from closed_forms) -----
def weights(T):
    Y = math.ceil(T)
    return [min(1.0, T - (y - 1)) for y in range(1, Y + 1)]     # index y-1


def events(T, L):
    out = []
    if L is None or L <= 0:
        return out
    n = 1
    while n * L < T:
        out.append(n * L)
        n += 1
    return out


def naive_skip(T, evs):
    w = weights(T)
    years = {math.ceil(t) for t in evs}
    return sum(w[y - 1] for y in years)


def naive_linear(T, base, slope):
    w = weights(T)
    return sum(w[k] * (base + slope * k) for k in range(len(w)))


def naive_grid_series(T, g):
    Y = math.ceil(T)
    out = []
    for k in range(Y):
        if g.kind == "CONSTANT":
            out.append(g.start)
        elif g.kind == "LINEAR_DECLINE_TO_FLOOR":
            out.append(max(g.floor, g.start - g.annual_decline * k))
        else:
            v = None
            for s in g.steps:
                if s.from_index <= k:
                    v = s.value
            out.append(v)
    return out


def naive_refrigerant(T, m0, rate, top_up, event_years):
    w = weights(T)
    per_year = {}
    for y in event_years:
        per_year[y] = per_year.get(y, 0) + 1
    m = m0
    leaked = 0.0
    before = []
    for y in range(1, len(w) + 1):
        leak = m * rate * w[y - 1]
        leaked += leak
        if not top_up:
            m -= leak
        for _ in range(per_year.get(y, 0)):
            before.append(m)
            m = m0
    return leaked, before, m


def rel(a, b):
    if a == b:
        return 0.0
    return abs(a - b) / max(abs(a), abs(b))


def pick_T():
    r = rng.random()
    if r < 0.3:
        return float(rng.randint(1, 300))
    if r < 0.5:
        k = rng.randint(1, 300)
        return max(0.01, k + rng.choice((-1, 1)) * rng.choice((2 ** -45, 1e-12, 1e-9, 1e-6, 0.5, 0.25)))
    if r < 0.6:
        return rng.choice((0.01, 0.1, 0.5, 0.99, 0.999999999, 1.0, 1.0000001))
    return rng.uniform(0.01, 300.0)


def pick_L(T):
    r = rng.random()
    if r < 0.25:
        k = rng.randint(1, 400)
        L = T / k
        return rng.choice((L, math.nextafter(L, 0), math.nextafter(L, 1e9), L * (1 + 1e-15), L * (1 - 1e-15)))
    if r < 0.4:
        return rng.choice((0.1, 0.2, 0.3, 0.7, 0.9, 1.1, 1.3, 0.01, 0.05, 1 / 3, 2 / 3, 1.0, 0.999999999999, 1.000000000001, 0.5, 2.5, 3.3, 7.1))
    if r < 0.5:
        return float(rng.randint(1, 120))
    if r < 0.55:
        return rng.choice((None, 0.0, -1.0, 1e9, T, math.nextafter(T, 0), math.nextafter(T, 1e9)))
    if r < 0.8:
        return rng.uniform(0.02, 3.0)
    return rng.uniform(0.02, 150.0)


fail = {}
worst = {}


def record(name, cond, info, err=None):
    if err is not None:
        worst[name] = max(worst.get(name, 0.0), err)
    if not cond:
        f = fail.setdefault(name, {"count": 0, "examples": []})
        f["count"] += 1
        if len(f["examples"]) < 3:
            f["examples"].append(info)


n_checks = 0
for it in range(N):
    T = pick_T()
    L = pick_L(T)
    if L is not None and L > 0 and T / L > 40000:
        L = T / 40000
    ev = events(T, L)
    # renewal_count
    n = cf.renewal_count(T, L)
    record("renewal_count", n == len(ev), (T, L, n, len(ev)))
    # skip_weight_periodic
    s1, s0 = cf.skip_weight_periodic(T, L, n), naive_skip(T, ev)
    e = abs(s1 - s0)
    record("skip_weight_periodic", e <= 1e-9 * max(1.0, s0), (T, L, s1, s0), e)
    # the quantity actually used downstream: T - skip (may cancel)
    y1, y0 = T - s1, T - s0
    record("years=T-skip_weight_periodic (rel 1e-9)", abs(y1 - y0) <= 1e-9 * abs(y0) or abs(y1 - y0) <= 1e-12 * T, (T, L, y1, y0))
    # skip_weight_events on explicit lists
    k = rng.randint(0, 12)
    evs = [rng.choice((rng.uniform(0, T), float(rng.randint(0, math.ceil(T))), T * rng.random(), math.ceil(T) - 1 + rng.random() * (T - math.ceil(T) + 1)))
           for _ in range(k)]
    evs = [t for t in evs if 0 < t < T]
    s1, s0 = cf.skip_weight_events(T, evs), naive_skip(T, evs)
    record("skip_weight_events", abs(s1 - s0) <= 1e-9 * max(1.0, s0), (T, evs, s1, s0), abs(s1 - s0))
    # linear_weighted_sum
    base = rng.choice((0.0, 1.0, rng.uniform(0, 1e7), rng.uniform(-1e3, 1e3)))
    slope = rng.choice((0.0, rng.uniform(-1e4, 1e4), base * rng.uniform(-0.003, 0.006), -base / max(1, math.ceil(T))))
    a, b = cf.linear_weighted_sum(T, base, slope), naive_linear(T, base, slope)
    scale = sum(abs(base + slope * kk) for kk in range(math.ceil(T))) or 1.0
    record("linear_weighted_sum", abs(a - b) <= 1e-9 * scale, (T, base, slope, a, b), abs(a - b) / scale)
    # grid_cumulative
    kind = rng.choice(("CONSTANT", "LINEAR", "LINEAR", "LINEAR_ODD", "STEP", "STEP", "STEP_UNSORTED", "STEP_GAP"))
    Y = math.ceil(T)
    w = weights(T)
    if kind == "CONSTANT":
        g = NS(kind="CONSTANT", start=rng.uniform(0, 1), annual_decline=None, floor=None, steps=None)
    elif kind == "LINEAR":
        start = rng.uniform(0.1, 1.0)
        floor = start * rng.choice((0.0, 0.05, 0.5, 1.0, rng.random()))
        v = rng.random()
        if v < 0.3:
            d = (start - floor) / rng.randint(1, Y + 2)              # floor reached exactly at an integer index
        elif v < 0.4:
            d = 0.0
        elif v < 0.5:
            d = (start - floor) / (Y - 1 + rng.random()) if Y > 1 else 0.3
        else:
            d = (start - floor) / rng.uniform(0.2, 400.0)
        g = NS(kind="LINEAR_DECLINE_TO_FLOOR", start=start, annual_decline=d, floor=floor, steps=None)
    elif kind == "LINEAR_ODD":
        start = rng.uniform(0.1, 1.0)
        g = NS(kind="LINEAR_DECLINE_TO_FLOOR", start=start, annual_decline=rng.choice((-0.01, 0.0, 0.01, -1e-6)),
               floor=start + rng.choice((0.2, -0.2, 0.0, 1e-9)), steps=None)
    else:
        idx = sorted({0} | {rng.randint(0, Y + 5) for _ in range(rng.randint(0, 8))})
        steps = [NS(from_index=i, value=rng.uniform(0.01, 1.0)) for i in idx]
        if kind == "STEP_UNSORTED":
            rng.shuffle(steps)
        if kind == "STEP_GAP":
            steps = [NS(from_index=s.from_index + rng.randint(1, 3), value=s.value) for s in steps]
        if rng.random() < 0.2:
            steps.insert(rng.randrange(len(steps) + 1), NS(from_index=rng.choice(idx), value=rng.uniform(0.01, 1.0)))   # duplicate index
            if kind == "STEP":
                steps.sort(key=lambda s: s.from_index)
        g = NS(kind="STEPWISE", start=None, annual_decline=None, floor=None, steps=steps)
    series = naive_grid_series(T, g)
    name = "grid_cumulative:" + kind
    try:
        a = cf.grid_cumulative(T, g)
    except Exception as exc:
        a = exc
    if any(v is None for v in series):
        record(name + " (loop undefined: a year has no step)", isinstance(a, Exception), (T, [(s.from_index, round(s.value, 3)) for s in g.steps], a))
    else:
        b = sum(w[kk] * series[kk] for kk in range(Y))
        ok = not isinstance(a, Exception) and abs(a - b) <= 1e-9 * max(abs(b), 1e-300)
        info = (T, vars(g) if g.steps is None else [(s.from_index, round(s.value, 4)) for s in g.steps], a, b)
        record(name, ok, info, None if isinstance(a, Exception) else rel(a, b))
    # refrigerant_device
    m0 = rng.choice((1.0, rng.uniform(0.1, 500.0)))
    rate = rng.choice((0.0, 1.0, 0.02, 0.1, 0.5, 0.999, 1e-3, 1e-5, 1e-7, 1e-9, 1e-12, rng.random(), rng.uniform(0, 0.2)))
    top = rng.random() < 0.3
    v = rng.random()
    if v < 0.4:
        Ld = pick_L(T)
        if Ld is not None and Ld > 0 and T / Ld > 5000:
            Ld = T / 5000
        yrs = [math.ceil(t) for t in events(T, Ld)]
    else:
        raw = [rng.choice((rng.uniform(0, T), float(rng.randint(0, Y)), Y - 1 + rng.random())) for _ in range(rng.randint(0, 8))]
        yrs = [math.ceil(t) for t in sorted(t for t in raw if 0 < t < T)]
    a = cf.refrigerant_device(T, m0, rate, top, yrs)
    b = naive_refrigerant(T, m0, rate, top, yrs)
    bucket = "rate>=1e-3" if rate >= 1e-3 or rate == 0.0 else ("rate=%.0e" % rate if rate in (1e-5, 1e-7, 1e-9, 1e-12) else "rate<1e-3 other")
    e_leak = rel(a[0], b[0])
    record(f"refrigerant_device.leaked [{bucket}]", e_leak <= 1e-9, (T, m0, rate, top, yrs[:6], a[0], b[0]), e_leak)
    e_end = rel(a[2], b[2]) if max(abs(a[2]), abs(b[2])) > 1e-300 else 0.0
    record("refrigerant_device.end", e_end <= 1e-9 or abs(a[2] - b[2]) <= 1e-12 * m0, (T, m0, rate, top, yrs[:6], a[2], b[2]), e_end)
    okb = len(a[1]) == len(b[1]) and all(rel(x, y) <= 1e-9 or abs(x - y) <= 1e-12 * m0 for x, y in zip(a[1], b[1]))
    record("refrigerant_device.before", okb, (T, m0, rate, top, yrs[:6], a[1][:4], b[1][:4]))
    n_checks += 1

print("iterations:", n_checks)
print("worst observed error per form:")
for k, v in sorted(worst.items()):
    print(f"   {k}: {v:.3e}")
print("FAILURES:")
for k, v in sorted(fail.items()):
    print(f"   {k}: {v['count']}")
    for ex in v["examples"]:
        print("       ", str(ex)[:400])
