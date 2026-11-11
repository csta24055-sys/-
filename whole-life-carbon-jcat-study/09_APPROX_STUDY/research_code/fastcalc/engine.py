"""Unified model: one line table, a few multiplier functions, one indicator step.

The whole calculation is written as

    E[stage] = sum over lines  activity * factor value * multiplier(stage; T, row parameters)

with the lines accumulated per (stage, factor id) BEFORE the factor is applied, and the
multipliers given by closed forms (``closed_forms``):

    once          1                       A1-A3, A4, A5, C1-C4
    renewals      N(T, cycle)             B4          (count function)
    repairs       rate * (T - skipped)    B3          (count function + year weights)
    rebuild       N(T, C) * scope         B5          (count function)
    annual        weighted year sum       B6, B7, B2  (arithmetic series / cumulative factor)
    decay         per charge cycle        B1          (geometric closed form)

Everything is computed in a single pass over the input rows. Gas breakdown, the CO2-only
result, the stage vector and all indicators are read from the accumulated table.
``evaluate(scn)`` returns results in the same shape as the reference calculation so that
they can be compared leaf by leaf. ``detail=False`` leaves out per-row lists and yearly
series (the totals, stage values, indicators and checks are unchanged).

Research tooling only: no UI, no persistence, no product engine.
"""
from __future__ import annotations

import math

from synth import model, population

from . import closed_forms as cf

ALLOWED = model.ALLOWED_LICENCE_STATES
STAGES = model.LIFECYCLE_STAGES
GRID = "GRID"
REFRIGERANT = "REFRIGERANT"
INITIAL = ("A1-A3", "A4", "A5", "C1", "C2", "C3", "C4")
SIMPLE_CLASSES = ("REBAR", "STRUCTURAL_STEEL", "CONCRETE", "TIMBER", "ENVELOPE", "INTERIOR")
M_FIELDS = ("quantity", "waste_rate", "reuse_rate", "material_life", "repair_rate", "refresh_cycle")
E_FIELDS = ("quantity", "service_life", "repair_rate", "end_of_life_mass_kg")
R_FIELDS = ("charge_mass_kg", "gwp", "annual_leak_rate", "replacement_loss_rate", "end_of_life_recovery_rate")

_BASELINE_TOTALS: dict[str, float] = {}


def clear_baseline_cache() -> None:
    _BASELINE_TOTALS.clear()


