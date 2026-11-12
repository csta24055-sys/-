"""Specification (data only) of the checks, memo items and tabulations that do not depend on
the study period T: C-05, QA-01 (b)(c), SYS-01, SYS-02, SYS-03, SYS-04 / QA-04, STO-01, STO-02,
X-09, the row parts of X-10 and of X-08.

One pattern for every check:   violation mark v[x] = sum of products of 0/1 predicates,
count n = sum_x v[x],   boolean ok = [n = 0],   list = the rows with v[x] = 1 (read-out).

Provenance: C-05, QA-01 (b)(c), SYS-04, QA-04, STO, X-10 are the specification of the three-task
run of 2026-11-12 (recovered from the session record); SYS-01, SYS-02, SYS-03, X-08, X-09 are new.

Fictional data, independent concept model; not a statement about any other tool.
"""
from .lib import (BY, C, CONV, EQ, EQC, F, FN, GE1, LE, MATCH, NN, NOT, OF, PR, RNG, STATES, VAL, VIA, sp)
from .physical import (CF, CW, D, DEM, EQT, HAUL, M, MC, OP, PM, RT, WW)

SQ, UA, UAS = "summary_quantities", "project.use_area_breakdown", "project.use_area_sorted"
CLS, CLSX, ROUTES, CYC = "CLS", "CLS.x", "ROUTES", "CYC"

