"""Reference units: end of life (C), memo items, aggregation (SUM), cross-checks (QA).

Written literally from the conceptual formulas. See ``base`` for conventions.
"""
from __future__ import annotations

from synth import model, population

from .base import (GRID, REFRIGERANT, STAGES, convert, finite, included, inside, left_out, lookup, n_years, nonneg,
                   positive, year_weights, zeros)
from .registry import UNITS, run_all, unit


# ----------------------------------------------------------------- C: end of life

@unit("C1-01")
def c1_01(scn, res):
    """解体作業排出。解体の活動ごとに 活動量×換算倍率×係数 を足す（係数の対象段階は C1）。
    活動量が欠損・有限でない・負、または係数が使えない活動は足さずに数える。"""
    total = 0.0
    lines = []
    skipped = 0
    for act in scn.end_of_life.demolition_activities:
        hit = lookup(scn, act.factor_id, "C1", act.unit)
        if not nonneg(act.quantity) or hit is None:
            skipped += 1
            continue
        activity = act.quantity * hit[1]
        total += activity * hit[0].value
        lines.append((act.factor_id, activity))
    return {"value": total, "n_skipped": skipped, "_lines": lines}


@unit("C2-01")
def c2_01(scn, res):
    """廃棄物搬出。資材の行ごとに 廃棄質量[kg]/1000×搬出距離[km]×換算倍率×係数 を足し（係数の対象段階は C2、
    tkm へ換算できること）、さらに行に属さない搬出（質量[t]×距離×換算倍率×係数）を足す。
    質量・距離が欠損・有限でない・負、または係数が使えない行は足さずに数える。"""
    total = 0.0
    by_item, row_lines, lines = [], [], []
    skipped = set()
    n_haul_skipped = 0
    for i, row in enumerate(scn.materials):
        eol = row.end_of_life
        hit = lookup(scn, eol.haul_factor_id, "C2", "tkm")
        if hit is None or not nonneg(eol.mass_kg) or not nonneg(eol.haul_distance_km):
            skipped.add(i)
            by_item.append(0.0)
            row_lines.append([])
            continue
        activity = eol.mass_kg / 1000.0 * eol.haul_distance_km * hit[1]
        e = activity * hit[0].value
        total += e
        by_item.append(e)
        row_lines.append([(eol.haul_factor_id, activity)])
    for haul in scn.end_of_life.waste_hauls:
        hit = lookup(scn, haul.factor_id, "C2", "tkm")
        if hit is None or not nonneg(haul.mass_t) or not nonneg(haul.distance_km):
            n_haul_skipped += 1
            continue
        activity = haul.mass_t * haul.distance_km * hit[1]
        total += activity * hit[0].value
        lines.append((haul.factor_id, activity))
    return {"value": total, "by_item": by_item, "n_skipped": len(skipped) + n_haul_skipped, "_row_lines": row_lines,
            "_lines": lines, "_skipped_rows": skipped}


def _routes(scn, landfill):
    stage = "C4" if landfill else "C3"
    total = 0.0
    by_item, row_lines = [], []
    skipped, partial = set(), set()
    routes_skipped = 0
    for i, row in enumerate(scn.materials):
        eol = row.end_of_life
        e_row = 0.0
        lines = []
        if not nonneg(eol.mass_kg):
            skipped.add(i)
        else:
            for route in eol.routes:
                if (route.route == "LANDFILL") != landfill:
                    continue
                hit = lookup(scn, route.factor_id, stage, "kg")
                if hit is None or not nonneg(route.fraction):
                    routes_skipped += 1
                    partial.add(i)
                    continue
                activity = eol.mass_kg * route.fraction * hit[1]
                e_row += activity * hit[0].value
                lines.append((route.factor_id, activity))
        total += e_row
        by_item.append(e_row)
        row_lines.append(lines)
    return {"value": total, "by_item": by_item, "n_skipped": len(skipped), "n_routes_skipped": routes_skipped,
            "_row_lines": row_lines, "_skipped_rows": skipped, "_partial_rows": partial}


@unit("C3-01")
def c3_01(scn, res):
    """廃棄物処理。資材の行ごと、最終処分以外の処理経路（再使用・リサイクル・中間処理）ごとに
    廃棄質量×経路の比率×換算倍率×経路の係数 を足す（係数の対象段階は C3）。廃棄質量が欠損・有限でない・負の行は
    足さずに n_skipped に数える。比率が欠損・有限でない・負、または係数が使えない経路は足さずに n_routes_skipped に数え、
    同じ行のほかの経路は計算する（比率が 0 の経路でも、係数が使えなければ数える）。"""
    return _routes(scn, False)


