"""Address → coordinate candidates with the GSI (国土地理院) address search, and coordinate → address.

Returns candidates only; the user picks one. The registry entry `gsi_address_search` records the
terms (attribution 「国土地理院」, no guarantee of accuracy). An address that matches only to a
town/chome level is marked as such: it does not identify a building.
"""
from __future__ import annotations

import re
import urllib.parse

from .net import SourceError, get_json

SEARCH = "https://msearch.gsi.go.jp/address-search/AddressSearch?q="
REVERSE = "https://mreversegeocoder.gsi.go.jp/reverse-geocoder/LonLatToAddress?lat=%.7f&lon=%.7f"


def _precision(title: str) -> str:
    if re.search(r"\d+番(地)?\d*|\d+-\d+(-\d+)?$|\d+号", title):
        return "lot"            # 番地・号まで一致
    if re.search(r"(丁目|町|村|字)", title):
        return "town"           # 町・丁目まで（建物は特定できない）
    return "area"


def geocode(address: str, limit: int = 8) -> dict:
    q = (address or "").strip()
    if not q:
        raise SourceError("住所または名称を入力する")
    # an address is personal data: it is sent to GSI but never written to the local cache
    data, meta = get_json(SEARCH + urllib.parse.quote(q), use_cache=False)
    if not isinstance(data, list):
        raise SourceError("住所検索の応答の形が想定と違う")
    cands = []
    for f in data[:limit]:
        try:
            lon, lat = f["geometry"]["coordinates"]
            title = f["properties"]["title"]
        except (KeyError, TypeError, ValueError):
            continue
        cands.append({"title": title, "lat": float(lat), "lon": float(lon), "precision": _precision(title)})
    return {"query": q, "candidates": cands, "source_id": "gsi_address_search", "fetched_at": meta["fetched_at"],
            "from_cache": meta["from_cache"],
            "note": "住所の一致は候補であり、同じ住所に複数の建物があることがある。地図で建物を確認して選ぶ。"}


def reverse(lat: float, lon: float) -> dict:
    data, meta = get_json(REVERSE % (lat, lon), use_cache=False)
    res = (data or {}).get("results") if isinstance(data, dict) else None
    return {"lat": lat, "lon": lon, "result": res, "source_id": "gsi_reverse_geocoder", "fetched_at": meta["fetched_at"]}
