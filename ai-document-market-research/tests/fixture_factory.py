"""Build a tiny, fully consistent research project that passes every gate.

Used only by the fault-injection tests: each test breaks ONE thing in a copy of this
fixture and asserts that the gate stops passing. The fixture content is synthetic test
data and is never mixed with the real ledgers.
"""
from __future__ import annotations
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import build_status  # noqa: E402
import research_gates  # noqa: E402

SCOPE = {'axes': 2, 'topics': 3, 'legacy': 4, 'competitors': 2, 'images': 0}
TOPICS = [('AXIS_01', 'AXIS_01_T01'), ('AXIS_01', 'AXIS_01_T02'), ('AXIS_02', 'AXIS_02_T01')]
LEGACY = [('AXIS_01_T01_Q1', 'AXIS_01', 'AXIS_01_T01', 'PRIMARY', 'alpha official report'), ('AXIS_01_T01_Q3', 'AXIS_01', 'AXIS_01_T01', 'COUNTEREXAMPLE', 'alpha failure'),
          ('AXIS_02_T01_Q2', 'AXIS_02', 'AXIS_02_T01', 'USER_VOICE', 'beta users'), ('AXIS_02_T01_Q4', 'AXIS_02', 'AXIS_02_T01', 'INTERNATIONAL', 'beta survey')]
ATTRS = build_status.ATTRS