@unit("C4-01")
def c4_01(scn, res):
    """最終処分。資材の行ごとに 廃棄質量×最終処分の比率×換算倍率×最終処分の係数 を足す（係数の対象段階は C4）。
    欠損・有限でない値・負の値・使えない係数の扱いは C3-01 と同じ。"""
    return _routes(scn, True)


@unit("X-14")
def x_14(scn, res):
    """設備機器の廃棄時排出。設備の行ごとに 廃棄質量[kg]×換算倍率×処理係数 を足す（C3 段階）。
    質量が欠損・有限でない・負、または係数が使えない行は足さずに数える。"""
    total = 0.0
    by_item, row_lines = [], []
    skipped = set()
    for j, eq in enumerate(scn.equipment):
        hit = lookup(scn, eq.eol_factor_id, "C3", "kg")
        if hit is None or not nonneg(eq.end_of_life_mass_kg):
            skipped.add(j)
            by_item.append(0.0)
            row_lines.append([])
            continue
        activity = eq.end_of_life_mass_kg * hit[1]
        e = activity * hit[0].value
        total += e
        by_item.append(e)
        row_lines.append([(eq.eol_factor_id, activity)])
    return {"value": total, "by_item": by_item, "n_skipped": len(skipped), "_row_lines": row_lines, "_skipped_rows": skipped}


@unit("C-05", depends_on=("A13-05",))
def c_05(scn, res):
    """資材の質量収支。資材の行ごとに、経路の比率がすべて有限かつ 0 以上で、その合計が 1 を超えないこと（許容 1e-6）、
    廃棄質量が据付質量（kg へ換算できる行のみ）を超えないこと（相対許容 1e-6）を検査する。比率に欠損・有限でない値・
    負の値がある行は違反とする（合計はそれ以外の比率で求める）。端材は工事中に現場を出るので、建物に残る質量は
    据付質量である。合計が 1 未満の行は違反ではなく未配分として数える。廃棄質量が欠損・有限でない・負の行、
    据付量が算出されていない行、kg へ換算できない行は質量を検査できないので n_mass_unchecked に数える。数値は補正しない。"""
    q_inst = res["A13-05"]["q_inst"]
    violations = []
    under = []
    unchecked = 0
    for i, row in enumerate(scn.materials):
        eol = row.end_of_life
        total = 0.0
        invalid = False
        for route in eol.routes:
            if nonneg(route.fraction):
                total += route.fraction
            else:
                invalid = True
        if invalid or total > 1.0 + 1e-6:
            violations.append(f"materials[{i}].end_of_life.routes")
        elif total < 1.0 - 1e-6:
            under.append(f"materials[{i}].end_of_life.routes")
        conv = convert(scn, row.quantity_unit, "kg", row.conversions)
        if conv is None or q_inst[i] is None or not nonneg(eol.mass_kg):
            unchecked += 1
        elif eol.mass_kg > q_inst[i] * conv * (1.0 + 1e-6):
            violations.append(f"materials[{i}].end_of_life.mass_kg")
    return {"ok": not violations, "violations": violations, "under_allocated": under, "n_mass_unchecked": unchecked}


@unit("X-09")
def x_09(scn, res):
    """廃棄物の発生品目別・処理経路別の集計。資材の行ごと、処理経路ごとに 質量×比率 と、
    それに経路の係数を掛けた排出を、資材区分×経路の表に足し込む。質量と比率が有効な経路は質量の表に入れ、
    係数も使える経路だけ排出の表に入れる（C3-01・C4-01 と同じ条件）。"""
    mass: dict[str, dict[str, float]] = {}
    emission: dict[str, dict[str, float]] = {}
    total = 0.0
    for row in scn.materials:
        eol = row.end_of_life
        if not nonneg(eol.mass_kg):
            continue
        m_row = mass.setdefault(row.material_class, {r: 0.0 for r in model.EOL_ROUTES})
        e_row = emission.setdefault(row.material_class, {r: 0.0 for r in model.EOL_ROUTES})
        for route in eol.routes:
            if not nonneg(route.fraction):
                continue
            m = eol.mass_kg * route.fraction
            m_row[route.route] += m
            hit = lookup(scn, route.factor_id, "C4" if route.route == "LANDFILL" else "C3", "kg")
            if hit is not None:
                e = m * hit[1] * hit[0].value
                e_row[route.route] += e
                total += e
    return {"value": total, "mass": mass, "emission": emission}


