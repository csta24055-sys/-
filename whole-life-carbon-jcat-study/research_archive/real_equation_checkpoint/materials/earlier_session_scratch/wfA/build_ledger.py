import json, sys, collections
from pathlib import Path
sys.dont_write_bytecode = True
import authored_units as A

ROOT = Path('/home/user/-/whole-life-carbon-jcat-study'); OUT = ROOT/'09_APPROX_STUDY/01_LEDGER'
formulas = {f['id']: f for f in json.load(open(ROOT/'04_FORMULAS/formulas.json'))['formulae']}
fam = json.load(open(OUT/'sheet_families.json'))['families']
fam_by_name = {f['family']: f for f in fam}
GATES = {'SYS-01', 'SYS-02', 'SYS-03'}

units = []
for fn in ('ledger_pre_qa_sum_sto.json', 'ledger_a_stages.json'):
    for e in json.load(open(fn)):
        e['author'] = 'ANALYST'
        units.append(e)
for e in A.EXISTING:
    f = formulas[e['id']]
    e = dict(e)
    e.update(name=f['name'], stage=f['stage'], origin='EXISTING_53', evidence_level='EXISTING_CONCEPT',
             inputs=list(f['inputs']) + e.pop('inputs_extra'), output=f['output'], author='MAIN_SESSION')
    units.append(e)
for e in A.ADDITIONAL:
    e = dict(e); e.pop('inputs_extra', None)
    e.update(origin='ADDITIONAL', author='MAIN_SESSION')
    units.append(e)

ids = [u['id'] for u in units]
assert len(ids) == len(set(ids)), 'duplicate ids'
assert set(formulas) <= set(ids), sorted(set(formulas) - set(ids))
idset = set(ids)
order = list(formulas) + sorted(i for i in ids if i.startswith('X-'))
units.sort(key=lambda u: order.index(u['id']))

for u in units:
    # sheet family links: names -> ids (authored) ; analysts gave ids already
    if 'sheet_family_names' in u:
        names = u.pop('sheet_family_names')
        missing = [n for n in names if n not in fam_by_name]
        assert not missing, (u['id'], missing)
        u['sheet_family_links'] = [fam_by_name[n]['family_id'] for n in names]
    # analyst links to zero-formula families are dropped (they were id guesses for presentation sheets)
    u['sheet_family_links'] = [s for s in u.get('sheet_family_links', []) if any(f['family_id'] == s and f['formula_xml_nodes'] > 0 for f in fam)]
    # gates are preconditions, not data dependencies
    deps = [d for d in u.get('depends_on', []) if d in idset]
    if u['id'] not in GATES:
        u['preconditions'] = sorted(d for d in deps if d in GATES)
        deps = [d for d in deps if d not in GATES]
    else:
        u['preconditions'] = []
    u['depends_on'] = sorted(set(deps))
    u['similar_units'] = sorted({s for s in u.get('similar_units', []) if s in idset and s != u['id']})
    u['n_inputs'] = len(u['inputs'])
    u.setdefault('structure_subclass', None); u.setdefault('ambiguities', []); u.setdefault('evidence', [])
    u.setdefault('not_computable_reason', None)
    u.pop('feeds', None)

# study design decision: A13-04 gets an independently designed model so that it can be researched
a1304 = next(u for u in units if u['id'] == 'A13-04')
a1304.update(structure_class='RATIO', structure_subclass='UNDEFINED_MODEL', computable_in_reference=True, not_computable_reason=None,
             canonical_form='E_unq = sum_i e_i * r_i / (1 - r_i),  0 <= r_i < 1   (本研究が独立に設計した上乗せ式。概念式そのものはモデル未定義)',
             loop_dims=['items'], complexity='O(N)', depends_on=['A13-01', 'A13-03'])
