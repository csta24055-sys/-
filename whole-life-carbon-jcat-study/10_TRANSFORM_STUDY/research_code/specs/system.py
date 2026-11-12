"""The unified specification of all 70 evaluation units (data only).

    inputs of a building
      -> common tables: flattened inputs, tokens, index sets, knot lattices      (INDEX_PLAN, STATIC_TABLES)
      -> masked sum-product 1 (program P1): coefficients, masks, row checks       (SPEC1)
      -> knot spectrum: the amplitudes of P1 placed on knots                      (EMIT)
      -> masked sum-product 2 (programs TIME and AGG at one study period T)       (specs/at_t.py)
      -> results of the 70 units                                                  (read-outs in tstudy/unified.py)

Fictional data, independent concept model; not a statement about any other tool.
"""
import copy

from . import pre_a
from .lib import C, EQ, MATCH, OF, TEMPLATES, CAL, sp
from .physical import (A5_01, BE, D, DY, EE, END_OF_LIFE, EQT, EVENTS, LINES, M, ME, OP, OPERATION, RE, REFRIGERANT, WW, XS, GS,
                       amplitudes)
from .gates import CHECKS, CLS, CLSX, CYC, ROUTES, SYS_01, SYS_02, SYS_03, UA, UAS
from .at_t import AGG, STAGES, TIME

# ---------------------------------------------------------------------------------------------
# common tables (built by tstudy/index.py; H = number of rows of the calendar)
# ---------------------------------------------------------------------------------------------
INDEX_PLAN = [
    {"op": "tokenise"},
    {"op": "product", "name": XS, "parent": CAL, "other": GS, "col": "s"},                      # year x grid step
    {"op": "product", "name": DY, "parent": D, "other": CAL, "col": "k"},                       # device x year
    {"op": "events", "name": ME, "parent": M, "cycle": "refresh_cycle"},
    {"op": "events", "name": EE, "parent": EQT, "cycle": "service_life", "lists": "equipment.replacement_event_list"},
    {"op": "events", "name": RE, "parent": D, "cycle": "service_life", "lists": "refrigerants.change_years"},
    {"op": "events", "name": BE, "parent": "boundary", "cycle": "replacement_cycle"},
    {"op": "sorted", "name": UAS, "source": UA, "by": "key"},                                    # use areas by name
    {"op": "distinct", "name": CLS, "sources": [[M, "material_class"]]},
    {"op": "distinct", "name": CYC, "sources": [[M, "refresh_cycle"], [EQT, "service_life"]]},
    {"op": "events", "name": CYC + ".events", "parent": CYC, "cycle": "value"},
    {"op": "static"},                                                                          # STATIC_TABLES below
    {"op": "product", "name": CLSX, "parent": CLS, "other": ROUTES, "col": "r"},                # class x route
    {"op": "range", "name": "Y0", "n": "H+1", "col": "i"},                                      # time point 0 and the years
    {"op": "product", "name": "Y0.x", "parent": "Y0", "other": "Y0", "col": "j"},               # year x year (running sum)
]

COMP_ROWS = [("A1-A3", "A13-01", 1), ("A1-A3", "A13-03", 1), ("A1-A3", "A13-04", 1), ("A1-A3", "X-01", 1), ("A4", "A4-01", 1), ("A4", "A4-02", 1),
             ("A5", "A5-04", 1), ("B1", "B1-02", 1), ("B1", "B1-03", 1), ("B1", "B1-04", 1), ("B2", "B2-01", 1), ("B3", "B3-01", 1),
             ("B4", "B4-02", 1), ("B5", "B5-01", 1), ("B6", "B6-03", 1), ("B6", "B2-01", -1), ("B7", "B7-04", 1), ("C1", "C1-01", 1),
             ("C2", "C2-01", 1), ("C3", "C3-01", 1), ("C3", "X-14", 1), ("C4", "C4-01", 1)]
STAGE_UNITS = {"A1-A3": ("A13-01", "A13-03", "A13-04", "X-01"), "A4": ("A4-01", "A4-02"), "A5": ("A5-01", "A5-02", "A5-03"),
               "B1": ("B1-02", "B1-03", "B1-04"), "B2": ("B2-01", "B6-01"), "B3": ("B3-01",), "B4": ("B4-02",), "B5": ("B5-01",),
               "B6": ("B6-01", "B6-02"), "B7": ("B7-01", "B7-02", "B7-03"), "C1": ("C1-01",), "C2": ("C2-01",), "C3": ("C3-01", "X-14"), "C4": ("C4-01",)}
