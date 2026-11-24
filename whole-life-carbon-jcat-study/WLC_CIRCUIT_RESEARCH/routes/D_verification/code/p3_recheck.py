"""Pass 3: re-check of the route A and E fixes made after D pass 1, and settlement of the disputes.
Route code is loaded only through probe_routes.load (read-only, bytecode off); D's oracle stays oracle_d.

Run: PYTHONDONTWRITEBYTECODE=1 math7-py -B code/p3_recheck.py
"""
import json, math, os, random, sys, time
from fractions import Fraction as F
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import oracle_d as O                     # noqa: E402
import probe_routes as PR                # noqa: E402  (load / point_set / compare helpers)
import check_boundary as CB              # noqa: E402
import check_joule_ac as JA              # noqa: E402
import bench as BE                       # noqa: E402
import mpmath as mp                      # noqa: E402

OUT = os.path.join(HERE, "..", "results")


# ------------------------------------------------------------------ A (1): orig fixes, raises, big comparison
def a_fixes(A, Aor, pts):
    L = {}
    for conv in O.CONVENTIONS:
        L[f"R1|{conv}"] = PR.compare(A.p0_r1(conv).G, "P0", conv, pts)
        L[f"R2|{conv}"] = PR.compare(A.p0_r2(conv).G, "P0", conv, pts)
        L[f"R3|{conv}"] = PR.compare(A.R3(conv).G, "P0", conv, pts)
        L[f"R3i_P0|{conv}"] = PR.compare(A.R3i([(F(1, 2), 20), (1, 55)], conv=conv).G, "P0", conv, pts)
        for pol in ("substitute", "additional"):
            L[f"p1_r1_{pol}|{conv}"] = PR.compare(A.p1_r1(pol, conv).G, "P1", conv, pts, pol)
        if conv != O.ORIG:
            L[f"R3k|{conv}"] = PR.compare(A.R3k(conv).G, "P0", conv, pts)
            L[f"px_r1|{conv}"] = PR.compare(A.px_r1(conv).G, "Px", conv, pts)
            L[f"p2_r1|{conv}"] = PR.compare(A.p2_r1(conv).G, "P2", conv, pts)
            L[f"R3i_Px|{conv}"] = PR.compare(A.R3i([(F(7, 20), 20), (F(17, 20), 20), (1, 35)], conv=conv).G, "Px", conv, pts)
    # explicit closed-band endpoints (exact), both policies, P0 and P1
    ends = {}
    for tau in (10, 20, 40):
        b = F(tau) / (1 - O.EPS)
        for t, lab in ((b, "tau/(1-eps)"), (b + F(1, 10**15), "+1e-15"), (b - F(1, 10**15), "-1e-15")):
            row = {"R3i_orig": str(A.R3i([(F(1, 2), 20), (1, 55)], conv=O.ORIG).G(t)), "D_P0_orig": str(O.G("P0", t, O.ORIG))}
            for pol in ("substitute", "additional"):
                row[f"p1_r1_{pol}"] = str(A.p1_r1(pol, O.ORIG).G(t)); row[f"D_P1_{pol}"] = str(O.G("P1", t, O.ORIG, pol))
            row["all_equal"] = row["R3i_orig"] == row["D_P0_orig"] and all(row[f"p1_r1_{p}"] == row[f"D_P1_{p}"] for p in ("substitute", "additional"))
            ends[f"{tau} {lab}"] = row
    raises = {}
    for name, fn in (("p2_r1(orig).G(15)", lambda: A.p2_r1(O.ORIG).G(15)), ("px_r1(orig).G(15)", lambda: A.px_r1(O.ORIG).G(15)),
                     ("R3k(orig)", lambda: A.R3k(O.ORIG).G(15)), ("R3i(conv='foo')", lambda: A.R3i([(1, 55)], conv="foo").G(15)),
                     ("p0_r1('foo').G(15)", lambda: A.p0_r1("foo").G(15)), ("oracle g_p2(orig)", lambda: Aor.g_p2(15, O.ORIG))):
        try:
            v = fn(); raises[name] = f"NO RAISE, returned {v}"
        except Exception as ex:
            raises[name] = f"raises {type(ex).__name__}"
    return {"large_comparison": L, "band_endpoints": ends, "unsupported": raises,
            "total_mismatches": sum(v["mismatches"] for v in L.values())}


