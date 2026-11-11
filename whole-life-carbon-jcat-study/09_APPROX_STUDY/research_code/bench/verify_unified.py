#!/usr/bin/env python3
"""Verification of the unified model against the reference calculation.

1. Exactness: every result leaf of every unit is compared on fictional scenarios:
   the benchmark (S, M, L), boundary cases, a varied population, scenarios with the
   generator's defects, adversarial mutations (``bench/mutations.py``), decimal period
   pairs, stage subsets with and without a defect in an upstream row, and invalid
   study periods (both sides must refuse). The comparison is purely relative
   (tolerance 1e-9, no absolute floor); a leaf the unified model returns and the
   reference does not is a failure in both output modes; an exception on one side
   only, or of another type, is a failure.
2. Study-period sweep: every unit the sweep returns for several periods from one pass
   over the rows, compared with a full reference run for each period.
3. Load: run time (garbage collector off and on), executed bytecode instructions and
   peak memory of the reference calculation and of the unified model.

All data are synthetic. Agreement here means the unified model reproduces the
independent reference calculation; it says nothing about accuracy on real buildings.

Run on a quiet machine:
    cd research_code && python3 -m bench.verify_unified [--population 400] [--dirty 60] [--repeats 7]
"""
from __future__ import annotations

import argparse
import copy
import gc
import json
import statistics
import sys
import time
import tracemalloc
from pathlib import Path

import synth
from bench import mutations
from common.compare import compare
from fastcalc import engine
from refcalc import registry
from synth import model, population

STUDY = Path(__file__).resolve().parents[2]
OUT = STUDY / "04_VERIFICATION" / "unified_model_exactness.json"
OUT_LOAD = STUDY / "04_VERIFICATION" / "unified_model_load.json"
EXACT_TOL = 1e-9
EXACT_FLOOR = 0.0                       # no absolute floor: the comparison is purely relative
SWEEP_PERIODS = (10.0, 30.0, 42.5, 50.0, 60.0, 75.0, 99.9, 100.0, 120.0)


def scenarios(n_population: int, n_dirty: int):
    for scn in population.standard_benchmark():
        yield "benchmark", scn
    for name, scn in population.edge_cases():
        yield "edge:" + name, scn
    for scn in population.verification_population(n_population, seed=20261111, max_size="M"):
        yield "population", scn
    combos = [(s, u) for s in model.STRUCTURES for u in model.USES]
    for k in range(n_dirty):
        s, u = combos[k % len(combos)]
        yield "defective", synth.make_scenario(1000 + k, s, u, "S", (30.0, 60.0, 62.5)[k % 3], dirty=True)
    for name, (mutate, options) in mutations.MUTATIONS.items():
        for seed, period in ((11, 60.0), (12, 60.0), (13, 42.5), (14, 59.999999)):
            opts = dict(mutations.SMALL)
            opts.update(options)
            scn = synth.make_scenario(seed, "RC", "office", "S", period, scenario_id=f"MUT-{name}-{seed}", **opts)
            mutate(scn)
            yield "mutated:" + name, scn
    for period, lives in mutations.DECIMAL_BOUNDARIES:
        for seed in (21, 22):
            yield "decimal", synth.make_scenario(seed, "S", "retail", "S", period, service_life_choices=lives,
                                                 explicit_event_share=0.0, change_list_share=0.0,
                                                 replacement_cycle=lives[0], reconstruction_scenario="REBUILD_IDENTICAL",
                                                 **mutations.SMALL)
    for stages in mutations.STAGE_SUBSETS:
        for period, lives in ((60.0, [0.5, 1.0]), (1.5, [1.0, 0.5, 0.75]), (60.0, [20.0, 30.0]), (7.0, [0.25, 3.5])):
            yield "stage_subset", synth.make_scenario(31, "W", "school", "S", period, service_life_choices=lives,
                                                      explicit_event_share=0.0, change_list_share=0.0,
                                                      included_stages=stages, **mutations.SMALL)
    # a stage subset together with a defect in a row that only an upstream unit reads
    for stages in mutations.UPSTREAM_DEFECT_SUBSETS:
        for name, mutate in mutations.UPSTREAM_DEFECTS.items():
            for seed, period in ((61, 60.0), (62, 42.5)):
                scn = synth.make_scenario(seed, "RC", "office", "S", period, included_stages=stages, replacement_cycle=25.0,
                                          reconstruction_scenario="REBUILD_IDENTICAL", profile_kind="CONSTANT",
                                          scenario_id=f"SUBSET-{'+'.join(stages)}-{name}-{seed}", **mutations.SMALL)
                mutate(scn)
                yield "stage_subset_with_defect:" + name, scn