_CHK = [(s, u) for s in STAGES for u in STAGE_UNITS[s]]
STATIC_TABLES = {
    "STG": {"name": list(STAGES), "up": [1 if s in ("A1-A3", "A4", "A5") else 0 for s in STAGES],
            "emb": [0 if s in ("B6", "B7") else 1 for s in STAGES]},
    "COMP": {"stage": [r[0] for r in COMP_ROWS], "unit": [r[1] for r in COMP_ROWS], "sign": [r[2] for r in COMP_ROWS],
             "needs_b2": [1 if (r[0], r[1]) == ("B6", "B2-01") else 0 for r in COMP_ROWS]},
    "CHK": {"stage": [c[0] for c in _CHK], "unit": [c[1] for c in _CHK]},
    ROUTES: {"name": ["REUSE", "RECYCLE", "PROCESSING", "LANDFILL"]},
}

# ---------------------------------------------------------------------------------------------
# program P1
# ---------------------------------------------------------------------------------------------
def _terms(out):
    for u in pre_a.UNITS:
        for st in u["steps"]:
            if st.get("out") == out:
                return copy.deepcopy(st["terms"])
    raise KeyError(out)

# unit values that do not depend on T, and the counters behind the completeness flag of X-02
CONST_VALUE = {"A13-01": "a01.value", "A13-03": "a03.value", "A13-04": "a04.value", "X-01": "x01.value", "A4-01": "a41.value", "A4-02": "a42.value",
               "A5-04": "a54.value", "C1-01": "c11.value", "C2-01": "c21.value", "C3-01": "c31.value", "X-14": "x14.value", "C4-01": "c41.value"}
BAD = {"A13-01": [["a01.n_skipped"]], "A13-03": [["a03.n_skipped"]], "A13-04": [["a04.n_skipped"]], "X-01": [["x01.n_skipped"]],
       "A4-01": [["a41.n_skipped"]], "A4-02": [["a42.n_skipped"]], "A5-01": [[EQ(OF("a51.ok", OP), 0)]], "A5-02": [["a52.n_skipped"]],
       "A5-03": [["a53.n_skipped"]], "B1-02": [["b12.nsk"]], "B1-03": [["b13.nsk"]], "B1-04": [["b14.nsk"]],
       "B2-01": [[EQ(OF("b21.ok", OP), 0)]], "B6-01": [[EQ(OF("b61.ok", OP), 0)]], "B3-01": [["b3.n_skipped"]],
       "B5-01": [[EQ("b5.computed", 0)]], "B6-02": [[OF("b62.nsk", OP)]], "B7-01": [[OF("b71.nsk", WW)]], "B7-02": [[OF("b72.nsk", WW)]],
       "B7-03": [[OF("b73.nsk", WW)]], "C1-01": [["c11.n_skipped"]], "C2-01": [["c21.n_skipped"]], "C3-01": [["c31.nsk"], ["c31.nrsk"]],
       "X-14": [["x14.n_skipped"]], "C4-01": [["c41.nsk"], ["c41.nrsk"]]}
T_UNITS = ("B1-02", "B1-03", "B1-04", "B2-01", "B3-01", "B4-02", "B5-01", "B6-03", "B7-04")
U_IDS = sorted(set(CONST_VALUE) | set(T_UNITS) | {u for us in STAGE_UNITS.values() for u in us})

INDEX_COLUMNS = {"id": "INDEX", "doc": "references between the index tables; amplitudes carried by events (X-10); counters of X-02", "steps": [
    sp(CAL, "cal.kp1", "none", [["_pos"], [C(1)]]),
    sp("Y0", "y0.im1", "none", [["i"], [C(-1)]]),
    MATCH("Y0", "y0.c", ["y0.im1"], CAL, ["_pos"]),
    MATCH("Y0.x", "y0.j", ["j"], "Y0", ["_row"]),
    MATCH("factors.gas_amounts", "x04.g", ["key"], "gases", ["value"]),
    MATCH("gases", "x04.w", ["value"], "gwp", ["key"]),
    *[sp("S", "bad." + uid, "none", terms) for uid, terms in BAD.items()],
], "outputs": {}}

