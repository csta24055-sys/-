"""手書き作図用の見本（①平面図・②Y3断面図）と、作図ガイド（③）のための要素抽出。

方針（図面の中身は変えない）:
- 見本は完成答案と同じ描画コード（answer_sheet）で描き、線の太さだけをペン幅に置き換える。
- ガイドの数値は、見本PDFに実際に描かれたベクター図形の座標から求める（手入力・推測なし）。
"""
from __future__ import annotations
from dataclasses import dataclass, field
import pymupdf
from . import answer_sheet as A
from .pdf_tools import _font

PT2MM = 25.4 / 72.0                      # 紙上 1pt = 0.3528 mm（A3 を「実際のサイズ」で印刷した場合）

# 手書き用のペン幅（pt）。値は分類のため互いに異なる値にしている
HAND_STYLE = {
    "bottom": 1.42,      # 法尻（根切り底の外形）  0.5 mm ペン
    "top": 0.86,         # 法肩                     0.3 mm ペン
    "ridge": 0.57,       # 稜線（角の斜線）         0.2 mm ペン
    "border": 0.58,      # 深さの境界（内部の段差） 0.2 mm ペン
    "pile": 1.80,        # 親杭の通り               0.5〜0.8 mm ペン
    "hmark": 0.60,       # 親杭の H 記号            0.2 mm ペン
    "dim": 0.35,         # 寸法線                   0.1 mm ペン
    "leader": 0.40,      # 引出線                   0.1 mm ペン
    "labelbox": 0.45,    # 深さ表示の枠             0.1 mm ペン
    "sec_outline": 0.84, # 断面の根切り線           0.3 mm ペン
    "sec_pile": 0.50,    # 断面の親杭               0.2 mm ペン
    "plan_fill_opacity": 0.40,
    "sec_fill_opacity": 0.55,
}
PEN = {"bottom": "0.5mm 茶（太）", "top": "0.3mm 茶（中）", "ridge": "0.2mm 茶（細）", "border": "0.2mm 茶（細）",
       "pile": "0.5〜0.8mm 赤（太）", "hmark": "0.2mm 赤", "dim": "0.1mm 赤", "leader": "0.1mm 赤",
       "labelbox": "0.1mm 赤", "sec_outline": "0.3mm 茶", "sec_pile": "0.2mm 赤"}
NAME = {"bottom": "法尻（根切り底の外形）", "top": "法肩", "ridge": "稜線", "border": "深さの境界（内部の段差）",
        "pile": "親杭の通り（東面）", "hmark": "親杭の H 記号", "dim": "寸法線", "leader": "引出線",
        "labelbox": "深さ表示の枠", "sec_outline": "根切り線（断面）", "sec_pile": "親杭（断面）"}


def _with_style(style):
    old = dict(A.STYLE)
    A.STYLE.update(style)
    return old


def make_samples(site, zones, res, src_pdf, out_plan, out_sec):
    """①平面図見本・②断面図見本（いずれも A3 縦 1 ページ目＝課題用紙そのままの位置）を作る。"""
    old = _with_style(HAND_STYLE)
    try:
        for kind, out in (("plan", out_plan), ("section", out_sec)):
            doc = pymupdf.open(src_pdf)
            doc.select([site.raw["answer_sheet"]["page_index"]])      # 1ページ目だけ（下地）
            page = doc[0]
            fn = _font(page)
            m = A.Mapper(site)
            if kind == "plan":
                A.draw_plan(page, fn, site, zones, m)
                A.legend(page, fn, m)
                r = pymupdf.Rect(*site.raw["answer_sheet"]["volume_text_at"])
                page.insert_textbox(r, f"{res.total:,.2f}", fontsize=12, fontname=fn, color=A.RED,
                                    align=pymupdf.TEXT_ALIGN_CENTER)
                A.formula_note(page, fn, res)
            else:
                A.draw_section(page, fn, site, zones, m)
            doc.save(out, garbage=3, deflate=True)
            doc.close()
    finally:
        A.STYLE.clear(); A.STYLE.update(old)


# ---------------------------------------------------------------- 要素の抽出
@dataclass
class Prim:
    cls: str                      # bottom/top/ridge/... /fill/text
    pts: list                     # [(x_pt, y_pt), ...] 線は2点、塗りは多角形
    color: tuple = ()
    text: str = ""
    size: float = 0.0
    extra: dict = field(default_factory=dict)


