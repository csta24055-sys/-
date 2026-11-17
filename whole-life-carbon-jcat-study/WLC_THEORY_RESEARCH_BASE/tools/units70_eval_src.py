# -*- coding: utf-8 -*-
# 70 評価単位の式の実行形（WLC_THEORY_RESEARCH_BASE/02 の各単位の式と 1 対 1。data/units70.json の helpers_py・eval_py の元）。
#
# 形式：「#@helpers」の塊は共通の部分式（02 の 2 節の記号）。「#@unit <ID>」の塊は 1 単位の式で、次の名前の上で実行する：
#   x = 入力のシナリオ（09 章の凍結した生成器 synth.model.Scenario。読むだけ）、T = 評価期間、
#   U = 上流の単位の結果（ID -> 辞書）、BASELINES = 基準案の登録（SUM-08）、LEDGER_SUM03(b) = 基準案 b の SUM-03 をこの台帳で計算する関数。
#   塊は out（辞書）を作る。キーが「_」で始まるものは単位の間の受け渡し用（行ごとの活動量など）で、公開の出力ではない。
# 実行の順序は塊が参照する単位 ID からの位相順（tools/check_units70.py が作る）。
#
# 由来と独立性（隠さない）：この実行形は、凍結した基準計算（09 章 research_code/refcalc）の定義文とコードの意味を、本台帳の
# 記号に合わせて短く書き直したもの（逐次の計算の順序も基準計算に合わせた）。refcalc も統一系（10 章 specs・tstudy）も import しない。
# したがって統一系との一致は「台帳の式が統一系の出力を再現する」ことの確認であり、基準計算から独立したモデルの検証ではない。
# 架空データ・独立概念モデルだけを扱う。J-CAT 原版の式・係数・値は含まない。
#@helpers
# 共通の部分式（02 の 2 節の記号と 1 対 1）。入力 x は生成器の Scenario、T は評価期間、U は上流の単位の結果。
import math
EPS = 1e-9                                        # epsilon（事象の規則の幅）
def nn(v):                                        # [0 <= v < inf]（None・NaN・無限は 0）
    return v is not None and not isinstance(v, bool) and v >= 0.0 and not math.isinf(v)
def rat(v):                                       # [0 <= v <= 1]
    return v is not None and not isinstance(v, bool) and 0.0 <= v <= 1.0
def pos(v):                                       # [0 < v < inf]
    return v is not None and not isinstance(v, bool) and v > 0.0 and not math.isinf(v)
def theta(T, tau):                                # theta_eps(T; tau) = [tau < T(1-eps)]
    return tau < T * (1.0 - EPS)
def Yn(T):                                        # Y = ceil(T)
    return math.ceil(T)
def wy(T, y):                                     # 年 y = k+1 の重み w_k(T) = clip(T-k, 0, 1)（1 <= y <= Y）
    return min(1.0, T - (y - 1))
def ycell(tau):                                   # 事象の年 y_tau = k_tau + 1 = max(1, ceil(tau(1-eps)))
    return max(1, math.ceil(tau * (1.0 - EPS)))
def periodic(T, c):                               # {n c : n >= 1, theta(T; n c)}（c が欠損・非正・無限なら空）
    out = []
    if not pos(c):
        return out
    n = 1
    while theta(T, n * c):
        out.append(n * c)
        n += 1
    return out
def explicit(T, L):                               # {t in L : t > 0, theta(T; t)}
    return [float(t) for t in L if t > 0 and theta(T, t)]
def cv(x, a, b, extra=()):                        # cv(a -> b)：同じ単位 1、行固有の換算、全体の換算の順。連鎖・逆算なし。なければ None
    if a == b:
        return 1.0
    for c in extra:
        if c.from_unit == a and c.to_unit == b:
            return c.factor
    for c in x.unit_conversions:
        if c.from_unit == a and c.to_unit == b:
            return c.factor
    return None
def fac(x, fid, stage, unit, extra=()):           # 係数ゲート G_s(f, u)：(F_f, cv) または None
    if fid is None or unit is None:
        return None
    r = x.factors.get(fid)
    if r is None or r.licence_status != "PERMITTED_PUBLIC" or list(r.stages) != [stage]:
        return None
    c = cv(x, unit, r.unit, extra)
    return None if c is None else (r.value, c)
def aunit(u):                                     # 「単位/year」の単位（それ以外は None）
    h, s, t = u.partition("/")
    return h if s and t == "year" else None
def gunit(g):                                     # 電力係数の単位「kgCO2e/<単位>」の分母
    h, s, t = g.unit.partition("/")
    return t if s and h == "kgCO2e" and t else None
def prof(p, Y):                                   # 年次量 v_k（記述子が使えれば記述子、なければ表）
    if p.kind == "CONSTANT" and p.base is not None:
        return [p.base] * Y
    if p.kind == "LINEAR_TREND" and p.base is not None and p.slope is not None:
        return [p.base + p.slope * k for k in range(Y)]
    return [p.table[k] for k in range(Y)]
def same(v, t):                                   # 2 つの系列の相対 1e-12 での一致
    return all(a == b or abs(a - b) <= 1e-12 * max(abs(a), abs(b)) for a, b in zip(v, t))
def grid_ok(g):                                   # 電力係数の記述子が整っているか
    if g.kind == "CONSTANT":
        return g.start is not None
    if g.kind == "LINEAR_DECLINE_TO_FLOOR":
        return None not in (g.start, g.floor, g.annual_decline) and g.annual_decline >= 0.0 and g.start >= g.floor
    if g.kind == "STEPWISE":
        s = g.steps or []
        return bool(s) and s[0].from_index == 0 and all(s[i].from_index < s[i + 1].from_index for i in range(len(s) - 1))
    return False
def grid_vals(g, Y):                              # gamma_k（X-06）
    if not grid_ok(g):
        return [g.table[k] for k in range(Y)]
    if g.kind == "CONSTANT":
        return [g.start] * Y
    if g.kind == "LINEAR_DECLINE_TO_FLOOR":
        return [max(g.floor, g.start - g.annual_decline * k) for k in range(Y)]
    out = []
    for k in range(Y):
        v = None
        for st in g.steps:
            if st.from_index <= k:
                v = st.value
        out.append(v)
    return out
STAGES = ("A1-A3", "A4", "A5", "B1", "B2", "B3", "B4", "B5", "B6", "B7", "C1", "C2", "C3", "C4")
GRID, REFR = "GRID", "REFRIGERANT"
def flat(rows):
    return [ln for r in rows for ln in r]

#@unit SYS-01
def state(owner, name, value):
    d = owner.states.get(name)
    if d is None:
        rec = x.provenance.get(owner.provenance_id)
        d = rec.value_state if rec is not None else "MISSING"
    if value is None:
        return "MISSING"
    if d == "DERIVED":
        return "DERIVED"
    if value == 0:
        return "EXPLICIT_ZERO"
    return d
counts = {s: 0 for s in ("OBSERVED", "ESTIMATE", "EXPLICIT_ZERO", "MISSING", "DERIVED")}
miss = []
def see(owner, name, value, path):
    s = state(owner, name, value)
    counts[s] = counts.get(s, 0) + 1
    if s == "MISSING":
        miss.append(path)
see(x.project, "gross_floor_area", x.project.gross_floor_area, "project.gross_floor_area")
for i, r in enumerate(x.materials):
    for nm in ("quantity", "waste_rate", "reuse_rate", "material_life", "repair_rate", "refresh_cycle"):
        see(r, nm, getattr(r, nm), "materials[%d].%s" % (i, nm))
    see(r, "transport.mass_t", r.transport.mass_t, "materials[%d].transport.mass_t" % i)
    see(r, "transport.distance_km", r.transport.distance_km, "materials[%d].transport.distance_km" % i)
    see(r, "end_of_life.mass_kg", r.end_of_life.mass_kg, "materials[%d].end_of_life.mass_kg" % i)
for i, e in enumerate(x.equipment):
    for nm in ("quantity", "service_life", "repair_rate", "end_of_life_mass_kg"):
        v = getattr(e, nm)
        if nm == "service_life" and v is None and e.replacement_event_list is not None:
            continue
        see(e, nm, v, "equipment[%d].%s" % (i, nm))
