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
    "MISSING": ("WLC-MISSING", "ESTIMATED", "LOW"),           # placeholder rows: the quantity is not known
}
PROFILE_UNIT = {"operation.electricity": "kWh/year", "operation.gas": "m3/year", "operation.oil": "L/year",
                "operation.district_heat": "MJ/year", "operation.onsite_generation": "kWh/year",
                "operation.onsite_export": "kWh/year", "water_waste.water": "m3/year", "water_waste.sewage": "m3/year",
                "water_waste.municipal_waste": "kg/year"}
TO_KG = {"kg": 1.0, "t": 1000.0}
# estimate methods whose concrete covers the whole building including foundations, and whose steel covers all steel
# (rebar + structural steel): RASMI kg/m2 and the MLIT area units are both whole-building, all-steel figures
WHOLE_BUILDING_METHODS = {"rasmi_mi_x_gfa", "mlit_area_unit_x_gfa"}


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
    """Engine state of a passed value. A zero is EXPLICIT_ZERO only when it is observed (confirmed / from a drawing);
    an assumed or statistical zero stays an ESTIMATE."""
    if isinstance(v.value, (int, float)) and not isinstance(v.value, bool) and v.value == 0 and v.state in ("confirmed", "from_drawing"):
        return "EXPLICIT_ZERO"
    return ENGINE_STATE[v.state]


_RANK = {"ESTIMATE": 0, "DERIVED": 1, "OBSERVED": 2, "EXPLICIT_ZERO": 2}


def _derived(*states) -> str:
    """State of a value computed from inputs: ESTIMATE if any input is an estimate, else DERIVED."""
    return "ESTIMATE" if any(s == "ESTIMATE" for s in states if s) else "DERIVED"


def _prov(state: str | None) -> str:
    """provenance_id of the record that matches a row's quantity state (MISSING for a placeholder row)."""
    return PROV_RECORDS["MISSING" if not state else ("OBSERVED" if state == "EXPLICIT_ZERO" else state)][0]


def _weakest(states) -> str:
    """The provenance record for an owner: the weakest state among the values it carries."""
    sts = [("OBSERVED" if x == "EXPLICIT_ZERO" else x) for x in states if x]
    if not sts:
        return PROV_RECORDS["MISSING"][0]
    return PROV_RECORDS[min(sts, key=lambda x: _RANK[x])][0]


def _is_whole(v, kind: str) -> bool:
    """An estimate that covers more than its field: concrete of the whole building, or all steel."""
    return v is not None and v.state in HAS_VALUE and (v.method in WHOLE_BUILDING_METHODS or getattr(v, "scope", "") == kind)


def _num(v: Value | None):
    """(number, engine_state, how) for a numeric field, or (None, None, reason)."""
    if v is None:
        return None, None, "未取得"
    if v.state in HAS_VALUE:
        return v.value, _es(v), LABEL[v.state]
    if v.state == "not_applicable":
        return "NA", None, "適用外"
    return None, None, LABEL[v.state]


def _has(v: Value | None) -> bool:
    return v is not None and v.state in HAS_VALUE


def _unknown(v: Value | None) -> bool:
    return v is None or v.state in ("not_obtained", "not_computable")


# stages that a missing input leaves incomplete directly (used for the 「下限」 flag and the stage marks); the stages that
# depend on these (B3 repair on A1-A3, B4 renewal on A/C, B5 rebuild on A/C when a rebuild is assumed) are added by
# the expansion inside build()
MATERIAL_STAGES = ("A1-A3", "A4", "C2", "C3", "C4")
EQUIPMENT_STAGES = ("A1-A3", "C3")


def expand_stages(stages, ctx: dict, kind: str | None = None) -> list:
    """The stages a gap reaches: the direct ones; B3 (repair is proportional to A1-A3); B4 (renewals repeat A and C) only
    when a renewal can fall inside the study period (ctx b4_material / b4_equipment); B5 (a rebuild repeats A and C)
    only when a rebuild or major refurbishment is assumed (ctx b5). Used by the bridge for its own record and by the
    server for the stages of the units the engine marks incomplete."""
    x = set(stages)
    if "A1-A3" in x:
        x.add("B3")
    if x & {"A1-A3", "A4", "C2", "C3", "C4"}:
        # only gaps in material or equipment rows repeat at renewals; other gaps (site fuel, profiles …) do not
        if (kind == "material" and ctx.get("b4_material")) or (kind == "equipment" and ctx.get("b4_equipment")):
            x.add("B4")
    if ctx.get("b5") and x & {"A1-A3", "A4", "A5", "C1", "C2", "C3", "C4"}:
        x.add("B5")
    return [s_ for s_ in FL.STAGES_ALL if s_ in x]


def _never(fid: str, v) -> bool:
    """not obtained, not computable, or 適用外 on a field that cannot be absent (na_never): treated as missing."""
    return v is None or v.state in ("not_obtained", "not_computable") or \
        (v.state == "not_applicable" and FL.FIELDS[fid].get("na_never"))


