#!/usr/bin/env python3
"""Third pass (checker's own code): tolerance-rule counterexample for AP-01 / AP-20, AP-09c per stage,
robustness of the safe-side repair approximation (other seed, edge cases), AP-05 guard per variant."""
import math
import sys

import numpy as np

from refcalc import registry
from refcalc.base import periodic_events
from synth import population, make_scenario

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
        return "n=0"
    a = np.asarray(xs, float)
    return "n=%d mean %+.5f p95 %.5f min %+.3e max %+.5f under %.1f%%" % (len(xs), a.mean(), np.percentile(np.abs(a), 95), a.min(), a.max(), 100 * (a < -1e-12).mean())


# ---------------------------------------------------------------- 1. tolerance rule vs "T/c - 1 <= N"
print("== 1. count rule")
for T, k in ((60.0, 3), (60.0, 1), (100.0, 4)):
    c = T * (1 - 5e-10) / k
    N = len(periodic_events(T, c))
    print(f"T={T} c={c!r}: reference N={N}, T/c-1={T / c - 1!r}, max(0,T/c-1) > N: {max(0.0, T / c - 1) > N}, T/c={T / c!r}")
T = 60.0
c = T * (1 - 5e-10) / 3
scn = make_scenario(11, "RC", "office", "S", T, n_materials=12, n_equipment=6, n_refrigerants=2,
                    service_life_choices=[c], explicit_event_share=0.0, change_list_share=0.0)
res = registry.run_all(scn)
B4 = res["B4-02"]["value"]
# unit emissions from the reference rows themselves (every row has N = 2 here)
lo = hi = 0.0
for i, row in enumerate(scn.materials):
    n = res["B4-03"]["by_item"][i]
    u = res["B4-02"]["by_item_material"][i] / n
    lo += max(0.0, T / row.refresh_cycle - 1) * u
    hi += T / row.refresh_cycle * u
for j, eq in enumerate(scn.equipment):
    n = len(res["B4-01"]["events"][j])
    u = res["B4-02"]["by_item_equipment"][j] / n
    lo += max(0.0, T / eq.service_life - 1) * u
    hi += T / eq.service_life * u
print(f"scenario with every life = {c!r}: B4={B4!r} lower bound={lo!r}  (lower-B4)/B4={(lo - B4) / B4:.3e}  "
      f"study's inside test lo <= B4*(1+1e-12): {lo <= B4 * (1 + 1e-12)}; AP-01 max_over <= 1e-12: {(lo - B4) / B4 <= 1e-12}")
# N = 0 case: life just below T
c0 = T * (1 - 5e-10)
scn = make_scenario(11, "RC", "office", "S", T, n_materials=12, n_equipment=6, n_refrigerants=2,
                    service_life_choices=[c0], explicit_event_share=0.0, change_list_share=0.0)
res = registry.run_all(scn)
print(f"scenario with every life = {c0!r}: reference B4 = {res['B4-02']['value']!r}; AP-01 count per row = {max(0.0, T / c0 - 1)!r} (> 0 while reference count is 0)")

# ---------------------------------------------------------------- 2/4. AP-09c per stage, AP-05 guard, NEW-B3 on the study population
def b3_variants(scn, res):
    T = scn.boundary.study_period
    w = weights(T)
    S = res["X-02"]["by_stage_all"]
    mfg = [res["A13-01"]["by_item"][i] + res["A13-03"]["by_item"][i] for i in range(len(scn.materials))]
    fixed = rowlb = 0.0
    cls = {}
    for i, row in enumerate(scn.materials):
        r = row.repair_rate
        if not nonneg(r):
            continue
        e0r = mfg[i] * r
        if okp(row.refresh_cycle):
            c = cls.setdefault(row.material_class, [0.0, 0.0]); c[0] += e0r; c[1] += e0r / row.refresh_cycle
            rowlb += e0r * (T - min(T, max(0.0, T / row.refresh_cycle - 1.0)))
        else:
            fixed += e0r * T
    for j, eq in enumerate(scn.equipment):
        r = eq.repair_rate
        if not nonneg(r):
            continue
        e0r = res["X-01"]["by_item"][j] * r
        if eq.replacement_event_list is not None:
            fixed += e0r * (T - sum(w[y] for y in {ev_year(t) for t in res["B4-01"]["events"][j]}))
        elif okp(eq.service_life):
            c = cls.setdefault("EQUIPMENT", [0.0, 0.0]); c[0] += e0r; c[1] += e0r / eq.service_life
            rowlb += e0r * (T - min(T, max(0.0, T / eq.service_life - 1.0)))
        else:
            fixed += e0r * T
    cp = fixed + sum(c[0] * (T - min(T, max(0.0, T / (c[0] / c[1]) - 1.0))) for c in cls.values() if c[1])
    return S["B3"], fixed + rowlb, cp, sum(S.values())


