#!/usr/bin/env python3
"""Extract what research workers ACTUALLY executed from their session transcripts.

A worker's own report is not trusted for "was this query run": this script reads the
tool-call records (web searches, page fetches, file writes) written by the runtime, so the
search ledger is built from executed calls, not from claims. Research tooling only.

Usage: python3 scripts/transcript_audit.py OUT_JSONL TRANSCRIPT_DIR [TRANSCRIPT_DIR ...] [--manifest CSV]

OUT_JSONL   one line per worker run = {unit_kind, unit_id, agent_id, run, searches[], fetches[], fetch_stamps[], wrote[]}
--manifest  also write a compact, committable execution manifest (one row per executed search or
            page fetch: query strings and URLs only, never page content) and a seal file next to it
            (<manifest>.seal.json with the manifest's sha256). The status builder counts a logged
            execution only when the manifest has the same call.

Search outcome is taken from the call's own result:
  ok        the engine answered in its normal format with a link list
  no_links  the engine answered in its normal format without links   -> executed, empty result
  refused   the engine answered "was not performed" (per-turn search budget used up) -> NOT executed, retry later
  error     anything else (tool error, validation error, interruption) -> NOT executed, retry later
"""
from __future__ import annotations
import csv
import hashlib
import json
import re
import sys
from pathlib import Path

UNIT_RX = [('TOPIC', re.compile(r'TOPIC_UNIT_ID=((?:AXIS_\d\d|ADD_[A-Z0-9]+)_T\d\d)')),
           ('TOPIC', re.compile(r'exactly ONE registered topic: ((?:AXIS_\d\d|ADD_[A-Z0-9]+)_T\d\d)')),
           ('COMPETITOR', re.compile(r'COMPETITOR_UNIT_ID=(C\d{3})')),
           ('SOURCE_REVIEW', re.compile(r'SOURCE_REVIEW_BATCH=([A-Za-z0-9_\-]+)'))]
URL_RX = re.compile(r'["\'](https?://[^"\'\s]+)["\']|(?<=\s)(https?://[^"\'\s;|&)]+)')
STAMP_RX = re.compile(r'## status=(\d+) chars=(\d+) fetched_at=(\S+)')
HEADER = 'Web search results for query:'
MANIFEST_FIELDS = ['run', 'agent_id', 'unit_kind', 'unit_id', 'action', 'ts', 'target', 'outcome', 'n_links']
SEARCH_ERRORS = {'ok': '', 'refused': 'REFUSED_BUDGET: per-turn web search budget used up', 'no_links': 'engine returned no links'}


