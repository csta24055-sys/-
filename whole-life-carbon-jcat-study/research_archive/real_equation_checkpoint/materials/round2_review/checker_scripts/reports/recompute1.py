import json, collections, math, sys
R='/home/user/-/whole-life-carbon-jcat-study/09_APPROX_STUDY/'
L=lambda p: json.load(open(R+p))
units=L('01_LEDGER/units.json'); cov=L('01_LEDGER/sheet_family_coverage.json'); fam=L('01_LEDGER/sheet_families.json')
unl=L('01_LEDGER/unlinked_input_disposition.json'); cna=L('01_LEDGER/considered_not_adopted.json')
pri=L('02_RANKING/research_priority.json'); axa=L('02_RANKING/axis_a.json'); axb=L('02_RANKING/axis_b.json')
models=L('03_MODELS/models.json'); cands=L('03_MODELS/candidates.json'); recs=L('03_MODELS/records/units.json')
ex=L('04_VERIFICATION/unified_model_exactness.json'); load=L('04_VERIFICATION/unified_model_load.json')
iu=L('04_VERIFICATION/input_usage.json'); ap=L('04_VERIFICATION/approximation_study.json'); prog=L('05_DECISIONS/progress_ledger.json')
C=collections.Counter
U=units['units']
print('units',len(U),units['unit_count'], C(u['origin'] for u in U))
print('structure', C(u['structure_class'] for u in U).most_common())
print('declared', units['structure_class_counts'])
print('computable', C(u['computable_in_reference'] for u in U))
# inputs referenced
ins=set()
for u in U:
    for i in u['inputs']: ins.add(i if isinstance(i,str) else json.dumps(i,ensure_ascii=False))
new=[i for i in ins if i.startswith('NEW:')]
print('distinct inputs',len(ins),'new',len(new),'existing',len(ins)-len(new))
print('sample', list(ins)[:5])
spec=json.load(open(R+'../03_INPUTS/inputs.json'))
print('spec type',type(spec), (list(spec.keys())[:10] if isinstance(spec,dict) else len(spec)))
# coverage
F=cov['families']
st=C(f['status'] for f in F); print('cov status',st, cov['families_by_status'])
nodes=collections.defaultdict(int)
for f in F: nodes[f['status']]+=f['formula_xml_nodes']
tot=sum(nodes.values()); print('nodes',dict(nodes),tot, fam['total_formula_nodes'])
for k,v in nodes.items(): print(' ',k,v, '%.4f%%'%(100*v/tot), cov['node_share_by_status'][k])
print('fam count',fam['family_count'],len(fam['families']), 'with formulas', sum(1 for f in fam['families'] if f['formula_xml_nodes']>0), fam['families_with_formulas'],'sheets',sum(f['sheet_count'] for f in fam['families']))
print('covered-with-zero-formulas', [ (f['family'],f['status']) for f in F if f['status'].startswith('COVERED') and f['formula_xml_nodes']==0])
print('not inspected', [(f['family'],f['formula_xml_nodes']) for f in F if f['status']=='NOT_INSPECTED'])
print('top12'); 
for f in sorted(F,key=lambda f:-f['formula_xml_nodes'])[:12]: print('  ',f['family'],f['formula_xml_nodes'],'%.2f'%(100*f['share_of_all_nodes']),f['related_units'],f['status'])
print('suffix',fam['nodes_by_scope_suffix'])
# coverage vs fam consistent?
fm={f['family_id']:f for f in fam['families']}
for f in F:
    g=fm[f['family_id']]
    if g['family']!=f['family'] or g['formula_xml_nodes']!=f['formula_xml_nodes']: print('MISMATCH fam',f['family_id'])
# links
uid={u['id'] for u in U}
link_from_cov=collections.defaultdict(set)
for f in F:
    for r in f['related_units']:
        if r not in uid: print('UNKNOWN unit in coverage',r,f['family_id'])
        link_from_cov[r].add(f['family_id'])
bad=0
for u in U:
    l=u['sheet_family_links']
    ids=set(x if isinstance(x,str) else x.get('family_id') for x in l)
    if ids!=link_from_cov.get(u['id'],set()):
        bad+=1; print('LINK MISMATCH',u['id'],sorted(ids),sorted(link_from_cov.get(u['id'],set())))
print('link mismatches',bad, 'example link', U[4]['sheet_family_links'][:2])
# non-inspected families with related units?
for f in F:
    if f['status'] in('NOT_INSPECTED','NON_CALCULATION') and f['related_units']: print('related on',f['status'],f['family'],f['related_units'])
    if f['status'].startswith('COVERED') and not f['related_units']: print('covered w/o units',f['family'])
    # COVERED_BY_EXISTING should have only existing units; ADDITIONAL has at least one X
    xs=[r for r in f['related_units'] if r.startswith('X-')]
    if f['status']=='COVERED_BY_EXISTING' and xs: print('EXISTING status but X units',f['family'],xs)
    if f['status']=='COVERED_BY_ADDITIONAL' and not xs: print('ADDITIONAL status but no X units',f['family'],f['related_units'])
# depends_on / feeds consistency
dep={u['id']:set(u['depends_on']) for u in U}
for u in U:
    for d in u['depends_on']:
        if d not in uid: print('dep unknown',u['id'],d)
    feeds=set(u['feeds']); exp={v for v in dep if u['id'] in dep[v]}
    if feeds!=exp: print('feeds mismatch',u['id'],sorted(feeds^exp))
    for g in u['gated_by']:
        if g not in ('SYS-01','SYS-02','SYS-03'): print('gated_by other',u['id'],g)
    for s in u['similar_units']:
        s2=s if isinstance(s,str) else s.get('id')
        if s2 not in uid: print('similar unknown',u['id'],s)
print('unlinked', unl['input_count'], len(unl['inputs']), C(i['disposition'] for i in unl['inputs']), unl['counts'])
print('cna',len(cna['not_adopted']))
print('authors',C(u['author'] for u in U)); print(units['authorship_note'])
print('evidence',C(u['evidence_level'] for u in U))
