import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compare, mine
from refcalc import registry
stats, mism, errors = compare.main(verbose=False)
for key, lst in mism.items():
    print('--- MISMATCH', key, 'in', len(lst), 'scenarios; first:', [x[0] for x in lst[:8]])
def show(uid, k, nmax=2, itemmax=6):
    for name, a, b, m in mism.get((uid,k), [])[:nmax]:
        print('  >>', uid, k, name, 'maxrel', m)
        if isinstance(a, list) and isinstance(b, list) and len(a)==len(b):
            n=0
            for i,(x,y) in enumerate(zip(a,b)):
                if not compare.close(x,y)[0]:
                    print('      idx', i, 'mine', x, 'ref', y); n+=1
                    if n>=itemmax: break
        elif isinstance(a, dict) and isinstance(b, dict):
            for kk in b:
                if not compare.close(a.get(kk), b[kk])[0]:
                    print('      key', kk, 'mine', a.get(kk), 'ref', b[kk])
        else:
            print('      mine', a, 'ref', b)
for key in list(mism):
    show(*key)
