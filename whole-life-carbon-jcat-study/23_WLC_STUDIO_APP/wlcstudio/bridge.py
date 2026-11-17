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

import dataclasses
import datetime as _dt
import hashlib
import json

from . import fields as FL
from .provenance import HAS_VALUE, LABEL, Value, competes

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
        self.inconsistent: list[str] = []          # inputs that contradict each other (reported, not blocking)
        self.na_refused: dict[str, str] = {}       # field -> why 適用外 cannot be used with the other inputs as they are
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


def _has(v: Value | None) -> bool:
    return v is not None and v.state in HAS_VALUE


def _num(v: Value | None):
    """(number, engine_state, how) for a numeric field, or (None, None, reason)."""
    if v is None:
        return None, None, "未取得"
    if v.state in HAS_VALUE:
        return v.value, _es(v), LABEL[v.state]
    if v.state == "not_applicable":
        return "NA", None, "適用外"
    return None, None, LABEL[v.state]


def _open_without(stages_: tuple) -> bool:
    """With the boundary unknown: does a boundary the screen offers (FL.STAGE_PRESETS) leave out all of these stages?
    A stored 適用外 that only these stages need is then usable with that boundary, so it is not listed as a missing
    required input (the boundary is listed, and stops the calculation); one that every offered boundary refuses is."""
    return any(not set(s_) & set(stages_) for _k, _l, s_ in FL.STAGE_PRESETS)


def _surely_zero(v: Value | None) -> bool:
    """適用外 of a na=zero field, or a value of 0 whose stated range does not reach above 0 (an assumed 0 with a range up
    to 150000 kWh is not a reason to drop the factor that the upper end needs)."""
    if v is None:
        return False
    if v.state == "not_applicable":
        return FL.FIELDS[v.field_id].get("na") == "zero"
    if v.state in HAS_VALUE and isinstance(v.value, (int, float)) and not isinstance(v.value, bool) and v.value == 0:
        u = v.uncertainty
        return not (u.kind in ("interval", "scenario") and isinstance(u.high, (int, float)) and u.high > 0)
    return False


def _surely_one(v: Value | None) -> bool:
    """A value of 1 whose stated range does not reach below 1 (a recovery rate of 100 %)."""
    if v is None or v.state not in HAS_VALUE or not isinstance(v.value, (int, float)) or isinstance(v.value, bool):
        return False
    if v.value != 1:
        return False
    u = v.uncertainty
    return not (u.kind in ("interval", "scenario") and isinstance(u.low, (int, float)) and u.low < 1)


def _low_end(v: Value) -> float:
    """The low end of a numeric value: the low end of its stated range (interval / scenario), else the value."""
    x = float(v.value)
    u = v.uncertainty
    if u.kind in ("interval", "scenario") and isinstance(u.low, (int, float)) and not isinstance(u.low, bool):
        x = min(x, float(u.low))
    return x


def _ranged(v: Value | None) -> bool:
    """A numeric value with a stated range (interval / scenario with numeric ends)."""
    u = getattr(v, "uncertainty", None)
    return _has(v) and isinstance(v.value, (int, float)) and not isinstance(v.value, bool) and u is not None and \
        u.kind in ("interval", "scenario") and \
        all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in (u.low, u.high))


def _inside(v: Value | None, period: float | None) -> bool:
    """Can an event every `v` years (a life, a cycle) fall inside the study period? Unknown: maybe; 適用外: no (never
    replaced), except on a field that cannot be absent (then it is missing: maybe); a number: when the LOW end of its
    stated range is shorter than T, so that a range reaching below T keeps the partners that act at that end (as
    _surely_zero does for a range above 0)."""
    x, _, _ = _num(v)
    if x is None:
        return True
    if x == "NA":
        return bool(FL.FIELDS[v.field_id].get("na_never"))
    if not isinstance(x, (int, float)) or isinstance(x, bool):
        return True
    return period is None or _low_end(v) < period


# The stages each input can change in this engine (a superset, measured one input at a time through the engine): an
# input whose stages all lie outside the chosen boundary cannot change the total, so it is reported as not reflected and
# is not counted as an estimate or a width. Equipment: the count reaches X-01 (A1-A3), repairs (B3), renewals (B4),
# a rebuild (B5) and X-14 (C3); the life only the renewals and the repair years (B3, B4); the mass X-14 (C3) and what
# repeats it (B4, B5). The equipment delivery / installation factors act only inside renewals (B4), not in A4 / A5.
_MAT_REACH = ("A1-A3", "A4", "A5", "B3", "B4", "B5", "C2", "C3", "C4")
_OP_REACH = ("B2", "B6")
_EQ_REACH = {"quantity": ("A1-A3", "B3", "B4", "B5", "C3"), "service_life": ("B3", "B4"),
             "end_of_life_mass_kg": ("B4", "B5", "C3")}
FIELD_REACH = {"m_repair_rate": ("B3",), "m_refresh_cycle": ("B3", "B4", "B5"), "m_transport_km": ("A4", "B4", "B5"),
               "m_transport_mode": ("A4", "B4", "B5"), "a_eol_haul_km": ("B4", "B5", "C2"),
               "a_eol_route": ("B4", "B5", "C3", "C4"), "e_repair_rate": ("B3",), "c_site_electricity": ("A5", "B5"),
               "c_diesel": ("A5", "B5"), "o_grid_construction": ("A5", "B5"), "o_grid_value": _OP_REACH,
               "o_source": _OP_REACH, "o_water_m3": ("B7",), "o_sewage_m3": ("B7",), "o_waste_kg": ("B7",),
               "a_reconstruction": ("B5",), "a_replacement_cycle": ("B5",), "a_recon_fraction": ("B5",)}
for _fid, _F in FL.FIELDS.items():
    if _fid not in FIELD_REACH:
        if _F["role"] == "equipment":
            FIELD_REACH[_fid] = _EQ_REACH[_F["part"]]
        elif _F["role"] in ("material", "mat_common"):
            FIELD_REACH[_fid] = _MAT_REACH
        elif _F["role"] == "refrigerant":
            FIELD_REACH[_fid] = ("B1", "B5")
        elif _F["role"] == "profile":
            FIELD_REACH[_fid] = _OP_REACH
# lives and cycles: an event every `v` years (_inside decides whether one can fall inside the study period)
EVENT_FIELDS = ("m_refresh_cycle", "a_replacement_cycle", "r_life") + tuple(
    f for f, F_ in FL.FIELDS.items() if F_["role"] == "equipment" and F_["part"] == "service_life")
# inputs whose HIGHER value gives a LOWER total (longer lives and cycles mean fewer renewals; more recovery, less loss):
# a range puts them at the opposite end (the waste rate depends on the quantity basis: see decreasing())
DECREASING = {"m_refresh_cycle", "e_hvac_life", "e_electrical_life", "e_plumbing_life", "e_conveyance_life", "r_life",
              "r_recovery_rate", "a_replacement_cycle", "o_pv_kwh", "m_reuse_rate"}


def decreasing(fid: str, values: dict) -> bool:
    """Does a HIGHER value of this input give a LOWER total? The fixed set above, and the waste rate when the quantities
    are not design quantities: the engine (A13-05) orders Q/(1-w) for DESIGN (a higher rate raises A1-A3 / A4) but
    orders Q and installs Q(1-w) otherwise, also when the basis is not given (a higher rate lowers C2-C4 and B4)."""
    if fid == "m_waste_rate":
        qb = values.get("m_quantity_basis")
        return not (_has(qb) and qb.value == "DESIGN")
    return fid in DECREASING


# inputs that cannot change the whole-life total in this engine: the facility-management share (moves B2 inside B6),
# generation / export once the purchase is known (handled by the reflection), the building data that only the
# per-area values or the record read (floor area, storeys, height, footprint, completion year with a constant grid
# factor), the reuse rate (no unit of this engine reads it), and the choices that are passed but read by no unit of
# the total (use, structure, new / existing, foundation, kind of operation data: measured, every option gives the
# same total). They are still passed and shown as reflected, but not counted as estimates or widths.
TOTAL_NEUTRAL = {"o_fm_ratio", "o_pv_kwh", "o_export_kwh", "b_gfa", "b_floors_above", "b_floors_below", "b_height",
                 "b_footprint", "b_completion_year", "m_reuse_rate", "b_use", "b_structure", "b_project_type",
                 "g_foundation", "o_source"}


def _competes(v: Value | None) -> bool:
    return competes(v)


def _whole_word(v: Value) -> str:
    """How a whole-building / all-steel value is named in the double-counting notes: only a statistical value is a
    「統計量」."""
    return "統計量" if v.state == "statistical" else "値（全体の量として入れたもの）"


def _unknown(v: Value | None) -> bool:
    return v is None or v.state in ("not_obtained", "not_computable")


def _gap_word(v: Value | None) -> str:
    """How a missing input is named in a gap's reason: 未取得 / 計算不能, or a stored 適用外 of a field that cannot be absent."""
    if v is None:
        return "未取得"
    return "適用外（無いということが無い項目）" if v.state == "not_applicable" else LABEL[v.state]


def _unit_blocks(blocked: dict, route_word: str, w) -> str:
    """Why a material quantity other than 0 in these units could not change the total, grouped by the reason (`blocked`:
    unit -> "factor" / "route" / "stage", in the order of the field's units)."""
    by = {}
    for u_, k_ in blocked.items():
        by.setdefault(k_, []).append(u_)
    parts = []
    if by.get("factor"):
        parts.append("%s では原単位が参照セットに無い" % "・".join(by["factor"]))
    if by.get("route"):
        parts.append("%s では解体時の質量が分かり、解体後の処理シナリオ（%s）が要る（計算できない）" % ("・".join(by["route"]), route_word))
    if by.get("stage"):
        parts.append("%s では%s評価範囲のどの段階も計算できない" % ("・".join(by["stage"]),
                                                       "施工時の廃棄率が未取得で発注量が決まらず、" if w is None else ""))
    return "。".join(parts)


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


