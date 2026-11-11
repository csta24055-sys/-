"""Reference units: use stage (B1-B7) and the schedules behind it.

Row by row, event by event and year by year, exactly as the conceptual formulas are
written. See ``base`` for the time conventions.
"""
from __future__ import annotations

from synth import model

from .base import (GRID, REFRIGERANT, convert, event_year, explicit_events, n_years, periodic_events,
                   usable_factor, year_weights, zeros)
from .registry import unit


# ----------------------------------------------------------------- B4: renewals

@unit("B4-01")
def b4_01(scn, res):
    """更新イベント年の生成。設備の行ごとに、明示の更新年一覧があれば 0 < t < T のものを、なければ
    耐用年数 L の倍数 n*L（n = 1, 2, ...）で n*L < T のものを、1 つずつ数え上げて一覧にする。
    評価期間の終わりちょうどの更新は含めない。"""
    T = scn.boundary.study_period
    events = []
    n = 0
    for eq in scn.equipment:
        if eq.replacement_event_list is not None:
            ev = explicit_events(T, eq.replacement_event_list)
        else:
            ev = periodic_events(T, eq.service_life)
        events.append(ev)
        n += len(ev)
    return {"events": events, "n_events": n}


@unit("B4-03")
def b4_03(scn, res):
    """交換回数の概算。資材の行ごとに、更新周期 c の倍数 n*c が n*c < T を満たす正の整数 n の個数を
    数え上げる。周期が欠損の行は 0 回。"""
    T = scn.boundary.study_period
    return {"by_item": [len(periodic_events(T, row.refresh_cycle)) for row in scn.materials]}


def material_install_line(scn, row, q_ord):
    """(factor id, activity) of the installation of one material row at a renewal, or None."""
    fid = row.installation_factor_id
    if fid is None or q_ord is None:
        return None
    rec = usable_factor(scn, fid)
    conv = convert(scn, row.quantity_unit, rec.unit, row.conversions) if rec is not None else None
    if conv is None:
        return None
    return fid, q_ord * conv


def equipment_extra_lines(scn, eq):
    """Delivery and installation lines of one equipment row at a renewal."""
    lines = []
    for fid in (eq.delivery_factor_id, eq.installation_factor_id):
        rec = usable_factor(scn, fid)
        conv = convert(scn, eq.quantity_unit, rec.unit) if rec is not None else None
        if eq.quantity is not None and conv is not None:
            lines.append((fid, eq.quantity * conv))
    return lines


@unit("B4-02", depends_on=("B4-01", "B4-03", "A13-05", "A13-01", "A13-03", "X-01", "A4-01", "A4-02",
                           "C2-01", "C3-01", "C4-01", "X-14"))
def b4_02(scn, res):
    """機器・資材更新負荷。更新 1 回ごとに、その行の 製造（A1-A3 の行結果）＋搬入（A4 の行結果）＋
    据付（据付係数があれば 発注量×係数）＋旧品の廃棄（C2・C3・C4 の行結果、設備は廃棄質量×係数）を足す。
    資材は B4-03 の回数だけ、設備は B4-01 の一覧の事象ごとに繰り返す。事象は発生年 ceil(t) に置く。"""
    T = scn.boundary.study_period
    by_year = zeros(n_years(T) + 1)
    q_ord = res["A13-05"]["q_ord"]
    mfg = (res["A13-01"], res["A13-03"])
    dlv = (res["A4-01"], res["A4-02"])
    disp = (res["C2-01"], res["C3-01"], res["C4-01"])
    total = 0.0
    by_mat, by_eq, mat_lines, eq_lines = [], [], [], []
    for i, row in enumerate(scn.materials):
        events = periodic_events(T, row.refresh_cycle) if res["B4-03"]["by_item"][i] else []
        lines = []
        for src in mfg + dlv + disp:
            lines += src["_row_lines"][i]
        inst = material_install_line(scn, row, q_ord[i])
        if inst is not None:
            lines.append(inst)
        u = 0.0
        for src in mfg + dlv + disp:
            u += src["by_item"][i]
        if inst is not None:
            u += inst[1] * scn.factors[inst[0]].value
        e = 0.0
        for tau in events:
            e += u
            by_year[event_year(tau)] += u
        total += e
        by_mat.append(e)
        mat_lines.append([(fid, act * len(events)) for fid, act in lines] if events else [])
    for j, eq in enumerate(scn.equipment):
        events = res["B4-01"]["events"][j]
        lines = res["X-01"]["_row_lines"][j] + equipment_extra_lines(scn, eq) + res["X-14"]["_row_lines"][j]
        u = 0.0
        for fid, act in lines:
            u += act * scn.factors[fid].value
        e = 0.0
        for tau in events:
            e += u
            by_year[event_year(tau)] += u
        total += e
        by_eq.append(e)
        eq_lines.append([(fid, act * len(events)) for fid, act in lines] if events else [])
    return {"value": total, "by_item_material": by_mat, "by_item_equipment": by_eq, "by_year": by_year,
            "_mat_lines": mat_lines, "_eq_lines": eq_lines}


