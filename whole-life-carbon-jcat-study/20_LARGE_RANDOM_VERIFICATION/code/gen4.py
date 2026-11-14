"""Stage 4: the declared sampling distribution of the large random verification (independent concept model,
fictional data; the frozen scenario generator of chapter 09 is used unchanged).

A case is (scenario, study period T). Scenario index i (0, 1, 2, ...) -> stratum and generator arguments, all drawn
from random.Random(SEED4 * 1_000_003 + i) (deterministic, independent of the order in which chunks are run).

Strata (probabilities):
  N  normal               0.40   valid scenarios like the verification population (size S 0.8 / M 0.2)
  B  boundary-heavy       0.20   valid scenarios; periods at and next to integers, event times, 0+ and H
  G  magnitudes           0.10   valid scenarios with every quantity and annual profile scaled by 10^U(-6, 6)
  E  coincident events    0.10   integer / divisor service lives from {10, 20, 30}, rebuild cycle 30, explicit lists
  S  special options      0.10   random subsets of the life-cycle stages in scope, CO2-only, explicit event lists,
                                 refrigerant change lists, top-up on/off, profile and grid kinds
  D  defects              0.10   dirty=True: missing / abnormal values injected by the generator (outside the
                                 reference's validity domain: compared without the domain filter, reported apart)
Periods per scenario: 5 (stratum-specific, below). Every period is <= H = 130.
"""
from __future__ import annotations

import copy
import math
import random

SEED4 = 20261114
STRATA = (("N", 0.40), ("B", 0.20), ("G", 0.10), ("E", 0.10), ("S", 0.10), ("D", 0.10))
STRUCTURES = ("S", "RC", "SRC", "W")
USES = ("office", "residential", "school", "hospital", "retail", "warehouse")
LIFE_MODES = ("MIXED", "EXACT_DIVISOR", "NON_DIVISOR", "CONTINUOUS", "INTEGER")
PROFILE_KINDS = ("CONSTANT", "LINEAR_TREND", "TABLE")
GRID_KINDS = ("CONSTANT", "LINEAR_DECLINE_TO_FLOOR", "STEPWISE", "TABLE")
STAGES = ("A1-A3", "A4", "A5", "B1", "B2", "B3", "B4", "B5", "B6", "B7", "C1", "C2", "C3", "C4")
H = 130.0


def rng_of(i: int) -> random.Random:
    return random.Random(SEED4 * 1_000_003 + i)


def stratum_of(r: random.Random) -> str:
    u, acc = r.random(), 0.0
    for s, p in STRATA:
        acc += p
        if u < acc:
            return s
    return STRATA[-1][0]


def plan(i: int) -> dict:
    """Generator arguments and period recipe of scenario i (no scenario object yet)."""
    r = rng_of(i)
    st = stratum_of(r)
    structure, use = r.choice(STRUCTURES), r.choice(USES)
    size = "M" if r.random() < (0.2 if st in ("N", "B") else 0.1) else "S"
    period = r.choice((30.0, 50.0, 60.0, 75.0, 100.0, 42.5, 62.5, 99.9))
    opt = {"service_life_mode": r.choice(LIFE_MODES), "profile_kind": r.choice((None,) + PROFILE_KINDS),
           "grid_kind": r.choice((None,) + GRID_KINDS), "multi_use": r.choice((None, True, False))}
    if r.random() < 0.25:
        opt["replacement_cycle"] = float(r.choice((20, 25, 30, 40)))
        opt["reconstruction_scenario"] = r.choice(("REBUILD_IDENTICAL", "MAJOR_REFURBISHMENT"))
    scale = None
    dirty = False
    if st == "G":
        scale = 10.0 ** r.uniform(-6.0, 6.0)
    elif st == "E":
        opt["service_life_mode"] = r.choice(("INTEGER", "EXACT_DIVISOR"))
        opt["service_life_choices"] = r.choice(([10.0, 20.0], [10.0, 20.0, 30.0], [20.0], [15.0, 30.0]))
        opt["replacement_cycle"] = 30.0
        opt["reconstruction_scenario"] = r.choice(("REBUILD_IDENTICAL", "MAJOR_REFURBISHMENT"))
        opt["explicit_event_share"] = r.choice((0.0, 0.5))
        opt["change_list_share"] = r.choice((0.0, 1.0))
        period = r.choice((60.0, 90.0, 120.0, 30.0))
    elif st == "S":
        stages = [s for s in STAGES if r.random() < 0.7] or ["A1-A3"]
        opt["included_stages"] = stages
        if r.random() < 0.3:
            opt["results_gas_scope"] = "CO2_ONLY"
        opt["explicit_event_share"] = r.choice((0.0, 0.3, 1.0))
        opt["change_list_share"] = r.choice((0.0, 0.5, 1.0))
        opt["top_up"] = r.choice((None, True, False))
    elif st == "D":
        dirty = True
    seed = r.randrange(1, 10 ** 9)
    periods = period_recipe(r, st)
    return dict(i=i, stratum=st, seed=seed, structure=structure, use=use, size=size, study_period=period, options=opt,
                scale=scale, dirty=dirty, periods=periods, baseline=(r.random() < 0.15))