def w(path: Path, fields: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        x = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        x.writeheader()
        x.writerows(rows)


def filler(n: int, head: str = '') -> str:
    body = '検査用の合成文書である。実在の調査結果ではない。'
    return head + '\n' + (body * (n // len(body) + 1))[:n] + '\n'


def build(root: Path) -> Path:
    reg, res, deliv = root / 'registry', root / 'research', root / 'deliverables'
    for d in (reg, res, deliv, root / 'reference_images', root / 'scripts', root / 'original_20261109' / 'registry', res / 'axis_synthesis'):
        d.mkdir(parents=True, exist_ok=True)
    axes = [{'axis_id': a, 'axis_name': a, 'topic_id': t, 'topic_name': t, 'stage': '', 'notes': '', 'origin': 'ORIGINAL', 'priority': 'P0', 'canonical_question': 'q'} for a, t in TOPICS]
    w(reg / 'research_axes.csv', list(axes[0]), axes)
    w(root / 'original_20261109' / 'registry' / 'research_axes.csv', list(axes[0]), axes[:1])
    w(reg / 'search_queries_candidates.csv', ['suggestion_id', 'axis_id', 'topic_id', 'target', 'sample_query', 'state', 'last_searched', 'notes'],
      [{'suggestion_id': s, 'axis_id': a, 'topic_id': t, 'target': g, 'sample_query': q} for s, a, t, g, q in LEGACY])
    w(reg / 'search_plans.csv', ['plan_id', 'axis_id', 'topic_id'], [{'plan_id': t + '_PLAN', 'axis_id': a, 'topic_id': t} for a, t in TOPICS])
    comps = [{'competitor_id': 'C001', 'name': 'Alpha', 'research_priority': 'P0', 'market_role': 'DIRECT', 'verification_state': 'UNVERIFIED_CANDIDATE', 'sources': ''},
             {'competitor_id': 'C002', 'name': 'Beta', 'research_priority': 'P2', 'market_role': 'DIRECT', 'verification_state': 'UNVERIFIED_CANDIDATE', 'sources': ''}]
    w(reg / 'competitor_candidates.csv', list(comps[0]), comps)
    w(root / 'original_20261109' / 'registry' / 'competitor_candidates.csv', list(comps[0]), comps[:1])

    log, src, smap, units, cunits = [], [], [], [], []
    n = {'q': 0, 's': 0, 'm': 0}

    def add_log(unit_kind, unit_id, topic, platform, query, route='', sid='', status='SNIPPET_ONLY'):
        n['q'] += 1
        log.append({'query_id': f"Q{n['q']:04d}", 'searched_at': '2026-11-12T00:00:00Z', 'platform': platform, 'query': query, 'results_found': '5', 'notes': '',
                    'axis_id': topic[:7], 'topic_id': topic, 'retrieval_status': status, 'suggestion_id': sid, 'route': route, 'followup_for': '',
                    'unit_kind': unit_kind, 'unit_id': unit_id, 'executor': 'worker:test', 'verified_by': 'TRANSCRIPT', 'blocked_reason': '', 'candidate_urls': ''})

    def add_source(unit_kind, unit_id, topic, role, group, stype='ACADEMIC', kind='FACT_MEASURED'):
        n['s'] += 1
        sid = f"S{n['s']:03d}"
        src.append({'source_id': sid, 'origin_group_id': group, 'url': f'https://example.org/{sid}', 'publisher': 'pub', 'published_at': '2026', 'checked_at': '2026-11-12T00:00:00Z',
                    'source_type': stype, 'country': 'JP', 'segment': 'x', 'axis_id': topic[:7], 'topic_id': topic, 'verified_state': 'DIRECT_ORIGINAL', 'is_accepted': 'yes',
                    'claim_text': 'claim', 'page_or_section': 'sec', 'n': '100', 'population': 'pop', 'selection_method': 'random', 'method': 'survey', 'unit': '%', 'notes': '',
                    'quote': 'a verbatim quote of enough length', 'quote_check': 'FOUND_IN_CACHE', 'statement_kind': kind, 'origin_org': group, 'added_in': 'sweep_test',
                    'review_state': 'S2_VERIFIED', 'review_notes': ''})
        n['m'] += 1
        smap.append({'map_id': f"M{n['m']:05d}", 'source_id': sid, 'unit_kind': unit_kind, 'unit_id': unit_id, 'role': role, 'claim_text': 'claim',
                     'quote': 'a verbatim quote of enough length', 'quote_check': 'FOUND_IN_CACHE', 'added_by': 'worker:test', 'review_state': 'S2_VERIFIED', 'review_notes': ''})
        add_log(unit_kind, unit_id, topic, 'direct_fetch:web_page', f'GET https://example.org/{sid}', route=role, status='RETRIEVED_FULL_TEXT')
        return sid

    for s, a, t, g, q in LEGACY:
        add_log('TOPIC', t, t, 'web_search_engine', q, route='LEGACY', sid=s)
    for a, t in TOPICS:
        got = []
        for route in ('PRIMARY', 'INDEPENDENT', 'COUNTER'):
            add_log('TOPIC', t, t, 'web_search_engine', f'{t} {route} search', route=route)
            got.append(add_source('TOPIC', t, t, route, f'OG_{t}_{route}'))
        units.append({'topic_id': t, 'definition': {'operational_definition': 'd', 'population_and_unit': 'p', 'business_question': 'b'},
                      'calculations_proposed': [{'target': 'x'}], 'non_identifiable': [], 'source_ids': got})
    for c in comps:
        cid = c['competitor_id']
        add_log('COMPETITOR', cid, 'AXIS_01_T01', 'web_search_engine', f'{cid} official', route='PRIMARY')
        add_log('COMPETITOR', cid, 'AXIS_01_T01', 'web_search_engine', f'{cid} complaints', route='COUNTER')
        sid = add_source('COMPETITOR', cid, 'AXIS_01_T01', 'PRIMARY', f'OG_{cid}', stype='OFFICIAL_VENDOR', kind='VENDOR_CLAIM')
        cunits.append({'competitor_id': cid, 'profile': {k: {'status': 'CONFIRMED_OFFICIAL', 'value': 'v', 'source_url': f'https://example.org/{sid}', 'quote': 'q', 'source_id': sid} for k in ATTRS},
                       'counter_findings': [], 'blockers': ''})
    w(reg / 'search_log.csv', list(log[0]), log)
    w(reg / 'source_evidence.csv', list(src[0]), src)
    w(reg / 'source_topic_map.csv', list(smap[0]), smap)
    (reg / 'topic_units.jsonl').write_text(''.join(json.dumps(u, ensure_ascii=False) + '\n' for u in units), encoding='utf-8')
    (reg / 'competitor_units.jsonl').write_text(''.join(json.dumps(u, ensure_ascii=False) + '\n' for u in cunits), encoding='utf-8')
    vids = [s['source_id'] for s in src]
    w(reg / 'source_dependencies.csv', ['source_id', 'origin_group_id', 'canonical_origin', 'dependency_type', 'depends_on', 'note'],
      [{'source_id': s['source_id'], 'origin_group_id': s['origin_group_id'], 'canonical_origin': s['origin_group_id'], 'dependency_type': 'ORIGINAL'} for s in src])
    w(reg / 'representativeness_audit.csv', ['source_id', 'population', 'n', 'sampling_method', 'selection_bias', 'grade'],
      [{'source_id': s['source_id'], 'population': 'pop', 'n': '100', 'sampling_method': 'random', 'selection_bias': 'low', 'grade': 'A_PROBABILITY_SAMPLE'} for s in src if s['statement_kind'] == 'FACT_MEASURED'])
    w(reg / 'axis_relations.csv', ['from_axis', 'to_axis', 'relation'], [{'from_axis': 'AXIS_01', 'to_axis': 'AXIS_02', 'relation': 'shares demand evidence'}])
    w(reg / 'non_identifiable.csv', ['topic_id', 'quantity', 'reason', 'data_needed'], [{'topic_id': 'AXIS_01_T01', 'quantity': 'x', 'reason': 'no data', 'data_needed': 'survey'}])
    calc = [{'calc_id': f'CALC_{t}_01', 'topic_id': t, 'target': 'share', 'formula': 'a/b', 'inputs_observed': 'a=1;b=2', 'inputs_assumed': '', 'script': 'calc.py',
             'result': '0.5', 'independent_check': 'MATCH', 'status': 'EXECUTED_AND_VERIFIED', 'category': 'OBSERVED', 'source_ids': vids[0], 'limits': 'fixture'} for _, t in TOPICS]
    w(reg / 'calculation_inventory.csv', list(calc[0]), calc)
    w(reg / 'quant_results.csv', ['result_id', 'metric', 'estimate', 'evidence_category', 'source_ids', 'sample_n'],
      [{'result_id': f'QR{i}', 'metric': 'm', 'estimate': '1', 'evidence_category': 'OBSERVED', 'source_ids': vids[0], 'sample_n': '100'} for i in range(5)])
    w(reg / 'product_claims.csv', ['claim_id', 'text', 'source_ids'], [{'claim_id': 'PC01', 'text': 't', 'source_ids': vids[0]}])
    need = [f'R{i:02d}' for i in range(1, 18)] + ['N01', 'N02', 'N03']
    w(reg / 'requirement_trace.csv', ['requirement_id', 'status', 'source_ids'], [{'requirement_id': r, 'status': 'TRACED', 'source_ids': vids[0]} for r in need])

    (res / 'research_manifest.json').write_text(json.dumps({'product_implementation_allowed': False, 'research_must_stop_after_report': True}), encoding='utf-8')
    (res / 'research_status.json').write_text(json.dumps({'steps': {f'S{i}': {} for i in range(10)}}), encoding='utf-8')
    (res / 'quant_outputs.json').write_text(json.dumps({'inventory_digest': research_gates.inventory_digest(calc)}), encoding='utf-8')
    (root / 'scripts' / 'decision_inputs.json').write_text(json.dumps({'payoffs': {'A': {'alpha': {'score': 0, 'evidence': vids[0]}}}}), encoding='utf-8')
    up = 'UPDATED_AT = 2026-11-12\n'
    cite = ' '.join(vids)
    (res / 'REPO_AUDIT.md').write_text(filler(500, 'STATUS = AUDITED\nREPO_PATH: fixture\nREAUDIT_AT: 2026-11-12'), encoding='utf-8')
    (res / 'FULL_SCOPE_EXECUTION_PLAN.md').write_text(filler(900), encoding='utf-8')
    actions = len([x for x in log if 'same_action_as=' not in x['notes']])
    (res / 'COLLECTION_COVERAGE_AUDIT.md').write_text(filler(600, f'EXECUTED_ACTIONS = {actions}'), encoding='utf-8')
    (res / 'SOURCE_DEPENDENCY_AUDIT.md').write_text(filler(600, f'INDEPENDENT_ORIGINS = {len({s["origin_group_id"] for s in src})}'), encoding='utf-8')
    (res / 'CONTRADICTIONS.md').write_text(filler(400, up), encoding='utf-8')
    (res / 'AXIS_RELATION_MODEL.md').write_text(filler(1600), encoding='utf-8')
    (res / 'SEGMENT_ANALYSIS.md').write_text(filler(1100, up + cite + ' 仕事 学校 支払 守秘 反証'), encoding='utf-8')
    (res / 'COMPETITOR_COMPARISON.md').write_text(filler(1300, up), encoding='utf-8')
    for name in ('QUANT_MODEL_REPORT.md', 'QUANT_REPRODUCIBILITY.md'):
        (res / name).write_text(filler(900, up), encoding='utf-8')
    for a in ('AXIS_01', 'AXIS_02'):
        (res / 'axis_synthesis' / f'{a}.md').write_text(filler(700, vids[0]), encoding='utf-8')
    (res / 'INTEGRATED_MODEL.md').write_text(filler(2100, 'AXIS_01 AXIS_02'), encoding='utf-8')
    (res / 'PRODUCT_ALTERNATIVES.md').write_text(filler(1600, up + cite + ' 案A 案B 案C 案D 案E 案F 案G 買収 提携 ライセンス 広告'), encoding='utf-8')
    (res / 'DECISION_ANALYSIS.md').write_text(filler(1500, up + '下振れ 期待後悔 条件付き NON_IDENTIFIABLE'), encoding='utf-8')
    (res / 'REPORT_QA.md').write_text(filler(600, up + 'APP_IMPLEMENTATION_CHANGED = NO 検証'), encoding='utf-8')
    for name in research_gates.DELIVERABLES:
        (deliv / name).write_text(filler(800, 'RESEARCH_STATUS = COMPLETE\n' + cite + ' 文字入力 学校 仕事 外部接続 競合 統計'), encoding='utf-8')
    build_status.compute(reg, write_files=True)
    return root
