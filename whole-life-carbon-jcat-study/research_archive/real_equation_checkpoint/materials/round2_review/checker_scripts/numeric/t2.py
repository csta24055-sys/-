from fuzzlib import *
s, T, log = build(365)
print(T, log)
print("material cycles", sorted({r.refresh_cycle for r in s.materials}, key=lambda x: (x is None, x)))
print("equip lives", [(e.service_life, e.replacement_event_list, e.repair_rate) for e in s.equipment])
ref, full, tot = run3(s)
print(ref["B3-01"]["value"], full["B3-01"]["value"], tot["B3-01"]["value"])
# by-year comparison
for y, (a, b) in enumerate(zip(ref["B3-01"]["by_year"], full["B3-01"]["by_year"])):
    if abs(a - b) > 1e-9 * max(abs(a), abs(b), 1e-30): print("year", y, a, b)
# isolate: which period
from refcalc import base
for c in sorted({r.refresh_cycle for r in s.materials if r.refresh_cycle} | {e.service_life for e in s.equipment if e.service_life}):
    ev = base.periodic_events(T, c)
    n = len(ev)
    w = base.year_weights(T)
    skip = {base.event_year(t) for t in ev}
    ref_years = sum(w[y] for y in range(1, len(w)) if y not in skip)
    eng_years = T - cf.skip_weight_periodic(T, c, cf.renewal_count(T, c)) if n else T
    if abs(ref_years - eng_years) > 1e-9: print("cycle", repr(c), "n", n, "ref years", ref_years, "engine years", eng_years, "distinct years", len(skip), "last", max(skip) if skip else None)
