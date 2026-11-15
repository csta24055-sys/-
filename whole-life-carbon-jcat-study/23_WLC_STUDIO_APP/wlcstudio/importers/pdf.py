"""Text-layer extraction from PDF drawings/schedules (pdftotext from poppler), page by page.

Only PDFs with a digital text layer are read; scanned images are reported as 'no text layer' (image
analysis is not attempted here). Lines that look like 'name ... number unit' become candidates marked
要確認 with the page and line as trace. A candidate never becomes a value without the user's acceptance:
a number read from a drawing can be a dimension, a reference or a total, so it must be confirmed.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import unicodedata
from pathlib import Path

from ..numbers import number_or_reason

UNITS = r"(m3|㎥|m³|m2|㎡|m²|t|kg|本|台|基|個|箇所|m|ｍ|ｔ)"
# "name … number unit": the unit ends the token ("120 ㎥" at the end of a line counts: ㎥ ㎡ m³ are not word characters,
# so \b would fail). The name starts with a non-digit and may hold digits after that (鉄筋 D13, コンクリート Fc24); the
# FIRST "number unit" after it is the quantity. An item number before the name ((1), 1., 1)) is not part of it.
# A bare item number (1   コンクリート …) and a floor label at the start of the name (3F slab concrete, B1F, 2階) are
# allowed. After a match, the rest of the line is read again: a two-column schedule holds two items on one line.
LINE = re.compile(r"^(?:(?:\(\d{1,3}\)|\d{1,3}[.)]|\d{1,4}(?=\s))\s*)?"
                  r"(?P<name>(?:(?:[BRbr]?\d{1,2}[Ff]|\d{1,2}階)\s*)?[^\d\s].{0,60}?)\s+(?P<q>-?\d[\d,]*(?:\.\d+)?)\s*"
                  r"(?P<u>" + UNITS + r")(?![A-Za-z0-9])")
MAX_PER_LINE = 8
# a number with a quantity unit somewhere on a line that LINE did not read: listed, not dropped silently
LOOSE = re.compile(r"(?<![A-Za-z0-9.,])-?\d[\d,]*(?:\.\d+)?\s*(?:m3|m2|t|kg)(?![A-Za-z0-9])")
# enclosed numbers (①, ⑴, ⒈, ㉑ …) are item marks: kept as they are (NFKC would make ① a digit of the name)
_ENCLOSED = re.compile(r"[^\u2460-\u24ff\u2776-\u2793\u3251-\u325f\u32b1-\u32bf]+")


def norm_line(ln: str) -> str:
    """NFKC (ｍ³ ㎥ → m3, full-width digits) except the enclosed item numbers."""
    return _ENCLOSED.sub(lambda m: unicodedata.normalize("NFKC", m.group(0)), ln)


def available() -> bool:
    return shutil.which("pdftotext") is not None


TIMEOUT_INFO, TIMEOUT_TEXT = 10, 20      # seconds: a crafted PDF must not hold the app's only worker
MAX_TEXT_OUT = 20_000_000                 # characters of extracted text


def read(data: bytes, doc_id: str, max_pages: int = 200) -> dict:
    if not available():
        return {"format": "pdf", "pages": [], "error": "pdftotext が無いので PDF を読めない"}
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "in.pdf"
        p.write_bytes(data)
        try:
            info = subprocess.run(["pdfinfo", str(p)], capture_output=True, text=True, timeout=TIMEOUT_INFO, errors="replace")
        except subprocess.TimeoutExpired:
            return {"format": "pdf", "pages": [], "error": "PDF の情報の読み取りが時間内に終わらなかった（%d 秒）" % TIMEOUT_INFO}
        m = re.search(r"Pages:\s+(\d+)", info.stdout)
        if not m:
            return {"format": "pdf", "pages": [], "error": "PDF として開けない"}
        n = min(int(m.group(1)), max_pages)
        # one run for all pages (pages are separated by form feeds), with one time limit for the whole document
        try:
            out = subprocess.run(["pdftotext", "-layout", "-f", "1", "-l", str(n), str(p), "-"],
                                 capture_output=True, text=True, timeout=TIMEOUT_TEXT, errors="replace").stdout
        except subprocess.TimeoutExpired:
            return {"format": "pdf", "pages": [], "error": "PDF の文字の読み取りが時間内に終わらなかった（%d 秒）。数量表は CSV・Excel で読み込む"
                                                          % TIMEOUT_TEXT}
        if len(out) > MAX_TEXT_OUT:
            return {"format": "pdf", "pages": [], "error": "PDF の文字が多すぎる（%d 文字まで）" % MAX_TEXT_OUT}
        texts = out.split("\f")
        pages, cands, refused = [], [], []
        for i in range(1, n + 1):
            t = texts[i - 1] if i - 1 < len(texts) else ""
            has_text = len(t.strip()) > 20
            pages.append({"page": i, "has_text": has_text, "n_chars": len(t)})
            for k, ln in enumerate(t.splitlines(), 1):
                ln = norm_line(ln.strip()[:500])
                rest, j = ln, 0
                while rest and j < MAX_PER_LINE:
                    mm = LINE.search(rest)
                    if not mm:
                        break
                    j += 1
                    trace = "%s:p%d/L%d%s" % (doc_id, i, k, "" if j == 1 else "-%d" % j)
                    q, why = number_or_reason(mm.group("q"))
                    if q is None:            # e.g. "1,5": refused like on the screen, and said
                        refused.append({"name": mm.group("name").strip()[:80], "trace": trace,
                                        "reason": "数量 %r を読めない（%s）" % (mm.group("q")[:30], why)})
                    else:
                        cands.append({"name": mm.group("name").strip(), "quantity": q, "unit": mm.group("u"),
                                      "trace": trace, "line": ln.strip()[:120], "needs_review": True})
                    rest = rest[mm.end():].strip()
                if rest and LOOSE.search(rest):
                    refused.append({"name": rest[:80], "trace": "%s:p%d/L%d" % (doc_id, i, k),
                                    "reason": "名前と数量の並びを読めなかった行（原本で確かめて、必要なら手で入れる）"})
    no_text = [pg["page"] for pg in pages if not pg["has_text"]]
    return {"format": "pdf", "n_pages": n, "pages": pages, "candidates": cands, "refused": refused, "pages_without_text": no_text,
            "note": "PDF の文字から読んだ候補。寸法・合計・参照番号を拾うことがあるので、必ず原本で確認して採用する。"
                    + ("文字の無いページ（スキャン画像）は読んでいない：%s" % no_text[:20] if no_text else "")}
