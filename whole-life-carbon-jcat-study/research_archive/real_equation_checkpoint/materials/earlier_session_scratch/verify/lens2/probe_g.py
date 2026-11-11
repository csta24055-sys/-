import sys, os, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe import *
OPT = {"generic_stage_check": True}
s0 = base(composite_share=0.0, epd_share=0.0)
ref0 = registry.run_all(s0)

def run(label, mut, units=None, opts=None, extra=None, src=None):
    s = copy.deepcopy(src or s0); mut(s)
    o = dict(OPT); o.update(opts or {})
    ref, me, bad = diff(s, opts=o, label=label, show=False, units=units)
    print(f"[{label}] diff={bad}")
    if extra and ref is not None and me is not None:
        extra(s, ref, me)
    return s, ref, me

b = s0.boundary
print("boundary", b.study_period, b.replacement_cycle, b.reconstruction_scenario, b.reconstruction_scope_fraction, b.included_lifecycle_stages, b.functional_unit, b.results_gas_scope)
def bd(**kw):
    def f(s):
        for k, v in kw.items():
            setattr(s.boundary, k, v)
    return f
def b5(s, r, m):
    print("   ref B5", {k: (v if not isinstance(v, list) else [(i, x) for i, x in enumerate(v) if x]) for k, v in r["B5-01"].items()})
    print("   mine B5", {k: (v if not isinstance(v, list) else [(i, x) for i, x in enumerate(v) if x]) for k, v in m["B5-01"].items()})
U = ["B5-01", "X-02", "SUM-01", "SUM-02", "SUM-03", "SUM-05", "SUM-07"]
run("REBUILD cycle 25 phi 1", bd(reconstruction_scenario="REBUILD_IDENTICAL", replacement_cycle=25.0, reconstruction_scope_fraction=1.0), units=U, extra=b5)
run("MAJOR_REFURB cycle 30 phi 0.4", bd(reconstruction_scenario="MAJOR_REFURBISHMENT", replacement_cycle=30.0, reconstruction_scope_fraction=0.4), units=U, extra=b5)
run("NONE with cycle 25", bd(reconstruction_scenario="NONE", replacement_cycle=25.0, reconstruction_scope_fraction=1.0), units=U, extra=b5)
run("REBUILD with cycle None", bd(reconstruction_scenario="REBUILD_IDENTICAL", replacement_cycle=None, reconstruction_scope_fraction=1.0), units=U, extra=b5)
run("REBUILD cycle 25 phi 1.7 (out of range)", bd(reconstruction_scenario="REBUILD_IDENTICAL", replacement_cycle=25.0, reconstruction_scope_fraction=1.7), units=U, extra=b5)
run("REBUILD cycle 25, stages subset (no C, no A5)", bd(reconstruction_scenario="REBUILD_IDENTICAL", replacement_cycle=25.0, reconstruction_scope_fraction=1.0, included_lifecycle_stages=["A1-A3", "A4", "B5"]), units=U, extra=lambda s, r, m: (b5(s, r, m), print("   ref X-02", r["X-02"]["by_stage"], "SUM-03", r["SUM-03"])))
run("REBUILD cycle 60 (== T)", bd(reconstruction_scenario="REBUILD_IDENTICAL", replacement_cycle=60.0, reconstruction_scope_fraction=1.0), units=U, extra=b5)
run("scenario unknown 'FOO' cycle 25", bd(reconstruction_scenario="FOO", replacement_cycle=25.0, reconstruction_scope_fraction=1.0), units=U, extra=b5)

# stage subsets: B6 without B2
def st(s, r, m):
    print("   ref by_stage", r["X-02"]["by_stage"])
    print("   ref B6-03", r["B6-03"]["value"], "B2-01", r["B2-01"]["value"], "SUM-01/02/03", r["SUM-01"]["value"], r["SUM-02"]["value"], r["SUM-03"]["value"], "SUM-07", r["SUM-07"])
run("stages [A1-A3, A4, A5, B6] (B2 excluded)", bd(included_lifecycle_stages=["A1-A3", "A4", "A5", "B6"]), units=U, extra=st)
run("stages [B2] only", bd(included_lifecycle_stages=["B2"]), units=U, extra=st)
run("stages [] empty", bd(included_lifecycle_stages=[]), units=U, extra=st)
run("stages unordered + duplicate + unknown", bd(included_lifecycle_stages=["C4", "A1-A3", "A1-A3", "D"]), units=U, extra=st)
run("gas scope CO2_ONLY", bd(results_gas_scope="CO2_ONLY"), extra=lambda s, r, m: print("   ref SUM-03", r["SUM-03"]["value"], "base", ref0["SUM-03"]["value"], "X-05", r["X-05"].get("value"), "B1 stage", r["X-02"]["by_stage"]["B1"]))
# SUM-05
def p(**kw):
    def f(s):
        for k, v in kw.items():
            setattr(s.project, k, v)
    return f
run("gfa None", p(gross_floor_area=None), units=U, extra=lambda s, r, m: print("   ref SUM-05", r["SUM-05"], "mine", m["SUM-05"]))
run("gfa 0", p(gross_floor_area=0.0), units=U, extra=lambda s, r, m: print("   ref SUM-05", r["SUM-05"], "mine", m["SUM-05"]))
run("functional_unit WHOLE_BUILDING", bd(functional_unit="WHOLE_BUILDING"), units=U, extra=lambda s, r, m: print("   ref SUM-05", r["SUM-05"], "mine", m["SUM-05"]))
# SUM-07 with zero total
def zero(s):
    s.boundary.included_lifecycle_stages = ["B5"]
run("only B5 included (total 0)", zero, units=U, extra=lambda s, r, m: print("   ref SUM-07", r["SUM-07"], "mine", m["SUM-07"], "SUM-05", r["SUM-05"]))
