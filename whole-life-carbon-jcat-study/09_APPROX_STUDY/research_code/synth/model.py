"""Input-side data model of the synthetic scenarios (research tooling only).

A ``Scenario`` mirrors the INPUT side of the independent conceptual model
(03_INPUTS/inputs.json, 124 fields in 12 groups). It carries raw inputs only and
never a derived result, so it is neutral to how any formula is evaluated: the
reference calculation and every candidate simplified model read the same
``Scenario`` object and nothing else.

Every number held by a scenario is SYNTHETIC and FICTIONAL (seeded random
generator, see ``generate.py``). Nothing here comes from J-CAT or from any real
emission-factor, service-life, repair-rate, leakage-rate or multiplier table.
The only non-random numbers in this module are unit definitions.

DATA CONVENTIONS (they describe the data, not how a formula must use it)
  * Time. ``boundary.study_period`` T is in years and may be non-integer.
    A year table has one entry per study year: index 0 is study year 1
    (calendar year ``boundary.study_start_year``), index k is study year k + 1.
    Tables hold at least ``YEAR_TABLE_MIN_LENGTH`` entries and at least
    ceil(T) entries.
  * Event years (``EquipmentRow.replacement_event_list``,
    ``RefrigerantDevice.change_years``) are integer offsets in years from the
    start of the study period (0 = start). Clean scenarios only hold offsets y
    with 0 < y < T.
  * ``None`` in a numeric field means MISSING (never zero). A zero that is meant
    as zero is the number 0.0, flagged ``EXPLICIT_ZERO`` in ``states``.
  * Value state of field ``f`` of an object ``o``:
    ``o.states.get(f, scenario.provenance[o.provenance_id].value_state)``.
    Nested fields use a dotted name, e.g. ``"transport.distance_km"``.
  * Factor values are kgCO2e per ``FactorRecord.unit``. A quantity may be in a
    different unit only when a documented conversion exists, either in
    ``Scenario.unit_conversions`` (unit definitions) or in the row's own
    ``conversions`` (row-specific, fictional, e.g. mass per m3).
  * ``Scenario.meta`` is bookkeeping for tests and reports (seed, options,
    injected defects). Calculations must not read it.
"""
from __future__ import annotations

import json
import types
import typing
from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any, Iterator, Optional, Sequence

# --------------------------------------------------------------------------
# Vocabulary
# --------------------------------------------------------------------------

SOURCE_TAG = "SYNTHETIC_FICTIONAL"
YEAR_TABLE_MIN_LENGTH = 130
METADATA_ONLY = "METADATA_ONLY"

GASES: tuple[str, ...] = ("CO2", "CH4", "N2O", "HFCs", "PFCs", "SF6", "NF3")

STATE_OBSERVED = "OBSERVED"
STATE_ESTIMATE = "ESTIMATE"
STATE_EXPLICIT_ZERO = "EXPLICIT_ZERO"
STATE_MISSING = "MISSING"
STATE_DERIVED = "DERIVED"
VALUE_STATES: tuple[str, ...] = (
    STATE_OBSERVED, STATE_ESTIMATE, STATE_EXPLICIT_ZERO, STATE_MISSING, STATE_DERIVED,
)

# Licence states follow the state machine of 01_COMPLIANCE/README.md (1-E).
LICENCE_PERMITTED = "PERMITTED_PUBLIC"
LICENCE_PERMISSION_REQUIRED = "PERMISSION_REQUIRED"
LICENCE_RESTRICTED = "RESTRICTED"
LICENCE_UNKNOWN = "UNKNOWN"
LICENCE_STATES: tuple[str, ...] = (
    LICENCE_PERMITTED, LICENCE_PERMISSION_REQUIRED, LICENCE_RESTRICTED, LICENCE_UNKNOWN,
)
ALLOWED_LICENCE_STATES: tuple[str, ...] = (LICENCE_PERMITTED,)

STRUCTURES: tuple[str, ...] = ("S", "RC", "SRC", "W")
USES: tuple[str, ...] = ("office", "residential", "school", "hospital", "retail", "warehouse")
SIZE_CLASSES: tuple[str, ...] = ("S", "M", "L")

LIFECYCLE_STAGES: tuple[str, ...] = (
    "A1-A3", "A4", "A5", "B1", "B2", "B3", "B4", "B5", "B6", "B7", "C1", "C2", "C3", "C4",
)
STAGE_MEMO = "MEMO"  # stage label of memo-only factors (not part of any stage total)

PROFILE_KINDS: tuple[str, ...] = ("CONSTANT", "LINEAR_TREND", "TABLE")
GRID_KINDS: tuple[str, ...] = ("CONSTANT", "LINEAR_DECLINE_TO_FLOOR", "STEPWISE", "TABLE")
EOL_ROUTES: tuple[str, ...] = ("REUSE", "RECYCLE", "PROCESSING", "LANDFILL")
EQUIPMENT_TRADES: tuple[str, ...] = ("ELECTRICAL", "HVAC", "PLUMBING", "CONVEYANCE")
CONSTRUCTION_DIVISIONS: tuple[str, ...] = (
    "FOUNDATION", "STRUCTURE", "ROOF_EXTERIOR_WALL", "OPENINGS", "INTERIOR",
)
MATERIAL_CLASSES: tuple[str, ...] = (
    "CONCRETE", "REBAR", "STRUCTURAL_STEEL", "TIMBER", "MASONRY", "GLASS", "ALUMINIUM",
    "INSULATION", "BOARD", "FINISH", "MEMBRANE", "PLASTIC", "MORTAR",
)
QUANTITY_BASES: tuple[str, ...] = ("DESIGN", "ORDERED", "AS_BUILT")
TRANSPORT_MODES: tuple[str, ...] = ("TRUCK_SMALL", "TRUCK_LARGE", "RAIL", "SHIP")
REFRIGERANT_APPLICATIONS: tuple[str, ...] = (
    "AIR_CONDITIONING", "INSULATION_FOAM", "FIRE_SUPPRESSION", "ELECTRICAL_INSULATION",
)
GAS_SCOPES: tuple[str, ...] = ("CO2E_ALL_GASES", "CO2_ONLY")
RECONSTRUCTION_SCENARIOS: tuple[str, ...] = ("NONE", "REBUILD_IDENTICAL", "MAJOR_REFURBISHMENT")
FUNCTIONAL_UNITS: tuple[str, ...] = ("WHOLE_BUILDING", "PER_M2_GFA", "PER_M2_GFA_YEAR")
PROJECT_TYPES: tuple[str, ...] = ("NEW_BUILD", "EXISTING", "EXTENSION_RENOVATION")
DESIGN_STAGES: tuple[str, ...] = ("CONCEPT", "SCHEMATIC_DESIGN", "CONSTRUCTION", "AS_BUILT")
SOURCE_TYPES: tuple[str, ...] = ("MEASURED", "DESIGN_DOCUMENT", "ESTIMATED", "LITERATURE", "CALCULATED")
DATA_QUALITIES: tuple[str, ...] = ("HIGH", "MEDIUM", "LOW")

