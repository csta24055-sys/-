"""Adapter for the full synthetic building (stage B): scenario raw fields -> two netlists.

  (1) amplitude crossbar (static, DC): factor rails (independent sources of value
      factor x V0), derived rails (x conversion), one inverting op-amp stage per further
      data factor (resistance = data x R0), potentiometer segments for 1/(1-w) and r/(1-r),
      summing junctions (KCL) per stage, per event group and for the B5 base.
      Solved once by `engine.dc.solve_dc` (exact).
  (2) lifecycle core (hybrid): time base, event clocks, packets, year cells, operation
      year banks, refrigerant cells, stage buses and readout buses. The amplitude op-amp
      outputs it samples enter as grounded ideal sources whose value is the DC solution of
      (1) (substitution theorem: an ideal op-amp output is a stiff voltage source).

Allowed operations only (W1 element value = primitive x constant; W2 key match; W3
single-input predicate; W4 enumeration); everything else is counted GREY and itemised.
No event times, counts, years, per-unit WLC values or reference code are computed here.
"""
from __future__ import annotations

from fractions import Fraction

from adapter import CONVENTIONS, PH, PRIO, Builder, OpLedger, Tracked, Units
from engine import Netlist
from engine.dc import kcl_residual, solve_dc

ALLOWED_LICENCE = ("PERMITTED_PUBLIC",)          # published vocabulary of the input schema
STAGES = ("A1-A3", "A4", "A5", "B1", "B2", "B3", "B4", "B5", "B6", "B7", "C1", "C2", "C3", "C4")
ALL_BLOCKS = ("AC", "OP", "EV", "REF")
R0 = Fraction(1)
COUNTER_BITS = (0, 1, 2, 3, 4, 5, 6, 7)   # 8-bit year counter (H < 256): bit positions, not years


class LayeredLedger(OpLedger):
    def __init__(self):
        super().__init__()
        self.layer = "amp"
        self.by_layer = {}

    def note(self, kind, what=""):
        super().note(kind, what)
        d = self.by_layer.setdefault(self.layer, {"W1": 0, "W2": 0, "W3": 0, "W4": 0, "GREY": 0, "data_elements": 0})
        d[kind] += 1

    def data_element(self):
        self.data_elements += 1
        d = self.by_layer.setdefault(self.layer, {"W1": 0, "W2": 0, "W3": 0, "W4": 0, "GREY": 0, "data_elements": 0})
        d["data_elements"] += 1


def T(L, x, label):
    """Wrap a raw numeric field (exact binary value of the float)."""
    if x is None:
        return None
    return Tracked(Fraction(x), label, L)


def pot_complement(x: Tracked, R=Fraction(1)):
    """Second segment (1-w)*R of a potentiometer of total R whose wiper position is w: produced
    by the same physical element (R_top + R_bot = R), one element value, counted W1
    (architecture section 1)."""
    x.ledger.note("W1", f"pot segment of {x.label}")
    return Tracked((1 - x.value) * R, f"(1-{x.label})R", x.ledger, "element")


def nonneg(x):
    if x is None:
        return False
    x.ledger.note("W3", f"nonneg({x.label})")
    return x.value >= 0


def positive(x):
    if x is None:
        return False
    x.ledger.note("W3", f"positive({x.label})")
    return x.value > 0


def present(x):
    """Value used directly as a (positive) conductance: zero -> no branch (value-equivalent),
    negative -> explicit error (never dropped silently)."""
    if x is None:
        return False
    x.ledger.note("W3", f"sign({x.label})")
    if x.value < 0:
        raise ValueError(f"{x.label}: negative value {x.value} not supported by this cell (rejected, not dropped)")
    return x.value > 0


def ratio(x):
    if x is None:
        return False
    x.ledger.note("W3", f"ratio({x.label})")
    return 0 <= x.value <= 1


def in_01_open_right(x):
    if x is None:
        return False
    x.ledger.note("W3", f"0<=x<1({x.label})")
    return 0 <= x.value < 1


def in_01_open(x):
    if x is None:
        return False
    x.ledger.note("W3", f"0<x<1({x.label})")
    return 0 < x.value < 1


class Sig:
    __slots__ = ("node", "sign")

    def __init__(self, node, sign):
        self.node, self.sign = node, sign


# ----------------------------------------------------------------- amplitude crossbar


class AmpNet:
    def __init__(self, scn, L, u):
        self.scn, self.L, self.u = scn, L, u
        self.nl = Netlist()
        self.k = 0
        self.rails, self.derived, self.inverted = {}, {}, {}
        self.nl.V("a.V0", "a.rail", "0", u.V0, cell="rails")
        self.unit_rail = Sig("a.rail", 1)
        self.exports = {}
        self.opamps = 0

    def fresh(self, p):
        self.k += 1
        return f"a.{p}{self.k}"

    # -- W2/W3 lookups (structure only) -----------------------------------------
    def convert(self, from_unit, to_unit, extra=()):
        """Conversion multiplier as a tracked primitive, None for identity, False if undocumented."""
        L = self.L
        L.note("W2", f"conv {from_unit}->{to_unit}")
        if from_unit == to_unit:
            return None
        for c in list(extra) + list(self.scn.unit_conversions):
            if c.from_unit == from_unit and c.to_unit == to_unit:
                return T(L, c.factor, f"conv[{from_unit}->{to_unit}]")
        return False

    def lookup(self, fid, stage, act_unit, extra=()):
        L = self.L
        if fid is None or act_unit is None:
            return None
        L.note("W2", f"factor {fid}")
        rec = self.scn.factors.get(fid)
        if rec is None:
            return None
        L.note("W3", f"licence {fid}")
        if rec.licence_status not in ALLOWED_LICENCE:
            return None
        L.note("W2", f"stage {fid}")
        if rec.stages != [stage]:
            return None
        conv = self.convert(act_unit, rec.unit, extra)
        if conv is False:
            return None
        return rec, conv

    # -- circuit primitives -------------------------------------------------------
    def factor_rail(self, fid, value):
        if fid not in self.rails:
            node = f"a.f.{fid}"
            v = T(self.L, value, f"factor[{fid}]") * self.u.V0
            self.L.data_element()
            self.nl.V(f"a.F.{fid}", node, "0", v.value, cell="factor_rail")
            self.rails[fid] = Sig(node, 1)
        return self.rails[fid]

    def stage(self, sig, R_in, R_f, cell):
        """Inverting op-amp stage: out = -(R_f/R_in) * in."""
        x, o = self.fresh("x"), self.fresh("o")
        self.nl.R(f"{x}.Rin", sig.node, x, R=self._v(R_in), cell=cell)
        self.nl.R(f"{x}.Rf", x, o, R=self._v(R_f), cell=cell)
        self.nl.opamp(f"{x}.A", "0", x, o, cell=cell)
        self.opamps += 1
        return Sig(o, -sig.sign)

    def _v(self, x):
        if isinstance(x, Tracked):
            self.L.data_element()
            return x.value
        return Fraction(x)

    def inv(self, sig):
        if sig.node not in self.inverted:
            self.inverted[sig.node] = self.stage(sig, R0, R0, "inverter")
        return self.inverted[sig.node]

    def mul(self, sig, x: Tracked, cell, div=None, scale=Fraction(1)):
        """sig * x * scale (feedback resistance x * (scale R0): ONE W1 product); with div=w also
        / (1-w) (input = pot segment (1-w)R0)."""
        R_in = pot_complement(div, R0) if div is not None else R0
        return self.stage(sig, R_in, x * (scale * R0), cell)

    def derived_rail(self, rec, conv):
        rail = self.factor_rail(rec.factor_id, rec.value)
        if conv is None:
            return rail
        key = (rec.factor_id, conv.value)
        self.L.note("W2", "derived rail key")
        if key not in self.derived:
            self.derived[key] = self.mul(rail, conv, "derived_rail")
        return self.derived[key]

    def sum(self, items, cell):
        """Summing junction: items = [(Sig, weight Tracked or None)]; returns Sig of -sum."""
        items = [(s, w) for s, w in items if s is not None]
        if not items:
            return None
        sign = items[0][0].sign
        x, o = self.fresh("sx"), self.fresh("so")
        for s, w in items:
            if s.sign != sign:
                s = self.inv(s)
            G = (w * self.u.Gu) if w is not None else self.u.Gu
            self.nl.R(f"{x}.{self.fresh('g')}", s.node, x, G=self._v(G), cell=cell)
        self.nl.R(f"{x}.Rf", x, o, R=R0, cell=cell)
        self.nl.opamp(f"{x}.A", "0", x, o, cell=cell)
        self.opamps += 1
        return Sig(o, -sign)

    def export(self, sig, name, want_sign=1):
        if sig is None:
            return None
        if sig.sign != want_sign:
            sig = self.inv(sig)
        self.exports[name] = (sig.node, want_sign)
        return name