for i, d in enumerate(x.refrigerants):
    for nm in ("charge_mass_kg", "gwp", "annual_leak_rate", "replacement_loss_rate", "end_of_life_recovery_rate"):
        see(d, nm, getattr(d, nm), "refrigerants[%d].%s" % (i, nm))
    if d.service_life is None and d.change_years is None:
        see(d, "service_life", None, "refrigerants[%d].service_life" % i)
c = x.construction
see(c, "electricity_kwh", c.electricity_kwh, "construction.electricity_kwh")
for i, f in enumerate(c.fuels):
    see(c, "fuels[%d].quantity" % i, f.quantity, "construction.fuels[%d].quantity" % i)
for i, f in enumerate(c.waste_streams):
    see(c, "waste_streams[%d].mass_kg" % i, f.mass_kg, "construction.waste_streams[%d].mass_kg" % i)
e = x.end_of_life
for i, a in enumerate(e.demolition_activities):
    see(e, "demolition_activities[%d].quantity" % i, a.quantity, "end_of_life.demolition_activities[%d].quantity" % i)
for i, h in enumerate(e.waste_hauls):
    see(e, "waste_hauls[%d].mass_t" % i, h.mass_t, "end_of_life.waste_hauls[%d].mass_t" % i)
    see(e, "waste_hauls[%d].distance_km" % i, h.distance_km, "end_of_life.waste_hauls[%d].distance_km" % i)
out = {"ok": not miss, "counts": counts, "violations": miss}

#@unit SYS-02
def uses():
    for i, r in enumerate(x.materials):
        b, qu, ex, tr, eo = "materials[%d]" % i, r.quantity_unit, r.conversions, r.transport, r.end_of_life
        if r.composition is not None:
            yield b + ".quantity_unit", qu, "UNIT:kg", ex, None
            for cp in r.composition:
                yield b + ".composition", "kg", cp.factor_id, (), "A1-A3"
        else:
            yield b + ".quantity_unit", qu, r.factor_id, ex, "A1-A3"
        if tr.delivery_factor_id is not None:
            yield b + ".quantity_unit", qu, tr.delivery_factor_id, ex, "A4"
        else:
            yield b + ".transport", "tkm", tr.factor_id, (), "A4"
        if r.installation_factor_id is not None:
            yield b + ".quantity_unit", qu, r.installation_factor_id, ex, "A5"
        yield b + ".end_of_life", "tkm", eo.haul_factor_id, (), "C2"
        for rt in eo.routes:
            yield b + ".end_of_life", "kg", rt.factor_id, (), "C4" if rt.route == "LANDFILL" else "C3"
    for i, q in enumerate(x.equipment):
        b = "equipment[%d]" % i
        yield b + ".quantity_unit", q.quantity_unit, q.factor_id, (), "A1-A3"
        if q.delivery_factor_id is not None:
            yield b + ".quantity_unit", q.quantity_unit, q.delivery_factor_id, (), "A4"
        if q.installation_factor_id is not None:
            yield b + ".quantity_unit", q.quantity_unit, q.installation_factor_id, (), "A5"
        if q.eol_factor_id is not None:
            yield b + ".end_of_life", "kg", q.eol_factor_id, (), "C3"
    gu = gunit(x.operation.grid)
    yield "construction.electricity", "kWh", "UNIT:%s" % gu, (), None
    for i, f in enumerate(x.construction.fuels):
        yield "construction.fuels[%d].unit" % i, f.unit, f.factor_id, f.conversions, "A5"
    for i, f in enumerate(x.construction.waste_streams):
        yield "construction.waste_streams[%d]" % i, "kg", f.factor_id, (), "A5"
    op, ww = x.operation, x.water_waste
    eu = aunit(op.electricity.unit)
    yield "operation.electricity", eu, "UNIT:%s" % gu, (), None
    yield "operation.onsite_generation", aunit(op.onsite_generation.unit), "UNIT:%s" % eu, (), None
    yield "operation.onsite_export", aunit(op.onsite_export.unit), "UNIT:%s" % eu, (), None
    yield "operation.gas", aunit(op.gas.unit), op.gas_factor_id, (), "B6"
    yield "operation.oil", aunit(op.oil.unit), op.oil_factor_id, (), "B6"
    yield "operation.district_heat", aunit(op.district_heat.unit), op.district_heat_factor_id, (), "B6"
    yield "water_waste.water", aunit(ww.water.unit), ww.water_factor_id, (), "B7"
    yield "water_waste.sewage", aunit(ww.sewage.unit), ww.sewage_factor_id, (), "B7"
    yield "water_waste.municipal_waste", aunit(ww.municipal_waste.unit), ww.waste_factor_id, (), "B7"
    for i, a in enumerate(x.end_of_life.demolition_activities):
        yield "end_of_life.demolition_activities[%d].unit" % i, a.unit, a.factor_id, (), "C1"
    for i, h in enumerate(x.end_of_life.waste_hauls):
        yield "end_of_life.waste_hauls[%d]" % i, "tkm", h.factor_id, (), "C2"
    cu = x.summary_quantities.concrete_uptake_factor_id
    if cu is not None:
        yield "summary_quantities.concrete_uptake", "m3", cu, (), "MEMO"
    for i, it in enumerate(x.cost_items):
        yield "cost_items[%d]" % i, it.currency, it.factor_id, (), "A1-A3"
viol, sm, n = set(), set(), 0
for path, au, fid, ex, stg in uses():
    n += 1
    if isinstance(fid, str) and fid.startswith("UNIT:"):
        tgt = fid[5:]
        if au is None or tgt == "None" or cv(x, au, tgt, ex) is None:
            viol.add(path)
        continue
    if au is None:
        viol.add(path)
        continue
    rec = x.factors.get(fid) if fid is not None else None
    if rec is None:
        continue
    if cv(x, au, rec.unit, ex) is None:
        viol.add(path)
    if list(rec.stages) != [stg]:
        sm.add("factors{%s}.stages" % fid)
out = {"ok": not viol and not sm, "n_checked": n, "violations": sorted(viol), "stage_mismatches": sorted(sm)}

#@unit SYS-03
def refs():
    for i, r in enumerate(x.materials):
        b = "materials[%d]" % i
        if r.composition is None:
            yield b + ".factor_id", r.factor_id
        else:
            for j, cp in enumerate(r.composition):
                yield b + ".composition[%d].factor_id" % j, cp.factor_id
        if r.epd is not None:
            yield b + ".epd.factor_id", r.epd.factor_id
        if r.installation_factor_id is not None:
            yield b + ".installation_factor_id", r.installation_factor_id
        if r.transport.delivery_factor_id is not None:
            yield b + ".transport.delivery_factor_id", r.transport.delivery_factor_id
        else:
            yield b + ".transport.factor_id", r.transport.factor_id
        yield b + ".end_of_life.haul_factor_id", r.end_of_life.haul_factor_id
        for j, rt in enumerate(r.end_of_life.routes):
            yield b + ".end_of_life.routes[%d].factor_id" % j, rt.factor_id
    for i, q in enumerate(x.equipment):
        b = "equipment[%d]" % i
        yield b + ".factor_id", q.factor_id
        for nm in ("eol_factor_id", "delivery_factor_id", "installation_factor_id"):
            v = getattr(q, nm)
            if v is not None:
                yield b + "." + nm, v
    for i, f in enumerate(x.construction.fuels):
        yield "construction.fuels[%d].factor_id" % i, f.factor_id
    for i, f in enumerate(x.construction.waste_streams):
        yield "construction.waste_streams[%d].factor_id" % i, f.factor_id
    op, ww = x.operation, x.water_waste
    for nm in ("gas_factor_id", "oil_factor_id", "district_heat_factor_id"):
        yield "operation." + nm, getattr(op, nm)
    for nm in ("water_factor_id", "sewage_factor_id", "waste_factor_id"):
        yield "water_waste." + nm, getattr(ww, nm)
    for i, a in enumerate(x.end_of_life.demolition_activities):
        yield "end_of_life.demolition_activities[%d].factor_id" % i, a.factor_id
    for i, h in enumerate(x.end_of_life.waste_hauls):
        yield "end_of_life.waste_hauls[%d].factor_id" % i, h.factor_id
    if x.summary_quantities.concrete_uptake_factor_id is not None:
        yield "summary_quantities.concrete_uptake_factor_id", x.summary_quantities.concrete_uptake_factor_id
    for i, it in enumerate(x.cost_items):
        yield "cost_items[%d].factor_id" % i, it.factor_id
