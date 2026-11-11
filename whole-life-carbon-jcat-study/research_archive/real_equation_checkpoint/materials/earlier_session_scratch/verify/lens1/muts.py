"""Mutation catalogue: each entry is (name, fn(scn, rng) -> bool applied)."""
from __future__ import annotations

import copy
import math

from synth import model, population

MUTS = []


def mut(name):
    def deco(fn):
        MUTS.append((name, fn))
        return fn
    return deco


def rows_of(scn, group):
    return {"mat": scn.materials, "eq": scn.equipment, "dev": scn.refrigerants}[group]


def targets(lst, r, scope):
    if not lst:
        return []
    if scope == "all":
        return list(lst)
    if scope == "half":
        return list(lst[::2])
    return [r.choice(lst)]


def getpath(obj, path):
    for p in path[:-1]:
        obj = getattr(obj, p)
    return obj, path[-1]


def add_field_muts(group, path, values, scopes=("one", "all")):
    label = ".".join(path)
    for vname, val in values:
        for scope in scopes:
            def fn(scn, r, val=val, scope=scope):
                T = scn.boundary.study_period
                t = targets(rows_of(scn, group), r, scope)
                if not t:
                    return False
                for row in t:
                    o, leaf = getpath(row, path)
                    setattr(o, leaf, val(T) if callable(val) else val)
                return True
            MUTS.append((f"{group}.{label}={vname}/{scope}", fn))


GEN = [("None", None), ("0", 0.0), ("int0", 0), ("neg", -3.7), ("tiny", 1e-12), ("huge", 1e12), ("one", 1.0)]
CYC = GEN + [("T", lambda T: T), ("T/2", lambda T: T / 2), ("T/3", lambda T: T / 3), ("0.3", 0.3), ("0.5", 0.5),
             ("0.999999999", 0.999999999), ("T-ulp", lambda T: math.nextafter(T, 0)), ("T+ulp", lambda T: math.nextafter(T, 1e9)),
             ("int10", 10), ("int1", 1), ("T/7", lambda T: T / 7), ("1.1", 1.1), ("0.1", lambda T: 0.1 if T <= 150 else 1.3)]
CYC = [(n, v) for n, v in CYC if n not in ("tiny",)]
RATE = GEN + [("0.5", 0.5), ("1e-9", 1e-9), ("0.999999", 0.999999), ("1.5", 1.5), ("1e-6", 1e-6), ("1e-4", 1e-4)]

for f in ("quantity", "reuse_rate", "material_life"):
    add_field_muts("mat", (f,), GEN)
add_field_muts("mat", ("waste_rate",), GEN + [("0.999999", 0.999999), ("0.5", 0.5), ("-0.1", -0.1)])
add_field_muts("mat", ("repair_rate",), RATE)
add_field_muts("mat", ("refresh_cycle",), CYC)
add_field_muts("mat", ("unquantified_cost_ratio",), GEN + [("0.5", 0.5), ("0.999", 0.999)])
add_field_muts("mat", ("transport", "mass_t"), GEN)
add_field_muts("mat", ("transport", "distance_km"), GEN)
add_field_muts("mat", ("transport", "load_factor"), [("None", None), ("0", 0.0), ("neg", -0.5), ("1e-9", 1e-9), ("2", 2.0)])
add_field_muts("mat", ("end_of_life", "mass_kg"), GEN)
add_field_muts("mat", ("end_of_life", "haul_distance_km"), [("0", 0.0), ("neg", -5.0), ("huge", 1e9)])
add_field_muts("mat", ("quantity_unit",), [("furlong", "furlong"), ("kg", "kg"), ("t", "t"), ("m2", "m2"), ("m3", "m3")])
add_field_muts("mat", ("quantity_basis",), [("DESIGN", "DESIGN"), ("ORDERED", "ORDERED"), ("AS_BUILT", "AS_BUILT")], scopes=("all",))
add_field_muts("mat", ("factor_id",), [("None", None), ("dangling", "F-NO-SUCH")])
add_field_muts("mat", ("transport", "factor_id"), [("None", None), ("dangling", "F-NO-SUCH")])
add_field_muts("mat", ("transport", "delivery_factor_id"), [("None", None), ("dangling", "F-NO-SUCH")])
add_field_muts("mat", ("end_of_life", "haul_factor_id"), [("None", None), ("dangling", "F-NO-SUCH")])
add_field_muts("mat", ("installation_factor_id",), [("None", None), ("dangling", "F-NO-SUCH")])
add_field_muts("mat", ("material_class",), [("REBAR", "REBAR"), ("TIMBER", "TIMBER"), ("OTHERX", "ZZZ")], scopes=("one", "half"))
add_field_muts("mat", ("construction_division",), [("INTERIOR", "INTERIOR"), ("OPENINGS", "OPENINGS")], scopes=("half",))
add_field_muts("mat", ("provenance_id",), [("dangling", "PRV-NOPE"), ("empty", "")], scopes=("one", "all"))
add_field_muts("mat", ("composition",), [("None", None), ("empty", lambda T: [])], scopes=("one", "all"))
add_field_muts("mat", ("epd",), [("None", None)], scopes=("all",))
add_field_muts("mat", ("conversions",), [("empty", lambda T: [])], scopes=("one", "all"))

