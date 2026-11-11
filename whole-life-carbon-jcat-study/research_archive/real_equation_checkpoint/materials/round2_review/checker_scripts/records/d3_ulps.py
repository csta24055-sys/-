import math
from fastcalc import closed_forms as cf
from refcalc import base
def bad(T, c):
    ev = base.periodic_events(T, c); w = base.year_weights(T)
    S = {base.event_year(t) for t in ev}
    return abs(cf.skip_weight_periodic(T, c, cf.renewal_count(T, c)) - sum(w[y] for y in S)) > 1e-9
c0 = 1.000000001
c = c0
for _ in range(40): c = math.nextafter(c, 0)
out = []
for k in range(-40, 41):
    out.append((k, bad(60.0, c), bad(42.5, c), bad(100.0, c)))
    c = math.nextafter(c, 2)
print("ulps from 1.000000001 where the closed form differs from the loop (T=60, 42.5, 100):")
print([k for k, a, b, d in out if a], [k for k, a, b, d in out if b], [k for k, a, b, d in out if d])
print("ulp of 1.0 =", math.ulp(1.0))
