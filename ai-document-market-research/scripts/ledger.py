#!/usr/bin/env python3
"""Evidence-ledger helper for the market study (research tooling only, no app code).

Appends rows to the registry CSVs from JSON-Lines input and validates them so that
only searches / page accesses that were really executed, and sources that were
really opened, are recorded. It never generates evidence by itself.

Usage:
    python3 scripts/ledger.py search  batch.jsonl   # executed searches / page accesses
    python3 scripts/ledger.py source  batch.jsonl   # reviewed sources
    python3 scripts/ledger.py quant   batch.jsonl   # quantitative results
    python3 scripts/ledger.py claim   batch.jsonl   # product claims
    python3 scripts/ledger.py stats                 # coverage summary

Logging convention (L1): one row = one (executed action, topic) pair. An executed
action (one web search or one page access) may be logged for more than one topic
only when its results were actually examined for that topic; such rows carry
`same_action_as=<query_id>` in notes, and `stats` reports distinct executed
actions separately from rows.
"""
from __future__ import annotations
import csv
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REG = ROOT / 'registry'

SOURCE_TYPES = {'OFFICIAL_VENDOR', 'INDEPENDENT_REVIEW', 'SPONSORED', 'ACADEMIC',
                'GOVERNMENT', 'CUSTOMER_FIRSTHAND', 'OTHER'}
VERIFIED = {'DIRECT_ORIGINAL', 'VERIFIED_SECONDARY', 'SNIPPET_ONLY', 'EXISTENCE_ONLY', 'NOT_FOUND'}
EVIDENCE_CATEGORIES = {'OBSERVED', 'MODEL_BASED', 'MIXED', 'ASSUMPTION_ONLY', 'NON_IDENTIFIABLE'}


def now() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def read(path: Path) -> tuple[list[str], list[dict]]:
    with path.open('r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or []), list(reader)


def write(path: Path, fields: list[str], rows: list[dict]) -> None:
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='raise')
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, '') for k in fields})


def topics() -> dict[str, str]:
    _, rows = read(REG / 'research_axes.csv')
    return {r['topic_id']: r['axis_id'] for r in rows}


def load_jsonl(path: str) -> list[dict]:
    out = []
    for i, line in enumerate(Path(path).read_text(encoding='utf-8').splitlines(), 1):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        try:
            out.append(json.loads(line))
        except ValueError as e:
            raise SystemExit(f'{path}:{i}: invalid JSON: {e}')
    return out


def add_search(path: str) -> None:
    fields, rows = read(REG / 'search_log.csv')
    t = topics()
    n = len(rows)
    for obj in load_jsonl(path):
        tid = obj.get('topic_id', '')
        if tid not in t:
            raise SystemExit(f'unknown topic_id: {tid!r}')
        for k in ('platform', 'query', 'retrieval_status'):
            if not str(obj.get(k, '')).strip():
                raise SystemExit(f'search row for {tid} is missing {k}')
        n += 1
        row = {k: '' for k in fields}
        row.update({k: str(v) for k, v in obj.items() if k in fields})
        row['query_id'] = obj.get('query_id') or f'Q{n:04d}'
        row['axis_id'] = t[tid]
        row['searched_at'] = obj.get('searched_at') or now()
        rows.append(row)
    if len({r['query_id'] for r in rows}) != len(rows):
        raise SystemExit('duplicate query_id')
    write(REG / 'search_log.csv', fields, rows)
    print(f'search_log rows: {len(rows)}')


