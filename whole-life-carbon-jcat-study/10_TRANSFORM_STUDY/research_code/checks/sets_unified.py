"""Verification sets of the unified system (fictional scenarios of the frozen generator).

  dev_*   scenarios the specification was developed on (2026-11-12 / 13)
  rep_*   the 693 (scenario, T) pairs that were NOT used for development in the run of 2026-11-12, rebuilt
          from the same seeds, periods and mutation code (the mutation code below is the code of that run,
          recovered from the session record); rep_defects are the 24 defect-injected pairs of that run
  new_*   pairs first used on 2026-11-13 after the specification of all 70 units was complete

Every entry is (label, scenario, periods, inside_valid_domain_expected).
"""
import copy

from tstudy import baseline, scenarios

REP_DEFECT_SEED = 616201
NEW_POPULATION_SEED = 750003
NEW_DEFECT_SEED = 760001
NEW_SPECIAL_SEED = 770001


def _gen():
    baseline.load()
    from synth import generate, model, population
    return generate, model, population


FAILED_MUTATIONS = []


def mut(s, tag, f):
    c = copy.deepcopy(s)
    try:
        f(c)
    except Exception as ex:                                   # a mutation that does not fit the scenario is listed, not hidden
        FAILED_MUTATIONS.append((tag, s.meta.scenario_id, "%s %s" % (type(ex).__name__, ex)))
        return None
    c.meta.scenario_id += "#" + tag
    return (tag + " | " + s.meta.scenario_id[:34], c)


def setattrs(path, **kw):
    def f(c):
        o = c
        for p in path.split("."):
            o = getattr(o, p)
        for k, v in kw.items():
            setattr(o, k, v)
    return f


