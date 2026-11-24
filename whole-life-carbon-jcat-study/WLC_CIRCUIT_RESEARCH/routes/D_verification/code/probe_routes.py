"""FALSIFICATION PROBES of route A/E code (NOT part of the oracle).

This is the only D module that loads route code, read-only, via importlib from file path,
with bytecode writing disabled. Its purpose is to (1) compare route realizations with the
independent oracle_d on a large random + adversarial point set and (2) drive route code on
inputs the routes did not test (latent defects outside their claimed domain).

Run: PYTHONDONTWRITEBYTECODE=1 math7-py -B code/probe_routes.py [n_right n_other]
"""
import importlib.util, json, math, os, random, sys, time
from fractions import Fraction as F
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import oracle_d as O  # noqa: E402

ROUTES = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(HERE, "..", "results")


def load(route, name, alias):
    path = os.path.join(ROUTES, route, "code", name + ".py")
    codedir = os.path.dirname(path)
    if codedir not in sys.path:
        sys.path.insert(0, codedir)      # route modules import siblings by bare name
    spec = importlib.util.spec_from_file_location(alias, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def point_set(n, seed):
    rng = random.Random(seed)
    pts = [F(t) for t in O.CONTRACT_POINTS + O.KNIFE_POINTS + ["10.00000001"]]
    d = F(1, 10**12)
    for tau in range(10, 61, 10):
        pts += [F(tau) - d, F(tau), F(tau) + d, F(tau) / (1 - O.EPS), F(tau) / (1 - O.EPS) + d]
    pts += [F(rng.randrange(0, 60 * 10**6 + 1), 10**6) for _ in range(n)]
    return pts


_EXP = {}


def expected(case, conv, pts, policy):
    k = (case, conv, policy, id(pts))
    if k not in _EXP:
        _EXP[k] = [O.G(case, t, conv, policy) for t in pts]
    return _EXP[k]


def compare(fn, case, conv, pts, policy="substitute"):
    bad = []
    exp = expected(case, conv, pts, policy)
    t0 = time.perf_counter()
    for t, e in zip(pts, exp):
        v = fn(t)
        if F(v) != e:
            bad.append({"t": str(t), "route": str(v), "D": str(e)})
            if len(bad) > 5:
                break
    return {"n": len(pts), "mismatches": len(bad), "examples": bad[:5], "seconds": round(time.perf_counter() - t0, 2)}


def main(n_right=100000, n_other=20000):
    A_or = load("A_waveform", "p0_oracle", "A_p0_oracle")
    sys.modules["p0_oracle"] = A_or
    A = load("A_waveform", "circuit_a", "A_circuit")
    Ej = load("E_resistor_energy", "joule", "E_joule")
    sys.modules["joule"] = Ej
    Ec = load("E_resistor_energy", "circuit_e", "E_circuit")
    sys.modules["circuit_e"] = Ec
    Eq = load("E_resistor_energy", "quad_check", "E_quad")
    sys.modules["quad_check"] = Eq
    Em = load("E_resistor_energy", "make_results", "E_make")

    res = {"large_random_comparison": {}, "latent_probes": {}}
    big = point_set(n_right, 20261124)
    small = point_set(n_other, 777)
    L = res["large_random_comparison"]
    for conv, pts in ((O.RIGHT, big), (O.LEFT, small), (O.ORIG, small)):
        L[f"A.R1|{conv}"] = compare(A.p0_r1(conv).G, "P0", conv, pts)
        L[f"A.R2|{conv}"] = compare(A.p0_r2(conv).G, "P0", conv, pts)
        L[f"A.R3|{conv}"] = compare(A.R3(conv).G, "P0", conv, pts)
        L[f"A.oracle|{conv}"] = compare(lambda t, c=conv: A_or.g_p0(t, c), "P0", conv, pts)
        L[f"E.ER1|{conv}"] = compare(lambda t, c=conv: Ec.g_er1(t, c), "P0", conv, pts)
        if conv != O.ORIG:
            L[f"A.R3k|{conv}"] = compare(A.R3k(conv).G, "P0", conv, pts)
            L[f"A.R3i_P0|{conv}"] = compare(A.R3i([(F(1, 2), 20), (1, 55)], conv=conv).G, "P0", conv, pts)
            L[f"A.R3i_Px|{conv}"] = compare(A.R3i([(F(7, 20), 20), (F(17, 20), 20), (1, 35)], conv=conv).G, "Px", conv, small)
            L[f"A.px_r1|{conv}"] = compare(A.px_r1(conv).G, "Px", conv, small)
            L[f"A.p2_r1|{conv}"] = compare(A.p2_r1(conv).G, "P2", conv, small)
            for pol in ("substitute", "additional"):
                L[f"A.p1_r1_{pol}|{conv}"] = compare(A.p1_r1(pol, conv).G, "P1", conv, small, pol)
    L["E.ER1_P2_efswitch|right"] = compare(lambda t: Ec.g_er1(t, "right", True), "P2", O.RIGHT, small)
    L["E.ER1_P2_efswitch|left"] = compare(lambda t: Ec.g_er1(t, "left", True), "P2", O.LEFT, small)

    P = res["latent_probes"]
    # 1. R3i silently accepts conv='orig' but ignores eps (left semantics with full clock rate)
    r3i = A.R3i([(F(1, 2), 20), (1, 55)], conv=O.ORIG)
    t = F("10.000000005")
    P["A.R3i(conv=orig) at 10.000000005"] = {"route": str(r3i.G(t)), "D_orig": str(O.G("P0", t, O.ORIG)),
                                             "D_left": str(O.G("P0", t, O.LEFT))}
    # 2. P1 under orig: R1 fires the renovation ExtEvent at physical 20 (not slowed) and resets the
    #    slowed clocks before they reach threshold -> differs from A's own g_p1(orig) and from D
    p1o = {}
    for pol in ("substitute", "additional"):
        for ts in ("20.00000001", "20.00000003", "30", "40", "60"):
            tt = F(ts)
            p1o[f"{pol}@{ts}"] = {"A.R1": str(A.p1_r1(pol, O.ORIG).G(tt)), "A.g_p1": str(A_or.g_p1(tt, O.ORIG, pol)),
                                  "E.J.p1": str(Ej.p1(ts, pol, "orig")), "D": str(O.G("P1", tt, O.ORIG, pol))}
    P["P1_under_orig_convention"] = p1o
    # 3. renovation at a non-coincident time 15 (restart semantics)
    ren15 = {}
    for pol in ("substitute", "additional"):
        c = A.R1([A.Clock("A", 10, 20), A.Clock("P", 20, 35)],
                 ext=[A.ExtEvent(15, 50, resets=("A", "P"), replaces=("A", "P"), kind="renovation")], policy=pol)
        for ts in ("15", "20", "25", "35", "55", "60"):
            ren15[f"{pol}@{ts}"] = {"A.R1": str(c.G(F(ts))), "D": str(O.G("P1", F(ts), O.RIGHT, pol, tau_R=F(15)))}
    P["renovation_at_15_restart"] = ren15
    # 4. order invariance of A's set rule: reverse clock list and duplicate ext order
    rev = A.R1([A.Clock("P", 20, 35), A.Clock("A", 10, 20)],
               ext=[A.ExtEvent(20, 50, resets=("A", "P"), replaces=("A", "P"), kind="renovation")], policy="substitute")
    P["A.R1 set-rule with reversed clock list, G(20),G(40)"] = [str(rev.G(20)), str(rev.G(40))]
    # 5. naive sequential orders
    import itertools
    P["A.R1 naive sequential G(20)"] = {"-".join(o): str(A.p1_r1("additional", O.RIGHT, sequential_order=list(o)).G(20))
                                        for o in itertools.permutations(["renovation", "A", "P"])}
    # 6. E fixed-step integrator at contract points (E benchmark only sampled random points)
    fs = {}
    for ts in O.CONTRACT_POINTS:
        v = Em.fixed_step(float(ts))
        fs[ts] = {"E.fixed_step(dt=1e-3)": repr(v), "D_right": float(O.G("P0", F(ts))), "abs_err": abs(v - float(O.G("P0", F(ts))))}
    P["E.fixed_step_contract_points"] = fs
    # 7. A's float closed form at contract/knife points
    P["A.g_p0_float"] = {f"{ts}|{c}": {"float": repr(A_or.g_p0_float(float(ts), c)), "exact": float(O.G("P0", F(ts), c))}
                         for ts in O.CONTRACT_POINTS + O.KNIFE_POINTS + ["10.00000001"] for c in O.CONVENTIONS
                         if A_or.g_p0_float(float(ts), c) != float(O.G("P0", F(ts), c))}
    # 8. A's zero-mean AC 'clock' does not integrate anything
    try:
        v = A.ac_clock_count(60, 0.1, 2 * math.pi, "zero")
        P["A.ac_clock_count(zero, c=0.1)"] = v
    except AssertionError as e:
        P["A.ac_clock_count(zero, c=0.1)"] = "AssertionError: function cannot simulate a threshold below the swing; it returns 0 by construction otherwise"
    # 9. A's single_clock_fit only tests (G(10),G(20)); D's general argument covers all c
    P["A.single_clock_fit(10)"] = str(A.single_clock_fit(F(10)))
    P["A.single_clock_fit(20)"] = str(A.single_clock_fit(F(20)))
    os.makedirs(OUT, exist_ok=True)
    json.dump(res, open(os.path.join(OUT, "probe_routes.json"), "w"), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    a = [int(x) for x in sys.argv[1:3]]
    main(*a)
