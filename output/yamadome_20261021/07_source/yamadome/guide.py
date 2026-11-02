"""04_手書き作図完全ガイド_実寸寸法と手順.pdf の生成と、手順からの再構成検証。

数値はすべて手書き見本（①②）に描かれたベクター図形の座標から求める（handwriting.extract）。
紙上の距離は「A3 用紙・実際のサイズ（100%）で印刷」したときの値（1pt = 25.4/72 mm）。
"""
from __future__ import annotations
import io
import math
from dataclasses import dataclass, field
import pymupdf
from PIL import Image
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union, linemerge
from .handwriting import PT2MM, PEN, NAME, extract
from .pdf_tools import JP_FONT

A3 = (841.92, 1190.52)
FONT = pymupdf.Font(fontfile=JP_FONT)
RED = (0.85, 0.0, 0.0)
BLUE = (0.0, 0.35, 0.85)
GREY = (0.55, 0.55, 0.55)


# ------------------------------------------------------------------ 座標の言い換え
@dataclass
class Ref:
    name: str
    x: float          # pt
    y: float          # pt


class Frame:
    """紙上の位置を「基準点から右/左・上/下に何 mm」で言うための枠組み。"""

    def __init__(self, site):
        a = site.raw["answer_sheet"]; g = a["plan_grid_pt"]; gx = site.grid_x; gy = site.grid_y
        self.sx = (g["X4"] - g["X1"]) / (gx["X4"] - gx["X1"])            # pt / 実寸mm
        self.sy = (g["Y2"] - g["Y3"]) / (gy["Y3"] - gy["Y2"])
        self.X = {k: g["X1"] + (v - gx["X1"]) * self.sx for k, v in gx.items()}
        self.Y = {"Y3": g["Y3"], "Y2": g["Y2"]}
        self.GL = a["section_GL_pt"]
        self.plan_refs = [Ref(f"{xk}・{yk}", xv, yv) for yk, yv in self.Y.items() for xk, xv in self.X.items()]

    def real(self, dpt, axis="x"):
        return dpt / (self.sx if axis == "x" else self.sy)

    def plan_ref(self, p):
        return min(self.plan_refs, key=lambda r: (r.x - p[0]) ** 2 + (r.y - p[1]) ** 2)

    def sec_ref(self, p):
        k = min(self.X, key=lambda k: abs(self.X[k] - p[0]))
        return Ref(f"{k}通り・GL", self.X[k], self.GL)


def mm(pt):
    return pt * PT2MM


def fmt(v):
    return f"{v:.1f}"


def offset_text(ref, p, frame):
    dx, dy = mm(p[0] - ref.x), mm(p[1] - ref.y)
    h = "右" if dx >= 0 else "左"; v = "下" if dy >= 0 else "上"
    s = []
    s.append(f"{h}{fmt(abs(dx))}" if abs(dx) >= 0.05 else "左右0")
    s.append(f"{v}{fmt(abs(dy))}" if abs(dy) >= 0.05 else "上下0")
    return "・".join(s) + " mm"


def direction_text(p, q):
    dx, dy = mm(q[0] - p[0]), mm(q[1] - p[1])
    L = math.hypot(dx, dy)
    if abs(dy) < 0.05:
        return ("水平・右" if dx > 0 else "水平・左"), L
    if abs(dx) < 0.05:
        return ("垂直・下" if dy > 0 else "垂直・上"), L
    h = "右" if dx > 0 else "左"; v = "下" if dy > 0 else "上"
    return f"斜め・{h}{v}（横{fmt(abs(dx))}・縦{fmt(abs(dy))}）", L


# ------------------------------------------------------------------ 手順の組立て
@dataclass
class Step:
    no: str
    title: str
    kind: str                     # line / point / fill / text / mark
    cls: str
    pts: list                     # pt
    ref: Ref | None = None
    start_from: str = ""          # 「STEP x の終点」など
    note: str = ""
    color: tuple = ()
    text: str = ""
    size: float = 0.0


@dataclass
class Group:
    title: str
    intro: str
    steps: list = field(default_factory=list)
    focus: list | None = None      # 拡大図の範囲 [x0,y0,x1,y1] pt（None なら手順から自動）


def _chains(segs, tol=0.02):
    """線分の集まりを、端点のつながった連続線（点列）に並べる。"""
    segs = [tuple(map(tuple, s)) for s in segs]
    used = [False] * len(segs)
    out = []
    for i, s in enumerate(segs):
        if used[i]:
            continue
        used[i] = True
        chain = [s[0], s[1]]
        grown = True
        while grown:
            grown = False
            for j, t in enumerate(segs):
                if used[j]:
                    continue
                for a, b in ((t[0], t[1]), (t[1], t[0])):
                    if math.dist(a, chain[-1]) < tol:
                        chain.append(b); used[j] = True; grown = True; break
                    if math.dist(b, chain[0]) < tol:
                        chain.insert(0, a); used[j] = True; grown = True; break
                if grown:
                    break
        out.append(chain)
    return out


def _minus(segs, others, tol=0.05):
    """segs のうち others の線と重なる部分を除く（重複して描かないため）。"""
    if not others:
        return segs
    cover = unary_union([LineString(o) for o in others]).buffer(tol)
    out = []
    for s in segs:
        r = LineString(s).difference(cover)
        for g in getattr(r, "geoms", [r]):
            if g.length > 0.1 and g.geom_type == "LineString":
                c = list(g.coords)
                out.append([c[0], c[-1]])
    return out


def _line_steps(prefix, chains, cls, frame, refmode="plan"):
    steps = []
    n = 0
    for chain in chains:
        # 始点は左上（北西）寄りの点にそろえる（閉じた輪郭のとき）
        closed = math.dist(chain[0], chain[-1]) < 0.02 and len(chain) > 3
        if closed:
            pts = chain[:-1]
            k = min(range(len(pts)), key=lambda i: (pts[i][1] + pts[i][0] * 0.2))
            pts = pts[k:] + pts[:k]
            chain = pts + [pts[0]]
        for i, (p, q) in enumerate(zip(chain, chain[1:])):
            n += 1
            ref = frame.plan_ref(p) if refmode == "plan" else frame.sec_ref(p)
            steps.append(Step(f"{prefix}{n}", "", "line", cls, [p, q], ref=ref,
                              start_from=("" if i == 0 else f"{prefix}{n-1} の終点")))
    return steps


