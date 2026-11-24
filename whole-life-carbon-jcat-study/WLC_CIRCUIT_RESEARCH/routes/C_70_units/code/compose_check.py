"""Route C experiments H-C1..H-C4 against the frozen refcalc oracle (Psi reading: axis = evaluation horizon T).

Usage (from anywhere):
  PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0 python3 -B code/compose_check.py [--only c1,c2,c3,c4,inv] [--quick]

Writes results/{inventory,hc1,hc2,hc3,hc4}.json.  Synthetic (fictional) data only; no network.
"""
from __future__ import annotations

import argparse
import copy
import random
import sys
import time

import common as C

DIRECT = None


def _direct() -> list[str]:
    global DIRECT
    if DIRECT is None:
        DIRECT = list(C.ledger()["role_members"]["DIRECT"])
    return DIRECT


_BENCH = None


def _bench():
    """scenarios.benchmark() generated once (the L scenario alone takes seconds to generate)."""
    global _BENCH
    if _BENCH is None:
        _BENCH = C.oracle()[1].benchmark()
    return _BENCH


def _edge(name: str):
    """A named boundary scenario of the frozen generator (scenarios.edge_set())."""
    for n, s in C.oracle()[1].edge_set():
        if n == name:
            return s
    raise KeyError(name)


def _at(scn, T: float, stages=None):
    s = copy.deepcopy(scn)
    s.boundary.study_period = float(T)
    if stages is not None:
        s.boundary.included_lifecycle_stages = list(stages)
    return s


# ------------------------------------------------------------------ inventory (verify architecture's [H] counts)
def inventory() -> dict:
    L = C.ledger()
    us = C.units()
    ids = [u["id"] for u in us]
    roles = {}
    for u in us:
        roles[u["role"]] = roles.get(u["role"], 0) + 1
    rows = C.comp_rows()
    blocks = {u["id"]: C.blocks_from_text(u["time_form"]) for u in us if u["role"] == "DIRECT"}
    block_count = {}
    for b in blocks.values():
        for x in b:
            block_count[x] = block_count.get(x, 0) + 1
    baseline, _ = C.oracle()
    reg_ids = sorted(baseline.load().UNITS)
    closure = C.refcalc_closure("SUM-03")
    # ledger formula edges vs refcalc declared edges
    led_dep = {u["id"]: sorted(u["depends_on_units"]) for u in us}
    ref_dep = {u: sorted(baseline.load().UNITS[u].depends_on) for u in reg_ids}
    dep_diff = {u: {"ledger_only": sorted(set(led_dep[u]) - set(ref_dep[u])),
                    "refcalc_only": sorted(set(ref_dep[u]) - set(led_dep[u]))}
                for u in ids if set(led_dep[u]) != set(ref_dep.get(u, []))}
    # composition edges in unit_dependencies.csv
    import csv
    with open(C.DEPS_CSV, encoding="utf-8") as f:
        comp_csv = [r for r in csv.DictReader(f) if r["kind"] == "composition"]
    upstream_by_role = {}
    for u in us:
        if u["id"] in closure:
            upstream_by_role.setdefault(u["role"], []).append(u["id"])
    out = {
        "n_units": len(us), "ids_unique": len(set(ids)) == len(ids),
        "ids_equal_refcalc_registry": sorted(ids) == reg_ids,
        "role_counts": roles, "role_counts_json_field": L["role_counts"],
        "role_members_consistent": all(sorted(L["role_members"][r]) == sorted(u["id"] for u in us if u["role"] == r)
                                       for r in roles),
        "n_comp_rows": len(rows), "n_comp_units": len({r[0] for r in rows}),
        "comp_rows": [list(r) for r in rows],
        "comp_units_equal_DIRECT": sorted({r[0] for r in rows}) == sorted(_direct()),
        "n_comp_edges_dependencies_csv": len(comp_csv),
        "comp_stages": sorted({r[1] for r in rows}), "refcalc_stages": C.refcalc_stages(),
        "non_trivial_rows": [list(r) for r in rows if r[2] != 1 or r[3] != "1"],
        "direct_blocks_from_text": blocks, "block_type_unit_counts": block_count,
        "n_distinct_block_types": len(block_count),
        "direct_multi_block_units": sorted(u for u, b in blocks.items() if len(b) > 1),
        "refcalc_closure_SUM03_by_role": {r: sorted(v) for r, v in upstream_by_role.items()},
        "n_time_dependent": sum(1 for u in us if u["time_dependent"]),
        "n_direct_time_dependent": sum(1 for u in us if u["role"] == "DIRECT" and u["time_dependent"]),
        "ledger_vs_refcalc_dep_differences": dep_diff,
        "architecture_H_claims": {
            "21 DIRECT + 49 others": roles.get("DIRECT") == 21 and len(us) - roles.get("DIRECT", 0) == 49,
            "COMP 22 rows": len(rows) == 22,
            "AUX/DEC/REF/AGG/BRK = 15/9/10/9/6": [roles.get(r) for r in
                                                  ("AUXILIARY", "DECISION", "REFERENCE", "AGGREGATE", "BREAKDOWN")]
                                                 == [15, 9, 10, 9, 6],
            "7 block types": len(block_count) == 7,
            "const(t=0) 7 units": block_count.get("const_t0") == 7,
            "const(t=T) 5 units": block_count.get("const_tT") == 5,
            "B2-01 in B2 (+1) and B6 (-iota_B2)": sorted(r[1:] for r in rows if r[0] == "B2-01")
                                                    == sorted([("B2", 1, "1"), ("B6", -1, "iota_B2")]),
        },
    }
    return out