def _cls_of(d):
    w = round(d.get("width") or 0, 2)
    if d.get("color") is None:
        return "fill"
    for k, v in HAND_STYLE.items():
        if not k.endswith("opacity") and abs(v - w) < 0.005:
            return k
    return f"w{w}"


def _subpaths(d):
    """図形を部分経路（点列, 閉じているか）に分解。'l' の連続・'qu'（四辺形）・'re'（矩形）に対応。"""
    out, cur = [], []
    for it in d["items"]:
        if it[0] == "l":
            p, q = (it[1].x, it[1].y), (it[2].x, it[2].y)
            if cur and (abs(cur[-1][0] - p[0]) + abs(cur[-1][1] - p[1]) > 0.01):
                out.append((cur, bool(d.get("closePath")), False)); cur = []
            if not cur:
                cur.append(p)
            cur.append(q)
        else:
            if cur:
                out.append((cur, bool(d.get("closePath")), False)); cur = []
            if it[0] == "qu":
                qd = it[1]; out.append(([(qd.ul.x, qd.ul.y), (qd.ur.x, qd.ur.y), (qd.lr.x, qd.lr.y), (qd.ll.x, qd.ll.y)], True, False))
            elif it[0] == "re":
                r = it[1]; out.append(([(r.x0, r.y0), (r.x1, r.y0), (r.x1, r.y1), (r.x0, r.y1)], True, False))
            elif it[0] == "c":
                out.append(([(it[1].x, it[1].y), (it[4].x, it[4].y)], False, True))
    if cur:
        out.append((cur, bool(d.get("closePath")), False))
    return out


def extract(sample_pdf, base_pdf, page_index=0):
    """見本PDFに追加された図形・文字を、下地（課題用紙）との差分として取り出す。
    返す要素: 線分（cls=線の種類, pts=2点 [pt]）、塗り（cls='fill', pts=多角形）、文字（cls='text'）。"""
    s = pymupdf.open(sample_pdf)[0]
    b = pymupdf.open(base_pdf)[page_index]
    bd = b.get_drawings()
    sd = s.get_drawings()
    assert len(sd) >= len(bd)
    prims = []
    for di, d in enumerate(sd[len(bd):]):
        subs = _subpaths(d)
        if d.get("fill") is not None:
            for pts, _, cv in subs:
                if len(pts) >= 3 and not cv:
                    prims.append(Prim("fill", pts, tuple(round(v, 3) for v in d["fill"]),
                                      extra={"opacity": d.get("fill_opacity"), "stroke": d.get("color") is not None, "did": di}))
        if d.get("color") is None:
            continue
        c = _cls_of(d)
        curve = any(it[0] == "c" for it in d["items"])
        for pts, closed, cv in subs:
            if cv:
                continue                                    # 引出線の端の黒丸（円）は dot として別に扱う
            segs = list(zip(pts, pts[1:])) + ([(pts[-1], pts[0])] if closed and len(pts) > 2 else [])
            for p, q in segs:
                if abs(p[0] - q[0]) + abs(p[1] - q[1]) > 0.01:
                    prims.append(Prim(c, [p, q], tuple(round(v, 3) for v in d["color"]),
                                      extra={"fill": d.get("fill"), "dot": curve, "did": di}))
        if curve:
            xs = [it[1].x for it in d["items"] if it[0] == "c"]; ys = [it[1].y for it in d["items"] if it[0] == "c"]
            prims.append(Prim("dot", [((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)], tuple(d["color"]), extra={"did": di}))
    base_spans = set()
    for blk in b.get_text("dict")["blocks"]:
        for ln in blk.get("lines", []):
            for sp in ln["spans"]:
                base_spans.add((sp["text"], tuple(round(v, 1) for v in sp["bbox"])))
    for blk in s.get_text("dict")["blocks"]:
        for ln in blk.get("lines", []):
            for sp in ln["spans"]:
                key = (sp["text"], tuple(round(v, 1) for v in sp["bbox"]))
                if key in base_spans or not sp["text"].strip():
                    continue
                x0, y0, x1, y1 = sp["bbox"]
                prims.append(Prim("text", [(x0, y0), (x1, y1)], text=sp["text"].replace("\xad", "-").replace("\xa0", " "),
                                  size=sp["size"], extra={"dir": ln.get("dir")}))
    return prims
