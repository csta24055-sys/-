from h import *
from common.compare import compare
inf = float("inf")
def study_fail(scn):
    ref, full, tot = run3(scn)
    scale = abs(ref["SUM-03"]["value"]) or 1.0
    out = []
    for uid in ref:
        c = compare(ref[uid], full.get(uid, {}), floor=1e-9 * scale)
        cs = compare(ref[uid], tot.get(uid, {}), floor=1e-9 * scale, ignore_missing=True)
        if not (c.within(1e-9) and not c.extra and cs.within(1e-9)):
            out.append((uid, c.worst_path, c.max_abs_rel_error, c.mismatches[:2], cs.max_abs_rel_error, cs.mismatches[:2]))
    return out, ref, full, tot

print("=== (b) renewal period 1.000000001: minimal demonstrations")
for T in (60.0, 30.0, 62.5):
    for where in ("material", "equipment"):
        s = mk(1, T, composite_share=0.0, epd_share=0.0, explicit_event_share=0.0, change_list_share=0.0, service_life_choices=[25.0])
        if where == "material":
            row = max(s.materials, key=lambda r: (r.quantity or 0) * (r.repair_rate or 0)); row.refresh_cycle = 1.000000001
            if not row.repair_rate: row.repair_rate = 0.01
        else:
            eq = s.equipment[0]; eq.service_life = 1.000000001; eq.repair_rate = eq.repair_rate or 0.01
        fails, ref, full, tot = study_fail(s)
        b3r, b3f, b3t = ref["B3-01"]["value"], full["B3-01"]["value"], tot["B3-01"]["value"]
        print(f"T={T} {where}: B3-01 ref {b3r!r} unified full {b3f!r} totals {b3t!r} rel {(b3f-b3r)/b3r:+.3e}; SUM-03 ref {ref['SUM-03']['value']!r} unified {full['SUM-03']['value']!r} rel {(full['SUM-03']['value']-ref['SUM-03']['value'])/ref['SUM-03']['value']:+.3e}; units failing the study's own comparison: {[f[0] for f in fails]}")
        print("     unified full output: B3-01 value", b3f, "vs sum of its own by_year", sum(full["B3-01"]["by_year"]), "| X-07 value", full["X-07"]["value"], "vs SUM-03", full["SUM-03"]["value"], "| QA-01", full["QA-01"], "ref QA-01", ref["QA-01"])
# sweep too
s = mk(1, 60.0, composite_share=0.0, epd_share=0.0, explicit_event_share=0.0, change_list_share=0.0, service_life_choices=[25.0])
s.materials[0].refresh_cycle = 1.000000001; s.materials[0].repair_rate = 0.02; s.boundary.baseline_scenario = None
got = engine.sweep(s, [10.0, 30.0, 60.0, 100.0])
for T in (10.0, 30.0, 60.0, 100.0):
    o = copy.deepcopy(s); o.boundary.study_period = T
    r = registry.run_all(o)
    print(f"   sweep T={T}: B3-01 ref {r['B3-01']['value']!r} sweep {got[T]['B3-01']['value']!r}")

print("=== (a) facility_management_ratio = 1.0 with small fuel use")
for scale in (1.0, 1e-3, 1e-5, 1e-6, 1e-7, 1e-8, 1e-9):
    s = mk(3, 60.0, profile_kind="CONSTANT", grid_kind="CONSTANT")
    s.operation.facility_management_ratio = 1.0
    for p in (s.operation.gas, s.operation.oil, s.operation.district_heat):
        p.base *= scale; p.table = [p.base] * len(p.table)
    fails, ref, full, tot = study_fail(s)
    print(f"  fuel scale {scale:g}: B6 stage ref {ref['X-02']['by_stage']['B6']!r} unified {full['X-02']['by_stage']['B6']!r}; QA-01 ref {ref['QA-01']} unified {full['QA-01']}; failing units {[f[0] for f in fails]}")
for share in (1.0, 0.9999999, 0.999999, 0.99999):
    s = mk(3, 60.0, profile_kind="CONSTANT", grid_kind="CONSTANT")
    s.operation.facility_management_ratio = share
    s.operation.gas_factor_id = s.operation.oil_factor_id = s.operation.district_heat_factor_id = None
    fails, ref, full, tot = study_fail(s)
    print(f"  share {share!r}, no fuel factor: B6 stage ref {ref['X-02']['by_stage']['B6']!r} unified {full['X-02']['by_stage']['B6']!r}; QA-01 ref ok={ref['QA-01']['ok']} unified ok={full['QA-01']['ok']}; failing units {[f[0] for f in fails]}")

print("=== (c) the study's compare() with infinities")
for a, b in ((inf, 1.0), (inf, -inf), (1.0, inf), (-inf, 5.0)):
    c = compare({"value": a}, {"value": b}, floor=1e-9)
    print(f"  compare(ref={a}, cand={b}): within(1e-9)={c.within(1e-9)} max_abs_rel_error={c.max_abs_rel_error} mismatches={c.mismatches}")
c = compare({"ok": True, "n": 1}, {"ok": 1, "n": True})
print("  compare(ref ok=True,n=1 ; cand ok=1,n=True): within =", c.within(1e-9), c.mismatches)
