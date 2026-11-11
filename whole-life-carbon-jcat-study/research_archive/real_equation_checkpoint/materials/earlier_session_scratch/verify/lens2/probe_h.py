import sys, os, copy, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe import *
from fractions import Fraction
from decimal import Decimal
OPT = {"generic_stage_check": True}

# ---- float boundary: event mathematically exactly at T
print("3*33.3 =", repr(3 * 33.3), " < 99.9 ?", 3 * 33.3 < 99.9, "| exact decimal: 3*33.3 == 99.9 ->", 3 * Decimal("33.3") == Decimal("99.9"))
cases = []
for T in ("42.5", "62.5", "99.9", "60", "50", "75", "30", "100"):
    for Ls in ("33.3", "11.1", "9.99", "19.98", "49.95", "3.33", "1.11", "0.7", "2.2", "8.5", "12.5", "0.1", "0.3", "0.6", "1.2", "2.4", "4.8", "1.5", "7.5", "0.2", "0.4", "6.6", "3.3", "16.65"):
        Td, Ld = Decimal(T), Decimal(Ls)
        Tf, Lf = float(T), float(Ls)
        exact = [n for n in range(1, 2000) if n * Ld < Td]
        n = 1; fl = []
        while n * Lf < Tf:
            fl.append(n); n += 1
        if len(exact) != len(fl):
            cases.append((T, Ls, len(exact), len(fl)))
print("decimal (T, L) pairs where float counting differs from exact decimal counting:", cases)
# year misallocation ceil(n*L) vs exact
mis = []
for Ls in ("2.2", "1.1", "0.1", "3.3", "6.6", "0.7", "1.4", "0.3", "0.6", "4.4", "5.5", "8.8", "12.1", "0.9", "1.8"):
    Ld, Lf = Decimal(Ls), float(Ls)
    for n in range(1, 400):
        ye = math.ceil(n * Ld); yf = math.ceil(n * Lf)
        if ye != yf:
            mis.append((Ls, n, str(n * Ld), repr(n * Lf), int(ye), yf)); break
print("first year misallocations (L, n, exact tau, float tau, exact year, float year):", mis)

# ---- reference behaviour for T=99.9, L=33.3
s = make_scenario(7, "RC", "office", "S", 99.9, scenario_id="PROBE", n_materials=12, n_equipment=6, n_refrigerants=4, composite_share=0.0, epd_share=0.0)
s.equipment[0].replacement_event_list = None; s.equipment[0].service_life = 33.3
s.materials[1].refresh_cycle = 33.3
s.refrigerants[0].change_years = None; s.refrigerants[0].service_life = 33.3
s.boundary.reconstruction_scenario = "REBUILD_IDENTICAL"; s.boundary.replacement_cycle = 33.3; s.boundary.reconstruction_scope_fraction = 1.0
ref, me, bad = diff(s, opts=OPT, label="T=99.9 L=33.3")
print("   ref B4-01 events eq0", ref["B4-01"]["events"][0], "B4-03 row1", ref["B4-03"]["by_item"][1], "B5 n_events", ref["B5-01"]["n_events"], "B1 before_events", ref["B1-02"]["_state"][0]["before_events"])
s2 = copy.deepcopy(s); s2.boundary.study_period = 60.0
for o in (s2.equipment[0],):
    o.service_life = 20.0
s2.materials[1].refresh_cycle = 20.0; s2.refrigerants[0].service_life = 20.0; s2.boundary.replacement_cycle = 20.0
ref2 = registry.run_all(s2)
print("   T=60 L=20: B4-01 events eq0", ref2["B4-01"]["events"][0], "B4-03 row1", ref2["B4-03"]["by_item"][1], "B5 n_events", ref2["B5-01"]["n_events"])
print("   T=99.9: B5 value", ref["B5-01"]["value"], "per event", ref["B5-01"]["value"] / max(1, ref["B5-01"]["n_events"]), "SUM-03", ref["SUM-03"]["value"])

# B3-01 partial-year effect of float year misallocation: T=55.5, L=2.2 (event n=25 mathematically at 55.0 -> year 55)
s3 = make_scenario(7, "RC", "office", "S", 55.5, scenario_id="PROBE", n_materials=12, n_equipment=6, n_refrigerants=4, composite_share=0.0, epd_share=0.0)
del s3.materials[1:]; del s3.equipment[1:]
s3.equipment[0].replacement_event_list = None; s3.equipment[0].service_life = 2.2
s3.materials[0].refresh_cycle = None
r3 = registry.run_all(s3)
ev = r3["B4-01"]["events"][0]
print("   T=55.5 L=2.2 events tail", ev[-3:], "years", [math.ceil(t) for t in ev[-3:]])
e0, rr = r3["X-01"]["by_item"][0], s3.equipment[0].repair_rate
by = r3["B3-01"]["by_year"]
m0 = r3["A13-01"]["by_item"][0] * (s3.materials[0].repair_rate or 0.0)
print("   B3-01 by_year[54..56]", by[54:57], "equipment e0*r", e0 * rr, "material e0*r", m0)

# ---- QA-02 vs B4-01 at t = 0
s4 = base(composite_share=0.0, epd_share=0.0)
s4.equipment[0].replacement_event_list = [0, 30]
s4.refrigerants[0].change_years = [0]; s4.refrigerants[0].service_life = None
r4 = registry.run_all(s4)
print("QA-02 with explicit event at t=0:", r4["QA-02"], "| B4-01 events", r4["B4-01"]["events"][0], "| B1 events", r4["B1-02"]["_state"][0]["before_events"])
s5 = base(composite_share=0.0, epd_share=0.0)
s5.equipment[0].replacement_event_list = [60]
r5 = registry.run_all(s5)
print("QA-02 with explicit event at t=T:", r5["QA-02"], "| B4-01 events", r5["B4-01"]["events"][0])

# ---- SYS-02 and electricity units
s6 = base(composite_share=0.0, epd_share=0.0)
r6a = registry.run_all(s6)
s6.operation.electricity.unit = "MWh/year"; s6.operation.grid.unit = "kgCO2e/MJ"; s6.operation.onsite_generation.unit = "MJ/year"
r6 = registry.run_all(s6)
print("electricity MWh/year, grid per MJ, generation MJ/year: SYS-02", r6["SYS-02"]["ok"], "B6-03", r6["B6-03"]["value"], "base", r6a["B6-03"]["value"])
