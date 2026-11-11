"""Reference units: input gates (SYS), factor resolution, product stage (A1-A3), A4, A5.

Every function follows the conceptual formula literally, row by row. The docstring of
each unit is the binding definition used in this study (see ``base`` for conventions).
"""
from __future__ import annotations

from synth import model

from .base import GRID, annual_unit, convert, grid_unit, lookup, nonneg
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


def factor_uses(scn):
    """Every place where an activity meets a factor: (path, activity unit, factor id, row conversions, stage).

    A use with factor id "UNIT:<unit>" is a pure unit conversion (no factor record).
    """
    for i, row in enumerate(scn.materials):
        base = f"materials[{i}]"
        qu, extra, tr, eol = row.quantity_unit, row.conversions, row.transport, row.end_of_life
        if row.composition is not None:
            yield f"{base}.quantity_unit", qu, "UNIT:kg", extra, None
            for comp in row.composition:
                yield f"{base}.composition", "kg", comp.factor_id, (), "A1-A3"
        else:
            yield f"{base}.quantity_unit", qu, row.factor_id, extra, "A1-A3"
        if tr.delivery_factor_id is not None:
            yield f"{base}.quantity_unit", qu, tr.delivery_factor_id, extra, "A4"
        else:
            yield f"{base}.transport", "tkm", tr.factor_id, (), "A4"
        if row.installation_factor_id is not None:
            yield f"{base}.quantity_unit", qu, row.installation_factor_id, extra, "A5"
        yield f"{base}.end_of_life", "tkm", eol.haul_factor_id, (), "C2"
        for route in eol.routes:
            yield f"{base}.end_of_life", "kg", route.factor_id, (), "C4" if route.route == "LANDFILL" else "C3"
    for i, eq in enumerate(scn.equipment):
        base = f"equipment[{i}]"
        yield f"{base}.quantity_unit", eq.quantity_unit, eq.factor_id, (), "A1-A3"
        if eq.delivery_factor_id is not None:
            yield f"{base}.quantity_unit", eq.quantity_unit, eq.delivery_factor_id, (), "A4"
        if eq.installation_factor_id is not None:
            yield f"{base}.quantity_unit", eq.quantity_unit, eq.installation_factor_id, (), "A5"
        if eq.eol_factor_id is not None:
            yield f"{base}.end_of_life", "kg", eq.eol_factor_id, (), "C3"
    site = scn.construction
    gu = grid_unit(scn.operation.grid)
    yield "construction.electricity", "kWh", f"UNIT:{gu}", (), None
    for i, fuel in enumerate(site.fuels):
        yield f"construction.fuels[{i}].unit", fuel.unit, fuel.factor_id, fuel.conversions, "A5"
    for i, waste in enumerate(site.waste_streams):
        yield f"construction.waste_streams[{i}]", "kg", waste.factor_id, (), "A5"
    op, ww = scn.operation, scn.water_waste
    eu = annual_unit(op.electricity.unit)
    yield "operation.electricity", eu, f"UNIT:{gu}", (), None
    yield "operation.onsite_generation", annual_unit(op.onsite_generation.unit), f"UNIT:{eu}", (), None
    yield "operation.onsite_export", annual_unit(op.onsite_export.unit), f"UNIT:{eu}", (), None
    yield "operation.gas", annual_unit(op.gas.unit), op.gas_factor_id, (), "B6"
    yield "operation.oil", annual_unit(op.oil.unit), op.oil_factor_id, (), "B6"
    yield "operation.district_heat", annual_unit(op.district_heat.unit), op.district_heat_factor_id, (), "B6"
    yield "water_waste.water", annual_unit(ww.water.unit), ww.water_factor_id, (), "B7"
    yield "water_waste.sewage", annual_unit(ww.sewage.unit), ww.sewage_factor_id, (), "B7"
    yield "water_waste.municipal_waste", annual_unit(ww.municipal_waste.unit), ww.waste_factor_id, (), "B7"
    for i, act in enumerate(scn.end_of_life.demolition_activities):
        yield f"end_of_life.demolition_activities[{i}].unit", act.unit, act.factor_id, (), "C1"
    for i, haul in enumerate(scn.end_of_life.waste_hauls):
        yield f"end_of_life.waste_hauls[{i}]", "tkm", haul.factor_id, (), "C2"
    cu = scn.summary_quantities.concrete_uptake_factor_id
    if cu is not None:
        yield "summary_quantities.concrete_uptake", "m3", cu, (), model.STAGE_MEMO
    for i, item in enumerate(scn.cost_items):
        yield f"cost_items[{i}]", item.currency, item.factor_id, (), "A1-A3"


