"""(g) Exact verification of the reduction rules, of the family identities, and of the counterexamples.

Usage: python3 -I tools/verify_families.py <out.json>        (seed 20261128, fictional numbers only)

Levels reported per check: P = proof in 05_families (the code only re-checks it on samples), E = exact rational
comparison on the samples, F = floating-point observation, CE = counterexample found and stored.
"""
import json
import math
import os
import random
import sys
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import five_families as ff  # noqa: E402

SEED = 20261128


def rnd_frac(rng, lo=-50, hi=50, den=8):
    return Fraction(rng.randint(lo * den, hi * den), rng.choice([1, 2, 4, den]))


def boundary_fracs():
    return [Fraction(x) for x in (-1, 0, 1)] + [Fraction(1, 2), Fraction(-1, 2), Fraction(3, 2), Fraction(5, 2)]


def check_rules(rng, n):
    res = {}
    cases = [(rnd_frac(rng), rnd_frac(rng)) for _ in range(n)]
    cases += [(a, b) for a in boundary_fracs() for b in boundary_fracs()]
    res["IF->mask"] = sum(ff.r_if(a < b, a, b) != (a if a < b else b) for a, b in cases)
    res["MIN->mask"] = sum(ff.r_min(a, b) != min(a, b) for a, b in cases)
    res["MAX->mask"] = sum(ff.r_max(a, b) != max(a, b) for a, b in cases)
    res["ABS->mask"] = sum(ff.r_abs(a) != abs(a) for a, _ in cases)
    trip = [(rnd_frac(rng), rnd_frac(rng, -10, 0), rnd_frac(rng, 0, 10)) for _ in range(n)]
    res["CLIP->mask"] = sum(ff.r_clip(x, lo, hi) != min(max(x, lo), hi) for x, lo, hi in trip)
    ys = [Fraction(rng.randint(0, 4000), rng.choice([1, 3, 7, 16])) for _ in range(n)] + [Fraction(k, 2) for k in range(0, 40)]
    # lattice-count rules are exact only on a DECLARED finite domain 0 <= y < N+1 (domain-limited proof)
    N = 600
    ins = [y for y in ys if y < N + 1]
    outs = [y for y in ys if y >= N + 1]
    res["FLOOR->lattice count (0<=y<N+1)"] = sum(ff.r_floor_count(y, N) != math.floor(y) for y in ins)
    res_out = {"FLOOR outside declared domain": dict(level="CE/E", samples=len(outs),
                                                     wrong=sum(ff.r_floor_count(y, N) != math.floor(y) for y in outs),
                                                     note="the finite lattice sum saturates at N: the domain bound is part of the rule")}

    def exact_round(y, d):
        s = Fraction(10) ** d
        return Fraction(math.floor(y * s + Fraction(1, 2))) / s
    NR = 500000
    res["ROUND->lattice count (y 10^d + 1/2 < NR+1)"] = sum(ff.r_round(y, d, NR) != exact_round(y, d)
                                                          for y in ys[:300] for d in (0, 1, 2) if y * 10 ** d + Fraction(1, 2) < NR + 1)
    res["MOD year flag->event sum"] = sum(ff.r_mod_flag(yr, c, 120) != int(yr % c == 0 and yr > 0)
                                        for c in range(1, 40) for yr in range(0, 121))
    res["replacements->count"] = sum(ff.r_replacements(T, c) != max(0, math.ceil(T / c) - 1)
                                     for c in (Fraction(k, 2) for k in range(1, 60)) for T in (Fraction(k, 4) for k in range(1, 400)))
    tab = [(k, Fraction(k * k, 3)) for k in range(30)]
    res["LOOKUP->sum of [key=k]"] = sum(ff.r_lookup(k, tab) != Fraction(k * k, 3) for k in range(30)) + int(ff.r_lookup(99, tab) is not ff.MISSING)
    out = {k: dict(level="E", mismatches=v) for k, v in res.items()}
    out.update(res_out)
    return out


