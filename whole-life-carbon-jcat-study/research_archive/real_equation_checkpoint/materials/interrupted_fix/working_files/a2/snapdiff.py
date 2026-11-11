"""Compare two snapshots written by snap.py: every digest must be equal."""
import collections
import json
import sys

a = json.load(open(sys.argv[1]))
b = json.load(open(sys.argv[2]))
diff_units = collections.Counter()
examples = {}
n_entries = n_digests = 0
if a.keys() != b.keys():
    print("DIFFERENT KEYS:", sorted(set(a) ^ set(b))[:10])
for key in a:
    if key not in b:
        continue
    n_entries += 1
    for mode in a[key]:
        x, y = a[key][mode], b[key].get(mode)
        if isinstance(x, dict):
            if not isinstance(y, dict) or x.keys() != y.keys():
                diff_units[("*keys*", mode)] += 1
                examples.setdefault(("*keys*", mode), (key, sorted(set(x) ^ set(y or {}))[:6]))
                continue
            for uid in x:
                n_digests += 1
                if x[uid] != y[uid]:
                    diff_units[(uid, mode if not mode.replace(".", "").isdigit() else "sweep")] += 1
                    examples.setdefault((uid, mode), key)
        else:
            n_digests += 1
            if x != y:
                diff_units[("held", mode)] += 1
print(f"entries compared {n_entries}, digests compared {n_digests}, differing {sum(diff_units.values())}")
for k, v in sorted(diff_units.items()):
    print("  DIFF", k, v, examples.get(k))
sys.exit(1 if diff_units or a.keys() != b.keys() else 0)
