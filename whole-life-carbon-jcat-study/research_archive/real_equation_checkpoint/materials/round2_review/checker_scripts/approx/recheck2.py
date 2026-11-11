#!/usr/bin/env python3
"""Second pass (checker's own code): propagation of upstream candidates, silent drops, extra candidates,
population-level candidates, AP-14, X-10 targets. Writes only into the scratch folder."""
import copy
import json
import math
import sys
from pathlib import Path

import numpy as np

from refcalc import registry
from synth import population

HERE = Path(__file__).resolve().parent
N = int(sys.argv[1]) if len(sys.argv) > 1 else 400
registry.load_all()
EPS = 1e-9


def okp(c):
    return c is not None and c > 0 and not math.isinf(c)


def nonneg(x):
    return x is not None and x >= 0 and not math.isinf(x)


def weights(T):
    return [0.0] + [min(1.0, T - (y - 1)) for y in range(1, math.ceil(T) + 1)]


def ev_year(tau):
    return max(1, math.ceil(tau * (1 - EPS)))


def st(xs):
    if not xs:
        return {"n": 0}
    a = np.asarray(xs, float)
    return {"n": len(xs), "mean": float(a.mean()), "p95": float(np.percentile(np.abs(a), 95)), "min": float(a.min()),
            "max": float(a.max()), "share_under": float((a < -1e-12).mean())}


X = {}
def ex(k, v):
    X.setdefault(k, []).append(v)


def stage_all(s):
    return registry.run_all(s, ids=["X-02"])["X-02"]["by_stage_all"]


