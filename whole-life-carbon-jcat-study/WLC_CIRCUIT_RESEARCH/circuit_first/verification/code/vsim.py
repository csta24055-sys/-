"""Independent exact re-simulator for DUMPED netlists (verifier code, V1).

Written from the element laws and the documented event semantics (topology.md sections 1/3,
netlist docstrings), NOT from the builder's solver. It reads only the JSON netlist that the
builder's engine dumps (or one built with the builder's adapter) and never imports the
builder's engine/mna/sim/linalg/audit.

Scope: exact (Fraction) networks of R, C, V, I, ideal op-amp (nullor), ideal switch, plus
boolean elements CMP, GATE, SR, DFF, CNT, SEQ, POR. No inductors, diodes or controlled sources
(the stage-A pilot/CF3 netlists contain none). Integrator-only (nilpotent) dynamics only: the
state is advanced with an exact Taylor chain u(t) = sum_k u^(k) t^k / k!, where
u^(k+1) is obtained from the SAME linear mode system with sources set to zero and the state
replaced by u^(k). Event times are exact rational roots (sympy); an irrational root raises.

Formulation (different from the builder's projector method): per mode the unknowns are
node voltages v, branch currents j of voltage-defined branches (V, closed SW, C, op-amp
output), capacitor derivatives du and node-voltage derivatives dv; equations are KCL,
branch equations, j_C = C du, and the time-derivative of every voltage-defined branch
equation. A row-reduced echelon form with the transformation matrix is cached per mode.
Impulsive re-initialisation: unknown charges Q on voltage-defined branches of the NEW
mode, new capacitor voltages u+ and node voltages v+; charge-KCL at every node,
u+ = u- + Q/C, new-mode branch equations. u+ must be unique.
"""
from __future__ import annotations

from fractions import Fraction as Fr
from math import factorial

import sympy

# ----------------------------------------------------------------- parsing


def num(x):
    if isinstance(x, bool):
        raise TypeError("bool")
    if isinstance(x, Fr):
        return x
    if isinstance(x, int):
        return Fr(x)
    if isinstance(x, float):
        raise TypeError("float value in exact verifier")
    if isinstance(x, str):
        if "/" in x:
            a, b = x.split("/")
            return Fr(int(a), int(b))
        return Fr(int(x))
    raise TypeError(repr(x))


ANALOG = ("R", "C", "V", "I", "OA", "SW", "E", "G")
UNSUPPORTED = ("L", "D", "F", "H")


class Net:
    def __init__(self, elements):
        self.els = elements
        self.by = {e["name"]: e for e in elements}
        bad = [e["name"] for e in elements if e["kind"] in UNSUPPORTED]
        if bad:
            raise ValueError(f"unsupported elements for the verifier simulator: {bad[:5]}")
        self.nodes = []
        seen = set()

        def addn(n):
            if n != "0" and n not in seen:
                seen.add(n)
                self.nodes.append(n)
        for e in elements:
            k = e["kind"]
            if k == "OA":
                for n in (e["inp"], e["inn"], e["out"]):
                    addn(n)
            elif k in ANALOG:
                addn(e["a"]); addn(e["b"])
                if k in ("E", "G"):
                    addn(e["cp"]); addn(e["cn"])
            elif k == "CMP":
                addn(e["plus"]); addn(e["minus"])
        self.nidx = {n: i for i, n in enumerate(self.nodes)}
        self.caps = [e for e in elements if e["kind"] == "C"]
        self.cidx = {e["name"]: i for i, e in enumerate(self.caps)}
        self.switches = [e for e in elements if e["kind"] == "SW"]
        self.cmps = [e for e in elements if e["kind"] == "CMP"]
        self.gates = [e for e in elements if e["kind"] == "GATE"]
        self.srs = [e for e in elements if e["kind"] == "SR"]
        self.dffs = [e for e in elements if e["kind"] == "DFF"]
        self.cnts = [e for e in elements if e["kind"] == "CNT"]
        self.seqs = [e for e in elements if e["kind"] == "SEQ"]
        self.pors = [e for e in elements if e["kind"] == "POR"]


# ----------------------------------------------------------------- exact RREF with transform


