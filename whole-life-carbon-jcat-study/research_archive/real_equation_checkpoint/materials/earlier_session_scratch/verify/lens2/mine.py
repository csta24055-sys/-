"""Independent re-derivation of selected units, written from the written definitions only
(units.json reference_semantics + refcalc/base.py docstring).  Does not import refcalc unit code.

Every function takes the scenario and a dict ``R`` of my own earlier results.
``ext`` holds reference results for the units outside my list (A5-04, B7-04, C1-01).
"""
import math

PERMITTED = "PERMITTED_PUBLIC"
STAGES = ("A1-A3", "A4", "A5", "B1", "B2", "B3", "B4", "B5", "B6", "B7", "C1", "C2", "C3", "C4")


# ---------------------------------------------------------------- conventions
def n_years(T):
    return math.ceil(T)


def weights(T):
    return [0.0] + [min(1.0, T - (y - 1)) for y in range(1, n_years(T) + 1)]


def periodic(T, L):
    out = []
    if L is None or L <= 0:
        return out
    n = 1
    while n * L < T:
        out.append(n * L)
        n += 1
    return out


def explicit(T, years):
    return [float(t) for t in years if 0 < t < T]


def fac(scn, fid):
    if fid is None:
        return None
    rec = scn.factors.get(fid)
    if rec is None or rec.licence_status != PERMITTED:
        return None
    return rec


def conv(scn, a, b, extra=()):
    if a == b:
        return 1.0
    for c in extra:
        if c.from_unit == a and c.to_unit == b:
            return c.factor
    for c in scn.unit_conversions:
        if c.from_unit == a and c.to_unit == b:
            return c.factor
    return None


# ---------------------------------------------------------------- A1-A3
def a13_05(scn, R):
    q_ord, q_inst, n_skipped = [], [], 0
    for row in scn.materials:
        Q, w = row.quantity, row.waste_rate
        if Q is None or w is None or not (0.0 <= w < 1.0) or Q < 0.0:
            q_ord.append(None); q_inst.append(None); n_skipped += 1
            continue
        if row.quantity_basis == "DESIGN":
            q_inst.append(Q); q_ord.append(Q / (1.0 - w))
        else:
            q_ord.append(Q); q_inst.append(Q * (1.0 - w))
    return {"q_ord": q_ord, "q_inst": q_inst, "n_skipped": n_skipped}


def a13_02(scn, R):
    by_item, n_invalid = [], 0
    for row in scn.materials:
        if row.composition is None:
            by_item.append(None)
            continue
        ok = abs(sum(c.mass_fraction for c in row.composition) - 1.0) <= 1e-6
        f = 0.0
        for c in row.composition:
            rec = fac(scn, c.factor_id)
            if rec is None or rec.unit != "kg" or list(rec.stages) != ["A1-A3"]:
                ok = False
                break
            f += c.mass_fraction * rec.value
        if ok:
            by_item.append(f)
        else:
            by_item.append(None); n_invalid += 1
    return {"by_item": by_item, "n_invalid": n_invalid}


def epd_applicable(scn, row, opts):
    """Licence, stages exactly A1-A3, unit convertible, valid at the assessment date."""
    e = row.epd
    if e is None:
        return None
    rec = fac(scn, e.factor_id)
    if rec is None:
        return None
    src = opts.get("epd_source", "record")
    stages = rec.stages if src == "record" else e.declared_stages
    unit = rec.unit if src == "record" else e.declared_unit
    valid = rec.valid_until if src == "record" else e.valid_until
    if list(stages) != ["A1-A3"]:
        return None
    c = conv(scn, row.quantity_unit, unit, row.conversions)
    if c is None:
        return None
    if valid is None:
        if not opts.get("epd_none_valid", False):
            return None
    elif valid < scn.project.assessment_date:
        return None
    return rec.value, c