# Defect kinds a dirty scenario can carry (see generate.make_scenario(dirty=True)).
DEFECT_KINDS: tuple[str, ...] = (
    "MISSING_VALUE", "UNKNOWN_LICENCE", "UNIT_MISMATCH", "COMPOSITE_FRACTION_SUM",
    "ROUTE_FRACTION_SUM", "NON_POSITIVE_AREA", "AREA_BREAKDOWN_MISMATCH",
    "EVENT_OUTSIDE_PERIOD",
)


# --------------------------------------------------------------------------
# Shared small records
# --------------------------------------------------------------------------

@dataclass(slots=True)
class UnitConversion:
    """quantity_in_to_unit = quantity_in_from_unit * factor, with its documented basis."""

    from_unit: str
    to_unit: str
    factor: float
    basis: str


def _definition(from_unit: str, to_unit: str, factor: float, text: str) -> UnitConversion:
    return UnitConversion(from_unit, to_unit, factor, "DEFINITION: " + text)


def base_unit_conversions() -> list[UnitConversion]:
    """Unit definitions shared by every scenario (the only non-random numbers).

    Each direction is listed explicitly; lookups never chain or invert entries.
    """
    return [
        _definition("t", "kg", 1000.0, "1 t = 1000 kg"),
        _definition("kg", "t", 0.001, "1 t = 1000 kg"),
        _definition("g", "kg", 0.001, "1 kg = 1000 g"),
        _definition("kg", "g", 1000.0, "1 kg = 1000 g"),
        _definition("kL", "L", 1000.0, "1 kL = 1000 L"),
        _definition("L", "kL", 0.001, "1 kL = 1000 L"),
        _definition("m3", "L", 1000.0, "1 m3 = 1000 L"),
        _definition("L", "m3", 0.001, "1 m3 = 1000 L"),
        _definition("MWh", "kWh", 1000.0, "1 MWh = 1000 kWh"),
        _definition("kWh", "MWh", 0.001, "1 MWh = 1000 kWh"),
        _definition("kWh", "MJ", 3.6, "1 kWh = 3.6 MJ"),
        _definition("MJ", "kWh", 1.0 / 3.6, "1 kWh = 3.6 MJ"),
        _definition("GJ", "MJ", 1000.0, "1 GJ = 1000 MJ"),
        _definition("MJ", "GJ", 0.001, "1 GJ = 1000 MJ"),
        _definition("km", "m", 1000.0, "1 km = 1000 m"),
        _definition("m", "km", 0.001, "1 km = 1000 m"),
        _definition("year", "month", 12.0, "1 year = 12 months"),
        _definition("month", "year", 1.0 / 12.0, "1 year = 12 months"),
        _definition("tCO2e", "kgCO2e", 1000.0, "1 t = 1000 kg"),
        _definition("kgCO2e", "tCO2e", 0.001, "1 t = 1000 kg"),
    ]


def conversion_factor(
    table: Sequence[UnitConversion],
    from_unit: str,
    to_unit: str,
    extra: Sequence[UnitConversion] = (),
) -> Optional[float]:
    """Multiplier from ``from_unit`` to ``to_unit`` or None when undocumented.

    ``extra`` (row-specific conversions) is searched before ``table``. Pure
    lookup: no chaining and no inversion of entries.
    """
    if from_unit == to_unit:
        return 1.0
    for conv in extra:
        if conv.from_unit == from_unit and conv.to_unit == to_unit:
            return conv.factor
    for conv in table:
        if conv.from_unit == from_unit and conv.to_unit == to_unit:
            return conv.factor
    return None


@dataclass(slots=True)
class Provenance:
    """Source record shared by the input values that came from the same source.

    PROVENANCE.* inputs. ``value_state`` is the declared state of every value
    covered by the record unless the owning object overrides it in ``states``.
    """

    provenance_id: str
    source_type: str                       # one of SOURCE_TYPES
    value_state: str                       # OBSERVED, ESTIMATE or DERIVED
    source_reference: str                  # fictional reference, never a real URL
    licence_status: str                    # one of LICENCE_STATES
    data_quality: str                      # one of DATA_QUALITIES
    last_verified_at: str                  # ISO date (fictional)
    measurement_year: int
    user_override_reason: Optional[str] = None
    uncertainty_distribution: Optional[str] = None


@dataclass(slots=True)
class FactorRecord:
    """One independent emission factor (FACTOR.* inputs). All values fictional.

    ``value`` is kgCO2e per ``unit`` and equals sum(gwp[g] * gas_amounts[g]) over
    ``Scenario.gases`` (kg of gas g per ``unit``).
    """

    factor_id: str
    value: float
    unit: str                              # denominator unit, e.g. kg, m3, m2, tkm, unit, L, MJ
    stages: list[str]                      # life-cycle stages covered by the value
    gas_amounts: dict[str, float]
    licence_status: str                    # one of LICENCE_STATES
    licence_basis: str                     # stated basis of the licence ("" when unknown)
    source_tag: str                        # always SYNTHETIC_FICTIONAL
    source_url: str                        # fictional "synthetic://" reference
    release_year: int
    region: str
    valid_until: Optional[str]             # ISO date
    boundary: str                          # declared unit and LCA boundary, free text
    quality_score: str                     # one of DATA_QUALITIES
    category: str                          # generator family label (descriptive only)


@dataclass(slots=True)
class Defect:
    """One defect injected on purpose into a dirty scenario (known truth for tests)."""

    kind: str                              # one of DEFECT_KINDS
    path: str                              # concrete location, e.g. materials[12].quantity
    detail: dict[str, Any] = field(default_factory=dict)
    related_checks: list[str] = field(default_factory=list)  # formula ids expected to react


@dataclass(slots=True)
class ScenarioMeta:
    """Generator bookkeeping. Not an input: calculations must not read it."""

    scenario_id: str
    seed: int
    structure: str
    use: str
    size_class: str
    flags: dict[str, Any] = field(default_factory=dict)
    injected_defects: list[Defect] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    source_tag: str = SOURCE_TAG


# --------------------------------------------------------------------------
# Project and boundary
# --------------------------------------------------------------------------