class Reduced:
    """Sparse RREF of M (rows x ncols) with the row transformation E (E M = R).
    Rows are dicts; pivot = shortest candidate row (limits fill-in). Exact Fractions."""

    def __init__(self, M, ncols):
        m = len(M)
        A = [{c: v for c, v in enumerate(r) if v != 0} for r in M]
        E = [{i: Fr(1)} for i in range(m)]
        colidx = {}
        for i, r in enumerate(A):
            for c in r:
                colidx.setdefault(c, set()).add(i)
        pivoted = [False] * m
        piv_of_row = {}
        for c in range(ncols):
            cand = [i for i in colidx.get(c, ()) if not pivoted[i]]
            if not cand:
                continue
            p = min(cand, key=lambda i: (len(A[i]), i))
            inv = 1 / A[p][c]
            A[p] = {k: v * inv for k, v in A[p].items()}
            E[p] = {k: v * inv for k, v in E[p].items()}
            for i in list(colidx.get(c, ())):
                if i == p:
                    continue
                f = A[i].get(c)
                if not f:
                    continue
                Ai, Ei = A[i], E[i]
                for k, v in A[p].items():
                    nv = Ai.get(k, 0) - f * v
                    if nv:
                        if k not in Ai:
                            colidx.setdefault(k, set()).add(i)
                        Ai[k] = nv
                    elif k in Ai:
                        del Ai[k]
                        colidx[k].discard(i)
                for k, v in E[p].items():
                    nv = Ei.get(k, 0) - f * v
                    if nv:
                        Ei[k] = nv
                    elif k in Ei:
                        del Ei[k]
            pivoted[p] = True
            piv_of_row[p] = c
        self.ncols = ncols
        self.piv_rows = piv_of_row                      # row -> pivot column
        self.nonpiv = [i for i in range(m) if not pivoted[i]]
        pivcols = set(piv_of_row.values())
        self.rank = len(pivcols)
        self.E = E
        self.free = [c for c in range(ncols) if c not in pivcols]
        free = set(self.free)
        self.det = {c: not (set(A[i]) & free) for i, c in piv_of_row.items()}

    def solve(self, rhs):
        """Particular solution (free = 0) and consistency residual."""
        def rr(i):
            return sum((v * rhs[k] for k, v in self.E[i].items() if rhs[k] != 0), Fr(0))
        incons = [x for x in (rr(i) for i in self.nonpiv) if x != 0]
        x = [Fr(0)] * self.ncols
        for i, c in self.piv_rows.items():
            x[c] = rr(i)
        return x, incons

    def determined(self, c):
        return self.det.get(c, False)


# ----------------------------------------------------------------- simulator


