"""文書出力（PDF・Word）と品質検査。structlab.exam.render（試験対策システム）を教材用に改良したもの。

元の設計を引き継ぐ点: 内容をブロックの列で受け取り、見た目はここだけで決める／白背景・黒文字・日本語フォントの埋め込み／
ページ番号「- n -」／PDF と Word の両方を出し、文字化け・空ページ・期待する文・ページ番号を検査する。
改良した点:
  * 数式: 表示式（"math"）は MathML で組版した画像、文中の式（$…$）は数式用フォント（FreeSerif）の斜体・上付き・下付き
  * 図（"img"）、囲み（"note"）、見出しの番号と目次（"toc"）、表の列幅の自動調整（紙面からはみ出さない）
  * 検査は poppler（pdftotext・pdffonts・pdfinfo・pdftoppm）で行う（pymupdf がこの環境に無いため）
ブロック: {"t": "title"|"subtitle"|"h1"|"h2"|"h3"|"p"|"small"|"pre"|"list"|"olist"|"table"|"math"|"img"|"note"
           |"space"|"break"|"toc", ...}
  p/small/pre/note: text（文中の式・**太字** を含む）  list/olist: items  table: rows（1 行目が見出し）
  math: tex（表示式。label で式番号）  img: path, width_mm, caption  note: title, text
"""
from __future__ import annotations

import re
import subprocess
from html import escape
from pathlib import Path

from tex2mml import to_plain, TexError, to_rl, to_runs

FONT_DIR = "/usr/share/fonts"
JP_CANDIDATES = [
    "/usr/share/fonts/opentype/ipaexfont-gothic/ipaexg.ttf",
    "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf",
    "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf",
]
MATH_FONTS = {"MSerif": "truetype/freefont/FreeSerif.ttf", "MSerifI": "truetype/freefont/FreeSerifItalic.ttf",
              "MSerifB": "truetype/freefont/FreeSerifBold.ttf"}
_FONTS: dict | None = None
INLINE = re.compile(r"\$([^$]+)\$")
BOLD = re.compile(r"\*\*(.+?)\*\*")


def fonts() -> dict:
    global _FONTS
    if _FONTS:
        return _FONTS
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    jp = next((p for p in JP_CANDIDATES if Path(p).exists()), None)
    if jp is None:
        raise RuntimeError("日本語フォントが見つからない")
    pdfmetrics.registerFont(TTFont("JP", jp))
    for name, rel in MATH_FONTS.items():
        pdfmetrics.registerFont(TTFont(name, f"{FONT_DIR}/{rel}"))
    from reportlab.lib.fonts import addMapping
    addMapping("JP", 0, 0, "JP")
    addMapping("JP", 1, 0, "JP")     # 太字は同じ書体（IPA ゴシックに太字が無い）。見出しは大きさで区別
    addMapping("JP", 0, 1, "JP")
    addMapping("JP", 1, 1, "JP")
    _patch_cjk()
    jp_chars = set(pdfmetrics.getFont("JP").face.charToGlyph)
    ms_chars = set(pdfmetrics.getFont("MSerif").face.charToGlyph)
    _FONTS = {"jp": "JP", "jp_path": jp, "jp_chars": jp_chars, "ms_chars": ms_chars}
    return _FONTS


MISSING: set[str] = set()   # どちらのフォントにも無い文字（品質検査で問題にする）

CANNOT_END = set("（「『〔［【〈《([{")


