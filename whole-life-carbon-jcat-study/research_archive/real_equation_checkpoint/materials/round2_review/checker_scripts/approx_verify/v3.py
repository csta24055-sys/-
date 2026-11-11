#!/usr/bin/env python3
"""Verifier's own check, pass 3: APP-9. Are the AP-18b / AP-19a parameters in-sample, and what happens out of sample?"""
import math

from refcalc import registry
from refcalc.base import periodic_events
from synth import population

registry.load_all()
EPS = 1e-9


def yw(T):
    return [0.0] + [min(1.0, T - (y - 1)) for y in range(1, math.ceil(T) + 1)]


def eyear(tau):
    return max(1, math.ceil(tau * (1 - EPS)))


def pct(vals, q):
    s = sorted(vals)
    pos = (len(s) - 1) * q / 100.0
    lo = int(math.floor(pos)); hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def S(xs):
    a = [abs(x) for x in xs]
    return "n=%d mean %+.5f p95 %.5f min %+.5f max %+.5f under %.1f%%" % (len(xs), sum(xs) / len(xs), pct(a, 95), min(xs), max(xs),
                                                                         100 * sum(x < -1e-12 for x in xs) / len(xs))


def ok(c):
    return c is not None and c > 0 and not math.isinf(c)


recs = []
n_rows = n_ratio_rows = 0
for scn in population.verification_population(400, seed=20261111, max_size="M"):
    res = registry.run_all(scn)
    T = scn.boundary.study_period
    st = res["X-02"]["by_stage_all"]
    cls = {}
    for i, row in enumerate(scn.materials):
        e0 = res["A13-01"]["by_item"][i] + res["A13-03"]["by_item"][i]
        r = row.repair_rate
        n_rows += 1
        n_ratio_rows += bool(row.unquantified_cost_ratio)
        if r is None or not r >= 0:
            continue
        q = cls.setdefault(row.material_class, {"E0": 0.0, "E0r": 0.0, "W": 0.0, "Wc": 0.0})
        q["E0"] += e0; q["E0r"] += e0 * r
        if ok(row.refresh_cycle):
            q["W"] += e0 * r; q["Wc"] += e0 * r / row.refresh_cycle       # weights e0*r (the repair weight)
    q = cls.setdefault("EQUIPMENT", {"E0": 0.0, "E0r": 0.0, "W": 0.0, "Wc": 0.0})
    for j, eq in enumerate(scn.equipment):
        e0 = res["X-01"]["by_item"][j]
        r = eq.repair_rate
        if r is None or not r >= 0:
            continue
        q["E0"] += e0; q["E0r"] += e0 * r
        if ok(eq.service_life):
            q["W"] += e0 * r; q["Wc"] += e0 * r / eq.service_life
    mfg = [res["A13-01"]["by_item"][i] + res["A13-03"]["by_item"][i] for i in range(len(scn.materials))]
    rat = [row.unquantified_cost_ratio for row in scn.materials]
    recs.append({"g": (scn.meta.structure, scn.meta.use), "T": T, "B3": st["B3"], "wlc": sum(st.values()), "cls": cls,
                 "a1304": res["A13-04"]["value"], "mfg": mfg, "rat": rat})

half = len(recs) // 2
tr, te = recs[:half], recs[half:]


def skipw(T, c):
    w = yw(T)
    return sum(w[y] for y in {eyear(t) for t in periodic_events(T, c)})


def pooled(rows):
    par = {}
    for r in rows:
        for k, c in r["cls"].items():
            p = par.setdefault(k, {"E0": 0.0, "E0r": 0.0, "W": 0.0, "Wc": 0.0})
            for x in p:
                p[x] += c[x]
    return par


par_all = pooled(tr)
par_grp = {}
for g in {r["g"] for r in tr}:
    par_grp[g] = pooled([r for r in tr if r["g"] == g])
out_all, out_grp, ins, tot_all = [], [], [], []
for r in te:
    T = r["T"]
    a = b = c_in = 0.0
    for k, c in r["cls"].items():
        p = par_all[k]
        a += c["E0"] * (p["E0r"] / p["E0"]) * (T - (skipw(T, p["W"] / p["Wc"]) if p["Wc"] else 0.0))
        pg = par_grp.get(r["g"], {}).get(k, p)
        b += c["E0"] * (pg["E0r"] / pg["E0"] if pg["E0"] else 0.0) * (T - (skipw(T, pg["W"] / pg["Wc"]) if pg["Wc"] else 0.0))
        c_in += c["E0r"] * (T - (skipw(T, c["W"] / c["Wc"]) if c["Wc"] else 0.0))
    out_all.append(a / r["B3"] - 1); out_grp.append(b / r["B3"] - 1); ins.append(c_in / r["B3"] - 1)
    tot_all.append((a - r["B3"]) / r["wlc"])
print("AP-18b, class parameters of the building itself (second half):                     ", S(ins))
print("AP-18b, class parameters pooled from the first half (all buildings):               ", S(out_all))
print("   same, difference relative to whole-life total:                                  ", S(tot_all))
print("AP-18b, class parameters pooled from the first half per (structure, use):          ", S(out_grp))

# AP-19a
print("share of material rows with a non-zero unquantified ratio: %.3f" % (n_ratio_rows / n_rows))
e_keep, e_all, e_out = [], [], []
# out of sample: one mean ratio from the training half (rows that carry a ratio), applied to the rows that carry one
tr_r = [x for r in tr for x in r["rat"] if x is not None and 0 < x < 1]
rbar_tr = sum(tr_r) / len(tr_r)
for r in recs:
    rr = [(e, x) for e, x in zip(r["mfg"], r["rat"]) if x is not None and 0 < x < 1]
    if not rr or not r["a1304"]:
        continue
    rb = sum(x for _, x in rr) / len(rr)
    e_keep.append(sum(e for e, _ in rr) * rb / (1 - rb) / r["a1304"] - 1)
    ra = sum((x or 0.0) for x in r["rat"]) / len(r["rat"])
    e_all.append(sum(r["mfg"]) * ra / (1 - ra) / r["a1304"] - 1)
    e_out.append(sum(e for e, _ in rr) * rbar_tr / (1 - rbar_tr) / r["a1304"] - 1)
print("AP-19a as measured by the study (mean of the rows that carry a ratio, applied to those rows):", S(e_keep))
print("AP-19a with one ratio for the whole bill (mean over all rows incl. zeros, all rows):         ", S(e_all))
print("AP-19a with a population mean ratio %.4f applied to the rows that carry one:                 " % rbar_tr, S(e_out))
