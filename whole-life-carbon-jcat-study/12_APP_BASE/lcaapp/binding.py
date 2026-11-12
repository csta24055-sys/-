"""Binding between the items of an input classification and the engine's input model.

A binding is data: for every model path (leaf, table or nested table) the id that the
classification uses for it, and the category the id sits in. The conversion code never
looks at a particular id, so another classification only needs another binding file.

Two bindings exist:

* ``provisional()`` - the stand-in used while the real classification file is not available
  in the repository. Its ids ARE the model paths (identity), its categories are the sections
  of the model. It is a developer stand-in, not the input classification of the app.
* ``load(path)`` - a binding file (``lca-binding/1``) written for a real classification.

Classification trees themselves are read by ``read_tree`` (generic, shape-tolerant).
"""
from __future__ import annotations

import collections
import json
import os
from typing import Any

from . import schema

BINDING_FORMAT = "lca-binding/1"
OTHER_WORDS = ("その他", "other", "others", "misc")

_SECTION_LABELS = {
    "project": "建物概要", "boundary": "評価条件・範囲", "provenance": "出典・根拠の記録",
    "summary_quantities": "主要数量（区分別の合計）", "materials": "資材", "equipment": "設備機器",
    "refrigerants": "冷媒", "construction": "施工現場", "operation": "運用（エネルギー）",
    "water_waste": "運用（水・廃棄物）", "end_of_life": "解体・廃棄", "cost_items": "費用で把握する範囲",
}


def relative_id(path: str) -> str:
    """Identity id of a model path: the part after the innermost row marker."""
    cut = max(path.rfind("[]."), path.rfind("{}."))
    return path[cut + 3:] if cut >= 0 else path


def table_paths(node: dict | None = None, path: str = ""):
    """Yield (table pattern path, node) for every table and keyed table of the building part."""
    if node is None:
        for name, child in schema.building_sections().items():
            yield from table_paths(child, name)
        return
    if node["type"] == "record":
        for name, child in node["fields"].items():
            yield from table_paths(child, f"{path}.{name}" if path else name)
    elif node["type"] in ("table", "ktable"):
        marker = "[]" if node["type"] == "table" else "{}"
        yield path + marker, node
        yield from table_paths(node["row"], path + marker)


class Binding:
    def __init__(self, id: str, version: str, classification: dict, categories: dict[str, str],
                 entries: dict[str, dict], provisional: bool = False):
        self.id, self.version = id, version
        self.classification = classification
        self.categories = categories                     # category id -> label
        self.entries = entries                           # model path -> {"id", "category"}
        self.provisional = provisional

    def id_for(self, path: str) -> str | None:
        entry = self.entries.get(path)
        return entry["id"] if entry else None

    def category_for(self, path: str) -> str | None:
        entry = self.entries.get(path)
        return entry.get("category") if entry else None

    def describe(self) -> dict:
        return {"id": self.id, "version": self.version, "classification": self.classification,
                "provisional": self.provisional, "n_bound": len(self.entries)}

    def coverage(self) -> dict:
        """Which model leaves have an id in this binding and which have none."""
        leaves = [p for p, _ in schema.leaves()]
        tables = [p for p, _ in table_paths()]
        unbound = [p for p in leaves + tables if p not in self.entries]
        return {"model_leaves": len(leaves), "model_tables": len(tables),
                "bound": len(leaves) + len(tables) - len(unbound), "unbound": unbound}

    def to_json(self) -> dict:
        return {"format": BINDING_FORMAT, "id": self.id, "version": self.version,
                "classification": self.classification, "categories": self.categories,
                "map": self.entries}


def provisional() -> Binding:
    """Identity binding over the engine's own input model (developer stand-in)."""
    entries: dict[str, dict] = {}
    for path, _ in schema.leaves():
        entries[path] = {"id": relative_id(path), "category": path.split(".")[0].split("[")[0].split("{")[0]}
    for path, _ in table_paths():
        entries[path] = {"id": relative_id(path[:-2]), "category": path.split(".")[0].split("[")[0].split("{")[0]}
    categories = {name: _SECTION_LABELS.get(name, name) for name in schema.building_sections()}
    return Binding(
        id="provisional-engine-model", version="1",
        classification={"id": "provisional-engine-model", "version": "1",
                        "note": "仮の分類。エンジンの入力モデルの区分をそのまま使う開発用の代用であり、アプリの入力分類ではない。"},
        categories=categories, entries=entries, provisional=True)


