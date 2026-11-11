"""One-off editing script: exact-substring replacements in fastcalc/engine.py (each must match exactly once)."""
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8").read()


def rep(old, new, count=1):
    global s
    n = s.count(old)
    if n != count:
        raise SystemExit(f"expected {count} occurrence(s), found {n}:\n{old[:200]}")
    s = s.replace(old, new)


# ------------------------------------------------------------------ helpers before finish
rep('''def finish(A: Aggregate, T: float | None = None, detail: bool | None = None, baseline_totals: dict | None = None,
           _compare: bool = True) -> dict:
''', '''# ---- every list of event years is built by one of these four functions ----

def _explicit_event_years(T, entries):
    """Years of the entries of an equipment row's explicit event list that are used (list order)."""
    return cf.explicit_years(T, entries)


def _change_years(T, change_years, service_life):
    """Years of the charge changes of one refrigerant device, in non-decreasing order."""
    if change_years is not None:
        return sorted(cf.explicit_years(T, change_years))
    if service_life is None:
        return []                                       # no list and no service life: the charge is never changed
    return cf.periodic_years(service_life, cf.renewal_count(T, service_life))


def _renewal_years(period, n_events):
    """Years of the periodic renewals of the rows that share a period (only the yearly outputs need them)."""
    return cf.periodic_years(period, n_events)


def _rebuild_years(period, n_events):
    """Years of the rebuild or major-refurbishment events (only the yearly output needs them)."""
    return cf.periodic_years(period, n_events)


# ---- every loop over the study years is in a named function: the five below, ``_values`` and ``_same``
#      above, and the year scans of closed_forms ----

def _purchased_series(consumption, generation, export, c_gen, c_exp, c_elec, g_values, elec_ok, Y, wl):
    """Year by year: purchased electricity max(0, .), its emission, and the weighted sum of the emission."""
    net_series = [0.0]
    elec_series = [0.0]
    elec_w = 0.0
    for k in range(Y):
        nk = max(0.0, consumption[k] - (generation[k] * c_gen - export[k] * c_exp))
        ek = nk * c_elec * g_values[k] if elec_ok else 0.0
        net_series.append(nk)
        elec_series.append(ek)
        elec_w += (wl if k == Y - 1 else 1.0) * ek
    return net_series, elec_series, elec_w


def _add_leak_series(out, charge, rate, top_up, ev_years, Y, wl):
    """Add the yearly leak of one refrigerant device to ``out`` (the series needs one value per year)."""
    m = 1.0
    k = 0
    for y in range(1, Y + 1):
        leak = m * rate * (wl if y == Y else 1.0)
        out[y] += charge * leak
        if not top_up:
            m -= leak
        while k < len(ev_years) and ev_years[k] == y:
            m = 1.0
            k += 1


def _add_repair_series(out, rate, w, skip_years, Y):
    """Add the yearly repair emission ``rate`` to ``out`` for every year without a renewal."""
    for y in range(1, Y + 1):                           # added year by year, never by subtraction
        if y not in skip_years:
            out[y] += rate * w[y]


def _annual_series(parts, fval, Y):
    """Yearly emission (unweighted) of the annual quantities of one unit."""
    out = [0.0] * (Y + 1)
    for profile, hit in parts:
        values = _values(profile, Y)
        value = fval[hit[0]]
        for k in range(Y):
            out[k + 1] += values[k] * hit[1] * value
    return out


def _whole_life_series(inc, stage_all, share, w, elec_series, series, b1_year, b1_event_year, b3_year, b4_year, b5_year,
                       b1_04, Y):
    """The whole-life series: initial stages in year 0, the yearly series, the end-of-life stages in the last year."""
    out = [0.0] * (Y + 1)
    for s in ("A1-A3", "A4", "A5"):
        if s in inc:
            out[0] += stage_all[s]
    for y in range(1, Y + 1):
        e = 0.0
        ew = w[y] * elec_series[y]
        if "B6" in inc:
            e += (ew * (1.0 - share) if "B2" in inc else ew) + w[y] * series["B6-02"][y]
        if "B2" in inc:
            e += ew * share
        if "B7" in inc:
            e += w[y] * (series["B7-01"][y] + series["B7-02"][y] + series["B7-03"][y])
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
    return {"by_year": out, "cumulative": cumulative, "value": running}


def finish(A: Aggregate, T: float | None = None, detail: bool | None = None, baseline_totals: dict | None = None,
           _compare: bool = True) -> dict:
''')

