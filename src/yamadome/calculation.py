"""掘削土量計算: 授業指定の方法A・方法B と検算。

積算の考え方（授業の余幅スライド）:
  余幅 a = 作業のゆとり幅 + 法幅/2、 法幅 = 根切り深さ h × 0.3（1.5m ≤ h < 5.0m）
区画（根切り底の外形）には作業のゆとり 500 を含めてあるので、オープンカットの3面に
さらに 0.3h/2 を加えて「垂直に掘ったとみなした」範囲で 面積×深さ を計算する。
東面（親杭横矢板）は鉛直なので広げない。
加えて、法面を実際の斜面として数値積分した幾何学的体積を参考値として出し、
余幅法との差を示す（第3の検算）。
"""
from __future__ import annotations
from dataclasses import dataclass
from shapely.geometry import box
from shapely.ops import unary_union
from .geometry import MM2_PER_M2, final_depth_pieces


@dataclass
class Result:
    method_a_rows: list
    method_a: float
    method_b_rows: list
    method_b: float
    a0_area: float
    exact_volume: float | None
    yohaba: dict
    tol: float = 1e-6

    @property
    def agree(self) -> bool:
        return abs(self.method_a - self.method_b) <= self.tol * max(1.0, self.method_a)

    @property
    def total(self) -> float:
        return self.method_a

    # 互換
    @property
    def slope_volume(self):
        return None


def _clip_east(g, east_x):
    if east_x is None:
        return g
    minx, miny, maxx, maxy = g.bounds
    return g.intersection(box(minx - 1, miny - 1, east_x, maxy + 1))


def widen(poly, dist_mm, east_x):
    """開放面だけ dist_mm 外側へ広げる（東面は east_x で打切り）。"""
    if dist_mm <= 0:
        return poly
    return _clip_east(poly.buffer(dist_mm, join_style=2), east_x)


def scope(site):
    """余幅（法幅/2）を付ける面の範囲。
    perimeter: 根切り底全体の外形 P の外側だけに付ける（授業: 外周法面・余幅。内部の段差は鉛直）
    all_faces: 各区画の全周に付ける（v1, 441.225 m³ の算定方法。比較用）"""
    return site.raw["retaining"].get("yohaba_scope", "perimeter")


def extend(p, dist_mm, east_x, outline, mode):
    """区画 p を dist_mm 広げる。mode=perimeter では外形 outline の外側の部分だけ加える。"""
    w = widen(p, dist_mm, east_x)
    if mode == "all_faces":
        return w
    return unary_union([p, w.difference(outline)])


def yohaba_zones(site, zones):
    """各区画を 法幅/2 = 0.3h/2 だけ（外周側へ）広げた区画リスト。"""
    ret = site.raw["retaining"]
    n = ret.get("slope_ratio")
    if ret.get("include_slope_volume") != "yohaba" or not n:
        return zones, {}
    east = ret.get("soldier_pile_x_mm")
    outline = unary_union([z[3] for z in zones])
    mode = scope(site)
    out, info = [], {}
    for name, cls, d, p in zones:
        half = n * d * 1000 / 2
        info[round(d, 2)] = half
        out.append((name, cls, d, extend(p, half, east, outline, mode)))
    return out, info


def method_a(zones):
    """V = Σ(Ai × hi) — Ai は最終深さ別に分割した重複のない区画。"""
    rows = []
    for depth, g in final_depth_pieces(zones):
        a = g.area / MM2_PER_M2
        rows.append((depth, a, a * depth))
    return rows, sum(r[2] for r in rows)


def method_b(zones, base_depth):
    """V = A0 × 1.65 + Σ(Aj × Δhj)

    A0 = 全区画の和集合（基本掘削範囲）。方法Aとは独立に、
    「深さ d 以上の領域の和集合」面積 × 層厚 を積み上げて計算する。
    明細は授業表示（各増掘り区画 × 基本深さからの Δh）。
    """
    a0 = unary_union([z[3] for z in zones])
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
    s = sum(r[3] for r in rows)
    if abs(s - layered) > 1e-6 * max(1, layered):
        raise AssertionError(f"方法Bの明細合計 {s} と層別計算 {layered} が不一致")
    return rows, layered, a0_area


def exact_slope_volume(site, zones, n_slices=400):
    """法面を実斜面（勾配 1:n）として扱った幾何学的体積 [m³]（数値積分）。"""
    ret = site.raw["retaining"]
    n = ret.get("slope_ratio")
    if not n:
        return None
    east = ret.get("soldier_pile_x_mm")
    outline = unary_union([z[3] for z in zones])
    mode = scope(site)
    dmax = max(z[2] for z in zones)
    dz = dmax / n_slices
    vol = 0.0
    for i in range(n_slices):
        z = (i + 0.5) * dz                       # GL からの深さ [m]
        parts = [extend(p, n * (d - z) * 1000, east, outline, mode) for _, _, d, p in zones if d > z]
        if parts:
            vol += unary_union(parts).area / MM2_PER_M2 * dz
    return vol


def compute(site, zones):
    yz, info = yohaba_zones(site, zones)
    rows_a, va = method_a(yz)
    rows_b, vb, a0 = method_b(yz, site.base_depth)
    ex = exact_slope_volume(site, zones)
    return Result(rows_a, va, rows_b, vb, a0, ex, info)
