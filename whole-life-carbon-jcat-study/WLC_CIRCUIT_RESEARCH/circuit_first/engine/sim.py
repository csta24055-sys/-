"""Event-driven hybrid simulation of a netlist.

Between events every mode is a linear time-invariant DAE with DC sources. Its solution
is computed in closed form: exactly (fractions.Fraction polynomials) when the state
matrix of every component is nilpotent (integrator-only networks), otherwise in floating
point via the matrix exponential (Van Loan integrals for energy meters).

Events: comparator threshold crossings (analytic roots for polynomial segments, bracketing
+ bisection for exponential segments), ideal-diode commutations, power-on, readouts.
Events at the same instant are processed in priority order; events with equal priority are
processed as a SET (one logic delta). Sequencers then run their zero-length phases in
lockstep; every switch change triggers a charge-conserving re-initialisation.

The full solution (node voltages, element currents, states, derivatives, impulse charges,
energy meters, event log) is exposed for independent auditing.
"""
from __future__ import annotations

import math
from fractions import Fraction
from math import factorial

from . import linalg as la
from .logic import Logic
from .mna import ComponentMode, ModeError, active_elements, partition
from .netlist import (GND, CCCS, VCCS, Capacitor, Comparator, Diode, Inductor, ISource,
                      OpAmp, PowerOn, Resistor, Switch)


def _conv(x, exact):
    if exact:
        if isinstance(x, float):
            raise TypeError("float value in an exact simulation")
        return Fraction(x)
    return float(x)


def fmt(x):
    if x is None:
        return None
    if isinstance(x, Fraction):
        return f"{x.numerator}/{x.denominator}" if x.denominator != 1 else str(x.numerator)
    if isinstance(x, bool):
        return x
    if isinstance(x, int):
        return str(x)
    return x


class GlobalMode:
    def __init__(self, sim, closed, diode_on):
        self.closed = frozenset(closed)
        self.diode_on = frozenset(diode_on)
        nl = sim.nl
        act = active_elements(nl, closed, diode_on)
        self.comps = []
        for nodes, els in partition(nl, act):
            key = (tuple(nodes), tuple(sorted(e.name for e in els)))
            cm = sim._comp_cache.get(key)
            if cm is None:
                cm = ComponentMode(nodes, els, None, sim.exact)
                sim._comp_cache[key] = cm
                sim.stats["component_modes"] += 1
            self.comps.append(cm)
        self.gidx = [[sim.sidx[n] for n in cm.state_names] for cm in self.comps]
        # forms: dict comp_id -> augmented local vector (len m+1), or None (indeterminate)
        ex = sim.exact
        self.node_form = {}
        self.node_form_any = {}   # includes gauge-dependent (indeterminate) potentials, free vars = 0
        self.elem_comp = {}
        for ci, cm in enumerate(self.comps):
            m = len(cm.state_names)
            for n in cm.nodes:
                c = cm.col[("v", n)]
                self.node_form_any[n] = {ci: list(cm.F[c]) + [cm.f0[c]] if m else [cm.f0[c]]}
                if c in cm.indeterminate:
                    self.node_form[n] = None
                else:
                    self.node_form[n] = {ci: list(cm.F[c]) + [cm.f0[c]] if m else [cm.f0[c]]}
            for e in cm.elements:
                self.elem_comp[e.name] = ci
        self.cur_form = {}
        Z = la.zero_like(ex)
        for e in nl.analog():
            self.cur_form[e.name] = self._current_form(sim, e)
        # augmented dynamics per component
        self.Aaug = []
        self.powers = []
        for cm in self.comps:
            m = len(cm.state_names)
            Aa = [list(cm.A[i]) + [cm.b[i]] for i in range(m)] + [[Z] * (m + 1)]
            self.Aaug.append(Aa)
            if ex:
                pw = getattr(cm, "_powers", None)
                if pw is None:
                    pw = la.nilpotent_powers(Aa, True)
                    if pw is None:
                        raise ModeError("non-nilpotent dynamics in an exact simulation; use exact=False")
                    cm._powers = pw
                self.powers.append(pw)

    def _current_form(self, sim, e):
        ex = sim.exact
        if e.name not in self.elem_comp:
            return {}  # inactive (open switch / off diode) or isolated: zero current
        ci = self.elem_comp[e.name]
        cm = self.comps[ci]
        m = len(cm.state_names)
        if ("j", e.name) in cm.col:
            c = cm.col[("j", e.name)]
            if c in cm.indeterminate:
                return None
            return {ci: (list(cm.F[c]) + [cm.f0[c]]) if m else [cm.f0[c]]}
        if isinstance(e, Resistor):
            return self._lin([(e.a, e.G), (e.b, -e.G)], ex)
        if isinstance(e, ISource):
            v = [la.zero_like(ex)] * m + [e.I]
            return {ci: v}
        if isinstance(e, Inductor):
            v = [la.zero_like(ex)] * (m + 1)
            v[cm.state_local[e.name]] = la.one_like(ex)
            return {ci: v}
        if isinstance(e, VCCS):
            return self._lin([(e.cp, e.gm), (e.cn, -e.gm)], ex)
        if isinstance(e, CCCS):
            ctrl = sim.nl.by_name[e.ctrl]
            f = self._current_form(sim, ctrl)
            if f is None:
                return None
            return {k: [x * e.gain for x in v] for k, v in f.items()}
        return {}

    def _lin(self, terms, ex):
        out = {}
        for node, coef in terms:
            if node == GND:
                continue
            f = self.node_form.get(node)
            if f is None:
                return None
            for k, v in f.items():
                if k in out:
                    out[k] = [a + coef * b for a, b in zip(out[k], v)]
                else:
                    out[k] = [coef * b for b in v]
        return out

    def vform(self, a, b, ex):
        return self._lin([(a, la.one_like(ex)), (b, -la.one_like(ex))], ex)

    def vform_any(self, a, b, ex):
        """Voltage a-b using a fixed particular solution for floating potentials (gauge)."""
        out = {}
        for node, coef in ((a, la.one_like(ex)), (b, -la.one_like(ex))):
            if node == GND:
                continue
            f = self.node_form_any.get(node)
            if f is None:
                return None
            for k, v in f.items():
                out[k] = [x + coef * y for x, y in zip(out[k], v)] if k in out else [coef * y for y in v]
        return out


