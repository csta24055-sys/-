"""Which binary-search variant of the approximate look-up reproduces Excel's cached values?"""
import sys, os, pickle, collections, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "jcat_tools"))
import excel_ref as X
import validate_ref as V
from store import Store, Err

def text_key(s, mode):
    s = s.lower()
    if mode == "cp":
        return s
    out = []
    for ch in s:
        try:
            b = ch.encode("cp932")
        except UnicodeEncodeError:
            b = b"\xff\xff" + ch.encode("utf-16-be")
        out.append(b)
    return b"".join(out)

def make(mode, early):
    def cls_key(v):
        if isinstance(v, bool):
            return (3, 1.0 if v else 0.0)
        if isinstance(v, float):
            return (1, v)
        if isinstance(v, str):
            return (2, text_key(v, mode))
        return (0, 0.0)
    def approx_pos(key, seq):
        kc = cls_key(key)
        lo, hi, best = 0, len(seq) - 1, -1
        while lo <= hi:
            mid = (lo + hi) // 2
            v = seq[mid]
            if v is None or isinstance(v, Err):
                j = mid
                while j >= lo and (seq[j] is None or isinstance(seq[j], Err)):
                    j -= 1
                if j < lo:
                    lo = mid + 1
                    continue
                v, mid2 = seq[j], j
            else:
                mid2 = mid
            vc = cls_key(v)
            if vc[0] != kc[0]:
                if vc[0] < kc[0]:
                    lo = mid + 1
                else:
                    hi = mid2 - 1
                continue
            if early and vc[1] == kc[1]:
                return mid2
            if vc[1] <= kc[1]:
                best = mid2
                lo = mid + 1
            else:
                hi = mid2 - 1
        return best
    return approx_pos

if __name__ == "__main__":
    V.STORE = Store(sys.argv[1])
    V.DATA = pickle.load(open(sys.argv[2], "rb"))
    pids = [p for p, d in V.DATA["patterns"].items() if set(d["funcs"]) & {"VLOOKUP", "HLOOKUP", "LOOKUP", "MATCH"}]
    print("patterns with look-ups", len(pids), "cells", sum(V.DATA["patterns"][p]["n"] for p in pids), flush=True)
    for mode in ("cp", "cp932"):
        for early in (False, True):
            X.approx_pos = make(mode, early)
            X._INDEX_CACHE.clear()
            t = time.time()
            res = V.work(pids)
            bad = {p: r for p, r in res.items() if r["bad"] or r["unsupported"]}
            print(mode, "early" if early else "plain", "cells", sum(r["n"] for r in res.values()), "bad cells", sum(r["bad"] for r in res.values()),
                  "bad patterns", len(bad), round(time.time() - t), "s", flush=True)
