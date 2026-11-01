"""解答用紙PDFの作成（PyMuPDF）。
  build  : 課題条件から独立した1ページ解答用紙を作成（原本PDF未入手時の版）
  fill   : 原本「05_課題＋解答用紙.pdf」の空白領域を画像解析で検出し、解答を書き込む
使い方: python sheet.py build out.pdf
        python sheet.py fill 05_課題＋解答用紙.pdf RC2_05_Answer.pdf [x0 y0 x1 y1]
"""
import json, sys, os, re
import pymupdf
import numpy as np

FONT = '/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf'
INK = (0.05, 0.15, 0.55)      # 記入文字（濃紺）
BLK = (0, 0, 0)
HERE = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(os.path.join(HERE, '..', 'out', 'calc.json')))

# 解答行: (種別, テキスト)  種別 h=見出し, f=式, a=答（枠付き）, n=注記
ANSWER = [
    ('h', '① 断面積'),
    ('f', 'A = b × D = 300 × 600 = 180,000 mm^{2}  (= 1.8×10^{5} mm^{2})'),
    ('h', '② 断面係数'),
    ('f', 'Z = b·D^{2} / 6 = 300 × 600^{2} / 6 = 18,000,000 mm^{3}  (= 1.8×10^{7} mm^{3})'),
    ('h', '③ 荷重による引張縁（下縁）の曲げ応力度'),
    ('f', 'M / Z = 36×10^{6} N·mm / 1.8×10^{7} mm^{3} = 2.0 N/mm^{2}  （下縁で引張）'),
    ('h', '④ プレストレスによる応力度の計算式（圧縮を＋、下縁＝引張縁）'),
    ('f', 'σ = − M/Z + P/A + P·e/Z      （P：有効プレストレス力，e：偏心距離）'),
    ('f', 'σ = − 2.0 + P / 180,000 + P × 100 / 18,000,000   [N/mm^{2}]'),
    ('f', '   = − 2.0 + P / 180,000 + P / 180,000'),
    ('h', 'FPC条件（フルプレストレッシング：引張縁に引張応力を生じさせない）'),
    ('f', 'σ（引張縁） = 0  とする'),
    ('h', '⑤ 必要プレストレス力 P（有効プレストレス力）'),
    ('f', '− 2.0 + 2P / 180,000 = 0  →  P = 2.0 × 90,000 = 180,000 N'),
    ('a', 'P = 180 kN     （P/A = 1.0 N/mm^{2}，P·e/Z = 1.0 N/mm^{2}）'),
    ('h', '⑥ 必要導入張力 Pe（有効プレストレス力 = 導入張力 × 0.6）'),
    ('f', 'Pe = P / 0.6 = 180 / 0.6'),
    ('a', 'Pe = 300 kN'),
    ('h', '⑦ 必要PC鋼材本数 N（12.7φ 1本あたり 156 kN）'),
    ('f', 'N = Pe / 156 = 300 / 156 = 1.92  →  切り上げ'),
    ('a', 'N = 2 本'),
    ('n', '確認：上縁 σ = +2.0 + 1.0 − 1.0 = +2.0 N/mm^{2}（圧縮），下縁 σ = 0 → FPC条件を満足'),
]


def _lines_height(fs):
    h = 0
    for k, _ in ANSWER:
        h += fs * (1.75 if k == 'a' else 1.45 if k == 'h' else 1.4)
    return h


def draw_answer(page, rect, fs=None):
    """rect内に解答行を描く。fsは収まる最大サイズを自動選択（上限10.5pt）。描いた枠のリストを返す."""
    page.insert_font(fontname='jp', fontfile=FONT)
    if fs is None:
        fs = 12.0
        while fs > 6 and (_lines_height(fs) > rect.height - 6 or
                          max(pymupdf.get_text_length(t, fontname='helv', fontsize=fs) * 1.05
                              for _, t in ANSWER) * 0 + _maxw(fs) > rect.width - 10):
            fs -= 0.25
    y = rect.y0 + fs + 3
    x = rect.x0 + 5
    boxes = []
    for k, t in ANSWER:
        if k == 'h':
            y += fs * 0.12
            put(page, (x, y), t, fs * 0.92, BLK)
            y += fs * 1.33
        elif k == 'f':
            put(page, (x + fs, y), t, fs, INK)
            y += fs * 1.4
        elif k == 'a':
            w = _tw(t, fs * 1.05) + 10
            box = pymupdf.Rect(x + fs - 4, y - fs * 1.05, x + fs - 4 + w, y + fs * 0.38)
            page.draw_rect(box, color=(0.75, 0.05, 0.05), width=0.9)
            put(page, (x + fs + 1, y), t, fs * 1.05, (0.75, 0.05, 0.05))
            boxes.append(box)
            y += fs * 1.75
        else:
            put(page, (x + fs, y), t, fs * 0.88, INK)
            y += fs * 1.4
    return fs, y