def knot_form(kernels):
    """Independent conversion of a kernel sum into truncated powers: C(T) = A0 + sum_t [t <(rule) T](p + qT)."""
    A0, ev, la = Fraction(0), {}, {}

    def add(d, t, p, q):
        a = d.setdefault(t, [Fraction(0), Fraction(0)])
        a[0] += p
        a[1] += q
    for k in kernels:
        a, s, l, g = Fraction(k.a), Fraction(k.s), Fraction(k.l), k.g
        if l == 0:
            if g == ff.NEG_INF:
                A0 += a
            else:
                add(ev, g, a, 0)
        elif g == ff.NEG_INF:
            add(la, k.s, -a * s, a)
            add(la, k.s + k.l, a * (s + l), -a)
        else:                                    # gated ramp, gate inside the ramp (s < g < (s+l)(1-eps))
            if g >= (k.s + k.l) * (1 - ff.EPS):
                add(ev, g, a * l, 0)
            else:
                add(ev, g, -a * s, a)
                add(la, k.s + k.l, a * (s + l), -a)

    def value(T):
        v = A0
        for t, (p, q) in ev.items():
            if t < T * (1 - ff.EPS):
                v += p + q * Fraction(T)
        for t, (p, q) in la.items():
            if t < T:
                v += p + q * Fraction(T)
        return v
    return value, len(ev), len(la)


def check_f3(rng, n_fun, n_T):
    """Kernel sum == knot form (TH-0 analogue, re-derived independently), on random kernel sums."""
    bad, pts = 0, 0
    for _ in range(n_fun):
        ks = []
        H = rng.randint(5, 80)
        for _ in range(rng.randint(1, 25)):
            typ = rng.choice(["const", "cell", "density", "atom", "gcell"])
            a = rnd_frac(rng, -20, 20)
            if typ == "const":
                ks.append(ff.Kernel(a))
            elif typ == "cell":
                ks.append(ff.Kernel(a, s=float(rng.randrange(H)), l=1.0))
            elif typ == "density":
                ks.append(ff.Kernel(a, s=0.0, l=float(H)))
            elif typ == "atom":
                tau = float(Fraction(rng.randint(1, 4 * H - 1), 4))
                ks.append(ff.Kernel(a, g=tau))
            else:
                k = rng.randrange(H)
                tau = k + rng.choice([0.25, 0.5, 0.75])
                ks.append(ff.Kernel(a, s=float(k), l=1.0, g=tau))
        val, _, _ = knot_form(ks)
        Ts = [rng.uniform(0.001, H) for _ in range(n_T)] + [float(x) for x in range(1, H + 1)] + [x + 0.5 for x in range(H)]
        for T in Ts:
            pts += 1
            bad += ff.f3_value(ks, T) != val(T)
    return dict(level="E", functions=n_fun, points=pts, mismatches=bad)


def check_f4(rng, n):
    bad = 0
    for _ in range(n):
        A = Fraction(rng.randint(0, 100), 100)
        b = rnd_frac(rng, 0, 5)
        u0 = rnd_frac(rng, 0, 50)
        it = ff.f4_affine(A, b, u0, 60)
        bad += sum(it[k] != ff.f4_closed(A, b, u0, k) for k in range(61))
    return dict(level="E", recurrences=n, mismatches=bad)


def check_unification(rng, n):
    """Continuous operation and discrete events are ONE measure: V(T) = mu([0, T)) with
    mu = sum_k r_k Leb|[k,k+1) + sum_j a_j delta_{tau_j}. The kernel sum equals the measure of [0, T) for every T,
    except at the event rule's float band (tau, sw(tau)] where the gate is [tau < T(1-eps)] instead of [tau < T]."""
    bad, band = 0, 0
    for _ in range(n):
        H = rng.randint(3, 40)
        rates = [rnd_frac(rng, 0, 9) for _ in range(H)]
        events = [(float(Fraction(rng.randint(1, 8 * H - 1), 8)), rnd_frac(rng, 0, 30)) for _ in range(rng.randint(0, 6))]
        ks = [ff.Kernel(r, s=float(k), l=1.0) for k, r in enumerate(rates)] + [ff.Kernel(a, g=t) for t, a in events]
        for T in [rng.uniform(0.01, H) for _ in range(40)] + [t + 1e-12 for t, _ in events]:
            meas = sum(rates[k] * min(max(Fraction(T) - k, 0), 1) for k in range(H)) + sum(a for t, a in events if t < T)
            v = ff.f3_value(ks, T)
            if v != meas:
                if any(t < T <= t / (1 - ff.EPS) * (1 + 1e-15) for t, _ in events):
                    band += 1
                else:
                    bad += 1
    return dict(level="E", functions=n, mismatches_outside_band=bad, differences_inside_event_band=band)