def constructed(ev):
    """Special conditions of the run of 2026-11-12 (115 cases on evaluation scenarios)."""
    generate, model, population = _gen()
    cases = []
    for s in [s for s in ev if s.operation.gas.kind != "TABLE" and s.operation.grid.kind != "TABLE"][:2]:
        def f1(c): c.operation.gas.table[40] *= 1.01
        def f2(c): c.operation.grid.table[25] += 1e-6
        def f3(c):
            w = c.water_waste.water
            w.kind, w.base, w.slope = "CONSTANT", w.table[0], None
            w.table[10] *= (1 + 5e-13)
        def f4(c):
            e = c.operation.electricity
            e.kind, e.base, e.slope = "LINEAR_TREND", 1000.0, 3.0
        cases += [mut(s, "gas table differs at year 40", f1), mut(s, "grid table differs at year 25", f2), mut(s, "water within 1e-12 of the table", f3),
                  mut(s, "electricity descriptor replaces table", f4)]
    for s in ev[3:5]:
        for tag, f in (("electricity MWh/year", setattrs("operation.electricity", unit="MWh/year")), ("electricity kWh/month", setattrs("operation.electricity", unit="kWh/month")),
                       ("electricity kWh (no time base)", setattrs("operation.electricity", unit="kWh")), ("generation in MJ/year", setattrs("operation.onsite_generation", unit="MJ/year")),
                       ("export unit unknown", setattrs("operation.onsite_export", unit="XYZ/year")), ("grid kgCO2e/MWh", setattrs("operation.grid", unit="kgCO2e/MWh")),
                       ("grid unit without denominator", setattrs("operation.grid", unit="kgCO2e/")), ("grid gCO2e/kWh", setattrs("operation.grid", unit="gCO2e/kWh")),
                       ("grid licence unknown", setattrs("operation.grid", licence_status="UNKNOWN")), ("gas in L/year", setattrs("operation.gas", unit="L/year")),
                       ("gas per day", setattrs("operation.gas", unit="m3/day")), ("oil factor missing", setattrs("operation", oil_factor_id=None)),
                       ("water factor unknown id", setattrs("water_waste", water_factor_id="NO-SUCH")), ("fm ratio 1.5", setattrs("operation", facility_management_ratio=1.5)),
                       ("fm ratio missing", setattrs("operation", facility_management_ratio=None)), ("intensity negative", setattrs("operation", electricity_per_m2_per_year=-1.0)),
                       ("constant without base", setattrs("operation.gas", kind="CONSTANT", base=None)),
                       ("stages without B2", setattrs("boundary", included_lifecycle_stages=[x for x in model.LIFECYCLE_STAGES if x != "B2"])),
                       ("stages without B6", setattrs("boundary", included_lifecycle_stages=[x for x in model.LIFECYCLE_STAGES if x != "B6"])),
                       ("stages B5 only", setattrs("boundary", included_lifecycle_stages=["B5"])),
                       ("stages B1 B6 only", setattrs("boundary", included_lifecycle_stages=["B1", "B6"])),
                       ("rebuild every 25 years, scope 0.3", setattrs("boundary", reconstruction_scenario="MAJOR_REFURBISHMENT", replacement_cycle=25.0, reconstruction_scope_fraction=0.3)),
                       ("rebuild scope invalid", setattrs("boundary", reconstruction_scenario="REBUILD_IDENTICAL", replacement_cycle=25.0, reconstruction_scope_fraction=1.4))):
            cases.append(mut(s, tag, f))
    for s in [x for x in ev if x.operation.grid.kind == "STEPWISE"][:2]:
        def g1(c): c.operation.grid.steps[0].from_index = 1
        def g2(c): c.operation.grid.steps[-1].from_index = c.operation.grid.steps[0].from_index
        def g3(c): c.operation.grid.steps = []
        cases += [mut(s, "steps do not start at 0", g1), mut(s, "steps not increasing", g2), mut(s, "steps empty", g3)]
    for s in [x for x in ev if x.operation.grid.kind == "LINEAR_DECLINE_TO_FLOOR"][:2]:
        cases += [mut(s, "start below floor", setattrs("operation.grid", floor=9.0)), mut(s, "steep decline (floor from year 3)", setattrs("operation.grid", annual_decline=0.08))]
    for s in [x for x in ev if any(d.change_years is not None for d in x.refrigerants) and x.equipment][:3]:
        def r1(c):
            d = next(d for d in c.refrigerants if d.change_years is not None); d.change_years = [0, 10.2, 10.7, 10.9, 30, 31]; d.top_up = False
        def r2(c):
            d = next(d for d in c.refrigerants if d.change_years is not None); d.change_years = [-3, 12, 500]; d.top_up = False
        def life(v, leak=None):
            def f(c):
                for d in c.refrigerants:
                    d.top_up, d.change_years, d.service_life = False, None, v
                    if leak is not None: d.annual_leak_rate = leak
            return f
        def r6(leak):
            def f(c):
                for d in c.refrigerants: d.top_up, d.change_years, d.annual_leak_rate = False, [], leak
            return f
        def r7(c):
            c.refrigerants[0].replacement_loss_rate = 1.2; c.refrigerants[-1].end_of_life_recovery_rate = None
            if len(c.refrigerants) > 2: c.refrigerants[1].gwp = -1.0
        def r8(c): c.equipment[0].replacement_event_list = [0, 15, 15.5, 44]
        cases += [mut(s, "list with 0 and three events in one year", r1), mut(s, "list with negative and far value", r2), mut(s, "all devices life 0.4, no top-up", life(0.4)),
                  mut(s, "all devices life 7.3, no top-up", life(7.3)), mut(s, "no change events at all, no top-up", life(None)),
                  mut(s, "life 25, leak 30%, no top-up", life(25.0, 0.30)), mut(s, "no events, leak 35%", r6(0.35)), mut(s, "no events, leak 60%", r6(0.60)),
                  mut(s, "invalid loss / recovery / gwp", r7), mut(s, "equipment list with 0", r8)]
    for s in [s for s in ev if s.boundary.baseline_scenario][:3]:
        def b1(c): c.project.gross_floor_area *= 1.5
        def b2(c): c.boundary.included_lifecycle_stages = [x for x in c.boundary.included_lifecycle_stages if x != "B7"]
        def b3(c): c.boundary.results_gas_scope = [g for g in model.GAS_SCOPES if g != c.boundary.results_gas_scope][0]
        def b4(c): next(iter(c.factors.values())).release_year += 7
        def b5(c): b1(c); b2(c); b4(c)
        def b6(c): c.boundary.baseline_scenario = "NO-SUCH-BASELINE"
        cases += [mut(s, "baseline: area differs", b1), mut(s, "baseline: stages differ", b2), mut(s, "baseline: gas scope differs", b3),
                  mut(s, "baseline: factor version differs", b4), mut(s, "baseline: three reasons", b5), mut(s, "baseline: unknown id", b6),
                  mut(s, "baseline: unchanged", lambda c: None)]
    return cases


DIRTY_KINDS = [("RC", "office"), ("S", "school"), ("W", "retail"), ("SRC", "hospital"), ("RC", "residential"), ("S", "warehouse"),
               ("W", "office"), ("SRC", "school"), ("RC", "retail"), ("S", "hospital"), ("W", "residential"), ("RC", "warehouse")]


def dirty(seed0, n=12):
    generate, model, population = _gen()
    return [("dirty %d" % (seed0 + i), generate.make_scenario(seed0 + i, st, use, "S" if i % 3 else "M", 60.0, dirty=True))
            for i, (st, use) in enumerate(DIRTY_KINDS[:n])]


