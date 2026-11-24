"""D checklist 4(iii), 5, 6 (X1): Joule cross terms, AC charge/energy, rectified clocks.
Independent re-derivation; no route code imported. Uses exact rational bookkeeping for
the squared amplitudes (amplitudes a_i = sqrt(q_i), q_i rational) and mpmath only to
print irrational numbers and for transcendental AC functions.

Run: PYTHONDONTWRITEBYTECODE=1 math7-py -B code/check_joule_ac.py
"""
import json, math, os, random, sys
from fractions import Fraction as F
sys.dont_write_bytecode = True
import mpmath as mp
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import oracle_d as O  # noqa: E402

mp.mp.dps = 40
OUT = os.path.join(HERE, "..", "results")
R, I0, KAPPA = F(3), F(2), F(1, 3)          # E fixture: 12 W, 4 kg/yr
AMT = {"AC": F(20), "PIPE": F(35)}


# ------------------------------------------------------------ exact window energy
def window_kg(segments, q, dc=I0):
    """segments: list of (length, {name: sign}); q[name] = a_name^2 (rational).
    Returns exact decomposition of kappa*R*int (dc + sum a_i s_i)^2 over the segments:
      const (rational), lin {i: coeff of a_i}, cross {(i,j): coeff of a_i a_j}."""
    const, lin, cross = F(0), {}, {}
    for L, sg in segments:
        L = F(L)
        const += KAPPA * R * L * (dc * dc + sum(q[i] * s * s for i, s in sg.items()))
        for i, s in sg.items():
            lin[i] = lin.get(i, F(0)) + KAPPA * R * L * 2 * dc * s
        names = sorted(sg)
        for x in range(len(names)):
            for y in range(x + 1, len(names)):
                i, j = names[x], names[y]
                cross[(i, j)] = cross.get((i, j), F(0)) + KAPPA * R * L * 2 * sg[i] * sg[j]
    return const, lin, cross


def evaluate(dec, q):
    const, lin, cross = dec
    v = mp.mpf(const.numerator) / const.denominator
    for i, c in lin.items():
        v += mp.mpf(c.numerator) / c.denominator * mp.sqrt(mp.mpf(q[i].numerator) / q[i].denominator)
    for (i, j), c in cross.items():
        qq = q[i] * q[j]
        v += mp.mpf(c.numerator) / c.denominator * mp.sqrt(mp.mpf(qq.numerator) / qq.denominator)
    return v


def q_for(amount, width):
    """a^2 such that a pulse ALONE of this width carries amount/kappa joules: a^2 R w = A/kappa."""
    return amount / (KAPPA * R * F(width))


def cross_only(dec, q):
    return evaluate((F(0), {}, dec[2]), q)


def dc_cross_only(dec, q):
    return evaluate((F(0), dec[1], {}), q)


def g_after(w, d20, q):
    """G(20+w) on ONE resistor: G0 + DC energy on [0,20+w] + (window@10 - its DC part)
    + (window@20 - its DC part)."""
    win10 = evaluate(window_kg([(w, {"AC": 1})], {"AC": q["AC"]}), q)
    dcw = mp.mpf(4) * mp.mpf(w.numerator) / w.denominator
    return 100 + 4 * (20 + mp.mpf(w.numerator) / w.denominator) + (win10 - dcw) + (evaluate(d20, q) - dcw)