@unit("X-10", depends_on=("A13-05", "B4-01", "B4-03"))
def x_10(scn, res):
    """ライフサイクル資源量・廃棄物量の集計（単位 kg）。資材の行ごとに、発注質量×(1＋更新回数) を資源量に、
    （端材質量＋廃棄質量）×(1＋更新回数) を廃棄物量に足す。設備は 廃棄質量×(1＋更新回数) を廃棄物量に足す。
    kg へ換算できない行、質量が欠損・有限でない・負の行は対象外として数える。"""
    q_ord, q_inst = res["A13-05"]["q_ord"], res["A13-05"]["q_inst"]
    resource = 0.0
    waste = 0.0
    excluded = 0
    for i, row in enumerate(scn.materials):
        conv = convert(scn, row.quantity_unit, "kg", row.conversions)
        if conv is None or q_ord[i] is None or not nonneg(row.end_of_life.mass_kg):
            excluded += 1
            continue
        k = 1 + res["B4-03"]["by_item"][i]
        resource += q_ord[i] * conv * k
        waste += ((q_ord[i] - q_inst[i]) * conv + row.end_of_life.mass_kg) * k
    for j, eq in enumerate(scn.equipment):
        if not nonneg(eq.end_of_life_mass_kg):
            excluded += 1
            continue
        waste += eq.end_of_life_mass_kg * (1 + len(res["B4-01"]["events"][j]))
    return {"resource_kg": resource, "waste_kg": waste, "n_excluded": excluded}


# ----------------------------------------------------------------- memo items

@unit("STO-01")
def sto_01(scn, res):
    """木材の炭素貯蔵（参考値）。木材数量[m3]×絶乾密度[kg/m3]×炭素含有率×44/12。いずれかが欠損・有限でない・負なら算出しない。
    排出の合計には加減しない。"""
    sq = scn.summary_quantities
    if not (nonneg(sq.timber_m3) and nonneg(sq.timber_dry_density_kg_per_m3) and nonneg(sq.timber_carbon_fraction)):
        return {"value": None}
    return {"value": sq.timber_m3 * sq.timber_dry_density_kg_per_m3 * sq.timber_carbon_fraction * (44.0 / 12.0)}


@unit("STO-02")
def sto_02(scn, res):
    """コンクリート炭酸化等の取り扱い（参考値）。コンクリート数量[m3]×換算倍率×吸収係数
    （係数は参考値用の段階 MEMO のもの）。数量が欠損・有限でない・負、または係数が使えなければ算出しない。排出の合計には加減しない。"""
    sq = scn.summary_quantities
    hit = lookup(scn, sq.concrete_uptake_factor_id, model.STAGE_MEMO, "m3")
    if hit is None or not nonneg(sq.concrete_m3):
        return {"value": None}
    return {"value": sq.concrete_m3 * hit[1] * hit[0].value}


# ----------------------------------------------------------------- stage vector

# The units X-02 composes each stage value from (the formula of the X-02 text).
STAGE_SOURCES = {
    "A1-A3": ("A13-01", "A13-03", "A13-04", "X-01"), "A4": ("A4-01", "A4-02"), "A5": ("A5-04",),
    "B1": ("B1-02", "B1-03", "B1-04"), "B2": ("B2-01",), "B3": ("B3-01",), "B4": ("B4-02",), "B5": ("B5-01",),
    "B6": ("B6-03", "B2-01"), "B7": ("B7-04",), "C1": ("C1-01",), "C2": ("C2-01",),
    "C3": ("C3-01", "X-14"), "C4": ("C4-01",),
}
B6_SOURCES_WITHOUT_B2 = ("B6-03",)      # with B2 outside the boundary nothing is subtracted from B6


def upstream_units(sources) -> tuple[str, ...]:
    """The given units and every unit they depend on, directly or indirectly (registry), sorted."""
    seen = set()
    todo = list(sources)
    while todo:
        uid = todo.pop()
        if uid not in seen:
            seen.add(uid)
            todo.extend(UNITS[uid].depends_on)
    return tuple(sorted(seen))


_UPSTREAM: dict = {}


def stage_upstream(stage: str, b2_included: bool = True) -> tuple[str, ...]:
    """Every unit whose result flows into the value of ``stage`` (data flow of the registry)."""
    key = (stage, b2_included or stage != "B6")
    if key not in _UPSTREAM:
        sources = STAGE_SOURCES[stage] if key[1] else B6_SOURCES_WITHOUT_B2
        _UPSTREAM[key] = upstream_units(sources)
    return _UPSTREAM[key]