@dataclass(slots=True)
class Project:
    """PROJECT.* inputs. Areas in m2, lengths in m."""

    building_name: str
    project_type: str                      # one of PROJECT_TYPES
    location: str                          # fictional region label
    climate_zone: str                      # fictional zone label
    building_use: str                      # main use, one of USES
    use_area_breakdown: dict[str, float]   # use -> floor area (m2); several keys for multi-use
    structure_type: str                    # one of STRUCTURES
    floors_above: int
    floors_below: int
    gross_floor_area: Optional[float]
    building_footprint: float
    typical_floor_area: float
    building_height: float
    maximum_span: float
    building_shape: str
    roof_system: str
    facade_system: str
    foundation_system: str
    completion_year: int
    assessment_date: str                   # ISO date; compare with FactorRecord.valid_until
    assessor: str
    design_stage: str                      # one of DESIGN_STAGES
    provenance_id: str = ""
    states: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class Boundary:
    """BOUNDARY.* inputs."""

    study_period: float                    # years, may be non-integer
    study_start_year: int                  # calendar year of table index 0
    replacement_cycle: Optional[float]     # building rebuild / major refurbishment cycle (years)
    reconstruction_scenario: str           # one of RECONSTRUCTION_SCENARIOS
    reconstruction_scope_fraction: float   # share of the initial upfront scope renewed per event
    included_lifecycle_stages: list[str]
    functional_unit: str                   # one of FUNCTIONAL_UNITS
    baseline_scenario: Optional[str]       # scenario id used as comparison baseline
    excluded_scope_notes: str
    results_gas_scope: str                 # one of GAS_SCOPES


# --------------------------------------------------------------------------
# Materials
# --------------------------------------------------------------------------

@dataclass(slots=True)
class CompositeComponent:
    """One component of a composite: per-kg component factor and its mass fraction."""

    factor_id: str
    mass_fraction: float


@dataclass(slots=True)
class EpdReference:
    """Product-specific (EPD-like) factor declared for a row.

    The declaration repeats what the referenced ``FactorRecord`` states. Whether
    the reference may be applied (stages, declared unit, validity against
    ``Project.assessment_date``) is decided by the formula, not stored here.
    """

    factor_id: str
    declared_stages: list[str]
    declared_unit: str
    valid_until: str                       # ISO date


@dataclass(slots=True)
class TransportLeg:
    """Delivery of one material row to site (TRANSPORT.* inputs).

    When ``delivery_factor_id`` is None the leg is described by mass and
    distance (factor per tkm). When it is set, the row declares a per-quantity
    delivery factor INSTEAD of the mass-distance description (never both).
    """

    mass_t: Optional[float]                # transported mass, tonnes
    distance_km: Optional[float]
    mode: str                              # one of TRANSPORT_MODES
    load_factor: float                     # fraction of capacity used
    factor_id: Optional[str]               # factor per tkm of the mode
    delivery_factor_id: Optional[str] = None  # factor per row quantity unit


@dataclass(slots=True)
class EolRoute:
    """Share of a row's end-of-life mass sent to one route, with the route factor (per kg)."""

    route: str                             # one of EOL_ROUTES
    fraction: float
    factor_id: Optional[str]


@dataclass(slots=True)
class MaterialEndOfLife:
    """End-of-life declaration of one material row (END_OF_LIFE.* inputs).

    ``routes`` always lists the four EOL_ROUTES in that order; fractions sum to 1
    in clean scenarios. The landfill quantity is mass_kg * fraction of LANDFILL.
    """

    mass_kg: Optional[float]
    routes: list[EolRoute]
    haul_distance_km: float
    haul_factor_id: Optional[str]          # factor per tkm


@dataclass(slots=True)
class MaterialRow:
    """One bill-of-quantities row (MATERIAL.* inputs).

    Factor source of a row: ``composition`` (composite, ``factor_id`` is None,
    component factors are per kg) or ``factor_id`` (generic factor), optionally
    with an ``epd`` reference. A composite row never carries an ``epd``.
    """

    material_id: str
    construction_division: str             # one of CONSTRUCTION_DIVISIONS
    material_class: str                    # one of MATERIAL_CLASSES
    specification: str
    quantity: Optional[float]
    quantity_unit: str
    quantity_basis: str                    # one of QUANTITY_BASES
    waste_rate: Optional[float]            # site offcut fraction, 0 <= r < 1
    reuse_rate: Optional[float]            # share of offcuts reused
    material_life: Optional[float]         # years
    repair_rate: Optional[float]           # fraction per year
    refresh_cycle: Optional[float]         # years between renewals
    factor_id: Optional[str]
    transport: TransportLeg
    end_of_life: MaterialEndOfLife
    epd: Optional[EpdReference] = None
    composition: Optional[list[CompositeComponent]] = None
    unquantified_cost_ratio: float = 0.0   # share of the row scope without quantities
    installation_factor_id: Optional[str] = None  # per quantity unit, used at renewals
    conversions: list[UnitConversion] = field(default_factory=list)  # row-specific
    provenance_id: str = ""
    states: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class SummaryQuantities:
    """Declared class totals (MATERIAL.*_quantity / *_area / *_volume inputs).

    In clean synthetic scenarios each total equals the sum of the detailed rows
    of that class (or division) expressed in the stated unit. The timber and
    concrete memo parameters are fictional.
    """

    reinforcement_kg: float
    steel_kg: float
    concrete_m3: float
    timber_m3: float
    envelope_m2: float
    interior_m2: float
    timber_dry_density_kg_per_m3: float
    timber_carbon_fraction: float
    concrete_uptake_factor_id: Optional[str]


# --------------------------------------------------------------------------
# Equipment and refrigerants
# --------------------------------------------------------------------------

@dataclass(slots=True)
class EquipmentRow:
    """One equipment row (EQUIPMENT.* inputs).

    When ``replacement_event_list`` is not None it is the declared schedule and
    replaces the one implied by ``service_life``.
    """

    equipment_id: str
    trade: str                             # one of EQUIPMENT_TRADES
    model: str
    quantity: Optional[float]
    quantity_unit: str                     # "unit"
    factor_id: Optional[str]               # per unit
    service_life: Optional[float]          # years
    repair_rate: Optional[float]           # fraction per year
    replacement_event_list: Optional[list[int]]
    end_of_life_mass_kg: Optional[float]   # total mass of the row at disposal
    eol_factor_id: Optional[str] = None    # per kg
    delivery_factor_id: Optional[str] = None      # per unit
    installation_factor_id: Optional[str] = None  # per unit
    provenance_id: str = ""
    states: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class RefrigerantDevice:
    """One refrigerant-like charge (REFRIGERANT.* inputs). Labels and GWP are fictional.

    Exactly one of ``change_years`` and ``service_life`` is set in clean
    scenarios. ``top_up`` says whether leaked mass is replenished every year.
    """

    device_id: str
    substance: str
    application: str                       # one of REFRIGERANT_APPLICATIONS
    charge_mass_kg: Optional[float]
    gwp: Optional[float]                   # kgCO2e per kg
    annual_leak_rate: Optional[float]      # fraction per year
    replacement_loss_rate: Optional[float]  # fraction per change event
    end_of_life_recovery_rate: Optional[float]
    change_years: Optional[list[int]]
    service_life: Optional[float]
    top_up: bool
    provenance_id: str = ""
    states: dict[str, str] = field(default_factory=dict)


