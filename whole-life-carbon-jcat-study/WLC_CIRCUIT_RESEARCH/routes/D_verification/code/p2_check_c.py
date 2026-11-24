"""Pass 2, route C checks (6) H-C1 independent composition = gate X4, (7) H-C3 exact ranks, (8) MAPPING.csv
spot check, (9) year-table replay counterexample; and gate X3 (B formula kinds vs C DIRECT block types).

Independence of the composition check (6): the per-unit values are NOT refcalc's. They are
  * B1-02/B1-03/B1-04: D's own exact refrigerant recurrence from RAW scenario inputs (p2_oracle_kernels),
  * other T-dependent units: D's own kernel evaluator h() applied to the msp/canon amplitude columns (P1),
  * the 12 constants: the msp P1 amplitudes (canon unit_terms),
composed with COMP rows read by D from units70.json, in exact Fraction arithmetic, and compared with
refcalc SUM-03 / X-02 (whose composition is refcalc's own X-02 code) and with canon's own total.
Run: PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0 python3 -B code/p2_check_c.py
"""
import copy, csv, json, math, os, random, re, sys, time
from fractions import Fraction as Fr
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import p2_common as C            # noqa: E402
import p2_oracle_kernels as K    # noqa: E402

UNITS_JSON = os.path.join(C.BASE, "data", "units70.json")
LEDGER_MD = os.path.join(C.BASE, "02_70評価単位の完全台帳.md")
C_MAP = os.path.join(C.RESEARCH, "routes", "C_70_units", "MAPPING.csv")
B_MAP = os.path.join(C.RESEARCH, "routes", "B_formula_network", "MAPPING.csv")
STAGES = ["A1-A3", "A4", "A5", "B1", "B2", "B3", "B4", "B5", "B6", "B7", "C1", "C2", "C3", "C4"]


def ledger():
    return json.load(open(UNITS_JSON, encoding="utf-8"))["units"]


def comp_rows_json():
    rows = []
    for u in ledger():
        comp = u.get("composition") or []
        for c in comp:
            rows.append((c["stage"], u["id"], int(c["sign"]), str(c["beta"])))
    return rows


class Evaluator:
    """D's per-unit exact values for one scenario (see module doc)."""

    def __init__(self, scn, canon, population):
        self.scn = scn
        self.sysm = canon.make_system(scn, population.BASELINES)
        self.can = canon.build(self.sysm)
        self.H = self.can.H
        self.inc = set(scn.boundary.included_lifecycle_stages or [])

    def units(self, T):
        v = {}
        for u, ts in self.can.unit_terms.items():
            if u in ("B1-04", "B1-04J"):
                continue
            v[u] = K.kernel_sum_rate(ts, T)     # canon Terms carry RATE amplitudes (chapter-17 kernel form); no windows here
        v.update(K.refrigerant(self.scn.refrigerants, T))   # overrides B1-02/B1-03 with the raw recurrence
        return v

    def compose(self, T, rows):
        V = self.units(T)
        stage = {}
        for s, u, sign, beta in rows:
            if s not in self.inc:
                continue
            b = Fr(1) if beta == "1" else (Fr(1) if "B2" in self.inc else Fr(0)) if beta == "iota_B2" else None
            if b is None:
                raise ValueError(beta)
            stage[s] = stage.get(s, Fr(0)) + sign * b * V.get(u, Fr(0))
        return stage, sum(stage.values(), Fr(0)), V


