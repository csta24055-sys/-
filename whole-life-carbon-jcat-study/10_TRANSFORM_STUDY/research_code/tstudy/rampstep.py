"""The ramp-step kernel: one operator for every dependence on the study period T.

Hypothesis HY-01 (exploration; see 04_HYPOTHESES): every quantity of the concept model that
depends on the study period T is the value at T of a superposition of *gated clipped ramps*

    Phi(T) = sum_j  a_j * [gate_j < T*(1-eps)] * clip((T - s_j) / l_j, 0, 1)

where the amplitudes a_j do not depend on T. The three shapes the model needs are special cases:

    atom at time tau          s = tau,  l = 0 (factor 1),  gate = tau     an event counted when tau < T
    year cell y               s = y-1,  l = 1,             gate = -inf    the year weight w_y = min(1, T-(y-1))
    gated year cell           s = y-1,  l = 1,             gate = tau     "the year that holds the event at tau"
    linear ramp over [0, L]   s = 0,    l = L, amplitude a*L              a*T for T <= L (a constant density)

The kernel is a measure-theoretic statement: Phi(T) = mu([0, T)) for a signed measure mu made of
atoms and of densities that are constant on year cells; the gate couples a cell to an atom.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

EPS = 1e-9              # the relative tolerance of the time rules of the concept model
NEG_INF = -math.inf


@dataclass(frozen=True)
class Piece:
    amp: float
    start: float
    length: float
    gate: float = NEG_INF

    def shape(self) -> tuple[float, float, float]:
        return (self.start, self.length, self.gate)


def h(T: float, start: float, length: float, gate: float) -> float:
    """The gated clipped ramp."""
    if not gate < T * (1.0 - EPS):
        return 0.0
    if length == 0.0:
        return 1.0
    x = (T - start) / length
    if x <= 0.0:
        return 0.0
    return 1.0 if x >= 1.0 else x


def phi(pieces, T: float) -> float:
    """Value at T of a superposition of pieces (math.fsum: the order of the pieces does not matter)."""
    return math.fsum(p.amp * h(T, p.start, p.length, p.gate) for p in pieces)


def atom(amp: float, tau: float) -> Piece:
    return Piece(amp, tau, 0.0, tau)


def constant(amp: float) -> Piece:
    return Piece(amp, 0.0, 0.0, NEG_INF)


def year_cell(amp: float, year: int, gate: float = NEG_INF) -> Piece:
    return Piece(amp, float(year - 1), 1.0, gate)


def density(amp_per_year: float, horizon: float) -> Piece:
    """A constant density from 0 to ``horizon``: amp_per_year * T for T <= horizon."""
    return Piece(amp_per_year * horizon, 0.0, horizon, NEG_INF)


def event_year(tau: float) -> int:
    """The study year an event at tau belongs to (the convention of the concept model)."""
    return max(1, math.ceil(tau * (1.0 - EPS)))


def periodic_times(horizon: float, period) -> list[float]:
    """Times n*period (n >= 1) before ``horizon`` under the tolerance rule; none for an invalid period."""
    out: list[float] = []
    if period is None or not period > 0.0 or math.isinf(period):
        return out
    n = 1
    while n * period < horizon * (1.0 - EPS):
        out.append(n * period)
        n += 1
    return out


def explicit_times(horizon: float, times) -> list[float]:
    return [float(t) for t in times if t > 0 and t < horizon * (1.0 - EPS)]


def merge(pieces) -> dict[tuple[float, float, float], float]:
    """Group pieces by shape: the separated form  Phi(T) = sum_shape A_shape * h_shape(T)."""
    out: dict[tuple[float, float, float], list[float]] = {}
    for p in pieces:
        out.setdefault(p.shape(), []).append(p.amp)
    return {k: math.fsum(v) for k, v in out.items()}


def phi_merged(merged: dict[tuple[float, float, float], float], T: float) -> float:
    return math.fsum(a * h(T, s, l, g) for (s, l, g), a in merged.items())
