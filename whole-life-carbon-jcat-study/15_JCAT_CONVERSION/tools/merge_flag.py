"""Replace the results of re-run patterns (after converter fixes) in the result files, in order."""
import os, pickle
C = os.path.dirname(os.path.abspath(__file__))
PLAN = [("L1_base.pkl", ["L1_base_flag.pkl", "L1_base_idx.pkl"], "plain"),
        ("L1_improved.pkl", ["L1_improved_flag.pkl", "L1_improved_idx.pkl"], "plain"),
        ("vb_base.pkl", ["vb_base_flag.pkl", "vb_base_idx.pkl"], "vb"),
        ("vb_improved.pkl", ["vb_improved_flag.pkl", "vb_improved_idx.pkl"], "vb")]
for main, fixes, kind in PLAN:
    pm = os.path.join(C, main)
    orig = pm + ".before_fixes"
    if not os.path.exists(orig):
        os.replace(pm, orig)
    m = pickle.load(open(orig, "rb"))
    for fx_ in fixes:
        f = pickle.load(open(os.path.join(C, fx_), "rb"))
        if kind == "plain":
            m.update(f); n = len(f)
        else:
            m["results"].update(f["results"]); n = len(f["results"]); m.setdefault("reruns", []).append(fx_)
        print(main, "<-", fx_, n)
    pickle.dump(m, open(pm, "wb"))
