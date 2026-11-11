# Explicit ref / fast values for the non-finite cases (additional finding), plus a B5-only single-defect case of the kind B-17 names
import copy
import synth
from refcalc import registry
from fastcalc import engine
registry.load_all()
nan = float("nan")
s = synth.make_scenario(11, "RC", "office", "S", 60.0, n_materials=12, n_equipment=6, n_refrigerants=4, grid_kind="CONSTANT", profile_kind="CONSTANT")
print("reconstruction_scenario", s.boundary.reconstruction_scenario)
fid = next(m.factor_id for m in s.materials if m.factor_id and m.epd is None and m.composition is None)
for label, fn in (("factor %s value NaN" % fid, lambda x: setattr(x.factors[fid], "value", nan)),
                  ("gas base NaN", lambda x: (setattr(x.operation.gas, "base", nan), setattr(x.operation.gas, "table", [nan] * len(x.operation.gas.table))))):
    s2 = copy.deepcopy(s); fn(s2)
    r = registry.run_all(s2)
    for detail in (True, False):
        f = engine.evaluate(s2, detail=detail)
        print(label, "detail", detail)
        for u, k in (("QA-01", "ok"), ("QA-01", "violations"), ("B5-01", "value"), ("B3-02", "value"), ("SUM-03", "value"), ("SUM-03", "complete")):
            print(f"    {u}.{k}: ref {r[u].get(k)!r} | fast {f[u].get(k)!r}")
rows = [i for i, m in enumerate(s.materials) if m.factor_id == fid]
print("rows using", fid, rows, "repair rates", [s.materials[i].repair_rate for i in rows])
