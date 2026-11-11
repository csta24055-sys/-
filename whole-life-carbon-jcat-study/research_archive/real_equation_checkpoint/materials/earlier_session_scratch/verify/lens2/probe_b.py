import sys, os, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe import *
OPT = {"generic_stage_check": True}
s0 = base(composite_share=0.0, epd_share=0.0)

def run(label, mut, units=None, opts=None, extra=None, src=None):
    s = copy.deepcopy(src or s0); mut(s)
    o = dict(OPT); o.update(opts or {})
    ref, me, bad = diff(s, opts=o, label=label, show=False)
    print(f"[{label}] diff={bad}")
    if extra and ref is not None and me is not None:
        extra(s, ref, me)
    return s, ref, me

# ---- P5 refresh_cycle vs material_life
row = s0.materials[1]
print("row1 life", row.material_life, "refresh", row.refresh_cycle, "repair", row.repair_rate)
print("all rows (life, refresh):", [(r.material_life, r.refresh_cycle) for r in s0.materials])
run("material_life changed to 7 (refresh kept)", lambda s: s.materials[1].__setattr__("material_life", 7.0),
    extra=lambda s, r, m: print("   B4-03 ref", r["B4-03"]["by_item"][1], "mine", m["B4-03"]["by_item"][1]))
run("refresh_cycle None, material_life 7", lambda s: (s.materials[1].__setattr__("refresh_cycle", None), s.materials[1].__setattr__("material_life", 7.0)),
    extra=lambda s, r, m: print("   B4-03 ref", r["B4-03"]["by_item"][1], "mine", m["B4-03"]["by_item"][1]))
run("refresh_cycle 0", lambda s: s.materials[1].__setattr__("refresh_cycle", 0.0),
    extra=lambda s, r, m: print("   B4-03 ref", r["B4-03"]["by_item"][1], "mine", m["B4-03"]["by_item"][1]))
run("refresh_cycle negative", lambda s: s.materials[1].__setattr__("refresh_cycle", -5.0),
    extra=lambda s, r, m: print("   B4-03 ref", r["B4-03"]["by_item"][1], "mine", m["B4-03"]["by_item"][1]))

# ---- P7 A13-05 ranges
for lab, mut in (("Q negative", lambda s: s.materials[1].__setattr__("quantity", -5.0)),
                 ("w negative", lambda s: s.materials[1].__setattr__("waste_rate", -0.1)),
                 ("w == 1", lambda s: s.materials[1].__setattr__("waste_rate", 1.0)),
                 ("w == 0.999999999", lambda s: s.materials[1].__setattr__("waste_rate", 0.999999999)),
                 ("basis unknown 'FOO'", lambda s: s.materials[1].__setattr__("quantity_basis", "FOO")),
                 ("Q == 0", lambda s: s.materials[1].__setattr__("quantity", 0.0)),
                 ):
    run("A13-05 " + lab, mut, extra=lambda s, r, m: print("   ref q_ord,q_inst", r["A13-05"]["q_ord"][1], r["A13-05"]["q_inst"][1], "mine", m["A13-05"]["q_ord"][1], m["A13-05"]["q_inst"][1], "A13-01 row ref", r["A13-01"]["by_item"][1]))

# ---- P8 A13-04 ranges
for rr in (1.0, 1.5, -0.2, 0.0, 0.999999, None):
    def mut(s, rr=rr):
        s.materials[1].unquantified_cost_ratio = rr
    try:
        run(f"A13-04 r={rr}", mut, extra=lambda s, r, m: print("   ref row", r["A13-04"]["by_item"][1], "mine", m["A13-04"]["by_item"][1], "e", r["A13-01"]["by_item"][1]))
    except Exception as e:
        print("   EXC", type(e).__name__, e)

# ---- P9 C-05 ordered vs installed
def c05(s, r, m):
    print("   ref C-05", r["C-05"], "| mine", {k: m["C-05"][k] for k in ("ok", "violations", "under_allocated", "n_mass_unchecked")})
for i, row in enumerate(s0.materials):
    c = mine.conv(s0, row.quantity_unit, "kg", row.conversions)
    print("   row", i, row.quantity_unit, "basis", row.quantity_basis, "Q", row.quantity, "w", row.waste_rate, "conv_kg", c, "eol", row.end_of_life.mass_kg)
ref0 = registry.run_all(s0)
k = next(i for i, row in enumerate(s0.materials) if mine.conv(s0, row.quantity_unit, "kg", row.conversions) is not None and row.waste_rate and row.waste_rate > 0.02)
ck = mine.conv(s0, s0.materials[k].quantity_unit, "kg", s0.materials[k].conversions)
ordk, instk = ref0["A13-05"]["q_ord"][k] * ck, ref0["A13-05"]["q_inst"][k] * ck
print("row", k, "ordered kg", ordk, "installed kg", instk)
run("C-05 eol between installed and ordered", lambda s: s.materials[k].end_of_life.__setattr__("mass_kg", 0.5 * (ordk + instk)), units=["C-05"], extra=c05)
run("C-05 eol = ordered*(1+5e-7)", lambda s: s.materials[k].end_of_life.__setattr__("mass_kg", ordk * (1 + 5e-7)), units=["C-05"], extra=c05)
run("C-05 eol = ordered*(1+1e-12)", lambda s: s.materials[k].end_of_life.__setattr__("mass_kg", ordk * (1 + 1e-12)), units=["C-05"], extra=c05)
run("C-05 eol = ordered*(1+2e-6)", lambda s: s.materials[k].end_of_life.__setattr__("mass_kg", ordk * (1 + 2e-6)), units=["C-05"], extra=c05)
run("C-05 eol = ordered*2", lambda s: s.materials[k].end_of_life.__setattr__("mass_kg", ordk * 2), units=["C-05"], extra=c05)
def fr(vals):
    def f(s):
        for rt, v in zip(s.materials[k].end_of_life.routes, vals):
            rt.fraction = v
    return f
run("C-05 fractions sum 1+5e-7", fr([0.25, 0.25, 0.25, 0.25 + 5e-7]), units=["C-05"], extra=c05)
run("C-05 fractions sum 1+2e-6", fr([0.25, 0.25, 0.25, 0.25 + 2e-6]), units=["C-05"], extra=c05)
run("C-05 fractions sum 1-5e-7", fr([0.25, 0.25, 0.25, 0.25 - 5e-7]), units=["C-05"], extra=c05)
run("C-05 fractions sum 1-2e-6", fr([0.25, 0.25, 0.25, 0.25 - 2e-6]), units=["C-05"], extra=c05)
run("C-05 negative fraction, sum 1", fr([-0.1, 0.6, 0.25, 0.25]), units=["C-05"], extra=c05)
run("C-05 fraction None", fr([None, 0.5, 0.25, 0.25]), units=["C-05"], extra=c05)
run("C-05 eol mass None", lambda s: s.materials[k].end_of_life.__setattr__("mass_kg", None), extra=lambda s, r, m: (c05(s, r, m), print("   C2/C3/C4 n_skipped ref", r["C2-01"]["n_skipped"], r["C3-01"]["n_skipped"], r["C4-01"]["n_skipped"], "mine", m["C2-01"]["n_skipped"], m["C3-01"]["n_skipped"], m["C4-01"]["n_skipped"])))
run("C-05 eol mass negative", lambda s: s.materials[k].end_of_life.__setattr__("mass_kg", -5.0), extra=lambda s, r, m: (c05(s, r, m), print("   C3 row ref", r["C3-01"]["by_item"][k], "mine", m["C3-01"]["by_item"][k])))
