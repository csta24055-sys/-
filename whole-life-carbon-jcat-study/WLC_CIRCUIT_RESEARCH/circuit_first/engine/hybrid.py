"""Scalable exact event-driven hybrid simulation (integrator-only networks).

Same semantics as `sim.Simulator` (MNA per mode, charge-conserving re-initialisation,
priority classes processed as sets, lockstep zero-length sequencer phases), organised for
large netlists:
  * nodes held by a grounded ideal voltage source are boundary nodes with a known potential;
    they do not merge components, so the network splits into many small components;
  * every component keeps its own time origin and closed-form polynomial state (lazy time);
    a switch change re-partitions and re-initialises only the touched components;
  * comparator / diode crossing times live in an event heap and are recomputed only when one
    of their components changed;
  * the boolean layer is event-driven (fan-out lists), with the same delta-cycle semantics.
Exact arithmetic only (Fractions); every mode must be nilpotent (polynomial states).
Application-agnostic.
"""
from __future__ import annotations

import heapq
from fractions import Fraction
from math import factorial

from . import linalg as la
from .mna import ComponentMode, ModeError
from .netlist import (DFF, GND, CCCS, CCVS, VCCS, VCVS, Capacitor, Comparator, Counter, Diode,
                      Gate, Inductor, OpAmp, PowerOn, Resistor, Sequencer, SRLatch, Switch, VSource)
from .logic import _gate
from .sim import fmt

F0 = Fraction(0)
F1 = Fraction(1)


# ----------------------------------------------------------------- boolean layer (event-driven)

class FastLogic:
    def __init__(self, netlist):
        dig = netlist.digital()
        self.sig = {"ONE": True, "ZERO": False}
        self.gates = [e for e in dig if isinstance(e, Gate)]
        self.count_val = {}
        self.comb_fan = {}
        self.edge_fan = {}
        self.ops = 0
        for e in dig:
            if isinstance(e, Gate):
                for i in e.inputs:
                    self.comb_fan.setdefault(i, []).append(e)
                    self.sig.setdefault(i, False)
                self.sig.setdefault(e.out, False)
            elif isinstance(e, SRLatch):
                self.sig[e.q] = bool(e.init)
                for s in (e.set, e.reset):
                    self.edge_fan.setdefault(s, []).append(e)
                    self.sig.setdefault(s, False)
            elif isinstance(e, DFF):
                self.sig[e.q] = bool(e.init)
                self.edge_fan.setdefault(e.clk, []).append(e)
                self.sig.setdefault(e.clk, False)
                self.sig.setdefault(e.d, False)
            elif isinstance(e, Counter):
                self.count_val[e.name] = 0
                for k in range(e.nbits):
                    self.sig[f"{e.prefix}{k}"] = False
                self.edge_fan.setdefault(e.clk, []).append(e)
                self.sig.setdefault(e.clk, False)
            elif isinstance(e, Sequencer):
                for s, v in e.idle.items():
                    self.sig[s] = bool(v)
                self.edge_fan.setdefault(e.trigger, []).append(e)
                self.sig.setdefault(e.trigger, False)
            elif isinstance(e, (Comparator, PowerOn)):
                self.sig.setdefault(e.out, False)
        # initial combinational settle
        changed = {}
        for _ in range(len(self.gates) + 2):
            any_change = False
            for g in self.gates:
                v = _gate(g.op, [self.sig[i] for i in g.inputs])
                if self.sig[g.out] != v:
                    self.sig[g.out] = v
                    any_change = True
            if not any_change:
                break

    def settle(self, changes):
        """Returns (started sequencers, {signal: (old, new)} over the whole settle)."""
        started, total = [], {}
        pending = dict(changes)
        for _ in range(1000):
            old = {}
            work = []
            for k, v in pending.items():
                v = bool(v)
                if self.sig.get(k, False) != v:
                    old.setdefault(k, self.sig.get(k, False))
                    self.sig[k] = v
                    work.append(k)
            while work:
                s = work.pop()
                for g in self.comb_fan.get(s, ()):
                    self.ops += 1
                    v = _gate(g.op, [self.sig[i] for i in g.inputs])
                    if self.sig[g.out] != v:
                        old.setdefault(g.out, self.sig[g.out])
                        self.sig[g.out] = v
                        work.append(g.out)
            for k, o in old.items():
                if o != self.sig[k]:
                    total[k] = (total[k][0] if k in total else o, self.sig[k])
            rising = {k for k, o in old.items() if not o and self.sig[k]}
            updates = {}
            seen = set()
            for s in rising:
                for e in self.edge_fan.get(s, ()):
                    if e.name in seen:
                        continue
                    seen.add(e.name)
                    if isinstance(e, SRLatch):
                        if e.reset in rising:
                            updates[e.q] = False
                        elif e.set in rising:
                            updates[e.q] = True
                    elif isinstance(e, DFF):
                        updates[e.q] = self.sig[e.d]
                    elif isinstance(e, Counter):
                        self.count_val[e.name] = (self.count_val[e.name] + 1) % (2 ** e.nbits)
                        for k in range(e.nbits):
                            updates[f"{e.prefix}{k}"] = bool((self.count_val[e.name] >> k) & 1)
                    elif isinstance(e, Sequencer):
                        started.append(e)
            pending = {k: v for k, v in updates.items() if self.sig[k] != v}
            if not pending:
                return started, total
        raise RuntimeError("logic does not settle")


