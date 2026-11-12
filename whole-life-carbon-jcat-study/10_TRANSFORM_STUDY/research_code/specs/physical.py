"""Specification (data only) of the quantity units that ``specs/pre_a.py`` does not hold:
end of life (C1-01, C2-01, C3-01, C4-01, X-14), the amplitudes of the use stage (B3, B4, B5),
operation (X-06, B6-01..04, B2-01, B7-01..04, X-11), refrigerants (B1-01..04), the masks of the
event tables, and the activity lines by factor (for X-04, X-05, QA-01(a), QA-03).

Everything here is independent of the study period T. Vocabulary: ``tstudy.msp``.
Provenance: the end-of-life units and the amplitudes are the specification of the
representative-value check of 2026-11-12 (recovered from the session record), operation and
refrigerants are the specification of the three-task run of 2026-11-12 (recovered); the event
masks, the tokenised A5-01 and the activity lines are new (2026-11-13).

Fictional data, independent concept model; not a statement about any other tool.
"""
from .lib import (BY, C, CAL, CONV, EQ, EQC, F, FN, GE1, LE, MATCH, NN, NOT, OF, PR, RATIO, RNG, VAL, VIA, sp)

M, MC, EQT = "materials", "materials.composition", "equipment"
RT = "materials.end_of_life.routes"
DEM, HAUL = "end_of_life.demolition_activities", "end_of_life.waste_hauls"
CF, CW = "construction.fuels", "construction.waste_streams"
OP, WW, GS = "operation", "water_waste", "operation.grid.steps"
XS = CAL + ".xsteps"
D, DY = "refrigerants", "refrigerants.years"
ME, EE, RE, BE = "materials.events", "equipment.events", "refrigerants.events", "boundary.events"
PM = VIA("end_of_life.mass_kg", "_parent")

# =============================================================================================
# A5-01 with the unit of the grid factor read from its text (replaces the closed list of specs/pre_a.py)
# =============================================================================================
A5_01 = {"id": "A5-01", "doc": "site electricity: kWh * multiplier * grid factor of the construction period", "steps": [
    sp(OP, "a51.gu_ok", "none", [[EQ("grid.unit~h", "kgCO2e"), PR("grid.unit~t"), NOT(EQ("grid.unit~t", ""))]]),
    CONV("a51.c", OP, C("kWh"), "grid.unit~t"),
    sp(OP, "a51.ok", "none", [[NN(OF("electricity_kwh", "construction")), EQ("a51.gu_ok", 1), EQ("a51.c.ok", 1),
                               EQ("grid.licence_status", "PERMITTED_PUBLIC")]]),
    sp(OP, "a51.value", "total", [[EQ("a51.ok", 1), OF("electricity_kwh", "construction"), "a51.c.f", "grid.construction_value"]]),
], "outputs": {"value": {"read": "scalar", "col": "a51.value"},
               "computed": {"read": "scalar", "table": OP, "col": "a51.ok", "as": "bool"}}}

# =============================================================================================
# end of life
# =============================================================================================
def _routes(uid, tag, stage, landfill):
    is_lf = EQ("route", "LANDFILL") if landfill else NOT(EQ("route", "LANDFILL"))
    return {"id": uid, "doc": "end-of-life routes: mass * fraction * multiplier * factor", "steps": [
        F(tag + ".f", RT, "factor_id", "stage.%s.is" % stage, C("kg")),
        sp(RT, tag + ".ok", "none", [[is_lf, EQ(tag + ".f.ok"), NN("fraction"), NN(PM)]]),
        sp(RT, tag + ".by_item", BY("_parent"), [[EQ(tag + ".ok"), PM, "fraction", tag + ".f.c.f", VAL(tag + ".f.ref")]]),
        sp(M, tag + ".value", "total", [[tag + ".by_item"]]),
        sp(RT, tag + ".rsk", "none", [[is_lf, NN(PM), EQ(tag + ".f.ok", 0)], [is_lf, NN(PM), EQ(tag + ".f.ok", 1), NOT(NN("fraction"))]]),
        sp(RT, tag + ".npart", BY("_parent"), [[tag + ".rsk"]]),
        sp(RT, tag + ".nrsk", "total", [[tag + ".rsk"]]),
        sp(M, tag + ".nsk", "total", [[NOT(NN("end_of_life.mass_kg"))]]),
    ], "outputs": {}}

