#!/usr/bin/env python3
"""Extract what research workers ACTUALLY executed from their session transcripts.

A worker's own report is not trusted for "was this query run": this script reads the
tool-call records (web searches and page fetches) written by the runtime, so that the
search ledger is built from executed calls, not from claims. Research tooling only.

Usage: python3 scripts/transcript_audit.py OUT_JSONL TRANSCRIPT_DIR [TRANSCRIPT_DIR ...]
Each output line: one worker run = {unit_kind, unit_id, agent_id, run, searches[], fetches[], wrote[]}
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

UNIT_RX = [('TOPIC', re.compile(r'TOPIC_UNIT_ID=((?:AXIS_\d\d|ADD_[A-Z0-9]+)_T\d\d)')),
           ('TOPIC', re.compile(r'exactly ONE registered topic: ((?:AXIS_\d\d|ADD_[A-Z0-9]+)_T\d\d)')),
           ('COMPETITOR', re.compile(r'COMPETITOR_UNIT_ID=(C\d{3})')),
           ('SOURCE_REVIEW', re.compile(r'SOURCE_REVIEW_BATCH=([A-Za-z0-9_\-]+)'))]
URL_RX = re.compile(r'["\'](https?://[^"\'\s]+)["\']|(?<=\s)(https?://[^"\'\s;|&)]+)')


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


def audit(path: Path) -> dict | None:
    unit_kind = unit_id = None
    uses: dict[str, dict] = {}
    searches, fetches, wrote = [], [], []
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
                    ls = links(res)
                    refused = 'was not performed' in res  # the tool answers in the normal format when the per-turn search budget is used up
                    ok = (not err) and (not refused) and 'Links: [' in res
                    searches.append({'ts': u['ts'], 'query': u['input'].get('query', ''), 'mode': u['input'].get('mode', ''),
                                     'ok': ok, 'refused': refused, 'n_links': len(ls) if ok else 0, 'links': ls[:10] if ok else [],
                                     'error': '' if ok else ('REFUSED_BUDGET: per-turn web search budget used up' if refused else res[:200])})
                elif u['name'] == 'Bash':
                    cmd = u['input'].get('command', '')
                    if 'fetch_text.py' in cmd:  # the tool may be called through a shell variable or in a loop
                        urls = list(dict.fromkeys(a or b for a, b in URL_RX.findall(cmd)))
                        marks = re.findall(r'## status=(\d+) chars=(\d+)', res)
                        for i, url in enumerate(urls):
                            st = marks[i] if len(marks) == len(urls) else ('0', '0')  # merge step reads the real status from the fetch cache
                            fetches.append({'ts': u['ts'], 'url': url, 'status': int(st[0]), 'chars': int(st[1])})
                elif u['name'] == 'Write':
                    wrote.append(u['input'].get('file_path', ''))
    if unit_id is None:
        return None
    return {'unit_kind': unit_kind, 'unit_id': unit_id, 'agent_id': path.stem.replace('agent-', ''), 'run': path.parent.name,
            'searches': searches, 'fetches': fetches, 'wrote': wrote}


def main() -> None:
    out = Path(sys.argv[1])
    n = 0
    with out.open('w', encoding='utf-8') as f:
        for d in sys.argv[2:]:
            for p in sorted(Path(d).glob('agent-*.jsonl')):
                r = audit(p)
                if r:
                    f.write(json.dumps(r, ensure_ascii=False) + '\n')
                    n += 1
    print(f'worker runs traced: {n}')


if __name__ == '__main__':
    main()
