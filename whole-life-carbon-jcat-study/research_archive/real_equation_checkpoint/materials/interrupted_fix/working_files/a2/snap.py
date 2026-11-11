"""Bit-for-bit snapshot of every public leaf of the unified model (full, totals, sweep).

Usage: PYTHONPATH=. python3 -B snap.py OUT.json [n_population n_dirty]
The digest of a unit is the sha1 of repr() of its flattened public leaves, so 0.0 and -0.0,
ints and floats, and every last bit of a float are distinguished.
"""
import hashlib
import json
import sys

from bench import verify_unified as vu
from common.compare import flatten
from fastcalc import engine
from refcalc import registry
from synth import population

registry.load_all()


def digest(result):
    out = {}
    for uid, value in result.items():
        if uid.startswith("_"):
            continue
        out[uid] = hashlib.sha1(repr(sorted(flatten(value).items())).encode()).hexdigest()[:16]
    return out


def main():
    out_path = sys.argv[1]
    n_pop = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    n_dirty = int(sys.argv[3]) if len(sys.argv) > 3 else 20
    snap = {}
    n = 0
    for group, scn in vu.scenarios(n_pop, n_dirty):
        n += 1
        key = f"{n:05d}|{group}|{scn.meta.scenario_id}"
        entry = {}
        for mode, detail in (("full", True), ("totals", False)):
            try:
                entry[mode] = digest(engine.evaluate(scn, detail=detail))
            except Exception as exc:                    # noqa: BLE001
                entry[mode] = {"*": type(exc).__name__ + ": " + str(exc)[:80]}
        snap[key] = entry
    pool = list(population.verification_population(12, seed=777, max_size="S"))
    pool += [scn for name, scn in population.edge_cases() if "period" not in name]
    for i, scn in enumerate(pool):
        got = engine.sweep(scn, vu.SWEEP_PERIODS, compare=True)
        snap[f"sweep{i:03d}|{scn.meta.scenario_id}"] = {repr(T): digest(res) for T, res in got.items()}
    # caller-held baseline totals
    for scn in population.standard_benchmark()[:2]:
        held = {}
        a = digest(engine.evaluate(scn, detail=False, baseline_totals=held))
        b = digest(engine.evaluate(scn, detail=True, baseline_totals=held))
        snap[f"held|{scn.meta.scenario_id}"] = {"first": a, "second": b, "held": repr(sorted(held.items()))}
    json.dump(snap, open(out_path, "w"), indent=0, sort_keys=True)
    print(len(snap), "entries ->", out_path)


if __name__ == "__main__":
    main()