END_OF_LIFE = [
    {"id": "C1-01", "doc": "demolition: quantity * multiplier * factor", "steps": [
        F("c11.f", DEM, "factor_id", "stage.C1.is", "unit"),
        sp(DEM, "c11.ok", "none", [[NN("quantity"), EQ("c11.f.ok")]]),
        sp(DEM, "c11.value", "total", [[EQ("c11.ok"), "quantity", "c11.f.c.f", VAL("c11.f.ref")]]),
        sp(DEM, "c11.n_skipped", "total", [[EQ("c11.ok", 0)]]),
    ], "outputs": {}},
    {"id": "C2-01", "doc": "waste haulage: rows (kg/1000 * km) and separate hauls (t * km)", "steps": [
        F("c21.f", M, "end_of_life.haul_factor_id", "stage.C2.is", C("tkm")),
        sp(M, "c21.ok", "none", [[EQ("c21.f.ok"), NN("end_of_life.mass_kg"), NN("end_of_life.haul_distance_km")]]),
        sp(M, "c21.by_item", "none", [[EQ("c21.ok"), "end_of_life.mass_kg", C(0.001), "end_of_life.haul_distance_km",
                                       "c21.f.c.f", VAL("c21.f.ref")]]),
        sp(M, "c21.mat", "total", [["c21.by_item"]]),
        sp(M, "c21.nm", "total", [[EQ("c21.ok", 0)]]),
        F("c21.h", HAUL, "factor_id", "stage.C2.is", C("tkm")),
        sp(HAUL, "c21.hok", "none", [[EQ("c21.h.ok"), NN("mass_t"), NN("distance_km")]]),
        sp(HAUL, "c21.haul", "total", [[EQ("c21.hok"), "mass_t", "distance_km", "c21.h.c.f", VAL("c21.h.ref")]]),
        sp(HAUL, "c21.nh", "total", [[EQ("c21.hok", 0)]]),
        sp("S", "c21.value", "none", [["c21.mat"], ["c21.haul"]]),
        sp("S", "c21.n_skipped", "none", [["c21.nm"], ["c21.nh"]]),
    ], "outputs": {}},
    _routes("C3-01", "c31", "C3", False),
    _routes("C4-01", "c41", "C4", True),
    {"id": "X-14", "doc": "equipment end of life: mass * multiplier * factor (stage C3)", "steps": [
        F("x14.f", EQT, "eol_factor_id", "stage.C3.is", C("kg")),
        sp(EQT, "x14.ok", "none", [[EQ("x14.f.ok"), NN("end_of_life_mass_kg")]]),
        sp(EQT, "x14.by_item", "none", [[EQ("x14.ok"), "end_of_life_mass_kg", "x14.f.c.f", VAL("x14.f.ref")]]),
        sp(EQT, "x14.value", "total", [["x14.by_item"]]),
        sp(EQT, "x14.n_skipped", "total", [[EQ("x14.ok", 0)]]),
    ], "outputs": {}},
]

