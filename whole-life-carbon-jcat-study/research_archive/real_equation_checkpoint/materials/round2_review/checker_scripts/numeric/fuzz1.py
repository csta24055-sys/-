from fuzzlib import *
import sys, collections
a, b = int(sys.argv[1]), int(sys.argv[2])
bad = collections.OrderedDict(); crash_same = collections.Counter(); n = 0
for seed in range(a, b):
    try:
        s, T, log = build(seed)
    except Exception as e:
        print("build failed", seed, repr(e)); continue
    n += 1
    ref, full, tot = run3(s)
    exc = [isinstance(x, Exception) for x in (ref, full, tot)]
    if any(exc):
        if all(exc) and type(ref) is type(full) is type(tot):
            crash_same[type(ref).__name__] += 1
        else:
            bad[seed] = ("CRASH", T, log, repr(ref)[:160] if exc[0] else "ok", repr(full)[:160] if exc[1] else "ok", repr(tot)[:160] if exc[2] else "ok")
        continue
    recs = []
    for uid in ref:
        recs += [("full", uid) + x for x in diffs(ref[uid], full.get(uid, {}), 1e-9, 0.0)]
        recs += [("tot", uid) + x for x in diffs(ref[uid], tot.get(uid, {}), 1e-9, 0.0, ignore_missing=True)]
    if recs:
        bad[seed] = ("DIFF", T, log, len(recs), recs[:4])
print(f"seeds {a}..{b}: {n} scenarios, same-type crashes {dict(crash_same)}, disagreements {len(bad)}")
for k, v in list(bad.items())[:25]:
    print(k, v)
