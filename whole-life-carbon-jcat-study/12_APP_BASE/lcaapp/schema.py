"""Structure of the engine's input model, read by reflection from the frozen dataclasses.

Nothing is copied from the model: the tree below is rebuilt from the type hints of
``synth.model.Scenario`` every time, so a change of the model shows up here by itself.

Node kinds
  record  {"type": "record", "optional", "cls", "fields": {name: node}}
  table   {"type": "table",  "optional", "row": record}            list of records
  ktable  {"type": "ktable", "key", "row": record}                 dict of records, keyed by ``key``
  leaf    {"type": "leaf", "kind", "elem", "optional", ...}        kind: number / integer / boolean /
                                                                   string / list / map / any
Paths use the grammar of ``synth.model.INPUT_FIELD_MAP``: dotted names, ``[]`` = each row of a
table, ``{}`` = each record of a keyed table.
"""
from __future__ import annotations

import dataclasses
import json
import re
import types
import typing
from typing import Any

from . import enginepath

# Parts of a scenario that a building input does not carry.
GENERATED = ("meta",)                                              # bookkeeping, written by the app
REFERENCE_PARTS = ("gases", "gwp", "unit_conversions", "factors", "price_index")   # reference data set

# Expected unit of a number leaf when the model fixes it (taken from the field names and the
# docstrings of the model: areas in m2, lengths in m, times in years).
_UNIT_SUFFIX = re.compile(r"_(kg|t|km|kwh|m3|m2|months)$")
_UNIT_NAMES = {"kwh": "kWh", "months": "month"}
_UNIT_EXPLICIT = {
    "project.gross_floor_area": "m2", "project.building_footprint": "m2", "project.typical_floor_area": "m2",
    "project.building_height": "m", "project.maximum_span": "m",
    "boundary.study_period": "year", "boundary.replacement_cycle": "year",
    "materials[].material_life": "year", "materials[].refresh_cycle": "year",
    "equipment[].service_life": "year", "refrigerants[].service_life": "year",
}
# A quantity whose unit is itself an input: the sibling leaf that holds the unit.
UNIT_LEAF = {
    "materials[].quantity": "quantity_unit", "equipment[].quantity": "quantity_unit",
    "construction.fuels[].quantity": "unit", "end_of_life.demolition_activities[].quantity": "unit",
}
# Leaves without which the engine cannot evaluate a building at all. Measured on 2026-11-12 by
# removing every input leaf in turn (see README, "必須項目"); everything else may be missing.
REQUIRED = (
    "project.use_area_breakdown",
    "materials[].material_class",
    "materials[].end_of_life.routes[].route",
    "operation.grid.construction_value",
    "operation.grid.table",
    "operation.grid.steps[].value",
    "water_waste.water.table",
    "water_waste.sewage.table",
    "water_waste.municipal_waste.table",
)

_cache: dict[str, Any] = {}


def _enums(m) -> dict[str, tuple[str, ...]]:
    """Vocabularies of the concept model per leaf path (for a list leaf: of its elements)."""
    out = {
        "project.project_type": m.PROJECT_TYPES, "project.building_use": m.USES,
        "project.structure_type": m.STRUCTURES, "project.design_stage": m.DESIGN_STAGES,
        "boundary.reconstruction_scenario": m.RECONSTRUCTION_SCENARIOS,
        "boundary.functional_unit": m.FUNCTIONAL_UNITS, "boundary.results_gas_scope": m.GAS_SCOPES,
        "boundary.included_lifecycle_stages": m.LIFECYCLE_STAGES,
        "materials[].construction_division": m.CONSTRUCTION_DIVISIONS,
        "materials[].material_class": m.MATERIAL_CLASSES, "materials[].quantity_basis": m.QUANTITY_BASES,
        "materials[].transport.mode": m.TRANSPORT_MODES, "materials[].end_of_life.routes[].route": m.EOL_ROUTES,
        "equipment[].trade": m.EQUIPMENT_TRADES, "refrigerants[].application": m.REFRIGERANT_APPLICATIONS,
        "operation.grid.kind": m.GRID_KINDS, "operation.grid.licence_status": m.LICENCE_STATES,
        "provenance{}.source_type": m.SOURCE_TYPES, "provenance{}.value_state": m.VALUE_STATES,
        "provenance{}.licence_status": m.LICENCE_STATES, "provenance{}.data_quality": m.DATA_QUALITIES,
    }
    for name in ("electricity", "gas", "oil", "district_heat", "onsite_generation", "onsite_export"):
        out[f"operation.{name}.kind"] = m.PROFILE_KINDS
    for name in ("water", "sewage", "municipal_waste"):
        out[f"water_waste.{name}.kind"] = m.PROFILE_KINDS
    return out


