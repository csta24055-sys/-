"""Pass 2, route B checks (1), (2), (5): D's own kernel/refrigerant evaluation vs refcalc vs B's grammar.py
vs msp, on scenarios and a T grid that route B did NOT use (evaluation_set items 6 and 10; random T with
seed 2026; boundary and band points around integer refrigerant event times, incl. T = sw(tau) itself).

B's grammar.py is loaded ONLY here, as a probe (importlib, bytecode off). D's oracle is p2_oracle_kernels.
Run: PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0 python3 -B code/p2_check_b.py
"""
import importlib.util, math, os, random, sys, time
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import p2_common as C            # noqa: E402
import p2_oracle_kernels as K    # noqa: E402

PIECE_UNITS = ["B4-02", "B5-01", "B6-03", "B7-04", "B3-01", "B1-03", "B1-02"]
BAND_SENSITIVE_PIECES = {"B1-02", "B1-03"}     # P1 amplitudes assume every event counted (canonical form)


def load_b():
    p = os.path.join(C.RESEARCH, "routes", "B_formula_network", "code", "grammar.py")
    spec = importlib.util.spec_from_file_location("B_grammar", p)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def integer_ref_events(scn, H):
    out = set()
    for dev in scn.refrigerants:
        if dev.top_up:
            continue
        for tau in K.device_events(dev, float(H)):
            if tau == round(tau) and tau < 100:
                out.add(float(tau))
    return sorted(out)


def all_event_times(sy, scn, H):
    g = {p.gate for ps in sy.pieces.values() for p in ps if p.gate != K.NEG_INF}
    for dev in scn.refrigerants:
        g |= set(K.device_events(dev, float(H)))
    return sorted(g)


def band_of(T, events):
    """events tau whose switch point exceeds their cell end K=ceil(fl(tau d)) with K < T <= sw(tau) (03 S3.4)."""
    hit = []
    for tau in events:
        Kc = math.ceil(tau * C.D)
        sw = C.switch_point(tau)
        if Kc < sw and Kc < T <= sw:
            hit.append(tau)
    return hit


def grid(scn, H):
    pts = {t: "contract" for t in (1.0, 9.999999, 10.0, 10.000001, 19.999999, 20.0, 20.000001, 30.0, 40.0, 60.0)}
    for t in (0.25, 3.7, 12.5, 25.0, 33.3, 47.9, 50.0, 75.5, 99.999999, 100.0, 129.5, 130.0):
        pts.setdefault(t, "extra")
    rng = random.Random(2026)
    for _ in range(8):
        pts.setdefault(round(rng.uniform(0.01, 130.0), 6), "random")
    for tau in integer_ref_events(scn, H)[:3]:
        sw = C.switch_point(tau)
        pts[tau * (1 + 2.5e-10)] = "band_in"
        pts[math.nextafter(sw, -math.inf)] = "band_in(sw-1ulp)"
        pts[sw] = "band_end(sw)"
        pts[math.nextafter(sw, math.inf)] = "after_sw(+1ulp)"
        pts[tau * (1 + 3e-9)] = "after_band"
    return dict(sorted(pts.items()))