bad, n = {}, 0
for path, fid in refs():
    n += 1
    if fid is None:
        key = path + " (no factor)"
    else:
        rec = x.factors.get(fid)
        if rec is None:
            key = "factors{%s} (no record)" % fid
        elif rec.licence_status != "PERMITTED_PUBLIC" or not rec.source_url:
            key = "factors{%s}.licence_status" % fid
        else:
            continue
    bad[key] = bad.get(key, 0) + 1
n += 1
if x.operation.grid.licence_status != "PERMITTED_PUBLIC":
    bad["operation.grid"] = 1
out = {"ok": not bad, "n_checked": n, "violations": sorted(bad), "n_references_affected": sum(bad.values())}

#@unit SYS-04
A = x.project.gross_floor_area
S = 0.0
for k in sorted(x.project.use_area_breakdown):
    S += x.project.use_area_breakdown[k]
if A is None or not A > 0.0:
    out = {"ok": False, "status": "INVALID", "sum": S, "residual": None}
else:
    r = A - S
    out = {"ok": abs(r) <= 1e-9 * A, "status": "EVALUATED", "sum": S, "residual": r}

#@unit QA-04
s = U["SYS-04"]
if s["status"] != "EVALUATED":
    out = {"ok": False, "status": "NOT_EVALUATED"}
else:
    out = {"ok": abs(s["residual"]) <= 1e-6 * x.project.gross_floor_area, "status": "EVALUATED"}

#@unit A13-05
qo, qi, sk = [], [], 0
for r in x.materials:
    Q, w = r.quantity, r.waste_rate
    if not nn(Q) or w is None or not 0.0 <= w < 1.0:
        qo.append(None); qi.append(None); sk += 1
    elif r.quantity_basis == "DESIGN":
        qi.append(Q); qo.append(Q / (1.0 - w))
    else:
        qo.append(Q); qi.append(Q * (1.0 - w))
out = {"q_ord": qo, "q_inst": qi, "n_skipped": sk}

#@unit X-13
qo, qi = U["A13-05"]["q_ord"], U["A13-05"]["q_inst"]
net, dis = [], []
for i, r in enumerate(x.materials):
    rho = r.reuse_rate
    if qo[i] is None or rho is None or not 0.0 <= rho <= 1.0:
        net.append(None); dis.append(None); continue
    d = (qo[i] - qi[i]) * (1.0 - rho)
    dis.append(d); net.append(qi[i] + d)
out = {"by_item": net, "waste_by_item": dis}

#@unit A13-02
val, parts, bad = [], [], 0
for r in x.materials:
    if r.composition is None:
        val.append(None); parts.append(None); continue
    s = v = 0.0; ok = True; wl = []
    for cp in r.composition:
        h = fac(x, cp.factor_id, "A1-A3", "kg")
        if h is None or not nn(cp.mass_fraction):
            ok = False; break
        s += cp.mass_fraction
        v += cp.mass_fraction * h[1] * h[0]
        wl.append((cp.factor_id, cp.mass_fraction, h[1]))
    if not ok or abs(s - 1.0) > 1e-6:
        val.append(None); parts.append(None); bad += 1
    else:
        val.append(v); parts.append(wl)
out = {"by_item": val, "n_invalid": bad, "_parts": parts}

#@unit X-15
comp = U["A13-02"]["by_item"]
kind, fv, cvv, unres, decl = [], [], [], 0, 0
for i, r in enumerate(x.materials):
    k = f = c = None
    epd = None
    if r.epd is not None:
        rec = x.factors.get(r.epd.factor_id) if r.epd.factor_id is not None else None
        if (rec is not None and list(r.epd.declared_stages) == list(rec.stages) and r.epd.declared_unit == rec.unit
                and r.epd.valid_until == rec.valid_until and rec.valid_until is not None
                and not rec.valid_until < x.project.assessment_date):
            epd = fac(x, r.epd.factor_id, "A1-A3", r.quantity_unit, r.conversions)
        if epd is None:
            decl += 1
    if epd is not None:
        k, f, c = "EPD", epd[0], epd[1]
    elif r.composition is not None:
        c = cv(x, r.quantity_unit, "kg", r.conversions)
        if comp[i] is not None and c is not None:
            k, f = "COMPOSITE", comp[i]
        else:
            c = None
    else:
        h = fac(x, r.factor_id, "A1-A3", r.quantity_unit, r.conversions)
        if h is not None:
            k, f, c = "GENERIC", h[0], h[1]
    if k is None:
        unres += 1
    kind.append(k); fv.append(f); cvv.append(c)
out = {"kind": kind, "factor": fv, "conv": cvv, "n_unresolved": unres, "n_epd_declined": decl}

#@unit A13-01
qo, rx, parts = U["A13-05"]["q_ord"], U["X-15"], U["A13-02"]["_parts"]
tot, bi, rl, sk = 0.0, [], [], set()
for i, r in enumerate(x.materials):
    k = rx["kind"][i]
    if k not in ("GENERIC", "COMPOSITE"):
        if k is None:
            sk.add(i)
        bi.append(0.0); rl.append([]); continue
    if qo[i] is None:
        sk.add(i); bi.append(0.0); rl.append([]); continue
    act = qo[i] * rx["conv"][i]
    e = act * rx["factor"][i]
    rl.append([(fid, act * fr * c) for fid, fr, c in parts[i]] if k == "COMPOSITE" else [(r.factor_id, act)])
    tot += e; bi.append(e)
out = {"value": tot, "by_item": bi, "n_skipped": len(sk), "_row_lines": rl, "_skipped_rows": sk}

#@unit A13-03
qo, rx = U["A13-05"]["q_ord"], U["X-15"]
tot, bi, rl, sk = 0.0, [], [], set()
for i, r in enumerate(x.materials):
    if rx["kind"][i] != "EPD":
        bi.append(0.0); rl.append([]); continue
    if qo[i] is None:
        sk.add(i); bi.append(0.0); rl.append([]); continue
    act = qo[i] * rx["conv"][i]
    e = act * rx["factor"][i]
    rl.append([(r.epd.factor_id, act)])
    tot += e; bi.append(e)
out = {"value": tot, "by_item": bi, "n_skipped": len(sk), "_row_lines": rl, "_skipped_rows": sk}

#@unit A13-04
a, b = U["A13-01"], U["A13-03"]
tot, bi, rl, sk = 0.0, [], [], 0
for i, r in enumerate(x.materials):
    rr = r.unquantified_cost_ratio
    if rr is None or rr == 0.0:
        bi.append(0.0); rl.append([]); continue
    if not 0.0 < rr < 1.0:
        sk += 1; bi.append(0.0); rl.append([]); continue
    g = rr / (1.0 - rr)
    e = (a["by_item"][i] + b["by_item"][i]) * g
    tot += e; bi.append(e)
    rl.append([(fid, act * g) for fid, act in a["_row_lines"][i] + b["_row_lines"][i]])
out = {"value": tot, "by_item": bi, "n_skipped": sk, "_row_lines": rl}

#@unit X-01
tot, bi, rl, sk = 0.0, [], [], set()
for j, q in enumerate(x.equipment):
    h = fac(x, q.factor_id, "A1-A3", q.quantity_unit)
    if not nn(q.quantity) or h is None:
        sk.add(j); bi.append(0.0); rl.append([]); continue
    act = q.quantity * h[1]
    e = act * h[0]
    tot += e; bi.append(e); rl.append([(q.factor_id, act)])
out = {"value": tot, "by_item": bi, "n_skipped": len(sk), "_row_lines": rl, "_skipped_rows": sk}

