#!/usr/bin/env python3
"""Approximate candidates measured against the reference calculation.

Each candidate replaces an exact step by something simpler. The signed relative error
(candidate - reference) / reference is collected on a population of fictional scenarios,
for the affected stage and for the whole-life total, overall and by structure and use.
Negative errors are under-estimations and are reported separately.

All data are synthetic. For candidates whose error depends on how real buildings are
composed (class-representative factors, floor-area regression, top-contributor
truncation, floor-area energy estimate) the numbers only demonstrate the method on a
fictional population; they are NOT evidence of practical accuracy.

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
from refcalc.base import year_weights
from refcalc.units_b import equipment_extra_lines, material_install_line
from refcalc.units_pre_a import SIMPLE_CLASSES, simple_class, summary_quantity
from synth import population

STUDY = Path(__file__).resolve().parents[2]
OUT = STUDY / "04_VERIFICATION" / "approximation_study.json"
TARGET_TOTAL, TARGET_STAGE = 0.01, 0.02


def stats(errors: list[float]) -> dict:
    if not errors:
        return {"n": 0}
    a = [abs(e) for e in errors]
    return {"n": len(errors), "mean_signed": sum(errors) / len(errors), "mean_abs": sum(a) / len(a),
            "p95_abs": percentile(a, 95), "max_abs": max(a), "max_over": max(errors), "max_under": min(errors),
            "share_under_estimated": sum(e < -1e-12 for e in errors) / len(errors)}


class Collector:
    def __init__(self, cid, title, replaces, stage, units):
        self.meta = {"candidate_id": cid, "title": title, "replaces": replaces, "stage": stage, "units": units}
        self.stage, self.total, self.groups = [], [], {}

    def add(self, scn, ref_stage, cand_stage, wlc):
        if ref_stage == 0.0:
            return
        e_stage = (cand_stage - ref_stage) / ref_stage
        e_total = (cand_stage - ref_stage) / wlc if wlc else 0.0
        self.stage.append(e_stage)
        self.total.append(e_total)
        for key in (f"structure={scn.meta.structure}", f"use={scn.meta.use}"):
            self.groups.setdefault(key, []).append(e_stage)

    def result(self):
        s, t = stats(self.stage), stats(self.total)
        out = dict(self.meta)
        out.update(stage_error=s, total_error=t,
                   by_group={k: stats(v) for k, v in sorted(self.groups.items())},
                   within_stage_target=bool(s.get("n")) and s["max_abs"] <= TARGET_STAGE,
                   within_total_target=bool(t.get("n")) and t["max_abs"] <= TARGET_TOTAL,
                   under_estimates=bool(s.get("n")) and s["max_under"] < -1e-9)
        return out


def per_renewal_emissions(scn, res):
    """(cycle, u, explicit count or None) for every row that can be renewed."""
    out = []
    q_ord = res["A13-05"]["q_ord"]
    for i, row in enumerate(scn.materials):
        u = sum(res[k]["by_item"][i] for k in ("A13-01", "A13-03", "A4-01", "A4-02", "C2-01", "C3-01", "C4-01"))
        inst = material_install_line(scn, row, q_ord[i])
        if inst is not None:
            u += inst[1] * scn.factors[inst[0]].value
        out.append((row.refresh_cycle, u, None))
    for j, eq in enumerate(scn.equipment):
        u = res["X-01"]["by_item"][j] + res["X-14"]["by_item"][j]
        u += sum(act * scn.factors[fid].value for fid, act in equipment_extra_lines(scn, eq))
        out.append((eq.service_life, u, len(res["B4-01"]["events"][j]) if eq.replacement_event_list is not None else None))
    return out


def run(n_population: int) -> dict:
    registry.load_all()
    C = {
        "AP-01": Collector("AP-01", "更新回数の連続近似 N ≈ max(0, T/c − 1)", "回数関数 N(T,c)", "B4", ["B4-01", "B4-03", "B4-02", "B5-01", "X-08", "X-10"]),
        "AP-02": Collector("AP-02", "更新回数の中点補正 N ≈ max(0, T/c − 1/2)", "回数関数 N(T,c)", "B4", ["B4-01", "B4-03", "B4-02", "B5-01", "X-08", "X-10"]),
        "AP-03": Collector("AP-03", "更新回数の切り捨てなし N ≈ T/c", "回数関数 N(T,c)", "B4", ["B4-01", "B4-03", "B4-02"]),
        "AP-04": Collector("AP-04", "修繕の更新年除外を無視（B3-02 で B3-01 を代用）", "修繕の年次積算", "B3", ["B3-01", "B3-02"]),
        "AP-05": Collector("AP-05", "冷媒漏洩の線形近似 1−(1−r)^k ≈ r·k", "充填サイクルの閉形式", "B1", ["B1-02", "B1-03", "B1-04"]),
        "AP-06": Collector("AP-06", "端材倍率の線形化 1/(1−w) ≈ 1+w", "発注量の算出", "A1-A3", ["A13-05", "X-13", "A13-01", "A13-03"]),
        "AP-08": Collector("AP-08", "買電排出を 平均買電量×平均係数×T で近似", "買電量×係数の年次積算", "B6", ["B6-01", "B6-03", "B6-04", "B2-01"]),
        "AP-09a": Collector("AP-09a", "電力係数を 5 年ごとの点の直線補間で持つ", "年次の電力係数系列", "B6", ["X-06", "B6-01", "X-11"]),
        "AP-09b": Collector("AP-09b", "電力係数を 10 年ごとの点の直線補間で持つ", "年次の電力係数系列", "B6", ["X-06", "B6-01", "X-11"]),
        "AP-12": Collector("AP-12", "質量上位 20％ の資材行だけ詳細計算し、残りを質量比で補う", "資材製造の全行計算", "A1-A3", ["A13-01", "A13-03", "X-17"]),
        "AP-13": Collector("AP-13", "面積当たり電力使用量による買電排出の推定（X-11）で実績計算を代用", "買電排出の年次積算", "B6", ["X-11", "B6-01"]),
    }
    conditional = {"AP-08:CONSTANT": [], "AP-08:LINEAR_TREND": [], "AP-08:TABLE": []}
    by_grid = {}
    leak_guard = {"rk<=0.05": [], "0.05<rk<=0.2": [], "rk>0.2": []}
    records = []                      # per scenario data for the population-level candidates
    n = 0
    for scn in population.verification_population(n_population, seed=20261111, max_size="M"):
        n += 1
        res = registry.run_all(scn)
        T = scn.boundary.study_period
        w = year_weights(T)
        Y = len(w) - 1
        stage = res["X-02"]["by_stage_all"]
        wlc = sum(stage.values())

        rows = per_renewal_emissions(scn, res)
        for cid, fn in (("AP-01", lambda T, c: max(0.0, T / c - 1.0)), ("AP-02", lambda T, c: max(0.0, T / c - 0.5)),
                        ("AP-03", lambda T, c: T / c)):
            approx = 0.0
            for cycle, u, explicit in rows:
                if explicit is not None:
                    approx += explicit * u
                elif cycle:
                    approx += fn(T, cycle) * u
            C[cid].add(scn, stage["B4"], approx, wlc)
        C["AP-04"].add(scn, stage["B3"], res["B3-02"]["value"], wlc)

        # refrigerants: linear leak per charge cycle
        approx_b1 = 0.0
        for dev, st in zip(scn.refrigerants, res["B1-02"]["_state"]):
            if st is None:
                continue
            years = [y for y, _ in st["before_events"]]
            exact_leak, before, end = cf.refrigerant_device(T, dev.charge_mass_kg, dev.annual_leak_rate, dev.top_up, years)
            m0, r = dev.charge_mass_kg, dev.annual_leak_rate
            leak = m0 * r * T                  # linear: every year leaks from a full charge
            approx_dev = leak
            if dev.replacement_loss_rate is not None:
                approx_dev += len(years) * m0 * dev.replacement_loss_rate
            if dev.end_of_life_recovery_rate is not None:
                approx_dev += m0 * (1.0 - dev.end_of_life_recovery_rate)
            approx_b1 += approx_dev * dev.gwp
            exact_dev = exact_leak + sum(b * (dev.replacement_loss_rate or 0.0) for b in before)
            exact_dev += end * (1.0 - dev.end_of_life_recovery_rate) if dev.end_of_life_recovery_rate is not None else 0.0
            if not dev.top_up and exact_dev > 0.0:
                cycle_years = T / (len(years) + 1)
                rk = r * cycle_years
                key = "rk<=0.05" if rk <= 0.05 else "0.05<rk<=0.2" if rk <= 0.2 else "rk>0.2"
                leak_guard[key].append(approx_dev / exact_dev - 1.0)
        C["AP-05"].add(scn, stage["B1"], approx_b1, wlc)

        # waste-rate linearisation on design-quantity rows
        approx_a = res["A13-04"]["value"] + res["X-01"]["value"]
        for i, row in enumerate(scn.materials):
            e = res["A13-01"]["by_item"][i] + res["A13-03"]["by_item"][i]
            if row.quantity_basis == "DESIGN" and row.waste_rate is not None:
                e *= (1.0 + row.waste_rate) * (1.0 - row.waste_rate)
            approx_a += e
        C["AP-06"].add(scn, stage["A1-A3"], approx_a, wlc)

        # electricity: mean demand x mean factor, and interpolated factor tables
        net, g = res["B6-04"]["by_year"], res["X-06"]["by_year"]
        elec_ref = sum(w[y] * net[y] * g[y] for y in range(1, Y + 1))
        fuel = res["B6-03"]["value"] - elec_ref
        b6_ref = res["B6-03"]["value"]
        if elec_ref > 0.0:
            mean_net = sum(w[y] * net[y] for y in range(1, Y + 1)) / T
            mean_g = sum(w[y] * g[y] for y in range(1, Y + 1)) / T
            approx = mean_net * mean_g * T + fuel
            C["AP-08"].add(scn, b6_ref, approx, wlc)
            kinds = {scn.operation.electricity.kind, scn.operation.onsite_generation.kind, scn.operation.onsite_export.kind}
            key = "CONSTANT" if kinds == {"CONSTANT"} else "TABLE" if "TABLE" in kinds else "LINEAR_TREND"
            conditional[f"AP-08:{key}"].append((approx - b6_ref) / b6_ref)
            for cid, step in (("AP-09a", 5), ("AP-09b", 10)):
                gi = [0.0]
                for k in range(Y):
                    lo = (k // step) * step
                    hi = min(lo + step, Y - 1) if Y > 1 else lo
                    if hi <= lo:
                        gi.append(g[lo + 1])
                    else:
                        gi.append(g[lo + 1] + (g[hi + 1] - g[lo + 1]) * (k - lo) / (hi - lo))
                approx = sum(w[y] * net[y] * gi[y] for y in range(1, Y + 1)) + fuel
                C[cid].add(scn, b6_ref, approx, wlc)
                by_grid.setdefault(f"{cid}:{scn.operation.grid.kind}", []).append((approx - b6_ref) / b6_ref)
            x11 = res["X-11"]["value"]
            if x11 is not None:
                C["AP-13"].add(scn, b6_ref, x11 + fuel, wlc)

        # top contributors by mass (known without any factor): detailed for the top 20 percent, the rest scaled by mass
        masses, emis = [], []
        for i, row in enumerate(scn.materials):
            m = row.end_of_life.mass_kg or 0.0
            masses.append(m)
            emis.append(res["A13-01"]["by_item"][i] + res["A13-03"]["by_item"][i])
        mat_ref = sum(emis)
        if mat_ref > 0.0 and len(masses) >= 10:
            order = sorted(range(len(masses)), key=lambda i: -masses[i])
            top = order[: max(1, len(order) // 5)]
            m_top, e_top = sum(masses[i] for i in top), sum(emis[i] for i in top)
            approx = e_top * sum(masses) / m_top if m_top else 0.0
            C["AP-12"].add(scn, mat_ref, approx, wlc)

        # data for population-level candidates
        class_e = {k: 0.0 for k in SIMPLE_CLASSES}
        for i, row in enumerate(scn.materials):
            k = simple_class(row)
            if k is not None:
                class_e[k] += emis[i]
        records.append({"structure": scn.meta.structure, "use": scn.meta.use, "T": T, "area": scn.project.gross_floor_area,
                        "wlc": wlc, "stage": dict(stage), "class_e": class_e,
                        "class_q": {k: summary_quantity(scn, k) for k in SIMPLE_CLASSES}, "mat_ref": mat_ref,
                        "scenario": scn})

    out = {cid: c.result() for cid, c in C.items()}
    out["AP-08"]["by_profile_kind"] = {k.split(":")[1]: stats(v) for k, v in conditional.items()}
    for cid in ("AP-09a", "AP-09b"):
        out[cid]["by_grid_kind"] = {k.split(":")[1]: stats(v) for k, v in sorted(by_grid.items()) if k.startswith(cid)}
    out["AP-05"]["by_rate_times_cycle_years_no_top_up_devices"] = {k: stats(v) for k, v in leak_guard.items()}

    # ---- population-level candidates: fit on the first half, test on the second half ----
    half = len(records) // 2
    train, test = records[:half], records[half:]

    def group_mean(rows, key, value):
        acc = {}
        for r in rows:
            k = key(r)
            s = acc.setdefault(k, [0.0, 0])
            s[0] += value(r)
            s[1] += 1
        return {k: s[0] / s[1] for k, s in acc.items()}

    # AP-10: class-representative factors per (structure, use) from the training half
    fbar = {}
    for k in SIMPLE_CLASSES:
        num = group_mean(train, lambda r: (r["structure"], r["use"]), lambda r, k=k: r["class_e"][k])
        den = group_mean(train, lambda r: (r["structure"], r["use"]), lambda r, k=k: r["class_q"][k])
        fbar[k] = {g: (num[g] / den[g] if den[g] else 0.0) for g in num}
    c10 = Collector("AP-10", "6 区分の要約数量×（構造×用途ごとの代表係数）で資材製造を概算", "資材製造の全行計算", "A1-A3（資材分）", ["X-17", "A13-01", "A13-03"])
    for r in test:
        g = (r["structure"], r["use"])
        if g not in fbar["CONCRETE"]:
            continue
        approx = sum(r["class_q"][k] * fbar[k][g] for k in SIMPLE_CLASSES)
        c10.add(r["scenario"], r["mat_ref"], approx, r["wlc"])
    out["AP-10"] = c10.result()

    # AP-11: whole-life total per floor area and year from (structure, use) group means
    c11 = Collector("AP-11", "延床面積×評価年数×（構造×用途ごとの平均原単位）でホールライフ合計を概算", "全段階の計算", "WLC", ["SUM-03", "SUM-04", "SUM-05"])
    mean_int = group_mean(train, lambda r: (r["structure"], r["use"]), lambda r: r["wlc"] / (r["area"] * r["T"]))
    for r in test:
        g = (r["structure"], r["use"])
        if g in mean_int:
            c11.add(r["scenario"], r["wlc"], mean_int[g] * r["area"] * r["T"], r["wlc"])
    out["AP-11"] = c11.result()

    # AP-15: every stage from floor area (and study years for the use stages) times a (structure, use) mean intensity
    ANNUAL = ("B1", "B2", "B3", "B4", "B5", "B6", "B7")
    by_stage15 = {}
    c15 = Collector("AP-15", "段階ごとに 延床面積（使用段階は×評価年数）×（構造×用途ごとの平均原単位）で概算する共通近似モデル",
                    "各段階の詳細計算", "全14段階", ["全排出単位"])
    for st in ("A1-A3", "A4", "A5", "B1", "B2", "B3", "B4", "B5", "B6", "B7", "C1", "C2", "C3", "C4"):
        scale = (lambda r: r["area"] * r["T"]) if st in ANNUAL else (lambda r: r["area"])
        mean_s = group_mean(train, lambda r: (r["structure"], r["use"]), lambda r, st=st, scale=scale: r["stage"][st] / scale(r))
        errs = []
        for r in test:
            g = (r["structure"], r["use"])
            if g in mean_s and r["stage"][st] > 0.0:
                errs.append(mean_s[g] * scale(r) / r["stage"][st] - 1.0)
        by_stage15[st] = stats(errs)
    for r in test:
        g = (r["structure"], r["use"])
        if g in mean_int:
            approx = 0.0
            for st in by_stage15:
                scale = r["area"] * r["T"] if st in ANNUAL else r["area"]
                m = group_mean(train, lambda q: (q["structure"], q["use"]), lambda q, st=st: q["stage"][st] / (q["area"] * q["T"] if st in ANNUAL else q["area"]))
                approx += m[g] * scale
            c15.add(r["scenario"], r["wlc"], approx, r["wlc"])
    out["AP-15"] = c15.result()
    out["AP-15"]["by_stage"] = by_stage15

    # AP-16: log-linear least-squares regression of the whole-life total on area, study years, structure and use
    import numpy as np
    structures = sorted({r["structure"] for r in records})
    uses = sorted({r["use"] for r in records})

    def features(r):
        return ([1.0, math.log(r["area"]), math.log(r["T"])] + [1.0 if r["structure"] == x else 0.0 for x in structures[1:]]
                + [1.0 if r["use"] == x else 0.0 for x in uses[1:]])

    X = np.array([features(r) for r in train])
    y = np.array([math.log(r["wlc"]) for r in train])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    c16 = Collector("AP-16", "ホールライフ合計の対数線形回帰（延床面積・評価年数・構造・用途）", "全段階の計算", "WLC", ["SUM-03", "SUM-04", "SUM-05"])
    for r in test:
        c16.add(r["scenario"], r["wlc"], math.exp(float(np.dot(features(r), beta))), r["wlc"])
    out["AP-16"] = c16.result()
    out["AP-16"]["n_parameters"] = int(len(beta))

    # AP-14: whole-life total at another study period by linear interpolation between two evaluated periods
    c14 = Collector("AP-14", "評価期間 T=60 の合計を、同じ建物の T=50 と T=75 の結果からの直線補間で求める", "評価期間ごとの再計算", "WLC", ["SUM-03"])
    for r in records[: min(80, len(records))]:
        vals = {}
        for T2 in (50.0, 60.0, 75.0):
            s2 = copy.deepcopy(r["scenario"])       # same building, only the study period changes
            s2.boundary.study_period = T2
            s2.boundary.baseline_scenario = None
            vals[T2] = registry.run_all(s2, ids=["SUM-03"])["SUM-03"]["value"]
        approx = vals[50.0] + (vals[75.0] - vals[50.0]) * (60.0 - 50.0) / 25.0
        c14.add(r["scenario"], vals[60.0], approx, vals[60.0])
    out["AP-14"] = c14.result()
    for cid in ("AP-10", "AP-11", "AP-12", "AP-13", "AP-15", "AP-16"):
        out[cid]["data_dependence"] = ("誤差は建物ごとの資材構成・係数のばらつき・使用量の分布で決まる。ここでの値は架空の母集団上のもので、"
                                       "実建物での精度を示さない。")
    out["AP-14"]["note"] = "同じ架空シナリオの評価期間だけを 50・60・75 年に変えて基準計算した結果どうしの比較。"
    return {"schema_version": "1.0", "population": n, "data_statement": "SYNTHETIC_FICTIONAL data only.",
            "error_definition": "(candidate - reference) / reference, signed; negative = under-estimation. total_error divides the same difference by the whole-life total.",
            "targets": {"total": TARGET_TOTAL, "stage": TARGET_STAGE}, "candidates": out}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--population", type=int, default=400)
    args = ap.parse_args()
    result = run(args.population)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    for cid, c in result["candidates"].items():
        s = c["stage_error"]
        if s.get("n"):
            print(f"{cid:7s} n={s['n']:4d} stage mean {s['mean_signed']:+.4f} p95|e| {s['p95_abs']:.4f} max over {s['max_over']:+.4f} "
                  f"max under {s['max_under']:+.4f} | total p95 {c['total_error']['p95_abs']:.4f}  {c['title']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
