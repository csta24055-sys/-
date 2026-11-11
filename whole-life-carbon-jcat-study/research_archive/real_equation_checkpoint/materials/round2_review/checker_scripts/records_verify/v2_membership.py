"""REC-2: does the unit's value come from a shared table / shared parameterised function?  REC-6: do closed forms affect the unit's own outputs?"""
import copy, json, collections
import synth
from fastcalc import engine, closed_forms as cf
from refcalc import registry
from common.compare import compare, flatten
registry.load_all()

def scn0(seed=8):
    return synth.make_scenario(seed, "S", "office", "S", 60.0)

def tables_equal(a, b):
    return a.keys() == b.keys() and all(a[k] == b[k] for k in a)

# ---- X-13: change every reuse_rate; which tables / units change?
s1 = scn0(); s2 = scn0()
for r in s2.materials:
    if r.reuse_rate is not None: r.reuse_rate = min(1.0, r.reuse_rate * 0.5 + 0.3)
r1 = engine.evaluate(s1, detail=True); r2 = engine.evaluate(s2, detail=True)
changed = [u for u in r1 if not u.startswith("_") and flatten(r1[u]) != flatten(r2[u])]
print("X-13: tables identical after changing every reuse_rate:", tables_equal(r1["_tables"], r2["_tables"]), "| units whose output changed:", changed)
print("X-13 totals-mode output:", engine.evaluate(s1, detail=False)["X-13"])
# ---- A13-05: totals-mode output; is there a table named for it?
t = engine.evaluate(s1, detail=False)
print("A13-05 totals-mode output:", t["A13-05"], "| table names:", sorted(k for k in t["_tables"] if not k.startswith("CLASS")))
# ---- B1-01: final after aggregate, no refrigerant_fractions call
calls = [0]; orig = cf.refrigerant_fractions
def counting(*a, **k):
    calls[0] += 1; return orig(*a, **k)
cf.refrigerant_fractions = counting
A = engine.aggregate(s1, False)
ref = registry.run_all(s1)
print("B1-01: A.misc['b1_01'] after aggregate =", A.misc["b1_01"], "reference =", ref["B1-01"]["value"], "| refrigerant_fractions calls so far:", calls[0])
R = engine.finish(A, 60.0, False, None)
print("       after finish: refrigerant_fractions calls:", calls[0], "| B1-01 in _tables?:", [k for k in R["_tables"] if k.startswith("B1")], R["_tables"]["B1"].keys())
cf.refrigerant_fractions = orig
# break the charge-cycle function: does B1-01 notice?
cf.refrigerant_fractions = lambda *a, **k: tuple(x if not isinstance(x, float) else x * 2 for x in orig(*a, **k))
Rb = engine.evaluate(s1, detail=False)
print("       with refrigerant_fractions broken (leak x2): B1-01", Rb["B1-01"]["value"] == ref["B1-01"]["value"], "B1-02 equal:", abs(Rb["B1-02"]["value"] - ref["B1-02"]["value"]) < 1e-9 * abs(ref["B1-02"]["value"]))
cf.refrigerant_fractions = orig
# ---- SYS-03: depends on source_url (never looked at by the resolver); memo not used
s3 = scn0()
used_fid = next(r.factor_id for r in s3.materials if r.factor_id is not None and r.composition is None)
s3.factors[used_fid].source_url = ""
r3 = engine.evaluate(s3, detail=False); ref3 = registry.run_all(s3)
print("SYS-03 after clearing one source_url: unified ok", r3["SYS-03"]["ok"], r3["SYS-03"]["violations"][:2], "| ref ok", ref3["SYS-03"]["ok"],
      "| SYS-02 changed:", flatten(r3["SYS-02"]) != flatten(engine.evaluate(s1, detail=False)["SYS-02"]),
      "| value tables identical:", tables_equal(r3["_tables"], t["_tables"]))
print("QA-03 after the same change: unified", r3["QA-03"]["ok"], r3["QA-03"]["violations"][:2])
# ---- A5-01 table
print("A5-01 table:", t["_tables"]["A5-01"], "value", t["A5-01"])
# ---- totals-mode outputs of operation units
for u in ("B6-01", "B6-02", "B6-04", "B7-01", "B7-02", "B7-03", "X-06", "X-07", "B4-03", "X-13"):
    print("  totals-mode output", u, t[u])

# ---- REC-6: break closed forms, see which units still pass their own comparison
def failing(scn, detail):
    ref = registry.run_all(scn); got = engine.evaluate(scn, detail=detail)
    floor = 1e-9 * abs(ref["SUM-03"]["value"]); bad = []
    info = {}
    for uid in ref:
        c = compare(ref[uid], got.get(uid, {}), floor=floor, ignore_missing=not detail)
        info[uid] = (c.n_numeric, c.n_other)
        if not c.within(1e-9): bad.append(uid)
    return bad, info
param = synth.make_scenario(5, "RC", "office", "S", 60.0, profile_kind="LINEAR_TREND", grid_kind="LINEAR_DECLINE_TO_FLOOR")
print("\nREC-6 baseline (nothing broken): failing totals", failing(param, False)[0], "full", failing(param, True)[0])
o = cf.linear_weighted_sum
cf.linear_weighted_sum = lambda T, b, s: 1.5 * o(T, b, s)
for detail in (False, True):
    bad, info = failing(param, detail)
    print(f" linear_weighted_sum x1.5, detail={detail}: failing units {bad}")
    print("    numeric/other leaves compared:", {u: info[u] for u in ("B6-02", "B7-01", "B7-02", "B7-03", "B6-03", "B7-04")})
cf.linear_weighted_sum = o
o2 = cf.segment_moments
cf.segment_moments = lambda seg, T: tuple(1.5 * x for x in o2(seg, T))
for detail in (False, True):
    bad, info = failing(param, detail)
    print(f" segment_moments x1.5, detail={detail}: failing units {bad}")
    print("    numeric/other leaves compared:", {u: info[u] for u in ("X-06", "B6-04", "B6-01", "B6-03", "B2-01", "X-11")})
cf.segment_moments = o2
ex = json.load(open("/home/user/-/whole-life-carbon-jcat-study/09_APPROX_STUDY/04_VERIFICATION/unified_model_exactness.json"))
print("published units_without_output_in_totals_mode:", ex["units_without_output_in_totals_mode"])
for u in ("B6-01", "B6-02", "B6-04", "B7-01", "X-06", "A13-05", "QA-02", "QA-04", "B1-01"):
    print("  published", u, ex["units"][u])
