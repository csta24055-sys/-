"""EXP-A1 (route A, candidate TC-A-01): recount of the saved unified model of the earlier study.

The saved model (``09_APPROX_STUDY/research_code/fastcalc``: ``engine.aggregate`` / ``engine.finish``
and ``closed_forms``) is measured here as a CANDIDATE. It is imported read-only and never edited;
faults are injected in this process only (monkeypatching, or a copy of the engine source that is
patched in memory and executed as a separate module object).

Parts
  A  Count of transformation kinds under RESEARCH_PROTOCOL.md section 5. The inventory of procedures
     (``LINE_MAP``) is a READING of the frozen code by the author of this script: every code line of
     the two files is assigned to a generic operator, a line builder, a unit-specific procedure, a
     per-row / per-year output procedure, a read-out or infrastructure. The script only checks that
     the map covers the files and counts lines; it cannot check the reading itself.
  B  Membership by fault injection: each shared function / shared table is broken, and for each of
     the 70 units it is recorded whether a public output changes (benchmark S and six scenarios of
     the design set with different options).
  C  Exactness: full outputs of all 70 units against the frozen reference on the design set, the
     evaluation set and the edge set (valid domain only), relative 1e-9, no absolute floor,
     zero-reference pairs counted separately. T sweep: ONE aggregate, ``finish`` at
     ``scenarios.SWEEP_PERIODS``, against fresh reference runs.
  D  Load: executed bytecode instructions and run time of reference vs unified model on benchmark
     S and M (same machine, same interpreter; a reference value only), and the split of the unified
     model into the part that does not depend on the study period (aggregate) and the part that is
     repeated for every period (finish).

Evidence level N (numerical, fictional data) for B, C and D; part A is a code reading. Checked by
the implementer only. Independent concept model; says nothing about real buildings or other tools.

Run from research_code:  python3 -B -m experiments.expA1_route_a_recount [--quick]
"""
from __future__ import annotations

import argparse
import ast
import contextlib
import copy
import io
import json
import math
import os
import platform
import re
import statistics
import sys
import time
import tokenize
import types

sys.dont_write_bytecode = True

from tstudy import baseline, scenarios

FASTCALC_TREE = "8f325fefd93cb5f3e2d61f34101f13d076e4a38b"   # git rev-parse HEAD:<frozen>/fastcalc
REL_TOL = 1e-9
HERE = os.path.dirname(os.path.abspath(__file__))
DEST = os.path.normpath(os.path.join(HERE, "..", "..", "03_ROUTES", "TC-A-01"))
FAULT_DESIGN_INDEX = (2, 4, 12, 25, 34, 55)   # six scenarios of design_set(60, "M") with different options
SWEEP_DESIGN_N = 24

DECLARED_OPERATORS = {   # operators (tags of part A) behind each declared model of 03_MODELS/models.json
    "K1": ("ROWTABLE", "STAGE"), "K2": ("COUNT", "EXPLICIT", "SKIP"), "K3": ("ANNUAL", "MOMENT", "SAME"),
    "K4": ("REFRIG",), "K5": ("PICK",), "K6": ("WITHIN",), "K7": ("RESOLVE", "RECIPE"),
}
HELPER_TAGS = ("TIME", "PRED")   # shared one-line rules, restated identically in the reference

# --------------------------------------------------------------------------------------------- part A
# start end kind procedure [units]   (frozen line numbers of fastcalc/engine.py, tree FASTCALC_TREE)
#   generic  one code path that serves several units; the units differ by data only
#   builder  pre-processing that builds the lines of a table with a formula / guard written for the unit
#   unit     calculation code that exists for the listed unit(s) only
#   spec     data-only invocation of a generic operator
#   detail   per-row / per-year outputs (full output mode only)
#   readout  result assembly (units found by the key at the start of the line when none is given)
#   infra    imports, constants, set-up, bookkeeping
ENGINE_MAP = """
1 53 infra -
54 61 generic PRED
62 66 generic WITHIN
67 71 generic ANNUAL
72 75 generic SAME
76 109 infra -
110 113 generic ROWTABLE
114 126 infra -
127 191 generic RESOLVE
192 202 unit U-SYS-03 SYS-03
203 223 unit U-SYS-01 SYS-01
224 245 infra -
246 250 unit U-SYS-01 SYS-01
251 261 unit U-A13-05 A13-05
262 267 unit U-FACTOR-CHOICE X-15
268 282 unit U-FACTOR-CHOICE A13-02,X-15
283 308 unit U-FACTOR-CHOICE X-15
309 323 builder LB-MFG A13-01,A13-03
324 332 builder LB-A13-04 A13-04
333 347 builder LB-A4-01 A4-01
348 353 builder LB-X-12 X-12
354 362 builder LB-A4-02 A4-02
363 372 builder LB-MAT-INSTALL B4-02
373 385 builder LB-C2-MAT C2-01
386 418 builder LB-ROUTES C3-01,C4-01,X-09
419 427 unit U-C-05 C-05
428 446 generic COUNT
447 451 builder LB-REPAIR-MAT B3-01,B3-02
452 456 builder LB-MASS-MAT X-10
457 466 builder LB-CLASS X-17
467 474 detail D-ROW-EMISSION A13-01,A13-03,A4-01,A4-02,C2-01,C3-01,C4-01
475 476 detail D-A13-05 A13-05
477 484 detail D-X-13 X-13
485 485 detail D-A13-02 A13-02
486 488 detail D-X-15 X-15
489 489 detail D-ROW-EMISSION A13-01
490 490 detail D-ROW-EMISSION A13-03
491 491 detail D-ROW-EMISSION A13-04
492 492 detail D-ROW-EMISSION A4-01
493 493 detail D-ROW-EMISSION A4-02
494 494 detail D-ROW-EMISSION X-12
495 495 detail D-ROW-EMISSION C2-01
496 496 detail D-ROW-EMISSION C3-01
497 497 detail D-ROW-EMISSION C4-01
498 498 detail D-B4-03 B4-03
499 499 detail D-B4-02-ITEM B4-02
500 504 infra -
505 509 unit U-SYS-01 SYS-01
510 523 builder LB-X-01 X-01
524 532 builder LB-EQ-DELIVERY-INSTALL B4-02
533 546 builder LB-X-14 X-14
547 552 builder LB-REPAIR-EQ B3-01,B3-02
553 568 generic COUNT
569 572 builder LB-MASS-EQ X-10
573 575 detail D-ROW-EMISSION X-01
576 576 detail D-ROW-EMISSION X-14
577 579 detail D-B4-02-ITEM B4-02,B4-01
580 583 unit U-B1-01 B1-01
584 585 infra -
586 589 unit U-SYS-01 SYS-01
590 594 unit U-B1-01 B1-01
595 595 generic REFRIG
596 607 builder LB-A5-01 A5-01
608 616 builder LB-A5-02 A5-02
617 624 builder LB-A5-03 A5-03
625 640 generic ANNUAL
641 652 builder LB-C1-01 C1-01
653 661 builder LB-C2-BUILDING C2-01
662 669 builder LB-STO-02 STO-02
670 687 builder LB-X-16 X-16
688 703 unit U-SYS-03 SYS-03
704 715 unit U-AREA-RESIDUAL SYS-04,QA-04
716 729 readout -
730 735 infra -
736 766 generic RECIPE
767 775 infra -
776 791 generic ANNUAL
792 813 infra -
814 821 generic ROWTABLE
822 830 generic COUNT
831 832 unit U-X-10 X-10
833 836 generic COUNT
837 841 unit U-B3-MULT B3-01,B3-02
842 846 generic EXPLICIT
847 850 unit U-QA-02 QA-02
851 859 generic EXPLICIT
860 862 unit U-B3-MULT B3-01,B3-02
863 864 unit U-X-10 X-10
865 867 generic EXPLICIT
868 875 generic REFRIG
876 881 unit U-QA-02 QA-02
882 894 generic REFRIG
895 896 unit U-B1-02 B1-02
897 903 unit U-B1-03 B1-03
904 907 unit U-B1-04 B1-04
908 919 detail D-B1-YEAR B1-02
920 920 generic REFRIG
921 926 generic MOMENT
927 935 unit U-X-06 X-06
936 972 unit U-ELEC B6-01,B6-04
973 977 unit U-B2-01 B2-01
978 1004 generic ANNUAL
1005 1009 generic ROWTABLE
1010 1010 unit U-A5-04 A5-04
1011 1011 unit U-B6-03 B6-03
1012 1012 unit U-B7-04 B7-04
1013 1033 unit U-B5-01 B5-01
1034 1083 generic STAGE
1084 1086 unit U-X-04-GWP X-04
1087 1087 generic STAGE
1088 1088 unit U-X-05-TOTAL X-05
1089 1091 unit U-B2-B6-RULE X-02,X-05
1092 1100 unit U-QA-01 QA-01
1101 1108 generic PICK
1109 1112 spec PICK SUM-01,SUM-02,SUM-03
1113 1114 infra -
1115 1118 unit U-SUM-07 SUM-07
1119 1147 unit U-SUM-08 SUM-08
1148 1150 unit U-QA-03 QA-03
1151 1155 unit U-STO-01 STO-01
1156 1158 unit U-X-11 X-11
1159 1166 unit U-X-17 X-17
1167 1170 unit U-X-09 X-09
1171 1181 unit U-X-03 X-03
1182 1190 unit U-X-08 X-08
1191 1192 infra -
1193 1245 readout -
1246 1246 unit U-SUM-04 SUM-04
1247 1247 unit U-SUM-05 SUM-05
1248 1248 unit U-SUM-06 SUM-06
1249 1253 readout -
1254 1255 readout - SUM-08
1256 1264 unit U-X-02-COMPLETE X-02
1265 1265 readout - X-02
1266 1266 readout - SUM-01
1267 1267 readout - SUM-02
1268 1268 readout - SUM-03
1269 1288 infra -
1289 1289 detail D-A13-05 A13-05
1290 1290 detail D-X-13 X-13
1291 1291 detail D-A13-02 A13-02
1292 1292 detail D-X-15 X-15
1293 1295 infra -
1296 1296 detail D-X-16 X-16
1297 1298 detail D-B4-03 B4-03
1299 1311 detail D-B4-01 B4-01
1312 1312 readout - B1-02
1313 1343 detail D-B4-B3-YEAR B4-02,B3-01
1344 1346 detail D-B5-YEAR B5-01
1347 1347 readout - X-06
1348 1348 readout - B6-04
1349 1349 readout - B6-01
1350 1359 generic ANNUAL
1360 1361 detail D-B4-02-ITEM B4-02
1362 1362 readout - B3-01
1363 1363 readout - B1-02
1364 1364 readout - B1-03
1365 1365 readout - B5-01
1366 1400 detail D-X-07 X-07
1401 1418 infra -
"""
CLOSED_FORMS_MAP = """
1 18 infra -
19 38 generic TIME
39 55 generic COUNT
56 78 generic SKIP
79 89 generic ANNUAL
90 170 generic MOMENT
171 219 generic REFRIG
"""

