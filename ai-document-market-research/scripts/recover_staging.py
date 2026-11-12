#!/usr/bin/env python3
"""Rebuild staged worker outputs from the runtime transcripts (research tooling only).

A worker's output file is written with the Write tool, so its full content is in the
transcript. This makes the staging area reproducible: if a staged file is lost, it is
restored from the record of what the worker actually wrote.

A run whose searches were ALL refused (per-turn search budget) produced its output without
the searches it needed; such an output is not restored, so the unit is planned again.

Usage: python3 scripts/recover_staging.py STAGING_DIR TRANSCRIPT_DIR [TRANSCRIPT_DIR ...]
"""
import json, re, sys
from pathlib import Path
PATH_RX = re.compile(r'/staging/(topics|competitors)/((?:AXIS_\d\d|ADD_[A-Z0-9]+)_T\d\d|C\d{3})\.json$')

def scan(p: Path):
    uses, writes, real, refused = {}, [], 0, 0
    for line in p.open(encoding='utf-8'):
        try: d = json.loads(line)
        except ValueError: continue
        msg = d.get('message') if isinstance(d.get('message'), dict) else {}
        c = msg.get('content')
        if not isinstance(c, list): continue
        for b in c:
            if not isinstance(b, dict): continue
            if b.get('type') == 'tool_use':
                uses[b.get('id')] = (b.get('name'), b.get('input') or {}, d.get('timestamp'))
            elif b.get('type') == 'tool_result' and b.get('tool_use_id') in uses:
                name, inp, ts = uses[b['tool_use_id']]
                res = b.get('content'); res = res if isinstance(res, str) else json.dumps(res, ensure_ascii=False)
                if name == 'WebSearch':
                    if 'was not performed' in res: refused += 1
                    elif 'Links: [' in res: real += 1
                elif name == 'Write' and not b.get('is_error') and PATH_RX.search(str(inp.get('file_path', ''))):
                    writes.append((ts, inp['file_path'], inp.get('content', '')))
    return writes, real, refused

def main():
    staging = Path(sys.argv[1]); best = {}; skipped = []
    for d in sys.argv[2:]:
        for p in sorted(Path(d).glob('agent-*.jsonl')):
            writes, real, refused = scan(p)
            for ts, path, content in writes:
                m = PATH_RX.search(path); key = (m.group(1), m.group(2))
                if refused > 0 and real == 0:
                    skipped.append(m.group(2)); continue
                if key not in best or ts > best[key][0]: best[key] = (ts, content)
    restored = kept = 0
    for (sub, uid), (ts, content) in best.items():
        out = staging / sub / f'{uid}.json'
        out.parent.mkdir(parents=True, exist_ok=True)
        if out.exists() and out.read_text(encoding='utf-8') == content: kept += 1; continue
        out.write_text(content, encoding='utf-8'); restored += 1
    print(json.dumps({'outputs_in_transcripts': len(best), 'restored_or_updated': restored, 'already_present': kept, 'not_restored_all_searches_refused': sorted(set(skipped) - {k[1] for k in best})}, ensure_ascii=False))

if __name__ == '__main__': main()