# =============================================================================================
# amplitudes of the use stage that do not depend on T: one renewal (B4), one repair year (B3), one rebuild (B5)
# =============================================================================================
def amplitudes(a01_skip, a03_skip, a41_skip, a42_skip):
    """The four arguments are the term lists of the n_skipped steps of A13-01, A13-03, A4-01, A4-02 of
    specs/pre_a.py (the same masks, per row instead of as a total)."""
    return {"id": "AMPLITUDES", "doc": "B3-01, B3-02, B4-02, B5-01, X-10: amplitudes per row and their completeness flags", "steps": [
        F("b4.inst.f", M, "installation_factor_id", "stage.A5.is", "quantity_unit", "materials.conversions"),
        sp(M, "b4.inst.ok", "none", [[PR("installation_factor_id"), EQ("b4.inst.f.ok"), EQ("a05.ok")]]),
        sp(M, "b4.inst", "none", [[EQ("b4.inst.ok"), "a05.q_ord", "b4.inst.f.c.f", VAL("b4.inst.f.ref")]]),
        sp(M, "b4.u_mat", "none", [["a01.by_item"], ["a03.by_item"], ["a41.by_item"], ["a42.by_item"],
                                   ["c21.by_item"], ["c31.by_item"], ["c41.by_item"], ["b4.inst"]]),
        F("b4.dlv.f", EQT, "delivery_factor_id", "stage.A4.is", "quantity_unit"),
        sp(EQT, "b4.dlv.ok", "none", [[PR("delivery_factor_id"), EQ("b4.dlv.f.ok"), NN("quantity")]]),
        sp(EQT, "b4.dlv", "none", [[EQ("b4.dlv.ok"), "quantity", "b4.dlv.f.c.f", VAL("b4.dlv.f.ref")]]),
        F("b4.ins.f", EQT, "installation_factor_id", "stage.A5.is", "quantity_unit"),
        sp(EQT, "b4.ins.ok", "none", [[PR("installation_factor_id"), EQ("b4.ins.f.ok"), NN("quantity")]]),
        sp(EQT, "b4.ins", "none", [[EQ("b4.ins.ok"), "quantity", "b4.ins.f.c.f", VAL("b4.ins.f.ref")]]),
        sp(EQT, "b4.u_eq", "none", [["x01.by_item"], ["b4.dlv"], ["b4.ins"], ["x14.by_item"]]),
        # a renewal whose components are incomplete (n_partial of B4-02)
        sp(M, "np.a01", "none", a01_skip), sp(M, "np.a03", "none", a03_skip),
        sp(M, "np.a41", "none", a41_skip), sp(M, "np.a42", "none", a42_skip),
        sp(M, "np.cnt", "none", [["np.a01"], ["np.a03"], ["np.a41"], ["np.a42"], [EQ("c21.ok", 0)], [NOT(NN("end_of_life.mass_kg"))],
                                 ["c31.npart"], ["c41.npart"], [PR("installation_factor_id"), EQ("b4.inst.ok", 0)]]),
        sp(M, "np.m", "none", [[GE1("np.cnt")]]),
        sp(EQT, "np.cnt_e", "none", [[EQ("x01.ok", 0)], [EQ("x14.ok", 0)], [PR("delivery_factor_id"), EQ("b4.dlv.ok", 0)],
                                     [PR("installation_factor_id"), EQ("b4.ins.ok", 0)]]),
        sp(EQT, "np.e", "none", [[GE1("np.cnt_e")]]),
        # repairs: emission of one full repair year of a row
        sp(M, "b3.a_mat", "none", [[NN("repair_rate"), "a01.by_item", "repair_rate"], [NN("repair_rate"), "a03.by_item", "repair_rate"]]),
        sp(EQT, "b3.a_eq", "none", [[NN("repair_rate"), "x01.by_item", "repair_rate"]]),
        sp(M, "b3.A_m", "total", [["b3.a_mat"]]), sp(EQT, "b3.A_e", "total", [["b3.a_eq"]]),
        sp(M, "b3.nsm", "total", [[NOT(NN("repair_rate"))]]), sp(EQT, "b3.nse", "total", [[NOT(NN("repair_rate"))]]),
        sp("S", "b3.n_skipped", "none", [["b3.nsm"], ["b3.nse"]]),
        # lines of a repair exist for rows with a positive rate and a non-zero initial emission
        sp(M, "b3.e0", "none", [["a01.by_item"], ["a03.by_item"]]),
        sp(M, "b3.lines", "none", [[NN("repair_rate"), NOT(EQ("repair_rate", 0)), NOT(EQ("b3.e0", 0))]]),
        sp(EQT, "b3.lines_e", "none", [[NN("repair_rate"), NOT(EQ("repair_rate", 0)), NOT(EQ("x01.by_item", 0))]]),
        # rebuild: scope fraction * initial upfront and end-of-life emission
        sp("S", "b5.base", "none", [[c] for c in ("a01.value", "a03.value", "a04.value", "x01.value", "a41.value", "a42.value",
                                                  "a54.value", "c11.value", "c21.value", "c31.value", "c41.value", "x14.value")]),
        sp("S", "b5.none", "none", [[EQ(OF("reconstruction_scenario", "boundary"), "NONE")]]),
        sp("S", "b5.live", "none", [[EQ("b5.none", 0), RATIO(OF("reconstruction_scope_fraction", "boundary"))]]),
        sp("S", "b5.computed", "none", [[EQ("b5.none", 1)], [EQ("b5.live", 1)]]),
        sp("S", "b5.u", "none", [[EQ("b5.live", 1), OF("reconstruction_scope_fraction", "boundary"), "b5.base"]]),
        sp("S", "b5.scope", "none", [[EQ("b5.live", 1), OF("reconstruction_scope_fraction", "boundary")]]),
    ], "outputs": {}}

# =============================================================================================
# event tables: which lattice counts, the first event of a year cell, amplitudes carried by the events
# =============================================================================================
LIST_E = PR(VIA("replacement_event_list#", "_parent"))
EVENTS = {"id": "EVENTS", "doc": "masks and amplitudes on the knot lattices of renewals and rebuilds", "steps": [
    MATCH(ME, "me.cal", ["cell"], CAL, ["_pos"]),
    MATCH(ME, "me.f", ["_parent", "cell"], ME, ["_parent", "cell"]),
    sp(ME, "me.first", "none", [[EQC("me.f", "_row")]]),
    sp(ME, "me.b4", "none", [[VIA("b4.u_mat", "_parent")]]),
    sp(ME, "me.b3", "none", [[EQ("me.first", 1), C(-1), VIA("b3.a_mat", "_parent")]]),
    sp(ME, "me.np", "none", [[EQ("ord", 0), VIA("np.m", "_parent")]]),
    sp(EE, "ee.act", "none", [[EQ("src", "LIST"), LIST_E], [EQ("src", "CYCLE"), NOT(LIST_E)]]),
    MATCH(EE, "ee.cal", ["cell"], CAL, ["_pos"]),
    MATCH(EE, "ee.f", ["_parent", "cell", C(1)], EE, ["_parent", "cell", "ee.act"]),
    sp(EE, "ee.first", "none", [[EQ("ee.act", 1), EQC("ee.f", "_row")]]),
    MATCH(EQT, "ee.e1", ["_row", C(1)], EE, ["_parent", "ee.act"]),
    sp(EE, "ee.is1", "none", [[EQ("ee.act", 1), EQC(VIA("ee.e1", "_parent"), "_row")]]),
    sp(EE, "ee.b4", "none", [[EQ("ee.act", 1), VIA("b4.u_eq", "_parent")]]),
    sp(EE, "ee.b3", "none", [[EQ("ee.first", 1), C(-1), VIA("b3.a_eq", "_parent")]]),
    sp(EE, "ee.np", "none", [[EQ("ee.is1", 1), VIA("np.e", "_parent")]]),
    sp(EE, "ee.one", "none", [[EQ("ee.act", 1)]]),
    sp(EQT, "ee.listed", "none", [[PR("replacement_event_list#")]]),
    MATCH(BE, "be.cal", ["cell"], CAL, ["_pos"]),
    sp(BE, "be.b5", "none", [[OF("b5.u", "S")]]),
    sp(BE, "be.one", "none", [[EQ(OF("b5.live", "S"), 1)]]),
], "outputs": {}}