# What each procedure is (short English label; the report describes them in Japanese).
PROCEDURES = {
    # generic operators: (label, units whose own output the operator computes directly)
    "ROWTABLE": ("row table: lines summed per (table, factor key) by _add, value = sum activity*factor by tot",
                 "A13-01 A13-03 A13-04 X-01 A4-01 A4-02 X-12 A5-01 A5-02 A5-03 C1-01 C2-01 C3-01 C4-01 X-14 X-16 STO-02 "
                 "B4-02 B3-01 B3-02 X-17 X-09 X-08"),
    "RESOLVE": ("factor resolution use/_resolve/conv/unit_only: (factor key, conversion) or decline; log = SYS-02",
                "SYS-02"),
    "COUNT": ("renewal count N(T,c) applied to the lines summed per distinct period (period groups)",
              "B4-01 B4-02 B4-03 X-08 X-10 B5-01 B3-01 B1-02 B1-03 B1-04"),
    "EXPLICIT": ("explicit event lists: per equipment row, events filtered by the time rule (second path of the count)",
                 "B4-01 B4-02 B3-01 X-10 X-08"),
    "SKIP": ("year weight of the years that hold a renewal (periodic closed form / explicit list)", "B3-01"),
    "ANNUAL": ("weighted year sum of an annual profile: closed form for CONSTANT / LINEAR_TREND, scan of a TABLE",
               "B6-02 B7-01 B7-02 B7-03 B6-03 B7-04"),
    "MOMENT": ("grid factor as piecewise-linear segments or table; moments G, H", "X-06 B6-03 B2-01 X-11"),
    "REFRIG": ("charge cycles of a refrigerant device: leaked share, share before each change, share at the end",
               "B1-02 B1-03 B1-04"),
    "STAGE": ("stage merge: tables of a stage merged per factor key, read with the columns total / CO2 / gases",
              "X-02 X-04 X-05"),
    "PICK": ("pick: sum of a subset of the stage vector", "SUM-01 SUM-02 SUM-03"),
    "WITHIN": ("residual test |residual| <= tolerance * scale", "SYS-04 QA-04 QA-01"),
    "RECIPE": ("composite factor of one distinct composition, computed once", "A13-02 X-03 X-15"),
    "SAME": ("descriptor equals year table (consistency flag)", "X-06 B6-04 B6-02 B7-01 B7-02 B7-03"),
    "TIME": ("time rules: inside, event_year, last_weight, n_years, valid_period (helper)", ""),
    "PRED": ("validity predicates _nonneg, _ratio (helper)", ""),
}
POST_ONLY = ("U-A5-04", "U-B6-03", "U-B7-04", "U-SUM-04", "U-SUM-05", "U-SUM-06", "U-SUM-07", "U-X-05-TOTAL")  # sums / ratios of finished values


def parse_map(text: str) -> list[dict]:
    rows = []
    for line in text.strip().splitlines():
        p = line.split()
        rows.append({"start": int(p[0]), "end": int(p[1]), "kind": p[2], "proc": p[3],
                     "units": p[4].split(",") if len(p) > 4 else []})
    return rows


def code_lines(path: str) -> tuple[list[str], set[int]]:
    """Source lines and the set of line numbers that carry code (no blank, comment-only or docstring lines)."""
    with open(path, encoding="utf-8") as f:
        src = f.read()
    doc = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                doc.update(range(first.lineno, first.end_lineno + 1))
    skip = (tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT, tokenize.ENCODING,
            tokenize.ENDMARKER)
    code = set()
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type not in skip:
            code.update(range(tok.start[0], tok.end[0] + 1))
    return src.splitlines(), code - doc