def build_plan_groups(prims, frame):
    legend_box = (550, 685, 800, 760)
    inleg = lambda p: all(legend_box[0] <= x <= legend_box[2] and legend_box[1] <= y <= legend_box[3] for x, y in p.pts)
    by = lambda c: [p.pts for p in prims if p.cls == c and not inleg(p)]
    bottom = by("bottom")
    top = _minus(by("top"), bottom)
    border = _minus(by("border"), bottom)
    ridge = by("ridge")
    G = []
    g = Group("平面2 法尻（根切り底の外形）を描く",
              "根切り底（床付け面）の外形線。基礎・梁の外面から作業のゆとり 500（実寸）外側にあり、"
              "基礎まわりは外へ張り出す。最初にすべての角に鉛筆で小さく印を付け、つないでから 0.5mm の茶ペンでなぞる。")
    g.steps = _line_steps("B", _chains(bottom), "bottom", frame)
    G.append(g)
    g = Group("平面3 深さの境界（内部の段差）を描く",
              "FS1（GL-1650）と基礎まわりの深掘り（GL-1850/2100/2200）の境界。内部の段差は鉛直なので1本線だけ（法面は描かない）。")
    g.steps = _line_steps("D", _chains(border), "border", frame)
    G.append(g)
    g = Group("平面4 法肩を描く",
              "法面の上端。法尻から外側へ 法幅 0.3h（実寸 495/555/630/660）離れた線。東面（親杭側）には法肩はない。")
    g.steps = _line_steps("T", _chains(top), "top", frame)
    G.append(g)
    g = Group("平面5 稜線（角の斜線）を描く",
              "法尻の角と法肩の角を結ぶ斜線。出隅・入隅とも描く。端点はすでに描いた法尻・法肩の角に一致する。")
    st = []
    for i, s in enumerate(ridge, 1):
        st.append(Step(f"R{i}", "", "line", "ridge", s, ref=frame.plan_ref(s[0])))
    g.steps = st
    G.append(g)
    g = Group("平面6 東面の親杭横矢板を描く", "親杭の通り（太線）と H 記号。H 記号は図示用の記号で、親杭のピッチを指定するものではない（資料にピッチの記載なし）。")
    st = [Step(f"K{i}", "", "line", "pile", s, ref=frame.plan_ref(s[0])) for i, s in enumerate(by("pile"), 1)]
    hm = [p for p in prims if p.cls == "hmark"]
    hm_h = [p for p in hm if abs(p.pts[0][1] - p.pts[1][1]) < 0.01]
    ys = sorted({round(p.pts[0][1], 2) for p in hm_h})
    hm_v = [p for p in hm if abs(p.pts[0][0] - p.pts[1][0]) < 0.01]
    st.append(Step("K-H", "", "mark", "hmark", [p.pts for p in hm], ref=frame.plan_ref(hm_h[0].pts[0]) if hm_h else None,
                   note=(f"H記号 {len(ys)} 個（親杭の通りの上、南端から北端まで等間隔 {fmt(mm(ys[1]-ys[0]))} mm）："
                         f"横棒 {fmt(mm(abs(hm_h[0].pts[1][0]-hm_h[0].pts[0][0])))} mm、縦棒 {fmt(mm(abs(hm_v[0].pts[1][1]-hm_v[0].pts[0][1])))} mm×2（横棒の両端）")
                   if len(ys) > 1 and hm_v else ""))
    g.steps = st
    G.append(g)
    # 寸法線（図形ごと）
    g = Group("平面7 寸法線を記入する", "寸法線（0.1mm 赤）と数値。数値は実寸（mm）で書く。寸法線の両端に短い斜線（矢印の代わり）を付ける。")
    g.steps = _dim_steps("M", [p for p in prims if p.cls == "dim"], [p for p in prims if p.cls == "text"], frame, "plan")
    G.append(g)
    # 深さ表示・引出線
    g = Group("平面8 深さ表示（枠）と引出線、注記を記入する",
              "深さは授業図と同じ「GL-1850」の形で枠に入れ、引出線の先に黒丸を付けて区画を指す。注記は図の位置に書く。")
    st = []
    boxes = _rects([p.pts for p in prims if p.cls == "labelbox"])
    for i, r in enumerate(boxes, 1):
        st.append(Step(f"L{i}", "", "line", "labelbox", [(r[0], r[1]), (r[2], r[3])], ref=frame.plan_ref((r[0], r[1])),
                       note=f"枠 横{fmt(mm(r[2]-r[0]))}×縦{fmt(mm(r[3]-r[1]))} mm"))
    for i, s in enumerate([p.pts for p in prims if p.cls == "leader" and not inleg(p)], 1):
        st.append(Step(f"Q{i}", "", "line", "leader", s, ref=frame.plan_ref(s[0])))
    for i, p in enumerate([p for p in prims if p.cls == "dot"], 1):
        st.append(Step(f"Q•{i}", "", "point", "leader", p.pts, ref=frame.plan_ref(p.pts[0]), note="直径 約0.6mm の黒丸"))
    used_txt = {id(t) for s in G[-1].steps for t in s.pts if False}
    for i, t in enumerate(_texts_not_dims(prims, G[-1].steps), 1):
        st.append(Step(f"N{i}", "", "text", "text", t.pts, ref=frame.plan_ref(t.pts[0]), text=t.text, size=t.size))
    g.steps = st
    G.append(g)
    # 凡例
    g = Group("平面9 凡例を記入する", "根切り図の右下（表題「根切り図 1/100」の右）に、塗り色と線の意味を書く。")
    st = []
    leg = [p for p in prims if inleg(p) and p.cls != "fill" and p.cls != "text"]
    for i, p in enumerate(leg, 1):
        st.append(Step(f"G{i}", "", "line", p.cls, p.pts, ref=frame.plan_ref(p.pts[0])))
    for i, p in enumerate([p for p in prims if inleg(p) and p.cls == "fill"], 1):
        st.append(Step(f"G塗{i}", "", "fill", "fill", p.pts, ref=frame.plan_ref(p.pts[0]), color=p.color))
    g.steps = st
    G.append(g)
    # 解答欄
    g = Group("平面10 掘削土量を解答欄に記入する",
              "用紙下部の「掘削土量：　　m3」の空欄に答えを書く（完成答案と同じ値）。")
    vol = [p for p in prims if p.cls == "text" and p.text.replace(",", "").replace(".", "").isdigit()
           and p.pts[0][1] > 1100]
    g.steps = [Step(f"V{i}", "", "text", "text", t.pts, ref=frame.plan_ref(t.pts[0]), text=t.text, size=t.size)
               for i, t in enumerate(vol, 1)]
    G.append(g)
    # 着色
    g = Group("平面11 着色する（色鉛筆・蛍光ペン）",
              "線で囲まれた範囲を塗る。法面（法尻と法肩の間）は塗らない（白抜き）。塗る前に線がすべて描けているか確認する。")
    st = []
    for i, p in enumerate([p for p in prims if p.cls == "fill" and not inleg(p) and p.color != (1.0, 1.0, 1.0)], 1):
        st.append(Step(f"C{i}", "", "fill", "fill", p.pts, ref=frame.plan_ref(p.pts[0]), color=p.color))
    g.steps = st
    G.append(g)
    return G


