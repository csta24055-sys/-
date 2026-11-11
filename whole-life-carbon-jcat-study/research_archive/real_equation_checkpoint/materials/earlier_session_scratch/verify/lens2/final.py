import sys, os, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compare
OPT = {"route_bad_skips_row": False, "generic_stage_check": True}
print("=== RUN A: adapted reading (route-level drop in C3/C4, '/year' strip in B6-02, None==0.0 in by_item) ===")
stats, mism, errors = compare.main(OPT, verbose=False, none_is_zero=True)
per = collections.OrderedDict()
for (uid, k), (n, bad, m) in stats.items():
    p = per.setdefault(uid, [0, 0, 0.0]); p[0] += n; p[1] += bad; p[2] = max(p[2], m)
tot = 0
for uid, (n, bad, m) in per.items():
    tot += n
    print(f"  {uid:7s} values={n:7d} mismatching_scenario_keys={bad} max_rel_diff={m:.1e}")
print("  TOTAL values", tot, "| units", len(per), "| errors", len(errors), "| mismatch keys", {k: len(v) for k, v in mism.items()})
kinds = collections.Counter(n.split(":")[0] for n, _ in compare.scenarios())
print("  scenarios", dict(kinds))
print("=== RUN B: literal reading (row skipped+counted when any route factor unusable; None for skipped rows) ===")
stats, mism, errors = compare.main({"generic_stage_check": True}, verbose=False, none_is_zero=False)
agg = collections.Counter()
for (uid, k), lst in mism.items():
    agg[(uid, k)] = len(lst)
print("  mismatching (unit,key): scenarios ->", dict(agg))
