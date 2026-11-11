from h import *
from common.compare import compare
for where in ("equipment", "material"):
    s = mk(1, 60.0, composite_share=0.0, epd_share=0.0)
    if where == "equipment":
        eq = s.equipment[0]; eq.repair_rate = 0.02; fid = eq.factor_id
    else:
        row = s.materials[0]; row.repair_rate = 0.02; fid = row.factor_id
    f = s.factors[fid]
    print(where, "factor", fid, "old value", f.value, "gas_amounts", {k: v for k, v in f.gas_amounts.items() if v})
    f.value = 0.0                                   # the record's value now contradicts its gas vector
    ref, full, tot = run3(s)
    for u, k in (("B3-01", "value"), ("SUM-03", "value"), ("X-04", "value"), ("X-04", "co2e_from_gases"), ("X-05", "value")):
        print(f"    {u}.{k}: ref {ref[u][k]!r} unified {full[u][k]!r} totals {tot[u][k]!r} rel {(full[u][k]-ref[u][k])/ref[u][k]:+.3e}")
    print("    X-04.by_gas.CO2 ref", ref["X-04"]["by_gas"]["CO2"], "unified", full["X-04"]["by_gas"]["CO2"], "| X-05.by_stage_co2.B3 ref", ref["X-05"]["by_stage_co2"]["B3"], "unified", full["X-05"]["by_stage_co2"]["B3"])
    scale = abs(ref["SUM-03"]["value"])
    bad = [u for u in ref if not compare(ref[u], full[u], floor=1e-9 * scale).within(1e-9)]
    print("    units failing the study's own comparison:", bad)
# consistent variant: the gwp of one gas is 0 and a factor consists of that gas only
s = mk(1, 60.0, composite_share=0.0, epd_share=0.0)
eq = s.equipment[0]; eq.repair_rate = 0.02; f = s.factors[eq.factor_id]
s.gwp["NF3"] = 0.0
f.gas_amounts = {g: (3.0 if g == "NF3" else 0.0) for g in f.gas_amounts}; f.value = 0.0   # value == sum(gwp*amount) == 0
ref, full, tot = run3(s)
print("consistent record (only gas NF3, gwp[NF3]=0, value 0): X-04.by_gas.NF3 ref", ref["X-04"]["by_gas"]["NF3"], "unified", full["X-04"]["by_gas"]["NF3"], "| X-04.value ref", ref["X-04"]["value"], "unified", full["X-04"]["value"])