# =============================================================================================
# operation: yearly coefficients on the calendar
# =============================================================================================
def _prof(as_, O, p):
    return {"use": "PROFILE", "as": as_, "with": {"O": O, "kind": p + ".kind", "base": p + ".base", "slope": p + ".slope",
                                                  "tab": O + "." + p + ".table"}}
def _annual(as_, O, fid, gate, p, v):
    return {"use": "ANNUALF", "as": as_, "with": {"O": O, "fid": fid, "gate": gate, "uh": p + ".unit~h", "ut": p + ".unit~t", "v": v}}

B64 = OF("b64.computed", OP)
OPERATION = {"id": "OPERATION", "doc": "X-06, B6-04, B6-01, B6-02, B6-03, B2-01, B7-01..04, X-11: yearly coefficients", "steps": [
    # ---- X-06 grid factor series
    sp(OP, "x06.wfC", "none", [[EQ("grid.kind", "CONSTANT"), PR("grid.start")]]),
    sp(OP, "x06.wfL", "none", [[EQ("grid.kind", "LINEAR_DECLINE_TO_FLOOR"), PR("grid.start"), PR("grid.floor"), PR("grid.annual_decline"),
                                RNG("grid.annual_decline", 0, "inf"), LE("grid.floor", "grid.start")]]),
    sp(GS, "x06.pm1", "none", [["_pos"], [C(-1)]]),
    MATCH(GS, "x06.prev", ["_parent", "x06.pm1"], GS, ["_parent", "_pos"]),
    sp(GS, "x06.pp1", "none", [["_pos"], [C(1)]]),
    MATCH(GS, "x06.next", ["_parent", "x06.pp1"], GS, ["_parent", "_pos"]),
    sp(GS, "x06.next_from", "none", [[VIA("from_index", "x06.next")]]),
    sp(GS, "x06.first0", BY("_parent"), [[EQ("_pos", 0), EQ("from_index", 0)]]),
    sp(GS, "x06.nbad", BY("_parent"), [[PR("x06.prev"), LE("from_index", VIA("from_index", "x06.prev"))]]),
    sp(OP, "x06.wfS", "none", [[EQ("grid.kind", "STEPWISE"), GE1("grid.steps#"), EQ("x06.first0", 1), EQ("x06.nbad", 0)]]),
    sp(OP, "x06.wf", "none", [[EQ("x06.wfC", 1)], [EQ("x06.wfL", 1)], [EQ("x06.wfS", 1)]]),
    MATCH(XS, "x06.sref", ["s"], GS, ["_row"]),
    sp(XS, "x06.sv", BY("_parent"), [
        [LE(VIA("from_index", "x06.sref"), VIA("_pos", "_parent")), NOT(PR(VIA("x06.next_from", "x06.sref"))), VIA("value", "x06.sref")],
        [LE(VIA("from_index", "x06.sref"), VIA("_pos", "_parent")), PR(VIA("x06.next_from", "x06.sref")),
         NOT(LE(VIA("x06.next_from", "x06.sref"), VIA("_pos", "_parent"))), VIA("value", "x06.sref")]]),
    sp(CAL, "x06.dl", "none", [[EQ(OF("x06.wfL", OP), 1), OF("grid.start", OP)],
                               [EQ(OF("x06.wfL", OP), 1), C(-1), OF("grid.annual_decline", OP), "_pos"]]),
    sp(CAL, "x06.g", "none", [
        [EQ(OF("x06.wfC", OP), 1), OF("grid.start", OP)],
        [EQ(OF("x06.wfL", OP), 1), LE(OF("grid.floor", OP), "x06.dl"), "x06.dl"],
        [EQ(OF("x06.wfL", OP), 1), NOT(LE(OF("grid.floor", OP), "x06.dl")), OF("grid.floor", OP)],
        [EQ(OF("x06.wfS", OP), 1), "x06.sv"],
        [EQ(OF("x06.wf", OP), 0), "value"]]),
    {"use": "CLOSE", "as": "x06.m", "with": {"v": "x06.g", "t": "value"}},
    # ---- B6-04 purchased electricity
    _prof("p.el", OP, "electricity"), _prof("p.gen", OP, "onsite_generation"), _prof("p.exp", OP, "onsite_export"),
    CONV("b64.cg", OP, "onsite_generation.unit~h", "electricity.unit~h"),
    CONV("b64.cx", OP, "onsite_export.unit~h", "electricity.unit~h"),
    sp(OP, "b64.computed", "none", [[EQ("electricity.unit~t", "year"), EQ("onsite_generation.unit~t", "year"),
                                     EQ("onsite_export.unit~t", "year"), EQ("b64.cg.ok", 1), EQ("b64.cx.ok", 1)]]),
    sp(CAL, "b64.inner", "none", [[EQ(B64, 1), "p.gen.v", OF("b64.cg.f", OP)], [EQ(B64, 1), C(-1), "p.exp.v", OF("b64.cx.f", OP)]]),
    sp(CAL, "b64.d", "none", [[EQ(B64, 1), "p.el.v"], [EQ(B64, 1), C(-1), "b64.inner"]]),
    sp(CAL, "b64.net", "none", [[EQ(B64, 1), RNG("b64.d", 0, "inf"), "b64.d"]]),
    sp(CAL, "b64.mis", "none", [["p.el.m.mis"], ["p.gen.m.mis"], ["p.exp.m.mis"]]),
    # ---- B6-01 purchased electricity emission
    sp(OP, "x06.gu_ok", "none", [[EQ("grid.unit~h", "kgCO2e"), PR("grid.unit~t"), NOT(EQ("grid.unit~t", ""))]]),
    CONV("b61.c", OP, "electricity.unit~h", "grid.unit~t"),
    sp(OP, "b61.ok", "none", [[EQ("grid.licence_status", "PERMITTED_PUBLIC"), EQ("b64.computed", 1), EQ("x06.gu_ok", 1), EQ("b61.c.ok", 1)]]),
    sp(CAL, "b61.e", "none", [[EQ(OF("b61.ok", OP), 1), "b64.net", OF("b61.c.f", OP), "x06.g"]]),
    # ---- B6-02 fuels
    _prof("p.gas", OP, "gas"), _prof("p.oil", OP, "oil"), _prof("p.dh", OP, "district_heat"),
    _annual("b62.gas", OP, "gas_factor_id", "stage.B6.is", "gas", "p.gas.v"),
    _annual("b62.oil", OP, "oil_factor_id", "stage.B6.is", "oil", "p.oil.v"),
    _annual("b62.dh", OP, "district_heat_factor_id", "stage.B6.is", "district_heat", "p.dh.v"),
    sp(CAL, "b62.e", "none", [["b62.gas.e"], ["b62.oil.e"], ["b62.dh.e"]]),
    sp(OP, "b62.nsk", "none", [[EQ("b62.gas.ok", 0)], [EQ("b62.oil.ok", 0)], [EQ("b62.dh.ok", 0)]]),
    sp(CAL, "b62.mis", "none", [["p.gas.m.mis"], ["p.oil.m.mis"], ["p.dh.m.mis"]]),
    # ---- B6-03, B2-01 amplitudes per year cell
    sp(CAL, "b63.a", "none", [["b61.e"], ["b62.e"]]),
    sp(OP, "b21.ok", "none", [[RATIO("facility_management_ratio")]]),
    sp(OP, "b21.share", "none", [[EQ("b21.ok", 1), "facility_management_ratio"]]),
    sp(CAL, "b21.a", "none", [[EQ(OF("b21.ok", OP), 1), "b61.e", OF("facility_management_ratio", OP)]]),
    # ---- B7
    _prof("p.wat", WW, "water"), _prof("p.sew", WW, "sewage"), _prof("p.msw", WW, "municipal_waste"),
    _annual("b71", WW, "water_factor_id", "stage.B7.is", "water", "p.wat.v"),
    _annual("b72", WW, "sewage_factor_id", "stage.B7.is", "sewage", "p.sew.v"),
    _annual("b73", WW, "waste_factor_id", "stage.B7.is", "municipal_waste", "p.msw.v"),
    sp(CAL, "b74.a", "none", [["b71.e"], ["b72.e"], ["b73.e"]]),
    sp(WW, "b71.nsk", "none", [[EQ("b71.ok", 0)]]), sp(WW, "b72.nsk", "none", [[EQ("b72.ok", 0)]]), sp(WW, "b73.nsk", "none", [[EQ("b73.ok", 0)]]),
    # ---- X-11 estimate from the floor area
    CONV("x11.c", OP, C("kWh"), "grid.unit~t"),
    sp(OP, "x11.ok", "none", [[RNG(OF("gross_floor_area", "project"), 0, "inf", lo_open=True, hi_open=True), NN("electricity_per_m2_per_year"),
                               EQ("x06.gu_ok", 1), EQ("x11.c.ok", 1), EQ("grid.licence_status", "PERMITTED_PUBLIC")]]),
    sp(CAL, "x11.a", "none", [[EQ(OF("x11.ok", OP), 1), OF("gross_floor_area", "project"), OF("electricity_per_m2_per_year", OP),
                               OF("x11.c.f", OP), "x06.g"]]),
], "outputs": {}}