a1304['ambiguities'] = list(a1304.get('ambiguities', [])) + ['概念式はモデル未定義。基準計算では、行ごとの未数量費用比率 r による上乗せ（独立設計）を採用した。J-CAT の工事分倍率とは無関係で、その値も使わない']
# new units created in this ledger must appear in the existing units' dependencies
def add_dep(uid, dep):
    u = next(x for x in units if x['id'] == uid)
    if dep not in u['depends_on']:
        u['depends_on'] = sorted(set(u['depends_on']) | {dep})
for uid in ('SUM-01', 'SUM-02', 'SUM-03', 'SUM-07'):
    u = next(x for x in units if x['id'] == uid); u['depends_on'] = ['X-02']
for uid in ('SUM-04', 'SUM-05', 'SUM-06', 'SUM-08'):
    add_dep(uid, 'SUM-03')
qa01 = next(x for x in units if x['id'] == 'QA-01'); qa01['depends_on'] = sorted(set(qa01['depends_on']) | {'X-02', 'X-01', 'X-14'})
add_dep('A13-01', 'X-15'); add_dep('A13-03', 'X-15'); add_dep('A4-01', 'X-15'); add_dep('A4-02', 'X-15')
add_dep('B3-02', 'X-01')

by = {u['id']: u for u in units}
for u in units:
    bad = [d for d in u['depends_on'] if d not in by]
    assert not bad, (u['id'], bad)
# feeds = inverse of depends_on ; similar_units symmetric
feeds = collections.defaultdict(set)
for u in units:
    for d in u['depends_on']:
        feeds[d].add(u['id'])
sim = collections.defaultdict(set)
for u in units:
    for s in u['similar_units']:
        sim[u['id']].add(s); sim[s].add(u['id'])
for u in units:
    u['feeds'] = sorted(feeds[u['id']])
    u['similar_units'] = sorted(sim[u['id']])
    u['gated_by'] = u.pop('preconditions')
# cycle check
state = {}
def visit(i, chain=()):
    if state.get(i) == 2: return
    assert state.get(i) != 1, 'cycle: ' + ' -> '.join(chain + (i,))
    state[i] = 1
    for d in by[i]['depends_on']: visit(d, chain + (i,))
    state[i] = 2
for i in by: visit(i)

KEYS = ['id', 'name', 'stage', 'origin', 'evidence_level', 'evidence', 'author', 'purpose', 'inputs', 'n_inputs', 'output',
        'structure_class', 'structure_subclass', 'canonical_form', 'loop_dims', 'branches', 'complexity', 'depends_on', 'feeds',
        'gated_by', 'similar_units', 'unification_potential', 'approximation_potential', 'expected_precision_loss',
        'boundary_unit_caveats', 'sheet_family_links', 'computable_in_reference', 'not_computable_reason', 'ambiguities',
        'reference_semantics_proposal']
VOCAB = {'LINEAR_SUM_PRODUCT', 'WEIGHTED_AVERAGE', 'MATRIX_EXPANSION', 'TIME_SERIES_SUM', 'RECURRENCE', 'EVENT_SCHEDULE', 'COUNT_FLOOR',
         'SUM_OF_STAGES', 'RATIO', 'MAX_CLAMP', 'PREDICATE_GATE', 'MASS_BALANCE_CONSTRAINT', 'LOOKUP_JOIN', 'UNDEFINED_MODEL'}
out_units = []
for u in units:
    assert u['structure_class'] in VOCAB, (u['id'], u['structure_class'])
    for k in ('purpose', 'canonical_form', 'unification_potential', 'approximation_potential', 'expected_precision_loss'):
        assert u.get(k), (u['id'], k)
    out_units.append({k: u.get(k) for k in KEYS if k in u or k != 'reference_semantics_proposal'})
