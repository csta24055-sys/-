"""List the (scenario, T) pairs of every verification set without computing anything."""
import csv, sys, json
sys.dont_write_bytecode = True
from checks import sets_unified
from tstudy import baseline
baseline.assert_frozen()
out = sys.argv[1]
rows = []
for name in sets_unified.ALL_SETS:
    cases = sets_unified.build([name])[name]
    n = 0
    for entry in cases:
        label, scn, periods = entry[0], entry[1], entry[2]
        m = scn.meta
        for T in periods:
            n += 1
            rows.append([name, label, m.scenario_id, m.seed, m.structure, m.use, m.size_class, len(scn.materials), len(scn.equipment),
                         len(scn.refrigerants), T, "outside_domain" if name in sets_unified.OUTSIDE_DOMAIN else "valid_domain"])
    print(name, n, flush=True)
with open(out, "w", encoding="utf-8-sig", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["集合", "ラベル", "シナリオID", "シード", "構造", "用途", "規模", "資材行", "設備行", "冷媒機器", "評価期間T", "領域"])
    w.writerows(rows)
print("pairs", len(rows), "failed mutations", len(sets_unified.FAILED_MUTATIONS))
