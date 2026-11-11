"""Reference units: use stage (B1-B7) and the schedules behind it.

Row by row, event by event and year by year, exactly as the conceptual formulas are
written. See ``base`` for the conventions.
"""
from __future__ import annotations

from synth import model

from .base import (GRID, REFRIGERANT, annual_unit, convert, explicit_events, grid_source, grid_unit, grid_values,
                   invalid_period, lookup, n_years, nonneg, periodic_events, positive, profile_matches_table,
                   profile_values, ratio, same_series, year_weights, zeros)
from .registry import unit


# ----------------------------------------------------------------- B4: renewals

@unit("B4-01")
def b4_01(scn, res):
    """更新イベント年の生成。設備の行ごとに、明示の更新年一覧があれば、有限の数で 0 < t かつ評価期間の内側にある
    ものを、なければ耐用年数 L の倍数 n*L（n = 1, 2, ...）で評価期間の内側にあるものを、1 つずつ数え上げ、
    それぞれが属する評価年 max(1, ceil(t*c)) の一覧（events）にする。内側とは t < T*c のことで、
    c は 1 − 1e-9 に最も近い倍精度数。判定はすべて入力の 2 進値に対する厳密な有理数演算で行い、
    n 番目の更新の時点は n*L そのもの（丸めた積ではない）とする。したがって評価期間の終わり
    （相対 1e-9 以内を含む）の更新は含めない。一覧の中の欠損・有限でない値は使わない（QA-02 が報告する）。
    同じ値が重複していれば、その回数だけ数える。一覧が無く耐用年数も欠損の行は、更新なし（事象なし）とする。
    一覧が無く、耐用年数が有限の正の数でない（0 以下・NaN・無限大）行は、事象なしとし n_invalid に数える。"""
    T = scn.boundary.study_period
    events = []
    n = 0
    invalid = 0
    for eq in scn.equipment:
        if eq.replacement_event_list is not None:
            ev = explicit_events(T, eq.replacement_event_list)
        else:
            if invalid_period(eq.service_life):
                invalid += 1
            ev = periodic_events(T, eq.service_life)
        events.append(ev)
        n += len(ev)
    return {"events": events, "n_events": n, "n_invalid": invalid}


@unit("B4-03")
def b4_03(scn, res):
    """交換回数の概算。資材の行ごとに、更新周期 L の倍数 n*L が評価期間の内側にある正の整数 n の個数を
    数え上げる（内側の判定と n*L の扱いは B4-01 と同じ厳密な規則）。周期が欠損の行は更新なし（0 回）。
    周期が有限の正の数でない（0 以下・NaN・無限大）行は 0 回とし、n_invalid に数える。"""
    T = scn.boundary.study_period
    counts = []
    invalid = 0
    for row in scn.materials:
        if invalid_period(row.refresh_cycle):
            invalid += 1
        counts.append(len(periodic_events(T, row.refresh_cycle)))
    return {"by_item": counts, "n_invalid": invalid}


def material_install_line(scn, row, q_ord):
    """(factor id, activity) of the installation of one material row at a renewal, or None."""
    fid = row.installation_factor_id
    if fid is None or q_ord is None:
        return None
    hit = lookup(scn, fid, "A5", row.quantity_unit, row.conversions)
    if hit is None:
        return None
    return fid, q_ord * hit[1]


def equipment_extra_lines(scn, eq):
    """Delivery (A4) and installation (A5) lines of one equipment row at a renewal, and whether one is unusable."""
    lines = []
    unusable = False
    for fid, stage in ((eq.delivery_factor_id, "A4"), (eq.installation_factor_id, "A5")):
        if fid is None:
            continue
        hit = lookup(scn, fid, stage, eq.quantity_unit)
        if hit is None or not nonneg(eq.quantity):
            unusable = True
            continue
        lines.append((fid, eq.quantity * hit[1]))
    return lines, unusable


B4_DEPS = ("B4-01", "B4-03", "A13-05", "A13-01", "A13-03", "X-01", "A4-01", "A4-02", "C2-01", "C3-01", "C4-01", "X-14")


