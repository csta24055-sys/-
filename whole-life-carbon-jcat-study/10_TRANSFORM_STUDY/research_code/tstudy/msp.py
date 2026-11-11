"""Masked sum-product engine of candidate TC-B-01 (route B). Research code, fictional data only.

ONE FORM
    out[g] = sum over rows x of a table  sum over terms t  prod_k phi_{t,k}(x)        grouped by g

Every evaluation unit is DATA: a list of steps (dictionaries, JSON-serialisable; no lambdas, no eval,
no Python expressions inside strings) plus a list of read-outs. The engine has no branch on a unit id.
Nothing in this module knows a unit; the specifications live in ``specs/``.

VOCABULARY (fixed; the engine counts every use per unit, see ``Engine.usage`` and ``static_usage``)

Step kinds
  ``sp``     the masked sum-product above. ``table`` names the index set (rows x), ``terms`` is a list of
             factor lists, ``group`` is the grouping g, ``out`` the name of the result column.
             Every ``sp`` step ends in ONE function, ``Engine.core`` (scatter-add of the row products).
  ``match``  first match of a keyed look-up: ref[x] = min{ y in table ``into`` : on(y) == keys(x) }.
             The result is a REFERENCE column (row position in ``into``, missing when no row matches).
             This is the only place that needs an order (min over row positions, i.e. the (min, .)
             semiring of DESIGN.md section 2); the engine counts how often more than one row matched.
  ``use``    not a computation: instantiates a named template (a list of steps with ``$parameter`` and
             ``@local-name`` placeholders) by textual substitution before anything is evaluated.

Factors phi of an ``sp`` term
  (1) column     an OPERAND (below) used as a number. A constant ``{"const": c}`` is the degenerate case.
  (2) predicate  0/1 factor ``{"pred": kind, "a": operand, ...}``, optional ``"not": true`` (1 - value):
        ``present``  the value is not missing
        ``range``    lo <= a <= hi with ``lo_open`` / ``hi_open``; bounds are numbers or "inf" / "-inf"
                     (finite and >= 0 is lo 0, hi "inf", hi_open; a ratio is lo 0, hi 1)
        ``eq``       a == b, b an operand: equal to a constant, or equal keys of two columns
        ``le``       a <= b, b an operand (numbers, or strings compared as text, e.g. ISO dates)
      A predicate on a missing value is 0 (``present`` included); ``not`` turns that into 1.
  (3) function   ``{"fn": name, "a": operand}``, an elementwise rational function of ONE column:
        ``inv`` 1/x, ``one_minus`` 1-x, ``inv_one_minus`` 1/(1-x), ``ratio_one_minus`` x/(1-x)

Operands (how a factor addresses a column)
  ``"name"``                         a column of the step's table (input column or an earlier result);
                                     ``"_row"`` is the row position, ``"_parent"`` the parent row of a child table
  ``{"col": name, "via": ref}``      gather through a reference column: the column ``name`` of the table the
                                     reference points into, taken at the referenced row (join through a key)
  ``{"col": name, "of": table}``     the single value of a one-row table (scenario scalar), same for all rows
  ``{"const": value}``               a constant (number or string)

Grouping
  ``"none"``         per row (the result is a new column of the table)
  ``"total"``        one number (stored in the one-row table ``S``)
  ``{"by": ref}``    scatter-add by a reference column into the rows of the table it points into

Read-outs (post-processing, no arithmetic): ``scalar`` (as float / int / bool), ``rows`` (list per row, None
where the ``where`` column is 0), ``enum`` (label of the indicator column that is 1), ``dict`` (key column ->
value for rows whose ``where`` column is not 0), ``record`` (nested dictionary), ``const`` (literal).

MISSING VALUES
  Every column carries a validity mask. None is never treated as zero:
  * a term whose predicates are not all 1 contributes exactly 0 (that is the mask of the form);
  * a term whose predicates are all 1 but which contains a missing column value (or a function value that
    is not finite) is MISSING; a row with a missing term is missing; a group that contains a missing row
    is missing; a row with a non-zero or missing product whose group reference is missing makes every
    group missing. Read-outs return None for a missing result.
  A column name that does not occur in a scenario (the flattening creates columns only for fields that
  occur) is an all-missing column; such names are collected in ``absent_columns`` so that a check can tell
  a field that is unused in one scenario from a misspelt name.

PRE-PROCESSING done here (generic, no unit knowledge): strings are replaced by integer codes (interned per
scenario) so that a string column can be gathered and compared like a number; ``le`` on strings uses the
rank of the code in the sorted list of strings.

TEST-ONLY FAULT SWITCHES (``fault`` argument; never set in a measurement)
  ``{"scale": 1.0001, "units": None | [unit ids]}``  multiply every result of ``Engine.core`` (optionally
        only in the steps of the listed units) by ``scale``;
  ``{"match": "last", "units": ...}``                ``match`` returns the last matching row instead of the first.
"""
from __future__ import annotations

