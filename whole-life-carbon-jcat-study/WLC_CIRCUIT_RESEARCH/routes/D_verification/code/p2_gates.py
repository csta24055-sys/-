"""Pass 2 gates X2 (B side) and X5.

X2: P0 recast in the ORIGINAL convention (architecture S1.2 right column). Route B's theta_eps kernel netlist
    (grammar.py, loaded as a probe) evaluated on the P0 pieces vs (a) D's pass-1 rational ledger oracle at the
    same float T (exact) and (b) route A's published orig-convention points (results/points.json, read as data).
    Includes the closed band endpoint 10/(1-eps): its float neighbours and the float switch point sw(10).
X5: on one 70-unit scenario, with canon.py + timechar.py (chapter 17, frozen; call conventions read from the
    source: canon.make_system(scn, population.BASELINES) -> canon.build(sysm) -> Canon; timechar.realtime(can)
    -> (masses, densities, Z terms); timechar.RT(masses, dens).M(T) counts atoms with sw(tau) <= T (closed
    [0,T], as 03 S7; timechar's docstring writes [0,T)); timechar.KF(Canon(H, terms)) is the knot form):
      C(T) - M([0,T]) = Z(T) != 0; dC/dT = rho + Z' with Z' != 0 (so dC/dT != rho) where B1 is included;
      C(0+) != A^init; an example with Z' < 0. Z is also rebuilt by D independently:
      Z_D(T) = A^term (msp constants of C1-01, C2-01, C3-01, C4-01, X-14) + B1-04 from D's raw recurrence.
Run: PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0 python3 -B code/p2_gates.py
"""
import importlib.util, json, math, os, sys
from fractions import Fraction as Fr
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import p2_common as C            # noqa: E402
import p2_oracle_kernels as K    # noqa: E402
import oracle_d as OD            # noqa: E402  (pass-1 rational ledger)


def load_b():
    p = os.path.join(C.RESEARCH, "routes", "B_formula_network", "code", "grammar.py")
    spec = importlib.util.spec_from_file_location("B_grammar", p)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def x2(B):
    H = 130
    pieces = K.p0_pieces(float(H))
    tstar = Fr(10) / (1 - OD.EPS)
    f0 = float(tstar)
    sw = B.switch_point(10.0)
    pts = {float(t): t for t in OD.CONTRACT_POINTS[1:] + OD.KNIFE_POINTS + ["10.00000001"]}
    extra = {math.nextafter(f0, -math.inf): "fl(10/(1-eps))-1ulp", f0: "fl(10/(1-eps))",
             math.nextafter(f0, math.inf): "fl(10/(1-eps))+1ulp", sw: "B.switch_point(10)",
             math.nextafter(sw, -math.inf): "sw(10)-1ulp"}
    Ts = sorted(set(pts) | set(extra))
    res, _, _ = B.eval_kernel(pieces, H, Ts, "clip")
    A = json.load(open(os.path.join(C.RESEARCH, "routes", "A_waveform", "results", "points.json")))["rows"]
    Aorig = {r["t"]: Fr(r["value"]) for r in A if r["case"] == "P0" and r["convention"] == "orig" and r["realization"] == "R1"}
    rows = []
    for T in Ts:
        b = res[T]["total"]
        d_exact_on_float = OD.G("P0", Fr(T), OD.ORIG)            # real-arithmetic rule at the float T
        lab = pts.get(T) or extra.get(T)
        a = Aorig.get(pts[T]) if T in pts else None
        rows.append({"T": repr(T), "label": lab, "B_theta_eps_kernel": b, "D_rational_orig_at_float_T": float(d_exact_on_float),
                     "abs_B_minus_D": abs(b - float(d_exact_on_float)),
                     "A_published_orig(decimal t)": (float(a) if a is not None else None),
                     "abs_B_minus_A": (abs(b - float(a)) if a is not None else None),
                     "event10_counted_B(float rule)": 10.0 < T * C.D, "event10_counted_real": Fr(T) > tstar})
    return {"rows": rows, "tstar_10/(1-eps)": str(tstar), "fl(tstar)": repr(f0), "sw(10)": repr(sw),
            "sw_minus_tstar_ulps": float((Fr(sw) - tstar) / Fr(math.ulp(f0))),
            "max_abs_B_minus_D_excluding_float_knife": max(r["abs_B_minus_D"] for r in rows
                                                           if r["label"] not in ("10.00000001",) and not r["label"].startswith(("fl(", "sw", "B.sw"))),
            "note": "B evaluates in float with the model's rule 10 < fl(T d); A/D use the real rule T > 10/(1-eps). They can differ "
                    "only on floats within ~2 ulp of 10/(1-eps) and at the float knife edge 10.00000001."}


