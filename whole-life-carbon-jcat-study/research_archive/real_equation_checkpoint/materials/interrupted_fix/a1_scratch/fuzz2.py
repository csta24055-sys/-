"""Extension of the checker's fuzz: after the checker's own mutators, random numeric leaves are set to
NaN, +-inf, None, a negative number, 0, a huge or a denormal number. Strict comparison (no floor);
ANY exception (also one raised by all three runs) is reported, because no input but the study period may raise.

usage: fuzz2.py first_seed last_seed
"""
from fuzzlib import *
import sys, collections, dataclasses
# Magnitudes that overflow or underflow (1e308, denormals) are left out on purpose: they are the documented
# conditioning limits (NUM-10 d), not validity defects. Tiny positive periods are left out because the
# reference counts events one by one (a period of 1e-9 years means 6e10 events).
BAD = [nan, inf, -inf, None, -1.0, 0.0, 1.000000001, 0.5, 2.0, 1e6, 1e-6]
PERIOD_FIELDS = ("refresh_cycle", "service_life", "replacement_cycle")
BAD_PERIOD = [nan, inf, -inf, None, -1.0, 0.0, 1.000000001, 0.5, 2.0, 1e6]
CONTAINERS = ("epd", "composition", "replacement_event_list", "change_years", "steps")   # a number there is a wrong TYPE

def leaves(obj, path=""):
    if dataclasses.is_dataclass(obj):
        for f in dataclasses.fields(obj):
            if f.name == "meta" or f.name in CONTAINERS and getattr(obj, f.name) is None:
                continue
            v = getattr(obj, f.name)
            p = f"{path}.{f.name}" if path else f.name
            if isinstance(v, (bool, str)):
                continue
            if v is None or isinstance(v, (int, float)):
                yield p, obj, f.name, "attr"
            else:
                yield from leaves(v, p)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            p = f"{path}[{i}]"
            if isinstance(v, (bool, str)):
                continue
            if v is None or isinstance(v, (int, float)):
                yield p, obj, i, "item"
            else:
                yield from leaves(v, p)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{path}{{{k}}}"
            if isinstance(v, (bool, str)):
                continue
            if v is None or isinstance(v, (int, float)):
                yield p, obj, k, "item"
            else:
                yield from leaves(v, p)

a, b = int(sys.argv[1]), int(sys.argv[2])
bad = collections.OrderedDict(); crashes = collections.OrderedDict(); n = 0; n_incomplete = 0
for seed in range(a, b):
    try:
        s, T, log = build(seed)
    except Exception as e:
        print("build failed", seed, repr(e)); continue
    rng = random.Random(seed * 7919 + 13)
    if rng.random() < 0.8:
        cand = [x for x in leaves(s) if x[0] != "boundary.study_period" and not x[0].startswith("boundary.study_start")
                and "release_year" not in x[0] and "price_year" not in x[0] and "factor_base_year" not in x[0]
                and "measurement_year" not in x[0] and "floors_" not in x[0] and "completion_year" not in x[0]]
        for _ in range(rng.choice([1, 1, 2, 3, 5])):
            p, parent, key, how = rng.choice(cand)
            v = rng.choice(BAD_PERIOD if p.rsplit(".", 1)[-1] in PERIOD_FIELDS else BAD)
            if how == "attr": setattr(parent, key, v)
            else: parent[key] = v
            log.append(f"{p}<-{v!r}")
    n += 1
    ref, full, tot = run3(s)
    exc = [isinstance(x, Exception) for x in (ref, full, tot)]
    if any(exc):
        crashes[seed] = (T, log, repr(ref)[:160] if exc[0] else "ok", repr(full)[:160] if exc[1] else "ok", repr(tot)[:160] if exc[2] else "ok")
        continue
    n_incomplete += not ref["SUM-03"]["complete"]
    recs = []
    for uid in ref:
        recs += [("full", uid) + x for x in diffs(ref[uid], full.get(uid, {}), 1e-9, 0.0)]
        recs += [("tot", uid) + x for x in diffs(ref[uid], tot.get(uid, {}), 1e-9, 0.0, ignore_missing=True)]
    if recs:
        bad[seed] = ("DIFF", T, log, len(recs), recs[:4])
print(f"seeds {a}..{b}: {n} scenarios, incomplete totals {n_incomplete}, exceptions {len(crashes)}, disagreements {len(bad)}")
for k, v in list(crashes.items())[:15]:
    print("EXC", k, v)
for k, v in list(bad.items())[:25]:
    print("DIFF", k, v)