@unit("B4-02", depends_on=B4_DEPS)
def b4_02(scn, res):
    """機器・資材更新負荷。更新 1 回ごとに、その行の次の合計を足す。資材の行：製造（A13-01＋A13-03 の行結果。
    未数量分の上乗せ A13-04 は含めない）＋搬入（A4-01 または A4-02 の行結果）＋据付（据付係数があれば、
    発注量×換算倍率×係数。係数の対象段階は A5）＋旧品の廃棄（C2-01・C3-01・C4-01 の行結果）。
    設備の行：製造（X-01 の行結果）＋搬入（搬入係数があれば、数量×換算倍率×係数。係数の対象段階は A4）＋
    据付（据付係数があれば、数量×換算倍率×係数。係数の対象段階は A5）＋旧品の廃棄（X-14 の行結果）。
    資材は B4-03 の回数だけ、設備は B4-01 の一覧の事象ごとに繰り返す。事象は発生年に置く。
    構成要素のうち計算できなかったもの（上流で除外された行、使えない据付・搬入係数）は足さず、
    更新があるのに構成要素が欠けた行の数を n_partial に数える。"""
    T = scn.boundary.study_period
    by_year = zeros(n_years(T) + 1)
    q_ord = res["A13-05"]["q_ord"]
    mfg = (res["A13-01"], res["A13-03"])
    dlv = (res["A4-01"], res["A4-02"])
    disp = (res["C2-01"], res["C3-01"], res["C4-01"])
    incomplete_m = set()
    for src in mfg + dlv + disp:
        incomplete_m |= src["_skipped_rows"]
    incomplete_m |= res["C3-01"]["_partial_rows"] | res["C4-01"]["_partial_rows"]
    total = 0.0
    partial = 0
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
        for y in events:
            e += u
            by_year[y] += u
        if events and (i in incomplete_m or (row.installation_factor_id is not None and inst is None)):
            partial += 1
        total += e
        by_mat.append(e)
        mat_lines.append([(fid, act * len(events)) for fid, act in lines] if events else [])
    incomplete_e = res["X-01"]["_skipped_rows"] | res["X-14"]["_skipped_rows"]
    for j, eq in enumerate(scn.equipment):
        events = res["B4-01"]["events"][j]
        extra, unusable = equipment_extra_lines(scn, eq)
        lines = res["X-01"]["_row_lines"][j] + extra + res["X-14"]["_row_lines"][j]
        u = 0.0
        for fid, act in lines:
            u += act * scn.factors[fid].value
        e = 0.0
        for y in events:
            e += u
            by_year[y] += u
        if events and (j in incomplete_e or unusable):
            partial += 1
        total += e
        by_eq.append(e)
        eq_lines.append([(fid, act * len(events)) for fid, act in lines] if events else [])
    return {"value": total, "by_item_material": by_mat, "by_item_equipment": by_eq, "by_year": by_year,
            "n_partial": partial, "_mat_lines": mat_lines, "_eq_lines": eq_lines}


@unit("X-08", depends_on=B4_DEPS + ("B4-02",))
def x_08(scn, res):
    """更新周期別の集計。更新 1 回当たりの排出 u を周期の値ごとに合算して U_c とし、E_c = 回数×U_c を出す。
    明示の更新年一覧を持つ設備は「EXPLICIT」にまとめる。合計は B4-02 に一致する。"""
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
        for fid, act in equipment_extra_lines(scn, eq)[0]:
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