# ----------------------------------------------------------------- amplitude rows


def q_ord_chain(A, rail_sig, row, q, w, cell):
    """rail * q_ord: q/(1-w) for DESIGN, q otherwise (one stage)."""
    if row.quantity_basis == "DESIGN":
        A.L.note("W2", "basis DESIGN")
        return A.mul(rail_sig, q, cell, div=w)
    A.L.note("W2", "basis ORDERED/AS_BUILT")
    return A.mul(rail_sig, q, cell)


def build_amplitudes(scn, L, u, blocks, mutations=()):
    A = AmpNet(scn, L, u)
    out = {"init": {s: [] for s in ("A1-A3", "A4", "A5")}, "term": {s: [] for s in ("C1", "C2", "C3", "C4")},
           "groups": {}, "repair_free": [], "skipped": {}}

    def skip(k):
        out["skipped"][k] = out["skipped"].get(k, 0) + 1

    def group(key):
        return out["groups"].setdefault(key, {"u": [], "rep": [], "rows": 0})

    for i, row in enumerate(scn.materials):
        L.note("W4", "material row")
        lab = f"m[{i}]"
        q = T(L, row.quantity, lab + ".q")
        w = T(L, row.waste_rate, lab + ".w")
        qok = nonneg(q) and in_01_open_right(w)
        a13 = None
        # factor resolution: EPD -> composite -> generic (wiring decisions)
        rail = None
        epd = row.epd
        if epd is not None:
            L.note("W2", "epd declaration")
            rec = scn.factors.get(epd.factor_id) if epd.factor_id is not None else None
            if rec is not None and epd.declared_stages == rec.stages and epd.declared_unit == rec.unit \
                    and epd.valid_until == rec.valid_until and rec.valid_until is not None:
                L.note("GREY", "EPD validity date comparison (two inputs)")
                if rec.valid_until >= scn.project.assessment_date:
                    hit = A.lookup(epd.factor_id, "A1-A3", row.quantity_unit, row.conversions)
                    if hit is not None:
                        rail = A.derived_rail(*hit)
        if rail is None and row.composition is not None:
            parts, ok = [], True
            fsum = None
            for j, comp in enumerate(row.composition):
                hit = A.lookup(comp.factor_id, "A1-A3", "kg")
                fr = T(L, comp.mass_fraction, f"{lab}.comp[{j}].fraction")
                if hit is None or not nonneg(fr):
                    ok = False
                    break
                parts.append((A.derived_rail(*hit), fr))
                fsum = fr if fsum is None else fsum + fr            # GREY: sum of fractions
            if ok:
                dev = fsum - 1                                      # GREY
                L.note("GREY", "|sum fraction - 1| <= 1e-6 predicate")
                ok = abs(dev.value) <= Fraction(1, 10 ** 6)
            conv = A.convert(row.quantity_unit, "kg", row.conversions) if ok else False
            if ok and conv is not False:
                comp_rail = A.sum(parts, "composite")               # -sum f_j conv_j frac_j
                rail = A.mul(comp_rail, conv, "derived_rail") if conv is not None else comp_rail
        elif rail is None:
            hit = A.lookup(row.factor_id, "A1-A3", row.quantity_unit, row.conversions)
            if hit is not None:
                rail = A.derived_rail(*hit)
        if rail is not None and qok and positive(q):
            a13 = q_ord_chain(A, rail, row, q, w, "mfg")
        elif rail is None or not qok:
            skip("A13")
        # unquantified scope ratio r/(1-r): inverting stage with the two pot segments
        ucr = T(L, row.unquantified_cost_ratio, lab + ".ucr")
        a1304 = None
        if a13 is not None and in_01_open(ucr):
            a1304 = A.stage(a13, pot_complement(ucr, R0), ucr * R0, "unquantified")
        # transport A4
        tr = row.transport
        a4 = None
        if tr.delivery_factor_id is not None:
            hit = A.lookup(tr.delivery_factor_id, "A4", row.quantity_unit, row.conversions)
            if hit is not None and qok and positive(q):
                a4 = q_ord_chain(A, A.derived_rail(*hit), row, q, w, "transport")
        else:
            hit = A.lookup(tr.factor_id, "A4", "tkm")
            m, d = T(L, tr.mass_t, lab + ".tr.mass"), T(L, tr.distance_km, lab + ".tr.dist")
            if hit is not None and nonneg(m) and nonneg(d) and positive(m) and positive(d):
                a4 = A.mul(A.mul(A.derived_rail(*hit), m, "transport"), d, "transport")
        # installation (renewals only)
        inst = None
        if row.installation_factor_id is not None:
            hit = A.lookup(row.installation_factor_id, "A5", row.quantity_unit, row.conversions)
            if hit is not None and qok and positive(q):
                inst = q_ord_chain(A, A.derived_rail(*hit), row, q, w, "installation")
        # end of life C2 / C3 / C4
        eol = row.end_of_life
        mk = T(L, eol.mass_kg, lab + ".eol.mass")
        c2 = None
        hit = A.lookup(eol.haul_factor_id, "C2", "tkm")
        dk = T(L, eol.haul_distance_km, lab + ".eol.dist")
        if hit is not None and nonneg(mk) and nonneg(dk) and positive(mk) and positive(dk):
            c2 = A.mul(A.mul(A.derived_rail(*hit), mk, "haul", scale=Fraction(1, 1000)), dk, "haul")
        c3 = c4 = None
        if nonneg(mk):
            for landfill, stage in ((False, "C3"), (True, "C4")):
                parts = []
                for j, route in enumerate(eol.routes):
                    L.note("W2", "route kind")
                    if (route.route == "LANDFILL") != landfill:
                        continue
                    hit = A.lookup(route.factor_id, stage, "kg")
                    fr = T(L, route.fraction, f"{lab}.route[{j}]")
                    if hit is not None and nonneg(fr) and positive(fr):
                        parts.append((A.derived_rail(*hit), fr))
                if parts and positive(mk):
                    s = A.mul(A.sum(parts, "eol_routes"), mk, "eol_routes")
                    if landfill:
                        c4 = s
                    else:
                        c3 = s
        if "AC" in blocks:
            for s in (a13, a1304):
                if s is not None:
                    out["init"]["A1-A3"].append(s)
            if a4 is not None:
                out["init"]["A4"].append(a4)
            for st, s in (("C2", c2), ("C3", c3), ("C4", c4)):
                if s is not None:
                    out["term"][st].append(s)
        # event group (B4/B3) by refresh cycle (W2 key)
        rc = T(L, row.refresh_cycle, lab + ".refresh")
        rr = T(L, row.repair_rate, lab + ".repair")
        has_cycle = positive(rc)
        key = ("P", rc.value) if has_cycle else None
        if key is not None:
            L.note("W2", "group key")
        if "EV" in blocks:
            if key is not None:
                g = group(key)
                g["rows"] += 1
                g["u"] += [s for s in (a13, a4, inst, c2, c3, c4) if s is not None]
            if a13 is not None and nonneg(rr) and positive(rr):
                (group(key)["rep"] if key is not None else out["repair_free"]).append((a13, rr))
    for j, eq in enumerate(scn.equipment):
        L.note("W4", "equipment row")
        lab = f"e[{j}]"
        q = T(L, eq.quantity, lab + ".q")
        x01 = None
        hit = A.lookup(eq.factor_id, "A1-A3", eq.quantity_unit)
        if hit is not None and nonneg(q) and positive(q):
            x01 = A.mul(A.derived_rail(*hit), q, "equipment")
        extra = []
        for fid, stage in ((eq.delivery_factor_id, "A4"), (eq.installation_factor_id, "A5")):
            if fid is None:
                continue
            hit = A.lookup(fid, stage, eq.quantity_unit)
            if hit is not None and nonneg(q) and positive(q):
                extra.append(A.mul(A.derived_rail(*hit), q, "equipment"))
        x14 = None
        mk = T(L, eq.end_of_life_mass_kg, lab + ".eol")
        hit = A.lookup(eq.eol_factor_id, "C3", "kg")
        if hit is not None and nonneg(mk) and positive(mk):
            x14 = A.mul(A.derived_rail(*hit), mk, "equipment")
        if "AC" in blocks:
            if x01 is not None:
                out["init"]["A1-A3"].append(x01)
            if x14 is not None:
                out["term"]["C3"].append(x14)
        if eq.replacement_event_list is not None:
            L.note("W3", "explicit list present")
            yrs = tuple(T(L, y, lab + ".evt") for y in eq.replacement_event_list)
            key = ("X", tuple(y.value for y in yrs))
            L.note("W2", "group key")
        else:
            sl = T(L, eq.service_life, lab + ".life")
            key = ("P", sl.value) if positive(sl) else None
            if key is not None:
                L.note("W2", "group key")
        rr = T(L, eq.repair_rate, lab + ".repair")
        if "EV" in blocks:
            if key is not None:
                g = group(key)
                g["rows"] += 1
                g["u"] += [s for s in [x01] + extra + [x14] if s is not None]
            if x01 is not None and nonneg(rr) and positive(rr):
                (group(key)["rep"] if key is not None else out["repair_free"]).append((x01, rr))
    # construction site (A5)
    site = scn.construction
    gu = grid_unit(scn.operation.grid, L)
    kwh = T(L, site.electricity_kwh, "site.kwh")
    if gu is not None and nonneg(kwh) and positive(kwh):
        conv = A.convert("kWh", gu)
        L.note("W3", "grid licence")
        if conv is not False and scn.operation.grid.licence_status in ALLOWED_LICENCE:
            node = "a.grid_cv"
            v = T(L, scn.operation.grid.construction_value, "grid.construction_value") * u.V0
            L.data_element()
            A.nl.V("a.Fcv", node, "0", v.value, cell="factor_rail")
            r = Sig(node, 1)
            if conv is not None:
                r = A.mul(r, conv, "derived_rail")
            if "AC" in blocks:
                out["init"]["A5"].append(A.mul(r, kwh, "site"))
    for k, fuel in enumerate(site.fuels):
        L.note("W4", "fuel row")
        hit = A.lookup(fuel.factor_id, "A5", fuel.unit, fuel.conversions)
        qq = T(L, fuel.quantity, f"fuel[{k}]")
        if hit is not None and nonneg(qq) and positive(qq) and "AC" in blocks:
            out["init"]["A5"].append(A.mul(A.derived_rail(*hit), qq, "site"))
    for k, ws in enumerate(site.waste_streams):
        L.note("W4", "site waste row")
        hit = A.lookup(ws.factor_id, "A5", "kg")
        mm = T(L, ws.mass_kg, f"sitewaste[{k}]")
        if hit is not None and nonneg(mm) and positive(mm) and "AC" in blocks:
            out["init"]["A5"].append(A.mul(A.derived_rail(*hit), mm, "site"))
    end = scn.end_of_life
    for k, act in enumerate(end.demolition_activities):
        L.note("W4", "demolition row")
        hit = A.lookup(act.factor_id, "C1", act.unit)
        qq = T(L, act.quantity, f"demo[{k}]")
        if hit is not None and nonneg(qq) and positive(qq) and "AC" in blocks:
            out["term"]["C1"].append(A.mul(A.derived_rail(*hit), qq, "demolition"))
    for k, haul in enumerate(end.waste_hauls):
        L.note("W4", "haul row")
        hit = A.lookup(haul.factor_id, "C2", "tkm")
        m, d = T(L, haul.mass_t, f"haul[{k}].m"), T(L, haul.distance_km, f"haul[{k}].d")
        if hit is not None and nonneg(m) and nonneg(d) and positive(m) and positive(d) and "AC" in blocks:
            out["term"]["C2"].append(A.mul(A.mul(A.derived_rail(*hit), m, "haul"), d, "haul"))
    # summing junctions and exports
    sums = {}
    for s, lst in list(out["init"].items()) + list(out["term"].items()):
        sums[s] = A.sum([(x, None) for x in lst], "stage_sum")
        A.export(sums[s], f"N.{s}")
    for key, g in out["groups"].items():
        g["N_U"] = A.export(A.sum([(x, None) for x in g["u"]], "group_sum"), f"NU.{key}")
        g["N_A"] = A.export(A.sum(g["rep"], "repair_sum"), f"NA.{key}")
    out["N_A_free"] = A.export(A.sum(out["repair_free"], "repair_sum"), "NA.free")
    # B5 base: phi x (initial + terminal totals)
    b = scn.boundary
    out["b5"] = None
    if "EV" in blocks:
        L.note("W2", "reconstruction scenario")
        phi = T(L, b.reconstruction_scope_fraction, "phi")
        if b.reconstruction_scenario != "NONE" and ratio(phi) and positive(phi):
            inc = set(b.included_lifecycle_stages)
            base = A.sum([(sums[s], None) for s in ("A1-A3", "A4", "A5", "C1", "C2", "C3", "C4")
                          if sums[s] is not None and ("iota_upstream_b5" not in mutations or s in inc)], "b5_base")
            if base is not None:
                out["b5"] = A.export(A.mul(base, phi, "b5_base"), "N.B5")
    return A, out


