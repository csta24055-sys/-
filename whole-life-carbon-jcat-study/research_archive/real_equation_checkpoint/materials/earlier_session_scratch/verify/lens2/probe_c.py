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

print("devices:", [(d.charge_mass_kg, d.gwp, d.annual_leak_rate, d.replacement_loss_rate, d.end_of_life_recovery_rate, d.change_years, d.service_life, d.top_up) for d in s0.refrigerants])
def b1(s, r, m):
    print("   ref  B1-02", r["B1-02"]["by_item"][0], "state", r["B1-02"]["_state"][0], "B1-03", r["B1-03"]["value"], "B1-04", r["B1-04"]["value"])
    print("   mine B1-02", m["B1-02"]["by_item"][0], "state", m["B1-02"]["_state"][0], "B1-03", m["B1-03"]["value"], "B1-04", m["B1-04"]["value"])
def dev(**kw):
    def f(s):
        d = s.refrigerants[0]
        for k, v in kw.items():
            setattr(d, k, v)
        del s.refrigerants[1:]
    return f
B1 = ["B1-02", "B1-03", "B1-04"]
run("B1 no top-up, life 10", dev(top_up=False, change_years=None, service_life=10.0, annual_leak_rate=0.05, charge_mass_kg=100.0, gwp=1.0, replacement_loss_rate=0.1, end_of_life_recovery_rate=0.7), units=B1, extra=b1)
run("B1 both change_years [7] and service_life 10", dev(top_up=False, change_years=[7], service_life=10.0, annual_leak_rate=0.05, charge_mass_kg=100.0, gwp=1.0, replacement_loss_rate=0.1, end_of_life_recovery_rate=0.7), units=B1, extra=b1)
run("B1 change_years [] and service_life 10", dev(top_up=False, change_years=[], service_life=10.0, annual_leak_rate=0.05, charge_mass_kg=100.0, gwp=1.0, replacement_loss_rate=0.1, end_of_life_recovery_rate=0.7), units=B1, extra=b1)
run("B1 neither", dev(top_up=False, change_years=None, service_life=None, annual_leak_rate=0.05, charge_mass_kg=100.0, gwp=1.0, replacement_loss_rate=0.1, end_of_life_recovery_rate=0.7), units=B1, extra=b1)
run("B1 duplicates [10,10,20]", dev(top_up=False, change_years=[10, 10, 20], service_life=None, annual_leak_rate=0.05, charge_mass_kg=100.0, gwp=1.0, replacement_loss_rate=0.1, end_of_life_recovery_rate=0.7), units=B1, extra=b1)
run("B1 unsorted [20,10]", dev(top_up=False, change_years=[20, 10], service_life=None, annual_leak_rate=0.05, charge_mass_kg=100.0, gwp=1.0, replacement_loss_rate=0.1, end_of_life_recovery_rate=0.7), units=B1, extra=b1)
run("B1 list with 0, 60, 65, -3", dev(top_up=False, change_years=[0, 60, 65, -3, 59], service_life=None, annual_leak_rate=0.05, charge_mass_kg=100.0, gwp=1.0, replacement_loss_rate=0.1, end_of_life_recovery_rate=0.7), units=B1, extra=b1)
run("B1 two lives in one year: life 0.5", dev(top_up=False, change_years=None, service_life=0.5, annual_leak_rate=0.05, charge_mass_kg=100.0, gwp=1.0, replacement_loss_rate=0.1, end_of_life_recovery_rate=0.7), units=B1, extra=lambda s, r, m: print("   ref n events", len(r["B1-02"]["_state"][0]["before_events"]), "B1-03", r["B1-03"]["value"], "mine n", len(m["B1-02"]["_state"][0]["before_events"]), m["B1-03"]["value"]))
run("B1 leak rate 1.0 no top-up", dev(top_up=False, change_years=None, service_life=25.0, annual_leak_rate=1.0, charge_mass_kg=100.0, gwp=1.0, replacement_loss_rate=0.1, end_of_life_recovery_rate=0.7), units=B1, extra=b1)
run("B1 leak rate 1.5 (out of range) no top-up", dev(top_up=False, change_years=None, service_life=25.0, annual_leak_rate=1.5, charge_mass_kg=100.0, gwp=1.0, replacement_loss_rate=0.1, end_of_life_recovery_rate=0.7), units=B1, extra=b1)
run("B1 recovery None", dev(top_up=False, change_years=None, service_life=25.0, annual_leak_rate=0.05, charge_mass_kg=100.0, gwp=1.0, replacement_loss_rate=0.1, end_of_life_recovery_rate=None), units=B1, extra=b1)
run("B1 loss None", dev(top_up=False, change_years=None, service_life=25.0, annual_leak_rate=0.05, charge_mass_kg=100.0, gwp=1.0, replacement_loss_rate=None, end_of_life_recovery_rate=0.7), units=B1, extra=b1)
run("B1 recovery 1.3", dev(top_up=False, change_years=None, service_life=25.0, annual_leak_rate=0.05, charge_mass_kg=100.0, gwp=1.0, replacement_loss_rate=0.1, end_of_life_recovery_rate=1.3), units=B1, extra=b1)
# non-integer T with event in the final partial year
sT = base(period=60.5, composite_share=0.0, epd_share=0.0)
run("B1 T=60.5 life 60.2 (event inside last partial year)", dev(top_up=False, change_years=None, service_life=60.2, annual_leak_rate=0.05, charge_mass_kg=100.0, gwp=1.0, replacement_loss_rate=0.1, end_of_life_recovery_rate=0.7), units=B1, extra=b1, src=sT)
run("B1 T=60.5 life 60.0", dev(top_up=True, change_years=None, service_life=60.0, annual_leak_rate=0.05, charge_mass_kg=100.0, gwp=1.0, replacement_loss_rate=0.1, end_of_life_recovery_rate=0.7), units=B1, extra=b1, src=sT)