# ---------------------------------------------------------------------------------------------- build
def build(values: dict[str, Value], refset: dict, title: str = "WLC Studio project", today: str | None = None,
          period: float | None = None) -> tuple[dict, dict]:
    """Return (lca-input/1 document, report). `period` (optional) only decides whether a renewal can fall inside the
    study period for the completeness report; the engine always gets T separately. Raises BridgeError only for an
    unusable reference set."""
    today = today or _dt.date.today().isoformat()
    fp = factor_profile(refset)
    P = fp["profile"]
    F_ = refset["data"]["factors"]
    d = _Doc(today)
    V = values.get
    missing_inputs: list[dict] = []

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
    st_set = set(stages or ())

    ctx = {"b5": False, "b4_material": True, "b4_equipment": True, "b1_replacement": True, "b2_moot": False,
           "route_stages": ["C3", "C4"]}

    def missing(fid, stage_list, reason, kind=None, label=None, gap="omitted"):
        """Record a gap whose stages are inside the boundary. gap="omitted": not in the total (the total is a lower bound);
        gap="assumed": in the total, but computed with an assumption instead of the inputs (the stage is not determined)."""
        hit = [s for s in expand_stages(stage_list, ctx, kind) if s in st_set]
        if hit and not any(m["field"] == fid for m in missing_inputs):
            missing_inputs.append({"field": fid, "label": label or FL.FIELDS[fid]["label"], "stages": hit, "reason": reason,
                                   "gap": gap, "screen_field": fid in FL.FIELDS})

    rec = V("a_reconstruction")
    if rec is not None and rec.state == "not_applicable":
        d.item("assessment", "boundary.reconstruction_scenario", "NONE")       # 適用外 = no reconstruction
        d.use("a_reconstruction", rec, "適用外：改修・建替えなし（NONE）として渡した", ["boundary.reconstruction_scenario"])
    else:
        scalar("a_reconstruction", "assessment", "boundary.reconstruction_scenario")
    rec_active = _has(rec) and rec.value != "NONE"
    cyc_x, _, _ = _num(V("a_replacement_cycle"))
    fra_x, _, _ = _num(V("a_recon_fraction"))
    # B5 can only be affected when a refurbishment / rebuild falls inside the study period and has a non-zero share
    cyc_in = not isinstance(cyc_x, (int, float)) or period is None or cyc_x < period
    fra0 = (fra_x == "NA" and FL.FIELDS["a_recon_fraction"]["na"] == "zero") or (isinstance(fra_x, (int, float)) and fra_x == 0)
    ctx["b5"] = rec_active and cyc_in and not fra0
    if rec_active:
        # the cycle and the share are passed only when a rebuild / refurbishment is assumed: the engine computes B5 for
        # any scenario other than "NONE", so passing them with an unknown scenario would add a rebuild nobody chose
        scalar("a_replacement_cycle", "assessment", "boundary.replacement_cycle")
        scalar("a_recon_fraction", "assessment", "boundary.reconstruction_scope_fraction")
        if _never("a_replacement_cycle", V("a_replacement_cycle")) and not fra0:
            missing("a_replacement_cycle", ("B5",), "改修・建替えの周期が未取得（エンジンは周期が無いと B5 を数えないが、不完全とは示さない）")
        if _unknown(V("a_recon_fraction")) and cyc_in:
            missing("a_recon_fraction", ("B5",), "改修の範囲の割合が未取得")
    else:
        for f in ("a_replacement_cycle", "a_recon_fraction"):
            d.skip(f, V(f), "改修・建替えを想定していない（または想定が未取得）ので渡さない")
        if _unknown(rec) and cyc_in:
            missing("a_reconstruction", ("B5",), "大規模改修・建替えの想定が未取得（B5 は計算できない）")

    # ------------------------------------------------------------------ materials
    common = {k: V(k) for k in ("m_waste_rate", "m_reuse_rate", "m_repair_rate", "m_refresh_cycle", "m_transport_km",
                                "m_transport_mode", "m_quantity_basis", "a_eol_haul_km")}
    route_v = V("a_eol_route")
    route = route_v.value if route_v and route_v.state in HAS_VALUE else None
    rows = []
    missing_materials = []
    # double counting: a whole-building concrete estimate already contains the foundations, an all-steel estimate
    # (rebar and structural steel together) already contains the other steel field
    skip = {}
    covered = {}          # fields whose quantity is already inside a whole-building / all-steel figure (not missing)
    whole_c, fdn = V("m_concrete"), V("m_concrete_fdn")
    if _is_whole(whole_c, "whole_building"):
        if _has(fdn):
            skip["m_concrete_fdn"] = "上部構造の欄に基礎を含む建物全体の統計量が入っているので、基礎の行は作らない（二重計上を防ぐ）"
            d.double_count.append("コンクリート：統計の全体量（基礎を含む）と基礎の値が両方ある。基礎の行は使っていない")
        elif _unknown(fdn):
            covered["m_concrete_fdn"] = "上部構造の欄の建物全体の統計量に含まれている（行は作らない）"
    rb, stl = V("m_rebar"), V("m_steel")
    for whole, other, wname, oname in ((rb, stl, "鉄筋", "鉄骨"), (stl, rb, "鉄骨", "鉄筋")):
        ofid = "m_steel" if oname == "鉄骨" else "m_rebar"
        if _is_whole(whole, "all_steel") and ofid not in skip and ("m_rebar" if ofid == "m_steel" else "m_steel") not in skip:
            if _has(other):
                skip[ofid] = "%sの欄に鉄の全量（鉄筋＋鉄骨）の統計量が入っているので、%sの行は作らない（二重計上を防ぐ）" % (wname, oname)
                d.double_count.append("鉄：統計の鉄の全量（%sの欄）と%sの値が両方ある。%sの行は使っていない" % (wname, oname, oname))
            elif _unknown(other):
                covered[ofid] = "%sの欄の鉄の全量（鉄筋＋鉄骨）の統計量に含まれている（行は作らない）" % wname
    rc_v = common["m_refresh_cycle"]
    rcx, _, _ = _num(rc_v)
    # can a material renewal fall inside the study period? (unknown cycle: maybe; 適用外 = no renewal)
    ctx["b4_material"] = rcx is None or (isinstance(rcx, (int, float)) and (period is None or rcx < period))
    lives = []
    for trade, _ in FL.TRADES:
        cx_, _, _ = _num(V("e_%s_count" % trade.lower()))
        lx_, _, _ = _num(V("e_%s_life" % trade.lower()))
        if cx_ == "NA" or (isinstance(cx_, (int, float)) and cx_ == 0):
            continue
        lives.append(lx_)
    ctx["b4_equipment"] = any(l is None or (isinstance(l, (int, float)) and (period is None or l < period)) for l in lives)
    route_st = {"LANDFILL": ("C4",)}.get(route, ("C3",)) if route else ("C3", "C4")
    ctx["route_stages"] = list(route_st)
    mat_stages = ("A1-A3", "A4", "C2") + route_st
    wx, wst, _ = _num(common["m_waste_rate"])
    w = 0.0 if wx == "NA" and FL.FIELDS["m_waste_rate"]["na"] == "zero" else (float(wx) if isinstance(wx, (int, float)) else None)
    w_state = "EXPLICIT_ZERO" if wx == "NA" else wst
    qb = common["m_quantity_basis"]
    basis = qb.value if _has(qb) else None
    b_state = ENGINE_STATE[qb.state] if _has(qb) else None
    used_tkm = False
    fallback_rows, no_transport_rows = [], []
    for fid, cls, label, unit, units, div, grp in FL.MATERIALS:
        v = V(fid)
        if _unknown(v) and fid in covered:
            d.skip(fid, v, covered[fid])
            continue
        if _unknown(v):
            missing_materials.append(label)
            missing(fid, mat_stages, "材料の数量が未取得：この材料は合計に入っていない", kind="material")
            d.skip(fid, v, (LABEL[v.state] if v else "未取得") + "：材料の行を作っていない（この材料は合計に入っていない）")
            continue
        if v.state == "not_applicable":
            d.skip(fid, v, "適用外：この材料は無い（行を作らない）")
            continue
        if fid in skip:
            d.skip(fid, v, skip[fid])
            continue
        q, qu = float(v.value), v.unit or unit
        fac = P["material"].get(cls, {})
        factor_id = fac.get(qu) or (fac.get("kg") if qu in TO_KG else None)
        if factor_id is None:
            d.unconnected.append({"label": label, "reason": "単位 %s の原単位が参照セットに無い（%s）" % (qu, "・".join(fac) or "なし")})
            missing(fid, mat_stages, "数量の単位 %s の原単位が無いので計算に入っていない" % qu, kind="material")
            d.skip(fid, v, "単位が原単位と合わない：反映外")
            continue
        if route is None:
            d.skip(fid, v, "解体後の処理シナリオが未設定：行を渡せない")
            continue
        mid = "M-%s" % fid
        qst = _es(v)
        states = {"quantity": qst}
        inst = P["install"].get(cls)
        if inst and not _same_dim(F_[inst]["unit"], qu):
            d.unconnected.append({"label": label + "の更新時の施工（B4）",
                                  "reason": "施工の原単位の単位 %s と数量の単位 %s が合わないので数えない" % (F_[inst]["unit"], qu)})
            rc, _, _ = _num(common["m_refresh_cycle"])
            if isinstance(rc, (int, float)) and (period is None or rc < period):     # a renewal can fall inside T
                missing(fid, ("B4",), "更新時の施工の原単位の単位が数量と合わない（更新のときの施工の分が入っていない）", kind="material")
            inst = None
        row = {"material_id": mid, "construction_division": div, "material_class": cls, "specification": None,
               "quantity": q, "quantity_unit": qu, "factor_id": factor_id,
               "installation_factor_id": inst, "provenance_id": _prov(qst)}
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
        row["quantity_basis"] = basis
        # masses as the engine reads them (A13-05): DESIGN: ordered = Q/(1-w), installed = Q; otherwise ordered = Q,
        # installed = Q(1-w). Delivery carries the ordered mass, end of life the installed mass.
        kg = TO_KG.get(qu)
        if kg is None:
            ordered_kg = installed_kg = None
        elif basis == "DESIGN":
            installed_kg = q * kg
            ordered_kg = q * kg / (1.0 - w) if w is not None and w < 1 else None
        else:
            ordered_kg = q * kg
            installed_kg = q * kg * (1.0 - w) if w is not None else None
        dist, dst, _ = _num(common["m_transport_km"])
        mode = common["m_transport_mode"]
        wb = (w_state, b_state) if (w is None or w > 0) else ()     # the basis matters only with offcuts
        if ordered_kg is not None and isinstance(dist, float) and _has(mode) and mode.value in P["transport"]:
            row.update({"transport.mass_t": ordered_kg / 1000.0, "transport.distance_km": dist, "transport.mode": mode.value,
                        "transport.factor_id": P["transport"][mode.value], "transport.delivery_factor_id": None})
            states.update({"transport.mass_t": _derived(qst, *(wb if basis == "DESIGN" else (b_state,))), "transport.distance_km": dst})
            how.append("運搬 トンキロ（%s・%s km）" % (mode.value, dist))
            used_tkm = True
        elif P["delivery"].get(cls) and _same_dim(F_[P["delivery"][cls]]["unit"], qu):
            row.update({"transport.mass_t": None, "transport.distance_km": None, "transport.mode": None,
                        "transport.factor_id": None, "transport.delivery_factor_id": P["delivery"][cls]})
            how.append("運搬 参照セットの配送原単位 %s（数量あたり。距離・手段の入力ではない）" % P["delivery"][cls])
            fallback_rows.append(label)
        else:
            row.update({"transport.mass_t": None, "transport.distance_km": None, "transport.mode": None,
                        "transport.factor_id": None, "transport.delivery_factor_id": None})
            if kg is not None and ordered_kg is None:
                why, cause = "廃棄率が未取得で発注量（運搬する質量）が決まらず、同じ単位の配送原単位も無い", "waste"
            elif kg is None:
                why, cause = "数量が %s で質量が分からず（密度を仮定しない）、同じ単位の配送原単位も無い" % qu, "unit"
            else:
                why, cause = "運搬距離・手段がそろわず、同じ単位の配送原単位も無い", "inputs"
            d.unconnected.append({"label": label + "の運搬（A4）", "reason": why})
            no_transport_rows.append((label, cause))
        row["transport.load_factor"] = None
        row["end_of_life.mass_kg"] = installed_kg
        if installed_kg is not None:
            states["end_of_life.mass_kg"] = _derived(qst, *(wb if basis != "DESIGN" else (b_state,)))
        else:
            d.unconnected.append({"label": label + "の解体時質量（C2〜C4）",
                                  "reason": (("数量が %s のため質量が分からない（密度を仮定しない）" % qu) if kg is None
                                             else "廃棄率が未取得で、施工後の質量が決まらない") + "。解体段階のこの行は不完全"})
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
        if _never("m_quantity_basis", qb) and (w is None or w > 0):
            missing("m_quantity_basis", mat_stages, "数量の基準（設計・発注・竣工）が%s：廃棄分の扱いが決まらない"
                    % (LABEL[qb.state] if qb else "未取得"), kind="material")
        w_stages = ("A1-A3",) + (("A4",) if basis == "DESIGN" else ("C2",) + route_st)
        for cf, stg, why in (("m_waste_rate", w_stages, "施工時の廃棄率が未取得（発注量・施工後の質量が決まらない）"),
                             ("m_repair_rate", ("B3",), "修繕率が未取得"),
                             ("m_refresh_cycle", ("B4", "B3"), "更新周期が未取得（エンジンは周期が無いと更新を数えないが、不完全とは示さない）"),
                             ("a_eol_haul_km", ("C2",), "解体材の運搬距離が未取得")):
            if _never(cf, common[cf]):
                missing(cf, stg, why, kind="material")
        if fallback_rows:
            # the per-quantity delivery factor of the reference set replaces distance × mode × mass: an assumption, so A4
            # (and what repeats it) is marked as not determined from the inputs
            d.assumed.append("運搬（A4）は %d 行（%s）で参照セットの配送原単位（数量あたり）を使った：運搬距離・手段の入力によるものではない（仮定）"
                             % (len(fallback_rows), "、".join(fallback_rows[:6])))
            missing("a4_delivery_fallback", ("A4",), "%d 行（%s）は運搬距離・手段ではなく、参照セットの数量あたりの配送原単位で計算した（仮定）"
                    % (len(fallback_rows), "、".join(fallback_rows[:6])), kind="material", label="運搬（A4）の代わりの原単位",
                    gap="assumed")
        by_cause = {}
        for lab, cause in no_transport_rows:
            by_cause.setdefault(cause, []).append(lab)
        if by_cause.get("inputs"):
            tf = "m_transport_km" if _never("m_transport_km", common["m_transport_km"]) else "m_transport_mode"
            missing(tf, ("A4",), "運搬を計算できない行がある（%s）" % "、".join(by_cause["inputs"][:6]), kind="material")
        if by_cause.get("unit"):
            missing("a4_no_mass", ("A4",), "数量が体積・面積で質量が分からず、同じ単位の配送原単位も無いので運搬を計算できない（%s）"
                    % "、".join(by_cause["unit"][:6]), kind="material", label="運搬（A4）：質量の分からない材料")
        # the "waste" cause is already covered by the waste-rate entry (its stages include A4)
    elif any(_has(V(f[0])) for f in FL.MATERIALS) and route is None:
        d.missing.append("解体後の処理シナリオ（材料の行ごとに必須）")
    for cf in ("m_waste_rate", "m_reuse_rate", "m_repair_rate", "m_refresh_cycle", "m_transport_km", "m_transport_mode",
               "m_quantity_basis", "a_eol_haul_km"):
        cv = common[cf]
        if cf in ("m_transport_km", "m_transport_mode") and rows and not used_tkm:
            d.skip(cf, cv, "トンキロで計算した行が無い（配送原単位を使ったか、質量・手段がそろわない）")
            continue
        if cf == "m_refresh_cycle" and rows and cv and cv.state == "not_applicable":
            d.use(cf, cv, "適用外：更新しない（材料の更新は数えない）", ["materials[].refresh_cycle"])
            continue
        if rows and cv and (cv.state in HAS_VALUE or (cv.state == "not_applicable" and FL.FIELDS[cf]["na"] == "zero")):
            d.use(cf, cv, "材料の全部の行に共通に渡した", [FL.FIELDS[cf]["engine"][0]])
        else:
            d.skip(cf, cv, "材料の行が無い" if not rows else ((LABEL[cv.state] if cv else "未取得") + "：渡していない"))

    # ------------------------------------------------------------------ construction (site)
    scalar("c_site_electricity", "construction", "construction.electricity_kwh", "construction", "electricity_kwh")
    if _unknown(V("c_site_electricity")):
        missing("c_site_electricity", ("A5",), "工事中の電力が未取得")
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
        # not obtained: a row with a MISSING quantity, so that the engine itself marks A5-02 incomplete
        if P["fuel"].get("DIESEL"):
            d.tables["construction"]["construction.fuels"] = [{"kind": "DIESEL", "quantity": None, "unit": "L",
                                                                "factor_id": P["fuel"]["DIESEL"], "@tables": {"conversions": []}}]
        missing("c_diesel", ("A5",), "工事中の軽油が未取得")
        d.skip("c_diesel", dv, (LABEL[dv.state] if dv else "未取得") + "：量の欠けた燃料の行を渡した（エンジンが A5 を不完全とする）")
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
        ids = P["equipment"].get(trade)
        if not ids:
            d.unconnected.append({"label": tl + "機器", "reason": "参照セットに原単位が無い"})
            d.skip("e_%s_count" % t, cv, "原単位が無い：反映外")
            missing("e_%s_count" % t, EQUIPMENT_STAGES, "%s機器の原単位が参照セットに無いので計算に入っていない" % tl, kind="equipment")
            continue
        if x is None:
            # not obtained: a row with a MISSING count, so that the engine marks X-01 / X-14 / B4-02 incomplete
            eq_rows.append({"equipment_id": "E-" + trade, "trade": trade, "model": None, "quantity": None, "quantity_unit": "unit",
                            "factor_id": ids["factor"], "eol_factor_id": ids["eol"], "delivery_factor_id": ids["delivery"],
                            "installation_factor_id": ids["install"], "replacement_event_list": None, "service_life": None,
                            "end_of_life_mass_kg": None, "repair_rate": None, "provenance_id": _prov(None), "states": {}})
            missing("e_%s_count" % t, EQUIPMENT_STAGES, "%s機器の台数が未取得（本当に無いと分かっているときだけ「適用外」）" % tl, kind="equipment")
            d.skip("e_%s_count" % t, cv, how + "：台数の欠けた設備の行を渡した（エンジンが不完全とする。この設備は合計に入っていない）")
            for f in ("life", "mass"):
                d.skip("e_%s_%s" % (t, f), V("e_%s_%s" % (t, f)), "台数が無いので渡していない")
            continue
        states = {"quantity": st}
        zero = float(x) == 0.0                       # a confirmed zero count: lives, masses and repair do not matter
        if zero:
            # no row at all: a row with count 0 and missing companions would make the engine flag units that cannot change
            d.use("e_%s_count" % t, cv, "台数 0：この設備の行は作らない", ["equipment"])
            for f in ("life", "mass"):
                d.skip("e_%s_%s" % (t, f), V("e_%s_%s" % (t, f)), "台数が 0 なので使われない")
            continue
        row = {"equipment_id": "E-" + trade, "trade": trade, "model": None, "quantity": float(x), "quantity_unit": "unit",
               "factor_id": ids["factor"], "eol_factor_id": ids["eol"], "delivery_factor_id": ids["delivery"],
               "installation_factor_id": ids["install"], "replacement_event_list": None, "provenance_id": _prov(st)}
        lx, lst, lhow = _num(lv)
        row["service_life"] = lx if isinstance(lx, float) else None
        if row["service_life"] is not None:
            states["service_life"] = lst
            d.use("e_%s_life" % t, lv, lhow, ["equipment[E-%s].service_life" % trade])
        elif lx == "NA":
            d.use("e_%s_life" % t, lv, "適用外：交換しない（交換は数えない）", ["equipment[E-%s].service_life" % trade])
        elif not zero:
            missing("e_%s_life" % t, ("B4", "B3"), "%s機器の耐用年数が未取得（エンジンは交換を数えないが、不完全とは示さない）" % tl,
                    kind="equipment")
            d.skip("e_%s_life" % t, lv, lhow + "：交換を数えられない（B4 のこの行は不完全）")
        else:
            d.skip("e_%s_life" % t, lv, "台数が 0 なので使われない")
        mx, mst, mhow = _num(mv)
        if isinstance(mx, float):
            row["end_of_life_mass_kg"] = mx * float(x)
            states["end_of_life_mass_kg"] = _derived(st, mst)
            d.use("e_%s_mass" % t, mv, "1 台の質量×台数", ["equipment[E-%s].end_of_life_mass_kg" % trade])
        else:
            row["end_of_life_mass_kg"] = None
            if not zero:
                missing("e_%s_mass" % t, ("C3",), "%s機器 1 台の解体時質量が%s" % (tl, LABEL[mv.state] if mv else "未取得"), kind="equipment")
            d.skip("e_%s_mass" % t, mv, mhow + ("：解体時の処理（C3）のこの行は不完全" if not zero else "：台数が 0 なので使われない"))
        x2, st2, _ = _num(rr)
        if x2 == "NA":
            row["repair_rate"], states["repair_rate"] = 0.0, "EXPLICIT_ZERO"
        else:
            row["repair_rate"] = float(x2) if isinstance(x2, float) else None
            if row["repair_rate"] is not None:
                states["repair_rate"] = st2
            elif not zero:
                missing("e_repair_rate", ("B3",), "設備の修繕率が未取得")
        row["states"] = states
        for s in states.values():
            d.used_states.add("OBSERVED" if s == "EXPLICIT_ZERO" else s)
        eq_rows.append(row)
        d.use("e_%s_count" % t, cv, "%s %s 台（原単位 %s）" % (tl, x, ids["factor"]), ["equipment[E-%s]" % trade])
    if eq_rows:
        d.tables["equipment"]["equipment"] = eq_rows
        if rr and (rr.state in HAS_VALUE or rr.state == "not_applicable") and any(r["quantity"] is not None for r in eq_rows):
            d.use("e_repair_rate", rr, "設備の全部の行に共通に渡した", ["equipment[].repair_rate"])
        else:
            d.skip("e_repair_rate", rr, "未取得：渡していない" if not (rr and rr.state in HAS_VALUE) else "台数のある設備の行が無い")
    else:
        d.skip("e_repair_rate", rr, "設備の行が無い")

    # ------------------------------------------------------------------ refrigerants
    cv = V("r_charge_kg")
    x, st, how = _num(cv)
    rparts = [k for k, F in FL.FIELDS.items() if F["role"] == "refrigerant" and k != "r_charge_kg"]
    if x == "NA" or (isinstance(x, (int, float)) and float(x) == 0.0):
        d.tables["equipment"]["refrigerants"] = []
        d.use("r_charge_kg", cv, "適用外：冷媒を使う機器なし" if x == "NA" else "充填量 0：冷媒の行は作らない", ["refrigerants"])
        for k in rparts:
            d.skip(k, V(k), "冷媒が無い（適用外・充填量 0）ので使われない")
    else:
        row = {"device_id": "R-1", "substance": None, "application": "AIR_CONDITIONING",
               "charge_mass_kg": float(x) if x is not None else None, "change_years": None,
               "provenance_id": _prov(st)}
        rzero = x is not None and float(x) == 0.0            # a confirmed zero charge: nothing leaks
        rl_x, _, _ = _num(V("r_life"))
        # a replacement (and its loss) happens inside T only with a known life shorter than T, or an unknown life
        ctx["b1_replacement"] = rl_x is None or (isinstance(rl_x, (int, float)) and (period is None or rl_x < period))
        states = {"charge_mass_kg": st} if st else {}
        if x is None:
            missing("r_charge_kg", ("B1",), "冷媒の充填量が未取得（冷媒を使わないと分かっているときだけ「適用外」）")
            d.skip("r_charge_kg", cv, how + "：充填量の欠けた冷媒の行を渡した（エンジンが B1 を不完全とする）")
        else:
            d.use("r_charge_kg", cv, how, ["refrigerants[R-1].charge_mass_kg"])
        for k in rparts:
            F = FL.FIELDS[k]
            kv = V(k)
            if F["part"] == "top_up":
                if kv and kv.state in HAS_VALUE:
                    row["top_up"] = kv.value == "yes"
                    if x is not None:
                        d.use(k, kv, LABEL[kv.state], ["refrigerants[R-1].top_up"])
                    else:
                        d.skip(k, kv, "充填量が無いので使われない")
                elif kv and kv.state == "not_applicable":
                    row["top_up"] = False            # 適用外 = no top-up happens
                    if x is not None:
                        d.use(k, kv, "適用外：補充しないとして渡した", ["refrigerants[R-1].top_up"])
                    else:
                        d.skip(k, kv, "適用外（補充しない）。ただし充填量が無いので使われない")
                elif rzero:
                    row["top_up"] = None
                    d.skip(k, kv, "充填量が 0 なので使われない")
                else:
                    # a missing top_up would silently change B1 by a large factor: do not compute B1 at all
                    row["top_up"] = None
                    if row["charge_mass_kg"] is not None:
                        row["charge_mass_kg"] = None
                        states.pop("charge_mass_kg", None)
                        d.reflect["r_charge_kg"]["reflected"] = False
                        d.reflect["r_charge_kg"].setdefault("reasons", []).append("漏えい分の補充の有無が未取得なので、充填量を渡していない")
                    missing("r_top_up", ("B1",), "漏えい分の補充の有無が%s（B1 を大きく変えるので、決まるまで B1 は計算しない）"
                            % (LABEL[kv.state] if kv else "未取得"))
                    d.skip(k, kv, "%s：B1 は計算していない（エンジンが不完全とする）" % (LABEL[kv.state] if kv else "未取得"))
                continue
            kx, kst, khow = _num(kv)
            if kx == "NA" and F["na"] == "zero":
                row[F["part"]], states[F["part"]] = 0.0, "EXPLICIT_ZERO"
                d.use(k, kv, "適用外：0 として渡した", ["refrigerants[R-1].%s" % F["part"]])
            elif kx == "NA" and F.get("na_note") and not F.get("na_never"):
                row[F["part"]] = None
                d.use(k, kv, "適用外：%s" % F["na_note"], ["refrigerants[R-1].%s" % F["part"]])
            elif isinstance(kx, float):
                row[F["part"]], states[F["part"]] = kx, kst
                d.use(k, kv, khow, ["refrigerants[R-1].%s" % F["part"]])
            else:
                row[F["part"]] = None
                if x is not None and not rzero and not (k == "r_loss_rate" and not ctx["b1_replacement"]):
                    missing(k, ("B1",), "%sが%s" % (F["label"], "適用外（0 にできない項目）" if kx == "NA" else khow))
                d.skip(k, kv, ("適用外（0 にできない項目）" if kx == "NA" else khow) + "：渡していない（B1 のこの部分は不完全）")
        if row["charge_mass_kg"] is None:
            # B1 is not computed at all: none of the refrigerant inputs reaches a result
            for k in rparts:
                r_ = d.reflect.get(k)
                if r_ and r_["reflected"]:
                    r_["reflected"] = False
                    r_["how"] = []
                    r_.setdefault("reasons", []).append("充填量を渡していないので B1 は計算していない（使われない）")
        row["states"] = states
        for s in states.values():
            d.used_states.add("OBSERVED" if s == "EXPLICIT_ZERO" else s)
        d.tables["equipment"]["refrigerants"] = [row]

    # ------------------------------------------------------------------ operation and water
    # The engine reads operation.electricity as CONSUMPTION and nets it: purchase = max(0, c − (generation − export)).
    # The screen asks for PURCHASED electricity (the bills already exclude self-consumed generation), so the
    # consumption passed is purchase + self-consumption, max(0, g − x); otherwise self-consumed PV is subtracted twice.
    pe, pe_st, _ = _num(V("o_elec_kwh"))
    g_, g_st, _ = _num(V("o_pv_kwh"))
    x_, x_st, _ = _num(V("o_export_kwh"))
    g0 = 0.0 if g_ == "NA" else g_
    x0 = 0.0 if x_ == "NA" else x_
    elec_override = None
    if isinstance(g0, (int, float)) and isinstance(x0, (int, float)) and x0 > g0:
        if stages is None or st_set & {"B6", "B2"}:
            d.missing.append("自家発電のうち外へ売った電力（%s kWh/年）が自家発電（%s kWh/年）より多い（入力の見直しが要る）"
                             % (x0, g0))
    elif isinstance(pe, (int, float)) and isinstance(g0, (int, float)) and isinstance(x0, (int, float)):
        selfc = max(0.0, g0 - x0)
        elec_override = (float(pe) + selfc, _derived(pe_st, g_st, x_st) if selfc > 0 else pe_st,
                         "購入電力 %s ＋ 自家消費 %s ＝ 電力の使用量 %s kWh/年として渡した" % (pe, selfc, float(pe) + selfc))
    # net purchased electricity provably 0 → the grid factor and the facility-management share cannot act
    pe0 = pe == "NA" or (isinstance(pe, (int, float)) and pe == 0)
    ctx["b2_moot"] = bool(pe0 and isinstance(g0, (int, float)) and isinstance(x0, (int, float)) and g0 >= x0)
    for fid, F in FL.FIELDS.items():
        if F["role"] != "profile":
            continue
        v = V(fid)
        x, st, how = _num(v)
        if fid == "o_elec_kwh" and elec_override is not None and x not in (None, "NA"):
            x, st, how = elec_override
        name = F["profile"]
        stage = "B7" if name.startswith("water_waste") else "B6"
        cat, owner = "operation", name.split(".")[0]
        if x == "NA":
            x, st, how = 0.0, "EXPLICIT_ZERO", "適用外：0 として渡した（明示のゼロ）"
        filled = False
        if x is None and F["required"] and stages is not None and stage not in st_set:
            x, st, how = 0.0, "EXPLICIT_ZERO", "%s を評価範囲から外したので、エンジンの必須の年表を 0 で満たした（計算には入らない）" % stage
            filled = True
        if x is None:
            if F["required"]:
                d.missing.append(F["label"])
            else:
                missing(fid, (stage,) + (("B2",) if fid in ("o_elec_kwh", "o_pv_kwh", "o_export_kwh") else ()),
                        "%sが未取得（本当に無いと分かっているときだけ「適用外」）" % F["label"])
            d.skip(fid, v, how + "：渡していない（%s のこの部分は合計に入らない）" % stage)
            continue
        d.item(cat, name + ".kind", "CONSTANT")
        d.item(cat, name + ".unit", PROFILE_UNIT[name])
        d.item(cat, name + ".base", float(x))
        d.state(owner, name.split(".", 1)[1], st)
        if filled:
            d.skip(fid, v, how)
        else:
            d.use(fid, v, how + "・年ごとに一定", [name])
    for name, fid in P["op"].items():
        d.item("operation", "operation.%s_factor_id" % name, fid)
    for name, fid in P["water"].items():
        d.item("operation", "water_waste.%s_factor_id" % ("waste" if name == "municipal_waste" else name), fid)
    scalar("o_fm_ratio", "operation", "operation.facility_management_ratio")
    if _unknown(V("o_fm_ratio")) and not ctx["b2_moot"]:
        missing("o_fm_ratio", ("B2", "B6"), "施設管理（B2）分の割合が未取得（B6 から差し引く分も決まらない）")
    scalar("o_source", "operation", "operation.energy_simulation_basis")
    gv, gc = V("o_grid_value"), V("o_grid_construction")
    gx, gst, ghow = _num(gv)
    g_filled = False
    if gx in (None, "NA") and stages is not None and not st_set & {"B6", "B2"}:
        gx, gst, ghow = 0.0, "EXPLICIT_ZERO", "B6・B2 を評価範囲から外したので、必須の年表を 0 で満たした（計算には入らない）"
        g_filled = True
    elif gx in (None, "NA") and ctx["b2_moot"]:
        gx, gst, ghow = 0.0, "EXPLICIT_ZERO", "購入電力が 0 なので係数は効かない：必須の年表を 0 で満たした（計算には入らない）"
        g_filled = True
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
        if g_filled:
            d.skip("o_grid_value", gv, ghow)
        else:
            d.use("o_grid_value", gv, ghow + "・評価期間中一定", ["operation.grid"])
    cx, cst, chow = _num(gc)
    c_filled = False
    se, _, _ = _num(V("c_site_electricity"))
    if cx in (None, "NA") and stages is not None and "A5" not in st_set:
        cx, cst, chow = 0.0, "EXPLICIT_ZERO", "A5 を評価範囲から外したので 0 で満たした（計算には入らない）"
        c_filled = True
    elif cx in (None, "NA") and (se == "NA" or (isinstance(se, (int, float)) and se == 0)):
        cx, cst, chow = 0.0, "EXPLICIT_ZERO", "工事中の電力が 0 なので係数は効かない：0 で満たした（計算には入らない）"
        c_filled = True
    if cx in (None, "NA"):
        d.missing.append(FL.FIELDS["o_grid_construction"]["label"])
        d.skip("o_grid_construction", gc, chow + "：渡していない")
    else:
        d.item("assessment", "operation.grid.construction_value", float(cx))
        if c_filled:
            d.skip("o_grid_construction", gc, chow)
        else:
            d.use("o_grid_construction", gc, chow, ["operation.grid.construction_value"])
    for owner in ("operation", "water_waste", "end_of_life"):
        d.item("operation", owner + ".provenance_id", "WLC-OBSERVED")

    # ------------------------------------------------------------------ owner states and provenance records
    for owner, st in d.states.items():
        key = owner + ".states"
        cat = "building" if owner == "project" else ("construction" if owner == "construction" else "operation")
        d.item(cat, key, dict(sorted(st.items())))
    for owner in ("project", "construction", "operation", "water_waste", "end_of_life"):
        # the owner's default record is the weakest evidence among its values (every passed value also has its own state)
        cat = "building" if owner == "project" else ("construction" if owner == "construction" else "operation")
        d.item(cat, owner + ".provenance_id", _weakest(d.states.get(owner, {}).values()))
    for owner in ("project", "construction", "operation", "water_waste", "end_of_life"):
        cat = "building" if owner == "project" else ("construction" if owner == "construction" else "operation")
        d.items[cat].setdefault(owner + ".states", {})
    # The records describe the kind of evidence; the verification date and measurement year are not known for the
    # whole class of values, so they are left unknown instead of stamping today's date.
    d.tables["assessment"]["provenance"] = [
        {"provenance_id": pid, "source_type": stype, "value_state": es, "source_reference": "wlcstudio://project/%s" % es.lower(),
         "licence_status": "PERMITTED_PUBLIC", "data_quality": dq, "last_verified_at": None, "measurement_year": None,
         "user_override_reason": None, "uncertainty_distribution": None}
        for es, (pid, stype, dq) in PROV_RECORDS.items()]

    # ------------------------------------------------------------------ stages that no screen can fill
    # (through the same expansion, so that a rebuild that repeats C1 and A5 is marked as well)
    missing("end_of_life.demolition_activities", ("C1",), "解体工事の作業量の入力欄がまだ無いので、C1 は合計に入っていない",
            label="解体工事（C1）")
    missing("construction.waste_streams", ("A5",), "現場の廃棄物の内訳の入力欄がまだ無いので、A5 のその分は合計に入っていない",
            label="現場の廃棄物（A5 の一部）")
    # estimates computed for other building data (floor area, use, structure) than the data now sent to the engine
    stale_estimates = []
    for fid, v in values.items():
        dep = getattr(v, "depends", None) or {}
        if not dep or v.state not in HAS_VALUE:
            continue
        diffs = []
        for k, was in dep.items():
            if k == "b_use_group":                    # only what the estimator used: residential or not
                cu = V("b_use")
                now = (("residential" if cu.value == "residential" else "non_residential") if cu is not None and cu.state in HAS_VALUE else None)
                if now != was:
                    diffs.append("用途の区分 %s → %s" % (was, now if now is not None else "未取得"))
                continue
            cur = V(k)
            now = cur.value if cur is not None and cur.state in HAS_VALUE else None
            if now != was and not (isinstance(now, (int, float)) and isinstance(was, (int, float)) and abs(now - was) <= 1e-9 * max(1, abs(was))):
                diffs.append("%s %s → %s" % (FL.FIELDS[k]["label"], was, now if now is not None else "未取得"))
        if diffs:
            stale_estimates.append({"field": fid, "label": FL.FIELDS[fid]["label"], "changes": diffs})
            d.assumed.append("「%s」の推定は前提が変わっている（%s）：概算し直す" % (FL.FIELDS[fid]["label"], "、".join(diffs)))

    # ------------------------------------------------------------------ ledger beyond the screens
    for k, why in FL.NOT_ON_SCREENS.items():
        d.unconnected.append({"label": k, "reason": "入力画面に欄が無い：" + why})
    if missing_materials:
        d.assumed.append("未取得の材料 %d 種は行を作っていない：合計に入っていない（合計は少なめ＝下限）" % len(missing_materials))
    other = [m for m in missing_inputs if m["field"] not in {f[0] for f in FL.MATERIALS} and m.get("gap") == "omitted"]
    if other:
        d.assumed.append("入っていない入力 %d 件（%s）の分は合計に入っていない（合計は少なめ＝下限）"
                         % (len(other), "、".join(m["label"] for m in other[:6]) + ("…" if len(other) > 6 else "")))

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
    omitted = [m for m in missing_inputs if m.get("gap") == "omitted"]
    # stages with something left out (the total is short there) and stages computed partly with an assumption
    incomplete_stages = sorted({s for m in omitted for s in m["stages"]})
    assumed_stages = sorted({s for m in missing_inputs if m.get("gap") == "assumed" for s in m["stages"]})
    report = {
        "factor_profile": {"kind": fp["kind"], "name": fp["name"], "version": fp["version"], "notes": fp["notes"]},
        "fields": sorted(d.reflect.values(), key=lambda r: list(FL.FIELDS).index(r["field"])),
        "by_state": by_state,
        "n_reflected": n_ref,
        "n_estimated": n_est,
        "missing_required": d.missing,
        "missing_materials": missing_materials,
        "missing_inputs": missing_inputs,
        "omitted_inputs": omitted,
        "stale_estimates": stale_estimates,
        "expand": dict(ctx),
        "incomplete_stages": incomplete_stages,
        "assumed_stages": assumed_stages,
        "unconnected": d.unconnected,
        "notes": d.assumed,
        "double_count": d.double_count,
        "stages": stages,
        "summary": ("計算に入った %d 項目のうち、統計推定・仮定が %d 項目。" % (n_ref, n_est)
                    + ("推定の割合が大きいので、合計は目安として読む。" if n_ref and n_est / n_ref > 0.3 else "")),
        "input_hash": input_hash(doc, values),
    }
    return doc, report


