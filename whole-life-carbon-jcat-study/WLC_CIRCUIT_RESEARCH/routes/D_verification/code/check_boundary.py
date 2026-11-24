"""D checklist 1: boundary table + row-by-row comparison with route A/E points.json
+ float slip-through. Reads route outputs as DATA only (JSON); imports only oracle_d.

Run: PYTHONDONTWRITEBYTECODE=1 math7-py -B code/check_boundary.py
(mpmath is used only for E's transcendental P0-AC rows; everything else is Fraction.)
"""
import json, math, os, sys
from fractions import Fraction as F
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import oracle_d as O  # noqa: E402

ROUTES = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(HERE, "..", "results")


def boundary_table():
    pts = O.CONTRACT_POINTS + O.KNIFE_POINTS + ["10.00000001"]
    rows = []
    for t in pts:
        rows.append({"t": t, **{c: O.dec(O.G("P0", F(t), c)) for c in O.CONVENTIONS}})
    band_end = F(10) / (1 - O.EPS)
    rows.append({"t": "10/(1-1e-9)", **{c: O.dec(O.G("P0", band_end, c)) for c in O.CONVENTIONS}})
    lim = []
    for tau in O.EVENT_TIMES:
        for c in O.CONVENTIONS:
            lo, hi = O.limits("P0", tau, c)
            lim.append({"a": str(tau), "conv": c, "left_limit": O.dec(lo), "value": O.dec(O.G("P0", tau, c)),
                        "right_limit": O.dec(hi)})
        a = F(tau) / (1 - O.EPS)
        lo, hi = O.limits("P0", a, O.ORIG)
        lim.append({"a": f"{tau}/(1-eps)", "conv": "orig", "left_limit": O.dec(lo),
                    "value": O.dec(O.G("P0", a, O.ORIG)), "right_limit": O.dec(hi)})
    # where do conventions disagree around tau=10?  (sample the closed band ends)
    band = {
        "at_10": [O.dec(O.G("P0", 10, c)) for c in O.CONVENTIONS],
        "at_band_end_10/(1-eps)": [O.dec(O.G("P0", band_end, c)) for c in O.CONVENTIONS],
        "just_after_band_end": [O.dec(O.G("P0", band_end + F(1, 10**15), c)) for c in O.CONVENTIONS],
        "finding": "right and orig differ on the CLOSED band [10, 10/(1-eps)] (orig excludes the event at "
                   "T=10/(1-eps) itself because the rule is strict); architecture S1.2 and A claim A-3 "
                   "write the half-open [nc, nc/(1-eps))",
    }
    return rows, lim, band


def parse_t(s):
    return F(s)


def compare_A():
    p = os.path.join(ROUTES, "A_waveform", "results", "points.json")
    rows = json.load(open(p))["rows"]
    mism, n, by = [], 0, {}
    for r in rows:
        t = parse_t(r["t"]); conv = r["convention"]; case = r["case"]
        if case == "P0":
            mine = O.G("P0", t, conv)
        elif case.startswith("P1-"):
            mine = O.G("P1", t, conv, case[3:])
        elif case in ("P2", "Px"):
            mine = O.G(case, t, conv)
        else:
            continue
        n += 1
        k = f"{case}|{r['realization']}|{conv}"
        by[k] = by.get(k, 0) + 1
        if F(r["value"]) != mine:
            mism.append({"row": r, "D": O.dec(mine)})
    return {"file": "routes/A_waveform/results/points.json", "rows_compared": n, "mismatches": mism,
            "rows_by_case_realization_conv": by}


