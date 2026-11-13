#!/usr/bin/env python3
"""Read-only split-accounting audit for CHAT 500 and scheduled 500 source leads.

Only counts distinct URLs discovered and ledgered. This is NOT S1/S2 evidence verification.
Run: python3 scripts/audit_split_500.py
"""
from __future__ import annotations
import csv
import json
from collections import Counter
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
E = ROOT / "external_handoff"
R = ROOT / "registry"
TRACK = {"fbclid", "gclid", "dclid"}

def load(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def url_key(url: str) -> str:
    p = urlsplit((url or "").strip())
    hostname = (p.hostname or "").lower().removeprefix("www.")
    query = urlencode(sorted((k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
                              if not k.lower().startswith("utm_") and k.lower() not in TRACK))
    return urlunsplit(("https", hostname, p.path.rstrip("/") or "/", query, ""))

def get_url(row: dict[str, str]) -> str:
    return (row.get("url") or row.get("source_url") or "").strip()

def audit() -> dict:
    original = load(R / "source_evidence.csv")
    supplemental = (load(E / "NEW_ORIGINAL_EVIDENCE_20261113_ADS_POLICY_RESEARCH.csv")
                    + load(E / "NEW_ORIGINAL_EVIDENCE_20261113_OCR_UI_RISK.csv"))
    topics = load(R / "research_axes.csv")
    added = load(R / "additional_axes.csv")
    topic_ids = {x["topic_id"] for x in topics + added}
    baseline_keys = {url_key(get_url(x)) for x in original + supplemental}

    chat_files = sorted(p for p in E.glob("BROAD_POOL_*.csv")
                        if "AUTOMATION" not in p.name)
    chat_files += [E / "CHAT500_WEB_ORIGINAL_SOURCES_20261114.csv",
                   E / "CHAT500_PRIOR_SEARCH_LOG_INDEXED_BATCH05_20261114.csv"]
    # File pattern for the ongoing scheduled worker; excludes deferred/lists.
    auto_files = sorted(p for p in E.glob("BROAD_POOL_*AUTOMATION*.csv"))
    auto_files += sorted(p for p in E.glob("AUTOMATION500_BATCH*.csv"))
    auto_files += sorted(p for p in E.glob("AUTO500_BATCH*.csv"))
    chat_records = [(p.name, x) for p in chat_files for x in load(p)]
    auto_records = [(p.name, x) for p in auto_files for x in load(p)]
    chat_keys = [url_key(get_url(row)) for _, row in chat_records]
    auto_keys = [url_key(get_url(row)) for _, row in auto_records]
    unique_chat = set(chat_keys)
    unique_auto = set(auto_keys)
    chat_new = unique_chat - baseline_keys
    auto_new = unique_auto - baseline_keys - unique_chat
    bad_chat = [(name, row.get("candidate_id"), row.get("candidate_topic_ids"))
                for name, row in chat_records
                if not row.get("candidate_topic_ids") or
                any(t not in topic_ids for t in row["candidate_topic_ids"].split(";") if t)]
    bad_auto = [(name, row.get("candidate_id"), row.get("candidate_topic_ids"))
                for name, row in auto_records
                if not row.get("candidate_topic_ids") or
                any(t not in topic_ids for t in row["candidate_topic_ids"].split(";") if t)]
    id_chat = [row.get("candidate_id", "") for _, row in chat_records]
    id_auto = [row.get("candidate_id", "") for _, row in auto_records]
    result = {
        "disclaimer": "Discovery URLs, not fully eligible, independent or S2 verified sources",
        "base_canonical_records": len(original),
        "base_supplement_records": len(supplemental),
        "chat_files": {p.name: sum(1 for f, _ in chat_records if f == p.name) for p in chat_files},
        "auto_files": {p.name: sum(1 for f, _ in auto_records if f == p.name) for p in auto_files},
        "chat_candidate_records": len(chat_records),
        "chat_distinct_url_records": len(unique_chat),
        "chat_urls_overlapping_baseline": sorted(unique_chat & baseline_keys),
        "chat_distinct_url_leads_beyond_baseline": len(chat_new),
        "chat_duplicate_url_count": sum(n - 1 for n in Counter(chat_keys).values() if n > 1),
        "chat_duplicate_id_count": sum(n - 1 for n in Counter(id_chat).values() if n > 1),
        "auto_candidate_records": len(auto_records),
        "auto_distinct_url_leads_beyond_chat_and_baseline": len(auto_new),
        "auto_overlap_chat": sorted(unique_auto & unique_chat),
        "auto_overlap_baseline": sorted(unique_auto & baseline_keys),
        "auto_duplicate_url_count": sum(n - 1 for n in Counter(auto_keys).values() if n > 1),
        "auto_duplicate_id_count": sum(n - 1 for n in Counter(id_auto).values() if n > 1),
        "invalid_chat_topic_records": bad_chat,
        "invalid_auto_topic_records": bad_auto,
        "coverage_axes": len({x["axis_id"] for x in topics}),
        "coverage_topics": len(topics),
        "additional_topics": len(added),
        "chat_500_candidate_target_met": len(chat_new) >= 500,
        "auto_500_candidate_target_met": len(auto_new) >= 500,
        "both_500_candidate_targets_met": len(chat_new) >= 500 and len(auto_new) >= 500,
        "source_eligibility_selection_completed": False,
        "strict_896_three_evidence_passed_not_inferred": True,
        "S1_status_not_changed": "FAIL",
    }
    result["PASS_STRUCTURAL_ONLY"] = (
        len(original) == 464 and len(supplemental) == 15
        and len(topics) == 325 and len(added) == 7
        and not bad_chat and not bad_auto
        and result["chat_duplicate_url_count"] == 0
        and result["chat_duplicate_id_count"] == 0
        and result["auto_duplicate_url_count"] == 0
        and result["auto_duplicate_id_count"] == 0
        and not result["auto_overlap_chat"]
        and not result["auto_overlap_baseline"]
    )
    return result

if __name__ == "__main__":
    outcome = audit()
    print(json.dumps(outcome, ensure_ascii=False, indent=2))
    raise SystemExit(0 if outcome["PASS_STRUCTURAL_ONLY"] else 2)
