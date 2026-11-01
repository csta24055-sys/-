"""元の課題PDF 1ページ目の解答欄へ、根切図・Y3断面図・掘削土量を直接書き込む。

課題用紙には設計図（通り芯・基礎・梁）が 1/100 で印刷されているため、
別の図を貼り付けるのではなく、通り芯の実測座標（config の answer_sheet）で
mm → pt に変換して、根切り範囲・法面・山留め・寸法を同じ座標系に重ねて描く。
"""
from __future__ import annotations
import pymupdf
from shapely.ops import unary_union
from shapely.geometry import LineString
from .geometry import final_depth_pieces, section_profile
from .calculation import widen
from .pdf_tools import _font

RED = (0.80, 0.05, 0.05)
BROWN = (0.55, 0.35, 0.10)
FILL = {1.65: (0.55, 0.75, 0.95), 1.85: (0.35, 0.80, 0.35), 2.10: (0.98, 0.70, 0.25), 2.20: (0.95, 0.45, 0.35)}


class Mapper:
    def __init__(self, site):
        a = site.raw["answer_sheet"]
        g = a["plan_grid_pt"]
        gx, gy = site.grid_x, site.grid_y
        self.x0 = g["X1"]
        self.sx = (g["X4"] - g["X1"]) / (gx["X4"] - gx["X1"])        # pt per mm
        self.y2 = g["Y2"]
        self.sy = (g["Y2"] - g["Y3"]) / (gy["Y3"] - gy["Y2"])
        self.gl = a["section_GL_pt"]

    def plan(self, x, y):
        return pymupdf.Point(self.x0 + x * self.sx, self.y2 - y * self.sy)

    def sec(self, x, z_mm):
        """z_mm: GL からの高さ（上向き正）。"""
        return pymupdf.Point(self.x0 + x * self.sx, self.gl - z_mm * self.sy)


def _poly(shape, geom, conv):
    for p in getattr(geom, "geoms", [geom]):
        if p.is_empty or p.geom_type != "Polygon":
            continue
        pts = [conv(*c) for c in p.exterior.coords]
        shape.draw_polyline(pts)


def _text(page, fn, pt, s, size=5.0, color=RED, align="c", rotate=0):
    w = pymupdf.get_text_length(s, fontname="helv", fontsize=size) * 1.6 + 4
    if rotate:
        r = pymupdf.Rect(pt.x - size, pt.y - w / 2, pt.x + size, pt.y + w / 2)
    elif align == "c":
        r = pymupdf.Rect(pt.x - w / 2, pt.y - size, pt.x + w / 2, pt.y + size * 1.2)
    else:
        r = pymupdf.Rect(pt.x, pt.y - size, pt.x + w, pt.y + size * 1.2)
    page.insert_textbox(r, s, fontsize=size, fontname=fn, color=color,
                        align=pymupdf.TEXT_ALIGN_CENTER if align == "c" else 0, rotate=rotate)


def _dim(page, fn, a, b, label, off=(0, 0), size=4.2):
    """a, b: pymupdf.Point（同じ x または同じ y）。off だけずらした寸法線と数値。"""
    a2 = pymupdf.Point(a.x + off[0], a.y + off[1]); b2 = pymupdf.Point(b.x + off[0], b.y + off[1])
    sh = page.new_shape()
    sh.draw_line(a2, b2)
    for p, q in ((a, a2), (b, b2)):
        if off != (0, 0):
            sh.draw_line(p, q)
        sh.draw_line(pymupdf.Point(q.x - 1.2, q.y + 1.2), pymupdf.Point(q.x + 1.2, q.y - 1.2))
    sh.finish(color=RED, width=0.35)
    sh.commit()
    mid = pymupdf.Point((a2.x + b2.x) / 2, (a2.y + b2.y) / 2)
    if abs(a2.x - b2.x) < 0.01:          # 縦寸法
        _text(page, fn, pymupdf.Point(mid.x - 3.2, mid.y), label, size, rotate=90)
    else:
        _text(page, fn, pymupdf.Point(mid.x, mid.y - 3.0), label, size)


