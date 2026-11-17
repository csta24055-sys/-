"""Probe of the missing-value and mask semantics of the unchanged research engine msp.py (read-only import).

Toy tables only; fictional numbers. The engine is imported read-only and is not modified.
Run from WLC_THEORY_RESEARCH_BASE/:
    WLCSTUDIO_OFFLINE=1 python3 -B tools/probe_msp_semantics.py ../10_TRANSFORM_STUDY/research_code > data/msp_semantics_probe.json
Used by 03_数式と記号の完全仕様.md section 4.4 and 04_マスク積和の理論.md section 2.5.
"""
import json
import math
import random
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, sys.argv[1])

import numpy as np  # noqa: E402
from tstudy import msp  # noqa: E402


class Tabs:
    def __init__(self, tables):
        self.rows = {}
        self.data = {}
        for name, cols in tables.items():
            n = len(next(iter(cols.values())))
            self.rows[name] = n
            d = {}
            for c, vals in cols.items():
                if any(isinstance(v, str) for v in vals):
                    arr = np.array(vals, dtype=object)
                    pres = np.array([v is not None for v in vals])
                else:
                    arr = np.array([math.nan if v is None else float(v) for v in vals])
                    pres = np.array([v is not None for v in vals])
                d[c] = arr
                d[c + "?"] = pres
            self.data[name] = d


def run(tables, steps):
    spec = {"units": [{"id": "U", "steps": steps, "outputs": {}}]}
    prog = msp.Program(spec)
    eng = msp.Engine(Tabs(tables))
    eng.run(prog)
    return eng


def col(eng, table, name):
    c = eng.cols[(table, name)]
    return [None if not ok else float(v) for v, ok in zip(c.v, c.m)]


out = {}

# 1-3: masks and missing values
tables = {"R": {"x": [1.0, None, 0.0, 2.0], "c": [1, 0, 1, 0]}}
steps = [
    {"op": "sp", "table": "R", "out": "masked", "group": "none",
     "terms": [[{"pred": "eq", "a": "c", "b": {"const": 1}}, "x"]]},
    {"op": "sp", "table": "R", "out": "inv_masked", "group": "none",
     "terms": [[{"pred": "range", "a": "x", "lo": 0, "hi": "inf", "lo_open": True, "hi_open": True},
                {"fn": "inv", "a": "x"}]]},
    {"op": "sp", "table": "R", "out": "inv_active", "group": "none",
     "terms": [[{"fn": "inv", "a": "x"}]]},
    {"op": "sp", "table": "R", "out": "tot_masked", "group": "total",
     "terms": [[{"pred": "eq", "a": "c", "b": {"const": 0}, "not": True}, "x"]]},
    {"op": "sp", "table": "R", "out": "tot_all", "group": "total", "terms": [["x"]]},
    {"op": "sp", "table": "R", "out": "pres", "group": "none",
     "terms": [[{"pred": "present", "a": "x"}]]},
    {"op": "sp", "table": "R", "out": "notpres", "group": "none",
     "terms": [[{"pred": "present", "a": "x", "not": True}]]},
]
e = run(tables, steps)
out["masked_row"] = col(e, "R", "masked")            # expected [1, 0, 0, 0]   (row 1: x missing but c=0 -> exactly 0)
out["inv_masked"] = col(e, "R", "inv_masked")        # expected [1, 0, 0, 0.5] (x=0 and x missing masked out)
out["inv_active"] = col(e, "R", "inv_active")        # expected [1, None, None, 0.5] (1/0 not finite -> missing)
out["tot_masked"] = col(e, msp.SCALARS, "tot_masked")  # rows with c=1 only: 1 + 0 = 1
out["tot_all"] = col(e, msp.SCALARS, "tot_all")      # a missing row makes the group missing -> [None]
out["present"] = col(e, "R", "pres")                 # [1, 0, 1, 1]
out["not_present"] = col(e, "R", "notpres")          # [0, 1, 0, 0]

# 4: match returns the FIRST row with equal keys
tables = {"A": {"k": [2, 3, 9]}, "B": {"k": [3, 2, 2, 3], "v": [10, 20, 30, 40]}}
steps = [
    {"op": "match", "table": "A", "out": "r", "keys": ["k"], "into": "B", "on": ["k"]},
    {"op": "sp", "table": "A", "out": "val", "group": "none",
     "terms": [[{"pred": "present", "a": "r"}, {"col": "v", "via": "r"}]]},
]
e = run(tables, steps)
out["match_ref"] = col(e, "A", "r")      # [1, 0, None]
out["match_val"] = col(e, "A", "val")    # [20, 10, 0]  (no match: masked by present -> exactly 0)

# 5: if/elif/else as exclusive masks, compared with direct evaluation on random inputs
random.seed(20261117)
xs = [random.uniform(-2, 2) for _ in range(2000)]
ys = [random.uniform(-2, 2) for _ in range(2000)]
tables = {"R": {"x": xs, "y": ys}}
A = {"pred": "le", "a": "x", "b": {"const": 0.0}}          # A: x <= 0
B = {"pred": "le", "a": "y", "b": "x"}                      # B: y <= x
nA, nB = dict(A, **{"not": True}), dict(B, **{"not": True})
steps = [{"op": "sp", "table": "R", "out": "z", "group": "none",
          "terms": [[A, "y"], [nA, B, "x", "y"], [nA, nB, {"fn": "one_minus", "a": "x"}]]}]
e = run(tables, steps)
z = col(e, "R", "z")
direct = [(y if x <= 0 else (x * y if y <= x else 1 - x)) for x, y in zip(xs, ys)]
out["if_elif_rows"] = len(xs)
out["if_elif_bit_identical"] = sum(1 for a, b in zip(z, direct) if a == b)

# 6: a string column inside a product is refused
tables = {"R": {"s": ["a", "b"], "x": [1, 2]}}
try:
    run(tables, [{"op": "sp", "table": "R", "out": "bad", "group": "none", "terms": [["s", "x"]]}])
    out["string_in_product"] = "accepted"
except msp.SpecError as ex:
    out["string_in_product"] = "SpecError: " + str(ex)

print(json.dumps(out, ensure_ascii=False, indent=1))