def he2():
    res = {}
    for w in (F(1, 10**6), F(1, 100), F(1)):
        q = {"AC": q_for(20, w), "PIPE": q_for(35, w)}
        d = window_kg([(w, {"AC": 1, "PIPE": 1})], q)
        res[f"equal_aligned_w={w}"] = {
            "cross_kg": mp.nstr(cross_only(d, q), 20), "dc_cross_kg": mp.nstr(dc_cross_only(d, q), 15),
            "4sqrt(20w)+4sqrt(35w)": mp.nstr(4 * mp.sqrt(20 * mp.mpf(w.numerator) / w.denominator)
                                              + 4 * mp.sqrt(35 * mp.mpf(w.numerator) / w.denominator), 15),
            "window_total_kg": mp.nstr(evaluate(d, q), 20),
            "G(20+w)_single_resistor": mp.nstr(g_after(w, d, q), 18)}
    res["20*sqrt(7)"] = mp.nstr(20 * mp.sqrt(7), 20)
    # unequal widths starting together: AC width w, PIPE width 4w
    w = F(1, 1000)
    q = {"AC": q_for(20, w), "PIPE": q_for(35, 4 * w)}
    d = window_kg([(w, {"AC": 1, "PIPE": 1}), (3 * w, {"PIPE": 1})], q)
    res["unequal_widths_w_and_4w"] = {"cross_kg": mp.nstr(cross_only(d, q), 20),
                                      "formula 2sqrt(AiAj)*overlap/sqrt(wi wj)": mp.nstr(2 * mp.sqrt(700) * 1 / 2, 20)}
    # misaligned equal widths, overlap w/2
    q = {"AC": q_for(20, w), "PIPE": q_for(35, w)}
    d = window_kg([(w / 2, {"AC": 1}), (w / 2, {"AC": 1, "PIPE": 1}), (w / 2, {"PIPE": 1})], q)
    res["misaligned_overlap_half"] = {"cross_kg": mp.nstr(cross_only(d, q), 20), "sqrt(700)": mp.nstr(mp.sqrt(700), 20)}
    # time-interleaved on ONE resistor: no AC x PIPE overlap
    d = window_kg([(w, {"AC": 1}), (w, {"PIPE": 1})], q)
    res["time_interleaved_single_resistor"] = {"cross_kg": mp.nstr(cross_only(d, q), 5),
                                               "dc_cross_kg": mp.nstr(dc_cross_only(d, q), 15)}
    # Walsh-orthogonal zero-mean pulses on ONE resistor, simultaneous, WITH dc: exact additivity
    wq = w / 4
    q = {"AC": q_for(20, w), "PIPE": q_for(35, w)}
    segs = [(wq, {"AC": 1, "PIPE": 1}), (wq, {"AC": 1, "PIPE": -1}), (wq, {"AC": -1, "PIPE": 1}), (wq, {"AC": -1, "PIPE": -1})]
    d = window_kg(segs, q)
    res["walsh_orthogonal_single_resistor"] = {
        "cross_coeffs": {f"{k}": str(v) for k, v in d[2].items()}, "dc_cross_coeffs": {k: str(v) for k, v in d[1].items()},
        "window_total_kg": str(d[0]), "expected 4w+20+35": str(4 * w + 55),
        "exactly_additive": d[1] == {"AC": 0, "PIPE": 0} and all(v == 0 for v in d[2].values()) and d[0] == 4 * w + 55,
        "charge_carried_(route_A_view)": "0 (zero-mean): orthogonality trick is NOT available to a charge accumulator"}
    # polarity: reversed pipe pulse, equal aligned
    w = F(1, 10**6)
    q = {"AC": q_for(20, w), "PIPE": q_for(35, w)}
    d = window_kg([(w, {"AC": 1, "PIPE": -1})], q)
    res["polarity_reversed_pipe_w=1e-6"] = {"window_total_kg": mp.nstr(evaluate(d, q), 18),
                                            "G(20+w)": mp.nstr(g_after(w, d, q), 18)}
    # three simultaneous events: pairwise 2 sqrt(AiAj)
    q3 = {"X": q_for(20, w), "Y": q_for(35, w), "Z": q_for(45, w)}
    d = window_kg([(w, {"X": 1, "Y": 1, "Z": 1})], q3)
    res["three_simultaneous"] = {"cross_kg": mp.nstr(cross_only(d, q3), 20),
                                 "2(sqrt(700)+sqrt(900)+sqrt(1575))": mp.nstr(2 * (mp.sqrt(700) + mp.sqrt(900) + mp.sqrt(1575)), 20)}
    # route A view: charge through one capacitor is additive for any shapes
    res["charge_additivity"] = "int(i_a+i_b)dt = q_a+q_b for every shape/overlap (linearity); rectangular pulses with area A/gamma: sum 55/gamma exactly"
    return res