def x_15(scn, R, opts):
    kind, factor, cv, n_unres = [], [], [], 0
    comp = R["A13-02"]["by_item"]
    for i, row in enumerate(scn.materials):
        k = f = c = None
        got = epd_applicable(scn, row, opts)
        if got is not None:
            k, (f, c) = "EPD", got
        elif row.composition is not None:
            cc = conv(scn, row.quantity_unit, "kg", row.conversions)
            if comp[i] is not None and cc is not None:
                k, f, c = "COMPOSITE", comp[i], cc
        elif row.factor_id is not None:
            rec = fac(scn, row.factor_id)
            if rec is not None:
                cc = conv(scn, row.quantity_unit, rec.unit, row.conversions)
                if cc is not None and (not opts.get("generic_stage_check") or list(rec.stages) == ["A1-A3"]):
                    k, f, c = "GENERIC", rec.value, cc
        if k is None:
            n_unres += 1
        kind.append(k); factor.append(f); cv.append(c)
    return {"kind": kind, "factor": factor, "conv": cv, "n_unresolved": n_unres}


def a13_01(scn, R):
    X, Q = R["X-15"], R["A13-05"]["q_ord"]
    total, by_item, n_skipped = 0.0, [], 0
    for i, row in enumerate(scn.materials):
        if X["kind"][i] == "EPD":
            by_item.append(0.0)
            continue
        if X["kind"][i] is None or Q[i] is None:
            by_item.append(None); n_skipped += 1
            continue
        e = Q[i] * X["conv"][i] * X["factor"][i]
        by_item.append(e); total += e
    return {"value": total, "by_item": by_item, "n_skipped": n_skipped}


def a13_03(scn, R):
    X, Q = R["X-15"], R["A13-05"]["q_ord"]
    total, by_item, n_skipped = 0.0, [], 0
    for i, row in enumerate(scn.materials):
        if X["kind"][i] != "EPD":
            by_item.append(0.0)
            continue
        if Q[i] is None:
            by_item.append(None); n_skipped += 1
            continue
        e = Q[i] * X["conv"][i] * X["factor"][i]
        by_item.append(e); total += e
    return {"value": total, "by_item": by_item, "n_skipped": n_skipped}


def row_mfg(R, i):
    """Manufacturing emission of material row i (A13-01 or A13-03), None if not computed."""
    a, b = R["A13-01"]["by_item"][i], R["A13-03"]["by_item"][i]
    if a is None or b is None:
        return None
    return a + b


def a13_04(scn, R):
    total, by_item = 0.0, []
    for i, row in enumerate(scn.materials):
        r, e = row.unquantified_cost_ratio, row_mfg(R, i)
        if r is None or not (0.0 < r < 1.0) or e is None:
            by_item.append(0.0)
            continue
        x = e * (r / (1.0 - r))
        by_item.append(x); total += x
    return {"value": total, "by_item": by_item}


def x_01(scn, R):
    total, by_item, n_skipped = 0.0, [], 0
    for eq in scn.equipment:
        rec = fac(scn, eq.factor_id)
        c = conv(scn, eq.quantity_unit, rec.unit) if rec is not None else None
        if eq.quantity is None or rec is None or c is None:
            by_item.append(None); n_skipped += 1
            continue
        e = eq.quantity * c * rec.value
        by_item.append(e); total += e
    return {"value": total, "by_item": by_item, "n_skipped": n_skipped}


# ---------------------------------------------------------------- A4
def a4_01(scn, R):
    total, by_item, n_skipped = 0.0, [], 0
    for row in scn.materials:
        tr = row.transport
        if tr.delivery_factor_id is not None:
            by_item.append(0.0)
            continue
        rec = fac(scn, tr.factor_id)
        c = conv(scn, "tkm", rec.unit) if rec is not None else None
        if tr.mass_t is None or tr.distance_km is None or rec is None or c is None:
            by_item.append(None); n_skipped += 1
            continue
        e = tr.mass_t * tr.distance_km * c * rec.value
        by_item.append(e); total += e
    return {"value": total, "by_item": by_item, "n_skipped": n_skipped}