F = {"AP-01": lambda T, c: max(0.0, T / c - 1.0), "AP-02": lambda T, c: max(0.0, T / c - 0.5), "AP-03": lambda T, c: T / c}
recs = []
drop = {"AP-02": 0, "AP-03": 0, "pairs": 0}
corr_md, corr_mh = [], []
n14 = {"T<75": 0, "T<75 with explicit lists": 0, "T<60": 0}
i_scn = 0
for scn in population.verification_population(N, seed=20261111, max_size="M"):
    i_scn += 1
    res = registry.run_all(scn)
    T = scn.boundary.study_period
    w = weights(T)
    Y = len(w) - 1
    S = res["X-02"]["by_stage_all"]
    WLC = sum(S.values())
    mats, eqs = scn.materials, scn.equipment
    q_ord, q_inst = res["A13-05"]["q_ord"], res["A13-05"]["q_inst"]
    mfg = [res["A13-01"]["by_item"][i] + res["A13-03"]["by_item"][i] for i in range(len(mats))]

    # ---- X-10 resource mass with the three count forms
    from synth import model as _m
    for cid, f in F.items():
        r_ = 0.0
        for i, row in enumerate(mats):
            conv = _m.conversion_factor(scn.unit_conversions, row.quantity_unit, "kg", row.conversions)
            if conv is None or q_ord[i] is None or not nonneg(row.end_of_life.mass_kg):
                continue
            r_ += q_ord[i] * conv * (1 + (f(T, row.refresh_cycle) if okp(row.refresh_cycle) else 0.0))
        ex(cid + ":X-10 resource", r_ / res["X-10"]["resource_kg"] - 1)

    # ---- by_material_class: (scenario, class) pairs whose reference B4 is 0 while AP-02 / AP-03 are not
    cls_ref, cls_c = {}, {}
    for i, row in enumerate(mats):
        cls_ref[row.material_class] = cls_ref.get(row.material_class, 0.0) + res["B4-02"]["by_item_material"][i]
        if okp(row.refresh_cycle):
            u_pos = (mfg[i] + res["A4-01"]["by_item"][i] + res["A4-02"]["by_item"][i] + res["C2-01"]["by_item"][i]
                     + res["C3-01"]["by_item"][i] + res["C4-01"]["by_item"][i]) > 0
            for cid in ("AP-02", "AP-03"):
                if u_pos and F[cid](T, row.refresh_cycle) > 0:
                    cls_c.setdefault(cid, set()).add(row.material_class)
    for k, v in cls_ref.items():
        drop["pairs"] += 1
        if v == 0:
            for cid in ("AP-02", "AP-03"):
                if k in cls_c.get(cid, ()):
                    drop[cid] += 1

    # ---- mass / distance correlation inside the population (A4-01 rows and C2 rows)
    ms = [row.transport.mass_t for i, row in enumerate(mats) if res["A4-01"]["_row_lines"][i]]
    ds = [row.transport.distance_km for i, row in enumerate(mats) if res["A4-01"]["_row_lines"][i]]
    # within-mode rank-free check: correlation of mass with (distance / mode mean distance)
    md = {}
    for i, row in enumerate(mats):
        if res["A4-01"]["_row_lines"][i]:
            md.setdefault(row.transport.factor_id, []).append(row.transport.distance_km)
    mean_d = {k: sum(v) / len(v) for k, v in md.items()}
    rel = [row.transport.distance_km / mean_d[row.transport.factor_id] for i, row in enumerate(mats) if res["A4-01"]["_row_lines"][i]]
    if len(ms) > 5:
        corr_md.append(float(np.corrcoef(np.log(np.asarray(ms) + 1e-300), rel)[0, 1]))
    hm = [row.end_of_life.mass_kg for i, row in enumerate(mats) if res["C2-01"]["_row_lines"][i]]
    hd = [row.end_of_life.haul_distance_km for i, row in enumerate(mats) if res["C2-01"]["_row_lines"][i]]
    if len(hm) > 5:
        corr_mh.append(float(np.corrcoef(np.log(np.asarray(hm) + 1e-300), hd)[0, 1]))

    # ---- propagated whole-life effect of upstream candidates (scenario rewritten so that the reference model
    #      itself computes with the approximated quantity; everything downstream follows)
    def rerun(mut):
        s2 = copy.deepcopy(scn)
        s2.boundary.baseline_scenario = None
        mut(s2)
        return stage_all(s2)

    # AP-07b: drop components below 5 percent and renormalise
    def m7b(s2):
        for i, row in enumerate(s2.materials):
            if row.composition is not None and res["X-15"]["kind"][i] == "COMPOSITE":
                kept = [c for c in row.composition if c.mass_fraction >= 0.05]
                tot = sum(c.mass_fraction for c in kept)
                for c in kept:
                    c.mass_fraction = c.mass_fraction / tot
                row.composition = kept
    r2 = rerun(m7b)
    ex("AP-07b:propagated total", sum(r2.values()) / WLC - 1)
    ex("AP-07b:local total (study definition)", (r2["A1-A3"] - S["A1-A3"]) / WLC)
    for s_ in ("A1-A3", "B3", "B4"):
        ex("AP-07b:propagated stage " + s_, r2[s_] / S[s_] - 1)

    # AP-17: every A4-01 row gets the simple mean distance of its mode
    def m17(s2):
        for i, row in enumerate(s2.materials):
            if res["A4-01"]["_row_lines"][i]:
                row.transport.distance_km = mean_d[row.transport.factor_id]
    r2 = rerun(m17)
    ex("AP-17:propagated total", sum(r2.values()) / WLC - 1)
    ex("AP-17:local total (study definition)", (r2["A4"] - S["A4"]) / WLC)
    ex("AP-17:stage A4 (rerun)", r2["A4"] / S["A4"] - 1)
    ex("AP-17:propagated stage B4", r2["B4"] / S["B4"] - 1)

    # AP-19a: every row that carries a ratio gets the simple mean ratio
    rr = [row.unquantified_cost_ratio for row in mats if row.unquantified_cost_ratio is not None and 0 < row.unquantified_cost_ratio < 1]
    if rr:
        rbar = sum(rr) / len(rr)
        def m19(s2):
            for row in s2.materials:
                if row.unquantified_cost_ratio is not None and 0 < row.unquantified_cost_ratio < 1:
                    row.unquantified_cost_ratio = rbar
        r2 = rerun(m19)
        ex("AP-19a:propagated total", sum(r2.values()) / WLC - 1)
        ex("AP-19a:local total (study definition)", (r2["A1-A3"] - S["A1-A3"]) / WLC)

    # AP-18c: every row gets the class mean route fractions (route factors are per class in the generator)
    cm = {}
    for row in mats:
        if nonneg(row.end_of_life.mass_kg):
            c = cm.setdefault(row.material_class, {"n": 0, "fr": {}})
            c["n"] += 1
            for route in row.end_of_life.routes:
                c["fr"][route.route] = c["fr"].get(route.route, 0.0) + route.fraction
    def m18c(s2):
        for row in s2.materials:
            if nonneg(row.end_of_life.mass_kg):
                c = cm[row.material_class]
                for route in row.end_of_life.routes:
                    route.fraction = c["fr"][route.route] / c["n"]
    r2 = rerun(m18c)
    ex("AP-18c:propagated total", sum(r2.values()) / WLC - 1)
    ex("AP-18c:local total (study definition)", (r2["C3"] + r2["C4"] - S["C3"] - S["C4"]) / WLC)
    ex("AP-18c:C3+C4 materials (rerun)", (r2["C3"] + r2["C4"] - S["C3"] - S["C4"]) / (res["C3-01"]["value"] + res["C4-01"]["value"]))
    ex("AP-18c:stage C4", r2["C4"] / S["C4"] - 1)
    ex("AP-18c:stage C3", r2["C3"] / S["C3"] - 1)

    # ---- candidates the study did not measure: repairs with the continuous renewal count in the exclusion term
    A0 = A1 = 0.0          # sum e0*r and sum e0*r/c  (rows with a periodic cycle)
    fixed = 0.0            # rows with explicit lists or no cycle: exact
    cls = {}
    b3_lb_clamped = 0.0
    for i, row in enumerate(mats):
        r = row.repair_rate
        if not nonneg(r):
            continue
        e0r = mfg[i] * r
        if okp(row.refresh_cycle):
            A0 += e0r; A1 += e0r / row.refresh_cycle
            c = cls.setdefault(row.material_class, [0.0, 0.0]); c[0] += e0r; c[1] += e0r / row.refresh_cycle
            b3_lb_clamped += e0r * (T - max(0.0, T / row.refresh_cycle - 1.0))
        else:
            fixed += e0r * T
    for j, eq in enumerate(eqs):
        r = eq.repair_rate
        if not nonneg(r):
            continue
        e0r = res["X-01"]["by_item"][j] * r
        if eq.replacement_event_list is not None:
            fixed += e0r * (T - sum(w[y] for y in {ev_year(t) for t in res["B4-01"]["events"][j]}))
        elif okp(eq.service_life):
            A0 += e0r; A1 += e0r / eq.service_life
            c = cls.setdefault("EQUIPMENT", [0.0, 0.0]); c[0] += e0r; c[1] += e0r / eq.service_life
            b3_lb_clamped += e0r * (T - max(0.0, T / eq.service_life - 1.0))
        else:
            fixed += e0r * T
    B3 = S["B3"]
    two_agg = fixed + A0 * (T + 1.0) - T * A1                   # skip = T/c - 1, not clamped: two sums only
    ex("NEW-B3 two sums: skip=T/c-1 unclamped | stage", two_agg / B3 - 1)
    ex("NEW-B3 two sums: skip=T/c-1 unclamped | total", (two_agg - B3) / WLC)
    ex("NEW-B3 clamped: skip=max(0,T/c-1) | stage", (fixed + b3_lb_clamped) / B3 - 1)
    ex("NEW-B3 clamped: skip=max(0,T/c-1) | total", (fixed + b3_lb_clamped - B3) / WLC)
    # class-parameter form: per class E0r and the e0r-weighted harmonic mean cycle; skip = max(0, T/cbar - 1)
    cp = fixed + sum(c[0] * (T - max(0.0, T / (c[0] / c[1]) - 1.0)) for c in cls.values() if c[1])
    ex("NEW-B3 class parameters (E0r, harmonic mean cycle), skip=max(0,T/cbar-1) | stage", cp / B3 - 1)
    ex("NEW-B3 class parameters | total", (cp - B3) / WLC)
    mid = fixed + A0 * (T + 0.5) - T * A1
    ex("NEW-B3 two sums: skip=T/c-1/2 unclamped | stage", mid / B3 - 1)

    # ---- records for the population-level candidates
    from refcalc.units_pre_a import SIMPLE_CLASSES, simple_class, summary_quantity
    ce = {k: 0.0 for k in SIMPLE_CLASSES}
    for i, row in enumerate(mats):
        k = simple_class(row)
        if k is not None:
            ce[k] += mfg[i]
    sto = res["STO-01"]["value"]
    recs.append({"g": (scn.meta.structure, scn.meta.use), "T": T, "area": scn.project.gross_floor_area, "wlc": WLC,
                 "ce": ce, "cq": {k: summary_quantity(scn, k) for k in SIMPLE_CLASSES}, "mat": sum(mfg),
                 "co2": res["X-05"]["value"], "tot": res["SUM-03"]["value"], "sto": sto,
                 "timber": scn.summary_quantities.timber_m3, "seed": scn.meta.seed, "id": scn.meta.scenario_id,
                 "scn": scn if i_scn <= 80 else None,
                 "explicit": any(e.replacement_event_list is not None for e in eqs) or any(d.change_years is not None for d in scn.refrigerants)})

