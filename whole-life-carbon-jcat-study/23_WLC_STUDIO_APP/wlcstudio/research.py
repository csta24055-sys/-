"""Turn a building chosen from the PLATEAU candidates into candidate values of the basic-information fields.

What PLATEAU records directly (storeys, measured height, address, usage) becomes a candidate that takes the
state 取得・確認済み when the user accepts it. What PLATEAU does not record is either not proposed (structure,
completion year) or proposed as an explicit assumption (total floor area = roof area × storeys × the dataset's
floor-area factor). Nothing is accepted automatically.
"""
from __future__ import annotations

import datetime as _dt

from .provenance import Value
from .sources.plateau import USAGE_HINT

STRUCTURE_WORDS = {"SRC": ("鉄骨鉄筋",), "RC": ("鉄筋コンクリート",), "S": ("鉄骨造", "軽量鉄骨"), "W": ("木造",)}


def plateau_proposals(c: dict, structure_chosen: str | None) -> tuple[list[Value], list[str]]:
    today = _dt.date.today().isoformat()
    bid = c.get("plateau_building_id") or c.get("gml_id") or "?"
    detail = "PLATEAU 建物 %s（タイル %s、調査年 %s）" % (bid, c.get("tile"), c.get("survey_year"))
    kw = dict(source_id="plateau", source_detail=detail, retrieved_at=today, permission="plateau_open_data")
    out, notes = [], []
    if c.get("storeys_above"):
        out.append(Value("b_floors_above", "confirmed", c["storeys_above"], "階", method="plateau_attribute",
                         note="bldg:storeysAboveGround", **kw))
    if c.get("storeys_below") is not None:
        if c["storeys_below"] == 0:
            out.append(Value("b_floors_below", "not_applicable", None, "", method="plateau_attribute",
                             note="bldg:storeysBelowGround = 0（地下なし）", **kw))
        else:
            out.append(Value("b_floors_below", "confirmed", c["storeys_below"], "階", method="plateau_attribute",
                             note="bldg:storeysBelowGround", **kw))
    if c.get("measured_height_m"):
        out.append(Value("b_height", "confirmed", round(float(c["measured_height_m"]), 2), "m", method="plateau_attribute",
                         note="bldg:measuredHeight（計測高さ。設計の高さと違うことがある）", **kw))
    if c.get("address"):
        out.append(Value("b_address", "confirmed", c["address"], "", method="plateau_attribute", note="bldg:address", **kw))
    tfa = c.get("total_floor_area_m2")
    if tfa and 0 < tfa < 1e7:
        out.append(Value("b_gfa", "confirmed", round(float(tfa), 2), "m2", method="plateau_attribute",
                         note="uro:totalFloorArea（都市計画基礎調査などの記録。自治体によって無い）", **kw))
    yc = c.get("year_of_construction")
    if yc and 1868 <= yc <= 2200:
        out.append(Value("b_completion_year", "confirmed", int(yc), "年", method="plateau_attribute",
                         note="bldg:yearOfConstruction", **kw))
    if c.get("estimated_gross_floor_area_m2") and not (tfa and tfa > 0):
        out.append(Value("b_gfa", "assumption", c["estimated_gross_floor_area_m2"], "m2", method="plateau_roof_x_storeys",
                         note="屋根伏面積 %.1f m2 × 地上階数 %s × 延べ面積換算係数 %s。延床面積の記録ではない（仮定）。"
                              % (c["roof_edge_area_m2"], c["storeys_above"], c["floor_area_factor"]), **kw))
    elif c.get("roof_edge_area_m2"):
        notes.append("延べ面積換算係数が無いので、延床面積の仮定値は作らなかった（屋根伏面積 %.1f m2）" % c["roof_edge_area_m2"])
    use = USAGE_HINT.get(c.get("usage") or "")
    if use:
        out.append(Value("b_use", "assumption", use, "", method="plateau_usage_hint",
                         note="PLATEAU の用途「%s」からの対応（用途の分類が違うので確認する）" % c["usage"], **kw))
    elif c.get("usage"):
        notes.append("PLATEAU の用途「%s」はエンジンの用途に対応づけていない" % c["usage"])
    code = str(c.get("structure_type") or c.get("structure_code") or "")
    if code:
        guess = next((s for s, words in STRUCTURE_WORDS.items() if any(w in code for w in words)), None)
        notes.append("PLATEAU の建物構造コード：%s%s" % (code, "" if guess is None else "（%s 造の手掛かり）" % guess))
        if guess and structure_chosen and guess != structure_chosen:
            notes.append("選んだ構造（%s）と PLATEAU の手掛かり（%s）が違う。図面で確かめる" % (structure_chosen, guess))
    else:
        notes.append("PLATEAU にこの建物の構造の記録が無い（構造は選んだものを使う）")
    if not (yc and 1868 <= yc <= 2200):
        notes.append("この建物には PLATEAU の建築年の記録が無い。")
    return out, notes