def compare_E():
    import mpmath as mp
    mp.mp.dps = 40
    p = os.path.join(ROUTES, "E_resistor_energy", "results", "points.json")
    rows = json.load(open(p))
    mism, n, ac, notes = [], 0, [], []
    for r in rows:
        t = parse_t(r["t"]); conv = r["convention"]; case = r["case"]
        if case == "P0-AC":
            # my own: G = 100 + 4t - sin(4 pi t)/pi + events(right)
            ev = O.G("P0", t, "right") - 100 - 4 * t
            g = 100 + 4 * mp.mpf(t.numerator) / t.denominator - mp.sin(4 * mp.pi * mp.mpf(t.numerator) / t.denominator) / mp.pi + int(ev)
            dev = g - (mp.mpf(O.G("P0", t).numerator) / O.G("P0", t).denominator)
            claim_exact = r["value"] is not None
            mine_exact = (4 * t).denominator == 1
            ok_dec = abs(mp.mpf(r["value_decimal"]) - g) < mp.mpf(10) ** -20
            ac.append({"t": r["t"], "E_value_decimal": r["value_decimal"], "D": mp.nstr(g, 25),
                       "E_dev": r["dev_from_P0_kg"], "D_dev": mp.nstr(dev, 6), "decimal_agree_1e-20": bool(ok_dec),
                       "exactness_agree": claim_exact == mine_exact})
            if not ok_dec or claim_exact != mine_exact:
                mism.append({"row": r, "D": mp.nstr(g, 25)})
            n += 1
            continue
        if case == "P0":
            mine = O.G("P0", t, conv)
        elif case.startswith("P1-"):
            mine = O.G("P1", t, conv, case[3:])
            if "E-R1" in r["realization"]:
                notes.append(f"P1 row t={r['t']}: realization label says E-R1 but make_results.py:37 writes "
                             "value=J.p1(t,pol) (closed form); no E circuit implements P1")
        elif case == "P2":
            mine = O.G("P2", t, conv)
        else:
            continue
        n += 1
        if F(r["value"]) != mine:
            mism.append({"row": r, "D": O.dec(mine)})
    return {"file": "routes/E_resistor_energy/results/points.json", "rows_compared": n, "mismatches": mism,
            "ac_rows": ac, "provenance_notes": sorted(set(notes))[:1] + ([f"... {len(notes)} P1 rows affected"] if notes else [])}


def float_slip():
    """fl(n*c) vs the rational n*c, and float event counting at exact event times."""
    out = {}
    for name, c_exact in (("0.1", F(1, 10)), ("0.7", F(7, 10)), ("10/3", F(10, 3))):
        cf = float(c_exact)
        N = int(F(60) / c_exact)
        prod_ne, floor_wrong, incl_wrong, ex = 0, 0, 0, []
        for n in range(1, N + 1):
            exact = n * c_exact
            prod = n * cf                       # float event time fl(n*fl(c))
            nearest = float(exact)              # correctly rounded rational n*c
            if prod != nearest:
                prod_ne += 1
            # float floor counting at the exact event instant (query = nearest float)
            cnt = math.floor(nearest / cf)
            if cnt != n:
                floor_wrong += 1
                if len(ex) < 4:
                    ex.append({"n": n, "t": repr(nearest), "floor(t/c)": cnt, "exact": n})
            # right-convention inclusion of event fl(n*c) at query t=nearest
            if not (prod <= nearest):
                incl_wrong += 1
        # accumulated clock: t_k = t_{k-1} + c in float (fixed-step-like event times)
        acc, drift_bad = 0.0, 0
        for n in range(1, N + 1):
            acc += cf
            if acc != float(n * c_exact):
                drift_bad += 1
        out[name] = {"n_events_to_60": N, "fl(n*c)!=fl(exact n*c)": prod_ne,
                     "floor(t/c)!=n at exact event instants": floor_wrong,
                     "event fl(n*c) NOT counted at t=fl(n*c exact) (right conv)": incl_wrong,
                     "repeated-addition clock != fl(n*c)": drift_bad, "examples_floor": ex}
    # the float knife edge of the orig convention
    t = 10.00000001
    tt = t * (1 - 1e-9)
    exact = O.G("P0", F("10.00000001"), O.ORIG)
    out["orig_knife_edge_10.00000001"] = {
        "float t*(1-eps)": repr(tt), "float counts event": tt > 10.0,
        "exact value": O.dec(exact), "exact counts event": exact != F(100) + 4 * F("10.00000001")}
    # do float evaluations agree at the knife points used for float tests?
    kp = {}
    for ts in O.KNIFE_POINTS:
        tf = float(ts)
        ttf = tf * (1 - 1e-9)
        kp[ts] = {"float_counts_10": ttf > 10.0, "exact_counts_10": F(ts) * (1 - O.EPS) > 10}
    out["knife_points_float_vs_exact"] = kp
    return out


def main():
    rows, lim, band = boundary_table()
    res = {"boundary_table_P0": rows, "exact_limits_P0": lim, "orig_band": band,
           "route_A_comparison": compare_A(), "route_E_comparison": compare_E(),
           "float_slip_through": float_slip()}
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "boundary_comparison.json"), "w") as f:
        json.dump(res, f, indent=1)
    a, e = res["route_A_comparison"], res["route_E_comparison"]
    print("A rows", a["rows_compared"], "mismatches", len(a["mismatches"]))
    print("E rows", e["rows_compared"], "mismatches", len(e["mismatches"]))
    for r in rows:
        print(r)
    print(json.dumps(band, indent=0))
    print(json.dumps(res["float_slip_through"], indent=0))
    print(e["provenance_notes"])
    return res


if __name__ == "__main__":
    main()
