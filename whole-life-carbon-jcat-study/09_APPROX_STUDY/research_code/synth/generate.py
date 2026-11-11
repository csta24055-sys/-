"""Seeded generator of fictional scenarios (research tooling only).

EVERY NUMBER PRODUCED HERE IS SYNTHETIC AND FICTIONAL. Values are drawn from
``random.Random`` instances derived from the caller's seed; the global random
state and the clock are never used. The ranges and multiplier tables below are
ILLUSTRATIVE ONLY: they were invented for this study so that formulas can be
exercised on inputs of plausible shape. None of them is taken from J-CAT or
from any real emission-factor, service-life, repair-rate, leakage-rate or
multiplier table. Results obtained on this data say nothing about accuracy on
real buildings.

Each section of a scenario uses its own random sub-stream (seed + section
name), so changing an option of one section leaves the other sections as they
were, and a dirty scenario equals the clean scenario of the same seed except
for the listed defects and state markers.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any, Optional, Sequence

from .model import (
    DATA_QUALITIES, DEFECT_KINDS, EOL_ROUTES, EQUIPMENT_TRADES, GAS_SCOPES, GASES, GRID_KINDS,
    LICENCE_PERMISSION_REQUIRED, LICENCE_PERMITTED, LICENCE_RESTRICTED, LICENCE_UNKNOWN,
    LIFECYCLE_STAGES, PROFILE_KINDS, RECONSTRUCTION_SCENARIOS, REFRIGERANT_APPLICATIONS,
    SIZE_CLASSES, SOURCE_TAG, STAGE_MEMO, STATE_DERIVED, STATE_ESTIMATE, STATE_EXPLICIT_ZERO,
    STATE_MISSING, STATE_OBSERVED, STRUCTURES, TRANSPORT_MODES, USES, YEAR_TABLE_MIN_LENGTH,
    AnnualProfile, Boundary, CompositeComponent, ConstructionSite, Defect, DemolitionActivity,
    EndOfLife, EolRoute, EpdReference, EquipmentRow, FactorRecord, GridFactorScenario, GridStep,
    MaterialEndOfLife, MaterialRow, Operation, Project, Provenance, RefrigerantDevice, Scenario,
    ScenarioMeta, SiteFuel, SiteWaste, SummaryQuantities, TransportLeg, UnitConversion, WasteHaul,
    WaterWaste, base_unit_conversions, conversion_factor, used_factor_ids,
)

GENERATOR_VERSION = "1.0"

# --------------------------------------------------------------------------
# Size classes (change here to rescale the benchmark)
# --------------------------------------------------------------------------
MATERIAL_ROWS: dict[str, int] = {"S": 200, "M": 2000, "L": 20000}
EQUIPMENT_ROWS: dict[str, int] = {"S": 60, "M": 600, "L": 6000}
REFRIGERANT_DEVICES: dict[str, int] = {"S": 5, "M": 40, "L": 300}
COMPOSITE_SHARE = 0.30                    # share of material rows that are composites
COMPOSITE_COMPONENTS = (3, 12)            # components per composite (min, max)
SPEC_COUNT: dict[str, int] = {"S": 4, "M": 8, "L": 16}        # generic specs per class / trade
COMPONENT_POOL: dict[str, int] = {"S": 30, "M": 80, "L": 200}  # per-kg component factors
MAX_STUDY_PERIOD = 300.0

SERVICE_LIFE_MODES: tuple[str, ...] = ("MIXED", "INTEGER", "EXACT_DIVISOR", "NON_DIVISOR", "CONTINUOUS")
EPD_INAPPLICABLE_REASONS: tuple[str, ...] = ("EXPIRED", "STAGE_MISMATCH", "UNIT_MISMATCH")
UNKNOWN_UNIT = "piece"                    # a unit with no documented conversion

# --------------------------------------------------------------------------
# FICTIONAL, ILLUSTRATIVE generator tables (invented; not from any data source)
# --------------------------------------------------------------------------

# FICTIONAL gross floor area range (m2), storeys and site duration (months) per size class.
GFA_RANGE: dict[str, tuple[float, float]] = {
    "S": (800.0, 3000.0), "M": (5000.0, 20000.0), "L": (30000.0, 120000.0),
}
FLOORS_RANGE: dict[str, tuple[int, int]] = {"S": (1, 5), "M": (3, 15), "L": (8, 40)}
SITE_DURATION_RANGE: dict[str, tuple[float, float]] = {
    "S": (6.0, 14.0), "M": (12.0, 30.0), "L": (24.0, 60.0),
}


@dataclass(frozen=True, slots=True)
class ClassSpec:
    """FICTIONAL description of a material class used by the generator."""

    unit: str                              # canonical quantity unit of the class
    intensity: tuple[float, float]         # FICTIONAL quantity per m2 of floor area
    mass_per_unit: tuple[float, float]     # FICTIONAL kg per canonical unit
    divisions: tuple[str, ...]             # divisions in which the class may appear


CLASS_SPECS: dict[str, ClassSpec] = {
    "CONCRETE": ClassSpec("m3", (0.25, 0.90), (1800.0, 2600.0), ("FOUNDATION", "STRUCTURE")),
    "REBAR": ClassSpec("kg", (20.0, 120.0), (1.0, 1.0), ("FOUNDATION", "STRUCTURE")),
    "STRUCTURAL_STEEL": ClassSpec("kg", (10.0, 150.0), (1.0, 1.0), ("STRUCTURE",)),
    "TIMBER": ClassSpec("m3", (0.005, 0.20), (350.0, 700.0), ("STRUCTURE", "INTERIOR")),
    "MASONRY": ClassSpec("m2", (0.05, 0.60), (80.0, 300.0), ("ROOF_EXTERIOR_WALL", "INTERIOR")),
    "GLASS": ClassSpec("m2", (0.05, 0.40), (15.0, 60.0), ("OPENINGS",)),
    "ALUMINIUM": ClassSpec("kg", (0.5, 8.0), (1.0, 1.0), ("OPENINGS", "ROOF_EXTERIOR_WALL")),
    "INSULATION": ClassSpec("m2", (0.3, 1.5), (1.0, 12.0), ("ROOF_EXTERIOR_WALL",)),
    "BOARD": ClassSpec("m2", (0.8, 3.5), (6.0, 25.0), ("INTERIOR",)),
    "FINISH": ClassSpec("m2", (1.0, 4.0), (1.0, 30.0), ("INTERIOR",)),
    "MEMBRANE": ClassSpec("m2", (0.2, 1.2), (1.0, 10.0), ("ROOF_EXTERIOR_WALL", "FOUNDATION")),
    "PLASTIC": ClassSpec("kg", (0.2, 4.0), (1.0, 1.0), ("INTERIOR", "OPENINGS")),
    "MORTAR": ClassSpec("kg", (5.0, 60.0), (1.0, 1.0), ("INTERIOR", "ROOF_EXTERIOR_WALL")),
}

# FICTIONAL multipliers by structure type: relative number of rows of a class
# and relative quantity of a class. Classes not listed use 1.0.
STRUCTURE_CLASS_WEIGHT: dict[str, dict[str, float]] = {
    "S": {"CONCRETE": 1.0, "REBAR": 0.8, "STRUCTURAL_STEEL": 2.0, "TIMBER": 0.3},
    "RC": {"CONCRETE": 2.0, "REBAR": 1.8, "STRUCTURAL_STEEL": 0.4, "TIMBER": 0.3},
    "SRC": {"CONCRETE": 1.8, "REBAR": 1.6, "STRUCTURAL_STEEL": 1.4, "TIMBER": 0.2},
    "W": {"CONCRETE": 0.8, "REBAR": 0.6, "STRUCTURAL_STEEL": 0.2, "TIMBER": 2.5},
}
STRUCTURE_QUANTITY_MULT: dict[str, dict[str, float]] = {
    "S": {"CONCRETE": 0.7, "REBAR": 0.6, "STRUCTURAL_STEEL": 1.5, "TIMBER": 0.3},
    "RC": {"CONCRETE": 1.3, "REBAR": 1.3, "STRUCTURAL_STEEL": 0.2, "TIMBER": 0.3},
    "SRC": {"CONCRETE": 1.2, "REBAR": 1.2, "STRUCTURAL_STEEL": 0.9, "TIMBER": 0.2},
    "W": {"CONCRETE": 0.4, "REBAR": 0.35, "STRUCTURAL_STEEL": 0.1, "TIMBER": 3.0},
}

# FICTIONAL multipliers by building use.
USE_QUANTITY_MULT: dict[str, float] = {
    "office": 1.00, "residential": 0.90, "school": 0.95, "hospital": 1.25, "retail": 0.85, "warehouse": 0.60,
}
USE_EQUIPMENT_MULT: dict[str, float] = {
    "office": 1.0, "residential": 0.7, "school": 0.8, "hospital": 1.8, "retail": 1.1, "warehouse": 0.4,
}
USE_OPERATION_MULT: dict[str, float] = {
    "office": 1.0, "residential": 0.6, "school": 0.7, "hospital": 1.9, "retail": 1.4, "warehouse": 0.35,
}
USE_WATER_MULT: dict[str, float] = {
    "office": 1.0, "residential": 1.6, "school": 0.9, "hospital": 2.2, "retail": 0.8, "warehouse": 0.2,
}
USE_REFRIGERANT_MULT: dict[str, float] = {
    "office": 1.0, "residential": 0.5, "school": 0.6, "hospital": 1.5, "retail": 1.8, "warehouse": 0.8,
}
# FICTIONAL relative number of equipment rows per trade (order of EQUIPMENT_TRADES) by use.
USE_TRADE_WEIGHT: dict[str, tuple[float, float, float, float]] = {
    "office": (0.35, 0.35, 0.22, 0.08),
    "residential": (0.30, 0.25, 0.35, 0.10),
    "school": (0.35, 0.30, 0.30, 0.05),
    "hospital": (0.30, 0.40, 0.25, 0.05),
    "retail": (0.40, 0.35, 0.15, 0.10),
    "warehouse": (0.45, 0.25, 0.15, 0.15),
}

# FICTIONAL service-life ranges (years).
DIVISION_LIFE_RANGE: dict[str, tuple[float, float]] = {
    "FOUNDATION": (60.0, 150.0), "STRUCTURE": (60.0, 150.0), "ROOF_EXTERIOR_WALL": (15.0, 60.0),
    "OPENINGS": (20.0, 50.0), "INTERIOR": (5.0, 40.0),
}
TRADE_LIFE_RANGE: dict[str, tuple[float, float]] = {
    "ELECTRICAL": (10.0, 40.0), "HVAC": (8.0, 30.0), "PLUMBING": (10.0, 40.0), "CONVEYANCE": (15.0, 40.0),
}
REFRIGERANT_LIFE_RANGE: tuple[float, float] = (8.0, 30.0)

# FICTIONAL factor magnitudes: value = 10 ** uniform(lo, hi) kgCO2e per unit.
FACTOR_LOG10_RANGE: dict[str, tuple[float, float]] = {
    "kg": (-1.3, 0.9), "m3": (1.5, 3.0), "m2": (0.0, 2.2),
    "COMPONENT": (-1.3, 1.0), "TRANSPORT": (-1.6, -0.5), "HAUL": (-1.4, -0.5), "EOL": (-2.5, -0.6),
    "EQUIPMENT": (1.5, 4.5), "EQUIPMENT_DELIVERY": (0.0, 2.0), "EQUIPMENT_INSTALLATION": (0.0, 2.0),
    "EQUIPMENT_EOL": (-2.0, -0.3),
    "FUEL_L": (0.2, 0.6), "FUEL_M3": (0.1, 0.5), "FUEL_MJ": (-1.5, -1.0),
    "SITE_WASTE": (-2.0, -0.3), "WATER": (-1.0, 0.0), "SEWAGE": (-0.8, 0.2), "MSW": (-1.5, 0.0),
    "DEMOLITION_M2": (0.3, 1.5), "DEMOLITION_H": (0.8, 2.0), "UPTAKE": (0.0, 1.5),
}
# FICTIONAL delivery / installation factors as a share of the class factor.
DELIVERY_SHARE_RANGE = (0.01, 0.08)
INSTALLATION_SHARE_RANGE = (0.01, 0.06)

# FICTIONAL transport distance ranges (km) per mode and mode weights.
TRANSPORT_DISTANCE: dict[str, tuple[float, float]] = {
    "TRUCK_SMALL": (5.0, 80.0), "TRUCK_LARGE": (20.0, 400.0), "RAIL": (100.0, 900.0), "SHIP": (300.0, 5000.0),
}
TRANSPORT_MODE_WEIGHT = (0.35, 0.45, 0.10, 0.10)

SITE_WASTE_KINDS: tuple[str, ...] = ("CONCRETE_RUBBLE", "WOOD", "METAL", "MIXED", "PLASTIC", "BOARD")
# (activity id, unit, FICTIONAL quantity per m2 of floor area, factor family)
DEMOLITION_ACTIVITIES: tuple[tuple[str, str, tuple[float, float], str], ...] = (
    ("MACHINE_DEMOLITION", "m2", (0.9, 1.1), "DEMOLITION_M2"),
    ("STRIP_OUT", "m2", (0.5, 1.0), "DEMOLITION_M2"),
    ("MACHINE_FUEL", "L", (0.5, 6.0), "FUEL_L"),
    ("SITE_CLEARANCE", "h", (0.01, 0.2), "DEMOLITION_H"),
)

# --------------------------------------------------------------------------
# Options of make_scenario
# --------------------------------------------------------------------------
DEFAULT_OPTIONS: dict[str, Any] = {
    "n_materials": None,
    "n_equipment": None,
    "n_refrigerants": None,
    "gross_floor_area": None,
    "multi_use": None,
    "profile_kind": None,
    "grid_kind": None,
    "service_life_mode": "MIXED",
    "service_life_choices": None,
    "top_up": None,
    "epd_share": 0.10,
    "epd_inapplicable_share": 0.20,
    "composite_share": COMPOSITE_SHARE,
    "composite_components": COMPOSITE_COMPONENTS,
    "composite_pool_ratio": 0.25,
    "unit_variety": True,
    "explicit_event_share": 0.15,
    "change_list_share": 0.30,
    "study_start_year": None,
    "replacement_cycle": None,
    "reconstruction_scenario": None,
    "results_gas_scope": "CO2E_ALL_GASES",
    "included_stages": None,
    "baseline_scenario": None,
    "table_length": None,
    "defect_share": 0.02,
    "defect_kinds": None,
    "state_variety": True,
    "scenario_id": None,
}

OPTION_HELP: dict[str, str] = {
    "n_materials": "number of material rows (default: by size class)",
    "n_equipment": "number of equipment rows (default: by size class)",
    "n_refrigerants": "number of refrigerant devices (default: by size class)",
    "gross_floor_area": "target gross floor area in m2 (default: drawn by size class)",
    "multi_use": "True/False forces a multi-use / single-use area breakdown (default: random)",
    "profile_kind": "force the kind of every annual quantity profile: CONSTANT, LINEAR_TREND or TABLE",
    "grid_kind": "force the grid scenario kind: CONSTANT, LINEAR_DECLINE_TO_FLOOR, STEPWISE or TABLE",
    "service_life_mode": "MIXED, INTEGER, EXACT_DIVISOR (lives divide the study period exactly), "
                         "NON_DIVISOR or CONTINUOUS",
    "service_life_choices": "explicit list of lives (years); every life is drawn from it",
    "top_up": "True/False forces the refrigerant top-up flag (default: random per device)",
    "epd_share": "share of material rows with a product-specific (EPD-like) factor",
    "epd_inapplicable_share": "share of those rows whose EPD is expired, off-stage or off-unit",
    "composite_share": "share of material rows that are composites",
    "composite_components": "(min, max) number of components of a composite",
    "composite_pool_ratio": "number of distinct composite recipes as a share of composite rows",
    "unit_variety": "False keeps every quantity in the unit of its factor (no conversions needed)",
    "explicit_event_share": "share of equipment rows with an explicit replacement_event_list",
    "change_list_share": "share of refrigerant devices with explicit change_years",
    "study_start_year": "calendar year of the first study year (default: random fictional year)",
    "replacement_cycle": "building replacement cycle in years (default: not shorter than the study period)",
    "reconstruction_scenario": "NONE, REBUILD_IDENTICAL or MAJOR_REFURBISHMENT (default: random)",
    "results_gas_scope": "CO2E_ALL_GASES or CO2_ONLY",
    "included_stages": "list of life-cycle stages in scope (default: all)",
    "baseline_scenario": "scenario id recorded as comparison baseline",
    "table_length": "length of the year tables (default: max(130, ceil(study period) + 1))",
    "defect_share": "dirty=True: share of rows that receive each kind of defect (at least one each)",
    "defect_kinds": "dirty=True: list of defect kinds to inject (default: all of model.DEFECT_KINDS)",
    "state_variety": "dirty=True: also mark some rows ESTIMATE / DERIVED / EXPLICIT_ZERO (not defects)",
    "scenario_id": "identifier stored in meta (default: built from the arguments)",
}

# Formula ids expected to react to each defect kind.
DEFECT_RELATED_CHECKS: dict[str, tuple[str, ...]] = {
    "MISSING_VALUE": ("SYS-01",),
    "UNKNOWN_LICENCE": ("SYS-03", "QA-03"),
    "UNIT_MISMATCH": ("SYS-02",),
    "COMPOSITE_FRACTION_SUM": ("A13-02",),
    "ROUTE_FRACTION_SUM": ("C-05",),
    "NON_POSITIVE_AREA": ("SYS-04", "QA-04", "SUM-04", "SUM-05"),
    "AREA_BREAKDOWN_MISMATCH": ("SYS-04", "QA-04"),
    "EVENT_OUTSIDE_PERIOD": ("QA-02",),
}


# --------------------------------------------------------------------------
# Small pure helpers
# --------------------------------------------------------------------------

def is_exact_divisor(period: float, life: float) -> bool:
    """True when ``period`` is an exact integer multiple of ``life`` (as floats, no rounding)."""
    return life > 0.0 and math.fmod(period, life) == 0.0


def is_near_divisor(period: float, life: float, rel_tol: float = 1e-6) -> bool:
    """True when ``life`` is not an exact divisor but period/life is within rel_tol of an integer."""
    if life <= 0.0:
        return False
    rem = math.fmod(period, life)
    if rem == 0.0:
        return False
    return min(rem, life - rem) < rel_tol * life


def exact_divisor_lives(period: float, lo: float, hi: float) -> list[float]:
    """Lives period/n inside [lo, hi] that divide ``period`` exactly; [period] when there is none."""
    out: list[float] = []
    for n in range(1, 5001):
        life = period / n
        if life < lo:
            break
        if life <= hi and is_exact_divisor(period, life):
            out.append(life)
    return out or [period]


def normalised_fractions(weights: Sequence[float], digits: int) -> list[float]:
    """Fractions proportional to ``weights``, rounded, with the largest absorbing the remainder."""
    total = sum(weights)
    fractions = [round(w / total, digits) for w in weights]
    k = max(range(len(fractions)), key=fractions.__getitem__)
    rest = 0.0
    for i, value in enumerate(fractions):
        if i != k:
            rest += value
    fractions[k] = 1.0 - rest
    return fractions


def co2e_of(gas_amounts: dict[str, float], gwp: dict[str, float]) -> float:
    """sum(gwp[g] * amount[g]) in the canonical gas order."""
    total = 0.0
    for gas in GASES:
        total += gwp[gas] * gas_amounts[gas]
    return total


def constant_profile(value: float, unit: str, length: int) -> AnnualProfile:
    return AnnualProfile("CONSTANT", unit, value, None, [value] * length)


def linear_profile(base: float, slope: float, unit: str, length: int) -> AnnualProfile:
    return AnnualProfile("LINEAR_TREND", unit, base, slope, [base + slope * k for k in range(length)])


def table_profile(values: Sequence[float], unit: str) -> AnnualProfile:
    return AnnualProfile("TABLE", unit, None, None, [float(v) for v in values])


def scaled_profile(profile: AnnualProfile, share: float) -> AnnualProfile:
    """A profile of the same kind whose values are ``share`` times those of ``profile``."""
    length = len(profile.table)
    if profile.kind == "CONSTANT":
        return constant_profile(profile.base * share, profile.unit, length)
    if profile.kind == "LINEAR_TREND":
        return linear_profile(profile.base * share, profile.slope * share, profile.unit, length)
    return table_profile([v * share for v in profile.table], profile.unit)


def grid_table(
    kind: str,
    length: int,
    start: Optional[float] = None,
    annual_decline: Optional[float] = None,
    floor: Optional[float] = None,
    steps: Optional[Sequence[GridStep]] = None,
) -> list[float]:
    """Year table implied by a grid descriptor (not defined for kind TABLE)."""
    if kind == "CONSTANT":
        return [start] * length
    if kind == "LINEAR_DECLINE_TO_FLOOR":
        return [max(floor, start - annual_decline * k) for k in range(length)]
    if kind == "STEPWISE":
        table: list[float] = []
        position, current = 0, steps[0].value
        for k in range(length):
            while position < len(steps) and steps[position].from_index <= k:
                current = steps[position].value
                position += 1
            table.append(current)
        return table
    raise ValueError(f"no closed form for grid kind {kind!r}")


def blended_multiplier(table: dict[str, float], breakdown: dict[str, float]) -> float:
    """Area-weighted mean of a per-use multiplier over a use-area breakdown."""
    total = sum(breakdown.values())
    if total <= 0.0:
        return 1.0
    return sum(table[use] * area for use, area in breakdown.items()) / total


# --------------------------------------------------------------------------
# Generation context
# --------------------------------------------------------------------------

@dataclass(slots=True)
class _Ctx:
    seed: int
    structure: str
    use: str
    size_class: str
    period: float
    opts: dict[str, Any]
    table_length: int
    start_year: int = 0
    assessment_date: str = ""
    _divisor_cache: dict[tuple[float, float], list[float]] = field(default_factory=dict)

    def rng(self, name: str) -> random.Random:
        """Independent random sub-stream of one section (string seeds hash deterministically)."""
        return random.Random(f"wlc-synth/{GENERATOR_VERSION}/{self.seed}/{name}")

    def divisor_lives(self, lo: float, hi: float) -> list[float]:
        key = (lo, hi)
        if key not in self._divisor_cache:
            self._divisor_cache[key] = exact_divisor_lives(self.period, lo, hi)
        return self._divisor_cache[key]


def _resolve_options(options: dict[str, Any]) -> dict[str, Any]:
    unknown = sorted(set(options) - set(DEFAULT_OPTIONS))
    if unknown:
        raise TypeError(f"unknown option(s) {unknown}; known options: {sorted(DEFAULT_OPTIONS)}")
    opts = dict(DEFAULT_OPTIONS)
    opts.update(options)
    if opts["profile_kind"] is not None and opts["profile_kind"] not in PROFILE_KINDS:
        raise ValueError(f"profile_kind must be one of {PROFILE_KINDS}")
    if opts["grid_kind"] is not None and opts["grid_kind"] not in GRID_KINDS:
        raise ValueError(f"grid_kind must be one of {GRID_KINDS}")
    if opts["service_life_mode"] not in SERVICE_LIFE_MODES:
        raise ValueError(f"service_life_mode must be one of {SERVICE_LIFE_MODES}")
    if opts["results_gas_scope"] not in GAS_SCOPES:
        raise ValueError(f"results_gas_scope must be one of {GAS_SCOPES}")
    if opts["reconstruction_scenario"] is not None and opts["reconstruction_scenario"] not in RECONSTRUCTION_SCENARIOS:
        raise ValueError(f"reconstruction_scenario must be one of {RECONSTRUCTION_SCENARIOS}")
    for name in ("epd_share", "epd_inapplicable_share", "composite_share", "explicit_event_share",
                 "change_list_share", "defect_share", "composite_pool_ratio"):
        if not 0.0 <= float(opts[name]) <= 1.0:
            raise ValueError(f"{name} must lie in [0, 1]")
    if opts["composite_share"] + opts["epd_share"] > 1.0 + 1e-12:
        raise ValueError("composite_share + epd_share must not exceed 1")
    lo, hi = opts["composite_components"]
    if not 1 <= int(lo) <= int(hi):
        raise ValueError("composite_components must be (min, max) with 1 <= min <= max")
    opts["composite_components"] = (int(lo), int(hi))
    if opts["service_life_choices"] is not None:
        choices = [float(v) for v in opts["service_life_choices"]]
        if not choices or min(choices) <= 0.0:
            raise ValueError("service_life_choices must be a non-empty list of positive lives")
        opts["service_life_choices"] = choices
    if opts["defect_kinds"] is not None:
        kinds = list(opts["defect_kinds"])
        bad = [k for k in kinds if k not in DEFECT_KINDS]
        if bad:
            raise ValueError(f"unknown defect kind(s) {bad}; known: {DEFECT_KINDS}")
        opts["defect_kinds"] = kinds
    if opts["included_stages"] is not None:
        stages = list(opts["included_stages"])
        bad = [s for s in stages if s not in LIFECYCLE_STAGES]
        if bad:
            raise ValueError(f"unknown life-cycle stage(s) {bad}")
        opts["included_stages"] = stages
    for name in ("n_materials", "n_equipment", "n_refrigerants"):
        if opts[name] is not None and int(opts[name]) < 0:
            raise ValueError(f"{name} must not be negative")
    return opts


def _json_options(opts: dict[str, Any]) -> dict[str, Any]:
    """Options as JSON-native values (tuples become lists)."""
    return {k: (list(v) if isinstance(v, tuple) else v) for k, v in opts.items()}


def _draw_life(rng: random.Random, ctx: _Ctx, lo: float, hi: float) -> float:
    """Service life in years according to the service-life options.

    Outside EXACT_DIVISOR mode a life is never left within 1e-6 (relative) of an
    exact divisor of the study period, so the number of renewals in a valid
    scenario never hinges on floating-point rounding. Near-divisor lives are
    produced on purpose only by population.edge_cases().
    """
    choices = ctx.opts["service_life_choices"]
    if choices is not None:
        return rng.choice(choices)
    mode = ctx.opts["service_life_mode"]
    if mode == "MIXED":
        mode = rng.choices(("INTEGER", "EXACT_DIVISOR", "CONTINUOUS"), weights=(0.5, 0.2, 0.3))[0]
    if mode == "EXACT_DIVISOR":
        return rng.choice(ctx.divisor_lives(lo, hi))
    life = lo
    for _ in range(200):
        if mode == "INTEGER":
            life = float(rng.randint(math.ceil(lo), math.floor(hi)))
        else:
            life = round(rng.uniform(lo, hi), 2)
        if is_near_divisor(ctx.period, life):
            continue
        if mode == "NON_DIVISOR":
            rem = math.fmod(ctx.period, life)
            if rem == 0.0 or min(rem, life - rem) < 1e-3 * life:
                continue
        return life
    return life


def _event_years(rng: random.Random, period: float, life: float) -> list[int]:
    """Irregular integer event offsets strictly inside (0, period)."""
    years: list[int] = []
    year = 0
    while True:
        year += max(1, round(life + rng.uniform(-2.0, 2.0)))
        if not year < period:
            return years
        years.append(year)


# --------------------------------------------------------------------------
# Factor catalogue
# --------------------------------------------------------------------------

class _Catalogue:
    """Builder of the fictional factor table of one scenario."""

    def __init__(self, ctx: _Ctx, gwp: dict[str, float]) -> None:
        self.ctx = ctx
        self.gwp = gwp
        self.factors: dict[str, FactorRecord] = {}
        self.material_unit: dict[str, list[str]] = {}   # class -> factors per canonical unit
        self.material_mass: dict[str, list[str]] = {}   # class -> factors per kg
        self.delivery: dict[str, str] = {}
        self.installation: dict[str, str] = {}
        self.eol: dict[str, dict[str, str]] = {}
        self.components: list[str] = []
        self.haul: list[str] = []
        self.equipment: dict[str, list[str]] = {}

    def add(self, rng: random.Random, factor_id: str, value: float, unit: str, stages: list[str],
            category: str, valid_until: Optional[str] = None) -> str:
        """Create a factor whose per-gas amounts reproduce its CO2e value exactly."""
        if factor_id in self.factors:
            raise ValueError(f"duplicate factor id {factor_id}")
        co2_share = rng.uniform(0.75, 0.995)
        shares = {gas: 0.0 for gas in GASES}
        shares["CO2"] = co2_share
        others = rng.sample(GASES[1:], rng.randint(1, 3))
        weights = [rng.random() + 0.05 for _ in others]
        weight_sum = sum(weights)
        for gas, weight in zip(others, weights):
            shares[gas] = (1.0 - co2_share) * weight / weight_sum
        amounts = {gas: value * shares[gas] / self.gwp[gas] for gas in GASES}
        start_year = self.ctx.start_year
        if valid_until is None:
            valid_until = f"{start_year + rng.randint(1, 6)}-12-31"
        self.factors[factor_id] = FactorRecord(
            factor_id=factor_id,
            value=co2e_of(amounts, self.gwp),
            unit=unit,
            stages=list(stages),
            gas_amounts=amounts,
            licence_status=LICENCE_PERMITTED,
            licence_basis="SYNTHETIC_FICTIONAL: generated for this study, no third-party rights",
            source_tag=SOURCE_TAG,
            source_url=f"synthetic://factor/{factor_id}",
            release_year=start_year - rng.randint(1, 4),
            region="SYNTH-REGION",
            valid_until=valid_until,
            boundary=f"declared unit 1 {unit}; stages {'+'.join(stages)}",
            quality_score=rng.choice(DATA_QUALITIES),
            category=category,
        )
        return factor_id

    def draw(self, rng: random.Random, family: str) -> float:
        lo, hi = FACTOR_LOG10_RANGE[family]
        return 10.0 ** rng.uniform(lo, hi)


def _build_catalogue(ctx: _Ctx, gwp: dict[str, float]) -> _Catalogue:
    rng = ctx.rng("catalogue")
    cat = _Catalogue(ctx, gwp)
    n_spec = SPEC_COUNT[ctx.size_class]
    for name, spec in CLASS_SPECS.items():
        centre = cat.draw(rng, spec.unit)
        ids = []
        for k in range(n_spec):
            value = centre * 10.0 ** rng.uniform(-0.25, 0.25)
            ids.append(cat.add(rng, f"F-MAT-{name}-{k + 1:02d}", value, spec.unit, ["A1-A3"], "MATERIAL_GENERIC"))
        cat.material_unit[name] = ids
        if spec.unit == "kg":
            cat.material_mass[name] = ids
        else:
            mass_centre = cat.draw(rng, "kg")
            cat.material_mass[name] = [
                cat.add(rng, f"F-MATKG-{name}-{k + 1:02d}", mass_centre * 10.0 ** rng.uniform(-0.25, 0.25),
                        "kg", ["A1-A3"], "MATERIAL_GENERIC_PER_MASS")
                for k in range(max(2, n_spec // 2))
            ]
        cat.delivery[name] = cat.add(
            rng, f"F-DEL-{name}", centre * rng.uniform(*DELIVERY_SHARE_RANGE), spec.unit, ["A4"], "DELIVERY_PER_QUANTITY")
        cat.installation[name] = cat.add(
            rng, f"F-INST-{name}", centre * rng.uniform(*INSTALLATION_SHARE_RANGE), spec.unit, ["A5"], "INSTALLATION")
        cat.eol[name] = {
            route: cat.add(rng, f"F-EOL-{name}-{route}", cat.draw(rng, "EOL"), "kg",
                           ["C4"] if route == "LANDFILL" else ["C3"], "END_OF_LIFE_ROUTE")
            for route in EOL_ROUTES
        }
    for k in range(COMPONENT_POOL[ctx.size_class]):
        cat.components.append(
            cat.add(rng, f"F-CMP-{k + 1:03d}", cat.draw(rng, "COMPONENT"), "kg", ["A1-A3"], "COMPOSITE_COMPONENT"))
    for mode in TRANSPORT_MODES:
        cat.add(rng, f"F-TR-{mode}", cat.draw(rng, "TRANSPORT"), "tkm", ["A4"], "TRANSPORT")
    for k in range(2):
        cat.haul.append(cat.add(rng, f"F-HAUL-{k + 1}", cat.draw(rng, "HAUL"), "tkm", ["C2"], "WASTE_HAUL"))
    for trade in EQUIPMENT_TRADES:
        centre = cat.draw(rng, "EQUIPMENT")
        cat.equipment[trade] = [
            cat.add(rng, f"F-EQ-{trade}-{k + 1:02d}", centre * 10.0 ** rng.uniform(-0.4, 0.4), "unit",
                    ["A1-A3"], "EQUIPMENT")
            for k in range(n_spec)
        ]
        cat.add(rng, f"F-EQDEL-{trade}", cat.draw(rng, "EQUIPMENT_DELIVERY"), "unit", ["A4"], "EQUIPMENT_DELIVERY")
        cat.add(rng, f"F-EQINST-{trade}", cat.draw(rng, "EQUIPMENT_INSTALLATION"), "unit", ["A5"],
                "EQUIPMENT_INSTALLATION")
        cat.add(rng, f"F-EQEOL-{trade}", cat.draw(rng, "EQUIPMENT_EOL"), "kg", ["C3"], "EQUIPMENT_END_OF_LIFE")
    cat.add(rng, "F-SITE-DIESEL", cat.draw(rng, "FUEL_L"), "L", ["A5"], "SITE_FUEL")
    cat.add(rng, "F-SITE-GAS", cat.draw(rng, "FUEL_M3"), "m3", ["A5"], "SITE_FUEL")
    cat.add(rng, "F-SITE-GAS-MJ", cat.draw(rng, "FUEL_MJ"), "MJ", ["A5"], "SITE_FUEL")
    cat.add(rng, "F-SITE-KEROSENE", cat.draw(rng, "FUEL_L"), "L", ["A5"], "SITE_FUEL")
    for kind in SITE_WASTE_KINDS:
        cat.add(rng, f"F-SITEWASTE-{kind}", cat.draw(rng, "SITE_WASTE"), "kg", ["A5"], "SITE_WASTE")
    cat.add(rng, "F-OP-GAS", cat.draw(rng, "FUEL_M3"), "m3", ["B6"], "OPERATION_FUEL")
    cat.add(rng, "F-OP-OIL", cat.draw(rng, "FUEL_L"), "L", ["B6"], "OPERATION_FUEL")
    cat.add(rng, "F-OP-DHEAT", cat.draw(rng, "FUEL_MJ"), "MJ", ["B6"], "OPERATION_FUEL")
    cat.add(rng, "F-WATER", cat.draw(rng, "WATER"), "m3", ["B7"], "WATER")
    cat.add(rng, "F-SEWAGE", cat.draw(rng, "SEWAGE"), "m3", ["B7"], "SEWAGE")
    cat.add(rng, "F-MSW", cat.draw(rng, "MSW"), "kg", ["B7"], "MUNICIPAL_WASTE")
    for activity_id, unit, _, family in DEMOLITION_ACTIVITIES:
        cat.add(rng, f"F-DEMO-{activity_id}", cat.draw(rng, family), unit, ["C1"], "DEMOLITION")
    cat.add(rng, "F-UPTAKE-CONCRETE", cat.draw(rng, "UPTAKE"), "m3", [STAGE_MEMO], "CARBON_UPTAKE_MEMO")
    return cat


# --------------------------------------------------------------------------
# Sections
# --------------------------------------------------------------------------

def _make_gwp(ctx: _Ctx) -> dict[str, float]:
    """FICTIONAL GWP vector. CO2 is 1 by definition of CO2e; the rest is random."""
    rng = ctx.rng("gwp")
    gwp = {"CO2": 1.0}
    for gas in GASES[1:]:
        gwp[gas] = round(10.0 ** rng.uniform(1.0, 4.3), 1)
    return gwp


def _make_provenance(ctx: _Ctx) -> dict[str, Provenance]:
    verified = f"{ctx.start_year - 1}-01-15"
    year = ctx.start_year - 1

    def record(pid: str, source_type: str, quality: str) -> Provenance:
        return Provenance(pid, source_type, STATE_OBSERVED, f"synthetic://source/{pid}", LICENCE_PERMITTED,
                          quality, verified, year)

    records = [
        record("PRV-DESIGN", "DESIGN_DOCUMENT", "HIGH"),
        record("PRV-MEASURED", "MEASURED", "HIGH"),
        record("PRV-SUPPLIER", "MEASURED", "MEDIUM"),
    ]
    return {r.provenance_id: r for r in records}


def _make_project(ctx: _Ctx) -> Project:
    rng = ctx.rng("project")
    target = ctx.opts["gross_floor_area"]
    drawn = round(rng.uniform(*GFA_RANGE[ctx.size_class]), 1)
    target = drawn if target is None else float(target)
    multi_draw = rng.random() < 0.35
    multi = multi_draw if ctx.opts["multi_use"] is None else bool(ctx.opts["multi_use"])
    main_share = rng.uniform(0.55, 0.90)
    others = rng.sample([u for u in USES if u != ctx.use], 2)
    n_other = rng.randint(1, 2)
    split = rng.uniform(0.3, 0.7)
    if multi:
        main_area = round(target * main_share, 1)
        rest = target - main_area
        if n_other == 1:
            breakdown = {ctx.use: main_area, others[0]: round(rest, 1)}
        else:
            first = round(rest * split, 1)
            breakdown = {ctx.use: main_area, others[0]: first, others[1]: round(rest - first, 1)}
    else:
        breakdown = {ctx.use: target}
    gfa = 0.0
    for area in breakdown.values():        # the declared total is the sum in dict order
        gfa += area
    floors_above = rng.randint(*FLOORS_RANGE[ctx.size_class])
    floors_below = rng.randint(0, 2)
    typical = round(gfa / (floors_above + floors_below), 1)
    return Project(
        building_name=f"SYNTHETIC BUILDING {ctx.seed}",
        project_type="NEW_BUILD",
        location=f"SYNTH-REGION-{rng.randint(1, 9)}",
        climate_zone=f"SYNTH-ZONE-{rng.randint(1, 8)}",
        building_use=ctx.use,
        use_area_breakdown=breakdown,
        structure_type=ctx.structure,
        floors_above=floors_above,
        floors_below=floors_below,
        gross_floor_area=gfa,
        building_footprint=round(typical * rng.uniform(1.0, 1.3), 1),
        typical_floor_area=typical,
        building_height=round(floors_above * rng.uniform(3.2, 4.5), 2),
        maximum_span=round(rng.uniform(4.0, 18.0), 2),
        building_shape=rng.choice(("RECTANGULAR", "L_SHAPE", "COURTYARD", "TOWER_PODIUM")),
        roof_system=rng.choice(("FLAT_MEMBRANE", "PITCHED_METAL", "GREEN_ROOF")),
        facade_system=rng.choice(("CURTAIN_WALL", "PRECAST_PANEL", "MASONRY_CLADDING", "TIMBER_CLADDING")),
        foundation_system=rng.choice(("SPREAD_FOOTING", "MAT", "PILED")),
        completion_year=ctx.start_year,
        assessment_date=ctx.assessment_date,
        assessor="SYNTHETIC_GENERATOR",
        design_stage=rng.choice(("CONCEPT", "SCHEMATIC_DESIGN", "CONSTRUCTION", "AS_BUILT")),
        provenance_id="PRV-DESIGN",
    )


def _make_boundary(ctx: _Ctx) -> Boundary:
    rng = ctx.rng("boundary")
    drawn_cycle = float(math.ceil(ctx.period) + rng.randint(0, 40))
    cycle = drawn_cycle if ctx.opts["replacement_cycle"] is None else float(ctx.opts["replacement_cycle"])
    drawn_scenario = rng.choices(RECONSTRUCTION_SCENARIOS, weights=(0.6, 0.2, 0.2))[0]
    scenario = ctx.opts["reconstruction_scenario"] or drawn_scenario
    refurbishment_share = round(rng.uniform(0.2, 0.6), 3)
    scope = {"NONE": 0.0, "REBUILD_IDENTICAL": 1.0, "MAJOR_REFURBISHMENT": refurbishment_share}[scenario]
    stages = ctx.opts["included_stages"]
    return Boundary(
        study_period=ctx.period,
        study_start_year=ctx.start_year,
        replacement_cycle=cycle,
        reconstruction_scenario=scenario,
        reconstruction_scope_fraction=scope,
        included_lifecycle_stages=list(LIFECYCLE_STAGES) if stages is None else list(stages),
        functional_unit="WHOLE_BUILDING",
        baseline_scenario=ctx.opts["baseline_scenario"],
        excluded_scope_notes="SYNTHETIC: external works and loose furniture are outside the scope",
        results_gas_scope=ctx.opts["results_gas_scope"],
    )


def _make_recipes(rng: random.Random, ctx: _Ctx, cat: _Catalogue, n_rows: int) -> list[list[tuple[str, float]]]:
    """Pool of composite recipes: lists of (component factor id, mass fraction)."""
    lo, hi = ctx.opts["composite_components"]
    hi = min(hi, len(cat.components))
    lo = min(lo, hi)
    expected = n_rows * ctx.opts["composite_share"] * ctx.opts["composite_pool_ratio"]
    recipes = []
    for _ in range(max(1, round(expected))):
        ids = rng.sample(cat.components, rng.randint(lo, hi))
        fractions = normalised_fractions([rng.uniform(0.05, 1.0) for _ in ids], 6)
        recipes.append(list(zip(ids, fractions)))
    return recipes


def _route_fractions(rng: random.Random) -> list[float]:
    if rng.random() < 0.10:
        fractions = [0.0] * len(EOL_ROUTES)
        fractions[rng.randrange(len(EOL_ROUTES))] = 1.0
        return fractions
    return normalised_fractions([rng.random() ** 2 + 1e-3 for _ in EOL_ROUTES], 4)


def _make_materials(
    ctx: _Ctx, cat: _Catalogue, project: Project, conversions: Sequence[UnitConversion]
) -> tuple[list[MaterialRow], dict[str, float], list[dict[str, str]]]:
    """Material rows, the class totals behind SummaryQuantities, and the inapplicable EPD list."""
    rng = ctx.rng("materials")
    n = MATERIAL_ROWS[ctx.size_class] if ctx.opts["n_materials"] is None else int(ctx.opts["n_materials"])
    opts = ctx.opts
    gfa = sum(project.use_area_breakdown.values())
    use_mult = blended_multiplier(USE_QUANTITY_MULT, project.use_area_breakdown)
    names = list(CLASS_SPECS)
    weights = [STRUCTURE_CLASS_WEIGHT[ctx.structure].get(c, 1.0) for c in names]
    class_total = {
        c: gfa * rng.uniform(*CLASS_SPECS[c].intensity) * STRUCTURE_QUANTITY_MULT[ctx.structure].get(c, 1.0) * use_mult
        for c in names
    }
    classes = rng.choices(names, weights=weights, k=n) if n else []
    row_weight = [rng.lognormvariate(0.0, 1.0) for _ in range(n)]
    weight_sum: dict[str, float] = {}
    for c, w in zip(classes, row_weight):
        weight_sum[c] = weight_sum.get(c, 0.0) + w
    recipes = _make_recipes(rng, ctx, cat, n)
    composite_share, epd_share = opts["composite_share"], opts["epd_share"]
    variety = bool(opts["unit_variety"])
    totals = {"reinforcement_kg": 0.0, "steel_kg": 0.0, "concrete_m3": 0.0, "timber_m3": 0.0,
              "envelope_m2": 0.0, "interior_m2": 0.0}
    inapplicable: list[dict[str, str]] = []
    rows: list[MaterialRow] = []
    for i in range(n):
        name = classes[i]
        spec = CLASS_SPECS[name]
        material_id = f"M{i + 1:06d}"
        division = rng.choice(spec.divisions)
        canonical_quantity = float(f"{class_total[name] * row_weight[i] / weight_sum[name]:.6g}")
        mass_per_unit = 1.0 if spec.unit == "kg" else round(rng.uniform(*spec.mass_per_unit), 3)
        mass_kg = canonical_quantity * mass_per_unit
        kind_draw, unit_draw, factor_draw = rng.random(), rng.random(), rng.random()
        quantity, quantity_unit = canonical_quantity, spec.unit
        if spec.unit == "kg" and variety and unit_draw < 0.20:
            quantity, quantity_unit = canonical_quantity / 1000.0, "t"
        row_conversions: list[UnitConversion] = []
        mass_conversion = UnitConversion(
            spec.unit, "kg", mass_per_unit, f"{SOURCE_TAG}: declared mass per {spec.unit} of row {material_id}")
        composition: Optional[list[CompositeComponent]] = None
        epd: Optional[EpdReference] = None
        factor_id: Optional[str] = None
        if kind_draw < composite_share:
            recipe_index = rng.randrange(len(recipes))
            composition = [CompositeComponent(fid, fraction) for fid, fraction in recipes[recipe_index]]
            specification = f"COMPOSITE-RECIPE-{recipe_index + 1:04d}"
            if spec.unit != "kg":
                row_conversions.append(mass_conversion)
        else:
            if spec.unit != "kg" and variety and factor_draw < 0.20:
                pool = cat.material_mass[name]
                row_conversions.append(mass_conversion)
            else:
                pool = cat.material_unit[name]
            spec_index = rng.randrange(len(pool))
            factor_id = pool[spec_index]
            specification = f"{name}-SPEC-{spec_index + 1:02d}"
            if kind_draw < composite_share + epd_share:
                generic = cat.factors[factor_id]
                to_factor_unit = conversion_factor(conversions, quantity_unit, generic.unit, row_conversions)
                declared_unit, stages = quantity_unit, ["A1-A3"]
                valid_until = f"{ctx.start_year + rng.randint(1, 5)}-12-31"
                reason_draw, reason = rng.random(), rng.choice(EPD_INAPPLICABLE_REASONS)
                if reason_draw < opts["epd_inapplicable_share"]:
                    inapplicable.append({"material_id": material_id, "reason": reason})
                    if reason == "EXPIRED":
                        valid_until = f"{ctx.start_year - rng.randint(2, 5)}-12-31"
                    elif reason == "STAGE_MISMATCH":
                        stages = ["A1-A3", "A4"]
                    else:
                        declared_unit = UNKNOWN_UNIT
                epd_id = cat.add(rng, f"F-EPD-{material_id}", generic.value * to_factor_unit * rng.uniform(0.6, 1.15),
                                 declared_unit, stages, "PRODUCT_SPECIFIC_EPD", valid_until)
                epd = EpdReference(epd_id, list(stages), declared_unit, valid_until)
        lo, hi = DIVISION_LIFE_RANGE[division]
        material_life = _draw_life(rng, ctx, lo, hi)
        refresh_cycle = material_life if rng.random() < 0.70 else _draw_life(rng, ctx, lo, hi)
        mode = rng.choices(TRANSPORT_MODES, weights=TRANSPORT_MODE_WEIGHT)[0]
        transport = TransportLeg(
            mass_t=float(f"{mass_kg * (1.0 + rng.uniform(0.0, 0.05)) / 1000.0:.6g}"),
            distance_km=round(rng.uniform(*TRANSPORT_DISTANCE[mode]), 1),
            mode=mode,
            load_factor=round(rng.uniform(0.4, 1.0), 3),
            factor_id=f"F-TR-{mode}",
            delivery_factor_id=cat.delivery[name] if rng.random() < 0.15 else None,
        )
        eol_factors = cat.eol[name]
        end_of_life = MaterialEndOfLife(
            mass_kg=float(f"{mass_kg * rng.uniform(0.9, 1.0):.6g}"),
            routes=[EolRoute(route, fraction, eol_factors[route])
                    for route, fraction in zip(EOL_ROUTES, _route_fractions(rng))],
            haul_distance_km=round(rng.uniform(5.0, 120.0), 1),
            haul_factor_id=rng.choice(cat.haul),
        )
        rows.append(MaterialRow(
            material_id=material_id,
            construction_division=division,
            material_class=name,
            specification=specification,
            quantity=quantity,
            quantity_unit=quantity_unit,
            quantity_basis=rng.choices(("DESIGN", "ORDERED", "AS_BUILT"), weights=(0.60, 0.25, 0.15))[0],
            waste_rate=round(rng.uniform(0.0, 0.12), 4),
            reuse_rate=round(rng.uniform(0.0, 0.6), 4),
            material_life=material_life,
            repair_rate=0.0 if rng.random() < 0.20 else round(rng.uniform(0.001, 0.03), 5),
            refresh_cycle=refresh_cycle,
            factor_id=factor_id,
            transport=transport,
            end_of_life=end_of_life,
            epd=epd,
            composition=composition,
            unquantified_cost_ratio=0.0 if rng.random() < 0.85 else round(rng.uniform(0.01, 0.2), 4),
            installation_factor_id=cat.installation[name] if rng.random() < 0.50 else None,
            conversions=row_conversions,
            provenance_id=rng.choice(("PRV-DESIGN", "PRV-MEASURED", "PRV-SUPPLIER")),
        ))
        if name == "REBAR":
            totals["reinforcement_kg"] += canonical_quantity
        elif name == "STRUCTURAL_STEEL":
            totals["steel_kg"] += canonical_quantity
        elif name == "CONCRETE":
            totals["concrete_m3"] += canonical_quantity
        elif name == "TIMBER":
            totals["timber_m3"] += canonical_quantity
        if spec.unit == "m2":
            if division in ("ROOF_EXTERIOR_WALL", "OPENINGS"):
                totals["envelope_m2"] += canonical_quantity
            elif division == "INTERIOR":
                totals["interior_m2"] += canonical_quantity
    return rows, totals, inapplicable


def _make_summary(ctx: _Ctx, totals: dict[str, float]) -> SummaryQuantities:
    rng = ctx.rng("summary")
    return SummaryQuantities(
        reinforcement_kg=totals["reinforcement_kg"],
        steel_kg=totals["steel_kg"],
        concrete_m3=totals["concrete_m3"],
        timber_m3=totals["timber_m3"],
        envelope_m2=totals["envelope_m2"],
        interior_m2=totals["interior_m2"],
        timber_dry_density_kg_per_m3=round(rng.uniform(300.0, 700.0), 1),   # FICTIONAL
        timber_carbon_fraction=round(rng.uniform(0.30, 0.60), 4),           # FICTIONAL
        concrete_uptake_factor_id="F-UPTAKE-CONCRETE",
    )


def _make_equipment(ctx: _Ctx, cat: _Catalogue, project: Project) -> list[EquipmentRow]:
    rng = ctx.rng("equipment")
    n = EQUIPMENT_ROWS[ctx.size_class] if ctx.opts["n_equipment"] is None else int(ctx.opts["n_equipment"])
    gfa = sum(project.use_area_breakdown.values())
    scale = blended_multiplier(USE_EQUIPMENT_MULT, project.use_area_breakdown) * gfa / (max(n, 1) * 50.0)
    trade_weights = USE_TRADE_WEIGHT[ctx.use]
    explicit_share = ctx.opts["explicit_event_share"]
    rows: list[EquipmentRow] = []
    for i in range(n):
        trade = rng.choices(EQUIPMENT_TRADES, weights=trade_weights)[0]
        pool = cat.equipment[trade]
        spec_index = rng.randrange(len(pool))
        quantity = float(1 + int(rng.lognormvariate(0.0, 1.0) * scale))
        service_life = _draw_life(rng, ctx, *TRADE_LIFE_RANGE[trade])
        events = _event_years(rng, ctx.period, service_life) if rng.random() < explicit_share else None
        rows.append(EquipmentRow(
            equipment_id=f"E{i + 1:06d}",
            trade=trade,
            model=f"{trade}-MODEL-{spec_index + 1:02d}",
            quantity=quantity,
            quantity_unit="unit",
            factor_id=pool[spec_index],
            service_life=service_life,
            repair_rate=round(rng.uniform(0.0, 0.04), 5),
            replacement_event_list=events,
            end_of_life_mass_kg=round(quantity * rng.uniform(5.0, 400.0), 3),
            eol_factor_id=f"F-EQEOL-{trade}",
            delivery_factor_id=f"F-EQDEL-{trade}" if rng.random() < 0.70 else None,
            installation_factor_id=f"F-EQINST-{trade}" if rng.random() < 0.70 else None,
            provenance_id=rng.choice(("PRV-DESIGN", "PRV-SUPPLIER")),
        ))
    return rows


def _make_refrigerants(ctx: _Ctx, project: Project) -> list[RefrigerantDevice]:
    rng = ctx.rng("refrigerants")
    opts = ctx.opts
    n = REFRIGERANT_DEVICES[ctx.size_class] if opts["n_refrigerants"] is None else int(opts["n_refrigerants"])
    # FICTIONAL fluids: invented labels with random GWP values.
    fluids = [(f"SYN-FLUID-{chr(ord('A') + k)}", round(10.0 ** rng.uniform(0.0, 3.6), 1)) for k in range(6)]
    charge_mult = blended_multiplier(USE_REFRIGERANT_MULT, project.use_area_breakdown)
    devices: list[RefrigerantDevice] = []
    for i in range(n):
        substance, gwp = rng.choice(fluids)
        top_up_draw = rng.random() < 0.60
        service_life = _draw_life(rng, ctx, *REFRIGERANT_LIFE_RANGE)
        explicit = rng.random() < opts["change_list_share"]
        change_years = _event_years(rng, ctx.period, service_life) if explicit else None
        devices.append(RefrigerantDevice(
            device_id=f"R{i + 1:05d}",
            substance=substance,
            application=rng.choices(REFRIGERANT_APPLICATIONS, weights=(0.70, 0.15, 0.10, 0.05))[0],
            charge_mass_kg=round(rng.uniform(0.5, 60.0) * charge_mult, 3),
            gwp=gwp,
            annual_leak_rate=round(rng.uniform(0.005, 0.15), 4),
            replacement_loss_rate=round(rng.uniform(0.0, 0.10), 4),
            end_of_life_recovery_rate=round(rng.uniform(0.20, 0.95), 4),
            change_years=change_years,
            service_life=None if explicit else service_life,
            top_up=top_up_draw if opts["top_up"] is None else bool(opts["top_up"]),
            provenance_id=rng.choice(("PRV-DESIGN", "PRV-SUPPLIER")),
        ))
    return devices


def _make_construction(ctx: _Ctx, project: Project) -> ConstructionSite:
    rng = ctx.rng("construction")
    gfa = sum(project.use_area_breakdown.values())
    variety = bool(ctx.opts["unit_variety"])
    diesel_l = round(gfa * rng.uniform(1.0, 10.0), 1)
    diesel_in_kl = rng.random() < 0.30
    gas_m3 = round(gfa * rng.uniform(0.05, 1.0), 1)
    gas_per_energy = rng.random() < 0.30
    heating_value = round(rng.uniform(20.0, 60.0), 2)                       # FICTIONAL MJ per m3
    with_kerosene = rng.random() < 0.50
    kerosene_l = round(gfa * rng.uniform(0.05, 1.0), 1)
    fuels = [
        SiteFuel("DIESEL", diesel_l / 1000.0, "kL", "F-SITE-DIESEL") if variety and diesel_in_kl
        else SiteFuel("DIESEL", diesel_l, "L", "F-SITE-DIESEL"),
        SiteFuel("GAS", gas_m3, "m3", "F-SITE-GAS-MJ",
                 [UnitConversion("m3", "MJ", heating_value, f"{SOURCE_TAG}: declared heating value of site gas")])
        if variety and gas_per_energy else SiteFuel("GAS", gas_m3, "m3", "F-SITE-GAS"),
    ]
    if with_kerosene:
        fuels.append(SiteFuel("KEROSENE", kerosene_l, "L", "F-SITE-KEROSENE"))
    kinds = rng.sample(SITE_WASTE_KINDS, rng.randint(3, len(SITE_WASTE_KINDS)))
    return ConstructionSite(
        electricity_kwh=round(gfa * rng.uniform(5.0, 40.0), 1),
        fuels=fuels,
        waste_streams=[SiteWaste(kind, round(gfa * rng.uniform(0.3, 6.0), 2), f"F-SITEWASTE-{kind}") for kind in kinds],
        duration_months=round(rng.uniform(*SITE_DURATION_RANGE[ctx.size_class]), 1),
        temporary_works="SYNTHETIC: scaffolding and site cabins, quantities not itemised",
        provenance_id="PRV-MEASURED",
    )


def _make_profile(rng: random.Random, ctx: _Ctx, base: float, unit: str) -> AnnualProfile:
    """Annual quantity profile of the forced or a random kind, always non-negative."""
    drawn = rng.choices(PROFILE_KINDS, weights=(0.40, 0.30, 0.30))[0]
    kind = ctx.opts["profile_kind"] or drawn
    trend = rng.uniform(-0.003, 0.006)
    n = ctx.table_length
    if kind == "CONSTANT":
        return constant_profile(base, unit, n)
    if kind == "LINEAR_TREND":
        return linear_profile(base, base * trend, unit, n)
    return table_profile([base * (1.0 + trend * k) * (1.0 + rng.uniform(-0.08, 0.08)) for k in range(n)], unit)


def _make_grid(rng: random.Random, ctx: _Ctx) -> GridFactorScenario:
    """FICTIONAL grid emission-factor scenario (kgCO2e/kWh)."""
    drawn = rng.choice(GRID_KINDS)
    kind = ctx.opts["grid_kind"] or drawn
    n = ctx.table_length
    start = round(10.0 ** rng.uniform(-0.7, -0.1), 4)
    construction_value = round(start * rng.uniform(1.0, 1.1), 4)
    annual_decline = floor = None
    steps: Optional[list[GridStep]] = None
    if kind == "CONSTANT":
        table = grid_table(kind, n, start=start)
    elif kind == "LINEAR_DECLINE_TO_FLOOR":
        floor = round(start * rng.uniform(0.05, 0.5), 4)
        annual_decline = (start - floor) / rng.uniform(15.0, 90.0)
        table = grid_table(kind, n, start=start, annual_decline=annual_decline, floor=floor)
    elif kind == "STEPWISE":
        steps, index, value = [GridStep(0, start)], 0, start
        while True:
            index += rng.randint(4, 15)
            if index >= n:
                break
            value = round(value * rng.uniform(0.6, 0.95), 6)
            steps.append(GridStep(index, value))
        table = grid_table(kind, n, steps=steps)
        start = None
    else:
        decline = rng.uniform(0.005, 0.02)
        table = [start * max(0.05, 1.0 - decline * k) * (1.0 + rng.uniform(-0.05, 0.05)) for k in range(n)]
        start = None
    return GridFactorScenario(
        scenario_id=f"GRID-{kind}-{ctx.seed}",
        kind=kind,
        unit="kgCO2e/kWh",
        start=start,
        annual_decline=annual_decline,
        floor=floor,
        steps=steps,
        table=table,
        construction_value=construction_value,
        licence_status=LICENCE_PERMITTED,
        source_tag=SOURCE_TAG,
        region="SYNTH-REGION",
    )


def _make_operation(ctx: _Ctx, project: Project) -> Operation:
    rng = ctx.rng("operation")
    gfa = sum(project.use_area_breakdown.values())
    mult = blended_multiplier(USE_OPERATION_MULT, project.use_area_breakdown)
    intensity = round(rng.uniform(60.0, 180.0) * mult, 3)                   # FICTIONAL kWh/m2/year
    electricity = _make_profile(rng, ctx, round(intensity * gfa, 3), "kWh/year")
    gas = _make_profile(rng, ctx, round(gfa * rng.uniform(0.5, 8.0) * mult, 3), "m3/year")
    oil_base = 0.0 if rng.random() < 0.40 else round(gfa * rng.uniform(0.05, 1.5) * mult, 3)
    oil = _make_profile(rng, ctx, oil_base, "L/year")
    heat_base = 0.0 if rng.random() < 0.50 else round(gfa * rng.uniform(10.0, 150.0) * mult, 3)
    district_heat = _make_profile(rng, ctx, heat_base, "MJ/year")
    generation_share = 0.0 if rng.random() < 0.30 else rng.uniform(0.02, 0.5)
    generation = _make_profile(rng, ctx, round(intensity * gfa * generation_share, 3), "kWh/year")
    export = scaled_profile(generation, round(rng.uniform(0.0, 0.4), 4))
    return Operation(
        new_or_existing="NEW",
        electricity=electricity,
        electricity_per_m2_per_year=intensity,
        gas=gas,
        gas_factor_id="F-OP-GAS",
        oil=oil,
        oil_factor_id="F-OP-OIL",
        district_heat=district_heat,
        district_heat_factor_id="F-OP-DHEAT",
        onsite_generation=generation,
        onsite_export=export,
        grid=_make_grid(rng, ctx),
        facility_management_ratio=round(rng.uniform(0.02, 0.2), 4),
        energy_simulation_basis="SYNTHETIC_DESIGN_CALCULATION",
        provenance_id="PRV-DESIGN",
    )


def _make_water_waste(ctx: _Ctx, project: Project) -> WaterWaste:
    rng = ctx.rng("water_waste")
    gfa = sum(project.use_area_breakdown.values())
    mult = blended_multiplier(USE_WATER_MULT, project.use_area_breakdown)
    water = _make_profile(rng, ctx, round(gfa * rng.uniform(0.3, 1.5) * mult, 3), "m3/year")
    sewage = scaled_profile(water, round(rng.uniform(0.8, 1.0), 4))
    waste = _make_profile(rng, ctx, round(gfa * rng.uniform(2.0, 20.0) * mult, 3), "kg/year")
    return WaterWaste(
        water=water, sewage=sewage, municipal_waste=waste,
        water_factor_id="F-WATER", sewage_factor_id="F-SEWAGE", waste_factor_id="F-MSW",
        provenance_id="PRV-DESIGN",
    )


def _make_end_of_life(ctx: _Ctx, cat: _Catalogue, project: Project) -> EndOfLife:
    rng = ctx.rng("end_of_life")
    gfa = sum(project.use_area_breakdown.values())
    variety = bool(ctx.opts["unit_variety"])
    chosen = rng.sample(range(len(DEMOLITION_ACTIVITIES)), rng.randint(2, len(DEMOLITION_ACTIVITIES)))
    activities: list[DemolitionActivity] = []
    for index in sorted(chosen):
        activity_id, unit, per_m2, _ = DEMOLITION_ACTIVITIES[index]
        quantity = round(gfa * rng.uniform(*per_m2), 2)
        in_kl = rng.random() < 0.5
        if unit == "L" and variety and in_kl:
            quantity, unit = quantity / 1000.0, "kL"
        activities.append(DemolitionActivity(
            activity_id, f"SYNTHETIC demolition activity {activity_id}", quantity, unit, f"F-DEMO-{activity_id}"))
    hauls = [
        WasteHaul(f"H{k + 1:02d}", "SYNTHETIC demolition waste not covered by material rows",
                  round(gfa * rng.uniform(0.005, 0.1), 3), round(rng.uniform(5.0, 150.0), 1), rng.choice(cat.haul))
        for k in range(rng.randint(2, 5))
    ]
    return EndOfLife(demolition_activities=activities, waste_hauls=hauls, provenance_id="PRV-DESIGN")


# --------------------------------------------------------------------------
# Defect injection (dirty scenarios)
# --------------------------------------------------------------------------

def _defect(kind: str, path: str, **detail: Any) -> Defect:
    return Defect(kind, path, dict(detail), list(DEFECT_RELATED_CHECKS[kind]))


def _take(pool: list[int], count: int) -> list[int]:
    """Remove and return up to ``count`` indices from the front of a shuffled pool."""
    taken = pool[:count]
    del pool[:count]
    return taken


def _shift_fraction(rng: random.Random, fraction: float) -> float:
    """A fraction moved by 0.02 to 0.3 (never below zero), so its group no longer sums to 1."""
    shift = round(rng.uniform(0.02, 0.3), 4)
    if rng.random() < 0.5 and fraction - shift >= 0.0:
        return fraction - shift
    return fraction + shift


def _outside_year(rng: random.Random, period: float) -> int:
    """An event offset that is not inside [0, period): at or after the end, or negative."""
    if rng.random() < 0.7:
        return math.ceil(period) + rng.randint(0, 20)
    return -rng.randint(1, 10)


def _inject_defects(scenario: Scenario, ctx: _Ctx) -> list[Defect]:
    """Mutate ``scenario`` with known defects and return their list."""
    rng = ctx.rng("dirty")
    share = ctx.opts["defect_share"]
    kinds = set(ctx.opts["defect_kinds"] if ctx.opts["defect_kinds"] is not None else DEFECT_KINDS)
    period = scenario.boundary.study_period
    defects: list[Defect] = []

    def count(n: int) -> int:
        return 0 if n == 0 else max(1, round(share * n))

    materials, equipment, devices = scenario.materials, scenario.equipment, scenario.refrigerants
    composite_pool = [i for i, row in enumerate(materials) if row.composition is not None]
    rng.shuffle(composite_pool)
    composite_hit = _take(composite_pool, count(len(composite_pool))) if "COMPOSITE_FRACTION_SUM" in kinds else []
    material_pool = [i for i in range(len(materials)) if i not in set(composite_hit)]
    rng.shuffle(material_pool)
    equipment_pool = list(range(len(equipment)))
    rng.shuffle(equipment_pool)
    device_pool = list(range(len(devices)))
    rng.shuffle(device_pool)

    for i in sorted(composite_hit):
        row = materials[i]
        j = rng.randrange(len(row.composition))
        row.composition[j].mass_fraction = _shift_fraction(rng, row.composition[j].mass_fraction)
        defects.append(_defect("COMPOSITE_FRACTION_SUM", f"materials[{i}].composition", row_id=row.material_id,
                               fraction_sum=sum(c.mass_fraction for c in row.composition)))

    if "MISSING_VALUE" in kinds:
        for i in sorted(_take(material_pool, count(len(materials)))):
            name = rng.choice(("quantity", "waste_rate", "material_life", "transport.distance_km"))
            if name == "transport.distance_km":
                materials[i].transport.distance_km = None
            else:
                setattr(materials[i], name, None)
            materials[i].states[name] = STATE_MISSING
            defects.append(_defect("MISSING_VALUE", f"materials[{i}].{name}", row_id=materials[i].material_id))
        for i in sorted(_take(equipment_pool, count(len(equipment)))):
            name = rng.choice(("quantity", "service_life"))
            setattr(equipment[i], name, None)
            equipment[i].states[name] = STATE_MISSING
            defects.append(_defect("MISSING_VALUE", f"equipment[{i}].{name}", row_id=equipment[i].equipment_id))
        for i in sorted(_take(device_pool, count(len(devices)))):
            name = rng.choice(("charge_mass_kg", "annual_leak_rate"))
            setattr(devices[i], name, None)
            devices[i].states[name] = STATE_MISSING
            defects.append(_defect("MISSING_VALUE", f"refrigerants[{i}].{name}", row_id=devices[i].device_id))

    if "UNIT_MISMATCH" in kinds:
        for i in sorted(_take(material_pool, count(len(materials)))):
            row = materials[i]
            expected = "kg" if row.composition is not None else scenario.factors[row.factor_id].unit
            row.quantity_unit = UNKNOWN_UNIT
            row.conversions = []
            defects.append(_defect("UNIT_MISMATCH", f"materials[{i}].quantity_unit", row_id=row.material_id,
                                   quantity_unit=UNKNOWN_UNIT, factor_unit=expected))

    if "ROUTE_FRACTION_SUM" in kinds:
        for i in sorted(_take(material_pool, count(len(materials)))):
            routes = materials[i].end_of_life.routes
            j = rng.randrange(len(routes))
            routes[j].fraction = _shift_fraction(rng, routes[j].fraction)
            defects.append(_defect("ROUTE_FRACTION_SUM", f"materials[{i}].end_of_life.routes",
                                   row_id=materials[i].material_id, fraction_sum=sum(r.fraction for r in routes)))

    if "EVENT_OUTSIDE_PERIOD" in kinds:
        for i in sorted(_take(equipment_pool, count(len(equipment)))):
            year = _outside_year(rng, period)
            equipment[i].replacement_event_list = sorted((equipment[i].replacement_event_list or []) + [year])
            defects.append(_defect("EVENT_OUTSIDE_PERIOD", f"equipment[{i}].replacement_event_list",
                                   row_id=equipment[i].equipment_id, event_year=year, study_period=period))
        for i in sorted(_take(device_pool, count(len(devices)))):
            year = _outside_year(rng, period)
            devices[i].change_years = sorted((devices[i].change_years or []) + [year])
            devices[i].service_life = None
            defects.append(_defect("EVENT_OUTSIDE_PERIOD", f"refrigerants[{i}].change_years",
                                   row_id=devices[i].device_id, event_year=year, study_period=period))

    area_kinds = [k for k in ("NON_POSITIVE_AREA", "AREA_BREAKDOWN_MISMATCH") if k in kinds]
    if area_kinds:                                   # one project: one area defect per scenario
        project = scenario.project
        kind = rng.choice(area_kinds)
        variant = rng.choice(("ZERO_TOTAL", "NEGATIVE_TOTAL", "NON_POSITIVE_PART"))
        scale = 1.0 + rng.choice((-1.0, 1.0)) * rng.uniform(0.02, 0.2)
        part = rng.choice(sorted(project.use_area_breakdown))
        part_value = rng.choice((0.0, -round(rng.uniform(1.0, 100.0), 1)))
        if kind == "AREA_BREAKDOWN_MISMATCH":
            project.gross_floor_area = round(project.gross_floor_area * scale, 1)
            defects.append(_defect(kind, "project.gross_floor_area", declared=project.gross_floor_area,
                                   breakdown_sum=sum(project.use_area_breakdown.values())))
        elif variant == "NON_POSITIVE_PART":
            project.use_area_breakdown[part] = part_value
            defects.append(_defect(kind, f"project.use_area_breakdown{{{part}}}", value=part_value))
        else:
            project.gross_floor_area = 0.0 if variant == "ZERO_TOTAL" else -project.gross_floor_area
            defects.append(_defect(kind, "project.gross_floor_area", value=project.gross_floor_area))

    if "UNKNOWN_LICENCE" in kinds:
        used = used_factor_ids(scenario)
        for factor_id in sorted(rng.sample(used, min(len(used), count(len(used))))):
            status = rng.choices((LICENCE_UNKNOWN, LICENCE_RESTRICTED, LICENCE_PERMISSION_REQUIRED),
                                 weights=(0.6, 0.2, 0.2))[0]
            scenario.factors[factor_id].licence_status = status
            scenario.factors[factor_id].licence_basis = ""
            defects.append(_defect("UNKNOWN_LICENCE", f"factors{{{factor_id}}}.licence_status", status=status))

    if ctx.opts["state_variety"]:
        _add_state_variety(scenario, ctx, rng, material_pool)
    return defects


def _add_state_variety(scenario: Scenario, ctx: _Ctx, rng: random.Random, free_rows: list[int]) -> None:
    """Mark some rows ESTIMATE / DERIVED / EXPLICIT_ZERO. These are valid states, not defects."""
    verified = f"{ctx.start_year - 1}-01-15"
    year = ctx.start_year - 1
    extra = [
        Provenance("PRV-ESTIMATE", "ESTIMATED", STATE_ESTIMATE, "synthetic://source/PRV-ESTIMATE", LICENCE_PERMITTED,
                   "LOW", verified, year, None, "SYNTHETIC: uniform, plus or minus 30 percent"),
        Provenance("PRV-LITERATURE", "LITERATURE", STATE_ESTIMATE, "synthetic://source/PRV-LITERATURE",
                   LICENCE_PERMITTED, "MEDIUM", verified, year),
        Provenance("PRV-DERIVED", "CALCULATED", STATE_DERIVED, "synthetic://source/PRV-DERIVED", LICENCE_PERMITTED,
                   "MEDIUM", verified, year, "SYNTHETIC: derived from drawings"),
    ]
    for record in extra:
        scenario.provenance[record.provenance_id] = record
    ids = [record.provenance_id for record in extra]
    estimate_rows = 0
    for row in scenario.materials:
        if rng.random() < 0.10:
            row.provenance_id = rng.choice(ids)
            estimate_rows += 1
    for row in scenario.equipment:
        if rng.random() < 0.10:
            row.provenance_id = rng.choice(ids)
    zero_paths: list[str] = []
    for i in sorted(_take(free_rows, max(1, round(0.01 * len(scenario.materials))) if scenario.materials else 0)):
        scenario.materials[i].quantity = 0.0
        scenario.materials[i].states["quantity"] = STATE_EXPLICIT_ZERO
        zero_paths.append(f"materials[{i}].quantity")
    scenario.meta.flags["state_variety"] = {
        "material_rows_estimate_or_derived": estimate_rows,
        "explicit_zero_paths": zero_paths,
    }


# --------------------------------------------------------------------------
# Public entry point
# --------------------------------------------------------------------------

def make_scenario(
    seed: int,
    structure: str,
    use: str,
    size_class: str,
    study_period: float = 60.0,
    dirty: bool = False,
    **options: Any,
) -> Scenario:
    """Build one fictional scenario, deterministic for a given argument set.

    ``structure`` is one of S / RC / SRC / W, ``use`` one of office /
    residential / school / hospital / retail / warehouse, ``size_class`` one of
    S / M / L (200 / 2000 / 20000 material rows, 60 / 600 / 6000 equipment rows,
    5 / 40 / 300 refrigerant devices). ``study_period`` is in years and may be
    non-integer. ``dirty=False`` gives a fully valid scenario; ``dirty=True``
    injects defects and lists them in ``meta.injected_defects``.
    See ``OPTION_HELP`` for the keyword options.
    """
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise TypeError("seed must be an int")
    if structure not in STRUCTURES:
        raise ValueError(f"structure must be one of {STRUCTURES}")
    if use not in USES:
        raise ValueError(f"use must be one of {USES}")
    if size_class not in SIZE_CLASSES:
        raise ValueError(f"size_class must be one of {SIZE_CLASSES}")
    period = float(study_period)
    if not (0.0 < period <= MAX_STUDY_PERIOD) or math.isnan(period):
        raise ValueError(f"study_period must satisfy 0 < T <= {MAX_STUDY_PERIOD}")
    opts = _resolve_options(options)
    needed = max(YEAR_TABLE_MIN_LENGTH, math.ceil(period) + 1)
    table_length = needed if opts["table_length"] is None else int(opts["table_length"])
    if table_length < needed:
        raise ValueError(f"table_length must be at least {needed} for this study period")
    ctx = _Ctx(seed, structure, use, size_class, period, opts, table_length)
    calendar = ctx.rng("calendar")
    drawn_year = calendar.randint(2030, 2040)        # fictional calendar years
    ctx.start_year = drawn_year if opts["study_start_year"] is None else int(opts["study_start_year"])
    ctx.assessment_date = f"{ctx.start_year - 1}-{calendar.randint(1, 12):02d}-{calendar.randint(1, 28):02d}"

    gwp = _make_gwp(ctx)
    conversions = base_unit_conversions()
    catalogue = _build_catalogue(ctx, gwp)
    project = _make_project(ctx)
    materials, totals, epd_inapplicable = _make_materials(ctx, catalogue, project, conversions)
    scenario_id = opts["scenario_id"] or (
        f"SYN-{structure}-{use}-{size_class}-T{period:g}-seed{seed}" + ("-DIRTY" if dirty else ""))
    meta = ScenarioMeta(
        scenario_id=scenario_id,
        seed=seed,
        structure=structure,
        use=use,
        size_class=size_class,
        flags={
            "generator_version": GENERATOR_VERSION,
            "dirty": bool(dirty),
            "study_period": period,
            "options": _json_options(opts),
            "epd_inapplicable": epd_inapplicable,
            "data_statement": "All values are synthetic and fictional; no real factor or rate table is used.",
        },
    )
    scenario = Scenario(
        meta=meta,
        project=project,
        boundary=_make_boundary(ctx),
        gases=list(GASES),
        gwp=gwp,
        unit_conversions=conversions,
        provenance=_make_provenance(ctx),
        factors=catalogue.factors,
        summary_quantities=_make_summary(ctx, totals),
        materials=materials,
        equipment=_make_equipment(ctx, catalogue, project),
        refrigerants=_make_refrigerants(ctx, project),
        construction=_make_construction(ctx, project),
        operation=_make_operation(ctx, project),
        water_waste=_make_water_waste(ctx, project),
        end_of_life=_make_end_of_life(ctx, catalogue, project),
    )
    if dirty:
        meta.injected_defects = _inject_defects(scenario, ctx)
    return scenario