counts = collections.Counter(u['structure_class'] for u in out_units)
ledger = {
 'schema_version': '1.1', 'generated': '2026-11-11', 'protocol': '00_POLICY/EVALUATION_PROTOCOL.md (P2, P3)',
 'scope_statement': '本台帳は独立概念モデルの計算構造だけを対象とする。原版ブックの数式本文は確認しておらず、約 382 万の数式ノードを調査したものではない。追加単位（X-）はシート名・未接続の入力項目・既存資料の記述から推定した独立設計の案であり、原版の式の再現ではない。',
 'authorship_note': 'author=ANALYST の 29 件は独立した分析担当 2 名が作成（reference_semantics_proposal は提案であり、基準計算が実際に採用した定義は reference_semantics に記載）。author=MAIN_SESSION の 41 件は主担当が作成。',
 'dependency_note': 'depends_on は計算結果の受け渡しだけを表す。入力検査（SYS-01・SYS-02・SYS-03）は gated_by に分けた。feeds は depends_on の逆引き。',
 'unit_count': len(out_units), 'existing_unit_count': sum(u['origin'] == 'EXISTING_53' for u in out_units),
 'additional_unit_count': sum(u['origin'] == 'ADDITIONAL' for u in out_units),
 'structure_class_counts': dict(sorted(counts.items(), key=lambda kv: -kv[1])), 'units': out_units,
}
json.dump(ledger, open(OUT/'units.json', 'w'), ensure_ascii=False, indent=1)

# sheet family coverage
cov = []
assert set(A.FAMILY_COVERAGE) == set(fam_by_name), (set(fam_by_name) ^ set(A.FAMILY_COVERAGE))
tot = collections.Counter(); nfam = collections.Counter()
for f in fam:
    status, rel, note = A.FAMILY_COVERAGE[f['family']]
    assert all(r in by for r in rel), (f['family'], rel)
    cov.append({'family_id': f['family_id'], 'family': f['family'], 'formula_xml_nodes': f['formula_xml_nodes'],
                'share_of_all_nodes': f['share_of_all_nodes'], 'status': status, 'related_units': rel,
                'correspondence_evidence': 'INFERRED_FROM_NAME_ONLY', 'note': note})
    tot[status] += f['formula_xml_nodes']; nfam[status] += 1
allnodes = sum(f['formula_xml_nodes'] for f in fam)
json.dump({'schema_version': '1.0', 'generated': '2026-11-11',
           'warning': '対応はシート名だけからの推定で、原版の式の内容は確認していない。「対応あり」は、その名称が示す計算構造を独立モデルの評価単位が表しているという意味であり、原版の式を調査・再現したという意味ではない。',
           'family_count': len(cov), 'families_by_status': dict(nfam),
           'node_share_by_status': {k: round(v/allnodes, 6) for k, v in tot.items()}, 'families': cov},
          open(OUT/'sheet_family_coverage.json', 'w'), ensure_ascii=False, indent=1)

links = json.load(open(ROOT/'06_LINEAGE/links.json'))
unl = [x['input_id'] for x in links['links_by_input'] if x['linkage_status'] == 'NOT_YET_LINKED']
assert set(unl) == set(A.UNLINKED), (set(unl) ^ set(A.UNLINKED))
disp = [{'input_id': i, 'disposition': A.UNLINKED[i][0], 'related_units': A.UNLINKED[i][1], 'note': A.UNLINKED[i][2]} for i in unl]
assert all(r in by for d in disp for r in d['related_units'])
json.dump({'schema_version': '1.0', 'generated': '2026-11-11', 'input_count': len(disp),
           'counts': dict(collections.Counter(d['disposition'] for d in disp)), 'inputs': disp},
          open(OUT/'unlinked_input_disposition.json', 'w'), ensure_ascii=False, indent=1)
json.dump({'schema_version': '1.0', 'generated': '2026-11-11', 'not_adopted': A.NOT_ADOPTED},
          open(OUT/'considered_not_adopted.json', 'w'), ensure_ascii=False, indent=1)
print('units', len(out_units), dict(counts))
print('families', dict(nfam), {k: round(v/allnodes, 4) for k, v in tot.items()})
print('unlinked', collections.Counter(d['disposition'] for d in disp))
print('max feeds', sorted(((len(u['feeds']), u['id']) for u in out_units), reverse=True)[:6])