def period_recipe(r: random.Random, st: str) -> list:
    """Periods as numbers or as recipes resolved against the scenario (own period, event times)."""
    lu = lambda: 10.0 ** r.uniform(-2.0, math.log10(H))
    if st == "B":
        out = []
        for _ in range(5):
            k = r.random()
            if k < 0.25:
                n = r.randint(1, 129)
                out.append(float(n) + r.choice((-1e-5, 0.0, 1e-5)))
            elif k < 0.6:
                out.append(("event", r.random(), r.choice((-1e-5, 0.0, 1e-5))))
            elif k < 0.75:
                out.append(r.uniform(0.001, 1.0))
            elif k < 0.85:
                out.append(H)
            else:
                out.append(("own", 0.0))
        return out
    return [("own", 0.0), r.uniform(0.5, H), r.uniform(0.5, H), lu(), float(r.randint(1, 130))]


def scale_scenario(scn, s: float):
    """Every quantity and annual profile multiplied by s (non-negative scaling keeps all physical constraints)."""
    c = copy.deepcopy(scn)
    for row in c.materials:
        if row.quantity is not None:
            row.quantity *= s
        if row.transport is not None and getattr(row.transport, "mass_t", None) is not None:
            row.transport.mass_t *= s
        if row.end_of_life is not None and getattr(row.end_of_life, "mass_kg", None) is not None:
            row.end_of_life.mass_kg *= s
    for eq in c.equipment:
        if eq.quantity is not None:
            eq.quantity *= s
        if getattr(eq, "end_of_life_mass_kg", None) is not None:
            eq.end_of_life_mass_kg *= s
    for d in c.refrigerants:
        if d.charge_mass_kg is not None:
            d.charge_mass_kg *= s
    op = c.operation
    profs = [op.electricity, op.gas, op.oil, op.district_heat, op.onsite_generation, op.onsite_export,
             c.water_waste.water, c.water_waste.sewage, c.water_waste.municipal_waste]
    for p in profs:
        if p is None:
            continue
        p.table = [v * s if v is not None else None for v in p.table]
        if p.base is not None:
            p.base *= s
        if p.slope is not None:
            p.slope *= s
    c.meta.scenario_id += "#x%.3g" % s
    return c


def make(p: dict):
    """The scenario of plan p (generator of chapter 09, unchanged)."""
    from synth import generate, population
    opt = {k: v for k, v in p["options"].items() if v is not None}
    scn = generate.make_scenario(p["seed"], p["structure"], p["use"], p["size"], p["study_period"], dirty=p["dirty"], **opt)
    if p["scale"] is not None:
        scn = scale_scenario(scn, p["scale"])
    if p["baseline"]:
        population.attach_baseline(scn)
    return scn


def resolve_periods(p: dict, scn, event_times: list) -> list:
    out = []
    for x in p["periods"]:
        if isinstance(x, (tuple, list)):
            if x[0] == "own":
                out.append(min(H, float(scn.boundary.study_period)))
            elif x[0] == "event":
                if event_times:
                    tau = event_times[min(len(event_times) - 1, int(x[1] * len(event_times)))]
                    T = tau + x[2]
                    out.append(min(H, max(1e-3, T)))
                else:
                    out.append(min(H, float(scn.boundary.study_period)))
        else:
            out.append(float(x))
    return out
