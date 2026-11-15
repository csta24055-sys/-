"""Public building attributes from PLATEAU 3D Tiles (国土交通省 Project PLATEAU), near a coordinate.

Path (all public, see registry.json `plateau`):
  1. municipality code from the GSI reverse geocoder (muniCd)
  2. the PLATEAU data catalog → building model (bldg) 3D Tiles of that city (smallest LOD)
  3. walk the tileset to the leaf tiles whose region contains the point
  4. read only the b3dm header and its batch table (HTTP Range) → per-building attributes
  5. buildings whose footprint box contains the point, else the nearest within `radius_m`

What PLATEAU gives is a candidate, not a confirmed fact: the user confirms the building. Attributes
that PLATEAU does not record (e.g. RC/S/SRC/W, the exact total floor area) are not invented:
structure is offered only as a hint from 建物構造コード / 耐火区分, and the total floor area only as an
explicitly marked estimate (屋根伏面積 × 地上階数 × 延べ面積換算係数, when the factor is present).
"""
from __future__ import annotations

import json
import math
import struct

from . import gsi
from .net import SourceError, get, get_json

CATALOG = "https://api.plateauview.mlit.go.jp/datacatalog/plateau-datasets"
SOURCE_ID = "plateau"


def _hav(lat1, lon1, lat2, lon2) -> float:
    r = 6371008.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def city_datasets(city_code: str) -> list[dict]:
    cat, _ = get_json(CATALOG, max_age=7 * 86400, timeout=90)
    # designated cities (政令市) publish per ward: the GSI muniCd is then the ward code (e.g. 熊本市中央区 43101,
    # city 43100), so a ward match comes first, then a whole-city dataset without a ward
    def pick(key):
        ward = [d for d in cat.get(key, []) if d.get("type_en") == "bldg" and str(d.get("ward_code") or "") == city_code]
        return ward or [d for d in cat.get(key, []) if d.get("type_en") == "bldg" and d.get("city_code") == city_code
                        and not d.get("ward_code")]
    rows = pick("latest_datasets") or pick("datasets")
    def lod(d):
        try:
            return int(str(d.get("lod") or 9))
        except ValueError:
            return 9
    rows.sort(key=lambda d: (lod(d), d.get("texture") is True, d.get("file_size") or 0))
    return rows


def _resolve(url: str, base: str) -> str:
    if url.startswith("http"):
        return url
    return base.rsplit("/", 1)[0] + "/" + url


def _contains(region, lat, lon) -> bool:
    w, s, e, n = region[:4]
    x, y = math.radians(lon), math.radians(lat)
    return w <= x <= e and s <= y <= n


def _leaf_tiles(ts_url: str, lat: float, lon: float, depth: int = 0) -> list[str]:
    ts, _ = get_json(ts_url, max_age=30 * 86400)
    out: list[str] = []

    def walk(node):
        reg = node.get("boundingVolume", {}).get("region")
        if reg and not _contains(reg, lat, lon):
            return
        uri = (node.get("content") or {}).get("uri") or (node.get("content") or {}).get("url")
        if uri:
            full = _resolve(uri, ts_url)
            if full.endswith(".json") and depth < 3:
                out.extend(_leaf_tiles(full, lat, lon, depth + 1))
            elif full.endswith(".b3dm"):
                out.append(full)
        for ch in node.get("children", []) or []:
            walk(ch)
    walk(ts["root"])
    return out


def _batch_table(b3dm_url: str) -> tuple[int, dict]:
    head, _ = get(b3dm_url, rng=(0, 27))
    magic, ver, blen, ftj, ftb, btj, btb = struct.unpack("<4sIIIIII", head[:28])
    if magic != b"b3dm":
        raise SourceError("建物の 3D Tiles の形式が想定と違う（b3dm でない）")
    start = 28
    ftjson, _ = get(b3dm_url, rng=(start, start + ftj - 1))
    n = json.loads(ftjson.decode("utf-8")).get("BATCH_LENGTH", 0)
    if not btj:
        return n, {}
    bstart = start + ftj + ftb
    bt_raw, _ = get(b3dm_url, rng=(bstart, bstart + btj - 1), timeout=120)
    bt = json.loads(bt_raw.decode("utf-8"))
    refs = {k: v for k, v in bt.items() if isinstance(v, dict) and "byteOffset" in v}
    if refs and btb:                                   # numeric columns stored in the binary part
        binp, _ = get(b3dm_url, rng=(bstart + btj, bstart + btj + btb - 1))
        fmt = {"DOUBLE": ("d", 8), "FLOAT": ("f", 4), "UNSIGNED_INT": ("I", 4), "INT": ("i", 4),
               "UNSIGNED_SHORT": ("H", 2), "SHORT": ("h", 2), "UNSIGNED_BYTE": ("B", 1), "BYTE": ("b", 1)}
        for k, ref in refs.items():
            code, size = fmt.get(ref.get("componentType"), (None, None))
            if code is None or ref.get("type", "SCALAR") != "SCALAR":
                continue
            off = int(ref["byteOffset"])
            if off + size * n <= len(binp):
                bt[k] = list(struct.unpack_from("<%d%s" % (n, code), binp, off))
    return n, bt


def _kv(attrs: dict, key: str):
    for kv in (attrs or {}).get("uro:KeyValuePairAttribute", []) or []:
        if kv.get("uro:key") == key:
            return kv.get("uro:codeValue")
    return None


