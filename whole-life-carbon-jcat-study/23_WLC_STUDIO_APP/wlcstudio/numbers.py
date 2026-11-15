"""Reading a number written by a person (screen input, a quantity table cell, a PDF line) — one rule everywhere.

- Full-width digits, signs and points are read (NFKC); the minus sign U+2212 is a minus.
- A comma is only a thousands separator: "12,500" and "1,234.5" are read; "1,5" or "12,50" (a decimal comma or a typo)
  are refused instead of silently becoming 15 or 1250.
- Spaces inside a number are refused ("1 5" is not 15); spaces around it are ignored.
- Only finite numbers; ASCII digits after normalisation (other scripts' digits are refused).
"""
from __future__ import annotations

import math
import re
import unicodedata

_THOUSANDS = re.compile(r"[+-]?\d{1,3}(?:,\d{3})+(?:\.\d+)?", re.ASCII)
_PLAIN = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", re.ASCII)
MAX_TEXT = 100                                   # a number is never longer than this


def parse_number(x) -> float:
    """The number, or ValueError with the reason (in Japanese, shown to the user)."""
    if isinstance(x, bool):
        raise ValueError("数値として読めない")
    if isinstance(x, (int, float)):
        try:
            f = float(x)
        except OverflowError:
            raise ValueError("大きすぎて数値として扱えない") from None
        if not math.isfinite(f):
            raise ValueError("有限の数値で入れる")
        return f
    t = unicodedata.normalize("NFKC", str(x)[:MAX_TEXT + 50]).strip().replace("−", "-")
    if len(t) > MAX_TEXT:
        raise ValueError("数値として長すぎる")
    if re.search(r"\s", t):
        raise ValueError("数の中に空白がある（3 桁の区切りはカンマ）")
    if "," in t:
        if not _THOUSANDS.fullmatch(t):
            raise ValueError("カンマは 3 桁ごとの区切りだけに使う（小数点はピリオド）")
        t = t.replace(",", "")
    if not _PLAIN.fullmatch(t):
        raise ValueError("数値として読めない")
    f = float(t)
    if not math.isfinite(f):
        raise ValueError("有限の数値で入れる")
    return f


def number_or_reason(x) -> tuple[float | None, str | None]:
    """(number, None) or (None, reason); an empty cell is (None, None)."""
    if x is None or (isinstance(x, str) and not x.strip()):
        return None, None
    try:
        return parse_number(x), None
    except ValueError as e:
        return None, str(e)