# --------------------------------------------------------------------------
# Construction site
# --------------------------------------------------------------------------

@dataclass(slots=True)
class SiteFuel:
    kind: str                              # e.g. DIESEL, GAS, KEROSENE
    quantity: Optional[float]
    unit: str
    factor_id: Optional[str]
    conversions: list[UnitConversion] = field(default_factory=list)


@dataclass(slots=True)
class SiteWaste:
    kind: str
    mass_kg: Optional[float]
    factor_id: Optional[str]               # per kg


@dataclass(slots=True)
class ConstructionSite:
    """CONSTRUCTION.* inputs. Site electricity uses ``Operation.grid.construction_value``."""

    electricity_kwh: Optional[float]
    fuels: list[SiteFuel]
    waste_streams: list[SiteWaste]
    duration_months: float
    temporary_works: str
    provenance_id: str = ""
    states: dict[str, str] = field(default_factory=dict)


# --------------------------------------------------------------------------
# Operation
# --------------------------------------------------------------------------

@dataclass(slots=True)
class AnnualProfile:
    """An annual quantity over the study years: descriptor AND explicit table.

    CONSTANT      table[k] == base
    LINEAR_TREND  table[k] == base + slope * k
    TABLE         no closed form; ``base`` and ``slope`` are None
    Which one counts: for CONSTANT and LINEAR_TREND the descriptor (``base``,
    ``slope``) is the input and the table is a redundant copy that must agree with
    it; for TABLE the table is the input. A disagreement between descriptor and
    table is an input defect that calculations report (they do not silently pick).
    ``unit`` is "<unit>/year"; no other time base is accepted.
    """

    kind: str                              # one of PROFILE_KINDS
    unit: str
    base: Optional[float]
    slope: Optional[float]
    table: list[float]


@dataclass(slots=True)
class GridStep:
    from_index: int                        # first table index at which ``value`` applies
    value: float


@dataclass(slots=True)
class GridFactorScenario:
    """Year-by-year electricity emission factor (kgCO2e/kWh): descriptor AND table.

    CONSTANT                 table[k] == start
    LINEAR_DECLINE_TO_FLOOR  table[k] == max(floor, start - annual_decline * k)
    STEPWISE                 table[k] == value of the last step with from_index <= k
    TABLE                    no closed form
    ``construction_value`` is the factor of the construction period, before
    table index 0.
    Which one counts: for a well-formed CONSTANT, LINEAR_DECLINE_TO_FLOOR
    (annual_decline >= 0, start >= floor) or STEPWISE (steps sorted by strictly
    increasing ``from_index``, the first at 0) scenario the descriptor is the input
    and the table a redundant copy that must agree; otherwise the table is the input.
    ``unit`` is "kgCO2e/<electricity unit>".
    """

    scenario_id: str
    kind: str                              # one of GRID_KINDS
    unit: str
    start: Optional[float]
    annual_decline: Optional[float]
    floor: Optional[float]
    steps: Optional[list[GridStep]]
    table: list[float]
    construction_value: float
    licence_status: str
    source_tag: str
    region: str


@dataclass(slots=True)
class Operation:
    """OPERATION.* inputs.

    ``electricity`` is the series entered as OPERATION.electricity_per_year. In
    this data set it is the electricity demand before netting on-site
    self-consumption; ``onsite_generation`` and ``onsite_export`` are separate
    series (export never exceeds generation in clean scenarios).
    ``electricity_per_m2_per_year`` is the declared design intensity; the tables
    are authoritative.
    """

    new_or_existing: str
    electricity: AnnualProfile             # kWh/year
    electricity_per_m2_per_year: float     # kWh/m2/year
    gas: AnnualProfile                     # m3/year
    gas_factor_id: Optional[str]
    oil: AnnualProfile                     # L/year
    oil_factor_id: Optional[str]
    district_heat: AnnualProfile           # MJ/year
    district_heat_factor_id: Optional[str]
    onsite_generation: AnnualProfile       # kWh/year
    onsite_export: AnnualProfile           # kWh/year
    grid: GridFactorScenario
    facility_management_ratio: float
    energy_simulation_basis: str
    provenance_id: str = ""
    states: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class WaterWaste:
    """WATER_WASTE.* inputs."""

    water: AnnualProfile                   # m3/year
    sewage: AnnualProfile                  # m3/year
    municipal_waste: AnnualProfile         # kg/year
    water_factor_id: Optional[str]
    sewage_factor_id: Optional[str]
    waste_factor_id: Optional[str]
    provenance_id: str = ""
    states: dict[str, str] = field(default_factory=dict)


# --------------------------------------------------------------------------
# End of life (building level)
# --------------------------------------------------------------------------

@dataclass(slots=True)
class DemolitionActivity:
    activity_id: str
    description: str
    quantity: Optional[float]
    unit: str
    factor_id: Optional[str]


@dataclass(slots=True)
class WasteHaul:
    """Haul of demolition waste that is NOT covered by any material row."""

    haul_id: str
    description: str
    mass_t: Optional[float]
    distance_km: Optional[float]
    factor_id: Optional[str]               # per tkm


@dataclass(slots=True)
class EndOfLife:
    """Building-level END_OF_LIFE.* inputs (row-level ones sit on MaterialRow)."""

    demolition_activities: list[DemolitionActivity]
    waste_hauls: list[WasteHaul]
    provenance_id: str = ""
    states: dict[str, str] = field(default_factory=dict)


# --------------------------------------------------------------------------
# Scenario
# --------------------------------------------------------------------------

@dataclass(slots=True)
class CostItem:
    """A scope known only by its cost (fictional), for the cost-based estimate with price correction.

    Not among the 124 input fields: these are NEW inputs introduced by the study.
    ``amount`` is in ``currency`` at the price level of ``price_year``; the factor is
    per currency unit at the price level of ``factor_base_year``.
    """

    item_id: str
    description: str
    amount: Optional[float]
    currency: str                          # fictional currency label, also the factor unit
    price_year: int
    factor_id: Optional[str]
    factor_base_year: int


@dataclass(slots=True)
class Scenario:
    """One complete fictional input set."""

    meta: ScenarioMeta
    project: Project
    boundary: Boundary
    gases: list[str]                       # order of the gas vector
    gwp: dict[str, float]                  # fictional kgCO2e per kg of gas (CO2 = 1 by definition)
    unit_conversions: list[UnitConversion]
    provenance: dict[str, Provenance]
    factors: dict[str, FactorRecord]
    summary_quantities: SummaryQuantities
    materials: list[MaterialRow]
    equipment: list[EquipmentRow]
    refrigerants: list[RefrigerantDevice]
    construction: ConstructionSite
    operation: Operation
    water_waste: WaterWaste
    end_of_life: EndOfLife
    cost_items: list[CostItem] = field(default_factory=list)      # NEW inputs (see CostItem)
    price_index: dict[int, float] = field(default_factory=dict)   # calendar year -> fictional price index


