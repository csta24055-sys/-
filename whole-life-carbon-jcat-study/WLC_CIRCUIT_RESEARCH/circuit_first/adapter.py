"""Netlist generator (adapter): primitive inputs -> element values and wiring.

Allowed operations (architecture section 4):
  W1  element value = primitive input x building-independent unit constant
  W2  key matching -> wiring (equal keys share a cell); returns no number
  W3  single-input validity predicate -> branch present / absent
  W4  enumeration: one cell per input row / list element
Every arithmetic operation on a data value goes through `Tracked`, which counts it. Any
operation that is not a single W1 product on a primitive is counted as GREY and itemised.

The adapter never computes event times, event counts, years, amplitudes x counts, or any
WLC result. It does not import any reference/oracle code.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction

from engine import Netlist

# ----------------------------------------------------------------- operation counting


class OpLedger:
    def __init__(self):
        self.counts = {"W1": 0, "W2": 0, "W3": 0, "W4": 0, "GREY": 0}
        self.grey_items = []
        self.data_elements = 0       # elements/sources whose value is data (W_in part 1)

    def note(self, kind, what=""):
        self.counts[kind] += 1
        if kind == "GREY":
            self.grey_items.append(what)


class Tracked:
    """A data value. Arithmetic with a plain (building-independent) constant on a primitive
    is W1; everything else is GREY. Comparisons are only available through W2/W3 helpers."""
    __slots__ = ("value", "kind", "label", "ledger")

    def __init__(self, value, label, ledger, kind="primitive"):
        self.value = Fraction(value)
        self.kind = kind
        self.label = label
        self.ledger = ledger

    def _bin(self, other, op, rev=False):
        if isinstance(other, Tracked):
            self.ledger.note("GREY", f"{self.label} {op} {other.label}")
            ov = other.value
            kind = "derived"
        else:
            ov = Fraction(other)
            if self.kind == "primitive" and op in ("*", "/") and not rev:
                self.ledger.note("W1", f"{self.label} {op} const")
                kind = "element"
            elif self.kind == "primitive" and op == "*" and rev:
                self.ledger.note("W1", f"const * {self.label}")
                kind = "element"
            else:
                self.ledger.note("GREY", f"{self.label}[{self.kind}] {op} const")
                kind = "derived"
        a, b = (ov, self.value) if rev else (self.value, ov)
        v = {"*": lambda: a * b, "/": lambda: a / b, "+": lambda: a + b, "-": lambda: a - b}[op]()
        return Tracked(v, f"({self.label}{op})", self.ledger, kind)

    def __mul__(self, o):
        return self._bin(o, "*")

    def __rmul__(self, o):
        return self._bin(o, "*", rev=True)

    def __truediv__(self, o):
        return self._bin(o, "/")

    def __add__(self, o):
        return self._bin(o, "+")

    def __radd__(self, o):
        return self._bin(o, "+", rev=True)

    def __sub__(self, o):
        return self._bin(o, "-")

    def __rsub__(self, o):
        return self._bin(o, "-", rev=True)

    def __float__(self):
        raise TypeError("raw extraction of a tracked value is not allowed")

    def __bool__(self):
        raise TypeError("truth value of a tracked value is not allowed (use W3 predicates)")

    def __lt__(self, o):
        raise TypeError("ordering of tracked values is not allowed")

    __le__ = __gt__ = __ge__ = __lt__


def w3_positive(x: "Tracked | None") -> bool:
    """W3: single-input validity predicate (present, finite, > 0)."""
    if x is None:
        return False
    x.ledger.note("W3", f"positive({x.label})")
    return x.value > 0


def w3_nonneg(x):
    if x is None:
        return False
    x.ledger.note("W3", f"nonneg({x.label})")
    return x.value >= 0


def w2_key(ledger, *parts):
    """W2: build a hashable matching key from primitive values (no number is returned to
    the netlist; the key only decides which inputs share one cell)."""
    ledger.note("W2", "key")
    out = []
    for p in parts:
        if isinstance(p, Tracked):
            out.append(("v", p.value))
        elif isinstance(p, (list, tuple, frozenset, set)):
            out.append(("s", frozenset((q.value if isinstance(q, Tracked) else q) for q in p)))
        else:
            out.append(("o", p))
    return tuple(out)


# ----------------------------------------------------------------- units / conventions


@dataclass(frozen=True)
class Units:
    gamma: Fraction = Fraction(1)     # kgCO2e per coulomb (defined simulation scaling)
    V0: Fraction = Fraction(1)        # rail voltage
    tau_y: Fraction = Fraction(1)     # simulated seconds per year
    Gu: Fraction = Fraction(1)        # unit conductance (siemens per kg-equivalent)


CONVENTIONS = {
    # name: (epsilon, readout priority)
    "right": (Fraction(0), 100),
    "left": (Fraction(0), 0),
    "original": (Fraction(1, 10 ** 9), 0),
}

PRIO = {"por": 5, "early": 10, "tick": 20, "fire": 30}
PH = [("trk", False), ("dmp", True), ("dmp", False), ("trk", True)]


def _wrap(ledger, x, label):
    if x is None:
        return None
    return Tracked(Fraction(str(x)) if isinstance(x, float) else Fraction(x), label, ledger)


# ----------------------------------------------------------------- builder


class Builder:
    def __init__(self, units: Units, eps: Fraction, ledger: OpLedger, mutations=()):
        self.u = units
        self.eps = eps
        self.L = ledger
        self.mut = set(mutations)
        self.nl = Netlist()
        self.taps = {}            # stage -> list of capacitor names whose charge is read out
        self.datapath = set()     # element names on the data path (Joule audit)
        self.cells = []           # (cell_type, instance, ports dict)
        self._prio_shift = 0

    # values -------------------------------------------------------------
    def val(self, x):
        """Element value from a tracked data value (counted as a data element)."""
        if isinstance(x, Tracked):
            self.L.data_elements += 1
            return x.value
        return Fraction(x)

    def cell(self, ctype, inst, **ports):
        self.cells.append((ctype, inst, ports))

    # primitives -----------------------------------------------------------
    def rails(self):
        u, nl = self.u, self.nl
        nl.V("rail.V0", "rail", "0", u.V0, cell="rails")
        nl.V("rail.Vn", "railn", "0", -u.V0, cell="rails")
        nl.V("rail.Vth", "vth", "0", u.V0, cell="rails")
        nl.V("rail.Vhi", "vhi", "0", 256 * u.V0, cell="rails")     # above the global ramp (H < 256)
        self.cell("rails", "rails")

    def integrator(self, tag, C, cell, **kw):
        x, o = f"{tag}.x", f"{tag}.o"
        self.nl.opamp(f"{tag}.A", "0", x, o, cell=cell, **kw)
        self.nl.C(f"{tag}.C", x, o, C, cell=cell, **kw)
        return x, o

    def packet(self, tag, Cs, src, dst_x, trig, polarity=+1, v0=None, cell="packet", datapath=True, **kw):
        """SC packet: Cs tracks `src` (plate b grounded) and dumps into virtual ground dst_x.
        polarity -1 swaps the plates at dump time (charge -Cs*v_src)."""
        nl = self.nl
        a, b = f"{tag}.a", f"{tag}.b"
        trk, dmp = f"{tag}.trk", f"{tag}.dmp"
        nl.C(f"{tag}.Cs", a, "0" if polarity > 0 else b, Cs, v0=(v0 if v0 is not None else 0), cell=cell, **kw)
        nl.switch(f"{tag}.St", a, src, trk, cell=cell, **kw)
        if polarity > 0:
            nl.switch(f"{tag}.Sd", a, dst_x, dmp, cell=cell, **kw)
            names = [f"{tag}.St", f"{tag}.Sd"]
        else:
            nl.switch(f"{tag}.Sbg", b, "0", trk, cell=cell, **kw)
            nl.switch(f"{tag}.Sag", a, "0", dmp, cell=cell, **kw)
            nl.switch(f"{tag}.Sbx", b, dst_x, dmp, cell=cell, **kw)
            names = [f"{tag}.St", f"{tag}.Sbg", f"{tag}.Sag", f"{tag}.Sbx"]
        nl.sequencer(f"{tag}.seq", trig, {trk: True, dmp: False},
                     [{(trk if k == "trk" else dmp): v} for k, v in PH], cell=cell, **kw)
        if datapath:
            self.datapath.update(names)
        return f"{tag}.Cs"

    def short(self, tag, a, b, trig, cell, **kw):
        sig = f"{tag}.sh"
        self.nl.switch(f"{tag}.Ssh", a, b, sig, cell=cell, **kw)
        self.nl.sequencer(f"{tag}.shseq", trig, {sig: False},
                          [{}, {sig: True}, {sig: False}, {}], cell=cell, **kw)

    def bus(self, stage):
        tag = f"bus.{stage}"
        if stage not in self.taps:
            self.integrator(tag, Fraction(1), "bus", stage=stage)
            self.taps[stage] = [f"{tag}.C"]
            self.cell("bus", stage)
        return f"{tag}.x"

    def timebase(self):
        u, nl, eps = self.u, self.nl, self.eps
        # year ramp: exactly one year per V_th, reset by a V_th*C_y packet; tick comparator
        Cy = u.Gu * u.tau_y
        x, o = self.integrator("tb.y", Cy, "timebase")
        nl.R("tb.y.G", "railn", x, G=u.Gu, cell="timebase")
        nl.comparator("tb.y.cmp", o, "vth", "tick", priority=PRIO["tick"], cell="timebase")
        self.packet("tb.y.rst", Cy, "vth", x, "tick", v0=u.V0, cell="timebase", datapath=False)
        nl.counter("tb.cnt", "tick", 8, "yr", cell="timebase")
        # global ramp (never reset): v = (1-eps) V0 t / tau_y, for explicit event comparators
        g = u.Gu if "clock_slope_one" in self.mut else u.Gu * (1 - eps)
        xg, og = self.integrator("tb.g", u.Gu * u.tau_y, "timebase")
        nl.R("tb.g.G", "railn", xg, G=g, cell="timebase")
        # lookahead comparator (shared by all event groups): P = [v_yearramp <= rho * v_global]
        # with rho = eps(2-eps)/(1-eps): at a late firing t_f = tau/(1-eps), P = 1 iff the
        # last tick K satisfies K >= tau(1-eps), i.e. the event belongs to the closed year K.
        rho = eps * (2 - eps) / (1 - eps)
        if rho == 0:
            pref = "0"
        else:
            pref = "tb.pref"
            nl.pot("tb.div", og, pref, "0", Fraction(1), 1 - rho, cell="timebase")
        if "lookahead_strict" in self.mut:
            nl.comparator("tb.P", o, pref, "Pn", priority=PRIO["early"], cell="timebase")
            nl.gate("tb.Pinv", "NOT", ["Pn"], "P", cell="timebase")
        else:
            nl.comparator("tb.P", pref, o, "P", priority=PRIO["early"], cell="timebase")
        self.cell("timebase", "timebase")
        return og

    def fire_prio(self):
        if "sequential_simultaneous" in self.mut:
            self._prio_shift += 1            # later-built sources are processed first
            return PRIO["fire"] + 50 - self._prio_shift
        return PRIO["fire"]

    def clock(self, tag, period: Tracked, restart_trig=None):
        """Integrate-and-fire clock. C_j = period * Gu * tau_y (W1); ramp slope (1-eps)."""
        u, nl, eps = self.u, self.nl, self.eps
        Cj = self.val(period * (u.Gu * u.tau_y))
        x, o = self.integrator(tag, Cj, "clock")
        g = u.Gu if "clock_slope_one" in self.mut else u.Gu * (1 - eps)
        nl.R(f"{tag}.G", "railn", x, G=g, cell="clock")
        nl.comparator(f"{tag}.late", o, "vth", f"{tag}.fire", priority=self.fire_prio(), cell="clock")
        Cr = self.val(period * (u.Gu * u.tau_y))
        self.packet(f"{tag}.rst", Cr, "vth", x, f"{tag}.fire", v0=u.V0, cell="clock", datapath=False)
        if restart_trig:
            self.short(f"{tag}.restart", x, o, restart_trig, cell="clock")
        self.cell("clock", tag, src="railn", out="group", reset="packet")
        return f"{tag}.fire"

    def explicit(self, tag, year: Tracked, gramp):
        """Explicit event at `year`: comparator of the global ramp against a data reference.
        After firing, its own phase generator moves the comparator input from the reference
        to a high rail (disarm), so the comparator falls in the same batch as clock fires."""
        u, nl = self.u, self.nl
        m = f"{tag}.m"
        nl.V(f"{tag}.Vl", f"{tag}.rl", "0", self.val(year * u.V0), cell="explicit")
        nl.switch(f"{tag}.Sarm", f"{tag}.rl", m, f"{tag}.dis", invert=True, cell="explicit")
        nl.switch(f"{tag}.Sdis", "vhi", m, f"{tag}.dis", cell="explicit")
        nl.comparator(f"{tag}.late", gramp, m, f"{tag}.fire", priority=self.fire_prio(), cell="explicit")
        nl.sequencer(f"{tag}.seq", f"{tag}.fire", {f"{tag}.dp": False},
                     [{}, {f"{tag}.dp": True}, {f"{tag}.dp": False}, {}], cell="explicit")
        nl.latch(f"{tag}.done", f"{tag}.dp", "ZERO", f"{tag}.dis", cell="explicit")
        self.cell("explicit", tag, src="global_ramp", out="group")
        return f"{tag}.fire"

    def OR(self, name, ins):
        ins = list(ins)
        if not ins:
            return "ZERO"
        if len(ins) == 1:
            return ins[0]
        self.nl.gate(name, "OR", ins, name, cell="logic")
        return name


# ----------------------------------------------------------------- scenario -> netlist


@dataclass
class Built:
    netlist: Netlist
    taps: dict
    datapath: set
    cells: list
    ledger: OpLedger
    stages: list
    group_signals: dict = field(default_factory=dict)
    item_seq: dict = field(default_factory=dict)


def build(scn: dict, units: Units = Units(), convention: str = "right", mutations=()) -> Built:
    eps, _ = CONVENTIONS[convention]
    L = OpLedger()
    B = Builder(units, eps, L, mutations)
    u = units
    B.rails()
    gramp = B.timebase()

    # ---- initial (t = 0) amounts: packet from the rail at power-on
    B.nl.power_on("por", "por", priority=PRIO["por"])
    for row in scn.get("initial", []):
        L.note("W4", "initial row")
        A = _wrap(L, row["amount"], f"init[{row['id']}].amount")
        if not w3_positive(A):
            continue
        x = B.bus(row["stage"])
        B.packet(f"pk.init.{row['id']}", B.val(A / (u.gamma * u.V0)), "rail", x, "por", v0=u.V0)
        B.cell("packet", f"init.{row['id']}", src="rail", dst="bus", trig="por")

    # ---- renovation comparators (explicit years), their own packets
    reno_fire = {}      # renovation id -> fire signal
    for rv in scn.get("renovations", []):
        L.note("W4", "renovation row")
        fires = []
        for k, yr in enumerate(rv.get("years", [])):
            L.note("W4", "renovation year")
            Y = _wrap(L, yr, f"reno[{rv['id']}].year[{k}]")
            if not w3_positive(Y):
                continue
            fires.append(B.explicit(f"rv.{rv['id']}.{k}", Y, gramp))
        rf = B.OR(f"rv.{rv['id']}.fire", fires)
        reno_fire[rv["id"]] = rf
        A = _wrap(L, rv.get("amount"), f"reno[{rv['id']}].amount")
        if w3_positive(A):
            B.packet(f"pk.rv.{rv['id']}", B.val(A / (u.gamma * u.V0)), "rail", B.bus(rv["stage"]), rf, v0=u.V0)
            B.cell("packet", f"rv.{rv['id']}", src="rail", dst="bus", trig="explicit")

    # ---- items grouped by W2 key into shared clocks / event groups
    groups = {}
    order = []
    for it in scn.get("items", []):
        L.note("W4", "item row")
        P = _wrap(L, it.get("period"), f"item[{it['id']}].period")
        ex = [_wrap(L, y, f"item[{it['id']}].explicit") for y in it.get("explicit", [])]
        subs = sorted(rv["id"] for rv in scn.get("renovations", [])
                      if rv.get("policy") == "substituted" and it["id"] in rv.get("replaces", []))
        key = w2_key(L, P if w3_positive(P) else None, ex, it.get("explicit_policy", "restart"), tuple(subs))
        if key not in groups:
            groups[key] = {"period": P if w3_positive(P) else None, "explicit": ex,
                           "policy": it.get("explicit_policy", "restart"), "subs": subs, "items": []}
            order.append(key)
        groups[key]["items"].append(it)

    group_signals = {}
    item_seq = {}
    for gi, key in enumerate(order):
        g = groups[key]
        gt = f"g{gi}"
        # explicit replacement comparators of this group
        efires = []
        for k, Y in enumerate(g["explicit"]):
            if not w3_positive(Y):
                continue
            efires.append(B.explicit(f"{gt}.x{k}", Y, gramp))
        sub_fires = [reno_fire[r] for r in g["subs"]]
        restart = []
        if g["policy"] == "restart":
            restart += efires
        restart += sub_fires
        restart_sig = B.OR(f"{gt}.restart", restart) if restart else None
        cfires = []
        if g["period"] is not None:
            cfires.append(B.clock(f"{gt}.clk", g["period"], restart_sig))
        ev = B.OR(f"{gt}.ev", cfires + efires)                 # own replacement events
        sub_any = B.OR(f"{gt}.sub", sub_fires)
        if sub_fires:
            B.nl.gate(f"{gt}.nsub", "NOT", [sub_any], f"{gt}.nsub", cell="logic")
            B.nl.gate(f"{gt}.pk", "AND", [ev, f"{gt}.nsub"], f"{gt}.pk", cell="logic")
            pk = f"{gt}.pk"
        else:
            pk = ev
        replaced = B.OR(f"{gt}.repl", [ev] + sub_fires)        # item renewed (own or renovation)
        group_signals[gt] = {"fire": replaced, "items": [it["id"] for it in g["items"]]}
        # per-item packets (W4: one per row)
        repair_rows = []
        for it in g["items"]:
            A = _wrap(L, it.get("amount"), f"item[{it['id']}].amount")
            if w3_positive(A):
                B.packet(f"pk.it.{it['id']}", B.val(A / (u.gamma * u.V0)), "rail", B.bus(it["stage"]), pk, v0=u.V0)
                B.cell("packet", f"it.{it['id']}", src="rail", dst="bus", trig="group")
                item_seq[it["id"]] = f"pk.it.{it['id']}.seq"
            if it.get("repair"):
                repair_rows.append(it)
        if repair_rows:
            _repair_group(B, gt, repair_rows, replaced)
        group_signals[gt]["replaced"] = replaced

    # ---- continuous flows (W4: one per row)
    item_group = {}
    for gt, gs in group_signals.items():
        for iid in gs["items"]:
            item_group[iid] = gt
    for fl in scn.get("flows", []):
        L.note("W4", "flow row")
        x = B.bus(fl["stage"])
        r = _wrap(L, fl.get("rate"), f"flow[{fl['id']}].rate")
        if fl.get("switch_on"):                      # efficiency change after a replacement
            L.note("W2", "flow->item")
            gt = item_group[fl["switch_on"]]
            lat = f"fl.{fl['id']}.after"
            B.nl.latch(f"fl.{fl['id']}.lat", group_signals[gt]["replaced"], "ZERO", lat, cell="flow")
            r2 = _wrap(L, fl.get("rate_after"), f"flow[{fl['id']}].rate_after")
            for nm, rate, inv in (("b", r, True), ("a", r2, False)):
                if not w3_nonneg(rate):
                    continue
                B.nl.R(f"fl.{fl['id']}.{nm}.G", "rail", f"fl.{fl['id']}.{nm}.n",
                       G=B.val(rate / (u.gamma * u.tau_y * u.V0)), cell="flow")
                B.nl.switch(f"fl.{fl['id']}.{nm}.S", f"fl.{fl['id']}.{nm}.n", x, lat, invert=inv, cell="flow")
                B.datapath.update({f"fl.{fl['id']}.{nm}.G", f"fl.{fl['id']}.{nm}.S"})
            B.cell("flow", fl["id"], src="rail", dst="bus", ctrl="latch")
        elif w3_nonneg(r):
            B.nl.R(f"fl.{fl['id']}.G", "rail", x, G=B.val(r / (u.gamma * u.tau_y * u.V0)), cell="flow")
            B.datapath.add(f"fl.{fl['id']}.G")
            B.cell("flow", fl["id"], src="rail", dst="bus")
        if fl.get("degradation"):                    # rate grows with age since replacement
            d = fl["degradation"]
            L.note("W2", "degradation->item")
            gt = item_group[d["item"]]
            slope = _wrap(L, d["slope"], f"flow[{fl['id']}].slope")
            tag = f"age.{fl['id']}"
            xa, oa = B.integrator(tag, u.Gu * u.tau_y, "age")
            B.nl.R(f"{tag}.G", "railn", xa, G=u.Gu, cell="age")
            if "age_not_reset" not in B.mut:
                B.short(f"{tag}.rst", xa, oa, group_signals[gt]["replaced"], cell="age")
            B.nl.R(f"fl.{fl['id']}.deg.G", oa, x, G=B.val(slope / (u.gamma * u.tau_y * u.V0)), cell="flow")
            B.datapath.add(f"fl.{fl['id']}.deg.G")
            B.cell("age", tag, src="railn", reset="group")
            B.cell("flow", fl["id"] + ".deg", src="age", dst="bus")
    return Built(B.nl, B.taps, B.datapath, B.cells, L, sorted(B.taps), group_signals, item_seq)


def _repair_group(B: Builder, gt, rows, fire):
    """Repair flows of one event group with the year-exclusion rule (per group, not per row).

    Amplitude: rail -G(e0)-> inverter -G(r)-> group summer N_A (v = V0 * sum e0 r).
    Year cell: N_A -G_h-> gate -> hold integrator with flying capacitor C_h; committed to the
    stage bus at every year tick. P=0 event (same year): discard C_h, stop flow till tick.
    P=1 event (belongs to the year that just closed): negative packet of one year's flow.
    """
    u, nl, L = B.u, B.nl, B.L
    stage = rows[0]["repair"]["stage"]
    bx = B.bus(stage)
    xs, NA = f"{gt}.rp.sum.x", f"{gt}.rp.NA"
    nl.opamp(f"{gt}.rp.sum.A", "0", xs, NA, cell="repair_amp")
    nl.R(f"{gt}.rp.sum.Rf", xs, NA, G=u.Gu, cell="repair_amp")
    for it in rows:
        e0 = _wrap(L, it["repair"]["base"], f"item[{it['id']}].repair.base")
        r = _wrap(L, it["repair"]["rate"], f"item[{it['id']}].repair.rate")
        if not (w3_nonneg(e0) and w3_nonneg(r)):
            continue
        x1, o1 = f"{gt}.rp.{it['id']}.x", f"{gt}.rp.{it['id']}.o"
        nl.R(f"{gt}.rp.{it['id']}.Ge", "rail", x1, G=B.val(e0 * u.Gu), cell="repair_amp")
        nl.opamp(f"{gt}.rp.{it['id']}.A", "0", x1, o1, cell="repair_amp")
        nl.R(f"{gt}.rp.{it['id']}.Rf", x1, o1, G=u.Gu, cell="repair_amp")
        nl.R(f"{gt}.rp.{it['id']}.Gr", o1, xs, G=B.val(r * u.Gu), cell="repair_amp")
        B.cell("repair_amp", f"{gt}.{it['id']}", src="rail", dst="group_summer")
    # hold (year) cell
    tag = f"{gt}.yc"
    xh, oh, p, n = f"{tag}.x", f"{tag}.o", f"{tag}.p", f"{tag}.n"
    nl.R(f"{tag}.Gh", NA, f"{tag}.g", G=1 / (u.gamma * u.tau_y * u.V0), cell="yearcell")
    nl.switch(f"{tag}.Sg", f"{tag}.g", xh, f"{tag}.gate", cell="yearcell")
    B.datapath.add(f"{tag}.Gh")
    nl.opamp(f"{tag}.A", "0", xh, oh, cell="yearcell")
    nl.C(f"{tag}.Ch", p, n, Fraction(1), cell="yearcell", stage=stage)
    nl.switch(f"{tag}.Sfp", p, xh, f"{tag}.fb", cell="yearcell")
    nl.switch(f"{tag}.Sfn", n, oh, f"{tag}.fb", cell="yearcell")
    nl.switch(f"{tag}.Scp", p, bx, f"{tag}.cm", cell="yearcell")
    nl.switch(f"{tag}.Scn", n, "0", f"{tag}.cm", cell="yearcell")
    nl.switch(f"{tag}.Ssh", p, n, f"{tag}.sh", cell="yearcell")
    B.taps[stage].append(f"{tag}.Ch")
    # control (booleans only)
    nl.sequencer(f"{tag}.commit", "tick", {f"{tag}.hold": False, f"{tag}.fb": True, f"{tag}.cm": False},
                 [{f"{tag}.hold": True}, {f"{tag}.fb": False}, {f"{tag}.cm": True}, {f"{tag}.cm": False},
                  {f"{tag}.fb": True}, {f"{tag}.hold": False}], cell="yearcell")
    # P (shared lookahead comparator level): the event belongs to the year that just closed
    P = "ZERO" if "no_lookahead" in B.mut else "P"
    nl.gate(f"{tag}.nP", "NOT", [P], f"{tag}.nP", cell="yearcell")
    nl.gate(f"{tag}.f0", "AND", [fire, f"{tag}.nP"], f"{tag}.fireP0", cell="yearcell")
    nl.gate(f"{tag}.f1", "AND", [fire, P], f"{tag}.fireP1", cell="yearcell")
    # S: current year already excluded; S': closed year already excluded
    nl.latch(f"{tag}.Sl", f"{tag}.fireP0", "tick", f"{tag}.S", cell="yearcell")
    nl.dff(f"{tag}.Sd", f"{tag}.S", "tick", f"{tag}.Sa", cell="yearcell")
    nl.latch(f"{tag}.Sbl", f"{tag}.neg", "tick", f"{tag}.Sb", cell="yearcell")
    nl.gate(f"{tag}.Sp", "OR", [f"{tag}.Sa", f"{tag}.Sb"], f"{tag}.Sprime", cell="yearcell")
    nl.gate(f"{tag}.nS", "NOT", [f"{tag}.S"], f"{tag}.nS", cell="yearcell")
    nl.gate(f"{tag}.nSp", "NOT", [f"{tag}.Sprime"], f"{tag}.nSprime", cell="yearcell")
    if "exclusion_per_event" in B.mut:
        nl.gate(f"{tag}.disc", "BUF", [f"{tag}.fireP0"], f"{tag}.discard", cell="yearcell")
        nl.gate(f"{tag}.ng", "BUF", [f"{tag}.fireP1"], f"{tag}.neg", cell="yearcell")
    else:
        nl.gate(f"{tag}.disc", "AND", [f"{tag}.fireP0", f"{tag}.nS"], f"{tag}.discard", cell="yearcell")
        nl.gate(f"{tag}.ng", "AND", [f"{tag}.fireP1", f"{tag}.nSprime"], f"{tag}.neg", cell="yearcell")
    nl.gate(f"{tag}.nh", "NOT", [f"{tag}.hold"], f"{tag}.nhold", cell="yearcell")
    nl.gate(f"{tag}.gt", "AND", [f"{tag}.nS", f"{tag}.nhold"], f"{tag}.gate", cell="yearcell")
    nl.sequencer(f"{tag}.discseq", f"{tag}.discard", {f"{tag}.sh": False},
                 [{}, {f"{tag}.sh": True}, {f"{tag}.sh": False}, {}], cell="yearcell")
    B.packet(f"{tag}.neg", 1 / (u.gamma * u.V0), NA, bx, f"{tag}.neg", polarity=-1, cell="yearcell")
    B.cell("yearcell", tag, src="group_summer", dst="bus", trig="group+tick")