def check6(canon, population):
    rows = comp_rows_json()
    from specs import system as S_
    spec_rows = sorted((s, u, int(g)) for s, u, g in S_.COMP_ROWS)
    json_rows = sorted((s, u, g) for s, u, g, b in rows)
    res = {"comp_rows_units70_json": len(rows), "comp_rows_specs_system": len(spec_rows),
           "comp_rows_identical(stage,unit,sign)": spec_rows == json_rows,
           "non_trivial_beta": [r for r in rows if r[3] != "1"], "cases": []}
    Ts = [1.0, 9.999999, 10.0, 10.000001, 20.0, 30.0, 33.3, 47.9, 60.0]
    cases = list(C.d_scenarios(("EV6", "EV10", "BM-S")))
    s = copy.deepcopy(dict(cases)["EV6"])
    s.boundary.included_lifecycle_stages = [x for x in s.boundary.included_lifecycle_stages if x != "B2"]
    s.meta.scenario_id += "-noB2"
    cases.append(("EV6-noB2", s))
    s2 = copy.deepcopy(dict(cases)["EV10"])
    s2.boundary.included_lifecycle_stages = ["B1", "B4", "B6", "C3"]
    s2.meta.scenario_id += "-B1B4B6C3"
    cases.append(("EV10-subset", s2))
    worst = {"total_vs_refcalc": 0.0, "stage_vs_refcalc": 0.0, "total_vs_canon": 0.0, "refcalc_fraction_sum_vs_SUM03": 0.0}
    for tag, scn in cases:
        ev = Evaluator(scn, canon, population)
        for T in Ts:
            dom = C.in_domain(scn, T)
            r = C.ref(scn, T)
            stage, tot, V = ev.compose(T, rows)
            can_tot = sum((t.amp * t.h(T) for t in ev.can.terms), Fr(0))
            ref_stage = r["X-02"]["by_stage"]
            st_err = max([C.rel(stage.get(k, 0), v) for k, v in ref_stage.items()] + [0.0])
            keys_equal = set(stage) == set(ref_stage)
            # refcalc's own per-unit floats composed in exact arithmetic (separates float summation from rules)
            rf = {}
            for s_, u, sign, beta in rows:
                if s_ in ev.inc:
                    b = 1 if beta == "1" else (1 if "B2" in ev.inc else 0)
                    rf[s_] = rf.get(s_, Fr(0)) + sign * b * Fr(r[u]["value"])
            row = {"case": tag, "T": T, "valid_domain": dom[:1], "D_total": float(tot), "refcalc_SUM03": r["SUM-03"]["value"],
                   "rel_D_vs_refcalc": C.rel(tot, r["SUM-03"]["value"]), "rel_D_vs_canon": C.rel(tot, can_tot),
                   "stage_rel_max": st_err, "stage_keys_equal": keys_equal,
                   "rel_refcalc_units_exact_sum_vs_SUM03": C.rel(sum(rf.values(), Fr(0)), r["SUM-03"]["value"]),
                   "unit_rel_max": max(C.rel(V.get(u, 0), r[u]["value"]) for _, u, _, _ in rows)}
            res["cases"].append(row)
            if not dom:
                worst["total_vs_refcalc"] = max(worst["total_vs_refcalc"], row["rel_D_vs_refcalc"])
                worst["stage_vs_refcalc"] = max(worst["stage_vs_refcalc"], st_err)
                worst["total_vs_canon"] = max(worst["total_vs_canon"], row["rel_D_vs_canon"])
                worst["refcalc_fraction_sum_vs_SUM03"] = max(worst["refcalc_fraction_sum_vs_SUM03"],
                                                             row["rel_refcalc_units_exact_sum_vs_SUM03"])
    res["worst_in_domain"] = worst
    res["all_stage_keys_equal"] = all(r["stage_keys_equal"] for r in res["cases"])
    return res


# ---------------------------------------------------------------- exact rank
def exact_rank(rows):
    M = [list(r) for r in rows]
    rank, ncol = 0, len(M[0]) if M else 0
    for c in range(ncol):
        piv = next((i for i in range(rank, len(M)) if M[i][c] != 0), None)
        if piv is None:
            continue
        M[rank], M[piv] = M[piv], M[rank]
        p = M[rank][c]
        for i in range(len(M)):
            if i != rank and M[i][c] != 0:
                f = M[i][c] / p
                M[i] = [a - f * b for a, b in zip(M[i], M[rank])]
        rank += 1
    return rank