def run_both(scn, baseline_totals=None):
    """(reference results or exception, full results, totals-only results)."""
    try:
        ref = registry.run_all(scn)
    except Exception as exc:                            # noqa: BLE001 - the type is compared below
        ref = exc
    out = []
    for detail in (True, False):
        try:
            out.append(engine.evaluate(scn, detail=detail, baseline_totals=baseline_totals))
        except Exception as exc:                        # noqa: BLE001
            out.append(exc)
    return ref, out[0], out[1]


def exactness(n_population: int, n_dirty: int) -> dict:
    per_unit: dict[str, dict] = {}
    by_group: dict[str, dict] = {}
    failures = []
    n_scn = 0
    empty_in_totals_mode = set()
    worst = {"max_abs_rel_error": 0.0, "unit": None, "path": None, "scenario": None, "mode": None}
    incomplete_seen = 0                                 # scenarios whose reference total is marked incomplete

    def note_worst(c, uid, scn, mode):
        if c.max_abs_rel_error > worst["max_abs_rel_error"]:
            worst.update(max_abs_rel_error=c.max_abs_rel_error, unit=uid, path=c.worst_path,
                         scenario=scn.meta.scenario_id, mode=mode)

    def fail(scn, group, unit, detail):
        if len(failures) < 60:
            failures.append({"scenario": scn.meta.scenario_id, "group": group, "unit": unit, **detail})

    for group, scn in scenarios(n_population, n_dirty):
        n_scn += 1
        g = by_group.setdefault(group.split(":")[0], {"scenarios": 0, "max_abs_rel_error": 0.0, "failed": 0})
        g["scenarios"] += 1
        ref, full, summary = run_both(scn)
        if isinstance(ref, Exception) or isinstance(full, Exception) or isinstance(summary, Exception):
            # every scenario of this list has a valid study period, so no side may raise at all
            g["failed"] += 1
            fail(scn, group, "*", {"error": f"reference {ref!r:.120}; unified {full!r:.120}; totals {summary!r:.120}"})
            continue
        scn_failed = False
        incomplete_seen += not ref["SUM-03"]["complete"]
        for uid, ref_value in ref.items():
            rec = per_unit.setdefault(uid, {"leaves_compared": 0, "non_numeric_compared": 0, "max_abs_rel_error": 0.0,
                                            "summary_leaves_compared": 0, "summary_max_abs_rel_error": 0.0, "failures": 0})
            c = compare(ref_value, full.get(uid, {}), floor=EXACT_FLOOR)
            cs = compare(ref_value, summary.get(uid, {}), floor=EXACT_FLOOR, ignore_missing=True)
            rec["leaves_compared"] += c.n_numeric
            rec["non_numeric_compared"] += c.n_other
            rec["max_abs_rel_error"] = max(rec["max_abs_rel_error"], c.max_abs_rel_error)
            rec["summary_leaves_compared"] += cs.n_numeric + cs.n_other
            rec["summary_max_abs_rel_error"] = max(rec["summary_max_abs_rel_error"], cs.max_abs_rel_error)
            g["max_abs_rel_error"] = max(g["max_abs_rel_error"], c.max_abs_rel_error, cs.max_abs_rel_error)
            note_worst(c, uid, scn, "full")
            note_worst(cs, uid, scn, "totals")
            if cs.n_numeric + cs.n_other == 0:
                empty_in_totals_mode.add(uid)
            if not (c.within(EXACT_TOL) and not c.extra and cs.within(EXACT_TOL) and not cs.extra):
                rec["failures"] += 1
                scn_failed = True
                fail(scn, group, uid, {"max_abs_rel_error": max(c.max_abs_rel_error, cs.max_abs_rel_error),
                                       "worst_path": c.worst_path or cs.worst_path,
                                       "mismatches": c.mismatches[:3], "missing": c.missing[:3], "extra": c.extra[:3],
                                       "summary_mismatches": cs.mismatches[:3], "summary_extra": cs.extra[:3]})
        for mode, got in (("full", full), ("totals", summary)):          # a unit only the unified model returns
            unknown = sorted(u for u in got if not u.startswith("_") and u not in ref)
            if unknown:
                scn_failed = True
                fail(scn, group, "*", {"error": f"units absent in the reference ({mode}): {unknown[:5]}"})
        g["failed"] += scn_failed
    always_empty = sorted(u for u in empty_in_totals_mode if per_unit[u]["summary_leaves_compared"] == 0)

    # invalid study periods: both sides must refuse in the same way
    refused = 0
    for bad in mutations.INVALID_PERIODS:
        scn = synth.make_scenario(41, "RC", "office", "S", 60.0, **mutations.SMALL)
        scn.boundary.study_period = bad
        ref, full, summary = run_both(scn)
        if all(isinstance(x, ValueError) for x in (ref, full, summary)):
            refused += 1
        else:
            fail(scn, "invalid_period", "*", {"error": f"T={bad!r}: {ref!r:.80} / {full!r:.80} / {summary!r:.80}"})

    # reuse of a baseline total held by the caller: same result as the reference, also after the baseline changes
    reuse_ok = True
    scn = synth.make_scenario(51, "SRC", "hospital", "S", 60.0)
    base = population.attach_baseline(scn)
    held: dict = {}
    for step in range(4):
        if step == 2:                                   # the baseline is edited: the caller must drop what it holds
            for row in base.materials:
                if row.quantity is not None:
                    row.quantity *= 1.5
            held.clear()
        if step == 3:                                   # the baseline becomes incomplete: the held entry carries the flag
            base.materials[0].quantity = None
            held.clear()
        ref = registry.run_all(scn, ids=["SUM-08"])["SUM-08"]
        got = engine.evaluate(scn, detail=False, baseline_totals=held)["SUM-08"]
        again = engine.evaluate(scn, detail=False, baseline_totals=held)["SUM-08"]      # now from the held entry
        for res in (got, again):
            c = compare(ref, res, floor=EXACT_FLOOR)
            reuse_ok = reuse_ok and c.within(EXACT_TOL) and not c.extra
        reuse_ok = reuse_ok and list(held) == [scn.boundary.baseline_scenario]
    # two baselines registered under different ids whose bookkeeping ids are equal: the held entries must not mix
    twins = []
    for seed in (52, 53):
        prop = synth.make_scenario(seed, "RC", "office", "S", 60.0, **mutations.SMALL)
        twin = population.attach_baseline(prop)
        twin.meta.scenario_id = "SAME-BOOKKEEPING-ID"
        twins.append(prop)
    held = {}
    for prop in twins:
        ref = registry.run_all(prop, ids=["SUM-08"])["SUM-08"]
        got = engine.evaluate(prop, detail=False, baseline_totals=held)["SUM-08"]
        c = compare(ref, got, floor=EXACT_FLOOR)
        reuse_ok = reuse_ok and c.within(EXACT_TOL) and not c.extra
    reuse_ok = reuse_ok and len(held) == 2
    if not reuse_ok:
        fail(scn, "baseline_reuse", "SUM-08", {"error": "caller-held baseline total gives a different result"})

    return {"scenarios": n_scn, "tolerance": EXACT_TOL, "absolute_floor": EXACT_FLOOR,
            "comparison": "relative difference of every public leaf, no absolute floor; NaN equals NaN only; an infinity "
                          "equals only the same infinity; a bool equals only a bool; leaves the unified model returns and "
                          "the reference does not are failures in both output modes",
            "by_group": by_group, "units": dict(sorted(per_unit.items())),
            "largest_difference": worst, "scenarios_with_incomplete_total": incomplete_seen,
            "invalid_periods_refused_by_both": f"{refused}/{len(mutations.INVALID_PERIODS)}",
            "baseline_reuse_checked": reuse_ok, "units_without_output_in_totals_mode": always_empty,
            "mutations": sorted(mutations.MUTATIONS), "failures": failures,
            "all_exact": not failures and all(u["failures"] == 0 for u in per_unit.values())}