def _spec1():
    units = []
    for u in pre_a.UNITS:
        units.append(A5_01 if u["id"] == "A5-01" else copy.deepcopy(u))
    units += END_OF_LIFE
    units.append(amplitudes(_terms("a01.n_skipped"), _terms("a03.n_skipped"), _terms("a41.n_skipped"), _terms("a42.n_skipped")))
    units += [EVENTS, OPERATION, REFRIGERANT, CHECKS, LINES, SYS_01, SYS_02, SYS_03, INDEX_COLUMNS]
    shared = list(pre_a.SHARED) + [{"use": "STAGE", "as": "stage.%s" % s, "with": {"stage": s}}
                                   for s in ("C1", "C2", "C3", "C4", "B6", "B7", "MEMO")]
    return {"name": "unified-70", "data_statement": "fictional data, independent concept model",
            "templates": dict(pre_a.TEMPLATES, **TEMPLATES), "shared": shared, "units": units}

SPEC1 = _spec1()
SPEC_TIME = {"name": "unified-70/time", "templates": {}, "shared": [], "units": [TIME]}
SPEC_AGG = {"name": "unified-70/agg", "templates": {}, "shared": [], "units": [AGG]}
PRE_A_UNITS = [u["id"] for u in pre_a.UNITS]

# ---------------------------------------------------------------------------------------------
# hand-over from P1 to the knot spectrum: which amplitude column becomes which knot shape of which spectrum
#   shape  const    a                       cell    a * clip(T - k, 0, 1)            (k = column "k")
#          atom     a * [tau < T(1-eps)]    gcell   a * [tau < T(1-eps)] * clip(T - k, 0, 1)
#          density  a * T  (T <= H)
# ---------------------------------------------------------------------------------------------
def _e(spec, table, shape, amp, **kw):
    return dict(spectrum=spec, table=table, shape=shape, amp=amp, **kw)

EMIT = [
    _e("B1-02", DY, "cell", "b1.a2", k="k"),
    _e("B1-03", RE, "atom", "b1.a3", tau="tau"),
    _e("B1-03", RE, "gcell", "b1.g3", k="cell", tau="tau"),
    _e("B1-04", D, "const", "b1.k4m0"),                       # jump form of the end residual (kept for comparison only)
    _e("B1-04", DY, "cell", "b1.y4", k="k"),
    _e("B1-04", DY, "atom", "b1.e4a", tau="b1.tau1"),
    _e("B1-04", DY, "gcell", "b1.e4g", k="k", tau="b1.tau1"),
    _e("B3-01", M, "density", "b3.a_mat"), _e("B3-01", EQT, "density", "b3.a_eq"),
    _e("B3-01", ME, "gcell", "me.b3", k="cell", tau="tau"), _e("B3-01", EE, "gcell", "ee.b3", k="cell", tau="tau"),
    _e("B4-02", ME, "atom", "me.b4", tau="tau"), _e("B4-02", EE, "atom", "ee.b4", tau="tau"),
    _e("N.b42", ME, "atom", "me.np", tau="tau"), _e("N.b42", EE, "atom", "ee.np", tau="tau"),
    _e("B5-01", BE, "atom", "be.b5", tau="tau"),
    _e("B6-03", CAL, "cell", "b63.a", k="_pos"),
    _e("EL", CAL, "cell", "b61.e", k="_pos"),                 # purchased-electricity emission (B2-01 = EL * share)
    _e("G", CAL, "cell", "x06.g", k="_pos"),                  # weighted sum of the grid factor (X-11)
    _e("B7-04", CAL, "cell", "b74.a", k="_pos"),
    *[_e("act." + n, CAL, "cell", c + ".act", k="_pos") for n, c in (("gas", "b62.gas"), ("oil", "b62.oil"), ("dh", "b62.dh"),
                                                                  ("wat", "b71"), ("sew", "b72"), ("msw", "b73"))],
    *[_e("mis." + n, CAL, "atom", c, tau="_pos") for n, c in (("b64", "b64.mis"), ("b62", "b62.mis"), ("b71", "p.wat.m.mis"),
                                                             ("b72", "p.sew.m.mis"), ("b73", "p.msw.m.mis"), ("x06", "x06.m.mis"))],
]
SPECTRA = sorted({e["spectrum"] for e in EMIT})
# unit value at T: the knot spectrum of that name, except where a product with a knot value or the interval form is used
VALUE_AT_T = {"B1-02": ("K", "B1-02"), "B1-03": ("K", "B1-03"), "B1-04": ("I", "B1-04"), "B2-01": (OP, "t.b21"), "B3-01": ("K", "B3-01"),
              "B4-02": ("K", "B4-02"), "B5-01": ("K", "B5-01"), "B6-03": ("K", "B6-03"), "B7-04": ("K", "B7-04")}
