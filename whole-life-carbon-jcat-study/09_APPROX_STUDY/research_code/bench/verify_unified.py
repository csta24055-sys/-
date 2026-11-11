#!/usr/bin/env python3
"""Verification of the unified model against the reference calculation.

1. Exactness: every result leaf of every unit is compared on fictional scenarios:
   the benchmark (S, M, L), boundary cases, a varied population, scenarios with the
   generator's defects, adversarial mutations (``bench/mutations.py``), decimal period
   pairs, stage subsets, and invalid study periods (both sides must refuse).
2. Study-period sweep: totals for several periods from one pass over the rows, compared
   with a full reference run for each period.
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
SWEEP_PERIODS = (10.0, 30.0, 42.5, 50.0, 60.0, 75.0, 99.9, 100.0, 120.0)
SWEEP_UNITS = ("X-02", "SUM-01", "SUM-02", "SUM-03", "SUM-04", "SUM-05", "B4-02", "B3-01", "B3-02", "B1-02", "B1-03",
               "B1-04", "B5-01", "B6-03", "B7-04", "B2-01", "X-04", "X-05", "X-08", "X-10", "X-11", "QA-02")


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

    def fail(scn, group, unit, detail):
        if len(failures) < 60:
            failures.append({"scenario": scn.meta.scenario_id, "group": group, "unit": unit, **detail})

    for group, scn in scenarios(n_population, n_dirty):
        n_scn += 1
        g = by_group.setdefault(group.split(":")[0], {"scenarios": 0, "max_abs_rel_error": 0.0, "failed": 0})
        g["scenarios"] += 1
        ref, full, summary = run_both(scn)
        if isinstance(ref, Exception) or isinstance(full, Exception) or isinstance(summary, Exception):
            same = all(isinstance(x, Exception) for x in (ref, full, summary)) and type(ref) is type(full) is type(summary)
            if not same:
                g["failed"] += 1
                fail(scn, group, "*", {"error": f"reference {ref!r:.120}; unified {full!r:.120}; totals {summary!r:.120}"})
            continue
        scale = abs(ref["SUM-03"]["value"]) or 1.0
        scn_failed = False
        for uid, ref_value in ref.items():
            rec = per_unit.setdefault(uid, {"leaves_compared": 0, "non_numeric_compared": 0, "max_abs_rel_error": 0.0,
                                            "summary_leaves_compared": 0, "summary_max_abs_rel_error": 0.0, "failures": 0})
            c = compare(ref_value, full.get(uid, {}), floor=EXACT_TOL * scale)
            cs = compare(ref_value, summary.get(uid, {}), floor=EXACT_TOL * scale, ignore_missing=True)
            rec["leaves_compared"] += c.n_numeric
            rec["non_numeric_compared"] += c.n_other
            rec["max_abs_rel_error"] = max(rec["max_abs_rel_error"], c.max_abs_rel_error)
            rec["summary_leaves_compared"] += cs.n_numeric + cs.n_other
            rec["summary_max_abs_rel_error"] = max(rec["summary_max_abs_rel_error"], cs.max_abs_rel_error)
            g["max_abs_rel_error"] = max(g["max_abs_rel_error"], c.max_abs_rel_error)
            if cs.n_numeric + cs.n_other == 0:
                empty_in_totals_mode.add(uid)
            if not (c.within(EXACT_TOL) and not c.extra and cs.within(EXACT_TOL)):
                rec["failures"] += 1
                scn_failed = True
                fail(scn, group, uid, {"max_abs_rel_error": c.max_abs_rel_error, "worst_path": c.worst_path,
                                       "mismatches": c.mismatches[:3], "missing": c.missing[:3], "extra": c.extra[:3],
                                       "summary_mismatches": cs.mismatches[:3]})
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
    for step in range(3):
        if step == 2:                                   # the baseline is edited: the caller must drop what it holds
            for row in base.materials:
                if row.quantity is not None:
                    row.quantity *= 1.5
            held.clear()
        ref = registry.run_all(scn, ids=["SUM-08"])["SUM-08"]
        got = engine.evaluate(scn, detail=False, baseline_totals=held)["SUM-08"]
        reuse_ok = reuse_ok and compare(ref, got, floor=EXACT_TOL).within(EXACT_TOL)
    if not reuse_ok:
        fail(scn, "baseline_reuse", "SUM-08", {"error": "caller-held baseline total gives a different result"})

    return {"scenarios": n_scn, "tolerance": EXACT_TOL, "by_group": by_group, "units": dict(sorted(per_unit.items())),
            "invalid_periods_refused_by_both": f"{refused}/{len(mutations.INVALID_PERIODS)}",
            "baseline_reuse_checked": reuse_ok, "units_without_output_in_totals_mode": always_empty,
            "mutations": sorted(mutations.MUTATIONS), "failures": failures,
            "all_exact": not failures and all(u["failures"] == 0 for u in per_unit.values())}


def sweep_check(n: int) -> dict:
    """Totals for several study periods from one aggregation versus a reference run per period."""
    worst = 0.0
    compared = 0
    failures = []
    pool = list(population.verification_population(n, seed=777, max_size="S"))
    pool += [scn for name, scn in population.edge_cases() if "period" not in name]
    for scn in pool:
        scn.boundary.baseline_scenario = None
        got = engine.sweep(scn, SWEEP_PERIODS)
        for T in SWEEP_PERIODS:
            other = copy.deepcopy(scn)
            other.boundary.study_period = T
            ref = registry.run_all(other)
            scale = abs(ref["SUM-03"]["value"]) or 1.0
            for uid in SWEEP_UNITS:
                c = compare(ref[uid], got[T][uid], floor=EXACT_TOL * scale, ignore_missing=True)
                compared += c.n_numeric
                worst = max(worst, c.max_abs_rel_error)
                if not c.within(EXACT_TOL) and len(failures) < 20:
                    failures.append({"scenario": scn.meta.scenario_id, "T": T, "unit": uid, "path": c.worst_path,
                                     "error": c.max_abs_rel_error, "mismatches": c.mismatches[:2]})
    return {"scenarios": len(pool), "periods": list(SWEEP_PERIODS), "units": list(SWEEP_UNITS), "values_compared": compared,
            "max_abs_rel_error": worst, "failures": failures, "all_exact": not failures}


def mechanisms() -> dict:
    """Counters of what the unified model actually does, on two fictional scenarios.

    These back the statements of the research records (for example "no factor is
    multiplied row by row when only totals are asked for"): tools/build_records.py
    asserts them, so a record cannot describe a mechanism the code does not have.
    """
    out = {}
    cases = {"parametric_inputs": {"profile_kind": "LINEAR_TREND", "grid_kind": "LINEAR_DECLINE_TO_FLOOR"},
             "year_table_inputs": {"profile_kind": "TABLE", "grid_kind": "TABLE"}}
    for name, options in cases.items():
        scn = synth.make_scenario(5, "RC", "office", "S", 60.0, n_materials=400, n_equipment=120, n_refrigerants=10, **options)
        A = engine.aggregate(scn, False)
        totals = engine.evaluate(scn, detail=False)
        full = engine.evaluate(scn, detail=True)
        ref = registry.run_all(scn)
        out[name] = {
            "rows": {"materials": len(scn.materials), "equipment": len(scn.equipment), "refrigerants": len(scn.refrigerants),
                     "cost_items": len(scn.cost_items)},
            "distinct": {"factor_records": len(scn.factors), "factors_used": ref["QA-03"]["n_used"],
                         "factor_uses_checked_by_reference": ref["SYS-02"]["n_checked"],
                         "renewal_periods": len(A.groups), "explicit_event_lists": len(A.explicit),
                         "compositions": len({tuple((c.factor_id, c.mass_fraction) for c in row.composition)
                                              for row in scn.materials if row.composition}),
                         "table_entries": sum(len(t) for t in totals["_tables"].values())},
            "totals_only": totals["_stats"], "full_outputs": full["_stats"],
        }
    return out


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
    ex["mechanism_counts"] = mechanisms()
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
