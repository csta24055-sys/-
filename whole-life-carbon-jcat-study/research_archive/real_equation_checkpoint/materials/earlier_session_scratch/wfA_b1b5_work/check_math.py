"""Sanity checks of the closed forms quoted in the B1-B5 ledger entries.
All numbers are random synthetic values (SYNTHETIC_FICTIONAL); nothing here is a J-CAT value."""
import math, random
from fractions import Fraction
random.seed(20261111)

def b1_sim(m, l, T, offsets, rho, r, policy):
    """Year-by-year state machine. Returns use leak, event loss, eol loss, recovered, charged-in."""
    R = m; use = evt = 0.0; rec = 0.0; charged = m
    offs = set(offsets)
    for y in range(1, T + 1):
        L = R * l; use += L; P = R - L
        if y == T:
            eol = P * (1 - r); rec += P * r; R = 0.0
        elif y in offs:
            evt += P * rho; rec += P * (1 - rho); R = m; charged += m
        elif policy == "ANNUAL_FULL":
            charged += m - P; R = m
        else:
            R = P
    return use, evt, eol, rec, charged

def b1_closed(m, l, T, offsets, rho, r, policy):
    ks = [0] + sorted(offsets) + [T]
    K = len(offsets)
    if policy == "NONE":
        a = [(1 - l) ** (ks[j] - ks[j - 1]) for j in range(1, K + 2)]
        use = m * sum(1 - x for x in a)
        evt = m * rho * sum(a[:K])
        eol = m * (1 - r) * a[K]
        phi = (K + 1) - (1 - rho) * sum(a[:K]) - r * a[K]
    else:
        use = m * l * T
        evt = m * (1 - l) * rho * K
        eol = m * (1 - l) * (1 - r)
        phi = l * T + (1 - l) * (rho * K + 1 - r)
    return use, evt, eol, phi

maxerr = 0.0
for _ in range(20000):
    T = random.randint(1, 120)
    m = random.uniform(0.1, 500); l = random.uniform(0, 0.4); rho = random.random(); r = random.random()
    nk = random.randint(0, min(6, T - 1))
    offsets = random.sample(range(1, T), nk) if T > 1 else []
    for policy in ("NONE", "ANNUAL_FULL"):
        use, evt, eol, rec, charged = b1_sim(m, l, T, offsets, rho, r, policy)
        cu, ce, cl, phi = b1_closed(m, l, T, offsets, rho, r, policy)
        for a, b in ((use, cu), (evt, ce), (eol, cl), (use + evt + eol, m * phi), (use + evt + eol + rec, charged)):
            maxerr = max(maxerr, abs(a - b) / max(1e-12, abs(b)))
print("B1 closed forms / mass balance max rel err:", maxerr)

# single life, no top-up: total release fraction 1 - r*(1-l)^T
for _ in range(1000):
    T = random.randint(1, 100); l = random.uniform(0, 0.3); r = random.random()
    use, evt, eol, rec, ch = b1_sim(1.0, l, T, [], 0.0, r, "NONE")
    assert abs(use + eol - (1 - r * (1 - l) ** T)) < 1e-12

# periodic cycle closed form for event loss: N*(1-l)^C*rho
for _ in range(2000):
    T = random.randint(2, 100); C = random.randint(1, 40); l = random.uniform(0, 0.3); rho = random.random()
    offs = [n * C for n in range(1, 1000) if n * C < T]
    N = math.ceil(Fraction(T, C)) - 1
    assert N == len(offs)
    use, evt, eol, rec, ch = b1_sim(1.0, l, T, offs, rho, 0.5, "NONE")
    assert abs(evt - rho * N * (1 - l) ** C) < 1e-12
    # annualised effective rate under ANNUAL_FULL: overestimate by rho*(T/C - N) + rho*l*N
    use2, evt2, eol2, rec2, ch2 = b1_sim(1.0, l, T, offs, rho, 0.5, "ANNUAL_FULL")
    ann = (l + rho / C) * T
    diff = ann - (use2 + evt2)
    assert abs(diff - (rho * (T / C - N) + rho * l * N)) < 1e-9 and diff > -1e-12

# first-order leak approx overestimates, exp approx underestimates, 2-term truncation underestimates
for _ in range(5000):
    d = random.randint(1, 80); l = random.uniform(1e-4, 0.3)
    exact = 1 - (1 - l) ** d
    assert l * d >= exact - 1e-15
    assert 1 - math.exp(-l * d) <= exact + 1e-15
    if d >= 2 and l * d < 1:
        assert l * d - math.comb(d, 2) * l * l <= exact + 1e-15
