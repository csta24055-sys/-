"""共通ユーティリティ。

再利用: math_interop_v0/phase1.py の canonical()/digest()/require() を
そのまま import する（同モジュールは標準ライブラリのみに依存し、
既存の厳密JSON正規化・SHA-256指紋の挙動を研究台帳でも共有するため）。
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "math_interop_v0"))
import phase1  # noqa: E402  (再利用: 既存の検証済みヘルパー)

canonical = phase1.canonical
digest = phase1.digest
require = phase1.require

DEFAULT_ROOT = REPO / "AI_WORLD_PRIMARY_RESEARCH"


def research_root() -> Path:
    return Path(os.environ.get("AI_RESEARCH_ROOT", DEFAULT_ROOT)).resolve()


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as fh:
        return [dict(r) for r in csv.DictReader(fh)]


def write_csv(path: Path, header: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=header, extrasaction="raise", lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in header})
    os.replace(tmp, path)


def atomic_write(path: Path, text: str) -> None:
    """途中停止しても半端なファイルを残さない（途中再開の前提）。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def write_json(path: Path, obj) -> None:
    atomic_write(path, json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def read_json(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def dropbox_content_hash(path: Path) -> str:
    """Dropbox公式 content_hash（4 MiBブロックごとのSHA-256を連結しSHA-256）。"""
    blocks = []
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(4 * 1024 * 1024), b""):
            blocks.append(hashlib.sha256(chunk).digest())
    return hashlib.sha256(b"".join(blocks)).hexdigest()