def grid_unit(grid, L):
    L.note("W2", "grid unit parse")
    head, sep, tail = grid.unit.partition("/")
    return tail if sep and head == "kgCO2e" and tail else None


def annual_unit(unit, L):
    L.note("W2", "annual unit parse")
    head, sep, tail = unit.partition("/")
    return head if sep and tail == "year" else None


# ----------------------------------------------------------------- lifecycle core


class Core(Builder):
    """Hybrid lifecycle core. Amplitude nodes of the crossbar appear as taps (grounded
    ideal sources valued by the crossbar's DC solution, not by the adapter)."""

    def __init__(self, units, eps, ledger, mutations=()):
        super().__init__(units, eps, ledger, mutations)
        self.taps_src = {}
        self.zbus = {}
        self.readout_caps = {}
        self.decoders = {}

    def integrator(self, tag, C, cell, **kw):
        x, o = f"{tag}.x", f"{tag}.o"
        acc = {"accumulator": True} if cell in ("bus", "readout") else {}
        self.nl.opamp(f"{tag}.A", "0", x, o, cell=cell, **kw, **acc)
        self.nl.C(f"{tag}.C", x, o, C, cell=cell, **kw)
        return x, o

    def tap(self, name, value):
        node = f"t.{name}"
        if name not in self.taps_src:
            self.nl.V(f"tap.{name}", node, "0", value, cell="tap")
            self.taps_src[name] = node
        return node

    def val(self, x):
        if isinstance(x, Tracked):
            self.L.data_element()
            return x.value
        return Fraction(x)

    def bus(self, stage):
        x = super().bus(stage)
        self.readout_caps.setdefault(stage, [f"bus.{stage}.C"])
        return x

    def z(self, stage):
        """Readout integrator of a stage (terminal packets and non-destructive copies),
        emptied at the start of every readout."""
        if stage not in self.zbus:
            tag = f"z.{stage}"
            x, o = self.integrator(tag, Fraction(1), "readout")
            self.nl.switch(f"{tag}.Ssh", x, o, f"{tag}.sh", cell="readout")
            self.nl.sequencer(f"{tag}.rst", "rd", {f"{tag}.sh": False},
                              [{f"{tag}.sh": True}, {f"{tag}.sh": False}], cell="readout")
            self.zbus[stage] = x
            self.readout_caps.setdefault(stage, [])
            self.readout_caps[stage].append(f"{tag}.C")
            self.cell("readout", stage)
        return self.zbus[stage]

    def decode(self, k):
        """Boolean decode of the 8-bit year counter == k (shared by all year banks)."""
        if k not in self.decoders:
            ins = []
            for b in COUNTER_BITS:
                bit = f"yr{b}"
                if (k >> b) & 1:
                    ins.append(bit)
                else:
                    nb = f"nyr{b}"
                    if nb not in self.nl.by_name:
                        self.nl.gate(nb, "NOT", [bit], nb, cell="timebase")
                    ins.append(nb)
            self.nl.gate(f"dec{k}", "AND", ins, f"dec{k}", cell="yearbank")
            self.decoders[k] = f"dec{k}"
        return self.decoders[k]


