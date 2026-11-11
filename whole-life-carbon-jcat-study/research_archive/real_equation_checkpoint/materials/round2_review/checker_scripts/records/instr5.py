"""Row-wise factor products for the pseudo-key tables (REFRIGERANT, GRID) in totals mode; passes over refrigerant rows in a sweep."""
import sys, collections
import synth
from fastcalc import engine
where = collections.Counter()
class CF(float):
    def __mul__(self, o):
        f = sys._getframe(1); where[(f.f_code.co_name, f.f_lineno)] += 1
        return float(self) * float(o)
    __rmul__ = __mul__
scn = synth.make_scenario(5, "RC", "office", "S", 60.0, n_materials=400, n_equipment=120, n_refrigerants=10,
                          profile_kind="LINEAR_TREND", grid_kind="LINEAR_DECLINE_TO_FLOOR")
for d in scn.refrigerants: d.gwp = CF(d.gwp)
scn.operation.grid.construction_value = CF(scn.operation.grid.construction_value)
A = engine.aggregate(scn, False)
print("aggregate (totals): products with a device GWP or the construction grid factor:", dict(where))
where.clear()
engine.finish(A, 60.0, False, None)
print("finish (totals):", dict(where))
where.clear()
class L(list):
    iters = 0
    def __iter__(self):
        L.iters += 1; return list.__iter__(self)
A.devices = L(A.devices)
engine.sweep  # noqa
for T in (10.0, 30.0, 42.5, 50.0, 60.0, 75.0, 99.9, 100.0, 120.0):
    engine.finish(A, T, False, None, _compare=False)
print("9 study periods from one aggregate: passes over the refrigerant devices in finish:", L.iters, "; GWP products:", sum(where.values()))
