import sys, os, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe import *
OPT = {"generic_stage_check": True}
s0 = base(composite_share=0.0, epd_share=0.0)

def run(label, mut, units=None, opts=None, extra=None, src=None):
    s = copy.deepcopy(src or s0); mut(s)
    o = dict(OPT); o.update(opts or {})
    ref, me, bad = diff(s, opts=o, label=label, show=False, units=units)
    print(f"[{label}] diff={bad}")
    if extra and ref is not None and me is not None:
        extra(s, ref, me)
    return s, ref, me

print("equipment:", [(e.quantity, e.quantity_unit, e.factor_id, e.service_life, e.repair_rate, e.replacement_event_list, e.end_of_life_mass_kg, e.eol_factor_id, e.delivery_factor_id, e.installation_factor_id) for e in s0.equipment])
def eq(**kw):
    def f(s):
        e = s.equipment[0]
        for k, v in kw.items():
            setattr(e, k, v)
    return f
def ev(s, r, m):
    print("   ref events", r["B4-01"]["events"][0], "B4-02 eq0", r["B4-02"]["by_item_equipment"][0], "| mine", m["B4-01"]["events"][0], m["B4-02"]["by_item_equipment"][0])
    y = [(i, a, b) for i, (a, b) in enumerate(zip(r["B3-01"]["by_year"], m["B3-01"]["by_year"])) if abs(a - b) > 1e-9 * max(abs(a), 1)]
    print("   B3-01 by_year diffs (idx, ref, mine):", y[:6])
U = ["B4-01", "B4-02", "B3-01", "B3-02", "X-01", "X-14"]
run("eq explicit unsorted+dups [30,10,10]", eq(replacement_event_list=[30, 10, 10]), units=U, extra=ev)
run("eq explicit [] with service_life", eq(replacement_event_list=[], service_life=10.0), units=U, extra=ev)
run("eq explicit [0,60,61,-1,59]", eq(replacement_event_list=[0, 60, 61, -1, 59]), units=U, extra=ev)
run("eq explicit floats [10.5, 10.9]", eq(replacement_event_list=[10.5, 10.9]), units=U, extra=ev)
run("eq neither", eq(replacement_event_list=None, service_life=None), units=U, extra=ev)
run("eq life 0", eq(replacement_event_list=None, service_life=0.0), units=U, extra=ev)
run("eq life 0.4 (several per year)", eq(replacement_event_list=None, service_life=0.4), units=U, extra=lambda s, r, m: print("   n ref", len(r["B4-01"]["events"][0]), "mine", len(m["B4-01"]["events"][0])))
run("eq quantity None", eq(quantity=None), units=U, extra=ev)
run("eq eol mass None", eq(end_of_life_mass_kg=None), units=U, extra=ev)
run("eq repair None", eq(repair_rate=None), units=U, extra=ev)
def unlic(fid):
    def f(s):
        s.factors[fid].licence_status = "UNKNOWN"
    return f
e0 = s0.equipment[0]
print("eq0 factors", e0.factor_id, e0.delivery_factor_id, e0.installation_factor_id, e0.eol_factor_id)
for fid in (e0.factor_id, e0.delivery_factor_id, e0.installation_factor_id, e0.eol_factor_id):
    if fid:
        run(f"eq0 factor {fid} unlicensed", unlic(fid), units=U, extra=ev)
run("eq quantity_unit 'set' (no conversion)", eq(quantity_unit="set"), units=U, extra=ev)
# equipment delivery factor in different unit with conversion
def eqconv(s):
    s.unit_conversions.append(model.UnitConversion("unit", "dozen", 1.0 / 12.0, "probe"))
    fid = s.equipment[0].delivery_factor_id or s.equipment[0].installation_factor_id
    s.factors[fid].unit = "dozen"
run("eq delivery/installation factor per 'dozen' with conversion unit->dozen", eqconv, units=U, extra=ev)
def eqconv2(s):
    s.unit_conversions.append(model.UnitConversion("unit", "dozen", 1.0 / 12.0, "probe"))
    s.factors[s.equipment[0].factor_id].unit = "dozen"
run("eq main factor per 'dozen' with conversion", eqconv2, units=U, extra=ev)
def eqconv3(s):
    s.unit_conversions.append(model.UnitConversion("kg", "lb", 2.2, "probe"))
    s.factors[s.equipment[0].eol_factor_id].unit = "lb"
run("eq eol factor per 'lb' with conversion kg->lb", eqconv3, units=U, extra=ev)

# ---- materials: installation factor and conversions
print("materials inst:", [(i, r.quantity_unit, r.installation_factor_id, r.transport.delivery_factor_id, r.transport.factor_id, r.refresh_cycle) for i, r in enumerate(s0.materials)])
