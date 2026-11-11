import json, collections, inspect
import synth
from synth import population
from fastcalc import engine
print(inspect.signature(population.standard_benchmark))
bm = population.standard_benchmark()
items = bm.items() if isinstance(bm, dict) else bm
for it in items:
    name, scn = it if isinstance(it, tuple) else (getattr(it.meta, "scenario_id", "?"), it)
    A = engine.aggregate(scn, False)
    n_rc = sum(1 for r in scn.materials if r.conversions)
    # distinct (factor, stage, unit) triples met by use() overall (memoised + per-row), replicated
    trip_row = set(); per_row = 0
    for r in scn.materials:
        if not r.conversions or r.quantity_unit is None: continue
        if r.composition is None and r.factor_id is not None:
            per_row += 1; trip_row.add((r.factor_id, "A1-A3", r.quantity_unit))
        if r.transport.delivery_factor_id is not None:
            per_row += 1; trip_row.add((r.transport.delivery_factor_id, "A4", r.quantity_unit))
        if r.installation_factor_id is not None:
            per_row += 1; trip_row.add((r.installation_factor_id, "A5", r.quantity_unit))
    print(name, "materials", len(scn.materials), "equipment", len(scn.equipment), "| factor_resolutions", A.stats["factor_resolutions"],
          "| unit_conversions_resolved", A.stats["unit_conversions_resolved"], "| rows with row conversions", n_rc,
          "| per-row (unmemoised) resolutions", per_row, "over distinct triples", len(trip_row), "| recipes", A.stats["recipes_computed"],
          "| factor records", len(scn.factors))
# M-GROUPS: row lines vs (period,key) entries on the mechanism scenario
scn = synth.make_scenario(5, "RC", "office", "S", 60.0, n_materials=400, n_equipment=120, n_refrigerants=10, profile_kind="LINEAR_TREND", grid_kind="LINEAR_DECLINE_TO_FLOOR")
class CD(dict):
    sets = 0
    def __setitem__(self, k, v):
        CD.sets += 1; dict.__setitem__(self, k, v)
oi = engine._Group.__init__
def pi(self):
    oi(self); self.u = CD()
engine._Group.__init__ = pi
A = engine.aggregate(scn, False)
engine._Group.__init__ = oi
entries = sum(len(g.u) for g in A.groups.values())
R = engine.finish(A, 60.0, False, None)
cnt = {c: engine.cf.renewal_count(60.0, c) for c in A.groups}
x08 = sum(len(A.groups[c].u) for c in A.groups if c is not None and cnt[c])
print("mechanism scenario: groups", len(A.groups), "| row lines added to period groups", CD.sets, "| (period,key) entries", entries, "| entries read by tot() for X-08 groups", x08,
      "| table_factor_products", R["_stats"]["table_factor_products"], "| distinct service-life values among rows:",
      len({r.refresh_cycle for r in scn.materials} | {e.service_life for e in scn.equipment}))
ex = json.load(open("/home/user/-/whole-life-carbon-jcat-study/09_APPROX_STUDY/04_VERIFICATION/unified_model_exactness.json"))
print("published year-table totals_only:", ex["mechanism_counts"]["year_table_inputs"]["totals_only"])