_FONTOBJ = pymupdf.Font(fontfile=FONT)
_SUP = re.compile(r'\^\{([^}]*)\}')
def _runs(t):
    """'10^{5}' → [('10',False),('5',True)]"""
    out, i = [], 0
    for m in _SUP.finditer(t):
        if m.start() > i: out.append((t[i:m.start()], False))
        out.append((m.group(1), True)); i = m.end()
    if i < len(t): out.append((t[i:], False))
    return out
def _tw(t, fs):
    return sum(_FONTOBJ.text_length(r, fontsize=fs * (0.62 if sup else 1)) for r, sup in _runs(t))
def put(page, pos, t, fs, color=BLK):
    x, y = pos
    for r, sup in _runs(t):
        f = fs * (0.62 if sup else 1)
        page.insert_text((x, y - (fs * 0.38 if sup else 0)), r, fontname='jp', fontsize=f, color=color)
        x += _FONTOBJ.text_length(r, fontsize=f)
    return x
def _maxw(fs):
    return max(_tw(t, fs * (1.05 if k == 'a' else 1.0)) + fs + 10 for k, t in ANSWER)


def draw_section(page, ox, oy, s):
    """断面図（300×600, PC鋼材を図心下100mm）。s: pt/mm."""
    w, h = 300 * s, 600 * s
    r = pymupdf.Rect(ox, oy, ox + w, oy + h)
    page.draw_rect(r, color=BLK, width=1.0, fill=(0.93, 0.93, 0.93))
    cy = oy + h / 2
    page.draw_line((ox - 6, cy), (ox + w + 6, cy), color=(0.4, 0.4, 0.4), width=0.5, dashes='[3 2] 0')
    ty = cy + 100 * s
    page.draw_circle((ox + w / 2, ty), 3.2, color=BLK, fill=BLK)
    fs = 7.5
    page.insert_text((ox + w + 8, cy + 2.5), '図心', fontname='jp', fontsize=fs)
    page.insert_text((ox + w + 8, ty + 2.5), 'PC鋼材', fontname='jp', fontsize=fs)
    # e寸法
    xd = ox + w * 0.18
    page.draw_line((xd, cy), (xd, ty), color=INK, width=0.7)
    for yy in (cy, ty):
        page.draw_line((xd - 3, yy), (xd + 3, yy), color=INK, width=0.7)
    page.insert_text((xd + 3, (cy + ty) / 2 + 3), 'e=100', fontname='jp', fontsize=fs, color=INK)
    # b, D
    page.insert_text((ox + w / 2 - 10, oy + h + 11), 'b=300', fontname='jp', fontsize=fs)
    page.insert_text((ox - 9, oy + h / 2 + 30), 'D=600', fontname='jp', fontsize=fs, rotate=90)
    page.insert_text((ox, oy - 4), '断面（単位 mm）', fontname='jp', fontsize=fs)


def draw_stress(page, ox, oy, hh, ww):
    """応力度分布図: −M/Z, P/A, P·e/Z, 合計（圧縮＋を右側）."""
    fs = 7
    sc = ww / 2 / 3.0       # pt per N/mm^{2}
    items = [('−M/Z', (2.0, -2.0)), ('P/A', (1.0, 1.0)), ('P·e/Z', (-1.0, 1.0)), ('合計 σ', (2.0, 0.0))]
    x = ox
    for i, (name, (top, bot)) in enumerate(items):
        cx = x + ww / 2
        page.draw_line((cx, oy), (cx, oy + hh), color=BLK, width=0.8)
        pts = [(cx, oy), (cx + top * sc, oy), (cx + bot * sc, oy + hh), (cx, oy + hh)]
        page.draw_polyline(pts + [pts[0]], color=INK, width=0.7, fill=(0.82, 0.87, 0.97), closePath=True)
        page.insert_text((x + 2, oy - 4), name, fontname='jp', fontsize=fs)
        lab = lambda v: ('0' if v == 0 else f'{v:+.1f}'.replace('-', '−'))
        def tag(v, yy):
            t = lab(v); w = _FONTOBJ.text_length(t, fontsize=fs)
            xx = cx + v * sc + 2 if v > 0 else (cx + v * sc - w - 2 if v < 0 else cx + 3)
            page.insert_text((xx, yy), t, fontname='jp', fontsize=fs, color=INK)
        tag(top, oy + 3); tag(bot, oy + hh + 2)
        if i < 3:
            page.insert_text((x + ww + 1, oy + hh / 2 + 3), '=' if i == 2 else '+', fontname='jp', fontsize=9)
        x += ww + 10
    put(page, (ox, oy + hh + 14), '上：上縁　下：下縁（引張縁）　単位 N/mm^{2}　圧縮を＋', 6.5)


