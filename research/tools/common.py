"""Shared helpers for the company-first shosha research repository.

All paths are resolved relative to the ``research/`` directory so the tools can be
run from anywhere (``python3 research/tools/xxx.py``). Tests point ``RESEARCH_ROOT``
at a temporary copy to exercise failure cases without touching the real data.
"""
from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import Iterable

ROOT = Path(os.environ.get("RESEARCH_ROOT", Path(__file__).resolve().parents[1]))
AS_OF = "2026-11-01"  # fixed initial snapshot date (研究基準日)
ASOF_SNAPSHOT = f"asof_{AS_OF}"

TOPIC_STATES = ("NOT_STARTED", "IN_PROGRESS", "PASS", "BLOCKED")
APPLICABILITY = ("APPLICABLE", "NOT_APPLICABLE", "UNKNOWN")
CLAIM_TYPES = ("FACT", "PARTY_CLAIM", "ANALYSIS", "HYPOTHESIS", "FORECAST", "UNKNOWN")
CLAIM_TYPE_JA = {
    "FACT": "確認事実",
    "PARTY_CLAIM": "当事者の主張",
    "ANALYSIS": "分析",
    "HYPOTHESIS": "仮説",
    "FORECAST": "予測",
    "UNKNOWN": "不明",
}
ACCESS = ("DIRECT", "ABSTRACT_ONLY", "SEARCH_SNIPPET", "UNAVAILABLE")
SOURCE_TYPES = ("REGULATOR", "COMPANY", "BANK", "PARTNER", "ACADEMIC", "MEDIA", "INTERVIEW", "SOCIAL", "OTHER")
RELATIONS = ("PRIMARY_DIRECT", "PRIMARY_INDIRECT", "SECONDARY", "REPOST")
MEASUREMENT = ("AUDITED", "REPORTED", "ESTIMATED", "PROJECTED", "ANECDOTAL")
DIRECTIONS = ("SUPPORT", "CONTRADICT", "CONTEXT", "NONE")
VALIDITY = ("CURRENT", "SUPERSEDED", "EXPIRED", "NEEDS_RECHECK", "HISTORICAL_IMMUTABLE", "DISPUTED")

TEMPLATE_MARKER = "<!-- TEMPLATE:NOT_STARTED -->"


def research_root() -> Path:
    return Path(os.environ.get("RESEARCH_ROOT", ROOT))


def read_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("//"):
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError as e:  # surface the location: a broken ledger must fail loudly
                raise ValueError(f"{path}:{i}: invalid JSON ({e})") from e
    return out


def write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")


def read_json(path: Path, default=None):
    if not path.exists():
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def companies(root: Path | None = None) -> list[dict]:
    root = root or research_root()
    return read_csv(root / "registry" / "company_registry.csv")


def short_code(company_id: str) -> str:
    """COMPANY_01 -> C01 (prefix used inside every evidence ID)."""
    return "C" + company_id.split("_")[-1]


def company_dir(company: dict, root: Path | None = None) -> Path:
    root = root or research_root()
    return root / "companies" / company["name_ja"]


def axes(root: Path | None = None) -> list[dict]:
    root = root or research_root()
    return read_csv(root / "registry" / "axis_registry.csv")


def axis_ids(root: Path | None = None) -> list[str]:
    seen = []
    for r in axes(root):
        if r["axis_id"] not in seen:
            seen.append(r["axis_id"])
    return seen
