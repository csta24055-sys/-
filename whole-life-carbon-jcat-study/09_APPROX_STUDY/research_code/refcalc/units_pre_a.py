"""Reference units: input gates (SYS), factor resolution, product stage (A1-A3), A4, A5.

Every function follows the conceptual formula literally, row by row. The docstring of
each unit is the binding definition used in this study (see ``base`` for conventions).
"""
from __future__ import annotations

from synth import model

from .base import GRID, convert, usable_factor
from .registry import unit

M_FIELDS = ("quantity", "waste_rate", "reuse_rate", "material_life", "repair_rate", "refresh_cycle")
E_FIELDS = ("quantity", "service_life", "repair_rate", "end_of_life_mass_kg")
R_FIELDS = ("charge_mass_kg", "gwp", "annual_leak_rate", "replacement_loss_rate", "end_of_life_recovery_rate")


def _state(scn, owner, name, value):
    declared = model.value_state(scn, owner, name)
    if value is None:
        return model.STATE_MISSING
    if declared == model.STATE_DERIVED:
        return model.STATE_DERIVED
    if value == 0:
        return model.STATE_EXPLICIT_ZERO
    return declared


@unit("SYS-01")
def sys_01(scn, res):
    """入力数値の状態判定。数値入力を 1 つずつ調べ、欠損（None）は MISSING、算出値は DERIVED、
    0 は EXPLICIT_ZERO、それ以外は宣言された状態（OBSERVED・ESTIMATE）とする。MISSING の場所を列挙する。
    その値が計算で使われるかどうかは問わない。機器の耐用年数と交換年一覧のように「どちらか一方」でよい項目は、
    両方ないときだけ欠損とする。"""
    counts = {s: 0 for s in model.VALUE_STATES}
    missing = []

    def see(owner, name, value, path):
        st = _state(scn, owner, name, value)
        counts[st] += 1
        if st == model.STATE_MISSING:
            missing.append(path)

    see(scn.project, "gross_floor_area", scn.project.gross_floor_area, "project.gross_floor_area")
    for i, row in enumerate(scn.materials):
        for name in M_FIELDS:
            see(row, name, getattr(row, name), f"materials[{i}].{name}")
        tr, eol = row.transport, row.end_of_life
        see(row, "transport.mass_t", tr.mass_t, f"materials[{i}].transport.mass_t")
        see(row, "transport.distance_km", tr.distance_km, f"materials[{i}].transport.distance_km")
        see(row, "end_of_life.mass_kg", eol.mass_kg, f"materials[{i}].end_of_life.mass_kg")
    for i, eq in enumerate(scn.equipment):
        for name in E_FIELDS:
            value = getattr(eq, name)
            if name == "service_life" and value is None and eq.replacement_event_list is not None:
                continue
            see(eq, name, value, f"equipment[{i}].{name}")
    for i, dev in enumerate(scn.refrigerants):
        for name in R_FIELDS:
            see(dev, name, getattr(dev, name), f"refrigerants[{i}].{name}")
        if dev.service_life is None and dev.change_years is None:
            see(dev, "service_life", None, f"refrigerants[{i}].service_life")
    site = scn.construction
    see(site, "electricity_kwh", site.electricity_kwh, "construction.electricity_kwh")
    for i, fuel in enumerate(site.fuels):
        see(site, f"fuels[{i}].quantity", fuel.quantity, f"construction.fuels[{i}].quantity")
    for i, waste in enumerate(site.waste_streams):
        see(site, f"waste_streams[{i}].mass_kg", waste.mass_kg, f"construction.waste_streams[{i}].mass_kg")
    end = scn.end_of_life
    for i, act in enumerate(end.demolition_activities):
        see(end, f"demolition_activities[{i}].quantity", act.quantity, f"end_of_life.demolition_activities[{i}].quantity")
    for i, haul in enumerate(end.waste_hauls):
        see(end, f"waste_hauls[{i}].mass_t", haul.mass_t, f"end_of_life.waste_hauls[{i}].mass_t")
        see(end, f"waste_hauls[{i}].distance_km", haul.distance_km, f"end_of_life.waste_hauls[{i}].distance_km")
    return {"ok": not missing, "counts": counts, "violations": missing}