@unit("SYS-02")
def sys_02(scn, res):
    """単位整合性検証。活動量と係数が出会うすべての箇所（資材の製造・搬入・輸送・据付・搬出・処理経路、
    設備、工事の燃料・廃棄物・電力、運用の年次量、解体、参考値、費用項目）について、活動量の単位が
    係数の分母の単位と一致するか、登録された換算（行固有の換算を優先、連鎖なし）があることを確かめる。
    年次量の単位は「単位/year」でなければならない。あわせて、係数の対象段階が使う段階と一致するかを確かめる。
    係数そのものが無い箇所は SYS-03 が報告する。"""
    violations, stage_mismatches = set(), set()
    n = 0
    for path, act_unit, fid, extra, stage in factor_uses(scn):
        n += 1
        if isinstance(fid, str) and fid.startswith("UNIT:"):
            target = fid[5:]
            if act_unit is None or target == "None" or convert(scn, act_unit, target, extra) is None:
                violations.add(path)
            continue
        if act_unit is None:
            violations.add(path)
            continue
        rec = scn.factors.get(fid) if fid is not None else None
        if rec is None:
            continue
        if convert(scn, act_unit, rec.unit, extra) is None:
            violations.add(path)
        if rec.stages != [stage]:
            stage_mismatches.add(f"factors{{{fid}}}.stages")
    return {"ok": not violations and not stage_mismatches, "n_checked": n, "violations": sorted(violations),
            "stage_mismatches": sorted(stage_mismatches)}


