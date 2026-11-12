"""Specification (data only) of the two sum-product programs that run at ONE study period T.

  TIME  the knot tables evaluated at T by gated sums: number of renewals per row, emission per
        year and per row, the end residual of the refrigerants in its interval form, the
        activity by factor of the repeated lines. The gate of a knot is the same predicate as
        in the knot spectrum:   event at tau counts  <=>  tau < T*(1 - 1e-9),
        weight of the year cell k:  w = clip(T - k, 0, 1).
  AGG   stage vector, totals, indicators, gas breakdown, yearly series, flags and comparisons.

The table TT (one row) carries T and the scalar values of the knot spectra at T (columns
``K.<name>``); before AGG the unit values are re-tabulated into the table U and the columns
``V.<unit>`` of TT (no arithmetic in between, see ``tstudy/unified.py``).

Fictional data, independent concept model; not a statement about any other tool.
"""
from .lib import (BY, C, CAL, EQ, EQC, FN, GE1, LE, MATCH, NN, NOT, OF, PR, RNG, VIA, sp)
from .physical import (BE, D, DY, EE, EQT, GWP, K4, L3, LINE_SLOTS, LOKP, M, M0, MC, ME, OKP, OP, RE, RL, ROKP, RT, STAGE_TAG,
                       STATIC_STAGES, TOP0, UF, WW)
from .gates import CYC

STAGES = ("A1-A3", "A4", "A5", "B1", "B2", "B3", "B4", "B5", "B6", "B7", "C1", "C2", "C3", "C4")
CE = "CYC.events"
T_, TIN = OF("T", "TT"), OF("Tin", "TT")
K = lambda name: OF("K." + name, "TT")
V = lambda uid: OF("V." + uid, "TT")
S = lambda name: OF(name, "S")
IN = lambda col: NOT(LE(TIN, col))                                    # tau < T*(1-eps)
WIN = [ROKP, NOT(LE(T_, "k")), LE(T_, "b1.kp1")]                      # the year cell that holds T: k < T <= k+1

def _mult(slot, row_m, row_e):
    """Multiplier factors of a slot: a row scalar of the materials / equipment row the line belongs to."""
    if slot["table"] == EQT:
        return list(row_e)
    if slot.get("via"):
        return [VIA(c, "_parent") if isinstance(c, str) else c for c in row_m]
    return list(row_m)

def _b3_mask(slot):
    if slot["table"] == EQT:
        return [EQ("b3.lines_e", 1)]
    return [EQ(VIA("b3.lines", "_parent"), 1)] if slot.get("via") else [EQ("b3.lines", 1)]

