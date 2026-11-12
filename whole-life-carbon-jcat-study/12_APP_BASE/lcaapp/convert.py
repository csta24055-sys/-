"""Common internal format -> the engine's input (a ``synth.model.Scenario``), built once per input.

The engine then flattens the scenario into its column tables, index sets and knot lattices
by itself (``tstudy.tables`` / ``tstudy.index``); nothing of that is repeated here.

Rules
  entered / zero   the value is handed over
  missing          None (a blank text stays ""); the engine skips what depends on it and says so
  absent           a table: no rows; a row marked absent: left out; a single value: None, because
                   the engine has no separate way to be told "does not exist" for one value
  invalid          None; the original stays in the common format and is listed as unsupported
Nothing is invented. The only values written here are the year tables that the model
defines as a redundant copy of a closed-form descriptor (CONSTANT, LINEAR_TREND, ...).
"""
from __future__ import annotations

from typing import Any

from . import enginepath, schema

FICTIONAL_TAG = "SYNTHETIC_FICTIONAL"
USER_TAG = "USER_INPUT_UNVERIFIED"
PROFILES = (("operation", ("electricity", "gas", "oil", "district_heat", "onsite_generation", "onsite_export")),
            ("water_waste", ("water", "sewage", "municipal_waste")))


class ConversionError(RuntimeError):
    """The engine's input object could not be built from the data."""


def _has_data(cnode: dict) -> bool:
    if cnode["t"] == "c":
        return cnode["s"] in ("entered", "zero")
    if cnode["t"] == "tab":
        return cnode["s"] in ("entered", "absent")
    return any(_has_data(child) for child in cnode["f"].values())


class _Walk:
    def __init__(self):
        self.not_passed: dict[str, list[str]] = {"missing": [], "absent": [], "invalid": []}
        self.counts = {"missing": 0, "absent": 0, "invalid": 0, "missing_optional": 0}
        self.dropped_rows: list[str] = []
        self.notes: list[dict] = []

    def _mark(self, state: str, where: str) -> None:
        self.counts[state] += 1
        if len(self.not_passed[state]) < 300:
            self.not_passed[state].append(where)

    def leaf(self, node: dict, cell: dict, where: str):
        state = cell["s"]
        if state in ("entered", "zero"):
            return cell["v"]
        if cell.get("why") != "unbound":
            self._mark(state, where)
            if state == "missing" and node["optional"]:
                self.counts["missing_optional"] += 1         # a leaf the model allows to be empty
        if node["kind"] == "map":
            return {}
        return cell.get("v") if state == "missing" else None       # "" for a blank text, else None

    def record(self, node: dict, cnode: dict, where: str) -> dict:
        out: dict[str, Any] = {}
        for name, child in node["fields"].items():
            c, w = cnode["f"][name], f"{where}.{name}" if where else name
            if child["type"] == "leaf":
                out[name] = self.leaf(child, c, w)
            elif child["type"] == "record":
                out[name] = None if child["optional"] and not _has_data(c) else self.record(child, c, w)
            else:
                out[name] = self.table(child, c, w)
        return out

    def table(self, node: dict, cnode: dict, where: str):
        if cnode["s"] in ("missing", "invalid"):
            if cnode.get("why") != "unbound":
                self._mark(cnode["s"], where)
            return None if node["optional"] else ({} if node["type"] == "ktable" else [])
        rows = []
        for i, row in enumerate(cnode["rows"]):
            w = f"{where}[{i}]"
            if row.get("s") == "absent":
                self._mark("absent", w)
                self.dropped_rows.append(w)
                continue
            rows.append((w, self.record(node["row"], row, w)))
        if node["type"] == "table":
            return [rec for _, rec in rows]
        out = {}
        for w, rec in rows:
            key = rec.get(node["key"])
            if key is None or key == "" or key in out:
                self.dropped_rows.append(w)
                self.notes.append({"level": "error", "code": "row_key", "path": w,
                                   "message": "キー（%s）がない、または重複している行は使わない" % node["key"]})
                continue
            out[key] = rec
        return out


