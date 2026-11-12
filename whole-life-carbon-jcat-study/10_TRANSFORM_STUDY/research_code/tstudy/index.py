"""Common tables of the unified system: index sets, lexical tokens and knot lattices.

Everything here is GENERIC: no function knows an evaluation unit, a field name of the concept
model or an emission formula. The functions only

  * split text at fixed separators (``tokenise``),
  * enumerate index sets (``add_product``, ``add_range``, ``add_distinct``, ``add_static``),
  * generate the knot lattices of a cycle or of a list of times and locate each knot in the
    year grid (``add_events``).

No arithmetic on input VALUES happens here except the knot positions ``n * cycle`` and the
year cell ``ceil(tau * (1 - eps)) - 1`` of a knot, which belong to the knot-spectrum structure
(the same rules as ``tstudy.rampstep``). Which tables are built for the concept model is
declared as data in ``specs/system.py`` (``INDEX_PLAN``).

Fictional data, independent concept model.
"""
from __future__ import annotations

import re

import numpy as np

from . import rampstep as rs

_BRACKET = re.compile(r"^([^\[\]]*)\[(\d+)\](?:\.(.*))?$")


def objects(values) -> np.ndarray:
    a = np.empty(len(values), dtype=object)
    for i, v in enumerate(values):
        a[i] = v
    return a


def put_table(tabs, name: str, cols: dict, masks: dict | None = None) -> None:
    """Add (or replace) a table; every column is fully present unless a mask is given."""
    n = 0
    data = {}
    for key, arr in cols.items():
        n = len(arr)
        data[key] = arr
        data[key + "?"] = np.ones(len(arr), dtype=bool) if not masks or key not in masks else masks[key]
    tabs.data[name] = data
    tabs.rows[name] = n


def tokenise(tabs) -> None:
    """Lexical companions of EVERY text column of every table:

    ``<name>~h`` / ``<name>~t``   text before / after the first "/"   (``~t`` missing without "/")
    ``<name>~p`` / ``<name>~i`` / ``<name>~s``   for a text of the form ``head[123].tail`` or ``head[123]``:
                                  head, the integer index and the tail (``~s`` missing without tail)
    """
    for cols in tabs.data.values():
        for name in [c for c in cols if not c.endswith("?") and "~" not in c]:
            arr = cols[name]
            if arr.dtype != object:
                continue
            ok = cols[name + "?"]
            n = len(arr)
            h, t, p, s = (np.empty(n, dtype=object) for _ in range(4))
            idx = np.full(n, np.nan)
            hm, tm, pm, sm = (np.zeros(n, dtype=bool) for _ in range(4))
            for i in range(n):
                v = arr[i]
                if not (ok[i] and isinstance(v, str)):
                    continue
                a, sep, b = v.partition("/")
                h[i] = a
                hm[i] = True
                if sep:
                    t[i] = b
                    tm[i] = True
                if "[" in v:
                    m = _BRACKET.match(v)
                    if m:
                        p[i] = m.group(1)
                        pm[i] = True
                        idx[i] = float(m.group(2))
                        if m.group(3) is not None:
                            s[i] = m.group(3)
                            sm[i] = True
            cols[name + "~h"], cols[name + "~h?"] = h, hm
            cols[name + "~t"], cols[name + "~t?"] = t, tm
            cols[name + "~p"], cols[name + "~p?"] = p, pm
            cols[name + "~i"], cols[name + "~i?"] = idx, pm.copy()
            cols[name + "~s"], cols[name + "~s?"] = s, sm


def add_range(tabs, name: str, n: int, col: str = "i") -> None:
    """The index set 0..n-1."""
    put_table(tabs, name, {col: np.arange(n, dtype=float)})


def add_product(tabs, name: str, parent: str, n_other: int, col: str) -> None:
    """All pairs (row of ``parent``, 0..n_other-1): the index set of a two-index sum. Child table of ``parent``."""
    n = tabs.rows.get(parent, 0)
    put_table(tabs, name, {"_parent": np.repeat(np.arange(n, dtype=float), n_other),
                           col: np.tile(np.arange(n_other, dtype=float), n)})