def a4_02(scn, R):
    Q = R["A13-05"]["q_ord"]
    total, by_item, n_skipped = 0.0, [], 0
    for i, row in enumerate(scn.materials):
        tr = row.transport
        if tr.delivery_factor_id is None:
            by_item.append(0.0)
            continue
        rec = fac(scn, tr.delivery_factor_id)
        c = conv(scn, row.quantity_unit, rec.unit, row.conversions) if rec is not None else None
        if Q[i] is None or rec is None or c is None:
            by_item.append(None); n_skipped += 1
            continue
        e = Q[i] * c * rec.value
        by_item.append(e); total += e
    return {"value": total, "by_item": by_item, "n_skipped": n_skipped}


# ---------------------------------------------------------------- C
def c2_01(scn, R):
    total, by_item, n_skipped = 0.0, [], 0
    for row in scn.materials:
        eol = row.end_of_life
        rec = fac(scn, eol.haul_factor_id)
        c = conv(scn, "tkm", rec.unit) if rec is not None else None
        if eol.mass_kg is None or eol.haul_distance_km is None or rec is None or c is None:
            by_item.append(None); n_skipped += 1
            continue
        e = eol.mass_kg / 1000.0 * eol.haul_distance_km * c * rec.value
        by_item.append(e); total += e
    for h in scn.end_of_life.waste_hauls:
        rec = fac(scn, h.factor_id)
        c = conv(scn, "tkm", rec.unit) if rec is not None else None
        if h.mass_t is None or h.distance_km is None or rec is None or c is None:
            n_skipped += 1
            continue
        total += h.mass_t * h.distance_km * c * rec.value
    return {"value": total, "by_item": by_item, "n_skipped": n_skipped}


def _routes(scn, R, wanted, opts):
    total, by_item, n_skipped = 0.0, [], 0
    for row in scn.materials:
        eol = row.end_of_life
        if eol.mass_kg is None:
            by_item.append(None); n_skipped += 1
            continue
        e, bad = 0.0, False
        for rt in eol.routes:
            if rt.route not in wanted:
                continue
            rec = fac(scn, rt.factor_id)
            c = conv(scn, "kg", rec.unit) if rec is not None else None
            if rec is None or c is None or rt.fraction is None:
                bad = True
                continue
            e += eol.mass_kg * rt.fraction * c * rec.value
        if bad and opts.get("route_bad_skips_row", True):
            by_item.append(None); n_skipped += 1
            continue
        by_item.append(e); total += e
    return {"value": total, "by_item": by_item, "n_skipped": n_skipped}


def c3_01(scn, R, opts):
    return _routes(scn, R, ("REUSE", "RECYCLE", "PROCESSING"), opts)


def c4_01(scn, R, opts):
    return _routes(scn, R, ("LANDFILL",), opts)


def x_14(scn, R):
    total, by_item, n_skipped = 0.0, [], 0
    for eq in scn.equipment:
        rec = fac(scn, eq.eol_factor_id)
        c = conv(scn, "kg", rec.unit) if rec is not None else None
        if eq.end_of_life_mass_kg is None or rec is None or c is None:
            by_item.append(None); n_skipped += 1
            continue
        e = eq.end_of_life_mass_kg * c * rec.value
        by_item.append(e); total += e
    return {"value": total, "by_item": by_item, "n_skipped": n_skipped}