def build(out):
    doc = pymupdf.open()
    page = doc.new_page(width=595.28, height=841.89)  # A4
    page.insert_font(fontname='jp', fontfile=FONT)
    M = 42
    page.insert_text((M, 50), '鉄筋コンクリート構造Ⅱ　第5回 演習課題　解答用紙', fontname='jp', fontsize=13.5)
    page.insert_text((330, 74), '学籍番号', fontname='jp', fontsize=9)
    page.insert_text((450, 74), '氏名', fontname='jp', fontsize=9)
    page.draw_line((372, 76), (440, 76), width=0.5); page.draw_line((472, 76), (553, 76), width=0.5)
    # 問題
    q = pymupdf.Rect(M, 86, 595.28 - M, 168)
    page.draw_rect(q, color=BLK, width=0.6)
    qt = ['【課題】 幅 300 mm × せい 600 mm の長方形断面梁に，設計曲げモーメント M = 36 kN·m が作用する。',
          'PC鋼材（12.7φ）を偏心距離 e = 100 mm で配置し，フルプレストレッシング（FPC）とする。',
          '有効プレストレス力は導入張力の 60 % とする。次を求めよ。',
          '　① 断面積 A　② 断面係数 Z　③ 曲げ応力度 M/Z　④ プレストレスによる応力度',
          '　⑤ 必要プレストレス力 P　⑥ 必要導入張力 Pe　⑦ 必要PC鋼材本数 N（12.7φ：156 kN/本）']
    for i, t in enumerate(qt):
        page.insert_text((q.x0 + 6, q.y0 + 15 + i * 14.5), t, fontname='jp', fontsize=8.8)
    # 図
    draw_section(page, M + 24, 192, 0.17)
    draw_stress(page, M + 150, 197, 102, 74)
    # 解答欄
    a = pymupdf.Rect(M, 335, 595.28 - M, 805)
    page.draw_rect(a, color=BLK, width=0.6)
    page.insert_text((a.x0 + 4, a.y0 - 4), '【解答】', fontname='jp', fontsize=9.5)
    fs, yend = draw_answer(page, a)
    doc.save(out, garbage=4, deflate=True)
    return dict(fs=fs, answer_rect=list(a), y_end=yend)


def find_blank(page, min_w=260, min_h=200, dpi=72):
    """レンダリング画像から最大の空白矩形（白画素のみ）を探す（ヒストグラム法）."""
    pix = page.get_pixmap(dpi=dpi, colorspace=pymupdf.csGRAY)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width)
    white = img > 245
    H, W = white.shape
    heights = np.zeros(W, dtype=int)
    best = (0, None)
    for y in range(H):
        heights = np.where(white[y], heights + 1, 0)
        stack = []
        for x in range(W + 1):
            h = heights[x] if x < W else 0
            start = x
            while stack and stack[-1][1] >= h:
                s, sh = stack.pop()
                area = sh * (x - s)
                if area > best[0] and (x - s) >= min_w and sh >= min_h:
                    best = (area, (s, y - sh + 1, x, y + 1))
                start = s
            stack.append((start, h))
    if best[1] is None:
        return None
    k = 72 / dpi
    x0, y0, x1, y1 = best[1]
    return pymupdf.Rect(x0 * k, y0 * k, x1 * k, y1 * k) + (4, 4, -4, -4)


def fill(src, out, rect=None):
    doc = pymupdf.open(src)
    page = doc[0]
    r = pymupdf.Rect(rect) if rect else find_blank(page)
    if r is None:
        raise SystemExit('空白領域が見つかりません。x0 y0 x1 y1 を指定してください。')
    fs, yend = draw_answer(page, r)
    if doc.page_count > 1:
        doc.select([0])
    doc.save(out, garbage=4, deflate=True)
    return dict(fs=fs, answer_rect=list(r), y_end=yend)


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'build':
        print(build(sys.argv[2]))
    else:
        rect = [float(v) for v in sys.argv[4:8]] if len(sys.argv) >= 8 else None
        print(fill(sys.argv[2], sys.argv[3], rect))
