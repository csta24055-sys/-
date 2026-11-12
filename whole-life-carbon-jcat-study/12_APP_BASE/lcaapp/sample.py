"""Fictional test inputs for developers (input screen 1 is not part of this base system).

``fictional_building`` asks the frozen generator of the earlier study for one fictional
building and writes it as an input document plus the reference data set it needs. Every
number is fictional; none describes a real building or a real emission factor.
"""
from __future__ import annotations

import json
from typing import Any

from . import INPUT_FORMAT, enginepath, refdata, schema
from .binding import Binding
from .common import looks_like_cell

REFSET_NAME = "fictional-demo"


def _cell(value: Any) -> Any:
    return {"value": value} if looks_like_cell(value) else value


def _record(node: dict, value: dict | None, path: str, binding: Binding, put_item, put_table) -> None:
    for name, child in node["fields"].items():
        p = f"{path}.{name}"
        v = None if value is None else value.get(name)
        if child["type"] == "leaf":
            item_id = binding.id_for(p)
            if item_id is not None and value is not None:
                put_item(p, item_id, _cell(v))
        elif child["type"] == "record":
            _record(child, v, p, binding, put_item, put_table)
        else:
            marker = "[]" if child["type"] == "table" else "{}"
            table_id = binding.id_for(p + marker)
            if table_id is not None and v is not None:
                put_table(p + marker, table_id, _rows(child, v, p + marker, binding))


def _rows(node: dict, value: Any, path: str, binding: Binding) -> list[dict]:
    rows = []
    for rec in (value.values() if isinstance(value, dict) else value):
        items: dict[str, Any] = {}
        nested: dict[str, Any] = {}
        _record(node["row"], rec, path, binding,
                lambda p, i, v, items=items: items.__setitem__(i, v),
                lambda p, i, v, nested=nested: nested.__setitem__(i, v))
        if nested:
            items["@tables"] = nested
        rows.append(items)
    return rows


def document_from_model(model_dict: dict, binding: Binding, title: str, data_kind: str = "fictional",
                        refset: dict | None = None) -> dict:
    """Input document that says the same as a scenario dict (inverse of the conversion)."""
    categories: dict[str, dict] = {cat: {"items": {}, "tables": {}, "others": []} for cat in binding.categories}   # in the order of the classification

    def bucket(path: str) -> dict:
        cat = binding.category_for(path) or "未分類"
        return categories.setdefault(cat, {"items": {}, "tables": {}, "others": []})

    def put_item(path: str, item_id: str, value: Any) -> None:
        bucket(path)["items"][item_id] = value

    def put_table(path: str, table_id: str, rows: list) -> None:
        bucket(path)["tables"][table_id] = rows

    for name, node in schema.building_sections().items():
        value = model_dict.get(name)
        if node["type"] == "record":
            _record(node, value, name, binding, put_item, put_table)
        else:
            marker = "[]" if node["type"] == "table" else "{}"
            table_id = binding.id_for(name + marker)
            if table_id is not None and value is not None:
                put_table(name + marker, table_id, _rows(node, value, name + marker, binding))
    doc = {"format": INPUT_FORMAT, "data_kind": data_kind, "title": title,
           "classification": binding.classification,
           "conditions": {"study_period": (model_dict.get("boundary") or {}).get("study_period")},
           "categories": categories}
    if refset is not None:
        doc["reference_set"] = {"name": refset["name"], "version": refset["version"]}
    return doc


def fictional_building(seed: int = 4201, structure: str = "RC", use: str = "office", size: str = "S",
                       study_period: float = 60.0, rows: int | None = 12, dirty: bool = False,
                       binding: Binding | None = None, **options) -> tuple[dict, dict, dict]:
    """(input document, reference set, scenario dict) of one fictional building.

    ``rows`` keeps only the first rows of the long tables so that the sample stays small;
    ``None`` keeps everything the generator makes.
    """
    from . import binding as binding_mod
    gen, io = enginepath.generator(), enginepath.model_io()
    scn = gen.make_scenario(seed, structure, use, size, study_period, dirty=dirty, **options)
    model_dict = json.loads(json.dumps(io.to_dict(scn)))
    if rows is not None:
        model_dict["materials"] = model_dict["materials"][:rows]
        model_dict["equipment"] = model_dict["equipment"][:max(2, rows // 3)]
        model_dict["refrigerants"] = model_dict["refrigerants"][:max(1, rows // 6)]
    binding = binding or binding_mod.default()
    note = "架空データ。凍結済みの生成器 synth.generate.make_scenario(seed=%d, %s, %s, %s) の出力。実在の建物・原単位ではない。" % (
        seed, structure, use, size)
    refset = refdata.from_model(model_dict, REFSET_NAME, "seed-%d" % seed, note)
    title = "架空の建物（%s・%s・seed %d）" % (structure, use, seed)
    return document_from_model(model_dict, binding, title, "fictional", refset), refset, model_dict
