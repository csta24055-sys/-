"""Missed candidates, measured on the study's own fictional population (same seed, same train/test split as bench/approx_study.py).
(1) exact two-moment closed form for purchased electricity with linear demand: E = B*G(T) + S*H(T), H = sum_k w_k * k * g_k
(2) M4 stage-ratio model anchored on the exactly computed A1-A3 instead of floor area (AP-15 uses area only)
SYNTHETIC data only: no statement about real buildings."""
import math, statistics
from fastcalc import engine, closed_forms as cf
from refcalc import registry
from refcalc.base import year_weights
from synth import population
from common.compare import percentile
registry.load_all()

def stats(e):
    a = [abs(x) for x in e]
    return "n=%d mean %+.1f%% p95|e| %.1f%% max over %+.1f%% max under %+.1f%%" % (len(e), 100*sum(e)/len(e), 100*percentile(a, 95), 100*max(e), 100*min(e))

recs = []
lin_err, lin_n, lin_clamped, kinds_seen = [], 0, 0, {}
for scn in population.verification_population(400, seed=20261111, max_size="M"):
    T = scn.boundary.study_period
    engine.clear_baseline_cache()
    scn.boundary.baseline_scenario = None
    R = engine.evaluate(scn, detail=False)
    st = R["X-02"]["by_stage_all"]
    recs.append({"g": (scn.meta.structure, scn.meta.use), "T": T, "area": scn.project.gross_floor_area, "stage": dict(st)})
    # ---- (1) electricity with parametric (CONSTANT / LINEAR_TREND) demand, generation and export
    op = scn.operation
    profs = (op.electricity, op.onsite_generation, op.onsite_export)
    if all(p.kind in ("CONSTANT", "LINEAR_TREND") for p in profs) and any(p.kind == "LINEAR_TREND" for p in profs):
        Y = math.ceil(T); w = year_weights(T)
        B = op.electricity.base - (op.onsite_generation.base - op.onsite_export.base)
        S = (op.electricity.slope or 0.0) - ((op.onsite_generation.slope or 0.0) - (op.onsite_export.slope or 0.0))
        ref = registry.run_all(scn, ids=["B6-03"])
        elec_ref = dict(ref["B6-03"]["_lines"]).get("GRID")
        g = ref["X-06"]["by_year"]
        if B >= 0.0 and B + S * (Y - 1) >= 0.0:          # linear net demand, non-negative at both ends: the clamp never acts
            G = sum(w[y] * g[y] for y in range(1, Y + 1))
            H = sum(w[y] * (y - 1) * g[y] for y in range(1, Y + 1))   # one extra cumulative per grid scenario
            cand = B * G + S * H if op.grid.licence_status in ("PERMITTED_PUBLIC",) or elec_ref else 0.0
            if elec_ref:
                lin_err.append(cand / elec_ref - 1.0); lin_n += 1
                kinds_seen[op.grid.kind] = kinds_seen.get(op.grid.kind, 0) + 1
        else:
            lin_clamped += 1
print("(1) two-moment closed form  E_elec = B*G(T) + S*H(T)  vs reference year loop")
print("    scenarios with linear (non-constant) parametric demand and inactive clamp:", lin_n, "| clamp could act (fallback to loop):", lin_clamped, "| grid kinds:", kinds_seen)
print("    max |relative difference|: %.3e" % max(abs(e) for e in lin_err))

# ---- (2) stage-ratio model anchored on exact A1-A3
half = len(recs) // 2
train, test = recs[:half], recs[half:]
def gmean(rows, val):
    acc = {}
    for r in rows:
        v = val(r)
        if v is None: continue
        s = acc.setdefault(r["g"], [0.0, 0]); s[0] += v; s[1] += 1
    return {k: s[0] / s[1] for k, s in acc.items()}
ONCE = ("A4", "A5", "C1", "C2", "C3", "C4"); TIMED = ("B3", "B4")
print("(2) stage error on the test half: AP-15-style (area x group mean intensity)  vs  ratio to exact A1-A3 (x T for B3/B4)")
tot_area, tot_ratio = [], []
pred_area = [0.0] * len(test); pred_ratio = [0.0] * len(test)
ALL = ("A1-A3", "A4", "A5", "B1", "B2", "B3", "B4", "B5", "B6", "B7", "C1", "C2", "C3", "C4")
ANNUAL = ("B1", "B2", "B3", "B4", "B5", "B6", "B7")
for s in ALL:
    scale_a = (lambda r: r["area"] * r["T"]) if s in ANNUAL else (lambda r: r["area"])
    ma = gmean(train, lambda r: r["stage"][s] / scale_a(r))
    if s in ONCE or s in TIMED:
        scale_r = (lambda r: r["stage"]["A1-A3"] * r["T"]) if s in TIMED else (lambda r: r["stage"]["A1-A3"])
        mr = gmean(train, lambda r: r["stage"][s] / scale_r(r) if r["stage"]["A1-A3"] > 0 else None)
    ea, er = [], []
    for i, r in enumerate(test):
        pa = ma[r["g"]] * scale_a(r)
        if s == "A1-A3":
            pr = r["stage"][s]                       # computed exactly
        elif s in ONCE or s in TIMED:
            pr = mr[r["g"]] * scale_r(r)
        else:
            pr = pa                                   # operational stages: same area model as AP-15
        pred_area[i] += pa; pred_ratio[i] += pr
        if r["stage"][s] > 0.0:
            ea.append(pa / r["stage"][s] - 1.0); er.append(pr / r["stage"][s] - 1.0)
    if s in ONCE or s in TIMED:
        print(f"    {s:5s} area model: {stats(ea)}\n          ratio model: {stats(er)}")
for i, r in enumerate(test):
    wlc = sum(r["stage"].values())
    tot_area.append(pred_area[i] / wlc - 1.0); tot_ratio.append(pred_ratio[i] / wlc - 1.0)
print("    whole-life total, all 14 stages by area model (AP-15):", stats(tot_area))
print("    whole-life total, A1-A3 exact + ratio model for A4,A5,B3,B4,C1-C4 + area model for B1,B2,B5,B6,B7:", stats(tot_ratio))
# embodied part only (what the ratio model replaces)
emb_ref = [sum(r["stage"][s] for s in ONCE + TIMED) for r in test]
print("    share of whole-life total in the replaced stages (A4,A5,B3,B4,C1-C4), median: %.1f%%" % (100 * statistics.median(e / sum(r["stage"].values()) for e, r in zip(emb_ref, test))))
