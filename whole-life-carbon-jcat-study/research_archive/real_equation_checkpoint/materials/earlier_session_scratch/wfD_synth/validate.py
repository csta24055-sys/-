import json, hashlib, re, sys, os
from collections import Counter, defaultdict
base=sys.argv[1]
S=json.load(open(os.path.join(base,'taxonomy_schema.json'),encoding='utf-8'))
T=json.load(open(os.path.join(base,'classification_tree.json'),encoding='utf-8'))
E=json.load(open(os.path.join(base,'example_records.json'),encoding='utf-8'))
errs=[]
for name,d in (('schema',S),('tree',T),('examples',E)):
    assert d['status']=='DESIGN_DRAFT', name
print('status OK (all three DESIGN_DRAFT)')
nodes={n['id']:n for n in T['nodes']}
assert len(nodes)==len(T['nodes']), 'dup node ids'
for n in T['nodes']:
    for k in ('id','level','name','parent','note','axis','level_kind','code','status'):
        if k not in n: errs.append(('tree missing',n.get('id'),k))
    if n['parent'] is not None:
        p=nodes.get(n['parent'])
        if not p: errs.append(('tree parent missing',n['id']))
        elif p['level']!=n['level']-1 or p['axis']!=n['axis']: errs.append(('tree level',n['id']))
    elif n['level']!=1: errs.append(('tree root level',n['id']))
    if not re.match(r'^(FN|IN)-[0-9]{6,}$', n['id']): errs.append(('tree id fmt',n['id']))
    if not re.match(r'^[A-Z][A-Z0-9_]{1,31}$', n['code']): errs.append(('tree code fmt',n['id']))
    if n['status'] not in S['enums']['record_status']: errs.append(('tree status',n['id']))
    if n['level_kind'] not in S['enums']['level_kind']: errs.append(('tree level_kind',n['id']))
    if n['axis'] not in S['enums']['axis']: errs.append(('tree axis',n['id']))
sib=defaultdict(list)
for n in T['nodes']: sib[(n['axis'],n['parent'])].append(n['code'])
for k,v in sib.items():
    if len(v)!=len(set(v)): errs.append(('dup sibling code',k))
allcodes=[n['code'] for n in T['nodes']]
if len(allcodes)!=len(set(allcodes)): errs.append(('dup code overall',[c for c,k in Counter(allcodes).items() if k>1]))
for m in T['directive_group_mapping']:
    n=nodes[m['node_id']]
    if n['code']!=m['code'] or n['name']!=m['directive_group'] or n['level']!=2: errs.append(('mapping',m))
cnt=Counter((n['axis'],n['level'],n['status']) for n in T['nodes'])
print('tree nodes',len(nodes),dict(cnt))
kids=defaultdict(int)
for n in T['nodes']:
    if n['parent']: kids[n['parent']]+=1
for n in T['nodes']:
    if n['axis']=='FUNCTION' and n['level']==2:
        if n['status']=='DRAFT' and kids[n['id']]==0: errs.append(('group w/o element',n['id']))
        if n['status']=='RESERVED' and kids[n['id']]!=0: errs.append(('reserved w/ element',n['id']))
print('max children under one node', max(kids.values()))
enums=S['enums']; recs=S['records']
for rn,r in recs.items():
    names=[f['name'] for f in r['fields']]
    if len(names)!=len(set(names)): errs.append(('dup field',rn))
    for f in r['fields']:
        for k in ('name','type','required','description'):
            if k not in f: errs.append(('schema field key',rn,f.get('name'),k))
        if not isinstance(f['required'],bool): errs.append(('required not bool',rn,f['name']))
        for en in re.findall(r'enum:([a-z_]+)', f['type']):
            if en not in enums: errs.append(('unknown enum',rn,f['name'],en))
    for pk in r['primary_key']:
        if pk not in names and not (rn=='spec_attribute' and pk=='type_id'): errs.append(('pk missing',rn,pk))
for f in S['common_fields']['fields']:
    for en in re.findall(r'enum:([a-z_]+)', f['type']):
        if en not in enums: errs.append(('unknown enum common',f['name'],en))
for a in S['common_fields']['applies_to']:
    if a not in recs: errs.append(('applies_to unknown',a))
print('records',len(recs),'core',[k for k,v in recs.items() if v['core']])
bad=re.compile(r'(factor_value|emission|gwp|price|density$|_rate$|service_life$|leak|multiplier)')
for rn,r in recs.items():
    for f in r['fields']:
        if bad.search(f['name']): errs.append(('value-like field',rn,f['name']))
used=set()
for rn,r in recs.items():
    for f in r['fields']: used|=set(re.findall(r'enum:([a-z_]+)', f['type']))