X02_DEPS = ("A13-01", "A13-02", "A13-03", "A13-04", "A13-05", "A4-01", "A4-02", "A5-01", "A5-02", "A5-03", "A5-04",
            "B1-02", "B1-03", "B1-04", "B2-01", "B3-01", "B4-01", "B4-02", "B4-03", "B5-01", "B6-01", "B6-02", "B6-03",
            "B6-04", "B7-01", "B7-02", "B7-03", "B7-04", "C1-01", "C2-01", "C3-01", "C4-01", "X-01", "X-06", "X-14",
            "X-15")


@unit("X-02", depends_on=X02_DEPS)
def x_02(scn, res):
    """段階結果ベクトルの合成。14 段階の値を次の規則で作る：A1-A3 = A13-01＋A13-03＋A13-04＋X-01、
    A4 = A4-01＋A4-02、A5 = A5-04、B1 = B1-02＋B1-03＋B1-04、B2 = B2-01、B3 = B3-01（B3-02 は使わない）、
    B4 = B4-02、B5 = B5-01、B6 = B6-03 − B2-01、B7 = B7-04、C1 = C1-01、C2 = C2-01、C3 = C3-01＋X-14、
    C4 = C4-01。by_stage には対象段階だけを入れる（対象外の段階は含めず、0 にもしない）。B2 が対象外のときは、
    B6 から B2-01 を引かず、by_stage の B6 = B6-03 とする（施設管理分がどの段階からも消えないようにする）。
    by_stage_all は、対象かどうかに関係なく 14 段階すべての値を上の式のまま並べたもので
    （B6 は常に B6-03 − B2-01）、検算と経年表記のために出す。
    完全性：段階の値は、その値に結果が流れ込む単位（上の式の単位と、それらが直接・間接に依存するすべての単位）の
    どれか 1 つでも何かを除外していれば不完全とする。その単位自身の段階が対象かどうかは問わない。
    「除外している」とは、件数 n_skipped・n_routes_skipped・n_partial・n_invalid・n_unresolved のいずれかが 1 以上、
    または computed が偽であること。対象段階のいずれかに流れ込む単位のうち除外のあるものは、
    incomplete_units に昇順で挙げ、1 つでもあれば complete を偽にする。B2 が対象外のとき、
    B6 に流れ込む単位は B6-03 とその上流だけとする（B2-01 は数えない）。"""
    v = lambda uid: res[uid]["value"]
    full = {
        "A1-A3": v("A13-01") + v("A13-03") + v("A13-04") + v("X-01"),
        "A4": v("A4-01") + v("A4-02"),
        "A5": v("A5-04"),
        "B1": v("B1-02") + v("B1-03") + v("B1-04"),
        "B2": v("B2-01"),
        "B3": v("B3-01"),
        "B4": v("B4-02"),
        "B5": v("B5-01"),
        "B6": v("B6-03") - v("B2-01"),
        "B7": v("B7-04"),
        "C1": v("C1-01"),
        "C2": v("C2-01"),
        "C3": v("C3-01") + v("X-14"),
        "C4": v("C4-01"),
    }
    inc = included(scn)
    by_stage = {s: full[s] for s in STAGES if s in inc}
    if "B6" in inc and "B2" not in inc:
        by_stage["B6"] = v("B6-03")
    incomplete = set()
    for s in STAGES:
        if s in inc:
            for uid in stage_upstream(s, "B2" in inc):
                if left_out(res[uid]):
                    incomplete.add(uid)
    return {"by_stage": by_stage, "by_stage_all": full, "complete": not incomplete, "incomplete_units": sorted(incomplete)}


X04_DEPS = ("A13-01", "A13-03", "A13-04", "X-01", "A4-01", "A4-02", "A5-01", "A5-02", "A5-03", "B1-02", "B1-03",
            "B1-04", "B2-01", "B3-01", "B4-02", "B5-01", "B6-03", "B7-04", "C1-01", "C2-01", "C3-01", "C4-01", "X-14")