def sweep_check(n: int) -> dict:
    """Every unit of the sweep (several study periods from one aggregation) versus a reference run per period.

    The comparison with the baseline (SUM-08) stays on for the scenarios that have one; for a period
    other than the baseline's own both sides must report NOT_COMPARABLE.
    """
    worst = 0.0
    worst_at = None
    compared = other_leaves = 0
    failures = []
    units_compared: set[str] = set()
    with_baseline = 0
    status_count: dict[str, int] = {}
    pool = list(population.verification_population(n, seed=777, max_size="S"))
    pool += [scn for name, scn in population.edge_cases() if "period" not in name]
    for scn in pool:
        with_baseline += scn.boundary.baseline_scenario is not None
        got = engine.sweep(scn, SWEEP_PERIODS, compare=True)
        for T in SWEEP_PERIODS:
            other = copy.deepcopy(scn)
            other.boundary.study_period = T
            ref = registry.run_all(other)
            status = ref["SUM-08"]["status"]
            status_count[status] = status_count.get(status, 0) + 1
            for uid, ref_value in ref.items():
                c = compare(ref_value, got[T].get(uid, {}), floor=EXACT_FLOOR, ignore_missing=True)
                compared += c.n_numeric
                other_leaves += c.n_other
                if c.n_numeric + c.n_other:
                    units_compared.add(uid)
                if c.max_abs_rel_error > worst:
                    worst, worst_at = c.max_abs_rel_error, {"scenario": scn.meta.scenario_id, "T": T, "unit": uid,
                                                            "path": c.worst_path}
                if not (c.within(EXACT_TOL) and not c.extra) and len(failures) < 20:
                    failures.append({"scenario": scn.meta.scenario_id, "T": T, "unit": uid, "path": c.worst_path,
                                     "error": c.max_abs_rel_error, "mismatches": c.mismatches[:2], "extra": c.extra[:2]})
            unknown = sorted(u for u in got[T] if not u.startswith("_") and u not in ref)
            if unknown and len(failures) < 20:
                failures.append({"scenario": scn.meta.scenario_id, "T": T, "unit": "*", "extra_units": unknown[:5]})
    return {"scenarios": len(pool), "scenarios_with_baseline": with_baseline, "periods": list(SWEEP_PERIODS),
            "units": sorted(units_compared), "n_units": len(units_compared),
            "units_without_output_in_totals_mode": sorted(set(registry.UNITS) - units_compared),
            "values_compared": compared, "non_numeric_compared": other_leaves, "sum_08_status_counts": status_count,
            "absolute_floor": EXACT_FLOOR, "max_abs_rel_error": worst, "largest_difference": worst_at,
            "failures": failures, "all_exact": not failures}


