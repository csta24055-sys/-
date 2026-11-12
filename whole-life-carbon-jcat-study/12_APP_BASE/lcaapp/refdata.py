"""Reference data sets: emission factors and other standard values the engine needs.

A set is plain data in the engine's own shape::

    {"format": "lca-refset/1", "name": "...", "version": "...",
     "data_kind": "fictional" | "licensed",
     "licence_status": "PERMITTED_PUBLIC", "source_note": "...",
     "data": {"gases": [...], "gwp": {...}, "unit_conversions": [...], "factors": {...},
              "price_index": {...}, "standard_values": {...}}}

Only two kinds can be registered:

* ``fictional`` - every factor record must carry the tag ``SYNTHETIC_FICTIONAL``;
* ``licensed``  - the registrant declares ``licence_status == "PERMITTED_PUBLIC"`` and names the
  source in ``source_note``. The app cannot check a licence; the declaration is stored with
  the set. Values of third-party tools must not be registered without permission
  (01_COMPLIANCE). No such data is shipped with the app.
"""
from __future__ import annotations

import hashlib
import json
import math
from typing import Any

from . import REFSET_FORMAT, schema
from .convert import FICTIONAL_TAG

KINDS = ("fictional", "licensed")
PERMITTED = "PERMITTED_PUBLIC"
ITEM_KINDS = ("gases", "gwp", "unit_conversions", "factors", "price_index", "standard_values")


class RefsetError(ValueError):
    """The reference data set may not be registered."""


def _num(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def digest(data: dict) -> str:
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def check(refset: Any) -> tuple[dict, list[dict]]:
    """Validated copy of a set and the list of records left out. Raises ``RefsetError`` when the
    set as a whole may not be registered."""
    if not isinstance(refset, dict) or refset.get("format") != REFSET_FORMAT:
        raise RefsetError("参照データは format %s のオブジェクトで与える" % REFSET_FORMAT)
    name, version = refset.get("name"), refset.get("version")
    if not isinstance(name, str) or not name or not isinstance(version, str) or not version:
        raise RefsetError("参照データには name と version（文字列）が要る")
    kind = refset.get("data_kind")
    if kind not in KINDS:
        raise RefsetError("data_kind は %s のどちらか" % "／".join(KINDS))
    data = refset.get("data")
    if not isinstance(data, dict):
        raise RefsetError("data がない")
    if kind == "licensed":
        if refset.get("licence_status") != PERMITTED or not str(refset.get("source_note") or "").strip():
            raise RefsetError("licensed の登録には licence_status = %s の宣言と、出典を書いた source_note が要る" % PERMITTED)
    gases = data.get("gases")
    gwp = data.get("gwp")
    if not isinstance(gases, list) or not gases or not all(isinstance(g, str) for g in gases):
        raise RefsetError("data.gases（ガス名の一覧）が要る")
    if not isinstance(gwp, dict) or not all(_num(gwp.get(g)) for g in gases):
        raise RefsetError("data.gwp に、すべてのガスの数値が要る")
    left_out: list[dict] = []
    factors = {}
    raw_factors = data.get("factors") or {}
    if not isinstance(raw_factors, dict):
        raise RefsetError("data.factors はオブジェクトで与える")
    fields = schema.model_schema()["factors"]["row"]["fields"]
    for fid, rec in raw_factors.items():
        why = None
        if not isinstance(rec, dict):
            why = "記録がオブジェクトではない"
        elif set(fields) - set(rec):
            why = "項目が足りない：" + "、".join(sorted(set(fields) - set(rec)))
        elif rec.get("factor_id") != fid:
            why = "factor_id がキーと違う"
        elif not _num(rec.get("value")) or not isinstance(rec.get("unit"), str) or not isinstance(rec.get("stages"), list):
            why = "value・unit・stages のどれかが使えない"
        elif not isinstance(rec.get("gas_amounts"), dict) or not all(_num(rec["gas_amounts"].get(g)) for g in gases):
            why = "gas_amounts に、すべてのガスの数値がない"
        elif kind == "fictional" and rec.get("source_tag") != FICTIONAL_TAG:
            raise RefsetError("fictional の参照データには、タグ %s のない係数（%s）を入れられない" % (FICTIONAL_TAG, fid))
        if why:
            left_out.append({"kind": "factor", "key": fid, "reason": why})
        else:
            factors[fid] = rec
    conversions = []
    for i, conv in enumerate(data.get("unit_conversions") or []):
        if isinstance(conv, dict) and isinstance(conv.get("from_unit"), str) and isinstance(conv.get("to_unit"), str) \
                and _num(conv.get("factor")) and isinstance(conv.get("basis"), str):
            conversions.append(conv)
        else:
            left_out.append({"kind": "unit_conversion", "key": str(i), "reason": "from_unit・to_unit・factor・basis が揃っていない"})
    price_index = {}
    for year, value in (data.get("price_index") or {}).items():
        try:
            int(year)
        except (TypeError, ValueError):
            left_out.append({"kind": "price_index", "key": str(year), "reason": "年が整数ではない"})
            continue
        if _num(value):
            price_index[str(year)] = value
        else:
            left_out.append({"kind": "price_index", "key": str(year), "reason": "数値ではない"})
    standard = data.get("standard_values") or {}
    if not isinstance(standard, dict):
        raise RefsetError("data.standard_values はオブジェクトで与える")
    clean = {"gases": list(gases), "gwp": {g: gwp[g] for g in gases}, "unit_conversions": conversions,
             "factors": factors, "price_index": price_index, "standard_values": standard}
    out = {"format": REFSET_FORMAT, "name": name, "version": version, "data_kind": kind,
           "licence_status": refset.get("licence_status") or (PERMITTED if kind == "fictional" else ""),
           "source_note": str(refset.get("source_note") or ""), "data": clean}
    out["sha256"] = digest(clean)
    return out, left_out


def from_model(model_dict: dict, name: str, version: str, source_note: str) -> dict:
    """A fictional reference set made of the reference parts of a generated scenario."""
    data = {part: model_dict[part] for part in schema.REFERENCE_PARTS}
    data["price_index"] = {str(k): v for k, v in data["price_index"].items()}
    data["standard_values"] = {}
    return {"format": REFSET_FORMAT, "name": name, "version": version, "data_kind": "fictional",
            "licence_status": PERMITTED, "source_note": source_note, "data": data}
