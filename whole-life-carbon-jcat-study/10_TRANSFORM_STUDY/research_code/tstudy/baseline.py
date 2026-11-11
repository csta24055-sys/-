"""Read-only access to the frozen reference calculation (the baseline of every error).

The baseline is the reference calculation of the earlier study as committed
(``09_APPROX_STUDY/research_code/refcalc`` with the fictional scenario generator ``synth``).
It is never modified. ``assert_frozen`` checks, before anything is measured, that the code
on disk is the committed code and that the committed code has the tree ids recorded in
``00_POLICY/RESEARCH_PROTOCOL.md`` section 2.
"""
from __future__ import annotations

import os
import subprocess
import sys
from typing import Any, Iterable

sys.dont_write_bytecode = True

_HERE = os.path.dirname(os.path.abspath(__file__))
STUDY_ROOT = os.path.normpath(os.path.join(_HERE, "..", "..", ".."))
REPO_ROOT = os.path.normpath(os.path.join(STUDY_ROOT, ".."))
FROZEN_REL = "whole-life-carbon-jcat-study/09_APPROX_STUDY/research_code"
FROZEN_CODE = os.path.join(REPO_ROOT, FROZEN_REL)

FROZEN_TREES = {
    "refcalc": "8976efea85c313e5e723fadf12382e02b3202913",
    "synth": "55caf5cd40db34e195678656e61d3ebdd65308ec",
    "common": "ad3d0b7eff1501655f35132d416159611d0ab1cd",
}

_checked = False
_registry = None


class BaselineChanged(RuntimeError):
    """The reference calculation on disk is not the frozen one."""


def _git(*args: str) -> str:
    return subprocess.run(["git", "-C", REPO_ROOT, *args], capture_output=True, text=True, check=True).stdout.strip()


def assert_frozen() -> dict[str, str]:
    """Raise ``BaselineChanged`` unless the baseline folders equal the recorded trees."""
    global _checked
    for name, want in FROZEN_TREES.items():
        rel = f"{FROZEN_REL}/{name}"
        got = _git("rev-parse", f"HEAD:{rel}")
        if got != want:
            raise BaselineChanged(f"{rel}: committed tree {got}, expected {want}")
        dirty = _git("status", "--porcelain", "--", rel)
        if dirty:
            raise BaselineChanged(f"{rel}: working tree differs from the commit:\n{dirty}")
    _checked = True
    return dict(FROZEN_TREES)


def load():
    """Import the frozen packages (read-only) and return the reference registry."""
    global _registry
    if _registry is None:
        if not _checked:
            assert_frozen()
        if FROZEN_CODE not in sys.path:
            sys.path.insert(0, FROZEN_CODE)
        from refcalc import registry  # noqa: E402  (frozen code)

        registry.load_all()
        _registry = registry
    return _registry


def unit_ids() -> list[str]:
    return sorted(load().UNITS)


def depends_on(unit_id: str) -> tuple[str, ...]:
    return load().UNITS[unit_id].depends_on


def run_reference(scn, ids: Iterable[str] | None = None) -> dict[str, dict[str, Any]]:
    """The reference results of ``scn`` (all units, or ``ids`` with their dependencies)."""
    return load().run_all(scn, ids)


def stage_vector(res: dict[str, dict]) -> dict[str, float]:
    """The 14 life-cycle stage values of a reference result (unit X-02)."""
    return dict(res["X-02"]["by_stage"])


def totals(res: dict[str, dict]) -> dict[str, float]:
    """Upfront, embodied and whole-life totals (units SUM-01..03)."""
    return {"SUM-01": res["SUM-01"]["value"], "SUM-02": res["SUM-02"]["value"], "SUM-03": res["SUM-03"]["value"]}