#@unit X-03
qo, rx, parts = U["A13-05"]["q_ord"], U["X-15"], U["A13-02"]["_parts"]
mass, em, tot = {}, {}, 0.0
for i, r in enumerate(x.materials):
    if rx["kind"][i] != "COMPOSITE" or qo[i] is None:
        continue
    kg = qo[i] * rx["conv"][i]
    for fid, fr, c in parts[i]:
        m = kg * fr
        e = m * c * x.factors[fid].value
        mass[fid] = mass.get(fid, 0.0) + m
        em[fid] = em.get(fid, 0.0) + e
        tot += e
out = {"value": tot, "mass_by_component": mass, "emission_by_component": em}

#@unit A4-01
tot, bi, rl, sk = 0.0, [], [], set()
for i, r in enumerate(x.materials):
    tr = r.transport
    if tr.delivery_factor_id is not None:
        bi.append(0.0); rl.append([]); continue
    h = fac(x, tr.factor_id, "A4", "tkm")
    if h is None or not nn(tr.mass_t) or not nn(tr.distance_km):
        sk.add(i); bi.append(0.0); rl.append([]); continue
    act = tr.mass_t * tr.distance_km * h[1]
    e = act * h[0]
    tot += e; bi.append(e); rl.append([(tr.factor_id, act)])
out = {"value": tot, "by_item": bi, "n_skipped": len(sk), "_row_lines": rl, "_skipped_rows": sk}

#@unit X-12
tot, bi, sk = 0.0, [], 0
for i, r in enumerate(x.materials):
    tr = r.transport
    if tr.delivery_factor_id is not None:
        bi.append(0.0); continue
    h = fac(x, tr.factor_id, "A4", "tkm")
    if h is None or not nn(tr.mass_t) or not nn(tr.distance_km) or not (tr.load_factor is not None and tr.load_factor > 0.0):
        sk += 1; bi.append(0.0); continue
    act = tr.mass_t * tr.distance_km * h[1] / tr.load_factor
    e = act * h[0]
    tot += e; bi.append(e)
out = {"value": tot, "by_item": bi, "n_skipped": sk}

#@unit A4-02
qo = U["A13-05"]["q_ord"]
tot, bi, rl, sk = 0.0, [], [], set()
for i, r in enumerate(x.materials):
    fid = r.transport.delivery_factor_id
    if fid is None:
        bi.append(0.0); rl.append([]); continue
    h = fac(x, fid, "A4", r.quantity_unit, r.conversions)
    if h is None or qo[i] is None:
        sk.add(i); bi.append(0.0); rl.append([]); continue
    act = qo[i] * h[1]
    e = act * h[0]
    tot += e; bi.append(e); rl.append([(fid, act)])
out = {"value": tot, "by_item": bi, "n_skipped": len(sk), "_row_lines": rl, "_skipped_rows": sk}

#@unit A5-01
kwh, g = x.construction.electricity_kwh, x.operation.grid
gu = gunit(g)
c = cv(x, "kWh", gu) if gu is not None else None
if not nn(kwh) or c is None or g.licence_status != "PERMITTED_PUBLIC":
    out = {"value": 0.0, "computed": False, "_lines": []}
else:
    e = kwh * c * g.construction_value
    out = {"value": e, "computed": True, "_lines": [(GRID, e)]}

#@unit A5-02
tot, ln, sk = 0.0, [], 0
for f in x.construction.fuels:
    h = fac(x, f.factor_id, "A5", f.unit, f.conversions)
    if not nn(f.quantity) or h is None:
        sk += 1; continue
    act = f.quantity * h[1]
    tot += act * h[0]; ln.append((f.factor_id, act))
out = {"value": tot, "n_skipped": sk, "_lines": ln}

#@unit A5-03
tot, ln, sk = 0.0, [], 0
for f in x.construction.waste_streams:
    h = fac(x, f.factor_id, "A5", "kg")
    if not nn(f.mass_kg) or h is None:
        sk += 1; continue
    act = f.mass_kg * h[1]
    tot += act * h[0]; ln.append((f.factor_id, act))
out = {"value": tot, "n_skipped": sk, "_lines": ln}

#@unit A5-04
p = {"power": U["A5-01"]["value"], "fuels": U["A5-02"]["value"], "waste": U["A5-03"]["value"]}
tot = 0.0
for k in ("power", "fuels", "waste"):
    tot += p[k]
out = {"value": tot, "parts": p, "other_assessed": False}

#@unit X-17
a, b = U["A13-01"]["by_item"], U["A13-03"]["by_item"]
CL = ("REBAR", "STRUCTURAL_STEEL", "CONCRETE", "TIMBER", "ENVELOPE", "INTERIOR")
def cls(r):
    if r.material_class in ("REBAR", "STRUCTURAL_STEEL", "CONCRETE", "TIMBER"):
        return r.material_class
    if r.quantity_unit == "m2":
        if r.construction_division in ("ROOF_EXTERIOR_WALL", "OPENINGS"):
            return "ENVELOPE"
        if r.construction_division == "INTERIOR":
            return "INTERIOR"
    return None
sq = x.summary_quantities
qmap = {"REBAR": sq.reinforcement_kg, "STRUCTURAL_STEEL": sq.steel_kg, "CONCRETE": sq.concrete_m3, "TIMBER": sq.timber_m3,
        "ENVELOPE": sq.envelope_m2, "INTERIOR": sq.interior_m2}
sums = {k: 0.0 for k in CL}
for i, r in enumerate(x.materials):
    k = cls(r)
    if k is not None:
        sums[k] += a[i] + b[i]
tot, bc = 0.0, {}
for k in CL:
    q = qmap[k]
    fb = sums[k] / q if q else 0.0
    e = q * fb
    tot += e
    bc[k] = {"quantity": q, "fbar": fb, "emission": e}
out = {"value": tot, "by_class": bc}

#@unit X-16
tot, bi, sk = 0.0, [], 0
for it in x.cost_items:
    pc, pb = x.price_index.get(it.price_year), x.price_index.get(it.factor_base_year)
    h = fac(x, it.factor_id, "A1-A3", it.currency)
    if not nn(it.amount) or h is None or pc is None or pb is None or not pc > 0.0 or not pb > 0.0:
        sk += 1; bi.append(0.0); continue
    e = it.amount * (pb / pc) * h[1] * h[0]
    tot += e; bi.append(e)
out = {"value": tot, "by_item": bi, "n_skipped": sk}

#@unit C1-01
tot, ln, sk = 0.0, [], 0
for a in x.end_of_life.demolition_activities:
    h = fac(x, a.factor_id, "C1", a.unit)
    if not nn(a.quantity) or h is None:
        sk += 1; continue
    act = a.quantity * h[1]
    tot += act * h[0]; ln.append((a.factor_id, act))
out = {"value": tot, "n_skipped": sk, "_lines": ln}

#@unit C2-01
tot, bi, rl, ln, sk, nh = 0.0, [], [], [], set(), 0
for i, r in enumerate(x.materials):
    eo = r.end_of_life
    h = fac(x, eo.haul_factor_id, "C2", "tkm")
    if h is None or not nn(eo.mass_kg) or not nn(eo.haul_distance_km):
        sk.add(i); bi.append(0.0); rl.append([]); continue
    act = eo.mass_kg / 1000.0 * eo.haul_distance_km * h[1]
    e = act * h[0]
    tot += e; bi.append(e); rl.append([(eo.haul_factor_id, act)])
for hl in x.end_of_life.waste_hauls:
    h = fac(x, hl.factor_id, "C2", "tkm")
    if h is None or not nn(hl.mass_t) or not nn(hl.distance_km):
        nh += 1; continue
    act = hl.mass_t * hl.distance_km * h[1]
    tot += act * h[0]; ln.append((hl.factor_id, act))
out = {"value": tot, "by_item": bi, "n_skipped": len(sk) + nh, "_row_lines": rl, "_lines": ln, "_skipped_rows": sk}

#@unit C3-01
tot, bi, rl, sk, part, rsk = 0.0, [], [], set(), set(), 0
for i, r in enumerate(x.materials):
    eo = r.end_of_life
    er, ln = 0.0, []
    if not nn(eo.mass_kg):
        sk.add(i)
    else:
        for rt in eo.routes:
            if rt.route == "LANDFILL":
                continue
            h = fac(x, rt.factor_id, "C3", "kg")
            if h is None or not nn(rt.fraction):
                rsk += 1; part.add(i); continue
            act = eo.mass_kg * rt.fraction * h[1]
            er += act * h[0]; ln.append((rt.factor_id, act))
    tot += er; bi.append(er); rl.append(ln)
