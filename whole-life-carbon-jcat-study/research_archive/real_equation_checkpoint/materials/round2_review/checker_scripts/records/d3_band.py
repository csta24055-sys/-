"""D3: 'for c >= 1 every event has its own year' -- scan the band just above 1, then show the effect end to end."""
import math, random, copy
from fastcalc import closed_forms as cf, engine
from refcalc import base, registry
from common.compare import compare
import synth
registry.load_all()
rnd = random.Random(7)

def brute(T, c):
    ev = base.periodic_events(T, c); w = base.year_weights(T)
    S = {base.event_year(t) for t in ev}
    return len(ev), len(S), sum(w[y] for y in S)

print("scan c = 1 + j*1e-10, T = 60")
fails = []
for j in range(0, 60):
    c = 1.0 + j * 1e-10
    n, ns, sw = brute(60.0, c)
    got = cf.skip_weight_periodic(60.0, c, cf.renewal_count(60.0, c))
    if abs(got - sw) > 1e-9: fails.append((j, c, n, ns, sw, got))
for f in fails: print("   j=%d c=%.12f events=%d distinct_years=%d reference_skip=%.6f closed_form=%.6f" % f)
print("random scan c in [1, 1+3e-9], T in {10,30,42.5,60,100}")
nb = 0; N = 20000; lo = 9; hi = 0
for _ in range(N):
    c = 1.0 + rnd.uniform(0, 3e-9); T = rnd.choice([10.0, 30.0, 42.5, 60.0, 100.0])
    n, ns, sw = brute(T, c)
    got = cf.skip_weight_periodic(T, c, cf.renewal_count(T, c))
    if abs(got - sw) > 1e-9:
        nb += 1; lo = min(lo, c - 1.0); hi = max(hi, c - 1.0)
print(f"   {nb}/{N} mismatches; offsets c-1 of failing periods between {lo:.3e} and {hi:.3e}")
print("random scan over wider ranges: c in [1+3e-9, 80] and (0,1)")
nb = 0
for _ in range(300000):
    c = rnd.choice([rnd.uniform(1.0 + 3e-9, 80.0), rnd.uniform(0.01, 1.0), 1.0 + 10 ** rnd.uniform(-8.5, -1)])
    T = rnd.choice([rnd.uniform(0.2, 130.0), float(rnd.randint(1, 120)), rnd.randint(1, 240) / 2.0])
    n, ns, sw = brute(T, c)
    if abs(cf.skip_weight_periodic(T, c, cf.renewal_count(T, c)) - sw) > 1e-9: nb += 1
print(f"   mismatches outside the band: {nb}/300000")

print("\nend to end: one clean synthetic scenario, every material refresh_cycle / equipment service_life set to 1.000000001")
for seed in (11, 12):
    for T in (60.0, 42.5):
        scn = synth.make_scenario(seed, "RC", "office", "S", T, explicit_event_share=0.0, change_list_share=0.0)
        for row in scn.materials: row.refresh_cycle = 1.000000001
        for eq in scn.equipment: eq.service_life = 1.000000001
        ref = registry.run_all(scn)
        for detail in (False, True):
            got = engine.evaluate(scn, detail=detail)
            line = []
            for uid in ("B3-01", "B4-02", "X-02", "SUM-03", "X-07", "QA-01"):
                c = compare(ref[uid], got[uid], floor=1e-9 * abs(ref["SUM-03"]["value"]), ignore_missing=not detail)
                line.append(f"{uid}: max rel err {c.max_abs_rel_error:.3e}{' MISMATCH ' + str(c.mismatches[:1]) if c.mismatches else ''}")
            print(f"  seed {seed} T {T} detail={detail}: ref B3-01 {ref['B3-01']['value']:.6g} fast {got['B3-01']['value']:.6g} | ref SUM-03 {ref['SUM-03']['value']:.8g} fast {got['SUM-03']['value']:.8g}")
            print("     ", "; ".join(line))
print("\nsame with only ONE material row changed (seed 11, T 60)")
scn = synth.make_scenario(11, "RC", "office", "S", 60.0)
i = next(i for i, r in enumerate(scn.materials) if r.repair_rate and r.repair_rate > 0)
scn.materials[i].refresh_cycle = 1.000000001
ref = registry.run_all(scn); got = engine.evaluate(scn, detail=False)
print("  row", i, "B3-01 ref", repr(ref["B3-01"]["value"]), "fast", repr(got["B3-01"]["value"]), "rel diff", abs(ref["B3-01"]["value"] - got["B3-01"]["value"]) / abs(ref["B3-01"]["value"]))
print("  SUM-03 ref", repr(ref["SUM-03"]["value"]), "fast", repr(got["SUM-03"]["value"]), "rel diff", abs(ref["SUM-03"]["value"] - got["SUM-03"]["value"]) / abs(ref["SUM-03"]["value"]))
