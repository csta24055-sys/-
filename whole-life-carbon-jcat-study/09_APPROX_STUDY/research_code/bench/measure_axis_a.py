#!/usr/bin/env python3
"""Axis A measurement: load of each reference unit on the standard synthetic benchmark.

Measures, per evaluation unit and per size class (S/M/L):
  time_ns            exclusive wall time of the unit function (median of repeats)
  time_share         time_ns / sum of all unit times
  operations         executed Python bytecode instructions (sys.monitoring)
  peak_memory_bytes  peak traced allocation increase while the unit runs (tracemalloc)

What is measured is the INDEPENDENT REFERENCE CALCULATION on FICTIONAL data.
The original workbooks are not executed and nothing here describes their run time.

Run on a quiet machine:
    cd research_code && python3 -m bench.measure_axis_a [--repeats 7] [--sizes S,M,L]
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

from refcalc import registry
from synth.population import standard_benchmark

STUDY = Path(__file__).resolve().parents[2]
OUT = STUDY / "02_RANKING" / "axis_a_measurements.json"
LEDGER = STUDY / "01_LEDGER" / "units.json"


class TimeHook(registry.Hook):
    def __init__(self) -> None:
        self.t: dict[str, int] = {}
        self._t0 = 0

    def before(self, unit_id: str) -> None:
        self._t0 = time.perf_counter_ns()

    def after(self, unit_id: str) -> None:
        self.t[unit_id] = time.perf_counter_ns() - self._t0


class OpsHook(registry.Hook):
    """Counts executed bytecode instructions per unit."""

    def __init__(self) -> None:
        self.n: dict[str, int] = {}
        self._count = 0
        self._mon = sys.monitoring
        self._tool = self._mon.PROFILER_ID
        self._mon.use_tool_id(self._tool, "axis_a_ops")
        self._mon.register_callback(self._tool, self._mon.events.INSTRUCTION, self._tick)

    def _tick(self, code, offset) -> None:
        self._count += 1

    def before(self, unit_id: str) -> None:
        self._count = 0
        self._mon.set_events(self._tool, self._mon.events.INSTRUCTION)

    def after(self, unit_id: str) -> None:
        self._mon.set_events(self._tool, 0)
        self.n[unit_id] = self._count

    def close(self) -> None:
        self._mon.set_events(self._tool, 0)
        self._mon.register_callback(self._tool, self._mon.events.INSTRUCTION, None)
        self._mon.free_tool_id(self._tool)


class MemHook(registry.Hook):
    def __init__(self) -> None:
        self.peak: dict[str, int] = {}
        self._base = 0

    def before(self, unit_id: str) -> None:
        tracemalloc.reset_peak()
        self._base = tracemalloc.get_traced_memory()[0]

    def after(self, unit_id: str) -> None:
        self.peak[unit_id] = max(0, tracemalloc.get_traced_memory()[1] - self._base)


def measure(scn, repeats: int) -> dict[str, dict]:
    ids = registry.order()
    runs: dict[str, list[int]] = {uid: [] for uid in ids}
    registry.run_all(scn)  # warm-up
    for _ in range(repeats):
        gc.collect()
        hook = TimeHook()
        registry.run_all(scn, hook=hook)
        for uid in ids:
            runs[uid].append(hook.t[uid])
    med = {uid: statistics.median(v) for uid, v in runs.items()}
    total = sum(med.values()) or 1
    ops = OpsHook()
    try:
        registry.run_all(scn, hook=ops)
    finally:
        ops.close()
    gc.collect()
    tracemalloc.start()
    try:
        mem = MemHook()
        registry.run_all(scn, hook=mem)
    finally:
        tracemalloc.stop()
    return {
        uid: {
            "time_ns": med[uid],
            "time_ns_min": min(runs[uid]),
            "time_ns_max": max(runs[uid]),
            "time_share": med[uid] / total,
            "operations": ops.n[uid],
            "peak_memory_bytes": mem.peak[uid],
        }
        for uid in ids
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeats", type=int, default=7)
    ap.add_argument("--sizes", default="S,M,L")
    args = ap.parse_args()
    sizes = args.sizes.split(",")
    registry.load_all()
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))["units"]
    bench = {s.meta.size_class: s for s in standard_benchmark()}
    per_size = {}
    for size in sizes:
        scn = bench[size]
        t0 = time.perf_counter()
        per_size[size] = measure(scn, args.repeats)
        print(f"size {size}: {len(per_size[size])} units measured in {time.perf_counter() - t0:.1f}s", file=sys.stderr)
    units = {}
    for u in ledger:
        uid = u["id"]
        if uid in registry.UNITS:
            units[uid] = {"measured": True, "not_measured_reason": None}
            for field in ("time_ns", "time_ns_min", "time_ns_max", "time_share", "operations", "peak_memory_bytes"):
                units[uid][field] = {size: per_size[size][uid][field] for size in sizes}
        else:
            units[uid] = {"measured": False,
                          "not_measured_reason": u.get("not_computable_reason") or "no reference implementation"}
    extra = sorted(set(registry.UNITS) - {u["id"] for u in ledger})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "schema_version": "1.0",
        "source": "research_code/bench/measure_axis_a.py on synth.population.standard_benchmark()",
        "what_is_measured": "The independent reference calculation on fictional data. Not the original workbooks.",
        "python": sys.version.split()[0],
        "repeats": args.repeats,
        "size_classes": sizes,
        "benchmark_rows": {size: {"material_rows": len(bench[size].materials),
                                  "equipment_rows": len(bench[size].equipment),
                                  "refrigerant_devices": len(bench[size].refrigerants),
                                  "study_period": bench[size].boundary.study_period} for size in sizes},
        "total_time_ns": {size: sum(v["time_ns"] for v in per_size[size].values()) for size in sizes},
        "registered_but_not_in_ledger": extra,
        "units": units,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    measured = sum(1 for v in units.values() if v["measured"])
    print(f"wrote {OUT.name}: {measured} measured, {len(units) - measured} not measured, extra={extra}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
