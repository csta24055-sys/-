"""Unified model of the independent conceptual calculation.

Two steps:

``aggregate(scn)``   one pass over the input rows, independent of the study period T.
                     Every emission is written as a line (table, factor key, activity) and
                     the activities are summed per table and factor key. Lines that recur
                     with a period are summed per distinct period.
``finish(agg, T)``   applies the multipliers that depend on T (renewal counts, repair
                     years, charge cycles, weighted year sums) and reads every result
                     from the tables: a value is sum over factor keys of activity * factor.

    E[stage] = sum over lines  activity * factor * multiplier(stage; T, row parameters)

``evaluate(scn)`` = ``finish(aggregate(scn), T)``. Because the first step does not depend
on T, another study period only needs ``finish`` again (``sweep``).

Results have the same shape as the reference calculation so that they can be compared
leaf by leaf. With ``detail=False`` the per-row lists and yearly series are left out and
no factor is multiplied row by row.

This module does not call the reference calculation. Research tooling only.
"""
from __future__ import annotations

import math

from synth import model, population

from . import closed_forms as cf

ALLOWED = model.ALLOWED_LICENCE_STATES
STAGES = model.LIFECYCLE_STAGES
MEMO = model.STAGE_MEMO
GRID = "GRID"                # purchased electricity: the activity is already an emission
REFRIGERANT = "REFRIGERANT"  # refrigerant releases: likewise
INITIAL = ("A1-A3", "A4", "A5", "C1", "C2", "C3", "C4")
SIMPLE_CLASSES = ("REBAR", "STRUCTURAL_STEEL", "CONCRETE", "TIMBER", "ENVELOPE", "INTERIOR")
M_FIELDS = ("quantity", "waste_rate", "reuse_rate", "material_life", "repair_rate", "refresh_cycle")
E_FIELDS = ("quantity", "service_life", "repair_rate", "end_of_life_mass_kg")
R_FIELDS = ("charge_mass_kg", "gwp", "annual_leak_rate", "replacement_loss_rate", "end_of_life_recovery_rate")
# which unit tables make up each stage (B-stage tables are filled in finish)
STAGE_TABLES = {
    "A1-A3": ("A13-01", "A13-03", "A13-04", "X-01"), "A4": ("A4-01", "A4-02"), "A5": ("A5-01", "A5-02", "A5-03"),
    "B1": ("B1",), "B2": ("B2-01",), "B3": ("B3-01",), "B4": ("B4-02",), "B5": ("B5-01",), "B6": ("B6",),
    "B7": ("B7-01", "B7-02", "B7-03"), "C1": ("C1-01",), "C2": ("C2-01",), "C3": ("C3-01", "X-14"), "C4": ("C4-01",),
}
STAGE_UNITS = {
    "A1-A3": ("A13-01", "A13-03", "A13-04", "X-01"), "A4": ("A4-01", "A4-02"), "A5": ("A5-01", "A5-02", "A5-03"),
    "B1": ("B1-02", "B1-03", "B1-04"), "B2": ("B2-01", "B6-01"), "B3": ("B3-01",), "B4": ("B4-02",), "B5": ("B5-01",),
    "B6": ("B6-01", "B6-02"), "B7": ("B7-01", "B7-02", "B7-03"), "C1": ("C1-01",), "C2": ("C2-01",),
    "C3": ("C3-01", "X-14"), "C4": ("C4-01",),
}


def _nonneg(x) -> bool:
    return x is not None and x >= 0.0 and not math.isinf(x)


def _ratio(x) -> bool:
    return x is not None and 0.0 <= x <= 1.0


def _within(residual, tol, scale) -> bool:
    """The one residual test shared by the area checks and the stage reconciliation."""
    return abs(residual) <= tol * scale


def _annual_unit(unit):
    head, sep, tail = unit.partition("/")
    return head if sep and tail == "year" else None


def _same(values, table) -> bool:
    return all(v == t or abs(v - t) <= 1e-12 * max(abs(v), abs(t)) for v, t in zip(values, table))


class _Group:
    """Rows renewed with the same period: their lines, summed per factor key."""

    __slots__ = ("u", "r", "resource", "waste", "incomplete", "equipment_rows")

    def __init__(self):
        self.u = {}            # one renewal: factor key -> activity
        self.r = {}            # repairs per year: factor key -> activity * repair rate
        self.resource = 0.0    # kg ordered per generation
        self.waste = 0.0       # kg of waste per generation
        self.incomplete = 0    # rows whose renewal lacks a component
        self.equipment_rows = 0


class Aggregate:
    """Everything that does not depend on the study period."""

    def __init__(self, scn, detail):
        self.scn = scn
        self.detail = detail
        self.tables = {}       # table name -> {factor key: activity}
        self.groups = {}       # period -> _Group
        self.explicit = []     # equipment with an explicit event list
        self.devices = []      # valid refrigerant devices
        self.annual = []       # annual quantities with a factor
        self.fval = {GRID: 1.0, REFRIGERANT: 1.0}   # factor key -> value (recipes get a derived value)
        self.recipes = {}      # composition content -> recipe record
        self.stats = {"factor_resolutions": 0, "unit_conversions_resolved": 0, "recipes_computed": 0,
                      "rows_scanned": 0, "row_factor_products": 0, "year_loop_iterations": 0,
                      "event_lists_built": 0, "table_factor_products": 0, "consistency_scan_values": 0}
        self.out = {}          # unit id -> results that are already final
        self.rows = {}         # per-row lists (detail only)


def _add(table, key, activity):
    table[key] = table.get(key, 0.0) + activity