@unit("X-08", depends_on=("B4-02", "B4-01", "B4-03", "A13-05", "A13-01", "A13-03", "X-01", "A4-01", "A4-02",
                          "C2-01", "C3-01", "C4-01", "X-14"))
def x_08(scn, res):
    """更新周期別の集計。更新 1 回当たりの排出 u を周期の値ごとに合算して U_c とし、E_c = 回数×U_c を出す。
    明示の更新年一覧を持つ設備は「EXPLICIT」にまとめる。合計は B4-02 に一致する。"""
    T = scn.boundary.study_period
    q_ord = res["A13-05"]["q_ord"]
    unit_emission: dict[str, float] = {}
    count: dict[str, int] = {}
    explicit = 0.0
    srcs = (res["A13-01"], res["A13-03"], res["A4-01"], res["A4-02"], res["C2-01"], res["C3-01"], res["C4-01"])
    for i, row in enumerate(scn.materials):
        n = res["B4-03"]["by_item"][i]
        if not n:
            continue
        u = 0.0
        for src in srcs:
            u += src["by_item"][i]
        inst = material_install_line(scn, row, q_ord[i])
        if inst is not None:
            u += inst[1] * scn.factors[inst[0]].value
        key = repr(float(row.refresh_cycle))
        unit_emission[key] = unit_emission.get(key, 0.0) + u
        count[key] = n
    for j, eq in enumerate(scn.equipment):
        events = res["B4-01"]["events"][j]
        if not events:
            continue
        u = res["X-01"]["by_item"][j] + res["X-14"]["by_item"][j]
        for fid, act in equipment_extra_lines(scn, eq):
            u += act * scn.factors[fid].value
        if eq.replacement_event_list is not None:
            explicit += u * len(events)
            continue
        key = repr(float(eq.service_life))
        unit_emission[key] = unit_emission.get(key, 0.0) + u
        count[key] = len(events)
    by_cycle = {}
    total = explicit
    for key in sorted(unit_emission, key=float):
        e = count[key] * unit_emission[key]
        by_cycle[key] = {"count": count[key], "unit_emission": unit_emission[key], "emission": e}
        total += e
    return {"value": total, "by_cycle": by_cycle, "explicit": explicit}


# ----------------------------------------------------------------- B3: repairs

def _skip_years(events):
    return {event_year(tau) for tau in events}


@unit("B3-01", depends_on=("A13-01", "A13-03", "X-01", "B4-01", "B4-03"))
def b3_01(scn, res):
    """年間修繕。資材・設備の行ごと、評価年ごとに、初期の製造排出 e0×年間修繕率 r×年重み w_y を足す。
    その行の更新が属する年は修繕を計上しない。修繕率が欠損の行は足さない。"""
    T = scn.boundary.study_period
    w = year_weights(T)
    by_year = zeros(len(w))
    total = 0.0
    mat_lines, eq_lines = [], []
    a, b = res["A13-01"], res["A13-03"]
    for i, row in enumerate(scn.materials):
        r = row.repair_rate
        e0 = a["by_item"][i] + b["by_item"][i]
        if r is None or r == 0.0 or e0 == 0.0:
            mat_lines.append([])
            continue
        skip = _skip_years(periodic_events(T, row.refresh_cycle)) if res["B4-03"]["by_item"][i] else set()
        years = 0.0
        for y in range(1, len(w)):
            if y in skip:
                continue
            e = e0 * r * w[y]
            by_year[y] += e
            total += e
            years += w[y]
        mat_lines.append([(fid, act * r * years) for fid, act in a["_row_lines"][i] + b["_row_lines"][i]])
    x = res["X-01"]
    for j, eq in enumerate(scn.equipment):
        r = eq.repair_rate
        e0 = x["by_item"][j]
        if r is None or r == 0.0 or e0 == 0.0:
            eq_lines.append([])
            continue
        skip = _skip_years(res["B4-01"]["events"][j])
        years = 0.0
        for y in range(1, len(w)):
            if y in skip:
                continue
            e = e0 * r * w[y]
            by_year[y] += e
            total += e
            years += w[y]
        eq_lines.append([(fid, act * r * years) for fid, act in x["_row_lines"][j]])
    return {"value": total, "by_year": by_year, "_mat_lines": mat_lines, "_eq_lines": eq_lines}


