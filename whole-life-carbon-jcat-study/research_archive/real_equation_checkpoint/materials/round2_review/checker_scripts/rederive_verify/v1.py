# Own check of RED-1 (stage-subset completeness) and RED-3 (invalid periods)
import copy, math
import synth
from refcalc import registry
from fastcalc import engine
registry.load_all()

def mk(seed, struct, use, T=60.0, **o):
    opts = dict(n_materials=12, n_equipment=6, n_refrigerants=4); opts.update(o)
    return synth.make_scenario(seed, struct, use, "S", T, **opts)

def show(tag, s):
    r = registry.run_all(s)
    f = engine.evaluate(s, detail=True)
    print(f"  {tag}: SUM-03 ref {r['SUM-03']['value']:.4f} fast {f['SUM-03']['value']:.4f} | complete ref {r['SUM-03']['complete']} fast {f['SUM-03']['complete']} | incomplete_units {r['X-02']['incomplete_units']} fast {f['X-02']['incomplete_units']}"
          f" | A13-01.n_skipped {r['A13-01']['n_skipped']} X-01.n_skipped {r['X-01']['n_skipped']} B3-01.n_skipped {r['B3-01']['n_skipped']} B5.computed {r['B5-01']['computed']}"
          f" | gates SYS-01 {r['SYS-01']['ok']} SYS-02 {r['SYS-02']['ok']} SYS-03 {r['SYS-03']['ok']} QA-01 {r['QA-01']['ok']} QA-02 {r['QA-02']['ok']} QA-03 {r['QA-03']['ok']} C-05 {r['C-05']['ok']}")
    return r

print("== RED-1: exact scenario of the finding (seed 11 RC office) and an unrelated one (seed 77 W school) ==")
for seed, st, use in ((11, "RC", "office"), (77, "W", "school")):
    for sub in (["B3"], ["B5"], ["B3", "B5"], ["B4"], ["A1-A3", "B3"], None):
        kw = dict(replacement_cycle=25.0, reconstruction_scenario="REBUILD_IDENTICAL")
        if sub is not None: kw["included_stages"] = sub
        s = mk(seed, st, use, **kw)
        print(seed, st, sub)
        r0 = show("clean ", s)
        for variant in ("none", "neg", "factor_only"):
            s2 = copy.deepcopy(s)
            order = sorted(range(len(s2.materials)), key=lambda i: -(r0["A13-01"]["by_item"][i] + r0["A13-03"]["by_item"][i]))
            if variant == "none":
                for i in order[:3]: s2.materials[i].quantity = None
                s2.equipment[0].factor_id = "F-NOT-IN-TABLE"
            elif variant == "neg":
                for i in order[:3]: s2.materials[i].quantity = -abs(s2.materials[i].quantity)
            else:
                # a single defect of a kind B-17 names: factor without a usage licence
                fid = s2.materials[order[0]].factor_id
                if fid is None: fid = s2.materials[order[1]].factor_id
                s2.factors[fid].licence_status = "RESTRICTED"
            show("defect/" + variant, s2)

print("\n== RED-3: invalid periods ==")
for seed, st, use in ((11, "RC", "office"), (77, "W", "school")):
    s = mk(seed, st, use, replacement_cycle=25.0, reconstruction_scenario="REBUILD_IDENTICAL")
    r0 = show("clean", s)
    print("   stages", {k: round(v, 2) for k, v in r0["X-02"]["by_stage"].items() if k in ("B1", "B3", "B4", "B5")})
    s2 = copy.deepcopy(s)
    s2.boundary.replacement_cycle = -25.0
    for m in s2.materials: m.refresh_cycle = -abs(m.refresh_cycle) if m.refresh_cycle else float("nan")
    for e in s2.equipment: e.replacement_event_list = None; e.service_life = float("nan")
    for d in s2.refrigerants: d.change_years = None; d.service_life = -3.0
    r = show("invalid periods", s2)
    print("   stages", {k: round(v, 2) for k, v in r["X-02"]["by_stage"].items() if k in ("B1", "B3", "B4", "B5")}, "SYS-01 violations", r["SYS-01"]["violations"], "B4-02 n_partial", r["B4-02"]["n_partial"], "B5 n_events", r["B5-01"]["n_events"])
    # one at a time
    for label, fn in (("replacement_cycle -25", lambda x: setattr(x.boundary, "replacement_cycle", -25.0)),
                      ("replacement_cycle None", lambda x: setattr(x.boundary, "replacement_cycle", None)),
                      ("replacement_cycle NaN", lambda x: setattr(x.boundary, "replacement_cycle", float("nan"))),
                      ("replacement_cycle inf", lambda x: setattr(x.boundary, "replacement_cycle", float("inf"))),
                      ("replacement_cycle 0", lambda x: setattr(x.boundary, "replacement_cycle", 0.0))):
        s3 = copy.deepcopy(s); fn(s3)
        r3 = registry.run_all(s3); f3 = engine.evaluate(s3)
        print(f"   {label}: B5 {r3['B5-01']['value']:.2f} computed {r3['B5-01']['computed']} n_events {r3['B5-01']['n_events']} complete {r3['SUM-03']['complete']} fast B5 {f3['B5-01']['value']:.2f} fast complete {f3['SUM-03']['complete']} SYS-01 {r3['SYS-01']['ok']}")
    # what does SYS-01 say for None periods on materials/equipment
    s4 = copy.deepcopy(s)
    s4.materials[0].refresh_cycle = None; s4.equipment[0].service_life = None; s4.equipment[0].replacement_event_list = None
    r4 = registry.run_all(s4)
    print("   None refresh_cycle / service_life: SYS-01", r4["SYS-01"]["ok"], r4["SYS-01"]["violations"], "complete", r4["SUM-03"]["complete"])
