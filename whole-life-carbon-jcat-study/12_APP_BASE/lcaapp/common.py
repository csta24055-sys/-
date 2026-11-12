"""Input document (classification item space) -> common internal format (engine model space).

Input document ``lca-input/1``::

    {"format": "lca-input/1", "data_kind": "fictional" | "real" | "unknown", "title": "...",
     "categories": {"<category id>": {
         "items":  {"<item id>": CELL, ...},
         "tables": {"<table id>": [ROW, ...]},          ROW = {"<column id>": CELL, ...,
                                                               "@tables": {"<nested table id>": [ROW, ...]},
                                                               "@state": "absent"}
         "others": [{"label": "...", "value": ..., "unit": "...", "note": "..."}, ...]}}}

    CELL = a bare value                      entered (a number equal to 0 is "zero")
         | null, "" or the key left out      missing     (未入力)
         | {"state": "absent"}               absent      (存在しない)
         | {"value": v, "unit": "kg", "note": "..."}

Common format ``lca-common/1``: the same information arranged by the paths of the engine's
input model, every leaf a cell ``{"t": "c", "s": state, "v": value, ...}`` with
``s`` in entered / zero / missing / absent / invalid. Nothing is filled in: a value that is
missing stays missing, a value that cannot be used is kept as ``raw`` and reported.
"""
from __future__ import annotations

import math
from typing import Any

from . import COMMON_FORMAT, DATA_KINDS, INPUT_FORMAT, schema
from .binding import Binding

STATES = ("entered", "zero", "missing", "absent", "invalid")
STATE_LABELS = {"entered": "入力あり", "zero": "ゼロ", "missing": "未入力", "absent": "存在しない", "invalid": "使えない値"}
CELL_KEYS = {"value", "unit", "state", "note"}
MAX_ISSUES = 2000

_NOT_GIVEN = object()
_UNBOUND = object()


class InputError(ValueError):
    """The input document cannot be read at all (not a JSON object of the expected kind)."""


class _Ctx:
    def __init__(self, binding: Binding, units: dict):
        self.binding, self.units = binding, units
        self.issues: list[dict] = []
        self.n_issues = 0
        self.unsupported: list[dict] = []
        self.stats = {s: 0 for s in STATES}
        self.unbound = 0

    def issue(self, level: str, code: str, path: str, message: str) -> None:
        self.n_issues += 1
        if len(self.issues) < MAX_ISSUES:
            self.issues.append({"level": level, "code": code, "path": path, "message": message})


def looks_like_cell(raw: Any) -> bool:
    return isinstance(raw, dict) and set(raw) <= CELL_KEYS and ("value" in raw or "state" in raw)


