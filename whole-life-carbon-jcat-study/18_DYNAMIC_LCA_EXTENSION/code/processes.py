"""Stage 2: process time functions of the 70-unit model (independent concept model, fictional data).

Every kernel term of the canonical whole-building equation (chapter 17, canon.py) is assigned to exactly ONE process
of the building's life cycle, and placed on the real-time axis t (time since the start of occupancy) by the
real-time decomposition of chapter 17 (TH-4):

  e_i(t) = sum of point masses (amount at a time) + piecewise-constant densities (rate on an interval)
           + terminal masses at t = T (emitted at the end of the study period; amount may depend on T)

This is the DERIVED layer (no assumption beyond the meaning of each unit). Distributions that the 70 units do not
define (construction period, supply-chain timing, end-of-life duration, within-year profiles) are added only in
extensions.py, each labelled as an assumption.

Process families (the number of instances is not fixed: rows of the input tables are instances):
  P01 material manufacturing      A13-01, A13-03, A13-04        t = 0
  P02 equipment manufacturing     X-01                          t = 0
  P03 transport to site           A4-01, A4-02                  t = 0
  P04 construction site           A5-04                         t = 0
  P05 refrigerant leakage         B1-02                         density per device x year cell
  P06 refrigerant at change       B1-03                         masses at change times, negative densities after them
  P07 facility management energy  B2-01 (stage B2)              density per year cell (= rho x electricity)
  P08 repair                      B3-01                         density; negative masses/densities in renewal years
  P09 replacement                 B4-02                         masses at renewal times
  P10 refurbishment / rebuild     B5-01                         masses at n C
  P11 operational energy          B6-03, -B2-01 (stage B6)      density per year cell
  P12 water and waste in use      B7-04                         density per year cell
  P13 demolition                  C1-01                         t = T
  P14 waste transport             C2-01                         t = T
  P15 waste processing            C3-01, X-14                   t = T
  P16 final disposal              C4-01                         t = T
  P17 refrigerant at end of life  B1-04                         t = T (amount = state of the stock at T)
"""
from __future__ import annotations

import bisect
import collections
import math
import os
import sys
from dataclasses import dataclass, field
from fractions import Fraction

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
CH17 = os.path.normpath(os.path.join(HERE, "..", "..", "17_WHOLE_BUILDING_TIME_THEORY", "code"))
if CH17 not in sys.path:
    sys.path.insert(0, CH17)

import canon                                   # noqa: E402  (also puts the chapter-11 research code on the path)
import timechar as tc                          # noqa: E402

NEG_INF, EPS = canon.NEG_INF, canon.EPS

FAMILIES = [
    ("P01", "資材の製造", ("A13-01", "A13-03", "A13-04"), "initial"),
    ("P02", "設備機器の製造", ("X-01",), "initial"),
    ("P03", "現場への輸送", ("A4-01", "A4-02"), "initial"),
    ("P04", "施工", ("A5-04",), "initial"),
    ("P05", "冷媒の漏洩", ("B1-02",), "flow"),
    ("P06", "冷媒の交換時の損失", ("B1-03",), "event"),
    ("P07", "施設管理のエネルギー", ("B2-01@B2",), "flow"),
    ("P08", "修繕", ("B3-01",), "flow+event"),
    ("P09", "更新", ("B4-02",), "event"),
    ("P10", "大型改修・建替", ("B5-01",), "event"),
    ("P11", "運用エネルギー", ("B6-03", "B2-01@B6"), "flow"),
    ("P12", "水・一般廃棄物", ("B7-04",), "flow"),
    ("P13", "解体", ("C1-01",), "terminal"),
    ("P14", "廃棄物の輸送", ("C2-01",), "terminal"),
    ("P15", "廃棄物の処理", ("C3-01", "X-14"), "terminal"),
    ("P16", "最終処分", ("C4-01",), "terminal"),
    ("P17", "冷媒の廃棄時の放出", ("B1-04",), "terminal"),
]
TERMINAL = {"C1-01", "C2-01", "C3-01", "X-14", "C4-01", "B1-04"}


def family_of(term) -> str:
    key = term.unit
    if term.unit == "B2-01":
        key = "B2-01@" + term.stage
    for pid, name, units, kind in FAMILIES:
        if key in units:
            return pid
    raise KeyError((term.unit, term.stage))


PARENT_TABLE = {"refrigerants.years": "refrigerants", "refrigerants.events": "refrigerants",
                "materials.events": "materials", "equipment.events": "equipment"}
ROW_TABLES = ("refrigerants", "materials", "equipment", "boundary.events")