@unit("B3-02", depends_on=("A13-01", "A13-03", "X-01"))
def b3_02(scn, res):
    """期間中の反復修繕（推計）。資材・設備の行ごとに 初期の製造排出×年間修繕率×評価年数 T を足す。
    B3-01 とは択一で、段階合計には B3-01 を使う（本式は更新年の除外をしない概算）。"""
    T = scn.boundary.study_period
    total = 0.0
    a, b = res["A13-01"]["by_item"], res["A13-03"]["by_item"]
    for i, row in enumerate(scn.materials):
        if row.repair_rate is not None:
            total += (a[i] + b[i]) * row.repair_rate * T
    for j, eq in enumerate(scn.equipment):
        if eq.repair_rate is not None:
            total += res["X-01"]["by_item"][j] * eq.repair_rate * T
    return {"value": total}


# ----------------------------------------------------------------- B1: refrigerants

def device_events(T, dev):
    if dev.change_years is not None:
        return sorted(explicit_events(T, dev.change_years))
    return periodic_events(T, dev.service_life)


def device_ok(dev):
    return None not in (dev.charge_mass_kg, dev.gwp, dev.annual_leak_rate)


@unit("B1-01")
def b1_01(scn, res):
    """物質の CO2e 充填量。機器ごとに 初期充填質量×GWP を足す。排出量ではなく在庫量であり、
    どの段階合計にも加えない。"""
    total = 0.0
    for dev in scn.refrigerants:
        if dev.charge_mass_kg is not None and dev.gwp is not None:
            total += dev.charge_mass_kg * dev.gwp
    return {"value": total}


@unit("B1-02")
def b1_02(scn, res):
    """使用期間の漏洩。機器ごとに評価年を 1 年ずつ進め、その年の漏洩 = 年初の残存量×年間漏洩率×年重み
    とする。毎年補充する機器は残存量が常に初期充填量、補充しない機器は年末に漏洩分を残存量から引く。
    機器の交換（交換年一覧、なければ耐用年数の倍数）は、それが属する年の年末に反映し、残存量を初期充填量に戻す。
    充填量・GWP・漏洩率のいずれかが欠損の機器は計上しない。"""
    T = scn.boundary.study_period
    w = year_weights(T)
    by_year = zeros(len(w))
    total = 0.0
    by_item, state = [], []
    for dev in scn.refrigerants:
        if not device_ok(dev):
            by_item.append(0.0)
            state.append(None)
            continue
        events_in_year: dict[int, int] = {}
        for tau in device_events(T, dev):
            y = event_year(tau)
            events_in_year[y] = events_in_year.get(y, 0) + 1
        m0 = dev.charge_mass_kg
        m = m0
        before_events = []
        e_dev = 0.0
        for y in range(1, len(w)):
            leak = m * dev.annual_leak_rate * w[y]
            e = leak * dev.gwp
            by_year[y] += e
            e_dev += e
            if not dev.top_up:
                m -= leak
            for _ in range(events_in_year.get(y, 0)):
                before_events.append((y, m))
                m = m0
        total += e_dev
        by_item.append(e_dev)
        state.append({"before_events": before_events, "end": m})
    return {"value": total, "by_item": by_item, "by_year": by_year, "_state": state,
            "_lines": [(REFRIGERANT, total)]}


@unit("B1-03", depends_on=("B1-02",))
def b1_03(scn, res):
    """更新時の漏洩。機器の交換 1 回ごとに、交換直前の残存量×交換時損失率×GWP を足す
    （残存量は B1-02 の年次計算の値）。損失率が欠損の機器は計上しない。"""
    by_year = zeros(n_years(scn.boundary.study_period) + 1)
    total = 0.0
    for dev, st in zip(scn.refrigerants, res["B1-02"]["_state"]):
        if st is None or dev.replacement_loss_rate is None:
            continue
        for y, m in st["before_events"]:
            e = m * dev.replacement_loss_rate * dev.gwp
            by_year[y] += e
            total += e
    return {"value": total, "by_year": by_year, "_lines": [(REFRIGERANT, total)]}