@unit("B3-01", depends_on=("A13-01", "A13-03", "X-01", "B4-01", "B4-03"))
def b3_01(scn, res):
    """年間修繕。資材・設備の行ごと、評価年ごとに、初期の製造排出 e0×年間修繕率 r×年重み w_y を足す。
    e0 は資材では A13-01＋A13-03 の行結果（未数量分の上乗せ A13-04 は含めない）、設備では X-01 の行結果。
    その行の更新が属する年は修繕を計上しない。修繕率が欠損・有限でない・負の行は足さずに数える。
    製造排出が上流で算出されなかった行は何も足さない（その除外は上流の単位が数え、X-02 が B3 を不完全とする）。
    製造排出が算出された行は、値が 0 でも修繕率が正なら排出の行を持つ（ガス別内訳に現れる）。"""
    T = scn.boundary.study_period
    w = year_weights(T)
    by_year = zeros(len(w))
    total = 0.0
    skipped = 0
    mat_lines, eq_lines = [], []
    a, b = res["A13-01"], res["A13-03"]
    for i, row in enumerate(scn.materials):
        r = row.repair_rate
        e0 = a["by_item"][i] + b["by_item"][i]
        if not nonneg(r):
            skipped += 1
            mat_lines.append([])
            continue
        if r == 0.0:
            mat_lines.append([])
            continue
        skip = set(periodic_events(T, row.refresh_cycle)) if res["B4-03"]["by_item"][i] else set()
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
        if not nonneg(r):
            skipped += 1
            eq_lines.append([])
            continue
        if r == 0.0:
            eq_lines.append([])
            continue
        skip = set(res["B4-01"]["events"][j])
        years = 0.0
        for y in range(1, len(w)):
            if y in skip:
                continue
            e = e0 * r * w[y]
            by_year[y] += e
            total += e
            years += w[y]
        eq_lines.append([(fid, act * r * years) for fid, act in x["_row_lines"][j]])
    return {"value": total, "by_year": by_year, "n_skipped": skipped, "_mat_lines": mat_lines, "_eq_lines": eq_lines}


@unit("B3-02", depends_on=("A13-01", "A13-03", "X-01"))
def b3_02(scn, res):
    """期間中の反復修繕（推計）。資材・設備の行ごとに 初期の製造排出×年間修繕率×評価年数 T を足す。
    初期の製造排出は B3-01 と同じ e0（資材は A13-01＋A13-03、設備は X-01。未数量分の上乗せ A13-04 は含めない）。
    修繕率が欠損・有限でない・負の行は足さずに数える。B3-01 とは択一で、段階合計には B3-01 を使う
    （本式は更新年の除外をしない概算）。"""
    T = scn.boundary.study_period
    total = 0.0
    skipped = 0
    a, b = res["A13-01"]["by_item"], res["A13-03"]["by_item"]
    for i, row in enumerate(scn.materials):
        if nonneg(row.repair_rate):
            total += (a[i] + b[i]) * row.repair_rate * T
        else:
            skipped += 1
    for j, eq in enumerate(scn.equipment):
        if nonneg(eq.repair_rate):
            total += res["X-01"]["by_item"][j] * eq.repair_rate * T
        else:
            skipped += 1
    return {"value": total, "n_skipped": skipped}


# ----------------------------------------------------------------- B1: refrigerants

def device_events(T, dev):
    """Years of the charge changes of one device (explicit list, else multiples of the service life)."""
    if dev.change_years is not None:
        return explicit_events(T, dev.change_years)
    return periodic_events(T, dev.service_life)


def device_ok(dev):
    if dev.change_years is None and invalid_period(dev.service_life):
        return False
    return nonneg(dev.charge_mass_kg) and nonneg(dev.gwp) and ratio(dev.annual_leak_rate)


@unit("B1-01")
def b1_01(scn, res):
    """物質の CO2e 充填量。機器ごとに 初期充填質量×GWP を足す。充填質量または GWP が欠損・有限でない・負の機器は
    足さずに数える。排出量ではなく在庫量であり、どの段階合計にも加えない。"""
    total = 0.0
    skipped = 0
    for dev in scn.refrigerants:
        if nonneg(dev.charge_mass_kg) and nonneg(dev.gwp):
            total += dev.charge_mass_kg * dev.gwp
        else:
            skipped += 1
    return {"value": total, "n_skipped": skipped}