def from_json(data: dict) -> Binding:
    if not isinstance(data, dict) or data.get("format") != BINDING_FORMAT:
        raise ValueError(f"binding file must have format {BINDING_FORMAT!r}")
    known = {p for p, _ in schema.leaves()} | {p for p, _ in table_paths()}
    entries = {}
    for path, entry in (data.get("map") or {}).items():
        if path not in known:
            raise ValueError(f"binding names a path the engine's input model does not have: {path}")
        if isinstance(entry, str):
            entry = {"id": entry}
        if not isinstance(entry, dict) or not isinstance(entry.get("id"), str) or not entry["id"]:
            raise ValueError(f"binding entry of {path} needs an id")
        entries[path] = {"id": entry["id"], "category": entry.get("category")}
        if entry.get("node"):
            entries[path]["node"] = entry["node"]            # the node of the classification tree the path belongs to
    return Binding(str(data.get("id") or "binding"), str(data.get("version") or "0"),
                   dict(data.get("classification") or {}), dict(data.get("categories") or {}), entries)


def load(path: str) -> Binding:
    with open(path, encoding="utf-8") as fh:
        return from_json(json.load(fh))


# --------------------------------------------------------------------------------------------
# Binding to the received input classification (five categories)
# --------------------------------------------------------------------------------------------
# Engine model path (regular expression) -> node of the complete classification tree. The first match wins.
# The ids of the items stay the engine's own names for now: the tree fixes categories, branches and
# details, not the ids of single input fields.
TREE_RULES = [
    (r"^project\.building_name", "building.identity.name"), (r"^project\.assessor", "building.identity.assessor"),
    (r"^project\.(location|climate_zone)", "building.identity.location"), (r"^project\.assessment_date", "building.identity.calc_date"),
    (r"^project\.completion_year", "building.identity.completion_year"), (r"^project\.design_stage", "building.identity.design_stage"),
    (r"^project\.building_use", "building.geometry.main_use"), (r"^project\.use_area_breakdown", "building.geometry.use_floor_areas"),
    (r"^project\.gross_floor_area", "building.geometry.gross_floor_area"), (r"^project\.floors_", "building.geometry.floors"),
    (r"^project\.building_height", "building.geometry.height"), (r"^project\.typical_floor_area", "building.geometry.typical_floor_area"),
    (r"^project\.(building_shape|building_footprint)", "building.geometry.shape"), (r"^project\.maximum_span", "building.geometry.max_span"),
    (r"^project\.structure_type", "building.structure.main_structure"), (r"^project\.foundation_system", "building.structure.foundation"),
    (r"^project\.roof_system", "building.structure.roof_spec"), (r"^project\.facade_system", "building.structure.facade_spec"),
    (r"^project\.project_type", "building.boundary.project_type"), (r"^project\.", "building.other"),
    (r"^boundary\.study_", "building.boundary.study_period"), (r"^boundary\.(replacement_cycle|reconstruction)", "building.boundary.replacement_cycle"),
    (r"^boundary\.excluded_scope_notes", "building.boundary.site_scope"), (r"^boundary\.included_lifecycle_stages", "assessment.method.stages"),
    (r"^boundary\.results_gas_scope", "assessment.method.gas_scope"), (r"^boundary\.", "assessment.method.purpose"),
    (r"^provenance", "assessment.check.basis_notes"),
    (r"^summary_quantities\.(timber_dry|timber_carbon|concrete_uptake)", "assessment.assumptions.carbon_coefficients"),
    (r"^summary_quantities", "construction.item_details.physical"),
    (r"^materials\[\]\.(material_id|specification)$", "construction.item_details.spec"),
    (r"^materials\[\]\.(construction_division|material_class)$", "construction.item_details.code"),
    (r"^materials\[\]\.(quantity|quantity_basis)$", "construction.item_details.quantity"),
    (r"^materials\[\]\.quantity_unit$", "construction.item_details.quantity_unit"),
    (r"^materials\[\]\.waste_rate$", "construction.transport.offcut_waste"), (r"^materials\[\]\.reuse_rate$", "construction.transport.reuse_recycle"),
    (r"^materials\[\]\.(material_life|refresh_cycle)$", "operation.maintenance.material_cycle"),
    (r"^materials\[\]\.repair_rate$", "operation.maintenance.repair_rate"), (r"^materials\[\]\.epd", "assessment.factors.epd"),
    (r"^materials\[\]\.composition", "assessment.factors.composite_factor"), (r"^materials\[\]\.conversions", "assessment.conversions.conversion_method"),
    (r"^materials\[\]\.unquantified_cost_ratio$", "assessment.conversions.unquantified"),
    (r"^materials\[\]\.transport\.(factor_id|delivery_factor_id)$", "assessment.factors.material_factor"),
    (r"^materials\[\]\.transport", "construction.transport.delivery"),
    (r"^materials\[\]\.end_of_life\.(haul_distance_km|haul_factor_id)$", "operation.end_of_life.waste_transport"),
    (r"^materials\[\]\.end_of_life", "operation.end_of_life.treatment_share"),
    (r"^materials\[\]\.(factor_id|installation_factor_id)$", "assessment.factors.material_factor"),
    (r"^materials\[\]\.(provenance_id|states)$", "assessment.check.basis_notes"), (r"^materials", "construction.item_details"),
    (r"^equipment\[\]\.(equipment_id|model)$", "equipment.eq_details.spec"), (r"^equipment\[\]\.trade$", "equipment.eq_details.usage_location"),
    (r"^equipment\[\]\.(quantity|quantity_unit)$", "equipment.eq_details.count"), (r"^equipment\[\]\.end_of_life_mass_kg$", "equipment.eq_details.weight"),
    (r"^equipment\[\]\.service_life$", "operation.maintenance.equipment_life"),
    (r"^equipment\[\]\.replacement_event_list$", "operation.maintenance.replacement_timing"),
    (r"^equipment\[\]\.repair_rate$", "operation.maintenance.repair_rate"), (r"^equipment\[\]\..*factor_id$", "assessment.factors.material_factor"),
    (r"^equipment\[\]\.(provenance_id|states)$", "assessment.check.basis_notes"), (r"^equipment", "equipment.eq_details"),
    (r"^refrigerants\[\]\.device_id$", "equipment.refrigerant_equipment.device_link"),
    (r"^refrigerants\[\]\.substance$", "equipment.refrigerant_equipment.substance"),
    (r"^refrigerants\[\]\.application$", "equipment.refrigerant_equipment.application"),
    (r"^refrigerants\[\]\.charge_mass_kg$", "equipment.refrigerant_equipment.charge"), (r"^refrigerants\[\]\.gwp$", "assessment.factors.gwp"),
    (r"^refrigerants\[\]\.(annual_leak_rate|replacement_loss_rate)$", "operation.leakage.leak_rate"),
    (r"^refrigerants\[\]\.end_of_life_recovery_rate$", "operation.leakage.recovery_rate"),
    (r"^refrigerants\[\]\.change_years$", "operation.leakage.change_timing"), (r"^refrigerants\[\]\.service_life$", "operation.leakage.service_period"),
    (r"^refrigerants\[\]\.top_up$", "operation.leakage.top_up"), (r"^refrigerants\[\]\.(provenance_id|states)$", "assessment.check.basis_notes"),
    (r"^refrigerants", "equipment.refrigerant_equipment"),
    (r"^construction\.electricity_kwh$", "construction.temporary.site_power_gas"), (r"^construction\.fuels\[\]\.conversions", "assessment.conversions.conversion_method"),
    (r"^construction\.fuels\[\]\.factor_id$", "assessment.factors.energy_factor"), (r"^construction\.fuels", "construction.temporary.site_fuel"),
    (r"^construction\.waste_streams\[\]\.factor_id$", "assessment.factors.material_factor"),
    (r"^construction\.waste_streams", "construction.transport.offcut_waste"),
    (r"^construction\.(duration_months|temporary_works)$", "construction.temporary.direct_temporary"),
    (r"^construction\.(provenance_id|states)$", "assessment.check.basis_notes"), (r"^construction", "construction.other"),
    (r"^operation\.new_or_existing$", "building.boundary.project_type"), (r"^operation\.electricity", "operation.energy.electricity"),
    (r"^operation\.gas\.", "operation.energy.city_gas"), (r"^operation\.oil\.", "operation.energy.oil_fuel"),
    (r"^operation\.district_heat\.", "operation.energy.other_energy"), (r"^operation\.onsite_generation", "operation.generation.generation"),
    (r"^operation\.onsite_export", "operation.generation.self_use_export"), (r"^operation\.grid", "assessment.assumptions.grid_future"),
    (r"^operation\..*factor_id$", "assessment.factors.energy_factor"), (r"^operation\.facility_management_ratio$", "operation.energy.fm_ratio"),
    (r"^operation\.(energy_simulation_basis|provenance_id|states)$", "assessment.check.basis_notes"), (r"^operation", "operation.other"),
    (r"^water_waste\.water\.", "operation.utility.water"), (r"^water_waste\.sewage\.", "operation.utility.sewage"),
    (r"^water_waste\.municipal_waste\.", "operation.utility.municipal_waste"), (r"^water_waste\..*factor_id$", "assessment.factors.energy_factor"),
    (r"^water_waste", "assessment.check.basis_notes"),
    (r"^end_of_life\.demolition_activities\[\]\.factor_id$", "assessment.factors.material_factor"),
    (r"^end_of_life\.demolition_activities", "operation.end_of_life.demolition"),
    (r"^end_of_life\.waste_hauls\[\]\.factor_id$", "assessment.factors.material_factor"),
    (r"^end_of_life\.waste_hauls", "operation.end_of_life.waste_transport"), (r"^end_of_life", "assessment.check.basis_notes"),
    (r"^cost_items", "construction.item_details.cost"),
]


