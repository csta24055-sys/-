"""Route B experiments: every kernel kind of the 70-unit model evaluated by grammar netlists and compared
with refcalc (primary oracle) and msp/unified.System (second oracle) on a T grid.

Run (from anywhere):
    PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0 python3 -B <route>/code/route_b_experiments.py
Writes results/kernel_comparison.json, results/points.json, results/summary.json.
"""
from __future__ import annotations

import json
import math
import os
import platform
import sys
import time

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import grammar as G  # noqa: E402
import oracle_io as O  # noqa: E402

TOL = 1e-9
CONTRACT_T = [1.0, 9.999999, 10.0, 10.000001, 19.999999, 20.0, 20.000001, 30.0, 40.0, 60.0]
EXTRA_T = [0.5, 7.3, 29.5, 59.999999, 100.25, 130.0]


def band_points(tau: float) -> list[tuple[float, str]]:
    """Points around an integer event time tau (architecture 1.2):
    band_in   tau*(1+5e-10)  inside the closed real band [tau, tau/(1-eps)] (floats: [tau, sw(tau)) with
              sw(tau) = fl(tau/(1-eps)) the first float that counts): the original does NOT count the event yet
    knife     tau*(1+1e-9)   the float knife edge (real arithmetic: not counted; float: counted) -> undefined
    band_out  tau*(1+2e-9)   just after the band: counted"""
    return [(tau * (1 + 5e-10), "band_in"), (tau * (1 + 1e-9), "knife"), (tau * (1 + 2e-9), "band_out")]


def rel(x, y) -> float:
    if x is None or y is None:
        return math.inf if (x is None) != (y is None) else 0.0
    if y == 0.0:
        return abs(x)
    return abs(x - y) / abs(y)


def integer_event_times(sy, scn) -> list[float]:
    taus = set()
    for name, ps in sy.pieces.items():
        for p in ps:
            if p.gate != G.NEG_INF and p.gate == round(p.gate):
                taus.add(float(p.gate))
    return sorted(taus)


def refrigerant_band_taus(scn, H: int, n: int = 3) -> list[float]:
    """Integer event times of refrigerant devices WITHOUT top-up (where the reset changes the state): the
    open band (K, sw(tau)) of these events is where the interval form is observed to deviate (03 5.4; 03 3.4
    excludes the closed (K, sw(tau)] conservatively from D')."""
    taus = set()
    for dev in scn.refrigerants:
        if dev.top_up:
            continue
        for tau in G.device_event_table(dev, float(H)):
            if tau == round(tau) and tau < 60:
                taus.add(float(tau))
    return sorted(taus)[:n]


def t_grid(sy, scn) -> list[tuple[float, str]]:
    pts = [(t, "contract") for t in CONTRACT_T] + [(t, "extra") for t in EXTRA_T]
    ints = integer_event_times(sy, scn)
    for tau in (10.0, 20.0, 29.0):
        if tau in ints:
            pts += band_points(tau)
    for tau in refrigerant_band_taus(scn, int(sy.H)):
        pts += band_points(tau)
    seen, out = set(), []
    for t, lab in pts:
        if t not in seen:
            seen.add(t)
            out.append((t, lab))
    return sorted(out)


# kernel -> (spectrum name in P1 pieces, refcalc unit, field)
PIECE_KERNELS = {
    "B4-02": "atom (event, theta_eps)",
    "B5-01": "atom (event, theta_eps)",
    "B6-03": "year cell w_k",
    "B7-04": "year cell w_k",
    "B3-01": "density min(T,H) + gated year cell",
    "B1-03": "atom + gated year cell (from P1 amplitudes)",
    "B1-02": "year cell (P1 state amplitudes u_dk)",
}
# kernels whose P1 amplitudes encode the refrigerant state assuming every event is counted (canonical form):
# they are expected to differ from refcalc inside the open band (K, sw(tau)) (outside D'; 03 3.4 excludes (K, sw]).
# B1-02 [P1 cells] in the band is NOT relied upon: D measured 8.9e-10 there on EV6, close to the 1e-9 tolerance.
BAND_SENSITIVE = {"B1-02 [P1 cells]", "B1-04 [msp interval]", "B1-04 [P1 jump pieces]"}