CHECKS = {"id": "CHECKS", "doc": "C-05, QA-01 (b)(c), SYS-04, QA-04, STO-01, STO-02, X-09, X-10, X-08 (row parts)", "steps": [
    # ---- C-05 mass balance of the material rows
    sp(RT, "c05.tot", BY("_parent"), [["fraction"]]),
    sp(RT, "c05.nneg", BY("_parent"), [[RNG("fraction", "-inf", 0, hi_open=True)]]),
    sp(M, "c05.v1", "none", [[GE1("c05.nneg")], [EQ("c05.nneg", 0), NOT(RNG("c05.tot", "-inf", 1.0 + 1e-6))]]),
    sp(M, "c05.under", "none", [[EQ("c05.v1", 0), RNG("c05.tot", "-inf", 1.0 - 1e-6, hi_open=True)]]),
    CONV("c05.c", M, "quantity_unit", C("kg"), "materials.conversions"),
    sp(M, "c05.chk", "none", [[EQ("c05.c.ok", 1), EQ("a05.ok", 1), PR("end_of_life.mass_kg")]]),
    sp(M, "c05.rhs", "none", [[EQ("c05.chk", 1), "a05.q_inst", "c05.c.f", C(1.0 + 1e-6)]]),
    sp(M, "c05.v2", "none", [[EQ("c05.chk", 1), NOT(LE("end_of_life.mass_kg", "c05.rhs"))]]),
    sp(M, "c05.nv", "total", [["c05.v1"], ["c05.v2"]]),
    sp("S", "c05.ok", "none", [[EQ("c05.nv", 0)]]),
    sp(M, "c05.nun", "total", [[EQ("c05.chk", 0)]]),
    # ---- QA-01 (b), (c): mutually exclusive row results
    sp(M, "qa1.b", "none", [[NOT(EQ("a01.by_item", 0)), NOT(EQ("a03.by_item", 0))]]),
    sp(M, "qa1.c", "none", [[NOT(EQ("a41.by_item", 0)), NOT(EQ("a42.by_item", 0))]]),
    sp(M, "qa1.n", "total", [["qa1.b"], ["qa1.c"]]),
    # ---- SYS-04 / QA-04 floor-area residual
    sp(UAS, "sys4.sum", BY("_parent"), [["value"]]),          # added in ascending order of the use name
    sp("project", "sys4.valid", "none", [[RNG("gross_floor_area", 0, "inf", lo_open=True)]]),
    sp("project", "sys4.res", "none", [[EQ("sys4.valid", 1), "gross_floor_area"], [EQ("sys4.valid", 1), C(-1), "sys4.sum"]]),
    sp("project", "sys4.nres", "none", [[C(-1), "sys4.res"]]),
    sp("project", "sys4.tol9", "none", [[EQ("sys4.valid", 1), C(1e-9), "gross_floor_area"]]),
    sp("project", "sys4.tol6", "none", [[EQ("sys4.valid", 1), C(1e-6), "gross_floor_area"]]),
    sp("project", "sys4.ok", "none", [[EQ("sys4.valid", 1), LE("sys4.res", "sys4.tol9"), LE("sys4.nres", "sys4.tol9")]]),
    sp("project", "qa4.ok", "none", [[EQ("sys4.valid", 1), LE("sys4.res", "sys4.tol6"), LE("sys4.nres", "sys4.tol6")]]),
    # ---- memo items
    sp(SQ, "sto1.ok", "none", [[NN("timber_m3"), NN("timber_dry_density_kg_per_m3"), NN("timber_carbon_fraction")]]),
    sp(SQ, "sto1.v", "none", [[EQ("sto1.ok", 1), "timber_m3", "timber_dry_density_kg_per_m3", "timber_carbon_fraction", C(44.0 / 12.0)]]),
    F("sto2.f", SQ, "concrete_uptake_factor_id", "stage.MEMO.is", C("m3")),
    sp(SQ, "sto2.ok", "none", [[EQ("sto2.f.ok", 1), NN("concrete_m3")]]),
    sp(SQ, "sto2.v", "none", [[EQ("sto2.ok", 1), "concrete_m3", "sto2.f.c.f", VAL("sto2.f.ref")]]),
    # ---- X-10 resource and waste mass per row (the knot stage multiplies by 1 + number of renewals)
    sp(M, "x10.ok", "none", [[EQ("c05.c.ok", 1), EQ("a05.ok", 1), NN("end_of_life.mass_kg")]]),
    sp(M, "x10.r", "none", [[EQ("x10.ok", 1), "a05.q_ord", "c05.c.f"]]),
    sp(M, "x10.dq", "none", [[EQ("x10.ok", 1), "a05.q_ord"], [EQ("x10.ok", 1), C(-1), "a05.q_inst"]]),
    sp(M, "x10.w", "none", [[EQ("x10.ok", 1), "x10.dq", "c05.c.f"], [EQ("x10.ok", 1), "end_of_life.mass_kg"]]),
    sp(EQT, "x10.we", "none", [[NN("end_of_life_mass_kg"), "end_of_life_mass_kg"]]),
    sp(M, "x10.nm", "total", [[EQ("x10.ok", 0)]]),
    sp(EQT, "x10.ne", "total", [[NOT(NN("end_of_life_mass_kg"))]]),
    sp("S", "x10.n_excluded", "none", [["x10.nm"], ["x10.ne"]]),
    # ---- X-09 waste mass and emission by material class and route (two-key grouping through the pair table)
    MATCH(M, "x09.cls", ["material_class"], CLS, ["value"]),
    MATCH(RT, "x09.rt", ["route"], ROUTES, ["name"]),
    MATCH(RT, "x09.cr", [VIA("x09.cls", "_parent"), "x09.rt"], CLSX, ["_parent", "r"]),
    sp(RT, "x09.m", BY("x09.cr"), [[NN(PM), NN("fraction"), PM, "fraction"]]),
    sp(RT, "x09.e", BY("x09.cr"), [[EQ("c31.ok", 1), PM, "fraction", "c31.f.c.f", VAL("c31.f.ref")],
                                   [EQ("c41.ok", 1), PM, "fraction", "c41.f.c.f", VAL("c41.f.ref")]]),
    sp(RT, "x09.value", "total", [[EQ("c31.ok", 1), PM, "fraction", "c31.f.c.f", VAL("c31.f.ref")],
                                  [EQ("c41.ok", 1), PM, "fraction", "c41.f.c.f", VAL("c41.f.ref")]]),
    sp(M, "x09.nc", BY("x09.cls"), [[NN("end_of_life.mass_kg")]]),
    # ---- X-08 emission of one renewal summed by the value of the cycle
    MATCH(M, "x08.cm", ["refresh_cycle"], CYC, ["value"]),
    MATCH(EQT, "x08.ce", ["service_life"], CYC, ["value"]),
    sp(EQT, "x08.ue", "none", [["x01.by_item"], ["x14.by_item"], ["b4.dlv"], ["b4.ins"]]),
    sp(M, "x08.Um", BY("x08.cm"), [[PR("x08.cm"), "b4.u_mat"]]),
    sp(EQT, "x08.Ue", BY("x08.ce"), [[PR("x08.ce"), EQ("ee.listed", 0), "x08.ue"]]),
    sp(M, "x08.nm", BY("x08.cm"), [[PR("x08.cm")]]),
    sp(EQT, "x08.ne", BY("x08.ce"), [[PR("x08.ce"), EQ("ee.listed", 0)]]),
    sp(CYC, "x08.U", "none", [["x08.Um"], ["x08.Ue"]]),
    sp(CYC, "x08.rows", "none", [["x08.nm"], ["x08.ne"]]),
], "outputs": {}}

