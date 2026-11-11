"""Independent check of REC-1. Own literal loop (does not import refcalc.base for the brute force)."""
import math, random, struct
from fastcalc import closed_forms as cf
EPS = 1e-9
def lit(T, c):
    # literal: enumerate events, set of years, sum weights
    Y = math.ceil(T)
    w = [0.0] + [min(1.0, T - (y - 1)) for y in range(1, Y + 1)]
    ev = []; n = 1
    while n * c < T * (1.0 - EPS):
        ev.append(n * c); n += 1
    ys = {max(1, math.ceil(t * (1.0 - EPS))) for t in ev}
    return len(ev), len(ys), sum(w[y] for y in ys)
def nxt(x, k):
    b = struct.unpack('<q', struct.pack('<d', x))[0] + k
    return struct.unpack('<d', struct.pack('<q', b))[0]
c0 = 1.000000001
print("c0 repr", repr(c0), "c0*(1-EPS)=", repr(c0 * (1 - EPS)))
Ts = [1.5, 2.0, 3.0, 5.0, 10.0, 25.0, 30.0, 42.5, 59.5, 60.0, 60.5, 99.9, 100.0, 120.0]
bad = {}
for k in range(-5000, 5001):
    c = nxt(c0, k)
    for T in Ts:
        n, ny, sw = lit(T, c)
        got = cf.skip_weight_periodic(T, c, cf.renewal_count(T, c))
        assert cf.renewal_count(T, c) == n
        if abs(got - sw) > 1e-9:
            bad.setdefault(k, []).append((T, n, ny, sw, got))
print("ulps offsets with mismatch within +-5000 ulp of 1.000000001:", sorted(bad))
for k, v in bad.items():
    for t in v: print("  k=%d T=%s events=%d distinct=%d literal=%r closed=%r" % ((k,) + t))
# whole band [1, 1+1.2e-9] random + (0.5,1) + wide
rnd = random.Random(12345); nb = 0; N = 0
for _ in range(400000):
    r = rnd.random()
    if r < 0.4: c = 1.0 + rnd.uniform(0, 1.2e-9)
    elif r < 0.5: c = nxt(1.0, rnd.randint(0, 6000000))
    elif r < 0.6: c = 1.0 - 10 ** rnd.uniform(-16, -1)
    elif r < 0.7: c = rnd.randint(1, 40) * (1 + rnd.choice([1e-9, -1e-9, 2e-9, 5e-10])) 
    elif r < 0.8: c = rnd.randint(1, 400) / rnd.randint(1, 40)
    else: c = rnd.uniform(0.02, 70)
    T = rnd.choice([rnd.uniform(0.3, 120), float(rnd.randint(1, 120)), rnd.randint(1, 240) / 2.0, rnd.randint(1,120)*(1+rnd.choice([1e-9,-1e-9]))])
    n, ny, sw = lit(T, c); N += 1
    got = cf.skip_weight_periodic(T, c, cf.renewal_count(T, c))
    if abs(got - sw) > 1e-9 * max(1, sw):
        nb += 1
        if nb <= 15: print("  MISMATCH c=%r T=%r n=%d distinct=%d lit=%r closed=%r" % (c, T, n, ny, sw, got))
print("random mismatches", nb, "/", N)
# multiples m*(1+1e-9) for m 1..60 and fractions
nb = 0
for m in range(1, 200):
    for num in (1, 2, 3, 4, 5, 7, 10):
        for f in (1 + 1e-9, 1 - 1e-9, 1.000000001, 1 / (1 - 1e-9), 1 + 2e-9):
            c = m / num * f
            for T in Ts:
                n, ny, sw = lit(T, c)
                got = cf.skip_weight_periodic(T, c, cf.renewal_count(T, c))
                if abs(got - sw) > 1e-9 * max(1, sw):
                    nb += 1
                    if nb <= 20: print("  MISMATCH c=%r T=%r n=%d distinct=%d lit=%r closed=%r" % (c, T, n, ny, sw, got))
print("targeted mismatches", nb)
