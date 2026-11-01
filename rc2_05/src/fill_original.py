"""原本「05_課題＋解答用紙.pdf」（/Rotate 90 の横向き1ページ）の各空欄へ解答を記入する。
座標はすべて画面表示上（842×595 pt, 左上原点）の値で指定し、derotation_matrix で PDF 座標へ変換する。
使い方: python fill_original.py 05_課題＋解答用紙.pdf RC2_05_Answer.pdf
"""
import re, sys
import pymupdf

FONT = '/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf'
F = pymupdf.Font(fontfile=FONT)
INK = (0.0, 0.12, 0.45)        # 記入（濃紺）
ANS = (0.80, 0.0, 0.0)         # 最終解答（赤）
SUP = re.compile(r'\^\{([^}]*)\}')

def runs(t):
    out, i = [], 0
    for m in SUP.finditer(t):
        if m.start() > i: out.append((t[i:m.start()], False))
        out.append((m.group(1), True)); i = m.end()
    if i < len(t): out.append((t[i:], False))
    return out

def width(t, fs):
    return sum(F.text_length(r, fontsize=fs * (0.62 if s else 1)) for r, s in runs(t))

class Writer:
    def __init__(self, page):
        self.p = page; self.m = page.derotation_matrix; self.rot = page.rotation
        page.insert_font(fontname='jp', fontfile=FONT)
        self.placed = []          # 画面座標での記入矩形（重なり検査用）

    def text(self, x, y, t, fs, color=INK, box=False, limit=None):
        """(x, y)=画面座標のベースライン左端。limit を超えるなら fs を縮小."""
        if limit:
            while width(t, fs) > limit - x and fs > 8: fs -= 0.25
        x0 = x
        for r, s in runs(t):
            f = fs * (0.62 if s else 1)
            pt = pymupdf.Point(x, y - (fs * 0.38 if s else 0)) * self.m
            self.p.insert_text(pt, r, fontname='jp', fontsize=f, color=color, rotate=self.rot)
            x += F.text_length(r, fontsize=f)
        rect = pymupdf.Rect(x0, y - fs * 0.88, x, y + fs * 0.12)
        if box:
            b = rect + (-3, -2, 3, 3)
            self.p.draw_rect(b * self.m, color=ANS, width=1.0)
            rect = b
        self.placed.append((rect, t, fs))
        return rect


def fill(src, out):
    doc = pymupdf.open(src); page = doc[0]
    assert page.rotation == 90 and abs(page.rect.width - 842) < 1, '想定外のページ形式'
    w = Writer(page)
    # ---- 必要プレストレス力 P ----
    w.text(551, 240, 'P・100/(300・600^{2}/6)', 17, limit=835)                         # 式の続き
    w.text(424, 268, '引張縁 σ = 0　→　−2.0 + P/(1.8×10^{5}) + P/(1.8×10^{5}) = 0', 14, limit=835)
    w.text(304, 290, '2P/(1.8×10^{5}) = 2.0　より', 14)
    w.text(312, 312, '1.8×10^{5} N = 180 kN', 17, color=ANS, box=True)
    w.text(300, 335, '（P/A = 1.0 N/mm^{2}，P・e/Z = 1.0 N/mm^{2}）', 12.5, limit=620)
    # ---- 応力度図の値 ----
    w.text(248, 508.5, '= 1.0', 13.5)                     # P/A
    w.text(387, 508.5, '= 1.0', 13.5)                     # P・e/Z
    w.text(548, 412, '= 0', 13.5)                       # σcp−σcpe（上縁）
    w.text(543, 487, '= 2.0', 13.5)                     # σcp＋σcpe（下縁）
    # ---- 必要導入張力 Pe ----
    w.text(664, 370, 'P/0.6 = 180/0.6', 16)
    w.text(680, 388, '= 300 kN', 15, color=ANS, box=True)
    # ---- 必要本数 N ----
    w.text(660, 430, 'Pe/Fy = 300/156', 16)
    w.text(672, 452, '= 1.92 → 2 本', 16, color=ANS, box=True)
    w.text(660, 470, '（12.7φ 降伏荷重 Fy = 156 kN/本）', 10.5)
    # ---- 下部余白：合成応力度の確認 ----
    w.text(24, 556, '確認（PS力 P = 180 kN 作用時）', 12)
    w.text(24, 575, '引張縁：−2.0 + 1.0 + 1.0 = 0（引張応力なし → FPC成立）　圧縮縁：+2.0 + 1.0 − 1.0 = +2.0 N/mm^{2}', 12, limit=600)
    w.text(598, 556, 'σcp − σcpe = 1.0 − 1.0 = 0', 12)
    w.text(598, 575, 'σcp ＋ σcpe = 1.0 ＋ 1.0 = 2.0 N/mm^{2}', 12, limit=836)
    doc.save(out, garbage=3, deflate=True)
    return w.placed

if __name__ == '__main__':
    import json
    placed = fill(sys.argv[1], sys.argv[2])
    for r, t, fs in placed: print([round(v) for v in r], fs, t)
    json.dump([[list(r), t, fs] for r, t, fs in placed],
              open(sys.argv[2].replace('.pdf', '_placed.json'), 'w'), ensure_ascii=False)