def draw_plan(page, fn, site, zones, m: Mapper):
    ret = site.raw["retaining"]
    n = ret["slope_ratio"]; east = ret["soldier_pile_x_mm"]
    bottom = unary_union([z[3] for z in zones])
    top = unary_union([widen(z[3], n * z[2] * 1000, east) for z in zones])

    sh = page.new_shape()                       # 法面
    _poly(sh, top.difference(bottom), m.plan)
    sh.finish(color=None, fill=(0.85, 0.70, 0.45), fill_opacity=0.45, width=0)
    sh.commit()
    sh = page.new_shape()
    _poly(sh, top, m.plan)
    sh.finish(color=BROWN, width=0.6, dashes="[3 1.5] 0")
    sh.commit()
    for depth, g in final_depth_pieces(zones):   # 根切り底（深さ別）
        sh = page.new_shape()
        _poly(sh, g, m.plan)
        sh.finish(color=None, fill=FILL[round(depth, 2)], fill_opacity=0.35, width=0)
        sh.commit()
    sh = page.new_shape()                       # 法尻（根切り底の外形）
    _poly(sh, bottom, m.plan)
    sh.finish(color=RED, width=1.1)
    sh.commit()
    # 法面のケバ（法肩→法尻の短線）
    sh = page.new_shape()
    b = bottom.boundary
    step = 600.0
    L = b.length; s = 0.0
    while s < L:
        p = b.interpolate(s)
        if p.x < east - 1:
            q = top.boundary.interpolate(top.boundary.project(p))
            if 50 < p.distance(q) < 2000:
                sh.draw_line(m.plan(q.x, q.y), m.plan(p.x, p.y))
        s += step
    sh.finish(color=BROWN, width=0.3)
    sh.commit()
    # 東面 親杭横矢板
    y0, y1 = bottom.bounds[1], bottom.bounds[3]
    sh = page.new_shape()
    sh.draw_line(m.plan(east, y0), m.plan(east, y1))
    sh.finish(color=RED, width=2.0)
    yy = y0
    while yy <= y1 + 1:
        c = m.plan(east, yy)
        sh.draw_rect(pymupdf.Rect(c.x - 2.2, c.y - 0.9, c.x + 2.2, c.y + 0.9))
        yy += 1000
    sh.finish(color=RED, fill=RED, width=0.3)
    sh.commit()

    # 深さラベル
    for name, cls, d, p in zones[1:]:
        c = p.representative_point() if "F5" not in name else p.centroid
        _text(page, fn, m.plan(c.x, c.y - 350), f"GL-{d*1000:,.0f}", 4.6)
    _text(page, fn, m.plan(8625, 6900), "FS1 根切り底 GL-1,650", 6.0)
    _text(page, fn, m.plan(8625, 6300), "床付け（捨てコン50・砕石50 下端）", 4.6)
    bx0, by0, bx1, by1 = zones[0][3].bounds
    _text(page, fn, m.plan(-1700, 5400), f"西面 オープンカット 法1:{n}", 4.8, rotate=90)
    _text(page, fn, m.plan(east + 650, 5400), "東面 親杭横矢板（H形鋼）", 4.8, rotate=90)
    _text(page, fn, m.plan(8625, by1 + 1800), f"北面 オープンカット 法1:{n}", 4.8)
    _text(page, fn, m.plan(8625, by0 - 950), f"南面 オープンカット 法1:{n}", 4.8)

    # 主要寸法（根切り底＝法尻）
    _dim(page, fn, m.plan(bx0, by1), m.plan(0, by1), f"{-bx0:,.0f}", off=(0, -6))
    _dim(page, fn, m.plan(17250, by1), m.plan(bx1, by1), f"{bx1-17250:,.0f}", off=(0, -6))
    _dim(page, fn, m.plan(bx1, 0), m.plan(bx1, by0), f"{-by0:,.0f}", off=(8, 0))
    _dim(page, fn, m.plan(bx1, 10800), m.plan(bx1, by1), f"{by1-10800:,.0f}", off=(8, 0))
    _dim(page, fn, m.plan(-590, 0), m.plan(-590, -1610), "1,610", off=(-9, 0))
    _dim(page, fn, m.plan(-590, 10800), m.plan(-590, 12300), "1,500", off=(-9, 0))
    _dim(page, fn, m.plan(4050, 12110), m.plan(7450, 12110), "3,400", off=(0, -5))
    _dim(page, fn, m.plan(5750, 10800), m.plan(5750, 12110), "1,310", off=(0, 0))
    _dim(page, fn, m.plan(9800, -1310), m.plan(13200, -1310), "3,400", off=(0, 5))
    sw = n * 1.65 * 1000
    _dim(page, fn, m.plan(bx0 - sw, 5000), m.plan(bx0, 5000), f"{sw:,.0f}", off=(0, 0), size=3.8)
    return top


