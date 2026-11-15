"""文字列の補助関数（structlab.exam.text の再実装）。

試験対策システムの第 1・2 部（text.py など）は取得できなかった（このセッションでは元のリポジトリを読めない）ため、
第 3・4 部のコード（classify・cues・topics・questions）が呼ぶ関数だけを、同じ名前と役割で最小限に作り直した。
元の実装と細部（区切り方・用語の取り出し方・類似度の定義）が違う可能性がある。

  norm(s)          全角・半角の統一（NFKC）、空白の整理（改行は残す）
  sentences(s)     文に分ける（。！？と改行）
  formulas(s)      「記号 = 式」の形の式を取り出す
  terms(s)         用語の候補（漢字・カタカナの 2 字以上の並び、英数字の語、段階の記号 A1-A3・B1-04 など）
  top_terms(ts,k)  文の集まりで頻度の高い用語（ありふれた語を除く）
  similarity(a,b)  文字の 2-gram の Jaccard 係数（日本語で語の区切りが無くても使える）
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter

STOP = set("""する される ため こと もの よう これ それ ここ ため 場合 以下 以上 など および また ただし つまり
本章 本研究 第 章 節 図 表 式 例 値 数 量 件 回 年 点 項 行 列 個 前 後 上 下 中 間 時 他 各 全 部 的 性 化 用 表示
""".split())
TERM = re.compile(r"[A-Z]\d(?:[-‐–][A-Z]?\d+)?(?:\s*[-‐–]\s*[A-Z]\d+)?|[一-鿿々]{2,}|[゠-ヿー]{2,}|[A-Za-z][A-Za-z0-9_]{1,}")
FORMULA = re.compile(r"(?<![A-Za-z0-9_])([A-Za-zα-ωΑ-Ω][A-Za-z0-9_α-ωΑ-Ω()]*\s*[=＝]\s*[^。、\n=＝]{1,80})")


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s or "")
    s = re.sub(r"[ \t　]+", " ", s)
    return s.strip()


def sentences(s: str) -> list[str]:
    out = []
    for part in re.split(r"(?<=[。！？!?])|\n+", norm(s)):
        part = part.strip(" ・-")
        if len(part) >= 2:
            out.append(part)
    return out


def formulas(s: str) -> list[str]:
    out = []
    for m in FORMULA.finditer(norm(s)):
        f = m.group(1).strip()
        if re.search(r"[0-9A-Za-zα-ω]", f.split("=")[-1]) and f not in out:
            out.append(f)
    return out


def terms(s: str) -> list[str]:
    return [t for t in (m.group(0).strip() for m in TERM.finditer(norm(s))) if t not in STOP and len(t) >= 2]


def top_terms(texts: list[str], k: int = 8) -> list[str]:
    c = Counter()
    for t in texts:
        c.update(terms(t))
    return [w for w, _ in c.most_common(k * 3) if not w.isdigit()][:k]


def _grams(s: str) -> set[str]:
    s = re.sub(r"\s", "", norm(s).lower())
    return {s[i:i + 2] for i in range(len(s) - 1)} if len(s) >= 2 else ({s} if s else set())


def similarity(a: str, b: str) -> float:
    ga, gb = _grams(a), _grams(b)
    if not ga or not gb:
        return 0.0
    return len(ga & gb) / len(ga | gb)