# ------------------------------------------------------------------ A (2): zero-mean AC clock dispute
def zero_mean_clock(rule, I0=1.0, omega=2 * math.pi, theta=0.1, T=10.0, dt=1e-4):
    """D's own event-exact simulator: q' = I0 sin(omega t); exact increments per step, bisection for hits
    and (clamp) for the zero crossing. rule: 'subtract' | 'zero' | 'zero+clamp' | 'subtract+clamp'."""
    Qc = lambda t: (I0 / omega) * (1 - math.cos(omega * t))          # antiderivative
    hits, t, q = 0, 0.0, 0.0
    clamp = "clamp" in rule
    while t < T:
        t2 = min(t + dt, T)
        dq = Qc(t2) - Qc(t)
        if q + dq >= theta:
            lo, hi = t, t2
            for _ in range(80):
                mid = 0.5 * (lo + hi)
                if q + Qc(mid) - Qc(t) >= theta:
                    hi = mid
                else:
                    lo = mid
            qh = q + Qc(hi) - Qc(t)
            q = qh - theta if rule.startswith("subtract") else 0.0
            hits += 1
            t = hi
            continue
        if clamp and q + dq < 0:
            q = 0.0                     # ideal diode: no negative charge
        else:
            q += dq
        t = t2
    return hits


def a_zero_mean(A):
    mine = {r: zero_mean_clock(r) for r in ("subtract", "zero", "zero+clamp", "subtract+clamp")}
    mine_4pi = {r: zero_mean_clock(r, omega=4 * math.pi) for r in ("zero", "zero+clamp")}
    Qc = lambda t: (1.0 / (2 * math.pi)) * (1 - math.cos(2 * math.pi * t))
    theirs = {f"reset={r},clamp={c}": len(A.simulate_clock(10.0, Qc, theta=0.1, reset=r, clamp=c))
              for r in ("subtract", "zero") for c in (False, True)}
    # analytic: first half-cycle hits for reset-to-zero: cos(omega t_k) = 1 - k*theta*omega/I0 while >= -1
    k = 0
    while 1 - (k + 1) * 0.1 * 2 * math.pi >= -1:
        k += 1
    return {"D_event_simulator(I0=1, omega=2pi, theta=0.1, 10 y)": mine, "D_omega=4pi": mine_4pi,
            "A_simulate_clock": theirs, "analytic_hits_per_positive_half_cycle": k,
            "verdict": "A is right: reset-to-zero at the exact hit equals subtract-reset (q_hit = theta); without a clamp the "
                       "first half-cycle gives 3 hits and the bounded offset never reaches theta again; with an ideal diode "
                       "clamp every positive half-cycle restarts from 0 and gives 3 hits -> 30 in 10 y. D's pass-1 note "
                       "('reset-to-zero would count once per positive half-cycle') was wrong on both counts."}


# ------------------------------------------------------------------ A (3): rectified clock error bound with phase
def Hf(u):
    k = math.floor(u / math.pi)
    return 2 * k + 1 - math.cos(u - k * math.pi)


def g(u):
    return Hf(u) - 2 * u / math.pi


def hit_err_over_h(c_over_h, phi, nmax, omega=2 * math.pi):
    h = math.pi / omega
    c = c_over_h * h
    I0 = math.pi / (2 * c)
    Q = lambda t: (I0 / omega) * (Hf(omega * t + phi) - Hf(phi))
    worst = 0.0
    for n in range(1, nmax + 1):
        lo, hi = n * c - h, n * c + h
        for _ in range(70):
            mid = 0.5 * (lo + hi)
            if Q(mid) < n:
                lo = mid
            else:
                hi = mid
        worst = max(worst, abs(hi - n * c) / h)
    return worst


def a16_bound():
    m = math.sqrt(1 - 4 / math.pi ** 2) + 2 * math.asin(2 / math.pi) / math.pi - 1
    bound = lambda phi: (m + abs(g(phi % math.pi))) / 2           # in units of h
    phis = [0.0, math.pi / 2, math.asin(2 / math.pi), math.pi - math.asin(2 / math.pi), math.pi / 4, 0.3, 1.0]
    rows = []
    for phi in phis:
        for coh in (20.25, 20.5, (1 + 5 ** 0.5) / 2 * 13, math.sqrt(2) * 17):
            e = hit_err_over_h(coh, phi, 400)
            rows.append({"phi": round(phi, 6), "c/h": round(coh, 6), "max_n<=400 |tau_n-nc|/h": e,
                         "closed_form_bound (m+|g(phi)|)/2": bound(phi), "within_bound": e <= bound(phi) + 1e-9})
    rng = random.Random(9)
    worst = 0.0
    for _ in range(60):
        phi = rng.uniform(0, math.pi); coh = rng.uniform(5, 30)
        e = hit_err_over_h(coh, phi, 200)
        worst = max(worst, e / bound(phi))
    return {"m": m, "m/2": m / 2, "global_sup m (phi=asin(2/pi) or pi-asin(2/pi))": m,
            "closed_form": "|tau_n - n c| <= (h/2)(m + |g(phi)|), g(u)=H(u)-2u/pi, |g|<=m; sharp (irrational c/h); "
                           "= m h/2 at phi in {0, pi/2}, = m h at phi = asin(2/pi)",
            "rows": rows, "random_max_ratio_to_bound": worst}