def input_hash(doc: dict, values: dict | None = None) -> str:
    """Fingerprint of the inputs: the engine document without the assessment date (today's date would make every result
    look stale the next day), plus the state, value, unit and scope of every field (a change from 適用外 to 未取得 can
    leave the document identical and still change what is missing)."""
    d = json.loads(json.dumps(doc))
    for c in d["categories"].values():
        c["items"].pop("project.assessment_date", None)
    fields = sorted((k, v.state, json.dumps(v.value, ensure_ascii=False, default=str), v.unit, getattr(v, "scope", ""))
                    for k, v in (values or {}).items())
    return hashlib.sha256(json.dumps([d, fields], sort_keys=True, ensure_ascii=False).encode()).hexdigest()


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
    vals = demo_values()
    vals["a_reconstruction"] = Value("a_reconstruction", "assumption", "MAJOR_REFURBISHMENT", method="coverage_probe")
    for fid, F in FL.FIELDS.items():            # every field the screens offer, filled once, so that coverage counts
        v = vals.get(fid)                       # what the screens CAN reach (the values themselves do not matter)
        if v is not None and v.state in HAS_VALUE:
            continue
        if F["type"] == "enum":
            x = F["enum"][0][0]
        elif F["type"] == "text":
            x = "x"
        else:
            lo, hi = F.get("range", (1, 1))
            x = float(min(max(lo, 1), hi)) if F["type"] == "number" else int(min(max(lo, 1), hi))
        unit = F.get("unit", "") if F["type"] in ("number", "integer") else ""
        vals[fid] = Value(fid, "assumption", x, unit, method="coverage_probe")
    doc, rep = build(vals, refset, "coverage")
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
    entries = list(binding["map"].values()) if isinstance(binding["map"], dict) else list(binding["map"])
    ids = [e["id"] for e in entries]
    reached = [i for i in ids if i in present]
    by_cat = {}
    for e in entries:
        b = by_cat.setdefault(e["category"], {"total": 0, "reached": 0})
        b["total"] += 1
        b["reached"] += e["id"] in present
    return {"n_binding": len(ids), "n_reached": len(reached), "by_category": by_cat,
            "not_reached": [i for i in ids if i not in present],
            "note": "4 画面の全項目に値がある場合に作られる文書に現れる ID を数えた（列の ID は表の中の相対名）。"}