@unit("B1-02")
def b1_02(scn, res):
    """使用期間の漏洩。機器ごとに評価年を 1 年ずつ進め、その年の漏洩を
    年初の残存量×年間漏洩率×年重み×GWP とする（残存量は質量、結果は CO2 換算量）。毎年補充する機器は残存量が常に初期充填量、補充しない機器は
    年末に漏洩分を残存量から引く。機器の交換（交換年一覧、なければ耐用年数の倍数。時点と年の判定は B4-01 と
    同じ厳密な規則）は、それが属する年の年末に反映し、残存量を初期充填量に戻す。交換年一覧も耐用年数も
    無い機器は交換なしとする。充填量・GWP が欠損・有限でない・負、漏洩率が欠損または 0〜1 の外の機器、
    交換年一覧が無く耐用年数が有限の正の数でない（0 以下・NaN・無限大）機器は計上せずに数える。"""
    T = scn.boundary.study_period
    w = year_weights(T)
    by_year = zeros(len(w))
    total = 0.0
    skipped = 0
    by_item, state = [], []
    for dev in scn.refrigerants:
        if not device_ok(dev):
            skipped += 1
            by_item.append(0.0)
            state.append(None)
            continue
        events_in_year: dict[int, int] = {}
        for y in device_events(T, dev):
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
    return {"value": total, "by_item": by_item, "by_year": by_year, "n_skipped": skipped, "_state": state,
            "_lines": [(REFRIGERANT, total)]}


@unit("B1-03", depends_on=("B1-02",))
def b1_03(scn, res):
    """更新時の漏洩。機器の交換 1 回ごとに、交換直前の残存量×交換時損失率×GWP を足す
    （残存量は B1-02 の年次計算の値）。損失率が欠損または 0〜1 の外の機器、B1-02 で除外された機器は計上せずに数える。"""
    by_year = zeros(n_years(scn.boundary.study_period) + 1)
    total = 0.0
    skipped = 0
    for dev, st in zip(scn.refrigerants, res["B1-02"]["_state"]):
        if st is None or not ratio(dev.replacement_loss_rate):
            skipped += 1
            continue
        for y, m in st["before_events"]:
            e = m * dev.replacement_loss_rate * dev.gwp
            by_year[y] += e
            total += e
    return {"value": total, "by_year": by_year, "n_skipped": skipped, "_lines": [(REFRIGERANT, total)]}


@unit("B1-04", depends_on=("B1-02",))
def b1_04(scn, res):
    """廃棄時未回収量。評価期間の終わりの残存量×(1 − 回収率)×GWP を機器ごとに足す。
    回収率が欠損または 0〜1 の外の機器、B1-02 で除外された機器は計上せずに数える（回収率 100％ とはみなさない）。
    本研究の基準計算では B1 段階に帰属させる（C 段階には入れない）。"""
    total = 0.0
    skipped = 0
    for dev, st in zip(scn.refrigerants, res["B1-02"]["_state"]):
        if st is None or not ratio(dev.end_of_life_recovery_rate):
            skipped += 1
            continue
        total += st["end"] * (1.0 - dev.end_of_life_recovery_rate) * dev.gwp
    return {"value": total, "n_skipped": skipped, "_lines": [(REFRIGERANT, total)]}


# ----------------------------------------------------------------- B5: rebuild / refurbishment

@unit("B5-01", depends_on=("A13-01", "A13-03", "A13-04", "X-01", "A4-01", "A4-02", "A5-04", "C1-01", "C2-01",
                           "C3-01", "C4-01", "X-14"))