def x1():
    """Gate X1: same P0, A (impulse charge) vs E (separate-resistor finite pulses, w=1e-6):
    agreement outside windows; at tau the pulse model gives the left value."""
    w = F(1, 10**6)
    out = {}
    for ts in O.CONTRACT_POINTS + ["10.0000005", "20.0000005"]:
        t = F(ts)
        a_val = O.G("P0", t, O.RIGHT)              # impulse/charge model (right-continuous)
        ev, _ = O.ledger("P0")
        # separate resistors, energy delivered on [tau, tau+w): amount * clip((t-tau)/w, 0, 1)
        e_val = 100 + 4 * t + sum((e.amount * min(max((t - e.time) / w, F(0)), F(1)) for e in ev), F(0))
        inside = any(e.time <= t < e.time + w for e in ev)
        out[ts] = {"A_impulse": O.dec(a_val), "E_separate_pulses": O.dec(e_val), "inside_window": inside,
                   "equal": a_val == e_val, "E_equals_left_value": e_val == O.G("P0", t, O.LEFT)}
    return out


# ------------------------------------------------------------ AC
def Hc(u):
    """Antiderivative of |sin| with Hc(0)=0 (mp)."""
    k = mp.floor(u / mp.pi)
    return 2 * k + 1 - mp.cos(u - k * mp.pi)


def zero_mean_ac():
    out = {}
    w = 2 * mp.pi
    for phi in (0, mp.pi / 3, 1.0, mp.pi):
        I0a = mp.mpf(1)
        qs = [(I0a / w) * (mp.cos(phi) - mp.cos(w * mp.mpf(k) / 997 + phi)) for k in range(0, 997 * 10)]
        out[f"phi={mp.nstr(phi, 6)}"] = {"min": mp.nstr(min(qs), 10), "max": mp.nstr(max(qs), 10),
                                         "bound_(I0/w)(cos phi +/- 1)": [mp.nstr((I0a / w) * (mp.cos(phi) - 1), 10),
                                                                          mp.nstr((I0a / w) * (mp.cos(phi) + 1), 10)]}
    # spurious counts: threshold BELOW the swing, reset (subtract) at the hit
    def count(theta, omega, T, I0a=1.0, dt=1e-4):
        q, n, t = 0.0, 0, 0.0
        while t < T:
            # exact increment over dt
            q += (I0a / omega) * (math.cos(omega * t) - math.cos(omega * (t + dt)))
            t += dt
            if q >= theta:
                q -= theta; n += 1
        return n
    out["spurious_counts_threshold_below_swing"] = {
        "theta=0.1, omega=2pi, T=10": count(0.1, 2 * math.pi, 10.0),
        "theta=0.1, omega=4pi, T=10": count(0.1, 4 * math.pi, 10.0),
        "theta=0.2, omega=2pi, T=10": count(0.2, 2 * math.pi, 10.0),
        "note": "subtract-reset clock driven by zero-mean AC counts by frequency/threshold, unrelated to any period c "
                "(A left this NOT_RUN); a reset-to-zero clock would count once per positive half-cycle."}
    return out


