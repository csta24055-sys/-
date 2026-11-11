import sys, copy, math, json, itertools, time
sys.path.insert(0, "/tmp/claude-0/-home-user--/49c0bd7e-a786-5ae4-9a1e-e89e7996ede3/scratchpad/recheck/rederive")
import synth
from synth import population
from refcalc import registry, base
import mine
registry.load_all()
ST = list(base.STAGES)
def close(a, b, tol=1e-9):
    return a == b or abs(a - b) <= tol * max(abs(a), abs(b), 1e-300)

print("== S1: every one of the 2^14 boundary subsets (tiny scenario, T=62.5, rebuild) ==")
s = synth.make_scenario(5, "SRC", "hospital", "S", 62.5, n_materials=4, n_equipment=3, n_refrigerants=2,
                        replacement_cycle=25.0, reconstruction_scenario="MAJOR_REFURBISHMENT")
s.boundary.included_lifecycle_stages = list(ST)
full = registry.run_all(s)
F = full["X-02"]["by_stage"]; FC = full["X-05"]["by_stage_co2"]
print("full by_stage", {k: round(v, 3) for k, v in F.items()}, "B2-01", full["B2-01"]["value"], "B6-03", full["B6-03"]["value"])
bad = 0; n = 0
t0 = time.time()
IDS = ["X-02", "SUM-01", "SUM-02", "SUM-03", "X-05", "X-07", "QA-01", "SUM-07", "X-04"]
for mask in range(1 << 14):
    sub = [ST[i] for i in range(14) if mask >> i & 1]
    s.boundary.included_lifecycle_stages = sub
    r = registry.run_all(s, ids=IDS)
    n += 1
    bs = r["X-02"]["by_stage"]
    exp = {}
    for st in sub:
        exp[st] = F[st]
    if "B6" in sub and "B2" not in sub:
        exp["B6"] = F["B6"] + F["B2"]
    ok = set(bs) == set(sub) and all(close(bs[k], exp[k]) for k in sub)
    tot = sum(exp.values())
    ok = ok and close(r["SUM-03"]["value"], tot) and close(r["X-07"]["value"], tot) and close(r["X-07"]["cumulative"][-1], tot)
    ok = ok and close(r["SUM-01"]["value"], sum(exp.get(k, 0.0) for k in ("A1-A3", "A4", "A5")))
    ok = ok and close(r["SUM-02"]["value"], sum(v for k, v in exp.items() if k not in ("B6", "B7")))
    co2 = sum(FC[k] for k in sub) + (FC["B2"] if ("B6" in sub and "B2" not in sub) else 0.0)
    ok = ok and close(r["X-05"]["value"], co2) and r["QA-01"]["ok"]
    # emissions that are in no reported stage: grid share B2 when B2 out and B6 out is by design; check when B6 in
    if not ok:
        bad += 1
        if bad <= 5: print("MISMATCH", sub, bs, r["SUM-03"], r["X-07"]["value"], r["X-05"]["value"], co2)
print("subsets", n, "mismatches", bad, "seconds", round(time.time() - t0, 1))
s.boundary.included_lifecycle_stages = list(ST)

print("\n== S2: X-05 and X-04 re-derived by substituting factor values (my implementation) ==")
def derive_gas(scn, gas, keep_grid):
    c = copy.deepcopy(scn)
    for f in c.factors.values():
        f.value = f.gas_amounts[gas]
    for d in c.refrigerants:
        if d.gwp is not None and d.gwp >= 0: d.gwp = 0.0
    if not keep_grid:
        g = c.operation.grid
        g.table = [0.0] * len(g.table); g.construction_value = 0.0
        if g.start is not None: g.start = 0.0
        if g.floor is not None: g.floor = 0.0
        if g.annual_decline is not None: g.annual_decline = 0.0
        if g.steps:
            for stp in g.steps: stp.value = 0.0
    return mine.run(c)["_all_stage"]
nbad = 0; ncase = 0
cases = [("pop%d" % i, x) for i, x in enumerate(population.verification_population(12, 99, max_size="S"))]
cases += [("dirty%d" % k, synth.make_scenario(300 + k, "W", "retail", "S", 50.0, dirty=True, n_materials=30, n_equipment=10, n_refrigerants=5)) for k in range(6)]
cases += [("edge:" + n_, x) for n_, x in population.edge_cases()]
for name, sc in cases:
    ref = registry.run_all(sc)
    ncase += 1
    mineco2 = derive_gas(sc, "CO2", True)
    rc = ref["X-05"]["by_stage_co2"]
    inc = set(sc.boundary.included_lifecycle_stages)
    # my all-stage B6 holds the carve-out only if B2 included; normalise to B6 - B2
    my = dict(mineco2)
    if "B2" not in inc: my["B6"] = my["B6"] - my["B2"]
    d = [(k, rc[k], my[k]) for k in ST if not close(rc[k], my[k], 1e-9) and abs(rc[k] - my[k]) > 1e-6]
    val = sum(my[k] for k in ST if k in inc) + (my["B2"] if ("B6" in inc and "B2" not in inc) else 0.0)
    if d or not close(ref["X-05"]["value"], val, 1e-9):
        nbad += 1; print("X-05 DIFF", name, d[:3], ref["X-05"]["value"], val)
    for gas in sc.gases:
        mg = derive_gas(sc, gas, False)
        tot = sum(mg.values()) if "B2" in inc else sum(mg.values())
        if not close(ref["X-04"]["by_gas"][gas], tot, 1e-8) and abs(ref["X-04"]["by_gas"][gas] - tot) > 1e-6:
            nbad += 1; print("X-04 DIFF", name, gas, ref["X-04"]["by_gas"][gas], tot)
print("cases", ncase, "diffs", nbad)

print("\n== S3: SUM-08 re-derived ==")
nb = 0; nc = 0
for name, sc in cases:
    ref = registry.run_all(sc)
    bid = sc.boundary.baseline_scenario
    r8 = ref["SUM-08"]
    if bid is None:
        assert r8["status"] == "NO_BASELINE"; continue
    b = population.BASELINES.get(bid)
    nc += 1
    mb = mine.run(b)["SUM-03"]["value"]; mp = mine.run(sc)["SUM-03"]["value"]
    if r8["status"] != "COMPARED" or not close(r8["delta"], mp - mb, 1e-8) or not close(r8["saving"], (mb - mp) / mb, 1e-8):
        nb += 1; print("SUM-08 DIFF", name, r8, mp - mb, (mb - mp) / mb)
print("with baseline", nc, "diffs", nb)