for f in S['common_fields']['fields']: used|=set(re.findall(r'enum:([a-z_]+)', f['type']))
print('enums used only inside object-typed fields:', sorted(set(enums)-used))
FLAG='FICTIONAL_PLACEHOLDER'
assert E['all_records_flag']==FLAG
n_rec=0
for k,v in E.items():
    if isinstance(v,list):
        for r in v:
            n_rec+=1
            if not (isinstance(r,dict) and r.get('record_flag')==FLAG): errs.append(('flag missing',k))
print('example records',n_rec,{k:len(v) for k,v in E.items() if isinstance(v,list)})
common=S['common_fields']['fields']
def check(recname):
    fields=recs[recname]['fields'][:]
    if recname in S['common_fields']['applies_to']: fields+=common
    for r in E[recname]:
        rid=r.get(recs[recname]['primary_key'][0])
        for f in fields:
            if f['required'] and f['name'] not in r: errs.append(('example missing required',recname,rid,f['name']))
            if f['name'] in r:
                val=r[f['name']]
                nullable=f['type'].endswith('|null')
                if val is None and not nullable: errs.append(('null in non-nullable',recname,rid,f['name']))
                m=re.fullmatch(r'enum:([a-z_]+)(\|null)?', f['type'])
                if m and val is not None and val not in enums[m.group(1)]: errs.append(('enum value',recname,f['name'],val))
                m=re.fullmatch(r'array<enum:([a-z_]+)>(\|null)?', f['type'])
                if m and val is not None:
                    for x in val:
                        if x not in enums[m.group(1)]: errs.append(('enum array value',recname,f['name'],x))
                if f['type'].startswith('array') and val is not None and not isinstance(val,list): errs.append(('not array',recname,f['name']))
                if f['type'].startswith('boolean') and val is not None and not isinstance(val,bool): errs.append(('not bool',recname,f['name']))
        extra=set(r)-{f['name'] for f in fields}-{'record_flag','explanation','identity_string_for_illustration','input_for_illustration','gate_result'}
        if extra: errs.append(('unknown field',recname,rid,sorted(extra)))
for rn in ('release','source','raw_record','unit_def','material_type','canonical_material','alias','unit_conversion','placement','merge_event','similarity_link','assembly','assembly_component','param_binding','calc_row'):
    check(rn)
for t in E['material_type']:
    for a in t['spec_attributes']:
        for f in recs['spec_attribute']['fields']:
            if f['required'] and f['name'] not in a: errs.append(('spec_attr missing',t['type_id'],f['name']))
        if a['role'] not in enums['attribute_role'] or a['value_type'] not in enums['attribute_value_type']: errs.append(('spec enum',t['type_id']))
        for x in a['affects']:
            if x not in enums['affects']: errs.append(('affects',x))
for k in ('material_type','canonical_material','alias','unit_conversion','placement','similarity_link','assembly','param_binding'):
    for r in E[k]:
        for pv in r['provenance']:
            if pv['derivation'] not in enums['derivation']: errs.append(('derivation',k))
        if r['status']=='ACTIVE' and not r.get('reviewed_by'): errs.append(('ACTIVE without reviewer',k))
for m in E['merge_event']:
    for fr in m['field_resolutions']:
        if fr['rule'] not in enums['field_resolution_rule']: errs.append(('field rule',m['merge_event_id']))
    if m['duplicate_level'] in ('D2_UNIT_VARIANT','D3_NEAR','D4_CROSS_SOURCE') and not m['reviewed_by']: errs.append(('merge needs reviewer',m['merge_event_id']))
for d in E['duplicate_handling']:
    if d['duplicate_level'] not in enums['duplicate_level']: errs.append(('dup level',d))
ids=set(nodes)
for k,pk in (('source','source_id'),('raw_record','raw_id'),('material_type','type_id'),('canonical_material','canonical_id'),('alias','alias_id'),('unit_conversion','conversion_id'),('placement','placement_id'),('merge_event','merge_event_id'),('similarity_link','link_id'),('assembly','assembly_id'),('param_binding','binding_id'),('calc_row','row_id'),('release','release_id')):
    for r in E[k]:
        if r[pk] in ids: errs.append(('dup id',r[pk]))
        ids.add(r[pk])
def refs(o):
    if isinstance(o,str):
        if re.fullmatch(r'(FN|IN)-\d{6}|[A-Z]{2,3}-FICT-\d{4}',o): yield o
    elif isinstance(o,list):
        for x in o: yield from refs(x)
    elif isinstance(o,dict):
        for kk,x in o.items():
            if kk in ('selection_id','zone_id'): continue
            yield from refs(x)
nref=0
for k,v in E.items():
    if isinstance(v,list):
        for r in v:
            for x in refs(r):
                nref+=1
                if x not in ids: errs.append(('dangling ref',k,x))
print('references checked',nref)
units={u['unit_code'] for u in E['unit_def']}
for t in E['material_type']:
    if t['declared_unit'] not in units: errs.append(('unit',t['type_id']))
    if nodes[t['substance_class_id']]['axis']!='ITEM': errs.append(('substance class axis',t['type_id']))