def part_a(frozen_code: str, unit_ids: list[str], declared: dict[str, str]) -> dict:
    """Line inventory of the saved model and the count of procedures (a reading; see module docstring)."""
    files = (("fastcalc/engine.py", ENGINE_MAP), ("fastcalc/closed_forms.py", CLOSED_FORMS_MAP))
    unit_re = re.compile(r'\s*"((?:[A-Z]+[0-9]*-[0-9]+))": ')
    per_unit = {u: {"unit": 0, "unit_exclusive": 0, "builder": 0, "detail": 0, "readout": 0, "spec": 0,
                    "procedures": set()} for u in unit_ids}
    by_kind_lines: dict[str, int] = {}
    procs: dict[str, dict] = {}
    n_code_total = 0
    for rel, text in files:
        lines, code = code_lines(os.path.join(frozen_code, rel))
        rows = parse_map(text)
        expect = 1
        for r in rows:   # the map must cover the file exactly once
            if r["start"] != expect or r["end"] < r["start"]:
                raise AssertionError(f"{rel}: line map is not contiguous at {r}")
            expect = r["end"] + 1
        if expect != len(lines) + 1:
            raise AssertionError(f"{rel}: line map ends at {expect - 1}, file has {len(lines)} lines")
        n_code_total += len(code)
        for r in rows:
            carried = None
            for no in range(r["start"], r["end"] + 1):
                if no not in code:
                    continue
                text_line = lines[no - 1]
                kind, proc, units = r["kind"], r["proc"], list(r["units"])
                # cross-cutting calls of the two checks that have no shared operator (they sit inside other blocks)
                if re.match(r"\s*see\(", text_line):
                    kind, proc, units = "unit", "U-SYS-01", ["SYS-01"]
                elif re.match(r"\s*(ref\(|refs\[.*\] = refs\.get)", text_line):
                    kind, proc, units = "unit", "U-SYS-03", ["SYS-03"]
                if kind == "readout" and not units:
                    m = unit_re.match(text_line)
                    if m and m.group(1) in per_unit:
                        carried = m.group(1)
                    elif text_line.strip().startswith(("R = ", "R.update", "})", "}", "A.out", "A.misc")):
                        carried = None
                    units = [carried] if carried else []
                    if not units:
                        kind = "infra"
                by_kind_lines[kind] = by_kind_lines.get(kind, 0) + 1
                if kind in ("generic", "builder", "unit", "detail"):
                    p = procs.setdefault(proc, {"kind": kind, "lines": 0, "units": set(), "where": set()})
                    p["lines"] += 1
                    p["units"].update(units)
                    p["where"].add(rel.split("/")[-1])
                for u in units:
                    if kind in per_unit[u]:
                        per_unit[u][kind] += 1
                        if kind == "unit" and len(units) == 1:
                            per_unit[u]["unit_exclusive"] += 1
                    if kind in ("builder", "unit", "detail"):
                        per_unit[u]["procedures"].add(proc)
    direct = {tag: v[1].split() for tag, v in PROCEDURES.items()}
    for tag, users in direct.items():
        procs[tag]["units"].update(users)
        for u in users:
            per_unit[u]["procedures"].add(tag)
    out_procs = []
    for name in sorted(procs, key=lambda n: (("generic", "builder", "unit", "detail").index(procs[n]["kind"]), n)):
        p = procs[name]
        kind = p["kind"]
        if name in HELPER_TAGS:
            kind = "helper"
        out_procs.append({"procedure": name, "kind": kind, "code_lines": p["lines"], "files": sorted(p["where"]),
                          "units": sorted(p["units"]), "n_units": len(p["units"]),
                          "units_differ_by": "data" if kind in ("generic", "helper") else "code",
                          "post_processing_only": name in POST_ONLY,
                          "label": PROCEDURES.get(name, ("",))[0]})
    count = {k: sum(1 for p in out_procs if p["kind"] == k) for k in ("generic", "helper", "builder", "unit", "detail")}
    count["unit_post_processing_only"] = sum(1 for p in out_procs if p["post_processing_only"])
    count["generic_serving_one_unit"] = sum(1 for p in out_procs if p["kind"] == "generic" and p["n_units"] <= 1)
    count["kinds_for_totals_level_outputs"] = count["generic"] + count["builder"] + count["unit"]
    count["kinds_for_full_outputs"] = count["kinds_for_totals_level_outputs"] + count["detail"]
    count["kinds_if_sums_and_ratios_are_post_processing"] = (count["kinds_for_totals_level_outputs"]
                                                             - count["unit_post_processing_only"])
    units_out = {}
    for u in unit_ids:
        d = per_unit[u]
        calc = d["unit"] + d["builder"]
        own = calc + d["detail"]
        units_out[u] = {"declared_model": declared.get(u, "none"), "calc_lines_unit": d["unit"],
                        "calc_lines_unit_exclusive": d["unit_exclusive"], "calc_lines_builder": d["builder"],
                        "detail_lines": d["detail"], "readout_lines": d["readout"], "spec_lines": d["spec"],
                        "unit_specific_calc_lines": calc, "unit_specific_code_lines": own, "procedures": sorted(d["procedures"]),
                        "generic_operators_direct": sorted(t for t, us in direct.items() if u in us)}
    return {
        "method": "reading of the frozen code by the implementer (line map in this script); not checked by anyone else",
        "rule": "RESEARCH_PROTOCOL.md section 5: a kind is one generic operator with one code path; procedures that "
                "differ by unit are counted one by one; pre-processing that hides a per-unit computation is counted",
        "code_lines_total": n_code_total, "code_lines_by_kind": by_kind_lines, "count": count,
        "procedures": out_procs, "units": units_out,
        "units_without_unit_specific_calc_lines": sorted(u for u, d in units_out.items() if d["unit_specific_calc_lines"] == 0),
        "units_without_unit_specific_code_lines": sorted(u for u, d in units_out.items() if d["unit_specific_code_lines"] == 0),
    }


# --------------------------------------------------------------------------------------------- part B

def flat(compare_mod, res: dict) -> dict[str, dict]:
    return {uid: compare_mod.flatten(val) for uid, val in res.items() if not uid.startswith("_")}


def _is_num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _differs(a, b) -> bool:
    if _is_num(a) and _is_num(b) and math.isnan(a) and math.isnan(b):
        return False
    return type(a) is not type(b) and not (_is_num(a) and _is_num(b)) or a != b


def reaction(base: dict, cand: dict) -> str:
    """'' no change, 'N' a numeric leaf of the unfaulted output changed, 'O' only non-numeric leaves or the shape changed."""
    if base == cand:
        return ""
    other = False
    for path, bv in base.items():
        if path not in cand:
            if _is_num(bv):
                return "N"
            other = True
        elif _differs(bv, cand[path]):
            if _is_num(bv):
                return "N"
            other = True
    if other or set(cand) - set(base):
        return "O"
    return ""


@contextlib.contextmanager
def patched(obj, name, new):
    old = getattr(obj, name)
    setattr(obj, name, new)
    try:
        yield
    finally:
        setattr(obj, name, old)