# --------------------------------------------------------------------------
# Traversal helpers (structure only, no formula)
# --------------------------------------------------------------------------

def annual_profiles(scenario: Scenario) -> list[tuple[str, AnnualProfile]]:
    """Every annual quantity profile of a scenario with its attribute path."""
    op, ww = scenario.operation, scenario.water_waste
    return [
        ("operation.electricity", op.electricity),
        ("operation.gas", op.gas),
        ("operation.oil", op.oil),
        ("operation.district_heat", op.district_heat),
        ("operation.onsite_generation", op.onsite_generation),
        ("operation.onsite_export", op.onsite_export),
        ("water_waste.water", ww.water),
        ("water_waste.sewage", ww.sewage),
        ("water_waste.municipal_waste", ww.municipal_waste),
    ]


def factor_references(scenario: Scenario) -> Iterator[tuple[str, Optional[str]]]:
    """Yield (path, factor_id) for every factor reference slot that is in use.

    Optional slots that are None by design (no EPD, no delivery factor, ...)
    are skipped; mandatory slots are yielded even when None.
    """
    for i, row in enumerate(scenario.materials):
        base = f"materials[{i}]"
        if row.composition is None:
            yield f"{base}.factor_id", row.factor_id
        else:
            for j, comp in enumerate(row.composition):
                yield f"{base}.composition[{j}].factor_id", comp.factor_id
        if row.epd is not None:
            yield f"{base}.epd.factor_id", row.epd.factor_id
        if row.installation_factor_id is not None:
            yield f"{base}.installation_factor_id", row.installation_factor_id
        if row.transport.delivery_factor_id is not None:
            yield f"{base}.transport.delivery_factor_id", row.transport.delivery_factor_id
        else:
            yield f"{base}.transport.factor_id", row.transport.factor_id
        yield f"{base}.end_of_life.haul_factor_id", row.end_of_life.haul_factor_id
        for j, route in enumerate(row.end_of_life.routes):
            yield f"{base}.end_of_life.routes[{j}].factor_id", route.factor_id
    for i, eq in enumerate(scenario.equipment):
        base = f"equipment[{i}]"
        yield f"{base}.factor_id", eq.factor_id
        for name in ("eol_factor_id", "delivery_factor_id", "installation_factor_id"):
            value = getattr(eq, name)
            if value is not None:
                yield f"{base}.{name}", value
    for i, fuel in enumerate(scenario.construction.fuels):
        yield f"construction.fuels[{i}].factor_id", fuel.factor_id
    for i, waste in enumerate(scenario.construction.waste_streams):
        yield f"construction.waste_streams[{i}].factor_id", waste.factor_id
    op, ww = scenario.operation, scenario.water_waste
    yield "operation.gas_factor_id", op.gas_factor_id
    yield "operation.oil_factor_id", op.oil_factor_id
    yield "operation.district_heat_factor_id", op.district_heat_factor_id
    yield "water_waste.water_factor_id", ww.water_factor_id
    yield "water_waste.sewage_factor_id", ww.sewage_factor_id
    yield "water_waste.waste_factor_id", ww.waste_factor_id
    for i, act in enumerate(scenario.end_of_life.demolition_activities):
        yield f"end_of_life.demolition_activities[{i}].factor_id", act.factor_id
    for i, haul in enumerate(scenario.end_of_life.waste_hauls):
        yield f"end_of_life.waste_hauls[{i}].factor_id", haul.factor_id
    if scenario.summary_quantities.concrete_uptake_factor_id is not None:
        yield "summary_quantities.concrete_uptake_factor_id", scenario.summary_quantities.concrete_uptake_factor_id
    for i, item in enumerate(scenario.cost_items):
        yield f"cost_items[{i}].factor_id", item.factor_id


def used_factor_ids(scenario: Scenario) -> list[str]:
    """Sorted ids of the factors referenced anywhere in the scenario."""
    return sorted({fid for _, fid in factor_references(scenario) if fid is not None})


def value_state(scenario: Scenario, owner: Any, field_name: str) -> str:
    """Declared state of ``owner.<field_name>`` (see DATA CONVENTIONS)."""
    override = owner.states.get(field_name)
    if override is not None:
        return override
    record = scenario.provenance.get(owner.provenance_id)
    return record.value_state if record is not None else STATE_MISSING


# --------------------------------------------------------------------------
# Input coverage: every id of 03_INPUTS/inputs.json -> model attribute path
# --------------------------------------------------------------------------
# Path grammar: dotted attribute names from Scenario; "[]" = each list element,
# "{}" = each dict value. A path may end on a record (e.g. an AnnualProfile).