# =============================================================================================
# SYS-01 state of every numeric input
# =============================================================================================
# (id, table of the values, value column, state key, owner table of the override dictionary, list name or None)
# list name None: the row is the owner, the override key is the field name;
# list name given: the single owner record holds the dictionary, the key is "<list>[<row>].<field>".
SYS1_FIELDS = (
    [("p.area", "project", "gross_floor_area", "gross_floor_area", "project", None)]
    + [("m." + f, M, f, f, M, None) for f in ("quantity", "waste_rate", "reuse_rate", "material_life", "repair_rate", "refresh_cycle",
                                              "transport.mass_t", "transport.distance_km", "end_of_life.mass_kg")]
    + [("e." + f, EQT, f, f, EQT, None) for f in ("quantity", "service_life", "repair_rate", "end_of_life_mass_kg")]
    + [("r." + f, D, f, f, D, None) for f in ("charge_mass_kg", "gwp", "annual_leak_rate", "replacement_loss_rate", "end_of_life_recovery_rate")]
    + [("r.nolife", D, "__no_value__", "service_life", D, None)]
    + [("c.elec", "construction", "electricity_kwh", "electricity_kwh", "construction", None),
       ("c.fuel", CF, "quantity", "quantity", "construction", "fuels"),
       ("c.waste", CW, "mass_kg", "mass_kg", "construction", "waste_streams"),
       ("d.dem", DEM, "quantity", "quantity", "end_of_life", "demolition_activities"),
       ("d.haul_m", HAUL, "mass_t", "mass_t", "end_of_life", "waste_hauls"),
       ("d.haul_d", HAUL, "distance_km", "distance_km", "end_of_life", "waste_hauls")]
)
SYS1_APP = {"e.service_life": "s1.app_sl", "r.nolife": "s1.app_nl"}

def _sys01():
    steps = [sp(EQT, "s1.app_sl", "none", [[PR("service_life")], [NOT(PR("service_life")), NOT(PR("replacement_event_list#"))]]),
             sp(D, "s1.app_nl", "none", [[NOT(PR("service_life")), NOT(PR("change_years#"))]])]
    prov = {}
    for fid, table, col, key, owner, lst in SYS1_FIELDS:
        if table not in prov:
            tag = "s1.one." + table
            steps.append(sp(table, tag, "none", [[C(1)]]))
            pkey = "provenance_id" if lst is None else OF("provenance_id", owner)
            steps.append(MATCH(table, "s1.prov." + table, [pkey], "provenance", ["key"]))
            prov[table] = tag
        if lst is None:
            steps.append(MATCH(table, "s1.o." + fid, ["_row", C(key)], owner + ".states", ["_parent", "key"]))
        else:
            steps.append(MATCH(table, "s1.o." + fid, [C(lst), "_row", C(key)], owner + ".states", ["key~p", "key~i", "key~s"]))
        steps.append({"use": "STATE", "as": "s1." + fid, "with": {"T": table, "v": col, "ovr": "s1.o." + fid, "prov": "s1.prov." + table,
                                                                 "app": SYS1_APP.get(fid, prov[table])}})
    for s in STATES:
        steps.append(sp("S", "sys1." + s, "none", [["s1.%s.n.%s" % (f[0], s)] for f in SYS1_FIELDS]))
    steps.append(sp("S", "sys1.ok", "none", [[EQ("sys1.MISSING", 0)]]))
    return {"id": "SYS-01", "doc": "state of every numeric input; the MISSING ones are listed", "steps": steps, "outputs": {}}

