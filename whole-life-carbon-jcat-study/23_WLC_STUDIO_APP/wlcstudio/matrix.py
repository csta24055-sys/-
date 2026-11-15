"""Vectorised parts of the bridge — only where the relation is genuinely linear (directive section 4).

1. Field → engine-input incidence  M ∈ {0,1}^{E×F}  (E engine ids reached by the screens, F screen fields) with three
   state masks over the fields: has (value-bearing), na (適用外), unknown (未取得・計算不能). "Unknown" is its own mask,
   never a 0 in `has`: reached = M·has > 0, blocked = M·unknown > 0 are reported separately.
2. A1-A3 of the generic material rows as an elementwise product  e = q ⊙ c ⊙ f  with
     q  the row quantity, c the unit multiplier (to the factor unit) × 1/(1−w) when the basis is DESIGN, f the factor value,
   and the stage sum  E = 1ᵀe. This mirrors engine unit A13-01 for rows that resolve to a generic factor (no EPD, no
   composite); tests/test_matrix.py checks e against the engine's own A13-01.by_item to 1e-9 relative.
3. Interval bounds of that sum: with c ≥ 0 and f ≥ 0, E is monotone in every q_i, so [1ᵀ(q_lo⊙c⊙f), 1ᵀ(q_hi⊙c⊙f)] is
   the exact range for independent q_i in [q_lo, q_hi] (no sampling).

NOT vectorised (left to the engine, as the Phase 0 audit lists): the 0/1 gates (licence, single stage, unit
convertibility, EPD dates), first-match lookups, the refrigerant state recurrence, the time knots and ceil/rounding,
SUM-05 (1/T) — forcing those into a matrix product would change the results.
"""
from __future__ import annotations

import numpy as np

from . import fields as FL
from .provenance import HAS_VALUE, Value


def incidence(values: dict[str, Value]) -> dict:
    fids = list(FL.FIELDS)
    eng = sorted({e for F in FL.FIELDS.values() for e in F["engine"]})
    M = np.zeros((len(eng), len(fids)), dtype=np.int8)
    ei = {e: i for i, e in enumerate(eng)}
    for j, fid in enumerate(fids):
        for e in FL.FIELDS[fid]["engine"]:
            M[ei[e], j] = 1
    st = [values[f].state if f in values else "not_obtained" for f in fids]
    has = np.array([s in HAS_VALUE for s in st], dtype=np.int8)
    na = np.array([s == "not_applicable" for s in st], dtype=np.int8)
    unknown = np.array([s in ("not_obtained", "not_computable") for s in st], dtype=np.int8)
    assert np.all(has + na + unknown == 1)          # every field is in exactly one mask
    reached = (M @ has) > 0
    only_unknown = ((M @ unknown) > 0) & ~reached & ((M @ na) == 0)
    return {"engine_ids": eng, "fields": fids, "M": M, "has": has, "na": na, "unknown": unknown,
            "n_engine_ids": len(eng), "n_reached": int(reached.sum()), "n_only_unknown": int(only_unknown.sum()),
            "reached": [e for e, r in zip(eng, reached) if r], "only_unknown": [e for e, r in zip(eng, only_unknown) if r],
            "no_engine_input": [f for f in fids if not FL.FIELDS[f]["engine"]]}


def _conv(refset: dict, from_unit: str, to_unit: str) -> float | None:
    if from_unit == to_unit:
        return 1.0
    for c in refset["data"]["unit_conversions"]:
        if c["from_unit"] == from_unit and c["to_unit"] == to_unit:
            return float(c["factor"])
    return None


def a13_vectors(doc: dict, refset: dict) -> dict:
    """q, c, f of the material rows of a bridge document (generic factors only) and e = q ⊙ c ⊙ f."""
    rows = []
    for cat in doc["categories"].values():
        rows += cat["tables"].get("materials", [])
    F = refset["data"]["factors"]
    q, c, f, ids, skipped = [], [], [], [], []
    for r in rows:
        rec = F.get(r.get("factor_id"))
        w = r.get("waste_rate")
        if rec is None or w is None or not (0 <= w < 1) or r.get("quantity") is None:
            skipped.append(r["material_id"])          # the engine skips such a row too (A13-05 gate)
            continue
        k = _conv(refset, r["quantity_unit"], rec["unit"])
        if k is None:
            skipped.append(r["material_id"])
            continue
        mult = k / (1.0 - w) if r.get("quantity_basis") == "DESIGN" else k
        q.append(float(r["quantity"]))
        c.append(mult)
        f.append(float(rec["value"]))
        ids.append(r["material_id"])
    q, c, f = np.array(q), np.array(c), np.array(f)
    e = q * c * f
    return {"ids": ids, "q": q, "c": c, "f": f, "e": e, "total": float(e.sum()), "skipped": skipped}


def a13_bounds(vec: dict, q_lo: np.ndarray, q_hi: np.ndarray) -> tuple[float, float]:
    if np.any(vec["c"] < 0) or np.any(vec["f"] < 0):
        raise ValueError("係数が負の行があるので単調ではない（区間の端だけでは決まらない）")
    w = vec["c"] * vec["f"]
    return float(w @ q_lo), float(w @ q_hi)