def text_of(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return '\n'.join(b.get('text', '') if isinstance(b, dict) else str(b) for b in content)
    return ''


def links(result_text: str) -> list[str]:
    m = re.search(r'Links: (\[.*?\])\n', result_text, re.S)
    if not m:
        return []
    try:
        return [x.get('url', '') for x in json.loads(m.group(1)) if isinstance(x, dict)]
    except ValueError:
        return re.findall(r'"url":"(https?://[^"]+)"', m.group(1))


def classify(res: str, is_error: bool) -> str:
    if is_error or not res.lstrip().startswith(HEADER):
        return 'error'
    if 'was not performed' in res[:1500]:
        return 'refused'
    return 'ok' if links(res) else 'no_links'


def audit(path: Path) -> dict | None:
    unit_kind = unit_id = None
    uses: dict[str, dict] = {}
    searches, fetches, stamps, wrote = [], [], [], []
    for line in path.open(encoding='utf-8'):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        msg = d.get('message') if isinstance(d.get('message'), dict) else {}
        content = msg.get('content')
        if unit_id is None and d.get('type') == 'user':
            t = text_of(content)
            for kind, rx in UNIT_RX:
                m = rx.search(t)
                if m:
                    unit_kind, unit_id = kind, m.group(1)
                    break
        if not isinstance(content, list):
            continue
        for b in content:
            if not isinstance(b, dict):
                continue
            if b.get('type') == 'tool_use':
                uses[b.get('id')] = {'name': b.get('name'), 'input': b.get('input') or {}, 'ts': d.get('timestamp')}
            elif b.get('type') == 'tool_result':
                u = uses.get(b.get('tool_use_id'))
                if not u:
                    continue
                res = text_of(b.get('content'))
                err = bool(b.get('is_error'))
                if u['name'] == 'WebSearch':
                    outcome = classify(res, err)
                    ls = links(res) if outcome == 'ok' else []
                    searches.append({'ts': u['ts'], 'query': u['input'].get('query', ''), 'mode': u['input'].get('mode', ''), 'outcome': outcome,
                                     'ok': outcome == 'ok', 'refused': outcome == 'refused', 'n_links': len(ls), 'links': ls[:10],
                                     'error': SEARCH_ERRORS.get(outcome, 'TOOL_ERROR: ' + ' '.join(res.split())[:160])})
                elif u['name'] == 'Bash':
                    cmd = u['input'].get('command', '')
                    if 'fetch_text.py' in cmd:  # the tool may be called through a shell variable or in a loop
                        urls = list(dict.fromkeys(a or b2 for a, b2 in URL_RX.findall(cmd)))
                        marks = STAMP_RX.findall(res)
                        stamps += [m[2] for m in marks]  # the fetch tool prints the cache timestamp of every page it returned
                        for i, url in enumerate(urls):
                            st = marks[i] if len(marks) == len(urls) else ('0', '0', '')  # the merge step reads the real status from the fetch cache
                            fetches.append({'ts': u['ts'], 'url': url, 'status': int(st[0]), 'chars': int(st[1])})
                elif u['name'] == 'Write' and not err:
                    wrote.append(u['input'].get('file_path', ''))
    if unit_id is None:
        return None
    return {'unit_kind': unit_kind, 'unit_id': unit_id, 'agent_id': path.stem.replace('agent-', ''), 'run': path.parent.name,
            'searches': searches, 'fetches': fetches, 'fetch_stamps': sorted(set(stamps)), 'wrote': wrote}


def derive(dirs: list) -> list[dict]:
    runs = []
    for d in dirs:
        for p in sorted(Path(d).glob('agent-*.jsonl')):
            r = audit(p)
            if r:
                runs.append(r)
    return runs


def manifest_rows(runs: list[dict]) -> list[dict]:
    out = []
    for r in runs:
        base = {'run': r['run'], 'agent_id': r['agent_id'], 'unit_kind': r['unit_kind'], 'unit_id': r['unit_id']}
        for s in r['searches']:
            out.append({**base, 'action': 'SEARCH', 'ts': s['ts'], 'target': s['query'], 'outcome': s['outcome'], 'n_links': str(s['n_links'])})
        seen = set()
        for f in r['fetches']:
            if f['url'] not in seen:
                seen.add(f['url'])
                out.append({**base, 'action': 'FETCH', 'ts': f['ts'], 'target': f['url'], 'outcome': '', 'n_links': ''})
    return sorted(out, key=lambda x: (x['run'], x['agent_id'], x['action'], x['ts'] or '', x['target']))


def manifest_digest(rows: list[dict]) -> str:
    blob = '\n'.join('\x1f'.join(str(r.get(k, '')) for k in MANIFEST_FIELDS) for r in rows)
    return hashlib.sha256(blob.encode('utf-8')).hexdigest()


def write_manifest(path: Path, runs: list[dict]) -> None:
    rows = manifest_rows(runs)
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=MANIFEST_FIELDS)
        w.writeheader()
        w.writerows(rows)
    seal = {'manifest_sha256': manifest_digest(rows), 'rows': len(rows), 'worker_runs': len(runs),
            'note': 'derived from runtime transcripts by scripts/transcript_audit.py; do not edit by hand'}
    Path(str(path) + '.seal.json').write_text(json.dumps(seal, ensure_ascii=False, indent=1), encoding='utf-8')


def main() -> None:
    args = sys.argv[1:]
    manifest = None
    if '--manifest' in args:
        i = args.index('--manifest')
        manifest = Path(args[i + 1])
        del args[i:i + 2]
    runs = derive(args[1:])
    with Path(args[0]).open('w', encoding='utf-8') as f:
        for r in runs:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    if manifest:
        write_manifest(manifest, runs)
    print(f'worker runs traced: {len(runs)}')


if __name__ == '__main__':
    main()
