import sys, os, copy, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe import *
OPT = {"generic_stage_check": True, "route_bad_skips_row": False}
cases = dict(population.edge_cases())
scn = cases["rebuild_within_period"]
ref = registry.run_all(scn)
me = mine.run(scn, ref, OPT)
T, C = scn.boundary.study_period, scn.boundary.replacement_cycle
segs = []
k = 0
while k * C < T:
    segs.append((k * C, min((k + 1) * C, T))); k += 1
def n_reset(c):
    if c is None or c <= 0:
        return 0
    n = 0
    for s, e in segs:
        j = 1
        while s + j * c < e:
            n += 1; j += 1
    return n
b4_ref = ref["B4-02"]["value"]
tot = 0.0; n_ref = n_alt = 0
for i, row in enumerate(scn.materials):
    n0 = ref["B4-03"]["by_item"][i]
    u = ref["B4-02"]["by_item_material"][i] / n0 if n0 else 0.0
    n1 = n_reset(row.refresh_cycle)
    tot += n1 * u; n_ref += n0; n_alt += n1
for j, e in enumerate(scn.equipment):
    ev = ref["B4-01"]["events"][j]
    u = ref["B4-02"]["by_item_equipment"][j] / len(ev) if ev else None
    if e.replacement_event_list is not None:
        n1 = len(ev)
    else:
        n1 = n_reset(e.service_life)
    if u is None and n1:
        print("   (row with events only under reset; unit emission unknown) eq", j)
        u = 0.0
    tot += n1 * (u or 0.0); n_ref += len(ev); n_alt += n1
print(f"edge:rebuild_within_period T={T} C={C} phi={scn.boundary.reconstruction_scope_fraction}: B4 reference (no reset) = {b4_ref:.1f} with {n_ref} renewals; with reset at each rebuild = {tot:.1f} with {n_alt} renewals; difference {b4_ref - tot:.1f} ({100*(b4_ref-tot)/b4_ref:.1f}% of B4, {100*(b4_ref-tot)/ref['SUM-03']['value']:.3f}% of SUM-03)")
# renewals happening less than 5 years before a rebuild (new part demolished shortly after)
late = 0.0
for i, row in enumerate(scn.materials):
    n0 = ref["B4-03"]["by_item"][i]
    if not n0: continue
    u = ref["B4-02"]["by_item_material"][i] / n0
    for n in range(1, n0 + 1):
        t = n * row.refresh_cycle
        nxt = math.ceil(t / C) * C
        if nxt < T and nxt - t < 5: late += u
print(f"   material renewals within 5 years before a full rebuild: {late:.1f} kgCO2e")