def c_05(scn, R, opts):
    Q = R["A13-05"]["q_ord" if opts.get("c05_mass", "ordered") == "ordered" else "q_inst"]
    viol, under, unchecked = [], [], 0
    for i, row in enumerate(scn.materials):
        eol = row.end_of_life
        fr = [rt.fraction for rt in eol.routes]
        s = sum(fr)
        bad_fraction = any(f < 0.0 for f in fr) or s > 1.0 + 1e-6
        if not bad_fraction and s < 1.0 - 1e-6:
            under.append(i)
        c = conv(scn, row.quantity_unit, "kg", row.conversions)
        bad_mass = False
        if c is None or Q[i] is None or eol.mass_kg is None:
            unchecked += 1
        else:
            bad_mass = eol.mass_kg > Q[i] * c * (1.0 + (1e-6 if opts.get("c05_mass_tol", True) else 0.0))
        if bad_fraction:
            viol.append((i, "FRACTION"))
        if bad_mass:
            viol.append((i, "MASS"))
    return {"ok": not viol, "violations": viol, "under_allocated": under, "n_mass_unchecked": unchecked}


# ---------------------------------------------------------------- B4 / B3
def b4_01(scn, R):
    T = scn.boundary.study_period
    events = []
    for eq in scn.equipment:
        if eq.replacement_event_list is not None:
            events.append(explicit(T, eq.replacement_event_list))
        else:
            events.append(periodic(T, eq.service_life))
    return {"events": events, "n_events": sum(len(e) for e in events)}


def b4_03(scn, R, opts):
    T = scn.boundary.study_period
    name = opts.get("material_cycle_field", "refresh_cycle")
    return {"by_item": [len(periodic(T, getattr(row, name))) for row in scn.materials]}


def mat_event_times(scn, opts):
    T = scn.boundary.study_period
    name = opts.get("material_cycle_field", "refresh_cycle")
    return [periodic(T, getattr(row, name)) for row in scn.materials]


def b4_02(scn, R, opts):
    T = scn.boundary.study_period
    Y = n_years(T)
    by_year = [0.0] * (Y + 1)
    Q = R["A13-05"]["q_ord"]
    total, bim, bie = 0.0, [], []
    times = mat_event_times(scn, opts)
    for i, row in enumerate(scn.materials):
        n = R["B4-03"]["by_item"][i]
        parts = [row_mfg(R, i), R["A4-01"]["by_item"][i], R["A4-02"]["by_item"][i],
                 R["C2-01"]["by_item"][i], R["C3-01"]["by_item"][i], R["C4-01"]["by_item"][i]]
        if row.installation_factor_id is not None:
            rec = fac(scn, row.installation_factor_id)
            c = conv(scn, row.quantity_unit, rec.unit, row.conversions) if rec is not None else None
            parts.append(None if (rec is None or c is None or Q[i] is None) else Q[i] * c * rec.value)
        u = sum(p for p in parts if p is not None)
        bim.append(n * u)
        total += n * u
        for t in times[i]:
            by_year[math.ceil(t)] += u
    for j, eq in enumerate(scn.equipment):
        parts = [R["X-01"]["by_item"][j], R["X-14"]["by_item"][j]]
        for fid in (eq.delivery_factor_id, eq.installation_factor_id):
            if fid is not None:
                rec = fac(scn, fid)
                c = conv(scn, eq.quantity_unit, rec.unit) if rec is not None else None
                parts.append(None if (rec is None or c is None or eq.quantity is None) else eq.quantity * c * rec.value)
        u = sum(p for p in parts if p is not None)
        ev = R["B4-01"]["events"][j]
        bie.append(len(ev) * u)
        total += len(ev) * u
        for t in ev:
            by_year[math.ceil(t)] += u
    return {"value": total, "by_item_material": bim, "by_item_equipment": bie, "by_year": by_year}


def b3_01(scn, R, opts):
    T = scn.boundary.study_period
    Y, w = n_years(T), weights(T)
    by_year = [0.0] * (Y + 1)
    total = 0.0
    times = mat_event_times(scn, opts)
    rows = []
    for i, row in enumerate(scn.materials):
        rows.append((row_mfg(R, i), row.repair_rate, {math.ceil(t) for t in times[i]}))
    for j, eq in enumerate(scn.equipment):
        rows.append((R["X-01"]["by_item"][j], eq.repair_rate, {math.ceil(t) for t in R["B4-01"]["events"][j]}))
    for e0, r, skip in rows:
        if e0 is None or r is None:
            continue
        for y in range(1, Y + 1):
            if y in skip:
                continue
            x = e0 * r * w[y]
            by_year[y] += x
            total += x
    return {"value": total, "by_year": by_year}