INPUT_FIELD_MAP: dict[str, str] = {
    # PROJECT (22)
    "PROJECT.building_name": "project.building_name",
    "PROJECT.project_type": "project.project_type",
    "PROJECT.location": "project.location",
    "PROJECT.climate_zone": "project.climate_zone",
    "PROJECT.building_use": "project.building_use",
    "PROJECT.use_area_breakdown": "project.use_area_breakdown",
    "PROJECT.structure_type": "project.structure_type",
    "PROJECT.number_of_floors_above": "project.floors_above",
    "PROJECT.number_of_floors_below": "project.floors_below",
    "PROJECT.gross_floor_area": "project.gross_floor_area",
    "PROJECT.building_footprint": "project.building_footprint",
    "PROJECT.typical_floor_area": "project.typical_floor_area",
    "PROJECT.building_height": "project.building_height",
    "PROJECT.maximum_span": "project.maximum_span",
    "PROJECT.building_shape": "project.building_shape",
    "PROJECT.roof_system": "project.roof_system",
    "PROJECT.facade_system": "project.facade_system",
    "PROJECT.foundation_system": "project.foundation_system",
    "PROJECT.completion_year": "project.completion_year",
    "PROJECT.assessment_date": "project.assessment_date",
    "PROJECT.assessor": "project.assessor",
    "PROJECT.design_stage": "project.design_stage",
    # BOUNDARY (9)
    "BOUNDARY.study_period": "boundary.study_period",
    "BOUNDARY.replacement_cycle": "boundary.replacement_cycle",
    "BOUNDARY.study_start_year": "boundary.study_start_year",
    "BOUNDARY.included_lifecycle_stages": "boundary.included_lifecycle_stages",
    "BOUNDARY.functional_unit": "boundary.functional_unit",
    "BOUNDARY.baseline_scenario": "boundary.baseline_scenario",
    "BOUNDARY.excluded_scope_notes": "boundary.excluded_scope_notes",
    "BOUNDARY.reconstruction_scenario": "boundary.reconstruction_scenario",
    "BOUNDARY.results_gas_scope": "boundary.results_gas_scope",
    # MATERIAL (20)
    "MATERIAL.material_id": "materials[].material_id",
    "MATERIAL.construction_division": "materials[].construction_division",
    "MATERIAL.material_class": "materials[].material_class",
    "MATERIAL.material_specification": "materials[].specification",
    "MATERIAL.quantity": "materials[].quantity",
    "MATERIAL.quantity_unit": "materials[].quantity_unit",
    "MATERIAL.quantity_basis": "materials[].quantity_basis",
    "MATERIAL.waste_rate": "materials[].waste_rate",
    "MATERIAL.reuse_rate": "materials[].reuse_rate",
    "MATERIAL.material_life": "materials[].material_life",
    "MATERIAL.repair_rate": "materials[].repair_rate",
    "MATERIAL.refresh_cycles": "materials[].refresh_cycle",
    "MATERIAL.additional_epd_reference": "materials[].epd.factor_id",
    "MATERIAL.unquantified_cost_ratio": "materials[].unquantified_cost_ratio",
    "MATERIAL.reinforcement_quantity": "summary_quantities.reinforcement_kg",
    "MATERIAL.steel_quantity": "summary_quantities.steel_kg",
    "MATERIAL.concrete_volume": "summary_quantities.concrete_m3",
    "MATERIAL.timber_quantity": "summary_quantities.timber_m3",
    "MATERIAL.envelope_area": "summary_quantities.envelope_m2",
    "MATERIAL.interior_area": "summary_quantities.interior_m2",
    # FACTOR (11)
    "FACTOR.factor_id": "factors{}.factor_id",
    "FACTOR.factor_value": "factors{}.value",
    "FACTOR.factor_unit": "factors{}.unit",
    "FACTOR.factor_stages": "factors{}.stages",
    "FACTOR.factor_source_url": "factors{}.source_url",
    "FACTOR.factor_release_year": "factors{}.release_year",
    "FACTOR.factor_region": "factors{}.region",
    "FACTOR.factor_license": "factors{}.licence_status",
    "FACTOR.factor_boundary": "factors{}.boundary",
    "FACTOR.factor_valid_until": "factors{}.valid_until",
    "FACTOR.factor_quality_score": "factors{}.quality_score",
    # TRANSPORT (5)
    "TRANSPORT.transported_mass": "materials[].transport.mass_t",
    "TRANSPORT.distance": "materials[].transport.distance_km",
    "TRANSPORT.mode": "materials[].transport.mode",
    "TRANSPORT.load_factor": "materials[].transport.load_factor",
    "TRANSPORT.transport_factor_id": "materials[].transport.factor_id",
    # CONSTRUCTION (6)
    "CONSTRUCTION.site_diesel": "construction.fuels[].quantity",
    "CONSTRUCTION.site_electricity": "construction.electricity_kwh",
    "CONSTRUCTION.site_gas": "construction.fuels[].quantity",
    "CONSTRUCTION.site_waste_mass": "construction.waste_streams[].mass_kg",
    "CONSTRUCTION.site_duration": "construction.duration_months",
    "CONSTRUCTION.temporary_works": "construction.temporary_works",
    # EQUIPMENT (9)
    "EQUIPMENT.equipment_id": "equipment[].equipment_id",
    "EQUIPMENT.equipment_trade": "equipment[].trade",
    "EQUIPMENT.equipment_model": "equipment[].model",
    "EQUIPMENT.equipment_quantity": "equipment[].quantity",
    "EQUIPMENT.equipment_factor_id": "equipment[].factor_id",
    "EQUIPMENT.equipment_service_life": "equipment[].service_life",
    "EQUIPMENT.equipment_repair_rate": "equipment[].repair_rate",
    "EQUIPMENT.replacement_event_list": "equipment[].replacement_event_list",
    "EQUIPMENT.equipment_end_of_life_mass": "equipment[].end_of_life_mass_kg",
    # REFRIGERANT (8)
    "REFRIGERANT.substance": "refrigerants[].substance",
    "REFRIGERANT.application": "refrigerants[].application",
    "REFRIGERANT.charge_mass": "refrigerants[].charge_mass_kg",
    "REFRIGERANT.gwp": "refrigerants[].gwp",
    "REFRIGERANT.annual_leak_rate": "refrigerants[].annual_leak_rate",
    "REFRIGERANT.replacement_loss_rate": "refrigerants[].replacement_loss_rate",
    "REFRIGERANT.end_of_life_recovery_rate": "refrigerants[].end_of_life_recovery_rate",
    "REFRIGERANT.refrigerant_change_years": "refrigerants[].change_years",
    # OPERATION (11)
    "OPERATION.new_or_existing": "operation.new_or_existing",
    "OPERATION.electricity_per_year": "operation.electricity",
    "OPERATION.electricity_per_m2_per_year": "operation.electricity_per_m2_per_year",
    "OPERATION.gas_per_year": "operation.gas",
    "OPERATION.oil_per_year": "operation.oil",
    "OPERATION.district_heat_per_year": "operation.district_heat",
    "OPERATION.onsite_generation_per_year": "operation.onsite_generation",
    "OPERATION.onsite_export_per_year": "operation.onsite_export",
    "OPERATION.grid_factor_scenario_id": "operation.grid.scenario_id",
    "OPERATION.facility_management_ratio": "operation.facility_management_ratio",
    "OPERATION.energy_simulation_basis": "operation.energy_simulation_basis",
    # WATER_WASTE (6)
    "WATER_WASTE.water_per_year": "water_waste.water",
    "WATER_WASTE.sewage_per_year": "water_waste.sewage",
    "WATER_WASTE.municipal_waste_per_year": "water_waste.municipal_waste",
    "WATER_WASTE.water_factor_id": "water_waste.water_factor_id",
    "WATER_WASTE.sewage_factor_id": "water_waste.sewage_factor_id",
    "WATER_WASTE.waste_factor_id": "water_waste.waste_factor_id",
    # END_OF_LIFE (9)
    "END_OF_LIFE.demolition_activity": "end_of_life.demolition_activities[].quantity",
    "END_OF_LIFE.demolition_factor_id": "end_of_life.demolition_activities[].factor_id",
    "END_OF_LIFE.waste_transport_mass": "end_of_life.waste_hauls[].mass_t",
    "END_OF_LIFE.waste_transport_distance": "end_of_life.waste_hauls[].distance_km",
    "END_OF_LIFE.waste_treatment_route": "materials[].end_of_life.routes[].route",
    "END_OF_LIFE.waste_recycle_fraction": "materials[].end_of_life.routes[].fraction",
    "END_OF_LIFE.waste_reuse_fraction": "materials[].end_of_life.routes[].fraction",
    "END_OF_LIFE.landfill_quantity": "materials[].end_of_life.routes[].fraction",
    "END_OF_LIFE.eol_factor_ids": "materials[].end_of_life.routes[].factor_id",
    # PROVENANCE (8)
    "PROVENANCE.source_type": "provenance{}.source_type",
    "PROVENANCE.source_reference": "provenance{}.source_reference",
    "PROVENANCE.license_status": "provenance{}.licence_status",
    "PROVENANCE.data_quality": "provenance{}.data_quality",
    "PROVENANCE.last_verified_at": "provenance{}.last_verified_at",
    "PROVENANCE.measurement_year": "provenance{}.measurement_year",
    "PROVENANCE.user_override_reason": "provenance{}.user_override_reason",
    "PROVENANCE.uncertainty_distribution": "provenance{}.uncertainty_distribution",
}