for c in E['unit_conversion']:
    for u in (c['from_unit'],c['to_unit']):
        if u not in units: errs.append(('conv unit',c['conversion_id'],u))
for c in E['canonical_material']:
    if hashlib.sha256(c['identity_string_for_illustration'].encode()).hexdigest()!=c['identity_key']: errs.append(('identity hash',c['canonical_id']))
act=[c['identity_key'] for c in E['canonical_material'] if c['status']=='ACTIVE']
if len(act)!=len(set(act)): errs.append(('identity not unique among ACTIVE',))
for r in E['raw_record']:
    s='|'.join([r['source_id'],r['name_text'],r['spec_text'] or '',r['unit_text'] or '',r['class_text'] or ''])
    if hashlib.sha256(s.encode()).hexdigest()!=r['content_hash']: errs.append(('content hash',r['raw_id']))
dni={s['source_id'] for s in E['source'] if s['storage_policy']=='DO_NOT_INGEST'}
if any(r['source_id'] in dni for r in E['raw_record']): errs.append(('raw from blocked source',))
for a in E['alias']:
    if (a['resolution']=='UNIQUE')!=(len(a['target_ids'])==1): errs.append(('alias resolution',a['alias_id']))
k=[(a['normalized_key'],a['context_node_id']) for a in E['alias'] if a['status']=='ACTIVE']
if len(k)!=len(set(k)): errs.append(('alias key dup',))
prim=Counter(p['type_id'] for p in E['placement'] if p['is_primary'])
pk2=[(p['function_node_id'],p['type_id']) for p in E['placement']]
if len(pk2)!=len(set(pk2)): errs.append(('placement dup',))
for p in E['placement']:
    if nodes[p['function_node_id']]['level_kind']!='ELEMENT': errs.append(('placement not element',p['placement_id']))
    if prim[p['type_id']]!=1: errs.append(('primary count',p['type_id']))
for c in E['unit_conversion']:
    if c['conversion_status']=='USABLE' and (c['basis_value_state']=='MISSING' or c['basis_license_status']!='PERMITTED_PUBLIC'): errs.append(('INV-08',c['conversion_id']))
tmap={t['type_id']:t for t in E['material_type']}
cmap={c['canonical_id']:c for c in E['canonical_material']}
pmap={p['placement_id']:p for p in E['placement']}
for r in E['calc_row']:
    for kk,vv in r.items():
        if kk.endswith('_ref') and vv is not None: errs.append(('ref not null',r['row_id'],kk))
    if r['computable']: errs.append(('computable',r['row_id']))
    if r['canonical_id'] and tmap[cmap[r['canonical_id']]['type_id']]['declared_unit']!=r['activity_unit']: errs.append(('activity unit',r['row_id']))
    if r['placement_id'] and pmap[r['placement_id']]['type_id']!=cmap[r['canonical_id']]['type_id']: errs.append(('placement/type mismatch',r['row_id']))
    if cmap[r['canonical_id']]['status']!='ACTIVE': errs.append(('row uses non-active',r['row_id']))
    for pk,ps in r['param_states'].items():
        if pk not in enums['param_kind'] or ps['bound_from'] not in enums['bound_from'] or ps['value_state'] not in enums['value_state'] or ps['license_status'] not in enums['license_status']: errs.append(('param_states',r['row_id']))
    if set(r['operation_count'])!={'pick','enter','search','accept','override'}: errs.append(('op keys',r['row_id']))
    if len(r['candidate_counts'])!=r['operation_count']['pick']: errs.append(('candidate count len',r['row_id']))
# double-count pairs flagged consistently
key=defaultdict(list)
for r in E['calc_row']:
    key[(r['placement_id'],cmap[r['canonical_id']]['type_id'],r['zone_id'])].append(r)
for kk,rows in key.items():
    mixed=len({bool(r['assembly_id']) for r in rows})>1
    for r in rows:
        if mixed != ('DOUBLE_COUNT_UNRESOLVED' in r['blocking_reasons']): errs.append(('double count flag',r['row_id']))
for c in E['assembly_component']:
    if tmap[cmap[c['target_id']]['type_id']]['declared_unit']!=c['component_unit']: errs.append(('component unit',c['line_no']))
    if c['placement_id'] and pmap[c['placement_id']]['type_id']!=cmap[c['target_id']]['type_id']: errs.append(('component placement',c['line_no']))
for n in E['normalization_trace']:
    for f in n['flags']:
        if f not in enums['stop_code'] and f not in enums['warning_code']: errs.append(('trace flag',f))
for fn in ('example_records.json','taxonomy_schema.json','classification_tree.json'):
    txt=open(os.path.join(base,fn),encoding='utf-8').read()
    for pat in ('kgCO2','CO2e','factor_value'):
        if pat in txt: errs.append(('suspicious token',fn,pat))
print('errors:',len(errs))
for e in errs: print(' ',e)
sys.exit(1 if errs else 0)
