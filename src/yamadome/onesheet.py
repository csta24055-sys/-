"""手書き作図ガイドの 1 枚版（A3）: 白紙の課題用紙 1 ページ目に、なぞる線（薄い青）と紙上 mm の要点を書き込む。

数値はすべて完成答案と同じ形状（config・geometry）から、課題用紙の通り芯の実測倍率で紙上 mm に換算する。
"""
from __future__ import annotations
import pymupdf
from shapely.ops import unary_union
from . import answer_sheet as A
from .calculation import widen
from .geometry import final_depth_pieces, section_profile
from .pdf_tools import _font

PT2MM = 25.4 / 72
GUIDE = (0.10, 0.40, 0.95)          # なぞる線・数値（青）
INK = (0.05, 0.05, 0.05)
CIRC = "①②③④⑤⑥⑦⑧⑨"


def build(out_pdf, site, zones, res, base_pdf):
    doc = pymupdf.open(base_pdf)
    doc.select([site.raw["answer_sheet"]["page_index"]])
    page = doc[0]
    fn = _font(page)
    m = A.Mapper(site)
    gx, gy = site.grid_x, site.grid_y
    kx = m.sx * PT2MM                  # 実寸 mm → 紙上 mm（横）
    ky = m.sy * PT2MM                  # （縦・深さ）
    X = lambda v: f"{abs(v) * kx:.1f}"
    Y = lambda v: f"{abs(v) * ky:.1f}"
    ret = site.raw["retaining"]; n = ret["slope_ratio"]; east = ret["soldier_pile_x_mm"]

    def txt(x, y, s, size=6.2, color=INK):
        page.insert_text(pymupdf.Point(x, y), s, fontsize=size, fontname=fn, color=color)

    def box(x0, y0, x1, y1, lines, size=6.2, lead=1.32, title=None):
        sh = page.new_shape(); sh.draw_rect(pymupdf.Rect(x0, y0, x1, y1))
        sh.finish(color=GUIDE, fill=(1, 1, 1), width=0.5); sh.commit()
        y = y0 + size + 2
        if title:
            txt(x0 + 3, y, title, size + 1.2, GUIDE); y += (size + 1.2) * lead
        for s in lines:
            if y > y1 - 2:
                raise RuntimeError(f"枠に収まらない: {s}")
            txt(x0 + 3, y, s, size); y += size * lead

    def lines_of(geom, width, dashes=None):
        sh = page.new_shape()
        A._poly(sh, geom, m.plan)
        sh.finish(color=GUIDE, width=width, dashes=dashes, stroke_opacity=0.75)
        sh.commit()

    # ---------------- 平面図：なぞる線（薄い青）
    bottom = unary_union([z[3] for z in zones])
    top = unary_union([widen(z[3], n * z[2] * 1000, east) for z in zones])
    for depth, g in final_depth_pieces(zones):
        lines_of(g, 0.35, "[2 1] 0")              # 深さの境界
    lines_of(top, 0.45)                           # 法肩
    lines_of(bottom, 0.8)                         # 法尻
    sh = page.new_shape()
    for a, b in A.ridge_lines(bottom, top, east):
        sh.draw_line(m.plan(*a), m.plan(*b))
    sh.finish(color=GUIDE, width=0.4, stroke_opacity=0.75); sh.commit()
    sh = page.new_shape()
    sh.draw_line(m.plan(east, bottom.bounds[1]), m.plan(east, bottom.bounds[3]))
    sh.finish(color=GUIDE, width=1.6, stroke_opacity=0.75); sh.commit()

    # 基礎掘削（法尻の四角）に番号、通り芯からの距離
    pits = [z for z in zones[1:]]
    order = sorted(pits, key=lambda z: (-z[3].bounds[3], z[3].bounds[0]))
    rows = []
    for i, (name, cls, d, p) in enumerate(order):
        c = p.centroid if "F5" not in name else p.representative_point()
        q = m.plan(c.x, c.y)
        sh = page.new_shape(); sh.draw_circle(q, 5.2); sh.finish(color=GUIDE, fill=(1, 1, 1), width=0.6); sh.commit()
        page.insert_textbox(pymupdf.Rect(q.x - 6, q.y - 4.6, q.x + 6, q.y + 5), str(i + 1), fontsize=6.8, fontname=fn,
                            color=GUIDE, align=pymupdf.TEXT_ALIGN_CENTER)
        x0, y0, x1, y1 = p.bounds
        gxk = min(gx, key=lambda k: abs(gx[k] - (x0 + x1) / 2)); gyk = min(gy, key=lambda k: abs(gy[k] - (y0 + y1) / 2))
        ox, oy = gx[gxk], gy[gyk]
        lab = name.split(" ")[0]
        if "F5" in name:
            xs = sorted({round(v[0]) for v in p.exterior.coords}); ys = sorted({round(v[1]) for v in p.exterior.coords})
            rows.append((f"{i+1} {lab} 三角形", f" 北辺 {gyk}上{Y(ys[-1]-oy)}：{gxk}左{X(xs[0]-ox)}〜右{X(xs[-1]-ox)}",
                         f" 斜辺：その左端 → {gxk}右{X(xs[-1]-ox)}・{gyk}下{Y(oy-ys[0])}", f" 深さ GL-{d*1000:.0f}"))
        else:
            rows.append((f"{i+1} {lab}（{gxk}・{gyk}）GL-{d*1000:.0f}",
                         f" 左{X(x0-ox)} 右{X(x1-ox)}" if x1 <= east - 1 else f" 左{X(x0-ox)} 右{X(x1-ox)}（親杭線）",
                         f" 下{Y(y0-oy)} 上{Y(y1-oy)}"))

    # 外周（FS1）の法尻
    bx0, by0, bx1, by1 = zones[0][3].bounds
    sw = {d: n * d * 1000 for d in (1.65, 1.85, 2.10, 2.20)}

    # ---------------- 断面図：なぞる線
    segs = section_profile(zones, gy["Y3"])
    x0s = segs[0][0]; swa = n * segs[0][2] * 1000
    prof = [(x0s - swa, 0), (x0s, -segs[0][2] * 1000)]
    for a_, b_, d in segs:
        prof += [(a_, -d * 1000), (b_, -d * 1000)]
    prof += [(segs[-1][1], 0)]
    sh = page.new_shape(); sh.draw_polyline([m.sec(*p) for p in prof]); sh.finish(color=GUIDE, width=0.8, stroke_opacity=0.8); sh.commit()
    for a_, b_, d in segs:                                    # 区間ごとの深さ（紙上 mm）
        if b_ - a_ > 1200:
            q = m.sec(a_, -d * 1000)
            txt(q.x + 2, q.y + 7.0, f"↓{Y(d*1000)}", 5.8, GUIDE)

    def sec_x(v):
        k = min(gx, key=lambda k: abs(gx[k] - v))
        dv = v - gx[k]
        return f"{k}{'右' if dv >= 0 else '左'}{X(dv)}"
    srows = [f"法面：GL上 {sec_x(x0s - swa)} → 下{Y(segs[0][2]*1000)}・{sec_x(x0s)}（斜線）"]
    for a_, b_, d in segs:
        srows.append(f"GL下{Y(d*1000)}（GL-{d*1000:.0f}）：{sec_x(a_)} 〜 {sec_x(b_)}")
    srows.append(f"東：{sec_x(segs[-1][1])} を GL まで垂直（親杭面）。段差は区間の境で垂直")

    # ---------------- 書き込み（余白）
    pr = "、".join(f"{X(sw[d])}" for d in (1.65, 1.85, 2.10, 2.20))
    box(56, 58, 612, 146, [
        "0 印刷は A3「実際のサイズ」。定規で X1〜X4 = %s mm、Y2〜Y3 = %s mm を確認（違えば数値×実測/%s）。数値はすべて紙の上の mm。"
        % (X(gx["X4"] - gx["X1"]), Y(gy["Y3"] - gy["Y2"]), X(gx["X4"] - gx["X1"])),
        "1 法尻＝根切り底の外形（0.5mm 茶）。外周：X1 から左 %s、Y2 から下 %s、Y3 から上 %s、東は X4 から右 %s の親杭線まで。"
        % (X(bx0), Y(by0), Y(by1 - gy["Y3"]), X(bx1 - gx["X4"])),
        "   基礎まわりは左の表の①〜⑧の四角（三角）まで外へ張り出す。四角の FS1 側の辺は深さの境界（0.2mm 茶、法面なし）。",
        "2 法肩（0.3mm 茶）：法尻の外側に平行、離れ %s mm（GL-1650 / 1850 / 2100 / 2200 の順）。東面には描かない。" % pr,
        "3 稜線（0.2mm 茶）：法尻の角と法肩の角を 45°で結ぶ（出隅・入隅とも）。",
        "4 東面：X4 から右 %s の線を太い赤で（親杭横矢板）。H記号は図示（ピッチの指定なし）。" % X(east - gx["X4"]),
        "5 深さ表示を枠で（GL-1650 / 1850 / 2100 / 2200）。寸法は実寸で：495｜500、1700｜1700、1310｜1090、1390／1610、1240、余幅100。",
        "6 着色：FS1＝黄、F3・F4・F5＝緑、F4A＝橙、F3A＝濃橙。法面（法尻〜法肩）は塗らない。  ※青い線は完成形（なぞる位置）。",
    ], size=6.0, title="根切り図（平面）の描き方")
    left = ["通り芯から（紙上 mm）"]
    for r in rows:
        left += list(r)
    box(18, 152, 107, 432, left, size=5.4, lead=1.36, title="基礎掘削の法尻")
    box(40, 700, 802, 768, [
        "0 基準は印刷済みの ▽GL の線と X1〜X4 の通り芯。深さは GL の線から下へ測る（↓ の数値、紙上 mm）。根切り線は 0.3mm 茶。",
        "1 " + srows[0] + "    2 " + srows[1],
        "3 " + "　".join(srows[2:5]),
        "   " + "　".join(srows[5:8]),
        "4 " + srows[-1] + "。親杭（山留H鋼）は東端の外側に細長い長方形、注記「余幅100」。",
        "5 着色は根切り線の土側に幅 約1.5mm の帯：法面・GL際・東の壁＝茶、底＝深さの色（黄・緑・橙・濃橙）。掘った部分の中は塗らない。",
    ], size=6.0, title="根切り断面図（Y3通り）の描き方")
    box(40, 1094, 420, 1154, [
        f"掘削土量 V = {res.total:.2f} m³（右の解答欄に記入）",
        f"方法A ΣAi×hi = {res.method_a:.3f} m³",
        f"方法B A0×1.65+ΣAj×Δhj = {res.a0_area:.3f}×1.65 + 増掘り = {res.method_b:.3f} m³",
        "余幅 = 作業ゆとり 0.5 + 法幅 0.3h/2（外周のみ）、東面は余幅 0.1・法なし",
        "仕上げ：青い線と自分の線が重なるか確認 → 完成見本（02・03）と照合",
    ], size=5.8, lead=1.25, title="答え・照合")
    doc.save(out_pdf, garbage=3, deflate=True)
    doc.close()