# ------------------------------------------------------------------ finish: head
rep('''    wl = cf.last_weight(T)
    stats = dict(A.stats)
    factors = scn.factors
''', '''    wl = cf.last_weight(T)
    factors = scn.factors
''')
rep('''    def tot(table):
        """Value of a table: one multiplication per distinct factor key."""
        total = 0.0
        for key, act in table.items():
            total += act * fval[key]
        stats["table_factor_products"] += len(table)
        return total

''', '')
rep('''        events = cf.explicit_years(T, years)            # the years of the entries that are used
''', '''        events = _explicit_event_years(T, years)        # the years of the entries that are used
''')

# ------------------------------------------------------------------ finish: refrigerants
rep('''    # ---- refrigerants: charge cycles ----
    b1_02 = b1_03 = b1_04 = 0.0
    b1_skip = [0, 0, 0]
    b1_items = []
    b1_year = [0.0] * (Y + 1)
    b1_event_year = [0.0] * (Y + 1)
    for j, (dev, ok) in enumerate(A.devices):
        years_raw = dev.change_years
        if years_raw is not None:
            check_list(years_raw, f"refrigerants[{j}].change_years")
        loss_ok, rec_ok = _ratio(dev.replacement_loss_rate), _ratio(dev.end_of_life_recovery_rate)
        if not ok:
            b1_skip[0] += 1
            b1_skip[1] += 1
            b1_skip[2] += 1
            b1_items.append(0.0)
            continue
        if years_raw is not None:
            ev_years = sorted(cf.explicit_years(T, years_raw))
        elif dev.service_life is None:
            ev_years = []                               # no list and no service life: the charge is never changed
        else:
            ev_years = cf.periodic_years(dev.service_life, cf.renewal_count(T, dev.service_life))
        charge = dev.charge_mass_kg * dev.gwp          # the device's charge in CO2e: the activity of all three terms
        leaked, before, end = cf.refrigerant_fractions(T, dev.annual_leak_rate, dev.top_up, ev_years)
        b1_02 += charge * leaked
        b1_items.append(charge * leaked)
        if loss_ok:
            for y, share in zip(ev_years, before):
                loss = charge * share * dev.replacement_loss_rate
                b1_03 += loss
                b1_event_year[y] += loss
        else:
            b1_skip[1] += 1
        if rec_ok:
            b1_04 += charge * end * (1.0 - dev.end_of_life_recovery_rate)
        else:
            b1_skip[2] += 1
        if detail:                                      # the yearly series needs one value per year
            m = 1.0
            k = 0
            for y in range(1, Y + 1):
                stats["year_loop_iterations"] += 1
                leak = m * dev.annual_leak_rate * (wl if y == Y else 1.0)
                b1_year[y] += charge * leak
                if not dev.top_up:
                    m -= leak
                while k < len(ev_years) and ev_years[k] == y:
                    m = 1.0
                    k += 1
    tables["B1"] = {REFRIGERANT: b1_02 + b1_03 + b1_04}
''', '''    # ---- refrigerants: the device table (charge x GWP) times the fractions of the charge cycle ----
    b1_01 = b1_02 = b1_03 = b1_04 = 0.0
    b1_01_skip = 0
    b1_skip = [0, 0, 0]
    b1_items = []
    b1_year = [0.0] * (Y + 1)
    b1_event_year = [0.0] * (Y + 1)
    charges = A.charges
    for j, (ok, rate, top_up, years_raw, life, loss_rate, recovery_rate) in enumerate(A.devices):
        charge = charges[j]                             # the device's charge in CO2e: the activity of all four terms
        if charge is None:
            b1_01_skip += 1
        else:
            b1_01 += charge                             # B1-01: the sum of the device table
        if years_raw is not None:
            check_list(years_raw, f"refrigerants[{j}].change_years")
        loss_ok, rec_ok = _ratio(loss_rate), _ratio(recovery_rate)
        if not ok:
            b1_skip[0] += 1
            b1_skip[1] += 1
            b1_skip[2] += 1
            b1_items.append(0.0)
            continue
        ev_years = _change_years(T, years_raw, life)
        leaked, before, end = cf.refrigerant_fractions(T, rate, top_up, ev_years)
        b1_02 += charge * leaked
        b1_items.append(charge * leaked)
        if loss_ok:
            for y, share in zip(ev_years, before):
                loss = charge * share * loss_rate
                b1_03 += loss
                b1_event_year[y] += loss
        else:
            b1_skip[1] += 1
        if rec_ok:
            b1_04 += charge * end * (1.0 - recovery_rate)
        else:
            b1_skip[2] += 1
        if detail:                                      # the yearly series needs one value per year
            _add_leak_series(b1_year, charge, rate, top_up, ev_years, Y, wl)
    tables["B1"] = {REFRIGERANT: b1_02 + b1_03 + b1_04}
''')