def _is_number(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _scalar(kind: str, v: Any):
    """(ok, value, note) for one scalar of the given kind."""
    if kind == "number":
        if _is_number(v):
            return True, v, None
        if isinstance(v, str):
            try:
                x = float(v.strip())
            except ValueError:
                return False, v, "数値ではない"
            return (True, x, "文字列を数値として読んだ") if math.isfinite(x) else (False, v, "有限の数値ではない")
        return False, v, "数値ではない"
    if kind == "integer":
        if isinstance(v, int) and not isinstance(v, bool):
            return True, v, None
        if isinstance(v, float) and math.isfinite(v) and v == int(v):
            return True, int(v), "小数表記の整数を整数として読んだ"
        if isinstance(v, str):
            try:
                return True, int(v.strip()), "文字列を整数として読んだ"
            except ValueError:
                return False, v, "整数ではない"
        return False, v, "整数ではない"
    if kind == "boolean":
        return (True, v, None) if isinstance(v, bool) else (False, v, "真偽値ではない")
    if kind == "string":
        return (True, v, None) if isinstance(v, str) else (False, v, "文字列ではない")
    return True, v, None


def _check_value(leaf: dict, v: Any):
    """(ok, value, note) for a whole leaf value."""
    kind, enum = leaf["kind"], leaf.get("enum")
    if kind == "list":
        if not isinstance(v, list):
            return False, v, "一覧（配列）ではない"
        out = []
        for x in v:
            ok, y, note = _scalar(leaf["elem"], x)
            if not ok or y is None:
                return False, v, "一覧の要素が使えない（%s）" % (note or "値なし")
            if enum and y not in enum:
                return False, v, "一覧の要素 %r は語彙にない" % (y,)
            out.append(y)
        return True, out, None
    if kind == "map":
        if not isinstance(v, dict):
            return False, v, "対応表（オブジェクト）ではない"
        out = {}
        for k, x in v.items():
            ok, y, note = _scalar(leaf["elem"], x)
            if not ok or y is None:
                return False, v, "対応表の要素 %r が使えない（%s）" % (k, note or "値なし")
            out[k] = y
        return True, out, None
    ok, y, note = _scalar(kind, v)
    if ok and enum and y not in enum:
        return False, v, "語彙にない値"
    return ok, y, note


def make_cell(raw: Any, leaf: dict, ctx: _Ctx, where: str) -> dict:
    """One leaf of the common format from whatever the document holds at that place."""
    if raw is _UNBOUND:
        ctx.unbound += 1
        ctx.stats["missing"] += 1
        return {"t": "c", "s": "missing", "v": None, "why": "unbound"}
    unit = note = state = None
    value = None if raw is _NOT_GIVEN else raw
    if looks_like_cell(raw):
        value, unit, state, note = raw.get("value"), raw.get("unit"), raw.get("state"), raw.get("note")
        if state is not None and state not in ("entered", "zero", "missing", "absent"):
            ctx.issue("warning", "unknown_state", where, "状態 %r は使えないので、値から判定した" % (state,))
            state = None
        if unit is not None and not isinstance(unit, str):
            ctx.issue("warning", "unit_not_text", where, "単位が文字列ではないので無視した")
            unit = None
    cell: dict = {"t": "c"}
    if note is not None:
        cell["note"] = str(note)

    def done(s: str, v: Any = None) -> dict:
        cell["s"], cell["v"] = s, v
        ctx.stats[s] += 1
        return cell

    if state == "absent":
        if value not in (None, ""):
            cell["raw"] = raw
            ctx.issue("warning", "absent_with_value", where, "「存在しない」と値が同時に指定されている。値は使わない")
        return done("absent")
    if state == "zero" and value is None:
        value = 0
    if state == "missing" or value is None:
        return done("missing")
    if value == "" and isinstance(value, str):
        return done("missing", "" if leaf["kind"] == "string" else None)     # a blank text field
    ok, value2, why = _check_value(leaf, value)
    if not ok:
        cell["raw"] = raw
        ctx.issue("error", "invalid_value", where, "%s：%s。計算には渡さない" % (_short(value), why))
        return done("invalid")
    if why:
        ctx.issue("info", "coerced", where, why)
        cell["raw"] = raw
    value = value2
    if unit is not None:
        expected = leaf.get("unit")
        if leaf.get("unit_leaf") or leaf["kind"] not in ("number", "integer"):
            cell["u"] = unit                                  # kept; compared with the unit leaf by the caller
        elif expected is None:
            cell["u"] = unit
            ctx.issue("info", "unit_kept", where, "単位 %s は保持した（この項目には照合する単位の定めがない）" % unit)
        elif unit != expected:
            factor = ctx.units.get((unit, expected))
            if factor is None:
                cell["raw"] = raw
                ctx.issue("error", "unit_mismatch", where,
                          "単位 %s を %s へ換算する定義がない。計算には渡さない" % (unit, expected))
                return done("invalid")
            cell["raw"] = raw
            value = value * factor
            cell["u"] = expected
            ctx.issue("info", "unit_converted", where, "単位を %s から %s へ換算した（倍率 %r）" % (unit, expected, factor))
        else:
            cell["u"] = unit
    is_zero = _is_number(value) and value == 0
    if state == "zero" and not is_zero:
        ctx.issue("warning", "zero_with_value", where, "「ゼロ」と 0 でない値が同時に指定されている。値を使う")
    return done("zero" if is_zero else "entered", value)


def _short(v: Any) -> str:
    text = repr(v)
    return text if len(text) <= 60 else text[:57] + "..."


def _record(node: dict, path: str, where: str, items: dict, tables: dict, ctx: _Ctx) -> dict:
    """Fill one record of the model from the pools of items and tables given at that level."""
    fields: dict[str, dict] = {}
    for name, child in node["fields"].items():
        p, w = f"{path}.{name}" if path else name, f"{where}.{name}" if where else name
        if child["type"] == "leaf":
            item_id = ctx.binding.id_for(p)
            raw = _UNBOUND if item_id is None else items.pop(item_id, _NOT_GIVEN)
            fields[name] = make_cell(raw, child, ctx, w)
        elif child["type"] == "record":
            fields[name] = _record(child, p, w, items, tables, ctx)
        else:
            fields[name] = _table(child, p, w, tables, ctx)
    for name, child in node["fields"].items():              # a quantity that carries its own unit
        if child["type"] == "leaf" and child.get("unit_leaf") and "u" in fields[name]:
            target = fields.get(child["unit_leaf"])
            unit, w = fields[name]["u"], f"{where}.{name}"
            if target is None or target.get("t") != "c":
                continue
            if target["s"] == "missing":
                ctx.stats["missing"] -= 1
                ctx.stats["entered"] += 1
                target.update({"s": "entered", "v": unit, "why": "from_value_unit"})
            elif target["v"] != unit:
                ctx.issue("error", "unit_conflict", w, "値に付いた単位 %s と単位の項目 %s が食い違う。計算には渡さない"
                          % (unit, target["v"]))
                ctx.stats[fields[name]["s"]] -= 1
                ctx.stats["invalid"] += 1
                fields[name].update({"s": "invalid", "raw": {"value": fields[name]["v"], "unit": unit}, "v": None})
    return {"t": "rec", "f": fields}


def _table(node: dict, path: str, where: str, tables: dict, ctx: _Ctx) -> dict:
    marker = "[]" if node["type"] == "table" else "{}"
    table_id = ctx.binding.id_for(path + marker)
    out: dict = {"t": "tab", "rows": []}
    if table_id is None:
        out["s"], out["why"] = "missing", "unbound"
        ctx.unbound += 1
        return out
    raw = tables.pop(table_id, _NOT_GIVEN)
    if looks_like_cell(raw) and raw.get("state") in ("absent", "missing") and raw.get("value") in (None, []):
        out["s"] = raw["state"]
        return out
    if raw is _NOT_GIVEN or raw is None:
        out["s"] = "missing"
        return out
    if not isinstance(raw, list):
        out["s"], out["raw"] = "invalid", raw
        ctx.issue("error", "invalid_table", where, "表は行の一覧（配列）で与える。計算には渡さない")
        return out
    out["s"] = "entered" if raw else "absent"                # an empty list says: there are none
    for i, row in enumerate(raw):
        w = f"{where}[{i}]"
        if not isinstance(row, dict):
            ctx.issue("error", "invalid_row", w, "行はオブジェクトで与える。この行は使わない")
            ctx.unsupported.append({"kind": "invalid_row", "where": w, "raw": row})
            continue
        row = dict(row)
        nested = row.pop("@tables", None)
        state = row.pop("@state", None)
        note = row.pop("@note", None)
        if nested is not None and not isinstance(nested, dict):
            ctx.issue("error", "invalid_nested", w, "@tables はオブジェクトで与える。入れ子の表は使わない")
            ctx.unsupported.append({"kind": "invalid_nested", "where": w, "raw": nested})
            nested = None
        nested = dict(nested or {})
        rec = _record(node["row"], path + marker, w, row, nested, ctx)
        if state == "absent":
            rec["s"] = "absent"
        elif state is not None:
            ctx.issue("warning", "unknown_state", w, "行の状態 %r は使えないので無視した" % (state,))
        if note is not None:
            rec["note"] = str(note)
        for key, value in row.items():
            ctx.unsupported.append({"kind": "unknown_column", "where": w, "id": key, "raw": value})
        for key, value in nested.items():
            ctx.unsupported.append({"kind": "unknown_table", "where": w, "id": key, "raw": value})
        out["rows"].append(rec)
    return out


def _others(category: str, raw: Any, ctx: _Ctx) -> list[dict]:
    """"Other" entries are kept as they are; they are never turned into numbers for the engine."""
    out = []
    if raw is None:
        return out
    if not isinstance(raw, list):
        raw = [raw]
    for i, entry in enumerate(raw):
        if isinstance(entry, dict):
            out.append({"category": category, "label": str(entry.get("label", "")), "value": entry.get("value"),
                        "unit": entry.get("unit") if isinstance(entry.get("unit"), str) else None,
                        "note": None if entry.get("note") is None else str(entry.get("note")), "raw": entry})
        else:
            out.append({"category": category, "label": "", "value": entry, "unit": None, "note": None, "raw": entry})
    return out


def build(doc: Any, binding: Binding, units: dict | None = None) -> dict:
    """Common internal format of one input document. Never raises on bad content, only on a
    document that is not an object at all."""
    if not isinstance(doc, dict):
        raise InputError("入力文書は JSON オブジェクトでなければならない")
    ctx = _Ctx(binding, units or {})
    if doc.get("format") != INPUT_FORMAT:
        ctx.issue("warning", "format", "format", "format が %s ではない（%r）。そのまま読んだ" % (INPUT_FORMAT, doc.get("format")))
    data_kind = doc.get("data_kind")
    if data_kind not in DATA_KINDS:
        ctx.issue("warning", "data_kind", "data_kind", "data_kind が %s のどれでもない。unknown として扱う" % "／".join(DATA_KINDS))
        data_kind = "unknown"
    items: dict[str, Any] = {}
    tables: dict[str, Any] = {}
    origin: dict[str, str] = {}
    others: list[dict] = []
    categories = doc.get("categories")
    if categories is None:
        categories = {}
        ctx.issue("warning", "no_categories", "categories", "categories がない。すべて未入力として扱う")
    if not isinstance(categories, dict):
        ctx.issue("error", "invalid_categories", "categories", "categories はオブジェクトで与える。入力は読めなかった")
        ctx.unsupported.append({"kind": "invalid_categories", "where": "categories", "raw": categories})
        categories = {}
    for cat, body in categories.items():
        if not isinstance(body, dict):
            ctx.issue("error", "invalid_category", f"categories.{cat}", "分類の中身はオブジェクトで与える。この分類は読めなかった")
            ctx.unsupported.append({"kind": "invalid_category", "where": f"categories.{cat}", "raw": body})
            continue
        for pool, key in ((items, "items"), (tables, "tables")):
            part = body.get(key)
            if part is None:
                continue
            if not isinstance(part, dict):
                ctx.issue("error", "invalid_" + key, f"categories.{cat}.{key}", "%s はオブジェクトで与える。読めなかった" % key)
                ctx.unsupported.append({"kind": "invalid_" + key, "where": f"categories.{cat}.{key}", "raw": part})
                continue
            for item_id, raw in part.items():
                tag = ("T:" if pool is tables else "I:") + item_id
                if item_id in pool:
                    ctx.issue("warning", "duplicate_id", f"categories.{cat}.{key}.{item_id}",
                              "同じ ID が分類 %s にもある。先のものを使う" % origin[tag])
                    ctx.unsupported.append({"kind": "duplicate_id", "where": f"categories.{cat}.{key}", "id": item_id, "raw": raw})
                    continue
                pool[item_id] = raw
                origin[tag] = cat
        others.extend(_others(cat, body.get("others"), ctx))
        for key in body:
            if key not in ("items", "tables", "others", "label", "note"):
                ctx.unsupported.append({"kind": "unknown_key", "where": f"categories.{cat}", "id": key, "raw": body[key]})
    sections = {}
    for name, node in schema.building_sections().items():
        if node["type"] == "record":
            sections[name] = _record(node, name, name, items, tables, ctx)
        elif node["type"] in ("table", "ktable"):
            sections[name] = _table(node, name, name, tables, ctx)
        else:
            item_id = binding.id_for(name)
            sections[name] = make_cell(_UNBOUND if item_id is None else items.pop(item_id, _NOT_GIVEN), node, ctx, name)
    for item_id, raw in items.items():
        ctx.unsupported.append({"kind": "unknown_item", "where": "categories.%s.items" % origin["I:" + item_id], "id": item_id, "raw": raw})
    for table_id, raw in tables.items():
        ctx.unsupported.append({"kind": "unknown_table", "where": "categories.%s.tables" % origin["T:" + table_id], "id": table_id, "raw": raw})
    if ctx.unsupported:
        ctx.issue("warning", "unsupported", "", "計算に使えない入力が %d 件ある（内容は保存し、未対応として一覧に出す）" % len(ctx.unsupported))
    return {
        "format": COMMON_FORMAT,
        "data_kind": data_kind,
        "title": str(doc.get("title") or ""),
        "binding": binding.describe(),
        "declared": {"reference_set": doc.get("reference_set"), "conditions": doc.get("conditions")},
        "sections": sections,
        "others": others,
        "unsupported": ctx.unsupported,
        "issues": ctx.issues,
        "n_issues": ctx.n_issues,
        "stats": dict(ctx.stats, unbound=ctx.unbound, others=len(others), unsupported=len(ctx.unsupported)),
    }


def unit_table(unit_conversions: list[dict] | None) -> dict:
    """{(from unit, to unit): factor} from the documented conversions of a reference data set."""
    out = {}
    for conv in unit_conversions or []:
        if isinstance(conv, dict) and _is_number(conv.get("factor")):
            out[(conv.get("from_unit"), conv.get("to_unit"))] = conv["factor"]
    return out


def summary(common: dict) -> dict:
    """Small report of a common document for lists and notes (no row data)."""
    levels = {"error": 0, "warning": 0, "info": 0}
    for issue in common["issues"]:
        levels[issue["level"]] = levels.get(issue["level"], 0) + 1
    return {"stats": common["stats"], "issue_levels": levels, "n_issues": common["n_issues"],
            "issues_truncated": common["n_issues"] > len(common["issues"]),
            "data_kind": common["data_kind"], "binding": common["binding"], "declared": common["declared"],
            "title": common["title"]}