def _unit_pairs(scn):
    """Every (path, quantity unit, factor id, row conversions) pair that needs a unit check."""
    for i, row in enumerate(scn.materials):
        base = f"materials[{i}]"
        if row.composition is not None:
            yield f"{base}.quantity_unit", row.quantity_unit, "kg", row.conversions
        else:
            yield f"{base}.quantity_unit", row.quantity_unit, row.factor_id, row.conversions
        if row.transport.delivery_factor_id is not None:
            yield f"{base}.quantity_unit", row.quantity_unit, row.transport.delivery_factor_id, row.conversions
        if row.installation_factor_id is not None:
            yield f"{base}.quantity_unit", row.quantity_unit, row.installation_factor_id, row.conversions
    for i, eq in enumerate(scn.equipment):
        yield f"equipment[{i}].quantity_unit", eq.quantity_unit, eq.factor_id, ()
    for i, fuel in enumerate(scn.construction.fuels):
        yield f"construction.fuels[{i}].unit", fuel.unit, fuel.factor_id, fuel.conversions
    op, ww = scn.operation, scn.water_waste
    yield "operation.gas", op.gas.unit.split("/")[0], op.gas_factor_id, ()
    yield "operation.oil", op.oil.unit.split("/")[0], op.oil_factor_id, ()
    yield "operation.district_heat", op.district_heat.unit.split("/")[0], op.district_heat_factor_id, ()
    yield "water_waste.water", ww.water.unit.split("/")[0], ww.water_factor_id, ()
    yield "water_waste.sewage", ww.sewage.unit.split("/")[0], ww.sewage_factor_id, ()
    yield "water_waste.municipal_waste", ww.municipal_waste.unit.split("/")[0], ww.waste_factor_id, ()
    for i, act in enumerate(scn.end_of_life.demolition_activities):
        yield f"end_of_life.demolition_activities[{i}].unit", act.unit, act.factor_id, ()


@unit("SYS-02")
def sys_02(scn, res):
    """単位整合性検証。「活動量×係数」を計算するすべての組について、数量の単位が係数の分母の単位と
    一致するか、登録された換算（行固有の換算を優先、連鎖なし）があることを確かめる。
    同じ数量が複数の係数（製造・搬入・据付）と組になる行は、1 つでも換算できなければその行を 1 件として報告する。"""
    violations = []
    n = 0
    for path, q_unit, target, extra in _unit_pairs(scn):
        n += 1
        if target == "kg":
            f_unit = "kg"
        else:
            rec = scn.factors.get(target) if target is not None else None
            if rec is None:
                continue  # a missing factor is reported by SYS-03, not here
            f_unit = rec.unit
        if convert(scn, q_unit, f_unit, extra) is None and (not violations or violations[-1] != path):
            violations.append(path)
    return {"ok": not violations, "n_checked": n, "violations": violations}


@unit("SYS-03")
def sys_03(scn, res):
    """係数権限ゲート。係数を参照している箇所を 1 つずつ調べ、係数が存在し、使用許諾の状態が
    PERMITTED_PUBLIC で、出典の参照が空でないことを確かめる。電力係数シナリオも対象。
    使えない係数を係数 ID ごとに報告し、影響を受ける参照箇所の数を数える。"""
    bad: dict[str, int] = {}
    n = 0
    for path, fid in model.factor_references(scn):
        n += 1
        rec = scn.factors.get(fid) if fid is not None else None
        if rec is None or rec.licence_status not in model.ALLOWED_LICENCE_STATES or not rec.source_url:
            key = f"factors{{{fid}}}.licence_status" if rec is not None else f"{path} (no factor)"
            bad[key] = bad.get(key, 0) + 1
    n += 1
    if scn.operation.grid.licence_status not in model.ALLOWED_LICENCE_STATES:
        bad["operation.grid"] = 1
    return {"ok": not bad, "n_checked": n, "violations": sorted(bad), "n_references_affected": sum(bad.values())}


@unit("SYS-04")
def sys_04(scn, res):
    """延床面積との面積整合。用途別面積を用途名の昇順に足し、延床面積との差 r = A - S を求める。
    A が欠損または 0 以下のときは INVALID。|r| <= 1e-9*A のとき一致とする。数値は補正しない。"""
    area = scn.project.gross_floor_area
    total = 0.0
    for use in sorted(scn.project.use_area_breakdown):
        total += scn.project.use_area_breakdown[use]
    if area is None or not area > 0.0:
        return {"ok": False, "status": "INVALID", "sum": total, "residual": None}
    residual = area - total
    return {"ok": abs(residual) <= 1e-9 * area, "status": "EVALUATED", "sum": total, "residual": residual}


