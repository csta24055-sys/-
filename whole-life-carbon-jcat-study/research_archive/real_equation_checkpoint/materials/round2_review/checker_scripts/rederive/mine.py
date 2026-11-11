"""Independent re-derivation of reference units from 01_LEDGER/units.json reference_semantics.

Written from the Japanese definition text and the convention docstring of refcalc/base.py only.
Reads only synth.model data classes. Does NOT import refcalc.
"""
import math

STAGES = ("A1-A3", "A4", "A5", "B1", "B2", "B3", "B4", "B5", "B6", "B7", "C1", "C2", "C3", "C4")
EPS = 1e-9
OKLIC = ("PERMITTED_PUBLIC",)


def fin_nonneg(x):
    return x is not None and isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) and x >= 0


def is_ratio(x):
    return fin_nonneg(x) and x <= 1.0


def conv(scn, a, b, extra=()):
    if a == b:
        return 1.0
    for c in list(extra) + list(scn.unit_conversions):
        if c.from_unit == a and c.to_unit == b:
            return c.factor
    return None


def usable(scn, fid, stage, unit, extra=()):
    if fid is None or unit is None:
        return None
    rec = scn.factors.get(fid)
    if rec is None or rec.licence_status not in OKLIC or list(rec.stages) != [stage]:
        return None
    c = conv(scn, unit, rec.unit, extra)
    if c is None:
        return None
    return rec, c


def inside(tau, T):
    return tau < T * (1 - EPS)


def ev_year(tau):
    return max(1, math.ceil(tau * (1 - EPS)))


def periodic(T, L):
    out = []
    if L is None or not (L > 0) or math.isinf(L):
        return out
    n = 1
    while inside(n * L, T):
        out.append(n * L)
        n += 1
    return out


def explicit(T, lst):
    return [float(t) for t in lst if t > 0 and inside(t, T)]


def weights(T):
    Y = math.ceil(T)
    return [0.0] + [min(1.0, T - (y - 1)) for y in range(1, Y + 1)]


def annual_unit(u):
    h, s, t = u.partition("/")
    return h if s and t == "year" else None


def prof(p, Y):
    if p.kind == "CONSTANT" and p.base is not None:
        return [p.base] * Y
    if p.kind == "LINEAR_TREND" and p.base is not None and p.slope is not None:
        return [p.base + p.slope * k for k in range(Y)]
    return [p.table[k] for k in range(Y)]


def grid_ok(g):
    if g.kind == "CONSTANT":
        return g.start is not None
    if g.kind == "LINEAR_DECLINE_TO_FLOOR":
        return None not in (g.start, g.floor, g.annual_decline) and g.annual_decline >= 0 and g.start >= g.floor
    if g.kind == "STEPWISE":
        st = g.steps or []
        return bool(st) and st[0].from_index == 0 and all(st[i].from_index < st[i + 1].from_index for i in range(len(st) - 1))
    return False


def grid_series(g, Y):
    if not grid_ok(g):
        return [g.table[k] for k in range(Y)], "TABLE"
    if g.kind == "CONSTANT":
        return [g.start] * Y, "DESCRIPTOR"
    if g.kind == "LINEAR_DECLINE_TO_FLOOR":
        return [max(g.floor, g.start - g.annual_decline * k) for k in range(Y)], "DESCRIPTOR"
    out = []
    for k in range(Y):
        v = None
        for s in g.steps:
            if s.from_index <= k:
                v = s.value
        out.append(v)
    return out, "DESCRIPTOR"


def grid_unit(g):
    h, s, t = g.unit.partition("/")
    return t if s and h == "kgCO2e" and t else None