def run_scenario(scn, log=print) -> dict:
    m = O.setup()
    S_ = m["system"]
    sid = scn.meta.scenario_id
    t0 = time.perf_counter()
    sy = O.system(scn)
    H = int(sy.H)
    grid = t_grid(sy, scn)
    Ts = [t for t, _ in grid]
    label = dict(grid)
    log(f"[{sid}] H={H}, {len(Ts)} T points, integer event times present: "
        f"{[t for t in (10.0, 20.0, 29.0) if t in integer_event_times(sy, scn)]}")
    ref, msp = {}, {}
    for T in Ts:
        ref[T] = O.reference_at(scn, T)
        msp[T] = sy.at(T)
    t_oracle = time.perf_counter() - t0
    rows = []

    def add(kernel, T, g, r, mm=None, kind=""):
        rows.append({"scenario": sid, "kernel": kernel, "kind": kind, "T": repr(T), "label": label[T], "grammar": g,
                     "refcalc": r, "msp": mm, "rel_ref": rel(g, r), "rel_msp": rel(g, mm) if mm is not None else None})

    costs = {}
    # ---- piece kernels (P1 amplitudes as external table) ----
    for unit, kind in PIECE_KERNELS.items():
        pieces = sy.pieces.get(unit, [])
        for mode in (("clip", "integrator") if unit in ("B6-03", "B7-04") else ("clip",)):
            tt = time.perf_counter()
            res, net, nk = G.eval_kernel(pieces, H, Ts, cell_mode=mode)
            name = f"{unit} [{'P1 cells' if unit == 'B1-02' else 'P1 pieces'}{'' if mode == 'clip' else ', integrator'}]"
            costs[name] = {"netlist": net.counts(), "pieces_by_kind": nk, "evals": net.evals,
                           "seconds": time.perf_counter() - tt}
            for T in Ts:
                add(name, T, res[T]["total"], ref[T][unit]["value"], msp[T][unit]["value"], kind)
    # B1-04 jump-form pieces (kept by the original for comparison only)
    res, net, nk = G.eval_kernel(sy.pieces.get("B1-04", []), H, Ts)
    costs["B1-04 [P1 jump pieces]"] = {"netlist": net.counts(), "pieces_by_kind": nk, "evals": net.evals}
    for T in Ts:
        add("B1-04 [P1 jump pieces]", T, res[T]["total"], ref[T]["B1-04"]["value"], msp[T]["B1-04"]["value"],
            "jump form of the terminal residual R(T)")
        add("B1-04 [msp interval]", T, msp[T]["B1-04"]["value"], ref[T]["B1-04"]["value"], None,
            "oracle-vs-oracle: msp interval form vs refcalc")
    # ---- refrigerant hybrid automaton from RAW inputs ----
    rc = G.RefrigerantCircuit(scn, H)
    tt = time.perf_counter()
    rr = rc.sweep(Ts)
    costs["refrigerant S/H automaton"] = {"primitives": dict(rc.prim), "state_tuple": rc.state_tuple(),
                                          "seconds": time.perf_counter() - tt, "unexpected": rc.unexpected}
    for T in Ts:
        for u in ("B1-02", "B1-03", "B1-04"):
            add(f"{u} [raw S/H automaton]", T, rr[T][u], ref[T][u]["value"], msp[T][u]["value"],
                "sample-hold + reset + switched integrator")
    rc0 = G.RefrigerantCircuit(scn, H, late_reset=False)
    rr0 = rc0.sweep(Ts)
    for T in Ts:
        for u in ("B1-02", "B1-04"):
            add(f"{u} [raw S/H, no late reset]", T, rr0[T][u], ref[T][u]["value"], msp[T][u]["value"],
                "ablation: comparator events after their cell closed are ignored")
    # ---- B2-01: linear gain (share in [0,1]: a divider) on the EL year-cell kernel ----
    share = scn.operation.facility_management_ratio
    res, net, _ = G.eval_kernel(sy.pieces.get("EL", []), H, Ts)
    ok = share is not None and 0.0 <= share <= 1.0
    for T in Ts:
        g = (res[T]["total"] * share) if ok else 0.0        # gain block k = share
        add("B2-01 [gain x year cells]", T, g, ref[T]["B2-01"]["value"], msp[T]["B2-01"]["value"],
            "T-independent gain on a year-cell kernel")
    # ---- count kernel from RAW equipment inputs ----
    net, out, n_tau = G.build_counter(scn, H)
    costs["B4-01 count [raw comparator bank]"] = {"netlist": net.counts(), "n_event_times": n_tau}
    for T in Ts:
        add("B4-01 n_events [raw comparator bank]", T, net.value(T, out), float(ref[T]["B4-01"]["n_events"]),
            float(msp[T]["B4-01"]["n_events"]), "count kernel sum of theta_eps")
    # ---- constants (P1 scalars as DC sources) ----
    for uid, col in S_.CONST_VALUE.items():
        a = float(sy.eng.col("S", col).v[0])
        for T in Ts:
            add(f"{uid} [DC source]", T, a, ref[T][uid]["value"], msp[T][uid]["value"], "constant")
    # ---- outer composition: SUM-03 = sum over COMP rows of iota_s*sigma*beta*V_u (gains + summing node) ----
    inc = set(scn.boundary.included_lifecycle_stages)
    piece_val = {}
    for unit in ("B3-01", "B4-02", "B5-01", "B6-03", "B7-04"):
        piece_val[unit], _, _ = G.eval_kernel(sy.pieces.get(unit, []), H, Ts)
    elres, _, _ = G.eval_kernel(sy.pieces.get("EL", []), H, Ts)
    for T in Ts:
        V = {uid: float(sy.eng.col("S", col).v[0]) for uid, col in S_.CONST_VALUE.items()}
        for unit in piece_val:
            V[unit] = piece_val[unit][T]["total"]
        V.update({u: rr[T][u] for u in ("B1-02", "B1-03", "B1-04")})
        V["B2-01"] = elres[T]["total"] * share if ok else 0.0
        terms = []
        for stage, unit, sign in S_.COMP_ROWS:
            if stage not in inc:
                continue
            beta = 1.0 if not (stage, unit) == ("B6", "B2-01") else (1.0 if "B2" in inc else 0.0)
            terms.append(sign * beta * V[unit])           # gain block (+-1, beta in {0,1})
        s3 = math.fsum(terms)                              # summing node
        add("SUM-03 [gain + summing node]", T, s3, ref[T]["SUM-03"]["value"], msp[T]["SUM-03"]["value"],
            "outer masked sum (stage x unit 0/+-1 matrix)")
        add("SUM-06 [gain 0.001]", T, 0.001 * s3, ref[T]["SUM-06"]["value"], msp[T]["SUM-06"]["value"], "gain")
        area = scn.project.gross_floor_area
        s5 = s3 / (area * T) if (area is not None and area > 0) else None          # EXTERNAL DIGITAL division
        add("SUM-05 [external digital division]", T, s5, ref[T]["SUM-05"]["value"], msp[T]["SUM-05"]["value"],
            "division by the sweep variable: NOT in G (class d)")
    return {"scenario": sid, "H": H, "grid": [(repr(t), l) for t, l in grid], "rows": rows, "costs": costs,
            "t_oracle_s": t_oracle, "integer_event_times": integer_event_times(sy, scn)}


