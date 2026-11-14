#!/usr/bin/env python3
"""Read-only audit: exactly 1000 distinct CHAT candidate URLs beyond 479 base records.

IMPORTANT: this is a URL-ledger audit, not a source/claim validity or S1 PASS audit.
The scheduled-task BPOOL071-BPOOL076 records are NOT counted by design.
Usage: python3 scripts/audit_chat_only_1000.py
"""
from __future__ import annotations
import csv, json
from collections import defaultdict, Counter
from pathlib import Path
from urllib.parse import urlsplit, parse_qsl, urlencode

ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT / "external_handoff"
REG = ROOT / "registry"
BASE = [
    REG / "source_evidence.csv",
    EXT / "NEW_ORIGINAL_EVIDENCE_20261113_ADS_POLICY_RESEARCH.csv",
    EXT / "NEW_ORIGINAL_EVIDENCE_20261113_OCR_UI_RISK.csv",
]
CHAT_BASE = [
    EXT / "BROAD_POOL_20261113_PRIMARY_SOURCES_BATCH01.csv",
    EXT / "BROAD_POOL_20261113_USER_EVIDENCE_BATCH02.csv",
    EXT / "BROAD_POOL_20261114_VERIFIED_DISCOVERY_BATCH03.csv",
    EXT / "BROAD_POOL_20261114_POLICY_SURVEYS_METHODS_BATCH04.csv",
    EXT / "CHAT500_WEB_ORIGINAL_SOURCES_20261114.csv",
    EXT / "CHAT500_PRIOR_SEARCH_LOG_INDEXED_BATCH05_20261114.csv",
]
CHAT_EXTRA = [
    EXT / "CHAT_EXTRA500_WEB_DISCOVERY_20261114.csv",
    EXT / "CHAT_EXTRA500_WEB_DISCOVERY_BATCH02_20261114.csv",
    EXT / "CHAT_EXTRA500_PRIOR_LOG_SCREENED_BATCH03_20261114.csv",
]
AUTO_IGNORED = [EXT / "BROAD_POOL_20261114_AUTOMATION_BATCH05.csv"]

def load(path: Path) -> list[dict[str,str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def norm(url: str) -> str:
    p = urlsplit((url or "").strip())
    host = (p.hostname or "").lower().removeprefix("www.")
    path = p.path.rstrip("/") or "/"
    if host == "web3.arxiv.org": host = "arxiv.org"
    import re
    if host == "arxiv.org":
        match = re.match(r"^/(?:abs|pdf|html)/(\d{4}\.\d{4,5})(?:v\d+)?(?:\.pdf)?(?:/.*)?$", path, re.I)
        if match: path = "/article/" + match.group(1)
    params = [(k,v) for k,v in parse_qsl(p.query,keep_blank_values=True) if k in {"id", "p", "page"}]
    return host + path.lower() + (("?" + urlencode(sorted(params))) if params else "")

def records(paths):
    return [(p.name,row) for p in paths for row in load(p)]

def get_url(row):
    return (row.get("url") or row.get("source_url") or "").strip()

def keys(rows):
    mapping=defaultdict(list)
    for filename,row in rows:
        mapping[norm(get_url(row))].append((filename,row.get("candidate_id") or row.get("evidence_id") or "BASE"))
    return mapping

def audit():
    base=records(BASE)
    first=records(CHAT_BASE)
    additional=records(CHAT_EXTRA)
    ignored=records(AUTO_IGNORED)
    B,F,E,A=keys(base),keys(first),keys(additional),keys(ignored)
    nfirst=set(F)-set(B)
    nextra=set(E)-set(B)-set(F)
    all_topics={r["topic_id"] for r in load(REG/"research_axes.csv")+load(REG/"additional_axes.csv")}
    invalid_topic=[(f,r.get("candidate_id")) for f,r in first+additional
                   if not (r.get("candidate_topic_ids") or r.get("topic_ids") or "")
                   or any(t not in all_topics for t in
                          (r.get("candidate_topic_ids") or r.get("topic_ids") or "").split(";"))]
    def overlaps(X,Y):
        return [{"url_key":k,"ids":v} for k,v in X.items() if k in Y]
    result={
        "definitions":"URL candidates only, not independently verified eligible S2 sources.",
        "baseline_records":len(base),
        "first_chat_rows":len(first),
        "first_chat_net_new_distinct_url_keys":len(nfirst),
        "first_chat_baseline_overlap":overlaps(F,B),
        "first_chat_internal_aliases":[{"url_key":k,"ids":v} for k,v in F.items() if len(v)>1],
        "additional_chat_rows":len(additional),
        "additional_chat_net_new_distinct_url_keys":len(nextra),
        "additional_chat_overlaps_baseline_or_first":overlaps(E,{**B,**F}),
        "additional_chat_internal_aliases":[{"url_key":k,"ids":v} for k,v in E.items() if len(v)>1],
        "ignored_automation_records":len(ignored),
        "additional_chat_crosses_automation":overlaps(E,A),
        "total_net_chat_url_candidates":len(nfirst)+len(nextra),
        "invalid_topic_references":invalid_topic,
        "original_study_independence_verified":"NO",
        "source_level_s2_verification_completed":"NO",
        "strict_896_id_triples_completed":0,
        "S1":"FAIL",
    }
    result["LEDGER_STRUCTURAL_PASS"]=(len(base)==479 and len(nfirst)==500 and len(nextra)==500
        and len(additional)==500 and not result["additional_chat_overlaps_baseline_or_first"]
        and not result["additional_chat_internal_aliases"]
        and not result["additional_chat_crosses_automation"] and not invalid_topic)
    return result

if __name__=="__main__":
    result=audit()
    print(json.dumps(result,ensure_ascii=False,indent=2))
    raise SystemExit(0 if result["LEDGER_STRUCTURAL_PASS"] else 2)