def run_pop(label, scns):
    e_row, e_cls, t_row, t_cls, e04 = [], [], [], [], []
    zero = 0
    for scn in scns:
        res = registry.run_all(scn)
        ref, a_row, a_cls, wlc = b3_variants(scn, res)
        if ref == 0:
            zero += (a_row != 0) + (a_cls != 0)
            continue
        e_row.append(a_row / ref - 1); e_cls.append(a_cls / ref - 1)
        t_row.append((a_row - ref) / wlc); t_cls.append((a_cls - ref) / wlc)
        e04.append(res["B3-02"]["value"] / ref - 1)
    print(f"-- {label}: reference 0 with candidate nonzero: {zero}")
    print("   row level  skip=min(T,max(0,T/c-1))        stage:", st(e_row), "| total:", st(t_row))
    print("   class parameters (E0r, harmonic mean cycle)  stage:", st(e_cls), "| total:", st(t_cls))
    print("   AP-04 (no exclusion) for comparison          stage:", st(e04))


print("== 3. safe-side repair approximation")
run_pop("study population (400, seed 20261111, max M)", population.verification_population(400, seed=20261111, max_size="M"))
run_pop("other population (240, seed 777, max M)", population.verification_population(240, seed=777, max_size="M"))
run_pop("other population (48, seed 4242, max L)", population.verification_population(48, seed=4242, max_size="L"))
ec = population.edge_cases()
names = []
for name, scn in ec:
    try:
        res = registry.run_all(scn)
    except Exception as exc:
        names.append((name, "ERR " + str(exc)[:40]))
        continue
    ref, a_row, a_cls, wlc = b3_variants(scn, res)
    names.append((name, ref, (a_row / ref - 1) if ref else (a_row - ref), (a_cls / ref - 1) if ref else (a_cls - ref)))
print("-- edge cases (reference B3, row-level error, class-level error; absolute difference when reference is 0):")
for x in names:
    print("   ", x[0], " ".join(f"{v:+.5e}" if isinstance(v, float) else str(v) for v in x[1:]))

print("== 2. AP-09c per stage, AP-05 guard")
b2, b6, comb = [], [], []
guard = {"A": {"<=0.05": [], "<=0.2": [], ">0.2": []}, "B": {"<=0.05": [], "<=0.2": [], ">0.2": []}}
for scn in population.verification_population(400, seed=20261111, max_size="M"):
    res = registry.run_all(scn)
    T = scn.boundary.study_period
    w = weights(T)
    Y = len(w) - 1
    S = res["X-02"]["by_stage_all"]
    if res["X-06"]["source"] == "TABLE" and res["B6-01"]["computed"]:
        net, g, el = res["B6-04"]["by_year"], res["X-06"]["by_year"], res["B6-01"]["by_year"]
        elec = sum(w[y] * el[y] for y in range(1, Y + 1))
        conv = next(el[y] / (net[y] * g[y]) for y in range(1, Y + 1) if net[y] and g[y])
        knots = sorted(set(list(range(0, Y, 5)) + [Y - 1]))
        gi = np.interp(range(Y), knots, [g[k + 1] for k in knots])
        a = sum(w[y] * net[y] * gi[y - 1] for y in range(1, Y + 1)) * conv
        sh = scn.operation.facility_management_ratio
        b2.append(a * sh / S["B2"] - 1)
        b6.append((S["B6"] + (a - elec) * (1 - sh)) / S["B6"] - 1)
        comb.append((a - elec) / res["B6-03"]["value"])
    for d, dev in enumerate(scn.refrigerants):
        stt = res["B1-02"]["_state"][d]
        if stt is None or dev.top_up or not dev.gwp:
            continue
        m0, r = dev.charge_mass_kg, dev.annual_leak_rate
        L = dev.replacement_loss_rate if (dev.replacement_loss_rate is not None and 0 <= dev.replacement_loss_rate <= 1) else None
        R = dev.end_of_life_recovery_rate if (dev.end_of_life_recovery_rate is not None and 0 <= dev.end_of_life_recovery_rate <= 1) else None
        exact = res["B1-02"]["by_item"][d] / dev.gwp
        vb = va = m0 * r * T
        evs = {}
        for y, m in stt["before_events"]:
            evs[y] = evs.get(y, 0) + 1
            if L is not None:
                exact += m * L
                vb += m0 * L
        acc = 0.0
        for y in range(1, Y + 1):
            acc += w[y]
            for _ in range(evs.get(y, 0)):
                if L is not None:
                    va += m0 * max(0.0, 1 - r * acc) * L
                acc = 0.0
        if R is not None:
            exact += stt["end"] * (1 - R)
            vb += m0 * (1 - R)
            va += m0 * max(0.0, 1 - r * acc) * (1 - R)
        if exact > 0:
            rk = r * T / (len(stt["before_events"]) + 1)
            key = "<=0.05" if rk <= 0.05 else "<=0.2" if rk <= 0.2 else ">0.2"
            guard["A"][key].append(va / exact - 1)
            guard["B"][key].append(vb / exact - 1)
print("AP-09c measured on B6-03 (study's quantity):", st(comb))
print("AP-09c on stage B6 (= B6-03 - B2-01):      ", st(b6))
print("AP-09c on stage B2 (= B2-01):              ", st(b2), "| scenarios with |error| > 2%:", sum(abs(x) > 0.02 for x in b2), "max abs", max(abs(x) for x in b2))
for v in ("B", "A"):
    for k, xs in guard[v].items():
        print(f"AP-05 per device, variant {v} ({'full charge everywhere' if v == 'B' else 'remaining m0*(1-rk)'}), r*k {k}: {st(xs)}")
