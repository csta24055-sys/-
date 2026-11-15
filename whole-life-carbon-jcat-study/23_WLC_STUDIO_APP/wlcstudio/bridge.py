"""Bridge: the values of the four screens -> an lca-input/1 document for the existing app (12_APP_BASE).

The engine is not changed and not re-implemented. This module only writes the document that
lcaapp.service.Service.import_document() already accepts, and reports for every screen field whether
and how it reached the calculation.

Rules (implementation directive, section 0-5 and 4):
  * only value-bearing states (confirmed / from_drawing / statistical / assumption) are passed;
    not_obtained and not_computable stay None (MISSING) — never 0;
  * not_applicable is passed as an explicit zero only for fields whose catalogue entry says na="zero"
    (the quantity really is nil, e.g. no basement); a row/table that does not exist is left out;
  * the evaluation boundary (included life-cycle stages) is always written: without it the engine
    sums no stage and returns 0 with complete=True (found in the Phase 0 audit);
  * every owner record carries provenance_id and a states map, so the engine's SYS-01 sees the real
    state (OBSERVED / DERIVED / ESTIMATE / EXPLICIT_ZERO) instead of MISSING;
  * factor ids are taken from the active reference set through a factor profile; with the fictional
    set the result is labelled as a fictional-factor calculation, never as a real emission;
  * no address and no building name goes into the engine document (data minimisation).
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json

from . import fields as FL
from .provenance import HAS_VALUE, LABEL, Value

ENGINE_STATE = {"confirmed": "OBSERVED", "from_drawing": "DERIVED", "statistical": "ESTIMATE", "assumption": "ESTIMATE"}
PROV_RECORDS = {
    "OBSERVED": ("WLC-OBSERVED", "MEASURED", "HIGH"),
    "DERIVED": ("WLC-DERIVED", "DESIGN_DOCUMENT", "HIGH"),
    "ESTIMATE": ("WLC-ESTIMATE", "ESTIMATED", "LOW"),
}
PROFILE_UNIT = {"operation.electricity": "kWh/year", "operation.gas": "m3/year", "operation.oil": "L/year",
                "operation.district_heat": "MJ/year", "operation.onsite_generation": "kWh/year",
                "operation.onsite_export": "kWh/year", "water_waste.water": "m3/year", "water_waste.sewage": "m3/year",
                "water_waste.municipal_waste": "kg/year"}
TO_KG = {"kg": 1.0, "t": 1000.0}
# estimate methods whose concrete quantity covers the whole building including foundations
WHOLE_BUILDING_METHODS = {"rasmi_mi_x_gfa"}


class BridgeError(ValueError):
    pass


# ---------------------------------------------------------------------------------------------- factor profile
def factor_profile(refset: dict) -> dict:
    """Which factor id of the reference set serves which purpose.

    A licensed set may ship its own profile as refset["wlcstudio_profile"]. For the fictional demo set the
    profile is read from its naming convention and every id is checked to exist with the expected unit.
    Returns {"profile": {...}, "notes": [...], "kind": "fictional"|"licensed"|...}.
    """
    data = refset["data"]
    F = data["factors"]
    if "wlcstudio_profile" in refset:
        prof = refset["wlcstudio_profile"]
        notes = ["参照セットに付属の対応表を使った"]
    else:
        prof = {"material": {}, "delivery": {}, "install": {}, "eol": {}, "transport": {}, "haul": None,
                "fuel": {}, "op": {}, "water": {}, "equipment": {}}
        for cls in sorted({fid.split("-")[2] for fid in F if fid.startswith("F-MAT-") and fid.count("-") == 3}):
            for pre in ("F-MAT-%s-01", "F-MATKG-%s-01"):
                fid = pre % cls
                if fid in F:
                    prof["material"].setdefault(cls, {})[F[fid]["unit"]] = fid
            for key, fid in (("delivery", "F-DEL-%s" % cls), ("install", "F-INST-%s" % cls)):
                if fid in F:
                    prof[key][cls] = fid
            for route in ("REUSE", "RECYCLE", "PROCESSING", "LANDFILL"):
                fid = "F-EOL-%s-%s" % (cls, route)
                if fid in F:
                    prof["eol"].setdefault(cls, {})[route] = fid
        for mode in ("TRUCK_SMALL", "TRUCK_LARGE", "RAIL", "SHIP"):
            if "F-TR-" + mode in F:
                prof["transport"][mode] = "F-TR-" + mode
        hauls = sorted(fid for fid in F if fid.startswith("F-HAUL-"))
        prof["haul"] = hauls[0] if hauls else None
        if "F-SITE-DIESEL" in F:
            prof["fuel"]["DIESEL"] = "F-SITE-DIESEL"
        for name, fid in (("gas", "F-OP-GAS"), ("oil", "F-OP-OIL"), ("district_heat", "F-OP-DHEAT")):
            if fid in F:
                prof["op"][name] = fid
        for name, fid in (("water", "F-WATER"), ("sewage", "F-SEWAGE"), ("municipal_waste", "F-MSW")):
            if fid in F:
                prof["water"][name] = fid
        for trade, _ in FL.TRADES:
            ids = {"factor": "F-EQ-%s-01" % trade, "delivery": "F-EQDEL-%s" % trade, "install": "F-EQINST-%s" % trade,
                   "eol": "F-EQEOL-%s" % trade}
            if all(v in F for v in ids.values()):
                prof["equipment"][trade] = ids
        notes = ["架空の参照セットの命名規則から対応表を作った（各分類の代表として -01 の原単位、運搬は %s）" % prof["haul"]]
    return {"profile": prof, "notes": notes, "kind": refset.get("data_kind", "unknown"),
            "name": refset.get("name"), "version": refset.get("version")}


# ---------------------------------------------------------------------------------------------- helpers
class _Doc:
    def __init__(self, today: str):
        self.items: dict[str, dict] = {c: {} for c in ("building", "construction", "equipment", "operation", "assessment")}
        self.tables: dict[str, dict] = {c: {} for c in self.items}
        self.states: dict[str, dict] = {}            # owner -> {field: STATE}
        self.used_states: set[str] = set()
        self.reflect: dict[str, dict] = {}            # fid -> report row
        self.unconnected: list[dict] = []
        self.missing: list[str] = []
        self.assumed: list[str] = []
        self.double_count: list[str] = []
        self.today = today

    def item(self, cat, key, value):
        self.items[cat][key] = value

    def state(self, owner: str, key: str, st: str):
        self.states.setdefault(owner, {})[key] = st
        self.used_states.add("OBSERVED" if st == "EXPLICIT_ZERO" else st)

    def use(self, fid, v: Value | None, how: str, engine_keys: list[str]):
        r = self.reflect.setdefault(fid, {"field": fid, "label": FL.FIELDS[fid]["label"], "state": v.state if v else "not_obtained",
                                           "reflected": False, "how": [], "engine": []})
        r["reflected"] = True
        r["how"].append(how)
        r["engine"].extend(engine_keys)

    def skip(self, fid, v: Value | None, reason: str):
        r = self.reflect.setdefault(fid, {"field": fid, "label": FL.FIELDS[fid]["label"], "state": v.state if v else "not_obtained",
                                           "reflected": False, "how": [], "engine": []})
        r.setdefault("reasons", []).append(reason)


def _same_dim(factor_unit: str, unit: str) -> bool:
    """The quantity unit equals the factor unit, or both are masses (the set defines t <-> kg)."""
    return factor_unit == unit or (factor_unit in TO_KG and unit in TO_KG)


def _es(v: Value) -> str:
    """Engine state of a passed value."""
    if isinstance(v.value, (int, float)) and not isinstance(v.value, bool) and v.value == 0:
        return "EXPLICIT_ZERO"
    return ENGINE_STATE[v.state]


def _num(v: Value | None):
    """(number, engine_state, how) for a numeric field, or (None, None, reason)."""
    if v is None:
        return None, None, "未取得"
    if v.state in HAS_VALUE:
        return v.value, _es(v), LABEL[v.state]
    if v.state == "not_applicable":
        return "NA", None, "適用外"
    return None, None, LABEL[v.state]


# ---------------------------------------------------------------------------------------------- build
def build(values: dict[str, Value], refset: dict, title: str = "WLC Studio project", today: str | None = None) -> tuple[dict, dict]:
    """Return (lca-input/1 document, report). Raises BridgeError only for an unusable reference set."""
    today = today or _dt.date.today().isoformat()
    fp = factor_profile(refset)
    P = fp["profile"]
    d = _Doc(today)
    V = values.get

    def scalar(fid, cat, key, owner=None, field=None, conv=lambda x: x):
        v = V(fid)
        x, st, how = _num(v) if FL.FIELDS[fid]["type"] in ("number", "integer") else (
            (v.value, ENGINE_STATE[v.state], LABEL[v.state]) if v and v.state in HAS_VALUE else (None, None, LABEL[v.state] if v else "未取得"))
        if x == "NA":
            if FL.FIELDS[fid]["na"] == "zero":
                d.item(cat, key, 0.0 if FL.FIELDS[fid]["type"] == "number" else 0)
                if owner:
                    d.state(owner, field or key.split(".", 1)[1], "EXPLICIT_ZERO")
                d.use(fid, v, "適用外：0 として渡した（明示のゼロ）", [key])
            else:
                d.skip(fid, v, "適用外：渡していない")
            return None
        if x is None:
            d.skip(fid, v, how + "：渡していない（欠損のまま。0 にしない）")
            return None
        d.item(cat, key, conv(x))
        if owner and st:
            d.state(owner, field or key.split(".", 1)[1], st)
        d.use(fid, v, how, [key])
        return x

    # ------------------------------------------------------------------ building / project
    for fid, F in FL.FIELDS.items():
        if F["role"] == "record":
            d.skip(fid, V(fid), "記録のみ（計算に使われない項目。エンジンへは渡さない）")
    scalar("b_structure", "building", "project.structure_type")
    use = scalar("b_use", "building", "project.building_use")
    gfa = scalar("b_gfa", "building", "project.gross_floor_area", "project", "gross_floor_area")
    if use and gfa:
        d.item("building", "project.use_area_breakdown", {use: gfa})
        d.use("b_gfa", V("b_gfa"), "用途別面積 {用途: 延床面積} を作った", ["project.use_area_breakdown"])
    else:
        d.missing.append("用途と延床面積（用途別面積はエンジンの必須入力）")
    scalar("b_floors_above", "building", "project.floors_above")
    scalar("b_floors_below", "building", "project.floors_below")
    scalar("b_height", "building", "project.building_height")
    scalar("b_footprint", "building", "project.building_footprint")
    y = scalar("b_completion_year", "building", "project.completion_year")
    if y:
        d.item("building", "boundary.study_start_year", int(y))
    scalar("b_project_type", "building", "project.project_type")
    scalar("g_foundation", "building", "project.foundation_system")
    d.item("building", "project.assessment_date", today)
    d.item("building", "project.provenance_id", "WLC-OBSERVED")

    # ------------------------------------------------------------------ boundary
    sv = V("a_stages")
    stages = None
    if sv and sv.state in HAS_VALUE:
        stages = list(next(s for k, _, s in FL.STAGE_PRESETS if k == sv.value))
        d.item("assessment", "boundary.included_lifecycle_stages", stages)
        d.use("a_stages", sv, LABEL[sv.state], ["boundary.included_lifecycle_stages"])
    else:
        d.missing.append("評価範囲（ライフサイクル段階）")
        d.skip("a_stages", sv, "未設定：計算しない（段階が空だとエンジンは 0 を返すため）")
    scalar("a_reconstruction", "assessment", "boundary.reconstruction_scenario")
    scalar("a_replacement_cycle", "assessment", "boundary.replacement_cycle")
    scalar("a_recon_fraction", "assessment", "boundary.reconstruction_scope_fraction")
    st_set = set(stages or ())

    # ------------------------------------------------------------------ materials
    common = {k: V(k) for k in ("m_waste_rate", "m_reuse_rate", "m_repair_rate", "m_refresh_cycle", "m_transport_km",
                                "m_transport_mode", "m_quantity_basis", "a_eol_haul_km")}
    route_v = V("a_eol_route")
    route = route_v.value if route_v and route_v.state in HAS_VALUE else None
    rows = []
    missing_materials = []
    for fid, cls, label, unit, units, div, grp in FL.MATERIALS:
        v = V(fid)
        if v is None or v.state in ("not_obtained", "not_computable"):
            missing_materials.append(label)
            d.skip(fid, v, (LABEL[v.state] if v else "未取得") + "：材料の行を作っていない（この材料は合計に入っていない）")
            continue
        if v.state == "not_applicable":
            d.skip(fid, v, "適用外：この材料は無い（行を作らない）")
            continue
        whole = V("m_concrete")
        if fid == "m_concrete_fdn" and whole and whole.state in HAS_VALUE and whole.method in WHOLE_BUILDING_METHODS:
            d.skip(fid, v, "上部構造の欄に基礎を含む建物全体の統計量が入っているので、行を作らない（二重計上を防ぐ）")
            d.double_count.append("コンクリート：統計の全体量（基礎を含む）と基礎の値が両方ある。基礎の行は使っていない")
            continue
        q, qu = float(v.value), v.unit or unit
        fac = P["material"].get(cls, {})
        factor_id = fac.get(qu) or (fac.get("kg") if qu in TO_KG else None)
        if factor_id is None:
            d.unconnected.append({"label": label, "reason": "単位 %s の原単位が参照セットに無い（%s）" % (qu, "・".join(fac) or "なし")})
            d.skip(fid, v, "単位が原単位と合わない：反映外")
            continue
        if route is None:
            d.skip(fid, v, "解体後の処理シナリオが未設定：行を渡せない")
            continue
        mid = "M-%s" % fid
        states = {"quantity": _es(v)}
        row = {"material_id": mid, "construction_division": div, "material_class": cls, "specification": None,
               "quantity": q, "quantity_unit": qu, "factor_id": factor_id,
               "installation_factor_id": P["install"].get(cls), "provenance_id": "WLC-OBSERVED"}
        how = ["数量 %s %s（%s）" % (q, qu, LABEL[v.state]), "原単位 %s" % factor_id]
        for cf, col in (("m_waste_rate", "waste_rate"), ("m_reuse_rate", "reuse_rate"), ("m_repair_rate", "repair_rate"),
                        ("m_refresh_cycle", "refresh_cycle")):
            cv = common[cf]
            x, st, h = _num(cv)
            if x == "NA" and FL.FIELDS[cf]["na"] == "zero":
                row[col], states[col] = 0.0, "EXPLICIT_ZERO"
            elif x not in (None, "NA"):
                row[col], states[col] = float(x), st
            else:
                row[col] = None
        qb = common["m_quantity_basis"]
        row["quantity_basis"] = qb.value if qb and qb.state in HAS_VALUE else None
        mass_kg = q * TO_KG[qu] if qu in TO_KG else None
        # A4: tonne-km when distance, mode and mass are known; otherwise the set's per-quantity delivery factor
        dist, dst, _ = _num(common["m_transport_km"])
        mode = common["m_transport_mode"]
        if mass_kg is not None and isinstance(dist, float) and mode and mode.state in HAS_VALUE and mode.value in P["transport"]:
            row.update({"transport.mass_t": mass_kg / 1000.0, "transport.distance_km": dist, "transport.mode": mode.value,
                        "transport.factor_id": P["transport"][mode.value], "transport.delivery_factor_id": None})
            states.update({"transport.mass_t": "DERIVED", "transport.distance_km": dst})
            how.append("運搬 トンキロ（%s・%s km）" % (mode.value, dist))
        elif P["delivery"].get(cls) and _same_dim(refset["data"]["factors"][P["delivery"][cls]]["unit"], qu):
            row.update({"transport.mass_t": None, "transport.distance_km": None, "transport.mode": None,
                        "transport.factor_id": None, "transport.delivery_factor_id": P["delivery"][cls]})
            how.append("運搬 参照セットの配送原単位 %s" % P["delivery"][cls])
        else:
            row.update({"transport.mass_t": None, "transport.distance_km": None, "transport.mode": None,
                        "transport.factor_id": None, "transport.delivery_factor_id": None})
            d.unconnected.append({"label": label + "の運搬（A4）", "reason": "質量・距離・手段がそろわず、同じ単位の配送原単位も無い"})
        row["transport.load_factor"] = None
        row["end_of_life.mass_kg"] = mass_kg
        if mass_kg is not None:
            states["end_of_life.mass_kg"] = "DERIVED"
        else:
            d.unconnected.append({"label": label + "の解体時質量（C2〜C4）",
                                  "reason": "数量が %s のため質量が分からない（密度を仮定しない）。解体段階のこの行は不完全" % qu})
        hk, hst, _ = _num(common["a_eol_haul_km"])
        row["end_of_life.haul_distance_km"] = hk if isinstance(hk, float) else None
        if isinstance(hk, float):
            states["end_of_life.haul_distance_km"] = hst
        row["end_of_life.haul_factor_id"] = P["haul"]
        row["unquantified_cost_ratio"] = None
        row["states"] = states
        eol = P["eol"].get(cls, {}).get(route)
        # no "composition" key: an empty composition list counts as present and would make the row a composite
        row["@tables"] = {"end_of_life.routes": [{"route": route, "fraction": 1.0, "factor_id": eol}], "conversions": []}
        rows.append(row)
        for s in states.values():
            d.used_states.add("OBSERVED" if s == "EXPLICIT_ZERO" else s)
        d.use(fid, v, "・".join(how), ["materials[%s]" % mid])
    if rows:
        d.tables["construction"]["materials"] = rows
        if route_v and route_v.state in HAS_VALUE:
            d.use("a_eol_route", route_v, "全部の材料の行に 1 つの処理（割合 1）として渡した", ["materials[].end_of_life.routes"])
    elif any(V(f[0]) and V(f[0]).state in HAS_VALUE for f in FL.MATERIALS) and route is None:
        d.missing.append("解体後の処理シナリオ（材料の行ごとに必須）")
    for cf in ("m_waste_rate", "m_reuse_rate", "m_repair_rate", "m_refresh_cycle", "m_transport_km", "m_transport_mode",
               "m_quantity_basis", "a_eol_haul_km"):
        cv = common[cf]
        if rows and cv and (cv.state in HAS_VALUE or (cv.state == "not_applicable" and FL.FIELDS[cf]["na"] == "zero")):
            d.use(cf, cv, "材料の全部の行に共通に渡した", [FL.FIELDS[cf]["engine"][0]])
        else:
            d.skip(cf, cv, "材料の行が無い" if not rows else ((LABEL[cv.state] if cv else "未取得") + "：渡していない"))

    # ------------------------------------------------------------------ construction (site)
    scalar("c_site_electricity", "construction", "construction.electricity_kwh", "construction", "electricity_kwh")
    dv = V("c_diesel")
    if dv and dv.state in HAS_VALUE and P["fuel"].get("DIESEL"):
        d.tables["construction"]["construction.fuels"] = [{"kind": "DIESEL", "quantity": float(dv.value), "unit": "L",
                                                            "factor_id": P["fuel"]["DIESEL"], "@tables": {"conversions": []}}]
        d.state("construction", "fuels[0].quantity", _es(dv))
        d.use("c_diesel", dv, "燃料の行（軽油・原単位 %s）" % P["fuel"]["DIESEL"], ["construction.fuels"])
    elif dv and dv.state == "not_applicable":
        d.tables["construction"]["construction.fuels"] = []
        d.use("c_diesel", dv, "適用外：燃料の行なし", ["construction.fuels"])
    else:
        d.skip("c_diesel", dv, (LABEL[dv.state] if dv else "未取得") + "：渡していない")
    d.item("construction", "construction.provenance_id", "WLC-OBSERVED")

    # ------------------------------------------------------------------ equipment
    eq_rows = []
    rr = V("e_repair_rate")
    for trade, tl in FL.TRADES:
        t = trade.lower()
        cv, lv, mv = V("e_%s_count" % t), V("e_%s_life" % t), V("e_%s_mass" % t)
        x, st, how = _num(cv)
        if x == "NA":
            d.skip("e_%s_count" % t, cv, "適用外：この設備は無い（行を作らない）")
            for f in ("life", "mass"):
                d.skip("e_%s_%s" % (t, f), V("e_%s_%s" % (t, f)), "設備が適用外")
            continue
        if x is None:
            d.skip("e_%s_count" % t, cv, how + "：設備の行を作っていない（この設備は合計に入っていない）")
            for f in ("life", "mass"):
                d.skip("e_%s_%s" % (t, f), V("e_%s_%s" % (t, f)), "台数が無いので渡していない")
            continue
        ids = P["equipment"].get(trade)
        if not ids:
            d.unconnected.append({"label": tl + "機器", "reason": "参照セットに原単位が無い"})
            d.skip("e_%s_count" % t, cv, "原単位が無い：反映外")
            continue
        states = {"quantity": st}
        row = {"equipment_id": "E-" + trade, "trade": trade, "model": None, "quantity": float(x), "quantity_unit": "unit",
               "factor_id": ids["factor"], "eol_factor_id": ids["eol"], "delivery_factor_id": ids["delivery"],
               "installation_factor_id": ids["install"], "replacement_event_list": None, "provenance_id": "WLC-OBSERVED"}
        lx, lst, lhow = _num(lv)
        row["service_life"] = lx if isinstance(lx, float) else None
        if row["service_life"] is not None:
            states["service_life"] = lst
            d.use("e_%s_life" % t, lv, lhow, ["equipment[E-%s].service_life" % trade])
        else:
            d.skip("e_%s_life" % t, lv, lhow + "：交換を数えられない（B4 のこの行は不完全）")
        mx, mst, mhow = _num(mv)
        if isinstance(mx, float):
            row["end_of_life_mass_kg"] = mx * float(x)
            states["end_of_life_mass_kg"] = "DERIVED"
            d.use("e_%s_mass" % t, mv, "1 台の質量×台数", ["equipment[E-%s].end_of_life_mass_kg" % trade])
        else:
            row["end_of_life_mass_kg"] = None
            d.skip("e_%s_mass" % t, mv, mhow + "：解体時の処理（C3）のこの行は不完全")
        x2, st2, _ = _num(rr)
        if x2 == "NA":
            row["repair_rate"], states["repair_rate"] = 0.0, "EXPLICIT_ZERO"
        else:
            row["repair_rate"] = float(x2) if isinstance(x2, float) else None
            if row["repair_rate"] is not None:
                states["repair_rate"] = st2
        row["states"] = states
        for s in states.values():
            d.used_states.add("OBSERVED" if s == "EXPLICIT_ZERO" else s)
        eq_rows.append(row)
        d.use("e_%s_count" % t, cv, "%s %s 台（原単位 %s）" % (tl, x, ids["factor"]), ["equipment[E-%s]" % trade])
    if eq_rows:
        d.tables["equipment"]["equipment"] = eq_rows
        if rr and (rr.state in HAS_VALUE or rr.state == "not_applicable"):
            d.use("e_repair_rate", rr, "設備の全部の行に共通に渡した", ["equipment[].repair_rate"])
        else:
            d.skip("e_repair_rate", rr, "未取得：渡していない")
    else:
        d.skip("e_repair_rate", rr, "設備の行が無い")

    # ------------------------------------------------------------------ refrigerants
    cv = V("r_charge_kg")
    x, st, how = _num(cv)
    rparts = [k for k, F in FL.FIELDS.items() if F["role"] == "refrigerant" and k != "r_charge_kg"]
    if x == "NA":
        d.tables["equipment"]["refrigerants"] = []
        d.use("r_charge_kg", cv, "適用外：冷媒を使う機器なし", ["refrigerants"])
        for k in rparts:
            d.skip(k, V(k), "冷媒が適用外")
    elif x is None:
        d.skip("r_charge_kg", cv, how + "：冷媒の行を作っていない（B1 は合計に入っていない）")
        for k in rparts:
            d.skip(k, V(k), "充填量が無いので渡していない")
    else:
        row = {"device_id": "R-1", "substance": None, "application": "AIR_CONDITIONING", "charge_mass_kg": float(x),
               "change_years": None, "provenance_id": "WLC-OBSERVED"}
        states = {"charge_mass_kg": st}
        d.use("r_charge_kg", cv, how, ["refrigerants[R-1].charge_mass_kg"])
        for k in rparts:
            F = FL.FIELDS[k]
            kv = V(k)
            if F["part"] == "top_up":
                if kv and kv.state in HAS_VALUE:
                    row["top_up"] = kv.value == "yes"
                    d.use(k, kv, LABEL[kv.state], ["refrigerants[R-1].top_up"])
                else:
                    row["top_up"] = None
                    d.skip(k, kv, "未取得：渡していない")
                continue
            kx, kst, khow = _num(kv)
            if kx == "NA" and F["na"] == "zero":
                row[F["part"]], states[F["part"]] = 0.0, "EXPLICIT_ZERO"
                d.use(k, kv, "適用外：0 として渡した", ["refrigerants[R-1].%s" % F["part"]])
            elif isinstance(kx, float):
                row[F["part"]], states[F["part"]] = kx, kst
                d.use(k, kv, khow, ["refrigerants[R-1].%s" % F["part"]])
            else:
                row[F["part"]] = None
                d.skip(k, kv, khow + "：渡していない（B1 のこの部分は不完全）")
        row["states"] = states
        for s in states.values():
            d.used_states.add("OBSERVED" if s == "EXPLICIT_ZERO" else s)
        d.tables["equipment"]["refrigerants"] = [row]

    # ------------------------------------------------------------------ operation and water
    for fid, F in FL.FIELDS.items():
        if F["role"] != "profile":
            continue
        v = V(fid)
        x, st, how = _num(v)
        name = F["profile"]
        stage = "B7" if name.startswith("water_waste") else "B6"
        cat, owner = "operation", name.split(".")[0]
        if x == "NA":
            x, st, how = 0.0, "EXPLICIT_ZERO", "適用外：0 として渡した（明示のゼロ）"
        if x is None and F["required"] and stages is not None and stage not in st_set:
            x, st, how = 0.0, "EXPLICIT_ZERO", "%s を評価範囲から外したので、エンジンの必須の年表を 0 で満たした（合計には入らない）" % stage
        if x is None:
            if F["required"]:
                d.missing.append(F["label"])
            d.skip(fid, v, how + "：渡していない（%s のこの部分は合計に入らない）" % stage)
            continue
        d.item(cat, name + ".kind", "CONSTANT")
        d.item(cat, name + ".unit", PROFILE_UNIT[name])
        d.item(cat, name + ".base", float(x))
        d.state(owner, name.split(".", 1)[1], st)
        d.use(fid, v, how + "・年ごとに一定", [name])
    for name, fid in P["op"].items():
        d.item("operation", "operation.%s_factor_id" % name, fid)
    for name, fid in P["water"].items():
        d.item("operation", "water_waste.%s_factor_id" % ("waste" if name == "municipal_waste" else name), fid)
    scalar("o_fm_ratio", "operation", "operation.facility_management_ratio")
    scalar("o_source", "operation", "operation.energy_simulation_basis")
    gv, gc = V("o_grid_value"), V("o_grid_construction")
    gx, gst, ghow = _num(gv)
    if gx is None and stages is not None and not st_set & {"B6", "B2"}:
        gx, gst, ghow = 0.0, "EXPLICIT_ZERO", "B6・B2 を評価範囲から外したので、必須の年表を 0 で満たした（合計には入らない）"
    if gx == "NA":
        gx = None
        ghow = "適用外にはできない（電力を使わない建物でも係数の表は必須）"
    if gx is None:
        d.missing.append(FL.FIELDS["o_grid_value"]["label"])
        d.skip("o_grid_value", gv, ghow + "：渡していない")
    else:
        d.item("assessment", "operation.grid.kind", "CONSTANT")
        d.item("assessment", "operation.grid.unit", "kgCO2e/kWh")
        d.item("assessment", "operation.grid.start", float(gx))
        d.item("assessment", "operation.grid.licence_status", "PERMITTED_PUBLIC")
        d.item("assessment", "operation.grid.source_tag", "USER_INPUT")
        d.state("operation", "grid.start", gst or "DERIVED")
        d.use("o_grid_value", gv, ghow + "・評価期間中一定", ["operation.grid"])
    cx, cst, chow = _num(gc)
    if cx is None and stages is not None and "A5" not in st_set:
        cx, cst, chow = 0.0, "EXPLICIT_ZERO", "A5 を評価範囲から外したので 0 で満たした（合計には入らない）"
    if cx in (None, "NA"):
        d.missing.append(FL.FIELDS["o_grid_construction"]["label"])
        d.skip("o_grid_construction", gc, chow + "：渡していない")
    else:
        d.item("assessment", "operation.grid.construction_value", float(cx))
        d.use("o_grid_construction", gc, chow, ["operation.grid.construction_value"])
    for owner in ("operation", "water_waste", "end_of_life"):
        d.item("operation", owner + ".provenance_id", "WLC-OBSERVED")

    # ------------------------------------------------------------------ owner states and provenance records
    for owner, st in d.states.items():
        key = owner + ".states"
        cat = "building" if owner == "project" else ("construction" if owner == "construction" else "operation")
        d.item(cat, key, dict(sorted(st.items())))
    for owner in ("project", "construction", "operation", "water_waste", "end_of_life"):
        cat = "building" if owner == "project" else ("construction" if owner == "construction" else "operation")
        d.items[cat].setdefault(owner + ".states", {})
    year = int(today[:4])
    d.tables["assessment"]["provenance"] = [
        {"provenance_id": pid, "source_type": stype, "value_state": es, "source_reference": "wlcstudio://project/%s" % es.lower(),
         "licence_status": "PERMITTED_PUBLIC", "data_quality": dq, "last_verified_at": today, "measurement_year": year,
         "user_override_reason": None, "uncertainty_distribution": None}
        for es, (pid, stype, dq) in PROV_RECORDS.items()]

    # ------------------------------------------------------------------ ledger beyond the screens
    for k, why in FL.NOT_ON_SCREENS.items():
        d.unconnected.append({"label": k, "reason": "入力画面に欄が無い：" + why})
    if missing_materials and rows:
        d.assumed.append("未取得の材料 %d 種は行を作っていない：合計に入っていない（過小の可能性）" % len(missing_materials))

    doc = {"format": "lca-input/1", "data_kind": "fictional" if fp["kind"] == "fictional" else "licensed",
           "title": title[:120],
           "reference_set": {"name": fp["name"], "version": fp["version"]},
           "categories": {c: {"items": d.items[c], "tables": d.tables[c]} for c in d.items}}
    by_state = {}
    for r in d.reflect.values():
        if r["reflected"]:
            by_state[r["state"]] = by_state.get(r["state"], 0) + 1
    n_est = by_state.get("statistical", 0) + by_state.get("assumption", 0)
    n_ref = sum(by_state.values())
    report = {
        "factor_profile": {"kind": fp["kind"], "name": fp["name"], "version": fp["version"], "notes": fp["notes"]},
        "fields": sorted(d.reflect.values(), key=lambda r: list(FL.FIELDS).index(r["field"])),
        "by_state": by_state,
        "n_reflected": n_ref,
        "n_estimated": n_est,
        "missing_required": d.missing,
        "missing_materials": missing_materials,
        "unconnected": d.unconnected,
        "notes": d.assumed,
        "double_count": d.double_count,
        "stages": stages,
        "summary": ("計算に入った %d 項目のうち、統計推定・仮定が %d 項目。" % (n_ref, n_est)
                    + ("推定の割合が大きいので、合計は目安として読む。" if n_ref and n_est / n_ref > 0.3 else "")),
        "input_hash": hashlib.sha256(json.dumps(doc, sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
    }
    return doc, report


def reflection_table(report: dict) -> list[dict]:
    """Rows 「項目・状態・計算に反映されたか・どう渡したか／理由」 for the result screen and the ledger."""
    out = []
    for r in report["fields"]:
        out.append({"field": r["field"], "label": r["label"], "state": r["state"], "reflected": r["reflected"],
                    "detail": "；".join(r["how"]) if r["reflected"] else "；".join(r.get("reasons", []))})
    return out


def binding_coverage() -> dict:
    """How many of the 241 entries of the input binding (13_INPUT_CLASSIFICATION) the four screens can reach.

    An entry counts as reachable when a document built from the reproducible demo contains it (as an item id, a
    table id or a column of a table row). Entries the bridge fills by itself (factor ids, provenance) are counted
    separately from those that come from a screen field."""
    from .demo import demo_values
    from .engine import APP_BASE, Engine  # noqa: F401  (APP_BASE: path only)
    binding = json.loads((APP_BASE.parent / "13_INPUT_CLASSIFICATION" / "binding_engine_model_v1.json").read_text(encoding="utf-8"))
    refset = json.loads((APP_BASE / "samples" / "refset_fictional.json").read_text(encoding="utf-8"))
    doc, rep = build(demo_values(), refset, "coverage")
    present = set()
    for c in doc["categories"].values():
        present.update(c["items"])
        for t, rows in c["tables"].items():
            present.add(t)
            for r in rows:
                present.update(k for k in r if k != "@tables")
                for nt, nrows in (r.get("@tables") or {}).items():
                    present.add(nt)
                    for nr in nrows:
                        present.update(nr)
    ids = [e["id"] for e in binding["map"]]
    reached = [i for i in ids if i in present]
    by_cat = {}
    for e in binding["map"]:
        b = by_cat.setdefault(e["category"], {"total": 0, "reached": 0})
        b["total"] += 1
        b["reached"] += e["id"] in present
    return {"n_binding": len(ids), "n_reached": len(reached), "by_category": by_cat,
            "not_reached": [i for i in ids if i not in present],
            "note": "架空デモの入力から作った文書に現れる ID を数えた（列の ID は表の中の相対名）。"}