# ------------------------------------------------------------------ E (5)(6)
def e_rho_and_walsh():
    w = F(1, 100)
    q = lambda A, ww: JA.q_for(A, ww)
    base = 2 * mp.sqrt(700)
    cases = {}
    def add(name, segs, qq):
        d = JA.window_kg(segs, qq)
        cr = JA.cross_only(d, qq)
        cases[name] = {"cross_kg": mp.nstr(cr, 12), "rho": mp.nstr(cr / base, 12)}
    add("equal aligned", [(w, {"AC": 1, "PIPE": 1})], {"AC": q(20, w), "PIPE": q(35, w)})
    add("widths w,4w", [(w, {"AC": 1, "PIPE": 1}), (3 * w, {"PIPE": 1})], {"AC": q(20, w), "PIPE": q(35, 4 * w)})
    add("half overlap", [(w / 2, {"AC": 1}), (w / 2, {"AC": 1, "PIPE": 1}), (w / 2, {"PIPE": 1})], {"AC": q(20, w), "PIPE": q(35, w)})
    add("widths w,9w", [(w, {"AC": 1, "PIPE": 1}), (8 * w, {"PIPE": 1})], {"AC": q(20, w), "PIPE": q(35, 9 * w)})
    s4 = w / 4
    add("rect vs Walsh(1,1,1,-1)", [(s4, {"AC": 1, "PIPE": 1}), (s4, {"AC": 1, "PIPE": 1}), (s4, {"AC": 1, "PIPE": 1}),
                                    (s4, {"AC": 1, "PIPE": -1})], {"AC": q(20, w), "PIPE": q(35, w)})
    add("interleaved", [(w, {"AC": 1}), (w, {"PIPE": 1})], {"AC": q(20, w), "PIPE": q(35, w)})
    add("Walsh pair", [(s4, {"AC": 1, "PIPE": 1}), (s4, {"AC": 1, "PIPE": -1}), (s4, {"AC": -1, "PIPE": 1}),
                       (s4, {"AC": -1, "PIPE": -1})], {"AC": q(20, w), "PIPE": q(35, w)})
    # qualification 1: inside the window, t = 20 + w/4 (first quarter of the Walsh scheme, DC on)
    qq = {"AC": q(20, w), "PIPE": q(35, w)}
    d = JA.window_kg([(s4, {"AC": 1, "PIPE": 1})], qq)
    inside = JA.cross_only(d, qq) + JA.dc_cross_only(d, qq)
    # qualification 3: AC operating current sqrt2*2 sin(2 pi s) vs Walsh AC pulse (+,+,-,-) on [20, 20+w)
    a = mp.sqrt(mp.mpf(20) / (mp.mpf(1) / 3 * 3 * mp.mpf(w.numerator) / w.denominator))
    wf = mp.mpf(w.numerator) / w.denominator
    I = mp.mpf(0)
    for k, sgn in enumerate((1, 1, -1, -1)):
        lo, hi = 20 + k * wf / 4, 20 + (k + 1) * wf / 4
        I += sgn * mp.quad(lambda s: mp.sqrt(2) * 2 * mp.sin(2 * mp.pi * s), [lo, hi])
    ac_cross = (mp.mpf(1) / 3) * 2 * 3 * a * I
    return {"rho_table": cases, "inside_window_t=20+w/4_kg": mp.nstr(inside, 10),
            "inside_split": {"event_x_event": mp.nstr(JA.cross_only(d, qq), 10), "dc_x_pulse": mp.nstr(JA.dc_cross_only(d, qq), 10)},
            "AC_operating_vs_Walsh_AC_pulse_kg(w=0.01)": mp.nstr(ac_cross, 10),
            "exactness_at_every_t_with_DC": ("d/dt [kappa*2R*int_0^t I0 i_p] = 2 kappa R I0 i_p(t) must vanish for all t => "
                                             "i_p = 0 a.e.: no nonzero event pulse can be exact at every t while a DC "
                                             "operating current flows (and event pulses need disjoint supports).")}