def counterexamples(rng):
    ce = {}
    # CE-1 real power / log are not rational maps (proof in 05_families/03); sample: sqrt(2) and log10(2) are irrational
    ce["CE-1 non-integer power"] = dict(level="P", note="x^(1/2) is not a rational function: if p/q = sqrt(x) then p^2 = x q^2, degree parity contradiction",
                                        sample="sqrt(2) = %.17g has no exact Fraction representation" % math.sqrt(2))
    ce["CE-2 log10"] = dict(level="P", note="log10 is transcendental over Q(x); no F1 map equals it on an interval",
                            sample="log10(2) = %.17g" % math.log10(2))
    # CE-3 division vs multiplication by the reciprocal changes floor/threshold results (float)
    found = []
    for _ in range(200000):
        a = rng.randint(1, 10 ** 6)
        b = rng.randint(1, 10 ** 4)
        if math.floor(a / b) != math.floor(a * (1.0 / b)):
            found.append((a, b, a / b, a * (1.0 / b)))
            if len(found) >= 3:
                break
    ce["CE-3 reciprocal product under floor"] = dict(level="CE/F", examples=found,
                                                     note="keep division as division before a floor/threshold (F1 must not rewrite a/b as a*(1/b) there)")
    # CE-4 the (K, sw(K)) band: interval (window) rule [K < T] vs event rule [K < T(1-eps)] for an event at integer K
    K = 17.0
    T = K * (1 + 0.5e-9)
    win = ff.Kernel(Fraction(5), lo=K, hi=K + 1)(T)
    atom = ff.Kernel(Fraction(5), g=K)(T)
    ce["CE-4 band (K, sw(K))"] = dict(level="CE/E", K=K, T=T, window_rule=str(win), event_rule=str(atom),
                                      note="same mathematical event, two time rules: they differ for T in (K, K/(1-eps)); a claim must name its rule or exclude the band")
    # CE-5 initial vs terminal amounts are indistinguishable in C(T) but not in real time
    A, Z, H = Fraction(100), Fraction(40), 30
    c_of_T = [A + Z for _ in range(1, H + 1)]
    real_initial = [A + (Z if t == H else 0) for t in range(0, H + 1)]
    real_swapped = [A + Z if t == 0 else A + Z for t in range(0, H + 1)]
    ce["CE-5 initial vs terminal"] = dict(level="P", C_T_constant=str(c_of_T[0]),
                                          realtime_cumulative_end_of_life_at_T=[str(x) for x in real_initial[:2]] + ["...", str(real_initial[-1])],
                                          realtime_if_booked_at_0=[str(x) for x in real_swapped[:2]] + ["...", str(real_swapped[-1])],
                                          note="C(T) is the same function; the real-time cumulative differs (TH-4 non-uniqueness). Time shape must be carried as metadata, not inferred from C(T).")
    # CE-6 missing treated as zero changes the total (the guard must return MISSING)
    g = ff.Guard()
    q = None
    val = ff.guarded(lambda q, guard: ff.f2_sum_product([(1, q, 3)]) if guard.finite(q, "q") else 0)(q, guard=g)
    ce["CE-6 missing is not zero"] = dict(level="E", result=str(val), violations=g.violations,
                                          note="a missing quantity gives MISSING, whereas zero-filling would report a smaller total as complete")
    # CE-7 rate-domain exceptions: open and closed intervals are not interchangeable
    g2 = ff.Guard()
    cases = {"gross-up 1/(1-w), w=1": g2.rate(1, "w", hi_open=True),
             "on-top r/(1-r), r=0": g2.rate(0, "r", lo_open=True, hi_open=True),
             "share rho=1": g2.rate(1, "rho"),
             "load factor 1.3 (not a 0..1 rate)": g2.positive(1.3, "load factor")}
    ce["CE-7 rate domains"] = dict(level="E", accepted={k: bool(v) for k, v in cases.items()}, violations=g2.violations)
    return ce


def main(out):
    rng = random.Random(SEED)
    res = dict(seed=SEED, rules=check_rules(rng, 3000), f3_kernel_vs_knot=check_f3(rng, 400, 60), f4_closed_form=check_f4(rng, 300),
               f3_continuous_event_unification=check_unification(rng, 300), counterexamples=counterexamples(rng))
    with open(out, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1, default=str)
    tot = sum(v.get("mismatches", 0) for v in res["rules"].values()) + res["f3_kernel_vs_knot"]["mismatches"] + res["f4_closed_form"]["mismatches"] \
        + res["f3_continuous_event_unification"]["mismatches_outside_band"]
    print(json.dumps({k: v for k, v in res.items() if k != "counterexamples"}, ensure_ascii=False, indent=1))
    print("COUNTEREXAMPLES", list(res["counterexamples"]))
    print("TOTAL mismatches (excluding declared band):", tot)
    return tot


if __name__ == "__main__":
    sys.exit(1 if main(sys.argv[1]) else 0)
