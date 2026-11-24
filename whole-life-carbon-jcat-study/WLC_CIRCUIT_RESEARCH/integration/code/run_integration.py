"""G4 integration checks of the composed model against oracles that are NOT the composed code.

  phi_check   Phi hybrid (both realizations) vs route D's rational event-ledger oracle (oracle_d.G), exact
              Fraction equality, P0/P1(both policies)/P1' (renovation at 15)/P2/Px x declared conventions;
              plus route A's published oracle rows (points.json, read as data).
  x2_link     Phi hybrid under 'orig' (horizon readout) vs route B's theta_eps kernel netlist on the P0 pieces
              (re-executes gate X2 through the composed code; float comparison at the same float T).
  psi_check   Psi composition (B netlists + C summing rule from units70.json) vs refcalc SUM-03, X-02 by_stage
              and the 21 DIRECT unit values, on evaluation_set EV2 and EV9 (unused by every route) and EV9
              without B2 (beta = iota_B2 exercised).
  x5_bridge   C(T) - M([0,T]) = Z(T) with canon/timechar (frozen ch.17 code, exact Fractions) on EV9, and the
              composed float C(T) placed in that identity.

Run: PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0 python3 -B code/run_integration.py
"""
from __future__ import annotations

import json
import math
import random
import sys
import time
from fractions import Fraction as F

import int_common as IC
import phi_hybrid as PH
import psi_compose as PS

CONTRACT = ["0", "1", "9.999999", "10", "10.000001", "19.999999", "20", "20.000001", "30", "40", "60"]
KNIFE = ["10.000000005", "10.00000002"]
EVENT_TIMES = [10, 15, 17, 20, 25, 27, 30, 35, 40, 60, 7]


def phi_points(n_random: int, seed: int = 20261124) -> list:
    rng = random.Random(seed)
    pts = {F(s) for s in CONTRACT + KNIFE}
    d = F(1, 10**12)
    for tau in EVENT_TIMES:
        for base in (F(tau), F(tau) / (1 - PH.EPS)):
            pts |= {base, base - d, base + d, base - F(1, 10**15), base + F(1, 10**15)}
    pts |= {F(rng.randrange(0, 60 * 10**6), 10**6) for _ in range(n_random)}
    return sorted(p for p in pts if p >= 0)


PHI_CASES = [("P0", None, {}, ("right", "left", "orig")),
             ("P1", "substitute", {}, ("right", "left", "orig")),
             ("P1", "additional", {}, ("right", "left", "orig")),
             ("P1", "substitute", {"tau_R": F(15)}, ("right", "left", "orig")),
             ("P1", "additional", {"tau_R": F(15)}, ("right", "left", "orig")),
             ("P2", None, {}, ("right", "left")),
             ("Px", None, {}, ("right", "left"))]


