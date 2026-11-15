#!/usr/bin/env python3
"""Rebuild staged worker outputs from the runtime transcripts (research tooling only).

A worker's output file is written with the Write tool, so its full content is in the
transcript. This makes the staging area reproducible: a staged file is whatever the worker
ASSIGNED TO THAT UNIT actually wrote, and nothing else.

- An output is restored only from a run whose assigned unit equals the unit in the file name
  (a worker cannot file a report for another unit).
- A run whose searches were ALL refused (per-turn search budget) produced its output without
  the searches it needed; such an output is not restored, so the unit is planned again.
- A staged file that no run of its unit wrote is moved aside (kept, never merged).

Usage: python3 scripts/recover_staging.py STAGING_DIR TRANSCRIPT_DIR [TRANSCRIPT_DIR ...]
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from transcript_audit import UNIT_RX, classify, text_of  # noqa: E402

PATH_RX = re.compile(r'/staging/(topics|competitors)/((?:AXIS_\d\d|ADD_[A-Z0-9]+)_T\d\d|C\d{3})\.json$')


def scan(p: Path):
    uses, writes, real, refused, unit = {}, [], 0, 0, None
    for line in p.open(encoding='utf-8'):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        msg = d.get('message') if isinstance(d.get('message'), dict) else {}
        c = msg.get('content')
        if unit is None and d.get('type') == 'user':
            t = text_of(c)
            for _, rx in UNIT_RX:
                m = rx.search(t)
                if m:
                    unit = m.group(1)
                    break
        if not isinstance(c, list):
            continue
        for b in c:
            if not isinstance(b, dict):
                continue
            if b.get('type') == 'tool_use':
                uses[b.get('id')] = (b.get('name'), b.get('input') or {}, d.get('timestamp'))
            elif b.get('type') == 'tool_result' and b.get('tool_use_id') in uses:
                name, inp, ts = uses[b['tool_use_id']]
                if name == 'WebSearch':
                    o = classify(text_of(b.get('content')), bool(b.get('is_error')))
                    refused += o == 'refused'
                    real += o in ('ok', 'no_links')
                elif name == 'Write' and not b.get('is_error') and PATH_RX.search(str(inp.get('file_path', ''))):
                    writes.append((ts, inp['file_path'], inp.get('content', '')))
    return unit, writes, real, refused


def main() -> None:
    staging = Path(sys.argv[1])
    best, skipped, foreign = {}, [], []
    for d in sys.argv[2:]:
        for p in sorted(Path(d).glob('agent-*.jsonl')):
            unit, writes, real, refused = scan(p)
            for ts, path, content in writes:
                m = PATH_RX.search(path)
                key = (m.group(1), m.group(2))
                if unit != m.group(2):
                    foreign.append(f'{unit}->{m.group(2)}')
                    continue
                if refused > 0 and real == 0:
                    skipped.append(m.group(2))
                    continue
                if key not in best or ts > best[key][0]:
                    best[key] = (ts, content)
    restored = kept = 0
    for (sub, uid), (ts, content) in best.items():
        out = staging / sub / f'{uid}.json'
        out.parent.mkdir(parents=True, exist_ok=True)
        if out.exists() and out.read_text(encoding='utf-8') == content:
            kept += 1
            continue
        out.write_text(content, encoding='utf-8')
        restored += 1
    orphans = []
    for sub in ('topics', 'competitors'):
        for f in sorted((staging / sub).glob('*.json')) if (staging / sub).exists() else []:
            if (sub, f.stem) not in best:
                side = staging / 'not_from_own_worker' / sub
                side.mkdir(parents=True, exist_ok=True)
                f.rename(side / f.name)
                orphans.append(f.stem)
    print(json.dumps({'outputs_in_transcripts': len(best), 'restored_or_updated': restored, 'already_present': kept,
                      'not_restored_all_searches_refused': sorted(set(skipped) - {k[1] for k in best}),
                      'ignored_written_for_another_unit': foreign, 'moved_aside_not_written_by_own_worker': orphans}, ensure_ascii=False))


if __name__ == '__main__':
    main()