@unit("A13-05")
def a13_05(scn, res):
    """数量による端材の扱い。端材率 w は発注量に対する比（0 <= w < 1）。数量の基準が DESIGN なら
    据付量 = Q、発注量 = Q/(1-w)。ORDERED・AS_BUILT なら 発注量 = Q、据付量 = Q*(1-w)。
    Q または w が欠損・範囲外の行は算出しない（0 にしない）。"""
    q_ord, q_inst = [], []
    skipped = 0
    for row in scn.materials:
        q, w = row.quantity, row.waste_rate
        if q is None or w is None or not 0.0 <= w < 1.0:
            q_ord.append(None)
            q_inst.append(None)
            skipped += 1
        elif row.quantity_basis == "DESIGN":
            q_inst.append(q)
            q_ord.append(q / (1.0 - w))
        else:
            q_ord.append(q)
            q_inst.append(q * (1.0 - w))
    return {"q_ord": q_ord, "q_inst": q_inst, "n_skipped": skipped}


@unit("X-13", depends_on=("A13-05",))
def x_13(scn, res):
    """端材の再使用を考慮した正味の発注量。処分される端材 = (発注量 - 据付量)*(1 - 再使用率)、
    正味の発注量 = 据付量 + 処分される端材。A13-05 の発注量の代替値で、段階合計には使わない。"""
    q_ord, q_inst = res["A13-05"]["q_ord"], res["A13-05"]["q_inst"]
    net, disposed = [], []
    for i, row in enumerate(scn.materials):
        if q_ord[i] is None or row.reuse_rate is None:
            net.append(None)
            disposed.append(None)
            continue
        d = (q_ord[i] - q_inst[i]) * (1.0 - row.reuse_rate)
        disposed.append(d)
        net.append(q_inst[i] + d)
    return {"by_item": net, "waste_by_item": disposed}


@unit("A13-02")
def a13_02(scn, res):
    """複合材の構成比からの推計。複合品の行ごとに、構成材の係数（kg 当たり、対象段階が A1-A3 のみ、
    使用許諾あり）を質量比で加重して複合係数を作る。質量比の合計が 1 から 1e-6 を超えてずれる行、
    使えない構成係数を含む行は係数を作らない。正規化はしない。"""
    out = []
    invalid = 0
    for row in scn.materials:
        if row.composition is None:
            out.append(None)
            continue
        total_fraction = 0.0
        value = 0.0
        ok = True
        for comp in row.composition:
            rec = usable_factor(scn, comp.factor_id)
            if rec is None or rec.unit != "kg" or rec.stages != ["A1-A3"]:
                ok = False
                break
            total_fraction += comp.mass_fraction
            value += comp.mass_fraction * rec.value
        if not ok or abs(total_fraction - 1.0) > 1e-6:
            out.append(None)
            invalid += 1
        else:
            out.append(value)
    return {"by_item": out, "n_invalid": invalid}


def _epd_applies(scn, row):
    """EPD gate: licensed record, stages exactly A1-A3, convertible unit, not expired."""
    if row.epd is None:
        return None
    rec = usable_factor(scn, row.epd.factor_id)
    if rec is None or rec.stages != ["A1-A3"] or rec.valid_until is None:
        return None
    if rec.valid_until < scn.project.assessment_date:
        return None
    conv = convert(scn, row.quantity_unit, rec.unit, row.conversions)
    if conv is None:
        return None
    return rec, conv


