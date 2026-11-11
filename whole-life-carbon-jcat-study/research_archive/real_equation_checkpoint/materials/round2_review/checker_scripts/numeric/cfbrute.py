"""Brute-force loops (my own) versus fastcalc.closed_forms."""
import math, random, sys
sys.dont_write_bytecode = True
from fastcalc import closed_forms as cf
EPS = 1e-9
def inside(t, T): return t < T * (1.0 - EPS)
def ey(t): return max(1, math.ceil(t * (1.0 - EPS)))
def weights(T):
    Y = math.ceil(T); return [0.0] + [min(1.0, T - (y - 1)) for y in range(1, Y + 1)]
def loop_count(T, p):
    if p is None or not (p > 0) or math.isinf(p): return 0
    n = 1
    while inside(n * p, T): n += 1
    return n - 1
def loop_skip(T, p):
    w = weights(T); n = loop_count(T, p)
    years = {ey(k * p) for k in range(1, n + 1)}
    return sum(w[y] for y in years), n, len(years)

rng = random.Random(5)
Ts = [0.3, 0.5, 1.0, 1.0000001, 1.5, 2.0, 2.5, 7.0, 10.0, 12.3, 29.999999999, 30.0, 42.5, 55.5, 59.9999999999, 60.0, 60.000001, 62.5, 99.9, 100.0, 120.0]
Ts += [rng.uniform(0.01, 130) for _ in range(40)]
ps = []
for b in (1.0, 2.0, 3.0, 5.0, 10.0, 0.5, 0.25):
    for k in range(-30, 31):
        ps.append(b * (1 + k * 1e-10))
    for k in (-3, -2, -1, 0, 1, 2, 3):
        x = b * 1.000000001
        for _ in range(abs(k)):
            x = math.nextafter(x, math.inf if k > 0 else -math.inf)
        ps.append(x)
        x = b / (1 - 1e-9)
        for _ in range(abs(k)):
            x = math.nextafter(x, math.inf if k > 0 else -math.inf)
        ps.append(x)
ps += [rng.uniform(0.02, 3.0) for _ in range(3000)] + [rng.uniform(0.9, 1.1) for _ in range(2000)] + [rng.uniform(1.0, 1.00000001) for _ in range(3000)] + [round(rng.uniform(0.05, 40), rng.choice([1, 2, 3])) for _ in range(3000)]
bad_count = bad_skip = 0; n = 0; examples = {}
for T in Ts:
    for p in ps:
        if T / p > 3000: continue
        n += 1
        nl = loop_count(T, p)
        if nl != cf.renewal_count(T, p): bad_count += 1
        s_ref, _, distinct = loop_skip(T, p)
        s_eng = cf.skip_weight_periodic(T, p, nl)
        if abs(s_ref - s_eng) > 1e-9 * max(1.0, abs(s_ref)):
            bad_skip += 1
            examples.setdefault(repr(p), []).append((T, nl, distinct, s_ref, s_eng))
print(f"periodic: {n} (T, period) pairs; renewal_count mismatches {bad_count}; skip_weight_periodic mismatches {bad_skip}")
print("distinct periods with a mismatch:", len(examples))
for p, v in sorted(examples.items(), key=lambda kv: float(kv[0]))[:40]:
    print("   period", p, "p*(1-1e-9) =", repr(float(p) * (1 - 1e-9)), "first:", v[0], "cases:", len(v))
