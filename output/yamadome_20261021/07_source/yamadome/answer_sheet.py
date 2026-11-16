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
from .pdf_tools import _font, JP_FONT

_JP = pymupdf.Font(fontfile=JP_FONT)

RED = (0.75, 0.05, 0.05)          # 答案の文字・寸法
BROWN = (0.55, 0.27, 0.05)        # 法肩・法尻・稜線（授業図の茶色の色鉛筆）
ORANGE = (0.90, 0.48, 0.08)       # 断面の根切り線（授業 X2断面の橙色の帯）
# 授業の着色根切図: FS1=黄、基礎掘削 GL-1850=緑、F4A=橙。F3A は授業写真に写っていないため橙を濃くして区別（未確認）
# 線の太さ [pt]。完成答案の値が既定値。手書き見本ではペン幅（0.5/0.3/0.2mm）に置き換える（handwriting.py）
STYLE = {"dim": 0.35, "labelbox": 0.45, "leader": 0.4, "border": 0.45, "top": 0.85, "bottom": 1.2, "ridge": 0.55,
         "pile": 1.8, "hmark": 0.6, "sec_outline": 0.5, "sec_pile": 0.5, "plan_fill_opacity": 0.40, "sec_fill_opacity": 0.55}
FILL = {1.65: (1.00, 0.93, 0.25), 1.85: (0.30, 0.78, 0.25), 2.10: (0.98, 0.62, 0.15), 2.20: (0.90, 0.40, 0.10)}


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
    w = _JP.text_length(s, fontsize=size) * 1.15 + 6
    if rotate:
        r = pymupdf.Rect(pt.x - size, pt.y - w / 2, pt.x + size, pt.y + w / 2)
    elif align == "c":
        r = pymupdf.Rect(pt.x - w / 2, pt.y - size, pt.x + w / 2, pt.y + size * 1.6)
    else:
        r = pymupdf.Rect(pt.x, pt.y - size, pt.x + w, pt.y + size * 1.6)
    rc = page.insert_textbox(r, s, fontsize=size, fontname=fn, color=color,
                             align=pymupdf.TEXT_ALIGN_CENTER if align == "c" else 0, rotate=rotate)
    if rc < 0:
        raise RuntimeError(f"文字が枠に収まらず描画されない: {s!r}")


def _dim(page, fn, a, b, label, off=(0, 0), size=5.6):
    """a, b: pymupdf.Point（同じ x または同じ y）。off だけずらした寸法線と数値。"""
    a2 = pymupdf.Point(a.x + off[0], a.y + off[1]); b2 = pymupdf.Point(b.x + off[0], b.y + off[1])
    sh = page.new_shape()
    sh.draw_line(a2, b2)
    for p, q in ((a, a2), (b, b2)):
        if off != (0, 0):
            sh.draw_line(p, q)
        sh.draw_line(pymupdf.Point(q.x - 1.2, q.y + 1.2), pymupdf.Point(q.x + 1.2, q.y - 1.2))
    sh.finish(color=RED, width=STYLE['dim'])
    sh.commit()
    mid = pymupdf.Point((a2.x + b2.x) / 2, (a2.y + b2.y) / 2)
    if abs(a2.x - b2.x) < 0.01:          # 縦寸法
        _text(page, fn, pymupdf.Point(mid.x - size * 0.75, mid.y), label, size, rotate=90)
    else:
        _text(page, fn, pymupdf.Point(mid.x, mid.y - size * 0.7), label, size)


def _boxlabel(page, fn, pt, text, size=5.6):
    """授業図と同じ枠付きの深さ表示（例: GL-1850）。"""
    w = _JP.text_length(text, fontsize=size) + 5
    r = pymupdf.Rect(pt.x - w / 2, pt.y - size * 0.95, pt.x + w / 2, pt.y + size * 0.75)
    sh = page.new_shape()
    sh.draw_rect(r)
    sh.finish(color=RED, fill=(1, 1, 1), fill_opacity=0.85, width=STYLE['labelbox'])
    sh.commit()
    page.insert_text(pymupdf.Point(r.x0 + 2.5, r.y1 - size * 0.3), text, fontsize=size, fontname=fn, color=RED)
    return r