def x5():
    canon, tc, population = C.canon_modules()
    tag, scn = C.d_scenarios(("EV6",))[0]
    sysm = canon.make_system(scn, population.BASELINES)
    can = canon.build(sysm)
    H = can.H
    kf = tc.KF(can)
    masses, dens, Zt = tc.realtime(can)
    rt = tc.RT(masses, dens)
    zkf = tc.KF(canon.Canon(H=H, terms=Zt))
    init_terms = [t for t in can.terms if t.kind == "const" and t.unit in tc.INITIAL_UNITS]
    A_init = sum((t.amp for t in init_terms), Fr(0))
    term_const = {u: sum((t.amp for t in can.terms if t.unit == u), Fr(0)) for u in ("C1-01", "C2-01", "C3-01", "C4-01", "X-14")}
    A_term = sum(term_const.values(), Fr(0))
    rows = []
    for T in (0.5, 5.3, 12.25, 30.5, 47.9):
        if C.in_domain(scn, T):
            continue
        Cv, Mv, Zv = kf(T), rt.M(Fr(T)), zkf(T)
        h = 1e-6
        Cs = (kf(T + h) - Cv) / (Fr(T + h) - Fr(T))
        Zs = (zkf(T + h) - Zv) / (Fr(T + h) - Fr(T))
        rho = rt.rho(Fr(T))
        ZD = A_term + Fr(K.refrigerant(scn.refrigerants, T)["B1-04"]) * (1 if "B1" in can.inc and can.inc["B1"] else 0)
        r = C.ref(scn, T)
        rows.append({"T": T, "C": float(Cv), "M([0,T])": float(Mv), "Z": float(Zv), "C-M==Z(exact)": Cv - Mv == Zv,
                     "Z!=0": Zv != 0, "dC/dT": float(Cs), "rho": float(rho), "Z'": float(Zs),
                     "dC/dT==rho+Z'(exact)": Cs == rho + Zs, "dC/dT!=rho": Cs != rho, "Z'<0": Zs < 0,
                     "Z_D_independent": float(ZD), "rel(Z_canon,Z_D)": C.rel(Zv, ZD),
                     "refcalc_SUM03": r["SUM-03"]["value"], "rel(C_canon,refcalc)": C.rel(Cv, r["SUM-03"]["value"]),
                     "rel(refcalc-Z_D, M_canon)": C.rel(Fr(r["SUM-03"]["value"]) - ZD, Mv)})
    # C(0+): C is affine on the first piece (0, first breakpoint): alpha = C(0+)
    a, b = 1e-7, 2e-7
    ca, cb = kf(a), kf(b)
    slope = (cb - ca) / (Fr(b) - Fr(a))
    C0 = ca - slope * Fr(a)
    Z0 = zkf(a) - ((zkf(b) - zkf(a)) / (Fr(b) - Fr(a))) * Fr(a)
    return {"scenario": scn.meta.scenario_id, "B1_included": bool(can.inc.get("B1")), "rows": rows,
            "C(0+)": float(C0), "A_init": float(A_init), "A_term": float(A_term), "R(0+)_part=Z(0+)-A_term": float(Z0 - A_term),
            "C(0+)==A_init+A_term+R(0+)(exact)": C0 == A_init + Z0, "C(0+)!=A_init": C0 != A_init,
            "n_masses": len(masses), "n_densities": len(dens), "n_terminal_terms": len(Zt),
            "convention_note": "RT.M counts atoms with switch point <= T (closed [0,T], 03 S7); timechar docstring line 11 says M([0, T))"}


def main():
    C.frozen()
    B = load_b()
    res = {"X2": x2(B), "X5": x5()}
    assert C.clean() == []
    C.dump("p2_gates.json", res)
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
