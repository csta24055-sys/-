"""Stage 2: dynamic characterisation of the real-time emission function (convolution with the CO2 impulse response).

The inventory of the 70-unit model is in kgCO2e (gases already weighted by GWP100). A dynamic characterisation of a
CO2e flow treats it as if it were CO2 -- an APPROXIMATION recorded as such (the gas split exists only per stage and
period, unit X-04, and is not resolved in time).

CO2 impulse response (multi-model mean of Joos et al. 2013, as adopted in IPCC AR5 WG1 ch. 8 SM; parameters as read
from the sources listed in 18/01 -- see the literature survey):
    IRF(t) = a0 + sum_{i=1..3} a_i exp(-t / tau_i)
    a = (0.2173, 0.2240, 0.2824, 0.2763),  tau = (394.4, 36.54, 4.304) years
Cumulative response  R(h) = int_0^h IRF = a0 h + sum a_i tau_i (1 - exp(-h/tau_i)).

Time-weighted metric with a FIXED calendar end point t_end (Levasseur et al. 2010 dynamic LCA; Kendall 2012 TAWP):
    W(t_end) = sum_events a_j R(t_end - t_j) / R(100)          (masses)
             + blocks: a/(t1-t0) int_{t0}^{t1} R(t_end - t)/R(100) dt   (closed form)
An emission at t_end or later contributes 0. A static GWP100 inventory corresponds to R(100)/R(100) = 1 for every
emission (no time weighting). The ratio W / total measures the effect of timing alone.
"""
from __future__ import annotations

import math

A = (0.2173, 0.2240, 0.2824, 0.2763)
TAU = (394.4, 36.54, 4.304)


def R(h: float) -> float:
    if h <= 0:
        return 0.0
    return A[0] * h + sum(a * t * (1.0 - math.exp(-h / t)) for a, t in zip(A[1:], TAU))


def RR(h: float) -> float:
    """int_0^h R(u) du (for uniform blocks)."""
    if h <= 0:
        return 0.0
    return A[0] * h * h / 2 + sum(a * t * (h - t * (1.0 - math.exp(-h / t))) for a, t in zip(A[1:], TAU))


R100 = R(100.0)


def weight_mass(t: float, t_end: float) -> float:
    return R(t_end - t) / R100


def weight_block(t0: float, t1: float, t_end: float) -> float:
    """Average of R(t_end - t)/R100 over t in [t0, t1] (exact integral)."""
    if t1 <= t0:
        return weight_mass(t0, t_end)
    # int_{t0}^{t1} R(t_end - t) dt = RR(t_end - t0) - RR(t_end - t1)   (R = 0 for negative arguments)
    hi, lo = t_end - t0, max(0.0, t_end - t1)
    return (RR(max(0.0, hi)) - RR(lo)) / (t1 - t0) / R100


def weighted(masses, blocks, t_end: float) -> float:
    w = sum(float(a) * weight_mass(float(t), t_end) for t, a, p in masses)
    w += sum(float(a) * weight_block(float(t0), float(t1), t_end) for t0, t1, a, p in blocks)
    return w