def tree_nodes(tree: dict) -> dict[str, str]:
    """node id -> label of every category, branch and detail of a (complete) classification tree."""
    out: dict[str, str] = {}
    for cat in tree.get("categories", []):
        out[cat["id"]] = cat.get("label", cat["id"])
        for br in cat.get("branches", []):
            bid = br["id"] if "." in br["id"] else "%s.%s" % (cat["id"], br["id"])
            out[bid] = br.get("label", bid)
            for d in br.get("details", []):
                out[d["id"]] = d.get("label", d["id"])
    return out


def for_tree(tree: dict) -> Binding:
    """Binding that files every input of the engine under the categories of the classification tree."""
    import re
    nodes = tree_nodes(tree)
    entries: dict[str, dict] = {}
    paths = [p for p, _ in schema.leaves()] + [p for p, _ in table_paths()]
    for path in paths:
        node = next((n for pat, n in TREE_RULES if re.search(pat, path)), None)
        if node is None or node not in nodes:
            raise ValueError("no node of the classification tree for the engine input %s (%s)" % (path, node))
        is_table = path.endswith(("[]", "{}"))
        entries[path] = {"id": relative_id(path[:-2] if is_table else path), "category": node.split(".")[0], "node": node}
    categories = {c["id"]: c.get("label", c["id"]) for c in tree.get("categories", []) if c["id"] != "review"}
    return Binding(id="jcat-input-tree-engine-model", version="1",
                   classification={"id": "jcat-input-tree", "name": tree.get("name"), "version": str(tree.get("version")),
                                   "note": "大分類・小分類・詳細分類は受領した入力分類による。項目の ID はエンジンの入力モデルの名前。"},
                   categories=categories, entries=entries)


