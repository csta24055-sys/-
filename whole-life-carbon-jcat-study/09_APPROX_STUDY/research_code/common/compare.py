"""Mechanical comparison of a candidate result with the reference result.

Errors are signed: negative means the candidate is BELOW the reference
(under-estimation), which the study tracks separately.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


def flatten(value: Any, prefix: str = "") -> dict[str, Any]:
    """Flatten nested dict/list results into ``{"path": leaf}``."""
    out: dict[str, Any] = {}
    if isinstance(value, dict):
        for key in sorted(value, key=str):
            if str(key).startswith("_"):
                continue  # working data for downstream units, not a result
            out.update(flatten(value[key], f"{prefix}.{key}" if prefix else str(key)))
    elif isinstance(value, (list, tuple)):
        for i, item in enumerate(value):
            out.update(flatten(item, f"{prefix}[{i}]"))
    else:
        out[prefix] = value
    return out


def signed_rel_error(ref: float, cand: float, floor: float = 0.0) -> float:
    """(cand - ref) / max(|ref|, floor). Zero when both are zero."""
    if ref == cand:
        return 0.0
    den = max(abs(ref), floor)
    if den == 0.0:
        return math.copysign(math.inf, cand - ref)
    return (cand - ref) / den


@dataclass
class Comparison:
    n_numeric: int = 0
    n_other: int = 0
    max_abs_rel_error: float = 0.0
    min_signed_rel_error: float = 0.0  # most negative = worst under-estimation
    max_signed_rel_error: float = 0.0
    worst_path: str = ""
    mismatches: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    extra: list[str] = field(default_factory=list)

    def within(self, rel_tol: float) -> bool:
        return not self.mismatches and not self.missing and self.max_abs_rel_error <= rel_tol


def compare(ref: Any, cand: Any, floor: float = 0.0, paths: set[str] | None = None,
            ignore_missing: bool = False) -> Comparison:
    """Compare every leaf of ``ref`` with ``cand``.

    ``floor`` guards relative errors of quantities whose reference is ~0.
    ``paths`` restricts the comparison to the given leaf paths.
    ``ignore_missing`` skips reference leaves the candidate does not produce (used for
    the summary mode, which leaves out per-row lists and yearly series).
    Non-numeric leaves (bools, strings, None) must be equal.
    """
    c = Comparison()
    fr, fc = flatten(ref), flatten(cand)
    for path, rv in fr.items():
        if paths is not None and path not in paths:
            continue
        if path not in fc:
            if not ignore_missing:
                c.missing.append(path)
            continue
        cv = fc[path]
        numeric = isinstance(rv, (int, float)) and not isinstance(rv, bool)
        if numeric and isinstance(cv, (int, float)) and not isinstance(cv, bool):
            if math.isnan(rv) or math.isnan(cv):
                if not (math.isnan(rv) and math.isnan(cv)):
                    c.mismatches.append(f"{path}: {rv!r} vs {cv!r}")
                continue
            err = signed_rel_error(float(rv), float(cv), floor)
            c.n_numeric += 1
            c.min_signed_rel_error = min(c.min_signed_rel_error, err)
            c.max_signed_rel_error = max(c.max_signed_rel_error, err)
            if abs(err) > c.max_abs_rel_error:
                c.max_abs_rel_error = abs(err)
                c.worst_path = path
        else:
            c.n_other += 1
            if rv != cv:
                c.mismatches.append(f"{path}: {rv!r} vs {cv!r}")
    if paths is None:
        c.extra = sorted(set(fc) - set(fr))
    return c


def percentile(values: list[float], q: float) -> float:
    """Linear-interpolated percentile (q in 0..100) of a non-empty list."""
    xs = sorted(values)
    if not xs:
        raise ValueError("empty")
    pos = (len(xs) - 1) * q / 100.0
    lo, hi = math.floor(pos), math.ceil(pos)
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)
