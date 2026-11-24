"""Boolean control layer: gates, edge-triggered latches/flip-flops/counters, sequencers.

Only booleans are read and written here (the counter holds an integer that is exposed
only as its bits). Synchronous semantics: within one delta cycle all edge-triggered
elements sample their inputs before any of them updates.
"""
from __future__ import annotations

from .netlist import DFF, Comparator, Counter, Gate, PowerOn, Sequencer, SRLatch


def _gate(op, vals):
    if op == "AND":
        return all(vals)
    if op == "OR":
        return any(vals)
    if op == "NOT":
        return not vals[0]
    if op == "BUF":
        return bool(vals[0])
    if op == "XOR":
        return sum(1 for v in vals if v) % 2 == 1
    if op == "NAND":
        return not all(vals)
    if op == "NOR":
        return not any(vals)
    raise ValueError(op)


class Logic:
    def __init__(self, netlist):
        self.sig = {"ONE": True, "ZERO": False}
        self.gates = [e for e in netlist.digital() if isinstance(e, Gate)]
        self.latches = [e for e in netlist.digital() if isinstance(e, SRLatch)]
        self.dffs = [e for e in netlist.digital() if isinstance(e, DFF)]
        self.counters = [e for e in netlist.digital() if isinstance(e, Counter)]
        self.seqs = [e for e in netlist.digital() if isinstance(e, Sequencer)]
        self.count_val = {c.name: 0 for c in self.counters}
        self.bool_ops = 0  # number of gate evaluations (boolean, for the audit)
        for e in netlist.digital():
            if isinstance(e, Comparator):
                self.sig.setdefault(e.out, False)
            elif isinstance(e, PowerOn):
                self.sig.setdefault(e.out, False)
            elif isinstance(e, SRLatch):
                self.sig[e.q] = bool(e.init)
            elif isinstance(e, DFF):
                self.sig[e.q] = bool(e.init)
            elif isinstance(e, Counter):
                for k in range(e.nbits):
                    self.sig[f"{e.prefix}{k}"] = False
            elif isinstance(e, Sequencer):
                for s, v in e.idle.items():
                    self.sig[s] = bool(v)
        for g in self.gates:
            for i in g.inputs:
                self.sig.setdefault(i, False)
            self.sig.setdefault(g.out, False)
        for l in self.latches:
            self.sig.setdefault(l.set, False)
            self.sig.setdefault(l.reset, False)
        for d in self.dffs:
            self.sig.setdefault(d.d, False)
            self.sig.setdefault(d.clk, False)
        for c in self.counters:
            self.sig.setdefault(c.clk, False)
        for s in self.seqs:
            self.sig.setdefault(s.trigger, False)
        self._comb()

    def _comb(self):
        for _ in range(len(self.gates) + 5):
            changed = False
            for g in self.gates:
                v = _gate(g.op, [self.sig[i] for i in g.inputs])
                self.bool_ops += 1
                if self.sig[g.out] != v:
                    self.sig[g.out] = v
                    changed = True
            if not changed:
                return
        raise RuntimeError("combinational loop does not settle")

    def settle(self, changes):
        """Apply source-signal changes; return (list of started sequencers, list of edges)."""
        prev = dict(self.sig)
        for k, v in changes.items():
            self.sig[k] = bool(v)
        started = []
        edges = []
        for _ in range(1000):
            self._comb()
            rising = {k for k, v in self.sig.items() if v and not prev.get(k, False)}
            for k, v in self.sig.items():
                if prev.get(k, False) != v:
                    edges.append((k, v))
            updates = {}
            for l in self.latches:
                if l.reset in rising:
                    updates[l.q] = False
                elif l.set in rising:
                    updates[l.q] = True
            for d in self.dffs:
                if d.clk in rising:
                    updates[d.q] = self.sig[d.d]
            for c in self.counters:
                if c.clk in rising:
                    self.count_val[c.name] = (self.count_val[c.name] + 1) % (2 ** c.nbits)
                    for k in range(c.nbits):
                        updates[f"{c.prefix}{k}"] = bool((self.count_val[c.name] >> k) & 1)
            for s in self.seqs:
                if s.trigger in rising:
                    started.append(s)
            prev = dict(self.sig)
            upd = {k: v for k, v in updates.items() if self.sig[k] != v}
            if not upd:
                return started, edges
            for k, v in upd.items():
                self.sig[k] = v
        raise RuntimeError("logic does not settle")