@unit("X-15", depends_on=("A13-02",))
def x_15(scn, res):
    """係数の検索結合と適用優先順位の解決。資材の行ごとに (1) 適用条件を満たす製品固有値（EPD）、
    (2) 複合品なら A13-02 の複合係数（数量は kg へ換算）、(3) 汎用係数、の順で係数を決め、
    数量の単位から係数の単位への換算倍率を求める。決められない行は未解決とする。"""
    composite = res["A13-02"]["by_item"]
    kind, factor, conv = [], [], []
    unresolved = 0
    for i, row in enumerate(scn.materials):
        k = f = c = None
        epd = _epd_applies(scn, row)
        if epd is not None:
            k, f, c = "EPD", epd[0].value, epd[1]
        elif row.composition is not None:
            c = convert(scn, row.quantity_unit, "kg", row.conversions)
            if composite[i] is not None and c is not None:
                k, f = "COMPOSITE", composite[i]
            else:
                c = None
        else:
            rec = usable_factor(scn, row.factor_id)
            if rec is not None and rec.stages == ["A1-A3"]:
                c = convert(scn, row.quantity_unit, rec.unit, row.conversions)
                if c is not None:
                    k, f = "GENERIC", rec.value
        if k is None:
            unresolved += 1
        kind.append(k)
        factor.append(f)
        conv.append(c)
    return {"kind": kind, "factor": factor, "conv": conv, "n_unresolved": unresolved}


def _material_stage(scn, res, kinds):
    q_ord = res["A13-05"]["q_ord"]
    rx = res["X-15"]
    total = 0.0
    by_item, row_lines = [], []
    skipped = 0
    for i, row in enumerate(scn.materials):
        k = rx["kind"][i]
        if k not in kinds:
            if k is None and "GENERIC" in kinds:
                skipped += 1
            by_item.append(0.0)
            row_lines.append([])
            continue
        if q_ord[i] is None:
            skipped += 1
            by_item.append(0.0)
            row_lines.append([])
            continue
        activity = q_ord[i] * rx["conv"][i]
        e = activity * rx["factor"][i]
        if k == "EPD":
            lines = [(row.epd.factor_id, activity)]
        elif k == "COMPOSITE":
            lines = [(comp.factor_id, activity * comp.mass_fraction) for comp in row.composition]
        else:
            lines = [(row.factor_id, activity)]
        total += e
        by_item.append(e)
        row_lines.append(lines)
    return {"value": total, "by_item": by_item, "n_skipped": skipped, "_row_lines": row_lines}


@unit("A13-01", depends_on=("A13-05", "X-15"))
def a13_01(scn, res):
    """資材製造排出量。製品固有値（EPD）を適用しない資材の行について、発注量×換算倍率×係数
    （汎用係数または A13-02 の複合係数）を行の順に足す。係数を決められない行と数量が欠損の行は
    足さずに件数を数える。"""
    return _material_stage(scn, res, ("GENERIC", "COMPOSITE"))


@unit("A13-03", depends_on=("A13-05", "X-15"))
def a13_03(scn, res):
    """EPD／商品固有値。製品固有値の適用条件（使用許諾、対象段階が A1-A3 のみ、単位が換算可能、
    算定日に有効）を満たす行について、発注量×換算倍率×製品固有値を足す。A13-01 とは行ごとに択一。"""
    return _material_stage(scn, res, ("EPD",))


@unit("A13-04", depends_on=("A13-01", "A13-03"))
def a13_04(scn, res):
    """未数量工事項目の推定（本研究が独立に設計した上乗せ式）。行ごとの未数量費用比率 r（0 < r < 1）
    について、その行の製造排出 e に r/(1-r) を掛けた分を足す。概念式自体はモデル未定義であり、
    他のツールの倍率とは無関係。"""
    a, b = res["A13-01"], res["A13-03"]
    total = 0.0
    by_item, row_lines = [], []
    for i, row in enumerate(scn.materials):
        r = row.unquantified_cost_ratio
        if r is None or not 0.0 < r < 1.0:
            by_item.append(0.0)
            row_lines.append([])
            continue
        g = r / (1.0 - r)
        e = (a["by_item"][i] + b["by_item"][i]) * g
        total += e
        by_item.append(e)
        row_lines.append([(fid, act * g) for fid, act in a["_row_lines"][i] + b["_row_lines"][i]])
    return {"value": total, "by_item": by_item, "_row_lines": row_lines}


@unit("X-01")
def x_01(scn, res):
    """設備機器の初期製造排出。設備の行ごとに 数量×換算倍率×係数 を足す。"""
    total = 0.0
    by_item, row_lines = [], []
    skipped = 0
    for eq in scn.equipment:
        rec = usable_factor(scn, eq.factor_id)
        conv = convert(scn, eq.quantity_unit, rec.unit) if rec is not None else None
        if eq.quantity is None or conv is None:
            skipped += 1
            by_item.append(0.0)
            row_lines.append([])
            continue
        activity = eq.quantity * conv
        e = activity * rec.value
        total += e
        by_item.append(e)
        row_lines.append([(eq.factor_id, activity)])
    return {"value": total, "by_item": by_item, "n_skipped": skipped, "_row_lines": row_lines}