# =============================================================================================
# refrigerants: start-of-year mass by the resolvent of the masked shift; amplitudes
# =============================================================================================
OKP, TOP0, ROKP = EQ(VIA("b1.ok", "_parent"), 1), EQ(VIA("top_up", "_parent"), 0), EQ(VIA("b1.rok", "_parent"), 1)
LOKP = EQ(VIA("b1.lok", "_parent"), 1)
M0, RL, K4, L3 = VIA("charge_mass_kg", "_parent"), VIA("annual_leak_rate", "_parent"), VIA("b1.k4", "_parent"), VIA("b1.l3", "_parent")
GWP = VIA("gwp", "_parent")
NDBL = 8                                   # (I - N)^-1 = prod_{j<8} (I + N^(2^j)) is exact for fewer than 256 years
UF = "b1.u%d" % NDBL

def _doubling(n):
    return [{"use": "DOUBLE", "as": "b1.dbl%d" % b, "with": {"T": DY, "neg": -(2 ** b), "uin": "b1.u%d" % b, "cin": "b1.c%d" % b,
                                                           "uout": "b1.u%d" % (b + 1), "cout": "b1.c%d" % (b + 1)}} for b in range(n)]

LIST_R = PR(VIA("change_years#", "_parent"))
REFRIGERANT = {"id": "REFRIGERANT", "doc": "B1-01..04: state by the resolvent of the masked shift; amplitudes", "steps": [
    sp(D, "b1.ok", "none", [[NN("charge_mass_kg"), NN("gwp"), RATIO("annual_leak_rate")]]),
    sp(D, "b1.q", "none", [[EQ("b1.ok", 1), EQ("top_up", 1)], [EQ("b1.ok", 1), EQ("top_up", 0), FN("one_minus", "annual_leak_rate")]]),
    sp(D, "b1.lok", "none", [[EQ("b1.ok", 1), RATIO("replacement_loss_rate")]]),
    sp(D, "b1.rok", "none", [[EQ("b1.ok", 1), RATIO("end_of_life_recovery_rate")]]),
    sp(D, "b1.k4", "none", [[EQ("b1.rok", 1), FN("one_minus", "end_of_life_recovery_rate"), "gwp"]]),
    sp(D, "b1.k4m0", "none", [[EQ("b1.rok", 1), "b1.k4", "charge_mass_kg"]]),
    sp(D, "b1.l3", "none", [[EQ("b1.lok", 1), "replacement_loss_rate", "gwp"]]),
    sp(D, "b11.ok", "none", [[NN("charge_mass_kg"), NN("gwp")]]),
    sp(D, "b11.v", "total", [[EQ("b11.ok", 1), "charge_mass_kg", "gwp"]]),
    sp(D, "b11.nsk", "total", [[EQ("b11.ok", 0)]]),
    sp(D, "b12.nsk", "total", [[EQ("b1.ok", 0)]]), sp(D, "b13.nsk", "total", [[EQ("b1.lok", 0)]]), sp(D, "b14.nsk", "total", [[EQ("b1.rok", 0)]]),
    # events: which lattice counts (explicit list when given, else multiples of the service life)
    sp(RE, "b1.act", "none", [[EQ("src", "LIST"), LIST_R], [EQ("src", "CYCLE"), NOT(LIST_R)]]),
    MATCH(RE, "re.cal", ["cell"], CAL, ["_pos"]),
    MATCH(DY, "dy.cal", ["k"], CAL, ["_pos"]),
    MATCH(DY, "b1.ev1", ["_parent", "k", C(1)], RE, ["_parent", "cell", "b1.act"]),       # first event of the year cell
    sp(DY, "b1.p", "none", [[PR("b1.ev1")]]),                                             # reset indicator
    sp(DY, "b1.km1", "none", [["k"], [C(-1)]]),
    sp(DY, "b1.kp1", "none", [["k"], [C(1)]]),
    MATCH(DY, "b1.pv1", ["_parent", "b1.km1"], DY, ["_parent", "k"]),
    # u = b + N u :  b = m0 at k = 0 and after a reset;  (N u)[k] = (1 - p[k-1]) * q * u[k-1]
    sp(DY, "b1.c0", "none", [[OKP, PR("b1.pv1"), EQ(VIA("b1.p", "b1.pv1"), 0), VIA("b1.q", "_parent")]]),
    sp(DY, "b1.u0", "none", [[OKP, EQ("k", 0), M0], [OKP, PR("b1.pv1"), EQ(VIA("b1.p", "b1.pv1"), 1), M0]]),
    *_doubling(NDBL),
    # amplitudes of the knot spectrum
    sp(DY, "b1.a2", "none", [[OKP, UF, RL, GWP]]),
    sp(DY, "b1.y4", "none", [[ROKP, TOP0, C(-1), K4, UF, RL]]),
    sp(DY, "b1.e4a", "none", [[ROKP, TOP0, EQ("b1.p", 1), K4, M0], [ROKP, TOP0, EQ("b1.p", 1), C(-1), K4, UF]]),
    sp(DY, "b1.e4g", "none", [[ROKP, TOP0, EQ("b1.p", 1), K4, UF, RL]]),
    sp(DY, "b1.tau1", "none", [[VIA("tau", "b1.ev1")]]),
    MATCH(RE, "b1.dy", ["_parent", "cell"], DY, ["_parent", "k"]),
    sp(RE, "b1.first", "none", [[EQ("b1.act", 1), EQC(VIA("b1.ev1", "b1.dy"), "_row")]]),
    sp(RE, "b1.a3", "none", [[LOKP, EQ("b1.act", 1), EQ("b1.first", 1), L3, VIA(UF, "b1.dy")],
                             [LOKP, EQ("b1.act", 1), EQ("b1.first", 0), L3, M0]]),
    sp(RE, "b1.g3", "none", [[LOKP, EQ("b1.act", 1), EQ("b1.first", 1), TOP0, C(-1), L3, VIA(UF, "b1.dy"), RL]]),
    # interval form of the end residual (B1-04): coefficients of the year cell k, summed over the devices
    sp(DY, "b1.iA", BY("dy.cal"), [[ROKP, K4, UF]]),
    sp(DY, "b1.iB", BY("dy.cal"), [[ROKP, TOP0, C(-1), K4, UF, RL]]),
], "outputs": {}}

