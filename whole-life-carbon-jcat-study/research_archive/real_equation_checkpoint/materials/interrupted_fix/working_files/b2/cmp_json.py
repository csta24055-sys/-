"""Compare two approximation_study.json files leaf by leaf. Usage: cmp_json.py A B [rel_tol]"""
import json, sys, math
a = json.load(open(sys.argv[1], encoding="utf-8")); b = json.load(open(sys.argv[2], encoding="utf-8"))
tol = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
n = [0, 0, 0]; worst = [0.0, None]
def walk(x, y, path):
    if isinstance(x, dict) and isinstance(y, dict):
        for k in sorted(set(x) | set(y)):
            if k not in x: print("ONLY IN B:", path + "/" + k); n[2] += 1
            elif k not in y: print("ONLY IN A:", path + "/" + k); n[2] += 1
            else: walk(x[k], y[k], path + "/" + k)
    elif isinstance(x, list) and isinstance(y, list) and len(x) == len(y):
        for i, (p, q) in enumerate(zip(x, y)): walk(p, q, f"{path}[{i}]")
    else:
        n[0] += 1
        if x != y:
            if isinstance(x, (int, float)) and isinstance(y, (int, float)) and not isinstance(x, bool) and not isinstance(y, bool):
                d = abs(x - y) / max(abs(x), abs(y), 1e-300)
                if d > worst[0]: worst[0], worst[1] = d, path
                if d <= tol: return
            n[1] += 1
            print("DIFF", path, repr(x)[:60], "->", repr(y)[:60])
walk(a, b, "")
print(f"leaves compared {n[0]}, different {n[1]}, keys only on one side {n[2]}, worst numeric rel diff {worst[0]:.3e} at {worst[1]}")
