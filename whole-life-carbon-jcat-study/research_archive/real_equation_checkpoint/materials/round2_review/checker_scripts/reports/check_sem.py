import json,re,sys
sys.dont_write_bytecode=True
from refcalc import registry
registry.load_all()
R='/home/user/-/whole-life-carbon-jcat-study/09_APPROX_STUDY/'
U=json.load(open(R+'01_LEDGER/units.json'))['units']
bad=0
for u in U:
    ref=registry.UNITS.get(u['id'])
    if ref is None: print('no ref',u['id']); bad+=1; continue
    doc=re.sub(r"\s*\n\s*","",ref.doc)
    if doc!=u['reference_semantics']: bad+=1; print('semantics differ',u['id'])
    if sorted(ref.depends_on)!=u['depends_on']: bad+=1; print('deps differ',u['id'])
print('registered',len(registry.UNITS),'ledger',len(U),'bad',bad, set(registry.UNITS)-{u['id'] for u in U})
# gated_by stats, n_inputs consistency
print('n_inputs mismatch',[u['id'] for u in U if u['n_inputs']!=len(u['inputs'])])
import collections
print('gated_by',collections.Counter(len(u['gated_by']) for u in U))
print('ambiguities total',sum(len(u['ambiguities']) for u in U))
# stale statements in ledger: proposals that say "基準計算には実装しない" while computable
for u in U:
    for k in ('reference_semantics_proposal','approximation_potential','unification_potential','purpose'):
        v=u.get(k) or ''
        if '実装しない' in v or '未定義' in v or 'UNDEFINED' in v: print(u['id'],k,v[:160])
    if u.get('structure_subclass')=='UNDEFINED_MODEL': print('subclass UNDEFINED_MODEL',u['id'],u['computable_in_reference'],u['not_computable_reason'])