def _rects(segs):
    """枠の4辺（線分）から矩形 [x0,y0,x1,y1] を復元。"""
    out = []
    for i in range(0, len(segs), 4):
        xs = [x for s in segs[i:i + 4] for x, _ in s]; ys = [y for s in segs[i:i + 4] for _, y in s]
        out.append((min(xs), min(ys), max(xs), max(ys)))
    return out


def _dim_steps(prefix, dprims, texts, frame, mode):
    """寸法: 図形ごとに 本体（最初の線）・寸法補助線（軸に平行な残り）・端部の斜線 に分ける。
    本体ごとに最寄りの数値文字を対応させる。"""
    groups = {}
    for p in dprims:
        groups.setdefault(p.extra.get("did"), []).append(p.pts)
    num = [t for t in texts if t.text.replace(",", "").replace(".", "").isdigit()]
    steps = []; i = 0
    for did, segs in groups.items():
        axis = [s for s in segs if abs(s[0][0] - s[1][0]) < 0.01 or abs(s[0][1] - s[1][1]) < 0.01]
        ticks = [s for s in segs if s not in axis]
        if not axis:
            continue
        main = axis[0]; ext = axis[1:]
        i += 1
        mid = ((main[0][0] + main[1][0]) / 2, (main[0][1] + main[1][1]) / 2)
        t = min(num, key=lambda t: math.dist(mid, ((t.pts[0][0] + t.pts[1][0]) / 2, (t.pts[0][1] + t.pts[1][1]) / 2))) if num else None
        ref = (frame.plan_ref if mode == "plan" else frame.sec_ref)(main[0])
        vert = abs(main[0][0] - main[1][0]) < 0.01
        steps.append(Step(f"{prefix}{i}", "", "line", "dim", main, ref=ref, text=t.text if t else "",
                          note=(f"数値「{t.text}」を線の{'左（縦書き）' if vert else '上'}に書く" if t else "") +
                               f"。両端に短い斜線（長さ{fmt(mm(math.dist(*ticks[0])))}mm、45°）" if ticks else ""))
        for j, e in enumerate(ext, 1):
            steps.append(Step(f"{prefix}{i}-{j}", "", "line", "dim", e, ref=(frame.plan_ref if mode == "plan" else frame.sec_ref)(e[0]),
                              note="寸法補助線（測る位置から寸法線まで）"))
    return steps


def _texts_not_dims(prims, dim_steps):
    used = {s.text for s in dim_steps if s.text}
    out = []
    for t in prims:
        if t.cls != "text":
            continue
        if t.text.replace(",", "").replace(".", "").isdigit():
            continue                       # 寸法数値は寸法線の手順で扱う
        out.append(t)
    return out


def build_section_groups(prims, frame):
    by = lambda c: [p.pts for p in prims if p.cls == c]
    G = []
    g = Group("断面2 根切り線（掘削輪郭）を描く",
              "西の法肩（GL上）から斜めに法尻へ下り、根切り底・段差をたどって東の親杭面で GL まで立ち上げる。"
              "最後に GL 上を細線で結んで輪郭を閉じる（完成答案と同じ）。0.3mm 茶ペン。")
    g.steps = _line_steps("S", _chains(by("sec_outline")), "sec_outline", frame, refmode="sec")
    G.append(g)
    g = Group("断面3 東面の親杭（山留H鋼）を描く", "親杭面（根切り線の東端）から外側に幅を取った細長い長方形。中は薄く赤で塗る。")
    rs = _rects(by("sec_pile"))
    g.steps = [Step(f"P{i}", "", "line", "sec_pile", [(r[0], r[1]), (r[2], r[3])], ref=frame.sec_ref((r[0], r[1])),
                    note=f"長方形 横{fmt(mm(r[2]-r[0]))}×縦{fmt(mm(r[3]-r[1]))} mm") for i, r in enumerate(rs, 1)]
    G.append(g)
    g = Group("断面4 寸法線・数値を記入する", "深さ寸法（GL からの縦の寸法）と、根切り底の区間寸法（下側の横一列）。0.1mm 赤。")
    g.steps = _dim_steps("M", [p for p in prims if p.cls == "dim"], [p for p in prims if p.cls == "text"], frame, "sec")
    G.append(g)
    g = Group("断面5 注記を記入する", "床付けレベル・法勾配・山留めの注記。")
    g.steps = [Step(f"N{i}", "", "text", "text", t.pts, ref=frame.sec_ref(t.pts[0]), text=t.text, size=t.size)
               for i, t in enumerate(_texts_not_dims(prims, []), 1)]
    G.append(g)
    g = Group("断面6 着色する（授業 X2断面と同じ部分着色）",
              "根切り線の土側（掘った側の反対）に沿って、幅 約1.5mm（実寸150）の帯で塗る。掘削部の内側は塗らない。"
              "法面と法肩の外の GL 際・東の壁＝茶、根切り底＝深さの色（FS1 黄・GL-1850 緑・F4A 橙・F3A 濃橙）、段差の立上りは深い側の色。")
    g.steps = [Step(f"C{i}", "", "fill", "fill", p.pts, ref=frame.sec_ref(p.pts[0]), color=p.color)
               for i, p in enumerate([p for p in prims if p.cls == "fill" and p.color != (0.75, 0.05, 0.05)], 1)]
    G.append(g)
    return G


# ------------------------------------------------------------------ 描画
COLOR_NAME = {(1.0, 0.93, 0.25): "黄（FS1 GL-1650）", (0.3, 0.78, 0.25): "緑（GL-1850）", (0.98, 0.62, 0.15): "橙（F4A GL-2100）",
              (0.9, 0.4, 0.1): "濃橙（F3A GL-2200）", (0.8, 0.58, 0.28): "茶（法面・GL際・東の壁）"}


def _ins(page, rect, s, size=9, color=(0, 0, 0), align=0):
    page.insert_font(fontname="ipag", fontfile=JP_FONT)
    rc = page.insert_textbox(rect, s, fontsize=size, fontname="ipag", color=color, align=align)
    if rc < 0:
        raise RuntimeError(f"文字が枠に収まらない: {s[:30]}")
    return rc