def instance_of(term, sysm=None) -> str:
    """Instance within the family: the input row (device, material, equipment item, refurbishment event) the term
    comes from (child tables are mapped to their parent row through the engine's _parent column)."""
    src = term.src or ""
    if ":" not in src or "[" not in src:
        return ""
    table = src.split(":")[0]
    row = int(src.split("[")[1].split("]")[0])
    if table in PARENT_TABLE and sysm is not None:
        try:
            par = int(sysm.eng.col(table, "_parent").v[row])
            return "%s#%d" % (PARENT_TABLE[table], par)
        except Exception:
            return "%s#%d" % (table, row)
    if table in ROW_TABLES:
        return "%s#%d" % (table, row)
    return ""


@dataclass
class ProcessFunction:
    """Real-time function of one process (exact Fractions): masses [(time, threshold or None, amount)],
    densities [(start, end, rate)], terminal terms (canonical kernel terms evaluated at T, emitted at t = T)."""
    pid: str
    masses: list = field(default_factory=list)
    densities: list = field(default_factory=list)
    terminal: list = field(default_factory=list)
    units: set = field(default_factory=set)
    n_terms: int = 0

    def emitted_before(self, T: float) -> Fraction:
        """M_i([0, T)): masses whose rule counts at T and densities integrated up to T (exact)."""
        TF = Fraction(T)
        v = Fraction(0)
        for tm, thr, a in self.masses:
            if thr is None or thr <= TF:
                v += a
        for a0, b0, r in self.densities:
            if TF > a0:
                v += r * (min(TF, b0) - a0)
        return v

    def terminal_at(self, T: float) -> Fraction:
        return sum((t.amp * t.h(T) for t in self.terminal), Fraction(0))

    def accounted(self, T: float) -> Fraction:
        """The process's contribution to C(T): realised part + terminal part."""
        return self.emitted_before(T) + self.terminal_at(T)

    def rate(self, t: Fraction) -> Fraction:
        return sum((r for a0, b0, r in self.densities if a0 <= t < b0), Fraction(0))

    def support(self):
        ts = [tm for tm, thr, a in self.masses if a != 0] + [a0 for a0, b0, r in self.densities if r != 0]
        te = [tm for tm, thr, a in self.masses if a != 0] + [b0 for a0, b0, r in self.densities if r != 0]
        if not ts:
            return None
        return (min(ts), max(te))


def decompose(can, sysm=None):
    """Family -> ProcessFunction, and instance key -> ProcessFunction (instances only where the input has rows)."""
    fam = {pid: ProcessFunction(pid) for pid, *_ in FAMILIES}
    inst_map = {}
    no_instance = collections.Counter()
    for t in can.terms:
        pid = family_of(t)
        targets = [fam[pid]]
        ik = instance_of(t, sysm)
        if not ik:
            no_instance[pid] += 1
        if ik:
            key = (pid, ik)
            if key not in inst_map:
                inst_map[key] = ProcessFunction(pid + "/" + ik)
            targets.append(inst_map[key])
        for P in targets:
            P.units.add(t.unit)
            P.n_terms += 1
            if t.unit in TERMINAL:
                P.terminal.append(t)
            elif t.kind == "const":
                P.masses.append((Fraction(0), None, t.amp))
            elif t.kind == "atom":
                P.masses.append((Fraction(t.start), Fraction(tc.tswitch(t.gate)), t.amp))
            elif t.kind in ("cell", "density"):
                s = Fraction(t.start)
                P.densities.append((s, s + Fraction(t.length), t.amp))
            elif t.kind == "gcell":
                s, e, ts = Fraction(t.start), Fraction(t.start) + Fraction(t.length), Fraction(tc.tswitch(t.gate))
                if ts >= e:
                    P.masses.append((Fraction(t.gate), ts, t.amp * (e - s)))
                else:
                    P.masses.append((Fraction(t.gate), ts, t.amp * (ts - s)))
                    P.densities.append((ts, e, t.amp))
            else:
                raise ValueError(t.kind)
    decompose.no_instance = dict(no_instance)          # terms of each family that belong to no input row
    return fam, inst_map


def annual_series(P: ProcessFunction, H: int):
    """Real-time amount emitted in each year [y-1, y), y = 1..H, by the realised part (exact), plus nothing for the
    terminal part (it is placed at t = T, not on the year grid)."""
    out = []
    for y in range(1, H + 1):
        out.append(P.emitted_before(float(y)) - (P.emitted_before(float(y - 1)) if y > 1 else Fraction(0)))
    return out