# ------------------------------------------------------------------ H-C1 composition = one summing node
def stage_variants(all_stages: list[str], seed: int = 20261124) -> dict[str, list[str]]:
    rnd = random.Random(seed)
    v = {"all14": list(all_stages),
         "no_B2": [s for s in all_stages if s != "B2"],
         "no_B6": [s for s in all_stages if s != "B6"],
         "B_only": [s for s in all_stages if s.startswith("B")]}
    for i in range(2):
        v[f"random{i}"] = sorted(rnd.sample(all_stages, rnd.randint(3, 11)), key=all_stages.index)
    return v


def hc1(quick: bool = False) -> dict:
    baseline, scenarios = C.oracle()
    stages = C.refcalc_stages()
    bench = _bench()
    if quick:
        bench = bench[:1]
    else:
        bench = bench + [_edge("rebuild_within_period"), _edge("refurbishment_divides_period")]
    variants = stage_variants(stages)
    cases = []
    t0 = time.perf_counter()
    n_runs = 0
    for si, scn in enumerate(bench):
        vnames = list(variants) if si < 2 else ["all14"]            # L: full stages only (cost)
        for vn in vnames:
            for T in C.T_GRID_C1:
                s = _at(scn, T, variants[vn])
                dom = scenarios.valid_domain(s)
                r = baseline.run_reference(s, _direct() + ["SUM-03", "X-02", "SUM-01", "SUM-02"])
                n_runs += 1
                vals = {u: r[u]["value"] for u in _direct()}
                inc = set(s.boundary.included_lifecycle_stages)
                st, tot = C.rebuild(vals, inc)
                ref_st = r["X-02"]["by_stage"]
                naive = sum(vals.values())                           # 21 DIRECT as 21 independent sources
                e_st = max((C.rel_err(st[k], ref_st[k]) for k in ref_st), default=0.0)
                cases.append({
                    "scenario": scn.meta.scenario_id, "stages": vn, "T": repr(T),
                    "in_domain": not dom, "domain_reasons": dom,
                    "SUM03": r["SUM-03"]["value"], "rebuilt": tot, "rel_err_total": C.rel_err(tot, r["SUM-03"]["value"]),
                    "stage_keys_equal": set(st) == set(ref_st), "max_rel_err_stage": e_st,
                    "rel_err_SUM01": C.rel_err(sum(st.get(k, 0.0) for k in ("A1-A3", "A4", "A5")), r["SUM-01"]["value"])
                    if r["SUM-01"]["value"] else 0.0,
                    "rel_err_SUM02": C.rel_err(sum(v for k, v in st.items() if k not in ("B6", "B7")), r["SUM-02"]["value"])
                    if r["SUM-02"]["value"] else 0.0,
                    "naive_21_sources_rel_err": C.rel_err(naive, r["SUM-03"]["value"]) if r["SUM-03"]["value"] else None,
                    "B2-01_over_C": vals["B2-01"] / r["SUM-03"]["value"] if r["SUM-03"]["value"] else None,
                })
    wall = time.perf_counter() - t0
    ind = [c for c in cases if c["in_domain"]]
    max_tot = max(c["rel_err_total"] for c in ind) if ind else None
    max_st = max(c["max_rel_err_stage"] for c in ind) if ind else None
    ok = bool(ind) and max_tot <= C.REL_TOL and max_st <= C.REL_TOL and all(c["stage_keys_equal"] for c in ind)
    # architecture [F] observation re-check (S scenario, all stages)
    S = [c for c in cases if c["scenario"].endswith("S-T60-seed101") and c["stages"] == "all14"]
    sv = {c["T"]: c["SUM03"] for c in S}
    return {
        "hypothesis": "H-C1", "verdict": "PASS" if ok else "FAIL", "tol_rel": C.REL_TOL,
        "n_cases": len(cases), "n_in_domain": len(ind), "n_out_of_domain": len(cases) - len(ind),
        "scenarios": [s.meta.scenario_id for s in bench], "stage_variants": variants, "T_grid": [repr(t) for t in C.T_GRID_C1],
        "max_rel_err_total_in_domain": max_tot, "max_rel_err_stage_in_domain": max_st,
        "max_rel_err_total_all": max(c["rel_err_total"] for c in cases),
        "max_rel_err_SUM01": max(c["rel_err_SUM01"] for c in cases), "max_rel_err_SUM02": max(c["rel_err_SUM02"] for c in cases),
        "counterexample_naive_21_sources": {
            "description": "sum of the 21 DIRECT values with sign +1 and no stage predicate (21 independent sources)",
            "rel_err_all14": sorted({round(c["naive_21_sources_rel_err"], 12) for c in cases if c["stages"] == "all14"}),
            "equals_B2-01_over_C_all14": all(abs(c["naive_21_sources_rel_err"] - abs(c["B2-01_over_C"])) < 1e-9
                                             for c in cases if c["stages"] == "all14"),
        },
        "architecture_F_recheck_S": {"T=9.999999": sv.get("9.999999"), "T=10": sv.get("10.0"),
                                     "T=10.000001": sv.get("10.000001"),
                                     "jump_10_to_10.000001": (sv.get("10.000001") - sv.get("10.0")) if S else None},
        "n_refcalc_runs": n_runs, "wall_s": wall, "cases": cases,
    }