# ------------------------------------------------------------------ finish: grid
rep('''        G, H = cf.segment_moments(segments, T)
        g_values = []
        for a, b, alpha, beta in segments:
            g_values.extend([alpha + beta * k for k in range(a, b)] if beta else [alpha] * (b - a))
        grid_matches = _same(g_values, grid.table)
''', '''        G, H = cf.segment_moments(segments, T)
        g_values = cf.segment_values(segments)          # one value per year: for the copy check and the yearly outputs
        grid_matches = _same(g_values, grid.table)
''')
rep('''        G, H = cf.table_moments(grid.table, T)
        stats["year_loop_iterations"] += Y
        g_values = grid.table[:Y]
''', '''        G, H = cf.table_moments(grid.table, T)
        g_values = grid.table[:Y]
''')
rep('''    grid_usable = grid_source != "NONE"
    stats["consistency_scan_values"] += Y               # table values read for the copy check or the validity check
''', '''    grid_usable = grid_source != "NONE"
''')
rep('''    profiles = (op.electricity, op.onsite_generation, op.onsite_export)
    stats["consistency_scan_values"] += 3 * Y
    states''', '''    profiles = (op.electricity, op.onsite_generation, op.onsite_export)
    states''')
rep('''        c_v, g_v, x_v = (_values(p, Y) for p in profiles)
        net_series = [0.0]
        elec_series = [0.0]
        for k in range(Y):
            stats["year_loop_iterations"] += 1
            nk = max(0.0, c_v[k] - (g_v[k] * c_gen - x_v[k] * c_exp))
            ek = nk * c_elec * g_values[k] if elec_ok else 0.0
            net_series.append(nk)
            elec_series.append(ek)
            elec_w += (wl if k == Y - 1 else 1.0) * ek
        if linear is not None and elec_ok:
''', '''        c_v, g_v, x_v = (_values(p, Y) for p in profiles)
        net_series, elec_series, elec_w = _purchased_series(c_v, g_v, x_v, c_gen, c_exp, c_elec, g_values, elec_ok, Y, wl)
        if linear is not None and elec_ok:
''')
rep('''    for name, profile, hit in A.annual:
        stats["consistency_scan_values"] += Y
        d, usable, matches = _profile_state(profile, Y)
''', '''    for name, profile, hit in A.annual:
        d, usable, matches = _profile_state(profile, Y)
''')
rep('''        else:
            total = 0.0
            tb = profile.table
            for k in range(Y):
                stats["year_loop_iterations"] += 1
                total += (wl if k == Y - 1 else 1.0) * tb[k]
        _add(tables[name], hit[0], total * hit[1])
''', '''        else:
            total = cf.table_weighted_sum(profile.table, T)
        _add(tables[name], hit[0], total * hit[1])
''')