@unit("X-03", depends_on=("A13-05", "X-15"))
def x_03(scn, res):
    """複合品の構成資材への展開。複合係数で計算した行を構成材に展開し、構成材ごとの質量
    （発注量を kg に換算×質量比）と排出（質量×構成材の係数）を合計する。"""
    q_ord = res["A13-05"]["q_ord"]
    rx = res["X-15"]
    mass: dict[str, float] = {}
    emission: dict[str, float] = {}
    total = 0.0
    for i, row in enumerate(scn.materials):
        if rx["kind"][i] != "COMPOSITE" or q_ord[i] is None:
            continue
        kg = q_ord[i] * rx["conv"][i]
        for comp in row.composition:
            m = kg * comp.mass_fraction
            e = m * scn.factors[comp.factor_id].value
            mass[comp.factor_id] = mass.get(comp.factor_id, 0.0) + m
            emission[comp.factor_id] = emission.get(comp.factor_id, 0.0) + e
            total += e
    return {"value": total, "mass_by_component": mass, "emission_by_component": emission}


def _transport(scn, res, with_load_factor):
    total = 0.0
    by_item, row_lines = [], []
    skipped = 0
    for row in scn.materials:
        tr = row.transport
        if tr.delivery_factor_id is not None:
            by_item.append(0.0)
            row_lines.append([])
            continue
        rec = usable_factor(scn, tr.factor_id)
        bad_load = with_load_factor and not (tr.load_factor is not None and tr.load_factor > 0.0)
        if rec is None or tr.mass_t is None or tr.distance_km is None or bad_load:
            skipped += 1
            by_item.append(0.0)
            row_lines.append([])
            continue
        activity = tr.mass_t * tr.distance_km
        if with_load_factor:
            activity = activity / tr.load_factor
        e = activity * rec.value
        total += e
        by_item.append(e)
        row_lines.append([(tr.factor_id, activity)])
    return {"value": total, "by_item": by_item, "n_skipped": skipped, "_row_lines": row_lines}


@unit("A4-01")
def a4_01(scn, res):
    """質量距離ベースの輸送。数量当たりの搬入係数を持たない資材の行について、
    輸送質量[t]×距離[km]×輸送手段の係数[kgCO2e/tkm] を足す。積載率では補正しない。"""
    return _transport(scn, res, False)


@unit("X-12")
def x_12(scn, res):
    """積載率による輸送排出の補正。A4-01 と同じ行について 質量×距離×係数÷積載率 を足す。
    係数が満載基準のときの代替値で、段階合計には使わない（A4-01 と択一）。"""
    return _transport(scn, res, True)


@unit("A4-02", depends_on=("A13-05",))
def a4_02(scn, res):
    """製品別輸送負荷。数量当たりの搬入係数を持つ資材の行について、発注量×換算倍率×搬入係数を足す。
    A4-01 とは行ごとに択一。"""
    q_ord = res["A13-05"]["q_ord"]
    total = 0.0
    by_item, row_lines = [], []
    skipped = 0
    for i, row in enumerate(scn.materials):
        fid = row.transport.delivery_factor_id
        if fid is None:
            by_item.append(0.0)
            row_lines.append([])
            continue
        rec = usable_factor(scn, fid)
        conv = convert(scn, row.quantity_unit, rec.unit, row.conversions) if rec is not None else None
        if conv is None or q_ord[i] is None:
            skipped += 1
            by_item.append(0.0)
            row_lines.append([])
            continue
        activity = q_ord[i] * conv
        e = activity * rec.value
        total += e
        by_item.append(e)
        row_lines.append([(fid, activity)])
    return {"value": total, "by_item": by_item, "n_skipped": skipped, "_row_lines": row_lines}


@unit("A5-01")
def a5_01(scn, res):
    """仮設電気。工期全体の買電量[kWh]×工事期間の電力排出係数。電力係数シナリオの使用許諾がない、
    または買電量が欠損のときは算出しない。"""
    kwh = scn.construction.electricity_kwh
    grid = scn.operation.grid
    if kwh is None or grid.licence_status not in model.ALLOWED_LICENCE_STATES:
        return {"value": 0.0, "computed": False, "_lines": []}
    return {"value": kwh * grid.construction_value, "computed": True, "_lines": [(GRID, kwh * grid.construction_value)]}