def new_special(pop):
    """Special conditions written on 2026-11-13 for the units added that day (states, unit and reference gates,
    lines, cycles, classes). ``pop`` are scenarios of the new population."""
    generate, model, population = _gen()
    cases = []
    for s in pop[:3]:
        def st1(c):                                           # SYS-01: overrides on rows, on the single records and on list items
            c.materials[0].states["quantity"] = "ESTIMATE"; c.materials[1].states["waste_rate"] = "DERIVED"
            c.materials[2].states["transport.mass_t"] = "MISSING"; c.materials[3].quantity = 0.0
            c.materials[4].states["end_of_life.mass_kg"] = "EXPLICIT_ZERO"; c.materials[5].refresh_cycle = None
            c.project.states["gross_floor_area"] = "ESTIMATE"; c.construction.states["electricity_kwh"] = "DERIVED"
            if c.construction.fuels: c.construction.states["fuels[0].quantity"] = "ESTIMATE"
            if len(c.construction.waste_streams) > 1: c.construction.states["waste_streams[1].mass_kg"] = "MISSING"
            if c.end_of_life.demolition_activities: c.end_of_life.states["demolition_activities[0].quantity"] = "DERIVED"
            if c.end_of_life.waste_hauls:
                c.end_of_life.states["waste_hauls[0].distance_km"] = "ESTIMATE"; c.end_of_life.waste_hauls[0].mass_t = None
            if c.equipment:
                c.equipment[0].service_life = None; c.equipment[0].replacement_event_list = [12.0, 30.0]
                c.equipment[-1].service_life = None; c.equipment[-1].replacement_event_list = None
            if c.refrigerants:
                c.refrigerants[0].service_life = None; c.refrigerants[0].change_years = None
                c.refrigerants[-1].states["gwp"] = "ESTIMATE"
        def st2(c):                                           # provenance record unknown / state of the record
            c.materials[0].provenance_id = "NO-SUCH-RECORD"
            for p in list(c.provenance.values())[:1]: p.value_state = "ESTIMATE"
            c.materials[1].states["quantity"] = None
        def u1(c):                                            # SYS-02: units that cannot be converted, wrong stage of a factor
            c.materials[0].quantity_unit = "furlong"; c.materials[1].transport.delivery_factor_id = None
            c.equipment[0].quantity_unit = None
            if c.construction.fuels: c.construction.fuels[0].unit = "barrel"
            if c.end_of_life.demolition_activities: c.end_of_life.demolition_activities[0].unit = "day"
            c.operation.gas.unit = "m3/month"; c.operation.onsite_export.unit = "XYZ/year"; c.water_waste.sewage.unit = "m3"
            if c.cost_items: c.cost_items[0].currency = "XXX"
            f = c.factors[c.operation.oil_factor_id]; f.stages = ["B6", "B7"]
            row = next(r for r in c.materials if r.composition is None); c.factors[row.factor_id].stages = ["A4"]
        def u3(c):                                            # SYS-02: only the stage of two factors is wrong (no unit problem)
            row = next(r for r in c.materials if r.composition is None); c.factors[row.factor_id].stages = ["A1-A3", "A4"]
            f = c.factors.get(c.water_waste.water_factor_id)
            if f is not None: f.stages = []
        def u2(c):                                            # SYS-03 / QA-03: missing reference, missing record, licence, empty source
            rows = [r for r in c.materials if r.composition is None]
            rows[0].factor_id = None; rows[1].factor_id = "NO-SUCH-FACTOR"; rows[2].end_of_life.haul_factor_id = "NO-SUCH-FACTOR"
            c.factors[rows[3].factor_id].licence_status = "RESTRICTED"; c.factors[rows[4].factor_id].source_url = ""
            c.factors[rows[5].transport.factor_id or rows[5].transport.delivery_factor_id].source_url = None
            if c.equipment:
                c.equipment[0].factor_id = None
                e = next((e for e in c.equipment if e.installation_factor_id is not None), None)
                if e is not None: c.factors[e.installation_factor_id].source_url = ""
            c.operation.gas_factor_id = None; c.water_waste.waste_factor_id = "NO-SUCH-FACTOR"
            comp = next((r for r in c.materials if r.composition), None)
            if comp is not None: comp.composition[0].factor_id = "NO-SUCH-FACTOR"
            c.operation.grid.licence_status = "PERMISSION_REQUIRED"
        def l1(c):                                            # lines: zero quantities keep their lines; install lines appear at a renewal
            for r in c.materials[:6]: r.quantity = 0.0
            for r in c.materials[6:12]: r.refresh_cycle = 45.0
            for e in c.equipment[:3]: e.service_life = 45.0; e.replacement_event_list = None
            for e in c.equipment[3:5]: e.replacement_event_list = [7.0, 3.5, 44.0, 3.5]
        def l2(c):                                            # rebuild with lines of every stage; repair rates 0 and invalid
            c.boundary.reconstruction_scenario, c.boundary.replacement_cycle, c.boundary.reconstruction_scope_fraction = "REBUILD_IDENTICAL", 20.0, 0.5
            c.materials[0].repair_rate = 0.0; c.materials[1].repair_rate = -0.1; c.materials[2].repair_rate = None
            if c.equipment: c.equipment[0].repair_rate = None
        def l3(c):                                            # every renewal year also holds repairs of other rows; cycles below one year
            for r in c.materials[:4]: r.refresh_cycle = 0.5
            for r in c.materials[4:8]: r.refresh_cycle = 1.0
            for e in c.equipment[:2]: e.service_life, e.replacement_event_list = 0.75, None
        def x9(c):                                            # X-09: classes without a valid mass, negative fractions, unknown route factor
            for r in c.materials[:5]: r.end_of_life.mass_kg = None
            c.materials[5].end_of_life.routes[0].fraction = -0.2; c.materials[6].end_of_life.routes[1].factor_id = "NO-SUCH-FACTOR"
            c.materials[7].end_of_life.routes[3].fraction = 1.4
        def gas(c):                                           # CO2-only scope and a baseline-free stage subset with B2 excluded
            c.boundary.results_gas_scope = "CO2_ONLY"
            c.boundary.included_lifecycle_stages = [x for x in model.LIFECYCLE_STAGES if x not in ("B2", "C4")]
        cases += [mut(s, "states: overrides and missing values", st1), mut(s, "states: unknown provenance record", st2),
                  mut(s, "units: not convertible, stage of a factor", u1), mut(s, "stages: two factors with a wrong stage only", u3),
                  mut(s, "references: missing, no record, licence, source", u2),
                  mut(s, "lines: zero quantities, shared cycles, unsorted lists", l1), mut(s, "rebuild 20 years, repair rates 0 / invalid", l2),
                  mut(s, "cycles of 0.5, 0.75 and 1 year", l3), mut(s, "routes: no mass, negative fraction, unknown factor", x9),
                  mut(s, "CO2 only, stages without B2 and C4", gas)]
    return cases


