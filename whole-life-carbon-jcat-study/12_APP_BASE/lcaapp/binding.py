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

import json
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
    return Binding(str(data.get("id") or "binding"), str(data.get("version") or "0"),
                   dict(data.get("classification") or {}), dict(data.get("categories") or {}), entries)


def load(path: str) -> Binding:
    with open(path, encoding="utf-8") as fh:
        return from_json(json.load(fh))


# --------------------------------------------------------------------------------------------
# Classification trees
# --------------------------------------------------------------------------------------------

_NAME_KEYS = ("id", "key", "code", "name", "label", "title", "名称", "名前", "項目名", "項目", "分類名", "分類",
              "大分類", "中分類", "小分類")
_CHILD_KEYS = ("children", "items", "nodes", "fields", "categories", "subcategories", "entries",
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
