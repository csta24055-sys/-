import sys, copy, math, json, time
import synth
from synth import population
from refcalc import registry, base
registry.load_all()
bench = population.standard_benchmark()
S = bench[0]
r = registry.run_all(S)
bs = r["X-02"]["by_stage"]
print("== benchmark S stage vector ==", {k: round(v) for k, v in bs.items()})
print("SUM-01/02/03", r["SUM-01"]["value"], r["SUM-02"]["value"], r["SUM-03"]["value"], "complete", r["X-02"]["complete"])

print("\n== A1: B-10 claim: B2 share of SUM-02 on benchmark S ==", r["B2-01"]["value"] / r["SUM-02"]["value"])
print("== B-10 claim 11.5%: B2-01 / B6-03 over edge cases ==")
for n_, e in population.edge_cases():
    try:
        re_ = registry.run_all(e)
    except Exception as ex:
        continue
    if re_["B6-03"]["value"]:
        x = re_["B2-01"]["value"] / re_["B6-03"]["value"]
        if abs(x - 0.115) < 0.0006: print("  ", n_, x)
print("   benchmark S: B2-01/B6-03 =", r["B2-01"]["value"] / r["B6-03"]["value"])

print("\n== A2: B-11 claim: equipment initial delivery / installation not counted (benchmark S) ==")
dlv = inst = 0.0
for eq in S.equipment:
    lines, unusable = [], False
    for fid, stage, tag in ((eq.delivery_factor_id, "A4", "d"), (eq.installation_factor_id, "A5", "i")):
        if fid is None: continue
        hit = base.lookup(S, fid, stage, eq.quantity_unit)
        if hit is None or not base.nonneg(eq.quantity): continue
        v = eq.quantity * hit[1] * hit[0].value
        if tag == "d": dlv += v
        else: inst += v
print("equipment initial delivery", dlv, "= %.4f%% of A4" % (100 * dlv / bs["A4"]), "; installation", inst, "= %.3f%% of A5" % (100 * inst / bs["A5"]))
print("== unlisted: MATERIAL initial installation (installation_factor_id is used at renewals only) ==")
q = r["A13-05"]["q_ord"]; minst = 0.0; nrows = 0
for i, row in enumerate(S.materials):
    if row.installation_factor_id is None or q[i] is None: continue
    hit = base.lookup(S, row.installation_factor_id, "A5", row.quantity_unit, row.conversions)
    if hit is None: continue
    minst += q[i] * hit[1] * hit[0].value; nrows += 1
print("material rows with installation factor", nrows, "of", len(S.materials), "initial installation not in A5:", minst, "= %.2f%% of A5, %.3f%% of SUM-01, %.3f%% of SUM-03" % (100 * minst / bs["A5"], 100 * minst / r["SUM-01"]["value"], 100 * minst / r["SUM-03"]["value"]))

print("\n== A3: B4-02 / B3-01 reading: does 'A1-A3 row result' include the A13-04 uplift? ==")
up = r["A13-04"]["by_item"]; nev = r["B4-03"]["by_item"]
extra_b4 = sum(up[i] * nev[i] for i in range(len(S.materials)))
print("A13-04 value", r["A13-04"]["value"], "share of A1-A3 %.2f%%" % (100 * r["A13-04"]["value"] / bs["A1-A3"]))
print("B4 (code, without uplift)", bs["B4"], "with uplift", bs["B4"] + extra_b4, "diff %.3f%% of B4, %.4f%% of SUM-03" % (100 * extra_b4 / bs["B4"], 100 * extra_b4 / r["SUM-03"]["value"]))
T = S.boundary.study_period; w = base.year_weights(T)
extra_b3 = 0.0
for i, row in enumerate(S.materials):
    if not base.nonneg(row.repair_rate) or up[i] == 0.0: continue
    skip = {base.event_year(t) for t in base.periodic_events(T, row.refresh_cycle)}
    extra_b3 += sum(up[i] * row.repair_rate * w[y] for y in range(1, len(w)) if y not in skip)
print("B3 (code, without uplift)", bs["B3"], "with uplift", bs["B3"] + extra_b3, "diff %.3f%% of B3" % (100 * extra_b3 / bs["B3"]))
print("== B4-02 text: equipment delivery/installation at renewals are not in the text ('搬入（A4 の行結果）') ==")
eq_extra = 0.0
from refcalc import units_b
for j, eq in enumerate(S.equipment):
    ev = r["B4-01"]["events"][j]
    for fid, act in units_b.equipment_extra_lines(S, eq)[0]:
        eq_extra += act * S.factors[fid].value * len(ev)
