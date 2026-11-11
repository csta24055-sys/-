"""Executed bytecode instructions of the unified model on the benchmark (sys.monitoring, as bench.verify_unified._Ops).

Usage: PYTHONPATH=. python3 -B instr_count.py OUT.json [sizes, e.g. SM or SML]
"""
import copy
import json
import sys

from bench.verify_unified import _Ops
from fastcalc import engine
from refcalc import registry
from synth import population

registry.load_all()
sizes = sys.argv[2] if len(sys.argv) > 2 else "SM"
out = {}
for scn in population.standard_benchmark():
    size = scn.meta.size_class
    if size not in sizes:
        continue
    plain = copy.deepcopy(scn)
    plain.boundary.baseline_scenario = None
    A = engine.aggregate(plain, False)
    periods = (30.0, 50.0, 75.0, 100.0)
    res = {
        "unified_totals_only": _Ops().run(lambda: engine.evaluate(plain, detail=False)),
        "unified_full_outputs": _Ops().run(lambda: engine.evaluate(plain, detail=True)),
        "aggregate_totals": _Ops().run(lambda: engine.aggregate(plain, False)),
        "finish_totals": _Ops().run(lambda: engine.finish(A, 60.0, False, None, _compare=False)),
        "four_more_periods": _Ops().run(lambda: [engine.finish(A, T, False, None, _compare=False) for T in periods]),
        "unified_totals_with_baseline": _Ops().run(lambda: engine.evaluate(scn, detail=False)),
    }
    out[size] = res
    print(size, res)
json.dump(out, open(sys.argv[1], "w"), indent=1)
