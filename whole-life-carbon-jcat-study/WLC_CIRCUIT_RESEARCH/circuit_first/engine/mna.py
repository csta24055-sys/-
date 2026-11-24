"""Modified nodal analysis of one switching mode, per connected component.

For a fixed mode (switch positions, diode states) the network is linear. Capacitors are
written as voltage-defined branches whose value is the state u_k (capacitor voltage),
inductors as current-defined branches whose value is the state i_k. Then

    M z = r0 + R s          (z = node voltages + auxiliary branch currents)

Left null vectors l of M give algebraic constraints on the states (capacitor loops with
voltage-defined branches, e.g. C parallel to a source or a virtual ground); right null
vectors are undetermined unknowns (circulating loop currents, floating nodes). The loop
currents are fixed by requiring that the constraints remain satisfied (d/dt of the
constraint = 0, sources are DC). Result: affine maps z = F s + f0 and s' = A s + b.

Impulsive re-initialisation at a mode change: impulse charges Q on the auxiliary
(current-unknown) branches must satisfy KCL (charge conservation at every node, with
controlled-source current relations) and bring the states onto the new constraint set.
"""
from __future__ import annotations

from fractions import Fraction

from . import linalg as la
from .netlist import (GND, CCCS, CCVS, VCCS, VCVS, Capacitor, Diode, Inductor, ISource,
                      OpAmp, Resistor, Switch, VSource)


class ModeError(RuntimeError):
    pass


class UF:
    def __init__(self):
        self.p = {}

    def find(self, x):
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[ra] = rb


def active_elements(netlist, closed, diode_on):
    """Analog elements that take part in the equations of this mode."""
    out = []
    for e in netlist.analog():
        if isinstance(e, Switch) and e.name not in closed:
            continue
        if isinstance(e, Diode) and e.name not in diode_on:
            continue
        out.append(e)
    return out


def partition(netlist, active):
    uf = UF()
    by = netlist.by_name
    for e in active:
        ns = [n for n in e.nodes() if n != GND]
        if isinstance(e, (VCVS, VCCS)):
            ns += [n for n in (e.cp, e.cn) if n != GND]
        if isinstance(e, (CCCS, CCVS)):
            c = by[e.ctrl]
            ns += [n for n in c.nodes() if n != GND]
        for n in ns:
            uf.find(n)
        for n in ns[1:]:
            uf.union(ns[0], n)
    groups = {}
    for e in active:
        ns = [n for n in e.nodes() if n != GND]
        if not ns:
            continue
        groups.setdefault(uf.find(ns[0]), []).append(e)
    nodes_of = {}
    for n in list(uf.p):
        nodes_of.setdefault(uf.find(n), []).append(n)
    comps = []
    for root, els in groups.items():
        comps.append((sorted(nodes_of[root]), els))
    comps.sort(key=lambda c: c[0][0])
    return comps


AUX_TYPES = (VSource, Switch, Diode, Capacitor, VCVS, CCVS, OpAmp)


