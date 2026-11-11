"""Fictional scenario sets of the transformation study.

Every scenario comes from the frozen generator of the earlier study (``synth``): random,
fictional values, no real factors, service lives or rates. Results on these scenarios say
nothing about real buildings.

Sets (RESEARCH_PROTOCOL.md section 6.3):
  * ``design_set``      scenarios a data-driven transformation may be built from
  * ``evaluation_set``  disjoint scenarios used only to measure errors (out of sample)
  * ``edge_set``        the named boundary conditions of the generator
  * ``benchmark``       the three standard sizes S / M / L
``valid_domain`` checks the conditions under which the reference value may be used as the
baseline (archive INDEX.md section 6.1); scenarios outside are excluded and reported.
"""
from __future__ import annotations

import copy
import math
from typing import Iterable

from . import baseline

DESIGN_SEED = 710001
EVALUATION_SEED = 720002
SWEEP_PERIODS = (1.0, 7.5, 10.0, 20.0, 25.0, 30.0, 33.3, 40.0, 42.5, 50.0, 59.9, 60.0, 60.1, 62.5, 75.0, 99.9,
                 100.0, 120.0)
EPS = 1e-9          # relative tolerance of the reference time rules
EDGE_LO = 1e-10     # an event time whose relative distance d to T or to a whole year satisfies
EDGE_HI = 1e-8      # EDGE_LO < d < EDGE_HI sits at the tolerance itself: binary rounding decides (knife edge)


def _population():
    baseline.load()
    from synth import population  # frozen generator

    return population


def design_set(n: int = 120, max_size: str = "M") -> list:
    return list(_population().verification_population(n, DESIGN_SEED, max_size))


def evaluation_set(n: int = 120, max_size: str = "M") -> list:
    return list(_population().verification_population(n, EVALUATION_SEED, max_size))


def edge_set() -> list[tuple[str, object]]:
    return _population().edge_cases()


def benchmark() -> list:
    return _population().standard_benchmark()


def with_period(scn, period: float):
    """A copy of ``scn`` with another study period (the year tables must be long enough)."""
    out = copy.deepcopy(scn)
    out.boundary.study_period = float(period)
    out.meta.scenario_id = f"{scn.meta.scenario_id}@T{period:g}"
    return out


def _bad_number(v, lo: float = 0.0, hi: float = math.inf) -> bool:
    return v is not None and (isinstance(v, bool) or not isinstance(v, (int, float)) or math.isnan(v) or math.isinf(v)
                              or v < lo or v > hi)


def _knife_edge(period: float, T: float) -> bool:
    """True when an event time n*period lies at the tolerance of the time rule (relative distance
    between 1e-10 and 1e-8 to T or to a whole year), where the reference depends on binary rounding."""
    if period is None or not (period > 0.0) or math.isinf(period):
        return False
    n_max = int(min(T / period + 2, 100000))
    for n in range(1, n_max + 1):
        tau = n * period
        for target in (T, float(round(tau))):
            if target <= 0.0:
                continue
            d = abs(tau - target) / target
            if EDGE_LO < d < EDGE_HI:
                return True
    return False


def valid_domain(scn) -> list[str]:
    """Reasons why the reference value of ``scn`` must not be used as a baseline (empty = usable).

    Implements the conditions of the archive INDEX.md section 6.1 that can be read from the
    inputs. Missing values (None) in a row are allowed: the reference skips and counts the row.
    """
    why: list[str] = []
    T = scn.boundary.study_period
    if _bad_number(T) or T is None or not T > 0.0:
        return ["study period is not a finite positive number"]
    op = scn.operation
    profiles = {"electricity": op.electricity, "gas": op.gas, "oil": op.oil, "district_heat": op.district_heat,
                "onsite_generation": op.onsite_generation, "onsite_export": op.onsite_export,
                "water": scn.water_waste.water, "sewage": scn.water_waste.sewage,
                "municipal_waste": scn.water_waste.municipal_waste}
    need = math.ceil(T)
    for name, p in profiles.items():
        if p is None:
            continue
        table = p.table or []
        if any(v is None for v in table[:need]):
            why.append(f"{name}: None inside the year table")
        if any(_bad_number(v) for v in table[:need] if v is not None):
            why.append(f"{name}: negative or non-finite annual quantity")
        if p.kind == "TABLE" and len(table) < need:
            why.append(f"{name}: year table shorter than the study period")
        if _bad_number(p.base) or (p.slope is not None and (math.isnan(p.slope) or math.isinf(p.slope))):
            why.append(f"{name}: invalid descriptor")
    g = op.grid
    if len(g.table) < need:
        why.append("grid: year table shorter than the study period")
    if any(v is None or _bad_number(v) for v in g.table[:need]):
        why.append("grid: negative, missing or non-finite factor in the table")
    for name in ("start", "annual_decline", "floor"):
        if _bad_number(getattr(g, name)):
            why.append(f"grid: invalid {name}")
    for f in scn.factors.values() if isinstance(scn.factors, dict) else scn.factors:
        if f.value is not None and (isinstance(f.value, bool) or math.isnan(f.value) or math.isinf(f.value)):
            why.append(f"factor {f.factor_id}: non-finite value")
        if f.factor_id in ("GRID", "REFRIGERANT"):
            why.append(f"factor id {f.factor_id} collides with a pseudo key")
        if f.value == 0.0 and f.gas_amounts and any(v for v in (f.gas_amounts.values() if isinstance(f.gas_amounts, dict)
                                                                   else f.gas_amounts) if v):
            why.append(f"factor {f.factor_id}: value 0 with gas amounts")
    for c in scn.unit_conversions:
        if _bad_number(c.factor):
            why.append("unit conversion: negative or non-finite factor")
    cycles: list[tuple[str, float]] = []
    for row in scn.materials:
        for name in ("material_life", "refresh_cycle"):
            v = getattr(row, name)
            if v is not None:
                cycles.append((f"material {row.material_id}.{name}", v))
    for eq in scn.equipment:
        if eq.service_life is not None:
            cycles.append((f"equipment {eq.equipment_id}.service_life", eq.service_life))
    for dev in scn.refrigerants:
        if dev.service_life is not None:
            cycles.append((f"refrigerant {dev.device_id}.service_life", dev.service_life))
    if scn.boundary.replacement_cycle is not None:
        cycles.append(("boundary.replacement_cycle", scn.boundary.replacement_cycle))
    seen_bad = seen_edge = False
    for name, v in cycles:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or math.isnan(v) or math.isinf(v) or v <= 0.0:
            if not seen_bad:
                why.append(f"{name}: cycle is not a finite positive number")
                seen_bad = True
        elif not seen_edge and _knife_edge(float(v), float(T)):
            why.append(f"{name}: an event time lies on a knife edge of the time rule")
            seen_edge = True
    stages = list(scn.boundary.included_lifecycle_stages)
    if len(stages) != 14 and getattr(scn.meta, "injected_defects", None):
        why.append("stage subset together with injected defects")
    if getattr(scn.meta, "injected_defects", None):
        why.append("scenario carries injected defects (outside the clean generator range)")
    return why


def usable(scenarios: Iterable) -> tuple[list, list[tuple[str, list[str]]]]:
    """Split scenarios into those inside the valid domain and the excluded ones with reasons."""
    ok, out = [], []
    for scn in scenarios:
        why = valid_domain(scn)
        if why:
            out.append((scn.meta.scenario_id, why))
        else:
            ok.append(scn)
    return ok, out
