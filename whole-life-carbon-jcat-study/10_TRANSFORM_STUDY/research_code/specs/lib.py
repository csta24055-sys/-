"""Constructors and shared templates of the unified specification (data only).

The functions below only build dictionaries of the vocabulary of ``tstudy.msp`` (they are a
shorthand for writing the data, nothing is computed here). The templates are lists of steps
with ``$parameter`` and ``@local`` placeholders, expanded by ``msp.Program``.

Fictional data, independent concept model.
"""

# ---- operands and factors -------------------------------------------------------------------
def C(v):
    return {"const": v}

def OF(col, table):
    return {"col": col, "of": table}

def VIA(col, ref):
    return {"col": col, "via": ref}

def EQ(a, v=1):
    return {"pred": "eq", "a": a, "b": {"const": v}}

def EQC(a, b):
    return {"pred": "eq", "a": a, "b": b}

def PR(a):
    return {"pred": "present", "a": a}

def LE(a, b):
    return {"pred": "le", "a": a, "b": b}

def NOT(p):
    return dict(p, **{"not": True})

def RNG(a, lo, hi, lo_open=False, hi_open=False):
    return {"pred": "range", "a": a, "lo": lo, "hi": hi, "lo_open": lo_open, "hi_open": hi_open}

def NN(a):
    """finite and >= 0"""
    return {"pred": "range", "a": a, "lo": 0, "hi": "inf", "hi_open": True}

def RATIO(a):
    return {"pred": "range", "a": a, "lo": 0, "hi": 1}

def GE1(a):
    return {"pred": "range", "a": a, "lo": 1, "hi": "inf"}

def FN(name, a):
    return {"fn": name, "a": a}

# ---- steps ------------------------------------------------------------------------------------
def sp(table, out, group, terms):
    return {"op": "sp", "table": table, "out": out, "group": group, "terms": terms}

def MATCH(table, out, keys, into, on):
    return {"op": "match", "table": table, "out": out, "keys": keys, "into": into, "on": on}

def F(as_, T, fid, gate, unit, extra="_none"):
    return {"use": "FACTOR", "as": as_, "with": {"T": T, "fid": fid, "gate": gate, "unit": unit, "extra": extra}}

def CONV(as_, T, frm, to, extra="_none"):
    return {"use": "CONV", "as": as_, "with": {"T": T, "from": frm, "to": to, "extra": extra}}

def BY(ref):
    return {"by": ref}

VAL = lambda ref: VIA("value", ref)

CAL = "operation.grid.table"          # the calendar: one row per study year, k = _pos = 0, 1, ...
STATES = ("OBSERVED", "ESTIMATE", "EXPLICIT_ZERO", "MISSING", "DERIVED")