def b3_02(scn, R):
    T = scn.boundary.study_period
    total = 0.0
    for i, row in enumerate(scn.materials):
        e0 = row_mfg(R, i)
        if e0 is None or row.repair_rate is None:
            continue
        total += e0 * row.repair_rate * T
    for j, eq in enumerate(scn.equipment):
        e0 = R["X-01"]["by_item"][j]
        if e0 is None or eq.repair_rate is None:
            continue
        total += e0 * eq.repair_rate * T
    return {"value": total}


# ---------------------------------------------------------------- B1
def b1_02(scn, R):
    T = scn.boundary.study_period
    Y, w = n_years(T), weights(T)
    by_year = [0.0] * (Y + 1)
    total, by_item, state = 0.0, [], []
    for dev in scn.refrigerants:
        m0, g, r = dev.charge_mass_kg, dev.gwp, dev.annual_leak_rate
        if m0 is None or g is None or r is None:
            by_item.append(None); state.append(None)
            continue
        if dev.change_years is not None:
            ev = explicit(T, dev.change_years)
        else:
            ev = periodic(T, dev.service_life)
        ev_years = sorted(math.ceil(t) for t in ev)
        m = m0
        e_dev = 0.0
        before = []
        for y in range(1, Y + 1):
            leak = m * r * w[y]
            e = leak * g
            by_year[y] += e
            e_dev += e
            if not dev.top_up:
                m -= leak
            for yy in ev_years:
                if yy == y:
                    before.append((y, m))
                    m = m0
        by_item.append(e_dev); total += e_dev
        state.append({"before_events": before, "end": m})
    return {"value": total, "by_item": by_item, "by_year": by_year, "_state": state}


def b1_03(scn, R):
    T = scn.boundary.study_period
    Y = n_years(T)
    by_year = [0.0] * (Y + 1)
    total = 0.0
    for d, dev in enumerate(scn.refrigerants):
        st = R["B1-02"]["_state"][d]
        if st is None or dev.replacement_loss_rate is None:
            continue
        for y, m in st["before_events"]:
            e = m * dev.replacement_loss_rate * dev.gwp
            by_year[y] += e
            total += e
    return {"value": total, "by_year": by_year}


def b1_04(scn, R):
    total = 0.0
    for d, dev in enumerate(scn.refrigerants):
        st = R["B1-02"]["_state"][d]
        if st is None or dev.end_of_life_recovery_rate is None:
            continue
        total += st["end"] * (1.0 - dev.end_of_life_recovery_rate) * dev.gwp
    return {"value": total}


# ---------------------------------------------------------------- B6 / B2
def x_06(scn, R):
    T = scn.boundary.study_period
    Y = n_years(T)
    g = scn.operation.grid
    out = [0.0]
    for y in range(1, Y + 1):
        k = y - 1
        if g.kind == "CONSTANT":
            v = g.start
        elif g.kind == "LINEAR_DECLINE_TO_FLOOR":
            v = max(g.floor, g.start - g.annual_decline * k)
        elif g.kind == "STEPWISE":
            v = None
            for s in g.steps:
                if s.from_index <= k:
                    v = s.value
        else:
            v = g.table[k]
        out.append(v)
    return {"by_year": out, "matches_table": all(out[y] == g.table[y - 1] for y in range(1, Y + 1))}


def b6_04(scn, R):
    T = scn.boundary.study_period
    Y = n_years(T)
    op = scn.operation
    out = [0.0]
    for y in range(1, Y + 1):
        k = y - 1
        out.append(max(0.0, op.electricity.table[k] - (op.onsite_generation.table[k] - op.onsite_export.table[k])))
    return {"by_year": out}