def b5_01(scn, res):
    """大型改修・建替イベント。建替シナリオが NONE でなければ、建替周期 C の倍数 n*C で評価期間の内側にあるもの
    （時点と年の判定は B4-01 と同じ厳密な規則）ごとに、範囲比 phi×（初期の A1-A3＋A4＋A5＋C1〜C4 の合計）を足す。
    初期の A1-A3 には未数量分の上乗せ A13-04 を含める（A13-01＋A13-03＋A13-04＋X-01）。
    範囲比が欠損または 0〜1 の外のとき、建替周期が欠損または有限の正の数でないときは算出しない
    （computed が偽）。建替シナリオが NONE のときは 0 で、周期と範囲比は使わない。
    部材の更新周期は建替で初期化しない。"""
    b = scn.boundary
    T = b.study_period
    by_year = zeros(n_years(T) + 1)
    if b.reconstruction_scenario == "NONE":
        return {"value": 0.0, "n_events": 0, "by_year": by_year, "computed": True, "_multiplier": 0.0}
    if not ratio(b.reconstruction_scope_fraction) or not positive(b.replacement_cycle):
        return {"value": 0.0, "n_events": 0, "by_year": by_year, "computed": False, "_multiplier": 0.0}
    base = 0.0
    for uid in ("A13-01", "A13-03", "A13-04", "X-01", "A4-01", "A4-02", "A5-04", "C1-01", "C2-01", "C3-01",
                "C4-01", "X-14"):
        base += res[uid]["value"]
    events = periodic_events(T, b.replacement_cycle)
    total = 0.0
    for y in events:
        e = b.reconstruction_scope_fraction * base
        by_year[y] += e
        total += e
    return {"value": total, "n_events": len(events), "by_year": by_year, "computed": True,
            "_multiplier": len(events) * b.reconstruction_scope_fraction}


# ----------------------------------------------------------------- B6 / B2 / B7: operation

@unit("X-06")
def x_06(scn, res):
    """電力排出係数の年次系列の生成。記述子が整っている場合（一定で初期値が有限かつ 0 以上、直線低下で初期値・下限・
    年低下量が有限、低下量が 0 以上、初期値 ≧ 下限 ≧ 0、段階的で段が 1 つ以上あり、段の添字が整数型で 0 から厳密に
    増加し、段の値が有限かつ 0 以上）は、評価年 y（添字 k = y-1）ごとに 一定値、max(下限, 初期値 − 年低下量×k)、
    該当する段の値 を作る（source は DESCRIPTOR）。それ以外は年次表の値を使う（source は TABLE）。
    年次表を使うには、評価年数 Y 以上の件数があり、先頭 Y 件がすべて有限かつ 0 以上でなければならない。
    記述子も年次表も使えないとき、電力排出係数は使えない（source は NONE、computed は偽、系列は 0 で埋める）。
    作った系列が年次表の先頭 Y 件と相対 1e-12 以内で一致するかを matches_table で報告する
    （年次表が Y 件に満たない、または有限でない値を含めば偽。年次表を使ったときは真、使えないときは偽）。"""
    g = scn.operation.grid
    Y = n_years(scn.boundary.study_period)
    source = grid_source(g, Y)
    if source == "NONE":
        return {"by_year": zeros(Y + 1), "matches_table": False, "source": source, "computed": False}
    values = grid_values(g, Y)
    return {"by_year": [0.0] + values, "matches_table": same_series(values, g.table), "source": source,
            "computed": True}


@unit("B6-04")
def b6_04(scn, res):
    """オンサイト発電の扱い。評価年ごとに 買電量 = max(0, 消費量 − (発電量 − 売電量)) を求める。
    max(0, …) は買電量の定義であり（自家消費を超える発電は買電を負にしない）、無効な値を 0 に丸めるものではない。
    年次量は、一定・直線の記述子があればその値（年次表は写し）、なければ年次表の値。使う Y 年分の値は
    すべて有限かつ 0 以上でなければならず、年次表を使うときは Y 件以上が必要。消費量・発電量・売電量の
    いずれかがこれを満たさないとき、単位が「単位/year」でないとき、発電量と売電量を消費量の単位へ
    換算できないときは算出しない（computed が偽）。記述子の値と年次表の写しが一致するか
    （写しが Y 件に満たない場合は不一致）を descriptors_match_tables で報告する。"""
    op = scn.operation
    Y = n_years(scn.boundary.study_period)
    eu = annual_unit(op.electricity.unit)
    gu, xu = annual_unit(op.onsite_generation.unit), annual_unit(op.onsite_export.unit)
    cg = convert(scn, gu, eu) if gu is not None and eu is not None else None
    cx = convert(scn, xu, eu) if xu is not None and eu is not None else None
    match = (profile_matches_table(op.electricity, Y) and profile_matches_table(op.onsite_generation, Y)
             and profile_matches_table(op.onsite_export, Y))
    c, g, x = profile_values(op.electricity, Y), profile_values(op.onsite_generation, Y), profile_values(op.onsite_export, Y)
    if eu is None or cg is None or cx is None or c is None or g is None or x is None:
        return {"by_year": zeros(Y + 1), "computed": False, "descriptors_match_tables": match}
    out = [0.0]
    for k in range(Y):
        out.append(max(0.0, c[k] - (g[k] * cg - x[k] * cx)))
    return {"by_year": out, "computed": True, "descriptors_match_tables": match}