def stage_lines(scn, res):
    """All (factor id, activity) lines behind each of the 14 stage values."""
    flat = lambda rows: [line for row in rows for line in row]
    out = {
        "A1-A3": flat(res["A13-01"]["_row_lines"]) + flat(res["A13-03"]["_row_lines"])
                 + flat(res["A13-04"]["_row_lines"]) + flat(res["X-01"]["_row_lines"]),
        "A4": flat(res["A4-01"]["_row_lines"]) + flat(res["A4-02"]["_row_lines"]),
        "A5": res["A5-01"]["_lines"] + res["A5-02"]["_lines"] + res["A5-03"]["_lines"],
        "B1": res["B1-02"]["_lines"] + res["B1-03"]["_lines"] + res["B1-04"]["_lines"],
        "B2": [(GRID, res["B2-01"]["value"])],
        "B3": flat(res["B3-01"]["_mat_lines"]) + flat(res["B3-01"]["_eq_lines"]),
        "B4": flat(res["B4-02"]["_mat_lines"]) + flat(res["B4-02"]["_eq_lines"]),
        "B6": res["B6-03"]["_lines"] + [(GRID, -res["B2-01"]["value"])],
        "B7": res["B7-04"]["_lines"],
        "C1": res["C1-01"]["_lines"],
        "C2": flat(res["C2-01"]["_row_lines"]) + res["C2-01"]["_lines"],
        "C3": flat(res["C3-01"]["_row_lines"]) + flat(res["X-14"]["_row_lines"]),
        "C4": flat(res["C4-01"]["_row_lines"]),
    }
    k = res["B5-01"]["_multiplier"]
    out["B5"] = [(fid, act * k) for s in ("A1-A3", "A4", "A5", "C1", "C2", "C3", "C4") for fid, act in out[s]] if k else []
    return out


def listed_gases(scn) -> list[str]:
    """The gas list without repetitions (the first occurrence counts, the order is kept)."""
    out = []
    for g in scn.gases:
        if g not in out:
            out.append(g)
    return out


def within(residual, tol, scale) -> bool:
    """|residual| <= tol*scale (false when the residual is not a number)."""
    return abs(residual) <= tol * scale


@unit("X-04", depends_on=X04_DEPS + ("X-02",))
def x_04(scn, res):
    """ガス別内訳と CO2 換算の合算。全 14 段階の排出の行（係数 ID と活動量）を 1 行ずつたどり、
    ガスごとに 活動量×係数のガス別量 を足す。ガスは一覧の重複を除いたもの（最初の出現を採り、順序は保つ）で、
    係数の記録にないガスの量は 0 とする。買電と冷媒はガス別の内訳を持たないため CO2 換算量のまま別掲する
    （買電・冷媒の行は係数 ID ではなく専用の印で区別する）。ガスの GWP が欠損・有限でない・負のときは、
    そのガスを CO2 換算の合計に足さずに n_gases_skipped に数える。
    値 = ガス別量×GWP の合計＋買電＋冷媒。これが 14 段階の値（X-02 の by_stage_all）の総和 S に、
    |値 − S| <= 1e-9×max(|S|, 1) で一致するか（相対 1e-9、|S| が 1 未満のときは絶対 1e-9）は、
    matches_stage_total で報告する。by_stage_recomputed は、段階ごとに排出の行を 活動量×係数の値 で足し直した値。"""
    gases = listed_gases(scn)
    by_gas = {g: 0.0 for g in gases}
    grid = refrigerant = 0.0
    recomputed = {}
    used = set()
    for stage, lines in stage_lines(scn, res).items():
        s_total = 0.0
        for fid, act in lines:
            if fid is GRID:
                grid += act
                s_total += act
            elif fid is REFRIGERANT:
                refrigerant += act
                s_total += act
            else:
                rec = scn.factors[fid]
                used.add(fid)
                s_total += act * rec.value
                for g in gases:
                    by_gas[g] += act * rec.gas_amounts.get(g, 0.0)
        recomputed[stage] = s_total
    from_gases = 0.0
    gases_skipped = 0
    for g in gases:
        gwp = scn.gwp.get(g)
        if not nonneg(gwp):
            gases_skipped += 1
            continue
        from_gases += gwp * by_gas[g]
    value = from_gases + grid + refrigerant
    stage_total = 0.0
    for s in STAGES:
        stage_total += res["X-02"]["by_stage_all"][s]
    return {"value": value, "by_gas": by_gas, "co2e_from_gases": from_gases,
            "grid_co2e": grid, "refrigerant_co2e": refrigerant, "by_stage_recomputed": recomputed,
            "n_gases_skipped": gases_skipped,
            "matches_stage_total": within(value - stage_total, 1e-9, max(abs(stage_total), 1.0)), "_used": used}


