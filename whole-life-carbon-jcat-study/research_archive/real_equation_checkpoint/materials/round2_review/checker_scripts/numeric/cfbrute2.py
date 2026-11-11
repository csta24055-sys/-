import math, random, sys
sys.dont_write_bytecode = True
from cfbrute import loop_count, loop_skip, weights, ey, inside, EPS
from fastcalc import closed_forms as cf
# 1. window around 1.000000001 in ulps
p0 = 1.000000001
hits = []
for T in (7.0, 30.0, 60.0, 62.5, 100.0, 129.5):
    x = p0
    for k in range(0, 4001):
        for sgn in (1, -1):
            p = p0 + sgn * k * math.ulp(1.0)
            nl = loop_count(T, p)
            s_ref, _, d = loop_skip(T, p)
            s_eng = cf.skip_weight_periodic(T, p, nl)
            if abs(s_ref - s_eng) > 1e-9:
                hits.append((T, sgn * k, p, nl, d, s_ref, s_eng))
ks = sorted({h[1] for h in hits})
print("ulp offsets from 1.000000001 with a mismatch:", ks[:50], "count", len(ks))
for h in hits[:6]: print("  ", h)
# also 1/(1-1e-9) and decimal strings near
for txt in ("1.000000001", "1.0000000010000001", "1.0000000009999999", "1.00000000100000008", "1.000000001000000082740371"):
    p = float(txt); T = 60.0; nl = loop_count(T, p); s_ref, _, d = loop_skip(T, p)
    print(txt, repr(p), "n", nl, "distinct years", d, "ref skip", s_ref, "engine skip", cf.skip_weight_periodic(T, p, nl))

# 2. explicit events
rng = random.Random(9)
bad = 0; n = 0
for _ in range(20000):
    T = rng.choice([0.3, 1.0, 1.5, 7.0, 29.999999999, 30.0, 42.5, 60.0, 60.000001, 99.9]) if rng.random() < 0.7 else rng.uniform(0.01, 130)
    Y = math.ceil(T)
    pool = [0.5, 1, 1.0000000005, 1.000000001, 2, 2.5, 3, 3, 7, T / 2, T / 3, Y - 1, Y - 0.5, Y - 1 + 1e-9, T * (1 - 2e-9), 1e-9, rng.uniform(0, T)]
    ev = [float(t) for t in (rng.choice(pool) for _ in range(rng.randrange(0, 9))) if t > 0 and inside(t, T)]
    w = weights(T); years = {ey(t) for t in ev}
    ref = sum(w[y] for y in years); eng = cf.skip_weight_events(T, ev); n += 1
    if abs(ref - eng) > 1e-12 * max(1, ref): bad += 1; print("events mismatch", T, ev, ref, eng)
print("skip_weight_events:", n, "cases, mismatches", bad)

# 3. linear_weighted_sum
bad = 0; worst = 0.0
for _ in range(20000):
    T = rng.choice([0.3, 1.0, 1.0000001, 1.5, 2.0, 7.0, 29.999999999, 30.0, 42.5, 60.0, 60.000001, 99.9, 129.5]) if rng.random() < 0.7 else rng.uniform(0.01, 130)
    base, slope = rng.uniform(0, 1e6), rng.choice([0.0, rng.uniform(-100, 100)])
    w = weights(T); ref = sum(w[k + 1] * (base + slope * k) for k in range(len(w) - 1))
    eng = cf.linear_weighted_sum(T, base, slope)
    rel = abs(ref - eng) / max(abs(ref), 1e-300); worst = max(worst, rel)
    if rel > 1e-9: bad += 1
print("linear_weighted_sum (positive-ish): worst rel", worst, "bad", bad)
# cancelling case
for T, base in ((60.0, 1e6), (42.5, 1e6), (60.0, 1.0)):
    Y = math.ceil(T)
    slope = -2 * base / (Y - 1)
    w = weights(T); ref = sum(w[k + 1] * (base + slope * k) for k in range(Y)); eng = cf.linear_weighted_sum(T, base, slope)
    print("  cancelling trend T", T, "base", base, "slope", slope, "loop", ref, "closed", eng)

# 4. grid segments / moments vs loop
class G: pass
def gvals(g, Y):
    if g.kind == "CONSTANT": return [g.start] * Y
    if g.kind == "LINEAR_DECLINE_TO_FLOOR": return [max(g.floor, g.start - g.annual_decline * k) for k in range(Y)]
    out = []
    for k in range(Y):
        v = None
        for st in g.steps:
            if st.from_index <= k: v = st.value
        out.append(v)
    return out