def run(scn, baselines=None):
    R = {}
    T = scn.boundary.study_period
    Y = math.ceil(T)
    W = weights(T)
    inc = set(scn.boundary.included_lifecycle_stages)
    mats, eqs, refs = scn.materials, scn.equipment, scn.refrigerants
    lines = {s: [] for s in STAGES}   # (factor_id or GRID/REFRIGERANT, activity, factor value)

    # ---- A13-05
    q_ord, q_inst = [], []
    nsk = 0
    for r in mats:
        Q, w = r.quantity, r.waste_rate
        if not fin_nonneg(Q) or not fin_nonneg(w) or not (w < 1.0):
            q_ord.append(None); q_inst.append(None); nsk += 1
            continue
        if r.quantity_basis == "DESIGN":
            q_inst.append(Q); q_ord.append(Q / (1 - w))
        else:
            q_ord.append(Q); q_inst.append(Q * (1 - w))
    R["A13-05"] = {"q_ord": q_ord, "q_inst": q_inst, "n_skipped": nsk}

    # ---- A13-02
    comp_f = []
    ninv = 0
    for r in mats:
        if r.composition is None:
            comp_f.append(None)
            continue
        ok = True
        tot = 0.0
        f = 0.0
        for c in r.composition:
            if c.mass_fraction is None or not (c.mass_fraction >= 0):
                ok = False
                break
            u = usable(scn, c.factor_id, "A1-A3", "kg")
            if u is None:
                ok = False
                break
            rec, cv = u
            tot += c.mass_fraction
            f += c.mass_fraction * cv * rec.value
        if ok and abs(tot - 1.0) > 1e-6:
            ok = False
        if not ok:
            ninv += 1
            comp_f.append(None)
        else:
            comp_f.append(f)
    R["A13-02"] = {"by_item": comp_f, "n_invalid": ninv}

    # ---- X-15
    kind, fac, cv_, nun, ndec = [], [], [], 0, 0
    for i, r in enumerate(mats):
        k = None
        if r.epd is not None:
            rec = scn.factors.get(r.epd.factor_id)
            good = (rec is not None and list(r.epd.declared_stages) == list(rec.stages)
                    and r.epd.declared_unit == rec.unit and r.epd.valid_until == rec.valid_until
                    and rec.licence_status in OKLIC and list(rec.stages) == ["A1-A3"]
                    and rec.valid_until is not None and rec.valid_until >= scn.project.assessment_date)
            c = conv(scn, r.quantity_unit, rec.unit, r.conversions) if good else None
            if good and c is not None:
                k = ("EPD", rec.value, c, rec.factor_id)
            else:
                ndec += 1
        if k is None:
            if r.composition is not None:
                c = conv(scn, r.quantity_unit, "kg", r.conversions)
                if comp_f[i] is not None and c is not None:
                    k = ("COMPOSITE", comp_f[i], c, None)
            else:
                u = usable(scn, r.factor_id, "A1-A3", r.quantity_unit, r.conversions)
                if u is not None:
                    k = ("GENERIC", u[0].value, u[1], u[0].factor_id)
        if k is None:
            nun += 1
            kind.append("UNRESOLVED"); fac.append(None); cv_.append(None)
        else:
            kind.append(k[0]); fac.append(k[1]); cv_.append(k[2])
    R["X-15"] = {"kind": kind, "factor": fac, "conv": cv_, "n_unresolved": nun, "n_epd_declined": ndec}

    # ---- A13-01 / A13-03
    e01, e03 = [0.0] * len(mats), [0.0] * len(mats)
    sk01, sk03 = set(), set()
    for i, r in enumerate(mats):
        if kind[i] == "EPD":
            if q_ord[i] is None:
                sk03.add(i)
            else:
                e03[i] = q_ord[i] * cv_[i] * fac[i]
        else:
            if kind[i] == "UNRESOLVED" or q_ord[i] is None:
                sk01.add(i)
            else:
                e01[i] = q_ord[i] * cv_[i] * fac[i]
    v01 = 0.0
    for x in e01:
        v01 += x
    v03 = 0.0
    for x in e03:
        v03 += x
    R["A13-01"] = {"value": v01, "by_item": e01, "n_skipped": len(sk01)}
    R["A13-03"] = {"value": v03, "by_item": e03, "n_skipped": len(sk03)}
    man_sk = sk01 | sk03

    # ---- A13-04
    e04 = [0.0] * len(mats)
    n04 = 0
    for i, r in enumerate(mats):
        rr = r.unquantified_cost_ratio
        if rr is None or rr == 0:
            continue
        if not (0 < rr < 1):
            n04 += 1
            continue
        e04[i] = (e01[i] + e03[i]) * rr / (1 - rr)
    R["A13-04"] = {"value": sum(e04), "by_item": e04, "n_skipped": n04}

    # ---- X-01
    ex01 = [0.0] * len(eqs)
    skx01 = set()
    for i, e in enumerate(eqs):
        u = usable(scn, e.factor_id, "A1-A3", e.quantity_unit)
        if not fin_nonneg(e.quantity) or u is None:
            skx01.add(i)
            continue
        ex01[i] = e.quantity * u[1] * u[0].value
    R["X-01"] = {"value": sum(ex01), "by_item": ex01, "n_skipped": len(skx01)}

    # ---- A4-01 / A4-02 / X-12
    e41, e42, e12 = [0.0] * len(mats), [0.0] * len(mats), [0.0] * len(mats)
    sk41, sk42, sk12 = set(), set(), set()
    for i, r in enumerate(mats):
        t = r.transport
        if t.delivery_factor_id is None:
            u = usable(scn, t.factor_id, "A4", "tkm", r.conversions)
            if not fin_nonneg(t.mass_t) or not fin_nonneg(t.distance_km) or u is None:
                sk41.add(i); sk12.add(i)
                continue
            e41[i] = t.mass_t * t.distance_km * u[1] * u[0].value
            lf = t.load_factor
            if lf is None or not (lf > 0) or math.isinf(lf):
                sk12.add(i)
            else:
                e12[i] = e41[i] / lf
        else:
            u = usable(scn, t.delivery_factor_id, "A4", r.quantity_unit, r.conversions)
            if q_ord[i] is None or u is None:
                sk42.add(i)
                continue
            e42[i] = q_ord[i] * u[1] * u[0].value
    R["A4-01"] = {"value": sum(e41), "by_item": e41, "n_skipped": len(sk41)}
    R["A4-02"] = {"value": sum(e42), "by_item": e42, "n_skipped": len(sk42)}
    R["X-12"] = {"value": sum(e12), "by_item": e12, "n_skipped": len(sk12)}

    # ---- A5
    g = scn.operation.grid
    gu = grid_unit(g)
    a51 = 0.0
    a51c = False
    kwh = scn.construction.electricity_kwh
    if g.licence_status in OKLIC and fin_nonneg(kwh) and gu is not None:
        c = conv(scn, "kWh", gu)
        if c is not None:
            a51 = kwh * c * g.construction_value
            a51c = True
    R["A5-01"] = {"value": a51, "computed": a51c}
    a52, n52 = 0.0, 0
    for f in scn.construction.fuels:
        u = usable(scn, f.factor_id, "A5", f.unit, f.conversions)
        if not fin_nonneg(f.quantity) or u is None:
            n52 += 1
            continue
        a52 += f.quantity * u[1] * u[0].value
    R["A5-02"] = {"value": a52, "n_skipped": n52}
    a53, n53 = 0.0, 0
    for wst in scn.construction.waste_streams:
        u = usable(scn, wst.factor_id, "A5", "kg")
        if not fin_nonneg(wst.mass_kg) or u is None:
            n53 += 1
            continue
        a53 += wst.mass_kg * u[1] * u[0].value
    R["A5-03"] = {"value": a53, "n_skipped": n53}
    R["A5-04"] = {"value": a51 + a52 + a53}

    # ---- B1
    b11, n11 = 0.0, 0
    for d in refs:
        if fin_nonneg(d.charge_mass_kg) and fin_nonneg(d.gwp):
            b11 += d.charge_mass_kg * d.gwp
        else:
            n11 += 1
    R["B1-01"] = {"value": b11, "n_skipped": n11}
    b12y = [0.0] * (Y + 1)
    b13y = [0.0] * (Y + 1)
    b12i = []
    b12 = b13 = b14 = 0.0
    n12 = n13 = n14 = 0
    for d in refs:
        if not fin_nonneg(d.charge_mass_kg) or not fin_nonneg(d.gwp) or not is_ratio(d.annual_leak_rate):
            n12 += 1; n13 += 1; n14 += 1
            b12i.append(0.0)
            continue
        evs = explicit(T, d.change_years) if d.change_years is not None else periodic(T, d.service_life)
        by = {}
        for t in evs:
            by.setdefault(ev_year(t), []).append(t)
        rem = d.charge_mass_kg
        tot = 0.0
        ok13 = is_ratio(d.replacement_loss_rate)
        for y in range(1, Y + 1):
            leak = rem * d.annual_leak_rate * W[y]
            tot += leak * d.gwp
            b12y[y] += leak * d.gwp
            if not d.top_up:
                rem -= leak
            for t in by.get(y, []):
                if ok13:
                    b13 += rem * d.replacement_loss_rate * d.gwp
                    b13y[y] += rem * d.replacement_loss_rate * d.gwp
                rem = d.charge_mass_kg
        b12 += tot
        b12i.append(tot)
        if not ok13:
            n13 += 1
        if is_ratio(d.end_of_life_recovery_rate):
            b14 += rem * (1 - d.end_of_life_recovery_rate) * d.gwp
        else:
            n14 += 1
    R["B1-02"] = {"value": b12, "by_item": b12i, "by_year": b12y, "n_skipped": n12}
    R["B1-03"] = {"value": b13, "by_year": b13y, "n_skipped": n13}
    R["B1-04"] = {"value": b14, "n_skipped": n14}

    # ---- B6-04, X-06, B6-01, B6-02, B6-03, B2-01
    op = scn.operation
    eu = annual_unit(op.electricity.unit)
    gnu = annual_unit(op.onsite_generation.unit)
    exu = annual_unit(op.onsite_export.unit)
    purchased = None
    if eu is not None and gnu is not None and exu is not None:
        cg, ce = conv(scn, gnu, eu), conv(scn, exu, eu)
        if cg is not None and ce is not None:
            co, ge, ex = prof(op.electricity, Y), prof(op.onsite_generation, Y), prof(op.onsite_export, Y)
            purchased = [0.0] + [max(0.0, co[k] - (ge[k] * cg - ex[k] * ce)) for k in range(Y)]
    R["B6-04"] = {"by_year": purchased if purchased is not None else [0.0] * (Y + 1), "computed": purchased is not None}
    gs, gsrc = grid_series(g, Y)
    R["X-06"] = {"by_year": [0.0] + gs, "source": gsrc}
    b61 = None
    if g.licence_status in OKLIC and purchased is not None and gu is not None:
        c = conv(scn, eu, gu)
        if c is not None:
            b61 = [0.0] + [purchased[y] * c * gs[y - 1] for y in range(1, Y + 1)]
    R["B6-01"] = {"by_year": b61 if b61 is not None else [0.0] * (Y + 1), "computed": b61 is not None}

    def annual_set(items, stage):
        by = [0.0] * (Y + 1)
        n = 0
        for p, fid in items:
            au = annual_unit(p.unit)
            u = usable(scn, fid, stage, au) if au is not None else None
            if u is None:
                n += 1
                continue
            vals = prof(p, Y)
            for y in range(1, Y + 1):
                by[y] += vals[y - 1] * u[1] * u[0].value
        return by, n
    b62, n62 = annual_set([(op.gas, op.gas_factor_id), (op.oil, op.oil_factor_id),
                           (op.district_heat, op.district_heat_factor_id)], "B6")
    R["B6-02"] = {"by_year": b62, "n_skipped": n62}
    e_grid = sum((b61[y] if b61 else 0.0) * W[y] for y in range(1, Y + 1))
    b63 = sum(((b61[y] if b61 else 0.0) + b62[y]) * W[y] for y in range(1, Y + 1))
    R["B6-03"] = {"value": b63}
    fm = op.facility_management_ratio
    b21c = is_ratio(fm) and b61 is not None
    b21 = e_grid * fm if b21c else 0.0
    R["B2-01"] = {"value": b21, "computed": b21c}
    ww = scn.water_waste
    b71, n71 = annual_set([(ww.water, ww.water_factor_id)], "B7")
    b72, n72 = annual_set([(ww.sewage, ww.sewage_factor_id)], "B7")
    b73, n73 = annual_set([(ww.municipal_waste, ww.waste_factor_id)], "B7")
    R["B7-01"] = {"by_year": b71, "n_skipped": n71}
    R["B7-02"] = {"by_year": b72, "n_skipped": n72}
    R["B7-03"] = {"by_year": b73, "n_skipped": n73}
    b74 = sum((b71[y] + b72[y] + b73[y]) * W[y] for y in range(1, Y + 1))
    R["B7-04"] = {"value": b74}

    # ---- B4-01, B4-03
    eq_ev = []
    for e in eqs:
        if e.replacement_event_list is not None:
            eq_ev.append(explicit(T, e.replacement_event_list))
        else:
            eq_ev.append(periodic(T, e.service_life))
    R["B4-01"] = {"events": eq_ev, "n_events": sum(len(x) for x in eq_ev)}
    mat_ev = [periodic(T, r.refresh_cycle) for r in mats]
    R["B4-03"] = {"by_item": [len(x) for x in mat_ev]}

    # ---- B3-01 / B3-02
    b31y = [0.0] * (Y + 1)
    b31 = b32 = 0.0
    n31 = 0
    for rows, e0s, evl, sks in ((mats, [a + b for a, b in zip(e01, e03)], mat_ev, man_sk), (eqs, ex01, eq_ev, skx01)):
        for i, r in enumerate(rows):
            if not fin_nonneg(r.repair_rate):
                n31 += 1
                continue
            yrs = {ev_year(t) for t in evl[i]}
            for y in range(1, Y + 1):
                if y in yrs:
                    continue
                b31y[y] += e0s[i] * r.repair_rate * W[y]
                b31 += e0s[i] * r.repair_rate * W[y]
            b32 += e0s[i] * r.repair_rate * T
    R["B3-01"] = {"value": b31, "by_year": b31y, "n_skipped": n31}
    R["B3-02"] = {"value": b32, "n_skipped": n31}

    # ---- C1..C4, X-14
    c1, nc1 = 0.0, 0
    for a in scn.end_of_life.demolition_activities:
        u = usable(scn, a.factor_id, "C1", a.unit)
        if not fin_nonneg(a.quantity) or u is None:
            nc1 += 1
            continue
        c1 += a.quantity * u[1] * u[0].value
    R["C1-01"] = {"value": c1, "n_skipped": nc1}
    c2i = [0.0] * len(mats)
    skc2 = set()
    c2 = 0.0
    nc2 = 0
    for i, r in enumerate(mats):
        el = r.end_of_life
        u = usable(scn, el.haul_factor_id, "C2", "tkm", r.conversions)
        if not fin_nonneg(el.mass_kg) or not fin_nonneg(el.haul_distance_km) or u is None:
            skc2.add(i); nc2 += 1
            continue
        c2i[i] = el.mass_kg / 1000 * el.haul_distance_km * u[1] * u[0].value
        c2 += c2i[i]
    for h in scn.end_of_life.waste_hauls:
        u = usable(scn, h.factor_id, "C2", "tkm")
        if not fin_nonneg(h.mass_t) or not fin_nonneg(h.distance_km) or u is None:
            nc2 += 1
            continue
        c2 += h.mass_t * h.distance_km * u[1] * u[0].value
    R["C2-01"] = {"value": c2, "by_item": c2i, "n_skipped": nc2}
    c3i, c4i = [0.0] * len(mats), [0.0] * len(mats)
    skc3, skc4, pc3, pc4 = set(), set(), set(), set()
    nr3 = nr4 = 0
    for i, r in enumerate(mats):
        el = r.end_of_life
        if not fin_nonneg(el.mass_kg):
            skc3.add(i); skc4.add(i)
            continue
        for rt in el.routes:
            st = "C4" if rt.route == "LANDFILL" else "C3"
            u = usable(scn, rt.factor_id, st, "kg", r.conversions)
            if rt.fraction is None or not (rt.fraction >= 0) or math.isinf(rt.fraction) or u is None:
                if st == "C3":
                    nr3 += 1; pc3.add(i)
                else:
                    nr4 += 1; pc4.add(i)
                continue
            v = el.mass_kg * rt.fraction * u[1] * u[0].value
            if st == "C3":
                c3i[i] += v
            else:
                c4i[i] += v
    R["C3-01"] = {"value": sum(c3i), "by_item": c3i, "n_skipped": len(skc3), "n_routes_skipped": nr3}
    R["C4-01"] = {"value": sum(c4i), "by_item": c4i, "n_skipped": len(skc4), "n_routes_skipped": nr4}
    x14i = [0.0] * len(eqs)
    sk14 = set()
    for i, e in enumerate(eqs):
        u = usable(scn, e.eol_factor_id, "C3", "kg")
        if not fin_nonneg(e.end_of_life_mass_kg) or u is None:
            sk14.add(i)
            continue
        x14i[i] = e.end_of_life_mass_kg * u[1] * u[0].value
    R["X-14"] = {"value": sum(x14i), "by_item": x14i, "n_skipped": len(sk14)}

    # ---- B4-02  (installation factor stage: A5; delivery: A4 -- my reading)
    b42y = [0.0] * (Y + 1)
    b42m, b42e = [0.0] * len(mats), [0.0] * len(eqs)
    npart = 0
    for i, r in enumerate(mats):
        if not mat_ev[i]:
            continue
        part = (i in man_sk) or (i in sk41) or (i in sk42) or (i in skc2) or (i in skc3) or (i in skc4) or (i in pc3) or (i in pc4)
        u_ = e01[i] + e03[i] + e41[i] + e42[i] + c2i[i] + c3i[i] + c4i[i]
        if r.installation_factor_id is not None:
            u = usable(scn, r.installation_factor_id, "A5", r.quantity_unit, r.conversions)
            if u is None or q_ord[i] is None:
                part = True
            else:
                u_ += q_ord[i] * u[1] * u[0].value
        if part:
            npart += 1
        for t in mat_ev[i]:
            b42y[ev_year(t)] += u_
            b42m[i] += u_
    for i, e in enumerate(eqs):
        if not eq_ev[i]:
            continue
        part = (i in skx01) or (i in sk14)
        u_ = ex01[i] + x14i[i]
        for fid, st in ((e.delivery_factor_id, "A4"), (e.installation_factor_id, "A5")):
            if fid is not None:
                u = usable(scn, fid, st, e.quantity_unit)
                if u is None or not fin_nonneg(e.quantity):
                    part = True
                else:
                    u_ += e.quantity * u[1] * u[0].value
        if part:
            npart += 1
        for t in eq_ev[i]:
            b42y[ev_year(t)] += u_
            b42e[i] += u_
    R["B4-02"] = {"value": sum(b42m) + sum(b42e), "by_item_material": b42m, "by_item_equipment": b42e,
                  "by_year": b42y, "n_partial": npart}

    # ---- stage values (all 14, B2 carved out)
    sA13 = v01 + v03 + R["A13-04"]["value"] + R["X-01"]["value"]
    sA4 = R["A4-01"]["value"] + R["A4-02"]["value"]
    sA5 = R["A5-04"]["value"]
    sC = c1 + c2 + (R["C3-01"]["value"] + R["X-14"]["value"]) + R["C4-01"]["value"]
    # ---- B5-01
    b = scn.boundary
    b5 = 0.0
    b5y = [0.0] * (Y + 1)
    b5c = True
    nev5 = 0
    if b.reconstruction_scenario != "NONE":
        if not is_ratio(b.reconstruction_scope_fraction):
            b5c = False
        else:
            for t in periodic(T, b.replacement_cycle):
                amt = b.reconstruction_scope_fraction * (sA13 + sA4 + sA5 + sC)
                b5 += amt
                b5y[ev_year(t)] += amt
                nev5 += 1
    R["B5-01"] = {"value": b5, "n_events": nev5, "by_year": b5y, "computed": b5c}

    allst = {"A1-A3": sA13, "A4": sA4, "A5": sA5, "B1": b12 + b13 + b14, "B2": b21, "B3": b31,
             "B4": R["B4-02"]["value"], "B5": b5, "B6": b63 - (b21 if "B2" in inc else 0.0), "B7": b74,
             "C1": c1, "C2": c2, "C3": R["C3-01"]["value"] + R["X-14"]["value"], "C4": R["C4-01"]["value"]}
    by_stage = {s: allst[s] for s in STAGES if s in inc}
    R["X-02"] = {"by_stage": by_stage}

    def ssum(names):
        t = 0.0
        for s in names:
            if s in inc:
                t += allst[s]
        return t
    R["SUM-01"] = {"value": ssum(("A1-A3", "A4", "A5"))}
    R["SUM-02"] = {"value": ssum(("A1-A3", "A4", "A5", "B1", "B2", "B3", "B4", "B5", "C1", "C2", "C3", "C4"))}
    wl = ssum(STAGES)
    R["SUM-03"] = {"value": wl}
    A = scn.project.gross_floor_area
    aok = A is not None and A > 0 and math.isfinite(A)
    R["SUM-04"] = {"value": wl / A if aok else None}
    R["SUM-05"] = {"value": wl / (A * T) if aok and T > 0 else None}
    R["SUM-06"] = {"value": wl / 1000}
    if wl <= 0 or any(v < 0 for v in by_stage.values()):
        R["SUM-07"] = {"defined": False}
    else:
        R["SUM-07"] = {"defined": True, "by_stage": {s: v / wl for s, v in by_stage.items()}}

    # ---- X-07
    yv = [0.0] * (Y + 1)
    for s in ("A1-A3", "A4", "A5"):
        if s in inc:
            yv[0] += allst[s]
    for y in range(1, Y + 1):
        grid_y = (b61[y] if b61 else 0.0) * W[y]
        fuel_y = b62[y] * W[y]
        b2_y = grid_y * fm if b21c else 0.0
        if "B6" in inc:
            yv[y] += grid_y + fuel_y - (b2_y if "B2" in inc else 0.0)
        if "B2" in inc:
            yv[y] += b2_y
        if "B7" in inc:
            yv[y] += (b71[y] + b72[y] + b73[y]) * W[y]
        if "B1" in inc:
            yv[y] += b12y[y] + b13y[y]
        if "B3" in inc:
            yv[y] += b31y[y]
        if "B4" in inc:
            yv[y] += b42y[y]
        if "B5" in inc:
            yv[y] += b5y[y]
    for s in ("C1", "C2", "C3", "C4"):
        if s in inc:
            yv[Y] += allst[s]
    if "B1" in inc:
        yv[Y] += b14
    cum, t = [], 0.0
    for v in yv:
        t += v
        cum.append(t)
    R["X-07"] = {"by_year": yv, "cumulative": cum, "value": cum[-1]}

    # ---- X-13
    net, wst = [], []
    for i, r in enumerate(mats):
        if q_ord[i] is None or not is_ratio(r.reuse_rate):
            net.append(None); wst.append(None)
            continue
        d = (q_ord[i] - q_inst[i]) * (1 - r.reuse_rate)
        wst.append(d); net.append(q_inst[i] + d)
    R["X-13"] = {"by_item": net, "waste_by_item": wst}

    # ---- X-16
    x16i, n16 = [], 0
    for it in scn.cost_items:
        u = usable(scn, it.factor_id, "A1-A3", it.currency)
        ib, ip = scn.price_index.get(it.factor_base_year), scn.price_index.get(it.price_year)
        if (not fin_nonneg(it.amount) or u is None or ib is None or ip is None or not (ib > 0) or not (ip > 0)
                or math.isinf(ib) or math.isinf(ip)):
            n16 += 1
            x16i.append(0.0)
            continue
        x16i.append(it.amount * (ib / ip) * u[1] * u[0].value)
    R["X-16"] = {"value": sum(x16i), "by_item": x16i, "n_skipped": n16}

    # ---- X-10
    res_kg = waste_kg = 0.0
    nex = 0
    for i, r in enumerate(mats):
        c = conv(scn, r.quantity_unit, "kg", r.conversions)
        m = r.end_of_life.mass_kg
        if c is None or q_ord[i] is None or not fin_nonneg(m):
            nex += 1
            continue
        n = len(mat_ev[i])
        res_kg += q_ord[i] * c * (1 + n)
        waste_kg += ((q_ord[i] - q_inst[i]) * c + m) * (1 + n)
    for i, e in enumerate(eqs):
        if not fin_nonneg(e.end_of_life_mass_kg):
            nex += 1
            continue
        waste_kg += e.end_of_life_mass_kg * (1 + len(eq_ev[i]))
    R["X-10"] = {"resource_kg": res_kg, "waste_kg": waste_kg, "n_excluded": nex}

    # ---- C-05
    viol, under = [], []
    nunch = 0
    for i, r in enumerate(mats):
        el = r.end_of_life
        bad = False
        fr = [rt.fraction for rt in el.routes]
        if any(f is None or not (f >= 0) for f in fr):
            bad = True
        else:
            s = sum(fr)
            if s > 1 + 1e-6:
                bad = True
            elif s < 1 - 1e-6:
                under.append(i)
        c = conv(scn, r.quantity_unit, "kg", r.conversions)
        if c is None or q_inst[i] is None or not fin_nonneg(el.mass_kg):
            nunch += 1
        else:
            if el.mass_kg > q_inst[i] * c * (1 + 1e-6):
                bad = True
        if bad:
            viol.append(i)
    R["C-05"] = {"ok": not viol, "viol_rows": viol, "under_rows": under, "n_mass_unchecked": nunch}

    # ---- QA-02
    v2, w2 = [], []
    for i, e in enumerate(eqs):
        if e.replacement_event_list is not None:
            if any(not (t >= 0 and inside(t, T)) for t in e.replacement_event_list):
                v2.append(f"equipment[{i}].replacement_event_list")
            if any(t == 0 for t in e.replacement_event_list):
                w2.append(f"equipment[{i}].replacement_event_list")
    for i, d in enumerate(refs):
        if d.change_years is not None:
            if any(not (t >= 0 and inside(t, T)) for t in d.change_years):
                v2.append(f"refrigerants[{i}].change_years")
            if any(t == 0 for t in d.change_years):
                w2.append(f"refrigerants[{i}].change_years")
    R["QA-02"] = {"ok": not v2, "violations": v2, "warnings": w2}

    R["_all_stage"] = allst
    R["_grid_total"] = e_grid
    return R
