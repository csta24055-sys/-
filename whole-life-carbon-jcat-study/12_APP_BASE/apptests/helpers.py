"""Shared fixtures of the tests. All data is fictional (frozen generator of the earlier study)."""
from __future__ import annotations

import copy
import json
import os
import tempfile

from lcaapp import binding, common, convert, enginepath, refdata, sample, service, store

_cache: dict = {}


def building(seed: int = 4201, rows: int | None = 12, **kw):
    """(input document, reference set, scenario dict) of a small fictional building (deep copies)."""
    key = (seed, rows, tuple(sorted(kw.items())))
    if key not in _cache:
        _cache[key] = sample.fictional_building(seed=seed, rows=rows, **kw)
    return copy.deepcopy(_cache[key])


def through_json(obj):
    return json.loads(json.dumps(obj, ensure_ascii=False))


def units(refset: dict) -> dict:
    return common.unit_table(refset["data"]["unit_conversions"])


def to_common(doc: dict, refset: dict, bind=None) -> dict:
    return common.build(through_json(doc), bind or binding.provisional(), units(refset))


def direct_results(model_dict: dict, period: float) -> dict:
    """The engine called directly on the scenario dict, without the app in between."""
    scn = enginepath.model_io().from_dict(copy.deepcopy(model_dict))
    return through_json(enginepath.unified().System(scn).at(period))


class TempStore:
    """A storage file in a temporary folder, removed afterwards."""

    def __enter__(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.dir.name, "test.sqlite3")
        self.store = store.Store(self.path)
        self.service = service.Service(self.store)
        return self

    def reopen(self):
        self.store.close()
        self.store = store.Store(self.path)
        self.service = service.Service(self.store)
        return self

    def __exit__(self, *exc):
        self.store.close()
        self.dir.cleanup()


def item(doc: dict, category: str, item_id: str):
    return doc["categories"][category]["items"][item_id]


def set_item(doc: dict, category: str, item_id: str, value) -> None:
    doc["categories"][category]["items"][item_id] = value


def cell_at(data: dict, section: str, *names):
    node = data["sections"][section]
    for name in names:
        node = node["rows"][name] if isinstance(name, int) else node["f"][name]
    return node


__all__ = ["binding", "common", "convert", "enginepath", "refdata", "sample", "service", "store"]