class Canvas:
    """元の課題用紙の一部（clip, pt）を、ガイドのページ上の rect に拡大して描く。"""

    def __init__(self, page, rect, base_page, clip, light=0.55):
        self.page, self.rect, self.clip = page, pymupdf.Rect(rect), pymupdf.Rect(clip)
        s = min(self.rect.width / self.clip.width, self.rect.height / self.clip.height)
        self.s = s
        w, h = self.clip.width * s, self.clip.height * s
        self.r = pymupdf.Rect(self.rect.x0, self.rect.y0, self.rect.x0 + w, self.rect.y0 + h)
        dpi = max(72, min(400, int(72 * s * 2)))
        pix = base_page.get_pixmap(dpi=dpi, clip=self.clip)
        im = Image.frombytes("RGB", (pix.w, pix.h), pix.samples)
        im = Image.blend(im, Image.new("RGB", im.size, (255, 255, 255)), light)
        bio = io.BytesIO(); im.save(bio, "PNG")
        page.insert_image(self.r, stream=bio.getvalue())
        sh = page.new_shape(); sh.draw_rect(self.r); sh.finish(color=GREY, width=0.5); sh.commit()

    def P(self, p):
        return pymupdf.Point(self.r.x0 + (p[0] - self.clip.x0) * self.s, self.r.y0 + (p[1] - self.clip.y0) * self.s)

    def inside(self, p):
        return self.clip.contains(pymupdf.Point(*p))

    def _box(self):
        from shapely.geometry import box
        c = self.clip
        return box(c.x0, c.y0, c.x1, c.y1)

    def line(self, p, q, color, width, dashes=None, opacity=1.0):
        g = LineString([p, q]).intersection(self._box())      # 枠の外にはみ出さない
        for seg in getattr(g, "geoms", [g]):
            if seg.is_empty or seg.geom_type != "LineString" or seg.length < 1e-6:
                continue
            a, b = seg.coords[0], seg.coords[-1]
            sh = self.page.new_shape(); sh.draw_line(self.P(a), self.P(b))
            sh.finish(color=color, width=width, dashes=dashes, stroke_opacity=opacity); sh.commit()

    def poly(self, pts, fill, opacity):
        g = Polygon(pts).buffer(0).intersection(self._box())
        for pg in getattr(g, "geoms", [g]):
            if pg.is_empty or pg.geom_type != "Polygon":
                continue
            sh = self.page.new_shape(); sh.draw_polyline([self.P(p) for p in pg.exterior.coords])
            sh.finish(color=None, fill=fill, fill_opacity=opacity, width=0); sh.commit()

    def dot(self, p, color, r=1.6, fill=None):
        if not self.inside(p):
            return
        sh = self.page.new_shape(); sh.draw_circle(self.P(p), r); sh.finish(color=color, fill=fill or color, width=0.5); sh.commit()

    def square(self, p, color, r=1.8):
        if not self.inside(p):
            return
        c = self.P(p); sh = self.page.new_shape(); sh.draw_rect(pymupdf.Rect(c.x - r, c.y - r, c.x + r, c.y + r))
        sh.finish(color=color, fill=(1, 1, 1), width=0.8); sh.commit()

    def label(self, p, s, color=RED, size=7, dx=2, dy=-2):
        if not self.inside(p):
            return
        c = self.P(p)
        self.page.insert_text(pymupdf.Point(c.x + dx, c.y + dy), s, fontsize=size, fontname="ipag", color=color)


def _draw_step(cv, st, color, width, opacity=1.0, mark=True):
    if st.kind == "line":
        p, q = st.pts
        if st.cls in ("labelbox", "sec_pile"):
            x0, y0 = p; x1, y1 = q
            for a, b in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
                cv.line(a, b, color, width, opacity=opacity)
        else:
            cv.line(p, q, color, width, opacity=opacity)
        if mark:
            cv.dot(p, color); cv.square(q, color)
    elif st.kind == "mark":
        for s in st.pts:
            cv.line(s[0], s[1], color, max(0.5, width * 0.6), opacity=opacity)
    elif st.kind == "point":
        cv.dot(st.pts[0], color, r=1.4)
    elif st.kind == "fill":
        cv.poly(st.pts, st.color, 0.75 if mark else 0.30)
        if mark:
            for a, b in zip(st.pts, st.pts[1:] + st.pts[:1]):
                cv.line(a, b, color, 0.9)
    elif st.kind == "text":
        (x0, y0), (x1, y1) = st.pts
        for a, b in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
            cv.line(a, b, color, 0.6, opacity=opacity)


def _bbox(steps):
    xs, ys = [], []
    for st in steps:
        pts = st.pts if st.kind != "mark" else [p for s in st.pts for p in s]
        for x, y in pts:
            xs.append(x); ys.append(y)
    return min(xs), min(ys), max(xs), max(ys)


def _fit(b, aspect, margin=14.0, minw=60.0):
    x0, y0, x1, y1 = b
    x0 -= margin; y0 -= margin; x1 += margin; y1 += margin
    w, h = max(x1 - x0, minw), max(y1 - y0, minw / aspect)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    if w / h < aspect:
        w = h * aspect
    else:
        h = w / aspect
    return (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)


def _r(v):
    return round(v + 0.0, 1)


def pos(frame, mode, p):
    """点 p の位置を「最寄りの基準点から右/左・下/上 mm（0.1mm 丸め）」で表す。(基準点, dx, dy) を返す。"""
    ref = frame.plan_ref(p) if mode == "plan" else frame.sec_ref(p)
    return ref, _r(mm(p[0] - ref.x)), _r(mm(p[1] - ref.y))


def pos_text(ref, dx, dy):
    h = f"右{fmt(dx)}" if dx > 0 else (f"左{fmt(-dx)}" if dx < 0 else "左右0")
    v = f"下{fmt(dy)}" if dy > 0 else (f"上{fmt(-dy)}" if dy < 0 else "上下0")
    return f"{ref.name} から {h}・{v}"


def row_text(st, frame, mode):
    """一覧表の1行: STEP, 開始位置, 方向・長さ, 終了位置, 線の種類・内容。"""
    pen = PEN.get(st.cls, "")
    nm = NAME.get(st.cls, st.cls)
    if st.kind == "line" and st.cls in ("labelbox", "sec_pile"):
        (x0, y0), (x1, y1) = st.pts
        a = pos(frame, mode, (x0, y0)); b = pos(frame, mode, (x1, y1))
        return [st.no, pos_text(*a) + "（左上の角）", f"長方形 横{fmt(mm(x1-x0))}×縦{fmt(mm(y1-y0))}",
                pos_text(*b) + "（右下の角）", f"{nm} {pen}" + (f"。{st.note}" if st.note else "")]
    if st.kind == "line":
        p, q = st.pts
        d, L = direction_text(p, q)
        a = pos(frame, mode, p); b = pos(frame, mode, q)
        start = (st.start_from + "（" + pos_text(*a) + "）") if st.start_from else pos_text(*a)
        return [st.no, start, f"{d} {fmt(L)}mm", pos_text(*b), f"{nm} {pen}" + (f"。{st.note}" if st.note else "")]
    if st.kind == "point":
        return [st.no, pos_text(*pos(frame, mode, st.pts[0])), "点", "—", st.note]
    if st.kind == "mark":
        return [st.no, "図のとおり", "—", "—", st.note]
    if st.kind == "fill":
        a = pos(frame, mode, st.pts[0])
        return [st.no, f"{pos_text(*a)} を含む範囲（頂点 {len(st.pts)}）", "塗り", "図の太枠の内側",
                COLOR_NAME.get(st.color, str(st.color))]
    if st.kind == "text":
        (x0, y0), _ = st.pts
        return [st.no, pos_text(*pos(frame, mode, (x0, y0))) + "（文字の左上）", "文字",
                f"文字の高さ 約{fmt(st.size * PT2MM * 0.72)}mm", f"「{st.text}」"]
    return [st.no, "", "", "", ""]