# =============================================================================================
# SYS-02 unit consistency of every place where an activity meets a factor (or a pure unit conversion)
# =============================================================================================
# factor uses: (id, table, applies, unit present, reference to the record, conversion ok, stage gate, path group)
YEAR = lambda p: EQ(p + ".unit~t", "year")
SYS2_USES = [
    ("m.gen", M, [NOT(PR("composition#"))], PR("quantity_unit"), "x15.g.ref", "x15.g.c.ok", "stage.A13.is", "m.qu"),
    ("m.part", MC, [], None, "a02.c.ref", "a02.c.c.ok", "stage.A13.is", "m.comp"),
    ("m.dlv", M, [PR("transport.delivery_factor_id")], PR("quantity_unit"), "a42.f.ref", "a42.f.c.ok", "stage.A4.is", "m.qu"),
    ("m.tr", M, [NOT(PR("transport.delivery_factor_id"))], None, "a41.f.ref", "a41.f.c.ok", "stage.A4.is", "m.tr"),
    ("m.inst", M, [PR("installation_factor_id")], PR("quantity_unit"), "b4.inst.f.ref", "b4.inst.f.c.ok", "stage.A5.is", "m.qu"),
    ("m.haul", M, [], None, "c21.f.ref", "c21.f.c.ok", "stage.C2.is", "m.eol"),
    ("m.rt3", RT, [NOT(EQ("route", "LANDFILL"))], None, "c31.f.ref", "c31.f.c.ok", "stage.C3.is", "m.eolr"),
    ("m.rt4", RT, [EQ("route", "LANDFILL")], None, "c41.f.ref", "c41.f.c.ok", "stage.C4.is", "m.eolr"),
    ("e.fac", EQT, [], PR("quantity_unit"), "x01.f.ref", "x01.f.c.ok", "stage.A13.is", "e.qu"),
    ("e.dlv", EQT, [PR("delivery_factor_id")], PR("quantity_unit"), "b4.dlv.f.ref", "b4.dlv.f.c.ok", "stage.A4.is", "e.qu"),
    ("e.ins", EQT, [PR("installation_factor_id")], PR("quantity_unit"), "b4.ins.f.ref", "b4.ins.f.c.ok", "stage.A5.is", "e.qu"),
    ("e.eol", EQT, [PR("eol_factor_id")], None, "x14.f.ref", "x14.f.c.ok", "stage.C3.is", "e.eol"),
    ("c.fuel", CF, [], PR("unit"), "a52.f.ref", "a52.f.c.ok", "stage.A5.is", "c.fuel"),
    ("c.waste", CW, [], None, "a53.f.ref", "a53.f.c.ok", "stage.A5.is", "c.waste"),
    ("o.gas", OP, [], YEAR("gas"), "b62.gas.f.ref", "b62.gas.f.c.ok", "stage.B6.is", "o.gas"),
    ("o.oil", OP, [], YEAR("oil"), "b62.oil.f.ref", "b62.oil.f.c.ok", "stage.B6.is", "o.oil"),
    ("o.dh", OP, [], YEAR("district_heat"), "b62.dh.f.ref", "b62.dh.f.c.ok", "stage.B6.is", "o.dh"),
    ("w.wat", WW, [], YEAR("water"), "b71.f.ref", "b71.f.c.ok", "stage.B7.is", "w.wat"),
    ("w.sew", WW, [], YEAR("sewage"), "b72.f.ref", "b72.f.c.ok", "stage.B7.is", "w.sew"),
    ("w.msw", WW, [], YEAR("municipal_waste"), "b73.f.ref", "b73.f.c.ok", "stage.B7.is", "w.msw"),
    ("d.dem", DEM, [], PR("unit"), "c11.f.ref", "c11.f.c.ok", "stage.C1.is", "d.dem"),
    ("d.haul", HAUL, [], None, "c21.h.ref", "c21.h.c.ok", "stage.C2.is", "d.haul"),
    ("q.cu", SQ, [PR("concrete_uptake_factor_id")], None, "sto2.f.ref", "sto2.f.c.ok", "stage.MEMO.is", "q.cu"),
    ("x.cost", "cost_items", [], PR("currency"), "x16.f.ref", "x16.f.c.ok", "stage.A13.is", "x.cost"),
]
# pure unit conversions: (id, table, applies, the predicates that must all hold, path group)
SYS2_UNITS = [
    ("m.kg", M, [PR("composition#")], [EQ("x15.k.ok", 1)], "m.qu"),
    ("c.elec", OP, [], [EQ("a51.gu_ok", 1), EQ("a51.c.ok", 1)], "c.elec"),
    ("o.elec", OP, [], [YEAR("electricity"), EQ("x06.gu_ok", 1), EQ("b61.c.ok", 1)], "o.elec"),
    ("o.gen", OP, [], [YEAR("onsite_generation"), YEAR("electricity"), EQ("b64.cg.ok", 1)], "o.gen"),
    ("o.exp", OP, [], [YEAR("onsite_export"), YEAR("electricity"), EQ("b64.cx.ok", 1)], "o.exp"),
]
# path groups that live on a child table are summed into the parent row
SYS2_CHILD = {"m.comp": MC, "m.eolr": RT}