# how a stored 適用外 on a field that cannot be absent (na_never: refused on save, but saved before that) is said: it is
# read as 未取得 (the bridge, the progress of the inputs)
NA_NEVER_WORD = "適用外（無いということが無い項目なので、未取得として扱う）"


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
        if v is not None and v.state == "not_applicable" and FL.FIELDS[fid].get("na_never"):
            # a stored 適用外 on a field that cannot be absent (saved before it was refused): missing, as 未取得
            x, how = None, NA_NEVER_WORD
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
        d.skip("a_stages", sv, (NA_NEVER_WORD if sv is not None and sv.state == "not_applicable" else "未設定")
               + "：計算しない（段階が空だとエンジンは 0 を返すため）")
    st_set = set(stages or ())

    ctx = {"b5": False, "b4_material": True, "b4_equipment": True, "b1_replacement": True, "b2_moot": False,
           "route_stages": ["C3", "C4"]}
    # multipliers that are surely 0 make whole stages of a kind of row moot: 0 km (A4 of every material row), a 0 haul
    # distance (C2), a repair rate of 0 (B3 of the materials / of the equipment). A gap cannot change those stages.
    ctx["dist0"] = _surely_zero(V("m_transport_km"))
    # a distance whose VALUE is 0 gives A4 = 0 for every row, also when its stated range reaches above 0 (the range is
    # moved to its ends by the range calculation; its partners, the mode and the masses, are still judged by dist0)
    _dv = V("m_transport_km")
    dist_at0 = ctx["dist0"] or (_has(_dv) and isinstance(_dv.value, (int, float)) and not isinstance(_dv.value, bool)
                                and _dv.value == 0)
    ctx["haul0"] = _surely_zero(V("a_eol_haul_km"))
    ctx["mrep0"] = _surely_zero(V("m_repair_rate"))
    ctx["erep0"] = _surely_zero(V("e_repair_rate"))
    zero_by_kind = {"material": {s_ for s_, z in (("A4", dist_at0), ("C2", ctx["haul0"]), ("B3", ctx["mrep0"])) if z},
                    "equipment": {"B3"} if ctx["erep0"] else set()}

    def missing(fid, stage_list, reason, kind=None, label=None, gap="omitted", ctx_over=None, advice=None):
        """Record a gap whose stages are inside the boundary. gap="omitted": not in the total (the total is a lower bound);
        gap="assumed": in the total, but computed with an assumption instead of the inputs (the stage is not determined);
        gap="split": the total is right but how it splits between stages is not determined (B2 counted inside B6).
        `advice`: what completes it when there is more than one way (shown in the hint of its stages)."""
        zero = zero_by_kind.get(kind, set()) | set((ctx_over or {}).get("zero", ()))
        hit = [s for s in expand_stages([s_ for s_ in stage_list if s_ not in zero], dict(ctx, **(ctx_over or {})), kind)
               if s in st_set and s not in zero]
        if hit and not any(m["field"] == fid for m in missing_inputs):
            missing_inputs.append({"field": fid, "label": label or FL.FIELDS[fid]["label"], "stages": hit, "reason": reason,
                                   "gap": gap, "screen_field": fid in FL.FIELDS, **({"advice": advice} if advice else {})})

    moot = []                     # (field, reason): passed, but a partner that is surely 0 makes it unable to act
    rec = V("a_reconstruction")
    if rec is not None and rec.state == "not_applicable":
        d.item("assessment", "boundary.reconstruction_scenario", "NONE")       # 適用外 = no reconstruction
        d.use("a_reconstruction", rec, "適用外：改修・建替えなし（NONE）として渡した", ["boundary.reconstruction_scenario"])
    else:
        scalar("a_reconstruction", "assessment", "boundary.reconstruction_scenario")
    rec_active = _has(rec) and rec.value != "NONE"
    # B5 can only be affected when a refurbishment / rebuild falls inside the study period (the low end of the cycle's
    # stated range below T) and has a non-zero share
    cyc_in = _inside(V("a_replacement_cycle"), period)
    fra0 = _surely_zero(V("a_recon_fraction"))
    cyc_never = _never("a_replacement_cycle", V("a_replacement_cycle"))
    fra_unknown = _unknown(V("a_recon_fraction"))
    # the engine's B5 is (share × the upfront and end-of-life emissions) at each cycle inside T, for any scenario other
    # than NONE: without the cycle or the share it is 0, and with a share of 0 or no cycle inside T it is 0. Then no
    # scenario can change the total — the same test for an active scenario and for NONE / 適用外
    b5_none = fra0 or not cyc_in or fra_unknown or cyc_never
    ctx["b5"] = rec_active and cyc_in and not fra0
    if rec_active:
        # the cycle and the share are passed only when a rebuild / refurbishment is assumed: the engine computes B5 for
        # any scenario other than "NONE", so passing them with an unknown scenario would add a rebuild nobody chose
        scalar("a_replacement_cycle", "assessment", "boundary.replacement_cycle")
        scalar("a_recon_fraction", "assessment", "boundary.reconstruction_scope_fraction")
        if cyc_never and not fra0:
            missing("a_replacement_cycle", ("B5",), "改修・建替えの周期が未取得（エンジンは周期が無いと B5 を数えないが、不完全とは示さない）")
        if fra_unknown and cyc_in:
            missing("a_recon_fraction", ("B5",), "改修の範囲の割合が未取得")
        # (b5_none above) the partner, and the choice between refurbishment and rebuild, cannot change the total
        if fra0:
            moot.append(("a_replacement_cycle", "渡したが、改修の範囲の割合が 0 なので B5 は 0（周期は効かない）"))
        elif fra_unknown:
            moot.append(("a_replacement_cycle", "渡したが、改修の範囲の割合が未取得なので B5 は計算できない（周期は合計を変えない。"
                                                "割合が要るかどうかだけを決める）"))
        if not cyc_in:
            moot.append(("a_recon_fraction", "渡したが、改修・建替えの周期が評価期間より長いので B5 は 0（割合は効かない）"))
        elif cyc_never:
            moot.append(("a_recon_fraction", "渡したが、改修・建替えの周期が未取得なので B5 は計算できない（割合は合計を変えない）"))
        if b5_none:
            moot.append(("a_reconstruction", "渡したが、B5 は 0 か計算できない（周期・割合による）ので、想定は合計を変えない"
                                             "（周期・割合が要るかどうかだけを決める）"))
    else:
        for f in ("a_replacement_cycle", "a_recon_fraction"):
            d.skip(f, V(f), "改修・建替えを想定していない（または想定が未取得）ので渡さない")
        if _unknown(rec) and cyc_in and not fra0:
            missing("a_reconstruction", ("B5",), "大規模改修・建替えの想定が未取得（B5 は計算できない）")
            # the cycle and the share that B5 needs as well, named at once (as the refrigerant parts of B1): B5 stays as
            # marked; only the named inputs grow (the cycle can fall inside T and the share is not 0 here)
            if cyc_never:
                missing("a_replacement_cycle", ("B5",), "改修・建替えの周期が%s（想定を入れても、周期が無いと B5 は計算できない）"
                        % _gap_word(V("a_replacement_cycle")))
            if fra_unknown:
                missing("a_recon_fraction", ("B5",), "改修の範囲の割合が%s（想定を入れても、割合が無いと B5 は計算できない）"
                        % _gap_word(V("a_recon_fraction")))
        elif _unknown(rec) and fra0:
            d.skip("a_reconstruction", rec, "改修の範囲の割合が 0 なので、想定がどれでも B5 は 0（想定は問わない）")
        elif b5_none and not _unknown(rec):
            # 想定しない（NONE）/ 適用外 — by the same test as an active scenario: no scenario would change B5
            why_ = ("改修の範囲の割合が 0 なので B5 は 0" if fra0 else
                    "改修・建替えの周期が評価期間より長いので B5 は 0" if not cyc_in else
                    "改修・建替えの周期が未取得なので B5 は計算できない" if cyc_never else
                    "改修の範囲の割合が未取得なので B5 は計算できない")
            moot.append(("a_reconstruction", "渡したが、どの想定でも B5 は 0 か計算できない（%s）ので、想定は合計を変えない"
                                             "（周期・割合が要るかどうかだけを決める）" % why_))

    # ------------------------------------------------------------------ materials
    common = {k: V(k) for k in ("m_waste_rate", "m_reuse_rate", "m_repair_rate", "m_refresh_cycle", "m_transport_km",
                                "m_transport_mode", "m_quantity_basis", "a_eol_haul_km")}
    route_v = V("a_eol_route")
    route = route_v.value if route_v and route_v.state in HAS_VALUE else None
    route_filled = False
    if route is None and stages is not None and not st_set & {"C2", "C3", "C4", "B4", "B5"}:
        # no included stage reads the route (e.g. 「建設時だけ」): a placeholder that cannot act, said as such
        route, route_filled = "LANDFILL", True
    rows = []
    missing_materials = []
    # double counting: a whole-building concrete estimate already contains the foundations, an all-steel estimate
    # (rebar and structural steel together) already contains the other steel field. A figure that is surely 0 (a 0 whose
    # stated range stays at 0: provenance.competes) contains nothing, so it neither drops nor covers the other field; a
    # value typed in the other field next to it contradicts it, which is said (inconsistent_inputs), not dropped
    skip = {}
    covered = {}          # fields whose quantity is already inside a whole-building / all-steel figure (not missing)
    whole_c, fdn = V("m_concrete"), V("m_concrete_fdn")
    if _is_whole(whole_c, "whole_building") and _competes(whole_c):
        if _competes(fdn):
            skip["m_concrete_fdn"] = "上部構造の欄に基礎を含む建物全体の%sが入っているので、基礎の行は作らない（二重計上を防ぐ）" % _whole_word(whole_c)
            d.double_count.append("コンクリート：建物全体（基礎を含む）の%sと基礎の値が両方ある。基礎の行は使っていない" % _whole_word(whole_c))
        elif _unknown(fdn):
            covered["m_concrete_fdn"] = "上部構造の欄の建物全体の%sに含まれている（行は作らない）" % _whole_word(whole_c)
    elif _is_whole(whole_c, "whole_building") and _competes(fdn):
        d.inconsistent.append("コンクリート：上部構造の欄の建物全体（基礎を含む）の%sが 0 なのに、基礎の欄に値がある。0 の全体量は何も"
                              "含まないので、基礎の行はそのまま使った（二重計上にはならない）" % _whole_word(whole_c))
    rb, stl = V("m_rebar"), V("m_steel")
    for whole, other, wname, oname in ((rb, stl, "鉄筋", "鉄骨"), (stl, rb, "鉄骨", "鉄筋")):
        ofid = "m_steel" if oname == "鉄骨" else "m_rebar"
        if _is_whole(whole, "all_steel") and not _competes(whole):
            if _competes(other):
                d.inconsistent.append("鉄：%sの欄の鉄の全量（鉄筋＋鉄骨）の%sが 0 なのに、%sの欄に値がある。0 の全体量は何も含まないので、"
                                      "%sの行はそのまま使った（二重計上にはならない）" % (wname, _whole_word(whole), oname, oname))
        elif _is_whole(whole, "all_steel") and ofid not in skip and ("m_rebar" if ofid == "m_steel" else "m_steel") not in skip:
            if _competes(other):
                skip[ofid] = "%sの欄に鉄の全量（鉄筋＋鉄骨）の%sが入っているので、%sの行は作らない（二重計上を防ぐ）" % (wname, _whole_word(whole), oname)
                d.double_count.append("鉄：鉄の全量（%sの欄）の%sと%sの値が両方ある。%sの行は使っていない" % (wname, _whole_word(whole), oname, oname))
            elif _unknown(other):
                covered[ofid] = "%sの欄の鉄の全量（鉄筋＋鉄骨）の%sに含まれている（行は作らない）" % (wname, _whole_word(whole))

    def skipped_if_nonzero(fid, v):
        """The whole-building / all-steel figure that a quantity other than 0 of this field would be left out for (the
        guard above, run with the field at a value that is not 0), or None. A 0 is never double counted, so the guard
        does not see it; but when every other value would be dropped, the 0 cannot change the total either. A figure
        that is surely 0 covers nothing (the guard above): it drops no value."""
        if fid == "m_concrete_fdn" and _is_whole(whole_c, "whole_building") and _competes(whole_c):
            return "上部構造の欄の建物全体（基礎を含む）の%s" % _whole_word(whole_c)
        if fid in ("m_rebar", "m_steel"):
            hyp = dataclasses.replace(v, value=1.0)
            rb_, stl_ = (hyp, stl) if fid == "m_rebar" else (rb, hyp)
            for whole, other, ofid, wname in ((rb_, stl_, "m_steel", "鉄筋"), (stl_, rb_, "m_rebar", "鉄骨")):
                if _is_whole(whole, "all_steel") and _competes(whole) and _competes(other):
                    return ("%sの欄の鉄の全量（鉄筋＋鉄骨）の%s" % (wname, _whole_word(whole))) if ofid == fid else None
        return None
    # can a material renewal fall inside the study period? (unknown cycle: maybe; 適用外 = no renewal; a range: its low end)
    ctx["b4_material"] = _inside(common["m_refresh_cycle"], period)
    renew = {}                 # per trade: can a replacement fall inside the study period? (unknown life: maybe)
    for trade, _ in FL.TRADES:
        cv_ = V("e_%s_count" % trade.lower())
        if (cv_ is not None and cv_.state == "not_applicable") or _surely_zero(cv_):
            continue
        renew[trade] = _inside(V("e_%s_life" % trade.lower()), period)
    ctx["b4_equipment"] = any(renew.values())
    eq_gap_renew = []          # trades with a count / mass gap that can be renewed inside T (the server's X-01 / X-14)
    route_st = {"LANDFILL": ("C4",)}.get(route, ("C3",)) if route else ("C3", "C4")
    ctx["route_stages"] = list(route_st)
    mat_stages = ("A1-A3", "A4", "C2") + route_st
    wx, wst, _ = _num(common["m_waste_rate"])
    w = 0.0 if wx == "NA" and FL.FIELDS["m_waste_rate"]["na"] == "zero" else (float(wx) if isinstance(wx, (int, float)) else None)
    w_state = "EXPLICIT_ZERO" if wx == "NA" else wst
    qb = common["m_quantity_basis"]
    basis = qb.value if _has(qb) else None
    b_state = ENGINE_STATE[qb.state] if _has(qb) else None
    route_massless = False

    def _mass_row(f_, c_, u_):
        """Would this field make a row with an installed mass? (a mass unit with a factor, as in the loop below)"""
        v_ = V(f_)
        if not _competes(v_) or f_ in skip or (v_.unit or u_) not in TO_KG:
            return False
        fac_ = P["material"].get(c_, {})
        return bool(fac_.get(v_.unit or u_) or fac_.get("kg")) and (basis == "DESIGN" or w is not None)
    if route is None and stages is not None:
        # the route acts only through the end-of-life (installed) mass of a row (the moot rule below). When no row can
        # have one — only m3 / m2 rows (no density is assumed), or quantities that are not design quantities with the
        # waste rate unknown — the route cannot act yet: a placeholder (as for 「建設時だけ」) instead of refusing the
        # calculation, and the route stays a named gap of the end-of-life stages (route_st keeps C3 and C4)
        route_massless = not any(_mass_row(f_, c_, u_) for f_, c_, _l, u_, *_ in FL.MATERIALS)
        if route_massless:
            route = "LANDFILL"
    used_tkm = False
    tkm_beyond0 = False        # a row at 0 km whose ordered mass is known: tonne-km (and the mode) act above 0 km
    fallback_rows, no_transport_rows = [], []
    row_stages = {}            # material field -> the stages its row can change (row_acts below)
    # shared input -> would another value of it let some row change a stage in the boundary? (row_acts below)
    alt_acts = {k: False for k in ("m_quantity_basis", "m_transport_km", "a_eol_haul_km", "a_eol_route")}
    # the shared inputs as every row reads them
    dist, dst, _ = _num(common["m_transport_km"])
    mode = common["m_transport_mode"]
    mode_ok = _has(mode) and mode.value in P["transport"]
    # the delivered (ordered) quantity the engine multiplies by a per-quantity delivery factor: its own ordered
    # quantity (A13-05), which it computes only when the waste rate is known — whatever the quantity basis
    delivered_known = w is not None
    hk, hst, _ = _num(common["a_eol_haul_km"])
    mrep_known = _num(common["m_repair_rate"])[0] is not None       # 適用外 is a rate of 0 (na="zero")

    def row_acts(qu, cls, b_, dist_=dist, dist0_=ctx["dist0"], hk_=hk, haul0_=ctx["haul0"], eol_="route", rst_=route_st):
        """The stages a row of class `cls` with a quantity in `qu` can change through its quantity, as the engine computes
        them: A1-A3 only with the waste rate (A13-05 orders nothing without it), A4 by tonne-km on the ordered mass or by
        the delivery factor on the ordered quantity (not at 0 km), C2-C4 with the end-of-life (installed) mass, and what
        repeats them (B3 repairs, B4 renewals, B5 a rebuild). The masses follow the quantity basis b_ (DESIGN: ordered =
        Q/(1-w), installed = Q; otherwise ordered = Q, installed = Q(1-w)); the other arguments let the shared inputs be
        tried at another value (would another basis, a distance other than 0, another route … let the row act?). Also
        asked for a quantity of 0 (no row): would a quantity other than 0 act?"""
        kg_ = TO_KG.get(qu)
        if eol_ == "route":
            eol_ = P["eol"].get(cls, {}).get(route)
        del_ok_ = bool(P["delivery"].get(cls)) and _same_dim(F_[P["delivery"][cls]]["unit"], qu)
        has_ord = kg_ is not None and (b_ != "DESIGN" or (w is not None and w < 1))
        has_ins = kg_ is not None and (b_ == "DESIGN" or w is not None)
        a_ = {"A1-A3"} if w is not None else set()
        if not dist0_ and ((has_ord and isinstance(dist_, float) and mode_ok) or (del_ok_ and delivered_known)):
            a_.add("A4")
        if has_ins:
            if isinstance(hk_, float) and not haul0_:
                a_.add("C2")
            if eol_:
                a_.update(rst_)
        if "A1-A3" in a_ and mrep_known and not ctx["mrep0"]:
            a_.add("B3")
        if a_ and ctx["b4_material"]:
            a_.add("B4")
        if a_ and ctx["b5"]:
            a_.add("B5")
        return a_

    route_word = LABEL[route_v.state] if route_v else "未取得"

    def needs_route(qu, cls, b_):
        """Would a row of class `cls` in `qu` under the basis b_ have an end-of-life (installed) mass while the route is
        only the massless placeholder (not given, an end-of-life stage in the boundary)? Then the route would be
        required (_mass_row above) and the calculation refused: such a value is not one that changes the total."""
        fac_ = P["material"].get(cls, {})
        return route_massless and qu in TO_KG and bool(fac_.get(qu) or fac_.get("kg")) and (b_ == "DESIGN" or w is not None)

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
        if _surely_zero(v):
            # like 0 台 and a 0 kg charge: no row, so that a nil quantity cannot leave masses or transport undetermined.
            # The 0 counts only when a quantity other than 0 would make a row that changes a stage in the boundary (the
            # same test as for a row: a missing waste rate, a unit without a factor … can leave every stage unable to act),
            # in ANY unit the field accepts: the unit stored with a 0 is arbitrary (0 t and 0 m3 are the same nil quantity),
            # so the 0 is not counted only when no accepted unit would let a value other than 0 act
            fac0 = P["material"].get(cls, {})
            whole_ = skipped_if_nonzero(fid, v)
            units0 = list(FL.FIELDS[fid].get("units") or ()) or [v.unit or unit]
            blocked_u = {}             # accepted unit -> why a value other than 0 in it could not change the total
            if stages is not None and not whole_:
                for u_ in units0:
                    if not (fac0.get(u_) or (fac0.get("kg") if u_ in TO_KG else None)):
                        blocked_u[u_] = "factor"
                    elif needs_route(u_, cls, basis):
                        # a row with an end-of-life mass, which needs the route (not given): such a value refuses the
                        # calculation
                        blocked_u[u_] = "route"
                    elif not row_acts(u_, cls, basis) & st_set:
                        blocked_u[u_] = "stage"
            acting_u = [u_ for u_ in units0 if u_ not in blocked_u]
            how0 = "数量 0：この材料の行は作らない"
            if stages is not None and not whole_ and blocked_u and acting_u:
                # counted (a value in another unit acts): which unit acts, and why the others would not
                how0 += "（0 でない数量は %s なら合計に効く。%s）" % ("・".join(acting_u), _unit_blocks(blocked_u, route_word, w))
            d.use(fid, v, how0, ["materials"])
            if stages is not None and whole_:
                # a value other than 0 would be dropped as double counting: no row either way
                moot.append((fid, "渡したが、0 でない値は%sに含まれるので行を作らない（二重計上を防ぐ）。数量 0 は合計を変えない"
                             % whole_))
            elif stages is not None and not acting_u:
                kinds = set(blocked_u.values())
                if kinds == {"factor"}:
                    moot.append((fid, "渡したが、単位 %s の原単位が参照セットに無いので、0 でない数量でもこの材料は計算に入らない"
                                      "（数量 0 は合計を変えない）" % "・".join(blocked_u)))
                elif kinds == {"route"}:
                    moot.append((fid, "渡したが、解体後の処理シナリオが%sで、0 でない数量ならこの行に解体時の質量が分かり処理シナリオが要る"
                                      "（計算できない）ので、数量 0 は合計を変えない（処理シナリオを入れると効く）" % route_word))
                elif kinds == {"stage"}:
                    moot.append((fid, "渡したが、%s0 でない数量でもこの材料の行は評価範囲のどの段階も計算できないので、数量 0 は"
                                      "合計を変えない（欠けた入力を入れると効く）"
                                 % ("施工時の廃棄率が未取得で発注量が決まらず、" if w is None else "")))
                else:
                    moot.append((fid, "渡したが、0 でない数量はどの単位でも、合計を変えないか計算が止まる（%s）ので、数量 0 は"
                                      "合計を変えない（欠けた入力を入れると効く）" % _unit_blocks(blocked_u, route_word, w)))
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
            if isinstance(rc, (int, float)) and _inside(common["m_refresh_cycle"], period):  # a renewal can fall inside T
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
        wb = (w_state, b_state) if (w is None or not _surely_zero(common["m_waste_rate"])) else ()  # basis matters only with offcuts
        if dist_at0:
            # 0 km: A4 is 0 whatever the mass and the mode (a mass that is not known is filled with 0: it cannot act). Also
            # for a 0 whose stated range reaches above 0: the value is 0 km (not the per-quantity delivery factor), and the
            # range calculation moves it to its ends
            mv_ = mode.value if mode_ok else sorted(P["transport"])[0]
            row.update({"transport.mass_t": ordered_kg / 1000.0 if ordered_kg is not None else 0.0, "transport.distance_km": 0.0,
                        "transport.mode": mv_, "transport.factor_id": P["transport"][mv_], "transport.delivery_factor_id": None})
            states.update({"transport.mass_t": _derived(qst, *(wb if basis == "DESIGN" else (b_state,))) if ordered_kg is not None
                           else "EXPLICIT_ZERO", "transport.distance_km": dst or "EXPLICIT_ZERO"})
            how.append("運搬 距離 0 km：A4 は 0（質量・手段は効かない）" if ctx["dist0"] else
                       "運搬 距離 0 km：A4 は 0（距離の範囲の上端では運搬を計算する）")
            used_tkm = True
            tkm_beyond0 |= ordered_kg is not None
        elif ordered_kg is not None and isinstance(dist, float) and mode_ok:
            mv_ = mode.value
            row.update({"transport.mass_t": ordered_kg / 1000.0, "transport.distance_km": dist, "transport.mode": mv_,
                        "transport.factor_id": P["transport"][mv_], "transport.delivery_factor_id": None})
            states.update({"transport.mass_t": _derived(qst, *(wb if basis == "DESIGN" else (b_state,))), "transport.distance_km": dst})
            how.append("運搬 トンキロ（%s・%s km）" % (mv_, dist))
            used_tkm = True
        elif P["delivery"].get(cls) and _same_dim(F_[P["delivery"][cls]]["unit"], qu) and delivered_known:
            row.update({"transport.mass_t": None, "transport.distance_km": None, "transport.mode": None,
                        "transport.factor_id": None, "transport.delivery_factor_id": P["delivery"][cls]})
            how.append("運搬 参照セットの配送原単位 %s（数量あたり。距離・手段の入力ではない）" % P["delivery"][cls])
            fallback_rows.append(label)
        else:
            row.update({"transport.mass_t": None, "transport.distance_km": None, "transport.mode": None,
                        "transport.factor_id": None, "transport.delivery_factor_id": None})
            has_del = bool(P["delivery"].get(cls)) and _same_dim(F_[P["delivery"][cls]]["unit"], qu)
            if kg is not None and ordered_kg is None:
                # DESIGN: the delivered (ordered) mass Q/(1-w) needs the waste rate (then tonne-km or the delivery factor)
                why, cause = "廃棄率が未取得で発注量（運搬する量）が決まらない", "waste"
            elif kg is not None:
                # the ordered mass is known (ORDERED / AS_BUILT: ordered = Q): the distance and the mode complete A4;
                # the waste rate alone would only give the per-quantity delivery factor (an assumption)
                why, cause = "運搬距離・手段がそろわない（そろえばトンキロで計算できる）" + (
                    "。廃棄率も未取得なので、参照セットの数量あたりの配送原単位も使えない" if has_del and not delivered_known
                    else "。同じ単位の配送原単位も無い"), "inputs"
            elif has_del and not delivered_known:
                # a volume / area row: only the per-quantity delivery factor can carry it, on the ordered quantity that the
                # engine computes only with the waste rate (whatever the basis)
                why, cause = ("数量が %s で質量が分からず（密度を仮定しない）、廃棄率が未取得なのでエンジンが発注量を求めず、"
                              "参照セットの数量あたりの配送原単位も使えない" % qu), "waste"
            else:
                why, cause = "数量が %s で質量が分からず（密度を仮定しない）、同じ単位の配送原単位も無い" % qu, "unit"
            d.unconnected.append({"label": label + "の運搬（A4）", "reason": why})
            no_transport_rows.append((label, cause, has_del and not delivered_known))
        row["transport.load_factor"] = None
        row["end_of_life.mass_kg"] = installed_kg
        if installed_kg is not None:
            states["end_of_life.mass_kg"] = _derived(qst, *(wb if basis != "DESIGN" else (b_state,)))
        else:
            d.unconnected.append({"label": label + "の解体時質量（C2〜C4）",
                                  "reason": (("数量が %s のため質量が分からない（密度を仮定しない）" % qu) if kg is None
                                             else "廃棄率が未取得で、施工後の質量が決まらない") + "。解体段階のこの行は不完全"})
            if kg is None:
                # a named gap (the same field takes t / kg): the hint and the lower-bound list say what completes it
                missing(fid, ("C2",) + route_st, "数量が %s で質量が分からない（密度を仮定しない）：解体段階（C2〜C4）と更新時のその分（B4）が"
                        "計算できない。t か kg で入れると C2〜C4 は計算できる（更新時の施工の原単位は %s あたりなので、B4 はどちらの単位でも"
                        "全部はそろわないことがある）" % (qu, qu), kind="material")
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
        acts = row_acts(qu, cls, basis)
        row_stages[fid] = acts
        # would another value of a shared input let this row change a stage in the boundary? (then it is not moot when no
        # row acts): another quantity basis, a distance other than 0 km (to the site, for disposal), another route
        # (a basis that would give this row an end-of-life mass while the route is not given refuses the calculation)
        alt_acts["m_quantity_basis"] |= any(row_acts(qu, cls, b_) & st_set for b_, _ in FL.FIELDS["m_quantity_basis"]["enum"]
                                            if not needs_route(qu, cls, b_))
        alt_acts["m_transport_km"] |= "A4" in row_acts(qu, cls, basis, dist_=1.0, dist0_=False)
        alt_acts["a_eol_haul_km"] |= bool(row_acts(qu, cls, basis, hk_=1.0, haul0_=False) & st_set)
        alt_acts["a_eol_route"] |= any(
            row_acts(qu, cls, basis, eol_=P["eol"].get(cls, {}).get(r_), rst_=("C4",) if r_ == "LANDFILL" else ("C3",)) & st_set
            for r_, _ in FL.FIELDS["a_eol_route"]["enum"])
        if stages is not None and not acts & st_set:
            moot.append((fid, "渡したが、%sこの行は評価範囲のどの段階も計算できないので、数量は合計を変えない（欠けた入力を入れると効く）"
                         % ("施工時の廃棄率が未取得で発注量が決まらず、" if w is None else "")))
    # (for the range: a distance whose value is 0 with rows whose ordered mass is known computes A4 by tonne-km at an
    # upper end above 0 km, where the mode is then needed)
    ctx["dist_at0"], ctx["tkm_beyond0"] = bool(dist_at0), bool(tkm_beyond0)
    if rows:
        d.tables["construction"]["materials"] = rows
        if route_v and route_v.state in HAS_VALUE:
            d.use("a_eol_route", route_v, "全部の材料の行に 1 つの処理（割合 1）として渡した", ["materials[].end_of_life.routes"])
        elif route_filled:
            d.skip("a_eol_route", route_v, "解体後の段階（C2〜C4・B4・B5）を評価範囲から外したので、処理シナリオは効かない："
                                           "行に仮の処理を入れた（計算には入らない）")
        elif route_massless:
            d.skip("a_eol_route", route_v, (LABEL[route_v.state] if route_v else "未取得") +
                   "：解体時の質量が分かる材料の行が無いので、いまは処理シナリオは効かない：行に仮の処理を入れた"
                   "（計算には入らない。質量が分かると必須）")
            missing("a_eol_route", ("C3", "C4"), "解体後の処理シナリオが%s（いまは解体時の質量が分かる材料の行が無いので効かないが、"
                    "質量が分かると必須）" % (LABEL[route_v.state] if route_v else "未取得"), kind="material")
        # the end-of-life stages (C2〜C4, and B4 / B5 that repeat them) are reached only through a row with a mass: an
        # m3 / m2 row has no end-of-life mass whatever the basis, the waste rate or the haul distance (its own gap says
        # 「t か kg で入れると」), so these inputs are not named as gaps of C2〜C4 without one
        mass_rows = any(r_["quantity_unit"] in TO_KG for r_ in rows)
        eol_st = (("C2",) + route_st) if mass_rows else ()
        if _never("m_quantity_basis", qb) and (w is None or w > 0):
            missing("m_quantity_basis", ("A1-A3", "A4") + eol_st, "数量の基準（設計・発注・竣工）が%s：廃棄分の扱いが決まらない"
                    % (LABEL[qb.state] if qb else "未取得"), kind="material")
        # the waste rate decides the ordered quantity (A1-A3; A4 when a row is carried by its ordered quantity) and, for
        # quantities that are not design quantities, the installed mass (C2〜C4)
        waste_a4 = basis == "DESIGN" or any(c_ == "waste" for _l, c_, _a in no_transport_rows)
        w_stages = ("A1-A3",) + (("A4",) if waste_a4 else ()) + (() if basis == "DESIGN" else eol_st)
        for cf, stg, why in (("m_waste_rate", w_stages, "施工時の廃棄率が未取得（発注量・施工後の質量が決まらない）"),
                             ("m_repair_rate", ("B3",), "修繕率が未取得"),
                             ("m_refresh_cycle", ("B4",), "更新周期が未取得（エンジンは周期が無いと更新を数えないが、不完全とは示さない）"),
                             ("a_eol_haul_km", eol_st[:1], "解体材の運搬距離が未取得")):
            if _never(cf, common[cf]):
                missing(cf, stg, why, kind="material")
                mr_, _, _ = _num(common["m_repair_rate"])
                # only when a row computes repairs (B3 needs its A1-A3): otherwise there is no repair to over-count
                if cf == "m_refresh_cycle" and "B3" in st_set and isinstance(mr_, (int, float)) and mr_ > 0 and \
                        any("B3" in a_ for a_ in row_stages.values()):
                    missing("m_refresh_cycle@B3", ("B3",), "更新周期が未取得：更新の年の修繕を除けないので、B3 は多めになりうる（合計には入っている）",
                            label="更新周期（修繕 B3 への影響）", gap="assumed")
        if fallback_rows:
            # the per-quantity delivery factor of the reference set replaces distance × mode × mass: an assumption, so A4
            # (and what repeats it) is marked as not determined from the inputs
            names = "、".join(fallback_rows[:6]) + ("ほか %d 行" % (len(fallback_rows) - 6) if len(fallback_rows) > 6 else "")
            d.assumed.append("運搬（A4）は %d 行（%s）で参照セットの配送原単位（数量あたり）を使った：運搬距離・手段の入力によるものではない（仮定）"
                             % (len(fallback_rows), names))
            missing("a4_delivery_fallback", ("A4",), "%d 行（%s）は運搬距離・手段ではなく、参照セットの数量あたりの配送原単位で計算した（仮定）"
                    % (len(fallback_rows), names), kind="material", label="運搬（A4）の代わりの原単位",
                    gap="assumed")
        by_cause = {}
        for lab, cause, _alt in no_transport_rows:
            by_cause.setdefault(cause, []).append(lab)
        if by_cause.get("inputs"):
            # the distance / mode is the gap of these rows (their ordered mass is known); both are named when both are
            # missing, and the waste rate is named as the other (assumed) way when it would allow the delivery factor
            tfs = [f for f in ("m_transport_km", "m_transport_mode") if _never(f, common[f])] or ["m_transport_mode"]
            alt = any(a_ for _l, c_, a_ in no_transport_rows if c_ == "inputs")
            advice = ("A4 は、運搬距離・手段を入れるとトンキロで計算できる（入力どおり）。廃棄率だけを入れると、参照セットの数量あたりの"
                      "配送原単位で計算する（仮定）") if alt else None
            for tf in tfs:
                missing(tf, ("A4",), "運搬を計算できない行がある（%s）" % "、".join(by_cause["inputs"][:6]), kind="material",
                        advice=advice)
        if by_cause.get("unit"):
            missing("a4_no_mass", ("A4",), "数量が体積・面積で質量が分からず、同じ単位の配送原単位も無いので運搬を計算できない（%s）"
                    % "、".join(by_cause["unit"][:6]), kind="material", label="運搬（A4）：質量の分からない材料")
        # the "waste" cause is already covered by the waste-rate entry (its stages include A4)
    elif any(_competes(V(f[0])) and f[0] not in skip for f in FL.MATERIALS) and route is None:
        if not (stages is None and route_v is not None and route_v.state == "not_applicable"
                and _open_without(("C2", "C3", "C4", "B4", "B5"))):
            # (with the boundary unknown, a stored 適用外 that a boundary the screen offers accepts — one without the
            # stages after demolition — is not a missing required input: the boundary is, and the row says the rest)
            d.missing.append("解体後の処理シナリオ（材料の行ごとに必須）")
        if route_v is not None and route_v.state == "not_applicable":
            # 適用外 is placed (it cannot act) when no stage after demolition is in the boundary, when there is no material
            # row, or when no row has an end-of-life mass (above); here a row has one, so the route is needed
            why_ = ("解体時の質量が分かる材料の行があり、解体後の段階が評価範囲にあるので、処理シナリオが要る。材料の行が無いとき、"
                    "質量の分かる行が無いとき、解体後の段階（C2〜C4・B4・B5）を評価範囲から外したときは適用外にできる")
            if stages is not None:
                d.na_refused["a_eol_route"] = why_
                d.skip("a_eol_route", route_v, "適用外にはできない（%s）：材料の行を渡せない（計算しない）" % why_)
            elif any(_mass_row(f_, c_, u_) for f_, c_, _l, u_, *_ in FL.MATERIALS):
                # the boundary is not given (the calculation stops for it anyway): whether the 適用外 can be used depends
                # on it, so it is not said to be impossible (the save accepted it; setting the boundary warns if it is not)
                d.skip("a_eol_route", route_v, "評価範囲が未取得なので、この適用外が使えるかは評価範囲で決まる（解体時の質量が分かる材料の"
                                               "行があるので、解体後の段階（C2〜C4・B4・B5）を評価範囲に入れると処理シナリオが要る。外したときは"
                                               "適用外にできる）：材料の行を渡せない（計算しない）")
            else:
                d.skip("a_eol_route", route_v, "評価範囲が未取得なので、この適用外はまだ判定していない（いまは解体時の質量が分かる材料の行が"
                                               "無いので、評価範囲を入れても適用外のまま計算できる。質量の分かる行ができると、解体後の段階を"
                                               "評価範囲に入れたときは処理シナリオが要る）：材料の行を渡せない（計算しない）")
        else:
            d.skip("a_eol_route", route_v, (LABEL[route_v.state] if route_v else "未取得") +
                   "：材料の行を渡せない（材料の行ごとに必須なので計算しない）")
    if "a_eol_route" not in d.reflect:
        # no material row (every quantity 0, 適用外 or 未取得): the route has nothing to act on, but it keeps its row
        d.skip("a_eol_route", route_v, ("材料の行が無いので、処理シナリオは効かない（渡していない）" if _has(route_v) else
                                        (LABEL[route_v.state] if route_v else "未取得") +
                                        "：材料の行が無いので、いまは渡していない（材料の行を作るときは必須）"))
    for cf in ("m_waste_rate", "m_reuse_rate", "m_repair_rate", "m_refresh_cycle", "m_transport_km", "m_transport_mode",
               "m_quantity_basis", "a_eol_haul_km"):
        cv = common[cf]
        if cf == "m_transport_km" and rows and not used_tkm and fallback_rows and _has(cv) and \
                isinstance(cv.value, (int, float)) and not (_ranged(cv) and _low_end(cv) > 0):
            # the rows are carried by the per-quantity delivery factor: the distance's value is not used, but 0 km would
            # make A4 0 (round 8), so a distance that may be 0 (no stated range, or a range down to 0) can change the total
            d.use(cf, cv, "距離が 0 km でないので、数量の行は参照セットの数量あたりの配送原単位で運搬（A4）を計算した"
                          "（距離の値そのものは使わない。0 km なら A4 は 0）", [])
            continue
        if cf in ("m_transport_km", "m_transport_mode") and rows and not used_tkm:
            d.skip(cf, cv, "トンキロで計算した行が無い（配送原単位を使ったか、質量・手段がそろわない）" +
                   ("。距離の範囲は 0 km を含まないので、どの値でも配送原単位のまま（合計を変えない）"
                    if cf == "m_transport_km" and fallback_rows and _ranged(cv) and _low_end(cv) > 0 else ""))
            continue
        if cf == "m_transport_mode" and ctx["dist0"]:
            d.skip(cf, cv, "運搬距離が 0 km なので手段は効かない（A4 は 0）")
            continue
        if cf == "m_transport_mode" and dist_at0 and rows and not tkm_beyond0:
            # a 0 km whose range reaches above 0: the mode acts at the upper end only through tonne-km on a known ordered
            # mass; without such a row (m3 / m2 rows, or the ordered mass not known) no distance lets the mode act
            d.skip(cf, cv, "運搬距離が 0 km で、範囲の上端でもトンキロで運搬を計算できる行（発注量の質量が分かる行）が無いので、"
                           "手段は効かない")
            continue
        if cf == "m_refresh_cycle" and rows and cv and cv.state == "not_applicable":
            d.use(cf, cv, "適用外：更新しない（材料の更新は数えない）", ["materials[].refresh_cycle"])
            continue
        if rows and cv and (cv.state in HAS_VALUE or (cv.state == "not_applicable" and FL.FIELDS[cf]["na"] == "zero")):
            d.use(cf, cv, "材料の全部の行に共通に渡した", [FL.FIELDS[cf]["engine"][0]])
        else:
            d.skip(cf, cv, "材料の行が無い" if not rows else ((LABEL[cv.state] if cv else "未取得") + "：渡していない"))
    if rows:
        # partners that cannot act (C2 and the routes multiply the end-of-life mass; the basis matters only with offcuts;
        # ORDERED / AS_BUILT order Q whatever the waste rate, so without a row with a mass its value changes nothing)
        eol_mass = any(r_["end_of_life.mass_kg"] is not None for r_ in rows)
        if not eol_mass:
            # (a distance of 0 km as well: no distance makes C2 act without a mass; the 0 still keeps C2 complete)
            moot.append(("a_eol_haul_km", "渡したが、解体時の質量が分かる材料の行が無いので、解体材の運搬（C2）は計算できない（距離は合計を変えない）"))
            moot.append(("a_eol_route", "渡したが、解体時の質量が分かる材料の行が無いので、処理シナリオは合計を変えない"
                                        "（どの段階が不完全になるかだけを決める）"))
        # two independent rules (a rate of 0 makes the basis moot; under ORDERED / AS_BUILT — and with the basis unknown,
        # which the engine reads the same way — the rate itself, 0 and 適用外 included, is moot without a mass row or an
        # end-of-life stage): both are applied, neither hides the other
        if _surely_zero(common["m_waste_rate"]):
            moot.append(("m_quantity_basis", "渡したが、施工時の廃棄率が 0 なので、数量の基準は発注量・施工後の質量を変えない（効かない）"))
        if basis != "DESIGN" and w is not None and (not mass_rows or not st_set & {"C2", "C3", "C4"}):
            # the rate acts only through the installed mass Q(1-w) of the end-of-life stages (and what repeats them). An
            # unknown basis is passed as ordered = Q (A13-05 reads a missing basis like ORDERED): DESIGN, the only basis
            # that would let the rate act on A1-A3, is the missing partner, and the basis stays a named gap
            moot.append(("m_waste_rate", ("渡したが、数量の基準が発注・竣工で、" if basis else
                                          "渡したが、数量の基準が未取得で（エンジンは発注数量と同じに扱う。設計数量なら廃棄率は発注量に効く）、") +
                         "質量の分かる材料の行か解体の段階（C2〜C4）が無いので、廃棄率の値は合計を変えない"
                         "（エンジンは廃棄率があるときだけ発注量を求めるので、値は要る）"))
        if route_massless and mass_rows:
            # t / kg rows without an end-of-life mass (quantities that are not design quantities, the waste rate unknown):
            # the design basis would give them one, which needs the route (not given) and refuses the calculation, and the
            # engine reads ORDERED and AS_BUILT the same way (it only tests for DESIGN). No basis changes the total: the
            # route is the unknown partner (it stays the named gap of the end-of-life stages)
            moot.append(("m_quantity_basis", "渡したが、解体後の処理シナリオが%sで、設計数量にすると t・kg の行に解体時の質量が分かり"
                                             "処理シナリオが要る（計算できない）。発注数量と竣工数量はエンジンが同じに扱うので、数量の基準は"
                                             "合計を変えない（処理シナリオを入れると効く）" % route_word))
        if w is None:
            # repairs are a share of the production emission (A1-A3), which the engine cannot compute without the rate
            moot.append(("m_repair_rate", "渡したが、施工時の廃棄率が未取得で材料の A1-A3 が計算できないので、修繕率（B3）は合計を変えない"))
        if stages is not None and not any(a_ & st_set for a_ in row_stages.values()):
            # no row can change a stage in the boundary (each row says why): the inputs that every row shares cannot change
            # the total either — unless another value of the input itself would let a row act (the basis: DESIGN gives the
            # installed mass without the waste rate, ORDERED / AS_BUILT the ordered mass for tonne-km; a distance of 0 km)
            # (the distance and the mode reach a row only by tonne-km, which makes A4 act: see the 0 km rule below)
            for cf, name in (("m_refresh_cycle", "更新周期"), ("m_repair_rate", "修繕率"), ("a_eol_haul_km", "解体材の運搬距離"),
                             ("a_eol_route", "処理シナリオ"), ("m_quantity_basis", "数量の基準")):
                if not alt_acts.get(cf):
                    moot.append((cf, "渡したが、評価範囲のどの段階も計算できる材料の行が無いので（各行の理由を参照）、%sは合計を変えない"
                                     "（欠けた入力を入れると効く）" % name))
        if dist_at0 and not alt_acts["m_transport_km"]:
            # a distance of 0 km keeps A4 at 0 (and complete); it is moot when no distance would let a row compute A4: the
            # ordered mass needs the waste rate under DESIGN, and the delivery factor needs it whatever the basis (also
            # for a 0 whose range reaches above 0: no end of the range can then change A4)
            moot.append(("m_transport_km", "渡したが、0 km 以外の距離でも運搬（A4）を計算できる材料の行が無いので（発注量が決まらない）、"
                                           "距離は合計を変えない（A4 は 0 のまま）"))

    # ------------------------------------------------------------------ construction (site)
    if _unknown(V("c_site_electricity")) and _surely_zero(V("o_grid_construction")):
        # the construction electricity factor is 0: the quantity cannot change A5 (filled, not an observation)
        d.item("construction", "construction.electricity_kwh", 0.0)
        d.state("construction", "electricity_kwh", "EXPLICIT_ZERO")
        d.skip("c_site_electricity", V("c_site_electricity"), "工事中の電力の排出係数が 0 なので量は効かない：0 で満たした（計算には入らない）")
    else:
        scalar("c_site_electricity", "construction", "construction.electricity_kwh", "construction", "electricity_kwh")
        if _unknown(V("c_site_electricity")):
            missing("c_site_electricity", ("A5",), "工事中の電力が未取得")
        elif _surely_zero(V("o_grid_construction")) and d.reflect.get("c_site_electricity", {}).get("reflected"):
            r_ = d.reflect["c_site_electricity"]
            r_["reflected"] = False
            r_.setdefault("reasons", []).append("渡したが、工事中の電力の排出係数が 0 なので A5 は変わらない")
    if _unknown(V("c_site_electricity")):
        # the quantity is the gap: the factor multiplies nothing until it is known. A factor of 0 makes the quantity moot
        # (filled with 0 above) and the unknown quantity makes the factor moot: each makes the other moot, neither counts
        moot.append(("o_grid_construction",
                     "渡したが、工事中の電力が未取得なので、係数の値は合計を変えない（係数が 0 なので工事中の電力は 0 で満たし、"
                     "A5 の電力の分は 0 のまま。0 でない係数なら工事中の電力が要る）" if _surely_zero(V("o_grid_construction")) else
                     "渡したが、工事中の電力が未取得なので A5 の電力の分は計算できない（係数は合計を変えない）"))
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
            rx_, rst_, _ = _num(rr)
            ph_states = {}
            ph_repair = 0.0 if rx_ == "NA" else (float(rx_) if isinstance(rx_, (int, float)) else None)
            if ph_repair is not None:
                ph_states["repair_rate"] = "EXPLICIT_ZERO" if rx_ == "NA" else rst_
            mass0 = _surely_zero(mv)                 # 0 kg per unit: the end-of-life mass is 0 whatever the count
            if mass0:
                ph_states["end_of_life_mass_kg"] = "EXPLICIT_ZERO"
            eq_rows.append({"equipment_id": "E-" + trade, "trade": trade, "model": None, "quantity": None, "quantity_unit": "unit",
                            "factor_id": ids["factor"], "eol_factor_id": ids["eol"], "delivery_factor_id": ids["delivery"],
                            "installation_factor_id": ids["install"], "replacement_event_list": None, "service_life": None,
                            "end_of_life_mass_kg": 0.0 if mass0 else None, "repair_rate": ph_repair, "provenance_id": _prov(None),
                            "states": ph_states})
            missing("e_%s_count" % t, EQUIPMENT_STAGES, "%s機器の台数が未取得（本当に無いと分かっているときだけ「適用外」）" % tl, kind="equipment",
                    ctx_over={"b4_equipment": renew.get(trade, True), "zero": ("C3",) if mass0 else ()})
            eq_gap_renew.append(renew.get(trade, True))
            # the other inputs of this row that its stages need as well, named at once (as the refrigerant parts of B1):
            # the life for B4 (unknown: a renewal can fall inside T) and the mass for C3 (and B4 / B5 by the expansion),
            # by the same tests as with a count. The stages stay as the count marks them; only the named inputs grow
            if _num(lv)[0] is None:
                missing("e_%s_life" % t, ("B4",), "%s機器の耐用年数が%s（台数を入れても、耐用年数が無いと交換を数えられない）"
                        % (tl, _gap_word(lv)), kind="equipment")
            if not mass0 and not isinstance(_num(mv)[0], float):
                missing("e_%s_mass" % t, ("C3",), "%s機器 1 台の解体時質量が%s（台数を入れても、質量が無いと解体時の処理（C3）を"
                        "計算できない）" % (tl, _gap_word(mv)), kind="equipment", ctx_over={"b4_equipment": renew.get(trade, True)})
            d.skip("e_%s_count" % t, cv, how + "：台数の欠けた設備の行を渡した（エンジンが不完全とする。この設備は合計に入っていない）")
            d.skip("e_%s_life" % t, lv, "台数が無いので渡していない")
            d.skip("e_%s_mass" % t, mv, "1 台の質量 0 を台数の欠けた仮の行に渡した（台数が無いので計算には入らない）" if mass0
                   else "台数が無いので渡していない")
            continue
        states = {"quantity": st}
        zero = _surely_zero(cv)                      # a confirmed zero count: lives, masses and repair do not matter
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
            missing("e_%s_life" % t, ("B4",), "%s機器の耐用年数が未取得（エンジンは交換を数えないが、不完全とは示さない）" % tl,
                    kind="equipment")
            ex_, _, _ = _num(rr)
            if isinstance(ex_, (int, float)) and ex_ > 0:   # a repair rate of 0 or 適用外: the life cannot change B3
                missing("e_life@B3", ("B3",), "設備の耐用年数が未取得：交換の年の修繕を除けないので、B3 は多めになりうる（合計には入っている）",
                        label="設備の耐用年数（修繕 B3 への影響）", gap="assumed")
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
                missing("e_%s_mass" % t, ("C3",), "%s機器 1 台の解体時質量が%s" % (tl, LABEL[mv.state] if mv else "未取得"), kind="equipment",
                        ctx_over={"b4_equipment": renew.get(trade, True)})
                eq_gap_renew.append(renew.get(trade, True))
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
    ctx["b4_equipment_gap"] = any(eq_gap_renew)
    if eq_rows:
        d.tables["equipment"]["equipment"] = eq_rows
        if rr and (rr.state in HAS_VALUE or rr.state == "not_applicable") and any(r["quantity"] is not None for r in eq_rows):
            d.use("e_repair_rate", rr, "設備の全部の行に共通に渡した", ["equipment[].repair_rate"])
        elif rr and (rr.state in HAS_VALUE or rr.state == "not_applicable"):
            d.skip("e_repair_rate", rr, "台数の欠けた仮の行に渡した（台数のある設備の行が無いので計算には入らない）")
        else:
            d.skip("e_repair_rate", rr, "未取得：渡していない")
    else:
        d.skip("e_repair_rate", rr, "設備の行が無い")

    # ------------------------------------------------------------------ refrigerants
    cv = V("r_charge_kg")
    x, st, how = _num(cv)
    rparts = [k for k, F in FL.FIELDS.items() if F["role"] == "refrigerant" and k != "r_charge_kg"]
    gwp0 = _surely_zero(V("r_gwp"))
    # no replacement inside T: 適用外 (交換しない), or a life whose stated range does not reach below T
    no_repl = not _inside(V("r_life"), period)
    # nothing leaks, nothing is lost at a replacement (or none falls inside T) and everything is recovered at the end:
    # B1 is 0 whatever the charge and the GWP
    b1_zero = _surely_zero(V("r_leak_rate")) and (_surely_zero(V("r_loss_rate")) or no_repl) and \
        _surely_one(V("r_recovery_rate"))

    def b1_blocked(over: str | None) -> list:
        """Why B1 cannot be computed and non-zero with the refrigerant inputs as they are, `over` (one of them) taken at a
        value that acts ([] = it can). The engine computes B1 of a device only with its charge, its GWP and its leak rate
        (and the bridge passes the charge only with the top-up known when something may leak); then B1-02 needs a leak,
        B1-03 a known loss rate and a replacement inside T (a known life whose low end is below T), B1-04 a known
        recovery rate below 100 %. A value that makes B1 0 counts only when this is [] for it: when its partner is
        unknown (or also makes B1 0), no value of it can change the total."""
        why = []
        cv_, gv_, lv_, tv_ = V("r_charge_kg"), V("r_gwp"), V("r_leak_rate"), V("r_top_up")
        if over != "r_charge_kg":
            if cv_ is not None and cv_.state == "not_applicable":
                why.append("冷媒を使う機器が無い（充填量が適用外）")
            elif _unknown(cv_):
                why.append("冷媒の充填量が%s" % (LABEL[cv_.state] if cv_ else "未取得"))
            elif _surely_zero(cv_):
                why.append("冷媒の充填量が 0")
        if over != "r_gwp":
            if _never("r_gwp", gv_):
                why.append("冷媒の GWP が%s" % ("未取得" if gv_ is None else
                                               "適用外（0 にできない項目）" if gv_.state == "not_applicable" else LABEL[gv_.state]))
            elif _surely_zero(gv_):
                why.append("冷媒の GWP が 0")
        leak_may = over == "r_leak_rate" or not _surely_zero(lv_)
        if over != "r_leak_rate" and _unknown(lv_):
            why.append("年あたりの漏えい率が%s" % (LABEL[lv_.state] if lv_ else "未取得"))
        elif leak_may and over != "r_top_up" and _unknown(tv_):
            why.append("漏えい分の補充の有無が%s（漏えいがあると B1 は計算しない）" % (LABEL[tv_.state] if tv_ else "未取得"))
        if why:
            return why
        lf_, ls_, rc_ = V("r_life"), V("r_loss_rate"), V("r_recovery_rate")
        lfx_, _, _ = _num(lf_)
        events = over == "r_life" or (isinstance(lfx_, (int, float)) and _inside(lf_, period))
        loss_may = over == "r_loss_rate" or (_num(ls_)[0] is not None and not _surely_zero(ls_))
        rec_may = over == "r_recovery_rate" or (isinstance(_num(rc_)[0], (int, float)) and not _surely_one(rc_))
        if leak_may or (events and loss_may) or rec_may:
            return []
        b13 = ("冷媒機器の交換周期が%s" % (LABEL[lf_.state] if lf_ else "未取得") if _unknown(lf_) else
               "交換しない" if lfx_ == "NA" else "評価期間内に交換なし") if not events else \
            ("交換時の損失率が%s" % (LABEL[ls_.state] if ls_ else "未取得") if _unknown(ls_) else "交換時の損失 0")
        b14 = "回収率 100%" if _surely_one(rc_) else "廃棄時の回収率が%s" % (
            "適用外（0 にできない項目）" if rc_ is not None and rc_.state == "not_applicable" else (LABEL[rc_.state] if rc_ else "未取得"))
        return ["漏えい 0・%s・%s（B1 の漏えい・交換時の損失・廃棄時の回収の分がどれも 0 か計算できない）" % (b13, b14)]

    def b1_decides(k, how):
        """A refrigerant value that makes B1 0 (no row): reflected as the reason, but not counted when no other value of it
        could let B1 be computed and non-zero (the partner it multiplies is unknown, or another input makes B1 0 too)."""
        d.use(k, V(k), how, ["refrigerants"])
        why_ = b1_blocked(k)
        if why_:
            moot.append((k, "渡したが、%sなので、この値を変えても B1 は 0 か計算できないまま（%sの値は合計を変えない）"
                         % ("。".join(why_), FL.FIELDS[k]["label"])))

    if x == "NA" or _surely_zero(cv) or gwp0 or b1_zero:
        d.tables["equipment"]["refrigerants"] = []
        if b1_zero and not (x == "NA" or _surely_zero(cv) or gwp0):
            why0 = "漏えい 0・交換時の損失 0（または評価期間内に交換なし）・回収率 100% なので B1 は 0"
            # the replacement loss is 0 because the rate is 0 or because no replacement falls inside T: when both hold,
            # neither the rate nor the life can change B1 alone (as in the row branch below), so neither decides
            loss0_ = _surely_zero(V("r_loss_rate"))
            deciding = {"r_leak_rate", "r_recovery_rate"} | ({"r_loss_rate"} if loss0_ and not no_repl else set()) | \
                ({"r_life"} if no_repl and not loss0_ else set())
            for k in ["r_charge_kg"] + rparts:
                if k in deciding:
                    b1_decides(k, why0 + "（冷媒の行は作らない）")
                else:
                    d.skip(k, V(k), why0 + "：使われない")
        elif gwp0 and not (x == "NA" or _surely_zero(cv)):
            d.skip("r_charge_kg", cv, "冷媒の GWP が 0 なので、充填量・漏えいは B1 に効かない（冷媒の行は作らない）")
            # with B1 0 for another reason as well (two reasons, each enough by itself), or with the charge, the leak rate
            # or the top-up unknown, no GWP can change the total (b1_blocked names which)
            b1_decides("r_gwp", "GWP 0：冷媒の行は作らない（B1 は 0）")
            for k in rparts:
                if k != "r_gwp":
                    d.skip(k, V(k), "GWP が 0 なので使われない")
        elif x == "NA":
            d.use("r_charge_kg", cv, "適用外：冷媒を使う機器なし", ["refrigerants"])
            for k in rparts:
                d.skip(k, V(k), "冷媒が無い（適用外・充填量 0）ので使われない")
        else:
            b1_decides("r_charge_kg", "充填量 0：冷媒の行は作らない")
            for k in rparts:
                d.skip(k, V(k), "冷媒が無い（適用外・充填量 0）ので使われない")
    else:
        row = {"device_id": "R-1", "substance": None, "application": "AIR_CONDITIONING",
               "charge_mass_kg": float(x) if x is not None else None, "change_years": None,
               "provenance_id": _prov(st)}
        rzero = False                                         # (a charge surely 0 makes no row above)
        leak0 = _surely_zero(V("r_leak_rate"))               # nothing leaks: whether leaks are topped up cannot matter
        # a replacement (and its loss) happens inside T only with a life (the low end of its range) shorter than T, or
        # an unknown life
        ctx["b1_replacement"] = _inside(V("r_life"), period)
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
                elif rzero or leak0:
                    row["top_up"] = False
                    d.skip(k, kv, "漏えい率が 0 なので、補充の有無は B1 に効かない（補充しないとして渡した）")
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
                if k == "r_life" and _surely_zero(V("r_loss_rate")) and \
                        (_surely_zero(V("r_leak_rate")) or (_has(V("r_top_up")) and V("r_top_up").value == "yes")):
                    moot.append(("r_life", "渡したが、交換時の損失が 0 なので交換周期は B1 に効かない"))
                if k == "r_loss_rate" and not ctx["b1_replacement"]:
                    moot.append(("r_loss_rate", "渡したが、評価期間内に冷媒機器の交換が無いので損失率は B1 に効かない"))
                elif k == "r_loss_rate" and _unknown(V("r_life")):
                    # the symmetric case of the life with the loss rate unknown (below): without a life the engine counts
                    # no replacement, so no loss rate can change B1; the life stays the named gap
                    moot.append(("r_loss_rate", "渡したが、冷媒機器の交換周期が未取得なので B1 の交換の分は計算できない（損失率は合計を変えない）"))
            else:
                row[F["part"]] = None
                life_moot = k == "r_life" and _surely_zero(V("r_loss_rate")) and \
                    (_surely_zero(V("r_leak_rate")) or (_has(V("r_top_up")) and V("r_top_up").value == "yes"))
                if life_moot:
                    ctx["b1_replacement"] = False      # the engine's B1-03 mark cannot act either
                # (also with the charge unknown: B1 needs every part, so the hint names all of them at once instead of
                # one more after each input)
                if not rzero and not life_moot and not (k == "r_loss_rate" and not ctx["b1_replacement"]):
                    missing(k, ("B1",), "%sが%s" % (F["label"], "適用外（0 にできない項目）" if kx == "NA" else khow))
                elif life_moot or (k == "r_loss_rate" and not ctx["b1_replacement"]):
                    d.skip(k, kv, ("適用外（0 にできない項目）" if kx == "NA" else khow) + "：効かない（%s）"
                           % ("交換時の損失が 0" if life_moot else "評価期間内に交換が無い"))
                    continue
                d.skip(k, kv, ("適用外（0 にできない項目）" if kx == "NA" else khow) + "：渡していない（B1 のこの部分は不完全）")
        # the engine computes B1 of a device only with its charge, its GWP and its leak rate (B1-02/03/04 all need them):
        # without one of them none of the refrigerant inputs reaches a result
        off = ("充填量を渡していない" if row["charge_mass_kg"] is None else
               "冷媒の GWP を渡していない" if row.get("gwp") is None else
               "年あたりの漏えい率を渡していない" if row.get("annual_leak_rate") is None else None)
        if off:
            for k in ["r_charge_kg"] + rparts:
                r_ = d.reflect.get(k)
                if r_ and r_["reflected"]:
                    r_["reflected"] = False
                    r_["how"] = []
                    r_.setdefault("reasons", []).append("%sなので B1 は計算していない（使われない）" % off)
        else:
            if row.get("replacement_loss_rate") is None and (leak0 or row.get("top_up") is True):
                # the loss rate is the gap: with nothing leaking (or leaks topped up) the life acts only through the loss
                # at a replacement, which the engine cannot compute without the rate — also when no replacement falls
                # inside T now (a shorter life would place one, and still without a loss rate). With no replacement the
                # loss rate is not a gap either: each makes the other moot, neither counts
                moot.append(("r_life", "渡したが、交換時の損失率が未取得なので B1 の交換の分は計算できない（周期は合計を変えない。"
                                       "損失率が要るかどうかだけを決める）"))
            if leak0 and _has(V("r_top_up")):
                moot.append(("r_top_up", "渡したが、漏えい率が 0 なので、補充の有無は B1 に効かない"))
            # B1-02 needs a leak, B1-03 a known loss at a replacement inside T (a known life), B1-04 a known recovery below
            # 100 %: when none can act (the rest is 0 or a gap), the charge and the GWP cannot change the total
            b1_now = b1_blocked(None)
            if b1_now:
                for k in ("r_charge_kg", "r_gwp"):
                    moot.append((k, "渡したが、%sなので、B1 は合計を変えない" % "。".join(b1_now)))
                if leak0 and _unknown(V("r_top_up")):
                    # a leak would make the bridge drop B1 (the top-up is unknown): B1 stays 0 or omitted, so no leak rate
                    # can change the total either
                    moot.append(("r_leak_rate", "渡したが、漏えい分の補充の有無が未取得なので、漏えいがあると B1 は計算しない。%sなので、"
                                                "漏えい率の値は合計を変えない" % "。".join(b1_now)))
        row["states"] = states
        for s in states.values():
            d.used_states.add("OBSERVED" if s == "EXPLICIT_ZERO" else s)
        d.tables["equipment"]["refrigerants"] = [row]

    # ------------------------------------------------------------------ operation and water
    # The engine reads operation.electricity as CONSUMPTION and nets it: purchase = max(0, c − (generation − export)).
    # The screen asks for PURCHASED electricity (the bills already exclude self-consumed generation). So:
    #  - generation and export both known and consistent: c = purchase + self-consumption max(0, g − x) (else the
    #    self-consumed part would be subtracted twice); the engine then gets back exactly the purchase;
    #  - otherwise, with the purchase known: generation and export cannot change B6/B2 (the purchase is what the bills
    #    say) → c = purchase, generation = export = 0 (filled, they do not act); unknown generation never drops B6;
    #  - purchase unknown: B6/B2 electricity cannot be computed whatever generation is (the purchase is the gap).
    pe, pe_st, _ = _num(V("o_elec_kwh"))
    g_, g_st, _ = _num(V("o_pv_kwh"))
    x_, x_st, _ = _num(V("o_export_kwh"))
    g0 = 0.0 if g_ == "NA" else g_
    x0 = 0.0 if x_ == "NA" else x_
    gx_known = isinstance(g0, (int, float)) and isinstance(x0, (int, float))
    pe_known = pe == "NA" or isinstance(pe, (int, float))
    inconsistent = gx_known and x0 > g0
    if inconsistent:
        d.inconsistent.append("自家発電のうち外へ売った電力（%s kWh/年）が自家発電（%s kWh/年）より多い：入力が矛盾している。%s"
                              % (x0, g0, "購入電力が分かっているので計算には効かない（購入電力をそのまま使った）" if pe_known
                                 else "購入電力も未取得"))
    elec_override, pv_fill = None, None
    grid0 = _surely_zero(V("o_grid_value"))              # a factor of 0: the purchase cannot change B6/B2 either
    if pe_known and gx_known and not inconsistent:
        selfc = max(0.0, g0 - x0)
        if isinstance(pe, (int, float)):
            # the consumption passed is derived (purchase + self-consumption); the engine's purchase comes back exactly
            # as the bills say, so PV / export are not counted as estimates that move the total (see the reflection)
            elec_override = (float(pe) + selfc, _derived(pe_st, g_st, x_st) if selfc > 0 else pe_st,
                             "購入電力 %s ＋ 自家消費 %s ＝ 電力の使用量 %s kWh/年として渡した" % (pe, selfc, float(pe) + selfc))
    elif pe_known or grid0:
        pv_fill = ("購入電力が分かっているので、自家発電・売電は B6・B2 に効かない（エンジンの買電量＝購入電力）："
                   "0 で満たした（計算には入らない）") if pe_known else \
            "運用時の電力の排出係数が 0 なので、自家発電・売電は B6・B2 に効かない：0 で満たした（計算には入らない）"
    # net purchased electricity surely 0, or a grid factor of 0 → the factor / the purchase / the share cannot act
    pe_zero = _surely_zero(V("o_elec_kwh"))
    ctx["b2_moot"] = pe_zero or grid0
    if pe is None:
        # the purchase is the gap: the factor multiplies nothing until it is known. A factor of 0 makes the purchase moot
        # (filled with 0 below) and the unknown purchase makes the factor moot: each makes the other moot, neither counts
        moot.append(("o_grid_value",
                     "渡したが、購入電力が未取得なので、係数の値は合計を変えない（係数が 0 なので購入電力は 0 で満たし、"
                     "電力の B6・B2 は 0 のまま。0 でない係数なら購入電力が要る）" if grid0 else
                     "渡したが、購入電力が未取得なので電力の B6・B2 は計算できない（係数は合計を変えない）"))
    for fid, F in FL.FIELDS.items():
        if F["role"] != "profile":
            continue
        v = V(fid)
        x, st, how = _num(v)
        if fid == "o_elec_kwh" and elec_override is not None and x not in (None, "NA"):
            x, st, how = elec_override
        if fid in ("o_pv_kwh", "o_export_kwh"):
            if pv_fill:
                d.item("operation", F["profile"] + ".kind", "CONSTANT")
                d.item("operation", F["profile"] + ".unit", PROFILE_UNIT[F["profile"]])
                d.item("operation", F["profile"] + ".base", 0.0)
                d.state("operation", F["profile"].split(".", 1)[1], "EXPLICIT_ZERO")
                d.skip(fid, v, pv_fill)
                continue
            if x is None:
                # never a gap of its own: with the purchase unknown the purchase is the gap (B6/B2 are flagged by it)
                d.skip(fid, v, how + "：渡していない（購入電力が未取得なので、どちらにしても電力の B6・B2 は計算できない）")
                continue
        name = F["profile"]
        stage = "B7" if name.startswith("water_waste") else "B6"
        cat, owner = "operation", name.split(".")[0]
        if x == "NA":
            x, st, how = 0.0, "EXPLICIT_ZERO", "適用外：0 として渡した（明示のゼロ）"
        filled = False
        if fid == "o_elec_kwh" and x is None and grid0:
            x, st, how = 0.0, "EXPLICIT_ZERO", "運用時の電力の排出係数が 0 なので、購入電力は B6・B2 に効かない：0 で満たした（計算には入らない）"
            filled = True
        if x is None and F["required"] and stages is not None and stage not in st_set:
            x, st, how = 0.0, "EXPLICIT_ZERO", "%s を評価範囲から外したので、エンジンの必須の年表を 0 で満たした（計算には入らない）" % stage
            filled = True
        if x is None:
            if F["required"]:
                d.missing.append(F["label"])
            else:
                missing(fid, (stage,) + (("B2",) if fid == "o_elec_kwh" and not _surely_zero(V("o_fm_ratio")) else ()),
                        "%sが未取得（本当に無いと分かっているときだけ「適用外」）" % F["label"])
            d.skip(fid, v, how + "：渡していない（%s のこの部分は合計に入らない）" % stage)
            continue
        d.item(cat, name + ".kind", "CONSTANT")
        d.item(cat, name + ".unit", PROFILE_UNIT[name])
        d.item(cat, name + ".base", float(x))
        d.state(owner, name.split(".", 1)[1], st)
        if filled:
            d.skip(fid, v, how)
        elif fid == "o_elec_kwh" and grid0:
            d.skip(fid, v, how + "：渡したが、運用時の電力の排出係数が 0 なので B6・B2 は変わらない")
        elif fid in ("o_pv_kwh", "o_export_kwh") and not pe_known:
            d.skip(fid, v, how + "：渡したが、購入電力が未取得なので電力の B6・B2 は計算できない（効かない）")
        elif fid in ("o_pv_kwh", "o_export_kwh") and pe_known:
            # passed (the self-consumed part is added to the consumption) but the total does not depend on it
            d.skip(fid, v, how + "：渡したが、購入電力が B6・B2 を決めるので合計は変わらない（自家消費の分を使用量に足しただけ）")
        else:
            d.use(fid, v, how + "・年ごとに一定", [name])
    for name, fid in P["op"].items():
        d.item("operation", "operation.%s_factor_id" % name, fid)
    for name, fid in P["water"].items():
        d.item("operation", "water_waste.%s_factor_id" % ("waste" if name == "municipal_waste" else name), fid)
    scalar("o_fm_ratio", "operation", "operation.facility_management_ratio")
    if _unknown(V("o_fm_ratio")) and not ctx["b2_moot"]:
        # the engine then counts the whole purchase in B6 and 0 in B2: the total is right, the split is not determined
        missing("o_fm_ratio", ("B2", "B6"), "施設管理（B2）分の割合が未取得：B2 の分は B6 に入っている（合計は変わらない。B2 と B6 の内訳が決まらない）",
                gap="split")
    scalar("o_source", "operation", "operation.energy_simulation_basis")
    gv, gc = V("o_grid_value"), V("o_grid_construction")
    gx, gst, ghow = _num(gv)
    g_filled = False
    g_open = False             # a stored 適用外 that some boundary would accept, with the boundary unknown (below)
    if gx in (None, "NA") and stages is not None and not st_set & {"B6", "B2"}:
        gx, gst, ghow = 0.0, "EXPLICIT_ZERO", "B6・B2 を評価範囲から外したので、必須の年表を 0 で満たした（計算には入らない）"
        g_filled = True
    elif gx in (None, "NA") and ctx["b2_moot"]:
        gx, gst, ghow = 0.0, "EXPLICIT_ZERO", "購入電力が 0 なので係数は効かない：必須の年表を 0 で満たした（計算には入らない）"
        g_filled = True
        # (b2_moot is the purchase here: a factor of 0 is not 未取得 / 適用外) the mirror of the factor 0 with the purchase
        # unknown: every purchase other than 0 needs the factor, which is not given (the calculation is refused), so the
        # purchase of 0 cannot change the total either: neither counts
        moot.append(("o_elec_kwh", "渡したが、運用時の電力の排出係数が%sなので、0 でない購入電力では計算できない（係数が要る）。"
                                   "購入電力 0 は合計を変えない（係数を入れると効く）" % (LABEL[gv.state] if gv else "未取得")))
    elif gx in (None, "NA") and pe is None:
        # the purchase is the gap as well: the factor cannot act until it is known (the moot rule above), so the required
        # table is filled like for a purchase of 0; both stay named gaps, and B6 / B2 stay incomplete (a lower bound).
        # 適用外 is accepted here (it cannot act), so it is not described as a value that cannot be 適用外
        missing("o_grid_value", ("B6",) + (("B2",) if not _surely_zero(V("o_fm_ratio")) else ()),
                "運用時の電力の排出係数が%s" % (
                    "適用外（購入電力も未取得：購入電力が 0・適用外でなければ係数が要る）" if gx == "NA" else
                    "%s（購入電力も未取得：電力の B6・B2 には両方が要る）" % (LABEL[gv.state] if gv else "未取得")))
        gx, gst, ghow = 0.0, "EXPLICIT_ZERO", "購入電力が未取得なので係数は効かない：必須の年表を 0 で満たした（計算には入らない）"
        g_filled = True
    if gx == "NA":
        # 適用外 is filled (it cannot act) when B6 / B2 are outside the boundary, the purchase is 0 / 適用外 or the purchase is
        # unknown (above); here the purchase may be above 0, so the factor is needed
        gx = None
        why_ = ("購入電力%sので、電力の B6・B2 に係数が要る。購入電力が 0・適用外のときや、B6・B2 を評価範囲から外したときは"
                "適用外にできる" % ("の範囲が 0 より上に届く" if pe == 0 else "がある"))
        if stages is not None:
            d.na_refused["o_grid_value"] = why_
            ghow = "適用外にはできない（%s）" % why_
        else:
            # the boundary is not given (the calculation stops for it anyway): the 適用外 is usable when B6 / B2 are left out
            ghow = "評価範囲が未取得なので、この適用外が使えるかは評価範囲で決まる（%s）" % why_
            # a boundary the screen offers leaves them out: then not a missing required input (the boundary is one,
            # and its row says on what it depends)
            g_open = _open_without(("B6", "B2"))
    if gx is None:
        if not g_open:
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
        elif pe_zero:
            d.skip("o_grid_value", gv, ghow + "：渡したが、購入電力が 0 なので B6・B2 は変わらない")
        else:
            d.use("o_grid_value", gv, ghow + "・評価期間中一定", ["operation.grid"])
    cx, cst, chow = _num(gc)
    c_filled = False
    if cx in (None, "NA") and stages is not None and "A5" not in st_set:
        cx, cst, chow = 0.0, "EXPLICIT_ZERO", "A5 を評価範囲から外したので 0 で満たした（計算には入らない）"
        c_filled = True
    elif cx in (None, "NA") and _surely_zero(V("c_site_electricity")):
        cx, cst, chow = 0.0, "EXPLICIT_ZERO", "工事中の電力が 0 なので係数は効かない：0 で満たした（計算には入らない）"
        c_filled = True
        # the mirror of the factor 0 with the site electricity unknown: every site electricity other than 0 needs the
        # factor, which is not given (the calculation is refused), so the 0 cannot change the total either
        moot.append(("c_site_electricity", "渡したが、工事中の電力の排出係数が%sなので、0 でない工事中の電力では計算できない（係数が要る）。"
                                           "工事中の電力 0 は合計を変えない（係数を入れると効く）" % (LABEL[gc.state] if gc else "未取得")))
    elif cx in (None, "NA") and _unknown(V("c_site_electricity")):
        # the site electricity is the gap as well: filled like for a site electricity of 0; both stay named gaps of A5
        missing("o_grid_construction", ("A5",), "工事中の電力の排出係数が%s" % (
            "適用外（工事中の電力も未取得：工事中の電力が 0・適用外でなければ係数が要る）" if cx == "NA" else
            "%s（工事中の電力も未取得：A5 の電力の分には両方が要る）" % (LABEL[gc.state] if gc else "未取得")))
        cx, cst, chow = 0.0, "EXPLICIT_ZERO", "工事中の電力が未取得なので係数は効かない：0 で満たした（計算には入らない）"
        c_filled = True
    if cx in (None, "NA"):
        if cx == "NA":
            # filled above when A5 is outside the boundary or the site electricity is 0 / 適用外 / unknown; here it may be
            # above 0, so the factor is needed
            elec_ = "の範囲が 0 より上に届く" if _num(V("c_site_electricity"))[0] == 0 else "がある"
            why_ = ("工事中の電力%sので、A5 の電力の分に係数が要る。工事中の電力が 0・適用外のときや、A5 を評価範囲から外したときは"
                    "適用外にできる" % elec_)
            if stages is not None:
                d.na_refused["o_grid_construction"] = why_
                chow = "適用外にはできない（%s）" % why_
            else:
                # the boundary is not given (the calculation stops for it anyway). Every boundary the screen offers has A5,
                # so once it is set this 適用外 is refused unless the site electricity is 0, 適用外 or unknown (each filled
                # above): said as what setting it does. No boundary the screen offers would accept it, so it stays a
                # missing required input (_open_without)
                chow = ("評価範囲が未取得なので、この適用外はまだ判定していない（工事中の電力%sので、評価範囲を入れると A5 の電力の分に"
                        "係数が要る。A5 はどの評価範囲にもあるので、工事中の電力が 0・適用外・未取得のときだけ適用外にできる）" % elec_)
        if not (cx == "NA" and stages is None and _open_without(("A5",))):
            d.missing.append(FL.FIELDS["o_grid_construction"]["label"])
        d.skip("o_grid_construction", gc, chow + "：渡していない")
    else:
        d.item("assessment", "operation.grid.construction_value", float(cx))
        if c_filled:
            d.skip("o_grid_construction", gc, chow)
        elif _surely_zero(V("c_site_electricity")):
            d.skip("o_grid_construction", gc, chow + "：渡したが、工事中の電力が 0 なので A5 は変わらない")
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
    # passed values that cannot change the total: a partner that is surely 0, or every stage they reach is outside the
    # boundary — not counted as reflected, as estimates, or as widths of the range
    for fid_, why_ in moot:
        r_ = d.reflect.get(fid_)
        if r_ and r_["reflected"]:
            r_["reflected"] = False
            r_.setdefault("reasons", []).append(why_)
    # a life or a cycle whose stated range lies entirely at or above T: no value of its range places an event inside the
    # study period, so it cannot change the total (not moved by the range, not counted). A value WITHOUT a stated range
    # keeps counting: its unknown range may reach below T. (Its partners are already judged by the low end: _inside.)
    if period is not None:
        for fid_ in EVENT_FIELDS:
            v_, r_ = V(fid_), d.reflect.get(fid_)
            if r_ and r_["reflected"] and _ranged(v_) and not _inside(v_, period):
                r_["reflected"] = False
                r_.setdefault("reasons", []).append(
                    "渡したが、範囲（%g〜%g 年）の下端も評価期間（%g 年）以上なので、範囲のどの値でも評価期間の内に交換・更新は起きない"
                    "（合計を変えない）" % (float(v_.uncertainty.low), float(v_.uncertainty.high), float(period)))
    if stages is not None:
        for fid_, r_ in d.reflect.items():
            reach = FIELD_REACH.get(fid_)
            if r_["reflected"] and reach and not set(reach) & st_set:
                r_["reflected"] = False
                r_.setdefault("reasons", []).append("渡したが、効く段階（%s）が評価範囲の外なので合計は変わらない" % "・".join(reach))
    neutral = TOTAL_NEUTRAL                 # cannot change the total (the split, per-area values, …)
    for fid_ in neutral:
        r_ = d.reflect.get(fid_)
        if r_ and r_["reflected"] and r_["state"] in ("statistical", "assumption"):
            r_["how"].append("合計は変えない入力なので、推定の数・範囲には数えない")
    by_state = {}
    for r in d.reflect.values():
        if r["reflected"]:
            by_state[r["state"]] = by_state.get(r["state"], 0) + 1
    n_est = sum(1 for r in d.reflect.values() if r["reflected"] and r["state"] in ("statistical", "assumption")
                and r["field"] not in neutral)
    n_ref = sum(by_state.values())
    omitted = [m for m in missing_inputs if m.get("gap") == "omitted"]
    # stages with something left out (the total is short there) and stages computed partly with an assumption
    incomplete_stages = sorted({s for m in omitted for s in m["stages"]})
    assumed_stages = sorted({s for m in missing_inputs if m.get("gap") == "assumed" for s in m["stages"]})
    split_stages = sorted({s for m in missing_inputs if m.get("gap") == "split" for s in m["stages"]})
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
        "split_stages": split_stages,
        "inconsistent_inputs": d.inconsistent,
        "na_refused": d.na_refused,
        "unconnected": d.unconnected,
        "notes": d.assumed,
        "double_count": d.double_count,
        "stages": stages,
        "summary": ("計算に入った %d 項目のうち、統計推定・仮定が %d 項目。" % (n_ref, n_est)
                    + ("推定の割合が大きいので、合計は目安として読む。" if n_ref and n_est / n_ref > 0.3 else "")),
        "input_hash": input_hash(doc, values),
    }
    return doc, report