COLS = [("STEP", 40), ("開始位置（基準点から紙上 mm）", 205), ("方向・紙上の長さ", 150), ("終了位置（基準点から紙上 mm）", 205), ("線の種類・ペン・内容", 170)]


def table(page, x, y, rows, size=7.4, rowh=11.5, maxy=None):
    page.insert_font(fontname="ipag", fontfile=JP_FONT)
    cx = x
    for (h, w) in COLS:
        page.insert_text(pymupdf.Point(cx + 2, y + 8), h, fontsize=size, fontname="ipag", color=(0, 0, 0)); cx += w
    sh = page.new_shape(); sh.draw_line(pymupdf.Point(x, y + 11), pymupdf.Point(cx, y + 11)); sh.finish(color=(0, 0, 0), width=0.6); sh.commit()
    yy = y + 11
    for r in rows:
        if maxy and yy + rowh > maxy:
            return yy, False
        cx = x
        for (h, w), v in zip(COLS, r):
            s = str(v)
            while FONT.text_length(s, fontsize=size) > w - 3 and len(s) > 1:
                s = s[:-1]
            if s != str(v):
                s = s[:-1] + "…"
            page.insert_text(pymupdf.Point(cx + 2, yy + 8.5), s, fontsize=size, fontname="ipag", color=(0, 0, 0)); cx += w
        yy += rowh
        sh = page.new_shape(); sh.draw_line(pymupdf.Point(x, yy), pymupdf.Point(cx, yy)); sh.finish(color=(0.8, 0.8, 0.8), width=0.3); sh.commit()
    return yy, True


def wrap_rows(rows):
    """長い「線の種類・内容」は2行目に折り返す。"""
    out = []
    for r in rows:
        s = str(r[4])
        w = COLS[4][1] - 4
        parts = []
        while FONT.text_length(s, fontsize=7.4) > w:
            k = len(s)
            while FONT.text_length(s[:k], fontsize=7.4) > w:
                k -= 1
            parts.append(s[:k]); s = s[k:]
        parts.append(s)
        out.append(r[:4] + [parts[0]])
        for p in parts[1:]:
            out.append(["", "", "", "", p])
    return out


# ------------------------------------------------------------------ ページ組立て
PLAN_CLIP = (130.0, 95.0, 790.0, 690.0)
SEC_CLIP = (90.0, 845.0, 800.0, 990.0)
CHUNK = 7


def _new(doc, title):
    page = doc.new_page(width=A3[0], height=A3[1])
    page.insert_font(fontname="ipag", fontfile=JP_FONT)
    page.insert_text(pymupdf.Point(36, 40), title, fontsize=15, fontname="ipag", color=(0, 0, 0))
    sh = page.new_shape(); sh.draw_line(pymupdf.Point(36, 48), pymupdf.Point(A3[0] - 36, 48)); sh.finish(color=(0, 0, 0), width=0.8); sh.commit()
    page.insert_text(pymupdf.Point(A3[0] - 120, A3[1] - 20), f"p.{doc.page_count}", fontsize=9, fontname="ipag", color=GREY)
    return page


def _refs_on(cv, frame, mode):
    pts = [(r.x, r.y, r.name) for r in frame.plan_refs] if mode == "plan" else [(x, frame.GL, f"{k}・GL") for k, x in frame.X.items()]
    for x, y, nm in pts:
        if cv.inside((x, y)):
            c = cv.P((x, y))
            sh = cv.page.new_shape()
            sh.draw_line(pymupdf.Point(c.x - 5, c.y), pymupdf.Point(c.x + 5, c.y)); sh.draw_line(pymupdf.Point(c.x, c.y - 5), pymupdf.Point(c.x, c.y + 5))
            sh.finish(color=BLUE, width=1.0); sh.commit()
            cv.label((x, y), nm, BLUE, 6.5, 3, 9)


def _offset_guide(cv, frame, mode, p):
    """基準点から開始点までの道のり（青の破線）と mm 表示。"""
    ref, dx, dy = pos(frame, mode, p)
    if not (cv.inside((ref.x, ref.y)) or True):
        return
    corner = (p[0], ref.y)
    cv.line((ref.x, ref.y), corner, BLUE, 0.7, dashes="[2 1.5] 0")
    cv.line(corner, p, BLUE, 0.7, dashes="[2 1.5] 0")
    mx = ((ref.x + corner[0]) / 2, ref.y)
    my = (corner[0], (corner[1] + p[1]) / 2)
    if abs(dx) >= 0.05:
        cv.label(mx, f"{'右' if dx > 0 else '左'}{fmt(abs(dx))}mm", BLUE, 6.5, -12, -3)
    if abs(dy) >= 0.05:
        cv.label(my, f"{'下' if dy > 0 else '上'}{fmt(abs(dy))}mm", BLUE, 6.5, 3, 2)


def _group_pages(doc, base_page, frame, mode, groups, gi, done):
    g = groups[gi]
    clip = PLAN_CLIP if mode == "plan" else SEC_CLIP
    chunks = [g.steps[i:i + CHUNK] for i in range(0, len(g.steps), CHUNK)] or [[]]
    for ci, chunk in enumerate(chunks):
        page = _new(doc, f"{g.title}" + (f"（{ci+1}/{len(chunks)}）" if len(chunks) > 1 else ""))
        _ins(page, pymupdf.Rect(36, 56, A3[0] - 36, 100), g.intro, 9)
        # 全体図
        top_h = 330 if mode == "plan" else 120
        cv = Canvas(page, (36, 104, A3[0] - 36, 104 + top_h), base_page, clip)
        for st in done:
            _draw_step(cv, st, (0.55, 0.40, 0.25), 0.6, opacity=0.6, mark=False)
        for st in chunk:
            _draw_step(cv, st, RED, 1.3, mark=False)
        _refs_on(cv, frame, mode)
        y = cv.r.y1 + 8
        page.insert_text(pymupdf.Point(36, y + 8), "全体図：赤＝このページで描く線、茶（薄）＝描き終えた線、青＋＝基準点（印刷された通り芯の交点）",
                         fontsize=7.5, fontname="ipag", color=(0.2, 0.2, 0.2))
        # 拡大図
        if chunk:
            zh = 300 if mode == "plan" else 260
            zr = (36, y + 16, A3[0] - 36, y + 16 + zh)
            b = _fit(_bbox(chunk), (zr[2] - zr[0]) / (zr[3] - zr[1]), margin=16)
            zc = Canvas(page, zr, base_page, b, light=0.45)
            for st in done:
                _draw_step(zc, st, (0.55, 0.40, 0.25), 0.8, opacity=0.6, mark=False)
            for st in chunk:
                _draw_step(zc, st, RED, 1.6)
                if st.kind in ("line", "point", "text", "fill") and not st.start_from:
                    _offset_guide(zc, frame, mode, st.pts[0])
                lab_p = st.pts[0] if st.kind != "mark" else st.pts[0][0]
                if st.kind == "line" and st.cls not in ("labelbox", "sec_pile"):
                    lab_p = ((st.pts[0][0] + st.pts[1][0]) / 2, (st.pts[0][1] + st.pts[1][1]) / 2)
                zc.label(lab_p, st.no, RED, 8, 3, -3)
            _refs_on(zc, frame, mode)
            y = zc.r.y1 + 6
            page.insert_text(pymupdf.Point(36, y + 8), "拡大図：●＝始点、□＝終点、青の破線＝基準点から始点までの測り方（紙上 mm）",
                             fontsize=7.5, fontname="ipag", color=(0.2, 0.2, 0.2))
            rows = wrap_rows([row_text(st, frame, mode) for st in chunk])
            table(page, 36, y + 16, rows, maxy=A3[1] - 30)
        done.extend(chunk)