import copy
import math
from typing import Any

import numpy as np

SCALARS = "S"          # one-row table that receives the results of group "total"
EMPTY = "_none"        # the empty table (for a look-up that has no row-specific table)
SHARED = "(shared)"    # unit tag of steps that do not belong to one unit


class SpecError(ValueError):
    """The specification asks for something outside the vocabulary."""


def _f_inv(x):
    return 1.0 / x


def _f_one_minus(x):
    return 1.0 - x


def _f_inv_one_minus(x):
    return 1.0 / (1.0 - x)


def _f_ratio_one_minus(x):
    return x / (1.0 - x)


FUNCTIONS = {"inv": _f_inv, "one_minus": _f_one_minus, "inv_one_minus": _f_inv_one_minus,
             "ratio_one_minus": _f_ratio_one_minus}
PREDICATES = ("present", "range", "eq", "le")
STEP_KINDS = ("sp", "match")
READ_KINDS = ("scalar", "rows", "enum", "dict", "record", "const")


class Col:
    """A column: values, validity mask, kind ("num", "cat" string codes, "ref" row reference, "void" all missing)."""

    __slots__ = ("v", "m", "kind", "target")

    def __init__(self, v, m, kind="num", target=None):
        self.v, self.m, self.kind, self.target = v, m, kind, target


# ---------------------------------------------------------------------------------------------
# Specification handling (pure data manipulation)
# ---------------------------------------------------------------------------------------------

def _subst(x, env: dict, prefix: str):
    if isinstance(x, str):
        if x.startswith("$"):
            if x[1:] not in env:
                raise SpecError(f"template parameter {x} is not bound")
            return copy.deepcopy(env[x[1:]])
        if x.startswith("@"):
            return f"{prefix}.{x[1:]}"
        return x
    if isinstance(x, list):
        return [_subst(i, env, prefix) for i in x]
    if isinstance(x, dict):
        return {k: _subst(v, env, prefix) for k, v in x.items()}
    return x


class Program:
    """A specification with its templates expanded: flat list of steps (each tagged with its unit)."""

    def __init__(self, spec: dict):
        self.spec = spec
        self.steps: list[dict] = []
        self.units: list[str] = [u["id"] for u in spec["units"]]
        self.outputs: dict[str, dict] = {u["id"]: u["outputs"] for u in spec["units"]}
        templates = spec.get("templates", {})

        def emit(steps, unit, via):
            for st in steps:
                if "use" in st:
                    if st["use"] not in templates:
                        raise SpecError(f"unknown template {st['use']}")
                    emit(_subst(templates[st["use"]], st["with"], st["as"]), unit, via + [st["use"]])
                else:
                    if st.get("op") not in STEP_KINDS:
                        raise SpecError(f"unknown step kind {st.get('op')!r}")
                    s = dict(st)
                    s["unit"] = unit
                    s["template"] = "/".join(via) if via else None
                    self.steps.append(s)

        emit(spec.get("shared", []), SHARED, [])
        for u in spec["units"]:
            emit(u["steps"], u["id"], [])
        seen = set()
        for s in self.steps:
            if s["out"] in seen:
                raise SpecError(f"result name {s['out']} is defined twice")
            seen.add(s["out"])


def _count(d: dict, key: str, n: int = 1) -> None:
    d[key] = d.get(key, 0) + n


def _operand_kind(op) -> str:
    if isinstance(op, str):
        return "operand:own"
    if "const" in op:
        return "operand:const"
    if "via" in op:
        return "operand:via"
    if "of" in op:
        return "operand:of"
    raise SpecError(f"bad operand {op!r}")