def aggregate(scn, detail: bool = True) -> Aggregate:
    """One pass over the input rows. Independent of the study period."""
    A = Aggregate(scn, detail)
    factors = scn.factors
    stats = A.stats
    T = {name: {} for name in ("A13-01", "A13-03", "A13-04", "X-01", "A4-01", "A4-02", "X-12", "A5-01", "A5-02", "A5-03",
                               "C1-01", "C2-01", "C3-01", "C4-01", "X-14", "STO-02", "X-16")}
    for k in SIMPLE_CLASSES:
        T["CLASS:" + k] = {}
    A.tables = T
    fval = A.fval

    # ---- one resolution per distinct (factor, stage, unit); one conversion per distinct unit pair ----
    table_conv = {}

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
            stats["unit_conversions_resolved"] += 1
            r = table_conv[key] = model.conversion_factor(scn.unit_conversions, u, v)
            return r

    unit_viol, stage_viol = set(), set()
    n_uses = 0
    memo = {}

    def use(fid, stage, unit, extra, path):
        """(factor key, conversion) when the factor may be used for this activity, else None."""
        nonlocal n_uses
        n_uses += 1
        if unit is None:
            unit_viol.add(path)
            return None
        if fid is None:
            return None
        if not extra:
            key = (fid, stage, unit)
            hit = memo.get(key)
            if hit is None:
                hit = memo[key] = _resolve(fid, stage, unit, ())
            if hit[1]:
                unit_viol.add(path)
            return hit[0]
        hit = _resolve(fid, stage, unit, extra)
        if hit[1]:
            unit_viol.add(path)
        return hit[0]

    def _resolve(fid, stage, unit, extra):
        stats["factor_resolutions"] += 1
        rec = factors.get(fid)
        if rec is None:
            return (None, False)
        c = conv(unit, rec.unit, extra)
        bad_stage = rec.stages != [stage]
        if bad_stage:
            stage_viol.add(f"factors{{{fid}}}.stages")
        if c is None or bad_stage or rec.licence_status not in ALLOWED:
            return (None, c is None)
        fval[fid] = rec.value
        return ((fid, c), False)

    def unit_only(path, a, b, extra=()):
        nonlocal n_uses
        n_uses += 1
        c = conv(a, b, extra) if a is not None and b is not None else None
        if c is None:
            unit_viol.add(path)
        return c

    # ---- licence gate: count references per factor id ----
    refs = {}
    bad_refs = {}

    def ref(fid, path):
        if fid is None:
            key = f"{path} (no factor)"
            bad_refs[key] = bad_refs.get(key, 0) + 1
        else:
            refs[fid] = refs.get(fid, 0) + 1

    # ---- input states ----
    prov = scn.provenance
    counts = {s: 0 for s in model.VALUE_STATES}
    missing = []
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

    skip = dict.fromkeys(("A13-05", "A13-01", "A13-03", "A13-04", "X-01", "A4-01", "A4-02", "X-12", "C2-01", "C3-01",
                          "C4-01", "X-14", "B3", "X-10"), 0)
    routes_skipped = {"C3": 0, "C4": 0}
    n_invalid = n_unresolved = n_declined = 0
    c05_viol, c05_under = [], []
    c05_unchecked = 0
    x09_mass, x09_emis = {}, {}
    groups = A.groups
    assessment = scn.project.assessment_date
    if detail:
        L = A.rows
        for k in ("q_ord", "q_inst", "net", "disp", "a1302", "kind", "factor", "conv", "a1301", "a1303", "a1304", "a401",
                  "a402", "x12", "c2", "c3", "c4", "mcycle", "mu", "x01", "x14", "eu", "ecycle", "eexp"):
            L[k] = []

    # =============================== materials ===============================
    for i, row in enumerate(scn.materials):
        stats["rows_scanned"] += 1
        base = f"materials[{i}]"
        tr, eol = row.transport, row.end_of_life
        qu, rconv = row.quantity_unit, row.conversions
        for name in M_FIELDS:
            see(row, name, getattr(row, name), f"{base}.{name}")
        see(row, "transport.mass_t", tr.mass_t, f"{base}.transport.mass_t")
        see(row, "transport.distance_km", tr.distance_km, f"{base}.transport.distance_km")
        see(row, "end_of_life.mass_kg", eol.mass_kg, f"{base}.end_of_life.mass_kg")

        q, w = row.quantity, row.waste_rate
        if not _nonneg(q) or w is None or not 0.0 <= w < 1.0:
            q_ord = q_inst = None
            skip["A13-05"] += 1
        elif row.quantity_basis == "DESIGN":
            q_inst = q
            q_ord = q / (1.0 - w)
        else:
            q_ord = q
            q_inst = q * (1.0 - w)

        # ---- which factor (EPD, composite, generic) ----
        comp = row.composition
        recipe = None
        hit = None
        c_kg = None
        if comp is not None:
            key = tuple([(c.factor_id, c.mass_fraction) for c in comp])
            recipe = A.recipes.get(key)
            if recipe is None:
                recipe = A.recipes[key] = _make_recipe(key, scn, stats, stage_viol, fval)
            c_kg = unit_only(f"{base}.quantity_unit", qu, "kg", rconv)
            n_uses += len(key)
            if recipe["unit_bad"]:
                unit_viol.add(f"{base}.composition")
            recipe["rows"] += 1
            if recipe["none_at"]:
                for j in recipe["none_at"]:
                    ref(None, f"{base}.composition[{j}].factor_id")
            if recipe["value"] is None:
                n_invalid += 1
        else:
            ref(row.factor_id, f"{base}.factor_id")
            hit = use(row.factor_id, "A1-A3", qu, rconv, f"{base}.quantity_unit")
        kind = f = c = fkey = None
        epd = row.epd
        if epd is not None:
            ref(epd.factor_id, f"{base}.epd.factor_id")
            rec = factors.get(epd.factor_id) if epd.factor_id is not None else None
            if (rec is not None and epd.declared_stages == rec.stages and epd.declared_unit == rec.unit
                    and epd.valid_until == rec.valid_until and rec.valid_until is not None
                    and not rec.valid_until < assessment and rec.stages == ["A1-A3"] and rec.licence_status in ALLOWED):
                ce = conv(qu, rec.unit, rconv)
                if ce is not None:
                    kind, f, c, fkey = "EPD", rec.value, ce, epd.factor_id
                    fval[fkey] = rec.value
            if kind is None:
                n_declined += 1
        if kind is None:
            if comp is not None:
                if recipe["value"] is not None and c_kg is not None:
                    kind, f, c, fkey = "COMPOSITE", recipe["value"], c_kg, key
            elif hit is not None:
                kind, fkey, c = "GENERIC", hit[0], hit[1]
                f = fval[fkey]
        if kind is None:
            n_unresolved += 1

        incomplete = False
        act_mfg = None
        if kind is None:
            skip["A13-01"] += 1
            incomplete = True
        elif q_ord is None:
            skip["A13-03" if kind == "EPD" else "A13-01"] += 1
            incomplete = True
        else:
            act_mfg = q_ord * c
            _add(T["A13-03" if kind == "EPD" else "A13-01"], fkey, act_mfg)
            if kind == "COMPOSITE":
                recipe["kg"] += act_mfg
                recipe["used"] = True
        r_unq = row.unquantified_cost_ratio
        g = None
        if r_unq is not None and r_unq != 0.0:
            if 0.0 < r_unq < 1.0:
                g = r_unq / (1.0 - r_unq)
                if act_mfg is not None:
                    _add(T["A13-04"], fkey, act_mfg * g)
            else:
                skip["A13-04"] += 1

        # ---- delivery: mass-distance, or per quantity ----
        dline = None
        x12 = None
        dfid = tr.delivery_factor_id
        if dfid is None:
            ref(tr.factor_id, f"{base}.transport.factor_id")
            hit = use(tr.factor_id, "A4", "tkm", (), f"{base}.transport")
            if hit is None or not _nonneg(tr.mass_t) or not _nonneg(tr.distance_km):
                skip["A4-01"] += 1
                skip["X-12"] += 1
                incomplete = True
            else:
                dline = (hit[0], tr.mass_t * tr.distance_km * hit[1])
                _add(T["A4-01"], dline[0], dline[1])
                lf = tr.load_factor
                if lf is not None and lf > 0.0:
                    x12 = dline[1] / lf
                    _add(T["X-12"], dline[0], x12)
                else:
                    skip["X-12"] += 1
        else:
            ref(dfid, f"{base}.transport.delivery_factor_id")
            hit = use(dfid, "A4", qu, rconv, f"{base}.quantity_unit")
            if hit is None or q_ord is None:
                skip["A4-02"] += 1
                incomplete = True
            else:
                dline = (hit[0], q_ord * hit[1])
                _add(T["A4-02"], dline[0], dline[1])

        iline = None
        ifid = row.installation_factor_id
        if ifid is not None:
            ref(ifid, f"{base}.installation_factor_id")
            hit = use(ifid, "A5", qu, rconv, f"{base}.quantity_unit")
            if hit is not None and q_ord is not None:
                iline = (hit[0], q_ord * hit[1])
            else:
                incomplete = True

        # ---- end of life ----
        ref(eol.haul_factor_id, f"{base}.end_of_life.haul_factor_id")
        mass = eol.mass_kg
        mass_ok = _nonneg(mass)
        hit = use(eol.haul_factor_id, "C2", "tkm", (), f"{base}.end_of_life")
        hline = None
        if hit is None or not mass_ok or not _nonneg(eol.haul_distance_km):
            skip["C2-01"] += 1
            incomplete = True
        else:
            hline = (hit[0], mass / 1000.0 * eol.haul_distance_km * hit[1])
            _add(T["C2-01"], hline[0], hline[1])
        rlines = []
        fraction_sum = 0.0
        negative = False
        if not mass_ok:
            skip["C3-01"] += 1
            skip["C4-01"] += 1
            incomplete = True
        else:
            m_row = x09_mass.get(row.material_class)
            if m_row is None:
                m_row = x09_mass[row.material_class] = dict.fromkeys(model.EOL_ROUTES, 0.0)
                x09_emis[row.material_class] = {r: {} for r in model.EOL_ROUTES}
            e_row = x09_emis[row.material_class]
        for j, route in enumerate(eol.routes):
            ref(route.factor_id, f"{base}.end_of_life.routes[{j}].factor_id")
            p = route.fraction
            fraction_sum += p
            negative = negative or p < 0.0
            stage = "C4" if route.route == "LANDFILL" else "C3"
            hit = use(route.factor_id, stage, "kg", (), f"{base}.end_of_life")
            if not mass_ok:
                continue
            p_ok = _nonneg(p)
            if p_ok:
                m_row[route.route] += mass * p
            if hit is None or not p_ok:
                routes_skipped[stage] += 1
                incomplete = True
                continue
            act = mass * p * hit[1]
            _add(T["C4-01" if stage == "C4" else "C3-01"], hit[0], act)
            _add(e_row[route.route], hit[0], act)
            rlines.append((stage, hit[0], act))
        if negative or fraction_sum > 1.0 + 1e-6:
            c05_viol.append(f"{base}.end_of_life.routes")
        elif fraction_sum < 1.0 - 1e-6:
            c05_under.append(f"{base}.end_of_life.routes")
        c_any = conv(qu, "kg", rconv) if comp is None else c_kg
        if c_any is None or q_inst is None or mass is None:
            c05_unchecked += 1
        elif mass > q_inst * c_any * (1.0 + 1e-6):
            c05_viol.append(f"{base}.end_of_life.mass_kg")

        # ---- the row's lines go to the group of its renewal period ----
        cycle = row.refresh_cycle if cf.valid_period(row.refresh_cycle) else None
        grp = groups.get(cycle)
        if grp is None:
            grp = groups[cycle] = _Group()
        gu = grp.u
        if act_mfg is not None:
            gu[fkey] = gu.get(fkey, 0.0) + act_mfg
        if dline is not None:
            gu[dline[0]] = gu.get(dline[0], 0.0) + dline[1]
        if hline is not None:
            gu[hline[0]] = gu.get(hline[0], 0.0) + hline[1]
        for _, rk, act in rlines:
            gu[rk] = gu.get(rk, 0.0) + act
        if iline is not None:
            gu[iline[0]] = gu.get(iline[0], 0.0) + iline[1]
        if incomplete:
            grp.incomplete += 1
        rr = row.repair_rate
        if not _nonneg(rr):
            skip["B3"] += 1
        elif act_mfg is not None and rr != 0.0:
            grp.r[fkey] = grp.r.get(fkey, 0.0) + act_mfg * rr
        if c_any is None or q_ord is None or not mass_ok:
            skip["X-10"] += 1
        else:
            grp.resource += q_ord * c_any
            grp.waste += (q_ord - q_inst) * c_any + mass

        # ---- class table for the simplified estimate ----
        if act_mfg is not None:
            mc = row.material_class
            cls = mc if mc in ("REBAR", "STRUCTURAL_STEEL", "CONCRETE", "TIMBER") else None
            if cls is None and qu == "m2":
                div = row.construction_division
                cls = "ENVELOPE" if div in ("ROOF_EXTERIOR_WALL", "OPENINGS") else "INTERIOR" if div == "INTERIOR" else None
            if cls is not None:
                _add(T["CLASS:" + cls], fkey, act_mfg)

        if detail:
            stats["row_factor_products"] += 1
            e_mfg = act_mfg * f if act_mfg is not None else 0.0
            v = lambda line: line[1] * fval[line[0]] if line is not None else 0.0
            e_del, e_c2 = v(dline), v(hline)
            e_c3 = sum(act * fval[rk] for st, rk, act in rlines if st == "C3")
            e_c4 = sum(act * fval[rk] for st, rk, act in rlines if st == "C4")
            L["q_ord"].append(q_ord)
            L["q_inst"].append(q_inst)
            rho = row.reuse_rate
            if q_ord is None or rho is None or not 0.0 <= rho <= 1.0:
                L["net"].append(None)
                L["disp"].append(None)
            else:
                d = (q_ord - q_inst) * (1.0 - rho)
                L["disp"].append(d)
                L["net"].append(q_inst + d)
            L["a1302"].append(recipe["value"] if recipe is not None else None)
            L["kind"].append(kind)
            L["factor"].append(f)
            L["conv"].append(c)
            L["a1301"].append(e_mfg if kind in ("GENERIC", "COMPOSITE") else 0.0)
            L["a1303"].append(e_mfg if kind == "EPD" else 0.0)
            L["a1304"].append(e_mfg * g if g is not None else 0.0)
            L["a401"].append(e_del if dfid is None else 0.0)
            L["a402"].append(e_del if dfid is not None else 0.0)
            L["x12"].append(x12 * fval[dline[0]] if x12 is not None else 0.0)
            L["c2"].append(e_c2)
            L["c3"].append(e_c3)
            L["c4"].append(e_c4)
            L["mcycle"].append(cycle)
            L["mu"].append(e_mfg + e_del + e_c2 + e_c3 + e_c4 + v(iline))

    # =============================== equipment ===============================
    for j, eq in enumerate(scn.equipment):
        stats["rows_scanned"] += 1
        base = f"equipment[{j}]"
        for name in E_FIELDS:
            value = getattr(eq, name)
            if name == "service_life" and value is None and eq.replacement_event_list is not None:
                continue
            see(eq, name, value, f"{base}.{name}")
        qty = eq.quantity
        qty_ok = _nonneg(qty)
        ref(eq.factor_id, f"{base}.factor_id")
        hit = use(eq.factor_id, "A1-A3", eq.quantity_unit, (), f"{base}.quantity_unit")
        lines = []
        incomplete = False
        mline = None
        if not qty_ok or hit is None:
            skip["X-01"] += 1
            incomplete = True
        else:
            mline = (hit[0], qty * hit[1])
            _add(T["X-01"], mline[0], mline[1])
            lines.append(mline)
        for fid, stage in ((eq.delivery_factor_id, "A4"), (eq.installation_factor_id, "A5")):
            if fid is None:
                continue
            refs[fid] = refs.get(fid, 0) + 1
            hit = use(fid, stage, eq.quantity_unit, (), f"{base}.quantity_unit")
            if hit is None or not qty_ok:
                incomplete = True
            else:
                lines.append((hit[0], qty * hit[1]))
        efid = eq.eol_factor_id
        eline = None
        hit = None
        if efid is not None:
            refs[efid] = refs.get(efid, 0) + 1
            hit = use(efid, "C3", "kg", (), f"{base}.end_of_life")
        emass_ok = _nonneg(eq.end_of_life_mass_kg)
        if hit is None or not emass_ok:
            skip["X-14"] += 1
            incomplete = True
        else:
            eline = (hit[0], eq.end_of_life_mass_kg * hit[1])
            _add(T["X-14"], eline[0], eline[1])
            lines.append(eline)
        rr = eq.repair_rate
        rline = None
        if not _nonneg(rr):
            skip["B3"] += 1
        elif mline is not None and rr != 0.0:
            rline = (mline[0], mline[1] * rr)
        years = eq.replacement_event_list
        if years is not None:
            A.explicit.append((j, years, lines, rline, eq.end_of_life_mass_kg if emass_ok else None, incomplete))
            cycle = None
        else:
            cycle = eq.service_life if cf.valid_period(eq.service_life) else None
            grp = groups.get(cycle)
            if grp is None:
                grp = groups[cycle] = _Group()
            for fk, act in lines:
                grp.u[fk] = grp.u.get(fk, 0.0) + act
            if rline is not None:
                grp.r[rline[0]] = grp.r.get(rline[0], 0.0) + rline[1]
            if incomplete:
                grp.incomplete += 1
            grp.equipment_rows += 1
            if emass_ok:
                grp.waste += eq.end_of_life_mass_kg
        if not emass_ok:
            skip["X-10"] += 1
        if detail:
            stats["row_factor_products"] += 1
            L["x01"].append(mline[1] * fval[mline[0]] if mline is not None else 0.0)
            L["x14"].append(eline[1] * fval[eline[0]] if eline is not None else 0.0)
            L["eu"].append(sum(act * fval[fk] for fk, act in lines))
            L["ecycle"].append(cycle)
            L["eexp"].append(years is not None)

    # =============================== refrigerants ===============================
    b1_01 = 0.0
    b1_01_skip = 0
    for j, dev in enumerate(scn.refrigerants):
        base = f"refrigerants[{j}]"
        for name in R_FIELDS:
            see(dev, name, getattr(dev, name), f"{base}.{name}")
        if dev.service_life is None and dev.change_years is None:
            see(dev, "service_life", None, f"{base}.service_life")
        charge_ok = _nonneg(dev.charge_mass_kg) and _nonneg(dev.gwp)
        if charge_ok:
            b1_01 += dev.charge_mass_kg * dev.gwp
        else:
            b1_01_skip += 1
        A.devices.append((dev, charge_ok and _ratio(dev.annual_leak_rate)))

    # =============================== construction site ===============================
    site = scn.construction
    grid = scn.operation.grid
    grid_ok = grid.licence_status in ALLOWED
    head, sep, tail = grid.unit.partition("/")
    grid_u = tail if sep and head == "kgCO2e" and tail else None
    see(site, "electricity_kwh", site.electricity_kwh, "construction.electricity_kwh")
    c_site = unit_only("construction.electricity", "kWh", grid_u)
    a5_01_ok = _nonneg(site.electricity_kwh) and c_site is not None and grid_ok
    if a5_01_ok:
        _add(T["A5-01"], GRID, site.electricity_kwh * c_site * grid.construction_value)
    a5_02_skip = a5_03_skip = 0
    for k, fuel in enumerate(site.fuels):
        see(site, f"fuels[{k}].quantity", fuel.quantity, f"construction.fuels[{k}].quantity")
        ref(fuel.factor_id, f"construction.fuels[{k}].factor_id")
        hit = use(fuel.factor_id, "A5", fuel.unit, fuel.conversions, f"construction.fuels[{k}].unit")
        if not _nonneg(fuel.quantity) or hit is None:
            a5_02_skip += 1
        else:
            _add(T["A5-02"], hit[0], fuel.quantity * hit[1])
    for k, waste in enumerate(site.waste_streams):
        see(site, f"waste_streams[{k}].mass_kg", waste.mass_kg, f"construction.waste_streams[{k}].mass_kg")
        ref(waste.factor_id, f"construction.waste_streams[{k}].factor_id")
        hit = use(waste.factor_id, "A5", "kg", (), f"construction.waste_streams[{k}]")
        if not _nonneg(waste.mass_kg) or hit is None:
            a5_03_skip += 1
        else:
            _add(T["A5-03"], hit[0], waste.mass_kg * hit[1])

    # =============================== operation: units and factors (values wait for T) ===============================
    op, ww = scn.operation, scn.water_waste
    eu = _annual_unit(op.electricity.unit)
    c_elec = unit_only("operation.electricity", eu, grid_u)
    c_gen = unit_only("operation.onsite_generation", _annual_unit(op.onsite_generation.unit), eu)
    c_exp = unit_only("operation.onsite_export", _annual_unit(op.onsite_export.unit), eu)
    for table, profile, fid, path, stage in (
            ("B6-02", op.gas, op.gas_factor_id, "operation.gas", "B6"),
            ("B6-02", op.oil, op.oil_factor_id, "operation.oil", "B6"),
            ("B6-02", op.district_heat, op.district_heat_factor_id, "operation.district_heat", "B6"),
            ("B7-01", ww.water, ww.water_factor_id, "water_waste.water", "B7"),
            ("B7-02", ww.sewage, ww.sewage_factor_id, "water_waste.sewage", "B7"),
            ("B7-03", ww.municipal_waste, ww.waste_factor_id, "water_waste.municipal_waste", "B7")):
        ref(fid, path.replace("municipal_waste", "waste") + "_factor_id")
        A.annual.append((table, profile, use(fid, stage, _annual_unit(profile.unit), (), path)))

    # =============================== building-level end of life, memo items, cost items ===============================
    end = scn.end_of_life
    c1_skip = 0
    for k, act in enumerate(end.demolition_activities):
        see(end, f"demolition_activities[{k}].quantity", act.quantity, f"end_of_life.demolition_activities[{k}].quantity")
        ref(act.factor_id, f"end_of_life.demolition_activities[{k}].factor_id")
        hit = use(act.factor_id, "C1", act.unit, (), f"end_of_life.demolition_activities[{k}].unit")
        if not _nonneg(act.quantity) or hit is None:
            c1_skip += 1
        else:
            _add(T["C1-01"], hit[0], act.quantity * hit[1])
    for k, haul in enumerate(end.waste_hauls):
        see(end, f"waste_hauls[{k}].mass_t", haul.mass_t, f"end_of_life.waste_hauls[{k}].mass_t")
        see(end, f"waste_hauls[{k}].distance_km", haul.distance_km, f"end_of_life.waste_hauls[{k}].distance_km")
        ref(haul.factor_id, f"end_of_life.waste_hauls[{k}].factor_id")
        hit = use(haul.factor_id, "C2", "tkm", (), f"end_of_life.waste_hauls[{k}]")
        if hit is None or not _nonneg(haul.mass_t) or not _nonneg(haul.distance_km):
            skip["C2-01"] += 1
        else:
            _add(T["C2-01"], hit[0], haul.mass_t * haul.distance_km * hit[1])
    sq = scn.summary_quantities
    sto_02_ok = False
    if sq.concrete_uptake_factor_id is not None:
        refs[sq.concrete_uptake_factor_id] = refs.get(sq.concrete_uptake_factor_id, 0) + 1
        hit = use(sq.concrete_uptake_factor_id, MEMO, "m3", (), "summary_quantities.concrete_uptake")
        if hit is not None and _nonneg(sq.concrete_m3):
            _add(T["STO-02"], hit[0], sq.concrete_m3 * hit[1])
            sto_02_ok = True
    x16_skip = 0
    x16_items = []
    deflator = {}
    for k, item in enumerate(scn.cost_items):
        ref(item.factor_id, f"cost_items[{k}].factor_id")
        hit = use(item.factor_id, "A1-A3", item.currency, (), f"cost_items[{k}]")
        dkey = (item.factor_base_year, item.price_year)
        if dkey not in deflator:                         # one ratio per distinct pair of years
            pb, pc = scn.price_index.get(item.factor_base_year), scn.price_index.get(item.price_year)
            deflator[dkey] = pb / pc if pb is not None and pc is not None and pb > 0.0 and pc > 0.0 else None
        d = deflator[dkey]
        if not _nonneg(item.amount) or hit is None or d is None:
            x16_skip += 1
            x16_items.append(None)
        else:
            act = item.amount * d * hit[1]
            _add(T["X-16"], hit[0], act)
            x16_items.append((hit[0], act))

    # =============================== checks that do not depend on T ===============================
    for key, rec in A.recipes.items():
        for fid, _ in key:
            if fid is not None:
                refs[fid] = refs.get(fid, 0) + rec["rows"]
    n_refs = sum(bad_refs.values())
    for fid, count in refs.items():
        n_refs += count
        rec = factors.get(fid)
        if rec is None:
            bad_refs[f"factors{{{fid}}} (no record)"] = count
        elif rec.licence_status not in ALLOWED or not rec.source_url:
            bad_refs[f"factors{{{fid}}}.licence_status"] = count
    if not grid_ok:
        bad_refs["operation.grid"] = 1
    area = scn.project.gross_floor_area
    area_sum = 0.0
    for use_name in sorted(scn.project.use_area_breakdown):
        area_sum += scn.project.use_area_breakdown[use_name]
    area_ok = area is not None and area > 0.0
    if not area_ok:
        sys_04 = {"ok": False, "status": "INVALID", "sum": area_sum, "residual": None}
        qa_04 = {"ok": False, "status": "NOT_EVALUATED"}
    else:
        residual = area - area_sum
        sys_04 = {"ok": _within(residual, 1e-9, area), "status": "EVALUATED", "sum": area_sum, "residual": residual}
        qa_04 = {"ok": _within(residual, 1e-6, area), "status": "EVALUATED"}

    A.out = {
        "SYS-01": {"ok": not missing, "counts": counts, "violations": missing},
        "SYS-02": {"ok": not unit_viol and not stage_viol, "n_checked": n_uses, "violations": sorted(unit_viol),
                   "stage_mismatches": sorted(stage_viol)},
        "SYS-03": {"ok": not bad_refs, "n_checked": n_refs + 1, "violations": sorted(bad_refs),
                   "n_references_affected": sum(bad_refs.values())},
        "SYS-04": sys_04,
        "QA-04": qa_04,
        "A13-05": {"n_skipped": skip["A13-05"]},
        "A13-02": {"n_invalid": n_invalid},
        "X-15": {"n_unresolved": n_unresolved, "n_epd_declined": n_declined},
        "C-05": {"ok": not c05_viol, "violations": c05_viol, "under_allocated": c05_under, "n_mass_unchecked": c05_unchecked},
    }
    A.misc = {"skip": skip, "routes_skipped": routes_skipped, "a5_01_ok": a5_01_ok, "a5_02_skip": a5_02_skip,
              "a5_03_skip": a5_03_skip, "c1_skip": c1_skip, "x16_skip": x16_skip, "x16_items": x16_items,
              "sto_02_ok": sto_02_ok, "b1_01": b1_01, "b1_01_skip": b1_01_skip, "x09_mass": x09_mass,
              "x09_emis": x09_emis, "grid_ok": grid_ok, "c_elec": c_elec, "c_gen": c_gen, "c_exp": c_exp,
              "c_site": c_site, "area_ok": area_ok}
    return A