print("equipment delivery+installation inside B4:", eq_extra, "= %.3f%% of B4, %.4f%% of SUM-03" % (100 * eq_extra / bs["B4"], 100 * eq_extra / r["SUM-03"]["value"]))
mat_inst_b4 = 0.0
for i, row in enumerate(S.materials):
    ln = units_b.material_install_line(S, row, q[i])
    if ln: mat_inst_b4 += ln[1] * S.factors[ln[0]].value * nev[i]
print("material installation inside B4:", mat_inst_b4, "= %.3f%% of B4" % (100 * mat_inst_b4 / bs["B4"]))

print("\n== A4: B1-02 text has no GWP: mass reading vs CO2e reading ==")
mass = 0.0
for dev in S.refrigerants:
    m = dev.charge_mass_kg
    evy = {}
    for tau in units_b.device_events(T, dev): evy[base.event_year(tau)] = evy.get(base.event_year(tau), 0) + 1
    for y in range(1, len(w)):
        leak = m * dev.annual_leak_rate * w[y]; mass += leak
        if not dev.top_up: m -= leak
        if evy.get(y): m = dev.charge_mass_kg
print("B1-02 code value (kgCO2e)", r["B1-02"]["value"], "literal text (kg of refrigerant)", mass)

print("\n== A5: B-7 claim (T=60, cycle 25, phi=1.0): renewals 31 -> 19, B4 -40.6%, whole life -1.9% ==")
for n_, e in population.edge_cases():
    if n_ != "rebuild_within_period": continue
    for phi in (e.boundary.reconstruction_scope_fraction, 1.0):
        e2 = copy.deepcopy(e); e2.boundary.reconstruction_scope_fraction = phi
        re_ = registry.run_all(e2)
        n_now = sum(re_["B4-03"]["by_item"]) + re_["B4-01"]["n_events"]
        # reset variant: renewals counted inside each segment between rebuild events
        C = e2.boundary.replacement_cycle; Tt = e2.boundary.study_period
        cuts = [0.0] + base.periodic_events(Tt, C) + [Tt]
        def count_reset(period):
            return sum(len(base.periodic_events(b - a, period)) for a, b in zip(cuts, cuts[1:]))
        n_reset = 0; b4_reset = 0.0
        srcs = ("A13-01", "A13-03", "A4-01", "A4-02", "C2-01", "C3-01", "C4-01")
        for i, row in enumerate(e2.materials):
            k0 = re_["B4-03"]["by_item"][i]
            k1 = count_reset(row.refresh_cycle)
            n_reset += k1
            if k0: b4_reset += re_["B4-02"]["by_item_material"][i] / k0 * k1
        for j, eq in enumerate(e2.equipment):
            ev = re_["B4-01"]["events"][j]
            if eq.replacement_event_list is not None:
                k1 = len(ev)
            else:
                k1 = count_reset(eq.service_life)
            n_reset += k1
            if ev: b4_reset += re_["B4-02"]["by_item_equipment"][j] / len(ev) * k1
        b4 = re_["X-02"]["by_stage"]["B4"]; wl = re_["SUM-03"]["value"]
        print("phi", phi, "renewals", n_now, "->", n_reset, "B4", b4, "->", b4_reset, "(%.1f%%)" % (100 * (b4_reset - b4) / b4), "whole life change %.2f%%" % (100 * (b4_reset - b4) / wl),
              "| B3 not recomputed")

print("\n== A6: duplicate explicit events count twice; QA-02 silent ==")
e = synth.make_scenario(21, "RC", "office", "S", 60.0, n_materials=6, n_equipment=4, n_refrigerants=2, explicit_event_share=1.0)
r0 = registry.run_all(e)
e2 = copy.deepcopy(e); e2.equipment[0].replacement_event_list = [15, 15, 15]
e3 = copy.deepcopy(e); e3.equipment[0].replacement_event_list = [15]
ra, rb = registry.run_all(e2), registry.run_all(e3)
print("[15] B4 eq0", rb["B4-02"]["by_item_equipment"][0], "[15,15,15] B4 eq0", ra["B4-02"]["by_item_equipment"][0], "QA-02", ra["QA-02"], "complete", ra["X-02"]["complete"])

