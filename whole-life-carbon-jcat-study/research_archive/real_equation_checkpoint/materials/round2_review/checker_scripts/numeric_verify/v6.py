import sys, math, random
sys.dont_write_bytecode = True
from refcalc import base
from fastcalc import closed_forms as cf, engine
import synth
from refcalc import registry
registry.load_all()
p0 = 1.000000001
def loop(T, q):
    ev = base.periodic_events(T, q); w = base.year_weights(T)
    return sum(w[y] for y in {base.event_year(t) for t in ev}), len(ev)
Ts = [float(t) for t in range(2, 121)] + [7.5, 42.5, 59.999999, 99.9, 60.0000001, 30.25, 119.5]
bad = {}
q = p0
for _ in range(6000): q = math.nextafter(q, 0.0)
tot = 0
for k in range(-6000, 6001):
    for T in Ts:
        l, n = loop(T, q); c = cf.skip_weight_periodic(T, q, cf.renewal_count(T, q)); tot += 1
        if n != cf.renewal_count(T, q) or abs(l - c) > 1e-9: bad.setdefault(k, []).append(T)
    q = math.nextafter(q, math.inf)
print("pairs scanned", tot, "bad ulp offsets:", {k: len(v) for k, v in bad.items()})
# general random scan, periods in [1, 3] and integers*(1+-small), includes multiples
rng = random.Random(7); nb = 0; N = 300000; ex = []
for _ in range(N):
    m = rng.choice([1, 1, 1, 2, 3, 5])
    q = m * (1.0 + rng.choice([0, 1e-9, -1e-9, 2e-9, 1e-9 + rng.uniform(-3e-16, 3e-16) * rng.randint(1, 50), rng.uniform(0, 2e-9)]))
    T = rng.choice(Ts)
    l, n = loop(T, q); c = cf.skip_weight_periodic(T, q, cf.renewal_count(T, q))
    if abs(l - c) > 1e-9: nb += 1; ex.append((T, q.hex()))
print("random scan bad:", nb, "of", N, "distinct periods:", sorted({e[1] for e in ex}), "p0 hex", p0.hex())
# sweep
s = synth.make_scenario(1, 'RC', 'office', 'S', 60.0, n_materials=12, n_equipment=6, n_refrigerants=4,
                        service_life_choices=[p0], explicit_event_share=0.0, change_list_share=0.0)
sw = engine.sweep(s, [30.0, 60.0])
import copy
for T in (30.0, 60.0):
    s2 = copy.deepcopy(s); s2.boundary.study_period = T
    r = registry.run_all(s2, ids=["B3-01", "SUM-03"])
    print("sweep T", T, "B3-01 ref", r["B3-01"]["value"], "sweep", sw[T]["B3-01"]["value"], "| SUM-03 ref", r["SUM-03"]["value"], "sweep", sw[T]["SUM-03"]["value"])
# one material row only
s = synth.make_scenario(1, 'RC', 'office', 'S', 60.0, n_materials=12, n_equipment=6, n_refrigerants=4)
rows = [m for m in s.materials if m.repair_rate and m.repair_rate > 0]
print("rows with repair:", len(rows), "of", len(s.materials))
rows[0].refresh_cycle = p0
r = registry.run_all(s); f = engine.evaluate(s)
print("one row: B3-01 ref", r["B3-01"]["value"], "unified", f["B3-01"]["value"], "rel", (f["B3-01"]["value"] - r["B3-01"]["value"]) / r["B3-01"]["value"], "SUM-03 rel", (f["SUM-03"]["value"] - r["SUM-03"]["value"]) / r["SUM-03"]["value"])
# self-consistency of the unified full output
s = synth.make_scenario(1, 'RC', 'office', 'S', 60.0, n_materials=12, n_equipment=6, n_refrigerants=4,
                        service_life_choices=[p0], explicit_event_share=0.0, change_list_share=0.0)
f = engine.evaluate(s)
print("unified: B3-01.value", f["B3-01"]["value"], "sum(by_year)", sum(f["B3-01"]["by_year"]), "X-07.value", f["X-07"]["value"], "SUM-03", f["SUM-03"]["value"], "QA-01", f["QA-01"])
