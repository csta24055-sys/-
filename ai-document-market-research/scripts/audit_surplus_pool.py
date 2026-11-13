#!/usr/bin/env python3
"""Audit surplus-discovery CSV batches without promoting candidates to S1/S2 evidence.

Read-only. Works from any current working directory:
    python3 scripts/audit_surplus_pool.py
    python3 scripts/audit_surplus_pool.py --json
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
BATCHES = "BROAD_POOL_*.csv"
VALID_GENRES = {"PRIMARY", "USER_VOICE", "COUNTEREXAMPLE", "INTERNATIONAL"}
REQUIRED = {
    "candidate_id", "url", "publisher", "origin_group", "source_class",
    "eligible_genres_to_verify", "candidate_topic_ids", "publication_date",
    "exact_scope_from_landing", "limitations_and_duplicates",
    "read_depth", "checked_on",
}
TRACKING_KEYS = {"fbclid", "gclid", "dclid", "mc_cid", "mc_eid"}


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def url_key(value: str) -> str:
    """Conservative URL normalization; never merge two distinct content query params."""
    parts = urlsplit(value.strip())
    host = (parts.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    path = parts.path.rstrip("/") or "/"
    args = sorted((k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
                  if not k.lower().startswith("utm_") and k.lower() not in TRACKING_KEYS)
    return urlunsplit(("https", host, path, urlencode(args), ""))


def audit(root: Path = ROOT) -> dict:
    batches = sorted((root / "external_handoff").glob(BATCHES))
    if not batches:
        raise ValueError("No real surplus CSV batches found")

    topic_ids = {row["topic_id"] for row in read_rows(root / "registry/research_axes.csv")}
    supplement_path = root / "registry/additional_axes.csv"
    if supplement_path.exists():
        topic_ids |= {row["topic_id"] for row in read_rows(supplement_path)}

    canonical = read_rows(root / "registry/source_evidence.csv")
    canonical_urls = {url_key(row["url"]) for row in canonical if row.get("url")}
    candidate_urls = defaultdict(list)
    origins = defaultdict(list)
    candidates = []
    errors = []
    batch_counts = {}

    for file in batches:
        with file.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            missing = REQUIRED - set(reader.fieldnames or ())
            if missing:
                errors.append(f"{file.name}: missing columns: {sorted(missing)}")
                continue
            batch = list(reader)
        batch_counts[file.name] = len(batch)
        for i, row in enumerate(batch, 2):
            label = f"{file.name}:{i}"
            candidates.append(row)
            candidate_urls[url_key(row["url"])].append(row["candidate_id"])
            origins[row["origin_group"]].append(row["candidate_id"])

            if not re.fullmatch(r"BPOOL\d{3,}", row["candidate_id"]):
                errors.append(f"{label}: malformed candidate ID")
            if urlsplit(row["url"]).scheme not in ("http", "https") or not urlsplit(row["url"]).hostname:
                errors.append(f"{label}: invalid URL")
            for field in REQUIRED - {"publication_date"}:
                if not row.get(field, "").strip():
                    errors.append(f"{label}: empty {field}")
            genres = {g.strip() for g in row["eligible_genres_to_verify"].split(";") if g.strip()}
            if not genres or genres - VALID_GENRES:
                errors.append(f"{label}: invalid genre tags {genres - VALID_GENRES}")
            topics = {t.strip() for t in row["candidate_topic_ids"].split(";") if t.strip()}
            if not topics or topics - topic_ids:
                errors.append(f"{label}: unknown topic IDs {topics - topic_ids}")

    ids = [row["candidate_id"] for row in candidates]
    duplicate_ids = sorted(k for k, n in Counter(ids).items() if n > 1)
    repeated_urls = {u: identifiers for u, identifiers in candidate_urls.items() if len(identifiers) > 1}
    repeated_canon = sorted(row["candidate_id"] for row in candidates
                            if url_key(row["url"]) in canonical_urls)
    if duplicate_ids:
        errors.append(f"Duplicate candidate IDs: {duplicate_ids}")
    if repeated_urls:
        errors.append(f"Duplicate URLs across batches: {repeated_urls}")
    if repeated_canon:
        errors.append(f"Already in canonical source_evidence URLs: {repeated_canon}")

    # Shared origin_group denotes potential dependency, never independent proof.
    shared_origins = {k: v for k, v in origins.items() if len(v) > 1}
    result = {
        "status": "CANDIDATES_ONLY_NOT_VERIFIED_EVIDENCE",
        "s1_gate": "FAIL_UNCHANGED",
        "base_canonical_rows_actual": len(canonical),
        "base_additional_rows_by_existing_policy_not_recounted": 15,
        "base_reference_records_by_existing_policy": len(canonical) + 15,
        "new_candidate_rows": len(candidates),
        "estimated_total_candidate_records": len(canonical) + 15 + len(candidates),
        "candidate_urls_unduplicated_in_batch": len(candidate_urls),
        "batch_counts": batch_counts,
        "duplicate_ids": duplicate_ids,
        "repeat_urls_between_batches": repeated_urls,
        "repeat_urls_with_canon": repeated_canon,
        "shared_origin_groups_needing_review": shared_origins,
        "errors": errors,
        "PASS_STRUCTURAL_ONLY": not errors,
        "not_a_proof_of_independent_origin_or_genre_fit": True,
        "not_a_896_search_id_3_evidence_audit": True,
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Machine-readable output (already JSON by default)")
    args = parser.parse_args()
    result = audit()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["PASS_STRUCTURAL_ONLY"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
