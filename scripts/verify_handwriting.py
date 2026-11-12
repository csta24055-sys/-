"""手書き見本 ①② が完成答案と同じ内容か（線の位置・文字・塗り）を検証する。

  python scripts/verify_handwriting.py
線の太さだけが違ってよい（ペン幅に置き換えたため）。
"""
import sys
from pathlib import Path
import pymupdf
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from yamadome import config  # noqa: E402

site = config.load(ROOT / "config/site.yaml")
ans = ROOT / "output/yamadome_20261021" / site.raw["answer_sheet"]["output_name"]
hw = ROOT / "output/yamadome_20261021/handwriting"
base = ROOT / site.raw["answer_sheet"]["pdf"]
SEC_Y = (845, 1000)   # 断面図の範囲（pt）


def geo(page, nbase):
    out = []
    for d in page.get_drawings()[nbase:]:
        pts = []
        for it in d["items"]:
            for v in it[1:]:
                if hasattr(v, "x"):
                    pts.append((round(v.x, 2), round(v.y, 2)))
                elif hasattr(v, "x0"):
                    pts += [(round(v.x0, 2), round(v.y0, 2)), (round(v.x1, 2), round(v.y1, 2))]
                elif hasattr(v, "ul"):
                    pts += [(round(p.x, 2), round(p.y, 2)) for p in (v.ul, v.ur, v.lr, v.ll)]
        col = tuple(round(c, 3) for c in d["color"]) if d.get("color") else None
        fil = tuple(round(c, 3) for c in d["fill"]) if d.get("fill") else None
        out.append((col, fil, tuple(pts)))
    return out


def words(page):
    return sorted((round(w[0], 1), round(w[1], 1), w[4]) for w in page.get_text("words"))


nb = len(pymupdf.open(base)[0].get_drawings())
A = pymupdf.open(ans)[0]
ga = geo(A, nb)
in_sec = lambda g: g[2] and all(SEC_Y[0] <= y <= SEC_Y[1] for _, y in g[2])
ok = True
for name, sel in (("02_手書き見本_根切り平面図.pdf", lambda g: not in_sec(g)), ("03_手書き見本_Y3通り断面図.pdf", in_sec)):
    S = pymupdf.open(hw / name)
    gs = geo(S[0], nb)
    want = sorted((g for g in ga if sel(g)), key=repr)
    got = sorted(gs, key=repr)
    same_geo = want == got
    wa = [w for w in words(A) if (SEC_Y[0] <= w[1] <= SEC_Y[1]) == (name.startswith("03"))]
    ws = words(S[0])
    base_w = words(pymupdf.open(base)[0])
    add = sorted(set(ws) - set(base_w)); want_w = sorted(set(wa) - set(base_w))
    if name.startswith("02"):
        want_w = [w for w in want_w if not (w[1] > 1060 and "Σ" in w[2] or w[2].startswith("方法") or w[2].startswith("余幅\xa0="))]
    same_txt = set(want_w) <= set(add)
    widths = sorted({round(d.get("width") or 0, 2) for d in S[0].get_drawings()[nb:] if d.get("color")})
    print(f"{name}: ページ {len(S)}・{S[0].rect.width:.0f}×{S[0].rect.height:.0f}pt(A3)  図形 {len(got)}（完成答案と位置・色が一致: {same_geo}）"
          f"  文字 {len(add)}（完成答案の文字を含む: {same_txt}）  線の太さ {widths} pt = 最細 {min(widths)*25.4/72:.2f}mm")
    ok &= same_geo and same_txt and S[0].rect == A.rect and min(widths) >= 0.35
print("総合:", "完成答案と内容一致" if ok else "不一致あり")
sys.exit(0 if ok else 1)