def _cell_period(L, value, label):
    return Tracked(value, label, L)


def year_cell(B, gt, NA_node, fire, stage):
    """Repair flow of one event group with the year-exclusion rule (see topology.md)."""
    u, nl = B.u, B.nl
    bx = B.bus(stage)
    tag = f"{gt}.yc"
    xh, oh, p, n = f"{tag}.x", f"{tag}.o", f"{tag}.p", f"{tag}.n"
    nl.R(f"{tag}.Gh", NA_node, f"{tag}.g", G=1 / (u.gamma * u.tau_y * u.V0), cell="yearcell")
    nl.switch(f"{tag}.Sg", f"{tag}.g", xh, f"{tag}.gate", cell="yearcell")
    nl.opamp(f"{tag}.A", "0", xh, oh, cell="yearcell")
    nl.C(f"{tag}.Ch", p, n, Fraction(1), cell="yearcell")
    nl.switch(f"{tag}.Sfp", p, xh, f"{tag}.fb", cell="yearcell")
    nl.switch(f"{tag}.Sfn", n, oh, f"{tag}.fb", cell="yearcell")
    nl.switch(f"{tag}.Scp", p, bx, f"{tag}.cm", cell="yearcell")
    nl.switch(f"{tag}.Scn", n, "0", f"{tag}.cm", cell="yearcell")
    nl.switch(f"{tag}.Ssh", p, n, f"{tag}.sh", cell="yearcell")
    nl.sequencer(f"{tag}.commit", "tick", {f"{tag}.hold": False, f"{tag}.fb": True, f"{tag}.cm": False},
                 [{f"{tag}.hold": True}, {f"{tag}.fb": False}, {f"{tag}.cm": True}, {f"{tag}.cm": False},
                  {f"{tag}.fb": True}, {f"{tag}.hold": False}], cell="yearcell")
    P = "ZERO" if "no_lookahead" in B.mut else "P"
    nl.gate(f"{tag}.nP", "NOT", [P], f"{tag}.nP", cell="yearcell")
    nl.gate(f"{tag}.f0", "AND", [fire, f"{tag}.nP"], f"{tag}.fireP0", cell="yearcell")
    nl.gate(f"{tag}.f1", "AND", [fire, P], f"{tag}.fireP1", cell="yearcell")
    nl.latch(f"{tag}.Sl", f"{tag}.fireP0", "tick", f"{tag}.S", cell="yearcell")
    nl.dff(f"{tag}.Sd", f"{tag}.S", "tick", f"{tag}.Sa", cell="yearcell")
    nl.latch(f"{tag}.Sbl", f"{tag}.neg", "tick", f"{tag}.Sb", cell="yearcell")
    nl.gate(f"{tag}.Sp", "OR", [f"{tag}.Sa", f"{tag}.Sb"], f"{tag}.Sprime", cell="yearcell")
    nl.gate(f"{tag}.nS", "NOT", [f"{tag}.S"], f"{tag}.nS", cell="yearcell")
    nl.gate(f"{tag}.nSp", "NOT", [f"{tag}.Sprime"], f"{tag}.nSprime", cell="yearcell")
    nl.gate(f"{tag}.disc", "AND", [f"{tag}.fireP0", f"{tag}.nS"], f"{tag}.discard", cell="yearcell")
    nl.gate(f"{tag}.ng", "AND", [f"{tag}.fireP1", f"{tag}.nSprime"], f"{tag}.neg", cell="yearcell")
    nl.gate(f"{tag}.nh", "NOT", [f"{tag}.hold"], f"{tag}.nhold", cell="yearcell")
    nl.gate(f"{tag}.gt", "AND", [f"{tag}.nS", f"{tag}.nhold"], f"{tag}.gate", cell="yearcell")
    nl.sequencer(f"{tag}.discseq", f"{tag}.discard", {f"{tag}.sh": False},
                 [{}, {f"{tag}.sh": True}, {f"{tag}.sh": False}, {}], cell="yearcell")
    B.packet(f"{tag}.neg", 1 / (u.gamma * u.V0), NA_node, bx, f"{tag}.neg", polarity=-1, cell="yearcell")
    # non-destructive readout: copy of the hold capacitor's charge into the B3 readout bus
    # sampled only during the readout sequence (an op-amp output must not drive a
    # capacitor while that op-amp has no feedback during the zero-length commit phases)
    c, a_, b_ = f"{tag}.cp", f"{tag}.cp.a", f"{tag}.cp.b"
    zx = B.z(stage)
    nl.C(f"{c}.Cs", a_, b_, Fraction(1), cell="readout")
    nl.switch(f"{c}.St", a_, oh, f"{c}.trk", cell="readout")
    nl.switch(f"{c}.Sbg", b_, "0", f"{c}.trk", cell="readout")
    nl.switch(f"{c}.Sag", a_, "0", f"{c}.dmp", cell="readout")
    nl.switch(f"{c}.Sbx", b_, zx, f"{c}.dmp", cell="readout")
    nl.sequencer(f"{c}.seq", "rd", {f"{c}.trk": False, f"{c}.dmp": False},
                 [{f"{c}.trk": True}, {f"{c}.trk": False, f"{c}.dmp": True}, {f"{c}.dmp": False}], cell="readout")
    B.cell("yearcell", "yc", src="tap", dst="bus", trig="group+tick", readout="copy")


def _bank(B, tag, prof, L, src_pos, src_neg, dst, Gs, cell, label, gate_sig=None):
    """Year bank: conductance value_k * Gs from a source node to dst during study year k+1.
    CONSTANT -> one branch; LINEAR_TREND -> base branch + 8-bit MDAC of the slope on the
    counter bits; otherwise TABLE -> one switched branch per table entry (decode)."""
    nl = B.nl

    def branch(name, src, G, ctrl):
        if gate_sig is not None:
            g = f"{name}.en"
            nl.gate(g, "AND", [ctrl, gate_sig], g, cell=cell)
            ctrl = g
        nl.R(f"{name}.G", src, f"{name}.n", G=B.val(G), cell=cell)
        nl.switch(f"{name}.S", f"{name}.n", dst, ctrl, cell=cell)

    base = T(L, prof.base, label + ".base")
    slope = T(L, prof.slope, label + ".slope")
    L.note("W2", "profile kind")
    if prof.kind == "CONSTANT" and base is not None:
        if present(base):
            branch(f"{tag}.base", src_pos, base * Gs, "ONE")
        return "CONSTANT"
    if prof.kind == "LINEAR_TREND" and base is not None and slope is not None:
        if present(base):
            branch(f"{tag}.base", src_pos, base * Gs, "ONE")
        L.note("W3", f"sign({slope.label})")
        if slope.value != 0:
            neg = slope.value < 0
            for b in COUNTER_BITS:
                G = slope * (Gs * (-(2 ** b) if neg else 2 ** b))
                branch(f"{tag}.m{b}", src_neg if neg else src_pos, G, f"yr{b}")
        return "LINEAR_TREND"
    for k, v in enumerate(prof.table):
        L.note("W4", "table entry")
        tv = T(L, v, f"{label}.table[{k}]")
        if present(tv) and k < 256:
            branch(f"{tag}.k{k}", src_pos, tv * Gs, B.decode(k))
    return "TABLE"


