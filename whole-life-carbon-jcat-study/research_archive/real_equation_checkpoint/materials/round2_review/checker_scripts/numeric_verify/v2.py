from vh import *
print("=== NUM-2 ===")
def show(label, s, units=()):
    r, f, t = three(s)
    print(" ", label)
    for nm, x in (("ref", r), ("full", f), ("tot", t)):
        if isinstance(x, Exception):
            print("    ", nm, "RAISES", repr(x)[:100])
        else:
            print("    ", nm, {u + "." + k: x[u][k] for u, k in units})
    return r, f, t
# (a) crash asymmetry in grid descriptor
for fld, v in (("annual_decline", nan), ("start", nan), ("floor", nan), ("start", inf), ("floor", -inf), ("annual_decline", inf), ("start", -inf), ("floor", inf)):
    s = mk(1, 60.0, grid_kind="LINEAR_DECLINE_TO_FLOOR"); setattr(s.operation.grid, fld, v)
    show(f"grid.{fld}={v}", s, (("X-06", "source"), ("SUM-03", "value")))
# baseline only
s = mk(5, 60.0, grid_kind="LINEAR_DECLINE_TO_FLOOR"); b = population.attach_baseline(s); b.operation.grid.annual_decline = nan
r, f, t = three(s); print("  baseline-only NaN decline: ref SUM-08", g(r, "SUM-08", "status"), "| full", g(f, "SUM-08", "status"), "| tot", g(t, "SUM-08", "status"))
# (b) QA-01
for label, mut in (("gas.base=nan", lambda s: setattr(s.operation.gas, "base", nan)),
                   ("grid.construction_value=nan", lambda s: setattr(s.operation.grid, "construction_value", nan)),
                   ("grid.construction_value=inf", lambda s: setattr(s.operation.grid, "construction_value", inf)),
                   ("water.base=inf", lambda s: setattr(s.water_waste.water, "base", inf)),
                   ("factor value nan (materials[0])", lambda s: setattr(s.factors[s.materials[0].factor_id], "value", nan)),
                   ):
    s = mk(1, 60.0, profile_kind="CONSTANT", composite_share=0.0, epd_share=0.0); mut(s)
    show(label, s, (("QA-01", "ok"), ("QA-01", "violations"), ("B5-01", "value"), ("B6-03", "value"), ("SUM-03", "value")))
s = mk(1, 60.0, profile_kind="LINEAR_TREND"); s.operation.gas.slope = inf
show("gas.slope=inf", s, (("B6-03", "value"), ("SUM-03", "value"), ("QA-01", "ok")))
s = mk(1, 60.0, grid_kind="TABLE") if False else mk(1, 60.0)
print("  grid kind of default scenario:", s.operation.grid.kind)
s.operation.grid.kind = "TABLE"; s.operation.grid.table[0] = inf
show("grid.table[0]=inf (kind TABLE)", s, (("B6-03", "value"), ("B2-01", "value"), ("X-06", "source")))
# does the study's NaN mutation hit any of these fields?
from bench import mutations
s = mk(1, 60.0); mutations._nan_inf(s)
print("  study mutation nan_and_infinite_values -> study comparison failures:", study_fails(s))
