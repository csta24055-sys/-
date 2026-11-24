"""Pass 4: independent re-verification of the G4 integration (integration/code) and of the B/C fix passes.
Integration modules are loaded read-only as PROBES (importlib, bytecode off); D's oracles stay oracle_d (Phi)
and p2_check_c.Evaluator / p2_oracle_kernels (Psi). Writes only routes/D_verification/results/.

Declared P1' semantics used by D (for renovation at a time tau_R that is NOT a scheduled replacement instant):
  the renovation incurs A_R=50 at tau_R and replaces BOTH items at tau_R, i.e. both replacement cycles restart
  from tau_R (next AC at tau_R+10k, next pipe at tau_R+20k). 'substitute' removes only individual replacement
  charges that fall at the SAME instant as the renovation (none when tau_R is non-coincident), so off-coincidence
  substitute == additional; replacements that were scheduled later but are pre-empted by the restart are never
  charged under either policy.
Run: PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0 math7-py -B code/p4_integration.py
"""
import ast, bisect, copy, importlib.util, json, math, os, random, statistics, sys, time
from fractions import Fraction as F
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import oracle_d as O               # noqa: E402
import probe_routes as PR          # noqa: E402
import p2_common as C2             # noqa: E402
import p2_check_c as PC            # noqa: E402
import bench as BE                 # noqa: E402

INTEG = os.path.join(C2.RESEARCH, "integration", "code")
OUT = os.path.join(HERE, "..", "results")