def _make_recipe(key, scn, stats, stage_viol, fval):
    """Composite factor of one distinct composition: value per kg, computed once."""
    stats["recipes_computed"] += 1
    total_fraction = value = 0.0
    ok = True
    unit_bad = False
    none_at = []
    parts = []
    for j, (fid, fraction) in enumerate(key):
        if fid is None:
            none_at.append(j)
        rec = scn.factors.get(fid) if fid is not None else None
        c = model.conversion_factor(scn.unit_conversions, "kg", rec.unit) if rec is not None else None
        if rec is not None and c is None:
            unit_bad = True
        if rec is not None and rec.stages != ["A1-A3"]:
            stage_viol.add(f"factors{{{fid}}}.stages")
        if (rec is None or c is None or rec.stages != ["A1-A3"] or rec.licence_status not in ALLOWED
                or not _nonneg(fraction)):
            ok = False
            continue
        total_fraction += fraction
        value += fraction * c * rec.value
        parts.append((fid, fraction, c))
    valid = ok and abs(total_fraction - 1.0) <= 1e-6
    if valid:
        fval[key] = value
    return {"value": value if valid else None, "parts": parts if valid else None, "unit_bad": unit_bad,
            "none_at": none_at, "rows": 0, "kg": 0.0, "used": False}


