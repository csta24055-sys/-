"""Registry and dependency-ordered runner for reference unit functions.

A unit function has the signature ``fn(scn, res) -> dict`` where ``scn`` is a
``synth.model.Scenario`` and ``res`` maps the ids of already computed units to
their results. Result conventions (so that results can be compared mechanically):

    {"value": float}                     scalar result (kgCO2e unless stated)
    {"value": ..., "by_item": [...]}     optional breakdown aligned with input rows
    {"value": ..., "by_year": [...]}     optional breakdown per year index
    {"value": ..., "by_stage": {...}}    optional breakdown per life-cycle stage
    {"ok": bool, "violations": [...]}    validation / gate units

A unit must read ``res`` only for the ids it declares in ``depends_on``.
"""
from __future__ import annotations

import importlib
import pkgutil
from dataclasses import dataclass
from typing import Any, Callable, Iterable


@dataclass(frozen=True)
class UnitDef:
    unit_id: str
    fn: Callable[[Any, dict], dict]
    depends_on: tuple[str, ...]
    doc: str


UNITS: dict[str, UnitDef] = {}


def unit(unit_id: str, depends_on: Iterable[str] = ()):
    """Register ``fn`` as the reference implementation of ``unit_id``."""

    def deco(fn):
        if unit_id in UNITS:
            raise ValueError(f"duplicate reference unit {unit_id}")
        UNITS[unit_id] = UnitDef(unit_id, fn, tuple(depends_on), (fn.__doc__ or "").strip())
        return fn

    return deco


def load_all() -> dict[str, UnitDef]:
    """Import every ``refcalc.units_*`` module so that its units register."""
    import refcalc

    for info in pkgutil.iter_modules(refcalc.__path__):
        if info.name.startswith("units_"):
            importlib.import_module(f"refcalc.{info.name}")
    return UNITS


def order(ids: Iterable[str] | None = None) -> list[str]:
    """Topological order of ``ids`` (default: all) including their dependencies."""
    wanted = list(UNITS) if ids is None else list(ids)
    done: list[str] = []
    state: dict[str, int] = {}

    def visit(uid: str, chain: tuple[str, ...]) -> None:
        if state.get(uid) == 2:
            return
        if state.get(uid) == 1:
            raise ValueError("dependency cycle: " + " -> ".join(chain + (uid,)))
        if uid not in UNITS:
            raise KeyError(f"unit {uid} is not registered (needed by {chain[-1] if chain else 'caller'})")
        state[uid] = 1
        for dep in UNITS[uid].depends_on:
            visit(dep, chain + (uid,))
        state[uid] = 2
        done.append(uid)

    for uid in sorted(wanted):
        visit(uid, ())
    return done


class Hook:
    """Override to observe each unit call (timing, counting, memory)."""

    def before(self, unit_id: str) -> None:  # pragma: no cover - interface
        pass

    def after(self, unit_id: str) -> None:  # pragma: no cover - interface
        pass


def run_all(scn, ids: Iterable[str] | None = None, hook: Hook | None = None) -> dict[str, dict]:
    """Compute the requested units (default: all) in dependency order."""
    res: dict[str, dict] = {}
    for uid in order(ids):
        fn = UNITS[uid].fn
        if hook is not None:
            hook.before(uid)
            res[uid] = fn(scn, res)
            hook.after(uid)
        else:
            res[uid] = fn(scn, res)
    return res