def _time():
    st = [
        sp("TT", "Tin", "none", [["T", C(1.0 - 1e-9)]]),
        # ---- calendar: the years that exist, the weight of each year cell, the cell that holds T
        sp(CAL, "t.in", "none", [[NOT(LE(T_, "_pos"))]]),
        sp(CAL, "t.dT", "none", [[T_], [C(-1), "_pos"]]),
        sp(CAL, "t.w", "none", [[EQ("t.in", 1), LE("cal.kp1", T_)], [EQ("t.in", 1), NOT(LE("cal.kp1", T_)), "t.dT"]]),
        sp(CAL, "t.last", "none", [[EQ("t.in", 1), LE(T_, "cal.kp1")]]),
        # ---- gates of the event knots
        sp(ME, "t.in_m", "none", [[IN("tau")]]),
        sp(EE, "t.in_e", "none", [[EQ("ee.act", 1), IN("tau")]]),
        sp(RE, "t.in_r", "none", [[EQ("b1.act", 1), IN("tau")]]),
        sp(BE, "t.in_b", "none", [[IN("tau")]]),
        sp(CE, "t.in_c", "none", [[IN("tau")]]),
        # ---- row scalars: number of renewals (B4-03), repair years = T - weight of the years that hold a renewal
        sp(ME, "t.cnt_m", BY("_parent"), [["t.in_m"]]),
        sp(EE, "t.cnt_e", BY("_parent"), [["t.in_e"]]),
        sp(ME, "t.skw_m", BY("_parent"), [[EQ("me.first", 1), "t.in_m", VIA("t.w", "me.cal")]]),
        sp(EE, "t.skw_e", BY("_parent"), [[EQ("ee.first", 1), "t.in_e", VIA("t.w", "ee.cal")]]),
        sp(M, "t.yrs_m", "none", [[T_], [C(-1), "t.skw_m"]]),
        sp(EQT, "t.yrs_e", "none", [[T_], [C(-1), "t.skw_e"]]),
        sp(M, "t.k_m", "none", [[C(1)], ["t.cnt_m"]]),
        sp(EQT, "t.k_e", "none", [[C(1)], ["t.cnt_e"]]),
        # ---- B4-02 per row and per year, B4-01 number of events, n_partial by rows (cross-check of the knot count)
        sp(ME, "t.b42_im", BY("_parent"), [["t.in_m", VIA("b4.u_mat", "_parent")]]),
        sp(EE, "t.b42_ie", BY("_parent"), [["t.in_e", VIA("b4.u_eq", "_parent")]]),
        sp(ME, "t.b42_ym", BY("me.cal"), [["t.in_m", VIA("b4.u_mat", "_parent")]]),
        sp(EE, "t.b42_ye", BY("ee.cal"), [["t.in_e", VIA("b4.u_eq", "_parent")]]),
        sp(CAL, "t.b42_y", "none", [["t.b42_ym"], ["t.b42_ye"]]),
        sp(EE, "t.b41_n", "total", [["t.in_e"]]),
        sp(M, "t.np_m", "total", [[EQ("np.m", 1), GE1("t.cnt_m")]]),
        sp(EQT, "t.np_e", "total", [[EQ("np.e", 1), GE1("t.cnt_e")]]),
        sp("S", "t.np", "none", [["t.np_m"], ["t.np_e"]]),
        # ---- B3-01 per year: weight * (all rows - rows whose renewal falls in the year), B3-02
        sp(ME, "t.sk_m", BY("me.cal"), [[EQ("me.first", 1), "t.in_m", VIA("b3.a_mat", "_parent")]]),
        sp(EE, "t.sk_e", BY("ee.cal"), [[EQ("ee.first", 1), "t.in_e", VIA("b3.a_eq", "_parent")]]),
        sp(CAL, "t.b3d_m", "none", [[S("b3.A_m")], [C(-1), "t.sk_m"]]),
        sp(CAL, "t.b3d_e", "none", [[S("b3.A_e")], [C(-1), "t.sk_e"]]),
        sp(CAL, "t.b3_y", "none", [["t.w", "t.b3d_m"], ["t.w", "t.b3d_e"]]),
        sp(M, "t.b32_m", "total", [["b3.a_mat", T_]]),
        sp(EQT, "t.b32_e", "total", [["b3.a_eq", T_]]),
        sp("S", "t.b32", "none", [["t.b32_m"], ["t.b32_e"]]),
        # ---- B5-01 per year, number of rebuilds, multiplier of the rebuild lines
        sp(BE, "t.b5_y", BY("be.cal"), [["t.in_b", S("b5.u")]]),
        sp(BE, "t.b5_n", "total", [["t.in_b", EQ(S("b5.live"), 1)]]),
        sp("S", "t.b5_k", "none", [["t.b5_n", "b5.scope"]]),
        # ---- B1-02 per device and per year, B1-03 per year
        sp(DY, "t.b12", "none", [[OKP, UF, RL, VIA("t.w", "dy.cal"), GWP]]),
        sp(DY, "t.b12_i", BY("_parent"), [["t.b12"]]),
        sp(DY, "t.b12_y", BY("dy.cal"), [["t.b12"]]),
        sp(RE, "t.b13", "none", [[LOKP, "t.in_r", EQ("b1.first", 1), L3, VIA(UF, "b1.dy")],
                                 [LOKP, "t.in_r", EQ("b1.first", 1), TOP0, C(-1), L3, VIA(UF, "b1.dy"), RL, VIA("t.w", "re.cal")],
                                 [LOKP, "t.in_r", EQ("b1.first", 0), L3, M0]]),
        sp(RE, "t.b13_y", BY("re.cal"), [["t.b13"]]),
        sp(CAL, "t.b1_y", "none", [["t.b12_y"], ["t.b13_y"]]),
        # ---- B1-04 end residual in its interval form (no subtraction from the initial charge)
        sp(DY, "t.b14w", "none", [[T_], [C(-1), "k"]]),
        sp(DY, "t.b14", "total", [
            WIN + [EQ("b1.p", 0), K4, UF],
            WIN + [EQ("b1.p", 1), LE(TIN, "b1.tau1"), K4, UF],
            WIN + [TOP0, EQ("b1.p", 0), C(-1), K4, UF, RL, "t.b14w"],
            WIN + [TOP0, EQ("b1.p", 1), LE(TIN, "b1.tau1"), C(-1), K4, UF, RL, "t.b14w"],
            WIN + [EQ("b1.p", 1), IN("b1.tau1"), K4, M0]]),
        # ---- scalars that are a product with a knot value: B2-01 = purchased-electricity emission * share, X-11
        sp(OP, "t.b21", "none", [[EQ("b21.ok", 1), K("EL"), "facility_management_ratio"]]),
        sp(OP, "t.x11", "none", [[EQ("x11.ok", 1), OF("gross_floor_area", "project"), "electricity_per_m2_per_year", "x11.c.f", K("G")]]),
        # ---- X-10 resource and waste mass: row mass * (1 + number of renewals)
        sp(M, "t.x10r", "total", [["x10.r", "t.k_m"]]),
        sp(M, "t.x10wm", "total", [["x10.w", "t.k_m"]]),
        sp(EQT, "t.x10we", "total", [["x10.we", "t.k_e"]]),
        sp("S", "t.x10w", "none", [["t.x10wm"], ["t.x10we"]]),
        # ---- X-08 by the value of the cycle
        sp(CE, "t.cnt_c", BY("_parent"), [["t.in_c"]]),
        sp(CYC, "t.x08_on", "none", [[GE1("t.cnt_c"), GE1("x08.rows")]]),
        sp(CYC, "t.x08_e", "none", [[EQ("t.x08_on", 1), "t.cnt_c", "x08.U"]]),
        sp(CYC, "t.x08_s", "total", [["t.x08_e"]]),
        sp(EQT, "t.x08_x", "total", [[EQ("ee.listed", 1), "x08.ue", "t.cnt_e"]]),
        sp("S", "t.x08_v", "none", [["t.x08_x"], ["t.x08_s"]]),
    ]
    # ---- activity by factor of the repeated lines: repairs (line * rate * repair years), renewals (line * count)
    l3, l4 = [], []
    for s in LINE_SLOTS:
        if s.get("b3"):
            st.append(sp(s["table"], "t.l3." + s["id"], BY(s["fref"]), [s["mask"] + _b3_mask(s) + s["act"] + _mult(s, ["repair_rate", "t.yrs_m"], ["repair_rate", "t.yrs_e"])]))
            l3.append("t.l3." + s["id"])
        if s.get("b4"):
            st.append(sp(s["table"], "t.l4." + s["id"], BY(s["fref"]), [s["mask"] + s["act"] + _mult(s, ["t.cnt_m"], ["t.cnt_e"])]))
            l4.append("t.l4." + s["id"])
    st += [sp("factors", "L.B3", "none", [[c] for c in l3]), sp("factors", "L.B4", "none", [[c] for c in l4])]
    for tag, table, k in (("b62.gas", OP, "act.gas"), ("b62.oil", OP, "act.oil"), ("b62.dh", OP, "act.dh"),
                          ("b71", WW, "act.wat"), ("b72", WW, "act.sew"), ("b73", WW, "act.msw")):
        st.append(sp(table, "t.l." + tag, BY(tag + ".f.ref"), [[EQ(tag + ".ok", 1), K(k)]]))
    st += [sp("factors", "L.B6", "none", [["t.l.b62.gas"], ["t.l.b62.oil"], ["t.l.b62.dh"]]),
           sp("factors", "L.B7", "none", [["t.l.b71"], ["t.l.b72"], ["t.l.b73"]]),
           sp("factors", "L.B5", "none", [[S("t.b5_k"), "L." + STAGE_TAG[s]] for s in STATIC_STAGES]),
           # factors used by at least one line at T (lines that exist only at a renewal count once a renewal has happened)
           sp(M, "t.u.inst", BY("b4.inst.f.ref"), [[EQ("b4.inst.ok", 1), GE1("t.cnt_m")]]),
           sp(EQT, "t.u.dlv", BY("b4.dlv.f.ref"), [[EQ("b4.dlv.ok", 1), GE1("t.cnt_e")]]),
           sp(EQT, "t.u.ins", BY("b4.ins.f.ref"), [[EQ("b4.ins.ok", 1), GE1("t.cnt_e")]]),
           sp("factors", "t.lp", "none", [["lp.const"], ["t.u.inst"], ["t.u.dlv"], ["t.u.ins"]]),
           sp("factors", "t.used", "none", [[GE1("t.lp")]]),
           sp("factors", "t.qa3_v", "none", [[EQ("t.used", 1), EQ("f.okq", 0)]]),
           sp("factors", "t.qa3_n", "total", [["t.used"]]),
           sp("factors", "t.qa3_nv", "total", [["t.qa3_v"]]),
           sp("S", "t.qa3_ok", "none", [[EQ("t.qa3_nv", 0)]])]
    return {"id": "TIME", "doc": "knot tables evaluated at T by gated sums", "steps": st, "outputs": {}}

