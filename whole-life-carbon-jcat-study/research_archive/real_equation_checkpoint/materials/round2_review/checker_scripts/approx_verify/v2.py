#!/usr/bin/env python3
"""Verifier's own check, pass 2: APP-5 (tolerance rule), APP-1 (analytic sign + adversarial synthetic inputs)."""
import math
import random

from refcalc import registry
from refcalc.base import periodic_events
from synth import make_scenario

registry.load_all()
EPS = 1e-9


def yw(T):
    return [0.0] + [min(1.0, T - (y - 1)) for y in range(1, math.ceil(T) + 1)]


def eyear(tau):
    return max(1, math.ceil(tau * (1 - EPS)))


print("== APP-5: reference count vs T/c - 1 near the boundary")
for T, k in ((60.0, 3), (60.0, 1), (100.0, 4), (30.0, 2)):
    for d in (5e-10, 9e-10, 2e-9):
        c = T * (1 - d) / k
        N = len(periodic_events(T, c))
        print(f"  T={T} c=T(1-{d:g})/{k}={c!r}: reference N={N}  T/c-1={T / c - 1:.12f}  lower>N: {max(0.0, T / c - 1) > N}  N<=T/c: {N <= T / c}")
T = 60.0
c = T * (1 - 5e-10) / 3
scn = make_scenario(11, "RC", "office", "S", T, n_materials=12, n_equipment=6, n_refrigerants=2,
                    service_life_choices=[c], explicit_event_share=0.0, change_list_share=0.0)
res = registry.run_all(scn)
B4 = res["X-02"]["by_stage_all"]["B4"]
cycles = {row.refresh_cycle for row in scn.materials} | {e.service_life for e in scn.equipment}
counts = set(res["B4-03"]["by_item"]) | {len(e) for e in res["B4-01"]["events"]}
# all rows have the same count 2 -> unit sum U = B4 / 2 ; AP-01 / AP-20 lower bound = U * (T/c - 1)
lo = B4 / 2 * (T / c - 1)
print(f"  scenario: cycles {cycles}, reference counts {counts}, B4={B4!r}, lower bound={lo!r}, (lo-B4)/B4={(lo - B4) / B4:.3e}, "
      f"study test lo <= B4*(1+1e-12): {lo <= B4 * (1 + 1e-12)}")
# does the study's own bracket code say the same?  (import only; nothing is written)
from bench import approx_study as A
rows = A.renewal_rows(scn, res)
from fastcalc import closed_forms as cf
lo2 = sum((r["n"] if r["explicit"] else (max(0.0, T / r["cycle"] - 1.0) if cf.valid_period(r["cycle"]) else 0.0)) * r["u"] for r in rows)
print(f"  study's own row data: lower bound={lo2!r}  inside test: {lo2 <= B4 * (1 + 1e-12)}  AP-01 error={(lo2 - B4) / B4:.3e}")

print("== APP-1: sign of true excluded weight - (T/c - 1), random (T, c), c >= 1")
rng = random.Random(5)
worst = float("inf"); worst_at = None; n = 0
for _ in range(400000):
    T = rng.choice((30.0, 42.5, 50.0, 60.0, 62.5, 75.0, 99.9, 100.0, round(rng.uniform(1.0, 120.0), 3)))
    c = rng.choice((round(rng.uniform(1.0, 130.0), 2), float(rng.randint(1, 120)), rng.uniform(1.0, 5.0)))
    w = yw(T)
    ev = periodic_events(T, c)
    true = sum(w[y] for y in {eyear(t) for t in ev})
    d = true - min(T, max(0.0, T / c - 1.0))
    n += 1
    if d < worst:
        worst, worst_at = d, (T, c, len(ev))
print(f"  {n} pairs: min(true - approx) = {worst:.3e} at (T, c, N) = {worst_at}")
worst = float("inf")
for _ in range(100000):
    T = round(rng.uniform(1.0, 120.0), 3)
    c = rng.uniform(0.05, 1.0)
    w = yw(T)
    ev = periodic_events(T, c)
    true = sum(w[y] for y in {eyear(t) for t in ev})
    d = true - min(T, max(0.0, T / c - 1.0))
    if d < worst:
        worst, worst_at = d, (T, c, len(ev))