@unit("B6-01", depends_on=("B6-04", "X-06"))
def b6_01(scn, res):
    """年間買電排出。評価年ごとに 買電量×換算倍率×その年の電力排出係数（X-06 の系列）。
    電力係数シナリオの使用許諾がない、電力排出係数が使えない（X-06 が算出されていない）、買電量が
    算出されていない、または買電量の単位を係数の単位へ換算できないときは算出しない。"""
    net, g = res["B6-04"]["by_year"], res["X-06"]["by_year"]
    grid = scn.operation.grid
    eu, gu = annual_unit(scn.operation.electricity.unit), grid_unit(grid)
    conv = convert(scn, eu, gu) if eu is not None and gu is not None else None
    ok = (grid.licence_status in model.ALLOWED_LICENCE_STATES and res["X-06"]["computed"] and res["B6-04"]["computed"]
          and conv is not None)
    out = [0.0]
    for y in range(1, len(net)):
        out.append(net[y] * conv * g[y] if ok else 0.0)
    return {"by_year": out, "computed": ok}


def _annual(scn, pairs, stage):
    """Per-year sum of annual quantity * conversion * factor for the given (profile, factor id) pairs."""
    Y = n_years(scn.boundary.study_period)
    out = zeros(Y + 1)
    used = []
    skipped = 0
    match = True
    for profile, fid in pairs:
        match = match and profile_matches_table(profile, Y)
        hit = lookup(scn, fid, stage, annual_unit(profile.unit))
        values = profile_values(profile, Y)
        if hit is None or values is None:
            skipped += 1
            continue
        used.append((values, fid, hit[1]))
        for k in range(Y):
            out[k + 1] += values[k] * hit[1] * hit[0].value
    return out, used, skipped, match


def _weighted_lines(scn, used):
    w = year_weights(scn.boundary.study_period)
    lines = []
    for values, fid, conv in used:
        act = 0.0
        for y in range(1, len(w)):
            act += w[y] * values[y - 1] * conv
        lines.append((fid, act))
    return lines


@unit("B6-02")
def b6_02(scn, res):
    """燃料の年間排出。評価年ごとに、ガス・石油・地域熱の消費量×換算倍率×係数 を足す（係数の対象段階は B6）。
    年次量は、一定・直線の記述子があればその値、なければ年次表の値。使う Y 年分の値はすべて有限かつ 0 以上で
    なければならず、年次表を使うときは Y 件以上が必要。これを満たさない燃料、単位が「単位/year」でない燃料、
    係数が使えない燃料は足さずに数える。記述子の値と年次表の写しが一致するか（写しが Y 件に満たない場合は不一致）は、
    descriptors_match_tables で報告する。"""
    op = scn.operation
    out, used, skipped, match = _annual(scn, ((op.gas, op.gas_factor_id), (op.oil, op.oil_factor_id),
                                              (op.district_heat, op.district_heat_factor_id)), "B6")
    return {"by_year": out, "n_skipped": skipped, "descriptors_match_tables": match, "_lines": _weighted_lines(scn, used)}


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
    """施設管理に帰属させる運用負荷。評価期間の買電排出（年重み付きの合計）×施設管理の比率（0〜1）。
    比率が欠損または範囲外のとき、買電排出（B6-01）が算出されていないときは算出しない（computed が偽）。
    B2 が対象段階に入っている場合に限り、段階ベクトルでは同額を B6 から差し引く
    （B6 と B2 の合計は変わらない）。B2 が対象外なら B6 から引かない。"""
    w = year_weights(scn.boundary.study_period)
    elec = res["B6-01"]["by_year"]
    share = scn.operation.facility_management_ratio
    if not ratio(share) or not res["B6-01"]["computed"]:
        return {"value": 0.0, "computed": False}
    total = 0.0
    for y in range(1, len(w)):
        total += w[y] * elec[y]
    return {"value": total * share, "computed": True}