def load_integ(name):
    if INTEG not in sys.path:
        sys.path.insert(0, INTEG)          # integration modules import int_common by bare name
    spec = importlib.util.spec_from_file_location("INT_" + name, os.path.join(INTEG, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    sys.modules["INT_" + name] = m          # dataclasses need the module registered before execution
    spec.loader.exec_module(m)
    return m


def imports_of(path):
    tree = ast.parse(open(path).read())
    mods = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            mods |= {a.name for a in n.names}
        elif isinstance(n, ast.ImportFrom):
            mods.add(n.module or "")
    return sorted(mods)


# ------------------------------------------------------------------ 1. Phi
def phi(PH):
    cases = [("P0", None, {}), ("P2", None, {})]
    for tr in (F(20), F(13), F(27)):
        for pol in ("substitute", "additional"):
            cases.append(("P1", pol, {"tau_R": tr}))
    for te in (F(3), F(13), F(47, 2)):
        cases.append(("Px", None, {"t_early": te}))
    base = PR.point_set(3000, 5151)
    reals = [("charge", {}), ("charge", {"gamma": F(3, 7), "C_cap": F(5)}), ("joule", {}), ("joule", {"R": F(5), "kappa": F(2, 7)})]
    rows, total_mm, n_cmp = [], 0, 0
    d = F(1, 10**12)
    for case, pol, kw in cases:
        ev, _ = O.ledger(case, pol or "substitute", **kw)
        evt = sorted({e.time for e in ev if e.time <= 60})
        for conv in (("right", "left", "orig") if case in ("P0", "P1") else ("right", "left")):
            pts = set(base)
            for tau in evt:
                pts |= {tau - d, tau, tau + d}
                if conv == "orig":
                    b = tau / (1 - O.EPS)
                    pts |= {b, b - F(1, 10**15), b + F(1, 10**15)}
            pts = sorted(p for p in pts if 0 <= p <= 62)
            exp = [O.G(case, t, conv, pol or "substitute", **kw) for t in pts]
            for rname, rkw in reals:
                h = PH.Hybrid(PH.pilot(case, pol, **kw), conv, rname, **rkw)
                got = h.run(pts)
                mm = [(str(t), str(got[t]), str(e)) for t, e in zip(pts, exp) if got[t] != e]
                total_mm += len(mm); n_cmp += len(pts)
                rows.append({"case": case, "policy": pol, "kw": {k: str(v) for k, v in kw.items()}, "conv": conv,
                             "realization": rname + (str(rkw) if rkw else ""), "n": len(pts), "mismatches": len(mm), "ex": mm[:3]})
    # explicit hand values for P1' at 13 and 27 (D's declared semantics)
    hand = {("P1", "substitute", 13, 40): 100 + 160 + 20 + 50 + 20 + 20 + 35,      # AC 10, R 13, AC 23, 33, pipe 33
            ("P1", "additional", 27, 40): 100 + 160 + 20 + 20 + 35 + 50 + 20,      # AC 10, 20, pipe 20, R 27, AC 37
            ("P1", "substitute", 27, 60): 100 + 240 + 20 + 20 + 35 + 50 + 20 + 20 + 20 + 35}   # +AC 37,47,57, pipe 47
    hv = {f"{c}-{p}-tauR{tr}@{t}": {"hand": v, "D": str(O.G(c, t, "right", p, tau_R=F(tr))),
                                     "integration": str(PH.G(c, F(t), "right", p, tau_R=F(tr)))}
          for (c, p, tr, t), v in hand.items()}
    return {"n_case_conv_realization": len(rows), "points_compared": n_cmp, "total_mismatches": total_mm, "rows": rows,
            "hand_values_P1prime": hv}


# ------------------------------------------------------------------ 2. Psi
def psi(PS, IC):
    canon, tc, pop = C2.canon_modules()
    m = C2.frozen()
    ev = m["scenarios"].evaluation_set(12)
    scen = []
    for tag, idx in (("EV0", 0), ("EV7", 7)):
        scen.append((tag, ev[idx]))
    s = copy.deepcopy(ev[7]); s.boundary.included_lifecycle_stages = [x for x in s.boundary.included_lifecycle_stages if x != "B2"]
    s.meta.scenario_id += "-noB2"; scen.append(("EV7-noB2", s))
    s = copy.deepcopy(ev[0]); s.boundary.included_lifecycle_stages = ["A1-A3", "B1", "B2", "B6", "C1", "C3"]
    s.meta.scenario_id += "-subset"; scen.append(("EV0-subset", s))
    rows = PC.comp_rows_json()
    direct = sorted({u for _, u, _, _ in rows})
    out = []
    for tag, scn in scen:
        sy = m["unified"].System(scn)
        base_T = [0.5, 3.7, 9.99999, 10.00001, 12.25, 19.99999, 20.00001, 30.5, 47.9, 59.99999, 75.5]
        gates = sorted({p.gate for ps in sy.pieces.values() for p in ps if p.gate != -math.inf and 1 < p.gate < 90})
        near = []
        for g in gates[:: max(1, len(gates) // 4)][:4]:
            for f in (1 - 3e-8, 1 + 3e-8):
                near.append(g * f)
        Ts, skipped = [], []
        for T in sorted(set(base_T + near)):
            (skipped if C2.domain_violations(scn, T) else Ts).append(T)
        pc = PS.PsiComposed(scn)
        comp = pc.sweep(Ts)
        evd = PC.Evaluator(scn, canon, pop)
        worst = {"integ_total_vs_refcalc": 0.0, "integ_stage_vs_refcalc": 0.0, "integ_unit_vs_refcalc": 0.0,
                 "D_total_vs_refcalc": 0.0, "integ_vs_D_total": 0.0}
        c1n = []
        for T in Ts:
            r = C2.ref(scn, T)
            stage, tot, V = evd.compose(T, rows)
            c = comp[T]
            worst["integ_total_vs_refcalc"] = max(worst["integ_total_vs_refcalc"], C2.rel(c["total"], r["SUM-03"]["value"]))
            worst["integ_stage_vs_refcalc"] = max([worst["integ_stage_vs_refcalc"]] + [C2.rel(c["stages"].get(k, 0.0), v) for k, v in r["X-02"]["by_stage"].items()])
            worst["integ_unit_vs_refcalc"] = max([worst["integ_unit_vs_refcalc"]] + [C2.rel(c["units"][u], r[u]["value"]) for u in direct])
            worst["D_total_vs_refcalc"] = max(worst["D_total_vs_refcalc"], C2.rel(tot, r["SUM-03"]["value"]))
            worst["integ_vs_D_total"] = max(worst["integ_vs_D_total"], C2.rel(c["total"], tot))
            if len(scn.boundary.included_lifecycle_stages) == 14:
                naive = math.fsum(r[u]["value"] for u in direct)
                S3 = r["SUM-03"]["value"]
                c1n.append({"T": T, "rel_err_naive": C2.rel(naive, S3), "rel(naive-SUM03, B2-01)": C2.rel(naive - S3, r["B2-01"]["value"]),
                            "B2-01/SUM03": r["B2-01"]["value"] / S3})
        out.append({"tag": tag, "scenario": scn.meta.scenario_id, "stages": len(scn.boundary.included_lifecycle_stages),
                    "n_T": len(Ts), "T_skipped_outside_domain": skipped, "near_event_T_used": [t for t in near if t in Ts],
                    "worst": worst, "stage_keys_equal": None,
                    "C1n": ({"min_rel_err": min(x["rel_err_naive"] for x in c1n), "max_rel_err": max(x["rel_err_naive"] for x in c1n),
                             "max rel(naive-C, B2-01)": max(x["rel(naive-SUM03, B2-01)"] for x in c1n)} if c1n else None),
                    "refrigerant_unexpected": pc.netcounts["refrigerant"]["unexpected"]})
    return out


# ------------------------------------------------------------------ 3. X5 on EV7 (steps crossing no jump), X2 link
def x5(tag_idx=7):
    canon, tc, pop = C2.canon_modules()
    m = C2.frozen()
    scn = m["scenarios"].evaluation_set(12)[tag_idx]
    sysm = canon.make_system(scn, pop.BASELINES)
    can = canon.build(sysm)
    kf = tc.KF(can)
    masses, dens, Zt = tc.realtime(can)
    rt = tc.RT(masses, dens)
    zkf = tc.KF(canon.Canon(H=can.H, terms=Zt))
    bps = sorted({float(k[0]) for k in kf.knots()} | {float(k[0]) for k in zkf.knots()} | {float(x) for x in rt.mt} | {float(x) for x in rt.dt})
    A_init = sum((t.amp for t in can.terms if t.kind == "const" and t.unit in tc.INITIAL_UNITS), F(0))
    rows = []
    for T in (2.3, 7.7, 15.5, 33.3, 41.7, 58.2):
        if C2.domain_violations(scn, T):
            rows.append({"T": T, "skipped": "domain"}); continue
        i = bisect.bisect_right(bps, T)
        nxt = bps[i] if i < len(bps) else math.inf
        at_bp = T in bps
        h = min(1e-6, (nxt - T) / 2)
        T2 = T + h
        Cv, Mv, Zv = kf(T), rt.M(F(T)), zkf(T)
        Cs = (kf(T2) - Cv) / (F(T2) - F(T)); Zs = (zkf(T2) - Zv) / (F(T2) - F(T)); rho = rt.rho(F(T))
        rows.append({"T": T, "h": h, "next_breakpoint": nxt, "T_is_breakpoint": at_bp, "C-M==Z": Cv - Mv == Zv, "Z": float(Zv),
                     "Z!=0": Zv != 0, "dC/dT==rho+Z'": Cs == rho + Zs, "dC/dT!=rho": Cs != rho, "Z'": float(Zs), "Z'<0": Zs < 0,
                     "rel(C,refcalc)": C2.rel(Cv, C2.ref(scn, T)["SUM-03"]["value"])})
    a, b = 1e-7, 2e-7
    C0 = kf(a) - ((kf(b) - kf(a)) / (F(b) - F(a))) * F(a)
    return {"scenario": scn.meta.scenario_id, "B1_included": bool(can.inc.get("B1")), "rows": rows,
            "C(0+)": float(C0), "A_init": float(A_init), "C(0+)!=A_init": C0 != A_init, "n_breakpoints": len(bps)}


def x2_link(PH):
    g = json.load(open(os.path.join(OUT, "p2_gates.json")))["X2"]["rows"]
    rows = []
    for r in g:
        T = float(r["T"])
        h = PH.G("P0", F(T), "orig")
        rows.append({"T": r["T"], "integration_orig_exact": float(h), "D_rational": r["D_rational_orig_at_float_T"],
                     "B_netlist": r["B_theta_eps_kernel"], "equal_D": float(h) == r["D_rational_orig_at_float_T"],
                     "abs_vs_B": abs(float(h) - r["B_theta_eps_kernel"])})
    return {"rows": rows, "all_equal_D": all(x["equal_D"] for x in rows), "max_abs_vs_B": max(x["abs_vs_B"] for x in rows)}


# ------------------------------------------------------------------ 4. benchmark order of magnitude
def bench(PH, PS):
    pts = BE.points()[:20011]
    def med(f, n=3):
        ts = []
        for _ in range(n):
            t0 = time.perf_counter(); f(); ts.append(time.perf_counter() - t0)
        return statistics.median(ts)
    t_h = med(lambda: PH.Hybrid(PH.pilot("P0"), "right", "charge").run(pts))
    t_b = med(lambda: [BE.b_frac(t) for t in pts])
    canon, tc, pop = C2.canon_modules()
    m = C2.frozen()
    scn = m["scenarios"].evaluation_set(12)[9]
    rng = random.Random(77)
    Ts = sorted(round(rng.uniform(0.01, 60.0), 6) for _ in range(200))
    Ts = [T for T in Ts if not C2.domain_violations(scn, T)]
    t_p = med(lambda: PS.PsiComposed(scn).sweep(Ts), 1)
    kf = tc.KF(canon.build(canon.make_system(scn, pop.BASELINES)))
    t_k = med(lambda: [kf(T) for T in Ts])
    return {"phi_hybrid_sweep_us_per_pt": t_h / len(pts) * 1e6, "phi_knots_bisect_us_per_pt": t_b / len(pts) * 1e6,
            "phi_ratio": t_h / t_b, "psi_composed_ms_per_T": t_p / len(Ts) * 1e3, "psi_canonKF_ms_per_T": t_k / len(Ts) * 1e3,
            "psi_ratio": t_p / t_k, "n_T": len(Ts)}


# ------------------------------------------------------------------ 5. B/C fix passes (reading + small execution)
def bc_fixes():
    import csv
    R = os.path.join(C2.RESEARCH, "routes")
    out = {}
    hb4 = json.load(open(os.path.join(R, "B_formula_network", "results", "hb4_counts.json")))
    out["B_hb4_keys_with_merged"] = sorted({k for s in hb4.get("scenarios", {}).values() for fam in s.values() if isinstance(fam, dict)
                                            for k in fam if "merged" in k.lower()})[:10]
    out["B_hb4_merged_snippet"] = {sid: {fk: {k: v for k, v in fv.items() if "merged" in k.lower() or "random" in k.lower() or "ratio" in k.lower()}
                                         for fk, fv in s.items() if isinstance(fv, dict) and fk.startswith("refrigerant")}
                                   for sid, s in hb4.get("scenarios", {}).items()}
    src = open(os.path.join(R, "B_formula_network", "code", "hb2_passive.py")).read()
    out["B_hb2_has_ramp_column"] = ("T" in src and ("ramp" in src.lower()))
    hb2 = json.load(open(os.path.join(R, "B_formula_network", "results", "hb2_illustration.json")))
    out["B_hb2_results_keys"] = list(hb2.keys())
    out["B_hb2_jump_min_sup"] = min(r["sup_error"] for r in hb2["jump_atom"])
    out["B_hb2_kink_sup"] = [r["sup_error"] for r in hb2["kink_w0"]]
    rbe = open(os.path.join(R, "B_formula_network", "code", "route_b_experiments.py")).read()
    tg = open(os.path.join(R, "B_formula_network", "tests", "test_grammar.py")).read()
    out["B_band_wording_halfopen_left"] = [s for s in ("[tau, tau/(1-eps))", "[τ, τ/(1−ε))") if s in rbe or s in tg]
    bm = {r["kind_id"]: r for r in csv.DictReader(open(os.path.join(R, "B_formula_network", "MAPPING.csv"), encoding="utf-8"))}
    out["B_K19_tuple"] = bm["K19"]["state_tuple_per_instance"]
    out["B_K10_justification"] = bm["K10"]["justification"][:200]
    to = open(os.path.join(R, "B_formula_network", "tests", "test_oracle.py")).read()
    out["B_tests_mention_out_of_sample"] = ("OUT_OF_SAMPLE" in to or "EV3" in to or "out_of_sample" in to.lower())
    out["B_tests_assertAlmostEqual_or_rel1e-6"] = ("1e-6" in to)
    led = {u["id"]: u for u in json.load(open(os.path.join(C2.BASE, "data", "units70.json"), encoding="utf-8"))["units"]}
    cm = list(csv.DictReader(open(os.path.join(R, "C_70_units", "MAPPING.csv"), encoding="utf-8")))
    diff = [r["claim_or_unit_id"] for r in cm if r["time_form_text"] != (led[r["claim_or_unit_id"]].get("time_form") or "")]
    diff_ws = [r["claim_or_unit_id"] for r in cm if r["time_form_text"].split() != (led[r["claim_or_unit_id"]].get("time_form") or "").split()]
    out["C_rows"] = len(cm)
    out["C_time_form_text_exact_mismatch_rows"] = diff
    out["C_time_form_text_mismatch_ignoring_whitespace"] = diff_ws
    out["C_rows_with_[H]_construct_column"] = sum(1 for r in cm if "[H]" in r.get("construct_class_tuple_evidence", ""))
    cl = open(os.path.join(R, "C_70_units", "claims.md"), encoding="utf-8").read() + open(os.path.join(R, "C_70_units", "README.md"), encoding="utf-8").read()
    out["C_rank_caveat_present"] = ("minimal" in cl and "rank" in cl)
    return out


def main():
    C2.frozen()
    assert C2.clean() == []
    t0 = time.perf_counter()
    PH = load_integ("phi_hybrid")
    IC = load_integ("int_common")
    sys.modules["int_common"] = IC
    PS = load_integ("psi_compose")
    res = {"phi_hybrid_imports": imports_of(os.path.join(INTEG, "phi_hybrid.py")),
           "psi_compose_imports": imports_of(os.path.join(INTEG, "psi_compose.py")),
           "phi": phi(PH), "psi": psi(PS, IC), "x5_EV7": x5(7), "x2_link": x2_link(PH), "bench": bench(PH, PS),
           "bc_fixes": bc_fixes()}
    res["seconds"] = round(time.perf_counter() - t0, 1)
    assert C2.clean() == []
    os.makedirs(OUT, exist_ok=True)
    json.dump(res, open(os.path.join(OUT, "p4_integration.json"), "w"), indent=1, default=str, ensure_ascii=False)
    short = {k: v for k, v in res.items() if k != "phi"}
    short["phi"] = {k: v for k, v in res["phi"].items() if k != "rows"}
    print(json.dumps(short, indent=1, default=str, ensure_ascii=False))


if __name__ == "__main__":
    main()