out = {"value": tot, "by_item": bi, "n_skipped": len(sk), "n_routes_skipped": rsk, "_row_lines": rl, "_skipped_rows": sk, "_partial_rows": part}

#@unit C4-01
tot, bi, rl, sk, part, rsk = 0.0, [], [], set(), set(), 0
for i, r in enumerate(x.materials):
    eo = r.end_of_life
    er, ln = 0.0, []
    if not nn(eo.mass_kg):
        sk.add(i)
    else:
        for rt in eo.routes:
            if rt.route != "LANDFILL":
                continue
            h = fac(x, rt.factor_id, "C4", "kg")
            if h is None or not nn(rt.fraction):
                rsk += 1; part.add(i); continue
            act = eo.mass_kg * rt.fraction * h[1]
            er += act * h[0]; ln.append((rt.factor_id, act))
    tot += er; bi.append(er); rl.append(ln)
out = {"value": tot, "by_item": bi, "n_skipped": len(sk), "n_routes_skipped": rsk, "_row_lines": rl, "_skipped_rows": sk, "_partial_rows": part}

#@unit X-14
tot, bi, rl, sk = 0.0, [], [], set()
for j, q in enumerate(x.equipment):
    h = fac(x, q.eol_factor_id, "C3", "kg")
    if h is None or not nn(q.end_of_life_mass_kg):
        sk.add(j); bi.append(0.0); rl.append([]); continue
    act = q.end_of_life_mass_kg * h[1]
    e = act * h[0]
    tot += e; bi.append(e); rl.append([(q.eol_factor_id, act)])
out = {"value": tot, "by_item": bi, "n_skipped": len(sk), "_row_lines": rl, "_skipped_rows": sk}

#@unit C-05
qi = U["A13-05"]["q_inst"]
viol, under, un = [], [], 0
for i, r in enumerate(x.materials):
    eo = r.end_of_life
    s, neg = 0.0, False
    for rt in eo.routes:
        s += rt.fraction
        neg = neg or rt.fraction < 0.0
    if neg or s > 1.0 + 1e-6:
        viol.append("materials[%d].end_of_life.routes" % i)
    elif s < 1.0 - 1e-6:
        under.append("materials[%d].end_of_life.routes" % i)
    c = cv(x, r.quantity_unit, "kg", r.conversions)
    if c is None or qi[i] is None or eo.mass_kg is None:
        un += 1
    elif eo.mass_kg > qi[i] * c * (1.0 + 1e-6):
        viol.append("materials[%d].end_of_life.mass_kg" % i)
out = {"ok": not viol, "violations": viol, "under_allocated": under, "n_mass_unchecked": un}

#@unit X-09
RTS = ("REUSE", "RECYCLE", "PROCESSING", "LANDFILL")
mass, em, tot = {}, {}, 0.0
for r in x.materials:
    eo = r.end_of_life
    if not nn(eo.mass_kg):
        continue
    mr = mass.setdefault(r.material_class, {q: 0.0 for q in RTS})
    er = em.setdefault(r.material_class, {q: 0.0 for q in RTS})
    for rt in eo.routes:
        if not nn(rt.fraction):
            continue
        m = eo.mass_kg * rt.fraction
        mr[rt.route] += m
        h = fac(x, rt.factor_id, "C4" if rt.route == "LANDFILL" else "C3", "kg")
        if h is not None:
            e = m * h[1] * h[0]
            er[rt.route] += e; tot += e
out = {"value": tot, "mass": mass, "emission": em}

#@unit X-10
qo, qi = U["A13-05"]["q_ord"], U["A13-05"]["q_inst"]
res, was, exc = 0.0, 0.0, 0
for i, r in enumerate(x.materials):
    c = cv(x, r.quantity_unit, "kg", r.conversions)
    if c is None or qo[i] is None or not nn(r.end_of_life.mass_kg):
        exc += 1; continue
    k = 1 + U["B4-03"]["by_item"][i]
    res += qo[i] * c * k
    was += ((qo[i] - qi[i]) * c + r.end_of_life.mass_kg) * k
for j, q in enumerate(x.equipment):
    if not nn(q.end_of_life_mass_kg):
        exc += 1; continue
    was += q.end_of_life_mass_kg * (1 + len(U["B4-01"]["events"][j]))
out = {"resource_kg": res, "waste_kg": was, "n_excluded": exc}

#@unit STO-01
sq = x.summary_quantities
if not (nn(sq.timber_m3) and nn(sq.timber_dry_density_kg_per_m3) and nn(sq.timber_carbon_fraction)):
    out = {"value": None}
else:
    out = {"value": sq.timber_m3 * sq.timber_dry_density_kg_per_m3 * sq.timber_carbon_fraction * (44.0 / 12.0)}

#@unit STO-02
sq = x.summary_quantities
h = fac(x, sq.concrete_uptake_factor_id, "MEMO", "m3")
out = {"value": None} if (h is None or not nn(sq.concrete_m3)) else {"value": sq.concrete_m3 * h[1] * h[0]}

#@unit B4-01
ev, n = [], 0
for q in x.equipment:
    e = explicit(T, q.replacement_event_list) if q.replacement_event_list is not None else periodic(T, q.service_life)
    ev.append(e); n += len(e)
out = {"events": ev, "n_events": n}

#@unit B4-03
out = {"by_item": [len(periodic(T, r.refresh_cycle)) for r in x.materials]}

#@unit B4-02
Y = Yn(T)
by = [0.0] * (Y + 1)
qo = U["A13-05"]["q_ord"]
src = [U[u] for u in ("A13-01", "A13-03", "A4-01", "A4-02", "C2-01", "C3-01", "C4-01")]
inc_m = set()
for s in src:
    inc_m |= s["_skipped_rows"]
inc_m |= U["C3-01"]["_partial_rows"] | U["C4-01"]["_partial_rows"]
def inst(r, q):
    f = r.installation_factor_id
    if f is None or q is None:
        return None
    h = fac(x, f, "A5", r.quantity_unit, r.conversions)
    return None if h is None else (f, q * h[1])
tot, part, bm, be, ml, el = 0.0, 0, [], [], [], []
for i, r in enumerate(x.materials):
    evs = periodic(T, r.refresh_cycle) if U["B4-03"]["by_item"][i] else []
    lines = []
    for s in src:
        lines += s["_row_lines"][i]
    it = inst(r, qo[i])
    if it is not None:
        lines.append(it)
    u = 0.0
    for s in src:
        u += s["by_item"][i]
    if it is not None:
        u += it[1] * x.factors[it[0]].value
    e = 0.0
    for tau in evs:
        e += u; by[ycell(tau)] += u
    if evs and (i in inc_m or (r.installation_factor_id is not None and it is None)):
        part += 1
    tot += e; bm.append(e)
    ml.append([(f, a * len(evs)) for f, a in lines] if evs else [])
inc_e = U["X-01"]["_skipped_rows"] | U["X-14"]["_skipped_rows"]
def extra(q):
    ls, bad = [], False
    for f, stg in ((q.delivery_factor_id, "A4"), (q.installation_factor_id, "A5")):
        if f is None:
            continue
        h = fac(x, f, stg, q.quantity_unit)
        if h is None or not nn(q.quantity):
            bad = True; continue
        ls.append((f, q.quantity * h[1]))
    return ls, bad
for j, q in enumerate(x.equipment):
    evs = U["B4-01"]["events"][j]
    ex, bad = extra(q)
    lines = U["X-01"]["_row_lines"][j] + ex + U["X-14"]["_row_lines"][j]
    u = 0.0
    for f, a in lines:
        u += a * x.factors[f].value
    e = 0.0
    for tau in evs:
        e += u; by[ycell(tau)] += u
    if evs and (j in inc_e or bad):
        part += 1
    tot += e; be.append(e)
    el.append([(f, a * len(evs)) for f, a in lines] if evs else [])