# ------------------------------------------------------------------ H-C2 block types of the 21 DIRECT units
def hc2(quick: bool = False) -> dict:
    baseline, scenarios = C.oracle()
    ub = C.unit_by_id()
    bench = _bench()[: (1 if quick else 2)] + ([] if quick else [_edge("rebuild_within_period")])
    per_cell, n_cells = 8, (20 if quick else 60)
    probe_T = [k + 0.37 for k in range(n_cells)]
    delta = 1e-6
    grid = [k + (i + 0.5) / per_cell for k in range(n_cells) for i in range(per_cell)]
    t0 = time.perf_counter()
    per_scn = {}
    replay = {}
    for scn in bench:
        series = {u: [] for u in _direct()}
        s = copy.deepcopy(scn)
        n_out = 0
        for T in grid:
            s.boundary.study_period = T
            if scenarios.valid_domain(s):
                n_out += 1
            r = baseline.run_reference(s, _direct())
            for u in _direct():
                series[u].append(r[u]["value"])
        pr = {u: [] for u in _direct()}
        for T in probe_T:
            vals = []
            for TT in (T, T + delta):
                s.boundary.study_period = TT
                vals.append(baseline.run_reference(s, _direct()))
            for u in _direct():
                pr[u].append((vals[0][u]["value"], vals[1][u]["value"]))
        sig = {u: C.block_signature(grid, series[u], per_cell, pr[u]) for u in _direct()}
        # by_year replay: amplitudes read once at T_ref = n_cells, replayed through an integrator with w_k(T)
        s.boundary.study_period = float(n_cells)
        rref = baseline.run_reference(s, _direct())
        rp = {}
        for u in _direct():
            by = rref[u].get("by_year")
            if not by:
                continue
            errs = []
            for T, v in zip(grid, series[u]):
                rep = by[0] + sum(by[y] * min(max(T - (y - 1), 0.0), 1.0) for y in range(1, len(by)))
                errs.append(C.rel_err(rep, v) if v else abs(rep - v))
            rp[u] = {"max_rel_err": max(errs), "n_points_rel_gt_1e-9": sum(1 for e in errs if e > 1e-9),
                     "n_points": len(errs)}
        replay[scn.meta.scenario_id] = rp
        per_scn[scn.meta.scenario_id] = {"n_grid": len(grid), "n_grid_out_of_domain": n_out, "signatures": sig}
    rows = []
    for u in _direct():
        declared = C.blocks_from_text(ub[u]["time_form"])
        feats = set()
        for sid in per_scn:
            feats |= set(per_scn[sid]["signatures"][u]["features"])
        single = [b for b in C.BLOCKS if C.fits(feats, [b])]
        rows.append({"unit": u, "declared_blocks": declared, "observed_features_union": sorted(feats),
                     "consistent_with_declared": C.fits(feats, declared) and bool(declared),
                     "single_block_types_that_fit": single,
                     "needs_composite": not single})
    unfit = [r["unit"] for r in rows if not r["consistent_with_declared"]]
    return {
        "hypothesis": "H-C2", "verdict": ("PASS" if not unfit else "FAIL") if not quick else "PARTIAL(quick)",
        "grid": {"per_cell": per_cell, "n_cells": n_cells, "points": f"k+(i+0.5)/{per_cell}"},
        "scenarios": list(per_scn), "units": rows, "units_not_fitting_declared": unfit,
        "units_needing_composite": [r["unit"] for r in rows if r["needs_composite"]],
        "by_year_replay": replay, "per_scenario": per_scn, "wall_s": time.perf_counter() - t0,
        "note": "t=0 vs t=T placement of constants is not observable from V(T) (both 'const'); taken from ledger text.",
    }