class ComponentMode:
    """Linear analysis of one connected component in one mode."""

    def __init__(self, nodes, elements, state_index, exact, fixed=None):
        """`fixed`: optional {node: voltage} of boundary nodes whose potential is imposed
        from outside (e.g. by a grounded ideal source); they get the equation v = value
        and no KCL row (their KCL determines only the imposing source's current)."""
        self.exact = exact
        fixed = fixed or {}
        self.fixed = dict(fixed)
        Z = la.zero_like(exact)
        O = la.one_like(exact)
        self.nodes = list(nodes)
        self.elements = list(elements)
        self.state_names = [e.name for e in elements if isinstance(e, (Capacitor, Inductor))]
        self.state_local = {n: i for i, n in enumerate(self.state_names)}
        ns = len(self.state_names)
        self.aux = [e.name for e in elements if isinstance(e, AUX_TYPES)]
        col = {}
        for i, n in enumerate(self.nodes):
            col[("v", n)] = i
        nn = len(self.nodes)
        for k, a in enumerate(self.aux):
            col[("j", a)] = nn + k
        self.col = col
        ncols = nn + len(self.aux)
        self.ncols = ncols
        rows = []
        r0 = []
        Rm = []
        row_of_node = {}

        def newrow():
            rows.append([Z] * ncols)
            r0.append(Z)
            Rm.append([Z] * ns)
            return len(rows) - 1

        for n in self.nodes:
            if n not in fixed:
                row_of_node[n] = newrow()
        for n in self.nodes:
            if n in fixed:
                r = newrow()
                rows[r][col[("v", n)]] = O
                r0[r] = fixed[n]

        def kcl(node, c, val):
            if node == GND or node in fixed:
                return
            r = row_of_node[node]
            rows[r][c] = rows[r][c] + val

        def kcl_rhs(node, val):  # known current leaving node into element -> rhs -val
            if node == GND or node in fixed:
                return
            r = row_of_node[node]
            r0[r] = r0[r] - val

        def vcol(n):
            return None if n == GND else col[("v", n)]

        def branch_row(pos, neg, coeffs_extra=()):
            r = newrow()
            if vcol(pos) is not None:
                rows[r][vcol(pos)] = rows[r][vcol(pos)] + O
            if vcol(neg) is not None:
                rows[r][vcol(neg)] = rows[r][vcol(neg)] - O
            for c, v in coeffs_extra:
                rows[r][c] = rows[r][c] + v
            return r

        by = {e.name: e for e in elements}
        self.by = by
        for e in elements:
            if isinstance(e, Resistor):
                for (p, q, s) in ((e.a, e.b, 1), (e.b, e.a, 1)):
                    if p == GND:
                        continue
                    if vcol(p) is not None:
                        kcl(p, vcol(p), e.G)
                    if vcol(q) is not None:
                        kcl(p, vcol(q), -e.G)
            elif isinstance(e, ISource):
                kcl_rhs(e.a, e.I)
                kcl_rhs(e.b, -e.I)
            elif isinstance(e, VCCS):
                for node, sg in ((e.a, 1), (e.b, -1)):
                    if node == GND:
                        continue
                    if vcol(e.cp) is not None:
                        kcl(node, vcol(e.cp), sg * e.gm)
                    if vcol(e.cn) is not None:
                        kcl(node, vcol(e.cn), -sg * e.gm)
            elif isinstance(e, CCCS):
                if ("j", e.ctrl) in col:
                    cc = col[("j", e.ctrl)]
                    kcl(e.a, cc, e.gain)
                    kcl(e.b, cc, -e.gain)
            elif isinstance(e, Inductor):
                k = self.state_local[e.name]
                # known current s_k leaving a into the inductor -> rhs
                if e.a != GND and e.a not in fixed:
                    Rm[row_of_node[e.a]][k] = Rm[row_of_node[e.a]][k] - O
                if e.b != GND and e.b not in fixed:
                    Rm[row_of_node[e.b]][k] = Rm[row_of_node[e.b]][k] + O
            if isinstance(e, AUX_TYPES):
                jc = col[("j", e.name)]
                if isinstance(e, OpAmp):
                    kcl(e.out, jc, O)            # norator current out -> ground
                    branch_row(e.inp, e.inn)     # nullator
                    continue
                kcl(e.a, jc, O)
                kcl(e.b, jc, -O)
                if isinstance(e, VSource):
                    r = branch_row(e.a, e.b)
                    r0[r] = r0[r] + e.V
                elif isinstance(e, (Switch, Diode)):
                    branch_row(e.a, e.b)
                elif isinstance(e, Capacitor):
                    r = branch_row(e.a, e.b)
                    Rm[r][self.state_local[e.name]] = O
                elif isinstance(e, VCVS):
                    extra = []
                    if vcol(e.cp) is not None:
                        extra.append((vcol(e.cp), -e.gain))
                    if vcol(e.cn) is not None:
                        extra.append((vcol(e.cn), e.gain))
                    branch_row(e.a, e.b, extra)
                elif isinstance(e, CCVS):
                    extra = []
                    if ("j", e.ctrl) in col:
                        extra.append((col[("j", e.ctrl)], -e.r))
                    branch_row(e.a, e.b, extra)
        self.M = rows
        self.r0 = r0
        self.Rm = Rm
        self._analyse(ns)

    # ------------------------------------------------------------------
    def _analyse(self, ns):
        ex = self.exact
        M, r0, Rm = self.M, self.r0, self.Rm
        nrows, ncols = len(M), self.ncols
        sol = la.GeneralSolver(M, ncols, ex)
        self.rank = sol.rank
        # constraints
        Lc, lc0 = [], []
        for l in sol.left_null:
            row = [la.dot(l, [Rm[i][k] for i in range(nrows)], ex) for k in range(ns)]
            c0 = la.dot(l, r0, ex)
            if all(la.is_zero(v, ex) for v in row):
                if not la.is_zero(c0, ex, sol.scale):
                    raise ModeError("inconsistent mode (source loop/cutset violates KVL/KCL)")
                continue
            Lc.append(row)
            lc0.append(c0)
        self.Lc, self.lc0 = Lc, lc0
        S = sol.particular_matrix()                       # ncols x nrows
        SR = la.matmul(S, Rm, ex) if ns else [[] for _ in range(ncols)]
        Sr0 = la.matvec(S, r0, ex)
        # derivative selector D: s' = D z
        D = la.zeros(ns, ncols, ex)
        for e in self.elements:
            if isinstance(e, Capacitor):
                k = self.state_local[e.name]
                D[k][self.col[("j", e.name)]] = 1 / e.C if not ex else Fraction(1) / e.C
            elif isinstance(e, Inductor):
                k = self.state_local[e.name]
                inv = (Fraction(1) / e.L) if ex else 1.0 / e.L
                if e.a != GND:
                    D[k][self.col[("v", e.a)]] = D[k][self.col[("v", e.a)]] + inv
                if e.b != GND:
                    D[k][self.col[("v", e.b)]] = D[k][self.col[("v", e.b)]] - inv
        self.D = D
        K = sol.right_null                                 # list of vectors (len ncols)
        # projector P = I - K Np Lc D applied to particular solution
        indeterminate_dirs = list(K)
        if K and Lc:
            LcD = la.matmul(Lc, D, ex)                     # nc x ncols
            KT = [list(col) for col in zip(*K)]            # ncols x nK
            N = la.matmul(LcD, KT, ex)                     # nc x nK
            nsol = la.GeneralSolver(N, len(K), ex)
            Np = nsol.particular_matrix()                  # nK x nc
            KNp = la.matmul(KT, Np, ex)                    # ncols x nc
            KNpLcD = la.matmul(KNp, LcD, ex)               # ncols x ncols
            P = la.eye(ncols, ex)
            P = [[a - b for a, b in zip(r1, r2)] for r1, r2 in zip(P, KNpLcD)]
            # remaining free directions
            indeterminate_dirs = []
            for v in nsol.right_null:
                indeterminate_dirs.append(la.matvec(KT, v, ex))
            F = la.matmul(P, SR, ex) if ns else [[] for _ in range(ncols)]
            f0 = la.matvec(P, Sr0, ex)
        else:
            F, f0 = SR, Sr0
        for v in indeterminate_dirs:
            dv = la.matvec(D, v, ex)
            if any(not la.is_zero(x, ex) for x in dv):
                raise ModeError("indeterminate dynamics in this mode")
        self.indeterminate = set()
        for v in indeterminate_dirs:
            for i, x in enumerate(v):
                if not la.is_zero(x, ex):
                    self.indeterminate.add(i)
        self.F, self.f0 = F, f0
        # dynamics
        self.A = la.matmul(D, F, ex) if ns else []
        self.b = la.matvec(D, f0, ex)
        # jump system: unknowns = auxiliary currents (impulse charges)
        nn = len(self.nodes)
        naux = len(self.aux)
        Dq = [row[nn:] for row in D]                       # ns x naux
        J = [row[nn:] for row in M]
        if Lc:
            J = J + la.matmul(Lc, Dq, ex)
        self.Dq = Dq
        self.jsol = la.GeneralSolver(J, naux, ex) if naux else None
        self.nJ_kcl = len(M)
        if self.jsol is not None:
            for v in self.jsol.right_null:
                ds = la.matvec(Dq, v, ex)
                if any(not la.is_zero(x, ex) for x in ds):
                    raise ModeError("non-unique impulsive re-initialisation")

    # ------------------------------------------------------------------
    def jump(self, s_minus):
        """Impulse charges Q (per aux branch) and new local state s_plus."""
        ex = self.exact
        naux = len(self.aux)
        if not self.Lc or naux == 0:
            return [la.zero_like(ex)] * naux, list(s_minus)
        viol = [la.dot(row, s_minus, ex) + c for row, c in zip(self.Lc, self.lc0)]
        if all(la.is_zero(v, ex) for v in viol):
            return [la.zero_like(ex)] * naux, list(s_minus)
        rhs = [la.zero_like(ex)] * self.nJ_kcl + [-v for v in viol]
        # consistency check
        for l in self.jsol.left_null:
            if not la.is_zero(la.dot(l, rhs, ex), ex, self.jsol.scale):
                raise ModeError("no charge-conserving re-initialisation exists")
        Q = self.jsol.particular(rhs)
        ds = la.matvec(self.Dq, Q, ex)
        return Q, [a + b for a, b in zip(s_minus, ds)]