out = {"value": tot, "by_item_material": bm, "by_item_equipment": be, "by_year": by, "n_partial": part,
       "_mat_lines": ml, "_eq_lines": el, "_extra": extra, "_inst": inst}

#@unit X-08
qo = U["A13-05"]["q_ord"]
inst, extra = U["B4-02"]["_inst"], U["B4-02"]["_extra"]
ue, cnt, expl = {}, {}, 0.0
src = [U[u] for u in ("A13-01", "A13-03", "A4-01", "A4-02", "C2-01", "C3-01", "C4-01")]
for i, r in enumerate(x.materials):
    n = U["B4-03"]["by_item"][i]
    if not n:
        continue
    u = 0.0
    for s in src:
        u += s["by_item"][i]
    it = inst(r, qo[i])
    if it is not None:
        u += it[1] * x.factors[it[0]].value
    key = repr(float(r.refresh_cycle))
    ue[key] = ue.get(key, 0.0) + u; cnt[key] = n
for j, q in enumerate(x.equipment):
    evs = U["B4-01"]["events"][j]
    if not evs:
        continue
    u = U["X-01"]["by_item"][j] + U["X-14"]["by_item"][j]
    for f, a in extra(q)[0]:
        u += a * x.factors[f].value
    if q.replacement_event_list is not None:
        expl += u * len(evs); continue
    key = repr(float(q.service_life))
    ue[key] = ue.get(key, 0.0) + u; cnt[key] = len(evs)
bc, tot = {}, expl
for key in sorted(ue, key=float):
    e = cnt[key] * ue[key]
    bc[key] = {"count": cnt[key], "unit_emission": ue[key], "emission": e}
    tot += e
out = {"value": tot, "by_cycle": bc, "explicit": expl}

#@unit B3-01
Y = Yn(T)
by = [0.0] * (Y + 1)
tot, sk, ml, el = 0.0, 0, [], []
a, b = U["A13-01"], U["A13-03"]
def rows(e0, r, skipy, lines, store):
    global tot
    if r == 0.0 or e0 == 0.0:
        store.append([]); return
    yrs = 0.0
    for y in range(1, Y + 1):
        if y in skipy:
            continue
        e = e0 * r * wy(T, y)
        by[y] += e
        tot += e
        yrs += wy(T, y)
    store.append([(f, ac * r * yrs) for f, ac in lines])
for i, m in enumerate(x.materials):
    r = m.repair_rate
    if not nn(r):
        sk += 1; ml.append([]); continue
    skipy = {ycell(t) for t in periodic(T, m.refresh_cycle)} if U["B4-03"]["by_item"][i] else set()
    rows(a["by_item"][i] + b["by_item"][i], r, skipy, a["_row_lines"][i] + b["_row_lines"][i], ml)
for j, q in enumerate(x.equipment):
    r = q.repair_rate
    if not nn(r):
        sk += 1; el.append([]); continue
    rows(U["X-01"]["by_item"][j], r, {ycell(t) for t in U["B4-01"]["events"][j]}, U["X-01"]["_row_lines"][j], el)
out = {"value": tot, "by_year": by, "n_skipped": sk, "_mat_lines": ml, "_eq_lines": el}

#@unit B3-02
tot, sk = 0.0, 0
a, b = U["A13-01"]["by_item"], U["A13-03"]["by_item"]
for i, m in enumerate(x.materials):
    if nn(m.repair_rate):
        tot += (a[i] + b[i]) * m.repair_rate * T
    else:
        sk += 1
for j, q in enumerate(x.equipment):
    if nn(q.repair_rate):
        tot += U["X-01"]["by_item"][j] * q.repair_rate * T
    else:
        sk += 1
out = {"value": tot, "n_skipped": sk}

#@unit B1-01
tot, sk = 0.0, 0
for d in x.refrigerants:
    if nn(d.charge_mass_kg) and nn(d.gwp):
        tot += d.charge_mass_kg * d.gwp
    else:
        sk += 1
out = {"value": tot, "n_skipped": sk}

#@unit B1-02
Y = Yn(T)
by = [0.0] * (Y + 1)
tot, sk, bi, stt = 0.0, 0, [], []
for d in x.refrigerants:
    if not (nn(d.charge_mass_kg) and nn(d.gwp) and rat(d.annual_leak_rate)):
        sk += 1; bi.append(0.0); stt.append(None); continue
    evs = sorted(explicit(T, d.change_years)) if d.change_years is not None else periodic(T, d.service_life)
    chi = {}
    for tau in evs:
        y = ycell(tau); chi[y] = chi.get(y, 0) + 1
    m0 = d.charge_mass_kg
    u = m0                                        # u_{d,0} = m_{0,d}（年初の残存量）
    before, ed = [], 0.0
    for y in range(1, Y + 1):
        leak = u * d.annual_leak_rate * wy(T, y)
        e = leak * d.gwp
        by[y] += e; ed += e
        if not d.top_up:
            u -= leak                             # 補充なし：u <- u(1 - r w)
        for _ in range(chi.get(y, 0)):
            before.append((y, u)); u = m0         # 交換：年末に m0 へ戻す
    tot += ed; bi.append(ed); stt.append({"before": before, "end": u})
out = {"value": tot, "by_item": bi, "by_year": by, "n_skipped": sk, "_state": stt, "_lines": [(REFR, tot)]}

#@unit B1-03
Y = Yn(T)
by = [0.0] * (Y + 1)
tot, sk = 0.0, 0
for d, st in zip(x.refrigerants, U["B1-02"]["_state"]):
    if st is None or not rat(d.replacement_loss_rate):
        sk += 1; continue
    for y, m in st["before"]:
        e = m * d.replacement_loss_rate * d.gwp
        by[y] += e; tot += e
out = {"value": tot, "by_year": by, "n_skipped": sk, "_lines": [(REFR, tot)]}

#@unit B1-04
tot, sk = 0.0, 0
for d, st in zip(x.refrigerants, U["B1-02"]["_state"]):
    if st is None or not rat(d.end_of_life_recovery_rate):
        sk += 1; continue
    tot += st["end"] * (1.0 - d.end_of_life_recovery_rate) * d.gwp
out = {"value": tot, "n_skipped": sk, "_lines": [(REFR, tot)]}

#@unit B5-01
bd = x.boundary
Y = Yn(T)
by = [0.0] * (Y + 1)
if bd.reconstruction_scenario == "NONE":
    out = {"value": 0.0, "n_events": 0, "by_year": by, "computed": True, "_mult": 0.0}
elif not rat(bd.reconstruction_scope_fraction):
    out = {"value": 0.0, "n_events": 0, "by_year": by, "computed": False, "_mult": 0.0}
else:
    base = 0.0
    for u in ("A13-01", "A13-03", "A13-04", "X-01", "A4-01", "A4-02", "A5-04", "C1-01", "C2-01", "C3-01", "C4-01", "X-14"):
        base += U[u]["value"]
    evs = periodic(T, bd.replacement_cycle)
    tot = 0.0
    for tau in evs:
        e = bd.reconstruction_scope_fraction * base
        by[ycell(tau)] += e; tot += e
    out = {"value": tot, "n_events": len(evs), "by_year": by, "computed": True, "_mult": len(evs) * bd.reconstruction_scope_fraction}

#@unit X-06
g = x.operation.grid
Y = Yn(T)
v = grid_vals(g, Y)
out = {"by_year": [0.0] + v, "matches_table": same(v, g.table[:Y]), "source": "DESCRIPTOR" if grid_ok(g) else "TABLE"}

#@unit B6-04
op = x.operation
Y = Yn(T)
eu = aunit(op.electricity.unit)
gu, xu = aunit(op.onsite_generation.unit), aunit(op.onsite_export.unit)
cg = cv(x, gu, eu) if gu is not None and eu is not None else None
cx = cv(x, xu, eu) if xu is not None and eu is not None else None
mt = all(same(prof(p, Y), p.table[:Y]) for p in (op.electricity, op.onsite_generation, op.onsite_export))
if eu is None or cg is None or cx is None:
    out = {"by_year": [0.0] * (Y + 1), "computed": False, "descriptors_match_tables": mt}