def check7(canon, population):
    m = C.frozen()
    rows = comp_rows_json()
    direct = sorted({u for _, u, _, _ in rows})
    edge = dict(m["scenarios"].edge_set())["rebuild_within_period"]
    out = {"grid": "T = 0.25..60 step 0.25 (240)", "direct_units": len(direct), "scenarios": {}}
    for tag, scn in list(C.d_scenarios(("BM-S", "BM-M", "EV6"))) + [("EDGE-rebuild", edge)]:
        ev = Evaluator(scn, canon, population)
        t0 = time.perf_counter()
        Ms, Md, Mt = [], [], []
        for i in range(1, 241):
            T = i / 4
            stage, tot, V = ev.compose(T, rows)
            Ms.append([Fr(1)] + [stage.get(s, Fr(0)) for s in STAGES])
            Md.append([Fr(1)] + [V.get(u, Fr(0)) for u in direct])
            Mt.append([Fr(1), tot])
        varying_st = [s for j, s in enumerate(STAGES) if len({r[j + 1] for r in Ms}) > 1]
        varying_u = [u for j, u in enumerate(direct) if len({r[j + 1] for r in Md}) > 1]
        rs, rd, rt = exact_rank(Ms) - 1, exact_rank(Md) - 1, exact_rank(Mt) - 1
        # float rank (numpy SVD) for comparison with C's numbers
        import numpy as np
        def frank(M, rtol):
            A = np.array([[float(x) for x in r[1:]] for r in M])
            nrm = np.linalg.norm(A, axis=0); nrm[nrm == 0] = 1      # scale by the ORIGINAL norm (as route C does):
            A = (A - A.mean(axis=0)) / nrm                         # a constant column then stays ~1e-16, not O(1)
            sv = np.linalg.svd(A, compute_uv=False)
            return int((sv > rtol * sv.max()).sum()) if sv.max() > 0 else 0
        out["scenarios"][tag] = {"scenario": scn.meta.scenario_id, "exact_rank_mod_const_total": rt,
                                 "exact_rank_mod_const_stage14": rs, "exact_rank_mod_const_direct21": rd,
                                 "float_rank_stage14(rtol 1e-9/1e-6)": [frank(Ms, 1e-9), frank(Ms, 1e-6)],
                                 "float_rank_direct21(rtol 1e-9/1e-6)": [frank(Md, 1e-9), frank(Md, 1e-6)],
                                 "T_varying_stages": varying_st, "T_varying_direct_units": varying_u,
                                 "seconds": round(time.perf_counter() - t0, 1)}
    out["interpretation"] = ("rank = dimension of the span of the sampled waveforms (lower bound on the span of the functions). "
                             "It bounds the number of independent accumulator OUTPUTS a fixed linear read-out needs; it does "
                             "not bound the realization state: every piecewise-linear waveform still needs its knots "
                             "(comparators/table entries), and rank 1 for the total does not mean one capacitor reproduces "
                             "C(T) without the 1e3-1e4 knot schedule.")
    return out


# ---------------------------------------------------------------- MAPPING spot check
def check8():
    led = {u["id"]: u for u in ledger()}
    text = open(LEDGER_MD, encoding="utf-8").read()
    rows = list(csv.DictReader(open(C_MAP, encoding="utf-8")))
    roles = {}
    for r in rows:
        roles[r["role"]] = roles.get(r["role"], 0) + 1
    sample = random.Random(20261124).sample(rows, 10)
    checks = []
    for r in sample:
        u = led[r["claim_or_unit_id"]]
        comp = u.get("composition") or []
        ok = {"role": r["role"] == u["role"], "stage": r["stage"] == u["stage"],
              "time_dependent": r["time_dependent"] == str(u["time_dependent"]),
              "time_form_text": r["time_form_text"].strip() == (u.get("time_form") or "").strip(),
              "comp_rows": len([x for x in r["comp_rows"].split(";") if x.strip()]) == len(comp),
              "id_in_ledger_text": r["claim_or_unit_id"] in text, "name_in_ledger_text": r["name"] in text}
        checks.append({"id": r["claim_or_unit_id"], "ok": ok, "status": r["status"], "evidence": r["evidence"],
                       "construct": r["target_circuit_construct"][:80], "class": r["circuit_class"]})
    flag = [r["claim_or_unit_id"] for r in rows if r["status"] in ("exact", "verified", "PASS")]
    no_h = [r["claim_or_unit_id"] for r in rows if "[H]" not in r["evidence"]]
    led_roles = {}
    for u in led.values():
        led_roles[u["role"]] = led_roles.get(u["role"], 0) + 1
    return {"n_rows": len(rows), "role_counts_mapping": roles, "role_counts_units70": led_roles,
            "sample_seed": 20261124, "sample": checks,
            "rows_with_status_exact_or_verified": flag,
            "rows_whose_evidence_lacks_[H]_for_design_columns": no_h,
            "status_counts": {s: sum(1 for r in rows if r["status"] == s) for s in sorted({r["status"] for r in rows})},
            "circuit_simulation_NOT_RUN_marked_on_DIRECT": sum(1 for r in rows if r["role"] == "DIRECT" and "NOT_RUN" in r["validation"])}