@unit("X-11", depends_on=("X-06",))
def x_11(scn, res):
    """床面積当たり統計値による運用エネルギーの推定。延床面積×面積当たり年間電力使用量[kWh/m2/年]×換算倍率×
    （電力排出係数の年重み付き合計）。面積が有限の正の数でない、原単位が欠損・有限でない・負、係数シナリオの
    使用許諾がない、電力排出係数が使えない（X-06 が算出されていない）、または kWh を係数の単位へ換算できないときは
    算出しない。実績の買電量を使わない推定値で、段階合計には使わない。"""
    w = year_weights(scn.boundary.study_period)
    g = res["X-06"]["by_year"]
    grid = scn.operation.grid
    area = scn.project.gross_floor_area
    gu = grid_unit(grid)
    conv = convert(scn, "kWh", gu) if gu is not None else None
    intensity = scn.operation.electricity_per_m2_per_year
    if (not positive(area) or not nonneg(intensity) or conv is None or not res["X-06"]["computed"]
            or grid.licence_status not in model.ALLOWED_LICENCE_STATES):
        return {"value": None}
    cumulative = 0.0
    for y in range(1, len(w)):
        cumulative += w[y] * g[y]
    return {"value": area * intensity * conv * cumulative}


def _b7(scn, profile, fid):
    out, used, skipped, match = _annual(scn, ((profile, fid),), "B7")
    return {"by_year": out, "n_skipped": skipped, "descriptors_match_tables": match, "_lines": _weighted_lines(scn, used)}


@unit("B7-01")
def b7_01(scn, res):
    """上水利用排出。評価年ごとに 上水使用量×換算倍率×係数（係数の対象段階は B7）。年次量の扱いは B6-02 と同じ。"""
    return _b7(scn, scn.water_waste.water, scn.water_waste.water_factor_id)


@unit("B7-02")
def b7_02(scn, res):
    """下水処理排出。評価年ごとに 下水量×換算倍率×係数（係数の対象段階は B7）。年次量の扱いは B6-02 と同じ。"""
    return _b7(scn, scn.water_waste.sewage, scn.water_waste.sewage_factor_id)


@unit("B7-03")
def b7_03(scn, res):
    """一般廃棄物排出。評価年ごとに 一般廃棄物量×換算倍率×係数（係数の対象段階は B7）。年次量の扱いは B6-02 と同じ。"""
    return _b7(scn, scn.water_waste.municipal_waste, scn.water_waste.waste_factor_id)


@unit("B7-04", depends_on=("B7-01", "B7-02", "B7-03"))
def b7_04(scn, res):
    """評価期間積算。評価年ごとの（上水＋下水＋一般廃棄物）の排出×年重み を y = 1..Y で足す。"""
    w = year_weights(scn.boundary.study_period)
    a, b, c = res["B7-01"]["by_year"], res["B7-02"]["by_year"], res["B7-03"]["by_year"]
    total = 0.0
    for y in range(1, len(w)):
        total += w[y] * (a[y] + b[y] + c[y])
    return {"value": total, "_lines": res["B7-01"]["_lines"] + res["B7-02"]["_lines"] + res["B7-03"]["_lines"]}
