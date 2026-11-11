import synth, copy, math
from fastcalc import engine
from refcalc import registry
from common.compare import compare
registry.load_all()
scn = synth.make_scenario(5, "RC", "office", "S", 60.0, n_materials=400, n_equipment=120, n_refrigerants=10, profile_kind="LINEAR_TREND", grid_kind="LINEAR_DECLINE_TO_FLOOR")
ext = []; 
for row in scn.materials:
    qu, rc = row.quantity_unit, row.conversions
    if not rc: continue
    sig = tuple((c.from_unit, c.to_unit, c.factor) for c in rc)
    if row.composition is None: ext.append((row.factor_id, "A1-A3", qu, sig))
    if row.transport.delivery_factor_id is not None: ext.append((row.transport.delivery_factor_id, "A4", qu, sig))
    if row.installation_factor_id is not None: ext.append((row.installation_factor_id, "A5", qu, sig))
print("per-row resolutions with row conversions:", len(ext), "distinct (factor, stage, unit, conversion content):", len(set(ext)), "distinct (factor, stage, unit):", len({e[:3] for e in ext}))
# standard benchmark: same numbers
from synth import population
for s in population.standard_benchmark():
    R = engine.evaluate(s, detail=False)
    n_rc = sum(1 for r in s.materials if r.conversions)
    print(s.meta.size_class, "rows", len(s.materials) + len(s.equipment), "factor_resolutions", R["_stats"]["factor_resolutions"], "rows with row conversions", n_rc,
          "EPD rows", sum(1 for r in s.materials if r.epd is not None), "groups", len(engine.aggregate(s, False).groups),
          "distinct periods/rows ratio %.2f" % (len(engine.aggregate(s, False).groups) / (len(s.materials) + len(s.equipment))))
# quick defect probes on summary quantities (X-17 path) and others
def both(s):
    out = []
    for f in (lambda: registry.run_all(s), lambda: engine.evaluate(s, detail=True), lambda: engine.evaluate(s, detail=False)):
        try: out.append(f())
        except Exception as e: out.append(e)
    return out
for name, mut in (("reinforcement_kg None", lambda s: setattr(s.summary_quantities, "reinforcement_kg", None)),
                  ("concrete_m3 nan", lambda s: setattr(s.summary_quantities, "concrete_m3", float("nan"))),
                  ("envelope_m2 negative", lambda s: setattr(s.summary_quantities, "envelope_m2", -5.0)),
                  ("timber_m3 inf", lambda s: setattr(s.summary_quantities, "timber_m3", float("inf")))):
    s = synth.make_scenario(11, "RC", "office", "S", 60.0); mut(s)
    r, a, b = both(s)
    if any(isinstance(x, Exception) for x in (r, a, b)):
        print(name, "->", [type(x).__name__ if isinstance(x, Exception) else "ok" for x in (r, a, b)])
    else:
        bad = [u for u in r if not compare(r[u], a[u], floor=1e-9 * abs(r["SUM-03"]["value"])).within(1e-9) or not compare(r[u], b[u], floor=1e-9 * abs(r["SUM-03"]["value"]), ignore_missing=True).within(1e-9)]
        print(name, "-> both ran; units differing:", bad)