def phi_check(n_random: int = 2000) -> dict:
    OD = IC.route_d_oracle()
    pts = phi_points(n_random)
    rows, mism = [], []
    for case, pol, kw, convs in PHI_CASES:
        tag = case + (f"-{pol}" if pol else "") + ("'(tau_R=15)" if kw else "")
        for conv in convs:
            vals = {}
            for real in PH.REALIZATIONS:
                h = PH.Hybrid(PH.pilot(case, pol, **kw), conv, real)
                vals[real] = h.run(pts)
                st = h.state_tuple()
                ops = dict(h.ops)
            n_bad = 0
            for t in pts:
                ref = OD.G(case, t, conv, pol or "substitute", **kw)
                for real in PH.REALIZATIONS:
                    if vals[real][t] != ref:
                        n_bad += 1
                        if len(mism) < 20:
                            mism.append({"case": tag, "conv": conv, "real": real, "t": str(t),
                                         "got": str(vals[real][t]), "oracle": str(ref)})
            rows.append({"case": tag, "conv": conv, "n_points": len(pts), "n_mismatch_both_realizations": n_bad,
                         "state_tuple_charge": PH.Hybrid(PH.pilot(case, pol, **kw), conv, "charge").state_tuple(),
                         "state_tuple_joule": st, "ops_last_sweep_joule": ops})
    # orig undefined for P2/Px: must raise
    rejects = {}
    for case in ("P2", "Px"):
        try:
            PH.Hybrid(PH.pilot(case), "orig")
            rejects[case] = "ACCEPTED (defect)"
        except ValueError:
            rejects[case] = "raises ValueError"
    # route A's published oracle rows (data only)
    with open(IC.A_POINTS, encoding="utf-8") as fh:
        A = json.load(fh)["rows"]
    amap = {"P0": ("P0", None), "P1-substitute": ("P1", "substitute"), "P1-additional": ("P1", "additional"),
            "P2": ("P2", None), "Px": ("Px", None)}
    a_cmp = {"n": 0, "mismatch": 0, "examples": []}
    for r in A:
        if r["case"] not in amap or "float" in r["t"]:
            continue
        try:
            t = F(r["t"])
        except (ValueError, ZeroDivisionError):
            continue
        case, pol = amap[r["case"]]
        if r["convention"] == "orig" and case in ("P2", "Px"):
            continue
        g = PH.G(case, t, r["convention"], pol)
        a_cmp["n"] += 1
        if g != F(r["value"]):
            a_cmp["mismatch"] += 1
            if len(a_cmp["examples"]) < 5:
                a_cmp["examples"].append({**r, "integration": str(g)})
    # gamma / C_cap invariance and the capacitor-energy separation (A-7), joule sanity (07: 3 ohm, 2 A, 5 s -> 60 J)
    inv = {}
    for g, c in ((1, 1), (5, 2), (F(1, 7), 3)):
        h = PH.Hybrid(PH.pilot("P0"), "right", "charge", gamma=g, C_cap=c)
        G40 = h.G(40)
        inv[f"gamma={g},C={c}"] = {"G(40)": str(G40), "V": str(h.capacitor_view()[0]), "E_cap": str(h.capacitor_view()[1])}
    joule_60J = F(3) * F(2) ** 2 * 5
    # permutation of simultaneous-event ordering: the set rule is order-free by construction; also check by
    # permuting the clock dict order and the external list order
    perm = set()
    for order in (("AC", "PIPE"), ("PIPE", "AC")):
        sp = PH.pilot("P1", "additional")
        sp.clocks = {k: sp.clocks[k] for k in order}
        for real in PH.REALIZATIONS:
            perm.add(PH.Hybrid(sp, "right", real).G(20))
    return {"points": len(pts), "cases": rows, "mismatches": mism, "orig_rejection": rejects,
            "A_points_rows_compared": a_cmp, "gamma_Ccap_invariance": inv, "joule_3ohm_2A_5s_J": str(joule_60J),
            "P1_additional_G20_over_orderings": sorted(str(x) for x in perm),
            "total_mismatch": sum(r["n_mismatch_both_realizations"] for r in rows)}


def x2_link() -> dict:
    B = IC.route_b_grammar()
    H = 130
    from collections import namedtuple
    P = namedtuple("Piece", "amp start length gate")
    pieces = [P(100.0, 0.0, 0.0, B.NEG_INF), P(4.0 * H, 0.0, float(H), B.NEG_INF)]
    for c, a in ((10.0, 20.0), (20.0, 35.0)):
        n = 1
        while n * c < H * B.D:
            pieces.append(P(a, n * c, 0.0, n * c))
            n += 1
    Ts = [float(s) for s in CONTRACT[1:] + KNIFE + ["10.00000001", "47.9", "59.5"]]
    f10 = float(F(10) / (1 - PH.EPS))
    Ts += [math.nextafter(f10, -math.inf), f10, math.nextafter(f10, math.inf), B.switch_point(10.0)]
    Ts = sorted(set(Ts))
    res, _, _ = B.eval_kernel(pieces, H, Ts, "clip")
    h = PH.Hybrid(PH.pilot("P0"), "orig", "charge")
    exact = h.run([F(T) for T in Ts])
    rows = []
    for T in Ts:
        b, p = res[T]["total"], exact[F(T)]
        rows.append({"T": repr(T), "B_theta_eps_netlist(float)": b, "Phi_hybrid_orig(exact at float T)": str(p),
                     "rel": IC.rel(b, p)})
    return {"rows": rows, "max_rel": max(r["rel"] for r in rows),
            "note": "same float T on both sides; B applies the model's float rule tau < fl(T*(1-eps)), the hybrid the real "
                    "rule. They may differ only within ~1 ulp of tau/(1-eps); observed max_rel above."}