print(f"  cycles below one year: min(true - approx) = {worst:.3e} at (T, c, N) = {worst_at}  (negative = candidate would under-estimate)")


def b3_forms(scn):
    res = registry.run_all(scn)
    T = scn.boundary.study_period
    w = yw(T)
    st = res["X-02"]["by_stage_all"]
    rowv = fixed = 0.0
    cls = {}
    for i, row in enumerate(scn.materials):
        r = row.repair_rate
        if r is None or not r >= 0:
            continue
        a = (res["A13-01"]["by_item"][i] + res["A13-03"]["by_item"][i]) * r
        c = row.refresh_cycle
        if c is not None and c > 0 and not math.isinf(c):
            rowv += a * (T - min(T, max(0.0, T / c - 1.0)))
            q = cls.setdefault(row.material_class, [0.0, 0.0]); q[0] += a; q[1] += a / c
        else:
            fixed += a * T
    for j, eq in enumerate(scn.equipment):
        r = eq.repair_rate
        if r is None or not r >= 0:
            continue
        a = res["X-01"]["by_item"][j] * r
        if eq.replacement_event_list is not None:
            fixed += a * (T - sum(w[y] for y in {eyear(t) for t in res["B4-01"]["events"][j]}))
        elif eq.service_life is not None and eq.service_life > 0:
            c = eq.service_life
            rowv += a * (T - min(T, max(0.0, T / c - 1.0)))
            q = cls.setdefault("EQUIPMENT", [0.0, 0.0]); q[0] += a; q[1] += a / c
        else:
            fixed += a * T
    clsv = fixed + sum(q[0] * (T - min(T, max(0.0, T * q[1] / q[0] - 1.0))) for q in cls.values() if q[0] > 0)
    B3 = st["B3"]
    return B3, (fixed + rowv) / B3 - 1, clsv / B3 - 1, res["B3-02"]["value"] / B3 - 1, (fixed + rowv - B3) / sum(st.values())


print("== APP-1: is 'inside the 2% stage target' a property of the candidate or of the generator's life mix?")
print("   (synthetic scenarios from the study's own generator, option service_life_choices; all lives >= 1 year)")
for T, lives in ((30.0, [29.0]), (30.0, [14.5, 29.0]), (30.0, [9.9, 14.9, 29.0]), (50.0, [49.0, 24.5]), (60.0, [59.0, 29.5, 19.6]),
                 (30.0, [7.0, 11.0, 13.0, 17.0, 23.0]), (60.0, [7.0, 11.0, 13.0, 17.0, 23.0, 37.0]), (100.0, [99.0, 49.5, 33.0])):
    errs = []
    for seed in range(20):
        scn = make_scenario(1000 + seed, ("RC", "S", "SRC", "W")[seed % 4], "office", "S", T, service_life_choices=lives,
                            explicit_event_share=0.0, change_list_share=0.0)
        errs.append(b3_forms(scn))
    print(f"   T={T} lives={lives}: row-level stage error {min(e[1] for e in errs):+.4f}..{max(e[1] for e in errs):+.4f}, class-level "
          f"{min(e[2] for e in errs):+.4f}..{max(e[2] for e in errs):+.4f}, AP-04 {min(e[3] for e in errs):+.4f}..{max(e[3] for e in errs):+.4f}, "
          f"total (row-level) max {max(e[4] for e in errs):+.4f}")
print("   service_life_mode NON_DIVISOR / CONTINUOUS, T=30 (default generator ranges):")
for mode in ("NON_DIVISOR", "CONTINUOUS", "INTEGER", "EXACT_DIVISOR"):
    errs = [b3_forms(make_scenario(2000 + seed, ("RC", "S", "SRC", "W")[seed % 4], ("office", "residential", "warehouse")[seed % 3], "S", 30.0,
                                   service_life_mode=mode)) for seed in range(40)]
    print(f"   mode {mode}: row-level {min(e[1] for e in errs):+.4f}..{max(e[1] for e in errs):+.4f}, class-level {min(e[2] for e in errs):+.4f}..{max(e[2] for e in errs):+.4f}")
