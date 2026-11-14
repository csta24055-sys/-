"""Stage 1, finding of the independent review: does C(T) for T <= H depend on the length H of the year tables?

The generator option table_length sets H. The generator draws every year of a table from one random stream, so
building the same seed with H = 130 and H = 160 gives DIFFERENT inputs (first trial: 6 of 8 differed). The test
therefore builds the scenario with H = 160 and makes a copy in which every year table is cut to its first 130 years
(identical inputs), then compares C(T) (canonical, exact) and the reference at T <= 130.

Usage (from this folder): python3 -B h_test.py <out.json>
"""
import dataclasses
import json
import random
import sys

sys.dont_write_bytecode = True
import canon                                   # noqa: E402
import timechar as tc                          # noqa: E402
from tstudy import baseline, scenarios         # noqa: E402


def tables(scn, n):
    op = scn.operation
    out = []
    for p in (op.electricity, op.gas, op.oil, op.district_heat, op.onsite_generation, op.onsite_export,
              scn.water_waste.water, scn.water_waste.sewage, scn.water_waste.municipal_waste, op.grid):
        t = getattr(p, "table", None)
        out.append(list(t[:n]) if t is not None else None)
    return out


def truncate(obj, n_long, n):
    """Copy of a scenario in which every numeric sequence of length n_long is cut to its first n entries."""
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        ch = {}
        for f in dataclasses.fields(obj):
            v = getattr(obj, f.name)
            nv = truncate(v, n_long, n)
            if nv is not v:
                ch[f.name] = nv
        return dataclasses.replace(obj, **ch) if ch else obj
    if isinstance(obj, (list, tuple)):
        if len(obj) == n_long and all(isinstance(x, (int, float)) or x is None for x in obj):
            return type(obj)(obj[:n])
        new = [truncate(x, n_long, n) for x in obj]
        return type(obj)(new) if any(a is not b for a, b in zip(new, obj)) else obj
    return obj


def main(outp):
    baseline.assert_frozen()
    baseline.load()
    from synth import generate, population
    rng = random.Random(4242)
    res = []
    for i in range(8):
        args = (rng.randrange(1, 10 ** 9), rng.choice(("S", "RC", "SRC", "W")), rng.choice(("office", "school", "hospital")), "S", 60.0)
        a = generate.make_scenario(*args, table_length=130)
        b0 = generate.make_scenario(*args, table_length=160)
        b = b0
        a = truncate(b0, 160, 130)          # identical inputs: the first 130 years of the same tables
        same_inputs = tables(a, 130) == tables(b, 130)
        ca = canon.build(canon.make_system(a, population.BASELINES))
        cb = canon.build(canon.make_system(b, population.BASELINES))
        ka, kb = tc.KF(ca), tc.KF(cb)
        Ts = [0.5, 10.0, 33.3, 60.0, 99.9, 129.5, 130.0]
        diff = [float(abs(ka(T) - kb(T)) / max(abs(ka(T)), 1)) for T in Ts]
        refd = []
        for T in (33.3, 129.5):
            ra = baseline.run_reference(scenarios.with_period(a, T))["SUM-03"]["value"]
            rb = baseline.run_reference(scenarios.with_period(b, T))["SUM-03"]["value"]
            refd.append(abs(ra - rb) / max(abs(ra), 1))
        r = dict(args=list(args), H=(ca.H, cb.H), same_first_130_years_of_tables=same_inputs, canonical_rel_diff=max(diff), reference_rel_diff=max(refd))
        res.append(r)
        print(r, flush=True)
    json.dump(res, open(outp, "w"), indent=1)


if __name__ == "__main__":
    main(sys.argv[1])
