"""Run every per-scenario measurement on the edge-case scenarios and on dirty scenarios: no exception, scenario restored."""
import json, traceback
import synth
from refcalc import registry
from synth import population
from bench import approx_measures as M
registry.load_all()
cases = list(population.edge_cases())
for seed in range(6):
    cases.append((f"dirty{seed}", synth.make_scenario(500 + seed, ("RC", "S", "SRC", "W")[seed % 4], "office", "S", (30.0, 62.5, 99.9)[seed % 3], dirty=True)))
X = M.Study()
bad = 0
for i, (name, scn) in enumerate(cases):
    before = json.dumps(synth.to_dict(scn), sort_keys=True)
    try:
        res = registry.run_all(scn)
        S = M.One(scn, res, load=True)
        M.m_counts(S, X); M.m_class_models(S, X); M.m_refrigerants(S, X); M.m_material_rows(S, X); M.m_composites(S, X)
        M.m_transport(S, X); M.m_electricity(S, X); M.m_annual_tables(S, X); M.m_gases(S, X)
    except Exception:
        bad += 1
        print("EXCEPTION in", name); traceback.print_exc(limit=3)
    if json.dumps(synth.to_dict(scn), sort_keys=True) != before:
        bad += 1; print("SCENARIO NOT RESTORED:", name)
print("cases", len(cases), "problems", bad)
# what the safe-side form gives on the edge cases (sign)
for cid in ("AP-23a", "AP-23b", "AP-04"):
    e = X.C[cid].primary.errors
    print(cid, "n", len(e), "min %.3e max %.3e" % (min(e), max(e)))
print("rows with a cycle below one year:", X.below_one_year)
for cid, col in X.C.items():
    if col.prop_n: print(cid, "propagation check worst", "%.2e" % col.prop_check, "n", col.prop_n)
