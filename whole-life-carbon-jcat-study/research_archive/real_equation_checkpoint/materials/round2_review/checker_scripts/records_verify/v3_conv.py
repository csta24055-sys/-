import collections, sys
import synth
from synth import model
from fastcalc import engine
scn = synth.make_scenario(5, "RC", "office", "S", 60.0, n_materials=400, n_equipment=120, n_refrigerants=10, profile_kind="LINEAR_TREND", grid_kind="LINEAR_DECLINE_TO_FLOOR")
pairs = collections.Counter(); orig = model.conversion_factor
def cc(table, u, v, *a, **k):
    pairs[(sys._getframe(1).f_code.co_name, u, v)] += 1
    return orig(table, u, v, *a, **k)
model.conversion_factor = cc
A = engine.aggregate(scn, False)
model.conversion_factor = orig
print(dict(pairs))
print("identity calls:", sum(n for (f, u, v), n in pairs.items() if u == v), "non-identity:", sum(n for (f, u, v), n in pairs.items() if u != v),
      "distinct non-identity pairs:", len({(u, v) for (f, u, v), n in pairs.items() if u != v}))
# how often does conv() return early (identity or row conversion) without counting?
