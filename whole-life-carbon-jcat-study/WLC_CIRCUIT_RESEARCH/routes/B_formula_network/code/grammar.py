"""Route B circuit grammar G and minimal kernel interpreters (Psi reading: the sweep variable is the
evaluation horizon T, NOT physical time t).

GRAMMAR G (the only arithmetic allowed inside a netlist)
    sweep    independent source whose value is the sweep variable T
    src      independent DC source (T-independent amplitude)
    gain     linear controlled source y = k*x with a T-independent coefficient k (VCVS / VCCS)
    sum      summing node (KCL), y = sum of inputs (math.fsum: the float model of an ideal node)
    gate     0/1 switch, y = x if ctrl == 1 else 0
    clip     saturation, y = min(max(x, lo), hi)
    cmp      comparator, y = [a < b] in {0, 1}
    table    external table y = values[int(index)]
    int      ideal integrator dx/dT = i(T) (input piecewise constant between declared breakpoints)
    sh       sample-hold / reset (used inside the hybrid automaton ``RefrigerantCircuit``)
No multiplier of two signals, no divider, no lookup by key, no string handling: those are NOT in G and
are classified as external digital logic (class d) in MAPPING.csv.

Classes used in MAPPING.csv: a passive (sources + R/C/KCL only), b active (comparator, clip, gain>1 or
sign inversion of a voltage), c switched-hybrid (integrator or sample-hold whose input is switched by
comparators/counters), d external digital, e not representable.

Conventions reproduced (original model, NOT the right-continuous pilot P0):
    an event at tau counts iff  tau < T*(1-eps), eps = 1e-9           (atom theta_eps)
    year cell k covers (k, k+1];  w_k(T) = clip(T-k, 0, 1)
    an event at tau belongs to cell k_tau = max(1, ceil(tau*(1-eps))) - 1
All values are floats; agreement with the oracles is a float agreement [F], not an equality.
"""
from __future__ import annotations

import bisect
import collections
import math

EPS = 1e-9
D = 1.0 - EPS                  # fl(1 - eps); T*D is the same float operation as refcalc's T*(1.0-EPS)
NEG_INF = -math.inf
PRIMITIVES = ("sweep", "src", "gain", "sum", "gate", "clip", "cmp", "table", "int", "sh")


class GrammarError(ValueError):
    pass