def _leader(page, a, b):
    sh = page.new_shape()
    sh.draw_line(a, b)
    sh.draw_circle(a, 0.8)
    sh.finish(color=RED, fill=RED, width=STYLE['leader'])
    sh.commit()


def _chain(page, fn, pts, fixed, axis, off, size=5.2):
    """寸法の連続（pts は可変軸の座標列 mm、fixed は固定軸 mm）。axis='x' で水平、'y' で鉛直。"""
    for u, v in zip(pts, pts[1:]):
        if axis == "x":
            a, b = (u, fixed), (v, fixed)
        else:
            a, b = (fixed, u), (fixed, v)
        yield a, b, f"{abs(v-u):,.0f}"


def ridge_lines(bottom, top, east, max_mm=1000.0):
    """法尻の角から法肩の角へ引く稜線（出隅・入隅とも）。東面（親杭側）は除く。"""
    out = []
    tv = [c for g in getattr(top, "geoms", [top]) for c in list(g.exterior.coords)[:-1]]
    for g in getattr(bottom, "geoms", [bottom]):
        for vx, vy in list(g.exterior.coords)[:-1]:
            if vx >= east - 1:
                continue
            best = None
            for tx, ty in tv:
                dx, dy = tx - vx, ty - vy
                if abs(dx) < 1 or abs(dy) < 1 or tx >= east - 1:
                    continue
                r = abs(dx) / abs(dy)
                d = (dx * dx + dy * dy) ** 0.5
                if 0.6 < r < 1.7 and d < max_mm and (best is None or d < best[0]):
                    best = (d, (tx, ty))
            if best:
                out.append(((vx, vy), best[1]))
    return out