def rect_hits(c, phi, nmax, omega=2 * mp.pi):
    """|I0 sin(omega t + phi)| with mean 1/c, hit times of Q=n (bisection). Returns max |tau_n - n c|."""
    I0a = mp.pi / (2 * c)
    Q = lambda t: (I0a / omega) * (Hc(omega * t + phi) - Hc(phi))
    worst = mp.mpf(0)
    for n in range(1, nmax + 1):
        lo, hi = mp.mpf(n * c) - mp.mpf(1), mp.mpf(n * c) + mp.mpf(1)
        for _ in range(110):
            mid = (lo + hi) / 2
            if Q(mid) < n:
                lo = mid
            else:
                hi = mid
        worst = max(worst, abs(hi - n * c))
    return worst


def rectified():
    out = {"phi=0_scan_c/h=k/4": {}, "phase_offsets_half_integer": {}}
    mp.mp.dps = 30
    h = mp.mpf(1) / 2            # omega=2pi -> half period 1/2
    for k in range(1, 41):
        c = h * k / 4
        err = rect_hits(c, 0, 12)
        out["phi=0_scan_c/h=k/4"][f"{k}/4"] = {"max_err": mp.nstr(err, 3), "exact(<1e-10; sqrt-conditioned at current zeros)": bool(err < mp.mpf(10) ** -10)}
    for phi in (0, mp.pi / 4, mp.mpf("0.3"), mp.pi / 2, mp.mpf("1.0")):
        c = h * mp.mpf("20.5")
        err = rect_hits(c, phi, 12)
        out["phase_offsets_half_integer"][f"phi={mp.nstr(phi, 6)}, c/h=20.5"] = {
            "max_err": mp.nstr(err, 4), "exact": bool(err < mp.mpf(10) ** -10)}
        err_int = rect_hits(h * 20, phi, 12)
        out["phase_offsets_half_integer"][f"phi={mp.nstr(phi, 6)}, c/h=20"] = {"max_err": mp.nstr(err_int, 4),
                                                                               "exact": bool(err_int < mp.mpf(10) ** -10)}
    # phases phi in [0,pi) for which half-integer multiples are exact: g(phi+pi/2)=g(phi)
    g = lambda u: Hc(u) - 2 * u / mp.pi
    f = lambda p: g(p + mp.pi / 2) - g(p)
    roots = []
    grid = [mp.pi * i / 2000 for i in range(2001)]
    for a, b in zip(grid[:-1], grid[1:]):
        fa, fb = f(a), f(b)
        if fa == 0:
            roots.append(a)
        elif fa * fb < 0:
            roots.append(mp.findroot(f, (a, b), solver="bisect"))
    out["phases_where_half_integer_exact"] = [mp.nstr(r / mp.pi, 12) + "*pi" for r in roots]
    # sharp bound for |tau_n - n c|/h when not exact
    m = mp.sqrt(1 - 4 / mp.pi ** 2) + 2 * mp.asin(2 / mp.pi) / mp.pi - 1
    worst = mp.mpf(0)
    rng = random.Random(5)
    for _ in range(40):
        c = mp.mpf(rng.uniform(0.3, 12.0))
        worst = max(worst, rect_hits(c, 0, 8) / h)
    out["hit_error_over_h"] = {"max_sampled": mp.nstr(worst, 8), "sharp_bound m/2": mp.nstr(m / 2, 8),
                               "A_claimed_bound": "1 (|tau_n - n c| < h)",
                               "note": "|tau_n-nc| = c|d(tau_n)| <= c*(I0/omega)*m = m*h/2 ~ 0.1053 h"}
    mp.mp.dps = 40
    return out


