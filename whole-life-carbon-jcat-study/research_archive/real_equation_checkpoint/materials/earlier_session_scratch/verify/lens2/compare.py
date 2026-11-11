"""Compare my independent implementation with the reference results."""
import math
import sys
import os
import collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mine  # noqa: E402

from refcalc import registry  # noqa: E402
from synth import population  # noqa: E402
from synth.generate import make_scenario  # noqa: E402

registry.load_all()
REL = 1e-9

# which keys of each unit are compared
KEYS = {
    "A13-05": ["q_ord", "q_inst", "n_skipped"],
    "A13-02": ["by_item", "n_invalid"],
    "X-15": ["kind", "factor", "conv", "n_unresolved"],
    "A13-01": ["value", "by_item", "n_skipped"],
    "A13-03": ["value", "by_item", "n_skipped"],
    "A13-04": ["value", "by_item"],
    "X-01": ["value", "by_item", "n_skipped"],
    "A4-01": ["value", "by_item", "n_skipped"],
    "A4-02": ["value", "by_item", "n_skipped"],
    "B4-01": ["events", "n_events"],
    "B4-03": ["by_item"],
    "B4-02": ["value", "by_item_material", "by_item_equipment", "by_year"],
    "B3-01": ["value", "by_year"],
    "B3-02": ["value"],
    "B1-02": ["value", "by_item", "by_year"],
    "B1-03": ["value", "by_year"],
    "B1-04": ["value"],
    "B5-01": ["value", "n_events", "by_year"],
    "X-06": ["by_year", "matches_table"],
    "B6-04": ["by_year"],
    "B6-01": ["by_year", "computed"],
    "B6-02": ["by_year", "n_skipped"],
    "B6-03": ["value"],
    "B2-01": ["value"],
    "C2-01": ["value", "by_item", "n_skipped"],
    "C3-01": ["value", "by_item", "n_skipped"],
    "C4-01": ["value", "by_item", "n_skipped"],
    "X-14": ["value", "by_item", "n_skipped"],
    "C-05": ["ok", "violations", "under_allocated", "n_mass_unchecked"],
    "X-02": ["by_stage", "by_stage_all"],
    "SUM-01": ["value"], "SUM-02": ["value"], "SUM-03": ["value"], "SUM-05": ["value"],
    "SUM-07": ["defined", "by_stage"],
}


NONE_IS_ZERO = False


def close(a, b):
    """Returns (equal, n_values, max_rel_err)."""
    if NONE_IS_ZERO and a is None and isinstance(b, float) and b == 0.0:
        return (True, 1, 0.0)
    if isinstance(b, str) and isinstance(a, int) and b.startswith("materials[%d]." % a):
        return (True, 1, 0.0)
    if isinstance(b, str) and isinstance(a, tuple) and len(a) == 2 and isinstance(a[1], str):
        want = "materials[%d].end_of_life.%s" % (a[0], "routes" if a[1] == "FRACTION" else "mass_kg")
        return (b == want, 1, 0.0)
    if isinstance(a, bool) or isinstance(b, bool) or isinstance(a, str) or isinstance(b, str) or a is None or b is None:
        return (a == b, 1, 0.0)
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if a == b:
            return (True, 1, 0.0)
        d = abs(a - b) / max(abs(a), abs(b), 1e-300)
        return (d <= REL or abs(a - b) <= 1e-9, 1, d)
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a) != set(b):
            return (False, 1, float("inf"))
        ok, n, m = True, 0, 0.0
        for k in a:
            o, nn, mm = close(a[k], b[k])
            ok, n, m = ok and o, n + nn, max(m, mm)
        return (ok, n, m)
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        if len(a) != len(b):
            return (False, 1, float("inf"))
        ok, n, m = True, 0, 0.0
        for x, y in zip(a, b):
            o, nn, mm = close(x, y)
            ok, n, m = ok and o, n + nn, max(m, mm)
        return (ok, n, m)
    return (a == b, 1, 0.0)


def scenarios():
    out = []
    for name, scn in population.edge_cases():
        out.append(("edge:" + name, scn))
    for i, scn in enumerate(population.verification_population(220, 20261111, max_size="S")):
        out.append((f"pop:{i}:{scn.meta.scenario_id}", scn))
    for seed in range(900, 930):
        s = make_scenario(seed, ("S", "RC", "SRC", "W")[seed % 4], ("office", "residential", "school", "hospital", "retail", "warehouse")[seed % 6],
                          "S", (60.0, 50.0, 62.5)[seed % 3], dirty=True)
        out.append((f"dirty:{seed}", s))
    return out


def main(opts=None, verbose=True, limit=None, none_is_zero=False):
    global NONE_IS_ZERO
    NONE_IS_ZERO = none_is_zero
    stats = collections.OrderedDict()
    mism = collections.defaultdict(list)
    scns = scenarios()
    if limit:
        scns = scns[:limit]
    errors = []
    for name, scn in scns:
        try:
            ref = registry.run_all(scn)
        except Exception as exc:  # reference crashed
            errors.append((name, "REF", repr(exc)))
            continue
        try:
            me = mine.run(scn, ref, opts)
        except Exception as exc:
            import traceback
            errors.append((name, "MINE", traceback.format_exc()))
            continue
        for uid, keys in KEYS.items():
            for k in keys:
                if k not in ref[uid]:
                    mism[(uid, k)].append((name, "missing-in-ref", None, None))
                    continue
                ok, n, m = close(me[uid].get(k), ref[uid][k])
                st = stats.setdefault((uid, k), [0, 0, 0.0])
                st[0] += n
                if ok:
                    st[2] = max(st[2], m)
                else:
                    st[1] += 1
                    mism[(uid, k)].append((name, me[uid].get(k), ref[uid][k], m))
    if verbose:
        print("scenarios:", len(scns), "errors:", len(errors))
        for e in errors[:10]:
            print("  ERROR", e[0], e[1], e[2][-1500:])
        tot = 0
        for (uid, k), (n, bad, m) in stats.items():
            tot += n
            print(f"{uid:8s} {k:20s} values={n:8d} scen_mismatch={bad:4d} max_rel_ok={m:.2e}")
        print("total values compared:", tot)
        for key, lst in mism.items():
            print("--- MISMATCH", key, "in", len(lst), "scenarios; first:", [x[0] for x in lst[:6]])
    return stats, mism, errors


if __name__ == "__main__":
    import json
    o = json.loads(sys.argv[1]) if len(sys.argv) > 1 else None
    main(o, none_is_zero=len(sys.argv) > 2)