class FaultBench:
    """Builds the faulted evaluators. Nothing on disk is touched."""

    def __init__(self, engine, cf):
        self.engine, self.cf = engine, cf
        with open(engine.__file__, encoding="utf-8") as f:
            self.source = f.read()
        self.faults: list[dict] = []
        self._build()

    # -- three ways to break something
    def _fn(self, module, name, wrap):
        mod = self.cf if module == "cf" else self.engine

        @contextlib.contextmanager
        def ctx():
            with patched(mod, name, wrap(getattr(mod, name))):
                yield self.engine.evaluate
        return ctx

    def _agg(self, mutate):
        """Break a shared table: the Aggregate is changed right after it has been built."""
        engine = self.engine

        @contextlib.contextmanager
        def ctx():
            orig = engine.aggregate

            def broken(scn, detail=True):
                A = orig(scn, detail)
                mutate(A)
                return A
            with patched(engine, "aggregate", broken):
                yield engine.evaluate
        return ctx

    def _src(self, replacements):
        """Break a closure: a copy of the engine source is patched in memory and executed as its own module."""
        src = self.source
        for old, new in replacements:
            if src.count(old) != 1:
                raise AssertionError(f"anchor occurs {src.count(old)} times: {old!r}")
            src = src.replace(old, new)
        mod = types.ModuleType("fastcalc.engine_fault")
        mod.__package__ = "fastcalc"
        mod.__file__ = self.engine.__file__ + " [patched in memory]"
        exec(compile(src, mod.__file__, "exec"), mod.__dict__)

        @contextlib.contextmanager
        def ctx():
            yield mod.evaluate
        return ctx

    def add(self, fid, operator, kind, target, how, ctx):
        self.faults.append({"id": fid, "operator": operator, "kind": kind, "target": target, "fault": how, "ctx": ctx})

    def _build(self):
        k = 1.01

        def scale_dict(d):
            for key in d:
                d[key] *= k

        def scale_groups(attr):
            def mutate(A):
                for g in A.groups.values():
                    if attr == "mass":
                        g.resource *= k
                        g.waste *= k
                    else:
                        scale_dict(getattr(g, attr))
            return mutate

        def scale_explicit(A):
            A.explicit = [(j, years, [(key, act * k) for key, act in lines], rline, emass, inc)
                          for j, years, lines, rline, emass, inc in A.explicit]

        def scale_annual(A):
            A.annual = [(t, p, (hit[0], hit[1] * k) if hit is not None else None) for t, p, hit in A.annual]

        class FaultyFactorValues(dict):
            def __getitem__(self, key):
                return dict.__getitem__(self, key) * k

        def faulty_aggregate_class(orig):
            class Faulty(orig):
                def __init__(self, scn, detail):
                    super().__init__(scn, detail)
                    self.fval = FaultyFactorValues(self.fval)
            return Faulty

        def faulty_recipe(orig):
            def broken(key, scn, stats, stage_viol, fval):
                r = orig(key, scn, stats, stage_viol, fval)
                if r["value"] is not None:
                    r["value"] *= k
                    fval[key] = r["value"]
                return r
            return broken

        def faulty_segments(orig):
            def broken(grid, Y):
                s = orig(grid, Y)
                return None if s is None else [(a, b, alpha * k, beta) for a, b, alpha, beta in s]
            return broken

        def faulty_profile(orig):
            def broken(profile, Y):
                d = orig(profile, Y)
                return None if d is None else (d[0] * k, d[1])
            return broken

        def faulty_fractions(orig):
            def broken(T, rate, top_up, event_years):
                leaked, before, end = orig(T, rate, top_up, event_years)
                return leaked * k, [b * k for b in before], end * k
            return broken

        a = self.add
        # K1 row table and its readers
        a("ROW.add", "ROWTABLE", "function", "engine._add", "activity * 1.01 when a line is added to a table",
          self._fn("engine", "_add", lambda o: lambda table, key, activity: o(table, key, activity * k)))
        a("ROW.tables", "ROWTABLE", "table", "Aggregate.tables (all row tables of aggregate)", "every activity * 1.01",
          self._agg(lambda A: [scale_dict(t) for t in A.tables.values()]))
        a("ROW.tot", "ROWTABLE", "closure", "finish.tot", "each product activity * factor * 1.01",
          self._src([("        for key, act in table.items():\n            total += act * fval[key]\n",
                      "        for key, act in table.items():\n            total += act * fval[key] * 1.01\n")]))
        a("ROW.fval", "ROWTABLE", "table", "Aggregate.fval (factor key -> value)", "every read of a factor value * 1.01",
          self._fn("engine", "Aggregate", faulty_aggregate_class))
        a("STAGE.merge", "STAGE", "closure", "finish: stage loop (stage_all)", "stage total * 1.01",
          self._src([("        stage_all[s] = total\n", "        stage_all[s] = total * 1.01\n")]))
        a("STAGE.gas_of", "STAGE", "closure", "finish.gas_of", "gas amounts of a factor key * 1.01",
          self._src([("            gas_cache[key] = g\n        return g\n",
                      "            gas_cache[key] = g\n        return {n_: v_ * 1.01 for n_, v_ in g.items()}\n")]))
        # K7 factor resolution
        a("RES.resolve", "RESOLVE", "closure", "aggregate._resolve", "conversion of a resolved factor * 1.01",
          self._src([("        return ((fid, c), False)\n", "        return ((fid, c * 1.01), False)\n")]))
        a("RES.decline", "RESOLVE", "closure", "aggregate._resolve", "every factor declined and reported as a unit mismatch",
          self._src([("        return ((fid, c), False)\n", "        return (None, True)\n")]))
        a("RES.conv", "RESOLVE", "closure", "aggregate.conv", "every unit conversion * 1.01 (also the identity)",
          self._src([("    def conv(u, v, extra=()):\n",
                      "    def conv(u, v, extra=()):\n        r_ = _conv0(u, v, extra)\n"
                      "        return r_ * 1.01 if r_ is not None else None\n\n    def _conv0(u, v, extra=()):\n")]))
        a("REC.recipe", "RECIPE", "function", "engine._make_recipe", "composite factor value * 1.01",
          self._fn("engine", "_make_recipe", faulty_recipe))
        # K2 counts, groups, repairs
        a("CNT.renewal_count", "COUNT", "function", "closed_forms.renewal_count", "count - 1 (not below 0)",
          self._fn("cf", "renewal_count", lambda o: lambda T, period: max(0, o(T, period) - 1)))
        a("CNT.groups_u", "COUNT", "table", "Aggregate.groups[*].u (one renewal per period)", "every activity * 1.01",
          self._agg(scale_groups("u")))
        a("CNT.groups_r", "COUNT", "table", "Aggregate.groups[*].r (repairs per year per period)", "every activity * 1.01",
          self._agg(scale_groups("r")))
        a("CNT.groups_mass", "COUNT", "table", "Aggregate.groups[*].resource / .waste", "both * 1.01",
          self._agg(scale_groups("mass")))
        a("EXP.lines", "EXPLICIT", "table", "Aggregate.explicit (lines of equipment with an event list)",
          "every activity * 1.01", self._agg(scale_explicit))
        a("SKIP.periodic", "SKIP", "function", "closed_forms.skip_weight_periodic", "result + 0.5",
          self._fn("cf", "skip_weight_periodic", lambda o: lambda T, period, n: o(T, period, n) + 0.5))
        a("SKIP.events", "SKIP", "function", "closed_forms.skip_weight_events", "result + 0.5",
          self._fn("cf", "skip_weight_events", lambda o: lambda T, events: o(T, events) + 0.5))
        # K3 annual sums and grid moments
        a("ANN.linear_weighted_sum", "ANNUAL", "function", "closed_forms.linear_weighted_sum", "result * 1.01",
          self._fn("cf", "linear_weighted_sum", lambda o: lambda T, base, slope: o(T, base, slope) * k))
        a("ANN.profile", "ANNUAL", "function", "engine._profile", "base of a parametric profile * 1.01",
          self._fn("engine", "_profile", faulty_profile))
        a("ANN.values", "ANNUAL", "function", "engine._values", "every yearly value * 1.01",
          self._fn("engine", "_values", lambda o: lambda profile, Y: [v * k for v in o(profile, Y)]))
        a("ANN.hits", "ANNUAL", "table", "Aggregate.annual (factor key, conversion of an annual quantity)",
          "conversion * 1.01", self._agg(scale_annual))
        a("MOM.segment_moments", "MOMENT", "function", "closed_forms.segment_moments", "G and H * 1.01",
          self._fn("cf", "segment_moments", lambda o: lambda segments, T: tuple(v * k for v in o(segments, T))))
        a("MOM.table_moments", "MOMENT", "function", "closed_forms.table_moments", "G and H * 1.01",
          self._fn("cf", "table_moments", lambda o: lambda table, T: tuple(v * k for v in o(table, T))))
        a("MOM.grid_segments", "MOMENT", "function", "closed_forms.grid_segments", "level of every segment * 1.01",
          self._fn("cf", "grid_segments", faulty_segments))
        a("SAME.same", "SAME", "function", "engine._same", "result negated",
          self._fn("engine", "_same", lambda o: lambda values, table: not o(values, table)))
        # K4, K5, K6
        a("REF.fractions", "REFRIG", "function", "closed_forms.refrigerant_fractions", "all three results * 1.01",
          self._fn("cf", "refrigerant_fractions", faulty_fractions))
        a("PICK.pick", "PICK", "closure", "finish.pick", "each stage value * 1.01 when it is picked",
          self._src([("                total += by_stage[s]\n", "                total += by_stage[s] * 1.01\n")]))
        a("WITHIN.within", "WITHIN", "function", "engine._within", "result negated",
          self._fn("engine", "_within", lambda o: lambda residual, tol, scale: not o(residual, tol, scale)))
        # helper rules
        a("TIME.inside", "TIME", "function", "closed_forms.inside", "event time shifted by one year (tau + 1)",
          self._fn("cf", "inside", lambda o: lambda tau, T: o(tau + 1.0, T)))
        a("TIME.event_year", "TIME", "function", "closed_forms.event_year", "year - 1 (not below 1)",
          self._fn("cf", "event_year", lambda o: lambda tau: max(1, o(tau) - 1)))
        a("TIME.last_weight", "TIME", "function", "closed_forms.last_weight", "weight of the last year * 0.99",
          self._fn("cf", "last_weight", lambda o: lambda T: o(T) * 0.99))
        a("PRED.nonneg", "PRED", "function", "engine._nonneg", "always False",
          self._fn("engine", "_nonneg", lambda o: lambda x: False))
        a("PRED.ratio", "PRED", "function", "engine._ratio", "always False",
          self._fn("engine", "_ratio", lambda o: lambda x: False))

    def table_fault(self, name):
        def mutate(A):
            t = A.tables.get(name)
            if t:
                for key in t:
                    t[key] *= 1.01
        return self._agg(mutate)


