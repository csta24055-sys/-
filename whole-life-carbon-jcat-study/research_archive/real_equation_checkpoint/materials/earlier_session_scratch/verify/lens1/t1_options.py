"""Part 1: generator-option fuzz (no post-generation mutation except baselines)."""
import copy
import json
import math
import random
import sys
import time

sys.path.insert(0, "/tmp/claude-0/-home-user--/49c0bd7e-a786-5ae4-9a1e-e89e7996ede3/scratchpad/verify/lens1")
import h
import synth
from synth import model, population

N = int(sys.argv[1]) if len(sys.argv) > 1 else 900
SEED = int(sys.argv[2]) if len(sys.argv) > 2 else 777001
rng = random.Random(SEED)

PERIODS = [0.01, 0.25, 0.5, 0.999999, 1.0, 1.000001, 1.5, 2.0, 2.5, 3.0000001, 4.5, 9.99, 10.0, 10.0000001, 12.0,
           19.999999, 20.0, 24.0, 25.0, 29.9999999, 30.0, 30.0000001, 37.3, 42.5, 59.999999, 60.0, 60.000001, 62.5,
           75.0, 99.9, 100.0, 120.0, 149.5, 200.0, 299.999, 300.0]


def pick_period():
    r = rng.random()
    if r < 0.6:
        return rng.choice(PERIODS)
    if r < 0.8:
        return round(rng.uniform(0.01, 300.0), rng.choice((0, 1, 2, 6)))or 0.01
    if r < 0.9:
        return float(rng.randint(1, 300))
    k = rng.randint(1, 299)
    return k + rng.choice((1e-9, -1e-9, 1e-12, -1e-12, 2 ** -40, -2 ** -40))


def pick_lives(T):
    r = rng.random()
    if r < 0.35:
        return None
    pool = [T, T / 2, T / 3, T / 4, T / 5, T / 7, T / 10, T * 1.0000001, T * 0.9999999, T / 2 * 1.0000001, T / 3 * 0.9999999,
            0.01, 0.1, 0.3, 0.5, 0.75, 0.99, 0.999999999, 1.0, 1.0000000001, 1.1, 1.5, 2.0, 2.5, 3.0, 7.0, 7.3, 10.0, 12.5, 15.0,
            20.0, 25.0, 30.0, 33.333333333333336, 40.0, 59.5, 60.0, 61.0, 100.0, 500.0, math.nextafter(T, 0), math.nextafter(T, 1e9)]
    pool = [p for p in pool if p > 0 and (T / p) < 4000]
    k = rng.randint(1, 5)
    return [rng.choice(pool) for _ in range(k)]