SENTINELS = {"不明", "Null", "NULL", "null", "", "-9999", "9999", "0001"}


def _s(x):
    """Text attribute, or None for PLATEAU's 'unknown' codes (不明, Null, -9999, 9999, 0001)."""
    if x is None:
        return None
    t = str(x).strip()
    return None if t in SENTINELS else t


def _num(x):
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def nearby(lat: float, lon: float, radius_m: float = 60.0, limit: int = 6) -> dict:
    rev = gsi.reverse(lat, lon)
    city = (rev.get("result") or {}).get("muniCd")
    if not city:
        raise SourceError("この地点の市区町村コードが分からない（国土地理院の逆ジオコーダ）")
    city = str(city).zfill(5)
    sets = city_datasets(city)
    if not sets:
        return {"city_code": city, "candidates": [], "source_id": SOURCE_ID,
                "note": "この市区町村の PLATEAU 建築物モデルは公開されていない（データカタログに無い）。"}
    ds = sets[0]
    tiles = _leaf_tiles(ds["url"], lat, lon)
    found = []
    for t in tiles:
        n, bt = _batch_table(t)
        xs, ys = bt.get("_x") or [], bt.get("_y") or []
        for i in range(n):
            try:
                x, y = float(xs[i]), float(ys[i])
            except (IndexError, TypeError, ValueError):
                continue
            box = [bt.get(k, [None] * n)[i] for k in ("_xmin", "_ymin", "_xmax", "_ymax")]
            inside = all(v is not None for v in box) and box[0] <= lon <= box[2] and box[1] <= lat <= box[3]
            d = _hav(lat, lon, y, x)
            if inside or d <= radius_m:
                found.append((0 if inside else 1, d, t, i, bt))
    found.sort(key=lambda r: (r[0], r[1]))
    cands, seen = [], set()
    for inside, d, t, i, bt in found:
        if len(cands) >= limit:
            break
        bid = (bt.get("uro:BuildingIDAttribute_uro:buildingID") or [None] * (i + 1))[i] if isinstance(bt.get("uro:BuildingIDAttribute_uro:buildingID"), list) else None
        gid = (bt.get("gml_id") or [None] * (i + 1))[i] if isinstance(bt.get("gml_id"), list) else None
        key = bid or gid or (t, i)
        if key in seen:                      # one building can appear in several tiles / parts: keep the nearest
            continue
        seen.add(key)
        def a(k):
            v = bt.get(k)
            return v[i] if isinstance(v, list) and i < len(v) else None
        attrs = a("attributes") or {}
        storeys = _num(a("bldg:storeysAboveGround"))
        below = _num(a("bldg:storeysBelowGround"))
        roof = _num(a("uro:BuildingDetailAttribute_uro:buildingRoofEdgeArea"))
        factor = _num(a("延べ面積換算係数"))
        gfa = None
        if roof and storeys and storeys > 0 and factor and factor > 0 and storeys < 900:
            gfa = roof * storeys * factor
        cands.append({
            "plateau_building_id": a("uro:BuildingIDAttribute_uro:buildingID"), "gml_id": a("gml_id"),
            "distance_m": round(d, 1), "contains_point": inside == 0,
            "address": _s(a("bldg:address")), "usage": _s(a("bldg:usage")), "class": _s(a("bldg:class")),
            "measured_height_m": _num(a("bldg:measuredHeight")),
            "storeys_above": int(storeys) if storeys and storeys < 900 else None,      # 9999 等は不明の符号
            "storeys_below": int(below) if below is not None and below < 900 else None,
            "roof_edge_area_m2": roof, "floor_area_factor": factor,
            "estimated_gross_floor_area_m2": round(gfa, 1) if gfa else None,
            "total_floor_area_m2": _num(a("uro:BuildingDetailAttribute_uro:totalFloorArea")),
            "structure_type": _s(a("uro:BuildingDetailAttribute_uro:buildingStructureType")),
            "year_of_construction": (lambda y: y if y and 1800 <= y <= 2200 else None)(_num(a("bldg:yearOfConstruction"))),  # "0001" etc. = unknown
            "fireproof": _s(a("uro:BuildingDetailAttribute_uro:fireproofStructureType")),
            "structure_code": _kv(attrs, "建物構造コード"),
            "survey_year": a("uro:BuildingDetailAttribute_uro:surveyYear"),
            "creation_date": a("core:creationDate"), "tile": t.rsplit("/", 1)[-1],
        })
    return {"city_code": city, "dataset": {k: ds.get(k) for k in ("id", "name", "year", "lod", "format", "url")},
            "candidates": cands, "source_id": SOURCE_ID, "n_tiles_read": len(tiles),
            "note": "PLATEAU の属性は自治体・年度で収録が違う。構造（RC・S・SRC・W）と延床面積は直接は記録されておらず、"
                    "構造は耐火区分・建物構造コードからの手掛かり、延床面積は屋根伏面積×地上階数×延べ面積換算係数の推定（仮定）である。"}


# PLATEAU usage → engine building-use hint (only a hint; the user confirms). Filled from the engine vocabulary.
# Only uses that exist in the engine vocabulary (synth.model.USES); others (宿泊施設 etc.) are not mapped.
USAGE_HINT = {"業務施設": "office", "事務所": "office", "共同住宅": "residential", "住宅": "residential",
              "商業施設": "retail", "文教厚生施設": "school", "医療施設": "hospital", "倉庫・運輸関係施設": "warehouse"}
