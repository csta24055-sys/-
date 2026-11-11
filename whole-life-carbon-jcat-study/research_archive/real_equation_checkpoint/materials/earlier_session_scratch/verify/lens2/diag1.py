import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compare, mine
from refcalc import registry
scns = dict(compare.scenarios())
name='edge:exact_multiple_lives'
scn=scns[name]
ref=registry.run_all(scn); me=mine.run(scn, ref)
print('B6-02 ref', ref['B6-02']['by_year'][:4], ref['B6-02']['n_skipped'], ref['B6-02'].get('_lines'))
print('B6-02 me ', me['B6-02']['by_year'][:4], me['B6-02']['n_skipped'])
op=scn.operation
for nm,prof,fid in (('gas',op.gas,op.gas_factor_id),('oil',op.oil,op.oil_factor_id),('dh',op.district_heat,op.district_heat_factor_id)):
    rec=scn.factors.get(fid)
    print(nm, prof.kind, prof.unit, prof.table[:3], fid, rec.unit if rec else None, rec.value if rec else None, rec.licence_status if rec else None, rec.stages if rec else None)
print([ (c.from_unit,c.to_unit,c.factor) for c in scn.unit_conversions])
print('B6-03', ref['B6-03'], me['B6-03'])