# ---------------------------------------------------------------------------------------------
# memoryless + integrator netlist
# ---------------------------------------------------------------------------------------------
class Net:
    """A netlist of grammar primitives. Nodes are evaluated in creation order (a DAG, no feedback)."""

    def __init__(self, name: str = ""):
        self.name = name
        self.ops: list[tuple[str, tuple, object]] = []
        self._memo: dict = {}
        self.ints: list[int] = []
        self.T = self._add("sweep", (), None)
        self.evals = 0              # primitive evaluations performed (cost counter)

    # --- construction (structural sharing of identical nodes) ---------------------------------
    def _add(self, prim, ins, par):
        if prim not in PRIMITIVES:
            raise GrammarError(prim)
        key = (prim, ins, par if not isinstance(par, list) else id(par))
        if prim not in ("int", "table") and key in self._memo:
            return self._memo[key]
        self.ops.append((prim, ins, par))
        n = len(self.ops) - 1
        self._memo[key] = n
        if prim == "int":
            self.ints.append(n)
        return n

    def src(self, a: float) -> int:
        return self._add("src", (), float(a))

    def gain(self, k: float, x: int) -> int:
        return self._add("gain", (x,), float(k))

    def sum(self, xs) -> int:
        xs = tuple(xs)
        if len(xs) == 1:
            return xs[0]
        return self._add("sum", xs, None)

    def gate(self, ctrl: int, x: int) -> int:
        return self._add("gate", (ctrl, x), None)

    def clip(self, x: int, lo: float, hi: float) -> int:
        return self._add("clip", (x,), (float(lo), float(hi)))

    def cmp(self, a: int, b: int) -> int:
        return self._add("cmp", (a, b), None)

    def table(self, index: int, values) -> int:
        return self._add("table", (index,), list(values))

    def integrator(self, current: int) -> int:
        return self._add("int", (current,), None)

    # --- derived (still only primitives) -------------------------------------------------------
    def t_shrunk(self) -> int:
        """T' = T*(1-eps): a T-independent gain (a resistive divider would do: passive)."""
        return self.gain(D, self.T)

    def theta(self, tau: float) -> int:
        """Atom gate theta_eps(T; tau) = [tau < T(1-eps)]."""
        return self.cmp(self.src(tau), self.t_shrunk())

    def w(self, k: int) -> int:
        """Year weight w_k(T) = clip(T - k, 0, 1)."""
        return self.clip(self.sum((self.T, self.src(-float(k)))), 0.0, 1.0)

    def cell_counter(self, H: int) -> int:
        """k(T) = ceil(T) - 1 = sum_{j=1}^{H-1} [j < T]  (a comparator bank; T in (0, H])."""
        return self.sum([self.cmp(self.src(float(j)), self.T) for j in range(1, H)])

    # --- evaluation -----------------------------------------------------------------------------
    def counts(self) -> dict:
        c = collections.Counter(p for p, _, _ in self.ops)
        c["sum_inputs"] = sum(len(ins) for p, ins, _ in self.ops if p == "sum")
        c["table_entries"] = sum(len(par) for p, _, par in self.ops if p == "table")
        return dict(c)

    def _static(self, T: float, istate: dict) -> list:
        v = [0.0] * len(self.ops)
        for n, (p, ins, par) in enumerate(self.ops):
            if p == "sweep":
                v[n] = T
            elif p == "src":
                v[n] = par
            elif p == "gain":
                v[n] = par * v[ins[0]]
            elif p == "sum":
                v[n] = math.fsum(v[i] for i in ins)
            elif p == "gate":
                v[n] = v[ins[1]] if v[ins[0]] == 1.0 else 0.0
            elif p == "clip":
                x = v[ins[0]]
                v[n] = par[0] if x < par[0] else par[1] if x > par[1] else x
            elif p == "cmp":
                v[n] = 1.0 if v[ins[0]] < v[ins[1]] else 0.0
            elif p == "table":
                v[n] = par[int(v[ins[0]])]
            elif p == "int":
                v[n] = istate[n]
        self.evals += len(self.ops)
        return v

    def value(self, T: float, out: int) -> float:
        """Memoryless evaluation (no integrator in the netlist)."""
        if self.ints:
            raise GrammarError("netlist has integrators: use sweep()")
        return self._static(float(T), {})[out]

    def sweep(self, Ts, outs, breakpoints=()) -> dict:
        """Hybrid sweep from T=0: integrators integrate their (piecewise constant) input current over the
        segments between consecutive breakpoints / query points; the current of a segment is read at its
        midpoint (exact because the declared breakpoints contain every switching point of the currents)."""
        Ts = sorted(set(float(t) for t in Ts))
        top = Ts[-1]
        pts = sorted(set(Ts) | {float(b) for b in breakpoints if 0.0 < b < top})
        want = set(Ts)
        istate = {n: 0.0 for n in self.ints}
        t0, res = 0.0, {}
        for t in pts:
            if t > t0:
                v = self._static(t0 + (t - t0) / 2.0, istate)
                for n in self.ints:
                    istate[n] += v[self.ops[n][1][0]] * (t - t0)
                t0 = t
            if t in want:
                v = self._static(t, istate)
                res[t] = {o: v[o] for o in outs}
        return res


# ---------------------------------------------------------------------------------------------
# kernels on amplitude tables (pieces of P1 -> EMIT, used as an external T-independent table)
# ---------------------------------------------------------------------------------------------
def classify_piece(p, H: float) -> str:
    a, s, l, g = p.amp, p.start, p.length, p.gate
    if l == 0.0:
        if g == NEG_INF:
            return "const"
        if s != g:
            raise GrammarError("atom with start != gate")
        return "atom"
    if l == 1.0:
        return "cell" if g == NEG_INF else "gcell"
    if s == 0.0 and l == H and g == NEG_INF:
        return "density"
    raise GrammarError(f"unknown piece shape {(s, l, g)}")


