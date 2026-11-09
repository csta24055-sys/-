"""漏えい検査パターンの一元管理。

公開リポジトリなので、個人名などの具体的な検査語はここに書かない。
- 一般パターン（下の GENERIC）: 接続情報・住宅記号など、書いても情報を漏らさないもの
- 非公開パターン: private_data/privacy_patterns.txt（gitignore 済み）または
  環境変数 AQROS_PRIVACY_PATTERNS（CI ではリポジトリの Secrets から渡す。改行または | 区切り）
"""
from __future__ import annotations

import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_FILE = ROOT / "private_data" / "privacy_patterns.txt"

GENERIC = [
    r"amazonaws\.com", r"\bec2-\d", r"(?i:passw(?:or)?d)\s*[=:]\s*\S+", r"(?i:ftp)://\S+",
    r"(?<![A-Za-z])[IWKST]邸",                       # 2023年度住宅の記号（姓の頭文字の可能性）→ 住宅23-n に置換して公開
    r"[A-Za-z0-9._%+-]+@(?!example\.)[A-Za-z0-9.-]+\.(?:ac\.jp|co\.jp|com|net|org|jp)\b",
]


def private_patterns() -> list[str]:
    pats: list[str] = []
    env = os.environ.get("AQROS_PRIVACY_PATTERNS", "")
    if env:
        pats += [p for p in re.split(r"[\n|]", env) if p.strip()]
    if PRIVATE_FILE.exists():
        pats += [ln.strip() for ln in PRIVATE_FILE.read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.startswith("#")]
    return pats


def regex(include_generic: bool = True) -> str:
    pats = (GENERIC if include_generic else []) + private_patterns()
    return "|".join(f"(?:{p})" for p in pats)


def has_private_list() -> bool:
    return bool(private_patterns())