# ------------------------------------------------------------------ finish: read-outs
rep('''    val = {name: tot(tables[name]) for name in (''', '''    val = {name: tot(tables[name], fval) for name in (''')
rep('''        total = co2 = 0.0
        for key, act in merged.items():
            if key is GRID:
                grid_total += act
                total += act
                co2 += act
            elif key is REFRIGERANT:
                refrigerant_total += act
                total += act
            else:
                total += act * fval[key]
                amounts = gas_of(key)
''', '''        stage_all[s] = tot(merged, fval)                # the value column (the two pseudo keys have the value 1)
        co2 = 0.0
        for key, act in merged.items():                 # the same entries with the gas columns
            if key is GRID:
                grid_total += act
                co2 += act
            elif key is REFRIGERANT:
                refrigerant_total += act
            else:
                amounts = gas_of(key)
''')
rep('''        stats["table_factor_products"] += len(merged)
        stage_all[s] = total
        stage_co2[s] = co2
''', '''        stage_co2[s] = co2
''')
rep('''    # ---- indicators: linear functions of the stage vector ----
    def pick(stages):
        total = 0.0
        for s in stages:
            if s in by_stage:
                total += by_stage[s]
        return total

    upfront = pick(("A1-A3", "A4", "A5"))
    embodied = pick(("A1-A3", "A4", "A5", "B1", "B2", "B3", "B4", "B5", "C1", "C2", "C3", "C4"))
    wlc = pick(STAGES)
    area = scn.project.gross_floor_area
    area_ok = M["area_ok"]
    if wlc > 0.0 and all(v >= 0.0 for v in by_stage.values()):
        sum_07 = {"defined": True, "by_stage": {s: v / wlc for s, v in by_stage.items()}}
    else:
        sum_07 = {"defined": False, "by_stage": {}}
''', '''    # ---- indicators: one function of the stage vector (a subset sum divided by a scale) ----
    upfront = indicator(by_stage, UPFRONT)
    embodied = indicator(by_stage, EMBODIED)
    wlc = indicator(by_stage, STAGES)                   # the whole-life total; the comparison below builds on it
    area = scn.project.gross_floor_area
    area_ok = M["area_ok"]
    if wlc > 0.0 and all(v >= 0.0 for v in by_stage.values()):
        sum_07 = {"defined": True, "by_stage": {s: indicator(by_stage, (s,), wlc) for s in by_stage}}
    else:
        sum_07 = {"defined": False, "by_stage": {}}
''')
rep('''        fbar = tot(tables["CLASS:" + k]) / qk
''', '''        fbar = tot(tables["CLASS:" + k], fval) / qk
''')
rep('''    for cls, routes in M["x09_emis"].items():
        x09_emis[cls] = {r: tot(t) for r, t in routes.items()}
''', '''    for cls, routes in A.route_tables.items():
        x09_emis[cls] = {r: tot(t, fval) for r, t in routes.items()}
''')
rep('''    x08_total = tot(explicit_b4)
''', '''    x08_total = tot(explicit_b4, fval)
''')
rep('''        u = group_u[cycle] = tot(A.groups[cycle].u)
''', '''        u = group_u[cycle] = tot(A.groups[cycle].u, fval)
''')
rep('''        "B1-01": {"value": M["b1_01"], "n_skipped": M["b1_01_skip"]},
''', '''        "B1-01": {"value": b1_01, "n_skipped": b1_01_skip},
''')
rep('''        "STO-02": {"value": tot(tables["STO-02"]) if M["sto_02_ok"] else None},
''', '''        "STO-02": {"value": tot(tables["STO-02"], fval) if M["sto_02_ok"] else None},
''')
rep('''        "SUM-04": {"value": wlc / area if area_ok else None},
        "SUM-05": {"value": wlc / (area * T) if area_ok else None},
        "SUM-06": {"value": wlc / 1000.0},
''', '''        "SUM-04": {"value": indicator(by_stage, STAGES, area) if area_ok else None},
        "SUM-05": {"value": indicator(by_stage, STAGES, area * T) if area_ok else None},
        "SUM-06": {"value": indicator(by_stage, STAGES, 1000.0)},
''')
rep('''    R["_stats"] = stats
    R["_tables"] = tables
''', '''    R["_stats"] = dict(A.stats)
    R["_tables"] = tables
''')

