#!/usr/bin/env python3
"""Strict research gates (v2) for the AI document market study. Research tooling only.

Changes from v1 (kept in original_20261109/scripts/):
- Scope is locked: 32 axes / 325 topics / 896 legacy queries / 80 competitor candidates.
- Nothing passes because a CSV says so. Topic / query / competitor status is RECOMPUTED from
  the search log (transcript-verified executions), the source ledger (quote found in the
  fetched page) and the unit records, and compared with the status files on disk.
- Stages follow the continuation directive: S1 collection for every topic, every legacy
  query and every candidate; S2 review of every adopted source; S3 representativeness and
  axis relations; S4 competitor audit; S5 every calculation id; S6 integration; S7 options
  A-G; S8 coverage audit; S9 formal deliverables ONLY after S0-S8 pass.
- A stage passes only if all earlier stages pass. Formal deliverables that exist before
  S0-S8 pass are reported as a violation.

Mechanical checks cannot establish that a source is true or a sample representative.

Usage:
    python3 scripts/research_gates.py check
    python3 scripts/research_gates.py evaluate   # also writes gate_evaluation.json, research_status.json, GATE_AUDIT_DETAIL.md
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_status  # noqa: E402

FULL_SCOPE = {'axes': 32, 'topics': 325, 'legacy': 896, 'competitors': 80, 'images': 8}
STEPS = [('S0', 'reaudit_and_scope_lock'), ('S1', 'collection_all_topics_queries_competitors'), ('S2', 'source_review_all'),
         ('S3', 'representativeness_and_axis_model'), ('S4', 'competitor_audit_all'), ('S5', 'calculations_all'),
         ('S6', 'cross_axis_integration'), ('S7', 'options_A_to_G'), ('S8', 'coverage_audit'), ('S9', 'formal_deliverables')]
MARKERS = ('NOT_STARTED', '【要調査】', '[TODO]', 'TODO:')
TERMINAL_CALC = {'EXECUTED_AND_VERIFIED', 'NON_IDENTIFIABLE', 'BLOCKED_DATA', 'REJECTED_INVALID_METHOD'}
CATEGORIES = {'OBSERVED', 'MODEL_BASED', 'MIXED', 'ASSUMPTION_ONLY', 'NON_IDENTIFIABLE', 'INVALID'}
STATEMENT_KINDS = {'FACT_MEASURED', 'VENDOR_CLAIM', 'OPINION', 'HYPOTHESIS', 'RULE_OR_GUIDELINE'}
REP_GRADES = {'A_PROBABILITY_SAMPLE', 'B_LARGE_NONPROBABILITY', 'C_SMALL_OR_SELF_SELECTED', 'D_UNKNOWN_METHOD', 'E_NOT_A_SAMPLE'}
DELIVERABLES = ['FINAL_RESEARCH_REPORT.md', 'FEATURE_PRIORITIZATION.md', 'UX_BUTTON_FLOW_SPEC.md', 'EXTERNAL_CONNECTION_POLICY_SPEC.md', 'DECISION_AND_OPEN_RISKS.md']
OWN_APP_UNMEASURABLE = re.compile(r'(当アプリ|このアプリ|自社アプリ|本アプリ).{0,20}(継続率|購入確率|購入率|転換率|買収確率|生成速度)')


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open('r', encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def text_at(path: Path) -> str:
    return path.read_text(encoding='utf-8') if path.exists() else ''


def has_substance(path: Path, min_length: int = 400) -> bool:
    s = text_at(path)
    return len(s.strip()) >= min_length and not any(x in s for x in MARKERS)


def ids(value: str) -> set[str]:
    return {x.strip() for x in (value or '').split(';') if x.strip()}


def nonempty(value) -> bool:
    return bool(value is not None and str(value).strip() and str(value).strip().upper() not in ('UNKNOWN', 'N/A', 'NONE', 'NULL'))


def stated_int(text: str, key: str) -> int | None:
    m = re.search(rf'{re.escape(key)}\s*=\s*(\d+)', text)
    return int(m.group(1)) if m else None


def same_rows(a: list[dict], b: list[dict]) -> bool:
    def norm(rows):
        return sorted(json.dumps({k: str(v) for k, v in r.items()}, ensure_ascii=False, sort_keys=True) for r in rows)
    return norm(a) == norm(b)


def inventory_digest(rows: list[dict]) -> str:
    keys = ('calc_id', 'topic_id', 'formula', 'inputs_observed', 'inputs_assumed', 'result', 'status', 'category')
    blob = '\n'.join('|'.join(str(r.get(k, '')) for k in keys) for r in sorted(rows, key=lambda r: r.get('calc_id', '')))
    return hashlib.sha256(blob.encode('utf-8')).hexdigest()


def image_state(root: Path) -> tuple[int, list[str]]:
    d = root / 'reference_images'
    present = list(d.glob('IMG_*'))
    bad = []
    chk = d / 'CHECKSUM_SHA256.txt'
    if chk.exists():
        for line in chk.read_text(encoding='utf-8').splitlines():
            if not line.startswith('IMG_'):
                continue
            name, sha = line.strip().split('\t')
            p = d / name
            if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest() != sha:
                bad.append(name)
    return len(present), bad


def assess(root: Path, scope: dict | None = None) -> dict:
    scope = scope or FULL_SCOPE
    r, research, d = root / 'registry', root / 'research', root / 'deliverables'
    axes, legacy, plans = read_csv(r / 'research_axes.csv'), read_csv(r / 'search_queries_candidates.csv'), read_csv(r / 'search_plans.csv')
    comps, log = read_csv(r / 'competitor_candidates.csv'), read_csv(r / 'search_log.csv')
    sources, smap = read_csv(r / 'source_evidence.csv'), read_csv(r / 'source_topic_map.csv')
    calc, quant, claims = read_csv(r / 'calculation_inventory.csv'), read_csv(r / 'quant_results.csv'), read_csv(r / 'product_claims.csv')
    deps, rep, relations = read_csv(r / 'source_dependencies.csv'), read_csv(r / 'representativeness_audit.csv'), read_csv(r / 'axis_relations.csv')
    nonid, reqtrace = read_csv(r / 'non_identifiable.csv'), read_csv(r / 'requirement_trace.csv')
    try:
        manifest = json.loads(text_at(research / 'research_manifest.json'))
    except ValueError:
        manifest = {}
    try:
        state = json.loads(text_at(research / 'research_status.json'))
    except ValueError:
        state = {}
    accepted = [s for s in sources if s.get('is_accepted', '').strip().lower() == 'yes']
    verified = [s for s in accepted if s.get('review_state') == 'S2_VERIFIED']
    vids = {s['source_id'] for s in verified}
    topic_ids = [a.get('topic_id', '') for a in axes]
    axis_ids = sorted({a.get('axis_id', '') for a in axes})
    conditions: dict[str, list[dict]] = {k: [] for k, _ in STEPS}

    def gate(stage: str, condition: bool, detail: str, unmet: list | None = None, action: str = '') -> None:
        conditions[stage].append({'pass': bool(condition), 'detail': detail, 'unmet': [] if condition else (unmet or [])[:400], 'action': '' if condition else action})

    # ------------------------------------------------------------------ S0
    gate('S0', len(axes) == scope['topics'] and len(set(topic_ids)) == len(axes) and len(axis_ids) == scope['axes'],
         f'scope lock: {len(axes)} topics / {len(axis_ids)} axes (required {scope["topics"]} / {scope["axes"]})', action='restore registry/research_axes.csv; topics may not be deleted')
    lq = [q.get('suggestion_id', '') for q in legacy]
    gate('S0', len(legacy) == scope['legacy'] and len(set(lq)) == len(lq) and all(q.get('topic_id') in set(topic_ids) for q in legacy),
         f'legacy query candidates: {len(legacy)} (required {scope["legacy"]})', action='restore registry/search_queries_candidates.csv')
    gate('S0', {p.get('topic_id') for p in plans} == set(topic_ids) and len(plans) == len(axes), f'search plans cover every topic: {len(plans)}')
    cidl = [c.get('competitor_id', '') for c in comps]
    gate('S0', len(comps) == scope['competitors'] and len(set(cidl)) == len(cidl), f'competitor candidates: {len(comps)} (required {scope["competitors"]})', action='restore registry/competitor_candidates.csv')
    old_axes, old_comp = read_csv(root / 'original_20261109' / 'registry' / 'research_axes.csv'), read_csv(root / 'original_20261109' / 'registry' / 'competitor_candidates.csv')
    gate('S0', {x['topic_id'] for x in old_axes} <= set(topic_ids) and {x['competitor_id'] for x in old_comp} <= set(cidl), 'all original topics and candidates are preserved')
    n_img, bad_img = image_state(root)
    gate('S0', n_img == scope['images'] and not bad_img, f'user reference images present and unmodified: {n_img}/{scope["images"]}', action='place the reference images from the user ZIP into reference_images/ (they are not stored in Git)')
    gate('S0', manifest.get('product_implementation_allowed') is False and manifest.get('research_must_stop_after_report') is True, 'manifest forbids app implementation')
    gate('S0', len(state.get('steps', {})) == 10, 'ten stage records in research_status.json')
    audit = text_at(research / 'REPO_AUDIT.md')
    gate('S0', 'STATUS = AUDITED' in audit and 'REPO_PATH:' in audit and 'REAUDIT_AT:' in audit and len(audit) > 400, 'repository / environment re-audit recorded for this continuation', action='write the re-audit section in research/REPO_AUDIT.md')
    recomputed = build_status.compute(r, write_files=False)
    on_disk = (read_csv(r / 'query_execution_status.csv'), read_csv(r / 'topic_execution_status.csv'), read_csv(r / 'competitor_execution_status.csv'))
    gate('S0', len(on_disk[0]) == scope['legacy'] and len(on_disk[1]) == scope['topics'] and len(on_disk[2]) == scope['competitors'],
         f'status ledgers have a fixed row for every id: queries {len(on_disk[0])}, topics {len(on_disk[1])}, competitors {len(on_disk[2])}', action='python3 scripts/build_status.py')
    gate('S0', same_rows(on_disk[0], recomputed['qrows']) and same_rows(on_disk[1], recomputed['trows']) and same_rows(on_disk[2], recomputed['crows']),
         'status ledgers equal the recomputation from the primary ledgers (not hand-edited, not stale)', action='python3 scripts/build_status.py')
    gate('S0', has_substance(research / 'FULL_SCOPE_EXECUTION_PLAN.md', 800), 'full-scope execution plan exists')
    quarantined = list((d / 'PROVISIONAL_QUARANTINED').glob('*.md')) if (d / 'PROVISIONAL_QUARANTINED').exists() else []
    gate('S0', all('PROVISIONAL_QUARANTINED' in text_at(p)[:400] for p in quarantined), f'earlier provisional deliverables are quarantined with a banner: {len(quarantined)}')

    # ------------------------------------------------------------------ S1
    trows, qrows, crows = recomputed['trows'], recomputed['qrows'], recomputed['crows']
    t_open = [t['topic_id'] + ': ' + t['blockers'] for t in trows if t['gate_state'] != 'S1_DONE']
    gate('S1', not t_open and len(trows) == scope['topics'], f'topics with a complete research-unit collection: {len(trows) - len(t_open)}/{scope["topics"]}', t_open,
         'run the topic worker for the listed topics (legacy queries verbatim, primary / independent / counter routes, unit record)')
    q_state = Counter(q['state'] for q in qrows)
    q_open = [q['suggestion_id'] for q in qrows if q['state'] == 'NOT_EXECUTED']
    gate('S1', not q_open and len(qrows) == scope['legacy'],
         f'legacy queries handled: executed {q_state["EXECUTED"]}, attempted-but-blocked {q_state["ATTEMPTED_BLOCKED"]}, not executed {q_state["NOT_EXECUTED"]} (of {scope["legacy"]})', q_open,
         'execute each listed legacy query verbatim once')
    c_open = [c['competitor_id'] + ' ' + c['name'] + ': ' + c['blockers'] for c in crows if c['gate_state'] != 'S1_DONE']
    gate('S1', not c_open and len(crows) == scope['competitors'], f'competitor candidates explored: {len(crows) - len(c_open)}/{scope["competitors"]}', c_open, 'run the competitor worker for the listed candidates')
    a_open = [t['topic_id'] + ': ' + t['blockers'] for t in recomputed.get('arows', []) if t['gate_state'] != 'S1_DONE']
    gate('S1', not a_open and same_rows(read_csv(r / 'additional_topic_status.csv'), recomputed.get('arows', [])),
         f'additional-hypothesis topics (outside the 325) explored: {len(recomputed.get("arows", [])) - len(a_open)}/{len(recomputed.get("arows", []))}', a_open, 'run the topic worker for the listed additional topics')
    qids = {x.get('query_id') for x in log}
    bad_log = [x.get('query_id', '?') for x in log if not re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}', x.get('searched_at', '')) or not nonempty(x.get('platform')) or not nonempty(x.get('query'))]
    for x in log:
        m = re.search(r'same_action_as=(Q\d+)', x.get('notes', ''))
        if m and m.group(1) not in qids:
            bad_log.append(x.get('query_id', '?'))
    gate('S1', not bad_log and len(qids) == len(log), f'search log integrity (dated, unique ids, valid same-action references): {len(log)} rows', bad_log)
    bad_acc = [s['source_id'] for s in accepted if s.get('verified_state') not in ('DIRECT_ORIGINAL', 'VERIFIED_SECONDARY') or not str(s.get('url', '')).startswith(('https://', 'http://'))
               or (s.get('added_in', '').startswith('sweep') and (s.get('quote_check') != 'FOUND_IN_CACHE' or not nonempty(s.get('quote'))))]
    gate('S1', not bad_acc, f'every accepted source was opened; sweep sources carry a quote found in the fetched page: {len(accepted)} accepted', bad_acc)
    all_src = {s.get('source_id') for s in sources}
    dangling = [m.get('map_id', '?') + '->' + m.get('source_id', '') for m in smap if m.get('source_id') not in all_src]
    for name in ('topic_units.jsonl', 'competitor_units.jsonl'):
        up = r / name
        if up.exists():
            for line in up.read_text(encoding='utf-8').splitlines():
                if line.strip():
                    u = json.loads(line)
                    uid = u.get('topic_id') or u.get('competitor_id')
                    dangling += [f'{uid}->{i}' for i in u.get('source_ids', []) if i not in all_src]
                    dangling += [f'{uid}.{k}->{a.get("source_id")}' for k, a in (u.get('profile') or {}).items() if isinstance(a, dict) and a.get('source_id') and a.get('source_id') not in all_src]
    gate('S1', not dangling, f'no reference points to a source that is missing from the ledger: {len(dangling)} dangling', dangling, 'restore the deleted source rows or re-collect the evidence')
    # executed actions: refused searches (per-turn budget) and same-action/cache rows are attempts or bookkeeping, not executions
    actions = len([x for x in log if 'same_action_as=' not in x.get('notes', '') and x.get('retrieval_status') != 'REFUSED_BUDGET'])
    cov = text_at(research / 'COLLECTION_COVERAGE_AUDIT.md')
    gate('S1', has_substance(research / 'COLLECTION_COVERAGE_AUDIT.md', 500) and stated_int(cov, 'EXECUTED_ACTIONS') == actions,
         f'coverage audit is current (EXECUTED_ACTIONS = {actions})', action='regenerate research/COLLECTION_COVERAGE_AUDIT.md after the last merge')

    # ------------------------------------------------------------------ S2
    pending = [s['source_id'] for s in accepted if s.get('review_state') not in ('S2_VERIFIED', 'S2_REJECTED')]
    gate('S2', not pending and len(accepted) > 0, f'every accepted source reviewed: verified {len(verified)}, pending {len(pending)}', pending, 'run the source-review workers for the pending sources')
    bad_ver = []
    for s in verified:
        if not (nonempty(s.get('quote')) and s.get('quote_check') == 'FOUND_IN_CACHE' and nonempty(s.get('origin_group_id')) and nonempty(s.get('publisher')) and nonempty(s.get('checked_at'))
                and s.get('statement_kind') in STATEMENT_KINDS and nonempty(s.get('page_or_section')) and nonempty(s.get('claim_text'))):
            bad_ver.append(s['source_id'])
    gate('S2', not bad_ver and len(verified) >= min(20, scope['topics']), f'verified sources carry quote, location, kind, origin and date: {len(verified) - len(bad_ver)}/{len(verified)}', bad_ver)
    acc_ids = {s['source_id'] for s in accepted}
    map_bad = [m['map_id'] for m in smap if m.get('source_id') in acc_ids and m.get('review_state') not in ('S2_VERIFIED', 'S2_REJECTED')]
    gate('S2', not map_bad, f'every source-to-unit mapping reviewed: {len(smap) - len(map_bad)}/{len(smap)}', map_bad)
    dep_by = {x.get('source_id'): x for x in deps}
    dep_missing = [s['source_id'] for s in verified if s['source_id'] not in dep_by]
    group_canon = defaultdict(set)
    for s in verified:
        if s['source_id'] in dep_by:
            group_canon[s['origin_group_id']].add(dep_by[s['source_id']].get('canonical_origin', ''))
    split = [g for g, c in group_canon.items() if len(c) != 1 or '' in c]
    independent = len({dep_by[s['source_id']].get('canonical_origin') for s in verified if s['source_id'] in dep_by})
    stated = stated_int(text_at(research / 'SOURCE_DEPENDENCY_AUDIT.md'), 'INDEPENDENT_ORIGINS')
    gate('S2', not dep_missing and not split and stated == independent and independent > 0,
         f'dependency ledger covers every verified source and the stated independent-origin count ({stated}) equals the recomputation ({independent})', dep_missing + ['split origin group: ' + g for g in split],
         'rebuild registry/source_dependencies.csv and restate INDEPENDENT_ORIGINS in research/SOURCE_DEPENDENCY_AUDIT.md')
    gate('S2', has_substance(research / 'CONTRADICTIONS.md', 300) and 'UPDATED_AT = 2026-11-1' in text_at(research / 'CONTRADICTIONS.md'), 'contradictions reviewed for the current evidence set')

    # ------------------------------------------------------------------ S3
    rep_by = {x.get('source_id'): x for x in rep}
    measured = [s['source_id'] for s in verified if s.get('statement_kind') == 'FACT_MEASURED']
    rep_bad = [i for i in measured if i not in rep_by or rep_by[i].get('grade') not in REP_GRADES or not all(str(rep_by[i].get(k, '')).strip() for k in ('population', 'n', 'sampling_method', 'selection_bias'))]
    gate('S3', not rep_bad and bool(measured), f'representativeness graded for every measured source: {len(measured) - len(rep_bad)}/{len(measured)}', rep_bad)
    rel_axes = {x.get('from_axis') for x in relations} | {x.get('to_axis') for x in relations}
    miss_ax = [a for a in axis_ids if a not in rel_axes]
    gate('S3', not miss_ax and has_substance(research / 'AXIS_RELATION_MODEL.md', 1500), f'axis relation model covers all axes: {len(axis_ids) - len(miss_ax)}/{len(axis_ids)}', miss_ax)
    gate('S3', bool(nonid) and all(str(x.get('reason', '')).strip() and str(x.get('data_needed', '')).strip() for x in nonid), f'unidentifiable quantities are listed with reason and required data: {len(nonid)}')
    seg = text_at(research / 'SEGMENT_ANALYSIS.md')
    gate('S3', has_substance(research / 'SEGMENT_ANALYSIS.md', 1000) and 'UPDATED_AT = 2026-11-1' in seg and len([i for i in vids if i in seg]) >= 5 and all(w in seg for w in ('仕事', '学校', '支払', '守秘', '反証')),
         'segment analysis rewritten on the verified evidence set')

    # ------------------------------------------------------------------ S4
    crow_by = {c['competitor_id']: c for c in crows}
    cunits = {}
    cu_path = r / 'competitor_units.jsonl'
    if cu_path.exists():
        for line in cu_path.read_text(encoding='utf-8').splitlines():
            if line.strip():
                u = json.loads(line)
                cunits[u['competitor_id']] = u
    no_reason = [c['competitor_id'] for c in crows if c['comparability'] == 'NOT_COMPARABLE' and not (str(c.get('unverifiable_reason', '')).strip() or str(c.get('blockers', '')).strip())]
    gate('S4', len(crows) == scope['competitors'] and not no_reason, f'every candidate is classed comparable / not comparable with a reason: {len(crows) - len(no_reason)}/{len(crows)}', no_reason)
    unbacked = []
    for cid, u in cunits.items():
        for k, a in (u.get('profile') or {}).items():
            if isinstance(a, dict) and str(a.get('status', '')).startswith('CONFIRMED') and a.get('source_id') not in vids:
                unbacked.append(f'{cid}.{k}')
    gate('S4', not unbacked, f'every confirmed competitor attribute is backed by a verified source: {len(unbacked)} unbacked', unbacked)
    p0_open = [c['competitor_id'] + ' ' + c['name'] for c in comps if c.get('research_priority') == 'P0' and crow_by.get(c['competitor_id'], {}).get('official_confirmed') != 'YES']
    gate('S4', not p0_open, f'highest-priority candidates confirmed from vendor-written material: {sum(c.get("research_priority") == "P0" for c in comps) - len(p0_open)}/{sum(c.get("research_priority") == "P0" for c in comps)}', p0_open,
         'obtain a vendor-written page for the listed candidates or keep the study BLOCKED for them')
    cc = text_at(research / 'COMPETITOR_COMPARISON.md')
    gate('S4', has_substance(research / 'COMPETITOR_COMPARISON.md', 1200) and 'UPDATED_AT = 2026-11-1' in cc, 'competitor comparison rewritten on the verified evidence set')

    # ------------------------------------------------------------------ S5
    calc_topics = {c.get('topic_id') for c in calc}
    no_calc = [t for t in topic_ids if t not in calc_topics]
    gate('S5', not no_calc and bool(calc), f'every topic has at least one calculation id: {len(topic_ids) - len(no_calc)}/{len(topic_ids)}', no_calc)
    bad_calc = []
    for c in calc:
        st, cat = c.get('status'), c.get('category')
        ok = st in TERMINAL_CALC and cat in CATEGORIES and nonempty(c.get('formula')) and nonempty(c.get('target'))
        if st == 'EXECUTED_AND_VERIFIED':
            ok = ok and nonempty(c.get('script')) and nonempty(c.get('result')) and c.get('independent_check') == 'MATCH' and ids(c.get('source_ids', '')) <= vids
            if cat == 'OBSERVED':
                ok = ok and bool(ids(c.get('source_ids', ''))) and not nonempty(c.get('inputs_assumed'))
        if st in ('NON_IDENTIFIABLE', 'BLOCKED_DATA'):
            ok = ok and not re.fullmatch(r'[-+]?[\d.,]+%?', str(c.get('result', '')).strip()) and nonempty(c.get('limits'))
        if st == 'REJECTED_INVALID_METHOD':
            ok = ok and cat == 'INVALID' and nonempty(c.get('limits'))
        if cat == 'OBSERVED' and OWN_APP_UNMEASURABLE.search(str(c.get('target', ''))):
            ok = False
        if not ok:
            bad_calc.append(c.get('calc_id', '?'))
    gate('S5', not bad_calc and bool(calc), f'every calculation id is in a justified terminal state: {len(calc) - len(bad_calc)}/{len(calc)}', bad_calc)
    bad_q = []
    for x in quant:
        cat = x.get('evidence_category')
        if cat not in CATEGORIES:
            bad_q.append(x.get('result_id', '?'))
        elif cat in ('OBSERVED', 'MODEL_BASED', 'MIXED') and not (ids(x.get('source_ids', '')) and ids(x.get('source_ids', '')) <= vids):
            bad_q.append(x.get('result_id', '?'))
        elif cat == 'OBSERVED' and OWN_APP_UNMEASURABLE.search(str(x.get('metric', ''))):
            bad_q.append(x.get('result_id', '?'))
        elif cat == 'NON_IDENTIFIABLE' and re.fullmatch(r'[-+]?[\d.,]+%?', str(x.get('estimate', '')).strip()):
            bad_q.append(x.get('result_id', '?'))
    gate('S5', not bad_q and len(quant) >= 5, f'reported numbers are classified and traceable to verified sources: {len(quant) - len(bad_q)}/{len(quant)}', bad_q)
    try:
        qo = json.loads(text_at(research / 'quant_outputs.json'))
    except ValueError:
        qo = {}
    gate('S5', bool(calc) and qo.get('inventory_digest') == inventory_digest(calc), 'recalculation output matches the current calculation inventory', action='python3 scripts/quant_recompute.py')
    gate('S5', all(has_substance(research / n, 800) and 'UPDATED_AT = 2026-11-1' in text_at(research / n) for n in ('QUANT_MODEL_REPORT.md', 'QUANT_REPRODUCIBILITY.md')), 'quantitative report and reproducibility notes rewritten')

    # ------------------------------------------------------------------ S6
    syn_bad = []
    for a in axis_ids:
        p = research / 'axis_synthesis' / f'{a}.md'
        t = text_at(p)
        if not (has_substance(p, 600) and (any(i in t for i in vids) or 'NO_VERIFIED_SOURCE' in t)):
            syn_bad.append(a)
    gate('S6', not syn_bad, f'axis syntheses exist for every axis: {len(axis_ids) - len(syn_bad)}/{len(axis_ids)}', syn_bad)
    im = text_at(research / 'INTEGRATED_MODEL.md')
    gate('S6', has_substance(research / 'INTEGRATED_MODEL.md', 2000) and all(a in im for a in axis_ids), 'integrated model refers to every axis')

    # ------------------------------------------------------------------ S7
    alt = text_at(research / 'PRODUCT_ALTERNATIVES.md')
    gate('S7', has_substance(research / 'PRODUCT_ALTERNATIVES.md', 1500) and 'UPDATED_AT = 2026-11-1' in alt and all(f'案{x}' in alt for x in 'ABCDEFG')
         and len([i for i in vids if i in alt]) >= 5 and all(w in alt for w in ('買収', '提携', 'ライセンス', '広告')), 'options A-G and the added hypotheses compared on the verified evidence set')
    dec = text_at(research / 'DECISION_ANALYSIS.md')
    try:
        dinp = json.loads(text_at(root / 'scripts' / 'decision_inputs.json'))
        cited = {i for o in dinp.get('payoffs', {}).values() for c in o.values() for i in ids(c.get('evidence', ''))}
    except ValueError:
        cited = {'<unreadable>'}
    gate('S7', has_substance(research / 'DECISION_ANALYSIS.md', 1400) and 'UPDATED_AT = 2026-11-1' in dec and all(w in dec for w in ('下振れ', '期待後悔', '条件付き', 'NON_IDENTIFIABLE')) and cited <= vids,
         'decision analysis is conditional, covers downside and regret, and cites only verified sources', sorted(cited - vids))

    # ------------------------------------------------------------------ S8
    qa = text_at(research / 'REPORT_QA.md')
    gate('S8', has_substance(research / 'REPORT_QA.md', 500) and 'UPDATED_AT = 2026-11-1' in qa and 'APP_IMPLEMENTATION_CHANGED = NO' in qa and '検証' in qa, 'final audit records that no application code was changed')
    req_ids = {x.get('requirement_id') for x in reqtrace}
    need = {f'R{i:02d}' for i in range(1, 18)} | {'N01', 'N02', 'N03'}
    req_bad = sorted(need - req_ids) + [x.get('requirement_id', '?') for x in reqtrace if not str(x.get('status', '')).strip() or not (ids(x.get('source_ids', '')) <= vids)]
    gate('S8', not req_bad, f'every user requirement and added hypothesis is traced to evidence or to a stated unknown: {len(need) - len(set(req_bad) & need)}/{len(need)}', req_bad)
    claim_bad = [x.get('claim_id', '?') for x in claims if not (ids(x.get('source_ids', '')) <= vids)]
    gate('S8', bool(claims) and not claim_bad, f'product claims cite only verified sources: {len(claims) - len(claim_bad)}/{len(claims)}', claim_bad)

    # ------------------------------------------------------------------ S9
    formal = [n for n in DELIVERABLES if (d / n).exists()]
    earlier_ok = all(all(c['pass'] for c in conditions[k]) for k, _ in STEPS[:9])
    gate('S9', len(formal) == len(DELIVERABLES) and all(has_substance(d / n, 700) and 'RESEARCH_STATUS = COMPLETE' in text_at(d / n) for n in DELIVERABLES), f'formal deliverables present: {len(formal)}/{len(DELIVERABLES)}')
    rpt = text_at(d / 'FINAL_RESEARCH_REPORT.md')
    gate('S9', len([i for i in vids if i in rpt]) >= 8 and all(w in rpt for w in ('文字入力', '学校', '仕事', '外部接続', '競合', '統計')), 'final report cites verified sources and covers the fixed requirements')
    violation = bool(formal) and not earlier_ok
    gate('S9', not violation, 'no formal deliverable exists before S0-S8 pass', formal if violation else [], 'move the files to deliverables/PROVISIONAL_QUARANTINED/')

    out, prior = {}, True
    first_fail = None
    for key, label in STEPS:
        checks = conditions[key]
        own = all(c['pass'] for c in checks)
        if prior and own:
            st = 'PASS'
        elif not own:
            st = 'FAIL'
        else:
            st = f'LOCKED_BY_{first_fail}'
        if not (prior and own) and first_fail is None:
            first_fail = key
        out[key] = {'label': label, 'state': st, 'checks': checks, 'pass_count': sum(c['pass'] for c in checks), 'total_checks': len(checks)}
        prior = prior and own
    external = []
    if q_state['ATTEMPTED_BLOCKED']:
        external.append(f'{q_state["ATTEMPTED_BLOCKED"]} legacy queries could not be executed')
    if p0_open:
        external.append(f'{len(p0_open)} highest-priority competitors lack vendor-written confirmation')
    overall = 'COMPLETE' if prior else ('BLOCKED' if (first_fail and all(not c['pass'] and 'BLOCKED' in c.get('action', '') for c in conditions[first_fail] if not c['pass'])) else 'INCOMPLETE')
    return {'research_status': overall, 'checked_at': datetime.now(timezone.utc).isoformat(), 'first_unmet_stage': first_fail,
            'source_rows': len(sources), 'accepted_rows': len(accepted), 'verified_rows': len(verified), 'independent_origins': independent,
            'verified_competitors': sum(c['official_confirmed'] == 'YES' for c in crows), 'executed_actions': actions,
            'legacy_queries': dict(q_state), 'topics_s1_done': len(trows) - len(t_open), 'competitors_s1_done': len(crows) - len(c_open),
            'calculation_ids': len(calc), 'formal_deliverable_violation': violation, 'external_blocks': external, 'steps': out,
            'warning': 'Mechanical checks do not establish source truth, sample representativeness or statistical validity; independent review required.'}


def audit_detail(result: dict) -> str:
    lines = ['# ゲート監査の詳細（機械生成）', '', f"生成時刻（UTC）：{result['checked_at']}", '', f"RESEARCH_STATUS = {result['research_status']}",
             f"最初に未達の工程：{result['first_unmet_stage'] or 'なし'}", '',
             f"- 実行した検索・アクセス：{result['executed_actions']}", f"- 採用資料：{result['accepted_rows']}（うちS2精査済み {result['verified_rows']}、独立起源 {result['independent_origins']}）",
             f"- テーマ（S1完了）：{result['topics_s1_done']}", f"- 旧検索候補：{json.dumps(result['legacy_queries'], ensure_ascii=False)}",
             f"- 競合候補（S1完了）：{result['competitors_s1_done']}、公式確認 {result['verified_competitors']}", f"- 計算ID：{result['calculation_ids']}", '']
    if result['external_blocks']:
        lines += ['## 外部要因による未達', ''] + [f'- {x}' for x in result['external_blocks']] + ['']
    for key, step in result['steps'].items():
        lines += [f"## {key} {step['label']}：{step['state']}（{step['pass_count']}/{step['total_checks']}）", '']
        for c in step['checks']:
            lines.append(f"- {'PASS' if c['pass'] else 'FAIL'}：{c['detail']}")
            if not c['pass']:
                if c.get('action'):
                    lines.append(f"  - 次の要求アクション：{c['action']}")
                if c.get('unmet'):
                    shown = c['unmet'][:60]
                    lines.append(f"  - 未達 {len(c['unmet'])} 件（先頭{len(shown)}件）：" + ' ／ '.join(str(x)[:90] for x in shown))
        lines.append('')
    lines += ['機械検査は、文書や台帳の整合を確かめるだけで、出典の真偽や標本の代表性を保証しない。', '']
    return '\n'.join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['check', 'evaluate'], nargs='?', default='check')
    parser.add_argument('--root', default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    root = Path(args.root).resolve()
    result = assess(root)
    if args.action == 'evaluate':
        (root / 'research').mkdir(exist_ok=True, parents=True)
        (root / 'research' / 'gate_evaluation.json').write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding='utf-8')
        (root / 'research' / 'GATE_AUDIT_DETAIL.md').write_text(audit_detail(result), encoding='utf-8')
        sp = root / 'research' / 'research_status.json'
        if sp.exists():
            cur = json.loads(sp.read_text(encoding='utf-8'))
            cur['research_state'] = result['research_status']
            cur['last_evaluated'] = result['checked_at']
            for sid, step in result['steps'].items():
                e = cur.setdefault('steps', {}).setdefault(sid, {})
                e['state'] = step['state']
                e['evaluated_at'] = result['checked_at']
                e['failure_reasons'] = [c['detail'] for c in step['checks'] if not c['pass']]
            sp.write_text(json.dumps(cur, ensure_ascii=False, indent=2), encoding='utf-8')
    print('RESEARCH_STATUS:', result['research_status'], '| first unmet stage:', result['first_unmet_stage'])
    print('Actions:', result['executed_actions'], 'Accepted:', result['accepted_rows'], 'Verified:', result['verified_rows'], 'Independent origins:', result['independent_origins'])
    for key, step in result['steps'].items():
        print(f'{key} {step["state"]} ({step["pass_count"]}/{step["total_checks"]})')
        for c in step['checks']:
            if not c['pass']:
                print('  - FAIL:', c['detail'])
    print('NOTICE:', result['warning'])


if __name__ == '__main__':
    main()