def transitive_deps(unit_id: str, cache: dict) -> set[str]:
    if unit_id not in cache:
        deps = set()
        for d in baseline.depends_on(unit_id):
            deps.add(d)
            deps |= transitive_deps(d, cache)
        cache[unit_id] = deps
    return cache[unit_id]


def part_b(engine, cf, compare_mod, unit_ids, declared_units, part_a_out) -> dict:
    bench = scenarios.benchmark()
    design = scenarios.design_set(60, "M")
    chosen = [bench[0]] + [design[i] for i in FAULT_DESIGN_INDEX]
    ok, excluded = scenarios.usable(chosen)
    if excluded:
        raise AssertionError(f"fault-injection scenario outside the valid domain: {excluded}")
    described = []
    for scn in chosen:
        op, b = scn.operation, scn.boundary
        described.append({
            "scenario": scn.meta.scenario_id, "rows": [len(scn.materials), len(scn.equipment), len(scn.refrigerants)],
            "study_period": b.study_period, "grid_kind": op.grid.kind,
            "profile_kinds": [op.electricity.kind, op.gas.kind, scn.water_waste.water.kind],
            "reconstruction": b.reconstruction_scenario, "replacement_cycle": b.replacement_cycle,
            "baseline_attached": b.baseline_scenario is not None, "gas_scope": b.results_gas_scope,
            "explicit_event_lists": sum(1 for e in scn.equipment if e.replacement_event_list is not None),
            "change_year_lists": sum(1 for d in scn.refrigerants if d.change_years is not None),
            "top_up_devices": sum(1 for d in scn.refrigerants if d.top_up),
            "composite_rows": sum(1 for m in scn.materials if m.composition is not None),
            "epd_rows": sum(1 for m in scn.materials if m.epd is not None)})
    base = [flat(compare_mod, engine.evaluate(scn)) for scn in chosen]
    again = [flat(compare_mod, engine.evaluate(scn)) for scn in chosen]
    if base != again:
        raise AssertionError("the unfaulted model is not deterministic; exact comparison would be meaningless")
    fb = FaultBench(engine, cf)
    table_names = sorted(engine.aggregate(chosen[0], False).tables)

    def run(ctx) -> tuple[dict[str, str], list[str]]:
        react = {u: "" for u in unit_ids}
        errors = []
        with ctx() as evaluate:
            for scn, b in zip(chosen, base):
                try:
                    res = flat(compare_mod, evaluate(scn))
                except Exception as exc:   # a fault may make the model fail; that is recorded, not hidden
                    errors.append(f"{scn.meta.scenario_id}: {type(exc).__name__}: {exc}")
                    continue
                for u in unit_ids:
                    r = reaction(b[u], res.get(u, {}))
                    if r == "N" or (r == "O" and react[u] == ""):
                        react[u] = r
        return react, errors

    matrix = {u: {} for u in unit_ids}
    faults_out = []
    for f in fb.faults:
        react, errors = run(f["ctx"])
        for u, r in react.items():
            if r:
                matrix[u][f["id"]] = r
        faults_out.append({"id": f["id"], "operator": f["operator"], "kind": f["kind"], "target": f["target"],
                           "fault": f["fault"], "units_numeric": sorted(u for u, r in react.items() if r == "N"),
                           "units_other_only": sorted(u for u, r in react.items() if r == "O"), "errors": errors})
    after = [flat(compare_mod, engine.evaluate(scn)) for scn in chosen]
    if after != base:
        raise AssertionError("a fault was not removed: the unfaulted outputs changed after the injections")

    # which unit reads which row table of aggregate
    table_reads = {}
    for name in table_names:
        react, errors = run(fb.table_fault(name))
        table_reads[name] = {"units_numeric": sorted(u for u, r in react.items() if r == "N"),
                             "units_other_only": sorted(u for u, r in react.items() if r == "O"), "errors": errors}

    cache: dict = {}
    for f in faults_out:
        hit = set(f["units_numeric"]) | set(f["units_other_only"])
        f["roots"] = sorted(u for u in hit if not (transitive_deps(u, cache) & hit))
    by_operator = {}
    for f in faults_out:
        d = by_operator.setdefault(f["operator"], {"faults": [], "numeric": set(), "other": set()})
        d["faults"].append(f["id"])
        d["numeric"].update(f["units_numeric"])
        d["other"].update(f["units_other_only"])
    operator_out = {}
    for tag, d in by_operator.items():
        claimed = set(part_a_out["procedures_by_name"][tag]["units"])
        reacts = d["numeric"] | d["other"]
        operator_out[tag] = {"faults": d["faults"], "units_numeric": sorted(d["numeric"]),
                             "units_other_only": sorted(d["other"] - d["numeric"]),
                             "direct_users_by_reading": sorted(claimed),
                             "direct_users_without_reaction": sorted(claimed - reacts)}
    helper_faults = {f["id"] for f in faults_out if f["operator"] in HELPER_TAGS}
    no_numeric = sorted(u for u in unit_ids if not any(r == "N" and fid not in helper_faults for fid, r in matrix[u].items()))
    no_any = sorted(u for u in unit_ids if not any(fid not in helper_faults for fid in matrix[u]))
    no_any_incl_helpers = sorted(u for u in unit_ids if not matrix[u])
    declared_check = {}
    for model_id, units in declared_units.items():
        own = {f["id"] for f in faults_out if f["operator"] in DECLARED_OPERATORS[model_id]}
        declared_check[model_id] = {
            "operators": list(DECLARED_OPERATORS[model_id]), "faults": sorted(own), "declared_units": len(units),
            "react_numeric": sorted(u for u in units if any(matrix[u].get(fid) == "N" for fid in own)),
            "react_other_only": sorted(u for u in units if any(fid in matrix[u] for fid in own)
                                       and not any(matrix[u].get(fid) == "N" for fid in own)),
            "no_reaction_to_own_model": sorted(u for u in units if not any(fid in matrix[u] for fid in own)),
        }
    strict = {}
    for u in unit_ids:
        info = part_a_out["units"][u]
        ops = info["generic_operators_direct"]
        b_ok = [t for t in ops if t in operator_out and u in (set(operator_out[t]["units_numeric"])
                                                               | set(operator_out[t]["units_other_only"]))]
        strict[u] = {"a_no_unit_specific_code": info["unit_specific_code_lines"] == 0,
                     "b_reacts_to_operator": b_ok, "unit_specific_code_lines": info["unit_specific_code_lines"],
                     "member_strict": info["unit_specific_code_lines"] == 0 and bool(b_ok)}
    return {
        "scenarios": described,
        "criterion": "exact inequality between the unfaulted and the faulted output of the SAME model on the same "
                     "scenario (the model is deterministic); N = a numeric leaf changed, O = only booleans, strings, "
                     "None or the shape of a list changed",
        "faults": faults_out, "matrix": matrix, "by_operator": operator_out, "row_table_reads": table_reads,
        "units_without_numeric_reaction_to_any_operator_fault": no_numeric,
        "units_without_any_reaction_to_any_operator_fault": no_any,
        "units_without_any_reaction_including_helper_rules": no_any_incl_helpers,
        "declared_membership_check": declared_check,
        "strict_membership_section_5_2": strict,
        "strict_members": sorted(u for u, s in strict.items() if s["member_strict"]),
        "note": "a reaction is necessary for membership, not sufficient: a unit downstream of a broken value reacts "
                "without calling the operator itself ('roots' lists the reacting units none of whose declared "
                "dependencies react)",
    }