# Remarks on mappings that are not one value per attribute.
INPUT_FIELD_NOTES: dict[str, str] = {
    "CONSTRUCTION.site_diesel": "fuel record with kind == 'DIESEL'",
    "CONSTRUCTION.site_gas": "fuel record with kind == 'GAS'",
    "END_OF_LIFE.waste_recycle_fraction": "route record with route == 'RECYCLE'",
    "END_OF_LIFE.waste_reuse_fraction": "route record with route == 'REUSE'",
    "END_OF_LIFE.landfill_quantity": (
        "not stored as a separate number: end_of_life.mass_kg times the fraction of the "
        "route record with route == 'LANDFILL'"
    ),
    "END_OF_LIFE.waste_transport_mass": (
        "building-level hauls; the haul of a material row is end_of_life.mass_kg "
        "over materials[].end_of_life.haul_distance_km"
    ),
    "FACTOR.factor_license": "status in licence_status, stated basis in licence_basis",
    "OPERATION.electricity_per_year": "AnnualProfile record (descriptor and year table)",
    "OPERATION.grid_factor_scenario_id": "the scenario itself is the record operation.grid",
    "MATERIAL.additional_epd_reference": "EpdReference record; None when the row has no EPD",
}

# Model attributes that have no id in inputs.json. The ledger writes them as "NEW:" inputs.
EXTRA_FIELD_MAP: dict[str, str] = {
    "NEW:GAS.gas_list": "gases",
    "NEW:GAS.gwp_vector": "gwp",
    "NEW:UNIT.conversion_table": "unit_conversions",
    "NEW:PROVENANCE.provenance_id": "provenance{}.provenance_id",
    "NEW:PROVENANCE.value_state": "provenance{}.value_state",
    "NEW:FACTOR.gas_amounts": "factors{}.gas_amounts",
    "NEW:FACTOR.licence_basis": "factors{}.licence_basis",
    "NEW:FACTOR.source_tag": "factors{}.source_tag",
    "NEW:FACTOR.category": "factors{}.category",
    "NEW:PROJECT.provenance_id": "project.provenance_id",
    "NEW:PROJECT.value_states": "project.states",
    "NEW:BOUNDARY.reconstruction_scope_fraction": "boundary.reconstruction_scope_fraction",
    "NEW:MATERIAL.composition": "materials[].composition",
    "NEW:MATERIAL.factor_id": "materials[].factor_id",
    "NEW:MATERIAL.epd_declared_stages": "materials[].epd.declared_stages",
    "NEW:MATERIAL.epd_declared_unit": "materials[].epd.declared_unit",
    "NEW:MATERIAL.epd_valid_until": "materials[].epd.valid_until",
    "NEW:MATERIAL.installation_factor_id": "materials[].installation_factor_id",
    "NEW:MATERIAL.row_conversions": "materials[].conversions",
    "NEW:MATERIAL.provenance_id": "materials[].provenance_id",
    "NEW:MATERIAL.value_states": "materials[].states",
    "NEW:TRANSPORT.delivery_factor_id": "materials[].transport.delivery_factor_id",
    "NEW:END_OF_LIFE.row_mass": "materials[].end_of_life.mass_kg",
    "NEW:END_OF_LIFE.row_haul_distance": "materials[].end_of_life.haul_distance_km",
    "NEW:END_OF_LIFE.row_haul_factor_id": "materials[].end_of_life.haul_factor_id",
    "NEW:END_OF_LIFE.demolition_activity_id": "end_of_life.demolition_activities[].activity_id",
    "NEW:END_OF_LIFE.demolition_description": "end_of_life.demolition_activities[].description",
    "NEW:END_OF_LIFE.demolition_unit": "end_of_life.demolition_activities[].unit",
    "NEW:END_OF_LIFE.haul_id": "end_of_life.waste_hauls[].haul_id",
    "NEW:END_OF_LIFE.haul_description": "end_of_life.waste_hauls[].description",
    "NEW:END_OF_LIFE.haul_factor_id": "end_of_life.waste_hauls[].factor_id",
    "NEW:END_OF_LIFE.provenance_id": "end_of_life.provenance_id",
    "NEW:END_OF_LIFE.value_states": "end_of_life.states",
    "NEW:SUMMARY.timber_dry_density": "summary_quantities.timber_dry_density_kg_per_m3",
    "NEW:SUMMARY.timber_carbon_fraction": "summary_quantities.timber_carbon_fraction",
    "NEW:SUMMARY.concrete_uptake_factor_id": "summary_quantities.concrete_uptake_factor_id",
    "NEW:EQUIPMENT.quantity_unit": "equipment[].quantity_unit",
    "NEW:EQUIPMENT.eol_factor_id": "equipment[].eol_factor_id",
    "NEW:EQUIPMENT.delivery_factor_id": "equipment[].delivery_factor_id",
    "NEW:EQUIPMENT.installation_factor_id": "equipment[].installation_factor_id",
    "NEW:EQUIPMENT.provenance_id": "equipment[].provenance_id",
    "NEW:EQUIPMENT.value_states": "equipment[].states",
    "NEW:REFRIGERANT.device_id": "refrigerants[].device_id",
    "NEW:REFRIGERANT.service_life": "refrigerants[].service_life",
    "NEW:REFRIGERANT.top_up": "refrigerants[].top_up",
    "NEW:REFRIGERANT.provenance_id": "refrigerants[].provenance_id",
    "NEW:REFRIGERANT.value_states": "refrigerants[].states",
    "NEW:CONSTRUCTION.fuel_kind": "construction.fuels[].kind",
    "NEW:CONSTRUCTION.fuel_unit": "construction.fuels[].unit",
    "NEW:CONSTRUCTION.fuel_factor_id": "construction.fuels[].factor_id",
    "NEW:CONSTRUCTION.fuel_conversions": "construction.fuels[].conversions",
    "NEW:CONSTRUCTION.waste_kind": "construction.waste_streams[].kind",
    "NEW:CONSTRUCTION.waste_factor_id": "construction.waste_streams[].factor_id",
    "NEW:CONSTRUCTION.provenance_id": "construction.provenance_id",
    "NEW:CONSTRUCTION.value_states": "construction.states",
    "NEW:OPERATION.gas_factor_id": "operation.gas_factor_id",
    "NEW:OPERATION.oil_factor_id": "operation.oil_factor_id",
    "NEW:OPERATION.district_heat_factor_id": "operation.district_heat_factor_id",
    "NEW:OPERATION.grid_kind": "operation.grid.kind",
    "NEW:OPERATION.grid_unit": "operation.grid.unit",
    "NEW:OPERATION.grid_start": "operation.grid.start",
    "NEW:OPERATION.grid_annual_decline": "operation.grid.annual_decline",
    "NEW:OPERATION.grid_floor": "operation.grid.floor",
    "NEW:OPERATION.grid_steps": "operation.grid.steps",
    "NEW:OPERATION.grid_table": "operation.grid.table",
    "NEW:OPERATION.grid_construction_value": "operation.grid.construction_value",
    "NEW:OPERATION.grid_licence_status": "operation.grid.licence_status",
    "NEW:OPERATION.grid_source_tag": "operation.grid.source_tag",
    "NEW:OPERATION.grid_region": "operation.grid.region",
    "NEW:OPERATION.provenance_id": "operation.provenance_id",
    "NEW:OPERATION.value_states": "operation.states",
    "NEW:WATER_WASTE.provenance_id": "water_waste.provenance_id",
    "NEW:WATER_WASTE.value_states": "water_waste.states",
}


