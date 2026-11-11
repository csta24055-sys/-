# Own check of RED-2 (negative / NaN numeric inputs), with ref-vs-fast agreement on each case
import copy, math
import synth
from refcalc import registry
from fastcalc import engine
from common.compare import compare
registry.load_all()
nan = float("nan")

def mk(seed=11, st="RC", use="office", T=60.0, **o):
    opts = dict(n_materials=12, n_equipment=6, n_refrigerants=4); opts.update(o)
    return synth.make_scenario(seed, st, use, "S", T, **opts)

def both(s):
    try:
        r = registry.run_all(s)
    except Exception as e:
        r = e
    try:
        f = engine.evaluate(s, detail=True)
    except Exception as e:
        f = e
    if isinstance(r, Exception) or isinstance(f, Exception):
        agree = f"ref {'RAISED '+type(r).__name__ if isinstance(r, Exception) else 'ok'} / fast {'RAISED '+type(f).__name__ if isinstance(f, Exception) else 'ok'}"
        return (None if isinstance(r, Exception) else r), agree
    c = compare(r, f)
    return r, f"ref-vs-fast within1e-9={c.within(1e-9)} maxrel={c.max_abs_rel_error:.2e} mism={len(c.mismatches)} missing={len(c.missing)} first={c.mismatches[:2]}"

def line(tag, r, agree, keys=()):
    if r is None:
        print(f"  {tag}: {agree}"); return
    g = lambda u, k: r[u].get(k)
    print(f"  {tag}: SUM-03 {r['SUM-03']['value']!r} complete {r['SUM-03']['complete']} inc {r['X-02']['incomplete_units']} gates SYS-01/02/03 {g('SYS-01','ok')}/{g('SYS-02','ok')}/{g('SYS-03','ok')} QA-01/03 {g('QA-01','ok')}/{g('QA-03','ok')} | " + " ".join(f"{u}.{k}={r[u].get(k)!r}" if k != 'stage' else f"{u}={r['X-02']['by_stage'].get(u)!r}" for u, k in keys) + " | " + agree)

for seed, st, use in ((11, "RC", "office"), (305, "S", "hospital")):
    print(f"=== seed {seed} {st} {use}")
    print("(a) annual quantities")
    s = mk(seed, st, use, profile_kind="CONSTANT")
    r0, a = both(s); line("clean", r0, a, (("B6-03", "value"), ("B7-04", "value"), ("B6-02", "n_skipped")))
    s2 = copy.deepcopy(s)
    for p in (s2.operation.gas, s2.water_waste.water):
        p.base = -abs(p.base); p.table = [p.base] * len(p.table)
    r, a = both(s2); line("gas & water base negative", r, a, (("B6-03", "value"), ("B7-04", "value"), ("B6-02", "n_skipped"), ("B7-01", "n_skipped")))
    s3 = copy.deepcopy(s); s3.operation.gas.base = nan; s3.operation.gas.table = [nan] * len(s3.operation.gas.table)
    r, a = both(s3); line("gas base NaN (table too)", r, a, (("B6-02", "n_skipped"),))
    s3 = copy.deepcopy(s); s3.operation.gas.base = None; s3.operation.gas.table[5] = None
    r, a = both(s3); line("gas base None + table[5] None", r, a)
    s4 = copy.deepcopy(s); s4.operation.electricity.base = -abs(s4.operation.electricity.base); s4.operation.electricity.table = [s4.operation.electricity.base] * len(s4.operation.electricity.table)
    r, a = both(s4); line("electricity demand negative", r, a, (("B6-04", "computed"), ("B6-01", "computed")))
    if r: print("     B6-01 total clean", sum(r0["B6-01"]["by_year"]), "->", sum(r["B6-01"]["by_year"]))
    print("(b) grid")
    s = mk(seed, st, use, grid_kind="CONSTANT")
    r0, a = both(s); line("clean", r0, a, (("B6-03", "value"), ("B2-01", "value"), ("A5-01", "value")))
    for label, v in (("grid start -0.4", -0.4), ("grid start NaN", nan)):
        s2 = copy.deepcopy(s); s2.operation.grid.start = v; s2.operation.grid.table = [v] * len(s2.operation.grid.table)
        r, a = both(s2); line(label, r, a, (("B6-03", "value"), ("B2-01", "value"), ("B2-01", "computed")))
    for label, v in (("construction_value -1", -1.0), ("construction_value NaN", nan), ("construction_value None", None)):
        s2 = copy.deepcopy(s); s2.operation.grid.construction_value = v
        r, a = both(s2); line(label, r, a, (("A5-01", "value"), ("A5-01", "computed")))
    print("(c) factor value")
    s = mk(seed, st, use, unit_variety=True)
    r0, a = both(s); line("clean", r0, a, (("A1-A3", "stage"),))
    fid = next(m.factor_id for m in s.materials if m.factor_id and m.epd is None and m.composition is None)
    for label, v in (("value NaN", nan), ("value -5", -5.0), ("value None", None), ("value inf", float("inf"))):
        s2 = copy.deepcopy(s); s2.factors[fid].value = v
        r, a = both(s2); line(f"{fid} {label}", r, a, (("A1-A3", "stage"),))
    print("   negative factor values in the clean generated catalogue:", sorted((k, f.value, f.stages) for k, f in s.factors.items() if not f.value >= 0)[:6])
    print("(d) row conversion")
    idx = [i for i, m in enumerate(s.materials) if m.conversions and r0["A13-01"]["by_item"][i] > 0]
    if idx:
        i = idx[0]
        for label, mult in (("negated", -1.0), ("NaN", nan), ("zero", 0.0)):
            s2 = copy.deepcopy(s)
            for c in s2.materials[i].conversions: c.factor = c.factor * mult if mult == mult else nan
            r, a = both(s2); line(f"row {i} conversion {label}", r, a, (("A13-01", "n_skipped"),))
            if r: print("     A13-01.by_item", r0["A13-01"]["by_item"][i], "->", r["A13-01"]["by_item"][i])
