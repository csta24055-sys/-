"""Further experiments on memberships and on what the per-unit exactness check can detect."""
import copy, collections, sys
import synth
from fastcalc import engine, closed_forms as cf
from refcalc import registry
from common.compare import compare
registry.load_all()
mk = lambda **o: synth.make_scenario(5, "RC", "office", "S", 60.0, n_materials=400, n_equipment=120, n_refrigerants=10, **o)
scn = mk(profile_kind="LINEAR_TREND", grid_kind="LINEAR_DECLINE_TO_FLOOR")
ref = registry.run_all(scn)
tot_ = engine.evaluate(scn, detail=False)

print("== 1. totals-mode output of each unit: keys, and whether any numeric (non-count) value is present")
novalue = []
for uid in sorted(ref):
    r = tot_.get(uid, {})
    keys = sorted(r)
    if "value" not in r and not any(isinstance(v, (float, dict, list)) and v for v in r.values()):
        novalue.append((uid, keys))
for uid, keys in novalue: print("   no value in totals mode:", uid, keys, "| reference keys:", sorted(k for k in ref[uid] if not k.startswith("_")))

print("\n== 2. group tables: entries multiplied for X-08 / B4-02 versus row lines")
A = engine.aggregate(scn, False)
n_entries = sum(len(g.u) for c, g in A.groups.items() if c is not None and cf.renewal_count(60.0, c))
all_entries = sum(len(g.u) for g in A.groups.values())
# row lines: count them by re-running aggregate with a counting _Group.u dict
class CD(dict):
    adds = 0
    def __setitem__(self, k, v):
        CD.adds += 1; dict.__setitem__(self, k, v)
orig_init = engine._Group.__init__
def init(self):
    orig_init(self); self.u = CD()
engine._Group.__init__ = init
engine.aggregate(scn, False)
engine._Group.__init__ = orig_init
print(f"   row lines added to the period groups: {CD.adds}; distinct (period, factor key) entries: {all_entries}; entries in groups with >=1 renewal: {n_entries}")
print(f"   groups {len(A.groups)}; rows {len(scn.materials) + len(scn.equipment)}; entries in the unit tables (_tables): {sum(len(t) for t in tot_['_tables'].values())}")
print("   table_factor_products reported:", tot_["_stats"]["table_factor_products"])
lives = collections.Counter([r.refresh_cycle for r in scn.materials] + [e.service_life for e in scn.equipment])
print("   distinct refresh_cycle/service_life values:", len(lives), "sample:", list(lives.items())[:8])

print("\n== 3. B1-01 is final after aggregate(), before any charge-cycle function runs")
called = [0]; o = cf.refrigerant_fractions
def spy(*a):
    called[0] += 1; return o(*a)
cf.refrigerant_fractions = spy
A = engine.aggregate(scn, False)
print("   A.misc['b1_01'] =", A.misc["b1_01"], "reference B1-01 =", ref["B1-01"]["value"], "refrigerant_fractions calls so far:", called[0])
cf.refrigerant_fractions = o

print("\n== 4. X-13 is not connected to any table: change every reuse_rate and compare tables")
s2 = copy.deepcopy(scn)
for r in s2.materials: r.reuse_rate = 0.123
a, b = engine.evaluate(scn, detail=True), engine.evaluate(s2, detail=True)
same_tables = a["_tables"] == b["_tables"]
changed = [u for u in ref if compare(a[u], b[u]).max_abs_rel_error > 0 or compare(a[u], b[u]).mismatches]
print("   tables identical:", same_tables, "| units whose output changed:", changed)

print("\n== 5. A5-01 table and the pseudo keys")
print("   _tables['A5-01'] =", tot_["_tables"]["A5-01"], " kWh*grid.construction_value =", scn.construction.electricity_kwh * scn.operation.grid.construction_value)
print("   _tables['B1'] =", tot_["_tables"]["B1"], " _tables['B2-01'] =", tot_["_tables"]["B2-01"], " _tables['B6-01'] =", tot_["_tables"]["B6-01"])

print("\n== 6. what the per-unit comparison detects when a closed form is deliberately broken")
def run_cmp(label, units):
    out = []
    for detail in (True, False):
        got = engine.evaluate(scn, detail=detail)
        for uid in units:
            c = compare(ref[uid], got[uid], floor=1e-9 * abs(ref["SUM-03"]["value"]), ignore_missing=not detail)
            out.append((uid, "full" if detail else "totals", "FAIL" if not c.within(1e-9) else "pass", c.n_numeric))
    print("  ", label)
    for uid in units:
        print("      ", uid, [(m, r, n) for u, m, r, n in out if u == uid])
o1 = cf.linear_weighted_sum
cf.linear_weighted_sum = lambda T, b, s: 1.5 * o1(T, b, s)
run_cmp("linear_weighted_sum x1.5 (the closed form named in the titles of B6-02, B7-01, B7-02, B7-03):", ["B6-02", "B7-01", "B7-02", "B7-03", "B7-04", "B6-03"])
cf.linear_weighted_sum = o1
o2 = cf.segment_moments
cf.segment_moments = lambda seg, T: tuple(1.5 * x for x in o2(seg, T))
run_cmp("segment_moments x1.5 (the closed form named in the titles of X-06, B6-01, B6-04):", ["X-06", "B6-04", "B6-01", "B6-03", "B2-01", "X-11"])
cf.segment_moments = o2