# ------------------------------------------------------------------ _detail
rep('''    L = A.rows
    fval = A.fval
    stats = R["_stats"]
    inc = set(scn.boundary.included_lifecycle_stages)
''', '''    L = A.rows
    fval = A.fval
    inc = set(scn.boundary.included_lifecycle_stages)
''')
rep('''    events_all = []
    n_events = 0
    cycle_years = {}                                    # event years of one period, built once per distinct period
    for j, eq in enumerate(scn.equipment):
        if L["eexp"][j]:
            ev = explicit_events[j]
        else:
            cycle = L["ecycle"][j]
            ev = cycle_years.get(cycle)
            if ev is None:
                ev = cycle_years[cycle] = cf.periodic_years(cycle, counts[cycle]) if counts[cycle] else []
            stats["event_lists_built"] += 1             # one list per equipment row in the output
            ev = list(ev)
        events_all.append(ev)
        n_events += len(ev)
''', '''    events_all = []
    n_events = 0
    period_years = {}                                   # event years of one period, built once per distinct period

    def years_of(cycle):
        ev = period_years.get(cycle)
        if ev is None:
            ev = period_years[cycle] = _renewal_years(cycle, counts[cycle]) if counts[cycle] else []
        return ev

    for j, explicit in enumerate(L["eexp"]):            # the per-row lists of the aggregation; the rows are not read again
        ev = explicit_events[j] if explicit else list(years_of(L["ecycle"][j]))    # a copy per row for the output
        events_all.append(ev)
        n_events += len(ev)
''')
rep('''            u = group_u[cycle] if cycle in group_u else sum(act * fval[key] for key, act in grp.u.items())
            for y in cf.periodic_years(cycle, n):
                b4_year[y] += u
                skip_years.add(y)
        if grp.r:
            rate = sum(act * fval[key] for key, act in grp.r.items())
            for y in range(1, Y + 1):               # added year by year, never by subtraction
                if y not in skip_years:
                    b3_year[y] += rate * w[y]
''', '''            u = group_u[cycle] if cycle in group_u else tot(grp.u, fval)
            for y in years_of(cycle):
                b4_year[y] += u
                skip_years.add(y)
        if grp.r:
            _add_repair_series(b3_year, tot(grp.r, fval), w, skip_years, Y)
''')
rep('''        if rline is not None:
            rate = rline[1] * fval[rline[0]]
            for y in range(1, Y + 1):
                if y not in skip_years:
                    b3_year[y] += rate * w[y]
    b5_year = [0.0] * (Y + 1)
    if b5_n:
        for y in cf.periodic_years(bnd.replacement_cycle, b5_n):
            b5_year[y] += bnd.reconstruction_scope_fraction * b5_base
''', '''        if rline is not None:
            _add_repair_series(b3_year, rline[1] * fval[rline[0]], w, skip_years, Y)
    b5_year = [0.0] * (Y + 1)
    if b5_n:
        for y in _rebuild_years(bnd.replacement_cycle, b5_n):
            b5_year[y] += bnd.reconstruction_scope_fraction * b5_base
''')
rep('''    series = {}
    for name, parts in annual_parts.items():
        out = [0.0] * (Y + 1)
        for profile, hit in parts:
            values = _values(profile, Y)
            value = fval[hit[0]]
            for k in range(Y):
                out[k + 1] += values[k] * hit[1] * value
        series[name] = out
        R[name]["by_year"] = out
''', '''    series = {}
    for name, parts in annual_parts.items():
        series[name] = R[name]["by_year"] = _annual_series(parts, fval, Y)
''')
rep('''    out = [0.0] * (Y + 1)
    for s in ("A1-A3", "A4", "A5"):
        if s in inc:
            out[0] += stage_all[s]
    share = scn.operation.facility_management_ratio if b2_ok else 0.0
    for y in range(1, Y + 1):
        e = 0.0
        ew = w[y] * elec_series[y]
        if "B6" in inc:
            e += (ew * (1.0 - share) if "B2" in inc else ew) + w[y] * series["B6-02"][y]
        if "B2" in inc:
            e += ew * share
        if "B7" in inc:
            e += w[y] * (series["B7-01"][y] + series["B7-02"][y] + series["B7-03"][y])
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
''', '''    share = scn.operation.facility_management_ratio if b2_ok else 0.0
    R["X-07"] = _whole_life_series(inc, stage_all, share, w, elec_series, series, b1_year, b1_event_year, b3_year, b4_year,
                                   b5_year, b1_04, Y)
''')

open(p, "w", encoding="utf-8").write(s)
print("ok", len(s))