for k in sorted(X):
    s = st(X[k])
    print(f"{k:86s} {s['n']:5d} mean {s['mean']:+.5f} p95 {s['p95']:.5f} min {s['min']:+.5f} max {s['max']:+.5f} under {s['share_under']*100:5.1f}%")
print("by_material_class: (scenario,class) pairs", drop["pairs"], "| reference 0 but AP-02 > 0:", drop["AP-02"], "| reference 0 but AP-03 > 0:", drop["AP-03"])
print("corr(log mass, distance/mode mean) per scenario: mean %.4f min %.4f max %.4f" % (np.mean(corr_md), np.min(corr_md), np.max(corr_md)))
print("corr(log eol mass, haul distance) per scenario: mean %.4f min %.4f max %.4f" % (np.mean(corr_mh), np.min(corr_mh), np.max(corr_mh)))

# ------------------------------------------------ population-level candidates (first half fits, second half tests)
half = len(recs) // 2
tr, te = recs[:half], recs[half:]
print("train/test: shared seeds", len({r["seed"] for r in tr} & {r["seed"] for r in te}), "shared ids", len({r["id"] for r in tr} & {r["id"] for r in te}),
      "| groups in test not in train", len({r["g"] for r in te} - {r["g"] for r in tr}))


def gmean(rows, fn):
    acc = {}
    for r in rows:
        v = fn(r)
        if v is None:
            continue
        a = acc.setdefault(r["g"], [0.0, 0]); a[0] += v; a[1] += 1
    return {k: a[0] / a[1] for k, a in acc.items()}