else:
    c, gg, xx = prof(op.electricity, Y), prof(op.onsite_generation, Y), prof(op.onsite_export, Y)
    out = {"by_year": [0.0] + [max(0.0, c[k] - (gg[k] * cg - xx[k] * cx)) for k in range(Y)], "computed": True,
           "descriptors_match_tables": mt}

#@unit B6-01
net, gm = U["B6-04"]["by_year"], U["X-06"]["by_year"]
g = x.operation.grid
eu, gu = aunit(x.operation.electricity.unit), gunit(g)
c = cv(x, eu, gu) if eu is not None and gu is not None else None
ok = g.licence_status == "PERMITTED_PUBLIC" and U["B6-04"]["computed"] and c is not None
out = {"by_year": [0.0] + [(net[y] * c * gm[y] if ok else 0.0) for y in range(1, len(net))], "computed": ok}

#@unit B6-02
op = x.operation
Y = Yn(T)
by = [0.0] * (Y + 1)
used, sk, mt = [], 0, True
for p, f in ((op.gas, op.gas_factor_id), (op.oil, op.oil_factor_id), (op.district_heat, op.district_heat_factor_id)):
    mt = mt and same(prof(p, Y), p.table[:Y])
    h = fac(x, f, "B6", aunit(p.unit))
    if h is None:
        sk += 1; continue
    v = prof(p, Y)
    used.append((v, f, h[1]))
    for k in range(Y):
        by[k + 1] += v[k] * h[1] * h[0]
ln = [(f, sum(wy(T, y) * v[y - 1] * c for y in range(1, Y + 1))) for v, f, c in used]
out = {"by_year": by, "n_skipped": sk, "descriptors_match_tables": mt, "_lines": ln}

#@unit B6-03
Y = Yn(T)
el, fu = U["B6-01"]["by_year"], U["B6-02"]["by_year"]
tot = et = 0.0
for y in range(1, Y + 1):
    tot += wy(T, y) * (el[y] + fu[y]); et += wy(T, y) * el[y]
out = {"value": tot, "_lines": [(GRID, et)] + U["B6-02"]["_lines"]}

#@unit B2-01
Y = Yn(T)
el = U["B6-01"]["by_year"]
rho = x.operation.facility_management_ratio
if not rat(rho):
    out = {"value": 0.0, "computed": False}
else:
    s = 0.0
    for y in range(1, Y + 1):
        s += wy(T, y) * el[y]
    out = {"value": s * rho, "computed": True}

#@unit X-11
Y = Yn(T)
gm, g = U["X-06"]["by_year"], x.operation.grid
A = x.project.gross_floor_area
gu = gunit(g)
c = cv(x, "kWh", gu) if gu is not None else None
I = x.operation.electricity_per_m2_per_year
if not pos(A) or not nn(I) or c is None or g.licence_status != "PERMITTED_PUBLIC":
    out = {"value": None}
else:
    G = 0.0
    for y in range(1, Y + 1):
        G += wy(T, y) * gm[y]
    out = {"value": A * I * c * G}

#@unit B7-01
Y = Yn(T)
p, f = x.water_waste.water, x.water_waste.water_factor_id
by = [0.0] * (Y + 1)
h = fac(x, f, "B7", aunit(p.unit))
v = prof(p, Y) if h is not None else None
if h is not None:
    for k in range(Y):
        by[k + 1] += v[k] * h[1] * h[0]
ln = [(f, sum(wy(T, y) * v[y - 1] * h[1] for y in range(1, Y + 1)))] if h is not None else []
out = {"by_year": by, "n_skipped": 0 if h is not None else 1, "descriptors_match_tables": same(prof(p, Y), p.table[:Y]), "_lines": ln}

#@unit B7-02
Y = Yn(T)
p, f = x.water_waste.sewage, x.water_waste.sewage_factor_id
by = [0.0] * (Y + 1)
h = fac(x, f, "B7", aunit(p.unit))
v = prof(p, Y) if h is not None else None
if h is not None:
    for k in range(Y):
        by[k + 1] += v[k] * h[1] * h[0]
ln = [(f, sum(wy(T, y) * v[y - 1] * h[1] for y in range(1, Y + 1)))] if h is not None else []
out = {"by_year": by, "n_skipped": 0 if h is not None else 1, "descriptors_match_tables": same(prof(p, Y), p.table[:Y]), "_lines": ln}

#@unit B7-03
Y = Yn(T)
p, f = x.water_waste.municipal_waste, x.water_waste.waste_factor_id
by = [0.0] * (Y + 1)
h = fac(x, f, "B7", aunit(p.unit))
v = prof(p, Y) if h is not None else None
if h is not None:
    for k in range(Y):
        by[k + 1] += v[k] * h[1] * h[0]
ln = [(f, sum(wy(T, y) * v[y - 1] * h[1] for y in range(1, Y + 1)))] if h is not None else []
out = {"by_year": by, "n_skipped": 0 if h is not None else 1, "descriptors_match_tables": same(prof(p, Y), p.table[:Y]), "_lines": ln}

#@unit B7-04
Y = Yn(T)
a, b, c = U["B7-01"]["by_year"], U["B7-02"]["by_year"], U["B7-03"]["by_year"]
tot = 0.0
for y in range(1, Y + 1):
    tot += wy(T, y) * (a[y] + b[y] + c[y])
out = {"value": tot, "_lines": U["B7-01"]["_lines"] + U["B7-02"]["_lines"] + U["B7-03"]["_lines"]}

#@unit X-02
v = lambda u: U[u]["value"]
full = {"A1-A3": v("A13-01") + v("A13-03") + v("A13-04") + v("X-01"), "A4": v("A4-01") + v("A4-02"), "A5": v("A5-04"),
        "B1": v("B1-02") + v("B1-03") + v("B1-04"), "B2": v("B2-01"), "B3": v("B3-01"), "B4": v("B4-02"), "B5": v("B5-01"),
        "B6": v("B6-03") - v("B2-01"), "B7": v("B7-04"), "C1": v("C1-01"), "C2": v("C2-01"), "C3": v("C3-01") + v("X-14"),
        "C4": v("C4-01")}
inc = set(x.boundary.included_lifecycle_stages)
bs = {s: full[s] for s in STAGES if s in inc}
if "B6" in inc and "B2" not in inc:
    bs["B6"] = v("B6-03")
SU = {"A1-A3": ("A13-01", "A13-03", "A13-04", "X-01"), "A4": ("A4-01", "A4-02"), "A5": ("A5-01", "A5-02", "A5-03"),
      "B1": ("B1-02", "B1-03", "B1-04"), "B2": ("B2-01", "B6-01"), "B3": ("B3-01",), "B4": ("B4-02",), "B5": ("B5-01",),
      "B6": ("B6-01", "B6-02"), "B7": ("B7-01", "B7-02", "B7-03"), "C1": ("C1-01",), "C2": ("C2-01",), "C3": ("C3-01", "X-14"),
      "C4": ("C4-01",)}
def bad(r):
    return bool(r.get("n_skipped") or r.get("n_routes_skipped") or r.get("n_partial") or r.get("computed") is False)
iu = []
for s in STAGES:
    if s in inc:
        for u in SU[s]:
            if bad(U[u]) and u not in iu:
                iu.append(u)
out = {"by_stage": bs, "by_stage_all": full, "complete": not iu, "incomplete_units": sorted(iu)}

