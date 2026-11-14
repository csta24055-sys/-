"""Typed cell values of the five workbooks (read from the private scan; read-only).

Excel value model used everywhere in this study:
  None      blank cell
  float     number
  str       text
  bool      logical
  Err(code) error value
"""
from __future__ import annotations

import collections
import math
import os
import re
import sqlite3
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "jcat_tools"))
import fx  # noqa: E402

BOOK = {1: "SIM", 2: "STD", 3: "CLS", 4: "SUM", 5: "DET"}
ERR_CODES = {"#NULL!": 1, "#DIV/0!": 2, "#VALUE!": 3, "#REF!": 4, "#NAME?": 5, "#NUM!": 6, "#N/A": 7, "#GETTING_DATA": 8}
ERR_NAMES = {v: k for k, v in ERR_CODES.items()}
KEY_SHIFT = 16384          # key of a cell = row * KEY_SHIFT + col


class Err:
    __slots__ = ("code",)

    def __init__(self, code: int):
        self.code = code

    def __eq__(self, other):
        return isinstance(other, Err) and other.code == self.code

    def __hash__(self):
        return hash(("err", self.code))

    def __repr__(self):
        return ERR_NAMES.get(self.code, "#ERR%d" % self.code)


def err(name: str) -> Err:
    return Err(ERR_CODES[name])


class Sheet:
    """Cells of one sheet: constants and the cached results of formula cells."""

    def __init__(self, book: str, name: str, sid: int):
        self.book, self.name, self.sid = book, name, sid
        self.values: dict[int, object] = {}         # key -> value (formula cells: cached result)
        self.formula: dict[int, str] = {}           # key -> formula text (formula cells only)
        self.max_row = self.max_col = 0

    def get(self, r: int, c: int):
        return self.values.get(r * KEY_SHIFT + c)


class Store:
    def __init__(self, scan_path: str, books=("SIM", "STD", "CLS", "SUM", "DET")):
        db = sqlite3.connect(scan_path)
        self.sheets: dict[tuple[str, str], Sheet] = {}
        self.order: list[tuple[str, str]] = []
        self.names: dict[str, dict[str, str]] = collections.defaultdict(dict)     # book -> NAME (upper) -> refers_to
        self.local_names: dict[tuple[str, str], dict[str, str]] = collections.defaultdict(dict)
        files = {fid: BOOK[fid] for fid in BOOK}
        sheet_by_idx = {}
        for sid, fid, idx, name in db.execute("SELECT id, file_id, idx, name FROM sheets ORDER BY file_id, idx"):
            book = files[fid]
            if book not in books:
                continue
            sh = Sheet(book, name, sid)
            self.sheets[(book, name)] = sh
            self.order.append((book, name))
            sheet_by_idx[(fid, idx - 1)] = name
        by_sid = {sh.sid: sh for sh in self.sheets.values()}
        ftype = {}
        for sid, r, c, t in db.execute("SELECT sheet_id, row, col, t FROM ftype"):
            if sid in by_sid:
                ftype[(sid, r, c)] = t
        for sid, r, c, t, v, f in db.execute("SELECT sheet_id, row, col, t, v, f FROM cells"):
            sh = by_sid.get(sid)
            if sh is None:
                continue
            key = r * KEY_SHIFT + c
            if t == "f":
                ft = ftype.get((sid, r, c), "n")
                val = self._typed(ft, v)
                if f is not None:
                    sh.formula[key] = f
                else:
                    sh.formula[key] = None          # shared formula child: text from the master (see Book.formula_text)
            else:
                if t == "z":
                    continue
                val = self._typed(t, v)
            sh.values[key] = val
            sh.max_row = max(sh.max_row, r)
            sh.max_col = max(sh.max_col, c)
        for fid, name, local, hidden, ref in db.execute("SELECT file_id, name, local_sheet, hidden, refers_to FROM names"):
            book = files.get(fid)
            if book not in books or ref is None:
                continue
            if local is not None and local != "":
                self.local_names[(book, sheet_by_idx.get((fid, int(local)), ""))][name.upper()] = ref
            else:
                self.names[book][name.upper()] = ref

    @staticmethod
    def _typed(t, v):
        if t == "n":
            return float(v) if v not in (None, "") else None
        if t in ("s", "str", "inlineStr"):
            return v if v is not None else ""
        if t == "b":
            return v in ("1", "true", "TRUE")
        if t == "e":
            return Err(ERR_CODES.get(v, 0))
        return None

    def sheet(self, book: str, name: str) -> Sheet | None:
        sh = self.sheets.get((book, name))
        if sh is None:                            # sheet names are case-insensitive in Excel
            for (b, n), s in self.sheets.items():
                if b == book and n.upper() == name.upper():
                    return s
        return sh

    def resolve_name(self, book: str, sheet: str, name: str):
        ref = self.local_names.get((book, sheet), {}).get(name.upper()) or self.names.get(book, {}).get(name.upper())
        return ref


def to_float_text(s: str):
    """Excel's coercion of a text to a number (the part that matters for these workbooks), or None."""
    t = s.strip()
    if not t:
        return None
    t = t.translate(str.maketrans("０１２３４５６７８９．，－＋％", "0123456789.,-+%"))
    pct = t.endswith("%")
    if pct:
        t = t[:-1].strip()
    if re.fullmatch(r"[+-]?(\d{1,3}(,\d{3})+|\d+)(\.\d*)?([eE][+-]?\d+)?|[+-]?\.\d+([eE][+-]?\d+)?", t):
        try:
            x = float(t.replace(",", ""))
        except ValueError:
            return None
        return x / 100.0 if pct else x
    return None
