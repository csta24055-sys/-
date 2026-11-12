"""Interval form of a knot spectrum on the year grid (used for the end residual of the refrigerants).

The jump form of ``tstudy.knots`` stores, for every knot, the CHANGE of the value and of the slope and
accumulates the changes from T = 0. For a state that decays over many orders of magnitude this subtracts
almost equal numbers (initial charge minus cumulative leaks). The interval form stores, for every year
cell k, the coefficients that are valid INSIDE the cell:

    E(T) = A[k] + B[k]*(T - k) + sum_{j in cell k, tau_j < T*(1-eps)} (a_j + g_j*(T - k)),      k < T <= k+1

with non-negative corrections (a_j, g_j) of the knots that lie inside the cell. In exact arithmetic the two
forms describe the same piecewise-linear function (the interval coefficients are the prefix sums of the
jumps); numerically the interval form adds terms of the size of the result only.

Evaluation: locate the cell (k = ceil(T) - 1), one binary search among the knots of that cell, and the
prefix sums of the corrections of that cell.
"""
from __future__ import annotations

import bisect
import collections
import math

from .knots import _prefix
from .rampstep import EPS


class IntervalSpectrum:
    def __init__(self, A, B, cells, taus, amps, gains):
        self.A, self.B = [float(x) for x in A], [float(x) for x in B]
        by = collections.defaultdict(list)
        for c, t, a, g in zip(cells, taus, amps, gains):
            by[int(c)].append((float(t), float(a), float(g)))
        self.cells = {}
        for c, items in by.items():
            items.sort()
            self.cells[c] = ([x[0] for x in items], _prefix([x[1] for x in items]), _prefix([x[2] for x in items]))
        self.n_knots = len(self.A) + sum(len(v[0]) for v in self.cells.values())

    def value(self, T: float) -> float:
        k = math.ceil(T) - 1
        w = T - k
        v = self.A[k] + self.B[k] * w
        if k in self.cells:
            keys, pa, pg = self.cells[k]
            i = bisect.bisect_left(keys, T * (1.0 - EPS))
            v += pa[i] + pg[i] * w
        return v