bad = 0; worst = 0.0; n = 0
for _ in range(30000):
    T = rng.choice([0.3, 1.0, 1.0000001, 1.5, 2.0, 7.0, 29.999999999, 30.0, 42.5, 60.0, 60.000001, 99.9, 129.5]) if rng.random() < 0.7 else rng.uniform(0.01, 130)
    Y = math.ceil(T); g = G(); g.steps = None
    r = rng.random()
    if r < 0.5:
        g.kind = "LINEAR_DECLINE_TO_FLOOR"; g.start = rng.choice([0.5, rng.uniform(0, 1)]); g.floor = rng.choice([0.0, g.start, g.start * rng.random()])
        m = rng.choice([1, 2, Y - 1, Y, Y + 1, 20, 20.5, 1000]); g.annual_decline = rng.choice([0.0, (g.start - g.floor) / max(m, 1), rng.uniform(0, 0.1), 1e-12])
    elif r < 0.6:
        g.kind = "CONSTANT"; g.start = rng.uniform(0, 1)
    else:
        g.kind = "STEPWISE"; idx = sorted(rng.sample(range(1, Y + 6), rng.randrange(0, min(5, Y + 5))))
        st = []
        for i in [0] + idx:
            s_ = G(); s_.from_index = i; s_.value = rng.uniform(0, 1); st.append(s_)
        g.steps = st
    seg = cf.grid_segments(g, Y)
    if seg is None: continue
    vals = gvals(g, Y); w = weights(T)
    ev = []
    for a, b, al, be in seg: ev.extend([al + be * k for k in range(a, b)])
    n += 1
    if ev != vals: bad += 1; print("segment values differ", g.kind, T, vars(g)); continue
    Gr = sum(w[k + 1] * vals[k] for k in range(Y)); Hr = sum(w[k + 1] * k * vals[k] for k in range(Y))
    Ge, He = cf.segment_moments(seg, T)
    for a_, b_ in ((Gr, Ge), (Hr, He)):
        rel = abs(a_ - b_) / max(abs(a_), 1e-300) if a_ != b_ else 0.0
        worst = max(worst, rel)
        if rel > 1e-9: bad += 1; print("moment mismatch", g.kind, T, a_, b_, seg[:3])
print("grid segments/moments:", n, "cases, bad", bad, "worst rel", worst)

# 5. refrigerant fractions vs year loop
bad = 0; worst = 0.0; n = 0
for _ in range(40000):
    T = rng.choice([0.3, 1.0, 1.0000001, 1.5, 2.0, 7.0, 29.999999999, 30.0, 42.5, 60.0, 60.000001, 99.9, 129.5]) if rng.random() < 0.7 else rng.uniform(0.01, 130)
    Y = math.ceil(T); w = weights(T)
    rate = rng.choice([0.0, 1.0, 1e-15, 1e-9, 1e-300, 0.5, 0.999999999, 1 - 1e-16, rng.random(), rng.random() * 0.05])
    top = rng.random() < 0.3
    evy = sorted(rng.choice([1, Y, max(1, Y - 1), rng.randrange(1, Y + 1)]) for _ in range(rng.randrange(0, 6)))
    m = 1.0; leaked = 0.0; before = []
    cnt = {}
    for y in evy: cnt[y] = cnt.get(y, 0) + 1
    for y in range(1, Y + 1):
        leak = m * rate * w[y]; leaked += leak
        if not top: m -= leak
        for _i in range(cnt.get(y, 0)):
            before.append(m); m = 1.0
    le, be, me = cf.refrigerant_fractions(T, rate, top, evy)
    n += 1
    for a_, b_ in [(leaked, le), (m, me)] + list(zip(before, be)):
        den = max(abs(a_), abs(b_))
        rel = abs(a_ - b_) / den if den else 0.0
        if rel > 1e-9:
            # report with absolute difference too
            if abs(a_ - b_) > 1e-12:
                bad += 1
                if bad < 6: print("refrigerant mismatch", T, rate, top, evy, a_, b_)
        worst = max(worst, rel if abs(a_ - b_) > 1e-18 else 0.0)
    if len(before) != len(be): bad += 1
print("refrigerant_fractions:", n, "cases, bad (abs>1e-12 and rel>1e-9)", bad, "worst rel (abs diff > 1e-18)", worst)
