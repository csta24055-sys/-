"""Relational view of a scenario: every input as columns of tables (generic, unit-independent).

The scenario of the frozen generator is a tree of dataclasses. This module flattens it by
reflection into tables of columns, without any knowledge of evaluation units:

  * a list of records becomes a table; a record nested in a row becomes dotted columns
    (``transport.mass_t``) plus a count column ``<field>#`` that is 1 where the record exists
    (missing where the field is None), so an optional record can be told from an absent one;
  * a list of records inside a row becomes a child table ``parent.field`` with a ``_parent``
    column (row index in the parent) and ``_pos`` (position in the list);
  * a list of numbers inside a row becomes a child table with ``_parent``, ``_pos``, ``value``;
  * a dictionary inside a row becomes a child table with ``_parent``, ``key``, ``value``
    (or the columns of the record when the values are records);
  * numbers are float arrays with NaN for a missing value (None) and a boolean companion
    column ``<name>?`` that is True where a value is present; everything else is an object array.

A missing list (None) and an empty list are told apart by the companion column of the parent
(``<field>?``). Nothing is computed here; the flattening is the same for every scenario.
"""
from __future__ import annotations

import dataclasses
import math
from typing import Any

import numpy as np


class Table:
    def __init__(self, name: str):
        self.name = name
        self.n = 0
        self._cols: dict[str, list] = {}

    def add_row(self) -> int:
        self.n += 1
        return self.n - 1

    def put(self, row: int, col: str, value: Any) -> None:
        c = self._cols.setdefault(col, [])
        while len(c) < row:
            c.append(None)
        if len(c) == row:
            c.append(value)
        else:
            c[row] = value

    def finish(self) -> dict[str, np.ndarray]:
        out: dict[str, np.ndarray] = {}
        for name, values in self._cols.items():
            values = values + [None] * (self.n - len(values))
            numeric = all(v is None or (isinstance(v, (int, float)) and not isinstance(v, bool)) for v in values)
            if numeric and any(v is not None for v in values) or (numeric and not values):
                out[name] = np.array([math.nan if v is None else float(v) for v in values], dtype=float)
                out[name + "?"] = np.array([v is not None for v in values], dtype=bool)
            elif all(v is None or isinstance(v, bool) for v in values) and any(v is not None for v in values):
                out[name] = np.array([bool(v) if v is not None else False for v in values], dtype=bool)
                out[name + "?"] = np.array([v is not None for v in values], dtype=bool)
            else:
                arr = np.empty(self.n, dtype=object)
                for i, v in enumerate(values):
                    arr[i] = v
                out[name] = arr
                out[name + "?"] = np.array([v is not None for v in values], dtype=bool)
        return out


class Tables:
    """All tables of one scenario: ``tables["materials"]["quantity"]`` is a column."""

    def __init__(self):
        self._raw: dict[str, Table] = {}
        self.data: dict[str, dict[str, np.ndarray]] = {}
        self.rows: dict[str, int] = {}

    def table(self, name: str) -> Table:
        if name not in self._raw:
            self._raw[name] = Table(name)
        return self._raw[name]

    def finish(self) -> "Tables":
        for name, t in self._raw.items():
            self.data[name] = t.finish()
            self.rows[name] = t.n
        return self

    def __getitem__(self, name: str) -> dict[str, np.ndarray]:
        return self.data[name]

    def describe(self) -> dict[str, dict]:
        return {name: {"rows": self.rows[name], "columns": sorted(c for c in cols if not c.endswith("?"))}
                for name, cols in sorted(self.data.items())}


def _is_record(v) -> bool:
    return dataclasses.is_dataclass(v) and not isinstance(v, type)


def _put_value(tabs: Tables, tname: str, row: int, col: str, v) -> None:
    t = tabs.table(tname)
    if _is_record(v):
        t.put(row, col + "#", 1)
        _put_record(tabs, tname, row, v, col + ".")
    elif isinstance(v, (list, tuple)):
        t.put(row, col + "#", len(v))
        child = f"{tname}.{col}"
        for pos, item in enumerate(v):
            r = tabs.table(child).add_row()
            tabs.table(child).put(r, "_parent", row)
            tabs.table(child).put(r, "_pos", pos)
            if _is_record(item):
                _put_record(tabs, child, r, item, "")
            else:
                tabs.table(child).put(r, "value", item)
    elif isinstance(v, dict):
        t.put(row, col + "#", len(v))
        child = f"{tname}.{col}"
        for pos, (key, item) in enumerate(v.items()):
            r = tabs.table(child).add_row()
            tabs.table(child).put(r, "_parent", row)
            tabs.table(child).put(r, "_pos", pos)
            tabs.table(child).put(r, "key", key)
            if _is_record(item):
                _put_record(tabs, child, r, item, "")
            else:
                tabs.table(child).put(r, "value", item)
    else:
        t.put(row, col, v)


def _put_record(tabs: Tables, tname: str, row: int, rec, prefix: str) -> None:
    for f in dataclasses.fields(rec):
        _put_value(tabs, tname, row, prefix + f.name, getattr(rec, f.name))


def from_scenario(scn) -> Tables:
    """Flatten a scenario into tables (see the module docstring)."""
    tabs = Tables()
    for f in dataclasses.fields(scn):
        v = getattr(scn, f.name)
        if isinstance(v, (list, tuple)):
            tabs.table(f.name)
            for item in v:
                r = tabs.table(f.name).add_row()
                if _is_record(item):
                    _put_record(tabs, f.name, r, item, "")
                else:
                    tabs.table(f.name).put(r, "value", item)
        elif isinstance(v, dict):
            tabs.table(f.name)
            for key, item in v.items():
                r = tabs.table(f.name).add_row()
                tabs.table(f.name).put(r, "key", key)
                if _is_record(item):
                    _put_record(tabs, f.name, r, item, "")
                else:
                    tabs.table(f.name).put(r, "value", item)
        elif _is_record(v):
            r = tabs.table(f.name).add_row()
            _put_record(tabs, f.name, r, v, "")
        else:
            r = tabs.table("scalars").add_row() if tabs.table("scalars").n == 0 else 0
            tabs.table("scalars").put(r, f.name, v)
    return tabs.finish()