def _footing_details(doc, base_page, frame, site, zones, plan_steps):
    """フーチング（基礎）まわりの拡大：基礎外面→法尻（作業ゆとり500）→法肩（法幅0.3h）の距離。"""
    from .calculation import widen
    n = site.raw["retaining"]["slope_ratio"]; east = site.raw["retaining"]["soldier_pile_x_mm"]
    P = lambda x, y: (frame.X["X1"] + x * frame.sx, frame.Y["Y2"] - y * frame.sy)
    fts = site.raw["footings"]
    for f in fts:
        pm = f["plan_mm"]
        if "x" not in pm:
            continue
        x0, x1 = pm["x"]; y0, y1 = pm["y"]
        d = -f["subgrade_GL_mm"] / 1000
        page = _new(doc, f"平面 拡大 {f['name']}（{f['at']}）まわり：基礎 → 法尻 → 法肩 の距離")
        _ins(page, pymupdf.Rect(36, 56, A3[0] - 36, 110),
             f"{f['name']} の基礎（印刷済みの四角）から外側へ、作業のゆとり 500（実寸）＝紙上 {fmt(500*frame.sx*PT2MM)}mm に法尻、"
             f"さらに法幅 0.3×{d:.2f}m = {0.3*d*1000:.0f}（実寸）＝紙上 {fmt(0.3*d*1000*frame.sx*PT2MM)}mm に法肩。"
             "内部（FS1 側）は段差が鉛直なので法尻（深さの境界）だけ。東面は親杭面で止める。", 9)
        a = P(x0 - 2400, y1 + 2400); b = P(x1 + 2400, y0 - 2400)
        clip = (min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1]))
        zc = Canvas(page, (36, 116, A3[0] - 36, 116 + 640), base_page, _fit(clip, (A3[0] - 72) / 640, margin=0))
        for st in plan_steps:
            if st.cls in ("bottom", "top", "ridge", "border", "pile"):
                _draw_step(zc, st, (0.55, 0.27, 0.05), 1.0, mark=False)
        # 寸法（青）: 基礎外面→法尻→法肩
        k = PT2MM
        def dim(p, q, txt, off=(0, 0)):
            zc.line(p, q, BLUE, 1.0)
            zc.dot(p, BLUE, 1.3); zc.dot(q, BLUE, 1.3)
            m = ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
            zc.label(m, txt, BLUE, 8, 3 + off[0], -3 + off[1])
        W = 500; S = 0.3 * d * 1000
        cy = (y0 + y1) / 2; cx = (x0 + x1) / 2
        for side, (fp, bp, tp) in {
            "西": (P(x0, cy), P(x0 - W, cy), P(x0 - W - S, cy)),
            "東": (P(x1, cy), P(min(x1 + W, east), cy), P(min(x1 + W + S, east), cy)),
            "南": (P(cx, y0), P(cx, y0 - W), P(cx, y0 - W - S)),
            "北": (P(cx, y1), P(cx, y1 + W), P(cx, y1 + W + S)),
        }.items():
            dim(fp, bp, f"{fmt(math.dist(fp, bp)*k)}mm")
            if math.dist(bp, tp) > 0.1:
                dim(bp, tp, f"{fmt(math.dist(bp, tp)*k)}mm", off=(0, 10))
        rows = [["基礎の外面", f"X: {x0}〜{x1}、Y: {y0}〜{y1}（実寸 mm、X1・Y2 基準）", "印刷済みの四角", "—", "課題PDF p.1"],
                ["法尻（作業ゆとり）", f"基礎外面から 500（実寸）", f"紙上 {fmt(500*frame.sx*k)}mm", "—", "0.5mm 茶"],
                ["法肩（法幅 0.3h）", f"法尻から {S:.0f}（実寸、h={d:.2f}m）", f"紙上 {fmt(S*frame.sx*k)}mm", "—", "0.3mm 茶"],
                ["内部の境界", "FS1 側は段差が鉛直", "法尻＝深さの境界の1本線", "—", "0.2mm 茶"]]
        table(page, 36, 116 + 650, rows)