PSI_T = [0.5, 1.0, 5.3, 9.999999, 10.0, 10.000001, 12.25, 19.999999, 20.0, 20.000001, 29.5, 30.0, 33.3, 47.9, 60.0,
         75.5, 99.0, 129.5]
DIRECT = None


def psi_check(tags=("EV2", "EV9", "EV9-noB2"), Ts=PSI_T, cell_mode="clip") -> dict:
    out = {"cases": [], "tol_rel": 1e-9}
    for tag in tags:
        scn = IC.psi_scenario(tag)
        ok_T = [T for T in Ts if not IC.domain_violations(scn, T)]
        skipped = [T for T in Ts if T not in ok_T]
        t0 = time.perf_counter()
        pc = PS.PsiComposed(scn, cell_mode)
        res = pc.sweep(ok_T)
        t_comp = time.perf_counter() - t0
        t0 = time.perf_counter()
        ref = {T: IC.refcalc_at(scn, T) for T in ok_T}
        t_ref = time.perf_counter() - t0
        worst = {"total": 0.0, "stage": 0.0, "unit": 0.0}
        worst_unit = None
        stage_keys_equal = True
        n_cmp = 0
        naive = {"max_rel_err_vs_SUM03": 0.0, "min_rel_err_vs_SUM03": math.inf, "max_rel(naive-C, B2-01)": 0.0}
        both = {"B2", "B6"} <= pc.inc
        for T in ok_T:
            r = ref[T]
            # control (route C claim C-1n, NOT_RUN by D): 21 DIRECT units as 21 independent +1 sources
            nv = math.fsum(res[T]["units"][u] for u in pc.comp_units)
            e = IC.rel(nv, r["SUM-03"]["value"])
            naive["max_rel_err_vs_SUM03"] = max(naive["max_rel_err_vs_SUM03"], e)
            naive["min_rel_err_vs_SUM03"] = min(naive["min_rel_err_vs_SUM03"], e)
            if both and len(pc.inc) == 14:
                naive["max_rel(naive-C, B2-01)"] = max(naive["max_rel(naive-C, B2-01)"],
                                                       IC.rel(nv - res[T]["total"], res[T]["units"]["B2-01"]))
            worst["total"] = max(worst["total"], IC.rel(res[T]["total"], r["SUM-03"]["value"]))
            n_cmp += 1
            bs = r["X-02"]["by_stage"]
            if set(bs) != set(res[T]["stages"]):
                stage_keys_equal = False
            for s, v in res[T]["stages"].items():
                worst["stage"] = max(worst["stage"], IC.rel(v, bs.get(s, math.nan)))
                n_cmp += 1
            for u in sorted(pc.comp_units):
                e = IC.rel(res[T]["units"][u], r[u]["value"])
                n_cmp += 1
                if e > worst["unit"]:
                    worst["unit"], worst_unit = e, (u, T)
        out["cases"].append({"scenario": tag, "scenario_id": scn.meta.scenario_id, "T_used": ok_T, "T_skipped_domain": skipped,
                             "included_stages": sorted(pc.inc), "n_comp_rows": len(pc.rows), "n_direct_units": len(pc.comp_units),
                             "n_comparisons": n_cmp, "max_rel": worst, "worst_unit": worst_unit,
                             "control_naive_21_sources": naive if len(pc.inc) == 14 else "not applicable (stage subset)",
                             "stage_keys_equal_refcalc": stage_keys_equal, "cell_mode": cell_mode,
                             "seconds_composed_sweep": t_comp, "seconds_refcalc_all_T": t_ref,
                             "refrigerant_state_tuple": pc.netcounts["refrigerant"]["state_tuple"],
                             "refrigerant_unexpected": pc.netcounts["refrigerant"]["unexpected"],
                             "C_values": {repr(T): res[T]["total"] for T in ok_T}})
    out["max_rel_overall"] = max(max(c["max_rel"].values()) for c in out["cases"])
    return out


