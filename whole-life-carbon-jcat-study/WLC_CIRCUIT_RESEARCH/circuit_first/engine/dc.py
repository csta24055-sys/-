"""Static (DC operating point) solution of a large resistive / controlled-source network.

Sparse MNA (KCL per node + branch equations), solved exactly with Fractions by
elimination in dependency order: an equation with a single unknown left is solved and
substituted (this resolves feed-forward chains of op-amp amplifiers, summing nodes and rail
currents); whatever remains (genuine loops) is solved densely. Capacitors are open circuits,
inductors short circuits are not supported (static networks only). Application-agnostic.
"""
from __future__ import annotations

from fractions import Fraction

from . import linalg as la
from .netlist import (GND, CCCS, CCVS, VCCS, VCVS, Capacitor, Diode, Inductor, ISource,
                      OpAmp, Resistor, Switch, VSource)


class DCError(RuntimeError):
    pass


def solve_dc(netlist, closed=None, exact=True):
    """Return (voltages {node: v}, currents {element: i}). `closed`: names of closed switches
    (default: switches whose ctrl is the constant signal "ONE")."""
    els = netlist.analog()
    if closed is None:
        closed = {e.name for e in els if isinstance(e, Switch) and (e.ctrl == "ONE") != e.invert}
    for e in els:
        if isinstance(e, (Inductor, Diode)):
            raise DCError(f"{e.kind} not supported in the static solver ({e.name})")
    eqs = []          # list of [dict col -> coef, const]  meaning sum coef*x = const
    kcl_row = {}

    def eq():
        eqs.append([{}, Fraction(0)])
        return len(eqs) - 1

    def add(r, col, c):
        if col is None or c == 0:
            return
        d = eqs[r][0]
        v = d.get(col, 0) + c
        if v == 0:
            d.pop(col, None)
        else:
            d[col] = v

    def V(n):
        return None if n == GND else ("v", n)

    def kcl(n):
        if n == GND:
            return None
        if n not in kcl_row:
            kcl_row[n] = eq()
        return kcl_row[n]

    for e in els:
        for n in e.nodes():
            kcl(n)
    for e in els:
        if isinstance(e, Resistor):
            for p, q in ((e.a, e.b), (e.b, e.a)):
                r = kcl(p)
                if r is not None:
                    add(r, V(p), e.G)
                    add(r, V(q), -e.G)
        elif isinstance(e, ISource):
            if e.a != GND:
                eqs[kcl(e.a)][1] -= e.I
            if e.b != GND:
                eqs[kcl(e.b)][1] += e.I
        elif isinstance(e, VCCS):
            for node, sg in ((e.a, 1), (e.b, -1)):
                r = kcl(node)
                if r is not None:
                    add(r, V(e.cp), sg * e.gm)
                    add(r, V(e.cn), -sg * e.gm)
        elif isinstance(e, CCCS):
            for node, sg in ((e.a, 1), (e.b, -1)):
                r = kcl(node)
                if r is not None:
                    add(r, ("j", e.ctrl), sg * e.gain)
        elif isinstance(e, Capacitor):
            continue
        elif isinstance(e, Switch) and e.name not in closed:
            continue
        elif isinstance(e, OpAmp):
            j = ("j", e.name)
            r = kcl(e.out)
            if r is not None:
                add(r, j, Fraction(1))
            r = eq()
            add(r, V(e.inp), Fraction(1))
            add(r, V(e.inn), Fraction(-1))
        elif isinstance(e, (VSource, Switch, VCVS, CCVS)):
            j = ("j", e.name)
            for node, sg in ((e.a, 1), (e.b, -1)):
                r = kcl(node)
                if r is not None:
                    add(r, j, Fraction(sg))
            r = eq()
            add(r, V(e.a), Fraction(1))
            add(r, V(e.b), Fraction(-1))
            if isinstance(e, VSource):
                eqs[r][1] += e.V
            elif isinstance(e, VCVS):
                add(r, V(e.cp), -e.gain)
                add(r, V(e.cn), e.gain)
            elif isinstance(e, CCVS):
                add(r, ("j", e.ctrl), -e.r)
    # ---- elimination in dependency order
    col_eqs = {}
    for i, (d, _) in enumerate(eqs):
        for c in d:
            col_eqs.setdefault(c, set()).add(i)
    val = {}
    alive = set(range(len(eqs)))
    stack = [i for i in alive if len(eqs[i][0]) == 1]
    steps = 0
    while stack:
        i = stack.pop()
        if i not in alive or len(eqs[i][0]) != 1:
            continue
        (c, coef), = eqs[i][0].items()
        x = eqs[i][1] / coef
        val[c] = x
        alive.discard(i)
        steps += 1
        for k in col_eqs.pop(c, ()):
            if k == i or k not in alive:
                continue
            d = eqs[k][0]
            eqs[k][1] -= d.pop(c) * x
            if len(d) == 1:
                stack.append(k)
            elif len(d) == 0:
                alive.discard(k)
                if eqs[k][1] != 0:
                    raise DCError("inconsistent static network")
    rest_cols = sorted({c for i in alive for c in eqs[i][0]}, key=str)
    dense = 0
    if rest_cols:
        rows = sorted(alive)
        if len(rest_cols) > 400:
            raise DCError(f"remaining coupled block too large ({len(rest_cols)})")
        idx = {c: k for k, c in enumerate(rest_cols)}
        M = [[Fraction(0)] * len(rest_cols) for _ in rows]
        y = []
        for r, i in enumerate(rows):
            for c, v in eqs[i][0].items():
                M[r][idx[c]] = v
            y.append(eqs[i][1])
        sol = la.GeneralSolver(M, len(rest_cols), True)
        if sol.right_null:
            raise DCError("static network has undetermined unknowns")
        z = sol.particular(y)
        for c, x in zip(rest_cols, z):
            val[c] = x
        dense = len(rest_cols)
    volts = {n: val.get(("v", n), Fraction(0)) for n in kcl_row}
    volts[GND] = Fraction(0)
    cur = {}
    for e in els:
        if isinstance(e, Resistor):
            cur[e.name] = e.G * (volts[e.a] - volts[e.b])
        elif isinstance(e, ISource):
            cur[e.name] = e.I
        elif isinstance(e, VCCS):
            cur[e.name] = e.gm * (volts[e.cp] - volts[e.cn])
        elif isinstance(e, Capacitor) or (isinstance(e, Switch) and e.name not in closed):
            cur[e.name] = Fraction(0)
        elif ("j", e.name) in val:
            cur[e.name] = val[("j", e.name)]
    for e in els:
        if isinstance(e, CCCS):
            cur[e.name] = e.gain * cur.get(e.ctrl, 0)
    info = {"equations": len(eqs), "peeled": steps, "dense_block": dense}
    return volts, cur, info


def kcl_residual(netlist, volts, cur):
    """Max |sum of currents| over nodes, recomputed from the solution only."""
    acc = {}
    for e in netlist.analog():
        if e.name not in cur:
            continue
        i = cur[e.name]
        if isinstance(e, OpAmp):
            terms = [(e.out, 1)]
        else:
            terms = [(e.a, 1), (e.b, -1)]
        for n, sg in terms:
            if n != GND:
                acc[n] = acc.get(n, 0) + sg * i
    return max((abs(v) for v in acc.values()), default=0)
