"""sweep / finish reuse versus a fresh reference run per period; state leakage; scenario mutation."""
from fuzzlib import *
import collections
PERIODS = [0.3, 0.999999999, 1.0, 1.0000001, 1.5, 2.0, 7.0, 12.3, 29.999999999, 30.0, 42.5, 59.9999999999, 60.0, 60.000001, 62.5, 99.9, 100.0, 120.0, 129.5, 130.0]
bad = collections.OrderedDict(); n = 0; nleaf = 0
import sys
a, b = int(sys.argv[1]), int(sys.argv[2])
for seed in range(a, b):
    s, T0, log = build(seed)
    s.boundary.baseline_scenario = None
    try:
        engine.check_period(s)
    except Exception:
        continue
    before = copy.deepcopy(s)
    try:
        got = engine.sweep(s, PERIODS)
    except Exception as e:
        got = e
    # mutation by sweep?
    try:
        same = (before == s)
    except Exception:
        same = None
    if same is False:
        bad[(seed, "MUTATED-BY-SWEEP")] = log
    A = None
    try:
        A = engine.aggregate(s, True)
    except Exception as e:
        A = e
    for T in PERIODS:
        o = copy.deepcopy(s); o.boundary.study_period = T
        try:
            ref = registry.run_all(o)
        except Exception as e:
            ref = e
        n += 1
        if isinstance(got, Exception) or isinstance(ref, Exception):
            # sweep raises for all periods at once; compare with a per-period full evaluate instead
            try:
                one = engine.evaluate(o, detail=False)
            except Exception as e:
                one = e
            if isinstance(one, Exception) != isinstance(ref, Exception) or (isinstance(one, Exception) and type(one) is not type(ref)):
                bad[(seed, T, "CRASH")] = (log, repr(ref)[:100], repr(one)[:100])
            continue
        recs = []
        for uid in ref:
            if uid == "SUM-08": continue
            recs += [(uid,) + x for x in diffs(ref[uid], got[T].get(uid, {}), 1e-9, 0.0, ignore_missing=True)]
        # same Aggregate finished for several periods with full detail, twice
        if not isinstance(A, Exception):
            try:
                f1 = engine.finish(A, T, True, None, _compare=False)
                f2 = engine.finish(A, T, True, None, _compare=False)
                for uid in ref:
                    if uid == "SUM-08": continue
                    recs += [("finish-full", uid) + x for x in diffs(ref[uid], f1.get(uid, {}), 1e-9, 0.0)]
                    recs += [("finish-twice", uid) + x for x in diffs(f1.get(uid, {}), f2.get(uid, {}), 0.0, 0.0)]
            except Exception as e:
                recs.append(("finish-full raised", repr(e)[:100]))
        nleaf += 1
        # ignore the known tiny refrigerant precision noise: keep only abs differences that matter
        recs = [r for r in recs if not (len(r) >= 5 and isnum(r[-3]) and isnum(r[-2]) and abs(r[-3] - r[-2]) < 1e-12 * max(1.0, abs(ref["SUM-03"]["value"]) if isnum(ref["SUM-03"]["value"]) and ref["SUM-03"]["value"] == ref["SUM-03"]["value"] else 1.0))]
        if recs:
            bad[(seed, T)] = (log, len(recs), recs[:3])
print(f"seeds {a}..{b}: {n} (scenario, period) pairs; disagreements {len(bad)}")
for k, v in list(bad.items())[:20]: print(k, str(v)[:900])