class Solution:
    """Container of everything produced by a run (exposed for auditing)."""

    def __init__(self):
        self.records = []
        self.jumps = []
        self.events = []
        self.readouts = []
        self.meters_cont = {}
        self.meters_jump = {}
        self.charge_cont = {}
        self.charge_jump = {}
        self.inexact_events = 0


class Simulator:
    def __init__(self, netlist, exact=True, scan_step=None, record=True, record_midpoints=True):
        self.nl = netlist
        self.exact = exact
        self.scan_step = scan_step
        self.record = record
        self.record_midpoints = record_midpoints
        self.stats = {"component_modes": 0, "global_modes": 0, "segments": 0, "instants": 0,
                      "micro_steps": 0, "jumps_nonzero": 0}
        self.state_els = netlist.states()
        self.snames = [e.name for e in self.state_els]
        self.sidx = {n: i for i, n in enumerate(self.snames)}
        self.s = []
        for e in self.state_els:
            self.s.append(_conv(e.v0 if isinstance(e, Capacitor) else e.i0, exact))
        self.logic = Logic(netlist)
        self.comparators = [e for e in netlist.digital() if isinstance(e, Comparator)]
        self.pors = [e for e in netlist.digital() if isinstance(e, PowerOn)]
        self.switches = [e for e in netlist.analog() if isinstance(e, Switch)]
        self.diodes = [e for e in netlist.analog() if isinstance(e, Diode)]
        self.diode_on = {d.name for d in self.diodes if d.on}
        self._comp_cache = {}
        self._mode_cache = {}
        self.sol = Solution()
        for e in netlist.analog():
            self.sol.meters_cont[e.name] = la.zero_like(exact)
            self.sol.meters_jump[e.name] = la.zero_like(exact)
            self.sol.charge_cont[e.name] = la.zero_like(exact)
            self.sol.charge_jump[e.name] = la.zero_like(exact)
        self.t = _conv(0, exact)
        self.seq_active = []
        self.por_done = False
        self.mode = None

    # ------------------------------------------------------------ mode handling
    def closed_set(self):
        return {s.name for s in self.switches if self.logic.sig.get(s.ctrl, False) != s.invert}

    def get_mode(self, closed, diode_on):
        key = (frozenset(closed), frozenset(diode_on))
        m = self._mode_cache.get(key)
        if m is None:
            m = GlobalMode(self, closed, diode_on)
            self._mode_cache[key] = m
            self.stats["global_modes"] += 1
        return m

    def local_aug(self, mode, ci, s=None):
        s = self.s if s is None else s
        return [s[g] for g in mode.gidx[ci]] + [la.one_like(self.exact)]

    def evalf(self, form, mode, s=None):
        if form is None:
            return None
        v = la.zero_like(self.exact)
        for ci, vec in form.items():
            v = v + la.dot(vec, self.local_aug(mode, ci, s), self.exact)
        return v

    def change_mode(self, reason):
        """Switch to the mode implied by logic/diodes with charge-conserving re-init."""
        new = self.get_mode(self.closed_set(), self.diode_on)
        old = self.mode
        if old is new:
            return
        s_minus = list(self.s)
        ex = self.exact
        jump_rec = None
        total_Q = {}
        for ci, cm in enumerate(new.comps):
            loc = [s_minus[g] for g in new.gidx[ci]]
            Q, loc_plus = cm.jump(loc)
            if any(not la.is_zero(q, ex) for q in Q):
                for name, q in zip(cm.aux, Q):
                    if not la.is_zero(q, ex):
                        total_Q[name] = q
                for g, v in zip(new.gidx[ci], loc_plus):
                    self.s[g] = v
        if total_Q:
            self.stats["jumps_nonzero"] += 1
            # energies on a linear transfer path: W_k = avg(v-, v+) * Q_k
            W = {}
            gauge = []
            for name, q in total_Q.items():
                e = self.nl.by_name[name]
                if isinstance(e, Capacitor):
                    k = self.sidx[name]
                    vm, vp = s_minus[k], self.s[k]
                else:
                    a, b = (e.out, GND) if isinstance(e, OpAmp) else (e.a, e.b)
                    vm = self.evalf(old.vform(a, b, ex), old, s_minus) if old else None
                    vp = self.evalf(new.vform(a, b, ex), new)
                    if old is not None and (vm is None or vp is None):
                        gauge.append(name)
                        vm = self.evalf(old.vform_any(a, b, ex), old, s_minus)
                        vp = self.evalf(new.vform_any(a, b, ex), new)
                if vm is None or vp is None:
                    W[name] = None
                else:
                    W[name] = (vm + vp) / 2 * q
                if reason == "init":
                    continue          # energy/charge accounting starts after initialisation
                self.sol.charge_jump[name] = self.sol.charge_jump[name] + q
                if W[name] is not None:
                    self.sol.meters_jump[name] = self.sol.meters_jump[name] + W[name]
            sw_loss = None
            if all(W[n] is not None for n in W if isinstance(self.nl.by_name[n], (Switch, Diode))):
                sw_loss = sum((W[n] for n in W if isinstance(self.nl.by_name[n], (Switch, Diode))),
                              la.zero_like(ex))
            stored = la.zero_like(ex)
            for i, e in enumerate(self.state_els):
                if isinstance(e, Capacitor):
                    stored = stored + e.C * (self.s[i] * self.s[i] - s_minus[i] * s_minus[i]) / 2
            jump_rec = {"t": fmt(self.t), "reason": reason,
                        "Q": {k: fmt(v) for k, v in total_Q.items()},
                        "W_absorbed": {k: fmt(v) for k, v in W.items()},
                        "switch_loss_linear_path": fmt(sw_loss),
                        "gauge_dependent_terms": gauge,
                        "delta_stored_C": fmt(stored),
                        "s_minus": {self.snames[i]: fmt(v) for i, v in enumerate(s_minus) if v != self.s[i]},
                        "s_plus": {self.snames[i]: fmt(v) for i, v in enumerate(self.s) if v != s_minus[i]}}
            self.sol.jumps.append(jump_rec)
        self.mode = new
        self.stats["micro_steps"] += 1
        if self.record:
            self._record("post:" + reason)

    # ------------------------------------------------------------ records
    def _record(self, tag, s=None, t=None, mode=None):
        mode = mode or self.mode
        s = self.s if s is None else s
        t = self.t if t is None else t
        ex = self.exact
        rec = {"t": fmt(t), "tag": tag,
               "closed": sorted(mode.closed), "diode_on": sorted(mode.diode_on),
               "v": {}, "i": {}, "s": {}, "ds": {}}
        for n in self.nl.nodes():
            f = mode.node_form.get(n)
            rec["v"][n] = fmt(self.evalf(f, mode, s)) if f is not None else None
        for e in self.nl.analog():
            if isinstance(e, OpAmp):
                rec["i"][e.name] = fmt(self.evalf(mode.cur_form[e.name], mode, s))
            else:
                rec["i"][e.name] = fmt(self.evalf(mode.cur_form[e.name], mode, s))
        for ci, cm in enumerate(mode.comps):
            loc = self.local_aug(mode, ci, s)
            for k, name in enumerate(cm.state_names):
                rec["ds"][name] = fmt(la.dot(list(cm.A[k]) + [cm.b[k]], loc, ex))
        for i, n in enumerate(self.snames):
            rec["s"][n] = fmt(s[i])
            rec["ds"].setdefault(n, fmt(la.zero_like(ex)))
        self.sol.records.append(rec)

    # ------------------------------------------------------------ monitors
    def monitors(self):
        """List of (kind, obj, form) for every comparator and diode in the current mode."""
        ex = self.exact
        out = []
        for c in self.comparators:
            out.append(("cmp", c, self.mode.vform(c.plus, c.minus, ex)))
        for d in self.diodes:
            if d.name in self.diode_on:
                out.append(("don", d, self.mode.cur_form[d.name]))
            else:
                out.append(("doff", d, self.mode.vform(d.a, d.b, ex)))
        return out

    def _derivs_now(self, form, kmax=4):
        """[y, y', y'', ...] at the current instant."""
        ex = self.exact
        res = []
        vecs = {ci: self.local_aug(self.mode, ci) for ci in form}
        for k in range(kmax):
            v = la.zero_like(ex)
            for ci, vec in form.items():
                v = v + la.dot(vec, vecs[ci], ex)
            res.append(v)
            vecs = {ci: la.matvec(self.mode.Aaug[ci], vecs[ci], ex) for ci in vecs}
        return res

    def _sign_after_now(self, form):
        ds = self._derivs_now(form)
        tol = 0 if self.exact else 1e-12 * max(1.0, max(abs(float(x)) for x in ds))
        for x in ds:
            if abs(x) > tol:
                return 1 if x > 0 else -1
        return 0

    def want_now(self, kind, obj, form):
        """Desired monitor state at the current instant (None if form indeterminate)."""
        if form is None:
            return None
        if kind == "cmp":
            ds = self._derivs_now(form, 1)
            y = ds[0]
            return y >= 0
        if kind == "don":
            return self._sign_after_now(form) >= 0
        if kind == "doff":
            return self._sign_after_now(form) > 0

    # ------------------------------------------------------------ instant processing
    def process_instant(self, readouts, forced=()):
        self.stats["instants"] += 1
        if self.record:
            self._record("arrive")
        forced = set(forced)
        guard = 0
        while True:
            guard += 1
            if guard > 100000:
                raise RuntimeError("event loop does not terminate")
            if self.seq_active:
                changes = {}
                nxt = []
                for seq, k in self.seq_active:
                    changes.update(seq.steps[k])
                    if k + 1 < len(seq.steps):
                        nxt.append((seq, k + 1))
                self.seq_active = nxt
                started, edges = self.logic.settle(changes)
                self._log_edges(edges)
                for s in started:
                    self.seq_active.append((s, 0))
                    self.sol.events.append({"t": fmt(self.t), "type": "seq", "name": s.name})
                self.change_mode("seq")
                continue
            # diode consistency first (physical commutation)
            flipped = False
            for kind, obj, form in self.monitors():
                if kind in ("don", "doff"):
                    w = self.want_now(kind, obj, form)
                    if obj.name in forced:
                        w = (kind == "doff")
                        forced.discard(obj.name)
                    if w is not None and w != (kind == "don"):
                        if kind == "don":
                            self.diode_on.discard(obj.name)
                        else:
                            self.diode_on.add(obj.name)
                        self.sol.events.append({"t": fmt(self.t), "type": "diode", "name": obj.name, "on": kind == "doff"})
                        flipped = True
                        break
            if flipped:
                self.change_mode("diode")
                continue
            pending = []
            for kind, obj, form in self.monitors():
                if kind == "cmp":
                    w = self.want_now(kind, obj, form)
                    if obj.name in forced:
                        w = not self.logic.sig[obj.out]
                    if w is not None and w != self.logic.sig[obj.out]:
                        pending.append((obj.priority, "cmp", obj, w))
            if not self.por_done:
                for p in self.pors:
                    pending.append((p.priority, "por", p, True))
            for r in readouts:
                if r["t"] == self.t and not r.get("done"):
                    pending.append((r["priority"], "read", r, None))
            if not pending:
                break
            pmin = min(p[0] for p in pending)
            batch = [p for p in pending if p[0] == pmin]
            changes = {}
            for _, kind, obj, w in batch:
                if kind == "read":
                    obj["done"] = True
                    self._readout(obj)
                elif kind == "cmp":
                    changes[obj.out] = w
                    forced.discard(obj.name)
                    self.sol.events.append({"t": fmt(self.t), "type": "cmp", "name": obj.name, "value": w, "priority": obj.priority})
                elif kind == "por":
                    changes[obj.out] = True
                    self.sol.events.append({"t": fmt(self.t), "type": "por", "name": obj.name})
            if any(k == "por" for _, k, _, _ in batch):
                self.por_done = True
            if changes:
                started, edges = self.logic.settle(changes)
                self._log_edges(edges)
                for s in started:
                    self.seq_active.append((s, 0))
                    self.sol.events.append({"t": fmt(self.t), "type": "seq", "name": s.name})
                self.change_mode("logic")

    def _log_edges(self, edges):
        for k, v in edges:
            self.sol.events.append({"t": fmt(self.t), "type": "edge", "signal": k, "value": v})

    def _readout(self, r):
        snap = {"t": fmt(self.t), "label": r.get("label"), "priority": r["priority"],
                "s": {n: self.s[i] for i, n in enumerate(self.snames)},
                "signals": dict(self.logic.sig),
                "counters": dict(self.logic.count_val),
                "meters_cont": dict(self.sol.meters_cont), "meters_jump": dict(self.sol.meters_jump),
                "charge_cont": dict(self.sol.charge_cont), "charge_jump": dict(self.sol.charge_jump)}
        self.sol.readouts.append(snap)
        if self.record:
            self._record("readout:" + str(r.get("label")))

    # ------------------------------------------------------------ continuous evolution
    def _segment_polys(self):
        """Exact: per component, list of coefficient vectors w_k with u(tau)=sum w_k tau^k."""
        out = []
        for ci in range(len(self.mode.comps)):
            u0 = self.local_aug(self.mode, ci)
            ws = []
            for k, P in enumerate(self.mode.powers[ci]):
                ws.append([x / factorial(k) for x in la.matvec(P, u0, True)])
            out.append(ws)
        return out

    def _poly_of(self, form, W):
        p = [Fraction(0)]
        for ci, vec in form.items():
            for k, wk in enumerate(W[ci]):
                c = la.dot(vec, wk, True)
                if k < len(p):
                    p[k] = p[k] + c
                else:
                    p.append(c)
        return la.poly_trim(p)

    def next_crossing_exact(self, h_max, W):
        best, who, inexact = None, [], False
        for kind, obj, form in self.monitors():
            if form is None:
                continue
            p = self._poly_of(form, W)
            if all(c == 0 for c in p):
                continue
            roots, ok = la.poly_roots_in(p, Fraction(0), h_max, True)
            cur = self.logic.sig[obj.out] if kind == "cmp" else (kind == "don")
            tstar = None
            for r in roots:
                if kind == "cmp" and not cur:
                    tstar = r
                    break
                sa = la.sign_after(p, r, True)
                if kind == "cmp" and cur and sa < 0:
                    tstar = r
                    break
                if kind == "don" and sa < 0:
                    tstar = r
                    break
                if kind == "doff" and sa > 0:
                    tstar = r
                    break
            if tstar is None:
                continue
            if best is None or tstar < best:
                best, who, inexact = tstar, [obj.name], (not ok)
            elif tstar == best:
                who.append(obj.name)
                inexact = inexact or (not ok)
        return best, who, inexact

    def _propagate_float(self, h):
        out = []
        for ci in range(len(self.mode.comps)):
            Aa = self.mode.Aaug[ci]
            E = la.expm_float([[x * h for x in r] for r in Aa])
            out.append(la.matvec(E, self.local_aug(self.mode, ci), False))
        return out

    def _eval_at_float(self, form, us):
        v = 0.0
        for ci, vec in form.items():
            v += la.dot(vec, us[ci], False)
        return v

    def next_crossing_float(self, h_max):
        step = self.scan_step or (h_max / 200 if h_max > 0 else h_max)
        mons = [(k, o, f) for k, o, f in self.monitors() if f is not None and f]

        def state_at(tau):
            return self._propagate_float(tau)

        def cond(kind, obj, form, us, cur):
            y = self._eval_at_float(form, us)
            if kind == "cmp":
                return (y >= 0) != cur
            if kind == "don":
                return y < 0
            return y > 0

        prev_tau = 0.0
        tau = 0.0
        while tau < h_max:
            tau = min(h_max, tau + step)
            us = state_at(tau)
            hits = []
            for kind, obj, form in mons:
                cur = self.logic.sig[obj.out] if kind == "cmp" else None
                if cond(kind, obj, form, us, cur):
                    hits.append((kind, obj, form, cur))
            if hits:
                lo, hi = prev_tau, tau
                for _ in range(80):
                    mid = (lo + hi) / 2
                    um = state_at(mid)
                    if any(cond(k, o, f, um, c) for k, o, f, c in hits):
                        hi = mid
                    else:
                        lo = mid
                    if hi - lo <= 1e-15 * max(1.0, hi):
                        break
                uh = state_at(hi)
                who = [o.name for k, o, f, c in hits if cond(k, o, f, uh, c)]
                return hi, who, True
            prev_tau = tau
        return None, [], False

    def advance(self, h):
        """Move the continuous state by h, integrating energy/charge meters."""
        self.stats["segments"] += 1
        ex = self.exact
        mode = self.mode
        if h == 0:
            return
        if ex:
            W = self._segment_polys()
            for e in self.nl.analog():
                fi = mode.cur_form[e.name]
                if not fi:
                    continue
                pi = self._poly_of(fi, W)
                if isinstance(e, OpAmp):
                    fv = mode.vform(e.out, GND, True)
                else:
                    fv = mode.vform(e.a, e.b, True)
                if fv is None:
                    raise ModeError(f"indeterminate voltage across current-carrying {e.name}")
                pv = self._poly_of(fv, W) if fv else [Fraction(0)]
                self.sol.meters_cont[e.name] += la.poly_integral(la.poly_mul(pv, pi), h)
                self.sol.charge_cont[e.name] += la.poly_integral(pi, h)
            if self.record and self.record_midpoints:
                smid = list(self.s)
                for ci in range(len(mode.comps)):
                    for j, g in enumerate(mode.gidx[ci]):
                        smid[g] = sum((W[ci][k][j] * (h / 2) ** k for k in range(len(W[ci]))), Fraction(0))
                self._record("mid", s=smid, t=self.t + h / 2)
            for ci in range(len(mode.comps)):
                for j, g in enumerate(mode.gidx[ci]):
                    self.s[g] = sum((W[ci][k][j] * h ** k for k in range(len(W[ci]))), Fraction(0))
        else:
            if self.record and self.record_midpoints:
                um = self._propagate_float(h / 2)
                smid = list(self.s)
                for ci in range(len(mode.comps)):
                    for j, g in enumerate(mode.gidx[ci]):
                        smid[g] = um[ci][j]
                self._record("mid", s=smid, t=self.t + h / 2)
            # sub-steps keep ||A|| h small (Van Loan integrals lose precision otherwise)
            nsub = 1
            for Aa in mode.Aaug:
                if Aa:
                    nrm = max(sum(abs(x) for x in r) for r in Aa)
                    nsub = max(nsub, int(math.ceil(nrm * h / 0.5)))
            hs = h / nsub
            for _ in range(nsub):
                self._float_step(hs)
        self.t = self.t + h

    def _float_step(self, h):
        mode = self.mode
        for ci, cm in enumerate(mode.comps):
            Aa = mode.Aaug[ci]
            m1 = len(Aa)
            u0 = self.local_aug(mode, ci)
            big = [[(Aa[i][j] * h if j < m1 else (h if j - m1 == i else 0.0)) for j in range(2 * m1)] for i in range(m1)] + \
                  [[0.0] * (2 * m1) for _ in range(m1)]
            Eb = la.expm_float(big)
            Phi_int = [row[m1:] for row in Eb[:m1]]
            uint = la.matvec(Phi_int, u0, False)
            for e in cm.elements:
                fi = mode.cur_form[e.name]
                if not fi:
                    continue
                if isinstance(e, OpAmp):
                    fv = mode.vform(e.out, GND, False)
                else:
                    fv = mode.vform(e.a, e.b, False)
                a = fv.get(ci, [0.0] * m1) if fv else [0.0] * m1
                b = fi.get(ci, [0.0] * m1)
                self.sol.charge_cont[e.name] += la.dot(b, uint, False)
                Wm = [[(a[i] * b[j] + b[i] * a[j]) / 2 for j in range(m1)] for i in range(m1)]
                vl = [[0.0] * (2 * m1) for _ in range(2 * m1)]
                for i in range(m1):
                    for j in range(m1):
                        vl[i][j] = -Aa[j][i] * h
                        vl[i][m1 + j] = Wm[i][j] * h
                        vl[m1 + i][m1 + j] = Aa[i][j] * h
                Ev = la.expm_float(vl)
                F12 = [row[m1:] for row in Ev[:m1]]
                F22 = [row[m1:] for row in Ev[m1:]]
                G = la.matmul([list(r) for r in zip(*F22)], F12, False)
                self.sol.meters_cont[e.name] += la.dot(u0, la.matvec(G, u0, False), False)
        us = self._propagate_float(h)
        for ci in range(len(mode.comps)):
            for j, g in enumerate(mode.gidx[ci]):
                self.s[g] = us[ci][j]

    # ------------------------------------------------------------ main loop
    def run(self, t_end, readouts=(), sample_times=()):
        ex = self.exact
        t_end = _conv(t_end, ex)
        rds = [{"t": _conv(r[0], ex), "priority": r[1], "label": r[2] if len(r) > 2 else None}
               for r in readouts]
        samples = sorted({_conv(x, ex) for x in sample_times})
        # initial mode with consistent initialisation (logged as a jump if needed)
        # initial ideal-diode states consistent with the initial states (no record yet)
        rec, self.record = self.record, False
        for _ in range(4 * len(self.diodes) + 1):
            self.mode = None
            self.mode = self.get_mode(self.closed_set(), self.diode_on)
            flip = None
            for kind, obj, form in self.monitors():
                if kind in ("don", "doff"):
                    w = self.want_now(kind, obj, form)
                    if w is not None and w != (kind == "don"):
                        flip = (kind, obj)
                        break
            if flip is None:
                break
            if flip[0] == "don":
                self.diode_on.discard(flip[1].name)
            else:
                self.diode_on.add(flip[1].name)
        self.record = rec
        self.mode = None
        self.change_mode("init")
        self.process_instant(rds)
        while self.t < t_end:
            h_max = t_end - self.t
            for r in rds:
                if not r.get("done") and r["t"] > self.t:
                    h_max = min(h_max, r["t"] - self.t)
            for x in samples:
                if x > self.t:
                    h_max = min(h_max, x - self.t)
                    break
            if ex:
                W = self._segment_polys()
                tau, who, inexact = self.next_crossing_exact(h_max, W)
            else:
                tau, who, inexact = self.next_crossing_float(h_max)
            forced = ()
            if tau is not None and tau <= h_max:
                h = tau
                if inexact:
                    self.sol.inexact_events += 1
                    forced = who
            else:
                h = h_max
            self.advance(h)
            self.process_instant(rds, forced)
        return self.sol

    # ------------------------------------------------------------ export
    def dump(self):
        sol = self.sol
        return {"netlist": self.nl.to_json(),
                "exact": self.exact,
                "states": self.snames,
                "records": sol.records,
                "jumps": sol.jumps,
                "events": [{k: fmt(v) if not isinstance(v, str) else v for k, v in e.items()} for e in sol.events],
                "meters": {"absorbed_energy_continuous": {k: fmt(v) for k, v in sol.meters_cont.items()},
                           "absorbed_energy_jumps_linear_path": {k: fmt(v) for k, v in sol.meters_jump.items()},
                           "charge_continuous": {k: fmt(v) for k, v in sol.charge_cont.items()},
                           "charge_jumps": {k: fmt(v) for k, v in sol.charge_jump.items()}},
                "readouts": [{"t": r["t"], "label": r["label"], "priority": r["priority"],
                              "s": {k: fmt(v) for k, v in r["s"].items()},
                              "counters": r["counters"]} for r in sol.readouts],
                "stats": dict(self.stats, inexact_events=sol.inexact_events)}