for f in ("quantity", "end_of_life_mass_kg"):
    add_field_muts("eq", (f,), GEN)
add_field_muts("eq", ("service_life",), CYC)
add_field_muts("eq", ("repair_rate",), RATE)
add_field_muts("eq", ("quantity_unit",), [("furlong", "furlong"), ("kg", "kg")])
for f in ("factor_id", "eol_factor_id", "delivery_factor_id", "installation_factor_id"):
    add_field_muts("eq", (f,), [("None", None), ("dangling", "F-NO-SUCH")])
EVL = [("None", None), ("empty", lambda T: []), ("[T]", lambda T: [T]), ("[0]", lambda T: [0]), ("[-5]", lambda T: [-5]),
       ("dups", lambda T: [min(1, T / 2), min(1, T / 2), T / 2, T / 2]), ("unsorted", lambda T: [T * 0.9, T * 0.1, T * 0.5, T * 0.3]),
       ("nonint", lambda T: [T * 0.123, T * 0.517, 0.2 if T > 0.2 else T / 3]), ("[T-ulp]", lambda T: [math.nextafter(T, 0)]),
       ("[ulp]", lambda T: [5e-324, 1e-9]), ("sameyear", lambda T: [T * 0.5, T * 0.5 + min(0.01, T * 0.01), T * 0.5 + min(0.02, T * 0.02)]),
       ("lastyear", lambda T: [math.ceil(T) - 0.5] if math.ceil(T) - 0.5 < T else [T * 0.999]),
       ("ints", lambda T: [k for k in range(1, min(40, math.ceil(T)))]), ("mix_outside", lambda T: [T + 5, -1, T / 2, 0, T]),
       ("intfloatmix", lambda T: [1, 1.0, 2] if T > 2 else [T / 2, T / 2])]
add_field_muts("eq", ("replacement_event_list",), EVL)

add_field_muts("dev", ("charge_mass_kg",), GEN)
add_field_muts("dev", ("gwp",), GEN)
add_field_muts("dev", ("annual_leak_rate",), RATE + [("1e-12", 1e-12), ("1-1e-12", 1 - 1e-12), ("0.3", 0.3)])
add_field_muts("dev", ("replacement_loss_rate",), [("None", None), ("0", 0.0), ("1", 1.0), ("neg", -0.2), ("2", 2.0)])
add_field_muts("dev", ("end_of_life_recovery_rate",), [("None", None), ("0", 0.0), ("1", 1.0), ("neg", -0.2), ("2", 2.0)])
add_field_muts("dev", ("change_years",), EVL)
add_field_muts("dev", ("service_life",), CYC)
add_field_muts("dev", ("top_up",), [("True", True), ("False", False), ("None", None), ("int1", 1), ("int0", 0)], scopes=("all", "half"))


# ---------- structured mutations ----------
def usable_ids(scn, unit=None, stages=None):
    out = []
    for fid, rec in scn.factors.items():
        if rec.licence_status not in model.ALLOWED_LICENCE_STATES:
            continue
        if unit is not None and rec.unit != unit:
            continue
        if stages is not None and rec.stages != stages:
            continue
        out.append(fid)
    return sorted(out)


@mut("dev.both_None_life_and_list/all")
def _(scn, r):
    for d in scn.refrigerants:
        d.service_life = None
        d.change_years = None
    return bool(scn.refrigerants)


