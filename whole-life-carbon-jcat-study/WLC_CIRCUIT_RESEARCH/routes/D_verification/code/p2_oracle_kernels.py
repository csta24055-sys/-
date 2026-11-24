"""Pass-2 D oracle for the horizon (Psi) side, written from the source TEXT (03 S3.2, S5.1, S5.4, S5.5;
refcalc docstrings) without importing route B/C code.

Kernels (03 S5.1, chapter 11/14 form, amplitudes T-independent):
    h(T; s, l, g) = [g < T(1-eps)] * clip((T - s)/l, 0, 1),   l = 0 => clip(.) = 1
  const  (0,0,-inf)      atom (tau,0,tau)      year cell (k,1,-inf) = w_k(T) = clip(T-k,0,1)
  gated cell (k,1,tau)   density (0,H,-inf) with amplitude a*H  => a*min(T,H)
Evaluation: exact Fraction of the float amplitudes/positions; the gate test in FLOAT exactly as the model
(g < fl(T*d)), as 03 S3.3 prescribes for exact comparison.

Refrigerant (03 S5.5 recurrence + refcalc B1-02/03/04 docstrings), per device d, for one horizon T:
  events counted at T: tau < fl(T*d) (explicit list, else fl(n*L) for n=1,2,...); event year
  y(tau) = max(1, ceil(fl(tau*d))); years y = 1..ceil(T) with weight w_y = min(1, T-(y-1));
  leak_y = m*r*w_y (B1-02 adds leak_y*GWP); without top-up m -= leak_y; each event of year y applied at the
  END of year y: record m (B1-03 adds m*lambda*GWP), then m = m0.  B1-04 = m_end*(1-eta)*GWP.
  Missing/invalid inputs: device skipped (B1-02 predicate), lambda/eta outside [0,1] -> not counted.
Exact rational arithmetic on the float inputs (so the comparison with refcalc is a float agreement).
"""
from __future__ import annotations

import math
from fractions import Fraction as Fr

EPS = 1e-9
D = 1.0 - EPS
NEG_INF = -math.inf


def h(T: float, start: float, length: float, gate: float) -> Fr:
    if not (gate < T * D):                          # float gate rule (model)
        return Fr(0)
    if length == 0.0:
        return Fr(1)
    x = (Fr(T) - Fr(start)) / Fr(length)
    return Fr(0) if x <= 0 else (Fr(1) if x >= 1 else x)


def kernel_sum(pieces, T: float) -> Fr:
    return sum((Fr(p.amp) * h(T, p.start, p.length, p.gate) for p in pieces if p.amp != 0.0), Fr(0))


def h_rate(T: float, start: float, length: float, gate: float) -> Fr:
    """Chapter-17 form of the same kernel (03 S5.1 second form): amplitude is a RATE for ramps,
    kappa = [g < T(1-eps)] * r_l(T - s), r_0 = 1, r_l(x) = clip(x, 0, l). Used for canon.py's Term amplitudes."""
    if not (gate < T * D):
        return Fr(0)
    if length == 0.0:
        return Fr(1)
    x = Fr(T) - Fr(start)
    return Fr(0) if x <= 0 else min(x, Fr(length))


def kernel_sum_rate(terms, T: float) -> Fr:
    return sum((Fr(p.amp) * h_rate(T, p.start, p.length, p.gate) for p in terms if p.amp != 0), Fr(0))


def kernel_by_kind(pieces, T: float, H: float) -> dict:
    out = {}
    for p in pieces:
        if p.amp == 0.0:
            continue
        if p.length == 0.0:
            k = "const" if p.gate == NEG_INF else "atom"
        elif p.length == 1.0:
            k = "cell" if p.gate == NEG_INF else "gcell"
        else:
            k = "density"
        out[k] = out.get(k, Fr(0)) + Fr(p.amp) * h(T, p.start, p.length, p.gate)
    return out


def _nonneg(x):
    return x is not None and x >= 0.0 and not math.isinf(x)


def _ratio(x):
    return x is not None and 0.0 <= x <= 1.0


def _positive(x):
    return x is not None and x > 0.0 and not math.isinf(x)


def device_events(dev, T: float) -> list:
    if dev.change_years is not None:
        return sorted(float(t) for t in dev.change_years if t > 0 and t < T * D)
    out, L = [], dev.service_life
    if not _positive(L):
        return out
    n = 1
    while n * L < T * D:
        out.append(n * L)
        n += 1
    return out


def refrigerant(devices, T: float) -> dict:
    b12 = b13 = b14 = Fr(0)
    Y = math.ceil(T)
    TF = Fr(T)
    for dev in devices:
        if not (_nonneg(dev.charge_mass_kg) and _nonneg(dev.gwp) and _ratio(dev.annual_leak_rate)):
            continue
        per = {}
        for tau in device_events(dev, T):
            y = max(1, math.ceil(tau * D))
            per[y] = per.get(y, 0) + 1
        m0, r, g = Fr(dev.charge_mass_kg), Fr(dev.annual_leak_rate), Fr(dev.gwp)
        m = m0
        lam_ok, eta_ok = _ratio(dev.replacement_loss_rate), _ratio(dev.end_of_life_recovery_rate)
        for y in range(1, Y + 1):
            w = min(Fr(1), TF - (y - 1))
            leak = m * r * w
            b12 += leak * g
            if not dev.top_up:
                m -= leak
            for _ in range(per.get(y, 0)):
                if lam_ok:
                    b13 += m * Fr(dev.replacement_loss_rate) * g
                m = m0
        if eta_ok:
            b14 += m * (1 - Fr(dev.end_of_life_recovery_rate)) * g
    return {"B1-02": b12, "B1-03": b13, "B1-04": b14}


def p0_pieces(H: float = 130.0):
    """P0 (architecture S1.2) as kernel pieces in the 03 S5.1 convention (for gate X2):
    G0=100 const, r=4/yr density (amplitude a*H), AC 20 at 10n, pipe 35 at 20n (atoms), n*c < H(1-eps)."""
    from collections import namedtuple
    P = namedtuple("Piece", "amp start length gate")
    ps = [P(100.0, 0.0, 0.0, NEG_INF), P(4.0 * H, 0.0, H, NEG_INF)]
    for c, a in ((10.0, 20.0), (20.0, 35.0)):
        n = 1
        while n * c < H * D:
            ps.append(P(a, n * c, 0.0, n * c))
            n += 1
    return ps