def operation(B, A, scn, L, iota, tapv):
    """Crossbar part of B6 (purchased electricity with on-site generation, fuels), B2, B7:
    the source rails of the year banks (factor x conversion, both polarities)."""
    op, ww = scn.operation, scn.water_waste
    info = {}

    def rail_pair(rec, conv, name):
        s = A.derived_rail(rec, conv)
        p = A.export(s, f"R+.{name}", 1)
        n = A.export(s, f"R-.{name}", -1)
        return p, n

    pending = []      # (tap names) resolved after the DC solve
    # fuels (B6) and water/waste (B7)
    for prof, fid, stage, nm in ((op.gas, op.gas_factor_id, "B6", "gas"), (op.oil, op.oil_factor_id, "B6", "oil"),
                                 (op.district_heat, op.district_heat_factor_id, "B6", "dh"),
                                 (ww.water, ww.water_factor_id, "B7", "water"), (ww.sewage, ww.sewage_factor_id, "B7", "sewage"),
                                 (ww.municipal_waste, ww.waste_factor_id, "B7", "mwaste")):
        hit = A.lookup(fid, stage, annual_unit(prof.unit, L))
        if hit is None:
            info[nm] = "not computed"
            continue
        p, n = rail_pair(*hit, nm)
        pending.append(("bank", nm, prof, p, n, stage))
    # purchased electricity
    eu = annual_unit(op.electricity.unit, L)
    gu_, xu = annual_unit(op.onsite_generation.unit, L), annual_unit(op.onsite_export.unit, L)
    cg = A.convert(gu_, eu) if gu_ is not None and eu is not None else False
    cx = A.convert(xu, eu) if xu is not None and eu is not None else False
    grid = op.grid
    gu = grid_unit(grid, L)
    gconv = A.convert(eu, gu) if eu is not None and gu is not None else False
    L.note("W3", "grid licence")
    ok = eu is not None and cg is not False and cx is not False and gconv is not False \
        and grid.licence_status in ALLOWED_LICENCE
    elec = None
    if ok:
        g_rail = A.unit_rail if cg is None else A.mul(A.unit_rail, cg, "derived_rail")
        x_rail = A.unit_rail if cx is None else A.mul(A.unit_rail, cx, "derived_rail")
        elec = {"c": (A.export(A.unit_rail, "E.c+", 1), A.export(A.unit_rail, "E.c-", -1)),
                "g": (A.export(g_rail, "E.g+", 1), A.export(g_rail, "E.g-", -1)),
                "x": (A.export(x_rail, "E.x+", 1), A.export(x_rail, "E.x-", -1)),
                "gconv": gconv}
    info["elec"] = "computed" if ok else "not computed"
    return pending, elec, info


def build_operation_core(B, scn, L, pending, elec, tapv, iota):
    u, nl = B.u, B.nl
    op = scn.operation
    Gs = 1 / (u.gamma * u.tau_y * u.V0)
    kinds = {}
    for _, nm, prof, p, n, stage in pending:
        kinds[nm] = _bank(B, f"op.{nm}", prof, L, B.tap(p, tapv[p]), B.tap(n, tapv[n]), B.bus(stage), Gs,
                          "yearbank", nm)
        B.cell("yearbank", nm, src="tap", dst="bus")
    if elec is None:
        return kinds
    Gu = u.Gu
    # net purchase: KCL summing of consumption - (generation - export)
    xs, s = "el.x", "el.s"
    nl.opamp("el.A", "0", xs, s, cell="elec")
    nl.R("el.Rf", xs, s, G=Gu, cell="elec")
    tp = {k: (B.tap(v[0], tapv[v[0]]), B.tap(v[1], tapv[v[1]])) for k, v in elec.items() if k != "gconv"}
    kinds["elec"] = _bank(B, "el.c", op.electricity, L, tp["c"][0], tp["c"][1], xs, Gu, "yearbank", "elec")
    kinds["gen"] = _bank(B, "el.g", op.onsite_generation, L, tp["g"][1], tp["g"][0], xs, Gu, "yearbank", "gen")
    kinds["exp"] = _bank(B, "el.e", op.onsite_export, L, tp["x"][0], tp["x"][1], xs, Gu, "yearbank", "export")
    # rectifier: VCCS (current = Gu * V0 * net) into P, R_p to ground, ideal diode clamp
    nl.add(__import__("engine").VCCS("el.vccs", "0", "el.P", "0", s, Gu, tags={"cell": "elec"}))
    nl.R("el.Rp", "el.P", "0", G=Gu, cell="elec")
    if "diode_after_integration" not in B.mut:
        nl.diode("el.D", "0", "el.P", cell="elec")
    nl.opamp("el.F1", "el.P", "el.E", "el.E", cell="elec")          # follower
    # conversion to the grid unit (inverting stage)
    gconv = elec["gconv"]
    Gin = (gconv * Gu) if gconv is not None else Gu
    nl.R("el.cv.Rin", "el.E", "el.cv.x", G=B.val(Gin), cell="elec")
    nl.R("el.cv.Rf", "el.cv.x", "el.Ep", G=Gu, cell="elec")
    nl.opamp("el.cv.A", "0", "el.cv.x", "el.Ep", cell="elec")       # Ep = -conv * V0 * net+
    nl.R("el.inv.Rin", "el.Ep", "el.inv.x", G=Gu, cell="elec")
    nl.R("el.inv.Rf", "el.inv.x", "el.Epp", G=Gu, cell="elec")
    nl.opamp("el.inv.A", "0", "el.inv.x", "el.Epp", cell="elec")    # Epp = +conv * V0 * net+
    # grid factor bank: F = conv * grid_k * V0 * net+
    xF = "el.gx"
    nl.opamp("el.gA", "0", xF, "el.F", cell="elec")
    nl.R("el.gRf", xF, "el.F", G=Gu, cell="elec")
    kinds["grid"] = grid_bank(B, op.grid, L, "el.Ep", "el.Epp", xF, Gu)
    # B2 / B6 split (rho) with iota_B2 steering, then the stage buses
    Gs_out = Gs
    share = T(L, op.facility_management_ratio, "fm_ratio")
    nl.R("el.o.G", "el.F", B.bus("B6"), G=Gs_out, cell="split")
    if ratio(share) and positive(share):
        nl.R("el.r.Rin", "el.F", "el.r.x", G=B.val(share * Gu), cell="split")
        nl.R("el.r.Rf", "el.r.x", "el.Fr", G=Gu, cell="split")
        nl.opamp("el.r.A", "0", "el.r.x", "el.Fr", cell="split")       # Fr = -rho F
        nl.R("el.r.Gm", "el.Fr", B.bus("B6"), G=Gs_out, cell="split")   # B6 loses rho F
        nl.R("el.ri.Rin", "el.Fr", "el.ri.x", G=Gu, cell="split")
        nl.R("el.ri.Rf", "el.ri.x", "el.Frp", G=Gu, cell="split")
        nl.opamp("el.ri.A", "0", "el.ri.x", "el.Frp", cell="split")    # Frp = +rho F
        to_b2 = "B2" in iota or "rho_always_subtracted" in B.mut
        nl.R("el.r.Gp", "el.Frp", "el.r.n", G=Gs_out, cell="split")
        nl.switch("el.r.S2", "el.r.n", B.bus("B2"), "ONE" if to_b2 else "ZERO", cell="split")
        nl.switch("el.r.S6", "el.r.n", B.bus("B6"), "ZERO" if to_b2 else "ONE", cell="split")
    B.cell("elec", "elec", src="tap", dst="bus", rect="diode", split="rho")
    return kinds


