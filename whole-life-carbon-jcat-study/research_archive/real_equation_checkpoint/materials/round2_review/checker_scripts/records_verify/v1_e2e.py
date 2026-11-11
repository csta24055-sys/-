import math, struct
import synth
from fastcalc import engine
from refcalc import registry
from common.compare import compare
registry.load_all()
def nxt(x, k):
    b = struct.unpack('<q', struct.pack('<d', x))[0] + k
    return struct.unpack('<d', struct.pack('<q', b))[0]
def rel(a, b): return abs(a - b) / max(abs(a), abs(b), 1e-300)
for seed, st, use, T in ((3, "S", "office", 60.0), (21, "W", "residential", 50.0), (7, "RC", "office", 35.5)):
    try:
        base_scn = synth.make_scenario(seed, st, use, "S", T)
    except Exception as e:
        print("make_scenario failed", seed, st, use, e); continue
    # sanity: unmodified scenario matches
    ref = registry.run_all(base_scn); got = engine.evaluate(base_scn, detail=True)
    print(f"seed {seed} {st}/{use} T={T}: unmodified B3-01 rel {rel(ref['B3-01']['value'], got['B3-01']['value']):.2e} SUM-03 rel {rel(ref['SUM-03']['value'], got['SUM-03']['value']):.2e}")
    for label, c in (("1.000000001", 1.000000001), ("next double up", nxt(1.000000001, 1)), ("next double down", nxt(1.000000001, -1)), ("1.0", 1.0), ("1+2e-9", 1.000000002)):
        scn = synth.make_scenario(seed, st, use, "S", T)
        # change ONE material row with repair
        i = next(i for i, r in enumerate(scn.materials) if r.repair_rate and r.repair_rate > 0)
        scn.materials[i].refresh_cycle = c
        ref = registry.run_all(scn)
        for detail in (False, True):
            got = engine.evaluate(scn, detail=detail)
            line = f"   period {label:17s} detail={detail!s:5s} B3-01 ref {ref['B3-01']['value']!r} fast {got['B3-01']['value']!r} rel {rel(ref['B3-01']['value'], got['B3-01']['value']):.2e}; SUM-03 rel {rel(ref['SUM-03']['value'], got['SUM-03']['value']):.2e}; B4-02 rel {rel(ref['B4-02']['value'], got['B4-02']['value']):.1e}"
            if detail:
                by_ref = ref['B3-01']['by_year']; by_got = got['B3-01']['by_year']
                line += f"; by_year max rel {max(rel(a, b) for a, b in zip(by_ref, by_got) if a or b):.1e}; sum(by_year fast)-value fast = {sum(by_got) - got['B3-01']['value']:.6g}"
                line += f"; X-07 value rel {rel(ref['X-07']['value'], got['X-07']['value']):.1e}; fast X-07 vs fast SUM-03 rel {rel(got['X-07']['value'], got['SUM-03']['value']):.1e}; QA-01 fast ok={got['QA-01']['ok']}"
            print(line)
        # whole-suite comparison in the study's own way
        got = engine.evaluate(scn, detail=True)
        bad = []
        floor = 1e-9 * abs(ref["SUM-03"]["value"])
        for uid in ref:
            cmpres = compare(ref[uid], got[uid], floor=floor)
            if cmpres.mismatches: bad.append(uid)
        print(f"      units failing the study's compare (rtol 1e-9, full outputs): {bad}")