def _range_key(v) -> list:
    """The stated range of a value (it decides the range shown with the result, and which partners can act)."""
    u = getattr(v, "uncertainty", None)
    return [u.kind, u.low, u.high] if u is not None else []


def input_hash(doc: dict, values: dict | None = None) -> str:
    """Fingerprint of the inputs: the engine document without the assessment date (today's date would make every result
    look stale the next day), plus the state, value, unit, scope and stated range of every field (a change from 適用外 to
    未取得 can leave the document identical and still change what is missing; a new range changes the range shown) —
    for a record-only field its state only (its value is used by nothing that the result shows).
    The document depends on the study period (a renewal or a refrigerant replacement inside T or not), so a result is
    compared with a document built for the period of that result."""
    d = json.loads(json.dumps(doc))
    for c in d["categories"].values():
        c["items"].pop("project.assessment_date", None)
    # the value of a record-only field (building name, address, notes) reaches neither the engine, nor the report, nor
    # the range: editing it does not make a result stale. Its state stays in (it is shown in the reflection table)
    fields = sorted((k, v.state, json.dumps(None if FL.FIELDS.get(k, {}).get("role") == "record" else v.value,
                                            ensure_ascii=False, default=str), v.unit, getattr(v, "scope", ""),
                     json.dumps(_range_key(v), default=str))
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
    lines += ["| 基礎の形式（`g_foundation`） | エンジンは `project.foundation_system` を読まない（記録のみ）。統計の概算の場合分けの説明に使う。推定の数・範囲には数えない |",
              "| 主な用途・構造・新築既存・運用データの種類（`b_use`・`b_structure`・`b_project_type`・`o_source`） | エンジンへは渡すが、"
              "合計を読む単位が無い（どの選択肢でも合計は同じ）。用途は延床面積と組み合わせて用途別面積（必須の入力）になり、用途・構造は統計の概算の"
              "前提に使う。推定の数・範囲には数えない |",
              "", "## 4. 値によっては計算に入らない場合", "",
              "- 未取得・計算不能の項目：渡さない（欠損のまま。0 にしない）。材料・設備が未取得なら、その行が無いので合計に入らない（結果に「少なめ（下限）」と出る）。",
              "- 数量の単位が参照セットの原単位と合わない材料（例：m3 の原単位しか無いのに m2）：行を作らない。",
              "- 数量が m3・m2 の材料：質量が分からないので（密度を仮定しない）、解体時の運搬・処理（C2〜C4）のその行は不完全。",
              "- 統計の全体量（基礎を含む）のコンクリートと、基礎のコンクリートが両方あるとき：基礎の行は作らない（二重計上の防止）。",
              ""]
    return "\n".join(lines)