def mechanisms() -> dict:
    """What the unified model actually does, measured from outside: the result of ``bench/mechanism_probe.py``.

    The probe replaces the tallies the engine used to keep. It observes multiplications by
    factor values, reads of the input rows, factor look-ups, unit conversions, event-year
    lists and loops over the study years with reporting stand-ins for the inputs, on the
    mechanism scenario (parametric inputs and year tables) and on the benchmark sizes, and
    evaluates the statements P1..P7 from the counts. Nothing is asserted here: a statement
    the counts do not support is stored as false.
    """
    from bench import mechanism_probe

    return mechanism_probe.run()


class _Ops:
    def __init__(self):
        self.n = 0
        self.mon = sys.monitoring
        self.tool = self.mon.PROFILER_ID

    def run(self, fn):
        self.n = 0
        self.mon.use_tool_id(self.tool, "verify_ops")
        self.mon.register_callback(self.tool, self.mon.events.INSTRUCTION, self._tick)
        self.mon.set_events(self.tool, self.mon.events.INSTRUCTION)
        try:
            fn()
        finally:
            self.mon.set_events(self.tool, 0)
            self.mon.register_callback(self.tool, self.mon.events.INSTRUCTION, None)
            self.mon.free_tool_id(self.tool)
        return self.n

    def _tick(self, code, offset):
        self.n += 1


