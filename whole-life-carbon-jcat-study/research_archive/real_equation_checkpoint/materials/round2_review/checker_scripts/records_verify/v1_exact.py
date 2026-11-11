from fractions import Fraction as F
import math
c = 1.000000001; EPS = 1e-9; one_minus = 1.0 - EPS
T = 60.0
print("c as exact fraction - 1 =", float(F(c) - 1), " (1-EPS) double - 1 =", float(F(one_minus) - 1))
prod = F(c) * F(one_minus)
print("exact c*(1-EPS) - 1 =", float(prod - 1))
# exact-arithmetic years (using the double constants but exact rational arithmetic) vs floating point
ex_years, fl_years = [], []
n = 1
while n * c < T * (1.0 - EPS):
    ex_years.append(max(1, math.ceil(F(n) * F(c) * F(one_minus))))
    fl_years.append(max(1, math.ceil((n * c) * (1.0 - EPS))))
    n += 1
print("events", len(fl_years), "| distinct years exact arithmetic:", len(set(ex_years)), "| distinct years floating point (reference loop):", len(set(fl_years)))
print("first events float years:", fl_years[:16]); print("first events exact years:", ex_years[:16])
# decimal semantics (c = 1.000000001 exactly, eps = 1e-9 exactly)
cd = F(1000000001, 10**9); ed = 1 - F(1, 10**9)
print("decimal semantics distinct years:", len({max(1, math.ceil(F(k) * cd * ed)) for k in range(1, len(fl_years) + 1)}))