def x5_bridge(tag="EV9", Ts=(0.5, 5.3, 12.25, 29.5, 47.9)) -> dict:
    canon, tc, population = IC.canon_modules()
    scn = IC.psi_scenario(tag)
    sysm = canon.make_system(scn, population.BASELINES)
    can = canon.build(sysm)
    kf = tc.KF(can)
    masses, dens, Zt = tc.realtime(can)
    rt = tc.RT(masses, dens)
    zkf = tc.KF(canon.Canon(H=can.H, terms=Zt))
    Ts = [T for T in Ts if not IC.domain_violations(scn, T)]
    comp = PS.PsiComposed(scn).sweep(Ts)
    rows = []
    for T in Ts:
        Cv, Mv, Zv = kf(T), rt.M(F(T)), zkf(T)
        rho = rt.rho(F(T))
        # one-sided difference on ONE affine piece: pick the largest h whose interval (T, T+h] holds no atom of M
        # (M(T+h) - M(T) == rho*h). At EV9, T=47.9 an atom lies in (47.9, 47.9+1e-6], so h=1e-6 would straddle a jump.
        h_used = None
        for h in (F(1, 10**6), F(1, 10**8), F(1, 10**10), F(1, 10**12)):
            if rt.M(F(T) + h) - Mv == rho * h:
                h_used = h
                break
        if h_used is None:
            raise RuntimeError(f"no atom-free step found at T={T}")
        dC = (kf(F(T) + h_used) - Cv) / h_used
        dZ = (zkf(F(T) + h_used) - Zv) / h_used
        Cc = comp[T]["total"]
        rows.append({"T": T, "C_canon": float(Cv), "M([0,T])": float(Mv), "Z(T)": float(Zv),
                     "C-M==Z (exact)": Cv - Mv == Zv, "Z!=0": Zv != 0,
                     "h_used": str(h_used),
                     "dC/dT==rho+Z' (exact, forward difference on one affine piece)": dC == rho + dZ,
                     "dC/dT!=rho": dC != rho, "Z'": float(dZ),
                     "C_composed(float)": Cc, "rel(C_composed, C_canon)": IC.rel(Cc, Cv),
                     "rel(C_composed - M, Z)": IC.rel(F(Cc) - Mv, Zv)})
    return {"scenario": tag, "scenario_id": scn.meta.scenario_id, "B1_included": bool(can.inc.get("B1")),
            "rows": rows, "n_masses": len(masses), "n_densities": len(dens), "n_terminal_terms": len(Zt),
            "note": "Psi identity on the 70-unit model; it does NOT relate the Phi pilot P0 to this scenario."}


def main(argv=None):
    t0 = time.perf_counter()
    fz = IC.frozen()
    res = {}
    res["phi"] = phi_check(2000)
    print("phi total mismatches:", res["phi"]["total_mismatch"], "points", res["phi"]["points"])
    res["x2_link"] = x2_link()
    print("x2 link max rel:", res["x2_link"]["max_rel"])
    res["psi"] = psi_check()
    print("psi max rel:", res["psi"]["max_rel_overall"])
    res["psi_integrator_cells_EV9"] = psi_check(("EV9",), PSI_T, "integrator")
    print("psi (integrator cells) max rel:", res["psi_integrator_cells_EV9"]["max_rel_overall"])
    res["x5"] = x5_bridge()
    print("x5:", [(r["T"], r["C-M==Z (exact)"], r["rel(C_composed, C_canon)"]) for r in res["x5"]["rows"]])
    res["meta"] = {**IC.provenance(), "frozen_trees": fz["trees"], "seconds": time.perf_counter() - t0,
                   "pycache_after": IC.pycache_dirs()}
    for k in ("phi", "x2_link", "psi", "psi_integrator_cells_EV9", "x5"):
        IC.dump(f"{k}.json", {"meta": res["meta"], k: res[k]})
    print(json.dumps(res["meta"], default=str))
    if res["meta"]["pycache_after"]:
        print("WARNING: __pycache__ present", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