def add_source(path: str) -> None:
    fields, rows = read(REG / 'source_evidence.csv')
    t = topics()
    seen = {r['source_id'] for r in rows}
    for obj in load_jsonl(path):
        sid = obj.get('source_id', '')
        if not sid or sid in seen:
            raise SystemExit(f'missing or duplicate source_id: {sid!r}')
        tid = obj.get('topic_id', '')
        if tid not in t:
            raise SystemExit(f'{sid}: unknown topic_id {tid!r}')
        if obj.get('source_type') not in SOURCE_TYPES:
            raise SystemExit(f'{sid}: bad source_type {obj.get("source_type")!r}')
        if obj.get('verified_state') not in VERIFIED:
            raise SystemExit(f'{sid}: bad verified_state {obj.get("verified_state")!r}')
        if not str(obj.get('url', '')).startswith(('https://', 'http://')):
            raise SystemExit(f'{sid}: malformed url')
        if obj.get('is_accepted') not in ('yes', 'no'):
            raise SystemExit(f'{sid}: is_accepted must be yes/no')
        if obj['is_accepted'] == 'yes' and obj['verified_state'] not in ('DIRECT_ORIGINAL', 'VERIFIED_SECONDARY'):
            raise SystemExit(f'{sid}: a source that was not opened and verified cannot be accepted')
        for k in ('origin_group_id', 'publisher', 'claim_text', 'page_or_section'):
            if not str(obj.get(k, '')).strip():
                raise SystemExit(f'{sid}: missing {k}')
        row = {k: 'UNKNOWN' for k in fields}
        row.update({k: str(v) for k, v in obj.items() if k in fields})
        row['axis_id'] = t[tid]
        row['checked_at'] = obj.get('checked_at') or now()
        rows.append(row)
        seen.add(sid)
    write(REG / 'source_evidence.csv', fields, rows)
    print(f'source_evidence rows: {len(rows)}')


def add_generic(path: str, filename: str, key: str) -> None:
    fields, rows = read(REG / filename)
    seen = {r[key] for r in rows}
    _, src = read(REG / 'source_evidence.csv')
    accepted = {r['source_id'] for r in src if r.get('is_accepted') == 'yes'}
    for obj in load_jsonl(path):
        if not obj.get(key) or obj[key] in seen:
            raise SystemExit(f'missing or duplicate {key}: {obj.get(key)!r}')
        cited = {x.strip() for x in str(obj.get('source_ids', '')).split(';') if x.strip()}
        if cited - accepted:
            raise SystemExit(f'{obj[key]}: cites sources that are not accepted: {sorted(cited - accepted)}')
        if filename == 'quant_results.csv' and obj.get('evidence_category') not in EVIDENCE_CATEGORIES:
            raise SystemExit(f'{obj[key]}: bad evidence_category')
        row = {k: '' for k in fields}
        row.update({k: str(v) for k, v in obj.items() if k in fields})
        rows.append(row)
        seen.add(obj[key])
    write(REG / filename, fields, rows)
    print(f'{filename} rows: {len(rows)}')


def stats() -> None:
    t = topics()
    _, s = read(REG / 'search_log.csv')
    _, e = read(REG / 'source_evidence.csv')
    acc = [r for r in e if r.get('is_accepted') == 'yes']
    actions = {r['query_id'] for r in s if 'same_action_as=' not in r.get('notes', '')}
    covered = {r['topic_id'] for r in s}
    print(json.dumps({
        'search_log_rows': len(s),
        'distinct_executed_actions': len(actions),
        'platforms': dict(Counter(r['platform'] for r in s)),
        'topics_with_logged_attempt': len(covered),
        'topics_total': len(t),
        'topics_without_attempt': sorted(set(t) - covered),
        'source_rows': len(e),
        'accepted_sources': len(acc),
        'direct_original_accepted': sum(r['verified_state'] == 'DIRECT_ORIGINAL' for r in acc),
        'independent_origins': len({r['origin_group_id'] for r in acc}),
        'axes_with_accepted_source': len({r['axis_id'] for r in acc}),
        'topics_with_accepted_source': len({r['topic_id'] for r in acc}),
        'source_types': dict(Counter(r['source_type'] for r in acc)),
    }, ensure_ascii=False, indent=1))


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    cmd = sys.argv[1]
    if cmd == 'stats':
        stats()
    elif cmd == 'search':
        add_search(sys.argv[2])
    elif cmd == 'source':
        add_source(sys.argv[2])
    elif cmd == 'quant':
        add_generic(sys.argv[2], 'quant_results.csv', 'result_id')
    elif cmd == 'claim':
        add_generic(sys.argv[2], 'product_claims.csv', 'claim_id')
    else:
        raise SystemExit(__doc__)


if __name__ == '__main__':
    main()