def _patch_cjk() -> None:
    """ReportLab の和文の行分割に禁則処理を足す（元の処理はそのまま使い、行の境目だけを直す）。
    - 行頭禁則の文字（、。）」など）が続くときは 2 文字まで前の行にぶら下げる（元の処理は 1 文字だけ）
    - 行末禁則の文字（（「『〔 など）で行が終わるときは、その文字を次の行へ送る
    複数の飾りを持つ段落（cjkFragSplit）と、飾りの無い段落（wordSplit）の両方に効かせる。
    文中の上付き・下付きの位置も、行に収まるよう浅くする。"""
    import inspect
    from reportlab.lib import textsplit as TS
    from reportlab.platypus import paragraph as P
    from reportlab.platypus import paraparser as PP
    PP.subFraction = 0.25
    PP.supFraction = 0.38
    if getattr(P, "_wlc_patched", False):
        return
    src = inspect.getsource(P.cjkFragSplit)
    key = "            lines.append(makeCJKParaLine(U[lineStartPos:i],maxWidth,widthUsed,extraSpace,lineBreak,calcBounds))"
    assert key in src, "ReportLab の版が違う"
    fix = (
        "            if not lineBreak:\n"
        "                _h = 0\n"
        "                while i < nU and U[i] in ALL_CANNOT_START and _h < 2:\n"
        "                    extraSpace -= float(getattr(U[i].width, 'normalizedValue', lambda m: U[i].width)(maxWidth)) if hasattr(U[i].width, 'normalizedValue') else U[i].width\n"
        "                    i += 1\n"
        "                    _h += 1\n"
        "                if i - 1 > lineStartPos + 1 and str(U[i - 1]) in _CANNOT_END:\n"
        "                    i -= 1\n"
        "                    extraSpace += U[i].width if not hasattr(U[i].width, 'normalizedValue') else 0\n")
    src = src.replace(key, fix + key)
    ns = dict(P.__dict__)
    ns["_CANNOT_END"] = CANNOT_END
    exec(compile(src, "<cjkFragSplit+kinsoku>", "exec"), ns)
    P.cjkFragSplit = ns["cjkFragSplit"]

    orig_ws = P.wordSplit

    def word_split(word, maxWidths, fontName, fontSize, encoding="utf8"):
        lines = orig_ws(word, maxWidths, fontName, fontSize, encoding)
        if len(lines) < 2 or not all(isinstance(t, str) for _, t in lines):
            return lines
        texts = [t for _, t in lines]
        for k in range(len(texts) - 1):
            moved = 0
            while texts[k + 1] and texts[k + 1][0] in P.ALL_CANNOT_START and moved < 2:
                texts[k] += texts[k + 1][0]
                texts[k + 1] = texts[k + 1][1:]
                moved += 1
            if len(texts[k]) > 2 and texts[k][-1] in CANNOT_END:
                texts[k + 1] = texts[k][-1] + texts[k + 1]
                texts[k] = texts[k][:-1]
        out = []
        for k, t in enumerate(texts):
            if not t:
                continue
            mw = maxWidths[min(k, len(maxWidths) - 1)] if isinstance(maxWidths, (list, tuple)) else maxWidths
            out.append([mw - sum(TS.getCharWidths(t, fontName, fontSize)), t])
        return out

    P.wordSplit = word_split
    P._wlc_patched = True


def _font_runs(text: str) -> str:
    """日本語フォントに無い文字（≥ ⇔ など）を数式用フォントに切り替える。どちらにも無い文字は MISSING に記録。"""
    F = fonts()
    out, cur, buf = [], None, []

    def flush():
        if buf:
            seg = escape("".join(buf), quote=False).replace("\n", "<br/>")
            out.append(f'<font name="MSerif">{seg}</font>' if cur == "ms" else seg)
            buf.clear()
    for ch in text:
        cp = ord(ch)
        if ch == "\n" or cp in F["jp_chars"]:
            kind = "jp"
        elif cp in F["ms_chars"]:
            kind = "ms"
        else:
            kind = "jp"
            MISSING.add(ch)
        if kind != cur:
            flush()
            cur = kind
        buf.append(ch)
    flush()
    return "".join(out)


# ---------------------------------------------------------------- inline text → reportlab markup
def _tokens(text: str) -> list[tuple[str, str, bool]]:
    """文を（種類 't' か 'm'、中身、強調か）の列に分ける。**…** は式をまたいでもよい。"""
    out, pos, bold = [], 0, False

    def plain(seg: str):
        nonlocal bold
        seg = seg.replace("`", "")
        for k, piece in enumerate(seg.split("**")):
            if k:
                bold = not bold
            if piece:
                out.append(("t", piece, bold))
    for m in INLINE.finditer(text):
        plain(text[pos:m.start()])
        out.append(("m", m.group(1), bold))
        pos = m.end()
    plain(text[pos:])
    return out


def rl_markup(text: str) -> str:
    """文中の $…$ を数式の飾りに、**…** を強調（薄い灰色の背景）に。それ以外は XML の特殊文字を逃がす。"""
    out = []
    for kind, s_, bold in _tokens(text):
        if kind == "t":
            piece = _font_runs(s_)
        else:
            try:
                piece = to_rl(s_)
            except TexError as e:
                raise TexError(f"文中の式 ${s_}$ : {e}") from None
        out.append(f'<font backColor="#eeeeee">{piece}</font>' if bold else piece)
    return "".join(out)