@unit("B1-04", depends_on=("B1-02",))
def b1_04(scn, res):
    """廃棄時未回収量。評価期間の終わりの残存量×(1 − 回収率)×GWP を機器ごとに足す。
    本研究の基準計算では B1 段階に帰属させる（C 段階には入れない）。"""
    total = 0.0
    for dev, st in zip(scn.refrigerants, res["B1-02"]["_state"]):
        if st is None or dev.end_of_life_recovery_rate is None:
            continue
        total += st["end"] * (1.0 - dev.end_of_life_recovery_rate) * dev.gwp
    return {"value": total, "_lines": [(REFRIGERANT, total)]}


# ----------------------------------------------------------------- B5: rebuild / refurbishment

@unit("B5-01", depends_on=("A13-01", "A13-03", "A13-04", "X-01", "A4-01", "A4-02", "A5-04", "C1-01", "C2-01",
                           "C3-01", "C4-01", "X-14"))
def b5_01(scn, res):
    """大型改修・建替イベント。建替シナリオが NONE でなければ、建替周期 C の倍数 n*C（n*C < T）ごとに、
    範囲比 phi×（初期の A1-A3＋A4＋A5＋C1〜C4 の合計）を足す。部材の更新周期は建替で初期化しない。"""
    b = scn.boundary
    T = b.study_period
    by_year = zeros(n_years(T) + 1)
    if b.reconstruction_scenario == "NONE":
        return {"value": 0.0, "n_events": 0, "by_year": by_year, "_multiplier": 0.0}
    base = 0.0
    for uid in ("A13-01", "A13-03", "A13-04", "X-01", "A4-01", "A4-02", "A5-04", "C1-01", "C2-01", "C3-01",
                "C4-01", "X-14"):
        base += res[uid]["value"]
    events = periodic_events(T, b.replacement_cycle)
    total = 0.0
    for tau in events:
        e = b.reconstruction_scope_fraction * base
        by_year[event_year(tau)] += e
        total += e
    return {"value": total, "n_events": len(events), "by_year": by_year,
            "_multiplier": len(events) * b.reconstruction_scope_fraction}


# ----------------------------------------------------------------- B6 / B2 / B7: operation

@unit("X-06")
def x_06(scn, res):
    """電力排出係数の年次系列の生成。評価年 y（表の添字 k = y-1）ごとに、シナリオの種類に応じて
    一定値、max(下限, 初期値 − 年低下量×k)、該当する段の値、年次表の値 のいずれかを作る。"""
    g = scn.operation.grid
    Y = n_years(scn.boundary.study_period)
    out = [0.0]
    for k in range(Y):
        if g.kind == "CONSTANT":
            v = g.start
        elif g.kind == "LINEAR_DECLINE_TO_FLOOR":
            v = max(g.floor, g.start - g.annual_decline * k)
        elif g.kind == "STEPWISE":
            v = None
            for step in g.steps:
                if step.from_index <= k:
                    v = step.value
        else:
            v = g.table[k]
        out.append(v)
    matches = all(out[k + 1] == g.table[k] or abs(out[k + 1] - g.table[k]) <= 1e-12 * abs(g.table[k]) for k in range(Y))
    return {"by_year": out, "matches_table": matches}


@unit("B6-04")
def b6_04(scn, res):
    """オンサイト発電の扱い。評価年ごとに 買電量 = max(0, 消費量 − (発電量 − 売電量)) を求める。"""
    op = scn.operation
    out = [0.0]
    for k in range(n_years(scn.boundary.study_period)):
        self_used = op.onsite_generation.table[k] - op.onsite_export.table[k]
        out.append(max(0.0, op.electricity.table[k] - self_used))
    return {"by_year": out}


@unit("B6-01", depends_on=("B6-04", "X-06"))
def b6_01(scn, res):
    """年間買電排出。評価年ごとに 買電量×その年の電力排出係数。電力係数シナリオの使用許諾がなければ算出しない。"""
    net, g = res["B6-04"]["by_year"], res["X-06"]["by_year"]
    ok = scn.operation.grid.licence_status in model.ALLOWED_LICENCE_STATES
    out = [0.0]
    for y in range(1, len(net)):
        out.append(net[y] * g[y] if ok else 0.0)
    return {"by_year": out, "computed": ok}


def _annual(scn, pairs):
    """Per-year sum of profile * conversion * factor for the given (profile, factor id) pairs."""
    Y = n_years(scn.boundary.study_period)
    out = zeros(Y + 1)
    used = []
    skipped = 0
    for profile, fid in pairs:
        rec = usable_factor(scn, fid)
        conv = convert(scn, profile.unit.split("/")[0], rec.unit) if rec is not None else None
        if conv is None:
            skipped += 1
            continue
        used.append((profile, fid, conv))
        for k in range(Y):
            out[k + 1] += profile.table[k] * conv * rec.value
    return out, used, skipped