def check_period(scn) -> float:
    T = scn.boundary.study_period
    if T is None or isinstance(T, bool) or not (T > 0.0) or math.isinf(T):
        raise ValueError("study_period must be a finite positive number of years")
    if len(scn.operation.grid.table) < math.ceil(T):
        raise ValueError("year tables are shorter than the study period")
    return T


def _profile(profile, Y):
    """(base, slope) of a parametric profile, or None when the year table is the input."""
    if profile.kind == "CONSTANT" and profile.base is not None:
        return profile.base, 0.0
    if profile.kind == "LINEAR_TREND" and profile.base is not None and profile.slope is not None:
        return profile.base, profile.slope
    return None


def _values(profile, Y):
    d = _profile(profile, Y)
    if d is None:
        return profile.table[:Y]
    return [d[0] + d[1] * k for k in range(Y)] if d[1] else [d[0]] * Y


def finish(A: Aggregate, T: float | None = None, detail: bool | None = None, baseline_totals: dict | None = None,
           _compare: bool = True) -> dict:
    """Apply the multipliers that depend on the study period and read the results from the tables."""
    scn = A.scn
    if T is None:
        T = check_period(scn)
    detail = A.detail if detail is None else detail
    if detail and not A.detail:
        raise ValueError("the aggregate was built without per-row lists")
    Y = cf.n_years(T)
    wl = cf.last_weight(T)
    stats = dict(A.stats)
    factors = scn.factors
    fval = A.fval
    tables = dict(A.tables)
    M = A.misc
    inc = set(scn.boundary.included_lifecycle_stages)
    bnd = scn.boundary
    op, ww = scn.operation, scn.water_waste
    grid = op.grid

    def tot(table):
        """Value of a table: one multiplication per distinct factor key."""
        total = 0.0
        for key, act in table.items():
            total += act * fval[key]
        stats["table_factor_products"] += len(table)
        return total

    # ---- renewals, repairs, masses: one multiplier per distinct period ----
    b4, b3, b3_alt = {}, {}, {}
    n_partial = 0
    resource = waste = 0.0
    counts = {}
    for cycle, grp in A.groups.items():
        n = cf.renewal_count(T, cycle)
        counts[cycle] = n
        resource += grp.resource * (1 + n)
        waste += grp.waste * (1 + n)
        if n:
            n_partial += grp.incomplete
            for key, act in grp.u.items():
                b4[key] = b4.get(key, 0.0) + act * n
        if grp.r:
            years = T - cf.skip_weight_periodic(T, cycle, n) if n else T
            for key, act in grp.r.items():
                b3[key] = b3.get(key, 0.0) + act * years
                b3_alt[key] = b3_alt.get(key, 0.0) + act * T
    explicit_b4 = {}
    explicit_events = {}
    n_events = sum(counts[c] * g.equipment_rows for c, g in A.groups.items())
    qa02, qa02_warn = [], []
    for j, years, lines, rline, emass, incomplete in A.explicit:
        if any(not (t >= 0 and cf.inside(t, T)) for t in years):
            qa02.append(f"equipment[{j}].replacement_event_list")
        if any(t == 0 for t in years):
            qa02_warn.append(f"equipment[{j}].replacement_event_list")
        events = [float(t) for t in years if t > 0 and cf.inside(t, T)]
        explicit_events[j] = events
        n = len(events)
        n_events += n
        if n:
            for key, act in lines:
                explicit_b4[key] = explicit_b4.get(key, 0.0) + act * n
            if incomplete:
                n_partial += 1
        if rline is not None:
            b3[rline[0]] = b3.get(rline[0], 0.0) + rline[1] * (T - cf.skip_weight_events(T, events))
            b3_alt[rline[0]] = b3_alt.get(rline[0], 0.0) + rline[1] * T
        if emass is not None:
            waste += emass * (1 + n)
    for key, act in explicit_b4.items():
        b4[key] = b4.get(key, 0.0) + act
    tables["B4-02"], tables["B3-01"], tables["B3-02"] = b4, b3, b3_alt

    # ---- refrigerants: charge cycles ----
    b1_02 = b1_03 = b1_04 = 0.0
    b1_skip = [0, 0, 0]
    b1_items = []
    b1_year = [0.0] * (Y + 1)
    b1_event_year = [0.0] * (Y + 1)
    for j, (dev, ok) in enumerate(A.devices):
        years_raw = dev.change_years
        if years_raw is not None:
            if any(not (t >= 0 and cf.inside(t, T)) for t in years_raw):
                qa02.append(f"refrigerants[{j}].change_years")
            if any(t == 0 for t in years_raw):
                qa02_warn.append(f"refrigerants[{j}].change_years")
        loss_ok, rec_ok = _ratio(dev.replacement_loss_rate), _ratio(dev.end_of_life_recovery_rate)
        if not ok:
            b1_skip[0] += 1
            b1_skip[1] += 1
            b1_skip[2] += 1
            b1_items.append(0.0)
            continue
        if years_raw is not None:
            ev_years = [cf.event_year(t) for t in sorted(float(t) for t in years_raw if t > 0 and cf.inside(t, T))]
        else:
            ev_years = [cf.event_year(k * dev.service_life) for k in range(1, cf.renewal_count(T, dev.service_life) + 1)]
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

    # ---- grid factor: moments of a piecewise-linear series, or of the table ----
    segments = cf.grid_segments(grid, Y)
    G, H = cf.segment_moments(segments, T) if segments is not None else cf.table_moments(grid.table, T)
    if segments is None:
        stats["year_loop_iterations"] += Y
    g_values = None
    if segments is None:
        g_values = grid.table[:Y]
    else:
        g_values = []
        for a, b, alpha, beta in segments:
            g_values.extend([alpha + beta * k for k in range(a, b)] if beta else [alpha] * (b - a))
    stats["consistency_scan_values"] += Y
    grid_matches = _same(g_values, grid.table[:Y])

    # ---- purchased electricity ----
    c_elec, c_gen, c_exp = M["c_elec"], M["c_gen"], M["c_exp"]
    eu = _annual_unit(op.electricity.unit)
    net_ok = eu is not None and c_gen is not None and c_exp is not None
    elec_ok = M["grid_ok"] and net_ok and c_elec is not None
    profiles = (op.electricity, op.onsite_generation, op.onsite_export)
    stats["consistency_scan_values"] += 3 * Y
    net_match = all(_same(_values(p, Y), p.table[:Y]) for p in profiles)
    net_series = elec_series = None
    elec_w = 0.0
    params = [_profile(p, Y) for p in profiles]
    linear = None
    if net_ok and all(p is not None for p in params):
        B = params[0][0] - (params[1][0] * c_gen - params[2][0] * c_exp)
        S = params[0][1] - (params[1][1] * c_gen - params[2][1] * c_exp)
        if B >= 0.0 and B + S * (Y - 1) >= 0.0:        # the clamp max(0, .) never acts
            linear = (B, S)
    if linear is not None and not detail:
        if elec_ok:
            elec_w = (linear[0] * G + linear[1] * H) * c_elec
    elif net_ok:
        c_v, g_v, x_v = (_values(p, Y) for p in profiles)
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
            elec_w = (linear[0] * G + linear[1] * H) * c_elec
    else:
        net_series = [0.0] * (Y + 1)
        elec_series = [0.0] * (Y + 1)
    share = op.facility_management_ratio
    b2_ok = _ratio(share)
    b2 = elec_w * share if b2_ok else 0.0
    tables["B2-01"] = {GRID: b2}
    tables["B6-01"] = {GRID: elec_w}

    # ---- annual quantities with a factor: weighted year sums ----
    for name in ("B6-02", "B7-01", "B7-02", "B7-03"):
        tables[name] = {}
    annual_skip = dict.fromkeys(("B6-02", "B7-01", "B7-02", "B7-03"), 0)
    annual_match = dict.fromkeys(("B6-02", "B7-01", "B7-02", "B7-03"), True)
    annual_parts = {name: [] for name in annual_skip}
    for name, profile, hit in A.annual:
        stats["consistency_scan_values"] += Y
        annual_match[name] = annual_match[name] and _same(_values(profile, Y), profile.table[:Y])
        if hit is None:
            annual_skip[name] += 1
            continue
        d = _profile(profile, Y)
        if d is not None:
            total = cf.linear_weighted_sum(T, d[0], d[1])
        else:
            total = 0.0
            tb = profile.table
            for k in range(Y):
                stats["year_loop_iterations"] += 1
                total += (wl if k == Y - 1 else 1.0) * tb[k]
        _add(tables[name], hit[0], total * hit[1])
        annual_parts[name].append((profile, hit))
    b6_table = dict(tables["B6-02"])
    _add(b6_table, GRID, elec_w - b2)
    tables["B6"] = b6_table

    # ---- unit values, read from the tables ----
    val = {name: tot(tables[name]) for name in (
        "A13-01", "A13-03", "A13-04", "X-01", "A4-01", "A4-02", "X-12", "A5-01", "A5-02", "A5-03", "C1-01", "C2-01",
        "C3-01", "C4-01", "X-14", "B4-02", "B3-01", "B3-02", "B6-02", "B7-01", "B7-02", "B7-03", "X-16")}
    a5_04 = val["A5-01"] + val["A5-02"] + val["A5-03"]
    b6_03 = elec_w + val["B6-02"]
    b7_04 = val["B7-01"] + val["B7-02"] + val["B7-03"]

    # ---- rebuild: one multiplier on the initial stages ----
    b5_computed = True
    b5_n = 0
    k5 = 0.0
    if bnd.reconstruction_scenario != "NONE":
        if _ratio(bnd.reconstruction_scope_fraction):
            b5_n = cf.renewal_count(T, bnd.replacement_cycle)
            k5 = b5_n * bnd.reconstruction_scope_fraction
        else:
            b5_computed = False
    b5_table = {}
    if k5:
        for s in INITIAL:
            for name in STAGE_TABLES[s]:
                for key, act in tables[name].items():
                    b5_table[key] = b5_table.get(key, 0.0) + act * k5
    tables["B5-01"] = b5_table
    b5_base = (val["A13-01"] + val["A13-03"] + val["A13-04"] + val["X-01"] + val["A4-01"] + val["A4-02"] + a5_04
               + val["C1-01"] + val["C2-01"] + val["C3-01"] + val["C4-01"] + val["X-14"])
    b5 = k5 * b5_base

    # ---- stage vector, gas breakdown, CO2-only: the same tables with other factor columns ----
    gases = scn.gases
    gas_cache = {}

    def gas_of(key):
        g = gas_cache.get(key)
        if g is None:
            if type(key) is tuple:                      # recipe: weighted gas amounts of its components
                g = dict.fromkeys(gases, 0.0)
                for fid, fraction, c in A.recipes[key]["parts"]:
                    amounts = factors[fid].gas_amounts
                    for name in gases:
                        g[name] += fraction * c * amounts[name]
            else:
                g = factors[key].gas_amounts
            gas_cache[key] = g
        return g

    by_gas = dict.fromkeys(gases, 0.0)
    grid_total = refrigerant_total = 0.0
    stage_all, stage_co2 = {}, {}
    used = set()
    for s in STAGES:
        merged = {}
        for name in STAGE_TABLES[s]:
            for key, act in tables[name].items():
                merged[key] = merged.get(key, 0.0) + act
        total = co2 = 0.0
        for key, act in merged.items():
            if key == GRID:
                grid_total += act
                total += act
                co2 += act
            elif key == REFRIGERANT:
                refrigerant_total += act
                total += act
            else:
                total += act * fval[key]
                amounts = gas_of(key)
                co2 += act * amounts["CO2"]
                for name in gases:
                    by_gas[name] += act * amounts[name]
                if type(key) is tuple:
                    used.update(fid for fid, _, _ in A.recipes[key]["parts"])
                else:
                    used.add(key)
        stats["table_factor_products"] += len(merged)
        stage_all[s] = total
        stage_co2[s] = co2
    from_gases = 0.0
    for name in gases:
        from_gases += scn.gwp[name] * by_gas[name]
    by_stage = {s: stage_all[s] for s in STAGES if s in inc}
    co2_total = sum(stage_co2[s] for s in STAGES if s in inc)
    if "B6" in inc and "B2" not in inc:                 # nothing may fall between B2 and B6
        by_stage["B6"] = b6_03
        co2_total += stage_co2["B2"]

    # stage values from the unit values: a second accumulation, compared with the first (QA-01)
    unit_stage = {
        "A1-A3": val["A13-01"] + val["A13-03"] + val["A13-04"] + val["X-01"], "A4": val["A4-01"] + val["A4-02"],
        "A5": a5_04, "B1": b1_02 + b1_03 + b1_04, "B2": b2, "B3": val["B3-01"], "B4": val["B4-02"], "B5": b5,
        "B6": b6_03 - b2, "B7": b7_04, "C1": val["C1-01"], "C2": val["C2-01"], "C3": val["C3-01"] + val["X-14"],
        "C4": val["C4-01"],
    }
    qa01 = [f"stage {s}" for s in STAGES if not _within(unit_stage[s] - stage_all[s], 1e-9, max(abs(unit_stage[s]), 1.0))]

    # ---- indicators: linear functions of the stage vector ----
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

    sum_08 = None
    if _compare:
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
                b_total = baseline_totals.get(bid) if baseline_totals is not None else None
                if b_total is None:                     # the caller may keep and reuse it; nothing is kept here
                    b_total = finish(aggregate(base_scn, False), None, False, None, _compare=False)["SUM-03"]["value"]
                    if baseline_totals is not None:
                        baseline_totals[bid] = b_total
                sum_08 = {"status": "COMPARED", "baseline": b_total, "delta": wlc - b_total,
                          "saving": (b_total - wlc) / b_total if b_total > 0.0 else None}

    # ---- remaining checks ----
    qa03 = [fid for fid in sorted(used) if factors[fid].licence_status not in ALLOWED or not factors[fid].source_url]
    sq = scn.summary_quantities
    if _nonneg(sq.timber_m3) and _nonneg(sq.timber_dry_density_kg_per_m3) and _nonneg(sq.timber_carbon_fraction):
        sto_01 = sq.timber_m3 * sq.timber_dry_density_kg_per_m3 * sq.timber_carbon_fraction * (44.0 / 12.0)
    else:
        sto_01 = None
    x11 = None
    if area_ok and not math.isinf(area) and _nonneg(op.electricity_per_m2_per_year) and M["c_site"] is not None and M["grid_ok"]:
        x11 = area * op.electricity_per_m2_per_year * M["c_site"] * G
    x17, x17_total = {}, 0.0
    summary_q = {"REBAR": sq.reinforcement_kg, "STRUCTURAL_STEEL": sq.steel_kg, "CONCRETE": sq.concrete_m3,
                 "TIMBER": sq.timber_m3, "ENVELOPE": sq.envelope_m2, "INTERIOR": sq.interior_m2}
    for k in SIMPLE_CLASSES:
        qk = summary_q[k]
        fbar = tot(tables["CLASS:" + k]) / qk if qk else 0.0
        x17[k] = {"quantity": qk, "fbar": fbar, "emission": qk * fbar}
        x17_total += qk * fbar
    x09_emis, x09_total = {}, 0.0
    for cls, routes in M["x09_emis"].items():
        x09_emis[cls] = {r: tot(t) for r, t in routes.items()}
        x09_total += sum(x09_emis[cls].values())
    x03_mass, x03_emis, x03_total = {}, {}, 0.0
    for key, rec in A.recipes.items():
        if not rec["used"]:
            continue
        kg = rec["kg"]                                  # the rows of one composition are expanded once
        for fid, fraction, c in rec["parts"]:
            m = kg * fraction
            e = m * c * factors[fid].value
            x03_mass[fid] = x03_mass.get(fid, 0.0) + m
            x03_emis[fid] = x03_emis.get(fid, 0.0) + e
            x03_total += e
    by_cycle = {}
    x08_total = tot(explicit_b4)
    explicit_total = x08_total
    group_u = {}
    for cycle in sorted((c for c in A.groups if c is not None and counts[c]), key=float):
        u = group_u[cycle] = tot(A.groups[cycle].u)
        e = counts[cycle] * u
        by_cycle[repr(float(cycle))] = {"count": counts[cycle], "unit_emission": u, "emission": e}
        x08_total += e
    skip = M["skip"]

    R = dict(A.out)
    R.update({
        "X-13": {},
        "A13-01": {"value": val["A13-01"], "n_skipped": skip["A13-01"]},
        "A13-03": {"value": val["A13-03"], "n_skipped": skip["A13-03"]},
        "A13-04": {"value": val["A13-04"], "n_skipped": skip["A13-04"]},
        "X-01": {"value": val["X-01"], "n_skipped": skip["X-01"]},
        "X-03": {"value": x03_total, "mass_by_component": x03_mass, "emission_by_component": x03_emis},
        "A4-01": {"value": val["A4-01"], "n_skipped": skip["A4-01"]},
        "X-12": {"value": val["X-12"], "n_skipped": skip["X-12"]},
        "A4-02": {"value": val["A4-02"], "n_skipped": skip["A4-02"]},
        "A5-01": {"value": val["A5-01"], "computed": M["a5_01_ok"]},
        "A5-02": {"value": val["A5-02"], "n_skipped": M["a5_02_skip"]},
        "A5-03": {"value": val["A5-03"], "n_skipped": M["a5_03_skip"]},
        "A5-04": {"value": a5_04, "parts": {"power": val["A5-01"], "fuels": val["A5-02"], "waste": val["A5-03"]},
                  "other_assessed": False},
        "X-17": {"value": x17_total, "by_class": x17},
        "X-16": {"value": val["X-16"], "n_skipped": M["x16_skip"]},
        "B4-01": {"n_events": n_events},
        "B4-03": {},
        "B4-02": {"value": val["B4-02"], "n_partial": n_partial},
        "X-08": {"value": x08_total, "by_cycle": by_cycle, "explicit": explicit_total},
        "B3-01": {"value": val["B3-01"], "n_skipped": skip["B3"]},
        "B3-02": {"value": val["B3-02"], "n_skipped": skip["B3"]},
        "B1-01": {"value": M["b1_01"], "n_skipped": M["b1_01_skip"]},
        "B1-02": {"value": b1_02, "n_skipped": b1_skip[0]},
        "B1-03": {"value": b1_03, "n_skipped": b1_skip[1]},
        "B1-04": {"value": b1_04, "n_skipped": b1_skip[2]},
        "B5-01": {"value": b5, "n_events": b5_n, "computed": b5_computed},
        "X-06": {"matches_table": grid_matches, "source": "DESCRIPTOR" if segments is not None else "TABLE"},
        "B6-04": {"computed": net_ok, "descriptors_match_tables": net_match},
        "B6-01": {"computed": elec_ok},
        "B6-02": {"n_skipped": annual_skip["B6-02"], "descriptors_match_tables": annual_match["B6-02"]},
        "B6-03": {"value": b6_03},
        "B2-01": {"value": b2, "computed": b2_ok},
        "X-11": {"value": x11},
        "B7-01": {"n_skipped": annual_skip["B7-01"], "descriptors_match_tables": annual_match["B7-01"]},
        "B7-02": {"n_skipped": annual_skip["B7-02"], "descriptors_match_tables": annual_match["B7-02"]},
        "B7-03": {"n_skipped": annual_skip["B7-03"], "descriptors_match_tables": annual_match["B7-03"]},
        "B7-04": {"value": b7_04},
        "C1-01": {"value": val["C1-01"], "n_skipped": M["c1_skip"]},
        "C2-01": {"value": val["C2-01"], "n_skipped": skip["C2-01"]},
        "C3-01": {"value": val["C3-01"], "n_skipped": skip["C3-01"], "n_routes_skipped": M["routes_skipped"]["C3"]},
        "C4-01": {"value": val["C4-01"], "n_skipped": skip["C4-01"], "n_routes_skipped": M["routes_skipped"]["C4"]},
        "X-14": {"value": val["X-14"], "n_skipped": skip["X-14"]},
        "X-09": {"value": x09_total, "mass": M["x09_mass"], "emission": x09_emis},
        "X-10": {"resource_kg": resource, "waste_kg": waste, "n_excluded": skip["X-10"]},
        "STO-01": {"value": sto_01},
        "STO-02": {"value": tot(tables["STO-02"]) if M["sto_02_ok"] else None},
        "X-04": {"value": from_gases + grid_total + refrigerant_total, "by_gas": by_gas, "co2e_from_gases": from_gases,
                 "grid_co2e": grid_total, "refrigerant_co2e": refrigerant_total, "by_stage_recomputed": unit_stage},
        "X-05": {"value": co2_total, "by_stage_co2": stage_co2},
        "X-07": {"value": wlc},
        "SUM-04": {"value": wlc / area if area_ok else None},
        "SUM-05": {"value": wlc / (area * T) if area_ok and T > 0.0 else None},
        "SUM-06": {"value": wlc / 1000.0},
        "SUM-07": sum_07,
        "QA-01": {"ok": not qa01, "violations": qa01},
        "QA-02": {"ok": not qa02, "violations": qa02, "warnings": qa02_warn},
        "QA-03": {"ok": not qa03, "violations": qa03, "n_used": len(used)},
    })
    if sum_08 is not None:
        R["SUM-08"] = sum_08
    incomplete = []
    for s in STAGES:
        if s in inc:
            for uid in STAGE_UNITS[s]:
                r = R[uid]
                if (r.get("n_skipped") or r.get("n_routes_skipped") or r.get("n_partial") or r.get("computed") is False) \
                        and uid not in incomplete:
                    incomplete.append(uid)
    complete = not incomplete
    R["X-02"] = {"by_stage": by_stage, "by_stage_all": stage_all, "complete": complete, "incomplete_units": sorted(incomplete)}
    R["SUM-01"] = {"value": upfront, "complete": complete}
    R["SUM-02"] = {"value": embodied, "complete": complete}
    R["SUM-03"] = {"value": wlc, "complete": complete}
    R["_stats"] = stats
    R["_tables"] = tables
    R["_n_events_check"] = n_events
    if not detail:
        del R["_n_events_check"]
    if detail:
        _detail(A, R, T, Y, wl, counts, group_u, explicit_events, b1_items, b1_year, b1_event_year, g_values,
                net_series, elec_series, annual_parts, b5_n, b5_base, b2_ok, stage_all, b1_04)
    return R