TEMPLATES = {
    # agreement of two year series: 1 where they differ by more than 1e-12 relative (and are not equal)
    # params: v, t
    "CLOSE": [
        sp(CAL, "@av", "none", [[RNG("$v", 0, "inf"), "$v"], [RNG("$v", "-inf", 0, hi_open=True), C(-1), "$v"]]),
        sp(CAL, "@at", "none", [[RNG("$t", 0, "inf"), "$t"], [RNG("$t", "-inf", 0, hi_open=True), C(-1), "$t"]]),
        sp(CAL, "@mx", "none", [[LE("@at", "@av"), "@av"], [NOT(LE("@at", "@av")), "@at"]]),
        sp(CAL, "@tol", "none", [[C(1e-12), "@mx"]]),
        sp(CAL, "@d", "none", [[PR("$t"), "$v"], [PR("$t"), C(-1), "$t"]]),
        sp(CAL, "@nd", "none", [[C(-1), "@d"]]),
        sp(CAL, "@mis", "none", [
            [PR("$t"), NOT(EQC("$v", "$t")), NOT(LE("@d", "@tol"))],
            [PR("$t"), NOT(EQC("$v", "$t")), LE("@d", "@tol"), NOT(LE("@nd", "@tol"))]]),
    ],
    # yearly values of an annual profile on the calendar
    # params: O (table of the record), kind, base, slope, tab (child table with the year table)
    "PROFILE": [
        sp("$O", "@d", "none", [[EQ("$kind", "CONSTANT"), PR("$base")],
                                [EQ("$kind", "LINEAR_TREND"), PR("$base"), PR("$slope")]]),
        MATCH(CAL, "@ref", ["_pos"], "$tab", ["_pos"]),
        sp(CAL, "@v", "none", [
            [EQ(OF("$kind", "$O"), "CONSTANT"), PR(OF("$base", "$O")), OF("$base", "$O")],
            [EQ(OF("$kind", "$O"), "LINEAR_TREND"), PR(OF("$base", "$O")), PR(OF("$slope", "$O")), OF("$base", "$O")],
            [EQ(OF("$kind", "$O"), "LINEAR_TREND"), PR(OF("$base", "$O")), PR(OF("$slope", "$O")), OF("$slope", "$O"), "_pos"],
            [EQ(OF("@d", "$O"), 0), VIA("value", "@ref")]]),
        sp(CAL, "@t", "none", [[VIA("value", "@ref")]]),
        {"use": "CLOSE", "as": "@m", "with": {"v": "@v", "t": "@t"}},
    ],
    # yearly emission of an annual quantity with a factor: value * multiplier * factor; @act = value * multiplier
    # params: O, fid, gate, uh, ut, v
    "ANNUALF": [
        {"use": "FACTOR", "as": "@f", "with": {"T": "$O", "fid": "$fid", "gate": "$gate", "unit": "$uh", "extra": "_none"}},
        sp("$O", "@ok", "none", [[EQ("@f.ok", 1), EQ("$ut", "year")]]),
        sp("$O", "@fv", "none", [[EQ("@ok", 1), VAL("@f.ref")]]),
        sp(CAL, "@act", "none", [[EQ(OF("@ok", "$O"), 1), "$v", OF("@f.c.f", "$O")]]),
        sp(CAL, "@e", "none", [[EQ(OF("@ok", "$O"), 1), "$v", OF("@f.c.f", "$O"), OF("@fv", "$O")]]),
    ],
    # one factor (I + N^s) of the resolvent of the masked shift N on a (parent, k) table
    # params: T, neg (= -s), uin, cin, uout, cout
    "DOUBLE": [
        sp("$T", "@ks", "none", [["k"], [C("$neg")]]),
        MATCH("$T", "@pv", ["_parent", "@ks"], "$T", ["_parent", "k"]),
        sp("$T", "$uout", "none", [["$uin"], [PR("@pv"), "$cin", VIA("$uin", "@pv")]]),
        sp("$T", "$cout", "none", [[PR("@pv"), "$cin", VIA("$cin", "@pv")]]),
    ],
    # state of one numeric input (SYS-01). The declared state is the override of the owner if there is one,
    # else the state of the provenance record, else MISSING.
    # params: T (table of the values), v (value column), ovr (reference to the override row), prov (reference
    #         to the provenance record), app (0/1 column: the field is looked at)
    # results: @s.<STATE> (0/1 per row), @n.<STATE> (totals)
    "STATE": (
        [sp("$T", "@d." + s, "none",
            [[PR(VIA("value", "$ovr")), EQ(VIA("value", "$ovr"), s)],
             [NOT(PR(VIA("value", "$ovr"))), PR("$prov"), EQ(VIA("value_state", "$prov"), s)]]
            + ([[NOT(PR(VIA("value", "$ovr"))), NOT(PR("$prov"))]] if s == "MISSING" else []))
         for s in STATES]
        + [sp("$T", "@live", "none", [[EQ("$app", 1), PR("$v"), EQ("@d.DERIVED", 0), NOT(EQ("$v", 0))]]),
           sp("$T", "@s.MISSING", "none", [[EQ("$app", 1), NOT(PR("$v"))], [EQ("@live", 1), EQ("@d.MISSING", 1)]]),
           sp("$T", "@s.DERIVED", "none", [[EQ("$app", 1), PR("$v"), EQ("@d.DERIVED", 1)]]),
           sp("$T", "@s.EXPLICIT_ZERO", "none", [[EQ("$app", 1), PR("$v"), EQ("@d.DERIVED", 0), EQ("$v", 0)],
                                                  [EQ("@live", 1), EQ("@d.EXPLICIT_ZERO", 1)]]),
           sp("$T", "@s.OBSERVED", "none", [[EQ("@live", 1), EQ("@d.OBSERVED", 1)]]),
           sp("$T", "@s.ESTIMATE", "none", [[EQ("@live", 1), EQ("@d.ESTIMATE", 1)]])]
        + [sp("$T", "@n." + s, "total", [["@s." + s]]) for s in STATES]
    ),
}
