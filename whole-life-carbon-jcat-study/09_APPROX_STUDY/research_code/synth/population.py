"""Scenario sets used by the study: benchmark, verification population, edge cases.

All scenarios are fictional. ``edge_cases`` builds small scenarios and then
overwrites a few INPUT values to reach boundary conditions that a random draw
would hit only by accident; each overwrite keeps the scenario a valid input set.
"""
from __future__ import annotations

import copy
import random
from typing import Callable, Iterator

from .generate import make_scenario
from .model import (EOL_ROUTES, GRID_KINDS, PROFILE_KINDS, STATE_EXPLICIT_ZERO, STRUCTURES, USES,
                    AnnualProfile, Scenario)

BENCHMARK_SEEDS = {"S": 101, "M": 102, "L": 103}
STUDY_PERIODS = (30.0, 50.0, 60.0, 75.0, 100.0)
NON_INTEGER_PERIODS = (42.5, 62.5, 99.9)
SIZE_WEIGHTS = (("S", 0.65), ("M", 0.33), ("L", 0.02))
LIFE_MODES = ("MIXED", "EXACT_DIVISOR", "NON_DIVISOR", "CONTINUOUS", "INTEGER")
SMALL = {"n_materials": 12, "n_equipment": 6, "n_refrigerants": 4}

# Comparison baselines are a second INPUT scenario, looked up by scenario id
# (``Boundary.baseline_scenario`` holds the id of the baseline of a proposal).
BASELINES: dict[str, Scenario] = {}


def attach_baseline(proposal: Scenario) -> Scenario:
    """Create, register and link a fictional "before improvement" twin of ``proposal``.

    The twin has the same area, period, stages and factor table (so it is comparable),
    15 percent more electricity and gas demand, no on-site generation, and 20 percent
    larger quantities in every tenth material row.
    """
    base = copy.deepcopy(proposal)
    base.meta.scenario_id = proposal.meta.scenario_id + "-BASELINE"
    base.boundary.baseline_scenario = None
    op = base.operation
    for profile, scale in ((op.electricity, 1.15), (op.gas, 1.15), (op.onsite_generation, 0.0), (op.onsite_export, 0.0)):
        profile.table = [v * scale for v in profile.table]
        if profile.base is not None:
            profile.base *= scale
        if profile.slope is not None:
            profile.slope *= scale
    for row in base.materials[::10]:
        if row.quantity is not None:
            row.quantity *= 1.2
    BASELINES[base.meta.scenario_id] = base
    proposal.boundary.baseline_scenario = base.meta.scenario_id
    return base


def standard_benchmark() -> list[Scenario]:
    """The three benchmark scenarios (same structure and use, sizes S / M / L), each with a baseline twin."""
    out = [make_scenario(BENCHMARK_SEEDS[size], "RC", "office", size, 60.0) for size in ("S", "M", "L")]
    for scn in out:
        attach_baseline(scn)
    return out


def verification_population(n: int, seed: int, max_size: str = "L") -> Iterator[Scenario]:
    """``n`` varied valid scenarios covering every structure x use combination."""
    rng = random.Random(seed)
    combos = [(s, u) for s in STRUCTURES for u in USES]
    allowed = [(size, w) for size, w in SIZE_WEIGHTS if "SML".index(size) <= "SML".index(max_size)]
    for i in range(n):
        structure, use = combos[i % len(combos)]
        size = rng.choices([s for s, _ in allowed], weights=[w for _, w in allowed])[0]
        period = rng.choice(NON_INTEGER_PERIODS) if rng.random() < 0.15 else rng.choice(STUDY_PERIODS)
        options = {
            "service_life_mode": rng.choice(LIFE_MODES),
            "profile_kind": rng.choice((None,) + PROFILE_KINDS),
            "grid_kind": rng.choice((None,) + GRID_KINDS),
            "multi_use": rng.choice((None, True, False)),
        }
        if rng.random() < 0.25:
            options["replacement_cycle"] = float(rng.choice((20, 25, 30, 40)))
            options["reconstruction_scenario"] = rng.choice(("REBUILD_IDENTICAL", "MAJOR_REFURBISHMENT"))
        if rng.random() < 0.10:
            options["results_gas_scope"] = "CO2_ONLY"
        scn = make_scenario(rng.randrange(1, 10**9), structure, use, size, period, **options)
        if rng.random() < 0.20:
            attach_baseline(scn)
        yield scn


def _set_profile(profile: AnnualProfile, values: list[float]) -> None:
    profile.kind, profile.base, profile.slope, profile.table = "TABLE", None, None, list(values)


def _zero_quantities(s: Scenario) -> None:
    for row in s.materials[::2]:
        row.quantity = row.transport.mass_t = row.end_of_life.mass_kg = 0.0
        for name in ("quantity", "transport.mass_t", "end_of_life.mass_kg"):
            row.states[name] = STATE_EXPLICIT_ZERO
    for eq in s.equipment[::2]:
        eq.quantity = eq.end_of_life_mass_kg = 0.0
        eq.states["quantity"] = eq.states["end_of_life_mass_kg"] = STATE_EXPLICIT_ZERO