def _strip_optional(tp: Any) -> Any:
    """Optional[X] -> X; other types unchanged."""
    origin = typing.get_origin(tp)
    if origin is typing.Union or origin is types.UnionType:
        args = [a for a in typing.get_args(tp) if a is not type(None)]
        if len(args) == 1:
            return args[0]
    return tp


def _type_hints(cls: type) -> dict[str, Any]:
    return typing.get_type_hints(cls)


def resolve_model_path(path: str, root: type | None = None) -> Any:
    """Return the declared type found at ``path``; KeyError if the path does not exist."""
    current: Any = Scenario if root is None else root
    for token in path.split("."):
        name, suffix = token, ""
        if token.endswith("[]") or token.endswith("{}"):
            name, suffix = token[:-2], token[-2:]
        current = _strip_optional(current)
        if not is_dataclass(current):
            raise KeyError(f"{path!r}: {token!r} is reached through a non-record type")
        hints = _type_hints(current)
        if name not in hints:
            raise KeyError(f"{path!r}: {current.__name__} has no attribute {name!r}")
        current = _strip_optional(hints[name])
        origin = typing.get_origin(current)
        if suffix == "[]":
            if origin is not list:
                raise KeyError(f"{path!r}: {name!r} is not a list")
            current = typing.get_args(current)[0]
        elif suffix == "{}":
            if origin is not dict:
                raise KeyError(f"{path!r}: {name!r} is not a dict")
            current = typing.get_args(current)[1]
    return current


def model_leaf_paths(root: type | None = None, prefix: str = "") -> list[str]:
    """Every leaf attribute path of the model (containers of plain values are leaves)."""
    cls: Any = Scenario if root is None else root
    out: list[str] = []
    hints = _type_hints(cls)
    for f in fields(cls):
        tp = _strip_optional(hints[f.name])
        origin = typing.get_origin(tp)
        path = prefix + f.name
        if is_dataclass(tp):
            out.extend(model_leaf_paths(tp, path + "."))
        elif origin is list and is_dataclass(_strip_optional(typing.get_args(tp)[0])):
            out.extend(model_leaf_paths(_strip_optional(typing.get_args(tp)[0]), path + "[]."))
        elif origin is dict and is_dataclass(_strip_optional(typing.get_args(tp)[1])):
            out.extend(model_leaf_paths(_strip_optional(typing.get_args(tp)[1]), path + "{}."))
        else:
            out.append(path)
    return out


def undocumented_model_paths() -> list[str]:
    """Leaf paths outside ``meta`` covered by neither INPUT_FIELD_MAP nor EXTRA_FIELD_MAP."""
    mapped = [p for p in INPUT_FIELD_MAP.values() if p != METADATA_ONLY]
    mapped.extend(EXTRA_FIELD_MAP.values())
    missing = []
    for leaf in model_leaf_paths():
        if leaf == "meta" or leaf.startswith("meta."):
            continue
        if not any(leaf == p or leaf.startswith(p + ".") for p in mapped):
            missing.append(leaf)
    return missing


def default_inputs_path() -> Path:
    """Location of 03_INPUTS/inputs.json relative to this file."""
    return Path(__file__).resolve().parents[3] / "03_INPUTS" / "inputs.json"


def check_input_coverage(inputs_path: Path | str | None = None) -> dict[str, int]:
    """Assert that every input id of inputs.json is mapped, and only those.

    Also asserts that every mapped attribute path exists in the model. Returns
    counts: total ids, ids mapped to an attribute, ids kept as METADATA_ONLY.
    """
    path = Path(inputs_path) if inputs_path is not None else default_inputs_path()
    spec = json.loads(path.read_text(encoding="utf-8"))
    ids = [entry["id"] for entry in spec["fields"]]
    assert len(ids) == len(set(ids)), "duplicate input ids in inputs.json"
    assert len(ids) == spec["total_fields"], "inputs.json: total_fields does not match the field list"
    unmapped = [i for i in ids if i not in INPUT_FIELD_MAP]
    assert not unmapped, f"input ids without a mapping: {unmapped}"
    unknown = sorted(set(INPUT_FIELD_MAP) - set(ids))
    assert not unknown, f"mapped ids that are not in inputs.json: {unknown}"
    metadata_only = 0
    for input_id in ids:
        target = INPUT_FIELD_MAP[input_id]
        if target == METADATA_ONLY:
            metadata_only += 1
            continue
        try:
            resolve_model_path(target)
        except KeyError as exc:  # re-raised as an assertion: the mapping itself is wrong
            raise AssertionError(f"{input_id}: {exc}") from exc
    for extra_id, target in EXTRA_FIELD_MAP.items():
        assert extra_id.startswith("NEW:"), f"extra field id must start with 'NEW:': {extra_id}"
        try:
            resolve_model_path(target)
        except KeyError as exc:
            raise AssertionError(f"{extra_id}: {exc}") from exc
    return {
        "total": len(ids),
        "mapped_to_attribute": len(ids) - metadata_only,
        "metadata_only": metadata_only,
    }
