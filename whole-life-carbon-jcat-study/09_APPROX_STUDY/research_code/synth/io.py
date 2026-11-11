"""JSON round-trip for scenarios (reproducibility of the synthetic data)."""
from __future__ import annotations

import json
import types
import typing
from dataclasses import asdict, fields, is_dataclass
from pathlib import Path
from typing import Any

from . import model
from .model import Scenario


def to_dict(scenario: Scenario) -> dict[str, Any]:
    """Plain-JSON representation of a scenario."""
    return asdict(scenario)


def _build(tp: Any, value: Any) -> Any:
    if value is None:
        return None
    origin = typing.get_origin(tp)
    if origin in (typing.Union, types.UnionType):
        args = [a for a in typing.get_args(tp) if a is not type(None)]
        return _build(args[0], value) if len(args) == 1 else value
    if origin in (list, typing.Sequence):
        (item,) = typing.get_args(tp) or (Any,)
        return [_build(item, v) for v in value]
    if origin is tuple:
        args = typing.get_args(tp)
        item = args[0] if args else Any
        return tuple(_build(item, v) for v in value)
    if origin is dict:
        args = typing.get_args(tp)
        item = args[1] if len(args) == 2 else Any
        return {k: _build(item, v) for k, v in value.items()}
    if isinstance(tp, type) and is_dataclass(tp):
        hints = typing.get_type_hints(tp, vars(model))
        return tp(**{f.name: _build(hints[f.name], value[f.name]) for f in fields(tp) if f.name in value})
    return value


def from_dict(data: dict[str, Any]) -> Scenario:
    """Inverse of ``to_dict``."""
    return _build(Scenario, data)


def save_json(scenario: Scenario, path: str | Path) -> None:
    Path(path).write_text(json.dumps(to_dict(scenario), ensure_ascii=False, sort_keys=True), encoding="utf-8")


def load_json(path: str | Path) -> Scenario:
    return from_dict(json.loads(Path(path).read_text(encoding="utf-8")))
