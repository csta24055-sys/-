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
from pathlib import Path

from ..numbers import number_or_reason

UNITS = r"(m3|㎥|m³|m2|㎡|m²|t|kg|本|台|基|個|箇所|m|ｍ|ｔ)"
LINE = re.compile(r"^(?P<name>[^\d\s][^\d]{0,40}?)\s+(?P<q>-?\d[\d,]*(?:\.\d+)?)\s*(?P<u>" + UNITS + r")\b")


def available() -> bool:
    return shutil.which("pdftotext") is not None


def read(data: bytes, doc_id: str, max_pages: int = 200) -> dict:
    if not available():
        return {"format": "pdf", "pages": [], "error": "pdftotext が無いので PDF を読めない"}
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "in.pdf"
        p.write_bytes(data)
        info = subprocess.run(["pdfinfo", str(p)], capture_output=True, text=True)
        m = re.search(r"Pages:\s+(\d+)", info.stdout)
        if not m:
            return {"format": "pdf", "pages": [], "error": "PDF として開けない"}
        n = min(int(m.group(1)), max_pages)
        pages, cands, refused = [], [], []
        for i in range(1, n + 1):
            t = subprocess.run(["pdftotext", "-layout", "-f", str(i), "-l", str(i), str(p), "-"],
                               capture_output=True, text=True).stdout
            has_text = len(t.strip()) > 20
            pages.append({"page": i, "has_text": has_text, "n_chars": len(t)})
            for k, ln in enumerate(t.splitlines(), 1):
                mm = LINE.search(ln.strip())
                if mm:
                    q, why = number_or_reason(mm.group("q"))
                    if q is None:            # e.g. "1,5": refused like on the screen, and said
                        refused.append({"name": mm.group("name").strip(), "trace": "%s:p%d/L%d" % (doc_id, i, k),
                                        "reason": "数量 %r を読めない（%s）" % (mm.group("q"), why)})
                        continue
                    cands.append({"name": mm.group("name").strip(), "quantity": q, "unit": mm.group("u"),
                                  "trace": "%s:p%d/L%d" % (doc_id, i, k), "line": ln.strip()[:120], "needs_review": True})
    no_text = [pg["page"] for pg in pages if not pg["has_text"]]
    return {"format": "pdf", "n_pages": n, "pages": pages, "candidates": cands, "refused": refused, "pages_without_text": no_text,
            "note": "PDF の文字から読んだ候補。寸法・合計・参照番号を拾うことがあるので、必ず原本で確認して採用する。"
                    + ("文字の無いページ（スキャン画像）は読んでいない：%s" % no_text[:20] if no_text else "")}