# =============================================================================================
# activity lines by factor. One slot = one kind of place where an activity meets a factor record.
#   stage   life-cycle stage of the line            mask   0/1 factors: the line exists
#   act     factors whose product is the activity    fref   reference to the factor record
#   via     the slot lives on a child table (multipliers of the row are read through _parent)
#   b3 / b4 the line is repeated by a repair (A13-01, A13-03, X-01 lines) / by a renewal
# =============================================================================================
A04 = FN("ratio_one_minus", "unquantified_cost_ratio")
A04P = FN("ratio_one_minus", VIA("unquantified_cost_ratio", "_parent"))
QA = ["a05.q_ord", "x15.conv"]
QAP = [VIA("a05.q_ord", "_parent"), VIA("x15.conv", "_parent"), "mass_fraction", "a02.c.c.f"]
GEN, EPD = [EQ("a01.ok", 1), EQ("x15.is_gen", 1)], [EQ("x15.is_epd", 1), EQ("a05.ok", 1)]
PART = [EQ(VIA("a01.ok", "_parent"), 1), EQ(VIA("x15.is_comp", "_parent"), 1)]
LINE_SLOTS = [
    {"id": "gen", "stage": "A1-A3", "table": M, "mask": GEN, "act": QA, "fref": "x15.g.ref", "b3": True, "b4": True},
    {"id": "epd", "stage": "A1-A3", "table": M, "mask": EPD, "act": QA, "fref": "x15.e.ref", "b3": True, "b4": True},
    {"id": "part", "stage": "A1-A3", "table": MC, "mask": PART, "act": QAP, "fref": "a02.c.ref", "via": True, "b3": True, "b4": True},
    {"id": "gen04", "stage": "A1-A3", "table": M, "mask": GEN + [EQ("a04.in", 1)], "act": QA + [A04], "fref": "x15.g.ref"},
    {"id": "epd04", "stage": "A1-A3", "table": M, "mask": EPD + [EQ("a04.in", 1)], "act": QA + [A04], "fref": "x15.e.ref"},
    {"id": "part04", "stage": "A1-A3", "table": MC, "mask": PART + [EQ(VIA("a04.in", "_parent"), 1)], "act": QAP + [A04P],
     "fref": "a02.c.ref", "via": True},
    {"id": "x01", "stage": "A1-A3", "table": EQT, "mask": [EQ("x01.ok", 1)], "act": ["quantity", "x01.f.c.f"], "fref": "x01.f.ref",
     "b3": True, "b4": True},
    {"id": "a41", "stage": "A4", "table": M, "mask": [EQ("a41.ok", 1)], "act": ["transport.mass_t", "transport.distance_km", "a41.f.c.f"],
     "fref": "a41.f.ref", "b4": True},
    {"id": "a42", "stage": "A4", "table": M, "mask": [EQ("a42.ok", 1)], "act": ["a05.q_ord", "a42.f.c.f"], "fref": "a42.f.ref", "b4": True},
    {"id": "a52", "stage": "A5", "table": CF, "mask": [EQ("a52.ok", 1)], "act": ["quantity", "a52.f.c.f"], "fref": "a52.f.ref"},
    {"id": "a53", "stage": "A5", "table": CW, "mask": [EQ("a53.ok", 1)], "act": ["mass_kg", "a53.f.c.f"], "fref": "a53.f.ref"},
    {"id": "c11", "stage": "C1", "table": DEM, "mask": [EQ("c11.ok", 1)], "act": ["quantity", "c11.f.c.f"], "fref": "c11.f.ref"},
    {"id": "c21", "stage": "C2", "table": M, "mask": [EQ("c21.ok", 1)],
     "act": ["end_of_life.mass_kg", C(0.001), "end_of_life.haul_distance_km", "c21.f.c.f"], "fref": "c21.f.ref", "b4": True},
    {"id": "c21h", "stage": "C2", "table": HAUL, "mask": [EQ("c21.hok", 1)], "act": ["mass_t", "distance_km", "c21.h.c.f"], "fref": "c21.h.ref"},
    {"id": "c31", "stage": "C3", "table": RT, "mask": [EQ("c31.ok", 1)], "act": [PM, "fraction", "c31.f.c.f"], "fref": "c31.f.ref",
     "via": True, "b4": True},
    {"id": "x14", "stage": "C3", "table": EQT, "mask": [EQ("x14.ok", 1)], "act": ["end_of_life_mass_kg", "x14.f.c.f"], "fref": "x14.f.ref",
     "b4": True},
    {"id": "c41", "stage": "C4", "table": RT, "mask": [EQ("c41.ok", 1)], "act": [PM, "fraction", "c41.f.c.f"], "fref": "c41.f.ref",
     "via": True, "b4": True},
    # lines that exist only at a renewal
    {"id": "inst", "stage": None, "table": M, "mask": [EQ("b4.inst.ok", 1)], "act": ["a05.q_ord", "b4.inst.f.c.f"], "fref": "b4.inst.f.ref",
     "b4": True},
    {"id": "dlv", "stage": None, "table": EQT, "mask": [EQ("b4.dlv.ok", 1)], "act": ["quantity", "b4.dlv.f.c.f"], "fref": "b4.dlv.f.ref",
     "b4": True},
    {"id": "ins", "stage": None, "table": EQT, "mask": [EQ("b4.ins.ok", 1)], "act": ["quantity", "b4.ins.f.c.f"], "fref": "b4.ins.f.ref",
     "b4": True},
]
STATIC_STAGES = ("A1-A3", "A4", "A5", "C1", "C2", "C3", "C4")
STAGE_TAG = {"A1-A3": "A13", "A4": "A4", "A5": "A5", "B1": "B1", "B2": "B2", "B3": "B3", "B4": "B4", "B5": "B5", "B6": "B6", "B7": "B7",
             "C1": "C1", "C2": "C2", "C3": "C3", "C4": "C4"}

