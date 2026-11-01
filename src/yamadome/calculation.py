"""掘削土量計算: 授業指定の方法A・方法B と検算。"""
from __future__ import annotations
from dataclasses import dataclass
from shapely.ops import unary_union
from .geometry import MM2_PER_M2, final_depth_pieces


@dataclass
class Result:
    method_a_rows: list      # [(depth, area_m2, volume_m3)]
    method_a: float
    method_b_rows: list      # [(label, area_m2, dh, volume_m3)]
    method_b: float
    a0_area: float
    slope_volume: float | None
    tol: float = 1e-6

    @property
    def agree(self) -> bool:
        return abs(self.method_a - self.method_b) <= self.tol * max(1.0, self.method_a)

    @property
    def total(self) -> float:
        return self.method_a + (self.slope_volume or 0.0)


def method_a(zones):
    """V = Σ(Ai × hi)  — Ai は最終深さ別に分割した重複のない区画。"""
    rows = []
    for depth, g in final_depth_pieces(zones):
        a = g.area / MM2_PER_M2
        rows.append((depth, a, a * depth))
    return rows, sum(r[2] for r in rows)


def method_b(zones, base_depth):
    """V = A0 × 1.65 + Σ(Aj × Δhj)

    方法Aとは独立な計算経路にするため、区画を最終深さで分割せず
    「深さ d 以上となる領域の和集合」の面積 × 層厚 を積み上げる（層別加算）。
    Σ の各項を授業の Δh（基本深さからの増掘り深さ）表示に直した明細も返す。
    """
    a0 = zones[0][3]
    a0_area = a0.area / MM2_PER_M2
    deeper = sorted({z[2] for z in zones if z[2] > base_depth})
    layered = a0_area * base_depth
    prev = base_depth
    for d in deeper:
        u = unary_union([z[3] for z in zones if z[2] >= d]).area / MM2_PER_M2
        layered += u * (d - prev)
        prev = d
    rows = [("A0 基本掘削", a0_area, base_depth, a0_area * base_depth)]
    for depth, g in final_depth_pieces(zones):
        if depth > base_depth:
            a = g.area / MM2_PER_M2
            dh = round(depth - base_depth, 6)
            rows.append((f"増掘り {depth:.2f}m 区画", a, dh, a * dh))
    detail_sum = sum(r[3] for r in rows)
    if abs(detail_sum - layered) > 1e-6 * max(1, layered):
        raise AssertionError(f"方法Bの明細合計 {detail_sum} と層別計算 {layered} が不一致")
    return rows, layered, a0_area


def slope_volume(a0_poly, depth_m, ratio_n, open_sides, east_x_mm=None):
    """オープンカット法面部分の体積（擬柱公式）。

    底面 = A0、天端 = 開放側の辺のみ n·H だけ外側へ広げた形。
    東面（親杭横矢板）は鉛直なので広げない。矩形に近い外形を前提とする。
    """
    from shapely.geometry import box
    H = depth_m * 1000.0

    def widened(h):
        g = a0_poly.buffer(ratio_n * h, join_style=2)
        minx, miny, maxx, maxy = a0_poly.bounds
        clip = [g.bounds[0], g.bounds[1], g.bounds[2], g.bounds[3]]
        if "east" not in open_sides:
            clip[2] = maxx if east_x_mm is None else east_x_mm
        if "west" not in open_sides:
            clip[0] = minx
        if "south" not in open_sides:
            clip[1] = miny
        if "north" not in open_sides:
            clip[3] = maxy
        return g.intersection(box(*clip))

    a1 = a0_poly.area
    am = widened(H / 2).area
    a2 = widened(H).area
    return H / 6 * (a1 + 4 * am + a2) / 1e9 - a1 * H / 1e9


def compute(site, zones):
    rows_a, va = method_a(zones)
    rows_b, vb, a0 = method_b(zones, site.base_depth)
    ret = site.raw["retaining"]
    sv = None
    if ret.get("include_slope_volume") and ret.get("slope_ratio") is not None:
        sides = [s for s in ("west", "south", "north", "east") if ret[s] == "open_cut"]
        sv = slope_volume(zones[0][3], site.raw["retaining"].get("slope_depth_m", site.base_depth),
                          float(ret["slope_ratio"]), sides, ret.get("soldier_pile_x_mm"))
    return Result(rows_a, va, rows_b, vb, a0, sv)