def tree_coverage_by_node(tree: dict, binding: Binding) -> dict:
    """Which detail nodes of the tree have an engine input bound to them, and which have none."""
    used = collections.Counter(e.get("node") for e in binding.entries.values() if e.get("node"))
    details = [d["id"] for c in tree.get("categories", []) for b in c.get("branches", []) for d in b.get("details", [])]
    return {"details": len(details), "with_engine_input": sorted(d for d in details if used.get(d)),
            "without_engine_input": sorted(d for d in details if not used.get(d)), "engine_inputs": sum(used.values())}


def default() -> Binding:
    """The binding stored with the input classification when it is there, else the provisional one."""
    from . import enginepath
    path = os.path.join(enginepath.STUDY_ROOT, "13_INPUT_CLASSIFICATION", "binding_engine_model_v1.json")
    return load(path) if os.path.exists(path) else provisional()


# --------------------------------------------------------------------------------------------
# Classification trees
# --------------------------------------------------------------------------------------------

_NAME_KEYS = ("id", "key", "code", "name", "label", "title", "名称", "名前", "項目名", "項目", "分類名", "分類",
              "大分類", "中分類", "小分類")
_CHILD_KEYS = ("children", "branches", "details", "items", "nodes", "fields", "categories", "subcategories", "entries",
               "子", "子項目", "項目一覧", "下位分類", "中分類一覧", "小分類一覧")