# ------------------------------------------------------------------ H-C3 state count depends on the observable
def hc3(quick: bool = False) -> dict:
    baseline, scenarios = C.oracle()
    stages = C.refcalc_stages()
    bench = _bench()[: (1 if quick else 2)] + ([] if quick else [_edge("rebuild_within_period")])
    grid = [0.25 * j for j in range(1, 241)] if not quick else [0.5 * j for j in range(1, 61)]
    out = {}
    t0 = time.perf_counter()
    for scn in bench:
        s = copy.deepcopy(scn)
        Y = {st: [] for st in stages}
        U = {u: [] for u in _direct()}
        tot = []
        n_out = 0
        for T in grid:
            s.boundary.study_period = T
            if scenarios.valid_domain(s):
                n_out += 1
            r = baseline.run_reference(s, _direct() + ["X-02", "SUM-03"])
            for st in stages:
                Y[st].append(r["X-02"]["by_stage"][st])
            for u in _direct():
                U[u].append(r[u]["value"])
            tot.append(r["SUM-03"]["value"])
        res = {"n_T": len(grid), "n_T_out_of_domain": n_out}
        for rtol in (1e-7, 1e-9, 1e-11):
            rk_s, dg_s = C.rank_mod_const([Y[st] for st in stages], rtol)
            rk_u, dg_u = C.rank_mod_const([U[u] for u in _direct()], rtol)
            rk_t, _ = C.rank_mod_const([tot], rtol)
            res[f"rtol={rtol:g}"] = {"rank_total": rk_t, "rank_stage14": rk_s, "rank_direct21": rk_u,
                                     "stage_residuals": [float(f"{d:.3e}") for d in dg_s],
                                     "direct_residuals": [float(f"{d:.3e}") for d in dg_u]}
        varying = [st for st in stages if C.rank_mod_const([Y[st]], 1e-9)[0] == 1]
        res["T_varying_stages"] = varying
        res["T_varying_direct_units"] = [u for u in _direct() if C.rank_mod_const([U[u]], 1e-9)[0] == 1]
        # pairwise check: is any varying stage (numerically) a combination of the others?
        res["drop_one_rank_stage"] = {st: C.rank_mod_const([Y[x] for x in varying if x != st], 1e-9)[0] for st in varying}
        out[scn.meta.scenario_id] = res
    first = next(iter(out.values()))["rtol=1e-09"]
    return {"hypothesis": "H-C3", "grid": f"T=0.25..60 step 0.25 ({len(grid)} pts)" if not quick else "quick",
            "per_scenario": out, "wall_s": time.perf_counter() - t0,
            "summary_rtol_1e-9": {sid: {k: v["rtol=1e-09"][k] for k in ("rank_total", "rank_stage14", "rank_direct21")}
                                  for sid, v in out.items()},
            "predicted_H": {"rank_total": 1, "rank_stage14": 7},
            "prediction_7_per_scenario": {sid: ("MATCH" if v["rtol=1e-09"]["rank_stage14"] == 7 else
                                                f"MISMATCH(rank={v['rtol=1e-09']['rank_stage14']}, varying stages="
                                                f"{len(v['T_varying_stages'])})") for sid, v in out.items()},
            "rank_equals_number_of_varying_stages": all(v["rtol=1e-09"]["rank_stage14"] == len(v["T_varying_stages"])
                                                        for v in out.values()),
            "verdict": "PASS" if all(v["rtol=1e-09"]["rank_total"] == 1 and v["rtol=1e-09"]["rank_stage14"] > 1
                                     and v["rtol=1e-09"]["rank_stage14"] == len(v["T_varying_stages"])
                                     for v in out.values()) else "FAIL",
            "verdict_scope": "core claim 'state count depends on the observable' (total rank 1 < stage-vector rank); "
                             "the numeric '7' holds only when all of B1..B7 vary on the grid",
            "note": "rank modulo constants = number of linearly independent T-varying waveforms an LTI linear "
                    "read-out needs; a lower bound on independent accumulator outputs, not a full minimal-realisation proof."}


