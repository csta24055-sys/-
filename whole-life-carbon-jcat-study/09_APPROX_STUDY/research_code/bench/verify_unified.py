#!/usr/bin/env python3
"""Verification of the unified model against the reference calculation.

1. Exactness: every result leaf of every unit is compared on a population of fictional
   scenarios (valid, boundary-condition and deliberately defective ones).
2. Load: run time, executed bytecode instructions and peak memory of the reference
   calculation and of the unified model on the standard benchmark.

All data are synthetic. Agreement here means the unified model reproduces the
independent reference calculation; it says nothing about accuracy on real buildings.

Run on a quiet machine:
    cd research_code && python3 -m bench.verify_unified [--population 400] [--dirty 60] [--repeats 7]
"""
from __future__ import annotations

import argparse
import gc
import json
import statistics
import sys
import time
import tracemalloc
from pathlib import Path

import synth
from common.compare import compare
from fastcalc import engine
from refcalc import registry
from synth import model, population

STUDY = Path(__file__).resolve().parents[2]
OUT = STUDY / "04_VERIFICATION" / "unified_model_exactness.json"
OUT_LOAD = STUDY / "04_VERIFICATION" / "unified_model_load.json"
EXACT_TOL = 1e-9


def scenarios(n_population: int, n_dirty: int):
    for scn in population.standard_benchmark()[:2]:
        yield "benchmark", scn
    for name, scn in population.edge_cases():
        yield "edge:" + name, scn
    for scn in population.verification_population(n_population, seed=20261111, max_size="M"):
        yield "population", scn
    combos = [(s, u) for s in model.STRUCTURES for u in model.USES]
    for k in range(n_dirty):
        s, u = combos[k % len(combos)]
        yield "defective", synth.make_scenario(1000 + k, s, u, "S", (30.0, 60.0, 62.5)[k % 3], dirty=True)


def exactness(n_population: int, n_dirty: int) -> dict:
    per_unit: dict[str, dict] = {}
    by_group: dict[str, dict] = {}
    failures = []
    n_scn = 0
    for group, scn in scenarios(n_population, n_dirty):
        n_scn += 1
        ref = registry.run_all(scn)
        engine.clear_baseline_cache()
        full = engine.evaluate(scn, detail=True)
        engine.clear_baseline_cache()
        summary = engine.evaluate(scn, detail=False)
        scale = abs(ref["SUM-03"]["value"]) or 1.0
        g = by_group.setdefault(group.split(":")[0], {"scenarios": 0, "max_abs_rel_error": 0.0, "failed": 0})
        g["scenarios"] += 1
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
            ok = c.within(EXACT_TOL) and not c.extra and cs.within(EXACT_TOL)
            if not ok:
                rec["failures"] += 1
                scn_failed = True
                if len(failures) < 40:
                    failures.append({"scenario": scn.meta.scenario_id, "group": group, "unit": uid,
                                     "max_abs_rel_error": c.max_abs_rel_error, "worst_path": c.worst_path,
                                     "mismatches": c.mismatches[:3], "missing": c.missing[:3], "extra": c.extra[:3],
                                     "summary_mismatches": cs.mismatches[:3]})
        g["failed"] += scn_failed
    return {"scenarios": n_scn, "tolerance": EXACT_TOL, "by_group": by_group, "units": dict(sorted(per_unit.items())),
            "failures": failures,
            "all_exact": not failures and all(u["failures"] == 0 for u in per_unit.values())}


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


def _measure(fn, repeats: int, ops: bool = True) -> dict:
    fn()
    times = []
    for _ in range(repeats):
        gc.collect()
        t0 = time.perf_counter_ns()
        fn()
        times.append(time.perf_counter_ns() - t0)
    gc.collect()
    tracemalloc.start()
    fn()
    peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    out = {"time_ms": statistics.median(times) / 1e6, "time_ms_min": min(times) / 1e6, "time_ms_max": max(times) / 1e6,
           "peak_memory_kib": peak / 1024}
    if ops:
        out["instructions"] = _Ops().run(fn)
    return out


def load(repeats: int) -> dict:
    out = {}
    for scn in population.standard_benchmark():
        size = scn.meta.size_class
        no_base = registry.order([u for u in registry.UNITS if u != "SUM-08"])

        def ref_all():
            registry.run_all(scn)

        def ref_without_comparison():
            registry.run_all(scn, ids=no_base)

        def fast_full_cold():
            engine.clear_baseline_cache()
            engine.evaluate(scn, detail=True)

        def fast_full_warm():
            engine.evaluate(scn, detail=True)

        def fast_summary_warm():
            engine.evaluate(scn, detail=False)

        res = {
            "rows": {"materials": len(scn.materials), "equipment": len(scn.equipment), "refrigerants": len(scn.refrigerants),
                     "study_period": scn.boundary.study_period},
            "reference_all_units": _measure(ref_all, repeats),
            "reference_without_SUM-08": _measure(ref_without_comparison, repeats),
            "unified_full_outputs_baseline_recomputed": _measure(fast_full_cold, repeats),
            "unified_full_outputs_baseline_cached": _measure(fast_full_warm, repeats),
            "unified_totals_only_baseline_cached": _measure(fast_summary_warm, repeats),
        }
        ref = res["reference_all_units"]
        for key in list(res):
            if key.startswith("unified"):
                r = res[key]
                r["time_reduction_vs_reference"] = 1.0 - r["time_ms"] / ref["time_ms"]
                r["speedup_vs_reference"] = ref["time_ms"] / r["time_ms"]
                r["instruction_reduction_vs_reference"] = 1.0 - r["instructions"] / ref["instructions"]
                r["memory_reduction_vs_reference"] = 1.0 - r["peak_memory_kib"] / ref["peak_memory_kib"]
        out[size] = res
        print(f"size {size}: reference {ref['time_ms']:.1f} ms, unified full (cached baseline) "
              f"{res['unified_full_outputs_baseline_cached']['time_ms']:.1f} ms", file=sys.stderr)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--population", type=int, default=400)
    ap.add_argument("--dirty", type=int, default=60)
    ap.add_argument("--repeats", type=int, default=7)
    ap.add_argument("--skip-load", action="store_true")
    args = ap.parse_args()
    registry.load_all()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    ex = exactness(args.population, args.dirty)
    ex.update(schema_version="1.0", what="Leaf-by-leaf comparison of the unified model (fastcalc.engine) with the reference "
              "calculation (refcalc) on fictional scenarios. 'summary' = the mode without per-row lists and yearly series.",
              data_statement="SYNTHETIC_FICTIONAL data only. Not evidence of accuracy on real buildings.",
              population=args.population, defective=args.dirty)
    OUT.write_text(json.dumps(ex, ensure_ascii=False, indent=1), encoding="utf-8")
    worst = max(u["max_abs_rel_error"] for u in ex["units"].values())
    print(f"exactness: {ex['scenarios']} scenarios, all_exact={ex['all_exact']}, worst relative difference {worst:.2e}, "
          f"{time.perf_counter() - t0:.0f}s")
    if not args.skip_load:
        ld = {"schema_version": "1.0", "python": sys.version.split()[0], "repeats": args.repeats,
              "what": "Reference calculation versus the unified model on the standard benchmark (same language, same machine, "
                      "pure Python on both sides). 'full outputs' produces every per-row list and yearly series the reference "
                      "produces; 'totals only' leaves those out.",
              "data_statement": "SYNTHETIC_FICTIONAL data only.", "sizes": load(args.repeats)}
        OUT_LOAD.write_text(json.dumps(ld, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0 if ex["all_exact"] else 1


if __name__ == "__main__":
    sys.exit(main())
