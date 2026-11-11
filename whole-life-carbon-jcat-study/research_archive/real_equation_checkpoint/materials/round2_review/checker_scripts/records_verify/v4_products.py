"""Count reads of factor values (fval[...]) by source line, totals vs full mode; count list constructions in finish (totals)."""
import sys, collections
import synth
from fastcalc import engine, closed_forms as cf

class CountingDict(dict):
    reads = collections.Counter()
    def __getitem__(self, k):
        f = sys._getframe(1)
        # called from genexpr/lambda too: record function name and line
        CountingDict.reads[(f.f_code.co_name, f.f_lineno)] += 1
        return dict.__getitem__(self, k)

orig_init = engine.Aggregate.__init__
def patched(self, scn, detail):
    orig_init(self, scn, detail)
    self.fval = CountingDict(self.fval)
engine.Aggregate.__init__ = patched

def mech_scn():
    return synth.make_scenario(5, "RC", "office", "S", 60.0, n_materials=400, n_equipment=120, n_refrigerants=10,
                               profile_kind="LINEAR_TREND", grid_kind="LINEAR_DECLINE_TO_FLOOR")
src = open(engine.__file__).read().split("\n")
for detail in (False, True):
    scn = mech_scn()
    CountingDict.reads.clear()
    A = engine.aggregate(scn, detail)
    agg = dict(CountingDict.reads); CountingDict.reads.clear()
    R = engine.finish(A, 60.0, detail, None)
    fin = dict(CountingDict.reads)
    print(f"==== detail={detail}: engine row_factor_products={R['_stats']['row_factor_products']} table_factor_products={R['_stats']['table_factor_products']}")
    for name, d in (("aggregate", agg), ("finish/_detail", fin)):
        print("  ", name, "fval reads total", sum(d.values()))
        for (fn, ln), n in sorted(d.items(), key=lambda x: x[0][1]):
            print(f"      line {ln:5d} ({fn}) x{n}: {src[ln-1].strip()[:110]}")
    if detail:
        n_emfg = sum(1 for k in A.rows["kind"] if k is not None and True)
        # rows where act_mfg is not None -> e_mfg = act_mfg * f is one more product per row (f already read)
        n_act = sum(1 for a, b in zip(A.rows["a1301"], A.rows["a1303"]) if (a or b))
        print("   material rows with a manufacturing product act_mfg*f (line 470), non-zero:", n_act)
# list constructions in totals mode (finish): replicate conditions from engine lines 846-892
scn = mech_scn(); A = engine.aggregate(scn, False); T = 60.0
n_explicit_lists = len(A.explicit)
lens = []
for dev, ok in A.devices:
    if not ok: continue
    if dev.change_years is not None:
        lens.append(len([cf.event_year(t) for t in sorted(float(t) for t in dev.change_years if t > 0 and cf.inside(t, T))]))
    else:
        lens.append(cf.renewal_count(T, dev.service_life))
print("totals mode: filtered explicit equipment event lists built in finish (line 851):", n_explicit_lists,
      "; refrigerant change-year lists built (lines 890-892):", len(lens), "lengths", lens,
      "; of which periodic enumerations:", sum(1 for d, ok in A.devices if ok and d.change_years is None))
print("engine counter event_lists_built (totals):", engine.finish(A, T, False, None)["_stats"]["event_lists_built"])