def _full_recycling(s: Scenario) -> None:
    for row in s.materials:
        for route in row.end_of_life.routes:
            route.fraction = 1.0 if route.route == "RECYCLE" else 0.0
    assert EOL_ROUTES[1] == "RECYCLE"


def _leak_extremes(s: Scenario) -> None:
    for i, dev in enumerate(s.refrigerants):
        dev.annual_leak_rate = (0.0, 1.0)[i % 2]
        dev.top_up = bool((i // 2) % 2)


def _recovery_extremes(s: Scenario) -> None:
    for i, dev in enumerate(s.refrigerants):
        dev.end_of_life_recovery_rate = (0.0, 1.0)[i % 2]
        dev.replacement_loss_rate = (0.0, 1.0)[(i // 2) % 2]


def _generation_exceeds(s: Scenario) -> None:
    op = s.operation
    gen = [v * 1.5 for v in op.electricity.table]
    _set_profile(op.onsite_generation, gen)
    _set_profile(op.onsite_export, [0.25 * v for v in gen])


def _grid_floor(s: Scenario) -> None:
    g = s.operation.grid
    g.kind, g.steps = "LINEAR_DECLINE_TO_FLOOR", None
    g.start = g.table[0] if g.table[0] > 0 else 0.5
    g.floor = 0.25 * g.start
    g.annual_decline = (g.start - g.floor) / 20.5  # floor is reached inside study year 21
    g.table = [max(g.floor, g.start - g.annual_decline * k) for k in range(len(g.table))]


def _waste_extremes(s: Scenario) -> None:
    for i, row in enumerate(s.materials):
        row.waste_rate = (0.0, 0.5, 0.9)[i % 3]


def _case(name: str, mutate: Callable[[Scenario], None] | None = None, period: float = 60.0,
          seed: int = 7, **options) -> tuple[str, Scenario]:
    opts = dict(SMALL)
    opts.update(options)
    scn = make_scenario(seed, "RC", "office", "S", period, scenario_id=f"EDGE-{name}", **opts)
    if mutate is not None:
        mutate(scn)
    scn.meta.notes.append(f"edge case: {name}")
    return name, scn


def edge_cases() -> list[tuple[str, Scenario]]:
    """Small named adversarial scenarios (all valid input sets)."""
    return [
        _case("exact_multiple_lives", service_life_choices=[5.0, 10.0, 12.0, 15.0, 20.0, 30.0],
              explicit_event_share=0.0, change_list_share=0.0),
        _case("life_equals_period", service_life_choices=[60.0], explicit_event_share=0.0, change_list_share=0.0),
        _case("life_longer_than_period", service_life_choices=[80.0, 150.0], explicit_event_share=0.0,
              change_list_share=0.0),
        _case("life_near_divisor", service_life_choices=[19.999999, 20.000001, 29.9999999, 30.0000001],
              explicit_event_share=0.0, change_list_share=0.0),
        _case("life_shorter_than_one_year", service_life_choices=[0.75, 0.5], explicit_event_share=0.0,
              change_list_share=0.0, period=10.0),
        _case("zero_quantities", _zero_quantities),
        _case("single_row", n_materials=1, n_equipment=1, n_refrigerants=1),
        _case("empty_lists", n_materials=0, n_equipment=0, n_refrigerants=0),
        _case("full_recycling", _full_recycling),
        _case("leak_rate_extremes", _leak_extremes, n_refrigerants=8),
        _case("recovery_extremes", _recovery_extremes, n_refrigerants=8),
        _case("generation_exceeds_consumption", _generation_exceeds),
        _case("grid_floor_mid_period", _grid_floor),
        _case("period_shorter_than_one_year", period=0.5),
        _case("period_non_integer", period=62.5),
        _case("period_just_above_integer", period=60.000001),
        _case("rebuild_within_period", replacement_cycle=25.0, reconstruction_scenario="REBUILD_IDENTICAL"),
        _case("refurbishment_divides_period", replacement_cycle=30.0, reconstruction_scenario="MAJOR_REFURBISHMENT"),
        _case("linear_trend_profiles", profile_kind="LINEAR_TREND", grid_kind="STEPWISE"),
        _case("table_profiles", profile_kind="TABLE", grid_kind="TABLE"),
        _case("constant_profiles", profile_kind="CONSTANT", grid_kind="CONSTANT"),
        _case("co2_only_scope", results_gas_scope="CO2_ONLY"),
        _case("stage_subset", included_stages=["A1-A3", "A4", "A5", "B6"]),
        _case("waste_rate_extremes", _waste_extremes),
        _case("all_composite", composite_share=1.0, epd_share=0.0),
        _case("no_composite", composite_share=0.0, epd_share=0.0),
        _case("all_epd", composite_share=0.0, epd_share=1.0, epd_inapplicable_share=0.5),
        _case("multi_use", multi_use=True),
        _case("explicit_event_lists", explicit_event_share=1.0, change_list_share=1.0),
        _case("top_up_all", top_up=True, n_refrigerants=8),
        _case("top_up_none", top_up=False, n_refrigerants=8),
        _case("with_baseline", lambda s: attach_baseline(s) and None),
    ]
