# Additional: reference vs unified model on non-finite numeric inputs that neither calculation validates
import copy, math
import synth
from refcalc import registry
from fastcalc import engine
from common.compare import compare
registry.load_all()
nan, inf = float("nan"), float("inf")
def mk(seed=11, st="RC", use="office", T=60.0, **o):
    opts = dict(n_materials=12, n_equipment=6, n_refrigerants=4); opts.update(o)
    return synth.make_scenario(seed, st, use, "S", T, **opts)
def run(label, s):
    r = registry.run_all(s)
    for detail in (True, False):
        f = engine.evaluate(s, detail=detail)
        c = compare(r, f, ignore_missing=not detail)
        print(f"{label} detail={detail}: within1e-9={c.within(1e-9)} mismatches={c.mismatches}")
s = mk(grid_kind="CONSTANT", profile_kind="CONSTANT", unit_variety=True)
run("clean", s)
fid = next(m.factor_id for m in s.materials if m.factor_id and m.epd is None and m.composition is None)
for label, fn in (
    ("factor value NaN", lambda x: setattr(x.factors[fid], "value", nan)),
    ("factor value inf", lambda x: setattr(x.factors[fid], "value", inf)),
    ("grid start NaN", lambda x: (setattr(x.operation.grid, "start", nan), setattr(x.operation.grid, "table", [nan] * len(x.operation.grid.table)))),
    ("grid construction_value NaN", lambda x: setattr(x.operation.grid, "construction_value", nan)),
    ("gas base NaN", lambda x: (setattr(x.operation.gas, "base", nan), setattr(x.operation.gas, "table", [nan] * len(x.operation.gas.table)))),
    ("gas base inf", lambda x: (setattr(x.operation.gas, "base", inf), setattr(x.operation.gas, "table", [inf] * len(x.operation.gas.table)))),
    ("row conversion NaN", lambda x: [setattr(c, "factor", nan) for c in x.materials[0].conversions]),
    ("gwp table NaN (CH4)", lambda x: x.gwp.__setitem__([g for g in x.gases if g != "CO2"][0], nan)),
    ("gas_amounts NaN", lambda x: x.factors[fid].gas_amounts.__setitem__("CO2", nan)),
):
    s2 = copy.deepcopy(s); fn(s2)
    try:
        run(label, s2)
    except Exception as e:
        print(label, "RAISED", type(e).__name__, e)