@unit("X-05", depends_on=X04_DEPS)
def x_05(scn, res):
    """GHG 版と CO2 版の並行算定。全ガス版と同じ行を改めてたどり、係数の CO2 の量だけを使って
    段階別の CO2 排出を求める（係数の記録に CO2 の量がなければ 0。ガスの一覧に CO2 が載っている必要はない）。
    買電は CO2 として数え、冷媒は 0 とする。by_stage_co2 は、対象かどうかに関係なく 14 段階すべての CO2 排出で、
    B6 は X-02 の by_stage_all と同じく B2 の分を引いた後の値。対象段階の合計を値とする
    （B2 が対象外で B6 が対象のときは、X-02 と同じく B2 の分を B6 に戻す）。"""
    by_stage = {}
    for stage, lines in stage_lines(scn, res).items():
        s_total = 0.0
        for fid, act in lines:
            if fid is GRID:
                s_total += act
            elif fid is not REFRIGERANT:
                s_total += act * scn.factors[fid].gas_amounts.get("CO2", 0.0)
        by_stage[stage] = s_total
    inc = included(scn)
    total = 0.0
    for s in STAGES:
        if s in inc:
            total += by_stage[s]
    if "B6" in inc and "B2" not in inc:
        total += by_stage["B2"]
    return {"value": total, "by_stage_co2": {s: by_stage[s] for s in STAGES}}


@unit("X-07", depends_on=("X-02", "B1-02", "B1-03", "B1-04", "B2-01", "B3-01", "B4-02", "B5-01", "B6-01", "B6-02", "B7-01",
                          "B7-02", "B7-03"))
def x_07(scn, res):
    """経年表記（年次・累積の排出系列）。対象段階について、初期段階（A1-A3・A4・A5）を時点 0 に、
    年次の排出（B6・B2・B7・B1 の漏洩・B3）を各評価年に、事象の排出（B4・B5・B1 の更新時損失）を発生年に、
    廃棄段階（C1〜C4）と B1 の廃棄時未回収を最終年に置き、累積を作る。累積の最終値は対象段階の合計に一致する。
    買電排出の B2 と B6 への振り分けは X-02 と同じ規則。"""
    T = scn.boundary.study_period
    w = year_weights(T)
    Y = n_years(T)
    inc = included(scn)
    stage = res["X-02"]["by_stage_all"]
    series = zeros(Y + 1)
    for s in ("A1-A3", "A4", "A5"):
        if s in inc:
            series[0] += stage[s]
    share = scn.operation.facility_management_ratio if res["B2-01"]["computed"] else 0.0
    for y in range(1, Y + 1):
        e = 0.0
        elec = w[y] * res["B6-01"]["by_year"][y]
        if "B6" in inc:
            e += (elec * (1.0 - share) if "B2" in inc else elec) + w[y] * res["B6-02"]["by_year"][y]
        if "B2" in inc:
            e += elec * share
        if "B7" in inc:
            e += w[y] * (res["B7-01"]["by_year"][y] + res["B7-02"]["by_year"][y] + res["B7-03"]["by_year"][y])
        if "B1" in inc:
            e += res["B1-02"]["by_year"][y] + res["B1-03"]["by_year"][y]
        if "B3" in inc:
            e += res["B3-01"]["by_year"][y]
        if "B4" in inc:
            e += res["B4-02"]["by_year"][y]
        if "B5" in inc:
            e += res["B5-01"]["by_year"][y]
        series[y] += e
    last = Y if Y >= 1 else 0
    for s in ("C1", "C2", "C3", "C4"):
        if s in inc:
            series[last] += stage[s]
    if "B1" in inc:
        series[last] += res["B1-04"]["value"]
    cumulative = []
    running = 0.0
    for v in series:
        running += v
        cumulative.append(running)
    return {"by_year": series, "cumulative": cumulative, "value": running}


# ----------------------------------------------------------------- SUM

def _sum(by_stage, stages):
    total = 0.0
    for s in stages:
        if s in by_stage:
            total += by_stage[s]
    return total


@unit("SUM-01", depends_on=("X-02",))
def sum_01(scn, res):
    """アップフロント。対象段階のうち A1-A3・A4・A5 の値をこの順に足す。除外した行などがあれば complete を偽にする（X-02 の判定）。"""
    return {"value": _sum(res["X-02"]["by_stage"], ("A1-A3", "A4", "A5")), "complete": res["X-02"]["complete"]}


@unit("SUM-02", depends_on=("X-02",))
def sum_02(scn, res):
    """エンボディド。対象段階のうち A1-A3・A4・A5・B1〜B5・C1〜C4 の値を足す（B6・B7 は含めない）。
    B2 は買電排出から切り出した施設管理分なので、この合計には運用由来の分が含まれる。
    除外した行などがあれば complete を偽にする（X-02 の判定）。"""
    return {"value": _sum(res["X-02"]["by_stage"], ("A1-A3", "A4", "A5", "B1", "B2", "B3", "B4", "B5", "C1", "C2", "C3", "C4")), "complete": res["X-02"]["complete"]}


