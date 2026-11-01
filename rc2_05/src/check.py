"""完成PDFの自動検査: ページ数・文字化け(グリフ欠落)・必須解答の有無・ページ外はみ出し・文字重なり・原本保持(画素比較)."""
import sys, itertools
import pymupdf, numpy as np

FONT = pymupdf.Font(fontfile='/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf')
REQUIRED = ['A = b × D = 300 × 600 = 180,000', 'Z = b·D', '18,000,000', 'M / Z = 36×10',
            'σ = − M/Z + P/A + P·e/Z', 'FPC', 'σ（引張縁） = 0', 'P = 180 kN', 'Pe = P / 0.6',
            'Pe = 300 kN', '300 / 156 = 1.92', 'N = 2 本']

def check(path, original=None, answer_rect=None):
    res, ok = [], True
    d = pymupdf.open(path); pg = d[0]
    res.append(('ページ数=1', d.page_count == 1))
    txt = pg.get_text()
    norm = txt.replace('\n', ' ').replace('\xa0', ' ').replace('･', '·').replace('\xad', '−')
    for r in REQUIRED:
        res.append((f'記入あり: {r}', r in norm))
    bad = sorted({c for c in txt if not c.isspace() and not FONT.has_glyph(ord(c)) and ord(c) > 127})
    res.append((f'グリフ欠落なし {bad}', not bad))
    res.append(('上付き記法の残骸(^{)なし', '^{' not in txt))
    res.append(('U+FFFD(文字化け)なし', '�' not in txt))
    spans = []
    for b in pg.get_text('dict')['blocks']:
        for l in b.get('lines', []):
            for s in l['spans']:
                if s['text'].strip():
                    spans.append((pymupdf.Rect(s['bbox']), s['text']))
    out = [t for r, t in spans if not pg.rect.contains(r)]
    res.append((f'ページ外はみ出しなし {out[:3]}', not out))
    ov = []
    for (r1, t1), (r2, t2) in itertools.combinations(spans, 2):
        i = r1 & r2
        if not i.is_empty and i.get_area() > 0.25 * min(r1.get_area(), r2.get_area()):
            ov.append((t1, t2))
    res.append((f'文字の重なりなし {ov[:3]}', not ov))
    if original:
        o = pymupdf.open(original)[0]
        a = np.frombuffer(o.get_pixmap(dpi=100, colorspace=pymupdf.csGRAY).samples, np.uint8).astype(int)
        b = np.frombuffer(pg.get_pixmap(dpi=100, colorspace=pymupdf.csGRAY).samples, np.uint8).astype(int)
        pix = o.get_pixmap(dpi=100); W, H = pix.width, pix.height
        a = a.reshape(H, W); b = b.reshape(H, W)
        mask = np.ones_like(a, bool)
        if answer_rect:
            k = 100 / 72; x0, y0, x1, y1 = [int(v * k) for v in answer_rect]
            mask[max(0, y0 - 2):y1 + 2, max(0, x0 - 2):x1 + 2] = False
        changed = int((np.abs(a - b) > 40)[mask].sum())
        covered = int(((a < 200) & (np.abs(a - b) > 40)).sum())   # 原本の黒画素が変化＝隠れた
        res.append((f'記入欄外の原本画素は不変 (変化{changed}px)', changed == 0))
        res.append((f'原本の線・文字を隠していない (変化{covered}px)', covered < 30))
    for name, v in res:
        print(('OK  ' if v else 'NG  ') + name); ok &= v
    print('総合:', 'PASS' if ok else 'FAIL')
    return ok

if __name__ == '__main__':
    rect = [float(v) for v in sys.argv[3:7]] if len(sys.argv) >= 7 else None
    sys.exit(0 if check(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] != '-' else None, rect) else 1)