def draw_plan(page, fn, site, zones, m: Mapper):
    ret = site.raw["retaining"]
    n = ret["slope_ratio"]; east = ret["soldier_pile_x_mm"]
    bottom = unary_union([z[3] for z in zones])
    top = unary_union([widen(z[3], n * z[2] * 1000, east) for z in zones])

    for depth, g in final_depth_pieces(zones):   # 根切り底（深さ別、授業図の配色）
        sh = page.new_shape()
        _poly(sh, g, m.plan)
        sh.finish(color=None, fill=FILL[round(depth, 2)], fill_opacity=STYLE['plan_fill_opacity'], width=0)
        sh.commit()
        sh = page.new_shape()                   # 深さの境界（内部の段差は鉛直＝1本線）
        _poly(sh, g, m.plan)
        sh.finish(color=BROWN, width=STYLE['border'])
        sh.commit()
    sh = page.new_shape()                       # 法肩
    _poly(sh, top, m.plan)
    sh.finish(color=BROWN, width=STYLE['top'])
    sh.commit()
    sh = page.new_shape()                       # 法尻（根切り底の外形）
    _poly(sh, bottom, m.plan)
    sh.finish(color=BROWN, width=STYLE['bottom'])
    sh.commit()
    sh = page.new_shape()                       # 稜線（角部の取り合い）
    for a_, b_ in ridge_lines(bottom, top, east):
        sh.draw_line(m.plan(*a_), m.plan(*b_))
    sh.finish(color=BROWN, width=STYLE['ridge'])
    sh.commit()
    # 東面 親杭横矢板（親杭の位置は概略表示）
    y0, y1 = bottom.bounds[1], bottom.bounds[3]
    sh = page.new_shape()
    sh.draw_line(m.plan(east, y0), m.plan(east, y1))
    sh.finish(color=RED, width=STYLE['pile'])
    yy = y0
    while yy <= y1 + 1:
        c = m.plan(east, yy)
        sh.draw_line(pymupdf.Point(c.x - 2.0, c.y - 1.0), pymupdf.Point(c.x - 2.0, c.y + 1.0))
        sh.draw_line(pymupdf.Point(c.x + 2.0, c.y - 1.0), pymupdf.Point(c.x + 2.0, c.y + 1.0))
        sh.draw_line(pymupdf.Point(c.x - 2.0, c.y), pymupdf.Point(c.x + 2.0, c.y))
        yy += 1000
    sh.finish(color=RED, width=STYLE['hmark'])
    sh.commit()

    # 深さ表示（授業図の枠付き表示 + 引出線）
    for name, cls, d, p in zones[1:]:
        bx = p.bounds
        if "F5" in name:
            anchor, at = (15600, 9300), (12400, 6300)
        elif bx[3] > 10800 + 500:
            anchor = ((bx[0] + bx[2]) / 2 + 900, bx[1] + 150); at = (anchor[0] + 300, bx[1] - 1100)
        else:
            anchor = ((bx[0] + bx[2]) / 2 + 900, bx[3] - 150)
            if anchor[0] > 15000:
                anchor = ((bx[0] + bx[2]) / 2 - 200, bx[3] - 150); at = (anchor[0] - 1500, bx[3] + 1100)
            else:
                at = (anchor[0] + 300, bx[3] + 1100)
        r = _boxlabel(page, fn, m.plan(*at), f"GL-{d*1000:.0f}")
        tip = m.plan(*anchor)
        _leader(page, tip, pymupdf.Point((r.x0 + r.x1) / 2, r.y0 if tip.y < r.y0 else r.y1))
    r = _boxlabel(page, fn, m.plan(8625, 6900), "GL-1650", 6.2)
    _leader(page, m.plan(7600, 7900), pymupdf.Point(r.x0, (r.y0 + r.y1) / 2))
    _text(page, fn, m.plan(8625, 6250), "FS1 根切り底（床付け）", 5.6)
    bx0, by0, bx1, by1 = zones[0][3].bounds
    _text(page, fn, m.plan(-3300, 7800), f"西面 オープンカット 法1:{n}", 5.6, rotate=90)
    _text(page, fn, m.plan(east + 650, 8300), "東面 親杭横矢板（山留H鋼）", 5.6, rotate=90)
    _text(page, fn, m.plan(8625, by1 + 1800), f"北面 オープンカット 法1:{n}", 5.6)
    _text(page, fn, m.plan(14520, -2150), f"南面 オープンカット 法1:{n}", 5.6)

    # 寸法（授業図の記入方法: 法幅｜作業ゆとり、基礎掘削の振分け）
    W, S165 = 500, n * 1.65 * 1000
    bf = site.raw["beams_outer_face_mm"]
    for (a_, b_, lab) in _chain(page, fn, [bf["west"] - W - S165, bf["west"] - W, bf["west"]], 3400, "x", 0):
        _dim(page, fn, m.plan(*a_), m.plan(*b_), lab, size=4.8)
    for (a_, b_, lab) in _chain(page, fn, [bf["south"] - W - S165, bf["south"] - W, bf["south"]], 9100, "y", 0):
        _dim(page, fn, m.plan(*a_), m.plan(*b_), lab, size=4.8)
    for (a_, b_, lab) in _chain(page, fn, [bf["north"], bf["north"] + W, bf["north"] + W + S165], 3550, "y", 0):
        _dim(page, fn, m.plan(*a_), m.plan(*b_), lab, size=4.8)
    for (a_, b_, lab) in _chain(page, fn, [-1610, 0, 1390], -590, "y", 0):
        _dim(page, fn, m.plan(*a_), m.plan(*b_), lab, off=(-26, 0))
    for (a_, b_, lab) in _chain(page, fn, [9300, 10800, 12300], -590, "y", 0):
        _dim(page, fn, m.plan(*a_), m.plan(*b_), lab, off=(-26, 0))
    for (a_, b_, lab) in _chain(page, fn, [9710, 10800, 12110, 12110 + n * 2.10 * 1000], 4050, "y", 0):
        _dim(page, fn, m.plan(*a_), m.plan(*b_), lab, off=(-6, 0), size=4.8)
    for (a_, b_, lab) in _chain(page, fn, [9800, 11500, 13200], -1310, "x", 0):
        _dim(page, fn, m.plan(*a_), m.plan(*b_), lab, off=(0, 9))
    for (a_, b_, lab) in _chain(page, fn, [4050, 5750, 7450], 12110, "x", 0):
        _dim(page, fn, m.plan(*a_), m.plan(*b_), lab, off=(0, -5))
    _dim(page, fn, m.plan(13200, 8700), m.plan(14440, 8700), "1,240", size=5.2)
    _dim(page, fn, m.plan(17250, by1), m.plan(bx1, by1), f"{bx1-17250:,.0f}", off=(0, -14), size=4.8)
    _text(page, fn, m.plan(bx1 + 200, by1 + 900), "余幅100", 4.8, align="l")
    return top