def build(which):
    """The named sets as lists of (label, scenario, periods)."""
    generate, model, population = _gen()
    S, M, L = scenarios.benchmark()
    out = {}
    own = lambda s: s.boundary.study_period
    if "dev_design" in which:
        out["dev_design"] = [(s.meta.scenario_id, s, [own(s), 60.0, 62.5, 33.3]) for s in scenarios.design_set(40)]
    if "dev_edge" in which:
        out["dev_edge"] = [("edge " + n, s, [own(s), 42.5]) for n, s in scenarios.edge_set()]
    ev = scenarios.evaluation_set(60) if any(w.startswith("rep_") for w in which) else []
    if "rep_evaluation" in which:
        out["rep_evaluation"] = [(s.meta.scenario_id, s, [own(s), 60.0, 62.5, 33.3, 120.0]) for s in ev]
    if "rep_boundary" in which:
        bt = [0.001, 0.5, 1.0, 26.999999, 27.0, 27.000001, 28.999999, 29.0, 29.000001, 59.999999, 60.000001, 99.9, 129.5, 130.0]
        b2 = [0.5, 1.0, 10.999999, 11.000001, 60.0, 99.9, 129.5, 130.0]
        out["rep_boundary"] = [("benchmark S", S, bt)] + [(s.meta.scenario_id, s, b2) for s in ev[:3]] + [("benchmark M", M, b2)]
    if "rep_constructed" in which:
        out["rep_constructed"] = [(c[0], c[1], [own(c[1]), 33.3, 12.5]) for c in constructed(ev) if c]
    if "rep_scale_L" in which:
        out["rep_scale_L"] = [("benchmark L", L, [60.0, 99.9])]
    if "rep_defects" in which:
        out["rep_defects"] = [(n, s, [60.0, 33.3]) for n, s in dirty(REP_DEFECT_SEED)]
    pop = list(population.verification_population(40, NEW_POPULATION_SEED, "M")) if any(w.startswith("new_") for w in which) else []
    if "new_population" in which:
        out["new_population"] = [(s.meta.scenario_id, s, [own(s), 45.0, 75.5, 100.0, 19.999999, 20.000001]) for s in pop]
    if "new_defects" in which:
        out["new_defects"] = [(n, s, [60.0, 47.3]) for n, s in dirty(NEW_DEFECT_SEED)]
    if "new_special" in which:
        out["new_special"] = [(c[0], c[1], [own(c[1]), 44.5, 8.0]) for c in new_special(pop) if c]
    return out


ALL_SETS = ("dev_design", "dev_edge", "rep_evaluation", "rep_boundary", "rep_constructed", "rep_scale_L", "rep_defects",
            "new_population", "new_defects", "new_special")
OUTSIDE_DOMAIN = ("rep_defects", "new_defects", "new_special")     # compared without the valid-domain filter, reported separately