def _detail(A, R, T, Y, wl, counts, group_u, explicit_events, b1_items, b1_year, b1_event_year, g_values,
            net_series, elec_series, annual_parts, b5_n, b5_base, b2_ok, stage_all, b1_04):
    """Per-row lists and yearly series (the same outputs as the reference; not needed for the totals)."""
    scn = A.scn
    L = A.rows
    fval = A.fval
    stats = R["_stats"]
    inc = set(scn.boundary.included_lifecycle_stages)
    bnd = scn.boundary
    R["A13-05"] = dict(R["A13-05"], q_ord=L["q_ord"], q_inst=L["q_inst"])
    R["X-13"] = {"by_item": L["net"], "waste_by_item": L["disp"]}
    R["A13-02"] = dict(R["A13-02"], by_item=L["a1302"])
    R["X-15"] = dict(R["X-15"], kind=L["kind"], factor=L["factor"], conv=L["conv"])
    for uid, key in (("A13-01", "a1301"), ("A13-03", "a1303"), ("A13-04", "a1304"), ("X-01", "x01"), ("A4-01", "a401"),
                     ("A4-02", "a402"), ("X-12", "x12"), ("C2-01", "c2"), ("C3-01", "c3"), ("C4-01", "c4"), ("X-14", "x14")):
        R[uid]["by_item"] = L[key]
    R["X-16"]["by_item"] = [it[1] * fval[it[0]] if it is not None else 0.0 for it in A.misc["x16_items"]]
    n_mat = [counts[c] for c in L["mcycle"]]
    R["B4-03"] = {"by_item": n_mat}
    events_all = []
    n_events = 0
    for j, eq in enumerate(scn.equipment):
        if L["eexp"][j]:
            ev = explicit_events[j]
        else:
            stats["event_lists_built"] += 1
            ev = [k * eq.service_life for k in range(1, counts[L["ecycle"][j]] + 1)]
        events_all.append(ev)
        n_events += len(ev)
    R["B4-01"] = {"events": events_all, "n_events": n_events}
    assert n_events == R["_n_events_check"]
    del R["_n_events_check"]
    R["B1-02"]["by_item"] = b1_items

    w = [0.0] + [1.0] * (Y - 1) + ([wl] if Y else [])
    b4_year = [0.0] * (Y + 1)
    b3_year = [0.0] * (Y + 1)
    for cycle, grp in A.groups.items():
        n = counts[cycle]
        skip_years = set()
        if n:
            u = group_u[cycle] if cycle in group_u else sum(act * fval[key] for key, act in grp.u.items())
            for k in range(1, n + 1):
                y = cf.event_year(k * cycle)
                b4_year[y] += u
                skip_years.add(y)
        if grp.r:
            rate = sum(act * fval[key] for key, act in grp.r.items())
            for y in range(1, Y + 1):               # added year by year, never by subtraction
                if y not in skip_years:
                    b3_year[y] += rate * w[y]
    for j, years, lines, rline, emass, incomplete in A.explicit:
        events = explicit_events[j]
        u = sum(act * fval[key] for key, act in lines)
        skip_years = set()
        for t in events:
            y = cf.event_year(t)
            b4_year[y] += u
            skip_years.add(y)
        if rline is not None:
            rate = rline[1] * fval[rline[0]]
            for y in range(1, Y + 1):
                if y not in skip_years:
                    b3_year[y] += rate * w[y]
    b5_year = [0.0] * (Y + 1)
    for k in range(1, b5_n + 1):
        b5_year[cf.event_year(k * bnd.replacement_cycle)] += bnd.reconstruction_scope_fraction * b5_base
    R["X-06"]["by_year"] = [0.0] + list(g_values)
    R["B6-04"]["by_year"] = net_series
    R["B6-01"]["by_year"] = elec_series
    series = {}
    for name, parts in annual_parts.items():
        out = [0.0] * (Y + 1)
        for profile, hit in parts:
            values = _values(profile, Y)
            value = fval[hit[0]]
            for k in range(Y):
                out[k + 1] += values[k] * hit[1] * value
        series[name] = out
        R[name]["by_year"] = out
    R["B4-02"].update(by_item_material=[n * u for n, u in zip(n_mat, L["mu"])],
                      by_item_equipment=[len(ev) * u for ev, u in zip(events_all, L["eu"])], by_year=b4_year)
    R["B3-01"]["by_year"] = b3_year
    R["B1-02"]["by_year"] = b1_year
    R["B1-03"]["by_year"] = b1_event_year
    R["B5-01"]["by_year"] = b5_year

    out = [0.0] * (Y + 1)
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


def evaluate(scn, detail: bool = True, baseline_totals: dict | None = None) -> dict:
    """All results of one scenario. ``baseline_totals`` is an optional dict the caller keeps to reuse baseline totals."""
    T = check_period(scn)
    return finish(aggregate(scn, detail), T, detail, baseline_totals)


def sweep(scn, periods) -> dict:
    """Totals for several study periods from ONE pass over the rows."""
    check_period(scn)
    A = aggregate(scn, False)
    out = {}
    for T in periods:
        if not (T > 0.0) or math.isinf(T) or len(scn.operation.grid.table) < math.ceil(T):
            raise ValueError("invalid study period")
        out[T] = finish(A, T, False, None, _compare=False)
    return out