SLOPE_TAN = (0.80, 0.58, 0.28)   # 授業 X2断面の法面・GL際の茶（黄土）色
BAND_MM = 150.0                   # 着色帯の幅（実寸 mm、1/100 で約1.5mm）


def band_pieces(prof, segs, lip_mm=1000.0, w=BAND_MM):
    """断面の根切り線 prof（西の法肩→法尻→…→東の壁上端）の土側に沿う着色帯を、
    区間ごとの色付き多角形 [(color, Polygon)] として返す（描画専用。形状・数値は変更しない）。

    授業 X2断面の塗り方: 法面と法肩外の GL 際＝茶、根切り底＝その深さの平面図と同じ色
    （FS1 黄・GL-1850 緑・F4A 橙・F3A 濃橙）、段差の立上りは深い側の色、掘削部の内側は塗らない。
    """
    from shapely.geometry import LineString, Polygon
    pts = [(prof[0][0] - lip_mm, 0.0)] + list(prof)          # 西側 GL 際の帯（オープンカット）
    out = []
    for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
        L = ((xb - xa) ** 2 + (yb - ya) ** 2) ** 0.5
        if L < 1e-6:
            continue
        nx, ny = (yb - ya) / L, -(xb - xa) / L                # 進行方向の右手＝土側
        # 角部の隙間が出ないよう、帯を進行方向の前後へ w だけ延ばす
        ex, ey = (xb - xa) / L * w, (yb - ya) / L * w
        q = Polygon([(xa - ex, ya - ey), (xb + ex, yb + ey), (xb + ex + nx * w, yb + ey + ny * w), (xa - ex + nx * w, ya - ey + ny * w)])
        if abs(ya - yb) < 1e-6 and ya < -1:                    # 根切り底
            d = round(-ya / 1000, 2)
            col, order = FILL.get(d, SLOPE_TAN), 2
        elif abs(xa - xb) < 1e-6 and min(ya, yb) < -1 and max(ya, yb) < -1:   # 段差の立上り
            d = round(-min(ya, yb) / 1000, 2)
            col, order = FILL.get(d, SLOPE_TAN), 1
        else:                                                  # 法面・GL際・東側の壁
            col, order = SLOPE_TAN, 0
        out.append((order, col, q))
    out.sort(key=lambda t: t[0])                               # 底の色を最後に重ねる（角は底の色）
    return [(col, q) for _, col, q in out]


def section_band(page, prof, segs, m, lip_mm=1000.0):
    from shapely.geometry import Polygon
    # 掘削部の内側には帯をはみ出させない（帯は土側だけ）
    cut = Polygon(list(prof) + [prof[0]])
    for col, q in band_pieces(prof, segs, lip_mm):
        g = q.difference(cut) if cut.is_valid else q
        sh = page.new_shape()
        _poly(sh, g, m.sec)
        sh.finish(color=None, fill=col, fill_opacity=STYLE['sec_fill_opacity'], width=0)   # 下の印刷文字（FG2A 等）が読める濃さ
        sh.commit()


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
    section_band(page, prof, segs, m, lip_mm=1000.0)   # 授業 X2断面と同じ着色（形状は prof のまま）
    sh = page.new_shape()                      # 根切り線（掘削輪郭、v2 と同じ線）
    sh.draw_polyline([m.sec(*p) for p in prof])
    sh.finish(color=BROWN, width=STYLE['sec_outline'])
    sh.commit()
    # 親杭
    dmax = max(s[2] for s in segs) * 1000
    sh = page.new_shape()
    sh.draw_rect(pymupdf.Rect(m.sec(east, 200), m.sec(east + 200, -dmax - 1300)))
    sh.finish(color=RED, fill=RED, fill_opacity=0.15, width=STYLE['sec_pile'])
    sh.commit()
    _text(page, fn, m.sec(east + 1600, -600), "親杭横矢板", 5.0)
    _text(page, fn, m.sec(east + 1600, -1050), "（山留H鋼）", 5.0)
    _dim(page, fn, m.sec(17340, -1500), m.sec(east, -1500), "100", size=4.4)
    _text(page, fn, m.sec(east + 1600, -1500), "余幅100", 5.0)
    _text(page, fn, m.sec(x0 - sw - 1300, -350), f"法1:{n}", 5.6)
    # 深さ寸法・床付けレベル
    seen = set()
    for a, b, d in segs:
        if b - a < 300:
            continue
        lab = f"{d*1000:,.0f}"
        if (d, round(a)) in seen:
            continue
        seen.add((d, round(a)))
        xm = (b - 260 if d != 1.85 else a + 330) if d != 1.65 else (a + b) / 2
        if d == 1.65 and (a, b, d) != max((s for s in segs if s[2] == 1.65), key=lambda s: s[1] - s[0]):
            continue
        _dim(page, fn, m.sec(xm, 0), m.sec(xm, -d * 1000), lab, size=5.0)
    for a, b, d in segs:
        if b - a > 1500:
            z = -d * 1000 + 330 if d == 1.65 else -d * 1000 - 300
            _text(page, fn, m.sec((a + b) / 2, z), f"床付 GL-{d*1000:,.0f}", 4.8)
    # 区間寸法（根切り底）
    edges = sorted({round(v) for a, b, _ in segs for v in (a, b)} | {round(x0 - sw)})
    for a, b in zip(edges, edges[1:]):
        if b - a < 300:
            continue
        _dim(page, fn, m.sec(a, -2950), m.sec(b, -2950), f"{b-a:,.0f}", size=4.6)
    return segs


