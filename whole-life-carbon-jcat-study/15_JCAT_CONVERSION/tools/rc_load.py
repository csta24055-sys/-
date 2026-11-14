"""Load and merge the random-case results of a book (several runs, e.g. rc_DET.pkl and rc_DET2.pkl)."""
import glob, os, pickle, collections


def load_all(lo_dir):
    out = {}
    for p in sorted(glob.glob(os.path.join(lo_dir, "rc_*.pkl"))):
        name = os.path.basename(p)[3:-4]
        book = name[:3]
        if book not in ("SIM", "STD", "DET", "SUM") or "test" in name:
            continue
        r = pickle.load(open(p, "rb"))
        m = out.setdefault(book, dict(book=book, seed=r["seed"], S=r["S"], fractions=[], cases=[], stats={}, examples={}))
        m["fractions"].append((r["cases"][0]["case"] if r["cases"] else None, r["cases"][-1]["case"] if r["cases"] else None, r["fraction"]))
        m["cases"] += r["cases"]
        for pid, d in r["stats"].items():
            t = m["stats"].setdefault(pid, {"improved": collections.Counter(), "base": collections.Counter()})
            for k in ("improved", "base"):
                t[k].update(d[k])
        for pid, ex in r["examples"].items():
            m["examples"].setdefault(pid, []).extend(ex)
    for m in out.values():
        m["cases"].sort(key=lambda c: c["case"])
    return out
