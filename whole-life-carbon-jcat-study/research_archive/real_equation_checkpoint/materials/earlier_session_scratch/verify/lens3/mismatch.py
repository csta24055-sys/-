"""Scenarios outside the verified population: does the unified model still equal the reference?"""
import copy
import synth
from fastcalc import engine
from refcalc import registry
from synth import population, model
registry.load_all()

def rel(a, b):
    return (a - b) / b if b else float("nan")

def show(tag, scn, keys=("SUM-03", "B6-03", "B7-04", "B2-01", "X-11")):
    ref = registry.run_all(scn)
    engine.clear_baseline_cache()
    full = engine.evaluate(scn, detail=True)
    engine.clear_baseline_cache()
    summ = engine.evaluate(scn, detail=False)
    print(f"[{tag}]")
    for k in keys:
        r, f, s = ref[k]["value"], full[k]["value"], summ[k]["value"]
        print(f"   {k:7s} ref={r:.6f} fast_full={f:.6f} fast_totals={s:.6f} rel(full)={rel(f, r):+.3e} rel(totals)={rel(s, r):+.3e}")
    print("   X-06 matches_table ref:", ref["X-06"].get("matches_table"), "fast_full:", full["X-06"].get("matches_table"), "fast_totals X-06:", summ["X-06"])
    print("   X-07 value (sum of yearly series) fast_full:", full["X-07"]["value"], "vs fast_full SUM-03:", full["SUM-03"]["value"], "ref X-07:", ref["X-07"]["value"])
    print("   SYS-01 ok / SYS-02 ok / QA-01 ok (ref):", ref["SYS-01"]["ok"], ref["SYS-02"]["ok"], ref["QA-01"]["ok"], "(fast):", full["SYS-01"]["ok"], full["SYS-02"]["ok"], full["QA-01"]["ok"])

# --- (1) annual profile: descriptor says CONSTANT, table (authoritative per synth/model.py) has one edited year
base = synth.make_scenario(4242, "RC", "office", "S", 60.0, profile_kind="CONSTANT", grid_kind="CONSTANT")
show("clean constant scenario (control)", base)
s1 = copy.deepcopy(base)
print("gas profile kind:", s1.operation.gas.kind, "base:", s1.operation.gas.base, "table[10]:", s1.operation.gas.table[10])
s1.operation.gas.table[10] *= 3.0          # user overrides one year in the authoritative table
show("gas table year 11 edited, descriptor unchanged", s1)

# --- (2) water profile LINEAR_TREND with an edited table year
s2 = synth.make_scenario(4243, "S", "school", "S", 50.0, profile_kind="LINEAR_TREND", grid_kind="LINEAR_DECLINE_TO_FLOOR")
show("clean linear scenario (control)", s2)
s2b = copy.deepcopy(s2)
s2b.water_waste.water.table[5] *= 2.0
show("water table year 6 edited, descriptor unchanged", s2b)

# --- (3) grid: descriptor parametric, table edited. Reference uses the descriptor (X-06), engine uses the TABLE when demand is not constant
s3 = copy.deepcopy(s2)
g = s3.operation.grid
print("grid kind:", g.kind, "electricity kind:", s3.operation.electricity.kind)
g.table[7] *= 1.5
show("grid table year 8 edited (demand LINEAR_TREND)", s3)
s4 = copy.deepcopy(base)
s4.operation.grid.table[7] *= 1.5
show("grid table year 8 edited (demand CONSTANT)", s4)