def _weighted_lines(scn, used):
    w = year_weights(scn.boundary.study_period)
    lines = []
    for profile, fid, conv in used:
        act = 0.0
        for y in range(1, len(w)):
            act += w[y] * profile.table[y - 1] * conv
        lines.append((fid, act))
    return lines


@unit("B6-02")
def b6_02(scn, res):
    """燃料の年間排出。評価年ごとに、ガス・石油・地域熱の消費量×換算倍率×係数 を足す。"""
    op = scn.operation
    out, used, skipped = _annual(scn, ((op.gas, op.gas_factor_id), (op.oil, op.oil_factor_id),
                                       (op.district_heat, op.district_heat_factor_id)))
    return {"by_year": out, "n_skipped": skipped, "_lines": _weighted_lines(scn, used)}


@unit("B6-03", depends_on=("B6-01", "B6-02"))
def b6_03(scn, res):
    """評価年数の積算。評価年ごとの（買電排出＋燃料排出）×年重み を y = 1..Y で足す。"""
    w = year_weights(scn.boundary.study_period)
    elec, fuel = res["B6-01"]["by_year"], res["B6-02"]["by_year"]
    total = 0.0
    e_total = 0.0
    for y in range(1, len(w)):
        total += w[y] * (elec[y] + fuel[y])
        e_total += w[y] * elec[y]
    return {"value": total, "_lines": [(GRID, e_total)] + res["B6-02"]["_lines"]}


@unit("B2-01", depends_on=("B6-01",))
def b2_01(scn, res):
    """施設管理に帰属させる運用負荷。評価期間の買電排出（年重み付きの合計）×施設管理の比率。
    段階ベクトルでは同額を B6 から差し引く（B6 と B2 の合計は変わらない）。"""
    w = year_weights(scn.boundary.study_period)
    elec = res["B6-01"]["by_year"]
    total = 0.0
    for y in range(1, len(w)):
        total += w[y] * elec[y]
    return {"value": total * scn.operation.facility_management_ratio}


@unit("X-11", depends_on=("X-06",))
def x_11(scn, res):
    """床面積当たり統計値による運用エネルギーの推定。延床面積×面積当たり年間電力使用量×
    （電力排出係数の年重み付き合計）。実績の買電量を使わない推定値で、段階合計には使わない。"""
    w = year_weights(scn.boundary.study_period)
    g = res["X-06"]["by_year"]
    area = scn.project.gross_floor_area
    if area is None:
        return {"value": None}
    cumulative = 0.0
    for y in range(1, len(w)):
        cumulative += w[y] * g[y]
    return {"value": area * scn.operation.electricity_per_m2_per_year * cumulative}


@unit("B7-01")
def b7_01(scn, res):
    """上水利用排出。評価年ごとに 上水使用量×係数。"""
    ww = scn.water_waste
    out, used, skipped = _annual(scn, ((ww.water, ww.water_factor_id),))
    return {"by_year": out, "n_skipped": skipped, "_lines": _weighted_lines(scn, used)}


@unit("B7-02")
def b7_02(scn, res):
    """下水処理排出。評価年ごとに 下水量×係数。"""
    ww = scn.water_waste
    out, used, skipped = _annual(scn, ((ww.sewage, ww.sewage_factor_id),))
    return {"by_year": out, "n_skipped": skipped, "_lines": _weighted_lines(scn, used)}


@unit("B7-03")
def b7_03(scn, res):
    """一般廃棄物排出。評価年ごとに 一般廃棄物量×係数。"""
    ww = scn.water_waste
    out, used, skipped = _annual(scn, ((ww.municipal_waste, ww.waste_factor_id),))
    return {"by_year": out, "n_skipped": skipped, "_lines": _weighted_lines(scn, used)}


@unit("B7-04", depends_on=("B7-01", "B7-02", "B7-03"))
def b7_04(scn, res):
    """評価期間積算。評価年ごとの（上水＋下水＋一般廃棄物）の排出×年重み を y = 1..Y で足す。"""
    w = year_weights(scn.boundary.study_period)
    a, b, c = res["B7-01"]["by_year"], res["B7-02"]["by_year"], res["B7-03"]["by_year"]
    total = 0.0
    for y in range(1, len(w)):
        total += w[y] * (a[y] + b[y] + c[y])
    return {"value": total, "_lines": res["B7-01"]["_lines"] + res["B7-02"]["_lines"] + res["B7-03"]["_lines"]}