# --------------------------------------------------------------------------------------------- part C

class UnitAcc:
    __slots__ = ("n", "n_other", "n_ref_zero", "n_ref_zero_cand_nonzero", "max_abs_when_ref_zero", "mismatches",
                 "max_rel", "worst", "examples")

    def __init__(self):
        self.n = self.n_other = self.n_ref_zero = self.n_ref_zero_cand_nonzero = self.mismatches = 0
        self.max_abs_when_ref_zero = self.max_rel = 0.0
        self.worst = None
        self.examples = []

    def bad(self, text):
        self.mismatches += 1
        if len(self.examples) < 3:
            self.examples.append(text)

    def summary(self):
        return {"n_values": self.n, "n_ref_zero": self.n_ref_zero, "n_non_numeric": self.n_other,
                "mismatches": self.mismatches, "max_rel_error": self.max_rel, "worst": self.worst,
                "n_ref_zero_with_nonzero_candidate": self.n_ref_zero_cand_nonzero,
                "max_abs_when_ref_zero": self.max_abs_when_ref_zero, "examples": self.examples}


def strict_compare(acc: UnitAcc, ref: dict, cand: dict, sid: str) -> None:
    """Leaf-by-leaf, relative 1e-9 against the reference, no absolute floor; a zero reference is counted apart."""
    for path, rv in ref.items():
        if path not in cand:
            acc.bad(f"{sid} {path}: missing in the candidate")
            continue
        cv = cand[path]
        if _is_num(rv) and _is_num(cv):
            if math.isnan(rv) or math.isnan(cv):
                if not (math.isnan(rv) and math.isnan(cv)):
                    acc.bad(f"{sid} {path}: {rv!r} vs {cv!r}")
                continue
            if rv == 0:
                acc.n_ref_zero += 1
                if cv != 0:
                    acc.n_ref_zero_cand_nonzero += 1
                    acc.max_abs_when_ref_zero = max(acc.max_abs_when_ref_zero, abs(cv))
                    acc.bad(f"{sid} {path}: reference 0, candidate {cv!r}")
                continue
            acc.n += 1
            rel = abs(cv - rv) / abs(rv)
            if rel > acc.max_rel:
                acc.max_rel = rel
                acc.worst = f"{sid} {path}"
            if not rel <= REL_TOL:
                acc.bad(f"{sid} {path}: {rv!r} vs {cv!r}")
        else:
            acc.n_other += 1
            if type(rv) is not type(cv) or rv != cv:
                acc.bad(f"{sid} {path}: {rv!r} vs {cv!r}")
    for path in cand:
        if path not in ref:
            acc.bad(f"{sid} {path}: not in the reference")


def totals_of(accs: dict[str, UnitAcc]) -> dict:
    return {"n_values": sum(a.n for a in accs.values()), "n_ref_zero": sum(a.n_ref_zero for a in accs.values()),
            "n_non_numeric": sum(a.n_other for a in accs.values()), "mismatches": sum(a.mismatches for a in accs.values()),
            "max_rel_error": max((a.max_rel for a in accs.values()), default=0.0),
            "n_ref_zero_with_nonzero_candidate": sum(a.n_ref_zero_cand_nonzero for a in accs.values()),
            "units_with_mismatch": sorted(u for u, a in accs.items() if a.mismatches)}


def part_c(engine, compare_mod, unit_ids, quick: bool) -> dict:
    n = 12 if quick else 60
    sets = {"design": scenarios.design_set(n, "M"), "evaluation": scenarios.evaluation_set(n, "M"),
            "edge": [s for _, s in scenarios.edge_set()]}
    out = {"tolerance": REL_TOL, "comparison": "own strict comparison (relative, no absolute floor; zero-reference pairs "
           "counted apart and required to be exactly zero) plus the frozen common.compare with floor 0 as a cross-check",
           "sets": {}}
    overall = {u: UnitAcc() for u in unit_ids}
    for name, scns in sets.items():
        ok, excluded = scenarios.usable(scns)
        accs = {u: UnitAcc() for u in unit_ids}
        frozen_fail = []
        frozen_max = 0.0
        for scn in ok:
            sid = scn.meta.scenario_id
            ref = baseline.run_reference(scn)
            cand = engine.evaluate(scn)
            fr, fc = flat(compare_mod, ref), flat(compare_mod, cand)
            if set(fr) != set(fc):
                raise AssertionError(f"{sid}: unit sets differ: {sorted(set(fr) ^ set(fc))}")
            for u in unit_ids:
                strict_compare(accs[u], fr[u], fc[u], sid)
                strict_compare(overall[u], fr[u], fc[u], sid)
            c = compare_mod.compare(ref, cand, 0.0)
            frozen_max = max(frozen_max, c.max_abs_rel_error)
            if not c.within(REL_TOL) or c.extra:
                frozen_fail.append(sid)
        out["sets"][name] = {"n_scenarios": len(scns), "n_usable": len(ok), "excluded": excluded,
                             "totals": totals_of(accs), "frozen_compare_failures": frozen_fail,
                             "frozen_compare_max_rel_error": frozen_max,
                             "per_unit": {u: accs[u].summary() for u in unit_ids}}
    out["all_sets"] = {"totals": totals_of(overall),
                       "per_unit": {u: {k: v for k, v in overall[u].summary().items() if k != "examples"} for u in unit_ids}}

    # T sweep: ONE aggregate per scenario, finish at every period, against a fresh reference run at that period
    design = sets["design"][: (6 if quick else SWEEP_DESIGN_N)]
    sweep_scns, _ = scenarios.usable(design + ([] if quick else sets["edge"]))
    per_T = {T: {u: UnitAcc() for u in unit_ids} for T in scenarios.SWEEP_PERIODS}
    per_unit = {u: UnitAcc() for u in unit_ids}
    excluded, n_pairs, n_aggregates = [], 0, 0
    for scn in sweep_scns:
        A = engine.aggregate(scn, True)
        n_aggregates += 1
        for T in scenarios.SWEEP_PERIODS:
            cur = scenarios.with_period(scn, T)
            why = scenarios.valid_domain(cur)
            if why:
                excluded.append((cur.meta.scenario_id, why))
                continue
            ref = baseline.run_reference(cur)
            cand = engine.finish(A, T, True, None)
            fr, fc = flat(compare_mod, ref), flat(compare_mod, cand)
            n_pairs += 1
            for u in unit_ids:
                strict_compare(per_T[T][u], fr[u], fc[u], cur.meta.scenario_id)
                strict_compare(per_unit[u], fr[u], fc[u], cur.meta.scenario_id)
    out["sweep"] = {
        "periods": list(scenarios.SWEEP_PERIODS), "n_scenarios": len(sweep_scns), "n_aggregates": n_aggregates,
        "n_scenario_period_pairs": n_pairs, "excluded": excluded,
        "scenarios": f"first {len(design)} of the design set" + ("" if quick else " and the usable edge set"),
        "note": "the per-row lists are built once at the scenario's own period; finish(A, T) is called with detail on; "
                "the comparison covers all 70 units with full outputs",
        "totals": totals_of(per_unit),
        "per_period": {repr(T): totals_of(per_T[T]) for T in scenarios.SWEEP_PERIODS},
        "per_unit": {u: per_unit[u].summary() for u in unit_ids},
    }
    return out