# ------------------------------------------------------------------ H-C4 non-DIRECT roles are not sources
def hc4(quick: bool = False) -> dict:
    baseline, scenarios = C.oracle()
    bench = _bench()[: (1 if quick else 2)]
    out = {}
    clos = C.refcalc_closure("SUM-03")
    for scn in bench:
        s = _at(scn, 30.0)
        r = baseline.run_reference(s)
        Cv = r["SUM-03"]["value"]
        e = {}
        # AUXILIARY: A5-01..03 are the parts of A5-04
        a5 = r["A5-01"]["value"] + r["A5-02"]["value"] + r["A5-03"]["value"]
        e["AUXILIARY:A5-01"] = {
            "identity": "A5-04 = A5-01 + A5-02 + A5-03", "rel_err_identity": C.rel_err(a5, r["A5-04"]["value"]),
            "add_A5-01_as_source_rel_change_of_C": r["A5-01"]["value"] / Cv,
            "add_A5-01_as_source_abs_kgCO2e": r["A5-01"]["value"], "upstream_of_SUM03": "A5-01" in clos,
            "why_wrong": "already inside A5-04 (DIRECT); adding it counts temporary electricity twice"}
        e["AUXILIARY:B4-01"] = {"keys": sorted(k for k in r["B4-01"] if not k.startswith("_")),
                                "n_events": r["B4-01"]["n_events"], "has_kgCO2e_value": "value" in r["B4-01"],
                                "why_wrong": "event grid (times, count); no kgCO2e value; feeds B4-02/B3-01 as schedule"}
        # DECISION: SYS-01 is not upstream of SUM-03; C unchanged when it is not computed
        rmin = baseline.run_reference(s, ["SUM-03"])
        e["DECISION:SYS-01"] = {
            "keys": sorted(k for k in r["SYS-01"] if not k.startswith("_")), "has_kgCO2e_value": "value" in r["SYS-01"],
            "upstream_of_SUM03": "SYS-01" in clos, "n_units_needed_for_SUM03": len(clos),
            "C_without_SYS01_equals_C": rmin["SUM-03"]["value"] == Cv, "SYS-01_computed_in_min_run": "SYS-01" in rmin,
            "why_wrong": "reports counts/ok; masks act inside each unit's own predicates; adding counts is dimensionally void"}
        # REFERENCE: B3-02 is an alternative estimate of B3
        e["REFERENCE:B3-02"] = {
            "B3-02_over_B3-01": r["B3-02"]["value"] / r["B3-01"]["value"],
            "add_as_source_rel_change_of_C": r["B3-02"]["value"] / Cv, "upstream_of_SUM03": "B3-02" in clos,
            "why_wrong": "second estimator of the same repair stage; adding it counts B3 about twice"}
        # AGGREGATE: SUM-03 is the node output itself; SUM-05 is a nonlinear read-out
        area = s.project.gross_floor_area
        e["AGGREGATE:SUM-03"] = {
            "add_as_source_rel_change_of_C": r["SUM-03"]["value"] / Cv,
            "SUM05_times_area_T_rel_err_vs_C": C.rel_err(r["SUM-05"]["value"] * area * 30.0, Cv),
            "upstream_of_SUM03": "SUM-03" in clos,
            "why_wrong": "it is the summing-node output (feedback would double C); SUM-04..07 are read-out arithmetic"}
        # BREAKDOWN: X-07 by-year series sums to C; X-08 equals B4-02
        e["BREAKDOWN:X-07"] = {
            "sum_by_year_rel_err_vs_C": C.rel_err(sum(r["X-07"]["by_year"]), Cv),
            "value_rel_err_vs_C": C.rel_err(r["X-07"]["value"], Cv),
            "X-08_rel_err_vs_B4-02": C.rel_err(r["X-08"]["value"], r["B4-02"]["value"]),
            "X-09_rel_err_vs_C3+C4": C.rel_err(r["X-09"]["value"], r["C3-01"]["value"] + r["C4-01"]["value"]),
            "add_X-07_as_source_rel_change_of_C": r["X-07"]["value"] / Cv, "upstream_of_SUM03": "X-07" in clos,
            "why_wrong": "branch-current read-out of the total; adding it doubles C"}
        # all 70 'value' fields as 70 sources (dimensionally inconsistent illustration)
        allv = sum(v["value"] for v in r.values() if isinstance(v.get("value"), (int, float))
                   and not isinstance(v.get("value"), bool))
        e["ALL70_value_fields_as_sources"] = {
            "n_units_with_numeric_value": sum(1 for v in r.values() if isinstance(v.get("value"), (int, float))
                                              and not isinstance(v.get("value"), bool)),
            "sum_over_C": allv / Cv,
            "note": "mixes kgCO2e, tCO2e, per-m2, kg-mass; shown only to quantify the error of '70 currents'"}
        out[scn.meta.scenario_id + "@T30"] = {"C": Cv, "examples": e}
    ok = all(ex["examples"]["AUXILIARY:A5-01"]["rel_err_identity"] <= 1e-12 and
             not ex["examples"]["DECISION:SYS-01"]["upstream_of_SUM03"] and
             ex["examples"]["DECISION:SYS-01"]["C_without_SYS01_equals_C"] and
             ex["examples"]["BREAKDOWN:X-07"]["value_rel_err_vs_C"] <= 1e-9 and
             ex["examples"]["AGGREGATE:SUM-03"]["add_as_source_rel_change_of_C"] == 1.0
             for ex in out.values())
    return {"hypothesis": "H-C4", "verdict": "PASS" if ok else "FAIL", "per_scenario": out,
            "refcalc_closure_SUM03_size": len(clos)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="inv,c1,c2,c3,c4")
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args(argv)
    todo = a.only.split(",")
    pyc_before = C.stray_pycache()
    if pyc_before:
        print("STOP: stray __pycache__ in frozen trees:", pyc_before)
        return 2
    prov = C.provenance()
    prov["frozen_trees"] = C.oracle()[0].assert_frozen()
    print("provenance", prov)
    suffix = "_quick" if a.quick else ""
    fns = {"inv": ("inventory", lambda q: inventory()), "c1": ("hc1", hc1), "c2": ("hc2", hc2),
           "c3": ("hc3", hc3), "c4": ("hc4", hc4)}
    for k in todo:
        name, fn = fns[k]
        t = time.perf_counter()
        res = fn(a.quick)
        res["provenance"] = prov
        res["elapsed_s"] = time.perf_counter() - t
        path = C.write_json(f"{name}{suffix}.json", res)
        brief = {kk: vv for kk, vv in res.items() if kk not in ("cases", "per_scenario", "comp_rows", "units",
                                                                  "by_year_replay", "provenance",
                                                                  "ledger_vs_refcalc_dep_differences")}
        print(f"== {name}: {path}")
        print(brief)
    pyc_after = C.stray_pycache()
    print("stray __pycache__ after run:", pyc_after)
    return 0 if not pyc_after else 3


if __name__ == "__main__":
    sys.exit(main())