def b6_01(scn, R):
    Y = n_years(scn.boundary.study_period)
    if scn.operation.grid.licence_status != PERMITTED:
        return {"by_year": None, "computed": False}
    n, g = R["B6-04"]["by_year"], R["X-06"]["by_year"]
    return {"by_year": [0.0] + [n[y] * g[y] for y in range(1, Y + 1)], "computed": True}


def b6_02(scn, R):
    Y = n_years(scn.boundary.study_period)
    op = scn.operation
    out = [0.0] * (Y + 1)
    n_skipped = 0
    for prof, fid in ((op.gas, op.gas_factor_id), (op.oil, op.oil_factor_id),
                      (op.district_heat, op.district_heat_factor_id)):
        rec = fac(scn, fid)
        # NOTE (definition gap): the profile unit is "<unit>/year" while the factor unit is "<unit>".
        # The written convention ("direct lookup, no chaining") gives no rule for the "/year" suffix.
        pu = prof.unit[:-5] if prof.unit.endswith("/year") else prof.unit
        c = conv(scn, pu, rec.unit) if rec is not None else None
        if rec is None or c is None:
            n_skipped += 1
            continue
        for y in range(1, Y + 1):
            out[y] += prof.table[y - 1] * c * rec.value
    return {"by_year": out, "n_skipped": n_skipped}


def b6_03(scn, R):
    T = scn.boundary.study_period
    Y, w = n_years(T), weights(T)
    el = R["B6-01"]["by_year"]
    fu = R["B6-02"]["by_year"]
    total = 0.0
    for y in range(1, Y + 1):
        total += ((el[y] if el is not None else 0.0) + fu[y]) * w[y]
    return {"value": total}


def b2_01(scn, R):
    T = scn.boundary.study_period
    Y, w = n_years(T), weights(T)
    el = R["B6-01"]["by_year"]
    if el is None:
        return {"value": None}
    s = 0.0
    for y in range(1, Y + 1):
        s += el[y] * w[y]
    return {"value": s * scn.operation.facility_management_ratio}


# ---------------------------------------------------------------- B5
def b5_01(scn, R, ext):
    T = scn.boundary.study_period
    Y = n_years(T)
    b = scn.boundary
    by_year = [0.0] * (Y + 1)
    if b.reconstruction_scenario == "NONE":
        return {"value": 0.0, "n_events": 0, "by_year": by_year}
    ev = periodic(T, b.replacement_cycle)
    base = (R["A13-01"]["value"] + R["A13-03"]["value"] + R["A13-04"]["value"] + R["X-01"]["value"]
            + R["A4-01"]["value"] + R["A4-02"]["value"] + ext["A5-04"]["value"] + ext["C1-01"]["value"]
            + R["C2-01"]["value"] + R["C3-01"]["value"] + R["X-14"]["value"] + R["C4-01"]["value"])
    per = b.reconstruction_scope_fraction * base
    for t in ev:
        by_year[math.ceil(t)] += per
    return {"value": len(ev) * per, "n_events": len(ev), "by_year": by_year}


# ---------------------------------------------------------------- stage vector and sums
def x_02(scn, R, ext):
    def v(x):
        return x["value"]
    b2 = v(R["B2-01"])
    allst = {
        "A1-A3": v(R["A13-01"]) + v(R["A13-03"]) + v(R["A13-04"]) + v(R["X-01"]),
        "A4": v(R["A4-01"]) + v(R["A4-02"]),
        "A5": v(ext["A5-04"]),
        "B1": v(R["B1-02"]) + v(R["B1-03"]) + v(R["B1-04"]),
        "B2": b2 if b2 is not None else 0.0,
        "B3": v(R["B3-01"]),
        "B4": v(R["B4-02"]),
        "B5": v(R["B5-01"]),
        "B6": v(R["B6-03"]) - (b2 if b2 is not None else 0.0),
        "B7": v(ext["B7-04"]),
        "C1": v(ext["C1-01"]),
        "C2": v(R["C2-01"]),
        "C3": v(R["C3-01"]) + v(R["X-14"]),
        "C4": v(R["C4-01"]),
    }
    inc = set(scn.boundary.included_lifecycle_stages)
    return {"by_stage": {s: allst[s] for s in STAGES if s in inc}, "by_stage_all": allst}