def _lines():
    steps = [sp("factors.gas_amounts", "f.co2", BY("_parent"), [[EQ("key", "CO2"), "value"]]),
             sp("factors", "f.okq", "none", [[EQ("licence_status", "PERMITTED_PUBLIC"), PR("source_url"), NOT(EQ("source_url", ""))]])]
    present = []
    for s in LINE_SLOTS:
        if s["stage"] is None:
            continue
        steps.append(sp(s["table"], "ln." + s["id"], BY(s["fref"]), [s["mask"] + s["act"]]))
        steps.append(sp(s["table"], "lp." + s["id"], BY(s["fref"]), [list(s["mask"])]))
        present.append("lp." + s["id"])
    for st in STATIC_STAGES:
        steps.append(sp("factors", "L." + STAGE_TAG[st], "none", [["ln." + s["id"]] for s in LINE_SLOTS if s["stage"] == st]))
    # lines of the operation stages exist for every usable fuel and water / waste factor
    for tag, table in (("b62.gas", OP), ("b62.oil", OP), ("b62.dh", OP), ("b71", WW), ("b72", WW), ("b73", WW)):
        steps.append(sp(table, "lp." + tag, BY(tag + ".f.ref"), [[EQ(tag + ".ok", 1)]]))
        present.append("lp." + tag)
    steps.append(sp("factors", "lp.const", "none", [[p] for p in present]))
    return {"id": "LINES", "doc": "activity by factor of the stages that do not depend on T; presence of lines", "steps": steps, "outputs": {}}

LINES = _lines()