#@unit X-04
def stage_lines():
    o = {"A1-A3": flat(U["A13-01"]["_row_lines"]) + flat(U["A13-03"]["_row_lines"]) + flat(U["A13-04"]["_row_lines"]) + flat(U["X-01"]["_row_lines"]),
         "A4": flat(U["A4-01"]["_row_lines"]) + flat(U["A4-02"]["_row_lines"]),
         "A5": U["A5-01"]["_lines"] + U["A5-02"]["_lines"] + U["A5-03"]["_lines"],
         "B1": U["B1-02"]["_lines"] + U["B1-03"]["_lines"] + U["B1-04"]["_lines"],
         "B2": [(GRID, U["B2-01"]["value"])],
         "B3": flat(U["B3-01"]["_mat_lines"]) + flat(U["B3-01"]["_eq_lines"]),
         "B4": flat(U["B4-02"]["_mat_lines"]) + flat(U["B4-02"]["_eq_lines"]),
         "B6": U["B6-03"]["_lines"] + [(GRID, -U["B2-01"]["value"])],
         "B7": U["B7-04"]["_lines"], "C1": U["C1-01"]["_lines"],
         "C2": flat(U["C2-01"]["_row_lines"]) + U["C2-01"]["_lines"],
         "C3": flat(U["C3-01"]["_row_lines"]) + flat(U["X-14"]["_row_lines"]), "C4": flat(U["C4-01"]["_row_lines"])}
    k = U["B5-01"]["_mult"]
    o["B5"] = [(f, a * k) for s in ("A1-A3", "A4", "A5", "C1", "C2", "C3", "C4") for f, a in o[s]] if k else []
    return o
bg = {g: 0.0 for g in x.gases}
grid = refr = 0.0
rec, used = {}, set()
SL = stage_lines()
for s, ls in SL.items():
    st = 0.0
    for f, a in ls:
        if f == GRID:
            grid += a; st += a
        elif f == REFR:
            refr += a; st += a
        else:
            r = x.factors[f]
            used.add(f)
            st += a * r.value
            for g in x.gases:
                bg[g] += a * r.gas_amounts[g]
    rec[s] = st
fg = 0.0
for g in x.gases:
    fg += x.gwp[g] * bg[g]
out = {"value": fg + grid + refr, "by_gas": bg, "co2e_from_gases": fg, "grid_co2e": grid, "refrigerant_co2e": refr,
       "by_stage_recomputed": rec, "_used": used, "_stage_lines": SL}

#@unit X-05
bs = {}
for s, ls in U["X-04"]["_stage_lines"].items():
    st = 0.0
    for f, a in ls:
        if f == GRID:
            st += a
        elif f != REFR:
            st += a * x.factors[f].gas_amounts["CO2"]
    bs[s] = st
inc = set(x.boundary.included_lifecycle_stages)
tot = 0.0
for s in STAGES:
    if s in inc:
        tot += bs[s]
if "B6" in inc and "B2" not in inc:
    tot += bs["B2"]
out = {"value": tot, "by_stage_co2": {s: bs[s] for s in STAGES}}

#@unit X-07
Y = Yn(T)
inc = set(x.boundary.included_lifecycle_stages)
st = U["X-02"]["by_stage_all"]
ser = [0.0] * (Y + 1)
for s in ("A1-A3", "A4", "A5"):
    if s in inc:
        ser[0] += st[s]
sh = x.operation.facility_management_ratio if U["B2-01"]["computed"] else 0.0
for y in range(1, Y + 1):
    e = 0.0
    el = wy(T, y) * U["B6-01"]["by_year"][y]
    if "B6" in inc:
        e += (el * (1.0 - sh) if "B2" in inc else el) + wy(T, y) * U["B6-02"]["by_year"][y]
    if "B2" in inc:
        e += el * sh
    if "B7" in inc:
        e += wy(T, y) * (U["B7-01"]["by_year"][y] + U["B7-02"]["by_year"][y] + U["B7-03"]["by_year"][y])
    if "B1" in inc:
        e += U["B1-02"]["by_year"][y] + U["B1-03"]["by_year"][y]
    if "B3" in inc:
        e += U["B3-01"]["by_year"][y]
    if "B4" in inc:
        e += U["B4-02"]["by_year"][y]
    if "B5" in inc:
        e += U["B5-01"]["by_year"][y]
    ser[y] += e
last = Y if Y >= 1 else 0
for s in ("C1", "C2", "C3", "C4"):
    if s in inc:
        ser[last] += st[s]
if "B1" in inc:
    ser[last] += U["B1-04"]["value"]
cum, run = [], 0.0
for v in ser:
    run += v; cum.append(run)
out = {"by_year": ser, "cumulative": cum, "value": run}

#@unit SUM-01
bs = U["X-02"]["by_stage"]
t = 0.0
for s in ("A1-A3", "A4", "A5"):
    if s in bs:
        t += bs[s]
out = {"value": t, "complete": U["X-02"]["complete"]}

#@unit SUM-02
bs = U["X-02"]["by_stage"]
t = 0.0
for s in ("A1-A3", "A4", "A5", "B1", "B2", "B3", "B4", "B5", "C1", "C2", "C3", "C4"):
    if s in bs:
        t += bs[s]
out = {"value": t, "complete": U["X-02"]["complete"]}

#@unit SUM-03
bs = U["X-02"]["by_stage"]
t = 0.0
for s in STAGES:
    if s in bs:
        t += bs[s]
out = {"value": t, "complete": U["X-02"]["complete"]}

#@unit SUM-04
A = x.project.gross_floor_area
out = {"value": U["SUM-03"]["value"] / A if (A is not None and A > 0.0) else None}

#@unit SUM-05
A = x.project.gross_floor_area
out = {"value": U["SUM-03"]["value"] / (A * T) if (A is not None and A > 0.0 and T > 0.0) else None}

#@unit SUM-06
out = {"value": U["SUM-03"]["value"] / 1000.0}

#@unit SUM-07
bs, C = U["X-02"]["by_stage"], U["SUM-03"]["value"]
if not C > 0.0 or any(v < 0.0 for v in bs.values()):
    out = {"defined": False, "by_stage": {}}
else:
    out = {"defined": True, "by_stage": {s: v / C for s, v in bs.items()}}

#@unit SUM-08
base = BASELINES.get(x.boundary.baseline_scenario)
if base is None:
    out = {"status": "NO_BASELINE", "delta": None, "saving": None}
else:
    why = []
    if base.project.gross_floor_area != x.project.gross_floor_area:
        why.append("AREA")
    if base.boundary.study_period != T:
        why.append("PERIOD")
    if set(base.boundary.included_lifecycle_stages) != set(x.boundary.included_lifecycle_stages):
        why.append("STAGES")
    if base.boundary.results_gas_scope != x.boundary.results_gas_scope:
        why.append("GAS_SCOPE")
    if {f.release_year for f in base.factors.values()} != {f.release_year for f in x.factors.values()}:
        why.append("FACTOR_VERSION")
    if why:
        out = {"status": "NOT_COMPARABLE", "reasons": why, "delta": None, "saving": None}
    else:
        b = LEDGER_SUM03(base)
        p = U["SUM-03"]["value"]
        out = {"status": "COMPARED", "baseline": b, "delta": p - b, "saving": (b - p) / b if b > 0.0 else None}

#@unit QA-01
viol = []
st, ag = U["X-02"]["by_stage_all"], U["X-04"]["by_stage_recomputed"]
for s in STAGES:
    if abs(st[s] - ag[s]) > 1e-9 * max(abs(st[s]), 1.0):
        viol.append("stage %s" % s)
a, b = U["A13-01"]["by_item"], U["A13-03"]["by_item"]
c, d = U["A4-01"]["by_item"], U["A4-02"]["by_item"]
for i in range(len(x.materials)):
    if a[i] != 0.0 and b[i] != 0.0:
        viol.append("materials[%d] A13-01/A13-03" % i)
    if c[i] != 0.0 and d[i] != 0.0:
        viol.append("materials[%d] A4-01/A4-02" % i)
out = {"ok": not viol, "violations": viol}

#@unit QA-02
viol, warn = [], []
for nm, rows_, at in (("equipment", x.equipment, "replacement_event_list"), ("refrigerants", x.refrigerants, "change_years")):
    for i, r in enumerate(rows_):
        L = getattr(r, at) or ()
        if any(not (t >= 0 and theta(T, t)) for t in L):
            viol.append("%s[%d].%s" % (nm, i, at))
        if any(t == 0 for t in L):
            warn.append("%s[%d].%s" % (nm, i, at))
out = {"ok": not viol, "violations": viol, "warnings": warn}

#@unit QA-03
viol = []
for f in sorted(U["X-04"]["_used"]):
    r = x.factors[f]
    if r.licence_status != "PERMITTED_PUBLIC" or not r.source_url:
        viol.append(f)
out = {"ok": not viol, "violations": viol, "n_used": len(U["X-04"]["_used"])}