def grid_bank(B, grid, L, src_neg, src_pos, dst, Gu):
    """Grid factor bank on the electricity signal (src_neg = -signal, src_pos = +signal)."""
    nl = B.nl
    st = T(L, grid.start, "grid.start")
    dc = T(L, grid.annual_decline, "grid.decline")
    fl = T(L, grid.floor, "grid.floor")
    L.note("W2", "grid kind")
    well = False
    if grid.kind == "CONSTANT":
        well = st is not None
    elif grid.kind == "LINEAR_DECLINE_TO_FLOOR":
        if st is not None and dc is not None and fl is not None and nonneg(dc):
            L.note("GREY", "grid start >= floor predicate (two inputs)")
            well = st.value >= fl.value
    elif grid.kind == "STEPWISE":
        steps = grid.steps or []
        L.note("W3", "steps present")
        well = bool(steps) and steps[0].from_index == 0
        for a, b in zip(steps[:-1], steps[1:]):
            L.note("GREY", "step order predicate (two inputs)")
            well = well and a.from_index < b.from_index

    def branch(name, src, G, ctrl):
        # switches on both sides: an open branch is isolated from the (non-fixed) signal node
        nl.switch(f"{name}.Si", src, f"{name}.m", ctrl, cell="grid")
        nl.R(f"{name}.G", f"{name}.m", f"{name}.n", G=B.val(G), cell="grid")
        nl.switch(f"{name}.S", f"{name}.n", dst, ctrl, cell="grid")

    if not well:
        for k, v in enumerate(grid.table):
            L.note("W4", "grid table entry")
            tv = T(L, v, f"grid.table[{k}]")
            if present(tv) and k < 256:
                branch(f"gr.k{k}", src_neg, tv * Gu, B.decode(k))
        return "TABLE"
    if grid.kind == "CONSTANT":
        if present(st):
            branch("gr.c", src_neg, st * Gu, "ONE")
        return "CONSTANT"
    if grid.kind == "STEPWISE":
        prev = None
        steps = grid.steps
        latches = []
        for i, sp in enumerate(steps):
            L.note("W4", "grid step")
            q = f"gr.L{i}"
            if sp.from_index == 0:
                nl.latch(f"{q}.l", "ZERO", "ZERO", q, init=True, cell="grid")
            else:
                nl.latch(f"{q}.l", B.decode(sp.from_index), "ZERO", q, cell="grid")
            latches.append(q)
        for i, sp in enumerate(steps):
            v = T(L, sp.value, f"grid.step[{i}]")
            if i + 1 < len(steps):
                nl.gate(f"gr.n{i + 1}", "NOT", [latches[i + 1]], f"gr.n{i + 1}", cell="grid")
                nl.gate(f"gr.a{i}", "AND", [latches[i], f"gr.n{i + 1}"], f"gr.a{i}", cell="grid")
                ctrl = f"gr.a{i}"
            else:
                ctrl = latches[i]
            if present(v):
                branch(f"gr.s{i}", src_neg, v * Gu, ctrl)
        return "STEPWISE"
    # LINEAR_DECLINE_TO_FLOOR: start - decline*k while above the floor (comparator), else floor
    u = B.u
    nl.opamp("gr.d.A", "0", "gr.d.x", "gr.d.o", cell="grid")
    nl.R("gr.d.Rf", "gr.d.x", "gr.d.o", G=Gu, cell="grid")
    nl.R("gr.d.st", "rail", "gr.d.x", G=B.val(st * Gu), cell="grid")
    nl.R("gr.d.fl", "railn", "gr.d.x", G=B.val(fl * Gu), cell="grid") if present(fl) else None
    for b in COUNTER_BITS:
        if positive(dc):
            nl.R(f"gr.d.m{b}.G", "railn", f"gr.d.m{b}.n", G=B.val(dc * (Gu * 2 ** b)), cell="grid")
            nl.switch(f"gr.d.m{b}.S", f"gr.d.m{b}.n", "gr.d.x", f"yr{b}", cell="grid")
    nl.comparator("gr.cmp", "0", "gr.d.o", "gr.above", priority=PRIO["early"], cell="grid")
    nl.gate("gr.nab", "NOT", ["gr.above"], "gr.floored", cell="grid")
    if present(st):
        branch("gr.st", src_neg, st * Gu, "gr.above")
    if positive(dc):
        for b in COUNTER_BITS:
            nl.gate(f"gr.mb{b}", "AND", [f"yr{b}", "gr.above"], f"gr.mb{b}", cell="grid")
            branch(f"gr.m{b}", src_pos, dc * (Gu * 2 ** b), f"gr.mb{b}")
    if present(fl):
        branch("gr.fl", src_neg, fl * Gu, "gr.floored")
    return "LINEAR_DECLINE_TO_FLOOR"


def build_core(scn, L, u, convention, blocks, amp, A, tapv, op_parts, ref_parts, mutations=()):
    """Generate the lifecycle-core netlist (all values from W1 / taps / constants)."""
    eps, _ = CONVENTIONS[convention]
    L.layer = "time"
    B = Core(u, eps, L, mutations)
    B.rails()
    gramp = B.timebase()
    B.nl.power_on("por", "por", priority=PRIO["por"])
    iota = set(scn.boundary.included_lifecycle_stages)
    Cpk = 1 / (u.gamma * u.V0)
    if "AC" in blocks:
        for s in ("A1-A3", "A4", "A5"):
            if f"N.{s}" in A.exports:
                node = B.tap(f"N.{s}", tapv[f"N.{s}"])
                B.packet(f"pk.init.{s}", Cpk, node, B.bus(s), "por", v0=tapv[f"N.{s}"])
                B.cell("packet", "init", src="tap", dst="bus", trig="por")
        for s in ("C1", "C2", "C3", "C4"):
            B.bus(s)
            if f"N.{s}" in A.exports:
                node = B.tap(f"N.{s}", tapv[f"N.{s}"])
                dst = B.bus(s) if "terminal_into_integrator" in B.mut else B.z(s)
                B.packet(f"pk.term.{s}", Cpk, node, dst, "rd", v0=tapv[f"N.{s}"])
                B.cell("packet", "term", src="tap", dst="readout", trig="rd")
    group_signals = {}
    if "EV" in blocks:
        for gi, (key, g) in enumerate(sorted(amp["groups"].items(), key=lambda kv: str(kv[0]))):
            gt = f"g{gi}"
            fires = []
            if key[0] == "P":
                fires.append(B.clock(f"{gt}.clk", Tracked(key[1], f"{gt}.period", L)))
            else:
                for k, y in enumerate(key[1]):
                    Y = Tracked(y, f"{gt}.year[{k}]", L)
                    if positive(Y):
                        fires.append(B.explicit(f"{gt}.x{k}", Y, gramp))
            fire = B.OR(f"{gt}.fire", fires)
            group_signals[gt] = {"fire": fire, "key": key, "rows": g["rows"]}
            if g.get("N_U"):
                node = B.tap(g["N_U"], tapv[g["N_U"]])
                B.packet(f"pk.{gt}", Cpk, node, B.bus("B4"), fire, v0=tapv[g["N_U"]])
                B.cell("packet", "group", src="tap", dst="bus", trig="group")
            if g.get("N_A"):
                year_cell(B, gt, B.tap(g["N_A"], tapv[g["N_A"]]), fire, "B3")
        if amp.get("N_A_free"):
            node = B.tap(amp["N_A_free"], tapv[amp["N_A_free"]])
            B.nl.R("rp.free.G", node, B.bus("B3"), G=1 / (u.gamma * u.tau_y * u.V0), cell="flow")
            B.cell("flow", "repair_free", src="tap", dst="bus")
        if amp.get("b5"):
            rc = T(L, scn.boundary.replacement_cycle, "replacement_cycle")
            if positive(rc):
                f = B.clock("b5.clk", rc)
                node = B.tap(amp["b5"], tapv[amp["b5"]])
                B.packet("pk.b5", Cpk, node, B.bus("B5"), f, v0=tapv[amp["b5"]])
                B.cell("packet", "b5", src="tap", dst="bus", trig="group")
    kinds = {}
    if "OP" in blocks and op_parts is not None:
        pending, elec = op_parts
        kinds = build_operation_core(B, scn, L, pending, elec, tapv, iota)
    if "REF" in blocks and ref_parts is not None:
        refrigerant_core(B, scn, L, ref_parts, tapv, gramp)
    for s in STAGES:
        B.bus(s)
    L.layer = "readout"
    return B, group_signals, kinds