# --------------------------------------------------------------------------------------------- part D

FINISH_BLOCKS = (   # frozen line ranges of engine.finish and what they work on
    (794, 821, "set-up", "neutral"),
    (822, 867, "renewals, repairs, explicit event lists", "T-dependent multipliers"),
    (868, 920, "refrigerant charge cycles (reads the device rows again)", "T-dependent multipliers"),
    (921, 935, "grid moments and descriptor check", "T-dependent multipliers"),
    (936, 977, "purchased electricity", "T-dependent multipliers"),
    (978, 1004, "annual quantities", "T-dependent multipliers"),
    (1005, 1012, "unit values read from the tables (calls of tot)", "reads: static and T-dependent tables mixed"),
    (1013, 1033, "rebuild", "T-dependent multipliers"),
    (1034, 1091, "stage merge with gas columns", "reads: static and T-dependent tables mixed"),
    (1092, 1147, "reconciliation, indicators, comparison", "reads: static and T-dependent tables mixed"),
    (1148, 1192, "remaining checks, class / route / component / cycle tables", "reads: mostly static tables"),
    (1193, 1277, "result assembly", "neutral"),
    (1280, 1400, "_detail: per-row lists and yearly series", "T-dependent outputs (full output only)"),
)


def count_instructions(fn):
    """Executed bytecode instructions per (code object, offset) while ``fn`` runs (sys.monitoring, Python >= 3.12)."""
    mon = sys.monitoring
    tool = mon.PROFILER_ID
    counts: dict = {}

    def on_instruction(code, offset):
        key = (code, offset)
        counts[key] = counts.get(key, 0) + 1

    mon.use_tool_id(tool, "expA1")
    mon.register_callback(tool, mon.events.INSTRUCTION, on_instruction)
    mon.set_events(tool, mon.events.INSTRUCTION)
    try:
        fn()
    finally:
        mon.set_events(tool, 0)
        mon.register_callback(tool, mon.events.INSTRUCTION, None)
        mon.free_tool_id(tool)
    return counts


def summarize_instructions(counts: dict) -> dict:
    by_package: dict[str, int] = {}
    by_function: dict[str, int] = {}
    engine_lines: dict[int, int] = {}
    line_of: dict = {}
    for (code, offset), n in counts.items():
        path = code.co_filename.replace(os.sep, "/")
        package = next((p for p in ("refcalc", "fastcalc", "synth", "common") if f"/{p}/" in path), "other")
        by_package[package] = by_package.get(package, 0) + n
        if package == "other":
            continue
        name = f"{package}/{os.path.basename(path)}:{code.co_qualname}"
        by_function[name] = by_function.get(name, 0) + n
        if path.endswith("fastcalc/engine.py"):
            table = line_of.get(code)
            if table is None:
                table = line_of[code] = {}
                for start, end, line in code.co_lines():
                    for off in range(start, end, 2):
                        table[off] = line
            line = table.get(offset)
            if line is not None:
                engine_lines[line] = engine_lines.get(line, 0) + n
    model = sum(v for p, v in by_package.items() if p != "other")
    top = sorted(by_function.items(), key=lambda kv: -kv[1])[:12]
    return {"instructions_model_code": model, "by_package": by_package, "top_functions": top, "_engine_lines": engine_lines,
            "_by_function": by_function}


def best_time(fn, repeats: int) -> float:
    times = []
    for _ in range(repeats):
        t = time.perf_counter()
        fn()
        times.append(time.perf_counter() - t)
    return statistics.median(times)


def part_d(engine, quick: bool) -> dict:
    if not hasattr(sys, "monitoring"):
        return {"skipped": "sys.monitoring is not available in this interpreter (Python >= 3.12 needed)"}
    bench = scenarios.benchmark()
    out = {"unit": "executed bytecode instructions inside refcalc / fastcalc / synth code objects (sys.monitoring "
                   "INSTRUCTION events); interpreter-specific, a reference value only",
           "python": platform.python_version(), "sizes": {}}
    for size, scn in (("S", bench[0]),) if quick else (("S", bench[0]), ("M", bench[1])):
        plain = copy.deepcopy(scn)
        plain.boundary.baseline_scenario = None   # without the comparison against the baseline twin (SUM-08)
        T = plain.boundary.study_period
        rec = {"rows": [len(scn.materials), len(scn.equipment), len(scn.refrigerants)], "study_period": T}
        holder = {}

        def measure(label, fn):
            s = summarize_instructions(count_instructions(fn))
            rec[label] = {k: v for k, v in s.items() if not k.startswith("_")}
            return s

        ref = measure("reference_all_units", lambda: baseline.run_reference(plain))
        full = measure("unified_full_output", lambda: engine.evaluate(plain, True))
        tot = measure("unified_totals_only", lambda: engine.evaluate(plain, False))
        agg = measure("unified_aggregate_full", lambda: holder.__setitem__("A", engine.aggregate(plain, True)))
        fin = measure("unified_finish_full", lambda: engine.finish(holder["A"], T, True, None))
        agg0 = measure("unified_aggregate_totals", lambda: holder.__setitem__("A0", engine.aggregate(plain, False)))
        fin0 = measure("unified_finish_totals", lambda: engine.finish(holder["A0"], T, False, None))
        with_base_ref = measure("reference_all_units_with_baseline_twin", lambda: baseline.run_reference(scn))
        with_base_uni = measure("unified_full_output_with_baseline_twin", lambda: engine.evaluate(scn, True))
        r = ref["instructions_model_code"]
        rec["ratios"] = {
            "unified_full_over_reference": full["instructions_model_code"] / r,
            "unified_totals_over_reference": tot["instructions_model_code"] / r,
            "with_baseline_twin_unified_full_over_reference":
                with_base_uni["instructions_model_code"] / with_base_ref["instructions_model_code"],
        }
        for label, a, f in (("full_output", agg, fin), ("totals_only", agg0, fin0)):
            ai, fi = a["instructions_model_code"], f["instructions_model_code"]
            blocks = []
            lines = f["_engine_lines"]
            in_blocks = 0
            for lo, hi, what, cls in FINISH_BLOCKS:
                v = sum(c for line, c in lines.items() if lo <= line <= hi)
                in_blocks += v
                blocks.append({"lines": [lo, hi], "what": what, "class": cls, "instructions": v, "share_of_finish": v / fi})
            closed = sum(v for name, v in f["_by_function"].items() if "closed_forms.py" in name)
            helpers = fi - in_blocks - closed
            by_class: dict[str, int] = {"closed forms (T-dependent multipliers)": closed,
                                        "helpers outside the blocks (_add, predicates, _profile, _values, synth)": helpers}
            for b in blocks:
                by_class[b["class"]] = by_class.get(b["class"], 0) + b["instructions"]
            k = len(scenarios.SWEEP_PERIODS)
            rec[f"split_{label}"] = {
                "aggregate_T_independent": ai, "finish_repeated_per_period": fi,
                "share_T_independent_of_one_evaluation": ai / (ai + fi),
                "finish_blocks": blocks,
                "finish_by_class": {c: {"instructions": v, "share_of_finish": v / fi} for c, v in by_class.items()},
                "sweep_of_k_periods": {"k": k, "reference_k_runs": k * r, "unified_one_aggregate_k_finish": ai + k * fi,
                                       "ratio": (ai + k * fi) / (k * r),
                                       "note": "reference instructions taken at the scenario's own period for all k"},
            }
        reps = 3 if size == "M" or quick else 7
        rec["seconds_median"] = {
            "repeats": reps,
            "reference_all_units": best_time(lambda: baseline.run_reference(plain), reps),
            "unified_full_output": best_time(lambda: engine.evaluate(plain, True), reps),
            "unified_totals_only": best_time(lambda: engine.evaluate(plain, False), reps),
            "unified_aggregate_full": best_time(lambda: engine.aggregate(plain, True), reps),
            "unified_finish_full": best_time(lambda: engine.finish(holder["A"], T, True, None), reps),
            "unified_finish_totals": best_time(lambda: engine.finish(holder["A0"], T, False, None), reps),
        }
        out["sizes"][size] = rec
    return out


