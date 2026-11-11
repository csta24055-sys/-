import sys, os, copy, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe import *
import collections

# 1. boundary-coincident periodic events in the study's own population
stat = collections.Counter(); ex = []
for i, scn in enumerate(population.verification_population(400, 20261111, max_size="S")):
    T = scn.boundary.study_period
    lives = [("eq", e.service_life) for e in scn.equipment if e.replacement_event_list is None] + \
            [("mat", r.refresh_cycle) for r in scn.materials] + \
            [("ref", d.service_life) for d in scn.refrigerants if d.change_years is None] + [("bld", scn.boundary.replacement_cycle)]
    for kind, L in lives:
        if L is None or L <= 0:
            continue
        n = round(T / L)
        if n >= 1 and abs(n * L - T) <= 1e-9 * T:
            counted = n * L < T
            stat[(T, "counted" if counted else "not counted", "exact" if n * L == T else "inexact")] += 1
            if counted and len(ex) < 8:
                ex.append((i, scn.meta.scenario_id, kind, T, L, n, repr(n * L)))
print("boundary-coincident periodic lives in verification_population(400, seed 20261111, S):")
for k, v in sorted(stat.items()):
    print("   ", k, v)
print("   examples counted although n*L ~ T:", ex)

# 2. B4 renewals coinciding with a B5 rebuild year (same-year double count)
for name, scn in population.edge_cases():
    if scn.boundary.reconstruction_scenario == "NONE":
        continue
    r = registry.run_all(scn)
    b5y = [y for y, v in enumerate(r["B5-01"]["by_year"]) if v]
    b4 = r["B4-02"]["by_year"]
    same = sum(b4[y] for y in b5y)
    print(f"edge:{name}: scenario={scn.boundary.reconstruction_scenario} C={scn.boundary.replacement_cycle} phi={scn.boundary.reconstruction_scope_fraction} B5 years {b5y} B5={r['B5-01']['value']:.1f} B4 total={r['B4-02']['value']:.1f} B4 in B5 years={same:.1f} ({100*same/r['B4-02']['value']:.2f}% of B4)")
    # renewals that happen within x years AFTER a full rebuild although the component was just renewed
    T = scn.boundary.study_period
    # per-row check: material rows whose renewal times coincide exactly with rebuild times
    rb = [n * scn.boundary.replacement_cycle for n in range(1, 100) if n * scn.boundary.replacement_cycle < T]
    co = [(i, row.refresh_cycle) for i, row in enumerate(scn.materials) if row.refresh_cycle and any(abs(k * row.refresh_cycle - t) < 1e-9 for t in rb for k in range(1, 200))]
    coe = [(j, e.service_life) for j, e in enumerate(scn.equipment) if e.replacement_event_list is None and e.service_life and any(abs(k * e.service_life - t) < 1e-9 for t in rb for k in range(1, 200))]
    print("     rows renewed at exactly a rebuild time: materials", co, "equipment", coe)

# 3. equipment initial delivery / installation: counted at renewal (B4) but not initially (A4/A5)
from synth.population import standard_benchmark
scn = standard_benchmark()[0]
r = registry.run_all(scn)
ini_del = ini_inst = 0.0; n_del = n_inst = 0
for e in scn.equipment:
    for fid, which in ((e.delivery_factor_id, "d"), (e.installation_factor_id, "i")):
        if fid is None or e.quantity is None:
            continue
        rec = scn.factors[fid]
        if rec.licence_status != "PERMITTED_PUBLIC":
            continue
        v = e.quantity * rec.value
        if which == "d":
            ini_del += v; n_del += 1
        else:
            ini_inst += v; n_inst += 1
mat_inst = 0.0; n_mi = 0
for i, row in enumerate(scn.materials):
    if row.installation_factor_id is None:
        continue
    rec = scn.factors[row.installation_factor_id]
    c = mine.conv(scn, row.quantity_unit, rec.unit, row.conversions)
    q = r["A13-05"]["q_ord"][i]
    if c is None or q is None:
        continue
    mat_inst += q * c * rec.value; n_mi += 1
bs = r["X-02"]["by_stage"]
print(f"benchmark S ({scn.meta.scenario_id}): A4={bs['A4']:.1f} A5={bs['A5']:.1f} B4={bs['B4']:.1f}")
print(f"   equipment initial delivery not in any stage: {ini_del:.1f} kgCO2e ({n_del} rows) = {100*ini_del/bs['A4']:.2f}% of A4")
print(f"   equipment initial installation not in any stage: {ini_inst:.1f} kgCO2e ({n_inst} rows) = {100*ini_inst/bs['A5']:.2f}% of A5")
print(f"   material installation by factor (counted only at renewals): one-time equivalent {mat_inst:.1f} kgCO2e ({n_mi} rows) = {100*mat_inst/bs['A5']:.2f}% of A5")
print("   stage list of delivery/installation factors:", {fid: scn.factors[fid].stages for e in scn.equipment for fid in (e.delivery_factor_id, e.installation_factor_id) if fid} )
print("   material installation factor stages:", {row.installation_factor_id: scn.factors[row.installation_factor_id].stages for row in scn.materials if row.installation_factor_id})
# 4. B2 carved out of B6 in benchmark and embodied share
print(f"   B2={bs['B2']:.1f} B6={bs['B6']:.1f} B6-03={r['B6-03']['value']:.1f} SUM-02={r['SUM-02']['value']:.1f} -> B2 is {100*bs['B2']/r['SUM-02']['value']:.2f}% of 'embodied'")