@unit("SUM-03", depends_on=("X-02",))
def sum_03(scn, res):
    """ホールライフ。対象段階（最大 14 段階）の値を A1-A3 から C4 の順に足す。除外した行などがあれば complete を偽にする
    （X-02 の判定）。"""
    return {"value": _sum(res["X-02"]["by_stage"], STAGES), "complete": res["X-02"]["complete"]}


def _area(scn):
    area = scn.project.gross_floor_area
    return area if positive(area) else None


@unit("SUM-04", depends_on=("SUM-03",))
def sum_04(scn, res):
    """延べ床面積当たり。ホールライフの合計÷延床面積。延床面積が欠損・有限でない・0 以下のときは算出しない。"""
    area = _area(scn)
    return {"value": res["SUM-03"]["value"] / area if area is not None else None}


@unit("SUM-05", depends_on=("SUM-03",))
def sum_05(scn, res):
    """年平均・床面積当たり。ホールライフの合計÷（延床面積×評価年数）。延床面積が欠損・有限でない・0 以下のときは
    算出しない（評価年数は、計算全体の前提として有限の正の数である）。"""
    area = _area(scn)
    if area is None:
        return {"value": None}
    return {"value": res["SUM-03"]["value"] / (area * scn.boundary.study_period)}


@unit("SUM-06", depends_on=("SUM-03",))
def sum_06(scn, res):
    """t-CO2e 換算。ホールライフの合計[kgCO2e]÷1000。"""
    return {"value": res["SUM-03"]["value"] / 1000.0}


@unit("SUM-07", depends_on=("X-02", "SUM-03"))
def sum_07(scn, res):
    """段階別割合。対象段階ごとに 段階の値÷ホールライフの合計。合計が正で、すべての対象段階の値が 0 以上のときだけ
    定義する（合計が 0 以下、または負の段階がある場合は定義しない）。"""
    by_stage = res["X-02"]["by_stage"]
    total = res["SUM-03"]["value"]
    if not total > 0.0 or not all(v >= 0.0 for v in by_stage.values()):
        return {"defined": False, "by_stage": {}}
    return {"defined": True, "by_stage": {s: v / total for s, v in by_stage.items()}}


@unit("SUM-08", depends_on=("SUM-03",))
def sum_08(scn, res):
    """改善案との差分。基準シナリオが指定されていれば、基準シナリオを同じ基準計算で最初から計算し、
    差 = 当該案 − 基準案、削減率 = (基準案 − 当該案)÷基準案 を求める（基準案の合計が 0 以下なら削減率は出さない）。
    状態は次のいずれか。NO_BASELINE：基準シナリオの ID が指定されていない。BASELINE_NOT_FOUND：ID は指定されて
    いるが、その ID のシナリオが登録されていない。NOT_COMPARABLE：延床面積・評価期間・対象段階・ガスの範囲・
    係数の版（公開年の集合）のいずれかが一致しない（理由を reasons に挙げる）。INCOMPLETE：比較可能だが、
    当該案または基準案のホールライフ合計が不完全（complete が偽）。このとき差と削減率は出さない。
    COMPARED：比較可能で両方の合計が完全。INCOMPLETE と COMPARED では、両案の完全性を、
    proposal_complete・baseline_complete で報告する。"""
    if scn.boundary.baseline_scenario is None:
        return {"status": "NO_BASELINE", "delta": None, "saving": None}
    base = population.BASELINES.get(scn.boundary.baseline_scenario)
    if base is None:
        return {"status": "BASELINE_NOT_FOUND", "delta": None, "saving": None}
    reasons = []
    if base.project.gross_floor_area != scn.project.gross_floor_area:
        reasons.append("AREA")
    if base.boundary.study_period != scn.boundary.study_period:
        reasons.append("PERIOD")
    if set(base.boundary.included_lifecycle_stages) != included(scn):
        reasons.append("STAGES")
    if base.boundary.results_gas_scope != scn.boundary.results_gas_scope:
        reasons.append("GAS_SCOPE")
    if {f.release_year for f in base.factors.values()} != {f.release_year for f in scn.factors.values()}:
        reasons.append("FACTOR_VERSION")
    if reasons:
        return {"status": "NOT_COMPARABLE", "reasons": reasons, "delta": None, "saving": None}
    base_total = run_all(base, ids=["SUM-03"])["SUM-03"]
    flags = {"proposal_complete": res["SUM-03"]["complete"], "baseline_complete": base_total["complete"]}
    if not (flags["proposal_complete"] and flags["baseline_complete"]):
        return {"status": "INCOMPLETE", "delta": None, "saving": None, **flags}
    b = base_total["value"]
    p = res["SUM-03"]["value"]
    return {"status": "COMPARED", "baseline": b, "delta": p - b, "saving": (b - p) / b if b > 0.0 else None, **flags}


