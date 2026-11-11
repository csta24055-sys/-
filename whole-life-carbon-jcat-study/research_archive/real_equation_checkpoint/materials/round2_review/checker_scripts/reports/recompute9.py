import json, collections, re
R='/home/user/-/whole-life-carbon-jcat-study/09_APPROX_STUDY/'
L=lambda p: json.load(open(R+p))
ex=L('04_VERIFICATION/unified_model_exactness.json'); load=L('04_VERIFICATION/unified_model_load.json'); iu=L('04_VERIFICATION/input_usage.json')
t4=open(R+'04_VERIFICATION/README.md').read(); t5=open(R+'05_DECISIONS/README.md').read(); t0=open(R+'README.md').read()
print('scenarios',ex['scenarios'],sum(g['scenarios'] for g in ex['by_group'].values()))
for k,g in ex['by_group'].items(): print(' ',k,g['scenarios'],'%.1e'%g['max_abs_rel_error'],g['failed'])
U=ex['units']
print('units',len(U),'leaves',sum(u['leaves_compared'] for u in U.values()),'nonnum',sum(u['non_numeric_compared'] for u in U.values()),'summary leaves',sum(u['summary_leaves_compared'] for u in U.values()))
mx=max(U.items(),key=lambda kv:kv[1]['max_abs_rel_error']); print('max unit',mx[0],'%.1e'%mx[1]['max_abs_rel_error'], 'max summary',max(u['summary_max_abs_rel_error'] for u in U.values()))
print('zero compared units',[(k,u['leaves_compared'],u['non_numeric_compared']) for k,u in U.items() if u['leaves_compared']==0])
print('zero any compared',[(k) for k,u in U.items() if u['leaves_compared']+u['non_numeric_compared']==0])
print('zero summary',[(k) for k,u in U.items() if u['summary_leaves_compared']==0], ex['units_without_output_in_totals_mode'])
print('failures',sum(u['failures'] for u in U.values()), ex['all_exact'], len(ex['mutations']),ex['mutations'])
ps=ex['period_sweep']; print('sweep',ps['scenarios'],ps['periods'],ps['values_compared'],'%.1e'%ps['max_abs_rel_error'],len(ps['units']))
print(' sweep units',ps['units'])
mc=ex['mechanism_counts']
for k in mc:
    print(k,'rows',mc[k]['rows'],'distinct',mc[k]['distinct'])
    print('   totals',mc[k]['totals_only']); print('   full',mc[k]['full_outputs'])
print('---- load')
RED=[('unified_full_outputs','reference_without_baseline_comparison'),('unified_totals_only','reference_without_baseline_comparison'),('unified_full_outputs_with_baseline_comparison','reference_with_baseline_comparison'),('unified_full_outputs_baseline_total_held_by_caller','reference_with_baseline_comparison'),('unified_four_more_periods_from_one_aggregation','reference_four_more_periods')]
print(list(load['sizes']['L']['reference_without_baseline_comparison'].keys())); print(load['sizes']['L']['unified_full_outputs'])
print(load['sizes']['L']['rows'],load['sizes']['L']['distinct'])
mm=0;n=0
for sz,d in load['sizes'].items():
    for u,r in RED:
        a=d[u]; b=d[r]
        keys=[k for k in a if k not in b]
        ins=1-a['instructions']/b['instructions']; tm=1-a['time_ns_gc_off']/b['time_ns_gc_off'] if 'time_ns_gc_off' in a else None
        print(sz,u,'instr',a.get('instructions'),'red %.1f%%'%(100*ins), {k:a[k] for k in keys})