def add_static(tabs, name: str, columns: dict) -> None:
    """A relation that is part of the model structure (written as data in the specification)."""
    cols = {}
    for key, values in columns.items():
        if any(isinstance(v, str) for v in values):
            cols[key] = objects(values)
        else:
            cols[key] = np.array([float(v) for v in values], dtype=float)
    put_table(tabs, name, cols)


def add_distinct(tabs, name: str, sources, col: str = "value") -> None:
    """The distinct present values of the listed (table, column) pairs, in ascending order."""
    seen = set()
    for table, column in sources:
        data = tabs.data.get(table, {})
        if column not in data:
            continue
        for v, ok in zip(data[column], data[column + "?"]):
            if ok and not (isinstance(v, float) and v != v):
                seen.add(v if isinstance(v, str) else float(v))
    values = sorted(seen)
    if values and isinstance(values[0], str):
        put_table(tabs, name, {col: objects(values)})
    else:
        put_table(tabs, name, {col: np.array(values, dtype=float)})


def add_sorted(tabs, name: str, source: str, by: str) -> None:
    """A copy of ``source`` with its rows in ascending order of the column ``by`` (ties keep their order).
    A sum over the copy adds the terms in that order (floating-point sums depend on the order)."""
    data, n = tabs.data.get(source, {}), tabs.rows.get(source, 0)
    order = sorted(range(n), key=lambda i: data[by][i]) if n else []
    tabs.data[name] = {k: v[order] for k, v in data.items()} if n else dict(data)
    tabs.rows[name] = n


def add_events(tabs, name: str, parent: str, horizon: float, cycle: str | None = None, lists: str | None = None) -> None:
    """Knot lattices of every row of ``parent`` (child table ``name``):

    source CYCLE  the times n*cycle (n = 1, 2, ...) of the cycle column,
    source LIST   the positive times of the child list table ``lists``,
    each with 0 < tau < horizon*(1-eps), sorted by time within (parent, source), and located in the year
    grid: ``cell`` = index k of the year cell (k, k+1] that holds the knot (rule of the concept model).
    ``ord`` is the position in the original list (LIST) or n-1 (CYCLE). Both sources are always generated;
    which one counts is decided by a mask of the sum-product.
    """
    par, tau, src, order = [], [], [], []
    n = tabs.rows.get(parent, 0)
    pdata = tabs.data.get(parent, {})
    if cycle and cycle in pdata and pdata[cycle].dtype != object:
        cyc, ok = pdata[cycle], pdata[cycle + "?"]
        for i in range(n):
            if ok[i]:
                for j, t in enumerate(rs.periodic_times(horizon, float(cyc[i]))):
                    par.append(i); tau.append(t); src.append("CYCLE"); order.append(j)
    if lists and tabs.rows.get(lists):
        lt = tabs.data[lists]
        by: dict[int, list] = {}
        for p, pos, v, ok in zip(lt["_parent"], lt["_pos"], lt["value"], lt["value?"]):
            if ok and v > 0 and v < horizon * (1.0 - rs.EPS):
                by.setdefault(int(p), []).append((float(v), int(pos)))
        for i in sorted(by):
            for t, pos in sorted(by[i]):
                par.append(i); tau.append(t); src.append("LIST"); order.append(pos)
    put_table(tabs, name, {"_parent": np.array(par, dtype=float), "tau": np.array(tau, dtype=float),
                           "cell": np.array([rs.event_year(t) - 1 for t in tau], dtype=float),
                           "src": objects(src), "ord": np.array(order, dtype=float)})


def add_prefixed(tabs, other, prefix: str, names, placeholders: dict | None = None) -> None:
    """Copy tables of another scenario under a prefix (second operand of a comparison). Without the other
    scenario, empty placeholders with the given row counts are added so that every reference resolves."""
    for name in names:
        if other is not None:
            tabs.data[prefix + name], tabs.rows[prefix + name] = other.data[name], other.rows[name]
        else:
            tabs.data[prefix + name], tabs.rows[prefix + name] = {}, (placeholders or {}).get(name, 0)
