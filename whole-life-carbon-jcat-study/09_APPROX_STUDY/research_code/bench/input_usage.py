#!/usr/bin/env python3
"""Which input fields are actually read: reference calculation versus unified model.

Every attribute read on the scenario objects is traced while a calculation runs on a
set of fictional scenarios (benchmark S and the edge cases). A field counts as read by
a calculation when any scenario makes the calculation read it. Reading a field is not
the same as the field influencing a result, so this is an upper bound of what is needed.

The input ids are those of 03_INPUTS/inputs.json (124) plus the fields this study added
(NEW:...). Research tooling only; nothing is changed in the scenarios.

Run:  cd research_code && python3 -m bench.input_usage
"""
from __future__ import annotations

import dataclasses
import inspect
import json
import sys
import typing
from pathlib import Path

from fastcalc import engine
from refcalc import registry
from synth import model, population

OUT = Path(__file__).resolve().parents[2] / "04_VERIFICATION" / "input_usage.json"
CLASSES = [c for _, c in inspect.getmembers(model, inspect.isclass) if dataclasses.is_dataclass(c) and c.__module__ == model.__name__]


def traced(fn) -> set:
    """Run ``fn`` and return the (class name, field) pairs read on model objects."""
    seen = set()
    base = object.__getattribute__

    def make(name, fields):
        def getter(self, attr):
            if attr in fields:
                seen.add((name, attr))
            return base(self, attr)
        return getter

    for cls in CLASSES:
        cls.__getattribute__ = make(cls.__name__, {f.name for f in dataclasses.fields(cls)})
    try:
        fn()
    finally:
        for cls in CLASSES:
            del cls.__getattribute__
    return seen


def owner_of(path: str):
    """(class name, field) of a model path such as ``materials[].transport.mass_t``."""
    cls = model.Scenario
    parts = [p.replace("[]", "").replace("{}", "") for p in path.split(".")]
    for i, name in enumerate(parts):
        if i == len(parts) - 1:
            return cls.__name__, name
        hint = typing.get_type_hints(cls)[name]
        while True:
            args = [a for a in typing.get_args(hint) if a is not type(None)]
            if dataclasses.is_dataclass(hint):
                break
            if not args:
                return cls.__name__, name          # a plain container: the field itself is the input
            hint = args[-1]
        cls = hint
    return cls.__name__, parts[-1]


def main() -> int:
    registry.load_all()
    scenarios = [population.standard_benchmark()[0]] + [s for _, s in population.edge_cases()]
    runs = {
        "reference_all_units": lambda s: registry.run_all(s),
        "unified_full_outputs": lambda s: engine.evaluate(s, detail=True),
        "unified_totals_only": lambda s: engine.evaluate(s, detail=False),
    }
    read = {}
    for name, fn in runs.items():
        seen = set()
        for scn in scenarios:
            seen |= traced(lambda: fn(scn))
        read[name] = seen
    fields = {}
    for input_id, path in list(model.INPUT_FIELD_MAP.items()) + list(model.EXTRA_FIELD_MAP.items()):
        if path == model.METADATA_ONLY:
            fields[input_id] = {"model_path": None, "metadata_only": True}
            continue
        owner = owner_of(path)
        fields[input_id] = {"model_path": path, "metadata_only": False, **{name: owner in seen for name, seen in read.items()}}
    live = {k: v for k, v in fields.items() if not v["metadata_only"]}
    count = lambda name, new: sum(1 for k, v in live.items() if v[name] and k.startswith("NEW:") == new)
    summary = {name: {"existing_inputs_read": count(name, False), "added_inputs_read": count(name, True)} for name in runs}
    not_in_totals = sorted(k for k, v in live.items() if v["reference_all_units"] and not v["unified_totals_only"])
    not_in_full = sorted(k for k, v in live.items() if v["reference_all_units"] and not v["unified_full_outputs"])
    never = sorted(k for k, v in live.items() if not v["reference_all_units"])
    OUT.write_text(json.dumps({
        "schema_version": "1.0",
        "what_is_measured": "Attribute reads on the scenario objects during a calculation, on fictional scenarios. A read field is an upper bound of a needed field.",
        "scenarios": len(scenarios),
        "inputs_in_specification": len(model.INPUT_FIELD_MAP), "inputs_added_by_this_study": len(model.EXTRA_FIELD_MAP),
        "metadata_only_inputs": sum(1 for v in fields.values() if v["metadata_only"]),
        "summary": summary,
        "read_by_reference_but_not_by_unified_totals_only": not_in_totals,
        "read_by_reference_but_not_by_unified_full_outputs": not_in_full,
        "not_read_by_reference": never,
        "fields": fields}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    print("reference only (vs totals):", not_in_totals)
    print("reference only (vs full):", not_in_full)
    print("not read by the reference:", len(never))
    return 0


if __name__ == "__main__":
    sys.exit(main())