def legend(page, fn, m: Mapper, origin=(560.0, 694.0)):
    x, y = origin
    items = [(FILL[1.65], "根切り底 GL-1650（FS1）"), (FILL[1.85], "根切り底 GL-1850（F3・F4・F5）"),
             (FILL[2.10], "根切り底 GL-2100（F4A）"), (FILL[2.20], "根切り底 GL-2200（F3A）"),
             (None, "法面（白抜き）：太線＝法尻、細線＝法肩、斜線＝稜線")]
    for i, (col, lab) in enumerate(items):
        yy = y + i * 11
        sh = page.new_shape()
        if col is None:
            sh.draw_line(pymupdf.Point(x, yy + 7), pymupdf.Point(x + 14, yy + 7))
            sh.finish(color=BROWN, width=STYLE['bottom'])
            sh.draw_line(pymupdf.Point(x, yy + 1), pymupdf.Point(x + 14, yy + 1))
            sh.finish(color=BROWN, width=STYLE['top'])
            sh.draw_line(pymupdf.Point(x, yy + 7), pymupdf.Point(x + 6, yy + 1))
            sh.finish(color=BROWN, width=STYLE['ridge'])
        else:
            sh.draw_rect(pymupdf.Rect(x, yy, x + 14, yy + 7))
            sh.finish(color=BROWN, fill=col, fill_opacity=0.5, width=0.4)
        sh.commit()
        page.insert_text(pymupdf.Point(x + 18, yy + 6.5), lab, fontsize=6.0, fontname=fn, color=RED)


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
    formula_note(page, fn, res)
    doc.save(out_pdf, garbage=3, deflate=True)
    doc.close()
    return _boxes(site, m, top, r)


def formula_note(page, fn, res):
    page.insert_textbox(pymupdf.Rect(60, 1098, 372, 1124),
                        f"方法A ΣAi·hi = {res.method_a:.3f}m3 ／ 方法B A0×1.65+ΣAj·Δhj = {res.a0_area:.3f}×1.65+… = {res.method_b:.3f}m3"
                        f"\n余幅 = 作業ゆとり0.5m + 法幅0.3h/2（外周のみ。内部の段差は鉛直。東面は親杭・余幅0.1m・法なし）",
                        fontsize=5.2, fontname=fn, color=RED)


def _boxes(site, m, top, r):
    tb = top.bounds
    p0, p1 = m.plan(tb[0] - 2500, tb[3] + 2500), m.plan(tb[2] + 3000, tb[1] - 2500)
    plan_box = [min(p0.x, p1.x), min(p0.y, p1.y), max(p0.x, p1.x), max(p0.y, p1.y)]
    s0, s1 = m.sec(tb[0] - 1500, 400), m.sec(tb[2] + 3000, -3300)
    sec_box = [s0.x, s0.y, s1.x, s1.y]
    return [plan_box, sec_box, list(r), [55, 1093, 377, 1128], [555, 690, 770, 750]]
