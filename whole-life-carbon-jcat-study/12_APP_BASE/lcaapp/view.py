"""What the result screen shows, taken from the engine's results (no number is made up here).

Every figure names the result key it was read from (``source``). A figure the engine did not
return is ``status = "not_computed"`` and is shown as 未計算; it is never replaced by a
placeholder. The only arithmetic done here is stated in the ``source`` text of the figure
(operational carbon = the two stage values B6 and B7 added).
"""
from __future__ import annotations

import math
from typing import Any

UNIT = "kg-CO2e"
OPERATIONAL_STAGES = ("B6", "B7")
STAGE_LABELS = {
    "A1-A3": "資材製造", "A4": "輸送", "A5": "施工", "B1": "使用（冷媒など）", "B2": "維持保全", "B3": "修繕",
    "B4": "更新", "B5": "改修", "B6": "運用エネルギー", "B7": "運用の水・廃棄物", "C1": "解体", "C2": "廃棄物輸送",
    "C3": "中間処理", "C4": "最終処分",
}
CHECK_LABELS = {
    "SYS-01": "入力値の状態（欠損の有無）", "SYS-02": "単位の整合", "SYS-03": "係数の出典・使用許諾",
    "SYS-04": "延床面積と用途別面積の一致", "QA-01": "段階の重複計上がないこと", "QA-02": "事象の時期が評価期間内にあること",
    "QA-03": "使用した係数の出典", "QA-04": "用途別面積の検算", "C-05": "資材の質量収支",
}
STANDING_NOTE = ("この結果は、架空データで検証した独立概念モデル（70 評価単位）による計算である。"
                 "他の算定ツールの結果との一致や、実建築物に対する精度を示すものではない。")
METHOD_NOTE = ("計算は既存の 2 構造エンジン（マスク付き積和・節点スペクトル）で行った。近似式は使っていない。"
               "基準計算との差は、架空データ 1,293 組の検証で相対 2.2e-12 以下（11_UNIFIED_SYSTEM/VERIFICATION.md）。")