def draw_section(page, fn, site, zones, m: Mapper):
    ret = site.raw["retaining"]
    n = ret["slope_ratio"]; east = ret["soldier_pile_x_mm"]
    y = site.grid_y["Y3"]
    segs = section_profile(zones, y)
    x0, x1 = segs[0][0], segs[-1][1]
    sw = n * segs[0][2] * 1000
    prof = [(x0 - sw, 0), (x0, -segs[0][2] * 1000)]
    for a, b, d in segs:
        prof += [(a, -d * 1000), (b, -d * 1000)]
    prof += [(x1, 0)]
    sh = page.new_shape()
    sh.draw_polyline([m.sec(*p) for p in prof] + [m.sec(x0 - sw, 0)])
    sh.finish(color=None, fill=(0.85, 0.70, 0.45), fill_opacity=0.18, width=0)
    sh.commit()
    sh = page.new_shape()
    sh.draw_polyline([m.sec(*p) for p in prof])
    sh.finish(color=RED, width=1.1)
    sh.commit()
    # 親杭
    dmax = max(s[2] for s in segs) * 1000
    sh = page.new_shape()
    sh.draw_rect(pymupdf.Rect(m.sec(east, 200), m.sec(east + 200, -dmax - 1300)))
    sh.finish(color=RED, fill=(1, 0.85, 0.85), width=0.5)
    sh.commit()
    _text(page, fn, m.sec(east + 1500, -600), "親杭横矢板", 4.6)
    _text(page, fn, m.sec(east + 1500, -1000), "（H形鋼）", 4.4)
    _text(page, fn, m.sec(east + 1500, -1450), "余幅100", 4.4)
    _text(page, fn, m.sec(x0 - sw - 200, -1150), f"法1:{n}", 4.6)
    # 深さ寸法・床付けレベル
    seen = set()
    for a, b, d in segs:
        if b - a < 300:
            continue
        lab = f"{d*1000:,.0f}"
        if (d, round(a)) in seen:
            continue
        seen.add((d, round(a)))
        xm = a + 260 if d != 1.65 else (a + b) / 2
        if d == 1.65 and (a, b, d) != max((s for s in segs if s[2] == 1.65), key=lambda s: s[1] - s[0]):
            continue
        _dim(page, fn, m.sec(xm, 0), m.sec(xm, -d * 1000), lab, size=3.8)
    for a, b, d in segs:
        if b - a > 1500:
            _text(page, fn, m.sec((a + b) / 2 + (600 if d == 1.65 else 0), -d * 1000 - 260), f"床付 GL-{d*1000:,.0f}", 3.8)
    # 区間寸法（根切り底）
    edges = sorted({round(v) for a, b, _ in segs for v in (a, b)} | {round(x0 - sw)})
    for a, b in zip(edges, edges[1:]):
        if b - a < 300:
            continue
        _dim(page, fn, m.sec(a, -2950), m.sec(b, -2950), f"{b-a:,.0f}", size=3.4)
    return segs


def legend(page, fn, m: Mapper, origin=(560.0, 700.0)):
    x, y = origin
    items = [((0.55, 0.75, 0.95), "根切り底 GL-1,650（FS1）"), ((0.35, 0.80, 0.35), "根切り底 GL-1,850（F3・F4・F5）"),
             ((0.98, 0.70, 0.25), "根切り底 GL-2,100（F4A）"), ((0.95, 0.45, 0.35), "根切り底 GL-2,200（F3A）"),
             ((0.85, 0.70, 0.45), "法面（法幅 0.3h）、破線＝法肩")]
    for i, (col, lab) in enumerate(items):
        yy = y + i * 11
        sh = page.new_shape()
        sh.draw_rect(pymupdf.Rect(x, yy, x + 14, yy + 7))
        sh.finish(color=RED, fill=col, fill_opacity=0.5, width=0.4)
        sh.commit()
        page.insert_text(pymupdf.Point(x + 18, yy + 6.5), lab, fontsize=5.5, fontname=fn, color=RED)


def write(src_pdf, out_pdf, site, zones, res):
    doc = pymupdf.open(src_pdf)
    page = doc[site.raw["answer_sheet"]["page_index"]]
    fn = _font(page)
    m = Mapper(site)
    top = draw_plan(page, fn, site, zones, m)
    draw_section(page, fn, site, zones, m)
    legend(page, fn, m)
    r = pymupdf.Rect(*site.raw["answer_sheet"]["volume_text_at"])
    page.insert_textbox(r, f"{res.total:,.2f}", fontsize=12, fontname=fn, color=RED, align=pymupdf.TEXT_ALIGN_CENTER)
    page.insert_textbox(pymupdf.Rect(60, 1098, 372, 1124),
                        f"方法A ΣAi·hi = {res.method_a:.3f}m3 ／ 方法B A0×1.65+ΣAj·Δhj = {res.a0_area:.3f}×1.65+… = {res.method_b:.3f}m3"
                        f"\n余幅 = 作業ゆとり0.5m + 法幅0.3h/2（東面は親杭・法なし）",
                        fontsize=5.2, fontname=fn, color=RED)
    doc.save(out_pdf, garbage=3, deflate=True)
    doc.close()
    tb = top.bounds
    p0, p1 = m.plan(tb[0] - 2500, tb[3] + 2500), m.plan(tb[2] + 3000, tb[1] - 2500)
    plan_box = [min(p0.x, p1.x), min(p0.y, p1.y), max(p0.x, p1.x), max(p0.y, p1.y)]
    s0, s1 = m.sec(tb[0] - 1500, 400), m.sec(tb[2] + 3000, -3300)
    sec_box = [s0.x, s0.y, s1.x, s1.y]
    return [plan_box, sec_box, list(r), [55, 1093, 377, 1128], [555, 695, 760, 760]]