def evaluate(scn, detail: bool = True) -> dict:
    T = scn.boundary.study_period
    Y = cf.n_years(T)
    wl = cf.last_weight(T) if Y else 0.0
    factors = scn.factors
    inc = set(scn.boundary.included_lifecycle_stages)

    # ---- memoised lookups (each distinct factor / unit pair is resolved once) ----
    usable: dict = {}

    def fac(fid):
        try:
            return usable[fid]
        except KeyError:
            rec = factors.get(fid) if fid is not None else None
            if rec is not None and rec.licence_status not in ALLOWED:
                rec = None
            usable[fid] = rec
            return rec

    table_conv: dict = {}

    def conv(u, v, extra=()):
        if u == v:
            return 1.0
        for c in extra:
            if c.from_unit == u and c.to_unit == v:
                return c.factor
        key = (u, v)
        try:
            return table_conv[key]
        except KeyError:
            r = model.conversion_factor(scn.unit_conversions, u, v)
            table_conv[key] = r
            return r

    # ---- the line table: activity accumulated per (stage, factor id) ----
    acc = {s: {} for s in STAGES}

    def add(stage, fid, act):
        d = acc[stage]
        d[fid] = d.get(fid, 0.0) + act

    refs: dict = {}            # factor id -> number of references (for the licence gate)
    none_refs: list = []       # references without a factor id
    recipes: dict = {}         # composition content -> [value or None, kg in A1-A3 use]
    recipe_refs: dict = {}

    # ---- input states (SYS-01) ----
    prov = scn.provenance
    counts = {s: 0 for s in model.VALUE_STATES}
    missing: list = []
    MISSING, DERIVED, ZERO = model.STATE_MISSING, model.STATE_DERIVED, model.STATE_EXPLICIT_ZERO

    def see(owner, name, value, path):
        st = owner.states.get(name) if owner.states else None
        if st is None:
            rec = prov.get(owner.provenance_id)
            st = rec.value_state if rec is not None else MISSING
        if value is None:
            st = MISSING
        elif st != DERIVED and value == 0:
            st = ZERO
        counts[st] += 1
        if st == MISSING:
            missing.append(path)

    see(scn.project, "gross_floor_area", scn.project.gross_floor_area, "project.gross_floor_area")

    unit_viol: list = []
    n_unit_checks = 0

    # ---- cycle groups for renewals (X-08 and the yearly series) ----
    cyc_u: dict = {}           # cycle -> sum of per-renewal emission u
    cyc_r: dict = {}           # cycle -> sum of e0 * repair rate (rows whose repairs skip renewal years)
    cyc_n: dict = {}
    repair_rate_sum = 0.0      # sum of e0 * repair rate over all rows with repairs
    explicit_b4 = 0.0
    b4_year = [0.0] * (Y + 1)
    b3_year_adjust = [0.0] * (Y + 1)   # per-year repair removed for explicit event lists

    val = dict.fromkeys(("A13-01", "A13-03", "A13-04", "X-01", "A4-01", "A4-02", "X-12", "C2-01", "C3-01", "C4-01",
                         "X-14", "B4-02", "B3-01", "B3-02", "X-03"), 0.0)
    skip = dict.fromkeys(("A13-05", "A13-01", "A13-03", "X-01", "A4-01", "A4-02", "X-12", "C2-01", "C3-01", "C4-01",
                          "X-14"), 0)
    n_invalid = n_unresolved = 0
    x10_resource = x10_waste = 0.0
    x10_excluded = 0
    c05_viol, c05_under = [], []
    c05_unchecked = 0
    x09_mass, x09_emis = {}, {}
    x09_total = 0.0
    class_sum = dict.fromkeys(SIMPLE_CLASSES, 0.0)

    if detail:
        L = {k: [] for k in ("q_ord", "q_inst", "net", "disp", "a1302", "kind", "factor", "conv", "a1301", "a1303",
                             "a1304", "a401", "a402", "x12", "c2", "c3", "c4", "n", "b4m", "x01", "x14", "b4e", "events")}

    assessment = scn.project.assessment_date
    weights_full = None

    # =============================== materials: one pass ===============================
    for i, row in enumerate(scn.materials):
        base = f"materials[{i}]"
        tr, eol = row.transport, row.end_of_life
        qu, rconv = row.quantity_unit, row.conversions
        # input states
        for name in M_FIELDS:
            see(row, name, getattr(row, name), f"{base}.{name}")
        see(row, "transport.mass_t", tr.mass_t, f"{base}.transport.mass_t")
        see(row, "transport.distance_km", tr.distance_km, f"{base}.transport.distance_km")
        see(row, "end_of_life.mass_kg", eol.mass_kg, f"{base}.end_of_life.mass_kg")

        # quantities (A13-05, X-13)
        q, w = row.quantity, row.waste_rate
        if q is None or w is None or not 0.0 <= w < 1.0:
            q_ord = q_inst = None
            skip["A13-05"] += 1
        elif row.quantity_basis == "DESIGN":
            q_inst = q
            q_ord = q / (1.0 - w)
        else:
            q_ord = q
            q_inst = q * (1.0 - w)

        # factor resolution (A13-02, X-15) with unit checks (SYS-02) and reference counts (SYS-03)
        unit_bad = False
        comp = row.composition
        recipe = None
        if comp is not None:
            key = tuple([(c.factor_id, c.mass_fraction) for c in comp])
            recipe = recipes.get(key)
            if recipe is None:
                total_fraction = value = 0.0
                ok = True
                for fid, fraction in key:
                    rec = fac(fid)
                    if rec is None or rec.unit != "kg" or rec.stages != ["A1-A3"]:
                        ok = False
                        break
                    total_fraction += fraction
                    value += fraction * rec.value
                recipe = recipes[key] = [value if ok and abs(total_fraction - 1.0) <= 1e-6 else None, key]
            recipe_refs[key] = recipe_refs.get(key, 0) + 1
            if recipe[0] is None:
                n_invalid += 1
            c_kg = conv(qu, "kg", rconv)
            n_unit_checks += 1
            unit_bad = c_kg is None
        else:
            fid = row.factor_id
            if fid is None:
                none_refs.append(f"{base}.factor_id (no factor)")
            else:
                refs[fid] = refs.get(fid, 0) + 1
            n_unit_checks += 1
            raw = factors.get(fid) if fid is not None else None
            c_gen = conv(qu, raw.unit, rconv) if raw is not None else None
            if raw is not None and c_gen is None:
                unit_bad = True

        kind = f = c = line_fid = None
        epd = row.epd
        if epd is not None:
            refs[epd.factor_id] = refs.get(epd.factor_id, 0) + 1
            rec = fac(epd.factor_id)
            if rec is not None and rec.stages == ["A1-A3"] and rec.valid_until is not None and not rec.valid_until < assessment:
                ce = conv(qu, rec.unit, rconv)
                if ce is not None:
                    kind, f, c, line_fid = "EPD", rec.value, ce, epd.factor_id
        if kind is None:
            if comp is not None:
                if recipe[0] is not None and c_kg is not None:
                    kind, f, c, line_fid = "COMPOSITE", recipe[0], c_kg, recipe[1]
            else:
                rec = fac(row.factor_id)
                if rec is not None and rec.stages == ["A1-A3"] and c_gen is not None:
                    kind, f, c, line_fid = "GENERIC", rec.value, c_gen, row.factor_id
        if kind is None:
            n_unresolved += 1

        # A1-A3
        e_mfg = act_mfg = 0.0
        has_mfg = False
        if kind is None:
            skip["A13-01"] += 1
        elif q_ord is None:
            skip["A13-03" if kind == "EPD" else "A13-01"] += 1
        else:
            act_mfg = q_ord * c
            e_mfg = act_mfg * f
            has_mfg = True
            add("A1-A3", line_fid, act_mfg)
            val["A13-03" if kind == "EPD" else "A13-01"] += e_mfg
            if kind == "COMPOSITE":
                rk = recipe
                rk.append(act_mfg) if len(rk) == 2 else rk.__setitem__(2, rk[2] + act_mfg)
        r_unq = row.unquantified_cost_ratio
        e_unq = 0.0
        if r_unq is not None and 0.0 < r_unq < 1.0:
            g = r_unq / (1.0 - r_unq)
            e_unq = e_mfg * g
            val["A13-04"] += e_unq
            if has_mfg:
                add("A1-A3", line_fid, act_mfg * g)

        # A4 (mass-distance or per-quantity delivery) and the load-factor variant
        e_del = act_del = 0.0
        del_fid = None
        dfid = tr.delivery_factor_id
        e_x12 = 0.0
        if dfid is None:
            tfid = tr.factor_id
            if tfid is None:
                none_refs.append(f"{base}.transport.factor_id (no factor)")
            else:
                refs[tfid] = refs.get(tfid, 0) + 1
            rec = fac(tfid)
            if rec is None or tr.mass_t is None or tr.distance_km is None:
                skip["A4-01"] += 1
                skip["X-12"] += 1
            else:
                act_del = tr.mass_t * tr.distance_km
                e_del = act_del * rec.value
                del_fid = tfid
                val["A4-01"] += e_del
                add("A4", tfid, act_del)
                lf = tr.load_factor
                if lf is not None and lf > 0.0:
                    e_x12 = act_del / lf * rec.value
                    val["X-12"] += e_x12
                else:
                    skip["X-12"] += 1
        else:
            refs[dfid] = refs.get(dfid, 0) + 1
            n_unit_checks += 1
            raw = factors.get(dfid)
            cd_raw = conv(qu, raw.unit, rconv) if raw is not None else None
            if raw is not None and cd_raw is None:
                unit_bad = True
            rec = fac(dfid)
            cd = cd_raw if rec is not None else None
            if cd is None or q_ord is None:
                skip["A4-02"] += 1
            else:
                act_del = q_ord * cd
                e_del = act_del * rec.value
                del_fid = dfid
                val["A4-02"] += e_del
                add("A4", dfid, act_del)

        # installation at renewals
        inst = None
        ifid = row.installation_factor_id
        if ifid is not None:
            refs[ifid] = refs.get(ifid, 0) + 1
            n_unit_checks += 1
            raw = factors.get(ifid)
            ci_raw = conv(qu, raw.unit, rconv) if raw is not None else None
            if raw is not None and ci_raw is None:
                unit_bad = True
            rec = fac(ifid)
            if rec is not None and ci_raw is not None and q_ord is not None:
                inst = (ifid, q_ord * ci_raw, q_ord * ci_raw * rec.value)
        if unit_bad:
            unit_viol.append(f"{base}.quantity_unit")

        # end of life: haul (C2), routes (C3 / C4), mass balance (C-05), item x route table (X-09)
        hfid = eol.haul_factor_id
        if hfid is None:
            none_refs.append(f"{base}.end_of_life.haul_factor_id (no factor)")
        else:
            refs[hfid] = refs.get(hfid, 0) + 1
        mass = eol.mass_kg
        e_c2 = act_c2 = 0.0
        rec = fac(hfid)
        has_c2 = False
        if rec is None or mass is None:
            skip["C2-01"] += 1
        else:
            act_c2 = mass / 1000.0 * eol.haul_distance_km
            e_c2 = act_c2 * rec.value
            has_c2 = True
            val["C2-01"] += e_c2
            add("C2", hfid, act_c2)
        e_c3 = e_c4 = 0.0
        route_lines = []
        fraction_sum = 0.0
        negative = False
        if mass is None:
            skip["C3-01"] += 1
            skip["C4-01"] += 1
        else:
            m_row = x09_mass.get(row.material_class)
            if m_row is None:
                m_row = x09_mass[row.material_class] = dict.fromkeys(model.EOL_ROUTES, 0.0)
                x09_emis[row.material_class] = dict.fromkeys(model.EOL_ROUTES, 0.0)
            e_row = x09_emis[row.material_class]
        for route in eol.routes:
            rfid = route.factor_id
            if rfid is None:
                none_refs.append(f"{base}.end_of_life.routes (no factor)")
            else:
                refs[rfid] = refs.get(rfid, 0) + 1
            p = route.fraction
            fraction_sum += p
            negative = negative or p < 0.0
            if mass is None:
                continue
            m = mass * p
            m_row[route.route] += m
            rec = fac(rfid)
            if rec is None:
                continue
            e = m * rec.value
            e_row[route.route] += e
            x09_total += e
            if route.route == "LANDFILL":
                e_c4 += e
                add("C4", rfid, m)
                route_lines.append(("C4", rfid, m))
            else:
                e_c3 += e
                add("C3", rfid, m)
                route_lines.append(("C3", rfid, m))
        val["C3-01"] += e_c3
        val["C4-01"] += e_c4
        if negative or fraction_sum > 1.0 + 1e-6:
            c05_viol.append(f"{base}.end_of_life.routes")
        elif fraction_sum < 1.0 - 1e-6:
            c05_under.append(f"{base}.end_of_life.routes")
        c_kg_any = conv(qu, "kg", rconv) if comp is None else c_kg
        if c_kg_any is None or q_ord is None or mass is None:
            c05_unchecked += 1
        elif mass > q_ord * c_kg_any * (1.0 + 1e-6):
            c05_viol.append(f"{base}.end_of_life.mass_kg")

        # renewals (B4) and repairs (B3) as multipliers of the row's own lines
        cycle = row.refresh_cycle
        n = cf.renewal_count(T, cycle)
        if c_kg_any is None or q_ord is None or mass is None:
            x10_excluded += 1
        else:
            x10_resource += q_ord * c_kg_any * (1 + n)
            x10_waste += ((q_ord - q_inst) * c_kg_any + mass) * (1 + n)
        e_b4 = 0.0
        if n:
            u = e_mfg + e_del + e_c2 + e_c3 + e_c4
            if inst is not None:
                u += inst[2]
            e_b4 = n * u
            val["B4-02"] += e_b4
            if has_mfg:
                add("B4", line_fid, act_mfg * n)
            if del_fid is not None:
                add("B4", del_fid, act_del * n)
            if has_c2:
                add("B4", hfid, act_c2 * n)
            for _, rfid, m in route_lines:
                add("B4", rfid, m * n)
            if inst is not None:
                add("B4", inst[0], inst[1] * n)
            cyc_u[cycle] = cyc_u.get(cycle, 0.0) + u
            cyc_n[cycle] = n
        rr = row.repair_rate
        if rr is not None:
            val["B3-02"] += e_mfg * rr * T
            if rr != 0.0 and e_mfg != 0.0:
                years = T - cf.skip_weight_periodic(T, cycle, n) if n else T
                val["B3-01"] += e_mfg * rr * years
                add("B3", line_fid, act_mfg * rr * years)
                repair_rate_sum += e_mfg * rr
                if n:
                    cyc_r[cycle] = cyc_r.get(cycle, 0.0) + e_mfg * rr

        # simplified-estimate classes (X-17)
        mc = row.material_class
        if mc in ("REBAR", "STRUCTURAL_STEEL", "CONCRETE", "TIMBER"):
            class_sum[mc] += e_mfg
        elif qu == "m2":
            div = row.construction_division
            if div in ("ROOF_EXTERIOR_WALL", "OPENINGS"):
                class_sum["ENVELOPE"] += e_mfg
            elif div == "INTERIOR":
                class_sum["INTERIOR"] += e_mfg

        if detail:
            L["q_ord"].append(q_ord)
            L["q_inst"].append(q_inst)
            if q_ord is None or row.reuse_rate is None:
                L["net"].append(None)
                L["disp"].append(None)
            else:
                d = (q_ord - q_inst) * (1.0 - row.reuse_rate)
                L["disp"].append(d)
                L["net"].append(q_inst + d)
            L["a1302"].append(recipe[0] if recipe is not None else None)
            L["kind"].append(kind)
            L["factor"].append(f)
            L["conv"].append(c)
            L["a1301"].append(e_mfg if kind in ("GENERIC", "COMPOSITE") else 0.0)
            L["a1303"].append(e_mfg if kind == "EPD" else 0.0)
            L["a1304"].append(e_unq)
            L["a401"].append(e_del if dfid is None else 0.0)
            L["a402"].append(e_del if dfid is not None else 0.0)
            L["x12"].append(e_x12)
            L["c2"].append(e_c2)
            L["c3"].append(e_c3)
            L["c4"].append(e_c4)
            L["n"].append(n)
            L["b4m"].append(e_b4)

    # =============================== equipment: one pass ===============================
    n_events_total = 0
    for j, eq in enumerate(scn.equipment):
        base = f"equipment[{j}]"
        for name in E_FIELDS:
            value = getattr(eq, name)
            if name == "service_life" and value is None and eq.replacement_event_list is not None:
                continue
            see(eq, name, value, f"{base}.{name}")
        fid = eq.factor_id
        if fid is None:
            none_refs.append(f"{base}.factor_id (no factor)")
        else:
            refs[fid] = refs.get(fid, 0) + 1
        n_unit_checks += 1
        raw = factors.get(fid) if fid is not None else None
        c_raw = conv(eq.quantity_unit, raw.unit) if raw is not None else None
        if raw is not None and c_raw is None:
            unit_viol.append(f"{base}.quantity_unit")
        rec = fac(fid)
        qty = eq.quantity
        e0 = act0 = 0.0
        has0 = False
        if qty is None or rec is None or c_raw is None:
            skip["X-01"] += 1
        else:
            act0 = qty * c_raw
            e0 = act0 * rec.value
            has0 = True
            val["X-01"] += e0
            add("A1-A3", fid, act0)
        efid = eq.eol_factor_id
        if efid is not None:
            refs[efid] = refs.get(efid, 0) + 1
        rec = fac(efid)
        e_eol = 0.0
        has_eol = False
        if rec is None or eq.end_of_life_mass_kg is None:
            skip["X-14"] += 1
        else:
            e_eol = eq.end_of_life_mass_kg * rec.value
            has_eol = True
            val["X-14"] += e_eol
            add("C3", efid, eq.end_of_life_mass_kg)
        extra = []
        u = e0 + e_eol
        for xfid in (eq.delivery_factor_id, eq.installation_factor_id):
            if xfid is None:
                continue
            refs[xfid] = refs.get(xfid, 0) + 1
            rec = fac(xfid)
            cx = conv(eq.quantity_unit, rec.unit) if rec is not None else None
            if qty is not None and cx is not None:
                extra.append((xfid, qty * cx))
                u += qty * cx * rec.value
        explicit = eq.replacement_event_list
        if explicit is not None:
            events = [float(t) for t in explicit if 0 < t < T]
            n = len(events)
        else:
            n = cf.renewal_count(T, eq.service_life)
            events = None
        n_events_total += n
        e_b4 = n * u
        if n:
            val["B4-02"] += e_b4
            if has0:
                add("B4", fid, act0 * n)
            for xfid, act in extra:
                add("B4", xfid, act * n)
            if has_eol:
                add("B4", efid, eq.end_of_life_mass_kg * n)
            if explicit is not None:
                explicit_b4 += e_b4
                for t in events:
                    b4_year[math.ceil(t)] += u
            else:
                cycle = eq.service_life
                cyc_u[cycle] = cyc_u.get(cycle, 0.0) + u
                cyc_n[cycle] = n
        if eq.end_of_life_mass_kg is None:
            x10_excluded += 1
        else:
            x10_waste += eq.end_of_life_mass_kg * (1 + n)
        rr = eq.repair_rate
        if rr is not None:
            val["B3-02"] += e0 * rr * T
            if rr != 0.0 and e0 != 0.0:
                if explicit is not None:
                    years = T - cf.skip_weight_events(T, events)
                    for y in {math.ceil(t) for t in events}:
                        b3_year_adjust[y] += e0 * rr * (wl if y == Y else 1.0)
                else:
                    years = T - cf.skip_weight_periodic(T, eq.service_life, n) if n else T
                    if n:
                        cyc_r[eq.service_life] = cyc_r.get(eq.service_life, 0.0) + e0 * rr
                val["B3-01"] += e0 * rr * years
                add("B3", fid, act0 * rr * years)
                repair_rate_sum += e0 * rr
        if detail:
            L["x01"].append(e0)
            L["x14"].append(e_eol)
            L["b4e"].append(e_b4)
            L["events"].append(events if events is not None else [k * eq.service_life for k in range(1, n + 1)])

    # =============================== refrigerants: closed form per charge cycle ===============================
    b1_01 = b1_02 = b1_03 = b1_04 = 0.0
    b1_items = []
    b1_year = [0.0] * (Y + 1)
    b1_event_year = [0.0] * (Y + 1)
    for j, dev in enumerate(scn.refrigerants):
        base = f"refrigerants[{j}]"
        for name in R_FIELDS:
            see(dev, name, getattr(dev, name), f"{base}.{name}")
        if dev.service_life is None and dev.change_years is None:
            see(dev, "service_life", None, f"{base}.service_life")
        m0, gwp, rate = dev.charge_mass_kg, dev.gwp, dev.annual_leak_rate
        if m0 is not None and gwp is not None:
            b1_01 += m0 * gwp
        if m0 is None or gwp is None or rate is None:
            b1_items.append(0.0)
            continue
        if dev.change_years is not None:
            years = [math.ceil(t) for t in sorted(float(t) for t in dev.change_years if 0 < t < T)]
        else:
            years = [math.ceil(k * dev.service_life) for k in range(1, cf.renewal_count(T, dev.service_life) + 1)]
        leaked, before, end = cf.refrigerant_device(T, m0, rate, dev.top_up, years)
        e = leaked * gwp
        b1_02 += e
        b1_items.append(e)
        if dev.replacement_loss_rate is not None:
            for y, m in zip(years, before):
                loss = m * dev.replacement_loss_rate * gwp
                b1_03 += loss
                b1_event_year[y] += loss
        if dev.end_of_life_recovery_rate is not None:
            b1_04 += end * (1.0 - dev.end_of_life_recovery_rate) * gwp
        if detail:                          # the yearly series still needs one value per year
            m = m0
            k = 0
            for y in range(1, Y + 1):
                leak = m * rate * (wl if y == Y else 1.0)
                b1_year[y] += leak * gwp
                if not dev.top_up:
                    m -= leak
                while k < len(years) and years[k] == y:
                    m = m0
                    k += 1
    add("B1", REFRIGERANT, b1_02 + b1_03 + b1_04)

    # =============================== construction site (A5) ===============================
    site = scn.construction
    grid = scn.operation.grid
    grid_ok = grid.licence_status in ALLOWED
    see(site, "electricity_kwh", site.electricity_kwh, "construction.electricity_kwh")
    a5_01 = 0.0
    a5_01_ok = site.electricity_kwh is not None and grid_ok
    if a5_01_ok:
        a5_01 = site.electricity_kwh * grid.construction_value
        add("A5", GRID, a5_01)
    a5_02 = a5_03 = 0.0
    a5_02_skip = a5_03_skip = 0
    for k, fuel in enumerate(site.fuels):
        see(site, f"fuels[{k}].quantity", fuel.quantity, f"construction.fuels[{k}].quantity")
        fid = fuel.factor_id
        if fid is None:
            none_refs.append(f"construction.fuels[{k}].factor_id (no factor)")
        else:
            refs[fid] = refs.get(fid, 0) + 1
        n_unit_checks += 1
        raw = factors.get(fid) if fid is not None else None
        c_raw = conv(fuel.unit, raw.unit, fuel.conversions) if raw is not None else None
        if raw is not None and c_raw is None:
            unit_viol.append(f"construction.fuels[{k}].unit")
        rec = fac(fid)
        if fuel.quantity is None or rec is None or c_raw is None:
            a5_02_skip += 1
            continue
        a5_02 += fuel.quantity * c_raw * rec.value
        add("A5", fid, fuel.quantity * c_raw)
    for k, waste in enumerate(site.waste_streams):
        see(site, f"waste_streams[{k}].mass_kg", waste.mass_kg, f"construction.waste_streams[{k}].mass_kg")
        fid = waste.factor_id
        if fid is None:
            none_refs.append(f"construction.waste_streams[{k}].factor_id (no factor)")
        else:
            refs[fid] = refs.get(fid, 0) + 1
        rec = fac(fid)
        if waste.mass_kg is None or rec is None:
            a5_03_skip += 1
            continue
        a5_03 += waste.mass_kg * rec.value
        add("A5", fid, waste.mass_kg)
    a5_04 = a5_01 + a5_02 + a5_03

    # =============================== operation (B6, B2, B7): weighted year sums ===============================
    op, ww = scn.operation, scn.water_waste
    G = cf.grid_cumulative(T, grid)             # None for a TABLE scenario
    profiles = (op.electricity, op.onsite_generation, op.onsite_export)
    need_series = detail or G is None or any(p.kind != "CONSTANT" for p in profiles)
    series = {}
    if need_series:
        gk = grid.table
        net = [0.0]
        elec = [0.0]
        elec_w = 0.0
        ct, gt, xt = op.electricity.table, op.onsite_generation.table, op.onsite_export.table
        for k in range(Y):
            nk = max(0.0, ct[k] - (gt[k] - xt[k]))
            ek = nk * gk[k] if grid_ok else 0.0
            net.append(nk)
            elec.append(ek)
            elec_w += (wl if k == Y - 1 else 1.0) * ek
        series["net"], series["elec"] = net, elec
        if G is None:
            G = 0.0
            for k in range(Y):
                G += (wl if k == Y - 1 else 1.0) * gk[k]
    if G is not None and all(p.kind == "CONSTANT" for p in profiles):
        # constant demand and generation: one multiplication with the cumulative factor
        elec_w = max(0.0, op.electricity.base - (op.onsite_generation.base - op.onsite_export.base)) * G if grid_ok else 0.0

    def annual(profile, fid, path, stage):
        """Weighted activity of one annual profile (closed form unless it is a table)."""
        nonlocal n_unit_checks
        if fid is None:
            none_refs.append(f"{path}_factor_id (no factor)")
        else:
            refs[fid] = refs.get(fid, 0) + 1
        n_unit_checks += 1
        raw = factors.get(fid) if fid is not None else None
        u0 = profile.unit.split("/")[0]
        c_raw = conv(u0, raw.unit) if raw is not None else None
        if raw is not None and c_raw is None:
            unit_viol.append(path)
        rec = fac(fid)
        if rec is None or c_raw is None:
            return None, None
        if profile.kind == "TABLE":
            total = 0.0
            tb = profile.table
            for k in range(Y):
                total += (wl if k == Y - 1 else 1.0) * tb[k]
        else:
            total = cf.linear_weighted_sum(T, profile.base, profile.slope or 0.0)
        act = total * c_raw
        add(stage, fid, act)
        return act * rec.value, (profile, c_raw, rec.value)

    def series_of(parts):
        out = [0.0] * (Y + 1)
        for part in parts:
            if part is None:
                continue
            profile, c_raw, value = part
            tb = profile.table
            for k in range(Y):
                out[k + 1] += tb[k] * c_raw * value
        return out

    b6_parts, b6_fuel, b6_skip = [], 0.0, 0
    for profile, fid, path in ((op.gas, op.gas_factor_id, "operation.gas"), (op.oil, op.oil_factor_id, "operation.oil"),
                               (op.district_heat, op.district_heat_factor_id, "operation.district_heat")):
        e, part = annual(profile, fid, path, "B6")
        if e is None:
            b6_skip += 1
        else:
            b6_fuel += e
            b6_parts.append(part)
    b7 = []
    for profile, fid, path in ((ww.water, ww.water_factor_id, "water_waste.water"),
                               (ww.sewage, ww.sewage_factor_id, "water_waste.sewage"),
                               (ww.municipal_waste, ww.waste_factor_id, "water_waste.municipal_waste")):
        b7.append(annual(profile, fid, path, "B7"))
    b7_total = sum(e for e, _ in b7 if e is not None)
    b6_03 = elec_w + b6_fuel
    b2 = elec_w * op.facility_management_ratio
    add("B6", GRID, elec_w - b2)
    add("B2", GRID, b2)
    area = scn.project.gross_floor_area
    x11 = area * op.electricity_per_m2_per_year * G if area is not None else None

    # =============================== building-level end of life (C1, C2 hauls) ===============================
    c1 = 0.0
    c1_skip = 0
    end = scn.end_of_life
    for k, act in enumerate(end.demolition_activities):
        see(end, f"demolition_activities[{k}].quantity", act.quantity, f"end_of_life.demolition_activities[{k}].quantity")
        fid = act.factor_id
        if fid is None:
            none_refs.append(f"end_of_life.demolition_activities[{k}].factor_id (no factor)")
        else:
            refs[fid] = refs.get(fid, 0) + 1
        n_unit_checks += 1
        raw = factors.get(fid) if fid is not None else None
        c_raw = conv(act.unit, raw.unit) if raw is not None else None
        if raw is not None and c_raw is None:
            unit_viol.append(f"end_of_life.demolition_activities[{k}].unit")
        rec = fac(fid)
        if act.quantity is None or rec is None or c_raw is None:
            c1_skip += 1
            continue
        c1 += act.quantity * c_raw * rec.value
        add("C1", fid, act.quantity * c_raw)
    for k, haul in enumerate(end.waste_hauls):
        see(end, f"waste_hauls[{k}].mass_t", haul.mass_t, f"end_of_life.waste_hauls[{k}].mass_t")
        see(end, f"waste_hauls[{k}].distance_km", haul.distance_km, f"end_of_life.waste_hauls[{k}].distance_km")
        fid = haul.factor_id
        if fid is None:
            none_refs.append(f"end_of_life.waste_hauls[{k}].factor_id (no factor)")
        else:
            refs[fid] = refs.get(fid, 0) + 1
        rec = fac(fid)
        if rec is None or haul.mass_t is None or haul.distance_km is None:
            skip["C2-01"] += 1
            continue
        val["C2-01"] += haul.mass_t * haul.distance_km * rec.value
        add("C2", fid, haul.mass_t * haul.distance_km)

    # =============================== rebuild (B5): a multiplier on the initial stages ===============================
    bnd = scn.boundary
    b5_n = cf.renewal_count(T, bnd.replacement_cycle) if bnd.reconstruction_scenario != "NONE" else 0
    k5 = b5_n * bnd.reconstruction_scope_fraction if bnd.reconstruction_scenario != "NONE" else 0.0
    b5_base = (val["A13-01"] + val["A13-03"] + val["A13-04"] + val["X-01"] + val["A4-01"] + val["A4-02"] + a5_04 + c1
               + val["C2-01"] + val["C3-01"] + val["C4-01"] + val["X-14"])
    b5 = k5 * b5_base
    if k5:
        d5 = acc["B5"]
        for s in INITIAL:
            for fid, act in acc[s].items():
                d5[fid] = d5.get(fid, 0.0) + act * k5

    # =============================== composites: expand recipe lines once per recipe ===============================
    x03_mass, x03_emis = {}, {}
    for key, recipe in recipes.items():
        kg = recipe[2] if len(recipe) > 2 else None
        if kg is None:
            continue
        for fid, fraction in key:
            m = kg * fraction
            e = m * factors[fid].value
            x03_mass[fid] = x03_mass.get(fid, 0.0) + m
            x03_emis[fid] = x03_emis.get(fid, 0.0) + e
            val["X-03"] += e
    for key, count in recipe_refs.items():
        for fid, _ in key:
            refs[fid] = refs.get(fid, 0) + count
    for s in STAGES:
        d = acc[s]
        for key in [k for k in d if type(k) is tuple]:
            act = d.pop(key)
            for fid, fraction in key:
                d[fid] = d.get(fid, 0.0) + act * fraction

    # =============================== stage vector, gases, CO2-only: read from the table ===============================
    gases = scn.gases
    by_gas = dict.fromkeys(gases, 0.0)
    grid_total = refrigerant_total = 0.0
    stage_all, stage_co2 = {}, {}
    used = set()
    for s in STAGES:
        total = co2 = 0.0
        for fid, act in acc[s].items():
            if fid == GRID:
                grid_total += act
                total += act
                co2 += act
            elif fid == REFRIGERANT:
                refrigerant_total += act
                total += act
            else:
                rec = factors[fid]
                used.add(fid)
                total += act * rec.value
                amounts = rec.gas_amounts
                co2 += act * amounts["CO2"]
                for g in gases:
                    by_gas[g] += act * amounts[g]
        stage_all[s] = total
        stage_co2[s] = co2
    from_gases = 0.0
    for g in gases:
        from_gases += scn.gwp[g] * by_gas[g]
    by_stage = {s: stage_all[s] for s in STAGES if s in inc}

    # stage values from the unit totals (a second, independent accumulation used by QA-01)
    unit_stage = {
        "A1-A3": val["A13-01"] + val["A13-03"] + val["A13-04"] + val["X-01"], "A4": val["A4-01"] + val["A4-02"],
        "A5": a5_04, "B1": b1_02 + b1_03 + b1_04, "B2": b2, "B3": val["B3-01"], "B4": val["B4-02"], "B5": b5,
        "B6": b6_03 - b2, "B7": b7_total, "C1": c1, "C2": val["C2-01"], "C3": val["C3-01"] + val["X-14"], "C4": val["C4-01"],
    }
    qa01 = [f"stage {s}" for s in STAGES if abs(unit_stage[s] - stage_all[s]) > 1e-9 * max(abs(unit_stage[s]), 1.0)]

    # =============================== indicators (SUM): linear functions of the stage vector ===============================
    def pick(stages):
        total = 0.0
        for s in stages:
            if s in by_stage:
                total += by_stage[s]
        return total

    upfront = pick(("A1-A3", "A4", "A5"))
    embodied = pick(("A1-A3", "A4", "A5", "B1", "B2", "B3", "B4", "B5", "C1", "C2", "C3", "C4"))
    wlc = pick(STAGES)
    area_ok = area is not None and area > 0.0
    if wlc > 0.0 and all(v >= 0.0 for v in by_stage.values()):
        sum_07 = {"defined": True, "by_stage": {s: v / wlc for s, v in by_stage.items()}}
    else:
        sum_07 = {"defined": False, "by_stage": {}}

    base_scn = population.BASELINES.get(bnd.baseline_scenario)
    if base_scn is None:
        sum_08 = {"status": "NO_BASELINE", "delta": None, "saving": None}
    else:
        reasons = []
        if base_scn.project.gross_floor_area != area:
            reasons.append("AREA")
        if base_scn.boundary.study_period != T:
            reasons.append("PERIOD")
        if set(base_scn.boundary.included_lifecycle_stages) != inc:
            reasons.append("STAGES")
        if base_scn.boundary.results_gas_scope != bnd.results_gas_scope:
            reasons.append("GAS_SCOPE")
        if {f.release_year for f in base_scn.factors.values()} != {f.release_year for f in factors.values()}:
            reasons.append("FACTOR_VERSION")
        if reasons:
            sum_08 = {"status": "NOT_COMPARABLE", "reasons": reasons, "delta": None, "saving": None}
        else:
            bid = base_scn.meta.scenario_id
            b_total = _BASELINE_TOTALS.get(bid)
            if b_total is None:                 # computed once per baseline, then reused
                b_total = _BASELINE_TOTALS[bid] = evaluate(base_scn, detail=False)["SUM-03"]["value"]
            sum_08 = {"status": "COMPARED", "baseline": b_total, "delta": wlc - b_total,
                      "saving": (b_total - wlc) / b_total if b_total > 0.0 else None}

    # =============================== checks (rule table evaluated on memoised keys) ===============================
    bad = {}
    n_refs = 0
    for fid, count in refs.items():
        n_refs += count
        rec = factors.get(fid)
        if rec is None or rec.licence_status not in ALLOWED or not rec.source_url:
            bad[f"factors{{{fid}}}.licence_status" if rec is not None else f"{fid} (no factor)"] = count
    for path in none_refs:
        bad[path] = bad.get(path, 0) + 1
    n_refs += len(none_refs)
    cu = scn.summary_quantities.concrete_uptake_factor_id
    if cu is not None:
        n_refs += 1
        rec = factors.get(cu)
        if rec is None or rec.licence_status not in ALLOWED or not rec.source_url:
            key = f"factors{{{cu}}}.licence_status"
            bad[key] = bad.get(key, 0) + 1
    if not grid_ok:
        bad["operation.grid"] = 1
    area_sum = 0.0
    for use in sorted(scn.project.use_area_breakdown):
        area_sum += scn.project.use_area_breakdown[use]
    if not area_ok:
        sys_04 = {"ok": False, "status": "INVALID", "sum": area_sum, "residual": None}
        qa_04 = {"ok": False, "status": "NOT_EVALUATED"}
    else:
        residual = area - area_sum
        sys_04 = {"ok": abs(residual) <= 1e-9 * area, "status": "EVALUATED", "sum": area_sum, "residual": residual}
        qa_04 = {"ok": abs(residual) <= 1e-6 * area, "status": "EVALUATED"}
    qa02 = []
    for j, eq in enumerate(scn.equipment):
        if eq.replacement_event_list and not all(0 <= t < T for t in eq.replacement_event_list):
            qa02.append(f"equipment[{j}].replacement_event_list")
    for j, dev in enumerate(scn.refrigerants):
        if dev.change_years and not all(0 <= t < T for t in dev.change_years):
            qa02.append(f"refrigerants[{j}].change_years")
    qa03 = [fid for fid in sorted(used) if factors[fid].licence_status not in ALLOWED or not factors[fid].source_url]

    sq = scn.summary_quantities
    rec = fac(sq.concrete_uptake_factor_id)
    cs = conv("m3", rec.unit) if rec is not None else None
    sto_02 = sq.concrete_m3 * cs * rec.value if cs is not None else None

    x17, x17_total = {}, 0.0
    summary_q = {"REBAR": sq.reinforcement_kg, "STRUCTURAL_STEEL": sq.steel_kg, "CONCRETE": sq.concrete_m3,
                 "TIMBER": sq.timber_m3, "ENVELOPE": sq.envelope_m2, "INTERIOR": sq.interior_m2}
    for k in SIMPLE_CLASSES:
        qk = summary_q[k]
        fbar = class_sum[k] / qk if qk else 0.0
        x17[k] = {"quantity": qk, "fbar": fbar, "emission": qk * fbar}
        x17_total += qk * fbar

    by_cycle, x08_total = {}, explicit_b4
    for cycle in sorted(cyc_u):
        e = cyc_n[cycle] * cyc_u[cycle]
        by_cycle[repr(float(cycle))] = {"count": cyc_n[cycle], "unit_emission": cyc_u[cycle], "emission": e}
        x08_total += e

    R = {
        "SYS-01": {"ok": not missing, "counts": counts, "violations": missing},
        "SYS-02": {"ok": not unit_viol, "n_checked": n_unit_checks, "violations": unit_viol},
        "SYS-03": {"ok": not bad, "n_checked": n_refs + 1, "violations": sorted(bad), "n_references_affected": sum(bad.values())},
        "SYS-04": sys_04,
        "A13-05": {"n_skipped": skip["A13-05"]},
        "X-13": {},
        "A13-02": {"n_invalid": n_invalid},
        "X-15": {"n_unresolved": n_unresolved},
        "A13-01": {"value": val["A13-01"], "n_skipped": skip["A13-01"]},
        "A13-03": {"value": val["A13-03"], "n_skipped": skip["A13-03"]},
        "A13-04": {"value": val["A13-04"]},
        "X-01": {"value": val["X-01"], "n_skipped": skip["X-01"]},
        "X-03": {"value": val["X-03"], "mass_by_component": x03_mass, "emission_by_component": x03_emis},
        "A4-01": {"value": val["A4-01"], "n_skipped": skip["A4-01"]},
        "X-12": {"value": val["X-12"], "n_skipped": skip["X-12"]},
        "A4-02": {"value": val["A4-02"], "n_skipped": skip["A4-02"]},
        "A5-01": {"value": a5_01, "computed": a5_01_ok},
        "A5-02": {"value": a5_02, "n_skipped": a5_02_skip},
        "A5-03": {"value": a5_03, "n_skipped": a5_03_skip},
        "A5-04": {"value": a5_04, "parts": {"power": a5_01, "fuels": a5_02, "waste": a5_03}, "other_assessed": False},
        "X-17": {"value": x17_total, "by_class": x17},
        "B4-01": {"n_events": n_events_total},
        "B4-03": {},
        "B4-02": {"value": val["B4-02"]},
        "X-08": {"value": x08_total, "by_cycle": by_cycle, "explicit": explicit_b4},
        "B3-01": {"value": val["B3-01"]},
        "B3-02": {"value": val["B3-02"]},
        "B1-01": {"value": b1_01},
        "B1-02": {"value": b1_02},
        "B1-03": {"value": b1_03},
        "B1-04": {"value": b1_04},
        "B5-01": {"value": b5, "n_events": b5_n},
        "X-06": {},
        "B6-04": {},
        "B6-01": {"computed": grid_ok},
        "B6-02": {"n_skipped": b6_skip},
        "B6-03": {"value": b6_03},
        "B2-01": {"value": b2},
        "X-11": {"value": x11},
        "B7-01": {"n_skipped": 0 if b7[0][0] is not None else 1},
        "B7-02": {"n_skipped": 0 if b7[1][0] is not None else 1},
        "B7-03": {"n_skipped": 0 if b7[2][0] is not None else 1},
        "B7-04": {"value": b7_total},
        "C1-01": {"value": c1, "n_skipped": c1_skip},
        "C2-01": {"value": val["C2-01"], "n_skipped": skip["C2-01"]},
        "C3-01": {"value": val["C3-01"], "n_skipped": skip["C3-01"]},
        "C4-01": {"value": val["C4-01"], "n_skipped": skip["C4-01"]},
        "X-14": {"value": val["X-14"], "n_skipped": skip["X-14"]},
        "C-05": {"ok": not c05_viol, "violations": c05_viol, "under_allocated": c05_under, "n_mass_unchecked": c05_unchecked},
        "X-09": {"value": x09_total, "mass": x09_mass, "emission": x09_emis},
        "X-10": {"resource_kg": x10_resource, "waste_kg": x10_waste, "n_excluded": x10_excluded},
        "STO-01": {"value": sq.timber_m3 * sq.timber_dry_density_kg_per_m3 * sq.timber_carbon_fraction * (44.0 / 12.0)},
        "STO-02": {"value": sto_02},
        "X-02": {"by_stage": by_stage, "by_stage_all": stage_all},
        "X-04": {"value": from_gases + grid_total + refrigerant_total, "by_gas": by_gas, "co2e_from_gases": from_gases,
                 "grid_co2e": grid_total, "refrigerant_co2e": refrigerant_total, "by_stage_recomputed": unit_stage},
        "X-05": {"value": sum(stage_co2[s] for s in STAGES if s in inc), "by_stage_co2": stage_co2},
        "X-07": {"value": wlc},
        "SUM-01": {"value": upfront},
        "SUM-02": {"value": embodied},
        "SUM-03": {"value": wlc},
        "SUM-04": {"value": wlc / area if area_ok else None},
        "SUM-05": {"value": wlc / (area * T) if area_ok and T > 0.0 else None},
        "SUM-06": {"value": wlc / 1000.0},
        "SUM-07": sum_07,
        "SUM-08": sum_08,
        "QA-01": {"ok": not qa01, "violations": qa01},
        "QA-02": {"ok": not qa02, "violations": qa02},
        "QA-03": {"ok": not qa03, "violations": qa03, "n_used": len(used)},
        "QA-04": qa_04,
    }
    if not detail:
        return R

    # =============================== per-row lists and yearly series (detail only) ===============================
    R["A13-05"].update(q_ord=L["q_ord"], q_inst=L["q_inst"])
    R["X-13"].update(by_item=L["net"], waste_by_item=L["disp"])
    R["A13-02"]["by_item"] = L["a1302"]
    R["X-15"].update(kind=L["kind"], factor=L["factor"], conv=L["conv"])
    for uid, key in (("A13-01", "a1301"), ("A13-03", "a1303"), ("A13-04", "a1304"), ("X-01", "x01"), ("A4-01", "a401"),
                     ("A4-02", "a402"), ("X-12", "x12"), ("C2-01", "c2"), ("C3-01", "c3"), ("C4-01", "c4"), ("X-14", "x14")):
        R[uid]["by_item"] = L[key]
    R["B4-01"]["events"] = L["events"]
    R["B4-03"]["by_item"] = L["n"]
    R["B1-02"]["by_item"] = b1_items

    w = [0.0] + [1.0] * (Y - 1) + ([wl] if Y else [])
    # renewals and repairs per year from the cycle groups (one entry per distinct cycle, not per row)
    b3_year = [repair_rate_sum * w[y] - b3_year_adjust[y] for y in range(Y + 1)]
    for cycle, n in cyc_n.items():
        u = cyc_u[cycle]
        rsum = cyc_r.get(cycle, 0.0)
        seen = set()
        for k in range(1, n + 1):
            y = math.ceil(k * cycle)
            b4_year[y] += u
            if y not in seen:
                seen.add(y)
                b3_year[y] -= rsum * w[y]
    b5_year = [0.0] * (Y + 1)
    for k in range(1, b5_n + 1):
        b5_year[math.ceil(k * bnd.replacement_cycle)] += bnd.reconstruction_scope_fraction * b5_base
    g_series = [0.0]
    for k in range(Y):
        if grid.kind == "CONSTANT":
            g_series.append(grid.start)
        elif grid.kind == "LINEAR_DECLINE_TO_FLOOR":
            g_series.append(max(grid.floor, grid.start - grid.annual_decline * k))
        elif grid.kind == "STEPWISE":
            v = None
            for step in grid.steps:
                if step.from_index <= k:
                    v = step.value
            g_series.append(v)
        else:
            g_series.append(grid.table[k])
    tb = grid.table
    R["X-06"].update(by_year=g_series,
                     matches_table=all(g_series[k + 1] == tb[k] or abs(g_series[k + 1] - tb[k]) <= 1e-12 * abs(tb[k]) for k in range(Y)))
    fuel_series = series_of(b6_parts)
    b7_series = [series_of([part]) for _, part in b7]
    R["B6-04"]["by_year"] = series["net"]
    R["B6-01"]["by_year"] = series["elec"]
    R["B6-02"]["by_year"] = fuel_series
    for uid, s in zip(("B7-01", "B7-02", "B7-03"), b7_series):
        R[uid]["by_year"] = s
    R["B4-02"].update(by_item_material=L["b4m"], by_item_equipment=L["b4e"], by_year=b4_year)
    R["B3-01"]["by_year"] = b3_year
    R["B1-02"]["by_year"] = b1_year
    R["B1-03"]["by_year"] = b1_event_year
    R["B5-01"]["by_year"] = b5_year

    out = [0.0] * (Y + 1)
    for s in ("A1-A3", "A4", "A5"):
        if s in inc:
            out[0] += stage_all[s]
    share = op.facility_management_ratio
    elec = series["elec"]
    for y in range(1, Y + 1):
        e = 0.0
        ew = w[y] * elec[y]
        if "B6" in inc:
            e += ew * (1.0 - share) + w[y] * fuel_series[y]
        if "B2" in inc:
            e += ew * share
        if "B7" in inc:
            e += w[y] * (b7_series[0][y] + b7_series[1][y] + b7_series[2][y])
        if "B1" in inc:
            e += b1_year[y] + b1_event_year[y]
        if "B3" in inc:
            e += b3_year[y]
        if "B4" in inc:
            e += b4_year[y]
        if "B5" in inc:
            e += b5_year[y]
        out[y] += e
    last = Y if Y >= 1 else 0
    for s in ("C1", "C2", "C3", "C4"):
        if s in inc:
            out[last] += stage_all[s]
    if "B1" in inc:
        out[last] += b1_04
    cumulative, running = [], 0.0
    for v in out:
        running += v
        cumulative.append(running)
    R["X-07"] = {"by_year": out, "cumulative": cumulative, "value": running}
    return R