def _not_all(preds):
    """Terms of  1 - prod(preds)  as an exclusive sum: the first predicate that fails."""
    return [preds[:i] + [NOT(preds[i])] for i in range(len(preds))]

def _sys02():
    steps, groups, n_terms, sm_terms = [], {}, [], []
    for uid, table, app, unit, ref, cok, gate, grp in SYS2_USES:
        have = [unit] if unit else []
        bad = ([app + [NOT(unit)]] if unit else []) + [app + have + [PR(ref), EQ(cok, 0)]]
        steps.append(sp(table, "s2.b." + uid, "none", bad))
        steps.append(sp(table, "s2.n." + uid, "total", [app or [C(1)]]))
        steps.append(sp(table, "s2.sm." + uid, BY(ref), [app + have + [PR(ref), NOT(EQ(VIA(gate, ref), 1))]]))
        groups.setdefault((grp, table), []).append("s2.b." + uid)
        n_terms.append("s2.n." + uid)
        sm_terms.append("s2.sm." + uid)
    for uid, table, app, preds, grp in SYS2_UNITS:
        steps.append(sp(table, "s2.b." + uid, "none", [app + t for t in _not_all(preds)]))
        steps.append(sp(table, "s2.n." + uid, "total", [app or [C(1)]]))
        groups.setdefault((grp, table), []).append("s2.b." + uid)
        n_terms.append("s2.n." + uid)
    tot = []
    for (grp, table), cols in groups.items():
        if grp in SYS2_CHILD:
            steps.append(sp(table, "s2.p." + grp, BY("_parent"), [[c] for c in cols]))
        else:
            steps.append(sp(table, "s2.p." + grp, "none", [[c] for c in cols]))
        steps.append(sp(table, "s2.t." + grp, "total", [[c] for c in cols]))
        tot.append("s2.t." + grp)
    steps += [sp("S", "sys2.n", "none", [[c] for c in n_terms]),
              sp("S", "sys2.nbad", "none", [[c] for c in tot]),
              sp("factors", "s2.sm", "none", [[c] for c in sm_terms]),
              sp("factors", "sys2.nsm", "total", [[GE1("s2.sm")]]),
              sp("S", "sys2.ok", "none", [[EQ("sys2.nbad", 0), EQ("sys2.nsm", 0)]])]
    return {"id": "SYS-02", "doc": "unit consistency and stage agreement of every factor use", "steps": steps, "outputs": {}}