class VSim:
    def __init__(self, netlist_json):
        self.net = Net(netlist_json)
        n = self.net
        self.u = [num(c.get("v0", 0) or 0) for c in n.caps]
        self.t = Fr(0)
        # boolean state
        self.sig = {"ONE": True, "ZERO": False}
        for c in n.cmps:
            self.sig[c["out"]] = False
        for p in n.pors:
            self.sig[p["out"]] = False
        for s in n.srs:
            self.sig[s["q"]] = bool(s.get("init", False))
        for d in n.dffs:
            self.sig[d["q"]] = bool(d.get("init", False))
        self.cval = {c["name"]: 0 for c in n.cnts}
        for c in n.cnts:
            for k in range(c["nbits"]):
                self.sig[f"{c['prefix']}{k}"] = False
        for s in n.seqs:
            for k, v in s["idle"].items():
                self.sig[k] = bool(v)
        for g in n.gates:
            for i in g["inputs"]:
                self.sig.setdefault(i, False)
            self.sig.setdefault(g["out"], False)
        for s in n.srs:
            self.sig.setdefault(s["set"], False); self.sig.setdefault(s["reset"], False)
        for d in n.dffs:
            self.sig.setdefault(d["d"], False); self.sig.setdefault(d["clk"], False)
        for c in n.cnts:
            self.sig.setdefault(c["clk"], False)
        for s in n.seqs:
            self.sig.setdefault(s["trigger"], False)
        self._comb()
        self.active_seq = []
        self.por_done = False
        self.mode_cache = {}
        self.jump_cache = {}
        self.events = []        # (t, kind, name, value)
        self.jumps = []         # dicts
        self.snaps = []         # readout snapshots
        self.instant_states = []  # (t, tag, u-copy)
        self.heat = {}          # element -> absorbed energy (continuous)
        self.jump_energy = []   # per jump: dict
        self.n_modes = 0

    # ------------------------------------------------------------- logic
    def _gate(self, op, vals):
        return {"AND": all(vals), "OR": any(vals), "NOT": (not vals[0]) if vals else None,
                "BUF": bool(vals[0]) if vals else None, "NAND": not all(vals), "NOR": not any(vals),
                "XOR": (sum(vals) % 2 == 1)}[op]

    def _comb(self):
        for _ in range(len(self.net.gates) + 3):
            ch = False
            for g in self.net.gates:
                v = self._gate(g["op"], [self.sig[i] for i in g["inputs"]])
                if self.sig[g["out"]] != v:
                    self.sig[g["out"]] = v
                    ch = True
            if not ch:
                return
        raise RuntimeError("combinational loop")

    def settle(self, changes):
        prev = dict(self.sig)
        for k, v in changes.items():
            self.sig[k] = bool(v)
        started = []
        for _ in range(500):
            self._comb()
            rising = {k for k, v in self.sig.items() if v and not prev.get(k, False)}
            for k, v in self.sig.items():
                if prev.get(k, False) != v:
                    self.events.append((self.t, "edge", k, v))
            upd = {}
            for s in self.net.srs:
                if s["reset"] in rising:
                    upd[s["q"]] = False
                elif s["set"] in rising:
                    upd[s["q"]] = True
            for d in self.net.dffs:
                if d["clk"] in rising:
                    upd[d["q"]] = self.sig[d["d"]]
            for c in self.net.cnts:
                if c["clk"] in rising:
                    self.cval[c["name"]] = (self.cval[c["name"]] + 1) % (2 ** c["nbits"])
                    for k in range(c["nbits"]):
                        upd[f"{c['prefix']}{k}"] = bool((self.cval[c["name"]] >> k) & 1)
            for s in self.net.seqs:
                if s["trigger"] in rising:
                    started.append(s)
            prev = dict(self.sig)
            upd = {k: v for k, v in upd.items() if self.sig[k] != v}
            if not upd:
                return started
            self.sig.update(upd)
        raise RuntimeError("logic does not settle")

    # ------------------------------------------------------------- analog modes
    def closed(self):
        return frozenset(s["name"] for s in self.net.switches
                         if self.sig.get(s["ctrl"], False) != bool(s.get("invert", False)))

    def _aux(self, closed):
        out = []
        for e in self.net.els:
            k = e["kind"]
            if k in ("V", "C", "OA", "E") or (k == "SW" and e["name"] in closed):
                out.append(e)
        return out

    def mode(self, closed):
        m = self.mode_cache.get(closed)
        if m is not None:
            return m
        self.n_modes += 1
        n = self.net
        N = len(n.nodes)
        aux = self._aux(closed)
        nc = len(n.caps)
        col = {}
        for i, nd in enumerate(n.nodes):
            col[("v", nd)] = i
        for k, e in enumerate(aux):
            col[("j", e["name"])] = N + k
        for k, c in enumerate(n.caps):
            col[("du", c["name"])] = N + len(aux) + k
        base = N + len(aux) + nc
        for i, nd in enumerate(n.nodes):
            col[("dv", nd)] = base + i
        for k, e in enumerate(aux):
            col[("dj", e["name"])] = base + N + k
        ncols = base + N + len(aux)
        rows, kinds = [], []

        def row():
            rows.append([Fr(0)] * ncols)
            return rows[-1]

        kcl = {nd: row() for nd in n.nodes}
        for nd in n.nodes:
            kinds.append(("kcl", nd))

        def vc(nd, pre="v"):
            return None if nd == "0" else col[(pre, nd)]

        for e in n.els:
            k = e["kind"]
            if k == "R":
                G = num(e["G"])
                for p, q in ((e["a"], e["b"]), (e["b"], e["a"])):
                    if p == "0":
                        continue
                    kcl[p][vc(p)] += G
                    if q != "0":
                        kcl[p][vc(q)] -= G
            elif k == "G":
                gm = num(e["gm"])
                for nd_, sg in ((e["a"], 1), (e["b"], -1)):
                    if nd_ == "0":
                        continue
                    if e["cp"] != "0":
                        kcl[nd_][vc(e["cp"])] += sg * gm
                    if e["cn"] != "0":
                        kcl[nd_][vc(e["cn"])] -= sg * gm
        for e in aux:
            jc = col[("j", e["name"])]
            if e["kind"] == "OA":
                if e["out"] != "0":
                    kcl[e["out"]][jc] += 1
            else:
                if e["a"] != "0":
                    kcl[e["a"]][jc] += 1
                if e["b"] != "0":
                    kcl[e["b"]][jc] -= 1
        # branch equations (value rows) and derivative rows
        for e in aux:
            for pre in ("v", "dv"):
                r = row()
                if e["kind"] == "OA":
                    a, b = e["inp"], e["inn"]
                else:
                    a, b = e["a"], e["b"]
                if vc(a, pre) is not None:
                    r[vc(a, pre)] += 1
                if vc(b, pre) is not None:
                    r[vc(b, pre)] -= 1
                if e["kind"] == "C" and pre == "dv":
                    r[col[("du", e["name"])]] -= 1
                if e["kind"] == "E":
                    g_ = num(e["gain"])
                    if vc(e["cp"], pre) is not None:
                        r[vc(e["cp"], pre)] -= g_
                    if vc(e["cn"], pre) is not None:
                        r[vc(e["cn"], pre)] += g_
                kinds.append((pre, e["name"]))
        for c in n.caps:
            r = row()
            r[col[("j", c["name"])]] = Fr(1)
            r[col[("du", c["name"])]] = -num(c["C"])
            kinds.append(("cap", c["name"]))
        # time derivative of KCL (sources DC): sum G dv + sum dj = 0
        for nd in n.nodes:
            r = row()
            for e in n.els:
                if e["kind"] == "R":
                    G = num(e["G"])
                    for p, q in ((e["a"], e["b"]), (e["b"], e["a"])):
                        if p != nd:
                            continue
                        r[col[("dv", p)]] += G
                        if q != "0":
                            r[col[("dv", q)]] -= G
                if e["kind"] == "G":
                    gm = num(e["gm"])
                    sg = 1 if e["a"] == nd else (-1 if e["b"] == nd else 0)
                    if sg:
                        if e["cp"] != "0":
                            r[col[("dv", e["cp"])]] += sg * gm
                        if e["cn"] != "0":
                            r[col[("dv", e["cn"])]] -= sg * gm
            for e in aux:
                c = col[("dj", e["name"])]
                if e["kind"] == "OA":
                    if e["out"] == nd:
                        r[c] += 1
                else:
                    if e["a"] == nd:
                        r[c] += 1
                    if e["b"] == nd:
                        r[c] -= 1
            kinds.append(("dkcl", nd))
        red = Reduced(rows, ncols)
        for c in n.caps:
            if not red.determined(col[("du", c["name"])]):
                raise RuntimeError(f"capacitor derivative not determined in mode: {c['name']}")
        m = {"aux": aux, "col": col, "kinds": kinds, "red": red, "N": N, "ncols": ncols}
        self.mode_cache[closed] = m
        return m

    def rhs(self, m, u, homogeneous):
        n = self.net
        r = []
        for kd in m["kinds"]:
            if kd[0] == "kcl":
                nd = kd[1]
                s = Fr(0)
                if not homogeneous:
                    for e in n.els:
                        if e["kind"] == "I":
                            if e["a"] == nd:
                                s -= num(e["I"])
                            if e["b"] == nd:
                                s += num(e["I"])
                r.append(s)
            elif kd[0] == "v":
                e = n.by[kd[1]]
                if e["kind"] == "V":
                    r.append(Fr(0) if homogeneous else num(e["V"]))
                elif e["kind"] == "C":
                    r.append(u[n.cidx[e["name"]]])
                else:
                    r.append(Fr(0))
            else:
                r.append(Fr(0))
        return r

    def solve_mode(self, m, u, homogeneous=False):
        x, inc = m["red"].solve(self.rhs(m, u, homogeneous))
        if inc:
            raise RuntimeError(f"inconsistent state for mode at t={self.t}: {inc[:3]}")
        return x

    def taylor(self, m):
        """Exact chain [u^(0), u^(1), ...] and node voltage derivatives [v^(0), ...]."""
        col = m["col"]
        n = self.net
        us, vs, js = [list(self.u)], [], []
        x = self.solve_mode(m, self.u)
        for k in range(len(n.caps) + 2):
            vs.append([x[col[("v", nd)]] for nd in n.nodes])
            js.append({e["name"]: x[col[("j", e["name"])]] for e in m["aux"]})
            du = [x[col[("du", c["name"])]] for c in n.caps]
            if all(d == 0 for d in du):
                return us, vs, js
            us.append(du)
            x = self.solve_mode(m, du, homogeneous=True)
        raise RuntimeError("non-nilpotent dynamics (verifier simulator handles integrators only)")

    def vdet(self, m, nd):
        if nd == "0":
            return True
        return m["red"].determined(m["col"][("v", nd)])

    # ------------------------------------------------------------- jumps
    def jump(self, closed_new):
        n = self.net
        key = closed_new
        J = self.jump_cache.get(key)
        if J is None:
            aux = self._aux(closed_new)
            N = len(n.nodes)
            nc = len(n.caps)
            col = {}
            for k, e in enumerate(aux):
                col[("Q", e["name"])] = k
            for k, c in enumerate(n.caps):
                col[("u", c["name"])] = len(aux) + k
            for i, nd in enumerate(n.nodes):
                col[("v", nd)] = len(aux) + nc + i
            ncols = len(aux) + nc + N
            rows, kinds = [], []
            kcl = {}
            for nd in n.nodes:
                rows.append([Fr(0)] * ncols); kcl[nd] = rows[-1]; kinds.append(("kcl", nd))
            for e in aux:
                q = col[("Q", e["name"])]
                if e["kind"] == "OA":
                    if e["out"] != "0":
                        kcl[e["out"]][q] += 1
                else:
                    if e["a"] != "0":
                        kcl[e["a"]][q] += 1
                    if e["b"] != "0":
                        kcl[e["b"]][q] -= 1
            for c in n.caps:
                r = [Fr(0)] * ncols
                r[col[("u", c["name"])]] = Fr(1)
                r[col[("Q", c["name"])]] = -1 / num(c["C"])
                rows.append(r); kinds.append(("cap", c["name"]))
            for e in aux:
                r = [Fr(0)] * ncols
                a, b = (e["inp"], e["inn"]) if e["kind"] == "OA" else (e["a"], e["b"])
                if a != "0":
                    r[col[("v", a)]] += 1
                if b != "0":
                    r[col[("v", b)]] -= 1
                if e["kind"] == "C":
                    r[col[("u", e["name"])]] -= 1
                if e["kind"] == "E":
                    g_ = num(e["gain"])
                    if e["cp"] != "0":
                        r[col[("v", e["cp"])]] -= g_
                    if e["cn"] != "0":
                        r[col[("v", e["cn"])]] += g_
                rows.append(r); kinds.append(("br", e["name"]))
            # post-jump static consistency of the NEW mode with FINITE currents j+ (resistor
            # KCL included): the state after the impulse must admit a continuous solution.
            base = ncols
            for k, e in enumerate(aux):
                col[("j", e["name"])] = base + k
            ncols2 = base + len(aux)
            rows = [r + [Fr(0)] * len(aux) for r in rows]
            for nd in n.nodes:
                r = [Fr(0)] * ncols2
                for e in n.els:
                    if e["kind"] == "R":
                        G = num(e["G"])
                        for p, q in ((e["a"], e["b"]), (e["b"], e["a"])):
                            if p != nd:
                                continue
                            r[col[("v", p)]] += G
                            if q != "0":
                                r[col[("v", q)]] -= G
                    if e["kind"] == "G":
                        gm = num(e["gm"])
                        sg = 1 if e["a"] == nd else (-1 if e["b"] == nd else 0)
                        if sg:
                            if e["cp"] != "0":
                                r[col[("v", e["cp"])]] += sg * gm
                            if e["cn"] != "0":
                                r[col[("v", e["cn"])]] -= sg * gm
                for e in aux:
                    jc = col[("j", e["name"])]
                    if e["kind"] == "OA":
                        if e["out"] == nd:
                            r[jc] += 1
                    else:
                        if e["a"] == nd:
                            r[jc] += 1
                        if e["b"] == nd:
                            r[jc] -= 1
                rows.append(r); kinds.append(("skcl", nd))
            ncols = ncols2
            red = Reduced(rows, ncols)
            for c in n.caps:
                if not red.determined(col[("u", c["name"])]):
                    raise RuntimeError(f"non-unique re-initialisation of {c['name']}")
            J = {"aux": aux, "col": col, "kinds": kinds, "red": red}
            self.jump_cache[key] = J
        rhs = []
        for kd in J["kinds"]:
            if kd[0] == "kcl":
                rhs.append(Fr(0))
            elif kd[0] == "skcl":
                s = Fr(0)
                for e in n.els:
                    if e["kind"] == "I":
                        if e["a"] == kd[1]:
                            s -= num(e["I"])
                        if e["b"] == kd[1]:
                            s += num(e["I"])
                rhs.append(s)
            elif kd[0] == "cap":
                rhs.append(self.u[n.cidx[kd[1]]])
            else:
                e = n.by[kd[1]]
                rhs.append(num(e["V"]) if e["kind"] == "V" else Fr(0))
        x, inc = J["red"].solve(rhs)
        if inc:
            raise RuntimeError("no charge-conserving re-initialisation")
        col = J["col"]
        u_new = [x[col[("u", c["name"])]] for c in n.caps]
        Q = {e["name"]: x[col[("Q", e["name"])]] for e in J["aux"]}
        return u_new, Q, J

    def change_mode(self, reason, old_closed):
        new = self.closed()
        if new == old_closed and reason != "init":
            return new
        u_minus = list(self.u)
        u_new, Q, J = self.jump(new)
        if u_new != u_minus:
            n = self.net
            rec = {"t": self.t, "reason": reason, "Q": {k: v for k, v in Q.items() if v != 0},
                   "u_minus": {c["name"]: u_minus[i] for i, c in enumerate(n.caps) if u_minus[i] != u_new[i]},
                   "u_plus": {c["name"]: u_new[i] for i, c in enumerate(n.caps) if u_minus[i] != u_new[i]}}
            # exact work of independent voltage sources (fixed voltage): W_src = V * Q (absorbed)
            rec["W_vsrc_absorbed"] = sum((num(n.by[k]["V"]) * q for k, q in Q.items() if n.by[k]["kind"] == "V"), Fr(0))
            rec["dE_C"] = sum((num(c["C"]) * (u_new[i] ** 2 - u_minus[i] ** 2) / 2 for i, c in enumerate(n.caps)), Fr(0))
            rec["dE_C_by"] = {c["name"]: num(c["C"]) * (u_new[i] ** 2 - u_minus[i] ** 2) / 2
                              for i, c in enumerate(n.caps) if u_new[i] != u_minus[i]}
            rec["W_oa_by"] = {}
            # op-amp output work on the linear path (output voltage affine in transferred charge)
            m_old = self.mode(old_closed) if old_closed is not None else None
            m_new = self.mode(new)
            w_oa = Fr(0)
            oa_ok = True
            for k, q in Q.items():
                e = n.by[k]
                if e["kind"] == "OA" and q != 0:
                    if m_old is None or not self.vdet(m_old, e["out"]):
                        oa_ok = False
                        continue
                    vm = self._node_v(m_old, e["out"], u_minus)
                    self.u = u_new
                    vp = self._node_v(m_new, e["out"], u_new) if self.vdet(m_new, e["out"]) else None
                    self.u = u_minus
                    if vp is None:
                        oa_ok = False
                        continue
                    w_oa += (vm + vp) / 2 * q
                    rec["W_oa_by"][k] = (vm + vp) / 2 * q
            rec["W_opamp_absorbed_linear_path"] = w_oa if oa_ok else None
            if oa_ok:
                rec["impulsive_loss"] = -(rec["W_vsrc_absorbed"] + w_oa + rec["dE_C"])
            self.jumps.append(rec)
        self.u = u_new
        return new

    def _node_v(self, m, nd, u):
        x = self.solve_mode(m, u)
        return Fr(0) if nd == "0" else x[m["col"][("v", nd)]]

    # ------------------------------------------------------------- comparators
    def _cmp_poly(self, m, vs, c):
        """Polynomial coefficients of y = v_plus - v_minus (list, ascending powers / k!)."""
        n = self.net
        out = []
        for k, v in enumerate(vs):
            yp = Fr(0) if c["plus"] == "0" else v[n.nidx[c["plus"]]]
            ym = Fr(0) if c["minus"] == "0" else v[n.nidx[c["minus"]]]
            out.append((yp - ym) / factorial(k))
        return out

    def want(self, m, vs, c):
        p = self._cmp_poly(m, vs, c)
        for nd in (c["plus"], c["minus"]):
            if not self.vdet(m, nd):
                return None
        return p[0] >= 0

    def falls_now(self, m, vs, c):
        """True output, y(now) = 0 and y < 0 immediately after."""
        p = self._cmp_poly(m, vs, c)
        if p[0] != 0:
            return False
        for a in p[1:]:
            if a != 0:
                return a < 0
        return False

    def next_crossing(self, m, vs, h_max):
        t = sympy.Symbol("t")
        best, who = None, []
        for c in self.net.cmps:
            if not (self.vdet(m, c["plus"]) and self.vdet(m, c["minus"])):
                continue
            p = self._cmp_poly(m, vs, c)
            if all(a == 0 for a in p[1:]):
                continue
            cur = self.sig[c["out"]]
            poly = sympy.Poly(list(reversed([sympy.Rational(a.numerator, a.denominator) for a in p])), t)
            cand = None
            for r in sorted(set(poly.real_roots())):
                if not r.is_Rational:
                    if r > 0 and r <= h_max:
                        raise RuntimeError("irrational event time")
                    continue
                rr = Fr(int(r.p), int(r.q))
                if rr <= 0 or rr > h_max:
                    continue
                # sign just after the root
                dp = poly
                sa = 0
                for _ in range(poly.degree() + 1):
                    dp = dp.diff(t)
                    val = dp.eval(r)
                    if val != 0:
                        sa = 1 if val > 0 else -1
                        break
                if not cur:
                    cand = rr        # y reaches 0 -> output true
                    break
                if cur and sa < 0:
                    cand = rr
                    break
            if cand is None:
                continue
            if best is None or cand < best:
                best, who = cand, [c["name"]]
            elif cand == best:
                who.append(c["name"])
        return best, who

    # ------------------------------------------------------------- instants
    def process_instant(self, readouts):
        cur_closed = self.closed()
        guard = 0
        late_fall = set()
        pending_snap = []
        while True:
            guard += 1
            if guard > 20000:
                raise RuntimeError("instant does not terminate")
            if not self.active_seq and pending_snap:
                # readout with a control pulse: snapshot after the pulse's sequences, then lower it
                for obj in pending_snap:
                    self._snap(obj)
                low = {obj["signal"]: False for obj in pending_snap if obj.get("signal")}
                pending_snap = []
                if low:
                    self.settle(low)
                    cur_closed = self.change_mode("logic", cur_closed)
                continue
            if self.active_seq:
                ch = {}
                nxt = []
                for s, k in self.active_seq:
                    ch.update(s["steps"][k])
                    if k + 1 < len(s["steps"]):
                        nxt.append((s, k + 1))
                self.active_seq = nxt
                started = self.settle(ch)
                for s in started:
                    self.active_seq.append((s, 0))
                    self.events.append((self.t, "seq", s["name"], True))
                cur_closed = self.change_mode("seq", cur_closed)
                continue
            m = self.mode(cur_closed)
            us, vs, js = self.taylor(m)
            pending = []
            for c in self.net.cmps:
                w = self.want(m, vs, c)
                if c["name"] in late_fall:
                    w = False
                if w is not None and w != self.sig[c["out"]]:
                    pending.append((c["priority"], "cmp", c, w))
            if not self.por_done:
                for p in self.net.pors:
                    pending.append((p["priority"], "por", p, True))
            for r in readouts:
                if r["t"] == self.t and not r.get("done"):
                    pending.append((r["priority"], "read", r, None))
            if not pending:
                # physically exact: a true comparator whose input is 0 and decreasing falls at t+
                lf = {c["name"] for c in self.net.cmps if self.sig[c["out"]] and self.falls_now(m, vs, c)
                      and c["name"] not in late_fall}
                if lf:
                    late_fall |= lf
                    continue
                break
            pmin = min(p[0] for p in pending)
            batch = [p for p in pending if p[0] == pmin]
            ch = {}
            for _, kind, obj, w in batch:
                if kind == "read":
                    obj["done"] = True
                    if obj.get("signal"):
                        ch[obj["signal"]] = True
                        pending_snap.append(obj)
                    else:
                        self._snap(obj)
                elif kind == "cmp":
                    ch[obj["out"]] = w
                    self.events.append((self.t, "cmp", obj["name"], w))
                elif kind == "por":
                    ch[obj["out"]] = True
                    self.events.append((self.t, "por", obj["name"], True))
            if any(k == "por" for _, k, _, _ in batch):
                self.por_done = True
            if ch:
                started = self.settle(ch)
                for s in started:
                    self.active_seq.append((s, 0))
                    self.events.append((self.t, "seq", s["name"], True))
                cur_closed = self.change_mode("logic", cur_closed)
        self.instant_states.append((self.t, list(self.u)))

    def _snap(self, obj):
        self.snaps.append({"t": self.t, "label": obj["label"], "priority": obj["priority"],
                           "u": {c["name"]: self.u[i] for i, c in enumerate(self.net.caps)},
                           "sig": dict(self.sig), "heat": dict(self.heat), "n_jumps": len(self.jumps),
                           "counters": dict(self.cval)})

    def advance(self, m, us, vs, js, h):
        """Exact polynomial advance by h with continuous energy meters (absorbed v*i)."""
        n = self.net
        nk = len(us)
        # node voltage polys (Taylor coefficients /k!)
        def vpoly(nd):
            if nd == "0":
                return [Fr(0)]
            i = n.nidx[nd]
            return [vs[k][i] / factorial(k) for k in range(len(vs))]

        def pmul(a, b):
            out = [Fr(0)] * (len(a) + len(b) - 1)
            for i, x in enumerate(a):
                if x == 0:
                    continue
                for j, y in enumerate(b):
                    out[i + j] += x * y
            return out

        def pint(a, h):
            return sum((c * h ** (k + 1) / (k + 1) for k, c in enumerate(a)), Fr(0))
        # branch currents: resistors from Ohm on node polys; aux currents from the chain
        # (j^(k) taken from the homogeneous solves: same chain index as v)
        for e in n.els:
            k = e["kind"]
            if k == "R":
                if not (self.vdet(m, e["a"]) and self.vdet(m, e["b"])):
                    continue
                dv = [x - y for x, y in _zip_pad(vpoly(e["a"]), vpoly(e["b"]))]
                i = [num(e["G"]) * x for x in dv]
                self.heat[e["name"]] = self.heat.get(e["name"], Fr(0)) + pint(pmul(dv, i), h)
            elif k in ("V", "C", "OA", "SW") and e["name"] in js[0]:
                a, b = (e["out"], "0") if k == "OA" else (e["a"], e["b"])
                if not (self.vdet(m, a) and self.vdet(m, b)):
                    continue
                if not m["red"].determined(m["col"][("j", e["name"])]):
                    continue
                ipoly = [js[kk][e["name"]] / factorial(kk) for kk in range(len(js))]
                dv = [x - y for x, y in _zip_pad(vpoly(a), vpoly(b))]
                self.heat[e["name"]] = self.heat.get(e["name"], Fr(0)) + pint(pmul(dv, ipoly), h)
            elif k == "I":
                dv = [x - y for x, y in _zip_pad(vpoly(e["a"]), vpoly(e["b"]))]
                self.heat[e["name"]] = self.heat.get(e["name"], Fr(0)) + pint([num(e["I"]) * x for x in dv], h)
        self.u = [sum((us[k][i] * h ** k / factorial(k) for k in range(nk)), Fr(0)) for i in range(len(self.u))]
        self.t += h

    def run(self, t_end, readouts=()):
        t_end = Fr(t_end)
        rds = [{"t": Fr(r[0]), "priority": r[1], "label": r[2] if len(r) > 2 else None,
                "signal": r[3] if len(r) > 3 else None} for r in readouts]
        # initial consistent state (charge-conserving init jump, not counted in energy)
        cl = self.closed()
        u_new, Q, J = self.jump(cl)
        self.init_jump = {"Q": {k: v for k, v in Q.items() if v != 0}}
        self.u = u_new
        self.process_instant(rds)
        while self.t < t_end:
            h_max = t_end - self.t
            for r in rds:
                if not r.get("done") and r["t"] > self.t:
                    h_max = min(h_max, r["t"] - self.t)
            m = self.mode(self.closed())
            us, vs, js = self.taylor(m)
            tau, who = self.next_crossing(m, vs, h_max)
            h = tau if tau is not None else h_max
            self.advance(m, us, vs, js, h)
            self.process_instant(rds)
        return self


def _zip_pad(a, b):
    L = max(len(a), len(b))
    a = a + [Fr(0)] * (L - len(a))
    b = b + [Fr(0)] * (L - len(b))
    return zip(a, b)


def readout_C(sim, snap, gamma=Fr(1)):
    """C = gamma * sum of charges of capacitors tagged with a stage (bus + year-cell taps)."""
    by_stage = {}
    for c in sim.net.caps:
        st = (c.get("tags") or {}).get("stage")
        if st is None:
            continue
        q = num(c["C"]) * snap["u"][c["name"]]
        by_stage[st] = by_stage.get(st, Fr(0)) + gamma * q
    return sum(by_stage.values(), Fr(0)), by_stage
