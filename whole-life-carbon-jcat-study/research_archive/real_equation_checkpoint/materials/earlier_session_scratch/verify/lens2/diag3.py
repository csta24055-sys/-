import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compare, mine
from refcalc import registry
scns = dict(compare.scenarios())
def lic(scn, fid):
    r = scn.factors.get(fid)
    return None if r is None else (r.licence_status, r.unit, r.stages, r.value)
for name in ['dirty:903']:
    scn=scns[name]
    ref=registry.run_all(scn); me=mine.run(scn, ref)
    print(name, 'defects:')
    for d in scn.meta.injected_defects:
        print('   ', d.kind, d.path, d.detail, d.related_checks)
    for i,row in enumerate(scn.materials):
        a, b = me['C3-01']['by_item'][i], ref['C3-01']['by_item'][i]
        if a is None:
            print('C3 row', i, 'mine', a, 'ref', b, 'mass', row.end_of_life.mass_kg)
            for rt in row.end_of_life.routes:
                print('      ', rt.route, rt.fraction, rt.factor_id, lic(scn, rt.factor_id))
            print('     ref _row_lines', ref['C3-01']['_row_lines'][i])
    print('C3 ref n_skipped', ref['C3-01']['n_skipped'], 'C4 ref n_skipped', ref['C4-01']['n_skipped'], 'mine', me['C3-01']['n_skipped'], me['C4-01']['n_skipped'])
    print('C-05 ref', ref['C-05'])
    print('C-05 me ', me['C-05'])
for name in ['dirty:905','dirty:913','dirty:914']:
    scn=scns[name]
    ref=registry.run_all(scn); me=mine.run(scn, ref)
    print(name, 'defects:')
    for d in scn.meta.injected_defects:
        print('   ', d.kind, d.path, d.detail, d.related_checks)
    print(' SUM-05 ref', ref['SUM-05'], 'mine', me['SUM-05'], 'gfa', scn.project.gross_floor_area, 'T', scn.boundary.study_period)
    print(' SUM-03 ref', ref['SUM-03'], 'mine', me['SUM-03'])
    for uid in ('C2-01','C4-01'):
        for i,row in enumerate(scn.materials):
            a, b = me[uid]['by_item'][i], ref[uid]['by_item'][i]
            if not compare.close(a,b)[0]:
                e=row.end_of_life
                print(' ', uid, 'row', i, 'mine', a, 'ref', b, 'mass', e.mass_kg, 'haul', e.haul_distance_km, e.haul_factor_id, lic(scn,e.haul_factor_id), [(rt.route, rt.fraction, rt.factor_id, lic(scn, rt.factor_id)) for rt in e.routes if rt.route=='LANDFILL'])
        print(' ', uid, 'n_skipped ref', ref[uid]['n_skipped'], 'mine', me[uid]['n_skipped'])
    for j,eq in enumerate(scn.equipment):
        a, b = me['X-14']['by_item'][j], ref['X-14']['by_item'][j]
        if not compare.close(a,b)[0]:
            print('  X-14 row', j, 'mine', a, 'ref', b, eq.end_of_life_mass_kg, eq.eol_factor_id, lic(scn, eq.eol_factor_id))
    print('  X-14 n_skipped', ref['X-14']['n_skipped'], me['X-14']['n_skipped'])