# ----------------------------------------------------------------- QA

@unit("QA-01", depends_on=("X-02", "X-04", "A13-01", "A13-03", "A4-01", "A4-02"))
def qa_01(scn, res):
    """相互排他の境界。(a) 14 段階のそれぞれについて、段階の値 v（X-02 の by_stage_all）と、その段階の排出の行を
    足し直した値 v'（X-04 の by_stage_recomputed）が |v − v'| <= 1e-9×max(|v|, 1) で一致すること
    （相対 1e-9、|v| が 1 未満のときは絶対 1e-9）、(b) 資材の行ごとに A13-01 と A13-03 が両方計上されて
    いないこと、(c) A4-01 と A4-02 が両方計上されていないこと、(d) ガス別内訳の合計が段階合計の総和に
    一致すること（X-04 の matches_stage_total）を確かめる。一致しないものを violations に挙げる。"""
    violations = []
    stage, again = res["X-02"]["by_stage_all"], res["X-04"]["by_stage_recomputed"]
    for s in STAGES:
        if not within(stage[s] - again[s], 1e-9, max(abs(stage[s]), 1.0)):
            violations.append(f"stage {s}")
    a, b = res["A13-01"]["by_item"], res["A13-03"]["by_item"]
    c, d = res["A4-01"]["by_item"], res["A4-02"]["by_item"]
    for i in range(len(scn.materials)):
        if a[i] != 0.0 and b[i] != 0.0:
            violations.append(f"materials[{i}] A13-01/A13-03")
        if c[i] != 0.0 and d[i] != 0.0:
            violations.append(f"materials[{i}] A4-01/A4-02")
    if not res["X-04"]["matches_stage_total"]:
        violations.append("gas breakdown total")
    return {"ok": not violations, "violations": violations}


@unit("QA-02")
def qa_02(scn, res):
    """時間境界検査。明示された更新年・交換年（設備の更新年一覧、冷媒機器の交換年一覧）のすべてが
    有限の数で、0 <= t かつ評価期間の内側（t < T*c、c は 1 − 1e-9 に最も近い倍精度数。入力の 2 進値に対する
    厳密な判定）にあることを確かめる。評価期間の終わりちょうど（相対 1e-9 以内を含む）は不合格。
    欠損・NaN・無限大の値も不合格とする（計算では使われない）。
    t = 0 は合格だが、計算では使われない（竣工時点そのもの）ので warnings に挙げる。同じ値が 2 回以上
    載っている一覧も、計算ではその回数だけ数えるので warnings に挙げる（1 つの一覧は 1 回だけ挙げる）。"""
    T = scn.boundary.study_period
    violations, warnings = [], []
    for name, rows, attr in (("equipment", scn.equipment, "replacement_event_list"), ("refrigerants", scn.refrigerants, "change_years")):
        for i, row in enumerate(rows):
            years = getattr(row, attr) or ()
            numbers = [t for t in years if finite(t)]
            if len(numbers) < len(years) or any(not (t >= 0 and inside(t, T)) for t in numbers):
                violations.append(f"{name}[{i}].{attr}")
            if any(t == 0 for t in numbers) or len(set(numbers)) < len(numbers):
                warnings.append(f"{name}[{i}].{attr}")
    return {"ok": not violations, "violations": violations, "warnings": warnings}


@unit("QA-03", depends_on=("X-04",))
def qa_03(scn, res):
    """出典ゲート。排出の行で実際に使われた係数を 1 つずつ調べ、すべて使用許諾があり出典の参照が空でないことを確かめる。"""
    violations = []
    for fid in sorted(res["X-04"]["_used"]):
        rec = scn.factors[fid]
        if rec.licence_status not in model.ALLOWED_LICENCE_STATES or not rec.source_url:
            violations.append(fid)
    return {"ok": not violations, "violations": violations, "n_used": len(res["X-04"]["_used"])}


@unit("QA-04", depends_on=("SYS-04",))
def qa_04(scn, res):
    """用途別面積の検算。SYS-04 の残差 r について |r| <= 1e-6×延床面積 なら合格。延床面積または用途別面積が
    無効（SYS-04 が INVALID）なら判定しない。"""
    s = res["SYS-04"]
    if s["status"] != "EVALUATED":
        return {"ok": False, "status": "NOT_EVALUATED"}
    return {"ok": abs(s["residual"]) <= 1e-6 * scn.project.gross_floor_area, "status": "EVALUATED"}