@unit("A5-02")
def a5_02(scn, res):
    """施工燃料。燃料の種類ごとに 数量×換算倍率×係数 を足す。換算できない・欠損の燃料は足さずに数える。"""
    total = 0.0
    lines = []
    skipped = 0
    for fuel in scn.construction.fuels:
        rec = usable_factor(scn, fuel.factor_id)
        conv = convert(scn, fuel.unit, rec.unit, fuel.conversions) if rec is not None else None
        if fuel.quantity is None or conv is None:
            skipped += 1
            continue
        activity = fuel.quantity * conv
        total += activity * rec.value
        lines.append((fuel.factor_id, activity))
    return {"value": total, "n_skipped": skipped, "_lines": lines}


@unit("A5-03")
def a5_03(scn, res):
    """工事廃棄物。廃棄物の種別ごとに 質量[kg]×処理係数 を足す。"""
    total = 0.0
    lines = []
    skipped = 0
    for waste in scn.construction.waste_streams:
        rec = usable_factor(scn, waste.factor_id)
        if waste.mass_kg is None or rec is None:
            skipped += 1
            continue
        total += waste.mass_kg * rec.value
        lines.append((waste.factor_id, waste.mass_kg))
    return {"value": total, "n_skipped": skipped, "_lines": lines}


@unit("A5-04", depends_on=("A5-01", "A5-02", "A5-03"))
def a5_04(scn, res):
    """工事負荷の合計。仮設電気・施工燃料・工事廃棄物をこの順に足す。その他の現場排出は入力がないため 0 を足さず、
    未評価として印を付ける。"""
    parts = {"power": res["A5-01"]["value"], "fuels": res["A5-02"]["value"], "waste": res["A5-03"]["value"]}
    total = 0.0
    for key in ("power", "fuels", "waste"):
        total += parts[key]
    return {"value": total, "parts": parts, "other_assessed": False}


SIMPLE_CLASSES = ("REBAR", "STRUCTURAL_STEEL", "CONCRETE", "TIMBER", "ENVELOPE", "INTERIOR")


def simple_class(row):
    """Summary class of a material row for the simplified estimate (None when outside the six)."""
    if row.material_class in ("REBAR", "STRUCTURAL_STEEL", "CONCRETE", "TIMBER"):
        return row.material_class
    if row.quantity_unit == "m2":
        if row.construction_division in ("ROOF_EXTERIOR_WALL", "OPENINGS"):
            return "ENVELOPE"
        if row.construction_division == "INTERIOR":
            return "INTERIOR"
    return None


def summary_quantity(scn, key):
    sq = scn.summary_quantities
    return {"REBAR": sq.reinforcement_kg, "STRUCTURAL_STEEL": sq.steel_kg, "CONCRETE": sq.concrete_m3,
            "TIMBER": sq.timber_m3, "ENVELOPE": sq.envelope_m2, "INTERIOR": sq.interior_m2}[key]


@unit("X-17", depends_on=("A13-01", "A13-03"))
def x_17(scn, res):
    """主要数量による簡易算定。6 区分（鉄筋・鉄骨・コンクリート・木材・外装・内装）ごとに、
    代表係数 fbar = 区分内の行の製造排出の合計 ÷ 要約数量 を求め、要約数量×代表係数 を足す。
    代表係数をその建物自身から作るので、6 区分の範囲では詳細計算と一致する（範囲外の資材は含まない）。"""
    a, b = res["A13-01"]["by_item"], res["A13-03"]["by_item"]
    sums = {k: 0.0 for k in SIMPLE_CLASSES}
    for i, row in enumerate(scn.materials):
        k = simple_class(row)
        if k is not None:
            sums[k] += a[i] + b[i]
    total = 0.0
    by_class = {}
    for k in SIMPLE_CLASSES:
        q = summary_quantity(scn, k)
        fbar = sums[k] / q if q else 0.0
        e = q * fbar
        total += e
        by_class[k] = {"quantity": q, "fbar": fbar, "emission": e}
    return {"value": total, "by_class": by_class}