def static_usage(program: Program) -> dict[str, dict[str, int]]:
    """How often each vocabulary element occurs in the expanded specification, per unit (data-independent)."""
    out: dict[str, dict[str, int]] = {}
    for st in program.steps:
        u = out.setdefault(st["unit"], {})
        _count(u, "step:" + st["op"])
        if st.get("template"):
            _count(u, "steps_from_template:" + st["template"])
        if st["op"] == "match":
            for k in st["keys"]:
                _count(u, _operand_kind(k))
            _count(u, "match_key_parts", len(st["keys"]))
            continue
        g = st.get("group", "none")
        _count(u, "group:" + (g if isinstance(g, str) else "by"))
        _count(u, "terms", len(st["terms"]))
        for term in st["terms"]:
            for f in term:
                if "pred" in f:
                    _count(u, "pred:" + f["pred"])
                    if f.get("not"):
                        _count(u, "pred.not")
                    _count(u, _operand_kind(f["a"]))
                    if "b" in f:
                        _count(u, _operand_kind(f["b"]))
                elif "fn" in f:
                    _count(u, "fn:" + f["fn"])
                    _count(u, _operand_kind(f["a"]))
                elif isinstance(f, dict) and "const" in f:
                    _count(u, "factor:const")
                else:
                    _count(u, "factor:column")
                    _count(u, _operand_kind(f))
    for uid, outs in program.outputs.items():
        u = out.setdefault(uid, {})

        def walk(ro):
            _count(u, "read:" + ro["read"])
            if ro["read"] == "record":
                for sub in ro["fields"].values():
                    walk(sub)

        for ro in outs.values():
            walk(ro)
    return out


# ---------------------------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------------------------

def _num(x) -> float:
    if x == "inf":
        return math.inf
    if x == "-inf":
        return -math.inf
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        raise SpecError(f"bad bound {x!r}")
    return float(x)


