"""Stage 2: time distributions that the 70-unit model does NOT define (labelled assumptions, never presented as derived).

The derived layer (processes.py) places each process where the meaning of its unit puts it: A stages at t = 0,
annual flows uniformly inside their year cells, events at their times, C stages and the refrigerant stock at t = T.
The model has no input for: the timing of manufacturing and transport before occupancy, the spread of site work
over the construction period, the duration of demolition and waste treatment after T, a within-year profile.
(The scenario does carry construction.duration_months and boundary.study_start_year; no unit uses them.)

Variants (each keeps every process total; only the timing changes):
  M0  model placement (derived)
  X1  A1-A5 spread uniformly over the construction period [-D_c, 0), D_c = duration_months / 12
  X2  manufacturing (P01, P02) at the start of construction -D_c, transport and site work (P03, P04) uniform over
      [-D_c, 0)
  X3  end of life (P13-P17) spread uniformly over [T, T + D_e), D_e = D_c (assumption: demolition as long as
      construction)
  X4  X1 + X3
Non-uniqueness: all variants give the same C_70(T); they differ in the real-time emission function e(t), in the
cumulative real-time curve and in any time-weighted metric (dynamic characterisation, dyncharac.py).

A variant is a list of (time or interval, amount, process id): masses (t, a) and uniform blocks (t0, t1, a).
"""
from __future__ import annotations

from fractions import Fraction

import processes as pr

INITIAL = ("P01", "P02", "P03", "P04")
EOL = ("P13", "P14", "P15", "P16", "P17")


def timeline(fam, T: float, variant: str, Dc: float, De: float | None = None):
    """Masses [(t, amount, pid)] and blocks [(t0, t1, amount, pid)] of the building with study period T."""
    De = Dc if De is None else De
    TF = Fraction(T)
    masses, blocks = [], []
    for pid, P in fam.items():
        # realised part
        for tm, thr, a in P.masses:
            if a == 0:
                continue
            t = Fraction(0) if thr is None else thr
            if thr is not None and thr > TF:
                continue
            if pid in INITIAL and variant in ("X1", "X4") and Dc > 0:
                blocks.append((-Fraction(Dc), Fraction(0), a, pid))
            elif pid in INITIAL and variant == "X2" and Dc > 0:
                if pid in ("P01", "P02"):
                    masses.append((-Fraction(Dc), a, pid))
                else:
                    blocks.append((-Fraction(Dc), Fraction(0), a, pid))
            else:
                masses.append((t, a, pid))
        for a0, b0, r in P.densities:
            if r == 0 or a0 >= TF:
                continue
            b = min(b0, TF)
            blocks.append((a0, b, r * (b - a0), pid))
        # terminal part (emitted at T)
        z = P.terminal_at(T)
        if z:
            if pid in EOL and variant in ("X3", "X4") and De > 0:
                blocks.append((TF, TF + Fraction(De), z, pid))
            else:
                masses.append((TF, z, pid))
    return masses, blocks


def total(masses, blocks) -> Fraction:
    return sum((a for t, a, p in masses), Fraction(0)) + sum((a for t0, t1, a, p in blocks), Fraction(0))


def cumulative(masses, blocks, t: Fraction) -> Fraction:
    """Real-time cumulative emission up to t (masses at time < t ... counted when t > their time; blocks pro rata)."""
    v = sum((a for tm, a, p in masses if tm < t), Fraction(0))
    for t0, t1, a, p in blocks:
        if t > t0:
            v += a * (min(t, t1) - t0) / (t1 - t0) if t1 > t0 else a
    return v