print("\n== A7: SYS-02 does not look at the EPD factor; SYS-03 vs X-14 for equipment without eol factor ==")
e = synth.make_scenario(22, "RC", "office", "S", 60.0, n_materials=8, n_equipment=4, n_refrigerants=2, epd_share=1.0, epd_inapplicable_share=0.0, composite_share=0.0)
r0 = registry.run_all(e)
e2 = copy.deepcopy(e)
row = e2.materials[0]
e2.factors[row.epd.factor_id].unit = "piece"; row.epd.declared_unit = "piece"
e2.factors[e2.materials[1].epd.factor_id].stages = ["A1-A3", "A4"]; e2.materials[1].epd.declared_stages = ["A1-A3", "A4"]
ra = registry.run_all(e2)
print("X-15 kinds", r0["X-15"]["kind"][:3], "->", ra["X-15"]["kind"][:3], "n_epd_declined", ra["X-15"]["n_epd_declined"], "SYS-02", ra["SYS-02"]["ok"], ra["SYS-02"]["violations"], ra["SYS-02"]["stage_mismatches"], "complete", ra["X-02"]["complete"],
      "A1-A3", r0["X-02"]["by_stage"]["A1-A3"], "->", ra["X-02"]["by_stage"]["A1-A3"])
e2 = copy.deepcopy(e); e2.equipment[0].eol_factor_id = None
ra = registry.run_all(e2)
print("equipment eol_factor_id None: SYS-03", ra["SYS-03"]["ok"], ra["SYS-03"]["violations"], "X-14 n_skipped", ra["X-14"]["n_skipped"], "complete", ra["X-02"]["complete"], ra["X-02"]["incomplete_units"])
print("clean generator: equipment rows with eol_factor_id None:", sum(1 for sc in bench for q_ in sc.equipment if q_.eol_factor_id is None), "of", sum(len(sc.equipment) for sc in bench))

print("\n== A8: zero-fraction route without factor marks the result incomplete ==")
e2 = copy.deepcopy(e); rt = e2.materials[0].end_of_life.routes
moved = rt[0].fraction; rt[1].fraction += moved; rt[0].fraction = 0.0; rt[0].factor_id = None
ra = registry.run_all(e2)
print("C3 n_routes_skipped", ra["C3-01"]["n_routes_skipped"], "complete", ra["X-02"]["complete"], ra["X-02"]["incomplete_units"], "SYS-03", ra["SYS-03"]["violations"])

print("\n== A9: SUM-08 unknown baseline id / incomplete compared ==")
e2 = copy.deepcopy(e); e2.boundary.baseline_scenario = "NO-SUCH-SCENARIO"
print("unknown id:", registry.run_all(e2)["SUM-08"])
e2 = copy.deepcopy(e); b = population.attach_baseline(e2)
for m in b.materials[:4]: m.quantity = None
ra = registry.run_all(e2)
print("baseline with 4 uncomputable rows:", ra["SUM-08"], "proposal complete", ra["X-02"]["complete"], "baseline complete", registry.run_all(b)["X-02"]["complete"])

print("\n== A10: X-17 with a zero declared summary quantity ==")
e2 = copy.deepcopy(S); e2.summary_quantities.concrete_m3 = 0.0
ra = registry.run_all(e2, ids=["X-17"])
print("CONCRETE class clean", r["X-17"]["by_class"]["CONCRETE"], "-> summary 0:", ra["X-17"]["by_class"]["CONCRETE"], "value", r["X-17"]["value"], "->", ra["X-17"]["value"])

print("\n== A11: tiny positive period: cost of the counting loop ==")
e2 = synth.make_scenario(23, "RC", "office", "S", 60.0, n_materials=1, n_equipment=1, n_refrigerants=1)
e2.materials[0].refresh_cycle = 1e-4
t0 = time.time(); ra = registry.run_all(e2, ids=["B4-03"]); print("period 1e-4, 1 row: B4-03", ra["B4-03"]["by_item"], "seconds", round(time.time() - t0, 2))

print("\n== A12: results_gas_scope is a label only ==")
e2 = copy.deepcopy(e); e2.boundary.results_gas_scope = "CO2_ONLY"
print("SUM-03 all gases", r0["SUM-03"]["value"], "CO2_ONLY", registry.run_all(e2)["SUM-03"]["value"], "X-05", r0["X-05"]["value"])