# ---------------------------------------------------------------- year-table replay
def check9():
    m = C.frozen()
    edge = dict(m["scenarios"].edge_set())["rebuild_within_period"]
    units = ["B1-02", "B1-03", "B3-01", "B4-02", "B5-01"]
    out = {}
    for tag, scn in list(C.d_scenarios(("BM-S", "BM-M"))) + [("EDGE-rebuild", edge)]:
        r60 = m["baseline"].run_reference(m["scenarios"].with_period(scn, 60.0), units)
        grid = [k + (i + 0.5) / 4 for k in range(60) for i in range(4)]
        res = {u: {"max_rel": 0.0, "max_abs_over_scale": 0.0, "n_rel_gt_1e-9": 0} for u in units if r60[u].get("by_year")}
        scale = {}
        series = {}
        for T in grid:
            r = m["baseline"].run_reference(m["scenarios"].with_period(scn, T), units)
            for u in res:
                series.setdefault(u, []).append((T, r[u]["value"]))
        for u in res:
            by = r60[u]["by_year"]
            sc = max(abs(v) for _, v in series[u]) or 1.0
            for T, v in series[u]:
                rep = Fr(by[0]) + sum((Fr(by[y]) * min(max(Fr(T) - (y - 1), Fr(0)), Fr(1)) for y in range(1, len(by))), Fr(0))
                e = C.rel(rep, v) if v else abs(float(rep))
                res[u]["max_rel"] = max(res[u]["max_rel"], e)
                res[u]["max_abs_over_scale"] = max(res[u]["max_abs_over_scale"], abs(float(rep) - v) / sc)
                res[u]["n_rel_gt_1e-9"] += e > 1e-9
            res[u]["n"] = len(series[u])
        out[tag] = res
    return out


# ---------------------------------------------------------------- X3
def x3():
    crow = [r for r in csv.DictReader(open(C_MAP, encoding="utf-8")) if r["role"] == "DIRECT"]
    brow = list(csv.DictReader(open(B_MAP, encoding="utf-8")))
    kind_to_block = {"K08": "const_t0", "K09": "const_tT", "K10": "year_cell", "K11": "year_cell", "K12": "density",
                     "K13": "atom", "K14": "gated_year_cell", "K19": "interval", "K17": "year_cell", "K18": "atom+gated_year_cell"}
    C_blocks = {}
    for r in crow:
        C_blocks[r["claim_or_unit_id"]] = set(x for x in re.split(r"[;,+ ]+", r["time_form_blocks"]) if x)
    c_types = set().union(*C_blocks.values())
    b_kinds_time = {r["kind_id"]: r["kind_name"] for r in brow}
    b_types = set()
    for k, b in kind_to_block.items():
        b_types |= set(b.split("+"))
    # per-unit: kinds whose example_units mention the unit
    ex = {}
    for r in brow:
        for u in re.findall(r"[A-Z]+\d*-\d+", r["example_units"]):
            ex.setdefault(u, set()).add(r["kind_id"])
    per_unit = {}
    for u, blocks in sorted(C_blocks.items()):
        kinds = sorted(ex.get(u, set()))
        mapped = set()
        for k in kinds:
            if k in kind_to_block:
                mapped |= set(kind_to_block[k].split("+"))
        per_unit[u] = {"C_blocks": sorted(blocks), "B_kinds_listing_unit": kinds, "B_kinds_as_blocks": sorted(mapped),
                       "C_only": sorted(blocks - mapped), "B_only": sorted(mapped - blocks)}
    b_only_kinds = sorted(k for k in b_kinds_time if k not in kind_to_block)
    return {"C_block_types_of_21_DIRECT": sorted(c_types), "B_kernel_kinds_mapped_to_block_types": sorted(b_types),
            "types_only_in_C": sorted(c_types - b_types), "types_only_in_B": sorted(b_types - c_types),
            "B_kinds_with_no_C_block_type": {k: b_kinds_time[k][:70] for k in b_only_kinds},
            "per_DIRECT_unit": per_unit, "kind_to_block_map_used(D's reading)": kind_to_block}


def main():
    C.frozen()
    canon, timechar, population = C.canon_modules()
    assert C.clean() == []
    t0 = time.perf_counter()
    res = {"check6_X4_composition": check6(canon, population)}
    res["check8_mapping"] = check8()
    res["X3"] = x3()
    res["check7_ranks"] = check7(canon, population)
    res["check9_year_table_replay"] = check9()
    res["seconds"] = round(time.perf_counter() - t0, 1)
    assert C.clean() == []
    C.dump("p2_check_c.json", res)
    s = {k: v for k, v in res["check6_X4_composition"].items() if k != "cases"}
    print(json.dumps({"c6": s, "c7": res["check7_ranks"], "c8": {k: v for k, v in res["check8_mapping"].items() if k != "sample"},
                      "c8_sample": [(x["id"], all(x["ok"].values()), {k: v for k, v in x["ok"].items() if not v}) for x in res["check8_mapping"]["sample"]],
                      "x3": {k: v for k, v in res["X3"].items() if k != "per_DIRECT_unit"},
                      "x3_units": {u: (v["C_only"], v["B_only"]) for u, v in res["X3"]["per_DIRECT_unit"].items()},
                      "c9": res["check9_year_table_replay"], "sec": res["seconds"]}, indent=1, default=str, ensure_ascii=False))


if __name__ == "__main__":
    main()