def e_ac_bound():
    """Search for violations of sup|kappa E - r t| = r(1+|sin 2phi|)/(2 omega) using
    E computed by independent Gauss-Legendre quadrature of i^2 R (not the closed form)."""
    mp.mp.dps = 25
    rng = random.Random(77)
    worst_ratio, viol = mp.mpf(0), 0
    rows = []
    for _ in range(12):
        phi = mp.mpf(rng.uniform(-3.2, 3.2)); om = mp.mpf(rng.uniform(0.5, 20))
        b = 4 * (1 + abs(mp.sin(2 * phi))) / (2 * om)
        mx = mp.mpf(0)
        Tper = mp.pi / om
        for j in range(60):
            t = Tper * j / 30
            e = mp.quad(lambda s: 3 * (mp.sqrt(2) * 2 * mp.sin(om * s + phi)) ** 2, [0, t]) if t > 0 else mp.mpf(0)
            dev = abs(e / 3 - 4 * t)
            mx = max(mx, dev)
            if dev > b * (1 + mp.mpf(10) ** -15):
                viol += 1
        # exact attainment point: sin(2 om t + 2 phi) = -sign(sin 2phi)
        target = -mp.pi / 2 if mp.sin(2 * phi) >= 0 else mp.pi / 2
        tt = (target - 2 * phi) / (2 * om)
        while tt < 0:
            tt += mp.pi / om
        e = mp.quad(lambda s: 3 * (mp.sqrt(2) * 2 * mp.sin(om * s + phi)) ** 2, [0, tt])
        att = abs(e / 3 - 4 * tt)
        worst_ratio = max(worst_ratio, mx / b)
        rows.append({"phi": mp.nstr(phi, 6), "omega": mp.nstr(om, 6), "bound": mp.nstr(b, 10),
                     "grid_max": mp.nstr(mx, 10), "attained_at_t*": mp.nstr(att, 15)})
    # lattice: phi=0, omega=2pi -> exact iff t in Z/4 ; second family for phi != 0
    lat = []
    for t in (F(1, 4), F(3, 8), F(1, 2), F(9999999, 10**6)):
        e = mp.quad(lambda s: 3 * (mp.sqrt(2) * 2 * mp.sin(2 * mp.pi * s)) ** 2, [0, mp.mpf(t.numerator) / t.denominator])
        lat.append({"t": str(t), "kappaE-4t": mp.nstr(e / 3 - 4 * mp.mpf(t.numerator) / t.denominator, 12)})
    phi = mp.mpf("0.3")
    t2 = (mp.pi - 4 * phi) / (4 * mp.pi)       # second family, omega=2pi, k=0
    e = mp.quad(lambda s: 3 * (mp.sqrt(2) * 2 * mp.sin(2 * mp.pi * s + phi)) ** 2, [0, t2])
    lat.append({"t": "second family (pi-4phi)/(2omega), phi=0.3", "kappaE-4t": mp.nstr(e / 3 - 4 * t2, 12)})
    mp.mp.dps = 40
    return {"violations": viol, "max grid/bound": mp.nstr(worst_ratio, 12), "cases": rows, "lattice": lat}


def he4():
    """EF step 1/3 -> 1/4 kg/J at t=10 with p=12 W (exact rational sweep)."""
    def good(t):
        t = F(t)
        return KAPPA * 12 * min(t, F(10)) + F(1, 4) * 12 * max(t - 10, F(0))
    def cur(t):
        t = F(t)
        return (KAPPA if t < 10 else F(1, 4)) * 12 * t
    def ini(t):
        return KAPPA * 12 * F(t)
    tab = {t: [O.dec(good(t)), O.dec(cur(t)), O.dec(ini(t))] for t in ("9.999999", "10", "20", "40", "60")}
    full = {t: [O.dec(O.G("P2", t)), O.dec(100 + cur(t) + (O.G("P0", t) - 100 - 4 * F(t)))] for t in ("10", "20", "60")}
    return {"[convert-then-integrate, meter-then-convert(current), meter(initial)]": tab,
            "full_G [P2, wrong readout]": full}


def main():
    res = {"HE2": he2(), "X1": x1(), "zero_mean_ac": zero_mean_ac(), "rectified_clock": rectified(),
           "E_ac_bound_search": e_ac_bound(), "HE4": he4()}
    os.makedirs(OUT, exist_ok=True)
    json.dump(res, open(os.path.join(OUT, "joule_ac_check.json"), "w"), indent=1, default=str)
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
