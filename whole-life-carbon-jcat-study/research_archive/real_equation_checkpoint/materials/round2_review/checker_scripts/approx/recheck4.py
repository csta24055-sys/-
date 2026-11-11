#!/usr/bin/env python3
"""Fourth pass (checker's own code): are the class parameters of AP-18b in-sample? Out-of-sample version
(class repair rate and class cycle taken from the first half of the population, applied to the second half)."""
import math

import numpy as np

from refcalc import registry
from synth import population

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


def count(T, c):
    n = 0
    while (n + 1) * c < T * (1 - EPS):
        n += 1
    return n


def st(xs):
    a = np.asarray(xs, float)
    return "n=%d mean %+.5f p95 %.5f min %+.5f max %+.5f under %.1f%%" % (len(xs), a.mean(), np.percentile(np.abs(a), 95), a.min(), a.max(), 100 * (a < -1e-12).mean())


recs = []
incomplete = 0
for scn in population.verification_population(400, seed=20261111, max_size="M"):
    res = registry.run_all(scn)
    incomplete += not res["X-02"]["complete"]
    T = scn.boundary.study_period
    S = res["X-02"]["by_stage_all"]
    cls = {}
    for i, row in enumerate(scn.materials):
        e0 = res["A13-01"]["by_item"][i] + res["A13-03"]["by_item"][i]
        c = cls.setdefault(row.material_class, {"E0": 0.0, "E0r": 0.0, "E0c": 0.0, "E0p": 0.0})
        if nonneg(row.repair_rate):
            c["E0"] += e0
            c["E0r"] += e0 * row.repair_rate
            if okp(row.refresh_cycle):
                c["E0p"] += e0
                c["E0c"] += e0 / row.refresh_cycle
    c = cls.setdefault("EQUIPMENT", {"E0": 0.0, "E0r": 0.0, "E0c": 0.0, "E0p": 0.0})
    for j, eq in enumerate(scn.equipment):
        e0 = res["X-01"]["by_item"][j]
        if nonneg(eq.repair_rate):
            c["E0"] += e0
            c["E0r"] += e0 * eq.repair_rate
            if okp(eq.service_life):
                c["E0p"] += e0
                c["E0c"] += e0 / eq.service_life
    recs.append({"g": (scn.meta.structure, scn.meta.use), "T": T, "B3": S["B3"], "wlc": sum(S.values()), "cls": cls})
print("scenarios of the population whose reference result is flagged incomplete (skipped rows):", incomplete)

half = len(recs) // 2
tr, te = recs[:half], recs[half:]
# class parameters from the training half, pooled over all buildings: repair rate (e0 weighted) and harmonic mean cycle (e0 weighted)
par = {}
for r in tr:
    for k, c in r["cls"].items():
        p = par.setdefault(k, {"E0": 0.0, "E0r": 0.0, "E0c": 0.0, "E0p": 0.0})
        for x in p:
            p[x] += c[x]
err, tot, err_in = [], [], []
for r in te:
    T = r["T"]
    w = weights(T)
    a = a_in = 0.0
    for k, c in r["cls"].items():
        p = par[k]
        rbar = p["E0r"] / p["E0"]
        cbar = p["E0p"] / p["E0c"]
        n = count(T, cbar)
        skip = sum(w[y] for y in {ev_year(m * cbar) for m in range(1, n + 1)})
        a += c["E0"] * rbar * (T - skip)
        # in-sample counterpart with the same weighting (parameters of the building itself)
        if c["E0c"]:
            cb = c["E0p"] / c["E0c"]
            n2 = count(T, cb)
            sk2 = sum(w[y] for y in {ev_year(m * cb) for m in range(1, n2 + 1)})
        else:
            sk2 = 0.0
        a_in += c["E0r"] * (T - sk2)
    err.append(a / r["B3"] - 1)
    tot.append((a - r["B3"]) / r["wlc"])
    err_in.append(a_in / r["B3"] - 1)
print("AP-18b with class parameters taken from OTHER buildings (first half -> second half), stage B3:", st(err))
print("   same, relative to the whole-life total:", st(tot))
print("AP-18b with the building's own parameters (in-sample, e0-weighted cycle), second half, stage B3:", st(err_in))