def _name_of(node: dict) -> str | None:
    for key in _NAME_KEYS:
        value = node.get(key)
        if isinstance(value, (str, int)) and str(value):
            return str(value)
    return None


def _children_of(node: Any) -> list[tuple[str | None, Any]]:
    if isinstance(node, list):
        return [(None, child) for child in node]
    if isinstance(node, dict):
        for key in _CHILD_KEYS:
            if isinstance(node.get(key), (list, dict)):
                return _children_of(node[key]) if isinstance(node[key], list) else list(node[key].items())
        if _name_of(node) is None:                       # mapping style: {"name": {...}, ...}
            return [(k, v) for k, v in node.items() if isinstance(v, (dict, list))]
    return []


def read_tree(data: Any, source: str = "") -> dict:
    """Summary of a classification tree of unknown shape: categories, leaves and "other" nodes.

    Only common shapes are understood (lists of nodes, nodes with a name and a list of
    children, or nested mappings keyed by name). The result says what was found; it does not
    interpret the meaning of any item.
    """
    leaves: list[dict] = []
    others: list[dict] = []

    def walk(node: Any, hint: str | None, trail: tuple[str, ...]) -> None:
        if isinstance(node, str):                               # an item given only by its name
            node, hint = {}, node
        name = (_name_of(node) if isinstance(node, dict) else None) or hint
        here = trail + ((name,) if name else ())
        children = _children_of(node)
        if name and any(word in name.lower() for word in OTHER_WORDS):
            others.append({"id": name, "trail": list(here)})
        if not children:
            if name:
                leaves.append({"id": name, "category": here[0] if here else None, "trail": list(here)})
            return
        for key, child in children:
            walk(child, key, here)

    top = _children_of(data)
    for key, child in top:
        walk(child, key, ())
    categories = []
    for key, child in top:
        name = (_name_of(child) if isinstance(child, dict) else None) or key
        categories.append({"id": name, "n_leaves": sum(1 for leaf in leaves if leaf["category"] == name)})
    return {"source": source, "n_categories": len(categories), "categories": categories,
            "n_leaves": len(leaves), "leaves": leaves, "others": others}


def tree_coverage(tree: dict, binding: Binding) -> dict:
    """Which leaves of a classification tree a binding connects to the engine's input model."""
    bound_ids = {entry["id"] for entry in binding.entries.values()}
    tree_ids = [leaf["id"] for leaf in tree["leaves"]]
    return {"tree_leaves": len(tree_ids),
            "bound": sorted(i for i in tree_ids if i in bound_ids),
            "unbound": sorted(i for i in tree_ids if i not in bound_ids),
            "binding_ids_not_in_tree": sorted(bound_ids - set(tree_ids))}
