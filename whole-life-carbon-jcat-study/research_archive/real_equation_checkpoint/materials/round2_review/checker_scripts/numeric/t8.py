from h import *
import re, collections
nan, inf = float("nan"), float("inf")
# (1) which reference leaves are absent in the totals mode
s = synth.make_scenario(101, "RC", "office", "S", 60.0); population.attach_baseline(s)
ref, full, tot = run3(s)
miss = collections.Counter(); present = collections.Counter(); extra = collections.Counter()
for uid in ref:
    fr, ft = flat(ref[uid]), flat(tot.get(uid, {}))
    for p in fr:
        pat = uid + ":" + re.sub(r"\[\d+\]", "[]", p)
        (present if p in ft else miss)[pat] += 1
    for p in ft:
        if p not in fr: extra[uid + ":" + p] += 1
print("leaf patterns absent in totals mode:"); 
for k, v in sorted(miss.items()): print("   ", k, v)
print("leaf patterns only in totals mode (not in the reference):", dict(extra))
print("units with no leaf at all in totals mode:", [u for u in ref if not flat(tot.get(u, {}))])
print("extra top-level keys in engine output:", [u for u in full if u not in ref], [u for u in tot if u not in ref])

# (2) details of a few NaN / inf single-field cases
def one(name, fn, variant_opts, T=60.0, units=("B5-01", "B6-03", "B2-01", "SUM-03", "QA-01", "X-06")):
    s = synth.make_scenario(79, "RC", "office", "S", T, n_materials=3, n_equipment=2, n_refrigerants=2, **variant_opts)
    fn(s)
    ref, full, tot = run3(s)
    print(f"[{name}]")
    for u in units:
        if isinstance(ref, Exception) or isinstance(full, Exception):
            print("    ref:", repr(ref)[:100], "| unified:", repr(full)[:100]); break
        a = {k: v for k, v in ref[u].items() if not k.startswith("_") and not isinstance(v, (list,)) or k == "violations"}
        b = {k: v for k, v in full[u].items() if not k.startswith("_") and not isinstance(v, (list,)) or k == "violations"}
        if diffs(a, b): print("    ", u, "ref", str(a)[:160], "| unified", str(b)[:160])
V2 = dict(profile_kind="CONSTANT", grid_kind="TABLE", composite_share=0.0, epd_share=0.0)
V0 = dict(profile_kind="LINEAR_TREND", grid_kind="LINEAR_DECLINE_TO_FLOOR", composite_share=0.0, epd_share=0.0)
one("grid.table[0]=inf", lambda s: s.operation.grid.table.__setitem__(0, inf), V2)
one("gas.slope=inf", lambda s: setattr(s.operation.gas, "slope", inf), V0)
one("gas.base=nan", lambda s: setattr(s.operation.gas, "base", nan), V0)
one("gas.table[0]=nan (TABLE kind)", lambda s: s.operation.gas.table.__setitem__(0, nan), dict(profile_kind="TABLE", grid_kind="TABLE"))
def f(s): next(iter(s.factors.values())).value = nan
one("first factor value=nan", f, V2)
one("construction_value=nan", lambda s: setattr(s.operation.grid, "construction_value", nan), V2)
one("unit_conversions[0].factor=nan", lambda s: setattr(s.unit_conversions[0], "factor", nan), V2)