def _num(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _get(results: dict, unit: str, key: str):
    part = results.get(unit)
    return part.get(key) if isinstance(part, dict) else None


def _indicator(key: str, label: str, value: Any, unit: str, source: str, complete: Any = None, why: str = "") -> dict:
    if not _num(value):
        return {"key": key, "label": label, "value": None, "unit": unit, "status": "not_computed", "source": source,
                "reason": why or "エンジンが値を返さなかった"}
    status = "incomplete" if complete is False else "ok"
    out = {"key": key, "label": label, "value": value, "unit": unit, "status": status, "source": source}
    if status == "incomplete":
        out["reason"] = "欠けた入力があり、その分は合計に入っていない"
    return out


def build(results: dict, study_period: float, context: dict | None = None) -> dict:
    """Display model of one calculation. ``context`` carries what is known about the input."""
    context = context or {}
    by_stage = _get(results, "X-02", "by_stage") or {}
    complete = _get(results, "X-02", "complete")
    indicators = [
        _indicator("whole_life", "ホールライフカーボン総量", _get(results, "SUM-03", "value"), UNIT, "SUM-03.value",
                   _get(results, "SUM-03", "complete")),
        _indicator("upfront", "アップフロントカーボン（A1〜A5）", _get(results, "SUM-01", "value"), UNIT, "SUM-01.value",
                   _get(results, "SUM-01", "complete")),
        _indicator("embodied", "エンボディドカーボン（B6・B7 以外）", _get(results, "SUM-02", "value"), UNIT, "SUM-02.value",
                   _get(results, "SUM-02", "complete")),
    ]
    b6, b7 = by_stage.get("B6"), by_stage.get("B7")
    indicators.append(_indicator(
        "operational", "オペレーショナルカーボン（B6＋B7）", b6 + b7 if _num(b6) and _num(b7) else None, UNIT,
        "X-02.by_stage の B6 と B7 の和（表示側で 2 値を加算）", complete, "段階 B6・B7 の値がそろっていない"))
    area_why = "延床面積が未入力、または正の値でない"
    indicators += [
        _indicator("per_area", "延床面積当たり", _get(results, "SUM-04", "value"), UNIT + "/m2", "SUM-04.value",
                   _get(results, "SUM-03", "complete"), area_why),
        _indicator("per_area_year", "延床面積・年当たり", _get(results, "SUM-05", "value"), UNIT + "/m2/年", "SUM-05.value",
                   _get(results, "SUM-03", "complete"), area_why),
        _indicator("tonnes", "ホールライフカーボン総量（t 換算）", _get(results, "SUM-06", "value"), "t-CO2e", "SUM-06.value",
                   _get(results, "SUM-03", "complete")),
    ]
    shares = _get(results, "SUM-07", "by_stage") if _get(results, "SUM-07", "defined") else None
    included = context.get("included_stages")
    stages = []
    for stage in by_stage:
        value = by_stage[stage]
        stages.append({"stage": stage, "label": STAGE_LABELS.get(stage, ""), "value": value if _num(value) else None,
                       "share": shares.get(stage) if isinstance(shares, dict) and _num(shares.get(stage)) else None,
                       "included": None if included is None else stage in included})
    by_year, cumulative = _get(results, "X-07", "by_year"), _get(results, "X-07", "cumulative")
    series = None
    if isinstance(by_year, list) and isinstance(cumulative, list) and len(by_year) == len(cumulative) and by_year \
            and all(_num(v) for v in by_year) and all(_num(v) for v in cumulative):
        series = {"by_year": by_year, "cumulative": cumulative, "source": "X-07.by_year, X-07.cumulative",
                  "start_year": context.get("study_start_year")}
    gases = None
    by_gas = _get(results, "X-04", "by_gas")
    if isinstance(by_gas, dict):
        gases = {"by_gas": {g: v for g, v in by_gas.items() if _num(v)},
                 "co2e_from_gases": _get(results, "X-04", "co2e_from_gases"),
                 "grid_co2e": _get(results, "X-04", "grid_co2e"),
                 "refrigerant_co2e": _get(results, "X-04", "refrigerant_co2e"), "source": "X-04"}
    comparison = results.get("SUM-08") if isinstance(results.get("SUM-08"), dict) else None
    checks = []
    for uid, label in CHECK_LABELS.items():
        part = results.get(uid)
        if not isinstance(part, dict):
            checks.append({"id": uid, "label": label, "ok": None, "n": None})
            continue
        lists = [part[k] for k in ("violations", "stage_mismatches", "warnings", "under_allocated") if isinstance(part.get(k), list)]
        n = sum(len(x) for x in lists) if lists else None            # None: the unit lists nothing, it only judges
        checks.append({"id": uid, "label": label, "ok": part.get("ok") if isinstance(part.get("ok"), bool) else None, "n": n,
                       "examples": [str(x) for x in (part.get("violations") or [])[:5]] if isinstance(part.get("violations"), list) else []})
    skipped = {uid: part["n_skipped"] for uid, part in results.items()
               if isinstance(part, dict) and _num(part.get("n_skipped")) and part["n_skipped"] > 0}
    return {
        "study_period": study_period, "unit": UNIT, "indicators": indicators, "stages": stages, "series": series,
        "gases": gases, "comparison": comparison, "checks": checks,
        "complete": complete if isinstance(complete, bool) else None,
        "incomplete_units": list(_get(results, "X-02", "incomplete_units") or []),
        "skipped": skipped,
        "notes": notes(results, context, complete, skipped),
    }


def notes(results: dict, context: dict, complete: Any, skipped: dict) -> list[dict]:
    """Notes on unsupported input and on the standing of the figures, written after the calculation."""
    out = [{"level": "info", "text": STANDING_NOTE}, {"level": "info", "text": METHOD_NOTE}]
    kind = context.get("data_kind")
    if kind == "fictional":
        out.append({"level": "info", "text": "入力は架空データ（検証用）である。実在の建物の値ではない。"})
    else:
        out.append({"level": "warning", "text": "入力データの種別は「%s」。値の出所と正しさは確認していない。" % (kind or "unknown")})
    ref = context.get("refset")
    if ref:
        text = "原単位・換算の参照データ：%s（版 %s、種別 %s）。" % (ref.get("name"), ref.get("version"), ref.get("data_kind"))
        if ref.get("data_kind") == "fictional":
            text += "架空の値であり、実在の排出原単位ではない。"
        out.append({"level": "info", "text": text})
    if complete is False:
        units = _get(results, "X-02", "incomplete_units") or []
        out.append({"level": "warning", "text": "合計は不完全である。欠けた入力のため計算できなかった部分は合計に入っていない"
                    + ("（該当する評価単位：%s）。" % "、".join(map(str, units[:20])) if units else "。")})
    if skipped:
        out.append({"level": "warning", "text": "入力が欠けていて計算から外れた行がある（評価単位ごとの行数：%s）。"
                    % "、".join("%s %d" % (u, n) for u, n in sorted(skipped.items())[:20])})
    counts = context.get("not_passed_counts") or {}
    for state, label in (("missing", "未入力"), ("absent", "存在しない"), ("invalid", "使えない値")):
        if counts.get(state):
            extra = ""
            if state == "missing" and counts.get("missing_optional"):
                extra = "うち %d 個は、空でもよい任意の項目。" % counts["missing_optional"]
            out.append({"level": "info" if state != "invalid" else "warning",
                        "text": "%sの項目が %d 個ある（エンジンへは値なしとして渡した。ゼロとはみなしていない）。%s" % (label, counts[state], extra)})
    if context.get("n_others"):
        out.append({"level": "info", "text": "「その他」の入力 %d 件は保存しているが、計算には使っていない。" % context["n_others"]})
    if context.get("n_unsupported"):
        out.append({"level": "warning", "text": "計算に使えなかった入力（未対応項目）が %d 件ある。内容は保存している。" % context["n_unsupported"]})
    if context.get("n_unbound"):
        out.append({"level": "info", "text": "この分類に対応項目がないエンジン側の入力が %d 個ある（未入力として扱った）。" % context["n_unbound"]})
    for note in context.get("conversion_notes") or []:
        out.append({"level": note.get("level", "info"), "text": note.get("message", "")})
    if context.get("engine_warnings"):
        out.append({"level": "warning", "text": "計算中に数値の警告が出た（%s）。極端に大きい入力などで、一部の値が有限でない可能性がある。"
                    % "、".join(context["engine_warnings"][:3])})
    if context.get("n_replaced"):
        out.append({"level": "warning", "text": "計算結果のうち有限でない値 %d 個は「未計算」として保存した。" % context["n_replaced"]})
    comparison = results.get("SUM-08")
    if isinstance(comparison, dict) and comparison.get("status") == "NOT_COMPARABLE":
        out.append({"level": "warning", "text": "基準案との比較はできなかった（理由：%s）。" % "、".join(map(str, comparison.get("reasons") or []))})
    return out