@unit("SYS-03")
def sys_03(scn, res):
    """係数権限ゲート。係数を参照している箇所を 1 つずつ調べ、係数 ID が空でなく、係数の記録が存在し、
    使用許諾の状態が PERMITTED_PUBLIC で、出典の参照が空でないことを確かめる。電力係数シナリオも対象。
    空の参照は場所ごとに、記録のない係数と使用許諾のない係数は係数 ID ごとに報告し、影響を受ける参照箇所の数を数える。"""
    bad: dict[str, int] = {}
    n = 0
    for path, fid in model.factor_references(scn):
        n += 1
        if fid is None:
            key = f"{path} (no factor)"
        else:
            rec = scn.factors.get(fid)
            if rec is None:
                key = f"factors{{{fid}}} (no record)"
            elif rec.licence_status not in model.ALLOWED_LICENCE_STATES or not rec.source_url:
                key = f"factors{{{fid}}}.licence_status"
            else:
                continue
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
    """数量による端材の扱い。端材率 w は発注量に対する比（0 <= w < 1）、数量 Q は 0 以上。数量の基準が DESIGN なら
    据付量 = Q、発注量 = Q/(1-w)。ORDERED・AS_BUILT なら 発注量 = Q、据付量 = Q*(1-w)。
    Q または w が欠損・範囲外の行は算出しない（0 にしない）。"""
    q_ord, q_inst = [], []
    skipped = 0
    for row in scn.materials:
        q, w = row.quantity, row.waste_rate
        if not nonneg(q) or w is None or not 0.0 <= w < 1.0:
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
    正味の発注量 = 据付量 + 処分される端材。再使用率は 0〜1。A13-05 の発注量の代替値で、段階合計には使わない。"""
    q_ord, q_inst = res["A13-05"]["q_ord"], res["A13-05"]["q_inst"]
    net, disposed = [], []
    for i, row in enumerate(scn.materials):
        rho = row.reuse_rate
        if q_ord[i] is None or rho is None or not 0.0 <= rho <= 1.0:
            net.append(None)
            disposed.append(None)
            continue
        d = (q_ord[i] - q_inst[i]) * (1.0 - rho)
        disposed.append(d)
        net.append(q_inst[i] + d)
    return {"by_item": net, "waste_by_item": disposed}


@unit("A13-02")
def a13_02(scn, res):
    """複合材の構成比からの推計。複合品の行ごとに、構成材の係数（対象段階が A1-A3 のみ、使用許諾あり、
    kg へ換算可能）を質量比で加重して kg 当たりの複合係数を作る。質量比が負のもの、合計が 1 から 1e-6 を超えて
    ずれる行、使えない構成係数を含む行は係数を作らない。正規化はしない。"""
    out, parts = [], []
    invalid = 0
    for row in scn.materials:
        if row.composition is None:
            out.append(None)
            parts.append(None)
            continue
        total_fraction = 0.0
        value = 0.0
        ok = True
        weights = []
        for comp in row.composition:
            hit = lookup(scn, comp.factor_id, "A1-A3", "kg")
            if hit is None or not nonneg(comp.mass_fraction):
                ok = False
                break
            total_fraction += comp.mass_fraction
            value += comp.mass_fraction * hit[1] * hit[0].value
            weights.append((comp.factor_id, comp.mass_fraction, hit[1]))
        if not ok or abs(total_fraction - 1.0) > 1e-6:
            out.append(None)
            parts.append(None)
            invalid += 1
        else:
            out.append(value)
            parts.append(weights)
    return {"by_item": out, "n_invalid": invalid, "_parts": parts}


def _epd_applies(scn, row):
    """EPD gate: declaration equals the record; licensed; stages exactly A1-A3; convertible; not expired."""
    epd = row.epd
    if epd is None:
        return None
    rec = scn.factors.get(epd.factor_id) if epd.factor_id is not None else None
    if rec is None or epd.declared_stages != rec.stages or epd.declared_unit != rec.unit or epd.valid_until != rec.valid_until:
        return None
    if rec.valid_until is None or rec.valid_until < scn.project.assessment_date:
        return None
    return lookup(scn, epd.factor_id, "A1-A3", row.quantity_unit, row.conversions)


@unit("X-15", depends_on=("A13-02",))
def x_15(scn, res):
    """係数の検索結合と適用優先順位の解決。資材の行ごとに (1) 製品固有値（EPD）、(2) 複合品なら A13-02 の複合係数
    （数量は kg へ換算）、(3) 汎用係数、の順で係数を決め、数量の単位から係数の単位への換算倍率を求める。
    EPD を使うのは、行の宣言（対象段階・単位・有効期限）が係数の記録と一致し、使用許諾があり、対象段階が A1-A3 のみで、
    有効期限が算定日以降（当日を含む）で、単位を換算できるときだけ。汎用係数も対象段階が A1-A3 のみのものに限る。
    決められない行は未解決とする。"""
    composite = res["A13-02"]["by_item"]
    kind, factor, conv = [], [], []
    unresolved = declined = 0
    for i, row in enumerate(scn.materials):
        k = f = c = None
        epd = _epd_applies(scn, row)
        if row.epd is not None and epd is None:
            declined += 1
        if epd is not None:
            k, f, c = "EPD", epd[0].value, epd[1]
        elif row.composition is not None:
            c = convert(scn, row.quantity_unit, "kg", row.conversions)
            if composite[i] is not None and c is not None:
                k, f = "COMPOSITE", composite[i]
            else:
                c = None
        else:
            hit = lookup(scn, row.factor_id, "A1-A3", row.quantity_unit, row.conversions)
            if hit is not None:
                k, f, c = "GENERIC", hit[0].value, hit[1]
        if k is None:
            unresolved += 1
        kind.append(k)
        factor.append(f)
        conv.append(c)
    return {"kind": kind, "factor": factor, "conv": conv, "n_unresolved": unresolved, "n_epd_declined": declined}


def _material_stage(scn, res, kinds):
    q_ord = res["A13-05"]["q_ord"]
    rx = res["X-15"]
    parts = res["A13-02"]["_parts"]
    total = 0.0
    by_item, row_lines = [], []
    skipped = set()
    for i, row in enumerate(scn.materials):
        k = rx["kind"][i]
        if k not in kinds:
            if k is None and "GENERIC" in kinds:
                skipped.add(i)
            by_item.append(0.0)
            row_lines.append([])
            continue
        if q_ord[i] is None:
            skipped.add(i)
            by_item.append(0.0)
            row_lines.append([])
            continue
        activity = q_ord[i] * rx["conv"][i]
        e = activity * rx["factor"][i]
        if k == "EPD":
            lines = [(row.epd.factor_id, activity)]
        elif k == "COMPOSITE":
            lines = [(fid, activity * fraction * c) for fid, fraction, c in parts[i]]
        else:
            lines = [(row.factor_id, activity)]
        total += e
        by_item.append(e)
        row_lines.append(lines)
    return {"value": total, "by_item": by_item, "n_skipped": len(skipped), "_row_lines": row_lines, "_skipped_rows": skipped}


@unit("A13-01", depends_on=("A13-02", "A13-05", "X-15"))
def a13_01(scn, res):
    """資材製造排出量。製品固有値（EPD）を適用しない資材の行について、発注量×換算倍率×係数
    （汎用係数または A13-02 の複合係数）を行の順に足す。係数を決められない行と数量が欠損・範囲外の行は
    足さずに件数を数える。"""
    return _material_stage(scn, res, ("GENERIC", "COMPOSITE"))


@unit("A13-03", depends_on=("A13-02", "A13-05", "X-15"))
def a13_03(scn, res):
    """EPD／商品固有値。X-15 が製品固有値を適用すると決めた行について、発注量×換算倍率×製品固有値を足す。
    A13-01 とは行ごとに択一。"""
    return _material_stage(scn, res, ("EPD",))


@unit("A13-04", depends_on=("A13-01", "A13-03"))
def a13_04(scn, res):
    """未数量工事項目の推定（本研究が独立に設計した上乗せ式）。行ごとの未数量費用比率 r（0 < r < 1）
    について、その行の製造排出 e に r/(1-r) を掛けた分を足す。r が 0 または欠損の行は何も足さない。
    r が負または 1 以上の行は足さずに数える。概念式自体はモデル未定義であり、他のツールの倍率とは無関係。"""
    a, b = res["A13-01"], res["A13-03"]
    total = 0.0
    by_item, row_lines = [], []
    skipped = 0
    for i, row in enumerate(scn.materials):
        r = row.unquantified_cost_ratio
        if r is None or r == 0.0:
            by_item.append(0.0)
            row_lines.append([])
            continue
        if not 0.0 < r < 1.0:
            skipped += 1
            by_item.append(0.0)
            row_lines.append([])
            continue
        g = r / (1.0 - r)
        e = (a["by_item"][i] + b["by_item"][i]) * g
        total += e
        by_item.append(e)
        row_lines.append([(fid, act * g) for fid, act in a["_row_lines"][i] + b["_row_lines"][i]])
    return {"value": total, "by_item": by_item, "n_skipped": skipped, "_row_lines": row_lines}


@unit("X-01")
def x_01(scn, res):
    """設備機器の初期製造排出。設備の行ごとに 数量×換算倍率×係数 を足す（係数の対象段階は A1-A3）。"""
    total = 0.0
    by_item, row_lines = [], []
    skipped = set()
    for j, eq in enumerate(scn.equipment):
        hit = lookup(scn, eq.factor_id, "A1-A3", eq.quantity_unit)
        if not nonneg(eq.quantity) or hit is None:
            skipped.add(j)
            by_item.append(0.0)
            row_lines.append([])
            continue
        activity = eq.quantity * hit[1]
        e = activity * hit[0].value
        total += e
        by_item.append(e)
        row_lines.append([(eq.factor_id, activity)])
    return {"value": total, "by_item": by_item, "n_skipped": len(skipped), "_row_lines": row_lines, "_skipped_rows": skipped}


@unit("X-03", depends_on=("A13-02", "A13-05", "X-15"))
def x_03(scn, res):
    """複合品の構成資材への展開。複合係数で計算した行を構成材に展開し、構成材ごとの質量
    （発注量を kg に換算×質量比）と排出（質量×構成材の係数）を合計する。"""
    q_ord = res["A13-05"]["q_ord"]
    rx = res["X-15"]
    parts = res["A13-02"]["_parts"]
    mass: dict[str, float] = {}
    emission: dict[str, float] = {}
    total = 0.0
    for i, row in enumerate(scn.materials):
        if rx["kind"][i] != "COMPOSITE" or q_ord[i] is None:
            continue
        kg = q_ord[i] * rx["conv"][i]
        for fid, fraction, c in parts[i]:
            m = kg * fraction
            e = m * c * scn.factors[fid].value
            mass[fid] = mass.get(fid, 0.0) + m
            emission[fid] = emission.get(fid, 0.0) + e
            total += e
    return {"value": total, "mass_by_component": mass, "emission_by_component": emission}


def _transport(scn, res, with_load_factor):
    total = 0.0
    by_item, row_lines = [], []
    skipped = set()
    for i, row in enumerate(scn.materials):
        tr = row.transport
        if tr.delivery_factor_id is not None:
            by_item.append(0.0)
            row_lines.append([])
            continue
        hit = lookup(scn, tr.factor_id, "A4", "tkm")
        bad_load = with_load_factor and not (tr.load_factor is not None and tr.load_factor > 0.0)
        if hit is None or not nonneg(tr.mass_t) or not nonneg(tr.distance_km) or bad_load:
            skipped.add(i)
            by_item.append(0.0)
            row_lines.append([])
            continue
        activity = tr.mass_t * tr.distance_km * hit[1]
        if with_load_factor:
            activity = activity / tr.load_factor
        e = activity * hit[0].value
        total += e
        by_item.append(e)
        row_lines.append([(tr.factor_id, activity)])
    return {"value": total, "by_item": by_item, "n_skipped": len(skipped), "_row_lines": row_lines, "_skipped_rows": skipped}


@unit("A4-01")
def a4_01(scn, res):
    """質量距離ベースの輸送。数量当たりの搬入係数を持たない資材の行について、
    輸送質量[t]×距離[km]×換算倍率×輸送手段の係数 を足す（係数の対象段階は A4、単位は tkm へ換算できること）。
    積載率では補正しない。"""
    return _transport(scn, res, False)


@unit("X-12")
def x_12(scn, res):
    """積載率による輸送排出の補正。A4-01 と同じ行について 質量×距離×係数÷積載率 を足す。積載率は正の数。
    係数が満載基準のときの代替値で、段階合計には使わない（A4-01 と択一）。"""
    return _transport(scn, res, True)


@unit("A4-02", depends_on=("A13-05",))
def a4_02(scn, res):
    """製品別輸送負荷。数量当たりの搬入係数を持つ資材の行について、発注量×換算倍率×搬入係数を足す
    （係数の対象段階は A4）。A4-01 とは行ごとに択一。"""
    q_ord = res["A13-05"]["q_ord"]
    total = 0.0
    by_item, row_lines = [], []
    skipped = set()
    for i, row in enumerate(scn.materials):
        fid = row.transport.delivery_factor_id
        if fid is None:
            by_item.append(0.0)
            row_lines.append([])
            continue
        hit = lookup(scn, fid, "A4", row.quantity_unit, row.conversions)
        if hit is None or q_ord[i] is None:
            skipped.add(i)
            by_item.append(0.0)
            row_lines.append([])
            continue
        activity = q_ord[i] * hit[1]
        e = activity * hit[0].value
        total += e
        by_item.append(e)
        row_lines.append([(fid, activity)])
    return {"value": total, "by_item": by_item, "n_skipped": len(skipped), "_row_lines": row_lines, "_skipped_rows": skipped}


@unit("A5-01")
def a5_01(scn, res):
    """仮設電気。工期全体の買電量[kWh]×換算倍率×工事期間の電力排出係数。電力係数シナリオの使用許諾がない、
    買電量が欠損・負、または kWh を係数の単位へ換算できないときは算出しない。"""
    kwh = scn.construction.electricity_kwh
    grid = scn.operation.grid
    gu = grid_unit(grid)
    conv = convert(scn, "kWh", gu) if gu is not None else None
    if not nonneg(kwh) or conv is None or grid.licence_status not in model.ALLOWED_LICENCE_STATES:
        return {"value": 0.0, "computed": False, "_lines": []}
    e = kwh * conv * grid.construction_value
    return {"value": e, "computed": True, "_lines": [(GRID, e)]}


@unit("A5-02")
def a5_02(scn, res):
    """施工燃料。燃料の種類ごとに 数量×換算倍率×係数 を足す（係数の対象段階は A5）。
    換算できない・欠損・負の燃料は足さずに数える。"""
    total = 0.0
    lines = []
    skipped = 0
    for fuel in scn.construction.fuels:
        hit = lookup(scn, fuel.factor_id, "A5", fuel.unit, fuel.conversions)
        if not nonneg(fuel.quantity) or hit is None:
            skipped += 1
            continue
        activity = fuel.quantity * hit[1]
        total += activity * hit[0].value
        lines.append((fuel.factor_id, activity))
    return {"value": total, "n_skipped": skipped, "_lines": lines}


@unit("A5-03")
def a5_03(scn, res):
    """工事廃棄物。廃棄物の種別ごとに 質量[kg]×換算倍率×処理係数 を足す（係数の対象段階は A5）。"""
    total = 0.0
    lines = []
    skipped = 0
    for waste in scn.construction.waste_streams:
        hit = lookup(scn, waste.factor_id, "A5", "kg")
        if not nonneg(waste.mass_kg) or hit is None:
            skipped += 1
            continue
        activity = waste.mass_kg * hit[1]
        total += activity * hit[0].value
        lines.append((waste.factor_id, activity))
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
    代表係数をその建物自身から作るので、定義上、6 区分の製造排出を区分別に集計し直したものに等しい
    （範囲外の資材は含まない）。代表係数を建物の外から与える場合の精度は、ここでは扱わない。"""
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


@unit("X-16")
def x_16(scn, res):
    """物価補正（費用ベース係数の基準年換算）。費用だけが分かっている項目ごとに、
    費用×(係数の基準年の物価指数÷費用の年の物価指数)×換算倍率×費用当たり係数 を足す（係数の対象段階は A1-A3）。
    費用が欠損・負、指数が無いか 0 以下、係数が使えない項目は足さずに数える。
    未数量分の代替推定であり、段階合計には使わない（A13-04 と択一）。"""
    total = 0.0
    by_item = []
    skipped = 0
    for item in scn.cost_items:
        p_cost = scn.price_index.get(item.price_year)
        p_base = scn.price_index.get(item.factor_base_year)
        hit = lookup(scn, item.factor_id, "A1-A3", item.currency)
        if not nonneg(item.amount) or hit is None or p_cost is None or p_base is None or not p_cost > 0.0 or not p_base > 0.0:
            skipped += 1
            by_item.append(0.0)
            continue
        e = item.amount * (p_base / p_cost) * hit[1] * hit[0].value
        total += e
        by_item.append(e)
    return {"value": total, "by_item": by_item, "n_skipped": skipped}
