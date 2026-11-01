"""根切り領域の幾何処理（Shapely）。

各水平位置での「最終掘削深さ」を求め、重複のない区画 (polygon, depth) に分解する。
深さの異なる区画が重なる場合は深い方を採用し、単純加算しない。
"""
from __future__ import annotations
from shapely.geometry import Polygon, LineString
from shapely.ops import unary_union

MM2_PER_M2 = 1_000_000.0


def poly(coords) -> Polygon:
    p = Polygon(coords)
    if not p.is_valid or p.area <= 0:
        raise ValueError(f"不正な多角形: {coords}")
    return p


def zone_polygons(site):
    """[(name, class, depth_m, Polygon)] — base_area を先頭に含む。"""
    ex = site.raw["excavation"]
    out = [("A0 基本掘削", "base", site.base_depth, poly(ex["base_area"]["polygon"]))]
    for z in ex["zones"]:
        out.append((z["name"], z["class"], site.depth(z["class"]), poly(z["polygon"])))
    return out


def check_containment(zones, tol_mm2=1.0):
    """各増掘り区画が基本掘削範囲（FS1）と接続しているか（孤立した区画は入力誤りの疑い）。
    基礎掘削は外周で基本範囲から張り出してよい（A0 は全区画の和集合として扱う）。"""
    base = zones[0][3]
    return [(name, 0.0) for name, _, _, p in zones[1:] if p.intersection(base).area <= tol_mm2]


def final_depth_pieces(zones):
    """重複のない (depth_m, geometry) の一覧。深い順に塗り重ねて差分を取る。"""
    pieces = []
    taken = None
    for depth in sorted({z[2] for z in zones}, reverse=True):
        g = unary_union([z[3] for z in zones if z[2] == depth])
        if taken is not None:
            g = g.difference(taken)
        if not g.is_empty:
            pieces.append((depth, g))
        taken = g if taken is None else unary_union([taken, g])
    return pieces


def section_profile(zones, y_mm):
    """y = y_mm の切断線上での [(x0, x1, depth_m)]（深さ別区間）。"""
    pieces = final_depth_pieces(zones)
    xs = [x for _, g in pieces for x in (g.bounds[0], g.bounds[2])]
    line = LineString([(min(xs) - 1, y_mm), (max(xs) + 1, y_mm)])
    segs = []
    for depth, g in pieces:
        inter = g.intersection(line)
        for s in getattr(inter, "geoms", [inter]):
            if s.is_empty or s.length <= 0:
                continue
            x0, _, x1, _ = s.bounds
            segs.append((x0, x1, depth))
    return sorted(segs)