# --------------------------------------------------------------------------------------------- main

def fastcalc_tree() -> str:
    rel = f"{baseline.FROZEN_REL}/fastcalc"
    got = baseline._git("rev-parse", f"HEAD:{rel}")
    dirty = baseline._git("--no-optional-locks", "status", "--porcelain", "--", rel)
    if got != FASTCALC_TREE:
        raise baseline.BaselineChanged(f"{rel}: committed tree {got}, expected {FASTCALC_TREE}")
    if dirty:
        raise baseline.BaselineChanged(f"{rel}: working tree differs from the commit:\n{dirty}")
    return got


def pycache_dirs(root: str) -> list[str]:
    return sorted(os.path.join(d, n) for d, names, _ in os.walk(root) for n in names if n == "__pycache__")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--quick", action="store_true", help="small sets, benchmark S only; the record is NOT written")
    args = ap.parse_args(argv)
    t0 = time.time()
    trees = dict(baseline.assert_frozen())
    trees["fastcalc"] = fastcalc_tree()
    baseline.load()
    from common import compare as compare_mod   # frozen, read-only
    from fastcalc import closed_forms as cf     # frozen candidate, read-only
    from fastcalc import engine

    unit_ids = baseline.unit_ids()
    with open(os.path.join(baseline.FROZEN_CODE, "..", "03_MODELS", "models.json"), encoding="utf-8") as f:
        models = json.load(f)
    declared_units = {m["id"]: m["units"] for m in models["models"]}
    declared = {u: m for m, units in declared_units.items() for u in units}

    a = part_a(baseline.FROZEN_CODE, unit_ids, declared)
    a["procedures_by_name"] = {p["procedure"]: p for p in a["procedures"]}
    t1 = time.time()
    b = part_b(engine, cf, compare_mod, unit_ids, declared_units, a)
    del a["procedures_by_name"]
    t2 = time.time()
    c = part_c(engine, compare_mod, unit_ids, args.quick)
    t3 = time.time()
    d = part_d(engine, args.quick)
    t4 = time.time()
    trees_after = dict(baseline.assert_frozen())
    trees_after["fastcalc"] = fastcalc_tree()

    out = {
        "experiment": "EXP-A1", "title": "route A: recount of the saved unified model (K1..K7) as candidate TC-A-01",
        "candidate": "TC-A-01", "route": "A", "formula_version": f"saved unified model as committed (fastcalc tree {trees['fastcalc']})",
        "evidence_level": "N (numerical, fictional data) for parts B, C, D; part A is a reading of the code by the "
                          "implementer; U (practical validity) is not reached",
        "checked_by": "implementer only",
        "data_statement": "fictional scenarios of the frozen generator; independent concept model (70 units); no original "
                          "file, formula, factor, service life or rate of any real tool; says nothing about real buildings "
                          "and claims no compatibility or equivalence with any tool",
        "output_scope": "all 70 units, full outputs (values, per-row lists, yearly series, counts, booleans, lists of "
                        "violations)",
        "frozen_trees": trees, "frozen_trees_after_run": trees_after,
        "pycache_dirs_in_frozen_code": pycache_dirs(baseline.FROZEN_CODE),
        "python": platform.python_version(), "quick": args.quick,
        "seconds": {"A": round(t1 - t0, 1), "B": round(t2 - t1, 1), "C": round(t3 - t2, 1), "D": round(t4 - t3, 1)},
        "A_count_of_transformation_kinds": a, "B_membership_by_fault_injection": b, "C_exactness": c, "D_load": d,
    }
    if not args.quick:
        os.makedirs(DEST, exist_ok=True)
        with open(os.path.join(DEST, "route_a_recount.json"), "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=1, default=lambda o: sorted(o) if isinstance(o, set) else str(o))

    print(json.dumps({"frozen_trees": trees, "seconds": out["seconds"], "count": a["count"],
                      "units_without_unit_specific_code_lines": a["units_without_unit_specific_code_lines"],
                      "strict_members": b["strict_members"],
                      "no_numeric_reaction": b["units_without_numeric_reaction_to_any_operator_fault"],
                      "no_reaction_at_all": b["units_without_any_reaction_to_any_operator_fault"],
                      "no_reaction_incl_helpers": b["units_without_any_reaction_including_helper_rules"],
                      "declared_without_reaction": {m: v["no_reaction_to_own_model"]
                                                    for m, v in b["declared_membership_check"].items()},
                      "fault_errors": {f["id"]: f["errors"][:2] for f in b["faults"] if f["errors"]},
                      "exactness": {k: v["totals"] for k, v in c["sets"].items()},
                      "exactness_frozen_compare_failures": {k: v["frozen_compare_failures"] for k, v in c["sets"].items()},
                      "sweep": {"pairs": c["sweep"]["n_scenario_period_pairs"], "excluded": len(c["sweep"]["excluded"]),
                                **c["sweep"]["totals"]},
                      "pycache_dirs_in_frozen_code": out["pycache_dirs_in_frozen_code"]}, ensure_ascii=False, indent=1))
    for size, rec in d.get("sizes", {}).items():
        print(size, json.dumps({"ratios": rec["ratios"],
                                "share_T_independent_full": rec["split_full_output"]["share_T_independent_of_one_evaluation"],
                                "share_T_independent_totals": rec["split_totals_only"]["share_T_independent_of_one_evaluation"],
                                "sweep_ratio_totals": rec["split_totals_only"]["sweep_of_k_periods"]["ratio"],
                                "seconds": rec["seconds_median"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