def make():
    structure = rng.choice(model.STRUCTURES)
    use = rng.choice(model.USES)
    size = rng.choices(("S", "M"), weights=(0.97, 0.03))[0]
    T = pick_period()
    T = min(max(T, 0.01), 300.0)
    o = {}
    if size == "S":
        o["n_materials"] = rng.choice((0, 1, 2, 5, 12, 12, 30, 80, None))
        o["n_equipment"] = rng.choice((0, 1, 2, 6, 6, 20, None))
        o["n_refrigerants"] = rng.choice((0, 1, 2, 4, 8, None))
    if rng.random() < 0.3:
        o["gross_floor_area"] = rng.choice((1.0, 50.0, 333.3, 1e4, 1e6))
    o["multi_use"] = rng.choice((None, True, False))
    o["profile_kind"] = rng.choice((None,) + model.PROFILE_KINDS)
    o["grid_kind"] = rng.choice((None,) + model.GRID_KINDS)
    o["service_life_mode"] = rng.choice(("MIXED", "INTEGER", "EXACT_DIVISOR", "NON_DIVISOR", "CONTINUOUS"))
    lives = pick_lives(T)
    if lives is not None:
        o["service_life_choices"] = lives
    o["top_up"] = rng.choice((None, True, False))
    cs = rng.choice((0.0, 0.1, 0.3, 0.5, 1.0))
    es = rng.choice((0.0, 0.1, 0.5, 1.0))
    if cs + es > 1.0:
        es = 1.0 - cs
    o["composite_share"], o["epd_share"] = cs, es
    o["epd_inapplicable_share"] = rng.choice((0.0, 0.2, 0.5, 1.0))
    lo = rng.randint(1, 4)
    o["composite_components"] = (lo, lo + rng.randint(0, 5))
    o["composite_pool_ratio"] = rng.choice((0.0, 0.05, 0.25, 1.0))
    o["unit_variety"] = rng.random() < 0.7
    o["explicit_event_share"] = rng.choice((0.0, 0.15, 0.5, 1.0))
    o["change_list_share"] = rng.choice((0.0, 0.3, 1.0))
    if rng.random() < 0.3:
        o["study_start_year"] = rng.choice((1990, 2026, 2100))
    r = rng.random()
    if r < 0.5:
        o["replacement_cycle"] = rng.choice((T, T / 2, T / 3, T * 2, 0.5, 1.0, 7.3, 20.0, 25.0, 30.0, T * 0.9999999, T / 2 * 1.0000001))
        if T / o["replacement_cycle"] > 4000:
            o["replacement_cycle"] = T / 3
    o["reconstruction_scenario"] = rng.choice((None, "NONE", "REBUILD_IDENTICAL", "MAJOR_REFURBISHMENT"))
    o["results_gas_scope"] = rng.choice(("CO2E_ALL_GASES", "CO2E_ALL_GASES", "CO2_ONLY"))
    r = rng.random()
    if r < 0.35:
        k = rng.choice((0, 1, 1, 2, 3, 5, 8, 13))
        o["included_stages"] = rng.sample(list(model.LIFECYCLE_STAGES), k)
    if rng.random() < 0.2:
        o["table_length"] = max(130, math.ceil(T) + 1) + rng.randint(0, 50)
    dirty = rng.random() < 0.45
    if dirty:
        r = rng.random()
        if r < 0.5:
            o["defect_kinds"] = [rng.choice(model.DEFECT_KINDS)]
        elif r < 0.8:
            o["defect_kinds"] = rng.sample(list(model.DEFECT_KINDS), rng.randint(2, 5))
        o["defect_share"] = rng.choice((0.02, 0.1, 0.5, 1.0))
        o["state_variety"] = rng.random() < 0.6
    seed = rng.randrange(1, 10 ** 9)
    args = (seed, structure, use, size, T)
    return args, dirty, o


def baseline_variant(scn):
    """Attach a baseline; maybe make it non comparable."""
    r = rng.random()
    if r > 0.4:
        return None
    base = population.attach_baseline(scn)
    v = rng.choice(("comparable", "comparable", "area", "period", "stages", "scope", "version", "zero_base", "missing_id"))
    if v == "area":
        base.project.gross_floor_area = (base.project.gross_floor_area or 1.0) * 1.01
    elif v == "period":
        base.boundary.study_period = scn.boundary.study_period + 1.0
    elif v == "stages":
        base.boundary.included_lifecycle_stages = list(base.boundary.included_lifecycle_stages)[:-1] or ["A1-A3", "C4", "B7"]
    elif v == "scope":
        base.boundary.results_gas_scope = "CO2_ONLY" if scn.boundary.results_gas_scope != "CO2_ONLY" else "CO2E_ALL_GASES"
    elif v == "version":
        next(iter(base.factors.values())).release_year += 77
    elif v == "zero_base":
        base.boundary.included_lifecycle_stages = []
        scn.boundary.included_lifecycle_stages = []
    elif v == "missing_id":
        scn.boundary.baseline_scenario = "NO-SUCH-BASELINE"
    return v


sigs = {}
status_count = {}
t0 = time.perf_counter()
n_done = 0
gen_fail = {}
for it in range(N):
    args, dirty, o = make()
    try:
        scn = synth.make_scenario(*args, dirty=dirty, **o)
    except Exception as exc:
        gen_fail[type(exc).__name__ + ": " + str(exc)[:80]] = gen_fail.get(type(exc).__name__ + ": " + str(exc)[:80], 0) + 1
        continue
    bv = baseline_variant(scn)
    st, fs = h.diff(scn)
    n_done += 1
    status_count[st] = status_count.get(st, 0) + 1
    for f in fs:
        s = h.signature(f)
        rec = sigs.setdefault(s, {"count": 0, "examples": []})
        rec["count"] += 1
        if len(rec["examples"]) < 2:
            rec["examples"].append({"args": args, "dirty": dirty, "opts": o, "baseline": bv, "finding": f})
print(f"scenarios compared: {n_done}  ({time.perf_counter() - t0:.0f}s) status={status_count}")
print("generator refusals:", gen_fail)
for s, rec in sorted(sigs.items(), key=lambda kv: -kv[1]["count"]):
    print("\n==", s, "count", rec["count"])
    for ex in rec["examples"]:
        print("   ", json.dumps(ex, default=str)[:900])