@mut("dev.leak_extremes_mix")
def _(scn, r):
    for i, d in enumerate(scn.refrigerants):
        d.annual_leak_rate = (0.0, 1.0, 1e-9, 0.5)[i % 4]
        d.top_up = bool((i // 4) % 2)
    return bool(scn.refrigerants)


@mut("eq.both_None_life_and_list/all")
def _(scn, r):
    for e in scn.equipment:
        e.service_life = None
        e.replacement_event_list = None
    return bool(scn.equipment)


@mut("mat.routes=empty/one")
def _(scn, r):
    if not scn.materials:
        return False
    r.choice(scn.materials).end_of_life.routes = []
    return True


@mut("mat.routes.fraction=neg/one")
def _(scn, r):
    rows = [m for m in scn.materials if m.end_of_life.routes]
    if not rows:
        return False
    r.choice(r.choice(rows).end_of_life.routes).fraction = -0.25
    return True


@mut("mat.routes.fraction=boundary(1+1e-6)/all")
def _(scn, r):
    ok = False
    for m in scn.materials:
        rs = m.end_of_life.routes
        if rs:
            s = sum(x.fraction for x in rs[1:])
            rs[0].fraction = r.choice((1.0 + 1e-6 - s, 1.0 - 1e-6 - s, 1.0 + 1.0000001e-6 - s, 1.0 - 1.0000001e-6 - s))
            ok = True
    return ok


@mut("mat.routes.fraction=all_landfill/all")
def _(scn, r):
    for m in scn.materials:
        for x in m.end_of_life.routes:
            x.fraction = 1.0 if x.route == "LANDFILL" else 0.0
    return bool(scn.materials)


@mut("mat.routes.factor_id=None/one")
def _(scn, r):
    rows = [m for m in scn.materials if m.end_of_life.routes]
    if not rows:
        return False
    r.choice(r.choice(rows).end_of_life.routes).factor_id = None
    return True


@mut("mat.routes.factor_id=dangling/one")
def _(scn, r):
    rows = [m for m in scn.materials if m.end_of_life.routes]
    if not rows:
        return False
    r.choice(r.choice(rows).end_of_life.routes).factor_id = "F-NO-SUCH"
    return True


@mut("mat.routes.duplicate_route/one")
def _(scn, r):
    rows = [m for m in scn.materials if m.end_of_life.routes]
    if not rows:
        return False
    m = r.choice(rows)
    m.end_of_life.routes.append(copy.deepcopy(r.choice(m.end_of_life.routes)))
    return True


@mut("mat.delivery_factor=valid_factor/half")
def _(scn, r):
    ok = False
    for m in scn.materials[::2]:
        ids = usable_ids(scn, unit=m.quantity_unit)
        if ids:
            m.transport.delivery_factor_id = r.choice(ids)
            ok = True
    return ok


@mut("mat.delivery_factor=any_factor/half")
def _(scn, r):
    ids = sorted(scn.factors)
    for m in scn.materials[::2]:
        m.transport.delivery_factor_id = r.choice(ids)
    return bool(scn.materials)


@mut("mat.installation_factor=any_factor/all")
def _(scn, r):
    ids = sorted(scn.factors)
    for m in scn.materials:
        m.installation_factor_id = r.choice(ids)
    return bool(scn.materials)


@mut("mat.factor_id=any_factor/half")
def _(scn, r):
    ids = sorted(scn.factors)
    for m in scn.materials[::2]:
        m.factor_id = r.choice(ids)
    return bool(scn.materials)


@mut("mat.epd=any_factor/half")
def _(scn, r):
    ids = sorted(scn.factors)
    for m in scn.materials[::2]:
        fid = r.choice(ids)
        m.epd = model.EpdReference(fid, ["A1-A3"], scn.factors[fid].unit, "2999-01-01")
    return bool(scn.materials)


@mut("mat.epd.factor_id=None|dangling/all")
def _(scn, r):
    ok = False
    for m in scn.materials:
        if m.epd is not None:
            m.epd.factor_id = r.choice((None, "F-NO-SUCH"))
            ok = True
    return ok


@mut("mat.epd_on_composite/all")
def _(scn, r):
    ids = usable_ids(scn, stages=["A1-A3"])
    ok = False
    for m in scn.materials:
        if m.composition is not None and ids:
            fid = r.choice(ids)
            m.epd = model.EpdReference(fid, ["A1-A3"], scn.factors[fid].unit, "2999-01-01")
            ok = True
    return ok


@mut("factors.valid_until=expired|None|equal")
def _(scn, r):
    ok = False
    for m in scn.materials:
        if m.epd is not None and m.epd.factor_id in scn.factors:
            scn.factors[m.epd.factor_id].valid_until = r.choice((None, "1900-01-01", scn.project.assessment_date, "9999-12-31"))
            ok = True
    return ok


@mut("project.assessment_date=late|early")
def _(scn, r):
    scn.project.assessment_date = r.choice(("9999-01-01", "0001-01-01"))
    return True


@mut("mat.composition.fraction_boundary/all")
def _(scn, r):
    ok = False
    for m in scn.materials:
        if m.composition:
            s = sum(c.mass_fraction for c in m.composition[1:])
            m.composition[0].mass_fraction = r.choice((1.0 + 1e-6 - s, 1.0 - 1e-6 - s, 1.0 + 1.01e-6 - s, 1.0 - 1.01e-6 - s, 1.0 - s))
            ok = True
    return ok


@mut("mat.composition.same_spec_different_content")
def _(scn, r):
    comps = [m for m in scn.materials if m.composition]
    if len(comps) < 2:
        return False
    a = comps[0]
    for b in comps[1:]:
        b.specification = a.specification
        b.composition = copy.deepcopy(a.composition)
        j = r.randrange(len(b.composition))
        v = r.choice(("fraction", "factor", "order", "identical", "extra"))
        if v == "fraction" and len(b.composition) >= 2:
            d = b.composition[j].mass_fraction * 0.5
            b.composition[j].mass_fraction -= d
            b.composition[(j + 1) % len(b.composition)].mass_fraction += d
        elif v == "factor":
            ids = usable_ids(scn, unit="kg", stages=["A1-A3"])
            if ids:
                b.composition[j].factor_id = r.choice(ids)
        elif v == "order":
            b.composition.reverse()
        elif v == "extra":
            b.composition.append(model.CompositeComponent(b.composition[0].factor_id, 0.0))
    return True


@mut("mat.composition.component=None|dangling|unlicensed|wrongunit/one")
def _(scn, r):
    comps = [m for m in scn.materials if m.composition]
    if not comps:
        return False
    m = r.choice(comps)
    c = r.choice(m.composition)
    v = r.choice(("None", "dangling", "unlicensed", "wrongunit", "wrongstage"))
    if v == "None":
        c.factor_id = None
    elif v == "dangling":
        c.factor_id = "F-NO-SUCH"
    elif v == "unlicensed":
        scn.factors[c.factor_id].licence_status = "RESTRICTED"
    elif v == "wrongunit":
        scn.factors[c.factor_id].unit = "m3"
    else:
        scn.factors[c.factor_id].stages = ["A1-A3", "A4"]
    return True


@mut("mat.composition.repeat_component/all")
def _(scn, r):
    ok = False
    for m in scn.materials:
        if m.composition:
            c = m.composition[0]
            half = c.mass_fraction / 2
            c.mass_fraction = half
            m.composition.append(model.CompositeComponent(c.factor_id, half))
            ok = True
    return ok


@mut("mat.composition_and_factor_dangling/all")
def _(scn, r):
    ok = False
    for m in scn.materials:
        if m.composition is not None:
            m.factor_id = r.choice((None, "F-NO-SUCH", m.factor_id))
            ok = True
    return ok


@mut("mat.make_composite_from_generic/half")
def _(scn, r):
    ids = usable_ids(scn, unit="kg", stages=["A1-A3"])
    if len(ids) < 2:
        return False
    for m in scn.materials[::2]:
        a, b = r.sample(ids, 2)
        m.composition = [model.CompositeComponent(a, 0.25), model.CompositeComponent(b, 0.75)]
    return bool(scn.materials)


@mut("mat.row_conversion_override/all")
def _(scn, r):
    for m in scn.materials:
        m.conversions = [model.UnitConversion(m.quantity_unit, "kg", r.choice((0.5, 2.0, 1000.0)), "TEST"),
                         model.UnitConversion(m.quantity_unit, "kg", 7.0, "TEST second entry")]
    return bool(scn.materials)


@mut("mat.states=DERIVED|MISSING|ESTIMATE|OBSERVED/all")
def _(scn, r):
    for m in scn.materials:
        for name in ("quantity", "waste_rate", "transport.mass_t", "end_of_life.mass_kg", "refresh_cycle"):
            if r.random() < 0.5:
                m.states[name] = r.choice(("DERIVED", "MISSING", "ESTIMATE", "OBSERVED", "EXPLICIT_ZERO"))
    return bool(scn.materials)


@mut("provenance=empty")
def _(scn, r):
    scn.provenance = {}
    return True


@mut("unit_conversions=empty")
def _(scn, r):
    scn.unit_conversions = []
    return True


@mut("unit_conversions=conflicting_duplicate_first")
def _(scn, r):
    scn.unit_conversions = [model.UnitConversion(c.from_unit, c.to_unit, c.factor * 3.0, "TEST") for c in scn.unit_conversions[:6]] + scn.unit_conversions
    return True


@mut("unit_conversions+row_overrides_shadowing_table")
def _(scn, r):
    ok = False
    for m in scn.materials:
        if m.quantity_unit in ("t", "kg", "m3", "L"):
            m.conversions = [model.UnitConversion("t", "kg", 999.0, "TEST"), model.UnitConversion("kg", "t", 0.002, "TEST")] + list(m.conversions)
            ok = True
    return ok


# ---- factors ----
@mut("factors.licence=random_bad/some")
def _(scn, r):
    for fid in r.sample(sorted(scn.factors), max(1, len(scn.factors) // 6)):
        scn.factors[fid].licence_status = r.choice(("UNKNOWN", "RESTRICTED", "PERMISSION_REQUIRED", "BOGUS"))
    return True


@mut("factors.licence=bad/all")
def _(scn, r):
    for rec in scn.factors.values():
        rec.licence_status = "UNKNOWN"
    return True


@mut("factors.source_url=empty/some")
def _(scn, r):
    for fid in r.sample(sorted(scn.factors), max(1, len(scn.factors) // 6)):
        scn.factors[fid].source_url = ""
    return True


@mut("factors.value=0|neg|huge/some")
def _(scn, r):
    for fid in r.sample(sorted(scn.factors), max(1, len(scn.factors) // 6)):
        scn.factors[fid].value = r.choice((0.0, -1.0, 1e9, 1e-12))
    return True


@mut("factors.stages=changed/some")
def _(scn, r):
    for fid in r.sample(sorted(scn.factors), max(1, len(scn.factors) // 6)):
        scn.factors[fid].stages = r.choice((["A1-A3", "A4"], [], ["A4"], ["A1-A3"], ["MEMO"]))
    return True


@mut("factors.unit=changed/some")
def _(scn, r):
    for fid in r.sample(sorted(scn.factors), max(1, len(scn.factors) // 6)):
        scn.factors[fid].unit = r.choice(("kg", "t", "m3", "furlong", "L", "MJ", "kWh", "unit", "tkm"))
    return True


@mut("factors.gas_amounts=inconsistent/some")
def _(scn, r):
    for fid in r.sample(sorted(scn.factors), max(1, len(scn.factors) // 6)):
        g = scn.factors[fid].gas_amounts
        k = r.choice(sorted(g))
        g[k] = r.choice((0.0, -1.0, g[k] * 2 + 1.0))
    return True


@mut("factors.release_year=changed/one")
def _(scn, r):
    scn.factors[r.choice(sorted(scn.factors))].release_year += 3
    return True


@mut("factors.delete_random/one")
def _(scn, r):
    del scn.factors[r.choice(sorted(scn.factors))]
    return True


@mut("gwp=zero|neg|changed")
def _(scn, r):
    for g in scn.gwp:
        scn.gwp[g] = r.choice((0.0, 1.0, -1.0, scn.gwp[g] * 2))
    return True


@mut("gases=reordered|subset")
def _(scn, r):
    g = list(scn.gases)
    r.shuffle(g)
    scn.gases = g[: r.choice((len(g), len(g), 3, 1, 0))]
    return True


# ---- construction ----
@mut("construction.electricity_kwh=None|0|neg")
def _(scn, r):
    scn.construction.electricity_kwh = r.choice((None, 0.0, -100.0))
    return True


@mut("construction.fuels.quantity|unit|factor")
def _(scn, r):
    if not scn.construction.fuels:
        return False
    f = r.choice(scn.construction.fuels)
    v = r.choice(("qNone", "q0", "unit", "fNone", "fdang", "conv", "noconv"))
    if v == "qNone":
        f.quantity = None
    elif v == "q0":
        f.quantity = 0.0
    elif v == "unit":
        f.unit = "furlong"
    elif v == "fNone":
        f.factor_id = None
    elif v == "fdang":
        f.factor_id = "F-NO-SUCH"
    elif v == "conv":
        f.conversions = [model.UnitConversion(f.unit, scn.factors[f.factor_id].unit, 42.0, "TEST")] if f.factor_id in scn.factors else []
    else:
        f.conversions = []
    return True


@mut("construction.lists=empty")
def _(scn, r):
    scn.construction.fuels = []
    scn.construction.waste_streams = []
    return True


@mut("construction.waste.mass|factor")
def _(scn, r):
    if not scn.construction.waste_streams:
        return False
    w = r.choice(scn.construction.waste_streams)
    v = r.choice(("mNone", "m0", "mneg", "fNone", "fdang"))
    if v == "mNone":
        w.mass_kg = None
    elif v == "m0":
        w.mass_kg = 0.0
    elif v == "mneg":
        w.mass_kg = -5.0
    elif v == "fNone":
        w.factor_id = None
    else:
        w.factor_id = "F-NO-SUCH"
    return True


# ---- operation ----
def all_profiles(scn):
    return [p for _, p in model.annual_profiles(scn)]


@mut("grid.licence=bad")
def _(scn, r):
    scn.operation.grid.licence_status = r.choice(("UNKNOWN", "RESTRICTED"))
    return True


@mut("grid.construction_value=0|neg")
def _(scn, r):
    scn.operation.grid.construction_value = r.choice((0.0, -0.3))
    return True


@mut("grid.table!=descriptor(one entry)")
def _(scn, r):
    g = scn.operation.grid
    Y = math.ceil(scn.boundary.study_period)
    k = r.randrange(Y)
    g.table[k] = g.table[k] * 1.5 + 0.01
    return True


@mut("grid.table!=descriptor(rel 1e-12 boundary)")
def _(scn, r):
    g = scn.operation.grid
    Y = math.ceil(scn.boundary.study_period)
    k = r.randrange(Y)
    g.table[k] = g.table[k] * (1 + r.choice((5e-13, 2e-12, -5e-13, -2e-12)))
    return True


@mut("grid.steps=unsorted")
def _(scn, r):
    g = scn.operation.grid
    if g.kind != "STEPWISE" or len(g.steps) < 2:
        return False
    g.steps = list(reversed(g.steps))
    return True


@mut("grid.steps=duplicate_from_index")
def _(scn, r):
    g = scn.operation.grid
    if g.kind != "STEPWISE" or len(g.steps) < 2:
        return False
    g.steps.insert(1, model.GridStep(g.steps[1].from_index, g.steps[1].value * 2))
    g.steps.append(model.GridStep(g.steps[0].from_index, 0.123))
    return True


@mut("grid.steps=first_from_index>0")
def _(scn, r):
    g = scn.operation.grid
    if g.kind != "STEPWISE":
        return False
    g.steps[0].from_index = 2
    return True


@mut("grid.steps=negative_and_beyond")
def _(scn, r):
    g = scn.operation.grid
    if g.kind != "STEPWISE":
        return False
    g.steps = [model.GridStep(-3, 0.9), model.GridStep(0, 0.5)] + g.steps[1:] + [model.GridStep(10 ** 6, 0.1)]
    return True


@mut("grid.to_stepwise_sorted")
def _(scn, r):
    g = scn.operation.grid
    Y = math.ceil(scn.boundary.study_period)
    idx = sorted({0} | {r.randrange(0, Y + 3) for _ in range(r.randint(0, 6))})
    g.kind, g.start, g.annual_decline, g.floor = "STEPWISE", None, None, None
    g.steps = [model.GridStep(i, round(r.uniform(0.05, 0.8), 4)) for i in idx]
    tb = []
    for k in range(len(g.table)):
        v = None
        for s in g.steps:
            if s.from_index <= k:
                v = s.value
        tb.append(v)
    g.table = tb
    return True


@mut("grid.to_linear(params)")
def _(scn, r):
    g = scn.operation.grid
    T = scn.boundary.study_period
    Y = math.ceil(T)
    g.kind, g.steps = "LINEAR_DECLINE_TO_FLOOR", None
    g.start = r.choice((0.5, 0.3, 1.0))
    v = r.choice(("floor_at_k", "never", "immediately", "zero_decline", "floor_eq_start", "exact_hit", "last_year", "neg_decline", "start_below_floor", "neg_decline_below_floor"))
    if v == "floor_at_k":
        g.floor = 0.1
        g.annual_decline = (g.start - g.floor) / r.uniform(0.5, max(1.0, Y + 2))
    elif v == "never":
        g.floor = 0.0
        g.annual_decline = g.start / (Y * 3.0)
    elif v == "immediately":
        g.floor = g.start * 0.99
        g.annual_decline = 1.0
    elif v == "zero_decline":
        g.floor, g.annual_decline = 0.1, 0.0
    elif v == "floor_eq_start":
        g.floor, g.annual_decline = g.start, 0.01
    elif v == "exact_hit":
        k = r.randint(1, max(1, Y))
        g.floor = 0.125
        g.start = 0.5
        g.annual_decline = 0.375 / k
    elif v == "last_year":
        g.floor = 0.1
        g.annual_decline = (g.start - g.floor) / r.choice((Y - 1 or 1, Y, Y - 0.5, Y + 0.5))
    elif v == "neg_decline":
        g.floor, g.annual_decline = 0.1, -0.01
    elif v == "start_below_floor":
        g.floor, g.annual_decline = g.start + 0.2, 0.01
    else:
        g.floor, g.annual_decline = g.start + 0.2, -0.01
    g.table = [max(g.floor, g.start - g.annual_decline * k) for k in range(len(g.table))]
    return True


@mut("grid.to_constant")
def _(scn, r):
    g = scn.operation.grid
    g.kind, g.steps, g.annual_decline, g.floor = "CONSTANT", None, None, None
    g.start = r.choice((0.0, 0.4, -0.1))
    g.table = [g.start] * len(g.table)
    return True


@mut("grid.to_table")
def _(scn, r):
    g = scn.operation.grid
    g.kind = "TABLE"
    return True


@mut("operation.facility_management_ratio=0|1|neg|1.5")
def _(scn, r):
    scn.operation.facility_management_ratio = r.choice((0.0, 1.0, -0.2, 1.5))
    return True


@mut("operation.electricity_per_m2=0|neg")
def _(scn, r):
    scn.operation.electricity_per_m2_per_year = r.choice((0.0, -3.0))
    return True


@mut("profile.table!=descriptor(one entry)/one")
def _(scn, r):
    ps = [p for p in all_profiles(scn) if p.kind != "TABLE"]
    if not ps:
        return False
    p = r.choice(ps)
    Y = math.ceil(scn.boundary.study_period)
    k = r.randrange(Y)
    p.table[k] = p.table[k] * 1.5 + 10.0
    return True


@mut("profile.table_clamped_at_zero(linear negative)/all")
def _(scn, r):
    ok = False
    for p in all_profiles(scn):
        if p.kind == "LINEAR_TREND" and p.base:
            p.slope = -p.base / 3.3
            p.table = [max(0.0, p.base + p.slope * k) for k in range(len(p.table))]
            ok = True
    return ok


@mut("profile.linear_negative_unclamped/all")
def _(scn, r):
    ok = False
    for p in all_profiles(scn):
        if p.kind == "LINEAR_TREND" and p.base:
            p.slope = -p.base / 3.3
            p.table = [p.base + p.slope * k for k in range(len(p.table))]
            ok = True
    return ok


@mut("profile.to_constant/all")
def _(scn, r):
    for p in all_profiles(scn):
        v = r.choice((0.0, 123.456, 1e7))
        p.kind, p.base, p.slope, p.table = "CONSTANT", v, r.choice((None, 0.0)), [v] * len(p.table)
    return True


@mut("profile.to_linear/all")
def _(scn, r):
    for p in all_profiles(scn):
        b, s = r.choice((0.0, 5000.0, 1e6)), r.choice((0.0, 3.3, -1.7, 1e3))
        p.kind, p.base, p.slope, p.table = "LINEAR_TREND", b, s, [b + s * k for k in range(len(p.table))]
    return True


@mut("profile.to_table/all")
def _(scn, r):
    for p in all_profiles(scn):
        p.kind, p.base, p.slope = "TABLE", None, None
        p.table = [v * r.uniform(0.5, 1.5) for v in p.table]
    return True


@mut("profile.kind=TABLE_keep_descriptor/all")
def _(scn, r):
    for p in all_profiles(scn):
        p.kind = "TABLE"
    return True


@mut("profile.constant_with_nonzero_slope/all")
def _(scn, r):
    ok = False
    for p in all_profiles(scn):
        if p.kind == "CONSTANT":
            p.slope = 5.0
            ok = True
    return ok


@mut("profile.unit=unknown|convertible/one")
def _(scn, r):
    p = r.choice(all_profiles(scn))
    p.unit = r.choice(("furlong/year", "MWh/year", "kL/year", "GJ/year", "t/year", "kg", "m3"))
    return True


@mut("profile.generation_exceeds/all")
def _(scn, r):
    op = scn.operation
    f = r.choice((1.0, 1.5, 0.999999, 10.0))
    for p, q in ((op.onsite_generation, op.electricity),):
        p.kind, p.base, p.slope, p.table = q.kind, (q.base * f if q.base is not None else None), (q.slope * f if q.slope is not None else None), [v * f for v in q.table]
    e = r.choice((0.0, 0.25, 1.0, 2.0))
    p, q = op.onsite_export, op.onsite_generation
    p.kind, p.base, p.slope, p.table = q.kind, (q.base * e if q.base is not None else None), (q.slope * e if q.slope is not None else None), [v * e for v in q.table]
    return True


@mut("profile.net_crosses_zero(linear)")
def _(scn, r):
    op = scn.operation
    n = len(op.electricity.table)
    Y = math.ceil(scn.boundary.study_period)
    b = 1000.0
    for p, (bb, ss) in ((op.electricity, (b, 0.0)), (op.onsite_generation, (0.0, 2 * b / max(1, Y))), (op.onsite_export, (0.0, 0.0))):
        p.kind, p.base, p.slope, p.table = "LINEAR_TREND", bb, ss, [bb + ss * k for k in range(n)]
    return True


@mut("operation.factor_ids=None|dangling|unlicensed")
def _(scn, r):
    op, ww = scn.operation, scn.water_waste
    slot = r.choice((("op", "gas_factor_id"), ("op", "oil_factor_id"), ("op", "district_heat_factor_id"),
                     ("ww", "water_factor_id"), ("ww", "sewage_factor_id"), ("ww", "waste_factor_id")))
    o = op if slot[0] == "op" else ww
    v = r.choice(("None", "dangling", "unlicensed"))
    if v == "None":
        setattr(o, slot[1], None)
    elif v == "dangling":
        setattr(o, slot[1], "F-NO-SUCH")
    else:
        fid = getattr(o, slot[1])
        if fid in scn.factors:
            scn.factors[fid].licence_status = "UNKNOWN"
    return True


@mut("operation.all_factor_ids=None")
def _(scn, r):
    op, ww = scn.operation, scn.water_waste
    op.gas_factor_id = op.oil_factor_id = op.district_heat_factor_id = None
    ww.water_factor_id = ww.sewage_factor_id = ww.waste_factor_id = None
    return True


# ---- end of life ----
@mut("eol.demolition.quantity|unit|factor")
def _(scn, r):
    acts = scn.end_of_life.demolition_activities
    if not acts:
        return False
    a = r.choice(acts)
    v = r.choice(("qNone", "q0", "qneg", "unit", "fNone", "fdang"))
    if v == "qNone":
        a.quantity = None
    elif v == "q0":
        a.quantity = 0.0
    elif v == "qneg":
        a.quantity = -3.0
    elif v == "unit":
        a.unit = "furlong"
    elif v == "fNone":
        a.factor_id = None
    else:
        a.factor_id = "F-NO-SUCH"
    return True


@mut("eol.hauls.mass|dist|factor")
def _(scn, r):
    hs = scn.end_of_life.waste_hauls
    if not hs:
        return False
    a = r.choice(hs)
    v = r.choice(("mNone", "dNone", "m0", "fNone", "fdang", "both"))
    if v == "mNone":
        a.mass_t = None
    elif v == "dNone":
        a.distance_km = None
    elif v == "m0":
        a.mass_t = 0.0
    elif v == "fNone":
        a.factor_id = None
    elif v == "fdang":
        a.factor_id = "F-NO-SUCH"
    else:
        a.mass_t = a.distance_km = None
    return True


@mut("eol.lists=empty")
def _(scn, r):
    scn.end_of_life.demolition_activities = []
    scn.end_of_life.waste_hauls = []
    return True


# ---- project / boundary / summary ----
@mut("project.gfa=None|0|neg|tiny|huge")
def _(scn, r):
    scn.project.gross_floor_area = r.choice((None, 0.0, -100.0, 1e-9, 1e12, 0))
    return True


@mut("project.use_area_breakdown=variants")
def _(scn, r):
    a = scn.project.gross_floor_area or 100.0
    scn.project.use_area_breakdown = r.choice(({}, {"office": a}, {"office": a * (1 + 5e-10)}, {"office": a * (1 + 2e-9)},
                                               {"office": a * (1 + 5e-7)}, {"office": a * (1 + 2e-6)}, {"b": a / 3, "a": a / 3, "c": a / 3},
                                               {"x": -a, "y": 2 * a}, {"office": a * (1 + 1e-9)}, {"office": a * (1 + 1e-6)}))
    return True


@mut("boundary.replacement=variants")
def _(scn, r):
    b = scn.boundary
    T = b.study_period
    b.reconstruction_scenario = r.choice(("REBUILD_IDENTICAL", "MAJOR_REFURBISHMENT", "NONE", "BOGUS"))
    b.replacement_cycle = r.choice((None, 0.0, -5.0, T, T / 2, T / 3, 0.5 if T < 500 else 5, math.nextafter(T, 0), 1, 1.0, T * 2))
    b.reconstruction_scope_fraction = r.choice((0.0, 1.0, 0.3, -0.5, 2.0))
    return True


@mut("boundary.included=variants")
def _(scn, r):
    S = list(model.LIFECYCLE_STAGES)
    scn.boundary.included_lifecycle_stages = r.choice(([], ["B3"], ["B1"], ["B6"], ["B2"], ["B5"], ["C3"], ["A1-A3", "A1-A3"], ["D"], S[::-1],
                                                       ["B4", "B3"], ["B7"], ["A5"], ["B6", "B2"], S + ["D"], r.sample(S, 4)))
    return True


@mut("boundary.study_period=changed_after_generation")
def _(scn, r):
    T = scn.boundary.study_period
    Y = len(scn.operation.electricity.table) - 1
    scn.boundary.study_period = min(float(Y), r.choice((T / 2, T + 0.5, T - 0.25 if T > 0.3 else T, math.ceil(T) + 1e-9, 0.01, 1.0, float(Y), 129.0, 17.25)))
    return True


@mut("boundary.gas_scope=CO2_ONLY")
def _(scn, r):
    scn.boundary.results_gas_scope = "CO2_ONLY"
    return True


@mut("summary.quantities=0|neg|huge")
def _(scn, r):
    sq = scn.summary_quantities
    for name in ("reinforcement_kg", "steel_kg", "concrete_m3", "timber_m3", "envelope_m2", "interior_m2"):
        if r.random() < 0.6:
            setattr(sq, name, r.choice((0.0, -5.0, 1e-9, 1e12, 0)))
    return True


@mut("summary.timber=variants")
def _(scn, r):
    sq = scn.summary_quantities
    sq.timber_dry_density_kg_per_m3 = r.choice((0.0, 450.0, -1.0))
    sq.timber_carbon_fraction = r.choice((0.0, 0.5, 1.0))
    return True


@mut("summary.concrete_uptake_factor=None|dangling|unlicensed|unit|nourl")
def _(scn, r):
    sq = scn.summary_quantities
    v = r.choice(("None", "dangling", "unlicensed", "unit", "nourl", "convertible"))
    fid = sq.concrete_uptake_factor_id
    if v == "None":
        sq.concrete_uptake_factor_id = None
    elif v == "dangling":
        sq.concrete_uptake_factor_id = "F-NO-SUCH"
    elif fid in scn.factors:
        if v == "unlicensed":
            scn.factors[fid].licence_status = "UNKNOWN"
        elif v == "unit":
            scn.factors[fid].unit = "furlong"
        elif v == "nourl":
            scn.factors[fid].source_url = ""
        else:
            scn.factors[fid].unit = "L"
    return True


# ---- baselines ----
@mut("baseline=comparable")
def _(scn, r):
    population.attach_baseline(scn)
    return True


@mut("baseline=not_comparable")
def _(scn, r):
    base = population.attach_baseline(scn)
    v = r.choice(("area", "period", "stages", "scope", "version", "areaNone", "multi"))
    if v in ("area", "multi"):
        base.project.gross_floor_area = (base.project.gross_floor_area or 1.0) * 1.01
    if v in ("period", "multi"):
        base.boundary.study_period = scn.boundary.study_period * 0.5
    if v in ("stages", "multi"):
        base.boundary.included_lifecycle_stages = list(base.boundary.included_lifecycle_stages)[1:]
    if v in ("scope", "multi"):
        base.boundary.results_gas_scope = "CO2_ONLY" if scn.boundary.results_gas_scope != "CO2_ONLY" else "CO2E_ALL_GASES"
    if v in ("version", "multi"):
        next(iter(base.factors.values())).release_year += 77
    if v == "areaNone":
        base.project.gross_floor_area = None
    return True


@mut("baseline=zero_or_negative_total")
def _(scn, r):
    base = population.attach_baseline(scn)
    v = r.choice(("empty_stages", "neg"))
    if v == "empty_stages":
        base.boundary.included_lifecycle_stages = []
        scn.boundary.included_lifecycle_stages = []
    else:
        for rec in base.factors.values():
            rec.value = -abs(rec.value)
        base.operation.grid.licence_status = "UNKNOWN"
        for d in base.refrigerants:
            d.gwp = -abs(d.gwp) if d.gwp is not None else None
    return True


@mut("baseline=stages_same_set_different_order_or_dups")
def _(scn, r):
    base = population.attach_baseline(scn)
    s = list(scn.boundary.included_lifecycle_stages)
    r.shuffle(s)
    base.boundary.included_lifecycle_stages = s + s[:2]
    return True


@mut("baseline=defective_baseline")
def _(scn, r):
    base = population.attach_baseline(scn)
    for m in base.materials[::3]:
        m.quantity = None
    for rec in list(base.factors.values())[::7]:
        rec.licence_status = "UNKNOWN"
    return True