# relative error of first order ~ l(d-1)/2 for small l*d
for l, d in ((0.001, 21), (0.002, 11), (0.0005, 41)):
    exact = 1 - (1 - l) ** d
    print("first-order rel err", l * d / exact - 1, "vs l(d-1)/2 =", l * (d - 1) / 2)
# Jensen: mean rate overestimates leak (no top-up)
for _ in range(2000):
    d = random.randint(1, 60); ls = [random.uniform(0, 0.3) for _ in range(5)]; cs = [random.uniform(1, 10) for _ in range(5)]
    true = sum(c * (1 - (1 - l) ** d) for c, l in zip(cs, ls))
    lbar = sum(c * l for c, l in zip(cs, ls)) / sum(cs)
    assert sum(cs) * (1 - (1 - lbar) ** d) >= true - 1e-9

# B4 counts: ceil(T/L)-1 == (Tm-1)//Lm == brute force, with L in whole months
for _ in range(50000):
    T = random.randint(1, 150); Lm = random.randint(1, 12 * 200); Tm = 12 * T
    brute = 0; n = 1
    while n * Lm < Tm:
        brute += 1; n += 1
    N1 = math.ceil(Fraction(Tm, Lm)) - 1
    N2 = (Tm - 1) // Lm
    assert brute == N1 == N2, (T, Lm, brute, N1, N2)
    x = Fraction(Tm, Lm)
    assert x - 1 <= N1 < x
    e = x - Fraction(1, 2) - N1
    assert Fraction(-1, 2) < e <= Fraction(1, 2)
    if x.denominator == 1:
        assert e == Fraction(1, 2) and N1 == x - 1
    # distinct year indices of events when L >= 1 year
    if Lm >= 12:
        idx = {(k * Lm) // 12 for k in range(1, N1 + 1)}
        assert len(idx) == N1 and all(0 <= j <= T - 1 for j in idx)
print("B4 count identities OK")

# floating point hazard example with decimal periods (synthetic)
bad = 0
for k in range(1, 400):
    L = k / 10.0
    for T in range(1, 121):
        exact = math.ceil(Fraction(T * 10, k)) - 1
        fl = math.ceil(T / L) - 1
        bad += (exact != fl)
print("float ceil(T/L)-1 mismatches for decimal L (out of 48k):", bad)

# B3 skip closed form: sum_y delta = T - N for L >= 1 year
for _ in range(20000):
    T = random.randint(1, 120); Lm = random.randint(12, 12 * 150); Tm = 12 * T
    N = (Tm - 1) // Lm
    skip = {(k * Lm) // 12 + 1 for k in range(1, N + 1)}   # operating year = index + 1
    cnt = sum(1 for y in range(1, T + 1) if y not in skip)
    assert cnt == T - N
print("B3 skip closed form OK")

# nested count with rebuild cycle R: N_R*(ceil(R/L)-1) + (ceil(T'/L)-1)
for _ in range(20000):
    T = random.randint(1, 200); R = random.randint(1, 150); L = random.randint(1, 80)
    NR = math.ceil(Fraction(T, R)) - 1
    Tp = T - NR * R
    assert 0 < Tp <= R
    closed = NR * (math.ceil(Fraction(R, L)) - 1) + (math.ceil(Fraction(Tp, L)) - 1)
    brute = 0
    segs = [(n * R, R) for n in range(NR)] + [(NR * R, Tp)]
    for s, length in segs:
        n = 1
        while n * L < length:
            brute += 1; n += 1
    assert closed == brute
    # annualised whole-building total (T/R) vs exact (N_R+1): underestimate by ceil(T/R)-T/R
    assert Fraction(T, R) <= NR + 1
print("nested rebuild count OK")

# arithmetic / geometric closed forms for sum of factor ratios at events (integer L)
for _ in range(5000):
    T = random.randint(2, 120); L = random.randint(1, 60); N = math.ceil(Fraction(T, L)) - 1
    d = random.uniform(0, 0.005); q = random.uniform(0.9, 0.999)
    s1 = sum(1 - d * n * L for n in range(1, N + 1)); c1 = N - d * L * N * (N + 1) / 2
    s2 = sum(q ** (n * L) for n in range(1, N + 1)); c2 = q ** L * (1 - q ** (N * L)) / (1 - q ** L)
    assert abs(s1 - c1) < 1e-9 and abs(s2 - c2) < 1e-9
print("event factor-sum closed forms OK")
