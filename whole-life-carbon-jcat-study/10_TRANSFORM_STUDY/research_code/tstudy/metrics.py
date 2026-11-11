"""Error statistics used for every candidate (RESEARCH_PROTOCOL.md section 6).

Errors are signed relative errors of a candidate value against the frozen reference value:
``(candidate - reference) / |reference|``. A reference value of exactly zero cannot carry a
relative error; such pairs are counted separately (``n_ref_zero``) with the absolute error,
never dropped silently.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field


def signed_rel(candidate: float, reference: float) -> float | None:
    if reference == 0.0:
        return None
    return (candidate - reference) / abs(reference)


def percentile(sorted_values: list[float], q: float) -> float:
    """Linear-interpolation percentile of an ascending list (q in [0, 1])."""
    if not sorted_values:
        return math.nan
    if len(sorted_values) == 1:
        return sorted_values[0]
    pos = q * (len(sorted_values) - 1)
    lo = math.floor(pos)
    hi = min(lo + 1, len(sorted_values) - 1)
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * (pos - lo)


@dataclass
class ErrorStats:
    """Accumulates signed relative errors of one quantity over scenarios."""

    name: str
    errors: list[float] = field(default_factory=list)
    worst: tuple[float, str] | None = None            # (signed error, scenario id) of the largest |error|
    n_ref_zero: int = 0
    max_abs_when_ref_zero: float = 0.0
    n_nonfinite: int = 0

    def add(self, candidate: float, reference: float, scenario_id: str = "") -> None:
        if candidate is None or isinstance(candidate, bool) or math.isnan(candidate) or math.isinf(candidate):
            self.n_nonfinite += 1
            return
        e = signed_rel(candidate, reference)
        if e is None:
            self.n_ref_zero += 1
            self.max_abs_when_ref_zero = max(self.max_abs_when_ref_zero, abs(candidate))
            return
        self.errors.append(e)
        if self.worst is None or abs(e) > abs(self.worst[0]):
            self.worst = (e, scenario_id)

    def summary(self) -> dict:
        errs = self.errors
        absolute = sorted(abs(e) for e in errs)
        n = len(errs)
        return {
            "quantity": self.name,
            "n": n,
            "mean_signed": sum(errs) / n if n else None,
            "mean_abs": sum(absolute) / n if n else None,
            "p95_abs": percentile(absolute, 0.95) if n else None,
            "max_abs": absolute[-1] if n else None,
            "min_signed": min(errs) if n else None,
            "max_signed": max(errs) if n else None,
            "share_under": sum(1 for e in errs if e < 0.0) / n if n else None,
            "worst": {"error": self.worst[0], "scenario": self.worst[1]} if self.worst else None,
            "n_ref_zero": self.n_ref_zero,
            "max_abs_when_ref_zero": self.max_abs_when_ref_zero,
            "n_nonfinite": self.n_nonfinite,
        }


def propagate_stage_change(stage_values: dict[str, float], included: list[str], changed: dict[str, float]) -> dict[str, float]:
    """Totals after replacing some stage values (downstream propagation of an approximation).

    ``stage_values`` are the reference stage values, ``changed`` the candidate values of the
    stages a candidate re-computes. Upfront = A1-A3..A5, embodied = all but B6 and B7,
    whole life = all included stages (the definitions of SUM-01..03 of the concept model).
    """
    v = dict(stage_values)
    v.update(changed)
    inc = set(included)
    upfront = sum(v[s] for s in ("A1-A3", "A4", "A5") if s in inc)
    embodied = sum(x for s, x in v.items() if s in inc and s not in ("B6", "B7"))
    whole = sum(x for s, x in v.items() if s in inc)
    return {"SUM-01": upfront, "SUM-02": embodied, "SUM-03": whole}