class Engine:
    def __init__(self, tabs, fault: dict | None = None):
        self.tabs = tabs
        self.cols: dict[tuple[str, str], Col] = {}
        self.sym: dict[str, int] = {}
        self.syms: list[str] = []
        self._rank = None
        self.fault = fault or {}
        self._fault_units = None if self.fault.get("units") is None else set(self.fault["units"])
        self.unit = SHARED
        self.usage: dict[str, dict[str, int]] = {}
        self.absent_columns: set[tuple[str, str]] = set()
        self.absent_tables: set[str] = set()
        self._names = sorted(tabs.rows, key=len, reverse=True)

    # ---- tables and columns -------------------------------------------------------------
    def nrows(self, table: str) -> int:
        if table == SCALARS:
            return 1
        if table == EMPTY:
            return 0
        n = self.tabs.rows.get(table)
        if n is None:
            self.absent_tables.add(table)
            return 0
        return n

    def parent(self, table: str) -> str | None:
        """The table a child table hangs under: the longest proper dotted prefix that is a table."""
        for name in self._names:
            if len(name) < len(table) and table.startswith(name + "."):
                return name
        return None

    def code(self, s: str) -> int:
        c = self.sym.get(s)
        if c is None:
            c = self.sym[s] = len(self.syms)
            self.syms.append(s)
            self._rank = None
        return c

    def ranks(self) -> np.ndarray:
        if self._rank is None:
            order = sorted(range(len(self.syms)), key=self.syms.__getitem__)
            rank = np.empty(len(self.syms) + 1, dtype=float)
            rank[order] = np.arange(len(order), dtype=float)
            rank[-1] = math.nan
            self._rank = rank
        return self._rank

    def col(self, table: str, name: str) -> Col:
        key = (table, name)
        c = self.cols.get(key)
        if c is not None:
            return c
        n = self.nrows(table)
        data = self.tabs.data.get(table, {}) if table not in (SCALARS, EMPTY) else {}
        if name == "_row":
            c = Col(np.arange(n, dtype=float), np.ones(n, dtype=bool), "ref", table)
        elif name not in data:
            if n:
                self.absent_columns.add(key)
            c = Col(np.full(n, math.nan), np.zeros(n, dtype=bool), "void")
        else:
            arr, present = data[name], data[name + "?"]
            if arr.dtype == object:
                codes = np.full(n, math.nan)
                kind = "void"
                for i in np.nonzero(present)[0]:
                    v = arr[i]
                    if not isinstance(v, str):
                        raise SpecError(f"column {table}.{name} holds a {type(v).__name__}; only numbers and strings")
                    codes[i] = self.code(v)
                    kind = "cat"
                c = Col(codes, present.copy(), kind)
            else:
                c = Col(arr.astype(float), present.copy(), "num")
        if name == "_parent":
            c.kind, c.target = "ref", self.parent(table)
        self.cols[key] = c
        return c

    def operand(self, table: str, op) -> Col:
        if isinstance(op, str):
            return self.col(table, op)
        if not isinstance(op, dict):
            raise SpecError(f"bad operand {op!r}")
        n = self.nrows(table)
        if "const" in op:
            v = op["const"]
            if isinstance(v, str):
                return Col(np.full(n, float(self.code(v))), np.ones(n, dtype=bool), "cat")
            return Col(np.full(n, float(v)), np.ones(n, dtype=bool), "num")
        name = op["col"]
        if "via" in op:
            ref = self.col(table, op["via"])
            if ref.kind == "void" or ref.target is None:
                if ref.kind not in ("void", "ref"):
                    raise SpecError(f"{table}.{op['via']} is not a reference column")
                return Col(np.full(n, math.nan), np.zeros(n, dtype=bool), "void")
            if ref.kind != "ref":
                raise SpecError(f"{table}.{op['via']} is not a reference column")
            src = self.col(ref.target, name)
            if src.v.size == 0:
                return Col(np.full(n, math.nan), np.zeros(n, dtype=bool), src.kind, src.target)
            idx = np.where(ref.m, ref.v, 0.0).astype(np.intp)
            return Col(np.where(ref.m, src.v[idx], math.nan), ref.m & src.m[idx], src.kind, src.target)
        if "of" in op:
            if self.nrows(op["of"]) != 1:
                raise SpecError(f"table {op['of']} is not a one-row table")
            src = self.col(op["of"], name)
            return Col(np.full(n, src.v[0]), np.full(n, bool(src.m[0])), src.kind, src.target)
        raise SpecError(f"bad operand {op!r}")

    # ---- factors -------------------------------------------------------------------------
    @staticmethod
    def _comparable(a: Col, b: Col, what) -> None:
        ka = "num" if a.kind == "ref" else a.kind
        kb = "num" if b.kind == "ref" else b.kind
        if "void" not in (ka, kb) and ka != kb:
            raise SpecError(f"comparison of a number with a string in {what!r}")

    def pred(self, table: str, f: dict) -> np.ndarray:
        kind = f["pred"]
        a = self.operand(table, f["a"])
        if kind == "present":
            r = a.m.copy()
        elif kind == "range":
            if a.kind == "cat":
                raise SpecError(f"range of a string column in {f!r}")
            lo, hi = _num(f.get("lo", "-inf")), _num(f.get("hi", "inf"))
            with np.errstate(invalid="ignore"):
                r = a.m & ((a.v > lo) if f.get("lo_open") else (a.v >= lo)) & ((a.v < hi) if f.get("hi_open") else (a.v <= hi))
        elif kind == "eq":
            b = self.operand(table, f["b"])
            self._comparable(a, b, f)
            with np.errstate(invalid="ignore"):
                r = a.m & b.m & (a.v == b.v)
        elif kind == "le":
            b = self.operand(table, f["b"])
            self._comparable(a, b, f)
            av, bv = a.v, b.v
            if "cat" in (a.kind, b.kind):
                rank = self.ranks()
                av = rank[np.where(a.m, av, -1.0).astype(np.intp)]
                bv = rank[np.where(b.m, bv, -1.0).astype(np.intp)]
            with np.errstate(invalid="ignore"):
                r = a.m & b.m & (av <= bv)
        else:
            raise SpecError(f"unknown predicate {kind!r}")
        if f.get("not"):
            r = ~r
        return r

    # ---- the two primitives -------------------------------------------------------------
    def _fault_here(self) -> bool:
        return self._fault_units is None or self.unit in self._fault_units

    def core(self, values: np.ndarray, index: np.ndarray, n_out: int) -> np.ndarray:
        """THE sum-product reduction: out[g] = sum of the row products whose group is g."""
        if n_out == 0:
            return np.zeros(0)
        out = np.bincount(index, weights=values, minlength=n_out)
        scale = self.fault.get("scale")
        if scale is not None and self._fault_here():      # test-only fault injection
            out = out * scale
        return out

    def run_sp(self, st: dict) -> None:
        table = st["table"]
        n = self.nrows(table)
        use = self.usage.setdefault(self.unit, {})
        acc = None
        acc_ok = np.ones(n, dtype=bool)
        kind, target = "num", None
        terms = st["terms"]
        if not terms:
            raise SpecError(f"step {st['out']} has no term")
        for term in terms:
            active = np.ones(n, dtype=bool)
            val = np.ones(n)
            ok = np.ones(n, dtype=bool)
            n_plain = 0
            for f in term:
                if not isinstance(f, (dict, str)):
                    raise SpecError(f"bad factor {f!r}")
                if isinstance(f, dict) and "pred" in f:
                    active &= self.pred(table, f)
                elif isinstance(f, dict) and "fn" in f:
                    if f["fn"] not in FUNCTIONS:
                        raise SpecError(f"unknown function {f['fn']!r}")
                    x = self.operand(table, f["a"])
                    if x.kind == "cat":
                        raise SpecError(f"function of a string column in {f!r}")
                    with np.errstate(all="ignore"):
                        y = FUNCTIONS[f["fn"]](x.v)
                        val = val * y
                    ok &= x.m & np.isfinite(y)
                    n_plain += 1
                else:
                    c = self.operand(table, f)
                    if c.kind in ("cat", "ref"):
                        # a string or a reference can only be gathered, never multiplied
                        if len(terms) != 1 or n_plain or sum(1 for g in term if not (isinstance(g, dict) and "pred" in g)) != 1:
                            raise SpecError(f"step {st['out']}: a string or reference column inside a product")
                        kind, target = c.kind, c.target
                    with np.errstate(all="ignore"):
                        val = val * c.v
                    ok &= c.m
                    n_plain += 1
            good = active & ok
            tv = np.where(good, val, 0.0)
            acc = tv if acc is None else acc + tv
            acc_ok &= ~active | ok
        g = st.get("group", "none")
        lost = False
        if g == "none":
            index, n_out, out_table = np.arange(n, dtype=np.intp), n, table
        elif g == "total":
            index, n_out, out_table = np.zeros(n, dtype=np.intp), 1, SCALARS
        elif isinstance(g, dict) and "by" in g:
            ref = self.col(table, g["by"])
            if ref.kind != "ref" or ref.target is None:
                raise SpecError(f"step {st['out']}: group column {g['by']} is not a reference column")
            out_table = ref.target
            n_out = self.nrows(out_table)
            keep = ref.m
            lost = bool(np.any(~keep & ((acc != 0.0) | ~acc_ok)))
            index = ref.v[keep].astype(np.intp)
            acc, acc_ok = acc[keep], acc_ok[keep]
        else:
            raise SpecError(f"unknown grouping {g!r}")
        out = self.core(acc, index, n_out)
        _count(use, "core_calls")
        _count(use, "core_products", int(n) * len(terms))
        if n_out:
            bad = np.bincount(index, weights=(~acc_ok).astype(float), minlength=n_out) > 0
        else:
            bad = np.zeros(0, dtype=bool)
        if lost:
            bad[:] = True
        self.cols[(out_table, st["out"])] = Col(np.where(bad, math.nan, out), ~bad, kind, target)

    def run_match(self, st: dict) -> None:
        table, into = st["table"], st["into"]
        na, nb = self.nrows(table), self.nrows(into)
        use = self.usage.setdefault(self.unit, {})
        if len(st["keys"]) != len(st["on"]) or not st["keys"]:
            raise SpecError(f"step {st['out']}: keys and on must have the same positive length")
        a_parts = [self.operand(table, k) for k in st["keys"]]
        b_parts = [self.col(into, k) for k in st["on"]]
        a_ok = np.ones(na, dtype=bool)
        b_ok = np.ones(nb, dtype=bool)
        for a, b in zip(a_parts, b_parts):
            self._comparable(a, b, st)
            a_ok &= a.m & ~np.isnan(a.v)
            b_ok &= b.m & ~np.isnan(b.v)
        ident = np.zeros(na + nb, dtype=np.int64)
        for a, b in zip(a_parts, b_parts):
            both = np.concatenate([np.where(a_ok, a.v, 0.0), np.where(b_ok, b.v, 0.0)])
            if both.size:
                uniq, inv = np.unique(both, return_inverse=True)
                ident = ident * len(uniq) + inv.reshape(-1)
        if ident.size:
            uniq, ident = np.unique(ident, return_inverse=True)
            ident = ident.reshape(-1)
            n_keys = len(uniq)
        else:
            n_keys = 0
        ida, idb = ident[:na], ident[na:]
        rows_b = np.nonzero(b_ok)[0]
        pos = np.full(n_keys, -1, dtype=np.intp)
        if self.fault.get("match") == "last" and self._fault_here():   # test-only fault injection
            pos[idb[rows_b]] = rows_b
        else:
            pos[idb[rows_b][::-1]] = rows_b[::-1]                      # first row in table order wins
        hit = pos[ida] if na else np.zeros(0, dtype=np.intp)
        found = a_ok & (hit >= 0)
        if na and rows_b.size:
            many = np.bincount(idb[rows_b], minlength=n_keys)[ida] > 1
            _count(use, "match_order_decided", int(np.sum(found & many)))
        _count(use, "match_probes", int(na))
        self.cols[(table, st["out"])] = Col(np.where(found, hit, 0).astype(float), found, "ref", into)

    def run(self, program: Program) -> "Engine":
        for st in program.steps:
            self.unit = st["unit"]
            if st["op"] == "sp":
                self.run_sp(st)
            else:
                self.run_match(st)
        self.unit = SHARED
        return self

    # ---- read-outs (post-processing) ----------------------------------------------------
    @staticmethod
    def _cast(v: float, ok: bool, as_: str):
        if not ok:
            return None
        v = float(v)
        if as_ == "float":
            return v
        if as_ == "int":
            return int(v) if v == math.floor(v) and not math.isinf(v) else v     # strict: no rounding
        if as_ == "bool":
            return bool(v) if v in (0.0, 1.0) else v
        raise SpecError(f"unknown read-out type {as_!r}")

    def read(self, ro: dict):
        k = ro["read"]
        if k == "const":
            return copy.deepcopy(ro["value"])
        if k == "record":
            return {name: self.read(sub) for name, sub in ro["fields"].items()}
        if k == "scalar":
            table = ro.get("table", SCALARS)
            if self.nrows(table) != 1:
                raise SpecError(f"scalar read-out of table {table} that is not a one-row table")
            c = self.col(table, ro["col"])
            return self._cast(c.v[0], bool(c.m[0]), ro.get("as", "float"))
        if k == "rows":
            c = self.col(ro["table"], ro["col"])
            as_ = ro.get("as", "float")
            if "where" in ro:
                w = self.col(ro["table"], ro["where"])
                keep = w.m & (w.v != 0.0)
            else:
                keep = np.ones(len(c.v), dtype=bool)
            return [self._cast(v, bool(m and kp), as_) for v, m, kp in zip(c.v.tolist(), c.m.tolist(), keep.tolist())]
        if k == "enum":
            n = self.nrows(ro["table"])
            out: list[Any] = [None] * n
            for label, name in ro["cases"]:
                c = self.col(ro["table"], name)
                for i in np.nonzero(c.m & (c.v != 0.0))[0]:
                    v = float(c.v[i])
                    out[i] = label if (v == 1.0 and out[i] is None) else (out[i], label, v)   # strict: one indicator, exactly 1
            return out
        if k == "dict":
            key = self.col(ro["table"], ro["key"])
            c = self.col(ro["table"], ro["col"])
            w = self.col(ro["table"], ro["where"])
            out_d = {}
            for i in np.nonzero(w.m & (w.v != 0.0))[0]:
                name = self.syms[int(key.v[i])] if key.kind == "cat" else float(key.v[i])
                out_d[name] = self._cast(c.v[i], bool(c.m[i]), ro.get("as", "float"))
            return out_d
        raise SpecError(f"unknown read-out {k!r}")

    def results(self, program: Program, units=None) -> dict[str, dict[str, Any]]:
        return {uid: {key: self.read(ro) for key, ro in program.outputs[uid].items()}
                for uid in (units or program.units)}


def evaluate(program: Program, tabs, fault: dict | None = None) -> tuple[dict[str, dict[str, Any]], Engine]:
    """Run a specification on the tables of one scenario; returns (results per unit, engine with counters)."""
    eng = Engine(tabs, fault).run(program)
    return eng.results(program), eng
