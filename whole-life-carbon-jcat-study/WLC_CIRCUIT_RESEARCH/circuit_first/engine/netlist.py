"""Generic netlist: analog elements (MNA) and boolean control elements.

The engine knows nothing about any application domain. Every element may carry a free
`tags` dict (used by callers for bookkeeping/audits only; never read by the solver).
Ground node is "0". Reserved boolean signals: "ONE" (always true), "ZERO" (always false).

Sign conventions
  * Every two-terminal element has terminals (a, b); its current i flows from a to b
    THROUGH the element (enters at a). Absorbed power p = (v_a - v_b) * i.
  * VSource: v_a - v_b = V.  ISource: current I flows a -> b through the source.
  * OpAmp (ideal, nullor): nullator v_inp = v_inn with zero input currents; norator from
    `out` to ground with arbitrary current (current j flows from out through the norator
    to ground).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from typing import Optional

GND = "0"


@dataclass
class Element:
    name: str
    tags: dict = field(default_factory=dict, kw_only=True)

    def nodes(self):
        return []

    kind = "element"


@dataclass
class Resistor(Element):
    a: str
    b: str
    G: object  # conductance (S)
    kind = "R"

    def nodes(self):
        return [self.a, self.b]


@dataclass
class Capacitor(Element):
    a: str
    b: str
    C: object
    v0: object = 0
    kind = "C"

    def nodes(self):
        return [self.a, self.b]


@dataclass
class Inductor(Element):
    a: str
    b: str
    L: object
    i0: object = 0
    kind = "L"

    def nodes(self):
        return [self.a, self.b]


@dataclass
class VSource(Element):
    a: str
    b: str
    V: object
    kind = "V"

    def nodes(self):
        return [self.a, self.b]


@dataclass
class ISource(Element):
    a: str
    b: str
    I: object
    kind = "I"

    def nodes(self):
        return [self.a, self.b]


@dataclass
class VCVS(Element):
    a: str
    b: str
    cp: str
    cn: str
    gain: object
    kind = "E"

    def nodes(self):
        return [self.a, self.b]


@dataclass
class VCCS(Element):
    a: str
    b: str
    cp: str
    cn: str
    gm: object
    kind = "G"

    def nodes(self):
        return [self.a, self.b]


@dataclass
class CCCS(Element):
    a: str
    b: str
    ctrl: str
    gain: object
    kind = "F"

    def nodes(self):
        return [self.a, self.b]


@dataclass
class CCVS(Element):
    a: str
    b: str
    ctrl: str
    r: object
    kind = "H"

    def nodes(self):
        return [self.a, self.b]


@dataclass
class OpAmp(Element):
    inp: str
    inn: str
    out: str
    kind = "OA"

    def nodes(self):
        return [self.inp, self.inn, self.out]


@dataclass
class Switch(Element):
    a: str
    b: str
    ctrl: str            # boolean signal
    invert: bool = False
    kind = "SW"

    def nodes(self):
        return [self.a, self.b]


@dataclass
class Diode(Element):
    a: str  # anode
    b: str  # cathode
    on: bool = False     # initial guess
    kind = "D"

    def nodes(self):
        return [self.a, self.b]


ANALOG_KINDS = (Resistor, Capacitor, Inductor, VSource, ISource, VCVS, VCCS, CCCS, CCVS,
                OpAmp, Switch, Diode)


# ----------------------------------------------------------------- boolean / mixed-signal

@dataclass
class Comparator(Element):
    """out = [v_plus - v_minus >= 0]; transitions are events with the given priority."""
    plus: str
    minus: str
    out: str
    priority: int = 50
    kind = "CMP"


@dataclass
class Gate(Element):
    op: str           # AND, OR, NOT, XOR, BUF, NAND, NOR
    inputs: list
    out: str
    kind = "GATE"


@dataclass
class SRLatch(Element):
    """Rising edge of `set` -> q=1, rising edge of `reset` -> q=0 (reset wins if both)."""
    set: str
    reset: str
    q: str
    init: bool = False
    kind = "SR"


@dataclass
class DFF(Element):
    d: str
    clk: str
    q: str
    init: bool = False
    kind = "DFF"


@dataclass
class Counter(Element):
    """Binary up-counter of `nbits` bits, increments on rising edge of clk; outputs
    signals f"{prefix}{k}" (k = 0 is the least significant bit)."""
    clk: str
    nbits: int
    prefix: str
    kind = "CNT"


@dataclass
class Sequencer(Element):
    """Non-overlapping phase generator: on a rising edge of `trigger`, applies `steps`
    (list of {signal: bool}) one after the other at the same instant (ideal zero-length
    phases). Between activations its outputs hold the `idle` values."""
    trigger: str
    idle: dict
    steps: list
    kind = "SEQ"


@dataclass
class PowerOn(Element):
    """Signal that rises once at the start time with the given priority."""
    out: str
    priority: int = 5
    kind = "POR"


DIGITAL_KINDS = (Comparator, Gate, SRLatch, DFF, Counter, Sequencer, PowerOn)


def _num(x):
    if isinstance(x, Fraction):
        return f"{x.numerator}/{x.denominator}" if x.denominator != 1 else str(x.numerator)
    return x


class Netlist:
    def __init__(self):
        self.elements: list[Element] = []
        self.by_name: dict[str, Element] = {}

    def add(self, el: Element) -> Element:
        if el.name in self.by_name:
            raise ValueError(f"duplicate element name {el.name}")
        self.elements.append(el)
        self.by_name[el.name] = el
        return el

    # convenience constructors -------------------------------------------------
    def R(self, name, a, b, R=None, G=None, **tags):
        if G is None:
            G = 1 / R if not isinstance(R, int) else Fraction(1, R)
        return self.add(Resistor(name, a, b, G, tags=tags))

    def C(self, name, a, b, C, v0=0, **tags):
        return self.add(Capacitor(name, a, b, C, v0, tags=tags))

    def L(self, name, a, b, L, i0=0, **tags):
        return self.add(Inductor(name, a, b, L, i0, tags=tags))

    def V(self, name, a, b, V, **tags):
        return self.add(VSource(name, a, b, V, tags=tags))

    def I(self, name, a, b, I, **tags):
        return self.add(ISource(name, a, b, I, tags=tags))

    def opamp(self, name, inp, inn, out, **tags):
        return self.add(OpAmp(name, inp, inn, out, tags=tags))

    def switch(self, name, a, b, ctrl, invert=False, **tags):
        return self.add(Switch(name, a, b, ctrl, invert, tags=tags))

    def diode(self, name, a, b, on=False, **tags):
        return self.add(Diode(name, a, b, on, tags=tags))

    def pot(self, name, top, wiper, bottom, R0, w, **tags):
        """Potentiometer: R(top-wiper) = w*R0, R(wiper-bottom) = (1-w)*R0."""
        self.R(name + ".t", top, wiper, R=w * R0, **tags)
        self.R(name + ".b", wiper, bottom, R=(1 - w) * R0, **tags)

    def comparator(self, name, plus, minus, out, priority=50, **tags):
        return self.add(Comparator(name, plus, minus, out, priority, tags=tags))

    def gate(self, name, op, inputs, out, **tags):
        return self.add(Gate(name, op, list(inputs), out, tags=tags))

    def latch(self, name, set, reset, q, init=False, **tags):
        return self.add(SRLatch(name, set, reset, q, init, tags=tags))

    def dff(self, name, d, clk, q, init=False, **tags):
        return self.add(DFF(name, d, clk, q, init, tags=tags))

    def counter(self, name, clk, nbits, prefix, **tags):
        return self.add(Counter(name, clk, nbits, prefix, tags=tags))

    def sequencer(self, name, trigger, idle, steps, **tags):
        return self.add(Sequencer(name, trigger, dict(idle), [dict(s) for s in steps], tags=tags))

    def power_on(self, name, out, priority=5, **tags):
        return self.add(PowerOn(name, out, priority, tags=tags))

    # queries -----------------------------------------------------------------
    def analog(self):
        return [e for e in self.elements if isinstance(e, ANALOG_KINDS)]

    def digital(self):
        return [e for e in self.elements if isinstance(e, DIGITAL_KINDS)]

    def nodes(self):
        out = []
        seen = set()
        for e in self.analog():
            for n in e.nodes():
                if n != GND and n not in seen:
                    seen.add(n)
                    out.append(n)
        for e in self.digital():
            if isinstance(e, Comparator):
                for n in (e.plus, e.minus):
                    if n != GND and n not in seen:
                        seen.add(n)
                        out.append(n)
        return out

    def states(self):
        return [e for e in self.elements if isinstance(e, (Capacitor, Inductor))]

    def to_json(self):
        out = []
        for e in self.elements:
            d = {"name": e.name, "kind": e.kind}
            for k, v in e.__dict__.items():
                if k in ("name", "tags"):
                    continue
                if isinstance(v, dict):
                    v = {kk: _num(vv) for kk, vv in v.items()}
                elif isinstance(v, list):
                    v = [({kk: _num(vv) for kk, vv in x.items()} if isinstance(x, dict) else _num(x)) for x in v]
                else:
                    v = _num(v)
                d[k] = v
            if e.tags:
                d["tags"] = {k: _num(v) for k, v in e.tags.items()}
            out.append(d)
        return out