from refcalc.units_pre_a import SIMPLE_CLASSES
P = {}
fb = {}
for k in SIMPLE_CLASSES:
    num, den = gmean(tr, lambda r: r["ce"][k]), gmean(tr, lambda r: r["cq"][k])
    fb[k] = {g: (num[g] / den[g] if den[g] else 0.0) for g in num}
gross = gmean(tr, lambda r: r["mat"] / sum(r["ce"].values()) if sum(r["ce"].values()) else None)
mi = gmean(tr, lambda r: r["wlc"] / (r["area"] * r["T"]))
sb = gmean(tr, lambda r: r["sto"] / r["timber"] if r["sto"] and r["timber"] else None)
kp = gmean(tr, lambda r: r["co2"] / r["tot"] if r["tot"] else None)
for r in te:
    g = r["g"]
    a = sum(r["cq"][k] * fb[k][g] for k in SIMPLE_CLASSES)
    P.setdefault("AP-10", []).append(a / r["mat"] - 1)
    P.setdefault("AP-10b", []).append(a * gross[g] / r["mat"] - 1)
    P.setdefault("AP-11", []).append(mi[g] * r["area"] * r["T"] / r["wlc"] - 1)
    if r["sto"] and r["timber"] and g in sb:
        P.setdefault("AP-21", []).append(sb[g] * r["timber"] / r["sto"] - 1)
    P.setdefault("AP-22b", []).append(kp[g] * r["tot"] / r["co2"] - 1)