def _sum(R, names):
    bs = R["X-02"]["by_stage"]
    t = 0.0
    for s in names:
        if s in bs:
            t += bs[s]
    return {"value": t}


def sum_01(scn, R):
    return _sum(R, ("A1-A3", "A4", "A5"))


def sum_02(scn, R):
    return _sum(R, ("A1-A3", "A4", "A5", "B1", "B2", "B3", "B4", "B5", "C1", "C2", "C3", "C4"))


def sum_03(scn, R):
    return _sum(R, STAGES)


def sum_05(scn, R):
    A, T = scn.project.gross_floor_area, scn.boundary.study_period
    if A is None or A <= 0.0 or T <= 0.0:
        return {"value": None}
    return {"value": R["SUM-03"]["value"] / (A * T)}


def sum_07(scn, R):
    bs, tot = R["X-02"]["by_stage"], R["SUM-03"]["value"]
    if tot <= 0.0 or any(x < 0.0 for x in bs.values()):
        return {"defined": False, "by_stage": None}
    return {"defined": True, "by_stage": {s: x / tot for s, x in bs.items()}}


ORDER = ["A13-05", "A13-02", "X-15", "A13-01", "A13-03", "A13-04", "X-01", "A4-01", "A4-02",
         "C2-01", "C3-01", "C4-01", "X-14", "C-05", "B4-01", "B4-03", "B4-02", "B3-01", "B3-02",
         "B1-02", "B1-03", "B1-04", "X-06", "B6-04", "B6-01", "B6-02", "B6-03", "B2-01", "B5-01",
         "X-02", "SUM-01", "SUM-02", "SUM-03", "SUM-05", "SUM-07"]


def run(scn, ext, opts=None):
    opts = opts or {}
    R = {}
    R["A13-05"] = a13_05(scn, R)
    R["A13-02"] = a13_02(scn, R)
    R["X-15"] = x_15(scn, R, opts)
    R["A13-01"] = a13_01(scn, R)
    R["A13-03"] = a13_03(scn, R)
    R["A13-04"] = a13_04(scn, R)
    R["X-01"] = x_01(scn, R)
    R["A4-01"] = a4_01(scn, R)
    R["A4-02"] = a4_02(scn, R)
    R["C2-01"] = c2_01(scn, R)
    R["C3-01"] = c3_01(scn, R, opts)
    R["C4-01"] = c4_01(scn, R, opts)
    R["X-14"] = x_14(scn, R)
    R["C-05"] = c_05(scn, R, opts)
    R["B4-01"] = b4_01(scn, R)
    R["B4-03"] = b4_03(scn, R, opts)
    R["B4-02"] = b4_02(scn, R, opts)
    R["B3-01"] = b3_01(scn, R, opts)
    R["B3-02"] = b3_02(scn, R)
    R["B1-02"] = b1_02(scn, R)
    R["B1-03"] = b1_03(scn, R)
    R["B1-04"] = b1_04(scn, R)
    R["X-06"] = x_06(scn, R)
    R["B6-04"] = b6_04(scn, R)
    R["B6-01"] = b6_01(scn, R)
    R["B6-02"] = b6_02(scn, R)
    R["B6-03"] = b6_03(scn, R)
    R["B2-01"] = b2_01(scn, R)
    R["B5-01"] = b5_01(scn, R, ext)
    R["X-02"] = x_02(scn, R, ext)
    R["SUM-01"] = sum_01(scn, R)
    R["SUM-02"] = sum_02(scn, R)
    R["SUM-03"] = sum_03(scn, R)
    R["SUM-05"] = sum_05(scn, R)
    R["SUM-07"] = sum_07(scn, R)
    return R