def run_scn(tag, scn, B):
    m = C.frozen()
    t0 = time.perf_counter()
    sy = m["unified"].System(scn)
    H = int(sy.H)
    G = grid(scn, H)
    Ts = list(G)
    evs = all_event_times(sy, scn, H)
    share = sy.s("b21.share", "operation")
    rows = []
    refs = {T: C.ref(scn, T) for T in Ts}
    msp = {T: sy.at(T) for T in Ts}
    Bk = {}
    for u in PIECE_UNITS:
        for mode in ("clip", "integrator"):
            res, net, nk = B.eval_kernel(sy.pieces.get(u, []), H, Ts, mode)
            Bk[(u, mode)] = res
    resEL, _, _ = B.eval_kernel(sy.pieces.get("EL", []), H, Ts, "clip")
    Brc = B.RefrigerantCircuit(scn, H, late_reset=True).sweep(Ts)
    Brc0 = B.RefrigerantCircuit(scn, H, late_reset=False).sweep(Ts)
    for T in Ts:
        lab = G[T]
        dom = C.in_domain(scn, T)
        band = band_of(T, evs)
        base = {"scenario": tag, "T": repr(T), "label": lab, "valid_domain_reasons": dom[:2],
                "in_excluded_band": bool(band), "band_taus": band[:3]}
        for u in PIECE_UNITS:
            mine = K.kernel_sum(sy.pieces.get(u, []), T)
            r = refs[T][u]["value"]
            rows.append({**base, "unit": u, "D": float(mine), "refcalc": r, "rel_D_ref": C.rel(mine, r),
                         "rel_Bclip_D": C.rel(Bk[(u, "clip")][T]["total"], mine),
                         "rel_Bint_D": C.rel(Bk[(u, "integrator")][T]["total"], mine),
                         "rel_msp_ref": C.rel(msp[T][u]["value"], r)})
        # B2-01 = share * EL (06 S6.4): D's evaluation of the EL pieces times the share
        mine = K.kernel_sum(sy.pieces.get("EL", []), T) * C.F(share) if share else C.F(0)
        r = refs[T]["B2-01"]["value"]
        rows.append({**base, "unit": "B2-01", "D": float(mine), "refcalc": r, "rel_D_ref": C.rel(mine, r),
                     "rel_Bclip_D": C.rel(share * resEL[T]["total"], mine) if share else 0.0, "rel_Bint_D": None,
                     "rel_msp_ref": C.rel(msp[T]["B2-01"]["value"], r)})
        mine = K.refrigerant(scn.refrigerants, T)
        for u in ("B1-02", "B1-03", "B1-04"):
            r = refs[T][u]["value"]
            rows.append({**base, "unit": u + " [refrigerant recurrence]", "D": float(mine[u]), "refcalc": r,
                         "rel_D_ref": C.rel(mine[u], r), "rel_Bauto_D": C.rel(Brc[T][u], mine[u]),
                         "rel_Bauto_noLate_D": C.rel(Brc0[T][u], mine[u]),
                         "rel_msp_ref": C.rel(msp[T][u]["value"], r), "rel_msp_D": C.rel(msp[T][u]["value"], mine[u])})
        rS = refs[T]["SUM-03"]["value"]
        rows.append({**base, "unit": "SUM-03", "refcalc": rS, "rel_msp_ref": C.rel(msp[T]["SUM-03"]["value"], rS)})
    return {"scenario": scn.meta.scenario_id, "tag": tag, "H": H, "n_T": len(Ts), "rows": rows,
            "integer_refrigerant_events": integer_ref_events(scn, H)[:6],
            "seconds": round(time.perf_counter() - t0, 1)}


def summarise(runs):
    S = {}
    for run in runs:
        for r in run["rows"]:
            key = r["unit"]
            inside = (not r["valid_domain_reasons"]) and (not r["in_excluded_band"])
            for f in ("rel_D_ref", "rel_Bclip_D", "rel_Bint_D", "rel_Bauto_D", "rel_Bauto_noLate_D", "rel_msp_ref", "rel_msp_D"):
                v = r.get(f)
                if v is None:
                    continue
                zone = "in_Dprime" if inside else ("band" if r["in_excluded_band"] else "outside_D_knife_window")
                d = S.setdefault(key, {}).setdefault(zone, {})
                d[f] = max(d.get(f, 0.0), v)
                d["n"] = d.get("n", 0) + (f == "rel_msp_ref")
    return S


def main():
    C.frozen()
    assert C.clean() == [], C.clean()
    B = load_b()
    runs = [run_scn(tag, s, B) for tag, s in C.d_scenarios(("EV6", "EV10"))]
    S = summarise(runs)
    # T = sw(tau) itself: does the msp interval form agree (03 S5.4 open band) or not (S3.4 closed band)?
    at_sw = [{k: r[k] for k in ("scenario", "T", "unit", "rel_msp_ref", "rel_D_ref")} for run in runs for r in run["rows"]
             if r["label"] in ("band_end(sw)", "band_in(sw-1ulp)", "after_sw(+1ulp)") and r["unit"].startswith("B1-04")]
    out = {"provenance": {"head": os.popen("git -C %s rev-parse HEAD" % C.STUDY).read().strip(),
                          "frozen_trees": C.frozen()["trees"]},
           "summary_max_rel_by_unit_and_zone": S, "B1-04_at_switch_point": at_sw, "runs": runs}
    C.dump("p2_check_b.json", out)
    assert C.clean() == [], C.clean()
    import json
    print(json.dumps({"summary": S, "at_sw": at_sw, "seconds": [r["seconds"] for r in runs]}, indent=1))


if __name__ == "__main__":
    main()
