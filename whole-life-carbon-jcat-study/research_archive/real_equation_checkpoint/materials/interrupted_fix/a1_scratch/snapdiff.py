"""Compare two snapshots made by snapshot.py: which public leaves changed (reference side and unified side)."""
import math, pickle, sys, collections, re
a = pickle.load(open(sys.argv[1], "rb")); b = pickle.load(open(sys.argv[2], "rb"))
tol = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
def same(x, y):
    if isinstance(x, float) and isinstance(y, float) and math.isnan(x) and math.isnan(y):
        return True
    if type(x) is not type(y) and not (isinstance(x, (int, float)) and isinstance(y, (int, float)) and not isinstance(x, bool) and not isinstance(y, bool)):
        return False
    if x == y:
        return True
    if tol and isinstance(x, (int, float)) and isinstance(y, (int, float)) and not isinstance(x, bool):
        if math.isfinite(x) and math.isfinite(y):
            return abs(x - y) <= tol * max(abs(x), abs(y))
    return False
for side, name in ((0, "reference"), (1, "unified full")):
    changed = collections.Counter(); added = collections.Counter(); removed = collections.Counter(); ex = {}
    crash = collections.Counter()
    for key in a:
        if key not in b:
            print("scenario missing in second snapshot", key); continue
        ra, rb = a[key][side], b[key][side]
        if isinstance(ra, str) or isinstance(rb, str):
            if ra != rb:
                crash[(key[1], ra if isinstance(ra, str) else "ok", rb if isinstance(rb, str) else "ok")] += 1
            continue
        for uid in sorted(set(ra) | set(rb)):
            fa, fb = ra.get(uid, {}), rb.get(uid, {})
            for path in set(fa) | set(fb):
                pat = uid + "." + re.sub(r"\[\d+\]", "[]", path)
                if path not in fb:
                    removed[pat] += 1
                elif path not in fa:
                    added[pat] += 1
                elif not same(fa[path], fb[path]):
                    changed[(pat, key[1].split(":")[0])] += 1
                    ex.setdefault((pat, key[1].split(":")[0]), (key, fa[path], fb[path]))
    print(f"===== {name}: scenarios {len(a)}")
    print("  crash changes:", dict(crash))
    print("  leaves added:"); [print("     ", k, v) for k, v in sorted(added.items())]
    print("  leaves removed:"); [print("     ", k, v) for k, v in sorted(removed.items())]
    print("  leaves changed:")
    for k, v in sorted(changed.items()):
        print("     ", k, v, "e.g.", ex[k])