study = json.loads(Path("/home/user/-/whole-life-carbon-jcat-study/09_APPROX_STUDY/04_VERIFICATION/approximation_study.json").read_text(encoding="utf-8"))["candidates"]
for k, v in P.items():
    s, ss = st(v), study[k]["stage_error"]
    print(f"{k:8s} own n={s['n']} mean {s['mean']:+.5f} p95 {s['p95']:.5f} min {s['min']:+.5f} max {s['max']:+.5f} | study n={ss['n']} mean {ss['mean_signed']:+.5f} p95 {ss['p95_abs']:.5f} min {ss['max_under']:+.5f} max {ss['max_over']:+.5f}")
# how much of AP-11 is the scenario-specific fictional factor catalogue: spread of the class factor of CONCRETE inside one group
for k in ("CONCRETE", "REBAR"):
    sp = []
    for g in {r["g"] for r in tr}:
        v = [r["ce"][k] / r["cq"][k] for r in tr if r["g"] == g and r["cq"][k] and r["ce"][k]]
        if len(v) > 2:
            sp.append(max(v) / min(v))
    print(f"class factor {k}: max/min inside one (structure,use) group of the training half: median {np.median(sp):.1f}, max {np.max(sp):.1f}")
# AP-21 from the generator ranges alone
print("AP-21 analytic range from the generator's uniform ranges (density 300-700, carbon 0.30-0.60, group mean near 500*0.45): "
      f"{500*0.45/(700*0.6)-1:+.3f} .. {500*0.45/(300*0.3)-1:+.3f}")

# ------------------------------------------------ AP-14 on the first 80 scenarios
e14, e14_ok, e14_trunc = [], [], []
for r in recs[:80]:
    scn = r["scn"]
    vals = {}
    for T2 in (50.0, 60.0, 75.0):
        s2 = copy.deepcopy(scn)
        s2.boundary.study_period = T2
        s2.boundary.baseline_scenario = None
        vals[T2] = registry.run_all(s2, ids=["SUM-03"])["SUM-03"]["value"]
    e = (vals[50.0] + (vals[75.0] - vals[50.0]) * 10.0 / 25.0) / vals[60.0] - 1
    e14.append(e)
    if r["T"] < 75:
        n14["T<75"] += 1
        if r["explicit"]:
            n14["T<75 with explicit lists"] += 1
            e14_trunc.append(e)
        else:
            e14_ok.append(e)
    else:
        e14_ok.append(e)
    if r["T"] < 60:
        n14["T<60"] += 1
s, ss = st(e14), study["AP-14"]["stage_error"]
print(f"AP-14 own n={s['n']} mean {s['mean']:+.5f} p95 {s['p95']:.5f} min {s['min']:+.5f} max {s['max']:+.5f} | study mean {ss['mean_signed']:+.5f} p95 {ss['p95_abs']:.5f} min {ss['max_under']:+.5f} max {ss['max_over']:+.5f}")
print("AP-14 scenarios whose own study period is below 75:", n14, "| error where explicit lists are cut at the original period:", st(e14_trunc), "| others:", st(e14_ok))
(HERE / f"recheck2_out_{N}.json").write_text(json.dumps({k: st(v) for k, v in X.items()}, indent=1), encoding="utf-8")