# =============================================================================================
# SYS-03 permission gate of every factor reference
# =============================================================================================
# (id, table, applies, column with the factor id, reference to the record)
SYS3_REFS = [
    ("m.fac", M, [NOT(PR("composition#"))], "factor_id", "x15.g.ref"),
    ("m.part", MC, [], "factor_id", "a02.c.ref"),
    ("m.epd", M, [PR("epd#")], "epd.factor_id", "x15.e.ref"),
    ("m.inst", M, [PR("installation_factor_id")], "installation_factor_id", "b4.inst.f.ref"),
    ("m.dlv", M, [PR("transport.delivery_factor_id")], "transport.delivery_factor_id", "a42.f.ref"),
    ("m.tr", M, [NOT(PR("transport.delivery_factor_id"))], "transport.factor_id", "a41.f.ref"),
    ("m.haul", M, [], "end_of_life.haul_factor_id", "c21.f.ref"),
    ("m.rt", RT, [], "factor_id", "c31.f.ref"),
    ("e.fac", EQT, [], "factor_id", "x01.f.ref"),
    ("e.eol", EQT, [PR("eol_factor_id")], "eol_factor_id", "x14.f.ref"),
    ("e.dlv", EQT, [PR("delivery_factor_id")], "delivery_factor_id", "b4.dlv.f.ref"),
    ("e.ins", EQT, [PR("installation_factor_id")], "installation_factor_id", "b4.ins.f.ref"),
    ("c.fuel", CF, [], "factor_id", "a52.f.ref"),
    ("c.waste", CW, [], "factor_id", "a53.f.ref"),
    ("o.gas", OP, [], "gas_factor_id", "b62.gas.f.ref"),
    ("o.oil", OP, [], "oil_factor_id", "b62.oil.f.ref"),
    ("o.dh", OP, [], "district_heat_factor_id", "b62.dh.f.ref"),
    ("w.wat", WW, [], "water_factor_id", "b71.f.ref"),
    ("w.sew", WW, [], "sewage_factor_id", "b72.f.ref"),
    ("w.msw", WW, [], "waste_factor_id", "b73.f.ref"),
    ("d.dem", DEM, [], "factor_id", "c11.f.ref"),
    ("d.haul", HAUL, [], "factor_id", "c21.h.ref"),
    ("q.cu", SQ, [PR("concrete_uptake_factor_id")], "concrete_uptake_factor_id", "sto2.f.ref"),
    ("x.cost", "cost_items", [], "factor_id", "x16.f.ref"),
]

def _sys03():
    steps, n, nofac, norec, cnt = [], [], [], [], []
    for uid, table, app, col, ref in SYS3_REFS:
        steps += [sp(table, "s3.n." + uid, "total", [app or [C(1)]]),
                  sp(table, "s3.nf." + uid, "none", [app + [NOT(PR(col))]]),
                  sp(table, "s3.nr." + uid, "none", [app + [PR(col), NOT(PR(ref))]]),
                  sp(table, "s3.tnf." + uid, "total", [["s3.nf." + uid]]),
                  sp(table, "s3.tnr." + uid, "total", [["s3.nr." + uid]]),
                  sp(table, "s3.c." + uid, BY(ref), [app + [PR(ref)]])]
        n.append("s3.n." + uid); nofac.append("s3.tnf." + uid); norec.append("s3.tnr." + uid); cnt.append("s3.c." + uid)
    steps += [sp("factors", "s3.cnt", "none", [[c] for c in cnt]),
              sp("factors", "s3.lic", "none", [[GE1("s3.cnt"), EQ("f.okq", 0)]]),
              sp("factors", "s3.nlic", "total", [[EQ("f.okq", 0), "s3.cnt"]]),
              sp(OP, "s3.grid", "none", [[NOT(EQ("grid.licence_status", "PERMITTED_PUBLIC"))]]),
              sp("S", "sys3.n", "none", [[c] for c in n] + [[C(1)]]),
              sp("S", "sys3.aff", "none", [[c] for c in nofac + norec] + [["s3.nlic"], [OF("s3.grid", OP)]]),
              sp("S", "sys3.ok", "none", [[EQ("sys3.aff", 0)]])]
    return {"id": "SYS-03", "doc": "every factor reference has a record that is licensed and has a source", "steps": steps, "outputs": {}}

SYS_01, SYS_02, SYS_03 = _sys01(), _sys02(), _sys03()