def summarise(runs) -> dict:
    out = {}
    for run in runs:
        for r in run["rows"]:
            key = r["kernel"]
            d = out.setdefault(key, {"n": 0, "max_rel_ref_asserted": 0.0, "max_rel_msp_asserted": 0.0,
                                     "n_fail": 0, "unasserted": [], "kind": r["kind"]})
            asserted = r["label"] != "knife" and not (key in BAND_SENSITIVE and r["label"] == "band_in")
            if "no late reset" in key:
                asserted = False
            if asserted:
                d["n"] += 1
                d["max_rel_ref_asserted"] = max(d["max_rel_ref_asserted"], r["rel_ref"])
                if r["rel_msp"] is not None:
                    d["max_rel_msp_asserted"] = max(d["max_rel_msp_asserted"], r["rel_msp"])
                if r["rel_ref"] > TOL:
                    d["n_fail"] += 1
            else:
                d["unasserted"].append({"scenario": r["scenario"], "T": r["T"], "label": r["label"],
                                        "rel_ref": r["rel_ref"], "rel_msp": r["rel_msp"]})
    return out


def main():
    t0 = time.perf_counter()
    res_dir = os.path.join(O.ROUTE, "results")
    os.makedirs(res_dir, exist_ok=True)
    runs = [run_scenario(s) for s in O.representative_scenarios(("S", "M")) + O.out_of_sample_scenarios()]
    summ = summarise(runs)
    meta = {"head": O.head_sha(), "frozen_trees": O.setup()["trees"], "python": platform.python_version(),
            "machine": platform.machine(), "tolerance_rel": TOL, "seconds": time.perf_counter() - t0,
            "pycache_in_frozen_trees": O.pycache_dirs()}
    with open(os.path.join(res_dir, "kernel_comparison.json"), "w") as f:
        json.dump({"meta": meta, "summary": summ, "runs": [{k: v for k, v in r.items() if k != "rows"} for r in runs]},
                  f, indent=1, default=str)
    with open(os.path.join(res_dir, "points.json"), "w") as f:
        json.dump([row for r in runs for row in r["rows"]], f, indent=0, default=str)
    for k, d in sorted(summ.items()):
        print(f"{k:45s} n={d['n']:3d} fail={d['n_fail']} max_rel_ref={d['max_rel_ref_asserted']:.2e} "
              f"max_rel_msp={d['max_rel_msp_asserted']:.2e} unasserted={len(d['unasserted'])}")
    print("meta", json.dumps(meta, default=str))
    return summ, meta


if __name__ == "__main__":
    main()