# ----------------------------------------------------------------- components


class Comp:
    __slots__ = ("cm", "t0", "u0", "W", "nodes", "els", "contrib")

    def __init__(self, cm, nodes, els):
        self.cm, self.nodes, self.els = cm, nodes, els
        self.contrib = {}
        self.t0, self.u0, self.W = None, None, None

    def anchor(self, t, u0):
        self.t0 = t
        self.u0 = list(u0)
        aug = list(u0) + [F1]
        self.W = [[x / factorial(k) for x in la.matvec(P, aug, True)] for k, P in enumerate(self.cm._powers)]

    def at(self, t):
        if t == self.t0:
            return list(self.u0)
        tau = t - self.t0
        m = len(self.u0)
        out = [F0] * m
        p = F1
        for k, w in enumerate(self.W):
            if k:
                p = p * tau
            for j in range(m):
                if w[j]:
                    out[j] += w[j] * p
        return out


class Hybrid:
    def __init__(self, netlist, record=False, record_jumps=False, log_edges=False, accumulators=True):
        self.nl = netlist
        self.record, self.record_jumps, self.log_edges = record, record_jumps, log_edges
        analog = netlist.analog()
        self.fixed, self.fixed_src = {}, {}
        for e in analog:
            if isinstance(e, VSource) and (e.a == GND) != (e.b == GND):
                n, v = (e.a, Fraction(e.V)) if e.b == GND else (e.b, -Fraction(e.V))
                if n in self.fixed:
                    raise ModeError(f"node {n} held by two sources")
                self.fixed[n] = v
                self.fixed_src[e.name] = n
        self.by = netlist.by_name
        # accumulators: an ideal integrator tagged `accumulator` (non-inverting input at a
        # fixed potential, one feedback capacitor, optional reset switches across it, nothing
        # else on its output) is solved as a sink: its virtual ground is a known-potential
        # node, its capacitor charge = time integral + impulses of all currents into it.
        self.acc, acc_names = {}, set()
        if accumulators:
            touch = {}
            for e in analog:
                for n in e.nodes():
                    touch.setdefault(n, []).append(e)
            mon_nodes = {n for c in netlist.digital() if isinstance(c, Comparator) for n in (c.plus, c.minus)}
            for e in analog:
                if not (isinstance(e, OpAmp) and e.tags.get("accumulator")):
                    continue
                X, O = e.inn, e.out
                if not (e.inp == GND or e.inp in self.fixed) or O in mon_nodes:
                    raise ModeError(f"{e.name}: not an accumulator")
                caps = [x for x in touch[O] if isinstance(x, Capacitor) and {x.a, x.b} == {X, O}]
                resets = [x for x in touch[O] if isinstance(x, Switch) and {x.a, x.b} == {X, O}]
                others = [x for x in touch[O] if x is not e and x not in caps and x not in resets]
                if len(caps) != 1 or others:
                    raise ModeError(f"{e.name}: not an accumulator")
                c = caps[0]
                sg = 1 if c.a == X else -1
                self.fixed[X] = F0 if e.inp == GND else self.fixed[e.inp]
                self.acc[X] = {"cap": c.name, "C": Fraction(c.C), "sign": sg, "out": O,
                               "resets": [r.name for r in resets], "q": Fraction(c.C) * Fraction(c.v0) * sg,
                               "reset": False, "comps": set(), "static": F0, "t": F0}
                acc_names |= {e.name, c.name} | {r.name for r in resets}
        self.acc_of_cap = {v["cap"]: X for X, v in self.acc.items()}
        self.acc_reset_sw = {r: X for X, v in self.acc.items() for r in v["resets"]}
        self.dyn = [e for e in analog if e.name not in self.fixed_src and e.name not in acc_names]
        self.cnodes = {}
        self.adj = {}
        for e in self.dyn:
            ns = list(e.nodes())
            if isinstance(e, (VCVS, VCCS)):
                ns += [e.cp, e.cn]
            if isinstance(e, (CCCS, CCVS)):
                ns += list(self.by[e.ctrl].nodes())
            ns = sorted({n for n in ns if n != GND and n not in self.fixed})
            self.cnodes[e.name] = ns
            for n in ns:
                self.adj.setdefault(n, []).append(e.name)
            if not ns and not isinstance(e, OpAmp):
                for X, sg in ((e.a, -1), (e.b, 1)):
                    if X in self.acc:
                        if isinstance(e, Resistor):
                            self.acc[X]["static"] += sg * e.G * (self.fixed.get(e.a, F0) - self.fixed.get(e.b, F0))
                        elif isinstance(e, ISource):
                            self.acc[X]["static"] += sg * Fraction(e.I)
                        else:
                            raise ModeError(f"{e.name}: unsupported static element at an accumulator")
        self.logic = FastLogic(netlist)
        self.switches = {e.name: e for e in analog if isinstance(e, Switch)}
        self.sw_fan = {}
        for s in self.switches.values():
            self.sw_fan.setdefault(s.ctrl, []).append(s.name)
        self.closed = {n for n, s in self.switches.items() if self.logic.sig.get(s.ctrl, False) != s.invert}
        for r, X in self.acc_reset_sw.items():
            if r in self.closed:
                self.acc[X]["reset"] = True
                self.acc[X]["q"] = F0
        self.diodes = {e.name: e for e in analog if isinstance(e, Diode)}
        self.diode_on = {n for n, d in self.diodes.items() if d.on}
        self.cmps = {e.name: e for e in netlist.digital() if isinstance(e, Comparator)}
        self.pors = [e for e in netlist.digital() if isinstance(e, PowerOn)]
        self.node_mon = {}
        for c in self.cmps.values():
            for n in (c.plus, c.minus):
                self.node_mon.setdefault(n, set()).add(c.name)
        for d in self.diodes.values():
            for n in (d.a, d.b):
                self.node_mon.setdefault(n, set()).add(d.name)
        self.cap_v0 = {e.name: Fraction(e.v0) for e in analog if isinstance(e, Capacitor)}
        for e in analog:
            if isinstance(e, Inductor):
                raise ModeError("inductors are not supported by the exact hybrid simulator")
        self._cache = {}
        self.comps = {}
        self.node2comp = {}
        self.cap2comp = {}
        self._cid = 0
        self.t = F0
        self.heap = []
        self.mver = {}
        self._hc = 0
        self.dirty = set()
        self._fell_post = set()
        self.seq_active = []
        self.por_done = False
        self.events, self.jumps, self.readouts, self.records = [], [], [], []
        self.stats = {"component_modes": 0, "rebuilds": 0, "instants": 0, "micro_steps": 0, "jumps_nonzero": 0}

    # ------------------------------------------------------------ partition / rebuild
    def _active(self, name):
        e = self.by[name]
        if isinstance(e, Switch):
            return name in self.closed
        if isinstance(e, Diode):
            return name in self.diode_on
        return True

    def _rebuild(self, seeds, reason):
        seeds = {n for n in seeds if n != GND and n not in self.fixed}
        if not seeds:
            return
        self.stats["rebuilds"] += 1
        region = set(seeds)
        old = set()
        for n in seeds:
            c = self.node2comp.get(n)
            if c is not None and c not in old:
                old.add(c)
                region |= self.comps[c].nodes
        # current state of capacitors in the region
        sval = {}
        for cid in old:
            comp = self.comps[cid]
            u = comp.at(self.t)
            for name, x in zip(comp.cm.state_names, u):
                sval[name] = x
        els = set()
        for n in region:
            for name in self.adj.get(n, ()):
                if self._active(name):
                    els.add(name)
        for name in els:
            if isinstance(self.by[name], Capacitor) and name not in sval:
                sval[name] = self.cap_v0[name] if name not in self.cap2comp else sval.get(name, self.cap_v0[name])
        for cid in old:
            self._acc_flush(cid)
            comp = self.comps.pop(cid)
            for X in getattr(comp, "contrib", {}):
                self.acc[X]["comps"].discard(cid)
            for n in comp.nodes:
                if self.node2comp.get(n) == cid:
                    del self.node2comp[n]
        # union-find
        parent = {n: n for n in region}

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x
        for name in els:
            ns = self.cnodes[name]
            for n in ns[1:]:
                ra, rb = find(ns[0]), find(n)
                if ra != rb:
                    parent[ra] = rb
        groups = {}
        for name in els:
            ns = self.cnodes[name]
            if ns:
                groups.setdefault(find(ns[0]), []).append(name)
        nodes_of = {}
        for n in region:
            nodes_of.setdefault(find(n), set()).add(n)
        for root, names in groups.items():
            nodes = nodes_of[root]
            names = sorted(names)
            key = (tuple(sorted(nodes)), tuple(names))
            cm = self._cache.get(key)
            if cm is None:
                elist = [self.by[x] for x in names]
                touched = set()
                for x in elist:
                    ns = list(x.nodes())
                    if isinstance(x, (VCVS, VCCS)):
                        ns += [x.cp, x.cn]
                    touched |= {n for n in ns if n in self.fixed}
                allnodes = sorted(nodes) + sorted(touched)
                cm = ComponentMode(allnodes, elist, None, True, fixed={n: self.fixed[n] for n in touched})
                aug = [list(cm.A[i]) + [cm.b[i]] for i in range(len(cm.state_names))] + \
                      [[F0] * (len(cm.state_names) + 1)]
                pw = la.nilpotent_powers(aug, True)
                if pw is None:
                    raise ModeError("non-nilpotent component in the exact hybrid simulator")
                cm._powers = pw
                cm._aug = aug
                self._cache[key] = cm
                self.stats["component_modes"] += 1
            loc = [sval.get(x, self.cap_v0[x]) for x in cm.state_names]
            Q, plus = cm.jump(loc)
            if any(q != 0 for q in Q):
                self.stats["jumps_nonzero"] += 1
                if self.record_jumps:
                    qd = {a: q for a, q in zip(cm.aux, Q) if q != 0}
                    # impulse through the grounded source that holds each boundary node (its KCL)
                    acc_n = {}
                    for a, q in qd.items():
                        e = self.by[a]
                        terms = [(e.out, 1)] if isinstance(e, OpAmp) else [(e.a, 1), (e.b, -1)]
                        for n, sg in terms:
                            if n in self.fixed:
                                acc_n[n] = acc_n.get(n, F0) + sg * q
                    for src, n in self.fixed_src.items():
                        if n in acc_n and acc_n[n] != 0:
                            e = self.by[src]
                            qd[src] = qd.get(src, F0) - acc_n[n] * (1 if e.a == n else -1)
                    self.jumps.append({"t": fmt(self.t), "reason": reason,
                                       "Q": {a: fmt(q) for a, q in qd.items()},
                                       "s_minus": {x: fmt(v) for x, v in zip(cm.state_names, loc)},
                                       "s_plus": {x: fmt(v) for x, v in zip(cm.state_names, plus)}})
            self._cid += 1
            comp = Comp(cm, nodes, names)
            comp.anchor(self.t, plus)
            self.comps[self._cid] = comp
            if self.acc:
                contrib = {}
                for x in names:
                    e = self.by[x]
                    if isinstance(e, OpAmp):
                        continue
                    for X, sg in ((e.a, -1), (e.b, 1)):
                        if X not in self.acc:
                            continue
                        vec = self._cur_vec(cm, e)
                        contrib[X] = [a + sg * b for a, b in zip(contrib[X], vec)] if X in contrib else [sg * b for b in vec]
                        if ("j", x) in cm.col:
                            q = Q[cm.aux.index(x)]
                            if q and not self.acc[X]["reset"]:
                                self.acc[X]["q"] += sg * q
                comp.contrib = contrib
                for X in contrib:
                    self.acc[X]["comps"].add(self._cid)
            for n in nodes:
                self.node2comp[n] = self._cid
            for x in cm.state_names:
                self.cap2comp[x] = self._cid
        # nodes of the region without any active element: floating, no component
        for n in region:
            self.dirty |= self.node_mon.get(n, set())

    # ------------------------------------------------------------ evaluation
    def _comp_anchor_now(self, cid):
        comp = self.comps[cid]
        if comp.t0 != self.t:
            self._acc_flush(cid)
            comp.anchor(self.t, comp.at(self.t))
        return comp

    # ------------------------------------------------------------ accumulators
    def _cur_vec(self, cm, e):
        """Augmented local vector of the current a->b of element e in component mode cm."""
        m = len(cm.state_names)

        def vvec(n):
            if n == GND:
                return [F0] * (m + 1)
            if n in cm.fixed:
                return [F0] * m + [cm.fixed[n]]
            c = cm.col[("v", n)]
            return list(cm.F[c]) + [cm.f0[c]]
        if ("j", e.name) in cm.col:
            c = cm.col[("j", e.name)]
            return list(cm.F[c]) + [cm.f0[c]]
        if isinstance(e, Resistor):
            return [e.G * (a - b) for a, b in zip(vvec(e.a), vvec(e.b))]
        if isinstance(e, VCCS):
            return [e.gm * (a - b) for a, b in zip(vvec(e.cp), vvec(e.cn))]
        if isinstance(e, ISource):
            return [F0] * m + [Fraction(e.I)]
        raise ModeError(f"{e.name}: unsupported element at an accumulator")

    def _contrib_integral(self, comp, vec, t):
        if t == comp.t0:
            return F0
        d = t - comp.t0
        tot, p = F0, d
        for k, w in enumerate(comp.W):
            c = la.dot(vec, w, True)
            if c:
                tot += c * p / (k + 1)
            p = p * d
        return tot

    def _acc_flush(self, cid):
        comp = self.comps[cid]
        for X, vec in getattr(comp, "contrib", {}).items():
            a = self.acc[X]
            if not a["reset"]:
                a["q"] += self._contrib_integral(comp, vec, self.t)

    def _acc_static_flush(self, X):
        a = self.acc[X]
        if not a["reset"]:
            a["q"] += a["static"] * (self.t - a["t"])
        a["t"] = self.t

    def acc_charge(self, X):
        a = self.acc[X]
        if a["reset"]:
            return F0
        q = a["q"] + a["static"] * (self.t - a["t"])
        for cid in a["comps"]:
            comp = self.comps[cid]
            q += self._contrib_integral(comp, comp.contrib[X], self.t)
        return q

    def _acc_toggle(self, X):
        a = self.acc[X]
        for cid in list(a["comps"]):
            self._comp_anchor_now(cid)
        self._acc_static_flush(X)
        now_reset = any(r in self.closed for r in a["resets"])
        if now_reset:
            a["q"] = F0
        a["reset"] = now_reset

    def node_poly(self, n):
        """Polynomial (in tau from now) of a node potential, or None if indeterminate."""
        if n == GND:
            return [F0]
        if n in self.fixed:
            return [self.fixed[n]]
        cid = self.node2comp.get(n)
        if cid is None:
            return None
        comp = self._comp_anchor_now(cid)
        c = comp.cm.col[("v", n)]
        if c in comp.cm.indeterminate:
            return None
        vec = list(comp.cm.F[c]) + [comp.cm.f0[c]]
        return la.poly_trim([la.dot(vec, w, True) for w in comp.W])

    def aux_poly(self, name):
        cid = None
        e = self.by[name]
        for n in self.cnodes[name]:
            cid = self.node2comp.get(n)
            break
        if cid is None:
            return None
        comp = self._comp_anchor_now(cid)
        c = comp.cm.col.get(("j", name))
        if c is None or c in comp.cm.indeterminate:
            return None
        vec = list(comp.cm.F[c]) + [comp.cm.f0[c]]
        return la.poly_trim([la.dot(vec, w, True) for w in comp.W])

    def _mon_poly(self, name):
        if name in self.cmps:
            c = self.cmps[name]
            p, m = self.node_poly(c.plus), self.node_poly(c.minus)
            if p is None or m is None:
                return None
            return la.poly_trim(la.poly_add(p, [-x for x in m]))
        d = self.diodes[name]
        if name in self.diode_on:
            return self.aux_poly(name)
        p, m = self.node_poly(d.a), self.node_poly(d.b)
        if p is None or m is None:
            return None
        return la.poly_trim(la.poly_add(p, [-x for x in m]))

    def _want(self, name, poly):
        if name in self.cmps:
            cur = self.logic.sig[self.cmps[name].out]
            y0 = poly[0]
            if y0 > 0:
                return True
            if y0 < 0:
                return False
            # at equality the output is high during the instant; a comparator that already
            # fell in this instant's post phase follows the sign just after the instant
            if name in self._fell_post:
                return la.sign_after(poly, F0, True) > 0
            return True
        sa = la.sign_after(poly, F0, True)
        return sa >= 0 if name in self.diode_on else sa > 0

    def _next_crossing(self, name, horizon):
        poly = self._mon_poly(name)
        if poly is None or all(c == 0 for c in poly) or len(poly) <= 1:
            return None
        roots, ok = la.poly_roots_in(poly, F0, horizon, True)
        if not ok:
            raise ModeError(f"irrational crossing time for {name}")
        if name in self.cmps:
            cur = self.logic.sig[self.cmps[name].out]
            for r in roots:
                if not cur or la.sign_after(poly, r, True) < 0:
                    return r
            return None
        on = name in self.diode_on
        for r in roots:
            sa = la.sign_after(poly, r, True)
            if (on and sa < 0) or (not on and sa > 0):
                return r
        return None

    def _push(self, name, t_end):
        self.mver[name] = self.mver.get(name, 0) + 1
        r = self._next_crossing(name, t_end - self.t)
        if r is not None:
            self._hc += 1
            heapq.heappush(self.heap, (self.t + r, self._hc, name, self.mver[name]))

    # ------------------------------------------------------------ logic -> switches
    def _apply_logic(self, changes):
        started, total = self.logic.settle(changes)
        if self.log_edges:
            for k, (o, n) in total.items():
                self.events.append({"t": fmt(self.t), "type": "edge", "signal": k, "value": n})
        for s in started:
            self.seq_active.append((s, 0))
            self.events.append({"t": fmt(self.t), "type": "seq", "name": s.name})
        seeds = set()
        for k in total:
            for sw in self.sw_fan.get(k, ()):
                s = self.switches[sw]
                want = self.logic.sig[s.ctrl] != s.invert
                if want != (sw in self.closed):
                    if want:
                        self.closed.add(sw)
                    else:
                        self.closed.discard(sw)
                    if sw in self.acc_reset_sw:
                        self._acc_toggle(self.acc_reset_sw[sw])
                    else:
                        seeds |= set(self.cnodes[sw])
        if seeds:
            self.stats["micro_steps"] += 1
            self._rebuild(seeds, "logic")
        return total

    # ------------------------------------------------------------ instants
    def process_instant(self, popped, readouts, t_end):
        self.stats["instants"] += 1
        check = set(popped) | self.dirty
        self.dirty = set()
        self._fell_post = set()
        pending_snap = []
        guard = 0
        while True:
            guard += 1
            if guard > 200000:
                raise RuntimeError("event loop does not terminate")
            check |= self.dirty
            self.dirty = set()
            if self.seq_active:
                changes, nxt = {}, []
                for seq, k in self.seq_active:
                    changes.update(seq.steps[k])
                    if k + 1 < len(seq.steps):
                        nxt.append((seq, k + 1))
                self.seq_active = nxt
                self._apply_logic(changes)
                continue
            if pending_snap:
                for r in pending_snap:
                    self._snapshot(r)
                lower = {r["signal"]: False for r in pending_snap if r.get("signal")}
                pending_snap = []
                if lower:
                    self._apply_logic(lower)
                continue
            flipped = None
            for name in sorted(x for x in check if x in self.diodes):
                poly = self._mon_poly(name)
                if poly is None:
                    continue
                w = self._want(name, poly)
                if w != (name in self.diode_on):
                    flipped = name
                    break
            if flipped:
                if flipped in self.diode_on:
                    self.diode_on.discard(flipped)
                else:
                    self.diode_on.add(flipped)
                self.events.append({"t": fmt(self.t), "type": "diode", "name": flipped, "on": flipped in self.diode_on})
                self._rebuild(set(self.cnodes[flipped]) | {self.diodes[flipped].a, self.diodes[flipped].b}, "diode")
                continue
            pending = []
            for name in check:
                if name in self.cmps:
                    poly = self._mon_poly(name)
                    if poly is None:
                        continue
                    w = self._want(name, poly)
                    if w != self.logic.sig[self.cmps[name].out]:
                        pending.append((self.cmps[name].priority, "cmp", name, w))
            if not self.por_done:
                for p in self.pors:
                    pending.append((p.priority, "por", p.name, True))
            for r in readouts:
                if r["t"] == self.t and not r.get("done"):
                    pending.append((r["priority"], "read", id(r), r))
            if not pending:
                # post phase: comparators at y = 0 that fall just after this instant switch now
                cands = []
                for name in check:
                    if name in self.cmps and self.logic.sig[self.cmps[name].out] and name not in self._fell_post:
                        poly = self._mon_poly(name)
                        if poly is not None and poly[0] == 0 and la.sign_after(poly, F0, True) < 0:
                            cands.append((self.cmps[name].priority, "cmp", name, False))
                if cands:
                    pm = min(c[0] for c in cands)
                    for c in cands:
                        if c[0] == pm:
                            pending.append(c)
                            self._fell_post.add(c[2])
            if not pending:
                break
            pmin = min(p[0] for p in pending)
            batch = [p for p in pending if p[0] == pmin]
            changes = {}
            for _, kind, name, w in sorted(batch, key=lambda b: str(b[2])):
                if kind == "cmp":
                    changes[self.cmps[name].out] = w
                    self.events.append({"t": fmt(self.t), "type": "cmp", "name": name, "value": w})
                elif kind == "por":
                    self.por_done = True
                    changes[self.by[name].out] = True
                    self.events.append({"t": fmt(self.t), "type": "por", "name": name})
                elif kind == "read":
                    w["done"] = True
                    if w.get("signal"):
                        changes[w["signal"]] = True
                    pending_snap.append(w)
            if changes:
                self._apply_logic(changes)
        check |= self.dirty
        self.dirty = set()
        for name in check:
            self._push(name, t_end)

    def _snapshot(self, r):
        caps = r.get("caps")
        names = caps if caps is not None else list(self.cap2comp)
        s = {}
        for x in names:
            s[x] = self.state(x)
        self.readouts.append({"t": self.t, "label": r.get("label"), "s": s,
                              "signals": {k: self.logic.sig[k] for k in r.get("signals", ())},
                              "counters": dict(self.logic.count_val)})
        if self.record:
            self.records.append(self.full_record("readout"))

    # ------------------------------------------------------------ main loop
    def run(self, t_end, readouts=()):
        t_end = Fraction(t_end)
        rds = [dict(r) for r in readouts]
        for r in rds:
            r["t"] = Fraction(r["t"])
        self._rebuild(set(self.adj) | {n for d in self.diodes.values() for n in (d.a, d.b)}, "init")
        if self.record and self.acc:
            raise ModeError("full records need accumulators=False")
        # resolve initial diode states
        for _ in range(4 * len(self.diodes) + 1):
            flip = None
            for name in sorted(self.diodes):
                poly = self._mon_poly(name)
                if poly is not None and self._want(name, poly) != (name in self.diode_on):
                    flip = name
                    break
            if flip is None:
                break
            if flip in self.diode_on:
                self.diode_on.discard(flip)
            else:
                self.diode_on.add(flip)
            self._rebuild({self.diodes[flip].a, self.diodes[flip].b}, "init")
        self.dirty = set(self.cmps) | set(self.diodes)
        if self.record:
            self.records.append(self.full_record("post:init"))
        self.process_instant([], rds, t_end)
        while True:
            while self.heap and self.mver.get(self.heap[0][2]) != self.heap[0][3]:
                heapq.heappop(self.heap)
            cands = [t_end]
            if self.heap:
                cands.append(self.heap[0][0])
            cands += [r["t"] for r in rds if not r.get("done") and r["t"] > self.t]
            tn = min(cands)
            if tn > t_end or (tn == self.t and tn == t_end):
                break
            self.t = tn
            popped = []
            while self.heap and self.heap[0][0] == tn:
                _, _, name, ver = heapq.heappop(self.heap)
                if self.mver.get(name) == ver:
                    popped.append(name)
            if self.record:
                self.records.append(self.full_record("arrive"))
            self.process_instant(popped, rds, t_end)
            if self.t >= t_end:
                break
        return self

    # ------------------------------------------------------------ export (small runs)
    def state(self, name):
        if name in self.acc_of_cap:
            a = self.acc[self.acc_of_cap[name]]
            return self.acc_charge(self.acc_of_cap[name]) / a["C"] * a["sign"]
        comp = self.comps[self.cap2comp[name]]
        return comp.at(self.t)[comp.cm.state_local[name]]

    def full_record(self, tag):
        """Same record format as sim.Simulator (node voltages, element currents, states,
        derivatives) at the current instant, for residual audits of small runs."""
        v = {}
        for n in self.nl.nodes():
            p = self.node_poly(n)
            v[n] = None if p is None else p[0]
        v[GND] = F0
        i = {}
        for e in self.dyn:
            if isinstance(e, Resistor):
                a, b = v.get(e.a, F0) if e.a != GND else F0, v.get(e.b, F0) if e.b != GND else F0
                i[e.name] = None if a is None or b is None else e.G * (a - b)
            elif isinstance(e, Switch) and e.name not in self.closed or isinstance(e, Diode) and e.name not in self.diode_on:
                i[e.name] = F0
            elif isinstance(e, VCCS):
                i[e.name] = e.gm * (v[e.cp] - v[e.cn]) if v.get(e.cp) is not None and v.get(e.cn) is not None else None
            elif isinstance(e, (Capacitor, VSource, Switch, Diode, VCVS, CCVS, OpAmp)):
                p = self.aux_poly(e.name)
                i[e.name] = None if p is None else p[0]
            else:
                i[e.name] = None
        for e in self.dyn:
            if isinstance(e, CCCS):
                i[e.name] = None if i.get(e.ctrl) is None else e.gain * i[e.ctrl]
        acc = {}
        for e in self.dyn:
            terms = [(e.out, 1)] if isinstance(e, OpAmp) else [(e.a, 1), (e.b, -1)]
            for n, sg in terms:
                if n in self.fixed and i.get(e.name) is not None:
                    acc[n] = acc.get(n, F0) + sg * i[e.name]
        for name, n in self.fixed_src.items():
            e = self.by[name]
            sg = 1 if e.a == n else -1
            i[name] = -acc.get(n, F0) * sg
        s, ds = {}, {}
        for x, cid in self.cap2comp.items():
            comp = self._comp_anchor_now(cid)
            k = comp.cm.state_local[x]
            s[x] = comp.u0[k]
            ds[x] = comp.W[1][k] if len(comp.W) > 1 else F0
        for x in self.cap_v0:
            if x not in s:
                s[x], ds[x] = self.cap_v0[x], F0
        return {"t": fmt(self.t), "tag": tag, "closed": sorted(self.closed), "diode_on": sorted(self.diode_on),
                "v": {k: fmt(x) for k, x in v.items() if k != GND}, "i": {k: fmt(x) for k, x in i.items()},
                "s": {k: fmt(x) for k, x in s.items()}, "ds": {k: fmt(x) for k, x in ds.items()}}

    def dump(self):
        return {"netlist": self.nl.to_json(), "exact": True, "states": sorted(self.cap_v0),
                "records": self.records, "jumps": self.jumps, "events": self.events,
                "stats": dict(self.stats)}