def _cover(doc, site, frame, res, plan_steps, sec_steps):
    page = _new(doc, "04 手書き作図完全ガイド ― 実寸寸法と手順（根切り図・Y3通り根切り断面図）")
    k = PT2MM
    x12 = (frame.X["X2"] - frame.X["X1"]) * k; x14 = (frame.X["X4"] - frame.X["X1"]) * k; y23 = (frame.Y["Y2"] - frame.Y["Y3"]) * k
    b1 = pos_text(*pos(frame, "plan", plan_steps[0].pts[0])); s1 = pos_text(*pos(frame, "sec", sec_steps[0].pts[0]))
    txt = f"""このガイドの使い方
A3 の白黒課題用紙を机に置き、定規（mm 目盛）と油性ペンで、完成答案（02/03 の見本）と同じ図を描くための手順書です。
すべての数値は、完成答案の PDF に描かれた線の座標から計算したもので、写真からの目測や推測は入っていません。
数値は「紙の上で定規を当てる距離（mm）」です。実寸（建物の寸法）ではありません。

1. まず印刷の倍率を確認する（必ず最初に）
・用紙：A3（297×420mm）。印刷設定は「実際のサイズ」または「100%」。「用紙に合わせる」「縮小」は使わない。
・印刷した課題用紙で、印刷済みの通り芯の間隔を測る：
    X1〜X2 = {fmt(x12)}mm、X1〜X4 = {fmt(x14)}mm、Y2〜Y3 = {fmt(y23)}mm になっていれば正しい。
・注意：この課題用紙の図は正確な 1/100 より約0.9% 大きく印刷されている（5,750 の寸法が 57.5mm ではなく {fmt(x12)}mm）。
  このガイドの数値はこの実際の用紙に合わせてあるので、「実寸÷100」で計算し直さず、表の数値をそのまま使う。
・もし X1〜X4 が {fmt(x14)}mm と違うときは、表の数値に（測った長さ ÷ {fmt(x14)}）を掛ける。

2. 基準点
・平面図：印刷済みの通り芯の交点（X1〜X4 と Y2・Y3 の交点、8 点）。例：最初の手順 B1 の始点「{b1}」は、
  その交点から書かれた向きと距離（mm）だけ定規で測った点、という意味。
・断面図：印刷済みの X1〜X4 の通り芯の線と、▽GL の線の交点。例：最初の手順 S1 の始点「{s1}」。
・方向は用紙を正しく置いたときの上下左右（平面図の上＝北、右＝東）。

3. 作業の順序（間違えにくい順）
  平面1 印刷・基準点の確認 → 平面2 法尻（外形）→ 平面3 深さの境界 → 平面4 法肩 → 平面5 稜線
  → 平面6 親杭 → 平面7 寸法線 → 平面8 深さ表示・注記 → 平面9 凡例 → 平面10 掘削土量 → 平面11 着色 → 照合
  断面1 基準の確認 → 断面2 根切り線 → 断面3 親杭 → 断面4 寸法線 → 断面5 注記 → 断面6 着色 → 照合
  各線は、先に鉛筆で始点・終点に小さな印（・）を付け、定規で結んでから油性ペンでなぞると失敗しにくい。

4. 道具とペン
  0.5mm 茶（法尻・太線）、0.3mm 茶（法肩・断面の根切り線）、0.2mm 茶（稜線・深さの境界）、0.1mm 赤（寸法・引出線・注記）、
  0.5〜0.8mm 赤（東面の親杭の通り）。塗り：黄・緑・橙・濃橙・茶（色鉛筆または蛍光ペン）。

5. 完成答案の内容（変更していない）
  掘削土量 {res.total:.3f} m³（方法A＝方法B）。深さ：FS1 GL-1650、F3・F4・F5 GL-1850、F4A GL-2100、F3A GL-2200。
  作業のゆとり 500、法幅 0.3h、余幅 a=0.5+0.3h/2（外周のみ）、東面は親杭横矢板（余幅100、法なし）。

6. 数値の出どころ
  ・このガイドの数値：完成答案（03_先生スライド準拠_断面着色修正_完成演習課題.pdf と同一の図形）のベクター座標から計算（0.1mm 単位に丸め）。
  ・図形そのものの根拠：課題PDF p.1 の実測（通り芯・基礎・梁の位置）、基礎リスト（p.5）、授業スライドの指示値（深さ・法幅・余幅）。
  ・写真から読み取った値：東面の「余幅100」「190」（授業の Y3 断面スライド）。親杭の H 記号の間隔は図示用で、ピッチの指定ではない。
  ・手順の数：平面図 {len(plan_steps)} 手順、断面図 {len(sec_steps)} 手順。
"""
    _ins(page, pymupdf.Rect(36, 60, A3[0] - 36, A3[1] - 40), txt, 10)


def _ref_page(doc, base_page, frame, mode):
    title = "平面1 基準点（印刷済みの通り芯の交点）を確認する" if mode == "plan" else "断面1 基準（通り芯と ▽GL の線）を確認する"
    page = _new(doc, title)
    clip = PLAN_CLIP if mode == "plan" else SEC_CLIP
    cv = Canvas(page, (36, 60, A3[0] - 36, 60 + (560 if mode == "plan" else 200)), base_page, clip, light=0.3)
    _refs_on(cv, frame, mode)
    k = PT2MM
    rows = []
    if mode == "plan":
        for yk in ("Y3", "Y2"):
            for a, b in zip(("X1", "X2", "X3"), ("X2", "X3", "X4")):
                rows.append([f"{a}・{yk}→{b}・{yk}", "印刷済みの交点", f"水平 {fmt((frame.X[b]-frame.X[a])*k)}mm", "実寸 5,750", "確認のみ"])
        rows.append(["X1・Y3→X1・Y2", "印刷済みの交点", f"垂直 {fmt((frame.Y['Y2']-frame.Y['Y3'])*k)}mm", "実寸 10,800", "確認のみ"])
        msg = "通り芯は一点鎖線で印刷済み。交点に鉛筆で小さく＋を付けておく（各手順の測り始めの点）。"
    else:
        for a, b in zip(("X1", "X2", "X3"), ("X2", "X3", "X4")):
            rows.append([f"{a}→{b}（GL線上）", "印刷済み", f"水平 {fmt((frame.X[b]-frame.X[a])*k)}mm", "実寸 5,750", "確認のみ"])
        msg = ("断面図の通り芯は平面図と同じ左右位置に印刷されている。▽GL の線が深さの基準。"
               f"深さの紙上距離：GL-1650＝{fmt(1650*frame.sy*k)}mm、GL-1850＝{fmt(1850*frame.sy*k)}mm、"
               f"GL-2100＝{fmt(2100*frame.sy*k)}mm、GL-2200＝{fmt(2200*frame.sy*k)}mm（GL の線から下へ）。"
               "印刷済みのフーチング下端線（F3A GL-2100、F4A GL-2000、F5 GL-1750）と、根切り底（床付け）はその 100（実寸）下。")
    y = cv.r.y1 + 10
    _ins(page, pymupdf.Rect(36, y, A3[0] - 36, y + 50), msg, 9)
    table(page, 36, y + 56, rows)


def _conversion_page(doc, frame):
    page = _new(doc, "付録 実寸 → この課題用紙の紙上 mm 換算表（印刷 100%）")
    k = PT2MM
    vals = [90, 100, 150, 190, 310, 360, 495, 500, 555, 590, 630, 660, 810, 860, 1000, 1090, 1240, 1310, 1390, 1500,
            1610, 1650, 1700, 1850, 2000, 2100, 2200, 2400, 2900, 3400, 5750, 10800, 17250]
    rows = [[f"{v:,}", f"{fmt(v*frame.sx*k)}", f"{fmt(v*frame.sy*k)}", f"{fmt(v/100)}", ""] for v in vals]
    _ins(page, pymupdf.Rect(36, 56, A3[0] - 36, 100),
         "横（東西）と縦（南北・深さ）でわずかに倍率が違う（印刷された通り芯から実測）。手順表の数値はこの倍率で計算済み。参考に正確な 1/100 の値も載せる。", 9)
    global COLS
    old = COLS
    COLS = [("実寸 mm", 90), ("紙上 横方向 mm", 120), ("紙上 縦方向 mm", 120), ("参考：1/100 の値 mm", 140), ("", 300)]
    try:
        table(page, 36, 104, rows)
    finally:
        COLS = old


def _all_table(doc, frame, mode, groups, title):
    rows = []
    for g in groups:
        rows.append([g.title, "", "", "", ""])
        rows += wrap_rows([row_text(st, frame, mode) for st in g.steps])
    i = 0
    while i < len(rows):
        page = _new(doc, title + "（一覧）")
        yy, _ = table(page, 36, 56, [], maxy=A3[1] - 30)
        y = 56
        chunk = []
        maxrows = int((A3[1] - 30 - 56 - 11) / 11.5)
        chunk = rows[i:i + maxrows]
        table(page, 36, 56, chunk, maxy=A3[1] - 30)
        i += maxrows