def build_kernel(pieces, H: int, cell_mode: str = "clip"):
    """Netlist for a superposition of kernels.

    cell_mode "clip":       each year cell is a clip block (memoryless) times a gain.
    cell_mode "integrator": all year cells share ONE integrator driven by a table of per-cell currents
                            indexed by the comparator-bank counter k(T) (switched current source).
    Densities always share one integrator (KCL sum of their currents).
    Returns (net, out_node, kind_nodes, breakpoints, n_by_kind).
    """
    net = Net("kernel")
    by_kind = collections.defaultdict(list)
    for p in pieces:
        if p.amp == 0.0:
            continue
        by_kind[classify_piece(p, float(H))].append(p)
    kind_out = {}
    bps: set[float] = set()
    # constants: DC sources into one node
    if by_kind["const"]:
        kind_out["const"] = net.sum([net.src(p.amp) for p in by_kind["const"]])
    # atoms: per distinct tau, parallel sources -> one gate driven by one comparator
    if by_kind["atom"]:
        groups = collections.defaultdict(list)
        for p in by_kind["atom"]:
            groups[p.gate].append(p.amp)
        kind_out["atom"] = net.sum([net.gate(net.theta(tau), net.sum([net.src(a) for a in amps]))
                                    for tau, amps in sorted(groups.items())])
    # gated year cells: comparator AND clip
    if by_kind["gcell"]:
        groups = collections.defaultdict(list)
        for p in by_kind["gcell"]:
            groups[(int(p.start), p.gate)].append(p.amp)
        terms = []
        for (k, tau), amps in sorted(groups.items()):
            terms.append(net.gate(net.theta(tau), _gain_node(net, None, net.w(k), amps)))
        kind_out["gcell"] = net.sum(terms)
    # year cells
    if by_kind["cell"]:
        groups = collections.defaultdict(list)
        for p in by_kind["cell"]:
            groups[int(p.start)].append(p.amp)
        if cell_mode == "clip":
            kind_out["cell"] = net.sum([_gain_node(net, None, net.w(k), amps) for k, amps in sorted(groups.items())])
        elif cell_mode == "integrator":
            # per-cell current table: B[k] = sum of the amplitudes of cell k (a KCL sum of sources, precomputed
            # as the table content - the table is external data, like the P1 amplitudes themselves)
            B = [math.fsum(groups.get(k, [0.0])) for k in range(H)]
            cur = net.table(net.cell_counter(H), B)
            kind_out["cell"] = net.integrator(cur)
            bps |= {float(j) for j in range(1, H)}
        else:
            raise GrammarError(cell_mode)
    # densities: currents summed at one capacitor node
    if by_kind["density"]:
        cur = net.sum([net.src(p.amp / p.length) for p in by_kind["density"]])
        kind_out["density"] = net.integrator(cur)
    out = net.sum(list(kind_out.values())) if kind_out else net.src(0.0)
    return net, out, kind_out, sorted(bps), {k: len(v) for k, v in by_kind.items()}


def _gain_node(net, amp_node, w_node, amps):
    """a * w with a T-independent amplitude: one linear controlled source per distinct amplitude group.
    (Amplitudes of the same shape add first: parallel sources; the gain is their T-independent sum.)"""
    a = math.fsum(amps)
    return net.gain(a, w_node)


def eval_kernel(pieces, H: int, Ts, cell_mode: str = "clip") -> tuple[dict, Net, dict]:
    net, out, kinds, bps, nk = build_kernel(pieces, H, cell_mode)
    outs = [out] + list(kinds.values())
    if net.ints:
        r = net.sweep(Ts, outs, bps)
    else:
        r = {float(T): {o: v for o, v in zip(outs, _vals(net, T, outs))} for T in Ts}
    res = {T: {"total": d[out], **{k: d[n] for k, n in kinds.items()}} for T, d in r.items()}
    return res, net, nk


def _vals(net, T, outs):
    v = net._static(float(T), {})
    return [v[o] for o in outs]


# ---------------------------------------------------------------------------------------------
# comparator switching point (zero-crossing location of a hybrid simulator, to machine precision)
# ---------------------------------------------------------------------------------------------
def switch_point(tau: float) -> float:
    """Smallest float T with tau < T*D (the comparator theta_eps(T; tau) is 1 exactly for T >= sw)."""
    t = tau / D
    while not (tau < t * D):
        t = math.nextafter(t, math.inf)
    while tau < math.nextafter(t, -math.inf) * D:
        t = math.nextafter(t, -math.inf)
    return t


def event_cell(tau: float) -> int:
    return max(1, math.ceil(tau * D)) - 1


