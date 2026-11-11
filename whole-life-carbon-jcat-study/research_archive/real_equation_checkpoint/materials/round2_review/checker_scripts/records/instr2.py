"""Where do factor-value multiplications, factor lookups and event enumerations happen in totals mode?"""
import sys, collections
import synth
from synth import model
from fastcalc import engine, closed_forms as cf

where = collections.Counter()
class CF(float):
    def __mul__(self, o):
        f = sys._getframe(1); where[("mul", f.f_code.co_name, f.f_lineno)] += 1
        return float(self) * float(o)
    __rmul__ = __mul__
class CountDict(dict):
    def get(self, k, d=None):
        f = sys._getframe(1); where[("lookup", f.f_code.co_name, f.f_lineno)] += 1
        return dict.get(self, k, d)
    def __getitem__(self, k):
        f = sys._getframe(1); where[("lookup", f.f_code.co_name, f.f_lineno)] += 1
        return dict.__getitem__(self, k)

scn = synth.make_scenario(5, "RC", "office", "S", 60.0, n_materials=400, n_equipment=120, n_refrigerants=10,
                          profile_kind="LINEAR_TREND", grid_kind="LINEAR_DECLINE_TO_FLOOR")
# distinct (factor, stage, unit) triples asked for without row conversions, and per-row calls with row conversions
triples = set(); with_extra = 0
def note(fid, stage, unit, extra):
    global with_extra
    if unit is None or fid is None: return
    if extra: with_extra += 1
    else: triples.add((fid, stage, unit))
for row in scn.materials:
    qu, rc = row.quantity_unit, row.conversions
    if row.composition is None: note(row.factor_id, "A1-A3", qu, rc)
    tr = row.transport
    if tr.delivery_factor_id is None: note(tr.factor_id, "A4", "tkm", ())
    else: note(tr.delivery_factor_id, "A4", qu, rc)
    if row.installation_factor_id is not None: note(row.installation_factor_id, "A5", qu, rc)
    note(row.end_of_life.haul_factor_id, "C2", "tkm", ())
    for rt in row.end_of_life.routes: note(rt.factor_id, "C4" if rt.route == "LANDFILL" else "C3", "kg", ())
for eq in scn.equipment:
    note(eq.factor_id, "A1-A3", eq.quantity_unit, ())
    for fid, st in ((eq.delivery_factor_id, "A4"), (eq.installation_factor_id, "A5")):
        if fid is not None: note(fid, st, eq.quantity_unit, ())
    if eq.eol_factor_id is not None: note(eq.eol_factor_id, "C3", "kg", ())
print("distinct (factor,stage,unit) triples from material+equipment rows without row conversions:", len(triples))
print("per-row resolutions forced by row-specific conversions (not memoised):", with_extra)
print("material rows with EPD (factor record looked up per row, outside use()):", sum(1 for r in scn.materials if r.epd is not None))
print("distinct EPD factor ids:", len({r.epd.factor_id for r in scn.materials if r.epd is not None}))

for rec in scn.factors.values(): rec.value = CF(rec.value)
scn.factors = CountDict(scn.factors)
conv_calls = collections.Counter(); orig = model.conversion_factor
def conv(*a, **k):
    f = sys._getframe(1); conv_calls[(f.f_code.co_name, f.f_lineno)] += 1; return orig(*a, **k)
model.conversion_factor = conv
rf = []; orig_rf = cf.refrigerant_fractions
def rfrac(T, rate, top_up, ev):
    rf.append(len(ev)); return orig_rf(T, rate, top_up, ev)
cf.refrigerant_fractions = rfrac
se = []; orig_se = cf.skip_weight_events
def swe(T, events):
    se.append(len(events)); return orig_se(T, events)
cf.skip_weight_events = swe
A = engine.aggregate(scn, False)
print("\n-- aggregate, totals mode --")
for k, v in sorted(where.items(), key=lambda kv: (kv[0][0], kv[0][2])): print("  ", k, v)
print("   model.conversion_factor calls:", dict(conv_calls), " engine counter unit_conversions_resolved =", A.stats["unit_conversions_resolved"])
print("   engine counter factor_resolutions =", A.stats["factor_resolutions"])
where.clear()
for k, v in list(A.fval.items()):
    if not isinstance(v, CF): A.fval[k] = CF(v)
R = engine.finish(A, 60.0, False, None)
print("\n-- finish, totals mode --")
for k, v in sorted(where.items(), key=lambda kv: (kv[0][0], kv[0][2])): print("  ", k, v)
print("   refrigerant event-year lists passed to refrigerant_fractions (lengths):", rf)
print("   explicit event lists filtered and passed to skip_weight_events (count, total events):", len(se), sum(se), "| explicit equipment:", len(A.explicit))
print("   engine counter event_lists_built =", R["_stats"]["event_lists_built"], " table_factor_products =", R["_stats"]["table_factor_products"])
print("   groups:", len(A.groups), " sum of len(group.u):", sum(len(g.u) for g in A.groups.values()), " lines if per row (approx: sum over tables of entries) ", sum(len(t) for t in R["_tables"].values()))