def _number(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _expand_tables(model_dict: dict, notes: list[dict]) -> list[str]:
    """Write the year tables that are a redundant copy of a closed-form descriptor."""
    gen = enginepath.generator()
    n = schema.year_table_length()
    done = []
    for section, names in PROFILES:
        for name in names:
            prof = (model_dict.get(section) or {}).get(name)
            if not isinstance(prof, dict) or prof.get("table") is not None:
                continue
            kind, base, slope = prof.get("kind"), prof.get("base"), prof.get("slope")
            if kind == "CONSTANT" and _number(base):
                prof["table"] = [base] * n
            elif kind == "LINEAR_TREND" and _number(base) and _number(slope):
                prof["table"] = [base + slope * k for k in range(n)]
            else:
                continue
            done.append(f"{section}.{name}.table")
    grid = (model_dict.get("operation") or {}).get("grid")
    if isinstance(grid, dict) and grid.get("table") is None:
        kind, start = grid.get("kind"), grid.get("start")
        try:
            if kind == "CONSTANT" and _number(start):
                grid["table"] = gen.grid_table(kind, n, start=start)
            elif kind == "LINEAR_DECLINE_TO_FLOOR" and all(_number(grid.get(k)) for k in ("start", "annual_decline", "floor")):
                grid["table"] = gen.grid_table(kind, n, start=start, annual_decline=grid["annual_decline"], floor=grid["floor"])
            elif kind == "STEPWISE" and grid.get("steps"):
                steps = [enginepath.model().GridStep(s["from_index"], s["value"]) for s in grid["steps"]]
                if all(isinstance(s.from_index, int) and _number(s.value) for s in steps):
                    grid["table"] = gen.grid_table(kind, n, steps=steps)
        except (TypeError, ValueError, KeyError, IndexError):
            grid["table"] = None
        if grid.get("table") is not None:
            done.append("operation.grid.table")
    if done:
        notes.append({"level": "info", "code": "tables_expanded", "path": "",
                      "message": "年次表 %d 本を記述子（一定・直線など）から展開した：%s" % (len(done), "、".join(done))})
    return done


def _instances(value: Any, parts: list[str], where: str):
    """(concrete path, value) of every instance of a pattern path inside a model dict."""
    if not parts:
        yield where, value
        return
    head, rest = parts[0], parts[1:]
    name, marker = (head[:-2], head[-2:]) if head.endswith(("[]", "{}")) else (head, "")
    child = value.get(name) if isinstance(value, dict) else None
    w = f"{where}.{name}" if where else name
    if not marker:
        if isinstance(value, dict):
            yield from _instances(child, rest, w)
    elif isinstance(child, list):
        for i, row in enumerate(child):
            yield from _instances(row, rest, f"{w}[{i}]")
    elif isinstance(child, dict):
        for key, row in child.items():
            yield from _instances(row, rest, f"{w}{{{key}}}")


def check_required(model_dict: dict) -> list[dict]:
    """The few values without which the engine cannot evaluate the building (blocking)."""
    out = []
    for path in schema.REQUIRED:
        for where, value in _instances(model_dict, path.split("."), ""):
            if value is None or value == "" or value == {} or value == []:
                out.append({"level": "error", "code": "required", "path": where,
                            "message": "必須項目が未入力、または使えない値である（計算できない）"})
    return out


def to_model(common: dict, refset: dict, scenario_id: str, study_period: float | None = None,
             baseline_id: str | None = None) -> tuple[dict, dict]:
    """(scenario as a plain dict, conversion report). ``refset`` supplies the reference parts."""
    walk = _Walk()
    model_dict: dict[str, Any] = {}
    for name, node in schema.building_sections().items():
        cnode = common["sections"][name]
        if node["type"] == "record":
            model_dict[name] = walk.record(node, cnode, name)
        elif node["type"] in ("table", "ktable"):
            model_dict[name] = walk.table(node, cnode, name)
        else:
            model_dict[name] = walk.leaf(node, cnode, name)
    notes = list(walk.notes)
    expanded = _expand_tables(model_dict, notes)
    data = refset.get("data") or {}
    for part in schema.REFERENCE_PARTS:
        node = schema.model_schema()[part]
        empty: Any = {} if node["type"] == "ktable" or node.get("kind") == "map" else []
        model_dict[part] = data.get(part, empty)
    project = model_dict.get("project") or {}
    boundary = model_dict.get("boundary")
    if isinstance(boundary, dict):
        if study_period is not None:
            boundary["study_period"] = study_period            # the calculation condition decides
        boundary["baseline_scenario"] = baseline_id
    model_dict["meta"] = {
        "scenario_id": scenario_id, "seed": 0,
        "structure": project.get("structure_type") or "", "use": project.get("building_use") or "",
        "size_class": "", "flags": {}, "injected_defects": [], "notes": [],
        "source_tag": FICTIONAL_TAG if common.get("data_kind") == "fictional" else USER_TAG,
    }
    blocking = check_required(model_dict)
    if walk.counts["absent"]:
        notes.append({"level": "info", "code": "absent_as_none", "path": "",
                      "message": "「存在しない」とされた単独の値はエンジンへ「値なし」として渡した（行・表は行なしとして渡した）"})
    report = {"blocking": blocking, "notes": notes, "expanded_tables": expanded,
              "not_passed": walk.not_passed, "not_passed_counts": walk.counts,
              "dropped_rows": walk.dropped_rows,
              "rows": {name: len(model_dict[name]) for name in ("materials", "equipment", "refrigerants", "cost_items")
                       if isinstance(model_dict.get(name), list)}}
    return model_dict, report


def build_scenario(model_dict: dict):
    """The engine's input object. Raises ``ConversionError`` with the reason instead of crashing."""
    try:
        return enginepath.model_io().from_dict(model_dict)
    except Exception as exc:                                    # shape the dataclasses cannot take
        raise ConversionError("エンジンの入力形式に組み立てられなかった：%s: %s" % (type(exc).__name__, exc)) from exc