# ---------------------------------------------------------------------------------------------
# refrigerant hybrid automaton (sample-hold + reset + switched integrator), from RAW scenario inputs
# ---------------------------------------------------------------------------------------------
def _nonneg(x):
    return x is not None and x >= 0.0 and not math.isinf(x)


def _ratio(x):
    return x is not None and 0.0 <= x <= 1.0


def _positive(x):
    return x is not None and x > 0.0 and not math.isinf(x)


def device_event_table(dev, H: float) -> list[float]:
    """External table of candidate event times up to the table horizon H (class d: enumeration).
    Same float construction as the model: explicit offsets 0 < t, else n*L for n = 1, 2, ..."""
    if dev.change_years is not None:
        return sorted(float(t) for t in dev.change_years if t > 0 and t < H * D)
    out, L = [], dev.service_life
    if not _positive(L):
        return out
    n = 1
    while n * L < H * D:
        out.append(n * L)
        n += 1
    return out


class _Dev:
    __slots__ = ("m0", "r", "gwp", "topup", "lam_ok", "lam", "eta_ok", "eta", "K", "m_hold", "pre_hold", "n_cur",
                 "prev_had", "i", "L_last", "t_last", "acc_e", "acc_b13")


class RefrigerantCircuit:
    """Per device:  S/H  m_hold   (charge at the start of the current year cell)
                    int  Lyr      (leaked mass of the current cell; current i = r*m_hold: VCCS on the held value)
                    S/H  acc_e    (accumulated leak emission of closed cells, gain GWP)
                    S/H  acc_b13  (accumulated replacement losses of closed cells, gain lambda*GWP)
                    counter n_cur (events of the current cell counted by their comparators)
    Shared: cell counter K(T) with thresholds 1..H-1; one comparator per event time (switch point sw(tau)).
    Events: boundary b (cell b-1 -> b) happens for T > b; comparator of tau fires for T >= sw(tau).
    A comparator that fires after its own cell closed (integer tau: sw(tau) > tau = cell end) applies a LATE
    reset: m_hold <- m0 and the integrator is re-initialised (sample of r*m0*(T-K)), which reproduces the
    model's recomputation of the whole history at each T.
    Readouts:  B1-02 = acc_e + GWP*Lyr;  m_end = m0 if n_cur > 0 else m_hold - [no top-up]*Lyr;
               B1-04 = (1-eta)*GWP*m_end;  B1-03 = acc_b13 + lambda*GWP*([n_cur>0]*m_before + (n_cur-1)^+ * m0).
    """

    def __init__(self, scn, H: int, late_reset: bool = True):
        self.H = int(H)
        self.late_reset = late_reset
        self.devs: list[_Dev] = []
        self.timeline = []            # (time, order, kind, device index, tau)
        self.prim = collections.Counter()
        for idx, dev in enumerate(scn.refrigerants):
            if not (_nonneg(dev.charge_mass_kg) and _nonneg(dev.gwp) and _ratio(dev.annual_leak_rate)):
                continue              # static predicate = configuration switch open (class d decides it)
            d = _Dev()
            d.m0, d.r, d.gwp, d.topup = dev.charge_mass_kg, dev.annual_leak_rate, dev.gwp, bool(dev.top_up)
            d.lam_ok, d.lam = _ratio(dev.replacement_loss_rate), dev.replacement_loss_rate
            d.eta_ok, d.eta = _ratio(dev.end_of_life_recovery_rate), dev.end_of_life_recovery_rate
            j = len(self.devs)
            self.devs.append(d)
            for tau in device_event_table(dev, float(H)):
                self.timeline.append((switch_point(tau), 0, "cmp", j, tau))
                self.prim["cmp"] += 1
        for b in range(1, self.H):
            self.timeline.append((float(b), 1, "bnd", -1, None))
        self.prim["cmp"] += self.H - 1         # cell counter thresholds
        nd = len(self.devs)
        self.prim.update({"sh": 3 * nd, "int": nd, "gain": 5 * nd, "gate": 2 * nd, "sum": 3 + 3 * nd,
                          "src": 4 * nd, "counter": 1 + nd})
        self.timeline.sort(key=lambda e: (e[0], e[1]))
        self.unexpected = []

    def _reset_state(self):
        for d in self.devs:
            d.K, d.m_hold, d.pre_hold, d.n_cur, d.prev_had = 0, d.m0, d.m0, 0, False
            d.i, d.L_last, d.t_last, d.acc_e, d.acc_b13 = d.r * d.m0, 0.0, 0.0, 0.0, 0.0

    @staticmethod
    def _L(d, T):
        return d.L_last + d.i * (T - d.t_last)

    def _boundary(self, b: float):
        for d in self.devs:
            Lfull = self._L(d, b)                  # = i*1 (cell fully elapsed)
            d.acc_e += Lfull * d.gwp
            m_after = d.m_hold - Lfull if not d.topup else d.m_hold
            if d.n_cur > 0:
                if d.lam_ok:
                    d.acc_b13 += m_after * d.lam * d.gwp
                    for _ in range(d.n_cur - 1):
                        d.acc_b13 += d.m0 * d.lam * d.gwp
                m_new = d.m0
            else:
                m_new = m_after
            d.prev_had = d.n_cur > 0
            d.pre_hold = m_after
            d.K, d.m_hold, d.n_cur = int(b), m_new, 0
            d.i, d.L_last, d.t_last = d.r * d.m_hold, 0.0, b

    def _fire(self, j: int, tau: float, t: float):
        d = self.devs[j]
        k = event_cell(tau)
        if k == d.K:
            d.n_cur += 1
        elif k == d.K - 1 and self.late_reset:
            if d.lam_ok:
                d.acc_b13 += (d.m0 if d.prev_had else d.pre_hold) * d.lam * d.gwp
            d.prev_had = True
            d.m_hold = d.m0
            d.i = d.r * d.m0
            d.L_last, d.t_last = d.i * (t - d.K), t       # sample-hold re-initialisation of the integrator
        elif k == d.K - 1:
            self.unexpected.append(("late event ignored", tau, t))
        else:
            self.unexpected.append(("event outside current/previous cell", tau, t, d.K))

    def readout(self, T: float) -> dict:
        b12 = b13 = b14 = 0.0
        for d in self.devs:
            L = self._L(d, T)
            b12 += d.acc_e + L * d.gwp
            m_before = d.m_hold - L if not d.topup else d.m_hold
            m_end = d.m0 if d.n_cur > 0 else m_before
            if d.eta_ok:
                b14 += m_end * (1.0 - d.eta) * d.gwp
            if d.lam_ok:
                v = d.acc_b13
                if d.n_cur > 0:
                    v += m_before * d.lam * d.gwp + (d.n_cur - 1) * (d.m0 * d.lam * d.gwp)
                b13 += v
        return {"B1-02": b12, "B1-03": b13, "B1-04": b14}

    def sweep(self, Ts) -> dict:
        self._reset_state()
        Ts = sorted(set(float(t) for t in Ts))
        out, p = {}, 0
        for T in Ts:
            if not (0.0 < T <= self.H):
                raise GrammarError("T outside (0, H]")
            while p < len(self.timeline):
                t, order, kind, j, tau = self.timeline[p]
                happened = (t <= T) if kind == "cmp" else (t < T)
                if not happened:
                    break
                if kind == "bnd":
                    self._boundary(t)
                else:
                    self._fire(j, tau, t)
                p += 1
            out[T] = self.readout(T)
        return out

    def state_tuple(self) -> tuple:
        nd = len(self.devs)
        n_ev = sum(1 for e in self.timeline if e[2] == "cmp")
        return (4 * nd, 1 + 2 * nd, (self.H - 1) + n_ev, n_ev + 6 * nd)


# ---------------------------------------------------------------------------------------------
# event counter (count kernel) from raw equipment inputs: comparator bank + summing node
# ---------------------------------------------------------------------------------------------
def equipment_event_table(eq, H: float) -> list[float]:
    if eq.replacement_event_list is not None:
        return [float(t) for t in eq.replacement_event_list if t > 0 and t < H * D]
    out, L = [], eq.service_life
    if not _positive(L):
        return out
    n = 1
    while n * L < H * D:
        out.append(n * L)
        n += 1
    return out


def build_counter(scn, H: int):
    net = Net("counter")
    taus = [tau for eq in scn.equipment for tau in equipment_event_table(eq, float(H))]
    out = net.sum([net.theta(t) for t in taus]) if taus else net.src(0.0)
    return net, out, len(taus)
