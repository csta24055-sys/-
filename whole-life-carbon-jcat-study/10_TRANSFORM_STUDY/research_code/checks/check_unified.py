"""All 70 evaluation units of the unified system against the frozen reference calculation.

Run from ``research_code``:

    PYTHONDONTWRITEBYTECODE=1 python3 -B -m checks.check_unified                 # every set (about 15 minutes)
    PYTHONDONTWRITEBYTECODE=1 python3 -B -m checks.check_unified dev_edge        # named sets only
    PYTHONDONTWRITEBYTECODE=1 python3 -B -m checks.check_unified --quick         # the short re-run test

Every public output key of every unit is compared leaf by leaf with the comparison of
``checks.check_msp_pre_a`` (never weakened: numbers relative 1e-9, a reference of exactly 0 must be
exactly 0, everything else exact including the type). The reference is used for comparison only.

Writes ``11_UNIFIED_SYSTEM/results/verification_<name>.json``. Evidence level: N (numerical agreement on
fictional data, checked by the implementer only). Not a proof and not a statement about any other tool.
"""
import collections
import json
import math
import os
import sys
import time

sys.dont_write_bytecode = True

from checks import sets_unified
from checks.check_msp_pre_a import Acc, compare, public
from tstudy import baseline, scenarios, unified

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.normpath(os.path.join(HERE, "..", "..", "11_UNIFIED_SYSTEM", "results"))
STAGES = unified.STAGES
B14_MODE = "interval"


def variety(want, counter, name):
    """How varied the reference values are (so that an all-true flag or an always-empty list is visible)."""
    if isinstance(want, bool):
        counter[name + (" = True" if want else " = False")] += 1
    elif want is None:
        counter[name + " is None"] += 1
    elif isinstance(want, str):
        counter[name + " = " + want] += 1
    elif isinstance(want, (list, dict)) and name.count("/") == 1:
        counter[name + (" non-empty" if len(want) else " empty")] += 1
    elif isinstance(want, int) and name.count("/") == 1:
        counter[name + (" > 0" if want else " = 0")] += 1


def percentile(xs, q):
    if not xs:
        return None
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(math.ceil(q * len(xs))) - 1)]