TIME = _time()

# =============================================================================================
IS, BIS = "boundary.included_lifecycle_stages", "base:boundary.included_lifecycle_stages"
HAS = EQ(OF("s8.has", "boundary"), 1)
AREA, BAREA = OF("gross_floor_area", "project"), OF("gross_floor_area", "base:project")
LINE_STAGES = ("A1-A3", "A4", "A5", "B3", "B4", "B5", "B6", "B7", "C1", "C2", "C3", "C4")     # stages with factor lines
INC = lambda s: EQ(S("inc." + STAGE_TAG[s]), 1)
ST = lambda s: S("st." + STAGE_TAG[s])

def _qa2(pre, tab, child):
    return [sp(child, pre + ".bad", BY("_parent"), [[NOT(RNG("value", 0, "inf"))], [RNG("value", 0, "inf"), LE(TIN, "value")]]),
            sp(child, pre + ".z", BY("_parent"), [[EQ("value", 0)]]),
            sp(tab, pre + ".v", "none", [[GE1(pre + ".bad")]]),
            sp(tab, pre + ".w", "none", [[GE1(pre + ".z")]]),
            sp(tab, pre + ".nv", "total", [[pre + ".v"]])]

def _stage_terms(kind):
    """Terms of the per-stage sum over the lines: kind "rc" = activity * factor value, "co" = activity * CO2 amount.
    Pseudo lines (purchased electricity, refrigerants) carry their CO2e value; refrigerants are 0 in the CO2 version."""
    out = {}
    for s in STAGES:
        tag = STAGE_TAG[s]
        t = [[S("x04.%s.%s" % (kind, tag))]] if s in LINE_STAGES else []
        if s == "A5":
            t = [[S("a51.value")]] + t
        elif s == "B1":
            t = [[V("B1-02")], [V("B1-03")], [V("B1-04")]] if kind == "rc" else [[C(0.0)]]
        elif s == "B2":
            t = [[V("B2-01")]]
        elif s == "B6":
            t = [[K("EL")]] + t + [[C(-1), V("B2-01")]]
        elif s == "B5":
            t = t + [[S("t.b5_k"), S("a51.value")]]
        out[s] = t
    return out