def _measure(fn, repeats: int) -> dict:
    fn()
    timed = {}
    for label, use_gc in (("gc_off", False), ("gc_on", True)):
        times = []
        for _ in range(repeats):
            gc.collect()
            if not use_gc:
                gc.disable()
            try:
                t0 = time.perf_counter_ns()
                fn()
                times.append(time.perf_counter_ns() - t0)
            finally:
                gc.enable()
        timed[label] = {"median_ms": statistics.median(times) / 1e6, "min_ms": min(times) / 1e6, "max_ms": max(times) / 1e6}
    gc.collect()
    tracemalloc.start()
    fn()
    peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    return {"instructions": _Ops().run(fn), "time_ms": timed["gc_off"]["median_ms"], "time_ms_min": timed["gc_off"]["min_ms"],
            "time_ms_gc_on": timed["gc_on"]["median_ms"], "time_ms_gc_on_min": timed["gc_on"]["min_ms"],
            "peak_memory_kib": peak / 1024}


def load(repeats: int) -> dict:
    out = {}
    for scn in population.standard_benchmark():
        size = scn.meta.size_class
        no_comparison = [u for u in registry.UNITS if u != "SUM-08"]
        plain = copy.deepcopy(scn)
        plain.boundary.baseline_scenario = None         # the same building without a baseline to compare with
        held: dict = {}
        engine.evaluate(scn, detail=False, baseline_totals=held)
        A = engine.aggregate(plain, False)
        other_periods = (30.0, 50.0, 75.0, 100.0)

        def ref_per_period():
            for T in other_periods:
                o = copy.copy(plain)
                o.boundary = copy.copy(plain.boundary)
                o.boundary.study_period = T
                registry.run_all(o, ids=["SUM-03"])

        res = {
            "rows": {"materials": len(scn.materials), "equipment": len(scn.equipment), "refrigerants": len(scn.refrigerants),
                     "study_period": scn.boundary.study_period},
            "reference_without_baseline_comparison": _measure(lambda: registry.run_all(scn, ids=no_comparison), repeats),
            "unified_full_outputs": _measure(lambda: engine.evaluate(plain, detail=True), repeats),
            "unified_totals_only": _measure(lambda: engine.evaluate(plain, detail=False), repeats),
            "reference_with_baseline_comparison": _measure(lambda: registry.run_all(scn), repeats),
            "unified_full_outputs_with_baseline_comparison": _measure(lambda: engine.evaluate(scn, detail=True), repeats),
            "unified_full_outputs_baseline_total_held_by_caller": _measure(
                lambda: engine.evaluate(scn, detail=True, baseline_totals=held), repeats),
            "reference_four_more_periods": _measure(ref_per_period, max(3, repeats // 2)),
            "unified_four_more_periods_from_one_aggregation": _measure(
                lambda: [engine.finish(A, T, False, None, _compare=False) for T in other_periods], repeats),
        }
        pairs = (("unified_full_outputs", "reference_without_baseline_comparison"),
                 ("unified_totals_only", "reference_without_baseline_comparison"),
                 ("unified_full_outputs_with_baseline_comparison", "reference_with_baseline_comparison"),
                 ("unified_full_outputs_baseline_total_held_by_caller", "reference_with_baseline_comparison"),
                 ("unified_four_more_periods_from_one_aggregation", "reference_four_more_periods"))
        for cand, base in pairs:
            r, b = res[cand], res[base]
            r["compared_with"] = base
            r["instruction_reduction"] = 1.0 - r["instructions"] / b["instructions"]
            r["time_reduction_gc_off"] = 1.0 - r["time_ms"] / b["time_ms"]
            r["time_reduction_gc_on"] = 1.0 - r["time_ms_gc_on"] / b["time_ms_gc_on"]
            r["memory_reduction"] = 1.0 - r["peak_memory_kib"] / b["peak_memory_kib"]
        st = engine.evaluate(plain, detail=False)["_stats"]
        res["mechanism_counts_totals_only"] = st
        res["mechanism_counts_full_outputs"] = engine.evaluate(plain, detail=True)["_stats"]
        res["distinct"] = {"factor_records": len(plain.factors), "renewal_periods": len(A.groups),
                           "compositions": len(A.recipes),
                           "explicit_event_lists": len(A.explicit)}
        out[size] = res
        print(f"size {size}: reference {res['reference_without_baseline_comparison']['time_ms']:.1f} ms, "
              f"unified full {res['unified_full_outputs']['time_ms']:.1f} ms, totals {res['unified_totals_only']['time_ms']:.1f} ms",
              file=sys.stderr)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--population", type=int, default=400)
    ap.add_argument("--dirty", type=int, default=60)
    ap.add_argument("--sweep", type=int, default=40)
    ap.add_argument("--repeats", type=int, default=7)
    ap.add_argument("--skip-load", action="store_true")
    args = ap.parse_args()
    registry.load_all()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    ex = exactness(args.population, args.dirty)
    ex["period_sweep"] = sweep_check(args.sweep)
    ex["all_exact"] = ex["all_exact"] and ex["period_sweep"]["all_exact"]
    # The measured operation counts get their own file beside this one (mechanism_probe.json, the file
    # ``python3 -m bench.mechanism_probe`` writes); the exactness file keeps the verdicts of the statements.
    probe = mechanisms()
    probe_file = OUT.parent / "mechanism_probe.json"
    probe_file.write_text(json.dumps(probe, ensure_ascii=False, indent=1), encoding="utf-8")
    ex["mechanism_probe"] = {"file": probe_file.name,
                             "statements": {key: st["holds"] for key, st in probe["statements"].items()},
                             "engine_counters_agree": probe["engine_counters"]["all_agree"],
                             "results_identical_to_uninstrumented_runs": probe["results_identical_to_uninstrumented_runs"]}
    ex.update(schema_version="2.0", what="Leaf-by-leaf comparison of the unified model (fastcalc.engine) with the reference "
              "calculation (refcalc) on fictional scenarios. 'summary' = the mode without per-row lists and yearly series.",
              data_statement="SYNTHETIC_FICTIONAL data only. Not evidence of accuracy on real buildings.",
              population=args.population, defective=args.dirty)
    OUT.write_text(json.dumps(ex, ensure_ascii=False, indent=1), encoding="utf-8")
    worst = max(u["max_abs_rel_error"] for u in ex["units"].values())
    print(f"exactness: {ex['scenarios']} scenarios, all_exact={ex['all_exact']}, worst relative difference {worst:.2e}, "
          f"sweep worst {ex['period_sweep']['max_abs_rel_error']:.2e}, {time.perf_counter() - t0:.0f}s")
    for f in ex["failures"][:12]:
        print("  FAIL", json.dumps(f, ensure_ascii=False)[:420])
    for f in ex["period_sweep"]["failures"][:6]:
        print("  SWEEP FAIL", json.dumps(f, ensure_ascii=False)[:300])
    if not args.skip_load:
        ld = {"schema_version": "2.0", "python": sys.version.split()[0], "repeats": args.repeats,
              "what": "Reference calculation versus the unified model on the standard benchmark (same language, same machine, "
                      "pure Python on both sides). Primary metric: executed bytecode instructions. Wall time is the median "
                      "with the garbage collector off; the value with it on is given beside it.",
              "data_statement": "SYNTHETIC_FICTIONAL data only.", "sizes": load(args.repeats)}
        OUT_LOAD.write_text(json.dumps(ld, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0 if ex["all_exact"] else 1


if __name__ == "__main__":
    sys.exit(main())
