#!/usr/bin/env python3
"""Approximate candidates measured against the reference calculation.

Each candidate replaces an exact step by something simpler. The signed relative error
(candidate - reference) / reference is collected on a population of fictional scenarios
for the quantity the candidate changes, overall and by structure, by use and - where the
candidate acts on material rows - by material class. Negative errors are under-estimations.

What a number here is measured on is stated with it:
  * ``stage`` names the primary quantity; ``by_stage`` holds the real stage values of the
    stage vector (X-02) a candidate changes, ``by_unit`` the own outputs of the units it is
    attached to (``bench.approx_meta`` is the single source of that attachment);
  * ``local_total_error`` is the difference of the changed quantity divided by the
    whole-life total; ``propagated_total_error`` is measured by re-running the reference
    calculation with the approximated input, so that everything downstream follows;
  * ``parameters_from`` says whether representative parameters come from the evaluated
    building itself (in-sample) or from other buildings (train/test split);
  * ``inputs`` and ``load`` say what a candidate needs and costs next to the exact form.

Parts: ``bench.approx_meta`` (what each candidate is and which units it is attached to),
``bench.approx_measures`` (the measurements on one scenario), ``bench.approx_support``
(collectors, reversible scenario rewrites, the kernels whose load is compared); this
module runs the population, fits the candidates that learn from other buildings and
assembles the result.

All data are synthetic. A measurement on fictional data can refute a candidate; it
cannot establish practical accuracy.

Run:  cd research_code && python3 -m bench.approx_study [--population 400] [--out PATH]
      (--out defaults to 04_VERIFICATION/approximation_study.json of the study)
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

from fastcalc import closed_forms as cf
from refcalc import registry
from refcalc.units_pre_a import SIMPLE_CLASSES, simple_class, summary_quantity
from synth import population

from bench import approx_support as sp
from bench.approx_measures import (B5_LABEL, C2_LABEL, COUNT_FORMS, STAGES14, X12_LABEL, One, Study, boundary_case, m_annual_tables,
                                   m_class_models, m_composites, m_counts, m_electricity, m_gases, m_material_rows, m_refrigerants,
                                   m_transport, renewal_rows, sign_guarantee, stress_repairs)
from bench.approx_meta import DECL, LOAD_NOT_THE_REASON, NOT_PROPAGATED, PROPAGATED, evidence_scope, order_key
from bench.approx_support import TARGET_STAGE, TARGET_TOTAL, Collector, Series, stats

__all__ = ["run", "main", "finish", "renewal_rows", "COUNT_FORMS", "OUT"]      # renewal_rows / COUNT_FORMS: kept importable from here

STUDY = Path(__file__).resolve().parents[2]
OUT = STUDY / "04_VERIFICATION" / "approximation_study.json"
ANNUAL = ("B1", "B2", "B3", "B4", "B5", "B6", "B7")
SYNTH_NOTE = "誤差は建物ごとの資材構成・係数や条件のばらつき・使用量の分布で決まる。ここでの値は架空の母集団上のもので、実建物での精度を示さない。"


# ----------------------------------------------------------------- assembling the result of one candidate

def finish(cid: str, col: Collector, X: Study) -> dict:
    d = DECL[cid]
    s = col.primary.result()
    local = stats(col.local_total)
    by_class, class_zero = col.class_result()
    by_stage = {k: v.result() for k, v in col.stages.items()}
    by_unit = col.unit_result()
    if not set(by_unit) <= set(d["units"]):
        raise SystemExit(f"{cid}: declared units {sorted(d['units'])} but measured on the own output of {sorted(by_unit)}")
    for uid in d["units"]:
        if uid not in by_unit:                           # no scenario of this population had a case for the unit
            by_unit[uid] = {}
            X.unmeasured.append(f"{cid}:{uid}")
    by_unit = {uid: by_unit[uid] for uid in d["units"]}
    out = {"candidate_id": cid, "title": d["title"], "replaces": d["replaces"], "stage": d["stage"], "units": d["units"],
           "units_stage_level": d["units_stage_level"], "scope": d["scope"], "evidence_scope": evidence_scope(d), "step": d["step"]}
    for key in ("stage_note", "units_note", "variant_of", "renamed_from", "note"):
        if key in d:
            out[key] = d[key]
    out["parameters_from"] = d["parameters_from"]
    for key in ("parameters_note", "keeps_row_membership"):
        if key in d:
            out[key] = d[key]

    propagated = stats(col.prop_total) if col.prop_n else None
    prop_stage = {k: col.prop_stages[k].result() for k in STAGES14 if k in col.prop_changed}
    if d["downstream_reuse"] == PROPAGATED:
        if not col.prop_n and s.get("n"):
            raise SystemExit(f"{cid}: declared as propagated but no propagated run was recorded")
        propagation = {"measured": True, "how": d["propagation_how"], "n": col.prop_n,
                       "rewrite_reproduces_local_candidate_max_rel_diff": col.prop_check, "stage_error": prop_stage}
    elif d["downstream_reuse"] == NOT_PROPAGATED:
        propagation = {"measured": False, "reason": d.get("propagation_reason") or (
            "この候補が変える量は下流の段階（B3・B4・B5）でも使われるが、候補は合計だけを出し、行ごとの値を出さないので、下流へ渡す値がない。"
            "local_total_error は下流への波及を含まない。")}
    elif d["downstream_reuse"] is None:
        propagation = {"measured": False, "reason": "候補が合計そのもの（または段階合計に入らない量）を出すので、波及の対象がない。"}
    else:
        propagation = {"measured": False, "reason": "この候補が変える量は、ほかの段階の計算に使われない。local_total_error が建物合計への影響の全部である。"}
    total = propagated if propagated and propagated.get("n") else local
    out.update(stage_error=s, local_total_error=local, propagated_total_error=propagated,
               total_error_kind="PROPAGATED" if propagated and propagated.get("n") else ("LOCAL" if local.get("n") else None),
               downstream_reuse=d["downstream_reuse"], propagation=propagation,
               by_group={k: stats(v) for k, v in sorted(col.groups.items())}, by_material_class=by_class)
    if by_class is None:
        out["by_material_class_reason"] = d.get("no_class_reason", "この母集団には、区分ごとの誤差を作れるシナリオがなかった。")
    else:
        out["by_material_class_zero_reference"] = class_zero
    out.update(n_reference_zero=col.primary.zero, n_reference_zero_candidate_nonzero=col.primary.zero_nonzero)
    if by_stage:
        out["by_stage"] = by_stage
    judged = [("primary", d["stage"], s)] if d["stage"] in STAGES14 else []
    judged += [("by_stage", k, v) for k, v in by_stage.items()] + [("propagation", k, v) for k, v in prop_stage.items()]
    judged = [j for j in judged if j[2].get("n")]
    if judged:
        src, name, worst = max(judged, key=lambda j: j[2]["max_abs"])
        out["worst_stage"] = {"stage": name, "measured_in": src, "max_abs": worst["max_abs"], "max_over": worst["max_over"],
                              "max_under": worst["max_under"]}
    else:
        out["worst_stage"] = None
    out["by_unit"] = by_unit
    # units whose own output is under-estimated in some case, whatever the sign on the primary quantity
    out["units_under_estimated"] = [uid for uid, qs in by_unit.items()
                                    if any(e["error"].get("n") and e["error"]["max_under"] < -1e-9 for e in qs.values())]
    if col.extra:
        out["other_targets"] = {k: v.result() for k, v in col.extra.items()}
    out.update(within_stage_target=sp.within(s, TARGET_STAGE) and all(sp.within(j[2], TARGET_STAGE) for j in judged),
               within_total_target=(total["max_abs"] <= TARGET_TOTAL) if total.get("n") else None,
               under_estimates=bool(s.get("n")) and s["max_under"] < -1e-9)
    a = X.inputs.get(cid)
    if a and a[2]:
        out["inputs"] = {"unit": d["inputs_unit"], "exact": a[0] / a[2], "candidate": a[1] / a[2], "n_scenarios": a[2], "text": d["inputs_text"]}
        out["inputs_measured"] = True
    else:
        out["inputs"] = {"text": d["inputs_text"]}
        out["inputs_measured"] = False
    out["load"] = {"measured": False, "reason": d.get("load_reason", LOAD_NOT_THE_REASON)}
    out.update(X.extra[cid])
    return out


def cases(X: Study, prefix: str, kernels: dict, note: str | None = None) -> dict:
    """Load results of a candidate measured under several input conditions."""
    found = {label: X.load.result(f"{prefix}:{key}", kernel) for key, (label, kernel) in kernels.items()}
    found = {k: v for k, v in found.items() if v["measured"]}
    if not found:
        return {"measured": False, "reason": "負荷を測る標本のシナリオに、この候補が当てはまる場合がなかった。"}
    out = {"measured": True, "unit": "executed bytecode instructions (sys.monitoring, INSTRUCTION events)", "cases": found}
    if note:
        out["note"] = note
    return out


# ----------------------------------------------------------------- the study

def run(n_population: int, load_every: int = 20, stress_seeds: int = 20, n_period_scenarios: int = 80) -> dict:
    registry.load_all()
    X = Study()
    C = X.C
    kept = []                                           # the first scenarios, for AP-14
    n = 0
    for scn in population.verification_population(n_population, seed=20261111, max_size="M"):
        res = registry.run_all(scn)
        S = One(scn, res, load=bool(load_every) and n % load_every == 0)
        n += 1
        if S.load:
            X.load.scenarios.append(scn.meta.scenario_id)
        if len(scn.boundary.included_lifecycle_stages) != len(STAGES14):
            X.excluded_stage_scenarios += 1
        T, stage, wlc = S.T, S.stage, S.wlc
        m_counts(S, X)
        cls_rec = m_class_models(S, X)
        m_refrigerants(S, X)
        mat = m_material_rows(S, X)
        m_composites(S, X)
        m_transport(S, X)
        m_electricity(S, X)
        m_annual_tables(S, X)
        m_gases(S, X)

        # ---- data for population-level candidates
        emis = mat["emis"]
        class_e = {k: 0.0 for k in SIMPLE_CLASSES}
        for i, row in enumerate(scn.materials):
            k = simple_class(row)
            if k is not None:
                class_e[k] += emis[i]
        sq = scn.summary_quantities
        sto = res["STO-01"]["value"]
        rec = {"group": S.group, "structure": scn.meta.structure, "use": scn.meta.use, "T": T,
               "area": scn.project.gross_floor_area, "wlc": wlc, "stage": dict(stage), "class_e": class_e,
               "class_q": {k: summary_quantity(scn, k) for k in SIMPLE_CLASSES}, "mat_ref": mat["mat_ref"],
               "co2": res["X-05"]["value"], "total_inc": S.sum03, "sto": sto, "timber": sq.timber_m3 if sto else None,
               "x17": res["X-17"]["value"], "sum03": S.sum03, "sum04": res["SUM-04"]["value"], "sum05": res["SUM-05"]["value"],
               "all_stages": len(scn.boundary.included_lifecycle_stages) == len(STAGES14),
               "n_rows": len(scn.materials) + len(scn.equipment) + len(scn.refrigerants), "n_materials": len(scn.materials)}
        rec.update(cls_rec)
        X.records.append(rec)
        if len(kept) < n_period_scenarios:
            kept.append(scn)
    records = X.records

    out = {}
    extra = X.extra
    # ---- pieces that belong to single candidates
    for cid, _ in COUNT_FORMS:
        t = X.b5[cid]
        b5_stats = t.primary.result()
        C[cid].units.setdefault("B5-01", {})["値（= 段階 B5。建替・大型改修の回数に適用）"] = {"level": "SCENARIO", "role": "REPLACED", "series": t.primary}
        x10 = C[cid].units["X-10"]
        extra[cid]["other_targets"] = {
            B5_LABEL: {"stage_error": b5_stats, "local_total_error": stats(t.local_total),
                       "n_reference_zero": t.primary.zero, "n_reference_zero_candidate_nonzero": t.primary.zero_nonzero},
            "X-10 資源量[kg]": x10["資源量[kg]"]["series"].result(), "X-10 廃棄物量[kg]": x10["廃棄物量[kg]"]["series"].result(),
            "X-08": "合計は B4-02 と同じ値なので、B4 の誤差がそのまま当てはまる。"}
        extra[cid]["load"] = X.load.result(cid, "fastcalc.closed_forms.renewal_count",
                                           "行ごとに 1 回ずつ評価した場合の命令数。統合モデルは回数を周期の値ごとに 1 回だけ求める（n_distinct_cycles）。")
    bound_text = ("基準計算の回数は N = ceil(T·c0/c) − 1（c0 は 1 − 1e-9 に最も近い倍精度数）なので、T·c0/c − 1 ≤ N < T·c0/c が成り立つ。"
                  "T/c − 1 ≤ N は、T/c が整数を相対 1e-9 以内で上回る周期では成り立たない（評価期間の終わりの相対 1e-9 以内の更新を数えないため）。"
                  "上限 N ≤ T/c は常に成り立つ。")
    boundary = boundary_case()
    extra["AP-01"]["bound"] = {"statement": bound_text, "near_boundary_scenario": boundary}
    extra["AP-04"]["load"] = X.load.result("AP-04", "fastcalc.closed_forms.skip_weight_periodic (with renewal_count)",
                                           "行ごとに 1 回ずつ評価した場合の命令数。統合モデルは周期の値ごとに 1 回だけ求める（n_distinct_cycles）。")
    for cid in ("AP-05a", "AP-05b"):
        extra[cid]["by_rate_times_cycle_years_no_top_up_devices"] = {k: v.result() for k, v in X.guard[cid].items()}
        extra[cid]["load"] = X.load.result(cid, "fastcalc.closed_forms.refrigerant_fractions (with the event years)")
    extra["AP-06"]["load"] = X.load.result("AP-06", "q / (1 - w)")
    for cid in ("AP-07a", "AP-07b"):
        extra[cid]["load"] = X.load.result(cid, "sum of mass fraction x component factor over all components",
                                           "行ごとに 1 回ずつ評価した場合の命令数。統合モデルは複合係数を配合の内容ごとに 1 回だけ求める（n_distinct_recipes）。")
    extra["AP-08"].update(
        by_profile_kind={k: v.result() for k, v in X.kind8["B6"].items()},
        by_profile_kind_stage_B2={k: v.result() for k, v in X.kind8["B2"].items()},
        by_profile_kind_B6_03={k: v.result() for k, v in X.kind8["B6-03"].items()},
        load=cases(X, "AP-08", {"closed": ("記述子で与えられ、打ち切りが働かない場合（閉形式どうし）", "B*G + S*H with fastcalc.closed_forms.segment_moments"),
                                "scan": ("年ごとに走査する場合（年次表、または打ち切りが働く場合）", "year scan of w * net * g")}))
    for cid in ("AP-09a", "AP-09b"):
        by = X.grid9.get(cid, {})
        extra[cid].update(
            by_grid_kind={k: v.result() for k, v in sorted(by.get("B6", {}).items())},
            by_grid_kind_stage_B2={k: v.result() for k, v in sorted(by.get("B2", {}).items())},
            by_grid_kind_B6_03={k: v.result() for k, v in sorted(by.get("B6-03", {}).items())},
            inputs_by_grid_source={src: {"exact": a[0] / a[2], "candidate": a[1] / a[2], "n_scenarios": a[2]}
                                   for src in ("DESCRIPTOR", "TABLE") for a in [X.inputs.get(f"{cid}|{src}")] if a},
            load=cases(X, cid, {"DESCRIPTOR": ("記述子で与えられる系列", "fastcalc.closed_forms.segment_moments (with grid_segments)"),
                                "TABLE": ("年次表で与えられる系列", "fastcalc.closed_forms.table_moments")},
                       "累積係数 G(T)・H(T) を求める命令数。候補は、粗い表から年ごとの値を作り直してから走査する。"))
    extra["AP-09c"].update(
        n_scenarios_computed_exactly=X.exact_scenarios["AP-09c"], data_dependence=SYNTH_NOTE,
        load=X.load.result("AP-09a:TABLE", "fastcalc.closed_forms.table_moments",
                           "年次表の系列だけに当てはめるので、AP-09a の年次表の場合と同じ。候補は入力の値が減るが、命令数は増える。"))
    for cid in ("AP-12", "AP-13", "AP-17", "AP-18", "AP-18a", "AP-18b", "AP-18c", "AP-19a", "AP-19c", "AP-23b", "AP-24a", "AP-24b"):
        extra[cid]["data_dependence"] = SYNTH_NOTE
    xs = [p[1] for p in X.cov["pairs"]]
    ys = [p[0] for p in X.cov["pairs"]]
    extra["AP-17"].update(
        other_targets={X12_LABEL: C["AP-17"].units["X-12"]["値（参考値）"]["series"].result(),
                       C2_LABEL: C["AP-17"].units["C2-01"]["値（= 段階 C2。搬出距離を単純平均に置換）"]["series"].result()},
        covariance_identity={
            "statement": "輸送手段ごとに Σm·d − (Σm)·(d の単純平均) = Σ(m − m の平均)(d − d の平均) なので、A4-01 の行の合計に対する候補の誤差は、"
                         "輸送手段内の質量と距離の標本共分散（×係数）の符号を変えたものに等しい。標本共分散が 0（距離がそろう、質量がそろう、など）のときだけ厳密になる。",
            "n_scenarios": X.cov["n"], "worst_relative_residual": X.cov["worst"]},
        realised_within_mode_correlation={
            "definition": "輸送手段ごとの質量と距離のピアソン相関（行が 5 以上で分散が 0 でない手段）を、手段の基準排出で重み付けして平均したシナリオごとの値。"
                          "架空データでは距離を質量と独立に生成している。",
            "n": len(xs), "mean": sum(xs) / len(xs) if xs else None, "min": min(xs) if xs else None, "max": max(xs) if xs else None,
            "correlation_with_scenario_error": pearson(xs, ys),
            "share_of_scenarios_where_positive_correlation_goes_with_under_estimation": (
                sum((x > 0) == (y < 0) for x, y in zip(xs, ys)) / len(xs) if xs else None)})
    extra["AP-22a"]["load"] = {"measured": False, "reason": "負荷は測っていない。不採用の理由は誤差（必ず過小）であり、計算負荷ではない。"}
    extra["AP-23a"].update(
        load=X.load.result("AP-23a", "fastcalc.closed_forms.skip_weight_periodic (with renewal_count)",
                           "行ごとに 1 回ずつ評価した場合の命令数。統合モデルは周期の値ごとに 1 回だけ求める（n_distinct_cycles）。"))
    extra["AP-23b"]["load"] = X.load.result("AP-23b", "fastcalc.closed_forms.skip_weight_periodic (with renewal_count), one call per row",
                                            "候補は区分ごとに 1 回（n_classes）、厳密な閉形式は行ごとに 1 回評価した場合の命令数。区分の 2 つの値を行から作る手間は含めていない。")
    extra["AP-24a"].update(
        n_scenarios_computed_exactly=X.exact_scenarios["AP-24a"],
        load=X.load.result("AP-24a", "year scan of the table (bench.approx_support.weighted_table)",
                           "候補は入力の値が減るが、粗い表から年ごとの値を作り直すので命令数は増える。"))
    extra["AP-24b"]["n_scenarios_computed_exactly"] = X.exact_scenarios["AP-24b"]

    # ---- stress scenarios and the sign guarantee of the safe-side repair forms
    stress = stress_repairs(stress_seeds)
    guarantee = sign_guarantee(X.below_one_year)
    for cid, key in (("AP-23a", "row"), ("AP-23b", "cls")):
        extra[cid]["stress_scenarios"] = {
            "note": "評価期間に近い架空の周期だけを持つシナリオ（生成器の service_life_choices で指定、明示の更新年一覧なし）。母集団の値とは別に集計した。",
            "cases": [{"study_period": c["T"], "service_life_choices": c["lives"], "n": c["n"], "stage_error": stats(c[key]),
                       "local_total_error": stats(c[key + "_total"]), "ap04_stage_error": stats(c["ap04"])} for c in stress],
            "stage_error_all_cases": stats([e for c in stress for e in c[key]]),
            "within_stage_target": all(abs(e) <= TARGET_STAGE for c in stress for e in c[key]) if stress else None}
        extra[cid]["sign_guarantee"] = guarantee

    for cid in DECL:
        if cid in ("AP-06b", "AP-20", "AP-10", "AP-10b", "AP-11", "AP-14", "AP-15", "AP-16", "AP-18d", "AP-21", "AP-22b", "AP-23c"):
            continue
        out[cid] = finish(cid, C[cid], X)
    for cid in ("AP-23a", "AP-23b"):                     # the stress scenarios count: the worst measured case decides
        c = out[cid]
        c["within_stage_target_on_population"] = c["within_stage_target"]
        c["within_stage_target"] = bool(c["within_stage_target"] and c["stress_scenarios"]["within_stage_target"])

    # ---- AP-06b (row level) and AP-20 (a bracket, not a point estimate)
    d = DECL["AP-06b"]
    x13 = C["AP-06b"].units["X-13"]["行ごとの正味発注量"]["series"].result()
    out["AP-06b"] = {"candidate_id": "AP-06b", "step": d["step"], "stage": d["stage"], "units": d["units"],
                     "units_stage_level": d["units_stage_level"], "scope": d["scope"], "evidence_scope": evidence_scope(d),
                     "title": d["title"], "replaces": d["replaces"], "parameters_from": None, "row_error": x13,
                     "note": "行ごとの数量は単位が行によって違うため、行ごとの相対誤差を集めた（シナリオ合計ではない）。",
                     "local_total_error": {"n": 0}, "propagated_total_error": None, "total_error_kind": None, "downstream_reuse": None,
                     "propagation": {"measured": False, "reason": "X-13 は参考値で、段階合計に使われない。"},
                     "by_material_class": None, "by_material_class_reason": d["no_class_reason"], "by_unit": C["AP-06b"].unit_result(),
                     "units_under_estimated": ["X-13"] if x13.get("n") and x13["max_under"] < -1e-9 else [],
                     "within_stage_target": None, "within_total_target": None,
                     "under_estimates": bool(x13.get("n")) and x13["max_under"] < -1e-9,
                     "inputs": {"text": d["inputs_text"]}, "inputs_measured": False,
                     "load": X.load.result("AP-06b", "q_inst * (1 + w*(1 - rho)/(1 - w))")}
    d = DECL["AP-20"]
    b = X.bracket
    lower, upper = b["lower"].result(), b["upper"].result()
    out["AP-20"] = {"candidate_id": "AP-20", "step": d["step"], "stage": d["stage"], "units": d["units"],
                    "units_stage_level": d["units_stage_level"], "scope": d["scope"], "evidence_scope": evidence_scope(d),
                    "title": d["title"], "replaces": d["replaces"], "parameters_from": None, "n": b["n"],
                    "share_reference_inside_bracket": b["inside"] / b["n"] if b["n"] else None,
                    "share_reference_inside_bracket_tolerance_form": b["inside_tolerance_form"] / b["n"] if b["n"] else None,
                    "n_including_near_boundary_scenario": b["n"] + 1,
                    "share_reference_inside_bracket_including_near_boundary_scenario": (
                        (b["inside"] + boundary["inside_with_lower_bound_T_over_c_minus_1"]) / (b["n"] + 1)),
                    "inside_test": "下限 ≤ B4×(1＋1e-12) かつ B4 ≤ 上限×(1＋1e-12)（1e-12 は和の丸めの分）。tolerance_form は下限を Σu·max(0, T(1−1e-9)/c − 1) とした場合。",
                    "bracket_width_relative_to_reference": stats(b["width"]),
                    "lower_bound_error": lower, "upper_bound_error": upper,
                    "bound": {"statement": bound_text, "near_boundary_scenario": boundary},
                    "local_total_error": {"n": 0}, "propagated_total_error": None, "total_error_kind": None, "downstream_reuse": d["downstream_reuse"],
                    "propagation": {"measured": False, "reason": "点推定ではないので、合計の誤差を作れない。"},
                    "by_material_class": None, "by_material_class_reason": d["no_class_reason"],
                    "by_unit": {"B4-02": {"値（= 段階 B4）の下限": {"level": "SCENARIO", "role": "REPLACED", "error": lower},
                                          "値（= 段階 B4）の上限": {"level": "SCENARIO", "role": "REPLACED", "error": upper}}},
                    "within_stage_target": None, "within_total_target": None, "under_estimates": None,
                    "inputs": {"text": d["inputs_text"]}, "inputs_measured": False,
                    "load": {"measured": False, "reason": "負荷は測っていない。上下限は AP-01 と AP-03 の回数の式 2 つを評価するので、命令数はその 2 つの和になる。"}}

    # ---- population-level candidates: fit on the first half, test on the second half
    half = len(records) // 2
    train, test = records[:half], records[half:]
    grp = lambda r: r["group"]

    def group_mean(rows, value):
        acc = {}
        for r in rows:
            v = value(r)
            if v is None:
                continue
            s = acc.setdefault(grp(r), [0.0, 0])
            s[0] += v
            s[1] += 1
        return {k: s[0] / s[1] for k, s in acc.items()}

    def own_totals(col, r, estimate):
        """SUM-03, SUM-04 and SUM-05 of a scenario that includes every stage, against an estimate of the total."""
        if not r["all_stages"]:
            return
        col.unit("SUM-03", "値").add(r["sum03"], estimate)
        col.unit("SUM-04", "値（合計÷延床面積）").add(r["sum04"], estimate / r["area"])
        col.unit("SUM-05", "値（合計÷（延床面積×評価年数））").add(r["sum05"], estimate / (r["area"] * r["T"]))

    # AP-10 / AP-10b: class-representative factors per (structure, use), without and with a gross-up for the other rows
    fbar = {}
    for k in SIMPLE_CLASSES:
        num, den = group_mean(train, lambda r, k=k: r["class_e"][k]), group_mean(train, lambda r, k=k: r["class_q"][k])
        fbar[k] = {g: (num[g] / den[g] if den[g] else 0.0) for g in num}
    gross = group_mean(train, lambda r: r["mat_ref"] / sum(r["class_e"].values()) if sum(r["class_e"].values()) else None)
    c10, c10b = C["AP-10"], C["AP-10b"]
    by_summary = {k: Series() for k in SIMPLE_CLASSES}
    for r in test:
        if grp(r) not in fbar["CONCRETE"]:
            continue
        approx = sum(r["class_q"][k] * fbar[k][grp(r)] for k in SIMPLE_CLASSES)
        c10.add(grp(r), r["mat_ref"], approx, r["wlc"])
        c10.unit("X-17", "値（6 区分の製造排出の合計）").add(r["x17"], approx)
        for k in SIMPLE_CLASSES:
            by_summary[k].add(r["class_e"][k], r["class_q"][k] * fbar[k][grp(r)])
        X.inp("AP-10", r["n_materials"], len(SIMPLE_CLASSES))
        if grp(r) in gross:
            c10b.add(grp(r), r["mat_ref"], approx * gross[grp(r)], r["wlc"])
            X.inp("AP-10b", r["n_materials"], len(SIMPLE_CLASSES))
    extra["AP-10"].update(data_dependence=SYNTH_NOTE, by_summary_class={k: v.result() for k, v in by_summary.items()})
    extra["AP-10b"]["data_dependence"] = SYNTH_NOTE
    out["AP-10"], out["AP-10b"] = finish("AP-10", c10, X), finish("AP-10b", c10b, X)

    # AP-11: whole-life total per floor area and year from (structure, use) group means
    c11 = C["AP-11"]
    mean_int = group_mean(train, lambda r: r["wlc"] / (r["area"] * r["T"]))
    for r in test:
        if grp(r) in mean_int:
            estimate = mean_int[grp(r)] * r["area"] * r["T"]
            c11.add(grp(r), r["wlc"], estimate, r["wlc"])
            own_totals(c11, r, estimate)
            X.inp("AP-11", r["n_rows"], 4)
    extra["AP-11"]["data_dependence"] = SYNTH_NOTE
    out["AP-11"] = finish("AP-11", c11, X)

    # AP-15: every stage from floor area (x study years for the use stages) times a (structure, use) mean intensity
    scale = lambda r, st: r["area"] * r["T"] if st in ANNUAL else r["area"]
    mean_stage = {st: group_mean(train, lambda r, st=st: r["stage"][st] / scale(r, st)) for st in STAGES14}
    c15 = C["AP-15"]
    single = {"A5": "A5-04", "B2": "B2-01", "B3": "B3-01", "B4": "B4-02", "B5": "B5-01", "B7": "B7-04", "C1": "C1-01", "C2": "C2-01", "C4": "C4-01"}
    for st in STAGES14:
        series = Series()
        for r in test:
            if grp(r) in mean_stage[st] and r["stage"][st] > 0.0:
                series.add(r["stage"][st], mean_stage[st][grp(r)] * scale(r, st), ratio_form=True)
        c15.stages[st] = series
        c15.units.setdefault("X-02", {})[f"段階 {st} の値"] = {"level": "SCENARIO", "role": "REPLACED", "series": series}
        if st in single:
            c15.units.setdefault(single[st], {})[f"値（= 段階 {st}）"] = {"level": "SCENARIO", "role": "REPLACED", "series": series}
    for r in test:
        if grp(r) in mean_int:
            est = {st: mean_stage[st][grp(r)] * scale(r, st) for st in STAGES14}
            estimate = sum(est[st] for st in STAGES14)
            c15.add(grp(r), r["wlc"], estimate, r["wlc"])
            if r["all_stages"]:
                c15.unit("SUM-01", "値（A1-A3＋A4＋A5）").add(sum(r["stage"][st] for st in ("A1-A3", "A4", "A5")),
                                                          sum(est[st] for st in ("A1-A3", "A4", "A5")))
                c15.unit("SUM-02", "値（B6・B7 を除く 12 段階）").add(sum(r["stage"][st] for st in STAGES14 if st not in ("B6", "B7")),
                                                              sum(est[st] for st in STAGES14 if st not in ("B6", "B7")))
                c15.unit("SUM-03", "値").add(r["sum03"], estimate)
            X.inp("AP-15", r["n_rows"], 4)
    extra["AP-15"]["data_dependence"] = SYNTH_NOTE
    out["AP-15"] = finish("AP-15", c15, X)

    # AP-16: log-linear least-squares regression of the whole-life total
    import numpy as np
    structures = sorted({r["structure"] for r in records})
    uses = sorted({r["use"] for r in records})

    def features(r):
        return ([1.0, math.log(r["area"]), math.log(r["T"])] + [1.0 if r["structure"] == x else 0.0 for x in structures[1:]]
                + [1.0 if r["use"] == x else 0.0 for x in uses[1:]])

    beta, *_ = np.linalg.lstsq(np.array([features(r) for r in train]), np.array([math.log(r["wlc"]) for r in train]), rcond=None)
    c16 = C["AP-16"]
    for r in test:
        estimate = math.exp(float(np.dot(features(r), beta)))
        c16.add(grp(r), r["wlc"], estimate, r["wlc"])
        own_totals(c16, r, estimate)
        X.inp("AP-16", r["n_rows"], 4)
    extra["AP-16"].update(n_parameters=int(len(beta)), data_dependence=SYNTH_NOTE)
    out["AP-16"] = finish("AP-16", c16, X)

    # AP-14: whole-life total at another study period by linear interpolation between two evaluated periods
    c14 = C["AP-14"]
    by_own = {"own_period>=75": [], "own_period<75": []}
    continued = {"all": [], "own_period>=75": [], "own_period<75": []}
    not_continued = 0

    def interpolated(scn, edit=None):
        vals = {}
        for T2 in (50.0, 60.0, 75.0):                 # same building, only the study period changes
            def change(p, T2=T2):
                p.set(scn.boundary, "study_period", T2)
                if edit is not None:
                    edit(p)
            vals[T2] = sp.rerun(scn, change, ["SUM-03"])["SUM-03"]["value"]
        return vals[60.0], vals[50.0] + (vals[75.0] - vals[50.0]) * 10.0 / 25.0

    for scn in kept:
        own_T = scn.boundary.study_period
        ref60, cand60 = interpolated(scn)
        c14.add((scn.meta.structure, scn.meta.use), ref60, cand60, ref60)
        c14.unit("SUM-03", "値（T=60）").add(ref60, cand60)
        key = "own_period>=75" if own_T >= 75.0 else "own_period<75"
        by_own[key].append((cand60 - ref60) / ref60)
        failed = []
        if own_T < 75.0:
            ref60, cand60 = interpolated(scn, lambda p, scn=scn, own_T=own_T: failed.append(sp.continue_lists(p, scn, own_T, 75.0)))
            not_continued += bool(failed and failed[0])
        continued["all"].append((cand60 - ref60) / ref60)
        continued[key].append((cand60 - ref60) / ref60)
    extra["AP-14"].update(
        note="同じ架空シナリオの評価期間だけを 50・60・75 年に変えて基準計算した結果どうしの比較。明示の更新年一覧（設備の更新年、冷媒の交換年）は、"
             "シナリオ自身の評価期間の内側にしか生成されていないので、自身の評価期間が 75 年より短いシナリオでは、評価期間を延ばしてもその先の更新が入らない。",
        by_own_study_period={k: stats(v) for k, v in by_own.items()},
        explicit_lists_continued={
            "how": "明示の更新年一覧を、シナリオ自身の評価期間の先へ 75 年まで続けた場合（設備は耐用年数ごと、冷媒機器は自身の一覧の平均間隔ごと。年単位に丸める）。",
            "stage_error": stats(continued["all"]),
            "by_own_study_period": {k: stats(continued[k]) for k in ("own_period>=75", "own_period<75")},
            "n_scenarios_with_a_list_that_could_not_be_continued": not_continued})
    out["AP-14"] = finish("AP-14", c14, X)

    # AP-18d / AP-23c: the class parameters of AP-18b / AP-23b taken from other buildings (same split, per structure x use)
    def pooled(rows, key, width):
        acc = {}
        for r in rows:
            for k, v in r[key].items():
                for g in (grp(r), None):                 # None: all training buildings together
                    s = acc.setdefault((g, k), [0.0] * width)
                    for i in range(width):
                        s[i] += v[i]
        return acc

    p18, p23 = pooled(train, "cls18", 4), pooled(train, "cls23", 3)

    def estimate18(r, g):
        """B3 per class from the class sums of the initial emission and pooled (repair rate, cycle); None without parameters."""
        out = {}
        for k, (e0, _, _, _) in r["cls18"].items():
            if not e0:
                continue
            p = p18.get((g, k))
            if p is None or not p[0]:
                return None                              # no building of the training half has this class
            cbar = p[2] / p[3] if p[3] else None
            nbar = cf.renewal_count(r["T"], cbar) if cbar else 0
            skip = cf.skip_weight_periodic(r["T"], cbar, nbar) if nbar else 0.0
            out[k] = e0 * (p[1] / p[0]) * (r["T"] - skip)
        return out

    def estimate23(r, g):
        out = dict(r["fixed23"])                         # rows with an explicit list or without a cycle stay exact
        for k, (_, _, e0) in r["cls23"].items():
            if not e0:
                continue
            p = p23.get((g, k))
            if p is None or not p[2]:
                return None
            if p[0]:
                out[k] = out.get(k, 0.0) + e0 * (p[0] / p[2]) * (r["T"] - min(r["T"], max(0.0, r["T"] * p[1] / p[0] - 1.0)))
        return out

    for cid, estimate, own_key, base in (("AP-18d", estimate18, "ap18b", "AP-18b"), ("AP-23c", estimate23, "ap23b", "AP-23b")):
        col = C[cid]
        same, pooled_all = Series(), Series()
        skipped = 0
        for r in test:
            by_class = estimate(r, grp(r))
            if by_class is None:
                skipped += 1
                continue
            value = sum(by_class.values())
            col.add(grp(r), r["b3"], value, r["wlc"])
            col.add_classes(r["b3_cls"], by_class)
            col.unit("B3-01", "値（= 段階 B3）").add(r["b3"], value)
            same.add(r["b3"], r[own_key])
            everyone = estimate(r, None)
            if everyone is not None:
                pooled_all.add(r["b3"], sum(everyone.values()))
        extra[cid].update(
            data_dependence=SYNTH_NOTE, n_test_scenarios_without_parameters=skipped,
            pooling="学習用の半分（母集団の前半）の建物から、構造×用途ごとに、区分の合計どうしの比として代表値を作った（AP-10 と同じ分け方）。",
            in_sample_on_the_same_test_scenarios={"candidate_id": base, "stage_error": same.result()},
            parameters_pooled_over_all_training_buildings={"stage_error": pooled_all.result()})
        out[cid] = finish(cid, col, X)

    # AP-21: timber carbon storage from the volume and one mean storage per m3 (memo value)
    c21 = C["AP-21"]
    sbar = group_mean(train, lambda r: r["sto"] / r["timber"] if r["sto"] and r["timber"] else None)
    for r in test:
        if r["sto"] and r["timber"] and grp(r) in sbar:
            c21.add(grp(r), r["sto"], sbar[grp(r)] * r["timber"])
            c21.unit("STO-01", "値（参考値）").add(r["sto"], sbar[grp(r)] * r["timber"])
    extra["AP-21"]["data_dependence"] = SYNTH_NOTE
    out["AP-21"] = finish("AP-21", c21, X)

    # AP-22b: CO2-only total as a constant share of the all-gas total
    c22 = C["AP-22b"]
    kappa = group_mean(train, lambda r: r["co2"] / r["total_inc"] if r["total_inc"] else None)
    for r in test:
        if r["co2"] and grp(r) in kappa:
            c22.add(grp(r), r["co2"], kappa[grp(r)] * r["total_inc"])
            c22.unit("X-05", "値（CO2 のみの合計）").add(r["co2"], kappa[grp(r)] * r["total_inc"])
    extra["AP-22b"].update(
        data_dependence=SYNTH_NOTE,
        load=X.load.result("AP-22b", "one product per factor key of the table (activity x CO2 amount)",
                           "厳密な読み方は係数キーごとに積 1 回（n_rows が係数キーの数）、候補は全ガスの合計に比を 1 回掛けるだけ。"))
    out["AP-22b"] = finish("AP-22b", c22, X)

    out = {cid: out[cid] for cid in sorted(out, key=order_key)}
    if set(out) != set(DECL):
        raise SystemExit(f"declared and measured candidates differ: {sorted(set(out) ^ set(DECL))}")
    if X.unmeasured and n >= 200:
        raise SystemExit(f"declared units without a measurement on their own output: {X.unmeasured}")
    return {"schema_version": "3.0", "population": n, "data_statement": "SYNTHETIC_FICTIONAL data only.",
            "error_definition": "(candidate - reference) / reference, signed; negative = under-estimation. stage_error is measured on the quantity named by "
                                "'stage'. local_total_error divides the difference of the changed quantity by the whole-life total (all 14 stages) and does "
                                "not include stages that reuse the changed quantity. propagated_total_error is (SUM-03' - SUM-03) / SUM-03 where SUM-03' "
                                "comes from re-running the reference calculation with the approximated input; propagation.stage_error holds the stage "
                                "values of that run. A case whose reference is 0 has no relative error: it is counted in n_reference_zero, and in "
                                "n_reference_zero_candidate_nonzero when the candidate is not 0.",
            "target_definition": "within_stage_target: the primary quantity and every real stage value measured for the candidate (by_stage, "
                                 "propagation.stage_error; worst_stage names the worst) have max |error| <= targets.stage and no case with reference 0 "
                                 "and candidate not 0. within_total_target: max |error| <= targets.total on propagated_total_error where it was "
                                 "measured, else on local_total_error (total_error_kind says which). For AP-23a / AP-23b the stress scenarios "
                                 "(fictional lives near the study period) count as well; the population alone is in "
                                 "within_stage_target_on_population. Meeting a target on fictional data does not establish practical accuracy.",
            "attachment_definition": "scope / units / units_stage_level / evidence_scope: see bench/approx_meta.py. units are exactly the units "
                                     "measured on their own output (by_unit); units_stage_level are measured only through a stage total or a sum of units.",
            "by_material_class_note": "by_material_class は、資材の行に作用する候補について、1 シナリオ内の資材区分ごとの合計の誤差を集めたもの（設備は EQUIPMENT）。"
                                      "基準が 0 の（シナリオ, 区分）の組は相対誤差を作れないので集計から外し、その数と、そのうち候補が 0 でない数を "
                                      "by_material_class_zero_reference と区分ごとの n_reference_zero・n_reference_zero_candidate_nonzero に記録した。",
            "row_data_rebuilds_reference_B4_max_rel_diff": X.worst["B4"],
            "row_data_rebuilds_reference_B3_max_rel_diff": X.worst["B3"],
            "row_data_rebuilds_annual_units_max_rel_diff": X.worst["annual"],
            "n_scenarios_with_excluded_stages": X.excluded_stage_scenarios,
            "n_rows_with_a_cycle_below_one_year": X.below_one_year,
            "units_without_a_case_in_this_population": X.unmeasured,
            "load_sample": {"every": load_every, "n_scenarios": len(X.load.scenarios), "scenarios": X.load.scenarios,
                            "note": "負荷（命令数）は、母集団のうちこの標本のシナリオの行で測った。候補の核と厳密な閉形式を、同じ行に対して 1 行 1 回ずつ呼んだときの命令数である。"},
            "numbering_note": "AP-07 は複合係数の構成材の切り捨て（AP-07a・AP-07b）。初版では測定せずに番号だけ空けていた。AP-20 は点推定ではなく上下限。"
                              "AP-05 は 2 つの変種に分けた（AP-05a：整合的な線形化、AP-05b：これまで AP-05 として公表していたもの）。"
                              "AP-18d・AP-23c は AP-18b・AP-23b の区分パラメータを他の建物から与えたもの、AP-19c は AP-19a を行の区別なしに当てはめたもの。"
                              "AP-23a・AP-23b は修繕の安全側の候補、AP-24a・AP-24b は年次表の間引き。",
            "targets": {"total": TARGET_TOTAL, "stage": TARGET_STAGE}, "candidates": out}


def pearson(xs, ys):
    if len(xs) < 2:
        return None
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    return sxy / math.sqrt(sxx * syy) if sxx > 0.0 and syy > 0.0 else None


def summary_line(cid: str, c: dict) -> str:
    s = c.get("stage_error") or c.get("row_error")
    if not s or not s.get("n"):
        return f"{cid:7s} (no point estimate)  {c['title'][:44]}"
    t = c.get("propagated_total_error") or c.get("local_total_error") or {}
    total = f" | total[{(c.get('total_error_kind') or '-')[:4]}] p95 {t['p95_abs']:.4f}" if t.get("n") else ""
    return (f"{cid:7s} n={s['n']:6d} mean {s['mean_signed']:+.4f} p95|e| {s['p95_abs']:.4f} over {s['max_over']:+.4f} "
            f"under {s['max_under']:+.4f}{total}  {c['title'][:36]}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--population", type=int, default=400)
    ap.add_argument("--out", type=Path, default=OUT, help="output file (default: the study's approximation_study.json)")
    args = ap.parse_args()
    t0 = time.time()
    result = run(args.population)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"population {result['population']}, B4 rebuilt from row data within {result['row_data_rebuilds_reference_B4_max_rel_diff']:.1e}, "
          f"B3 within {result['row_data_rebuilds_reference_B3_max_rel_diff']:.1e}")
    for cid, c in result["candidates"].items():
        print(summary_line(cid, c))
    b = result["candidates"]["AP-20"]
    print(f"AP-20   n={b['n']} inside {b['share_reference_inside_bracket']:.3f} width mean {b['bracket_width_relative_to_reference']['mean_abs']:.3f}")
    print(f"written {args.out} in {time.time() - t0:.0f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
