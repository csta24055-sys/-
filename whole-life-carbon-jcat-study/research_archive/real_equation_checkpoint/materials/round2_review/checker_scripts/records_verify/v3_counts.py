"""Independent instrumentation for REC-3 / REC-4 / REC-9 on the study's mechanism scenario."""
import sys, collections, json
import synth
from synth import model
from fastcalc import engine, closed_forms as cf

def mech_scn(**options):
    return synth.make_scenario(5, "RC", "office", "S", 60.0, n_materials=400, n_equipment=120, n_refrigerants=10, **options)

class CountingFactors(dict):
    calls = collections.Counter()
    def _note(self):
        f = sys._getframe(2)
        CountingFactors.calls[(f.f_code.co_name, f.f_lineno)] += 1
    def get(self, k, d=None):
        self._note(); return dict.get(self, k, d)
    def __getitem__(self, k):
        self._note(); return dict.__getitem__(self, k)

conv_calls = collections.Counter()
orig_conv = model.conversion_factor
def counting_conv(*a, **k):
    f = sys._getframe(1)
    conv_calls[(f.f_code.co_name, f.f_lineno)] += 1
    return orig_conv(*a, **k)

ey_calls = collections.Counter()
orig_ey = cf.event_year
def counting_ey(t):
    f = sys._getframe(1); ey_calls[(f.f_code.co_name, f.f_lineno)] += 1
    return orig_ey(t)

class Proxy:
    """Counts attribute reads of an input row, per phase."""
    phase = "aggregate"
    reads = collections.Counter()
    def __init__(self, obj, kind, idx):
        object.__setattr__(self, "_o", obj); object.__setattr__(self, "_k", kind); object.__setattr__(self, "_i", idx)
    def __getattr__(self, name):
        Proxy.reads[(Proxy.phase, self._k, self._i)] += 1
        return getattr(self._o, name)

for label, opts in (("parametric", {"profile_kind": "LINEAR_TREND", "grid_kind": "LINEAR_DECLINE_TO_FLOOR"}),):
    for detail in (False, True):
        scn = mech_scn(**opts)
        scn.factors = CountingFactors(scn.factors)
        scn.refrigerants = [Proxy(d, "refrigerant", i) for i, d in enumerate(scn.refrigerants)]
        scn.equipment = [Proxy(d, "equipment", i) for i, d in enumerate(scn.equipment)]
        CountingFactors.calls.clear(); conv_calls.clear(); ey_calls.clear(); Proxy.reads.clear()
        model.conversion_factor = counting_conv; cf.event_year = counting_ey
        Proxy.phase = "aggregate"
        A = engine.aggregate(scn, detail)
        agg_factor = dict(CountingFactors.calls); agg_conv = dict(conv_calls)
        CountingFactors.calls.clear()
        Proxy.phase = "finish"
        R = engine.finish(A, 60.0, detail, None)
        fin_factor = dict(CountingFactors.calls)
        model.conversion_factor = orig_conv; cf.event_year = orig_ey
        st = R["_stats"]
        print(f"===== {label} detail={detail}")
        print(" engine counters:", {k: st[k] for k in ("factor_resolutions", "unit_conversions_resolved", "rows_scanned", "row_factor_products", "event_lists_built", "table_factor_products", "recipes_computed", "year_loop_iterations")})
        print(" model.conversion_factor calls by (function, line):", agg_conv, "total", sum(agg_conv.values()))
        print(" factors lookups in aggregate by (function, line):", agg_factor, "total", sum(agg_factor.values()))
        print(" factors lookups in finish by (function, line):", fin_factor, "total", sum(fin_factor.values()))
        print(" event_year calls by (function, line):", dict(ey_calls), "total", sum(ey_calls.values()))
        rr = collections.Counter()
        for (ph, kind, i), n in Proxy.reads.items(): rr[(ph, kind, "rows")] += 1; rr[(ph, kind, "attr_reads")] += n
        print(" row proxies:", dict(rr))
        print(" explicit lists", len(A.explicit), "devices", len(A.devices), "groups", len(A.groups))

# split of the counted resolutions: memoised vs per-row (rows with row conversions)
scn = mech_scn(profile_kind="LINEAR_TREND", grid_kind="LINEAR_DECLINE_TO_FLOOR")
n_rowconv = sum(1 for r in scn.materials if r.conversions)
print("material rows with row-specific conversions:", n_rowconv, "of", len(scn.materials), "; fuels with conversions:", sum(1 for f in scn.construction.fuels if f.conversions))
# replicate use(): count per-row (extra) resolutions and their distinct triples
per_row = 0; triples = set(); memo = set()
for r in scn.materials:
    if r.composition is None and r.factor_id is not None and r.quantity_unit is not None:
        if r.conversions: per_row += 1; triples.add((r.factor_id, "A1-A3", r.quantity_unit))
    if r.transport.delivery_factor_id is not None and r.conversions and r.quantity_unit is not None:
        per_row += 1; triples.add((r.transport.delivery_factor_id, "A4", r.quantity_unit))
    if r.installation_factor_id is not None and r.conversions and r.quantity_unit is not None:
        per_row += 1; triples.add((r.installation_factor_id, "A5", r.quantity_unit))
for f in scn.construction.fuels:
    if f.conversions and f.factor_id is not None and f.unit is not None:
        per_row += 1; triples.add((f.factor_id, "A5", f.unit))
print("per-row (non-memoised) resolutions:", per_row, "covering distinct triples:", len(triples))
ex = json.load(open("/home/user/-/whole-life-carbon-jcat-study/09_APPROX_STUDY/04_VERIFICATION/unified_model_exactness.json"))
mc = ex["mechanism_counts"]["parametric_inputs"]
print("published:", mc["rows"], mc["distinct"], "\n totals:", mc["totals_only"], "\n full:", mc["full_outputs"])