# ------------------------------------------------------------------ E (7)(8)(9)
def e_checks(Ec, Eq, pts):
    L = {}
    for conv in O.CONVENTIONS:
        L[f"ER1_P0|{conv}"] = PR.compare(lambda t, c=conv: Ec.g_er1(t, c), "P0", conv, pts)
        for pol in ("substitute", "additional"):
            L[f"ER1_P1_{pol}|{conv}"] = PR.compare(lambda t, c=conv, p=pol: Ec.g_er1(t, c, p1=p), "P1", conv, pts, pol)
    L["ER1_P2_efswitch|right"] = PR.compare(lambda t: Ec.g_er1(t, "right", True), "P2", O.RIGHT, pts)
    tuples = {"STATES_P1": Ec.ER1.STATES_P1, "STATES_P1_MERGED": Ec.ER1.STATES_P1_MERGED}
    # ledger semantics: E's 'substitute' is a net -5 table entry while the AC@20 and pipe@20 clocks still fire
    m = Ec.ER1("right", p1="substitute"); m.run_to(F(20))
    ledger_note = {"E_S_ledger_at_20": str(m.S), "explanation": "S = 20(AC@10)+20(AC@20)+35(pipe@20)-5(net renovation entry) = 70; "
                   "D's separate-ledger substitute keeps {AC@10 20, RENOV@20 50} = 70. Same total, different ledger content."}
    # fixed step: E's fixed_step_true vs D's d_sweep on both point sets
    rng = random.Random(12345)
    e_pts = [F(rng.randrange(0, 60_000_000), 1_000_000) for _ in range(1000)]
    d_pts = BE.points()
    fs = {}
    for dt in (1e-2, 1e-3, 1e-4):
        row = {}
        for name, P in (("E_1000_pts(seed 12345)", e_pts), ("D_100011_pts(seed 20261124)", d_pts)):
            ex = [float(O.G("P0", t)) for t in P]
            eo = Eq.fixed_step_true(dt, P)
            e_big = sum(1 for t, x in zip(P, ex) if abs(eo[t] - x) > 1.0)
            do = BE.d_sweep([float(t) for t in P], dt)
            d_big = sum(1 for y, x in zip(do, ex) if abs(y - x) > 1.0)
            row[name] = {"E_rule(round(t/dt) steps, reset to 0)": e_big, "D_rule(steps with s+dt<=t, interpolate, subtract)": d_big}
        row["contract_points_E_rule"] = {ts: Eq.fixed_step_true(dt, [F(ts)])[F(ts)] for ts in ("10", "20", "40", "60")}
        fs[str(dt)] = row
    pj = CB.compare_E()
    return {"large_comparison": L, "total_mismatches": sum(v["mismatches"] for v in L.values()), "tuples": tuples,
            "substitute_ledger_semantics": ledger_note, "fixed_step": fs,
            "points_json": {"rows_compared": pj["rows_compared"], "mismatches": len(pj["mismatches"]),
                            "n_rows_in_file": len(json.load(open(os.path.join(CB.ROUTES, "E_resistor_energy", "results", "points.json"))))}}


def main():
    t0 = time.perf_counter()
    Aor = PR.load("A_waveform", "p0_oracle", "A_p0_oracle"); sys.modules["p0_oracle"] = Aor
    A = PR.load("A_waveform", "circuit_a", "A_circuit")
    Ej = PR.load("E_resistor_energy", "joule", "E_joule"); sys.modules["joule"] = Ej
    Ec = PR.load("E_resistor_energy", "circuit_e", "E_circuit"); sys.modules["circuit_e"] = Ec
    Eq = PR.load("E_resistor_energy", "quad_check", "E_quad"); sys.modules["quad_check"] = Eq
    pts = PR.point_set(20000, 3030)
    pa = CB.compare_A()
    res = {"A_fixes": a_fixes(A, Aor, pts),
           "A_points_json": {"rows_compared": pa["rows_compared"], "mismatches": len(pa["mismatches"]),
                             "n_rows_in_file": len(json.load(open(os.path.join(CB.ROUTES, "A_waveform", "results", "points.json")))["rows"]),
                             "by_case": pa["rows_by_case_realization_conv"]},
           "A_zero_mean_dispute": a_zero_mean(A), "A16_bound_dispute": a16_bound(),
           "E_rho_walsh": e_rho_and_walsh(), "E_checks": e_checks(Ec, Eq, pts)}
    res["seconds"] = round(time.perf_counter() - t0, 1)
    os.makedirs(OUT, exist_ok=True)
    json.dump(res, open(os.path.join(OUT, "p3_recheck.json"), "w"), indent=1, default=str)
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
