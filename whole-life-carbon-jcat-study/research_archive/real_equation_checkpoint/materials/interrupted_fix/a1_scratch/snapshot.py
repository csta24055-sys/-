"""Snapshot of the public result leaves of both calculations on the study's scenario list.

usage: snapshot.py OUT.pkl [n_population n_dirty]
Scenarios whose run raises are stored as the exception type name.
"""
import pickle, sys
sys.dont_write_bytecode = True
from bench import verify_unified as vu
from common.compare import flatten
from refcalc import registry
from fastcalc import engine
registry.load_all()

out_path = sys.argv[1]
n_pop = int(sys.argv[2]) if len(sys.argv) > 2 else 60
n_dirty = int(sys.argv[3]) if len(sys.argv) > 3 else 20
snap = {}
for idx, (group, scn) in enumerate(vu.scenarios(n_pop, n_dirty)):
    if group == "benchmark" and scn.meta.size_class != "S":
        continue
    key = (idx, group, scn.meta.scenario_id)
    try:
        ref = registry.run_all(scn)
        r = {uid: flatten(v) for uid, v in ref.items()}
    except Exception as exc:
        r = type(exc).__name__
    try:
        full = engine.evaluate(scn, detail=True)
        f = {uid: flatten(v) for uid, v in full.items() if not uid.startswith("_")}
    except Exception as exc:
        f = type(exc).__name__
    snap[key] = (r, f)
with open(out_path, "wb") as fh:
    pickle.dump(snap, fh)
print("scenarios", len(snap))
