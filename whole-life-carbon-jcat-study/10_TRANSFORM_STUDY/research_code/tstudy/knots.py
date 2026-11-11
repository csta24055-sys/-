"""The knot spectrum: the canonical form of a ramp-step superposition.

A superposition of gated clipped ramps (``tstudy.rampstep``) is a piecewise-linear function of
the study period T with jumps. In the truncated-power basis it reads

    E(T) = base + sum_{j : t_j < T} (c0_j + c1_j * T)

with knots t_j (event times and whole years). Two knot lists are kept because the concept model
uses two comparison rules: event knots open when  tau < T*(1-eps)  (an event at T is not
counted), lattice knots when  t < T  (year boundaries).

With prefix sums over the sorted knots, E(T) is evaluated for ANY T by two binary searches:

    E(T) = base + P0e[ke] + T*P1e[ke] + P0p[kp] + T*P1p[kp].

Laplace-Stieltjes view (for the record, not used numerically): E is the cumulative function of a
measure with atoms and a piecewise-constant density, and its Laplace transform is
(1/s^2) * sum_j (c1_j + s*(c0_j + c1_j t_j)) * exp(-s t_j)  - a generalized Dirichlet polynomial over s^2.
"""
from __future__ import annotations

import bisect
import math

from .rampstep import EPS, NEG_INF, Piece


def _prefix(values: list[float]) -> list[float]:
    """Running sums with Neumaier compensation; out[k] = sum of the first k values."""
    out = [0.0]
    s = 0.0
    comp = 0.0
    for v in values:
        t = s + v
        comp += (s - t) + v if abs(s) >= abs(v) else (v - t) + s
        s = t
        out.append(s + comp)
    return out


class KnotSpectrum:
    """Sorted knots with prefix sums; ``value(T)`` costs two binary searches."""

    def __init__(self, pieces):
        base: list[float] = []
        ev: list[tuple[float, float, float]] = []      # (tau, c0, c1), opens when tau < T*(1-eps)
        la: list[tuple[float, float, float]] = []      # (t, c0, c1),   opens when t < T
        for p in pieces:
            self._add(p, base, ev, la)
        ev.sort(key=lambda k: k[0])
        la.sort(key=lambda k: k[0])
        self.base = math.fsum(base)
        self.ev_keys = [k[0] for k in ev]
        self.la_keys = [k[0] for k in la]
        self.p0e, self.p1e = _prefix([k[1] for k in ev]), _prefix([k[2] for k in ev])
        self.p0p, self.p1p = _prefix([k[1] for k in la]), _prefix([k[2] for k in la])

    @staticmethod
    def _add(p: Piece, base, ev, la) -> None:
        a, s, l, g = p.amp, p.start, p.length, p.gate
        if a == 0.0:
            return
        if l == 0.0:
            if g == NEG_INF:
                base.append(a)
            else:
                ev.append((g, a, 0.0))
            return
        end = s + l
        if g == NEG_INF:
            la.append((s, -a * s / l, a / l))
            la.append((end, a * end / l, -a / l))
        elif g >= end * (1.0 - EPS):                   # the gate opens when the cell is already complete
            ev.append((g, a, 0.0))
        else:
            ev.append((g, -a * s / l, a / l))
            la.append((end, a * end / l, -a / l))

    @property
    def n_knots(self) -> int:
        return len(self.ev_keys) + len(self.la_keys)

    @property
    def n_distinct_knots(self) -> int:
        return len(set(self.ev_keys)) + len(set(self.la_keys))

    def value(self, T: float) -> float:
        ke = bisect.bisect_left(self.ev_keys, T * (1.0 - EPS))
        kp = bisect.bisect_left(self.la_keys, T)
        return self.base + (self.p0e[ke] + self.p0p[kp]) + T * (self.p1e[ke] + self.p1p[kp])
