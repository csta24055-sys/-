"""NUM-1 own check: brute-force the loop definition vs closed form. No use of checker's helper."""
import sys, math
sys.dont_write_bytecode = True
from fractions import Fraction
from refcalc import base, registry
from fastcalc import closed_forms as cf, engine
import synth
from common.compare import compare
registry.load_all()

p = 1.000000001
print("period repr", repr(p), "hex", p.hex())
print("p*(1-1e-9) =", repr(p*(1.0-1e-9)), " == 1.0?", p*(1.0-1e-9) == 1.0)
print("exact rational p*(1-eps_double) - 1 =", float(Fraction(p)*Fraction(1.0-1e-9) - 1))
for T in (7.0, 30.0, 60.0):
    ev = base.periodic_events(T, p)
    yrs = [base.event_year(t) for t in ev]
    w = base.year_weights(T)
    loop = sum(w[y] for y in set(yrs))
    print(T, "n", len(ev), "distinct", len(set(yrs)), "years", yrs[:12], "loop", loop, "cf", cf.skip_weight_periodic(T, p, len(ev)))
    # exact arithmetic: where 'should' events fall under the definition in exact arithmetic (ceil(n*p*(1-1e-9)))
    exact = [max(1, math.ceil(Fraction(n)*Fraction(p)*(1-Fraction(1,10**9)))) for n in range(1, len(ev)+1)]
    print("   exact-rational years distinct:", len(set(exact)), exact[:12])

# neighbours
import struct
def nxt(x, k):
    for _ in range(abs(k)):
        x = math.nextafter(x, math.inf if k > 0 else -math.inf)
    return x
bad = []
for k in range(-50, 51):
    q = nxt(p, k)
    for T in (7.0, 30.0, 60.0, 99.9):
        ev = base.periodic_events(T, q)
        w = base.year_weights(T)
        loop = sum(w[y] for y in {base.event_year(t) for t in ev})
        c = cf.skip_weight_periodic(T, q, cf.renewal_count(T, q))
        if abs(loop - c) > 1e-9:
            bad.append((k, T, loop, c))
print("neighbour failures (ulps offset, T, loop, cf):", bad)

# wider scan: random periods in [1, 1+1e-8] and other integer-ish
import random
rng = random.Random(12345)
nbad = 0; ntot = 0; badper = set()
for _ in range(200000):
    q = 1.0 + rng.random() * 3e-9 if rng.random() < 0.5 else rng.choice([1,2,3,5,10]) * (1.0 + rng.uniform(-3e-9, 3e-9))
    T = rng.choice([7.0, 30.0, 60.0, 42.5, 99.9, 100.0])
    ev = base.periodic_events(T, q)
    w = base.year_weights(T)
    loop = sum(w[y] for y in {base.event_year(t) for t in ev})
    c = cf.skip_weight_periodic(T, q, cf.renewal_count(T, q))
    ntot += 1
    if abs(loop - c) > 1e-9:
        nbad += 1; badper.add(q)
print("random scan near integers: bad", nbad, "of", ntot, "distinct bad periods", sorted(badper)[:10], len(badper))

# scenario
s = synth.make_scenario(1, 'RC', 'office', 'S', 60.0, n_materials=12, n_equipment=6, n_refrigerants=4,
                        service_life_choices=[1.000000001], explicit_event_share=0.0, change_list_share=0.0)
print("periods in scenario: materials", sorted({m.refresh_cycle for m in s.materials}, key=lambda x: (x is None, x)), "equipment", sorted({e.service_life for e in s.equipment}, key=lambda x:(x is None,x)))
r = registry.run_all(s); f = engine.evaluate(s, detail=True); t = engine.evaluate(s, detail=False)
scale = abs(r["SUM-03"]["value"])
fails = []
for u in r:
    c = compare(r[u], f.get(u, {}), floor=1e-9*scale); cs = compare(r[u], t.get(u, {}), floor=1e-9*scale, ignore_missing=True)
    if not (c.within(1e-9) and not c.extra and cs.within(1e-9)):
        fails.append((u, c.worst_path, c.max_abs_rel_error, cs.max_abs_rel_error))
for x in fails: print("FAIL", x)
print("B3-01", r["B3-01"]["value"], f["B3-01"]["value"], t["B3-01"]["value"]); print("SUM-03", r["SUM-03"]["value"], f["SUM-03"]["value"])
print("SYS/QA flags ref:", {k: r[k].get("ok") for k in r if k.startswith(("SYS","QA"))})