def run_set(name, cases, baselines, check_domain=True, system_factory=None, verbose=True):
    accs = collections.OrderedDict()
    var = collections.Counter()
    rel = collections.defaultdict(list)                 # relative differences of the whole-life total and of the stages
    n_pairs = n_excluded = n_failed = 0
    notes = []
    t0 = time.perf_counter()
    t_sys = t_ref = 0.0
    make = system_factory or (lambda scn: unified.System(scn, baselines=baselines, b14=B14_MODE))
    for label, scn, periods in cases:
        try:
            t = time.perf_counter()
            sysm = make(scn)
            t_sys += time.perf_counter() - t
        except Exception as ex:                          # reported, never hidden
            n_failed += len(periods)
            notes.append("PREPARE FAILED %s: %s %s" % (label, type(ex).__name__, str(ex)[:200]))
            continue
        for T in periods:
            cur = scenarios.with_period(scn, T)
            why = scenarios.valid_domain(cur) if check_domain else []
            if why:
                n_excluded += 1
                notes.append("excluded %s T=%r: %s" % (label, T, why[0]))
                continue
            try:
                t = time.perf_counter()
                ref = baseline.run_reference(cur)
                t_ref += time.perf_counter() - t
            except Exception as ex:
                n_excluded += 1
                notes.append("reference raised %s T=%r: %s %s" % (label, T, type(ex).__name__, str(ex)[:120]))
                continue
            try:
                t = time.perf_counter()
                got = sysm.at(T)
                t_sys += time.perf_counter() - t
            except Exception as ex:
                n_failed += 1
                notes.append("SYSTEM FAILED %s T=%r: %s %s" % (label, T, type(ex).__name__, str(ex)[:200]))
                continue
            n_pairs += 1
            sid = "%s|T=%r" % (label, T)
            for uid in sorted(ref):
                want = public(ref[uid])
                have = got.get(uid, {})
                for key in sorted(set(want) | set(have)):
                    acc = accs.setdefault((uid, key), Acc())
                    if key not in want or key not in have:
                        acc.n_struct_mismatch += 1
                        acc.note(sid, key, key in have, key in want, "key on one side only")
                        continue
                    compare(have[key], want[key], key, acc, sid)
                    variety(want[key], var, uid + "/" + key)
            r3, g3 = ref["SUM-03"]["value"], got["SUM-03"]["value"]
            if r3:
                rel["SUM-03"].append(abs(g3 - r3) / abs(r3))
            for st, r in ref["X-02"]["by_stage"].items():
                g = got["X-02"]["by_stage"].get(st)
                if r and g is not None:
                    rel[st].append(abs(g - r) / abs(r))
    units = collections.OrderedDict()
    for (uid, key), acc in accs.items():
        u = units.setdefault(uid, {"keys": {}, "n_compared": 0, "n_mismatch": 0, "max_rel": 0.0})
        u["keys"][key] = {"n_compared": acc.n_compared, "n_mismatch": acc.n_mismatch, "max_rel": acc.max_rel,
                          "n_bit_identical": acc.n_bit_identical, "n_float": acc.n_float, "examples": acc.examples}
        u["n_compared"] += acc.n_compared
        u["n_mismatch"] += acc.n_mismatch
        u["max_rel"] = max(u["max_rel"], acc.max_rel)
    worst = max(((u["max_rel"], uid) for uid, u in units.items()), default=(0.0, "-"))
    res = {"set": name, "n_pairs": n_pairs, "n_excluded": n_excluded, "n_failed": n_failed, "seconds": round(time.perf_counter() - t0, 1),
           "seconds_system": round(t_sys, 1), "seconds_reference": round(t_ref, 1),
           "n_units": len(units), "n_keys": len(accs), "n_values": sum(u["n_compared"] for u in units.values()),
           "n_mismatch": sum(u["n_mismatch"] for u in units.values()),
           "units_with_mismatch": sorted(uid for uid, u in units.items() if u["n_mismatch"]),
           "max_rel": worst[0], "max_rel_unit": worst[1],
           "precision": {k: {"n": len(v), "p95": percentile(v, 0.95), "max": max(v) if v else None} for k, v in sorted(rel.items())},
           "units": units, "variety": dict(sorted(var.items())), "notes": notes}
    if verbose:
        p = res["precision"].get("SUM-03", {})
        stage_p95 = max((v["p95"] or 0.0 for k, v in res["precision"].items() if k != "SUM-03"), default=0.0)
        print("[%-16s] pairs %4d  excluded %2d  failed %2d | units %d  keys %d  values %9d  mismatches %d | max rel %.2e (%s) | "
              "SUM-03 p95 %.1e  stage p95 %.1e | %5.0f s" % (name, n_pairs, n_excluded, n_failed, res["n_units"], res["n_keys"], res["n_values"],
                                                             res["n_mismatch"], res["max_rel"], res["max_rel_unit"], p.get("p95") or 0.0,
                                                             stage_p95, res["seconds"]), flush=True)
        for uid in res["units_with_mismatch"]:
            for key, k in units[uid]["keys"].items():
                if k["n_mismatch"]:
                    print("     MISMATCH %s/%s: %d of %d  e.g. %s" % (uid, key, k["n_mismatch"], k["n_compared"], k["examples"][:1]))
        for n in notes:
            if not n.startswith("excluded"):
                print("     NOTE", n)
    return res


def main(argv):
    baseline.assert_frozen()
    baseline.load()
    from synth import population
    quick = "--quick" in argv
    names = [a for a in argv if not a.startswith("--")]
    if quick:
        S = scenarios.benchmark()[0]
        cases = {"quick": [("benchmark S", S, [60.0, 62.5, 33.3])] + [("edge " + n, s, [s.boundary.study_period])
                                                                    for n, s in scenarios.edge_set()]}
    else:
        cases = sets_unified.build(names or sets_unified.ALL_SETS)
    os.makedirs(OUT_DIR, exist_ok=True)
    total = 0
    for name, cs in cases.items():
        res = run_set(name, cs, population.BASELINES, check_domain=name not in sets_unified.OUTSIDE_DOMAIN)
        total += res["n_mismatch"] + res["n_failed"]
        res["frozen_trees"] = baseline.FROZEN_TREES
        res["b14_mode"] = B14_MODE
        with open(os.path.join(OUT_DIR, "verification_%s.json" % name), "w") as f:
            json.dump(res, f, indent=1, sort_keys=False)
    print("TOTAL mismatches + failures: %d" % total)
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