def ledger_markdown() -> str:
    """docs/unconnected_inputs.md: the screen fields and the engine inputs that do not reach the calculation, with reasons."""
    cov = binding_coverage()
    lines = ["# 計算に反映されない入力の一覧（未接続台帳）", "",
             "生成：`python3 -B -m wlcstudio ledger --md docs/unconnected_inputs.md`。プロジェクトごとの反映の有無は、"
             "結果の画面と `GET /api/projects/{id}/ledger` に出る（未取得・適用外・記録のみの理由つき）。", "",
             "## 1. 入力分類（13_INPUT_CLASSIFICATION の結び付け 241 項目）のうち、4 画面から届くもの", "",
             "4 画面の全項目に値があるときに作られる文書に現れる ID：**%d / %d**。" % (cov["n_reached"], cov["n_binding"]), "",
             "| 大分類 | 届く | 全体 |", "|---|---:|---:|"]
    for k, b in cov["by_category"].items():
        lines.append("| %s | %d | %d |" % (k, b["reached"], b["total"]))
    lines += ["", "届かない ID（画面に欄が無い、またはアプリが既定で書かないもの）：", "",
              ", ".join("`%s`" % i for i in cov["not_reached"]), "",
              "（この 241 項目は、詳細分類 175 のうち 77 に結び付いている。残りの 98 の詳細分類はエンジンの入力が無い：12_APP_BASE の README と 13 の README を参照）", "",
              "## 2. 入力画面に欄が無いエンジンの入力（理由つき）", "", "| エンジンの入力 | 理由 |", "|---|---|"]
    for k, why in FL.NOT_ON_SCREENS.items():
        lines.append("| `%s` | %s |" % (k, why))
    lines += ["", "## 3. 画面にあるが計算には使わない項目（記録のみ）", "", "| 項目 | 理由 |", "|---|---|"]
    for fid, F in FL.FIELDS.items():
        if not F["engine"]:
            lines.append("| %s（`%s`） | %s |" % (F["label"], fid, F["help"] or "記録のみ"))
    lines += ["| 基礎の形式（`g_foundation`） | エンジンは `project.foundation_system` を読まない（記録のみ）。統計の概算の場合分けの説明に使う |",
              "| 主な用途・構造（`b_use`・`b_structure`） | エンジンの単位は用途・構造を直接は読まない（用途別面積と、材料の行の分類を通じて効く） |",
              "", "## 4. 値によっては計算に入らない場合", "",
              "- 未取得・計算不能の項目：渡さない（欠損のまま。0 にしない）。材料・設備が未取得なら、その行が無いので合計に入らない（結果に「少なめ（下限）」と出る）。",
              "- 数量の単位が参照セットの原単位と合わない材料（例：m3 の原単位しか無いのに m2）：行を作らない。",
              "- 数量が m3・m2 の材料：質量が分からないので（密度を仮定しない）、解体時の運搬・処理（C2〜C4）のその行は不完全。",
              "- 統計の全体量（基礎を含む）のコンクリートと、基礎のコンクリートが両方あるとき：基礎の行は作らない（二重計上の防止）。",
              ""]
    return "\n".join(lines)
