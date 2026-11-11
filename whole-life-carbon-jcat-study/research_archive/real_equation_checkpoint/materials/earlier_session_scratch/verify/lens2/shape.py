import json, sys
from refcalc import registry
from synth import population
registry.load_all()
cases = population.edge_cases()
name, scn = cases[0]
res = registry.run_all(scn)
MY = "A13-05 A13-02 X-15 A13-01 A13-03 A13-04 X-01 A4-01 A4-02 B4-01 B4-03 B4-02 B3-01 B3-02 B1-02 B1-03 B1-04 B5-01 X-06 B6-04 B6-01 B6-02 B6-03 B2-01 C2-01 C3-01 C4-01 X-14 C-05 X-02 SUM-01 SUM-02 SUM-03 SUM-05 SUM-07".split()
def short(v, n=200):
    s = repr(v)
    return s if len(s) <= n else s[:n] + '...'
for uid in MY:
    r = res[uid]
    print('###', uid, 'deps', registry.UNITS[uid].depends_on)
    for k, v in r.items():
        if isinstance(v, list):
            print('   ', k, ': list len', len(v), short(v[:3], 300))
        elif isinstance(v, dict):
            print('   ', k, ': dict len', len(v), short(v, 300))
        else:
            print('   ', k, ':', short(v))
