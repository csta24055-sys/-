"""国内外文献の書誌（Crossref）と要旨（Crossref/Semantic Scholar/OpenAlex）を取得して knowledge/literature_raw.json に保存する。
要旨が取得できない文献は『書誌のみ確認』として扱う（内容の数値は主張しない）。"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOIS = sys.argv[1:] or []


def get(url):
    r = subprocess.run(["curl", "-sS", "-m", "25", url], capture_output=True, text=True)
    try:
        return json.loads(r.stdout)
    except Exception:  # noqa: BLE001
        return None


def strip_tags(s):
    return re.sub(r"<[^>]+>", "", s or "").strip()


def main():
    out_p = ROOT / "knowledge" / "literature_raw.json"
    have = json.loads(out_p.read_text(encoding="utf-8")) if out_p.exists() else {}
    for doi in DOIS:
        key = doi.lower()
        if key in have:
            continue
        cr = get(f"https://api.crossref.org/works/{doi}")
        if not cr or "message" not in cr:
            have[key] = {"doi": doi, "error": "crossref_not_found"}
            print("NOT FOUND", doi)
            continue
        m = cr["message"]
        abstract = strip_tags(m.get("abstract"))
        source = "crossref" if abstract else None
        if not abstract:
            oa = get(f"https://api.openalex.org/works/doi:{doi}")
            if oa and oa.get("abstract_inverted_index"):
                inv = oa["abstract_inverted_index"]
                pos = sorted((p, w) for w, ps in inv.items() for p in ps)
                abstract = " ".join(w for _, w in pos)
                source = "openalex"
        have[key] = {"doi": m.get("DOI"), "title": (m.get("title") or [""])[0], "venue": (m.get("container-title") or [""])[0],
                     "year": m.get("issued", {}).get("date-parts", [[None]])[0][0],
                     "authors": [f"{a.get('family','')}, {a.get('given','')}".strip(", ") for a in m.get("author", [])][:6],
                     "volume": m.get("volume"), "page": m.get("page"), "abstract": abstract, "abstract_source": source}
        print(m.get("DOI"), "|", have[key]["year"], "|", have[key]["title"][:80], "| abs:", source)
        time.sleep(0.5)
    out_p.write_text(json.dumps(have, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
