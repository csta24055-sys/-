"""保存したHTML/Markdownから本文テキストを取り出し、抜粋照合用に正規化する（標準ライブラリのみ）。

ダウンロードした資料は信頼できないデータとして扱い、解析のみ行う（実行しない）。
"""
from __future__ import annotations

import html
import json
import re
import unicodedata
from html.parser import HTMLParser

SKIP = {"style", "noscript", "svg", "head"}


class _Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.scripts: list[str] = []
        self._skip = 0
        self._in_script = False

    def handle_starttag(self, tag, attrs):
        if tag in SKIP:
            self._skip += 1
        elif tag == "script":
            self._in_script = True
        elif tag in ("p", "br", "li", "h1", "h2", "h3", "h4", "div", "tr", "section"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in SKIP and self._skip:
            self._skip -= 1
        elif tag == "script":
            self._in_script = False

    def handle_data(self, data):
        if self._in_script:
            self.scripts.append(data)
        elif not self._skip:
            self.parts.append(data)


def extract(raw: str) -> tuple[str, str]:
    """(可視テキスト, script内テキスト) を返す。script内はNext.js等のSSRデータ用の予備。"""
    p = _Text()
    p.feed(raw)
    script = "\n".join(p.scripts)
    # JSON文字列中のエスケープ（’, \" など）を戻す
    script = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), script)
    script = script.replace('\\"', '"').replace("\\n", "\n")
    return html.unescape("".join(p.parts)), script


QUOTES = {"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-",
          " ": " ", "‑": "-", "−": "-"}


def norm(s: str) -> str:
    """照合用の正規化: NFKC・引用符/ダッシュの統一・Markdown強調/コード記号の除去・空白の圧縮・小文字化。"""
    s = unicodedata.normalize("NFKC", s)
    for a, b in QUOTES.items():
        s = s.replace(a, b)
    s = re.sub(r"[*_`]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip().lower()


def contains(haystack_norm: str, excerpt: str) -> bool:
    e = norm(excerpt)
    return bool(e) and e in haystack_norm


HEADINGS = {"h1", "h2", "h3", "h4"}


class _Sections(HTMLParser):
    """見出し（h1〜h4）ごとに本文を区切る。原文位置（どの見出しの下か）を機械的に特定するため。"""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.sections: list[list] = [["（見出し前）", []]]
        self._skip = 0
        self._head: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        if tag in SKIP or tag == "script":
            self._skip += 1
        elif tag in HEADINGS and not self._skip:
            self._head = []

    def handle_endtag(self, tag):
        if (tag in SKIP or tag == "script") and self._skip:
            self._skip -= 1
        elif tag in HEADINGS and self._head is not None:
            title = re.sub(r"\s+", " ", "".join(self._head)).strip()
            self.sections.append([title or "（無題の見出し）", []])
            self._head = None

    def handle_data(self, data):
        if self._skip:
            return
        if self._head is not None:
            self._head.append(data)
        else:
            self.sections[-1][1].append(data)


def sections(raw: str) -> list[tuple[str, str]]:
    p = _Sections()
    p.feed(raw)
    return [(h, norm(html.unescape("".join(t)))) for h, t in p.sections]


def locate(secs: list[tuple[str, str]], excerpt: str) -> str:
    """抜粋を含む見出しをすべて返す（同じ文が複数の節にある場合は「 / 」で区切る）。"""
    e = norm(excerpt)
    return " / ".join(h for h, t in secs if e and e in t)
