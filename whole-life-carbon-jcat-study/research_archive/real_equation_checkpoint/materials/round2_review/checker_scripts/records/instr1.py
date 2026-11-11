"""Independent instrumentation of fastcalc.engine on the scenario used by bench.verify_unified.mechanisms()."""
import sys, json, collections
import synth
from synth import model
from fastcalc import engine, closed_forms as cf
from refcalc import registry
registry.load_all()

class CF(float):
    n = 0
    def __mul__(self, o):
        CF.n += 1; return float(self) * float(o)
    __rmul__ = __mul__

class CountDict(dict):
    gets = 0
    def get(self, k, d=None):
        CountDict.gets += 1; return dict.get(self, k, d)
    def __getitem__(self, k):
        CountDict.gets += 1; return dict.__getitem__(self, k)

class Spy:
    phase = "none"
    counts = collections.Counter()
    def __init__(self, obj, kind, idx):
        object.__setattr__(self, "_o", obj); object.__setattr__(self, "_k", kind); object.__setattr__(self, "_i", idx)
    def __getattr__(self, name):
        Spy.counts[(Spy.phase, self._k)] += 1
        Spy.rows_touched.setdefault((Spy.phase, self._k), set()).add(self._i)
        return getattr(self._o, name)
Spy.rows_touched = {}

def run(options, detail, label):
    scn = synth.make_scenario(5, "RC", "office", "S", 60.0, n_materials=400, n_equipment=120, n_refrigerants=10, **options)
    ref = registry.run_all(scn)
    for rec in scn.factors.values():
        rec.value = CF(rec.value)
    scn.factors = CountDict(scn.factors)
    scn.materials = [Spy(r, "material", i) for i, r in enumerate(scn.materials)]
    scn.equipment = [Spy(r, "equipment", i) for i, r in enumerate(scn.equipment)]
    scn.refrigerants = [Spy(r, "refrigerant", i) for i, r in enumerate(scn.refrigerants)]
    conv_calls = [0]
    orig_conv = model.conversion_factor
    def conv(*a, **k):
        conv_calls[0] += 1; return orig_conv(*a, **k)
    model.conversion_factor = conv
    ev_calls = [0]; orig_ev = cf.event_year
    def ev(t):
        ev_calls[0] += 1; return orig_ev(t)
    cf.event_year = ev
    vals = [0, 0]; orig_values = engine._values
    def values(p, Y):
        vals[0] += 1; out = orig_values(p, Y); vals[1] += len(out); return out
    engine._values = values
    orig_detail = engine._detail
    def det(*a, **k):
        Spy.phase = "detail"; return orig_detail(*a, **k)
    engine._detail = det
    CF.n = 0; CountDict.gets = 0; Spy.counts.clear(); Spy.rows_touched.clear()
    Spy.phase = "aggregate"
    A = engine.aggregate(scn, detail)
    agg = dict(cf_products=CF.n, factor_dict_lookups=CountDict.gets, conversion_factor_calls=conv_calls[0], event_year_calls=ev_calls[0])
    # wrap recipe values too
    for k, v in list(A.fval.items()):
        if not isinstance(v, CF):
            A.fval[k] = CF(v)
    CF.n = 0; CountDict.gets = 0; conv_calls[0] = 0; ev_calls[0] = 0
    Spy.phase = "finish"
    R = engine.finish(A, 60.0, detail, None)
    fin = dict(cf_products=CF.n, factor_dict_lookups=CountDict.gets, conversion_factor_calls=conv_calls[0], event_year_calls=ev_calls[0],
               values_calls=vals[0], values_elements=vals[1])
    model.conversion_factor = orig_conv; cf.event_year = orig_ev; engine._values = orig_values; engine._detail = orig_detail
    n_epd = sum(1 for r in scn.materials if r._o.epd is not None)
    n_rconv = sum(1 for r in scn.materials if r._o.conversions)
    n_comp = sum(1 for r in scn.materials if r._o.composition is not None)
    n_exp = sum(1 for e in scn.equipment if e._o.replacement_event_list is not None)
    print("=====", label, "detail=", detail)
    print(" rows: materials", len(scn.materials), "equipment", len(scn.equipment), "refrigerants", len(scn.refrigerants),
          "| with EPD", n_epd, "| with row conversions", n_rconv, "| composite", n_comp, "| explicit-event equipment", n_exp)
    print(" engine _stats:", R["_stats"])
    print(" aggregate measured:", agg)
    print(" finish measured:   ", fin)
    print(" row attribute reads by phase/kind:", dict(Spy.counts))
    print(" distinct rows touched by phase/kind:", {k: len(v) for k, v in Spy.rows_touched.items()})
    print(" table entries:", sum(len(t) for t in R["_tables"].values()), " SYS-02 n_checked", R["SYS-02"]["n_checked"], "ref", ref["SYS-02"]["n_checked"])
    return scn, A, R

for opts, label in (({"profile_kind": "LINEAR_TREND", "grid_kind": "LINEAR_DECLINE_TO_FLOOR"}, "parametric"),
                    ({"profile_kind": "TABLE", "grid_kind": "TABLE"}, "year_table")):
    for detail in (False, True):
        run(opts, detail, label)