def _note_parts(b: dict) -> list[dict]:
    """囲みの中身（mdparse の parts。古い形の text・items も受け付ける）。"""
    if "parts" in b:
        return b["parts"]
    parts = [{"k": "p", "text": t} for t in str(b.get("text", "")).split("\n\n") if t.strip()]
    return parts + [{"k": "li", "text": it} for it in b.get("items", [])]


# ---------------------------------------------------------------- PDF
def _ends_with_break(story) -> bool:
    from reportlab.platypus import PageBreak, Spacer
    for fl in reversed(story):
        if isinstance(fl, Spacer):
            continue
        return isinstance(fl, PageBreak)
    return False


def to_pdf(blocks: list[dict], path: Path, title: str, header: str = "", math_png: dict | None = None,
           toc: bool = False) -> Path:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (BaseDocTemplate, Frame, Image, KeepTogether, PageBreak, PageTemplate,
                                    Paragraph, Spacer, Table, TableStyle)
    from reportlab.platypus.tableofcontents import TableOfContents
    f = fonts()["jp"]
    math_png = math_png or {}
    st = {
        "title": ParagraphStyle("title", fontName=f, fontSize=20, leading=28, alignment=TA_CENTER, spaceAfter=10),
        "subtitle": ParagraphStyle("subtitle", fontName=f, fontSize=11, leading=17, alignment=TA_CENTER, spaceAfter=6),
        "h1": ParagraphStyle("h1", fontName=f, fontSize=15, leading=21, spaceBefore=6, spaceAfter=8, keepWithNext=1),
        "h2": ParagraphStyle("h2", fontName=f, fontSize=12.5, leading=18, spaceBefore=10, spaceAfter=4, keepWithNext=1),
        "h3": ParagraphStyle("h3", fontName=f, fontSize=11, leading=16, spaceBefore=7, spaceAfter=2, keepWithNext=1),
        "p": ParagraphStyle("p", fontName=f, fontSize=10, leading=16.5, wordWrap="CJK"),
        "small": ParagraphStyle("small", fontName=f, fontSize=8.5, leading=13, wordWrap="CJK", textColor=colors.HexColor("#333333")),
        "pre": ParagraphStyle("pre", fontName=f, fontSize=9.5, leading=15, wordWrap="CJK", leftIndent=10),
        "li": ParagraphStyle("li", fontName=f, fontSize=10, leading=16, wordWrap="CJK", leftIndent=14, bulletIndent=3,
                             bulletFontName=f),
        "cell": ParagraphStyle("cell", fontName=f, fontSize=8.8, leading=13, wordWrap="CJK"),
        "cellh": ParagraphStyle("cellh", fontName=f, fontSize=8.8, leading=13, wordWrap="CJK"),
        "note": ParagraphStyle("note", fontName=f, fontSize=9.6, leading=15.5, wordWrap="CJK"),
        "noteh": ParagraphStyle("noteh", fontName=f, fontSize=9.8, leading=15),
        "cap": ParagraphStyle("cap", fontName=f, fontSize=8.8, leading=13, alignment=TA_CENTER, wordWrap="CJK"),
    }
    frame_w = A4[0] - 36 * mm

    class Doc(BaseDocTemplate):
        def afterFlowable(self, fl):
            if isinstance(fl, Paragraph) and getattr(fl, "_toc", None) is not None:
                lvl, txt = fl._toc
                key = f"h{id(fl)}"
                self.canv.bookmarkPage(key)
                olvl = min(lvl, getattr(self, "_olvl", -1) + 1)   # しおりは一段ずつしか深くできない
                self._olvl = olvl
                self.canv.addOutlineEntry(txt, key, level=olvl, closed=olvl > 0)
                self.notify("TOCEntry", (lvl, txt, self.page, key))

    story = []
    if toc:
        pass
    for b in blocks:
        t = b["t"]
        if t in ("title", "subtitle", "h1", "h2", "h3", "p", "small", "pre"):
            if t == "h1" and story and not b.get("nobreak") and not _ends_with_break(story):
                story.append(PageBreak())
            para = Paragraph(rl_markup(b.get("text", "")), st[t])
            if t in ("h1", "h2") and b.get("toc", True):
                para._toc = (0 if t == "h1" else 1, re.sub(r"\$([^$]+)\$", lambda m: m.group(1), b.get("text", "")))
            story.append(para)
        elif t in ("list", "olist"):
            for i, it in enumerate(b["items"], 1):
                bullet = f"{i}." if t == "olist" else "・"
                story.append(Paragraph(rl_markup(it), st["li"], bulletText=bullet))
        elif t == "table":
            rows = b["rows"]
            ncol = max(len(r) for r in rows)
            rows = [r + [""] * (ncol - len(r)) for r in rows]
            widths = b.get("widths_mm")
            if widths:
                cw = [w * mm for w in widths]
            else:  # 文字数に応じた幅（最小 12%）
                def _vis(c):   # 式は組んだ後の長さで数える
                    return len(re.sub(r"\$([^$]*)\$", lambda m_: to_plain(m_.group(1)), str(c)))
                lens = [max(min(_vis(r[j]), 60) for r in rows) + 4 for j in range(ncol)]
                tot = sum(lens)
                cw = [max(frame_w * 0.12, frame_w * x / tot) for x in lens]
                k = frame_w / sum(cw)
                cw = [c * k for c in cw]
            data = [[Paragraph(rl_markup(str(c)), st["cellh" if i == 0 else "cell"]) for c in r] for i, r in enumerate(rows)]
            tb = Table(data, repeatRows=1, colWidths=cw)
            tb.setStyle(TableStyle([("FONTNAME", (0, 0), (-1, -1), f), ("GRID", (0, 0), (-1, -1), 0.4, colors.black),
                                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#efefef")),
                                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                                    ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4)]))
            story.append(tb)
        elif t == "math":
            png, w, h = math_png[b["tex"]]
            scale = min(1.0, (frame_w - 30) / w)
            img = Image(str(png), width=w * scale, height=h * scale)
            if b.get("label"):
                row = Table([["", img, Paragraph(f'<font name="MSerif">({escape(b["label"])})</font>', st["p"])]],
                            colWidths=[28, frame_w - 56, 28])
                row.setStyle(TableStyle([("FONTNAME", (0, 0), (-1, -1), f), ("ALIGN", (1, 0), (1, 0), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
                story.append(row)
            else:
                img.hAlign = "CENTER"
                story.append(img)
        elif t == "img":
            from reportlab.lib.utils import ImageReader
            iw, ih = ImageReader(str(b["path"])).getSize()
            w = min(frame_w, b.get("width_mm", 160) * mm)
            img = Image(str(b["path"]), width=w, height=w * ih / iw)
            img.hAlign = "CENTER"
            parts = [img]
            if b.get("caption"):
                parts.append(Paragraph(rl_markup(b["caption"]), st["cap"]))
            story.append(KeepTogether(parts))
        elif t == "note":
            inner = []
            if b.get("title"):
                inner.append(Paragraph(rl_markup(b["title"]), st["noteh"]))
            for part in _note_parts(b):
                if part["k"] == "p":
                    inner.append(Paragraph(rl_markup(part["text"]), st["note"]))
                elif part["k"] == "li":
                    inner.append(Paragraph(rl_markup(part["text"]), st["li"], bulletText="・"))
                else:
                    png, w, h = math_png[part["tex"]]
                    sc = min(1.0, (frame_w - 40) / w)
                    im = Image(str(png), width=w * sc, height=h * sc)
                    im.hAlign = "CENTER"
                    inner.append(im)
            box = Table([[inner]], colWidths=[frame_w])
            box.setStyle(TableStyle([("FONTNAME", (0, 0), (-1, -1), f), ("BOX", (0, 0), (-1, -1), 0.7, colors.black),
                                     ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f6f6f6")),
                                     ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                                     ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
            story.append(box)
        elif t == "space":
            n = int(b.get("lines", 4))
            box = Table([[""]] * n, colWidths=[frame_w], rowHeights=[8 * mm] * n)
            box.setStyle(TableStyle([("FONTNAME", (0, 0), (-1, -1), f), ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.grey),
                                     ("BOX", (0, 0), (-1, -1), 0.6, colors.black)]))
            story.append(KeepTogether([box]))
        elif t == "break":
            story.append(PageBreak())
        elif t == "toc":
            tocf = TableOfContents()
            tocf.levelStyles = [ParagraphStyle("t0", fontName=f, fontSize=10.5, leading=17, leftIndent=0),
                                ParagraphStyle("t1", fontName=f, fontSize=9.2, leading=14, leftIndent=14)]
            story.append(Paragraph("目次", st["h1"]))
            story.append(tocf)
            story.append(PageBreak())
        else:
            raise ValueError(f"知らないブロック {t}")
        story.append(Spacer(1, 3 if t in ("list", "olist", "p") else 6))

    def footer(c, d):
        c.saveState()
        c.setFont(f, 8)
        c.drawCentredString(A4[0] / 2, 10 * mm, f"- {d.page} -")
        if header:
            c.drawString(18 * mm, A4[1] - 11 * mm, header)
            c.setLineWidth(0.3)
            c.line(18 * mm, A4[1] - 12.5 * mm, A4[0] - 18 * mm, A4[1] - 12.5 * mm)
        c.restoreState()

    path.parent.mkdir(parents=True, exist_ok=True)
    import functools
    from reportlab.pdfgen.canvas import Canvas
    doc = Doc(str(path), pagesize=A4, title=title, author="", leftMargin=18 * mm, rightMargin=18 * mm,
              topMargin=18 * mm, bottomMargin=18 * mm)
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="f")
    doc.addPageTemplates([PageTemplate(id="p", frames=[frame], onPage=footer)])
    doc.multiBuild(story, canvasmaker=functools.partial(Canvas, initialFontName=f, initialFontSize=10))
    return path


# ---------------------------------------------------------------- Word
def _add_runs(par, text: str, size=None):
    from docx.oxml.ns import qn
    from docx.shared import Pt
    for kind, s, bold in _tokens(text):
        if kind == "t":
            r = par.add_run(s)
            r.bold = bold
            if size:
                r.font.size = Pt(size)
        else:
            for txt, italic, v, mbold in to_runs(s):
                r = par.add_run(txt)
                r.font.name = "FreeSerif"
                r._element.rPr.rFonts.set(qn("w:ascii"), "FreeSerif")
                r._element.rPr.rFonts.set(qn("w:hAnsi"), "FreeSerif")
                r.italic = italic
                r.bold = bold or mbold
                if v == "sub":
                    r.font.subscript = True
                elif v == "sup":
                    r.font.superscript = True
                if size:
                    r.font.size = Pt(size)


def to_docx(blocks: list[dict], path: Path, title: str, math_png: dict | None = None) -> Path:
    import docx
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Mm, Pt
    math_png = math_png or {}
    d = docx.Document()
    sec = d.sections[0]
    sec.page_width, sec.page_height = Mm(210), Mm(297)
    sec.left_margin = sec.right_margin = sec.top_margin = sec.bottom_margin = Mm(18)
    style = d.styles["Normal"]
    style.font.name = "IPAGothic"
    style.element.rPr.rFonts.set(qn("w:eastAsia"), "IPAゴシック")
    style.font.size = Pt(10.5)
    for hs in ("Title", "Heading 1", "Heading 2", "Heading 3"):
        s = d.styles[hs]
        s.font.name = "IPAGothic"
        s.element.rPr.rFonts.set(qn("w:eastAsia"), "IPAゴシック")
        s.font.color.rgb = None
    d.core_properties.title = title
    # ページ番号（フッターに PAGE フィールド）
    fp = sec.footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fp.add_run("- ")
    run = fp.add_run()
    for tag, txt in (("begin", None), (None, "PAGE"), ("end", None)):
        if tag:
            el = OxmlElement("w:fldChar")
            el.set(qn("w:fldCharType"), tag)
        else:
            el = OxmlElement("w:instrText")
            el.set(qn("xml:space"), "preserve")
            el.text = txt
        run._r.append(el)
    fp.add_run(" -")
    first_h1 = True
    for b in blocks:
        t = b["t"]
        if t == "title":
            p = d.add_heading(level=0)
            _add_runs(p, b["text"])
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif t == "subtitle":
            p = d.add_paragraph()
            _add_runs(p, b["text"])
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif t in ("h1", "h2", "h3"):
            if t == "h1" and not first_h1 and not b.get("nobreak"):
                d.add_page_break()
            first_h1 = first_h1 and t != "h1"
            p = d.add_heading(level=int(t[1]))
            _add_runs(p, b["text"])
        elif t in ("p", "pre", "small"):
            p = d.add_paragraph()
            _add_runs(p, b["text"], size=8.5 if t == "small" else None)
        elif t in ("list", "olist"):
            for it in b["items"]:
                p = d.add_paragraph(style="List Number" if t == "olist" else "List Bullet")
                _add_runs(p, it)
        elif t == "table":
            rows = b["rows"]
            ncol = max(len(r) for r in rows)
            tb = d.add_table(rows=len(rows), cols=ncol)
            tb.style = "Table Grid"
            tb.alignment = WD_TABLE_ALIGNMENT.CENTER
            for i, r in enumerate(rows):
                for j in range(ncol):
                    cell = tb.cell(i, j)
                    cell.paragraphs[0].text = ""
                    _add_runs(cell.paragraphs[0], str(r[j]) if j < len(r) else "", size=9)
        elif t == "math":
            png, w, h = math_png[b["tex"]]
            p = d.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            wpt = min(w, 470)
            p.add_run().add_picture(str(png), width=Pt(wpt))
            if b.get("label"):
                p.add_run(f"　({b['label']})")
        elif t == "img":
            p = d.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.add_run().add_picture(str(b["path"]), width=Mm(min(170, b.get("width_mm", 160))))
            if b.get("caption"):
                c = d.add_paragraph()
                c.alignment = WD_ALIGN_PARAGRAPH.CENTER
                _add_runs(c, b["caption"], size=9)
        elif t == "note":
            tb = d.add_table(rows=1, cols=1)
            tb.style = "Table Grid"
            cell = tb.cell(0, 0)
            shd = OxmlElement("w:shd")
            shd.set(qn("w:val"), "clear")
            shd.set(qn("w:fill"), "F2F2F2")
            cell._tc.get_or_add_tcPr().append(shd)
            first = True
            if b.get("title"):
                _add_runs(cell.paragraphs[0], b["title"])
                for r in cell.paragraphs[0].runs:
                    r.bold = True
                first = False
            for part in _note_parts(b):
                p = cell.paragraphs[0] if first else cell.add_paragraph()
                first = False
                if part["k"] == "p":
                    _add_runs(p, part["text"], size=9.5)
                elif part["k"] == "li":
                    _add_runs(p, "・" + part["text"], size=9.5)
                else:
                    png, w, h = math_png[part["tex"]]
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    p.add_run().add_picture(str(png), width=Pt(min(w, 450)))
            d.add_paragraph()
        elif t == "space":
            for _ in range(int(b.get("lines", 4))):
                d.add_paragraph("_" * 60)
        elif t == "break":
            d.add_page_break()
        elif t == "toc":
            p = d.add_paragraph()
            r = p.add_run()
            for tag, txt in (("begin", None), (None, 'TOC \\o "1-2" \\h \\z \\u'), ("separate", None), ("end", None)):
                if tag:
                    el = OxmlElement("w:fldChar")
                    el.set(qn("w:fldCharType"), tag)
                else:
                    el = OxmlElement("w:instrText")
                    el.set(qn("xml:space"), "preserve")
                    el.text = txt
                r._r.append(el)
            d.add_paragraph("（目次は Word で開いたあと「フィールドの更新」で表示されます）")
            d.add_page_break()
    path.parent.mkdir(parents=True, exist_ok=True)
    d.save(str(path))
    return path


# ---------------------------------------------------------------- checks
def check_pdf(path: Path, expect: list[str] = (), render_dir: Path | None = None, render_pages: list[int] = (),
              header: str = "") -> dict:
    """PDF の品質検査: 開けるか・各ページに文字があるか・置換文字（文字化け）・期待する文・各ページのページ番号・
    フォントの埋め込み。render_pages のページは画像にして目で確かめるために保存する。"""
    res = {"file": path.name, "ok": True, "problems": []}
    try:
        info = subprocess.run(["pdfinfo", str(path)], capture_output=True, text=True, check=True).stdout
    except Exception as e:  # noqa: BLE001
        return {"file": path.name, "ok": False, "problems": [f"開けない: {e}"]}
    pages = int(re.search(r"Pages:\s+(\d+)", info).group(1))
    res["pages"] = pages
    texts = []
    for i in range(1, pages + 1):
        texts.append(subprocess.run(["pdftotext", "-f", str(i), "-l", str(i), "-layout", str(path), "-"],
                                    capture_output=True, text=True).stdout)
    fonts_out = subprocess.run(["pdffonts", str(path)], capture_output=True, text=True).stdout.splitlines()[2:]
    not_emb = [ln.split()[0] for ln in fonts_out if ln.strip() and re.search(r"\s(no)\s+(yes|no)\s+(yes|no)\s+\d+\s+\d+\s*$", ln)]
    res["fonts"] = sorted({ln.split()[0] for ln in fonts_out if ln.strip()})
    if not_emb:
        used = _glyphs_in_fonts(path, set(not_emb))
        if used:
            res["problems"].append(f"埋め込まれていないフォントで描いた文字がある {used}")
        else:
            res["note"] = f"参照だけで文字を描いていないフォント {sorted(set(not_emb))}（reportlab が既定で置く）"
    if not pages:
        res["problems"].append("ページが無い")
    body = [re.sub(r"-\s*\d+\s*-", "", t.replace(header, "") if header else t).strip() for t in texts]
    empty = [i + 1 for i, t in enumerate(body) if len(t) < 3]
    if empty:
        res["problems"].append(f"本文の無いページ {empty}")
    allt = "".join(texts)
    if "�" in allt:
        res["problems"].append("置換文字（文字化け）がある")
    lines_ = [ln.strip() for t in texts for ln in t.splitlines() if ln.strip()]
    bad_start = [ln[:20] for ln in lines_ if ln[0] in "、。，．"]
    bad_end = [ln[-20:] for ln in lines_ if ln[-1] in "（「『〔［【"]
    res["kinsoku"] = {"line_start": len(bad_start), "line_end": len(bad_end)}
    if bad_start or bad_end:   # 和文の禁則（行頭の句読点、行末の開き括弧）
        res["problems"].append(f"禁則の違反：行頭の句読点 {len(bad_start)}、行末の開き括弧 {len(bad_end)}（例 {(bad_start + bad_end)[:2]}）")
    flat = re.sub(r"\s", "", allt)
    missing = [e for e in expect if re.sub(r"\s", "", e) not in flat]
    if missing:
        res["problems"].append(f"期待する文が見つからない: {missing[:3]}")
    nopage = [i + 1 for i, t in enumerate(texts) if f"- {i + 1} -" not in t]
    if nopage:
        res["problems"].append(f"ページ番号が無いページ {nopage[:10]}")
    if render_dir is not None and render_pages:
        render_dir.mkdir(parents=True, exist_ok=True)
        for pg in render_pages:
            if 1 <= pg <= pages:
                subprocess.run(["pdftoppm", "-f", str(pg), "-l", str(pg), "-r", "70", "-png", str(path),
                                str(render_dir / f"{path.stem}_p{pg}")], check=False)
    res["ok"] = not res["problems"]
    return res


def _glyphs_in_fonts(path: Path, base_names: set[str]) -> dict:
    """埋め込まれていないフォント（BaseFont 名）で、実際に文字を描く命令（Tj・TJ・'・"）があるページと回数。"""
    import pypdf
    from pypdf.generic import ContentStream
    r = pypdf.PdfReader(str(path))
    out = {}
    for i, pg in enumerate(r.pages, 1):
        fonts = pg.get("/Resources", {}).get("/Font", {})
        keys = {k for k in fonts if str(fonts[k].get_object().get("/BaseFont", "")).lstrip("/") in base_names}
        if not keys:
            continue
        cur, n = None, 0
        for operands, op in ContentStream(pg.get_contents(), r).operations:
            if op == b"Tf":
                cur = str(operands[0])
            elif op in (b"Tj", b"TJ", b"'", b'"') and cur in keys:
                n += 1
        if n:
            out[i] = n
    return out


def check_docx(path: Path, expect: list[str] = (), n_images: int | None = None) -> dict:
    import docx
    try:
        d = docx.Document(str(path))
    except Exception as e:  # noqa: BLE001
        return {"file": path.name, "ok": False, "problems": [f"開けない: {e}"]}
    text = "\n".join(p.text for p in d.paragraphs) + "\n".join(
        c.text for t in d.tables for r in t.rows for c in r.cells)
    flat = re.sub(r"\s", "", text)
    missing = [e for e in expect if re.sub(r"\s", "", e) not in flat]
    probs = [f"期待する文が見つからない: {missing[:3]}"] if missing else []
    if "�" in text:
        probs.append("置換文字（文字化け）がある")
    imgs = len(d.inline_shapes)
    if n_images is not None and imgs != n_images:
        probs.append(f"画像（式・図）の数が違う: {imgs}（期待 {n_images}）")
    return {"file": path.name, "ok": not probs, "problems": probs, "images": imgs}
