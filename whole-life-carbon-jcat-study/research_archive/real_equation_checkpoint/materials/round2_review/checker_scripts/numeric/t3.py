from fuzzlib import *
from refcalc import base
for seed in (311, 329, 368):
    s, T, log = build(seed)
    cyc = sorted({r.refresh_cycle for r in s.materials if base.positive(r.refresh_cycle)} | {e.service_life for e in s.equipment if base.positive(e.service_life) and e.replacement_event_list is None})
    print(seed, T, log)
    for c in cyc:
        ev = base.periodic_events(T, c); n = len(ev); w = base.year_weights(T); skip = {base.event_year(t) for t in ev}
        ry = sum(w[y] for y in range(1, len(w)) if y not in skip)
        ey = T - cf.skip_weight_periodic(T, c, cf.renewal_count(T, c)) if n else T
        if abs(ry - ey) > 1e-9: print("   cycle", repr(c), "n", n, "ref years", ry, "engine years", ey, "distinct", len(skip))
