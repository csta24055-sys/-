"""原本へ記入した提出用PDFの自動検査.
使い方: python check_original.py 原本.pdf RC2_05_Answer.pdf RC2_05_Answer_placed.json"""
import sys, json, itertools
import pymupdf, numpy as np
FONT = pymupdf.Font(fontfile='/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf')
REQ = ['P・100/(300・600', 'σ = 0', '180 kN', 'P/0.6 = 180/0.6', '300 kN', '300/156', '1.92', '2 本',
       'P/A = 1.0', 'P・e/Z = 1.0', 'FPC成立']
ORIG_TEXT = ['演習課題：プレストレストコンクリート梁の設計', 'σ = －M/Z ＋P/A ＋P・e/Z', '＜必要導入張力＞',
             '＜必要本数＞', '有効PS力はPC鋼材の降伏荷重の0.6倍', 'PSによる', '断面の応力状態']

def main(orig, filled, placed_json):
    res = []
    o, f = pymupdf.open(orig), pymupdf.open(filled)
    pg = f[0]
    res.append(('1ページ', f.page_count == 1))
    res.append(('ページ寸法・回転が原本と同一', pg.rect == o[0].rect and pg.rotation == o[0].rotation))
    txt = pg.get_text().replace('\xa0', ' ').replace('･', '・').replace('\n', ' ')
    for r in REQ: res.append((f'記入あり: {r}', r in txt))
    for r in ORIG_TEXT: res.append((f'原本文字保持: {r}', r in txt))
    bad = sorted({c for c in txt if ord(c) > 127 and not c.isspace() and not FONT.has_glyph(ord(c))})
    res.append((f'記入文字のグリフ欠落なし {bad}', not bad))   # 原本フォント分も含め検査（原本は埋込みフォント）
    res.append(('上付き記法の残骸なし', '^{' not in txt and '�' not in txt))
    placed = [(pymupdf.Rect(r), t) for r, t, _ in json.load(open(placed_json))]
    vis = pymupdf.Rect(0, 0, 842, 595.2)
    res.append(('記入がページ内', all(vis.contains(r) for r, _ in placed)))
    ov = [(a[1], b[1]) for a, b in itertools.combinations(placed, 2) if not (a[0] & b[0]).is_empty and (a[0] & b[0]).get_area() > 1]
    res.append((f'記入どうしの重なりなし {ov}', not ov))
    # 原本の文字・図形と記入矩形の重なり（原本テキスト行の画面座標）
    m = o[0].rotation_matrix
    otext = [(pymupdf.Rect(l['bbox']) * m, ''.join(s['text'] for s in l['spans']))
             for b in o[0].get_text('dict')['blocks'] for l in b.get('lines', [])]
    hit = [(t, ot) for r, t in placed for orr, ot in otext if (r & orr).get_area() > 4]
    res.append((f'原本の文字と重ならない {hit[:4]}', not hit))
    # 画素比較
    dpi = 100; k = dpi / 72
    A = np.frombuffer(o[0].get_pixmap(dpi=dpi, colorspace=pymupdf.csGRAY).samples, np.uint8)
    pix = f[0].get_pixmap(dpi=dpi, colorspace=pymupdf.csGRAY)
    B = np.frombuffer(pix.samples, np.uint8)
    A = A.reshape(pix.height, pix.width).astype(int); B = B.reshape(pix.height, pix.width).astype(int)
    diff = np.abs(A - B) > 40
    mask = np.ones_like(diff)
    for r, _ in placed:
        x0, y0, x1, y1 = int(r.x0 * k) - 3, int(r.y0 * k) - 4, int(r.x1 * k) + 3, int(r.y1 * k) + 4
        mask[max(0, y0):y1, max(0, x0):x1] = False
    outside = int((diff & mask).sum())
    covered = int((diff & (A < 160)).sum())
    res.append((f'記入箇所以外の原本画素は不変（変化 {outside} px）', outside == 0))
    res.append((f'原本の線・文字・図を塗りつぶしていない（原本の濃色画素の変化 {covered} px）', covered < 25))
    ok = True
    for n, v in res: print(('OK  ' if v else 'NG  ') + n); ok &= v
    print('総合:', 'PASS' if ok else 'FAIL'); return ok

if __name__ == '__main__':
    sys.exit(0 if main(*sys.argv[1:4]) else 1)
