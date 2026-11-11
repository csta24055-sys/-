"""Independent check of the table candidates (AP-24a, AP-24b, AP-09a/b) by re-running the reference on rewritten tables.

For each of the first N scenarios the year tables are overwritten with their coarse versions and the reference
calculation is run again; the stage errors of that run must equal the errors the study's measurement functions
recorded (which compute the candidate locally). Nothing is written to the repository.
"""
import sys
from refcalc import registry
from refcalc.base import profile_uses_descriptor
from synth import population
from bench import approx_measures as M, approx_support as sp

N = int(sys.argv[1]) if len(sys.argv) > 1 else 60
registry.load_all()
worst = {}
def note(key, a, b):
    worst[key] = max(worst.get(key, 0.0), abs(a - b))
cnt = {}
for i, scn in enumerate(population.verification_population(N, seed=20261111, max_size="M")):
    res = registry.run_all(scn)
    S = M.One(scn, res)
    X = M.Study()
    M.m_electricity(S, X)
    M.m_annual_tables(S, X)
    Y, st = S.Y, S.stage
    op, ww = scn.operation, scn.water_waste

    def coarse_table(p, profile, step=5):
        if not profile_uses_descriptor(profile):
            t = list(profile.table)
            t[:Y] = sp.coarse(t[:Y], step)
            p.set(profile, "table", t)

    # AP-24a
    def e24a(p):
        for prof in (op.gas, op.oil, op.district_heat, ww.water, ww.sewage, ww.municipal_waste):
            coarse_table(p, prof)
    new = sp.rerun(scn, e24a, ["X-02"])["X-02"]["by_stage_all"]
    col = X.C["AP-24a"]
    for s in ("B6", "B7"):
        mine = col.stages[s].errors[-1] if s in col.stages and col.stages[s].errors else 0.0
        note("AP-24a " + s, mine, (new[s] - st[s]) / st[s])
        cnt["AP-24a " + s] = cnt.get("AP-24a " + s, 0) + (s in col.stages and bool(col.stages[s].errors))
    for s in st:
        if s not in ("B6", "B7"): note("AP-24a other stages unchanged", 0.0, (new[s] - st[s]) / st[s] if st[s] else 0.0)

    # AP-24b
    def e24b(p):
        for prof in (op.electricity, op.onsite_generation, op.onsite_export):
            coarse_table(p, prof)
    new = sp.rerun(scn, e24b, ["X-02"])["X-02"]["by_stage_all"]
    col = X.C["AP-24b"]
    for s in ("B6", "B2"):
        mine = col.stages[s].errors[-1] if s in col.stages and col.stages[s].errors else 0.0
        note("AP-24b " + s, mine, (new[s] - st[s]) / st[s])
        cnt["AP-24b " + s] = cnt.get("AP-24b " + s, 0) + (s in col.stages and bool(col.stages[s].errors))

    # AP-09a / AP-09b: the grid factor as a coarse table
    g = res["X-06"]["by_year"][1:]
    for cid, step in (("AP-09a", 5), ("AP-09b", 10)):
        def e09(p, step=step):
            grid = op.grid
            t = list(grid.table)
            t[:Y] = sp.coarse(g, step)
            p.set(grid, "kind", "TABLE"); p.set(grid, "start", None); p.set(grid, "steps", None); p.set(grid, "table", t)
        new = sp.rerun(scn, e09, ["X-02"])["X-02"]["by_stage_all"]
        col = X.C[cid]
        for s in ("B6", "B2"):
            note(cid + " " + s, col.stages[s].errors[-1], (new[s] - st[s]) / st[s])
        cnt[cid] = cnt.get(cid, 0) + 1
print("scenarios", i + 1, "cases", cnt)
for k in sorted(worst): print("%-34s worst |difference of relative errors| = %.2e" % (k, worst[k]))