def build_guide(out_pdf, site, zones, res, plan_sample, sec_sample, base_pdf):
    frame = Frame(site)
    base_doc = pymupdf.open(base_pdf); base_page = base_doc[site.raw["answer_sheet"]["page_index"]]
    pprims = extract(plan_sample, base_pdf); sprims = extract(sec_sample, base_pdf)
    pg = build_plan_groups(pprims, frame); sg = build_section_groups(sprims, frame)
    plan_steps = [s for g in pg for s in g.steps]; sec_steps = [s for g in sg for s in g.steps]
    doc = pymupdf.open()
    _cover(doc, site, frame, res, plan_steps, sec_steps)
    _conversion_page(doc, frame)
    _ref_page(doc, base_page, frame, "plan")
    done = []
    for gi in range(len(pg)):
        _group_pages(doc, base_page, frame, "plan", pg, gi, done)
        if pg[gi].title.startswith("平面4"):
            pass
    _footing_details(doc, base_page, frame, site, zones, plan_steps)
    _ref_page(doc, base_page, frame, "section")
    done = []
    for gi in range(len(sg)):
        _group_pages(doc, base_page, frame, "section", sg, gi, done)
    _all_table(doc, frame, "plan", pg, "平面図 作図寸法")
    _all_table(doc, frame, "sec", sg, "Y3通り断面図 作図寸法")
    rec = reconstruct(frame, pg, sg)
    rec["cov"] = {"plan": coverage(pprims, pg), "sec": coverage(sprims, sg)}
    _verify_pages(doc, base_page, frame, pg, sg, rec, plan_sample, sec_sample)
    doc.save(out_pdf, garbage=3, deflate=True)
    return {"plan_steps": len(plan_steps), "sec_steps": len(sec_steps), "pages": doc.page_count, **rec["stats"], "coverage": rec["cov"]}


# ------------------------------------------------------------------ 手順からの再構成と照合
def reconstruct(frame, pg, sg):
    """表に書いた数値（0.1mm 丸め・基準点からの位置）だけから線の端点を作り直し、元の図形と比べる。"""
    err = []; recs = {"plan": [], "sec": []}
    for mode, groups in (("plan", pg), ("sec", sg)):
        for g in groups:
            for st in g.steps:
                if st.kind not in ("line", "point", "fill", "text"):
                    continue
                pts = st.pts
                newp = []
                for p in pts:
                    ref, dx, dy = pos(frame, mode, p)
                    q = (ref.x + dx / PT2MM, ref.y + dy / PT2MM)
                    err.append(math.dist(p, q) * PT2MM)
                    newp.append(q)
                recs[mode].append((st, newp))
    return {"recs": recs, "stats": {"max_err_mm": max(err), "mean_err_mm": sum(err) / len(err), "n_points": len(err)}}


def coverage(prims, groups):
    """見本の線がすべてどれかの手順に含まれるか。寸法線端部の斜線（各寸法の注記で指示）は別に数える。"""
    segs = []
    for g in groups:
        for st in g.steps:
            if st.kind == "line":
                if st.cls in ("labelbox", "sec_pile"):
                    (x0, y0), (x1, y1) = st.pts
                    segs += [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))]
                else:
                    segs.append(tuple(st.pts))
            elif st.kind == "mark":
                segs += [tuple(x) for x in st.pts]
    cover = unary_union([LineString(x) for x in segs]).buffer(0.06)
    lines = [p for p in prims if p.cls not in ("fill", "text", "dot")]
    miss = [p for p in lines if not cover.contains(LineString(p.pts))]
    ticks = [p for p in miss if p.cls == "dim" and math.dist(*p.pts) * PT2MM < 1.5]
    other = [p for p in miss if p not in ticks]
    texts = [p for p in prims if p.cls == "text"]
    used = {st.text for g in groups for st in g.steps if st.text}
    fills = [p for p in prims if p.cls == "fill" and p.color not in ((1.0, 1.0, 1.0),)]
    nfill = sum(1 for g in groups for st in g.steps if st.kind == "fill")
    return {"lines": len(lines), "lines_missing": len(other), "ticks_by_note": len(ticks),
            "texts": len(texts), "texts_missing": len([t for t in texts if t.text not in used]),
            "fills": len(fills), "fills_in_steps": nfill}


def _verify_pages(doc, base_page, frame, pg, sg, rec, plan_sample, sec_sample):
    page = _new(doc, "照合 ― このガイドの数値だけで描き直した図（赤）と完成見本（黒）の重ね合わせ")
    st = rec["stats"]
    _ins(page, pymupdf.Rect(36, 56, A3[0] - 36, 140),
         f"表の数値（基準点からの紙上 mm、0.1mm 単位）だけを使って全 {st['n_points']} 点を作り直し、完成見本の線の端点と比べた。"
         f"ずれは最大 {st['max_err_mm']:.3f}mm、平均 {st['mean_err_mm']:.3f}mm（0.1mm に丸めた誤差の範囲。定規の目盛の 1/2 以下）。"
         "下図は、作り直した線（赤）を完成見本の上に重ねたもの。赤が黒の線とずれなく重なっていれば一致。\n"
         + "".join(f"{nm}：見本の線 {c['lines']} 本のうち手順に含まれない線 {c['lines_missing']} 本（寸法線端部の斜線 {c['ticks_by_note']} 本は各寸法の手順の注記で指示）、"
                   f"文字 {c['texts']} 個のうち手順にない文字 {c['texts_missing']} 個、塗り {c['fills']} 範囲（親杭の塗りは手順 P の注記）。\n"
                   for nm, c in (("平面図", rec["cov"]["plan"]), ("断面図", rec["cov"]["sec"]))), 9.5)
    for mode, sample, clip, y0, h in (("plan", plan_sample, PLAN_CLIP, 146, 620), ("sec", sec_sample, SEC_CLIP, 146 + 630, 220)):
        sp = pymupdf.open(sample)[0]
        cv = Canvas(page, (36, y0, A3[0] - 36, y0 + h), sp, clip, light=0.0)
        for s, newp in rec["recs"][mode]:
            if s.kind == "line" and s.cls not in ("labelbox", "sec_pile"):
                cv.line(newp[0], newp[1], RED, 0.5)
            elif s.kind == "line":
                (x0, y0_), (x1, y1) = newp
                for a, b in (((x0, y0_), (x1, y0_)), ((x1, y0_), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0_))):
                    cv.line(a, b, RED, 0.5)
            elif s.kind == "fill":
                for a, b in zip(newp, newp[1:] + newp[:1]):
                    cv.line(a, b, RED, 0.4)
