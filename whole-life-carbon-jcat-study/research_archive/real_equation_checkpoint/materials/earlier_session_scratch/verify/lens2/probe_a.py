import sys, os, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe import *

# ---------- P1/P2 EPD applicability source and boundary
s0 = base(composite_share=0.0, epd_share=1.0, epd_inapplicable_share=0.0)
ref, me, bad = diff(s0, label="EPD base")
print(" kinds", ref["X-15"]["kind"])
i = epd_row(s0)
row = s0.materials[i]; rec = s0.factors[row.epd.factor_id]
print(" row", i, "epd decl", row.epd.declared_stages, row.epd.declared_unit, row.epd.valid_until, "| rec", rec.stages, rec.unit, rec.valid_until, "| assess", s0.project.assessment_date, "qunit", row.quantity_unit)

def kind_after(mut, label):
    s = copy.deepcopy(s0); mut(s)
    r = registry.run_all(s)
    print(f"   {label:70s} -> ref kind[{i}] = {r['X-15']['kind'][i]}")
    return r

kind_after(lambda s: s.materials[i].epd.__setattr__("declared_stages", ["A1-A3", "A4"]), "declaration stages widened, record unchanged")
kind_after(lambda s: s.factors[s.materials[i].epd.factor_id].__setattr__("stages", ["A1-A3", "A4"]), "record stages widened, declaration unchanged")
kind_after(lambda s: s.materials[i].epd.__setattr__("valid_until", "2000-01-01"), "declaration expired, record unchanged")
kind_after(lambda s: s.factors[s.materials[i].epd.factor_id].__setattr__("valid_until", "2000-01-01"), "record expired, declaration unchanged")
kind_after(lambda s: s.materials[i].epd.__setattr__("declared_unit", "zzz"), "declaration unit unconvertible, record unchanged")
kind_after(lambda s: s.factors[s.materials[i].epd.factor_id].__setattr__("unit", "zzz"), "record unit unconvertible, declaration unchanged")
def both_valid(d):
    def f(s):
        s.materials[i].epd.valid_until = d; s.factors[s.materials[i].epd.factor_id].valid_until = d
    return f
kind_after(both_valid(s0.project.assessment_date), "valid_until == assessment_date (both)")
kind_after(lambda s: s.factors[s.materials[i].epd.factor_id].__setattr__("valid_until", None), "record valid_until None, declaration valid")
def decl_none(s):
    s.materials[i].epd.valid_until = None
try:
    kind_after(decl_none, "declaration valid_until None")
except Exception as e:
    print("   declaration valid_until None -> REF RAISED", type(e).__name__, e)
kind_after(lambda s: s.factors[s.materials[i].epd.factor_id].__setattr__("licence_status", "UNKNOWN"), "record licence UNKNOWN")
# date format issue: non-padded ISO string
kind_after(both_valid("2100-1-1"), "valid_until '2100-1-1' (non-padded)")
kind_after(both_valid(s0.project.assessment_date[:8] + "9"), "valid_until day '9' non padded same month")

# ---------- P3 generic factor stage scope
s1 = base(composite_share=0.0, epd_share=0.0)
j = 0
fid = s1.materials[j].factor_id
print("generic row", j, fid, s1.factors[fid].stages, s1.factors[fid].unit, s1.materials[j].quantity_unit)
for st in (["A1-A3", "A4"], ["C3"], []):
    s = copy.deepcopy(s1); s.factors[fid].stages = st
    r = registry.run_all(s)
    print(f"   generic factor stages={st}: ref kind={r['X-15']['kind'][j]} A13-01 row={r['A13-01']['by_item'][j]} n_skipped={r['A13-01']['n_skipped']}")
# a transport per-tkm factor used as generic manufacturing factor of a row whose unit is tkm?
# ---------- P4 composite component
s2 = base(composite_share=1.0, epd_share=0.0)
row = s2.materials[0]; c0 = row.composition[0]
print("composite row0 comps", [(c.factor_id, c.mass_fraction, s2.factors[c.factor_id].unit, s2.factors[c.factor_id].stages) for c in row.composition], "qunit", row.quantity_unit)
for lab, mut in (("component stages ['A1-A3','A4']", lambda s: s.factors[c0.factor_id].__setattr__("stages", ["A1-A3", "A4"])),
                 ("component unit 't'", lambda s: s.factors[c0.factor_id].__setattr__("unit", "t")),
                 ("fraction sum 1+2e-6", lambda s: s.materials[0].composition[0].__setattr__("mass_fraction", c0.mass_fraction + 2e-6)),
                 ("fraction sum 1+5e-7", lambda s: s.materials[0].composition[0].__setattr__("mass_fraction", c0.mass_fraction + 5e-7)),
                 ("negative fraction compensated", lambda s: (s.materials[0].composition[0].__setattr__("mass_fraction", c0.mass_fraction + 0.5), s.materials[0].composition[1].__setattr__("mass_fraction", s.materials[0].composition[1].mass_fraction - 0.5 - 0.3), s.materials[0].composition[2].__setattr__("mass_fraction", s.materials[0].composition[2].mass_fraction + 0.3))),
                 ("empty composition []", lambda s: s.materials[0].__setattr__("composition", [])),
                 ("composite row also has generic factor_id", lambda s: (s.materials[0].__setattr__("factor_id", s1.materials[0].factor_id), s.factors.__setitem__(s1.materials[0].factor_id, s1.factors[s1.materials[0].factor_id]), s.factors[c0.factor_id].__setattr__("licence_status", "UNKNOWN"))),
                 ):
    s = copy.deepcopy(s2); mut(s)
    ref, me, bad = diff(s, label=lab, show=False)
    print(f"   {lab:45s}: ref A13-02[0]={ref['A13-02']['by_item'][0]} kind={ref['X-15']['kind'][0]} | mine A13-02[0]={me['A13-02']['by_item'][0]} kind={me['X-15']['kind'][0]} | diff={bad}")
