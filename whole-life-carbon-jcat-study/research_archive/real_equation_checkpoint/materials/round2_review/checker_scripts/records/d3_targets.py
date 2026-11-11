import math
from fastcalc import closed_forms as cf
from refcalc import base
def bad(T, c):
    ev = base.periodic_events(T, c); w = base.year_weights(T)
    S = {base.event_year(t) for t in ev}
    return abs(cf.skip_weight_periodic(T, c, cf.renewal_count(T, c)) - sum(w[y] for y in S)) > 1e-9
found = set(); n = 0
Ts = [1.5, 7.0, 10.0, 12.3, 30.0, 42.5, 55.5, 59.999999, 60.0, 62.5, 99.9, 100.0, 120.0]
for m in list(range(1, 41)) + [1 / k for k in range(2, 21)] + [k / 10 for k in range(1, 100)]:
    for f in (1 + 1e-9, 1 - 1e-9, 1 / (1 - 1e-9), 1 / (1 + 1e-9), 1.0, 1 + 2e-9, 1 + 5e-10):
        c0 = m * f
        cands = [c0, float(repr(round(c0, 12)))]
        for base_c in cands:
            c = base_c
            for _ in range(4): c = math.nextafter(c, 0)
            for _ in range(9):
                for T in Ts:
                    n += 1
                    if bad(T, c): found.add(c)
                c = math.nextafter(c, 1e9)
print(n, "cases; failing periods:", sorted(found))
