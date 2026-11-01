"""課題PDFの読み取り（テキスト・ベクター・高解像度画像化）と解答欄への書き込み。"""
from __future__ import annotations
import json
from pathlib import Path
import pymupdf

PT_PER_MM = 72 / 25.4


def render_pages(pdf, out_dir, dpi=400):
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    with pymupdf.open(pdf) as doc:
        for i, page in enumerate(doc):
            p = out_dir / f"page{i+1:02d}_{dpi}dpi.png"
            page.get_pixmap(dpi=dpi).save(p)
            paths.append(p)
    return paths


def dump_text_and_vectors(pdf, out_json):
    """各ページのテキスト（座標付き）と線分数を出力。寸法の根拠調査用。"""
    data = []
    with pymupdf.open(pdf) as doc:
        for i, page in enumerate(doc):
            words = [dict(text=w[4], bbox=[round(v, 1) for v in w[:4]]) for w in page.get_text("words")]
            data.append(dict(page=i + 1, size_pt=[page.rect.width, page.rect.height],
                             size_mm=[round(page.rect.width / PT_PER_MM, 1), round(page.rect.height / PT_PER_MM, 1)],
                             n_drawings=len(page.get_drawings()), words=words))
    Path(out_json).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    return data


def fill_answer_sheet(src_pdf, out_pdf, page_index, items):
    """items: [(kind, rect_pt[x0,y0,x1,y1], payload)] kind = 'pdf' (ベクター図) | 'text'。
    元ページの内容は残し、指定矩形にのみ重ねる。"""
    doc = pymupdf.open(src_pdf)
    page = doc[page_index]
    for kind, rect, payload in items:
        r = pymupdf.Rect(*rect)
        if kind == "pdf":
            with pymupdf.open(payload) as fig:
                page.show_pdf_page(r, fig, 0, keep_proportion=True)
        elif kind == "text":
            page.insert_textbox(r, payload, fontsize=9, fontname="japan", color=(0.75, 0, 0))
    doc.save(out_pdf, garbage=3, deflate=True)
    doc.close()


def compare_outside_boxes(src_pdf, out_pdf, page_index, boxes_pt, dpi=150):
    """解答欄以外の画素が変わっていないか（欠落チェック）。変化画素率を返す。"""
    import numpy as np
    def arr(p):
        with pymupdf.open(p) as d:
            pix = d[page_index].get_pixmap(dpi=dpi)
            return np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
    a, b = arr(src_pdf), arr(out_pdf)
    mask = np.ones(a.shape[:2], bool)
    k = dpi / 72
    for x0, y0, x1, y1 in boxes_pt:
        mask[int(y0 * k):int(y1 * k) + 1, int(x0 * k):int(x1 * k) + 1] = False
    diff = (np.abs(a.astype(int) - b.astype(int)).sum(axis=2) > 30) & mask
    return diff.sum() / mask.sum()
