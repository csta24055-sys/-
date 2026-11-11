from vh import *
def flags(x):
    return {k: x[k].get("ok") for k in x if k.startswith(("SYS", "QA"))}, {k: x[k].get("complete") for k in ("SUM-01", "SUM-03")}, x["X-02"]["incomplete_units"]
for label, mut in (("gas.base=nan", lambda s: setattr(s.operation.gas, "base", nan)),
                   ("gas.base=-5e9 (negative annual quantity)", lambda s: (setattr(s.operation.gas, "base", -5e9), setattr(s.operation.gas, "table", [-5e9] * len(s.operation.gas.table)))),
                   ("factor value nan", lambda s: setattr(s.factors[s.materials[0].factor_id], "value", nan)),
                   ("factor value negative", lambda s: setattr(s.factors[s.materials[0].factor_id], "value", -1e9)),
                   ("grid.construction_value=nan", lambda s: setattr(s.operation.grid, "construction_value", nan))):
    s = mk(1, 60.0, profile_kind="CONSTANT", composite_share=0.0, epd_share=0.0); mut(s)
    r, f, t = three(s)
    print(label); print("   ref  SUM-03", r["SUM-03"]["value"], flags(r)); print("   full SUM-03", f["SUM-03"]["value"], flags(f))
print("--- NUM-9 extras")
s = mk(71, 60.0, scenario_id="V9"); b = population.attach_baseline(s)
held = {}
e1 = engine.evaluate(s, detail=False, baseline_totals=held)["SUM-08"]
for row in b.materials:
    if row.quantity is not None: row.quantity *= 2.0
r2 = registry.run_all(s, ids=["SUM-08"])["SUM-08"]; e2 = engine.evaluate(s, detail=False, baseline_totals=held)["SUM-08"]; e3 = engine.evaluate(s, detail=False)["SUM-08"]
print("  edited baseline: ref", r2["baseline"], "held", e2["baseline"], "no held", e3["baseline"])
e4 = engine.evaluate(s, detail=False, baseline_totals={b.meta.scenario_id: 0.0})["SUM-08"]; print("  supplied 0.0:", e4)
