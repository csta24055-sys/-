import json, collections, re
R='/home/user/-/whole-life-carbon-jcat-study/09_APPROX_STUDY/'
L=lambda p: json.load(open(R+p))
load=L('04_VERIFICATION/unified_model_load.json'); iu=L('04_VERIFICATION/input_usage.json'); ex=L('04_VERIFICATION/unified_model_exactness.json')
t4=open(R+'04_VERIFICATION/README.md').read(); t5=open(R+'05_DECISIONS/README.md').read(); t0=open(R+'README.md').read()
ORDER=['reference_without_baseline_comparison','unified_full_outputs','unified_totals_only','reference_with_baseline_comparison','unified_full_outputs_with_baseline_comparison','unified_full_outputs_baseline_total_held_by_caller','reference_four_more_periods','unified_four_more_periods_from_one_aggregation']
rows=re.findall(r'^\| ([SML]) \| ([\d,]+) \| (.+?) \| ([\d,]+) \| (.+?) \| ([\d\.]+) \| (.+?) \| ([\d\.]+) \| ([\d,]+) \| (.+?) \|$',t4,flags=re.M)
print('load rows',len(rows)); mm=0;n=0
for i,r in enumerate(rows):
    sz=r[0]; d=load['sizes'][sz][ORDER[i%8]]
    def p(x): return '—' if x is None else '%.1f％'%(100*x)
    exp=(sz,'{:,}'.format(load['sizes'][sz]['rows']['materials']),'{:,}'.format(d['instructions']),p(d.get('instruction_reduction')),'%.1f'%d['time_ms'],p(d.get('time_reduction_gc_off')),'%.1f'%d['time_ms_gc_on'],'{:,}'.format(round(d['peak_memory_kib'])),p(d.get('memory_reduction')))
    got=(r[0],r[1],r[3],r[4],r[5],r[6],r[7],r[8],r[9])
    n+=len(exp)
    if exp!=got: mm+=1; print('load mismatch',i,exp,got)
    # independent recompute of reductions
    if 'compared_with' in d:
        b=load['sizes'][sz][d['compared_with']]
        for k,(x,y) in {'instruction_reduction':(d['instructions'],b['instructions']),'time_reduction_gc_off':(d['time_ms'],b['time_ms']),'time_reduction_gc_on':(d['time_ms_gc_on'],b['time_ms_gc_on']),'memory_reduction':(d['peak_memory_kib'],b['peak_memory_kib'])}.items():
            if abs((1-x/y)-d[k])>1e-9: print('reduction recompute mismatch',sz,ORDER[i%8],k,1-x/y,d[k])
print('load cells',n,'mismatch',mm)
# mechanism table in 04
mc=ex['mechanism_counts']
keys=[('行ごとの係数の乗算','row_factor_products'),('表の読み出しでの乗算','table_factor_products'),('年ごとの繰り返し','year_loop_iterations'),('作った更新年の一覧','event_lists_built'),('複合係数の計算','recipes_computed'),('係数の解決','factor_resolutions'),('単位換算の解決','unit_conversions_resolved'),('読んだ行','rows_scanned'),('記述子と年次表の読み比べ（値の数）','consistency_scan_values')]
for ja,k in keys:
    m=re.search(r'^\| '+re.escape(ja)+r' \| ([\d,]+) \| ([\d,]+) \| ([\d,]+) \| ([\d,]+) \|$',t4,flags=re.M)
    exp=tuple('{:,}'.format(mc[a][b][k]) for a in('parametric_inputs','year_table_inputs') for b in('totals_only','full_outputs'))
    if not m or m.groups()!=exp: print('mech mismatch',ja,exp,m and m.groups())
print('mech table ok; rows',mc['parametric_inputs']['rows'],'distinct factors used',mc['parametric_inputs']['distinct']['factors_used'],mc['parametric_inputs']['distinct']['renewal_periods'],mc['parametric_inputs']['distinct']['compositions'])
# input usage
F=iu['fields']
spec=[k for k,v in F.items() if not k.startswith('NEW')]
print('fields',len(F),'prefix counts',collections.Counter(k.split(':')[0] if ':' in k else 'SPEC' for k in F))
def cnt(col): 
    e=sum(1 for k,v in F.items() if v[col] and not k.startswith('NEW:')); a=sum(1 for k,v in F.items() if v[col] and k.startswith('NEW:')); return e,a
for col in('reference_all_units','unified_full_outputs','unified_totals_only'): print(col,cnt(col), iu['summary'][col])
print('spec',iu['inputs_in_specification'],'added',iu['inputs_added_by_this_study'],'metadata_only',iu['metadata_only_inputs'],sum(1 for v in F.values() if v['metadata_only']))
print('not read by reference',len(iu['not_read_by_reference']), 'of which spec', sum(1 for k in iu['not_read_by_reference'] if not k.startswith('NEW:')), 'NEW', sum(1 for k in iu['not_read_by_reference'] if k.startswith('NEW:')))
unl=L('01_LEDGER/unlinked_input_disposition.json')
meta=[i['input_id'] for i in unl['inputs'] if i['disposition']=='METADATA_ONLY']
print('ledger METADATA_ONLY',len(meta),'of which read by reference',[m for m in meta if F.get(m,{}).get('reference_all_units')], 'missing in fields',[m for m in meta if m not in F])
print('spec not read',sorted(k for k in iu['not_read_by_reference'] if not k.startswith('NEW:')))
print('what',iu['what_is_measured'])
units=L('01_LEDGER/units.json')['units']
ins=set(i for u in units for i in u['inputs'])
exist_ref={i for i in ins if not i.startswith('NEW:')}
print('ledger existing inputs referenced',len(exist_ref),'read',sum(1 for i in exist_ref if F.get(i,{}).get('reference_all_units')),'not in fields',[i for i in exist_ref if i not in F][:10])
print('read by reference but not referenced by any ledger unit',sorted(k for k,v in F.items() if v['reference_all_units'] and not k.startswith('NEW:') and k not in exist_ref))
print('referenced by ledger but not read',sorted(i for i in exist_ref if i in F and not F[i]['reference_all_units']))
newl={i for i in ins if i.startswith('NEW:')}
print('ledger NEW',len(newl),'iu NEW',sum(1 for k in F if k.startswith('NEW:')), 'overlap',len(newl&set(F)))