def _agg():
    st = [
        # ---- X-02 stage vector and completeness
        MATCH("STG", "x02.iref", ["name"], IS, ["value"]),
        sp("STG", "x02.inc", "none", [[PR("x02.iref")]]),
        sp("STG", "x02.b2in", "total", [[EQ("name", "B2"), EQ("x02.inc", 1)]]),
        MATCH("COMP", "x02.s", ["stage"], "STG", ["name"]), MATCH("COMP", "x02.u", ["unit"], "U", ["id"]),
        sp("COMP", "x02.full", BY("x02.s"), [["sign", VIA("value", "x02.u")]]),
        sp("COMP", "x02.bsraw", BY("x02.s"), [[EQ("needs_b2", 0), "sign", VIA("value", "x02.u")],
                                              [EQ("needs_b2", 1), EQ(S("x02.b2in"), 1), "sign", VIA("value", "x02.u")]]),
        sp("STG", "x02.bs", "none", [[EQ("x02.inc", 1), "x02.bsraw"]]),
        MATCH("CHK", "x02.cs", ["stage"], "STG", ["name"]), MATCH("CHK", "x02.cu", ["unit"], "U", ["id"]),
        sp("CHK", "x02.ninc", BY("x02.cu"), [[EQ(VIA("x02.inc", "x02.cs"), 1), GE1(VIA("bad", "x02.cu"))]]),
        sp("U", "x02.uinc", "none", [[GE1("x02.ninc")]]),
        sp("U", "x02.n", "total", [["x02.uinc"]]),
        sp("S", "x02.complete", "none", [[EQ("x02.n", 0)]]),
    ]
    for s in STAGES:                                            # the stage values and inclusion marks as scalars
        st += [sp("STG", "inc." + STAGE_TAG[s], "total", [[EQ("name", s), EQ("x02.inc", 1)]]),
               sp("STG", "st." + STAGE_TAG[s], "total", [[EQ("name", s), "x02.full"]])]
    st += [
        # ---- SUM-01..07
        sp("STG", "sum1", "total", [[EQ("x02.inc", 1), EQ("up", 1), "x02.bs"]]),
        sp("STG", "sum2", "total", [[EQ("x02.inc", 1), EQ("emb", 1), "x02.bs"]]),
        sp("STG", "sum3", "total", [[EQ("x02.inc", 1), "x02.bs"]]),
        sp("S", "sum4.ok", "none", [[RNG(AREA, 0, "inf", lo_open=True)]]),
        sp("S", "sum4", "none", [[EQ("sum4.ok", 1), "sum3", FN("inv", AREA)]]),
        sp("S", "sum5.den", "none", [[EQ("sum4.ok", 1), AREA, T_]]),
        sp("S", "sum5", "none", [[EQ("sum4.ok", 1), "sum3", FN("inv", "sum5.den")]]),
        sp("S", "sum6", "none", [["sum3", C(0.001)]]),
        sp("STG", "sum7.neg", "total", [[EQ("x02.inc", 1), RNG("x02.bs", "-inf", 0, hi_open=True)]]),
        sp("S", "sum7.def", "none", [[RNG("sum3", 0, "inf", lo_open=True), EQ("sum7.neg", 0)]]),
        sp("STG", "sum7.share", "none", [[EQ("x02.inc", 1), EQ(S("sum7.def"), 1), "x02.bs", FN("inv", S("sum3"))]]),
        # ---- SUM-08 comparison with the baseline scenario
        MATCH("boundary", "s8.b", ["baseline_scenario"], "base:meta", ["scenario_id"]),
        sp("boundary", "s8.has", "none", [[PR("s8.b")]]),
        sp("boundary", "s8.eqA", "none", [[EQC(AREA, BAREA)], [NOT(PR(AREA)), NOT(PR(BAREA))]]),
        sp("boundary", "s8.eqT", "none", [[EQC(T_, OF("study_period", "base:boundary"))]]),
        MATCH(IS, "s8.m1", ["value"], BIS, ["value"]), sp(IS, "s8.d1", "total", [[NOT(PR("s8.m1"))]]),
        MATCH(BIS, "s8.m2", ["value"], IS, ["value"]), sp(BIS, "s8.d2", "total", [[NOT(PR("s8.m2"))]]),
        sp("boundary", "s8.eqG", "none", [[EQC("results_gas_scope", OF("results_gas_scope", "base:boundary"))]]),
        MATCH("factors", "s8.f1", ["release_year"], "base:factors", ["release_year"]), sp("factors", "s8.e1", "total", [[NOT(PR("s8.f1"))]]),
        MATCH("base:factors", "s8.f2", ["release_year"], "factors", ["release_year"]), sp("base:factors", "s8.e2", "total", [[NOT(PR("s8.f2"))]]),
        sp("S", "s8.rA", "none", [[HAS, EQ(OF("s8.eqA", "boundary"), 0)]]),
        sp("S", "s8.rT", "none", [[HAS, EQ(OF("s8.eqT", "boundary"), 0)]]),
        sp("S", "s8.rS", "none", [[HAS, NOT(EQ("s8.d1", 0))], [HAS, EQ("s8.d1", 0), NOT(EQ("s8.d2", 0))]]),
        sp("S", "s8.rG", "none", [[HAS, EQ(OF("s8.eqG", "boundary"), 0)]]),
        sp("S", "s8.rF", "none", [[HAS, NOT(EQ("s8.e1", 0))], [HAS, EQ("s8.e1", 0), NOT(EQ("s8.e2", 0))]]),
        sp("S", "s8.nr", "none", [["s8.rA"], ["s8.rT"], ["s8.rS"], ["s8.rG"], ["s8.rF"]]),
        sp("S", "s8.cmp", "none", [[HAS, EQ("s8.nr", 0)]]),
        sp("S", "s8.delta", "none", [[EQ("s8.cmp", 1), "sum3"], [EQ("s8.cmp", 1), C(-1), OF("base_sum3", "TT")]]),
        sp("S", "s8.bp", "none", [[EQ("s8.cmp", 1), OF("base_sum3", "TT")], [EQ("s8.cmp", 1), C(-1), "sum3"]]),
        sp("S", "s8.pos", "none", [[EQ("s8.cmp", 1), RNG(OF("base_sum3", "TT"), 0, "inf", lo_open=True)]]),
        sp("S", "s8.sav", "none", [[EQ("s8.pos", 1), "s8.bp", FN("inv", OF("base_sum3", "TT"))]]),
    ]
    # ---- X-04 / X-05: sums over the lines by stage; gas breakdown; QA-01 (a)
    for s in LINE_STAGES:
        tag = STAGE_TAG[s]
        st += [sp("factors", "x04.rc." + tag, "total", [["L." + tag, "value"]]),
               sp("factors", "x04.co." + tag, "total", [["L." + tag, "f.co2"]])]
    rc, co = _stage_terms("rc"), _stage_terms("co")
    for s in STAGES:
        tag = STAGE_TAG[s]
        st += [sp("S", "x04.rec." + tag, "none", rc[s]), sp("S", "x05.st." + tag, "none", co[s])]
    st += [
        sp("STG", "x04.rec", "none", [[EQ("name", s), S("x04.rec." + STAGE_TAG[s])] for s in STAGES]),
        sp("STG", "x05.co2", "none", [[EQ("name", s), S("x05.st." + STAGE_TAG[s])] for s in STAGES]),
        sp("factors", "x04.A", "none", [["L." + STAGE_TAG[s]] for s in LINE_STAGES]),
        sp("factors.gas_amounts", "x04.bygas", BY("x04.g"), [[PR("x04.g"), VIA("x04.A", "_parent"), "value"]]),
        sp("gases", "x04.fg", "total", [[VIA("value", "x04.w"), "x04.bygas"]]),
        sp("S", "x04.grid", "none", [["a51.value"], [V("B2-01")], [K("EL")], [C(-1), V("B2-01")], ["t.b5_k", "a51.value"]]),
        sp("S", "x04.refr", "none", [[V("B1-02")], [V("B1-03")], [V("B1-04")]]),
        sp("S", "x04.value", "none", [["x04.fg"], ["x04.grid"], ["x04.refr"]]),
        sp("STG", "x05.sum", "total", [[EQ("x02.inc", 1), "x05.co2"]]),
        sp("S", "x05.value", "none", [["x05.sum"], [INC("B6"), NOT(INC("B2")), "x05.st.B2"]]),
        # QA-01 (a): the stage value and the sum over its lines agree within 1e-9 * max(|stage|, 1)
        sp("STG", "qa1.d", "none", [["x02.full"], [C(-1), "x04.rec"]]),
        sp("STG", "qa1.nd", "none", [[C(-1), "qa1.d"]]),
        sp("STG", "qa1.abs", "none", [[RNG("x02.full", 0, "inf"), "x02.full"], [RNG("x02.full", "-inf", 0, hi_open=True), C(-1), "x02.full"]]),
        sp("STG", "qa1.tol", "none", [[RNG("qa1.abs", 1, "inf"), C(1e-9), "qa1.abs"], [RNG("qa1.abs", "-inf", 1, hi_open=True), C(1e-9)]]),
        sp("STG", "qa1.a", "none", [[NOT(LE("qa1.d", "qa1.tol"))], [LE("qa1.d", "qa1.tol"), NOT(LE("qa1.nd", "qa1.tol"))]]),
        sp("STG", "qa1.na", "total", [["qa1.a"]]),
        sp("S", "qa1.ok", "none", [[EQ("qa1.na", 0), EQ("qa1.n", 0)]]),
    ]
    # ---- X-07 yearly series and its running sum
    c = "y0.c"
    YIN, LAST = EQ(VIA("t.in", c), 1), EQ(VIA("t.last", c), 1)
    W, EL = VIA("t.w", c), VIA("b61.e", c)
    st += [
        sp("Y0", "x07.s", "none", [
            [EQ("i", 0), INC("A1-A3"), ST("A1-A3")], [EQ("i", 0), INC("A4"), ST("A4")], [EQ("i", 0), INC("A5"), ST("A5")],
            [YIN, INC("B6"), INC("B2"), W, EL, FN("one_minus", OF("b21.share", OP))],
            [YIN, INC("B6"), NOT(INC("B2")), W, EL],
            [YIN, INC("B6"), W, VIA("b62.e", c)],
            [YIN, INC("B2"), W, EL, OF("b21.share", OP)],
            [YIN, INC("B7"), W, VIA("b74.a", c)],
            [YIN, INC("B1"), VIA("t.b1_y", c)], [YIN, INC("B3"), VIA("t.b3_y", c)],
            [YIN, INC("B4"), VIA("t.b42_y", c)], [YIN, INC("B5"), VIA("t.b5_y", c)],
            [LAST, INC("C1"), ST("C1")], [LAST, INC("C2"), ST("C2")], [LAST, INC("C3"), ST("C3")], [LAST, INC("C4"), ST("C4")],
            [LAST, INC("B1"), V("B1-04")]]),
        sp("Y0.x", "x07.c", BY("_parent"), [[LE("j", VIA("i", "_parent")), VIA("x07.s", "y0.j")]]),
        sp("Y0", "x07.value", "total", [[LAST, "x07.c"]]),
        # ---- QA-02 explicit event years inside the study period
        *_qa2("qa2.e", EQT, "equipment.replacement_event_list"),
        *_qa2("qa2.r", D, "refrigerants.change_years"),
        sp("S", "qa2.ok", "none", [[EQ("qa2.e.nv", 0), EQ("qa2.r.nv", 0)]]),
        # ---- agreement of descriptors and year tables: [number of differing years before T == 0]
        *[sp("S", "dmt." + n, "none", [[EQ(K("mis." + n), 0)]]) for n in ("b64", "b62", "b71", "b72", "b73", "x06")],
    ]
    return {"id": "AGG", "doc": "stage vector, totals, indicators, gas breakdown, yearly series, flags, comparisons", "steps": st, "outputs": {}}

AGG = _agg()