def _strip_optional(tp):
    origin = typing.get_origin(tp)
    if origin is typing.Union or origin is types.UnionType:
        args = [a for a in typing.get_args(tp) if a is not type(None)]
        if len(args) == 1:
            return args[0], True
    return tp, False


_SCALARS = {float: "number", int: "integer", bool: "boolean", str: "string"}


def _node(tp, m, path: str) -> dict:
    tp, optional = _strip_optional(tp)
    if isinstance(tp, type) and dataclasses.is_dataclass(tp):
        hints = typing.get_type_hints(tp, vars(m))
        return {"type": "record", "optional": optional, "cls": tp.__name__,
                "fields": {f.name: _node(hints[f.name], m, f"{path}.{f.name}" if path else f.name)
                           for f in dataclasses.fields(tp)}}
    origin = typing.get_origin(tp)
    if origin is list:
        (item,) = typing.get_args(tp)
        if isinstance(item, type) and dataclasses.is_dataclass(item):
            return {"type": "table", "optional": optional, "row": _node(item, m, path + "[]")}
        return {"type": "leaf", "kind": "list", "elem": _SCALARS.get(item, "any"), "optional": optional}
    if origin is dict:
        key, item = typing.get_args(tp)
        if isinstance(item, type) and dataclasses.is_dataclass(item):
            row = _node(item, m, path + "{}")
            return {"type": "ktable", "optional": optional, "key": next(iter(row["fields"])), "row": row}
        return {"type": "leaf", "kind": "map", "elem": _SCALARS.get(item, "any"),
                "int_keys": key is int, "optional": optional}
    return {"type": "leaf", "kind": _SCALARS.get(tp, "any"), "optional": optional}


def _decorate(node: dict, path: str, enums: dict, labels: dict) -> None:
    if node["type"] == "record":
        for name, child in node["fields"].items():
            _decorate(child, f"{path}.{name}" if path else name, enums, labels)
    elif node["type"] in ("table", "ktable"):
        _decorate(node["row"], path + ("[]" if node["type"] == "table" else "{}"), enums, labels)
    else:
        node["path"] = path
        if path in enums:
            node["enum"] = list(enums[path])
        name = path.rsplit(".", 1)[-1]
        unit = _UNIT_EXPLICIT.get(path)
        hit = _UNIT_SUFFIX.search(name)
        if unit is None and hit and "_per_" not in name and node["kind"] == "number":
            unit = _UNIT_NAMES.get(hit.group(1), hit.group(1))
        if unit:
            node["unit"] = unit
        if path in UNIT_LEAF:
            node["unit_leaf"] = UNIT_LEAF[path]
        if path in REQUIRED:
            node["required"] = True
        if path in labels:
            node.update(labels[path])


def _inventory_labels(m) -> dict[str, dict]:
    """Label and id of the existing input inventory for the leaves it names one-to-one."""
    try:
        with open(enginepath.INVENTORY, encoding="utf-8") as fh:
            fields = {f["id"]: f for f in json.load(fh)["fields"]}
    except (OSError, ValueError, KeyError):
        return {}
    by_path: dict[str, list[str]] = {}
    for input_id, path in m.INPUT_FIELD_MAP.items():
        by_path.setdefault(path, []).append(input_id)
    out = {}
    for path, ids in by_path.items():
        if len(ids) == 1 and ids[0] in fields:
            out[path] = {"input_id": ids[0], "label": fields[ids[0]].get("label") or ""}
    return out


def model_schema() -> dict:
    """The building part of the scenario model: {section name: node}."""
    if "schema" not in _cache:
        m = enginepath.model()
        root = _node(m.Scenario, m, "")
        enums, labels = _enums(m), _inventory_labels(m)
        sections = {}
        for name, node in root["fields"].items():
            if name in GENERATED:
                continue
            _decorate(node, name, enums, labels)
            sections[name] = node
        _cache["schema"] = sections
    return _cache["schema"]


def building_sections() -> dict:
    return {k: v for k, v in model_schema().items() if k not in REFERENCE_PARTS}


def reference_sections() -> dict:
    return {k: v for k, v in model_schema().items() if k in REFERENCE_PARTS}


def leaves(node: dict | None = None, path: str = ""):
    """Yield (pattern path, leaf node) of every leaf below ``node`` (default: the building part)."""
    if node is None:
        for name, child in building_sections().items():
            yield from leaves(child, name)
        return
    if node["type"] == "record":
        for name, child in node["fields"].items():
            yield from leaves(child, f"{path}.{name}" if path else name)
    elif node["type"] == "table":
        yield from leaves(node["row"], path + "[]")
    elif node["type"] == "ktable":
        yield from leaves(node["row"], path + "{}")
    else:
        yield path, node


def year_table_length() -> int:
    return enginepath.model().YEAR_TABLE_MIN_LENGTH
