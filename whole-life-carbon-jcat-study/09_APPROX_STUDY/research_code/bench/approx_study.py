#!/usr/bin/env python3
"""Approximate candidates measured against the reference calculation.

Each candidate replaces an exact step by something simpler. The signed relative error
(candidate - reference) / reference is collected on a population of fictional scenarios
for the quantity the candidate changes (a stage, or a memo quantity) and for the
whole-life total, overall and by structure, by use and - where the candidate acts on
material rows - by material class. Negative errors are under-estimations.

All data are synthetic. For candidates whose error depends on how real buildings are
composed (class-representative parameters, floor-area intensities, regressions,
top-contributor truncation) the numbers only demonstrate the method on a fictional
population; they are NOT evidence of practical accuracy.

Run:  cd research_code && python3 -m bench.approx_study [--population 400]
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import sys
from pathlib import Path

from common.compare import percentile
from fastcalc import closed_forms as cf
from refcalc import registry
from refcalc.base import annual_unit, convert, event_year, grid_unit, lookup, nonneg, periodic_events, ratio, year_weights
from refcalc.units_b import equipment_extra_lines, material_install_line
from refcalc.units_pre_a import SIMPLE_CLASSES, simple_class, summary_quantity
from synth import population

STUDY = Path(__file__).resolve().parents[2]
OUT = STUDY / "04_VERIFICATION" / "approximation_study.json"
TARGET_TOTAL, TARGET_STAGE = 0.01, 0.02
STAGES14 = ("A1-A3", "A4", "A5", "B1", "B2", "B3", "B4", "B5", "B6", "B7", "C1", "C2", "C3", "C4")
ANNUAL = ("B1", "B2", "B3", "B4", "B5", "B6", "B7")


def stats(errors: list[float]) -> dict:
    if not errors:
        return {"n": 0}
    a = [abs(e) for e in errors]
    return {"n": len(errors), "mean_signed": sum(errors) / len(errors), "mean_abs": sum(a) / len(a),
            "p95_abs": percentile(a, 95), "max_abs": max(a), "max_over": max(errors), "max_under": min(errors),
            "share_under_estimated": sum(e < -1e-12 for e in errors) / len(errors)}


class Collector:
    """Errors of one candidate. ``stage`` names the reference quantity the candidate changes."""

    def __init__(self, cid, title, replaces, stage, units, step):
        self.meta = {"candidate_id": cid, "title": title, "replaces": replaces, "stage": stage, "units": units, "step": step}
        self.stage, self.total, self.groups, self.classes = [], [], {}, {}
        self.zero_reference = 0        # reference 0 while the candidate is not: no relative stage error exists

    def add(self, scn, ref, cand, wlc=None):
        if wlc:
            self.total.append((cand - ref) / wlc)
        if ref == 0.0:
            if cand != 0.0:
                self.zero_reference += 1
            return
        e = (cand - ref) / ref
        self.stage.append(e)
        for key in (f"structure={scn.meta.structure}", f"use={scn.meta.use}"):
            self.groups.setdefault(key, []).append(e)

    def add_classes(self, ref_by_class: dict, cand_by_class: dict):
        """Per material class: error of the class sum within one scenario."""
        for k, ref in ref_by_class.items():
            if ref:
                self.classes.setdefault(k, []).append((cand_by_class.get(k, 0.0) - ref) / ref)

    def result(self):
        s, t = stats(self.stage), stats(self.total)
        out = dict(self.meta)
        out.update(stage_error=s, total_error=t, by_group={k: stats(v) for k, v in sorted(self.groups.items())},
                   by_material_class={k: stats(v) for k, v in sorted(self.classes.items())} or None,
                   n_reference_zero_candidate_nonzero=self.zero_reference,
                   within_stage_target=bool(s.get("n")) and s["max_abs"] <= TARGET_STAGE and self.zero_reference == 0,
                   within_total_target=(bool(t.get("n")) and t["max_abs"] <= TARGET_TOTAL) if t.get("n") else None,
                   under_estimates=bool(s.get("n")) and s["max_under"] < -1e-9)
        return out


def renewal_rows(scn, res):
    """Every row that can be renewed: class, period, emission of one renewal, reference count, explicit schedule?"""
    out = []
    q_ord = res["A13-05"]["q_ord"]
    srcs = [res[k]["by_item"] for k in ("A13-01", "A13-03", "A4-01", "A4-02", "C2-01", "C3-01", "C4-01")]
    for i, row in enumerate(scn.materials):
        u = sum(src[i] for src in srcs)
        inst = material_install_line(scn, row, q_ord[i])
        if inst is not None:
            u += inst[1] * scn.factors[inst[0]].value
        e0 = res["A13-01"]["by_item"][i] + res["A13-03"]["by_item"][i]
        out.append({"cls": row.material_class, "cycle": row.refresh_cycle, "u": u, "n": res["B4-03"]["by_item"][i],
                    "explicit": False, "e0": e0, "r": row.repair_rate, "events": None})
    for j, eq in enumerate(scn.equipment):
        u = res["X-01"]["by_item"][j] + res["X-14"]["by_item"][j]
        u += sum(act * scn.factors[fid].value for fid, act in equipment_extra_lines(scn, eq)[0])
        events = res["B4-01"]["events"][j]
        out.append({"cls": "EQUIPMENT", "cycle": eq.service_life, "u": u, "n": len(events),
                    "explicit": eq.replacement_event_list is not None, "e0": res["X-01"]["by_item"][j], "r": eq.repair_rate,
                    "events": events})
    return out


def repair_years(T, w, events):
    skip = {event_year(tau) for tau in events}
    return sum(w[y] for y in range(1, len(w)) if y not in skip)


COUNT_FORMS = (("AP-01", lambda T, c: max(0.0, T / c - 1.0)), ("AP-02", lambda T, c: max(0.0, T / c - 0.5)),
               ("AP-03", lambda T, c: T / c))


def run(n_population: int) -> dict:
    registry.load_all()
    cnt_units = ["B4-01", "B4-03", "B4-02", "X-08", "B5-01", "X-10"]
    mk = Collector
    C = {
        "AP-01": mk("AP-01", "更新回数の連続近似 N ≈ max(0, T/c − 1)", "回数関数 N(T,c)", "B4", cnt_units, "M3"),
        "AP-02": mk("AP-02", "更新回数の中点補正 N ≈ max(0, T/c − 1/2)", "回数関数 N(T,c)", "B4", cnt_units, "M3"),
        "AP-03": mk("AP-03", "更新回数の切り捨てなし N ≈ T/c", "回数関数 N(T,c)", "B4", cnt_units, "M3"),
        "AP-04": mk("AP-04", "修繕の更新年除外を無視（B3-02 で B3-01 を代用）", "修繕の年次積算", "B3", ["B3-01", "B3-02"], "M3"),
        "AP-05": mk("AP-05", "冷媒漏洩の線形近似 1−(1−r)^k ≈ r·k", "充填サイクルの閉形式", "B1", ["B1-02", "B1-03", "B1-04"], "M3"),
        "AP-06": mk("AP-06", "端材倍率の線形化 1/(1−w) ≈ 1+w", "発注量の算出", "A1-A3", ["A13-05", "X-13"], "M3"),
        "AP-07a": mk("AP-07a", "複合係数：質量比 5％ 未満の構成材を切り捨てる（補正なし）", "複合係数の加重和", "複合品の製造排出（X-03）", ["A13-02", "X-03"], "M3"),
        "AP-07b": mk("AP-07b", "複合係数：質量比 5％ 未満の構成材を切り捨て、残りの比率を合計 1 に補正", "複合係数の加重和", "複合品の製造排出（X-03）", ["A13-02", "X-03"], "M3"),
        "AP-08": mk("AP-08", "買電排出を 平均買電量×平均係数×T で近似", "買電量×係数の年次積算", "B6", ["B6-01", "B6-03", "B6-04", "B2-01"], "M3"),
        "AP-09a": mk("AP-09a", "電力係数を 5 年ごとの点の直線補間で持つ（全種類の系列に適用）", "年次の電力係数系列", "B6", ["X-06"], "M3"),
        "AP-09b": mk("AP-09b", "電力係数を 10 年ごとの点の直線補間で持つ（全種類の系列に適用）", "年次の電力係数系列", "B6", ["X-06"], "M3"),
        "AP-09c": mk("AP-09c", "併用：パラメータ型の系列は厳密な閉形式、年次表の系列だけ 5 年ごとの点の直線補間", "年次の電力係数系列", "B6", ["X-06", "B6-01"], "M6"),
        "AP-12": mk("AP-12", "併用：質量上位 20％ の資材行だけ詳細計算し、残りを質量比で補う", "資材製造の全行計算", "A1-A3（資材分）", ["A13-01", "A13-03"], "M6"),
        "AP-13": mk("AP-13", "面積当たり電力使用量による買電排出の推定（X-11）で実績計算を代用", "買電排出の年次積算", "B6", ["X-11", "B6-01"], "M4"),
        "AP-17": mk("AP-17", "輸送：輸送手段ごとに 合計質量×単純平均距離 で求める", "行ごとの質量×距離", "A4", ["A4-01", "X-12"], "M3"),
        "AP-18a": mk("AP-18a", "区分パラメータ：資材区分ごとに代表更新周期（更新 1 回の排出で重み付けした調和平均）を 1 つ持つ", "行ごとの更新周期", "B4", ["B4-02", "B4-03", "X-08"], "M4"),
        "AP-18b": mk("AP-18b", "区分パラメータ：資材区分ごとに代表修繕率（初期排出で重み付けした平均）と代表更新周期を持つ", "行ごとの修繕率と更新周期", "B3", ["B3-01"], "M4"),
        "AP-18c": mk("AP-18c", "区分パラメータ：資材区分ごとに処理経路の比率（単純平均）と経路係数（単純平均）を持ち、行は質量だけにする", "行ごとの経路比率と係数", "C3＋C4", ["C3-01", "C4-01", "X-09"], "M4"),
        "AP-18": mk("AP-18", "区分パラメータによる共通近似モデル（AP-18a〜c を同時に適用）", "行ごとのライフサイクル条件", "B3＋B4＋C3＋C4", ["B3-01", "B4-02", "C3-01", "C4-01"], "M4"),
        "AP-19a": mk("AP-19a", "未数量分：行ごとの比率の代わりに単純平均の比率 1 つを使う", "行ごとの上乗せ倍率", "未数量分（A13-04）", ["A13-04"], "M3"),
        "AP-19b": mk("AP-19b", "未数量分：行ごとの比率の代わりに最大の比率 1 つを使う（安全側）", "行ごとの上乗せ倍率", "未数量分（A13-04）", ["A13-04"], "M3"),
        "AP-22a": mk("AP-22a", "全ガスの合計を CO2 のみの合計で代用する", "ガス別の合算", "対象段階の合計", ["X-04", "X-05"], "M3"),
    }
    conditional = {"CONSTANT": [], "LINEAR_TREND": [], "TABLE": []}
    by_grid = {}
    leak_guard = {"rk<=0.05": [], "0.05<rk<=0.2": [], "rk>0.2": []}
    targets = {cid: {"B5": Collector(cid, "", "", "B5", [], ""), "X-10.resource_kg": [], "X-10.waste_kg": []} for cid, _ in COUNT_FORMS}
    bracket = {"inside": 0, "n": 0, "width": [], "lower": [], "upper": []}
    hybrid_exact = 0
    x13_rows, x12_err, c2_err = [], [], []
    worst_rebuild = 0.0
    records = []
    n = 0
    for scn in population.verification_population(n_population, seed=20261111, max_size="M"):
        n += 1
        res = registry.run_all(scn)
        T = scn.boundary.study_period
        w = year_weights(T)
        Y = len(w) - 1
        stage = res["X-02"]["by_stage_all"]
        wlc = sum(stage.values())
        rows = renewal_rows(scn, res)

        # the row data must rebuild the reference before any candidate is judged against it
        rebuilt = sum(r["n"] * r["u"] for r in rows)
        if stage["B4"]:
            worst_rebuild = max(worst_rebuild, abs(rebuilt - stage["B4"]) / stage["B4"])

        # ---- renewal count forms on B4 (by class), B5 and the mass totals of X-10 ----
        ref_cls = {}
        for r in rows:
            ref_cls[r["cls"]] = ref_cls.get(r["cls"], 0.0) + r["n"] * r["u"]
        for cid, fn in COUNT_FORMS:
            approx, cls = 0.0, {}
            for r in rows:
                k = r["n"] if r["explicit"] else (fn(T, r["cycle"]) if cf.valid_period(r["cycle"]) else 0.0)
                approx += k * r["u"]
                cls[r["cls"]] = cls.get(r["cls"], 0.0) + k * r["u"]
            C[cid].add(scn, stage["B4"], approx, wlc)
            C[cid].add_classes(ref_cls, cls)
            b5 = res["B5-01"]
            if b5["computed"] and scn.boundary.reconstruction_scenario != "NONE" and cf.valid_period(scn.boundary.replacement_cycle):
                per_event = b5["value"] / b5["n_events"] if b5["n_events"] else (
                    scn.boundary.reconstruction_scope_fraction * sum(stage[s] for s in ("A1-A3", "A4", "A5", "C1", "C2", "C3", "C4")))
                targets[cid]["B5"].add(scn, stage["B5"], fn(T, scn.boundary.replacement_cycle) * per_event, wlc)
            # X-10: masses times (1 + count)
            q_ord, q_inst = res["A13-05"]["q_ord"], res["A13-05"]["q_inst"]
            resource = waste = 0.0
            for i, row in enumerate(scn.materials):
                conv = convert(scn, row.quantity_unit, "kg", row.conversions)
                if conv is None or q_ord[i] is None or not nonneg(row.end_of_life.mass_kg):
                    continue
                k = 1.0 + (fn(T, row.refresh_cycle) if cf.valid_period(row.refresh_cycle) else 0.0)
                resource += q_ord[i] * conv * k
                waste += ((q_ord[i] - q_inst[i]) * conv + row.end_of_life.mass_kg) * k
            for j, eq in enumerate(scn.equipment):
                if nonneg(eq.end_of_life_mass_kg):
                    k = len(res["B4-01"]["events"][j]) if eq.replacement_event_list is not None else (
                        fn(T, eq.service_life) if cf.valid_period(eq.service_life) else 0.0)
                    waste += eq.end_of_life_mass_kg * (1.0 + k)
            x10 = res["X-10"]
            if x10["resource_kg"]:
                targets[cid]["X-10.resource_kg"].append(resource / x10["resource_kg"] - 1.0)
            if x10["waste_kg"]:
                targets[cid]["X-10.waste_kg"].append(waste / x10["waste_kg"] - 1.0)

        # ---- AP-20: guaranteed bracket [sum u*(T/c-1), sum u*T/c] ----
        lo = sum((r["n"] if r["explicit"] else (max(0.0, T / r["cycle"] - 1.0) if cf.valid_period(r["cycle"]) else 0.0)) * r["u"] for r in rows)
        hi = sum((r["n"] if r["explicit"] else (T / r["cycle"] if cf.valid_period(r["cycle"]) else 0.0)) * r["u"] for r in rows)
        if stage["B4"] > 0.0:
            bracket["n"] += 1
            bracket["inside"] += lo <= stage["B4"] * (1 + 1e-12) and stage["B4"] <= hi * (1 + 1e-12)
            bracket["width"].append((hi - lo) / stage["B4"])
            bracket["lower"].append(lo / stage["B4"] - 1.0)
            bracket["upper"].append(hi / stage["B4"] - 1.0)

        # ---- repairs: AP-04, and the class-parameter model AP-18a/b ----
        C["AP-04"].add(scn, stage["B3"], res["B3-02"]["value"], wlc)
        agg = {}
        for r in rows:
            a = agg.setdefault(r["cls"], {"U": 0.0, "U_over_c": 0.0, "E0r": 0.0, "E0": 0.0, "b4": 0.0, "b3": 0.0, "explicit": 0.0})
            periodic = cf.valid_period(r["cycle"]) and not r["explicit"]
            if r["explicit"]:
                a["explicit"] += r["n"] * r["u"]
            elif periodic:
                a["U"] += r["u"]
                a["U_over_c"] += r["u"] / r["cycle"]
            a["b4"] += r["n"] * r["u"]
            if nonneg(r["r"]) and r["r"] and r["e0"]:
                events = r["events"] if r["events"] is not None else (periodic_events(T, r["cycle"]) if r["n"] else [])
                a["b3"] += r["e0"] * r["r"] * repair_years(T, w, events)
                a["E0r"] += r["e0"] * r["r"]
                a["E0"] += r["e0"]
        b4_18, b3_18, cls_b4 = 0.0, 0.0, {}
        for k, a in agg.items():
            cbar = a["U"] / a["U_over_c"] if a["U_over_c"] else None
            nbar = cf.renewal_count(T, cbar) if cbar else 0
            cls_b4[k] = a["explicit"] + nbar * a["U"]
            b4_18 += cls_b4[k]
            skip = cf.skip_weight_periodic(T, cbar, nbar) if nbar else 0.0
            b3_18 += a["E0r"] * (T - skip)
        C["AP-18a"].add(scn, stage["B4"], b4_18, wlc)
        C["AP-18a"].add_classes({k: a["b4"] for k, a in agg.items()}, cls_b4)
        C["AP-18b"].add(scn, stage["B3"], b3_18, wlc)

        # ---- AP-18c: class-level end-of-life routes ----
        cls_route = {}
        ref_c = res["C3-01"]["value"] + res["C4-01"]["value"]
        for i, row in enumerate(scn.materials):
            eol = row.end_of_life
            if not nonneg(eol.mass_kg):
                continue
            c = cls_route.setdefault(row.material_class, {"mass": 0.0, "rows": 0, "routes": {}})
            c["mass"] += eol.mass_kg
            c["rows"] += 1
            for route in eol.routes:
                hit = lookup(scn, route.factor_id, "C4" if route.route == "LANDFILL" else "C3", "kg")
                if hit is None or not nonneg(route.fraction):
                    continue
                q = c["routes"].setdefault(route.route, [0.0, 0.0, 0])
                q[0] += route.fraction
                q[1] += hit[1] * hit[0].value
                q[2] += 1
        c_18 = sum(c["mass"] * sum((q[0] / c["rows"]) * (q[1] / q[2]) for q in c["routes"].values()) for c in cls_route.values())
        C["AP-18c"].add(scn, ref_c, c_18, wlc)
        ref_18 = stage["B3"] + stage["B4"] + ref_c
        C["AP-18"].add(scn, ref_18, b3_18 + b4_18 + c_18, wlc)

        # ---- refrigerants: linear leak per charge cycle ----
        approx_b1 = 0.0
        for d, (dev, st) in enumerate(zip(scn.refrigerants, res["B1-02"]["_state"])):
            if st is None:
                continue
            m0, r = dev.charge_mass_kg, dev.annual_leak_rate
            n_ev = len(st["before_events"])
            approx_dev = m0 * r * T                       # every year leaks from a full charge
            exact_dev = res["B1-02"]["by_item"][d] / dev.gwp if dev.gwp else 0.0
            if ratio(dev.replacement_loss_rate):
                approx_dev += n_ev * m0 * dev.replacement_loss_rate
                exact_dev += sum(m for _, m in st["before_events"]) * dev.replacement_loss_rate
            if ratio(dev.end_of_life_recovery_rate):
                approx_dev += m0 * (1.0 - dev.end_of_life_recovery_rate)
                exact_dev += st["end"] * (1.0 - dev.end_of_life_recovery_rate)
            approx_b1 += approx_dev * dev.gwp
            if not dev.top_up and exact_dev > 0.0:
                rk = r * T / (n_ev + 1)
                key = "rk<=0.05" if rk <= 0.05 else "0.05<rk<=0.2" if rk <= 0.2 else "rk>0.2"
                leak_guard[key].append(approx_dev / exact_dev - 1.0)
        C["AP-05"].add(scn, stage["B1"], approx_b1, wlc)

        # ---- material rows: waste linearisation, unquantified ratio, top contributors ----
        emis, extra = [], []
        for i in range(len(scn.materials)):
            emis.append(res["A13-01"]["by_item"][i] + res["A13-03"]["by_item"][i])
            extra.append(res["A13-04"]["by_item"][i])
        approx_a, ref_cls6, cls6 = res["X-01"]["value"], {}, {}
        for i, row in enumerate(scn.materials):
            e = emis[i] + extra[i]
            scale = 1.0
            if row.quantity_basis == "DESIGN" and row.waste_rate is not None and 0.0 <= row.waste_rate < 1.0:
                scale = (1.0 + row.waste_rate) * (1.0 - row.waste_rate)
            approx_a += e * scale
            ref_cls6[row.material_class] = ref_cls6.get(row.material_class, 0.0) + e
            cls6[row.material_class] = cls6.get(row.material_class, 0.0) + e * scale
        C["AP-06"].add(scn, stage["A1-A3"], approx_a, wlc)
        C["AP-06"].add_classes(ref_cls6, cls6)
        # X-13: net order quantity with reuse of offcuts, linearised the same way (row level; quantities have row units)
        q_o, q_i, net13 = res["A13-05"]["q_ord"], res["A13-05"]["q_inst"], res["X-13"]["by_item"]
        for i, row in enumerate(scn.materials):
            if row.quantity_basis != "DESIGN" or net13[i] is None or not q_o[i] or not q_o[i] > q_i[i] or not net13[i]:
                continue
            w_i = 1.0 - q_i[i] / q_o[i]
            keep = (net13[i] - q_i[i]) / (q_o[i] - q_i[i])          # 1 - reuse rate
            x13_rows.append(q_i[i] * (1.0 + w_i * keep) / net13[i] - 1.0)

        ratios = [(emis[i], row.unquantified_cost_ratio) for i, row in enumerate(scn.materials)
                  if row.unquantified_cost_ratio is not None and 0.0 < row.unquantified_cost_ratio < 1.0]
        if ratios:
            base = sum(e for e, _ in ratios)
            rbar = sum(r for _, r in ratios) / len(ratios)
            rmax = max(r for _, r in ratios)
            C["AP-19a"].add(scn, res["A13-04"]["value"], base * rbar / (1.0 - rbar), wlc)
            C["AP-19b"].add(scn, res["A13-04"]["value"], base * rmax / (1.0 - rmax), wlc)

        masses = [row.end_of_life.mass_kg or 0.0 for row in scn.materials]
        mat_ref = sum(emis)
        if mat_ref > 0.0 and len(masses) >= 10:
            order = sorted(range(len(masses)), key=lambda i: -masses[i])
            top = order[: max(1, len(order) // 5)]
            m_top, e_top = sum(masses[i] for i in top), sum(emis[i] for i in top)
            C["AP-12"].add(scn, mat_ref, e_top * sum(masses) / m_top if m_top else 0.0, wlc)

        # ---- composites: drop components below 5 percent of the mass ----
        parts, rx, q_ord = res["A13-02"]["_parts"], res["X-15"], res["A13-05"]["q_ord"]
        ref_x3 = cut = cut_norm = 0.0
        ref_c7, cut_c7, norm_c7 = {}, {}, {}
        for i, row in enumerate(scn.materials):
            if rx["kind"][i] != "COMPOSITE" or q_ord[i] is None:
                continue
            kg = q_ord[i] * rx["conv"][i]
            full = sum(frac * c * scn.factors[fid].value for fid, frac, c in parts[i])
            kept = [(fid, frac, c) for fid, frac, c in parts[i] if frac >= 0.05]
            part = sum(frac * c * scn.factors[fid].value for fid, frac, c in kept)
            share = sum(frac for _, frac, _ in kept)
            ref_x3 += kg * full
            cut += kg * part
            cut_norm += kg * part / share if share else 0.0
            k = row.material_class
            ref_c7[k] = ref_c7.get(k, 0.0) + kg * full
            cut_c7[k] = cut_c7.get(k, 0.0) + kg * part
            norm_c7[k] = norm_c7.get(k, 0.0) + (kg * part / share if share else 0.0)
        C["AP-07a"].add(scn, ref_x3, cut, wlc)
        C["AP-07a"].add_classes(ref_c7, cut_c7)
        C["AP-07b"].add(scn, ref_x3, cut_norm, wlc)
        C["AP-07b"].add_classes(ref_c7, norm_c7)

        # ---- transport: total mass x simple mean distance per mode ----
        modes = {}
        for i, row in enumerate(scn.materials):
            if not res["A4-01"]["_row_lines"][i]:
                continue
            tr = row.transport
            hit = lookup(scn, tr.factor_id, "A4", "tkm")
            m = modes.setdefault(tr.factor_id, [0.0, 0.0, 0, hit[1] * hit[0].value])
            m[0] += tr.mass_t
            m[1] += tr.distance_km
            m[2] += 1
        a4_17 = res["A4-02"]["value"] + sum(m[0] * (m[1] / m[2]) * m[3] for m in modes.values())
        C["AP-17"].add(scn, stage["A4"], a4_17, wlc)
        # the same mean distance on X-12 (activity divided by the load factor) and on the haul of C2
        m12 = {}
        for i, row in enumerate(scn.materials):
            tr = row.transport
            hit = lookup(scn, tr.factor_id, "A4", "tkm") if tr.delivery_factor_id is None else None
            if hit is None or not nonneg(tr.mass_t) or not nonneg(tr.distance_km) or not (tr.load_factor is not None and tr.load_factor > 0.0):
                continue
            m = m12.setdefault(tr.factor_id, [0.0, 0.0, 0, hit[1] * hit[0].value])
            m[0] += tr.mass_t / tr.load_factor
            m[1] += tr.distance_km
            m[2] += 1
        if res["X-12"]["value"]:
            x12_err.append(sum(m[0] * (m[1] / m[2]) * m[3] for m in m12.values()) / res["X-12"]["value"] - 1.0)
        hauls, c2_rows = {}, 0.0
        for i, row in enumerate(scn.materials):
            if not res["C2-01"]["_row_lines"][i]:
                continue
            eol = row.end_of_life
            hit = lookup(scn, eol.haul_factor_id, "C2", "tkm")
            m = hauls.setdefault(eol.haul_factor_id, [0.0, 0.0, 0, hit[1] * hit[0].value])
            m[0] += eol.mass_kg / 1000.0
            m[1] += eol.haul_distance_km
            m[2] += 1
            c2_rows += res["C2-01"]["by_item"][i]
        if stage["C2"]:
            c2_err.append((stage["C2"] - c2_rows + sum(m[0] * (m[1] / m[2]) * m[3] for m in hauls.values())) / stage["C2"] - 1.0)

        # ---- electricity: mean demand x mean factor, interpolated factor tables, floor-area estimate ----
        op = scn.operation
        g = res["X-06"]["by_year"]
        eu, gu = annual_unit(op.electricity.unit), grid_unit(op.grid)
        conv = convert(scn, eu, gu) if eu is not None and gu is not None else None
        if res["B6-01"]["computed"] and conv is not None:
            net = [v * conv for v in res["B6-04"]["by_year"]]
            elec_ref = sum(w[y] * net[y] * g[y] for y in range(1, Y + 1))
            b6_ref = res["B6-03"]["value"]
            fuel = b6_ref - elec_ref
            if elec_ref > 0.0:
                mean_net = sum(w[y] * net[y] for y in range(1, Y + 1)) / T
                mean_g = sum(w[y] * g[y] for y in range(1, Y + 1)) / T
                approx = mean_net * mean_g * T + fuel
                C["AP-08"].add(scn, b6_ref, approx, wlc)
                kinds = {op.electricity.kind, op.onsite_generation.kind, op.onsite_export.kind}
                key = "CONSTANT" if kinds == {"CONSTANT"} else "TABLE" if "TABLE" in kinds else "LINEAR_TREND"
                conditional[key].append((approx - b6_ref) / b6_ref)
                for cid, step in (("AP-09a", 5), ("AP-09b", 10)):
                    gi = [0.0]
                    for k in range(Y):
                        lo_k = (k // step) * step
                        hi_k = min(lo_k + step, Y - 1) if Y > 1 else lo_k
                        gi.append(g[lo_k + 1] if hi_k <= lo_k else g[lo_k + 1] + (g[hi_k + 1] - g[lo_k + 1]) * (k - lo_k) / (hi_k - lo_k))
                    approx = sum(w[y] * net[y] * gi[y] for y in range(1, Y + 1)) + fuel
                    C[cid].add(scn, b6_ref, approx, wlc)
                    by_grid.setdefault(f"{cid}:{op.grid.kind}", []).append((approx - b6_ref) / b6_ref)
                    if cid == "AP-09a":
                        if res["X-06"]["source"] == "TABLE":
                            C["AP-09c"].add(scn, b6_ref, approx, wlc)
                        else:
                            hybrid_exact += 1
                x11 = res["X-11"]["value"]
                if x11 is not None:
                    C["AP-13"].add(scn, b6_ref, x11 + fuel, wlc)

        # ---- gases: CO2 only instead of all gases (included stages) ----
        total_inc = res["SUM-03"]["value"]
        C["AP-22a"].add(scn, total_inc, res["X-05"]["value"], total_inc)

        # ---- data for population-level candidates ----
        class_e = {k: 0.0 for k in SIMPLE_CLASSES}
        for i, row in enumerate(scn.materials):
            k = simple_class(row)
            if k is not None:
                class_e[k] += emis[i]
        sq = scn.summary_quantities
        sto = res["STO-01"]["value"]
        records.append({"structure": scn.meta.structure, "use": scn.meta.use, "T": T, "area": scn.project.gross_floor_area,
                        "wlc": wlc, "stage": dict(stage), "class_e": class_e,
                        "class_q": {k: summary_quantity(scn, k) for k in SIMPLE_CLASSES}, "mat_ref": mat_ref,
                        "co2": res["X-05"]["value"], "total_inc": total_inc,
                        "sto": sto, "timber": sq.timber_m3 if sto else None, "scenario": scn})

    out = {cid: c.result() for cid, c in C.items()}
    for cid, _ in COUNT_FORMS:
        t = targets[cid]
        out[cid]["other_targets"] = {
            "B5（建替・大型改修の回数に適用）": {"stage_error": stats(t["B5"].stage), "total_error": stats(t["B5"].total),
                                     "n_reference_zero_candidate_nonzero": t["B5"].zero_reference},
            "X-10 資源量[kg]": stats(t["X-10.resource_kg"]), "X-10 廃棄物量[kg]": stats(t["X-10.waste_kg"]),
            "X-08": "合計は B4-02 と同じ値なので、B4 の誤差がそのまま当てはまる。"}
    out["AP-17"]["other_targets"] = {"X-12（積載率補正後の輸送。参考値）": stats(x12_err), "C2（廃棄物搬出。行ごとの搬出距離を単純平均に置換）": stats(c2_err)}
    out["AP-06b"] = {"candidate_id": "AP-06b", "step": "M3", "stage": "X-13 の行ごとの正味発注量", "units": ["X-13"],
                     "title": "端材の再使用を考慮した正味発注量の線形化 1 + w(1−ρ)/(1−w) ≈ 1 + w(1−ρ)", "replaces": "正味発注量の算出",
                     "row_error": stats(x13_rows), "note": "行ごとの数量は単位が行によって違うため、行ごとの相対誤差を集めた（シナリオ合計ではない）。"}
    out["AP-08"]["by_profile_kind"] = {k: stats(v) for k, v in conditional.items()}
    for cid in ("AP-09a", "AP-09b"):
        out[cid]["by_grid_kind"] = {k.split(":")[1]: stats(v) for k, v in sorted(by_grid.items()) if k.startswith(cid)}
    out["AP-09c"]["n_scenarios_computed_exactly"] = hybrid_exact
    out["AP-05"]["by_rate_times_cycle_years_no_top_up_devices"] = {k: stats(v) for k, v in leak_guard.items()}
    out["AP-20"] = {"candidate_id": "AP-20", "step": "M6", "stage": "B4", "units": ["B4-02"],
                    "title": "併用：点推定の代わりに、必ず成り立つ上下限 Σu·max(0,T/c−1) ≤ B4 ≤ Σu·T/c を使う（明示の更新年一覧は厳密）",
                    "replaces": "回数関数 N(T,c)", "n": bracket["n"], "share_reference_inside_bracket": bracket["inside"] / bracket["n"] if bracket["n"] else None,
                    "bracket_width_relative_to_reference": stats(bracket["width"]),
                    "lower_bound_error": stats(bracket["lower"]), "upper_bound_error": stats(bracket["upper"])}

    # ---- population-level candidates: fit on the first half, test on the second half ----
    half = len(records) // 2
    train, test = records[:half], records[half:]
    grp = lambda r: (r["structure"], r["use"])

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

    # AP-10 / AP-10b: class-representative factors per (structure, use), without and with a gross-up for the other rows
    fbar = {}
    for k in SIMPLE_CLASSES:
        num, den = group_mean(train, lambda r, k=k: r["class_e"][k]), group_mean(train, lambda r, k=k: r["class_q"][k])
        fbar[k] = {g: (num[g] / den[g] if den[g] else 0.0) for g in num}
    gross = group_mean(train, lambda r: r["mat_ref"] / sum(r["class_e"].values()) if sum(r["class_e"].values()) else None)
    c10 = Collector("AP-10", "6 区分の要約数量×（構造×用途ごとの代表係数）で資材製造を概算", "資材製造の全行計算", "A1-A3（資材分）", ["X-17", "A13-01", "A13-03"], "M4")
    c10b = Collector("AP-10b", "AP-10 に、6 区分に入らない資材の分の割増（構造×用途ごとの平均比）を掛ける", "資材製造の全行計算", "A1-A3（資材分）", ["X-17", "A13-01", "A13-03"], "M4")
    for r in test:
        if grp(r) not in fbar["CONCRETE"]:
            continue
        approx = sum(r["class_q"][k] * fbar[k][grp(r)] for k in SIMPLE_CLASSES)
        c10.add(r["scenario"], r["mat_ref"], approx, r["wlc"])
        if grp(r) in gross:
            c10b.add(r["scenario"], r["mat_ref"], approx * gross[grp(r)], r["wlc"])
    out["AP-10"], out["AP-10b"] = c10.result(), c10b.result()

    # AP-11: whole-life total per floor area and year from (structure, use) group means
    c11 = Collector("AP-11", "延床面積×評価年数×（構造×用途ごとの平均原単位）でホールライフ合計を概算", "全段階の計算", "WLC", ["SUM-03", "SUM-04", "SUM-05"], "M5")
    mean_int = group_mean(train, lambda r: r["wlc"] / (r["area"] * r["T"]))
    for r in test:
        if grp(r) in mean_int:
            c11.add(r["scenario"], r["wlc"], mean_int[grp(r)] * r["area"] * r["T"], r["wlc"])
    out["AP-11"] = c11.result()

    # AP-15: every stage from floor area (x study years for the use stages) times a (structure, use) mean intensity
    scale = lambda r, st: r["area"] * r["T"] if st in ANNUAL else r["area"]
    mean_stage = {st: group_mean(train, lambda r, st=st: r["stage"][st] / scale(r, st)) for st in STAGES14}
    by_stage15 = {}
    for st in STAGES14:
        errs = [mean_stage[st][grp(r)] * scale(r, st) / r["stage"][st] - 1.0 for r in test if grp(r) in mean_stage[st] and r["stage"][st] > 0.0]
        by_stage15[st] = stats(errs)
    c15 = Collector("AP-15", "段階ごとに 延床面積（使用段階は×評価年数）×（構造×用途ごとの平均原単位）で概算する共通近似モデル",
                    "各段階の詳細計算", "WLC（段階別は by_stage）", ["全排出単位"], "M4")
    for r in test:
        if grp(r) in mean_int:
            c15.add(r["scenario"], r["wlc"], sum(mean_stage[st][grp(r)] * scale(r, st) for st in STAGES14), r["wlc"])
    out["AP-15"] = c15.result()
    out["AP-15"]["by_stage"] = by_stage15

    # AP-16: log-linear least-squares regression of the whole-life total
    import numpy as np
    structures = sorted({r["structure"] for r in records})
    uses = sorted({r["use"] for r in records})

    def features(r):
        return ([1.0, math.log(r["area"]), math.log(r["T"])] + [1.0 if r["structure"] == x else 0.0 for x in structures[1:]]
                + [1.0 if r["use"] == x else 0.0 for x in uses[1:]])

    beta, *_ = np.linalg.lstsq(np.array([features(r) for r in train]), np.array([math.log(r["wlc"]) for r in train]), rcond=None)
    c16 = Collector("AP-16", "ホールライフ合計の対数線形回帰（延床面積・評価年数・構造・用途）", "全段階の計算", "WLC", ["SUM-03", "SUM-04", "SUM-05"], "M5")
    for r in test:
        c16.add(r["scenario"], r["wlc"], math.exp(float(np.dot(features(r), beta))), r["wlc"])
    out["AP-16"] = c16.result()
    out["AP-16"]["n_parameters"] = int(len(beta))

    # AP-14: whole-life total at another study period by linear interpolation between two evaluated periods
    c14 = Collector("AP-14", "評価期間 T=60 の合計を、同じ建物の T=50 と T=75 の結果からの直線補間で求める", "評価期間ごとの再計算", "WLC", ["SUM-03"], "M3")
    for r in records[: min(80, len(records))]:
        vals = {}
        for T2 in (50.0, 60.0, 75.0):
            s2 = copy.deepcopy(r["scenario"])       # same building, only the study period changes
            s2.boundary.study_period = T2
            s2.boundary.baseline_scenario = None
            vals[T2] = registry.run_all(s2, ids=["SUM-03"])["SUM-03"]["value"]
        c14.add(r["scenario"], vals[60.0], vals[50.0] + (vals[75.0] - vals[50.0]) * 10.0 / 25.0, vals[60.0])
    out["AP-14"] = c14.result()

    # AP-21: timber carbon storage from the volume and one mean storage per m3 (memo value)
    c21 = Collector("AP-21", "木材の炭素貯蔵：数量×（構造×用途ごとの平均の m3 当たり貯蔵量）", "密度×炭素含有率の入力", "STO-01（参考値）", ["STO-01"], "M3")
    sbar = group_mean(train, lambda r: r["sto"] / r["timber"] if r["sto"] and r["timber"] else None)
    for r in test:
        if r["sto"] and r["timber"] and grp(r) in sbar:
            c21.add(r["scenario"], r["sto"], sbar[grp(r)] * r["timber"])
    out["AP-21"] = c21.result()

    # AP-22b: CO2-only total as a constant share of the all-gas total
    c22 = Collector("AP-22b", "CO2 のみの合計 = 全ガスの合計 ×（構造×用途ごとの平均の CO2 比）", "CO2 版の並行算定", "CO2 のみの合計（X-05）", ["X-05"], "M3")
    kappa = group_mean(train, lambda r: r["co2"] / r["total_inc"] if r["total_inc"] else None)
    for r in test:
        if r["co2"] and grp(r) in kappa:
            c22.add(r["scenario"], r["co2"], kappa[grp(r)] * r["total_inc"])
    out["AP-22b"] = c22.result()

    for cid in ("AP-10", "AP-10b", "AP-11", "AP-12", "AP-13", "AP-15", "AP-16", "AP-17", "AP-18", "AP-18a", "AP-18b", "AP-18c",
                "AP-19a", "AP-21", "AP-22b", "AP-09c"):
        out[cid]["data_dependence"] = ("誤差は建物ごとの資材構成・係数や条件のばらつき・使用量の分布で決まる。ここでの値は架空の母集団上のもので、"
                                       "実建物での精度を示さない。")
    out["AP-14"]["note"] = "同じ架空シナリオの評価期間だけを 50・60・75 年に変えて基準計算した結果どうしの比較。"
    return {"schema_version": "2.0", "population": n, "data_statement": "SYNTHETIC_FICTIONAL data only.",
            "error_definition": "(candidate - reference) / reference, signed; negative = under-estimation. total_error divides the same difference by the whole-life total (all 14 stages).",
            "by_material_class_note": "by_material_class は、資材の行に作用する候補について、1 シナリオ内の資材区分ごとの合計の誤差を集めたもの（設備は EQUIPMENT）。",
            "row_data_rebuilds_reference_B4_max_rel_diff": worst_rebuild,
            "numbering_note": "AP-07 は複合係数の構成材の切り捨て（AP-07a・AP-07b）。初版では測定せずに番号だけ空けていた。AP-20 は点推定ではなく上下限。",
            "targets": {"total": TARGET_TOTAL, "stage": TARGET_STAGE}, "candidates": out}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--population", type=int, default=400)
    args = ap.parse_args()
    result = run(args.population)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"population {result['population']}, B4 rebuilt from row data within {result['row_data_rebuilds_reference_B4_max_rel_diff']:.1e}")
    for cid, c in result["candidates"].items():
        s = c.get("stage_error")
        if s and s.get("n"):
            t = c["total_error"]
            print(f"{cid:7s} n={s['n']:4d} mean {s['mean_signed']:+.4f} p95|e| {s['p95_abs']:.4f} over {s['max_over']:+.4f} "
                  f"under {s['max_under']:+.4f} | total p95 {t['p95_abs']:.4f}  {c['title'][:44]}" if t.get("n") else
                  f"{cid:7s} n={s['n']:4d} mean {s['mean_signed']:+.4f} p95|e| {s['p95_abs']:.4f} over {s['max_over']:+.4f} "
                  f"under {s['max_under']:+.4f}  {c['title'][:44]}")
    b = result["candidates"]["AP-20"]
    print(f"AP-20   n={b['n']} inside {b['share_reference_inside_bracket']:.3f} width mean {b['bracket_width_relative_to_reference']['mean_abs']:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