def refrigerant_amp(A, scn, L):
    """Crossbar part of B1: initial charge amplitude V0*m0 per valid device (W4)."""
    out = []
    for i, d in enumerate(scn.refrigerants):
        L.note("W4", "refrigerant device")
        m0 = T(L, d.charge_mass_kg, f"rf[{i}].m0")
        gwp = T(L, d.gwp, f"rf[{i}].gwp")
        r = T(L, d.annual_leak_rate, f"rf[{i}].leak")
        if not (nonneg(m0) and nonneg(gwp) and ratio(r)):
            out.append(None)
            continue
        node = A.export(A.mul(A.unit_rail, m0, "refrigerant"), f"M0.{i}", 1) if positive(m0) else None
        out.append({"dev": d, "m0": m0, "gwp": gwp, "r": r, "tap": node})
    return out


def refrigerant_core(B, scn, L, parts, tapv, gramp):
    """B1 per device: charge integrator, year-start sample-hold, leak and drain currents,
    replacement losses (mid-year: packet + correction flow until the tick; at/near a whole
    year: pending sample at the tick, dumped at the firing), reset to m0, terminal residual."""
    u, nl, eps = B.u, B.nl, B.eps
    Gu = u.Gu
    b1 = B.bus("B1")
    Cpk = 1 / (u.gamma * u.V0)
    Gb = 1 / (u.gamma * u.tau_y * u.V0)
    for i, p in enumerate(parts or []):
        if p is None or p["tap"] is None:
            continue
        d = p["dev"]
        tg = f"rf{i}"
        m0n = B.tap(p["tap"], tapv[p["tap"]])
        # main charge integrator: u_m = V0*m, output om = -V0*m
        xm, om = f"{tg}.xm", f"{tg}.om"
        nl.opamp(f"{tg}.Am", "0", xm, om, cell="refrigerant")
        nl.C(f"{tg}.Cm", xm, om, Fraction(1), cell="refrigerant")

        def inv_stage(name, src, Rf, cell="refrigerant"):
            x, o = f"{tg}.{name}.x", f"{tg}.{name}.o"
            nl.R(f"{tg}.{name}.Rin", src, x, R=R0, cell=cell)
            nl.R(f"{tg}.{name}.Rf", x, o, R=B.val(Rf), cell=cell)
            nl.opamp(f"{tg}.{name}.A", "0", x, o, cell=cell)
            return o
        mp = inv_stage("mp", om, R0)                                  # +V0 m (live)
        # year-start sample-hold of om -> Hn = -V0 m_start
        hc = f"{tg}.hc"
        nl.C(f"{tg}.Ch", hc, "0", Fraction(1), cell="refrigerant")
        nl.switch(f"{tg}.Shs", hc, om, f"{tg}.hs", cell="refrigerant")
        nl.opamp(f"{tg}.Fh", hc, f"{tg}.Hn", f"{tg}.Hn", cell="refrigerant")
        Hg = inv_stage("hg", f"{tg}.Hn", p["gwp"] * R0) if positive(p["gwp"]) else None   # +V0 gwp m_start
        r = p["r"]
        top = bool(d.top_up)
        L.note("W3", "top_up flag")
        # signals
        fires, Es = [], []
        if d.change_years is not None:
            L.note("W3", "explicit change years present")
            for k, y in enumerate(d.change_years):
                Y = T(L, y, f"rf[{i}].year[{k}]")
                if not positive(Y):
                    continue
                f = B.explicit(f"{tg}.x{k}", Y, gramp)
                fires.append(f)
                nl.V(f"{tg}.x{k}.Ve", f"{tg}.x{k}.re", "0", B.val(Y * (u.V0 * (1 - eps) ** 2)), cell="explicit")
                nl.comparator(f"{tg}.x{k}.early", gramp, f"{tg}.x{k}.re", f"{tg}.x{k}.e", priority=PRIO["early"], cell="explicit")
                nl.gate(f"{tg}.x{k}.nd", "NOT", [f"{tg}.x{k}.dis"], f"{tg}.x{k}.nd", cell="explicit")
                nl.gate(f"{tg}.x{k}.E", "AND", [f"{tg}.x{k}.e", f"{tg}.x{k}.nd"], f"{tg}.x{k}.E", cell="explicit")
                Es.append(f"{tg}.x{k}.E")
        else:
            sl = T(L, d.service_life, f"rf[{i}].life")
            if positive(sl):
                f = B.clock(f"{tg}.clk", sl)
                fires.append(f)
                # exact early comparator: remaining time to the firing <= kappa * elapsed time
                kappa = eps * (2 - eps) / (1 - eps) ** 2
                xg, og = B.integrator(f"{tg}.gr", u.Gu * u.tau_y, "clock")
                nl.R(f"{tg}.gr.G", "railn", xg, G=u.Gu * (1 - eps), cell="clock")
                xe, oe = f"{tg}.E.x", f"{tg}.E.o"
                nl.opamp(f"{tg}.E.A", "0", xe, oe, cell="clock")
                nl.R(f"{tg}.E.Rf", xe, oe, G=Gu, cell="clock")
                if kappa:
                    nl.R(f"{tg}.E.Gg", og, xe, G=kappa * Gu, cell="clock")
                nl.R(f"{tg}.E.Gn", "railn", xe, G=B.val(sl * Gu), cell="clock")
                nl.R(f"{tg}.E.Gj", f"{tg}.clk.o", xe, G=B.val(sl * Gu), cell="clock")
                nl.comparator(f"{tg}.E.cmp", "0", oe, f"{tg}.E", priority=PRIO["early"], cell="clock")
                Es.append(f"{tg}.E")
        fire = B.OR(f"{tg}.fire", fires)
        E = B.OR(f"{tg}.Eall", Es)
        P = "ZERO" if "no_lookahead" in B.mut else "P"
        nl.gate(f"{tg}.nP", "NOT", [P], f"{tg}.nP", cell="refrigerant")
        nl.gate(f"{tg}.f0", "AND", [fire, f"{tg}.nP"], f"{tg}.fireP0", cell="refrigerant")
        nl.gate(f"{tg}.f1", "AND", [fire, P], f"{tg}.fireP1", cell="refrigerant")
        nl.gate(f"{tg}.tE", "AND", ["tick", E], f"{tg}.tickE", cell="refrigerant")
        nl.latch(f"{tg}.Fl", f"{tg}.fireP0", "tick", f"{tg}.F", cell="refrigerant")
        nl.gate(f"{tg}.nF", "NOT", [f"{tg}.F"], f"{tg}.nF", cell="refrigerant")
        # leak into B1 (year-start hold) and drain of the charge (no top-up, before a replacement)
        if Hg is not None and positive(r):
            if "refrigerant_rc_decay" in B.mut:
                # MUTATION: leak read from the live (continuously decaying) charge
                src = inv_stage("live_g", om, p["gwp"] * R0)
                src = inv_stage("live_gi", src, R0)
                src = inv_stage("live_gj", src, R0)
            else:
                src = Hg
            nl.R(f"{tg}.Gleak", src, b1, G=B.val(r * Gb), cell="refrigerant")
            if not top:
                nl.R(f"{tg}.Gdr", f"{tg}.Hn", f"{tg}.dr", G=B.val(r * (1 / u.tau_y)), cell="refrigerant")
                # drain off while the hold capacitor samples (no self-feedback in that phase)
                nl.gate(f"{tg}.nhs", "NOT", [f"{tg}.hs"], f"{tg}.nhs", cell="refrigerant")
                nl.gate(f"{tg}.dren", "AND", [f"{tg}.nF", f"{tg}.nhs"], f"{tg}.dren", cell="refrigerant")
                nl.switch(f"{tg}.Sdr", f"{tg}.dr", xm, f"{tg}.dren", cell="refrigerant")
        lam = T(L, d.replacement_loss_rate, f"rf[{i}].loss")
        has_loss = ratio(lam) and positive(lam) and Hg is not None
        if has_loss:
            Lnode = inv_stage("lg", inv_stage("ll", om, lam * R0), p["gwp"] * R0)   # -V0 lam gwp m
            # correction flow after a mid-year replacement: -lam gwp m_start r until the tick
            if not top and positive(r):
                cl = inv_stage("cl", Hg, lam * R0)                    # -V0 lam gwp m_start
                nl.gate(f"{tg}.corr", "AND", [f"{tg}.F"], f"{tg}.corrS", cell="refrigerant")
                nl.R(f"{tg}.Gcorr", cl, f"{tg}.cn", G=B.val(r * Gb), cell="refrigerant")
                nl.switch(f"{tg}.Scorr", f"{tg}.cn", b1, f"{tg}.corrS", cell="refrigerant")
            # mid-year loss packet (sampled now)
            la_, lb_ = f"{tg}.lp.a", f"{tg}.lp.b"
            nl.C(f"{tg}.lp.Cs", la_, lb_, Cpk, cell="refrigerant")
            nl.switch(f"{tg}.lp.St", la_, Lnode, f"{tg}.lp.trk", cell="refrigerant")
            nl.switch(f"{tg}.lp.Sbg", lb_, "0", f"{tg}.lp.trk", cell="refrigerant")
            nl.switch(f"{tg}.lp.Sag", la_, "0", f"{tg}.lp.dmp", cell="refrigerant")
            nl.switch(f"{tg}.lp.Sbx", lb_, b1, f"{tg}.lp.dmp", cell="refrigerant")
            # pending sample taken at the tick, dumped at a firing that belongs to that year
            pa, pb = f"{tg}.pp.a", f"{tg}.pp.b"
            nl.C(f"{tg}.pp.Cs", pa, pb, Cpk, cell="refrigerant")
            nl.switch(f"{tg}.pp.St", pa, Lnode, f"{tg}.pp.trk", cell="refrigerant")
            nl.switch(f"{tg}.pp.Sbg", pb, "0", f"{tg}.pp.trk", cell="refrigerant")
            nl.switch(f"{tg}.pp.Sag", pa, "0", f"{tg}.pp.dmp", cell="refrigerant")
            nl.switch(f"{tg}.pp.Sbx", pb, b1, f"{tg}.pp.dmp", cell="refrigerant")
        # reset to m0: short the charge capacitor, then an m0 packet from the crossbar tap
        nl.switch(f"{tg}.Ssh", xm, om, f"{tg}.sh", cell="refrigerant")
        ma, = (f"{tg}.m0.a",)
        nl.C(f"{tg}.m0.Cs", ma, "0", Fraction(1), v0=tapv[p["tap"]], cell="refrigerant")
        nl.gate(f"{tg}.m0t", "NOR", [f"{tg}.m0off1", f"{tg}.m0off2", f"{tg}.m0off3"], f"{tg}.m0trk", cell="refrigerant")
        nl.gate(f"{tg}.m0d", "OR", [f"{tg}.m0dmp1", f"{tg}.m0dmp2", f"{tg}.m0dmp3"], f"{tg}.m0dmp", cell="refrigerant")
        nl.switch(f"{tg}.m0.St", ma, m0n, f"{tg}.m0trk", cell="refrigerant")
        nl.switch(f"{tg}.m0.Sd", ma, xm, f"{tg}.m0dmp", cell="refrigerant")
        nl.gate(f"{tg}.shg", "OR", [f"{tg}.sh1", f"{tg}.sh2"], f"{tg}.sh", cell="refrigerant")
        nl.gate(f"{tg}.hsg", "OR", [f"{tg}.hs1", f"{tg}.hs2", f"{tg}.hs3"], f"{tg}.hs", cell="refrigerant")
        # power-on: m0 packet, then the first year-start sample
        nl.sequencer(f"{tg}.por", "por", {f"{tg}.m0off3": False, f"{tg}.m0dmp3": False, f"{tg}.hs1": False},
                     [{f"{tg}.m0off3": True}, {f"{tg}.m0dmp3": True}, {f"{tg}.m0dmp3": False},
                      {f"{tg}.m0off3": False}, {f"{tg}.hs1": True}, {f"{tg}.hs1": False}], cell="refrigerant")
        # every tick: (if an event belongs to the closing year) pending loss sample and reset; then sample-hold
        lt = {f"{tg}.pp.trk": False} if has_loss else {}
        nl.sequencer(f"{tg}.tickE", f"{tg}.tickE", dict(lt, **{f"{tg}.sh1": False, f"{tg}.m0off1": False, f"{tg}.m0dmp1": False}),
                     [dict({f"{tg}.pp.trk": True} if has_loss else {}),
                      dict({f"{tg}.pp.trk": False} if has_loss else {}, **{f"{tg}.sh1": True, f"{tg}.m0off1": True}),
                      {f"{tg}.sh1": False}, {f"{tg}.m0dmp1": True}, {f"{tg}.m0dmp1": False}, {f"{tg}.m0off1": False}],
                     cell="refrigerant")
        nl.sequencer(f"{tg}.tick", "tick", {f"{tg}.hs2": False},
                     [{}, {}, {}, {}, {}, {}, {f"{tg}.hs2": True}, {f"{tg}.hs2": False}], cell="refrigerant")
        # mid-year replacement: loss packet from the live charge, reset to m0
        ls = {f"{tg}.lp.trk": True, f"{tg}.lp.dmp": False} if has_loss else {}
        nl.sequencer(f"{tg}.f0seq", f"{tg}.fireP0", dict(ls, **{f"{tg}.sh2": False, f"{tg}.m0off2": False, f"{tg}.m0dmp2": False}),
                     [dict({f"{tg}.lp.trk": False} if has_loss else {}),
                      dict({f"{tg}.lp.dmp": True} if has_loss else {}, **{f"{tg}.sh2": True}),
                      dict({f"{tg}.lp.dmp": False} if has_loss else {}, **{f"{tg}.sh2": False, f"{tg}.m0off2": True}),
                      dict({f"{tg}.lp.trk": True} if has_loss else {}, **{f"{tg}.m0dmp2": True}),
                      {f"{tg}.m0dmp2": False}, {f"{tg}.m0off2": False}]
                     + ([{f"{tg}.hs3": True}, {f"{tg}.hs3": False}] if "init_before_leak" in B.mut else []),
                     cell="refrigerant")
        if has_loss:
            nl.sequencer(f"{tg}.f1seq", f"{tg}.fireP1", {f"{tg}.pp.dmp": False},
                         [{}, {f"{tg}.pp.dmp": True}, {f"{tg}.pp.dmp": False}], cell="refrigerant")
        # terminal residual R(T) = (1 - eta) gwp m(T): readout packet into the B1 readout bus
        eta = T(L, d.end_of_life_recovery_rate, f"rf[{i}].eta")
        if ratio(eta) and Hg is not None:
            o1 = inv_stage("eta", mp, pot_complement(eta, R0))      # -V0 (1-eta) m
            o2 = inv_stage("rg", o1, p["gwp"] * R0)                   # +V0 (1-eta) gwp m
            dst = b1 if "terminal_into_integrator" in B.mut else B.z("B1")
            B.packet(f"{tg}.term", Cpk, o2, dst, "rd", v0=0, cell="refrigerant", datapath=False)
        B.cell("refrigerant", "device", src="tap", dst="bus", trig="group+tick", readout="terminal")
