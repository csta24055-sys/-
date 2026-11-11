"""Specification (data only) of 18 units of the independent concept model for ``tstudy.msp``:
product stage (A13-01..05, X-01, X-03, X-13, X-15, X-17, X-16), transport (A4-01, A4-02, X-12) and
construction (A5-01..04). SYS-01..04 are not part of this file.

This module defines dictionaries and lists only. Vocabulary: see the docstring of ``tstudy.msp``.
Result names are prefixed with a short unit tag (``a05.`` = A13-05, ``x15.`` = X-15, ...).
Fictional data, independent concept model; not a statement about any other tool.
"""

TEMPLATES = {
    # Stage gate of a factor record: the list ``stages`` has one entry and that entry is the stage.
    # params: stage
    "STAGE": [
        {"op": "sp", "table": "factors.stages", "out": "@n", "group": {"by": "_parent"},
         "terms": [[{"pred": "eq", "a": "value", "b": {"const": "$stage"}}]]},
        {"op": "sp", "table": "factors", "out": "@is", "group": "none",
         "terms": [[{"pred": "eq", "a": "stages#", "b": {"const": 1}},
                    {"pred": "eq", "a": "@n", "b": {"const": 1}}]]},
    ],
    # Unit conversion multiplier from $from to $to: 1 when equal, else the first row-specific entry
    # (table $extra, child of $T), else the first entry of the scenario table. No chaining.
    # params: T, from, to, extra      results: @ok (0/1), @f (multiplier, 0 where @ok is 0)
    "CONV": [
        {"op": "match", "table": "$T", "out": "@xref", "keys": ["_row", "$from", "$to"],
         "into": "$extra", "on": ["_parent", "from_unit", "to_unit"]},
        {"op": "match", "table": "$T", "out": "@cref", "keys": ["$from", "$to"],
         "into": "unit_conversions", "on": ["from_unit", "to_unit"]},
        {"op": "sp", "table": "$T", "out": "@ok", "group": "none", "terms": [
            [{"pred": "eq", "a": "$from", "b": "$to"}],
            [{"pred": "eq", "a": "$from", "b": "$to", "not": True}, {"pred": "present", "a": "@xref"}],
            [{"pred": "eq", "a": "$from", "b": "$to", "not": True}, {"pred": "present", "a": "@xref", "not": True},
             {"pred": "present", "a": "@cref"}]]},
        {"op": "sp", "table": "$T", "out": "@f", "group": "none", "terms": [
            [{"pred": "eq", "a": "$from", "b": "$to"}],
            [{"pred": "eq", "a": "$from", "b": "$to", "not": True}, {"pred": "present", "a": "@xref"},
             {"col": "factor", "via": "@xref"}],
            [{"pred": "eq", "a": "$from", "b": "$to", "not": True}, {"pred": "present", "a": "@xref", "not": True},
             {"pred": "present", "a": "@cref"}, {"col": "factor", "via": "@cref"}]]},
    ],
    # Factor look-up with its gates: record exists, licence PERMITTED_PUBLIC, stage gate $gate (a column of
    # the table factors), activity unit $unit convertible to the unit of the record.
    # params: T, fid, gate, unit, extra      results: @ref (row of factors), @unit, @c.f (multiplier), @ok (0/1)
    "FACTOR": [
        {"op": "match", "table": "$T", "out": "@ref", "keys": ["$fid"], "into": "factors", "on": ["key"]},
        {"op": "sp", "table": "$T", "out": "@unit", "group": "none", "terms": [[{"col": "unit", "via": "@ref"}]]},
        {"use": "CONV", "as": "@c", "with": {"T": "$T", "from": "$unit", "to": "@unit", "extra": "$extra"}},
        {"op": "sp", "table": "$T", "out": "@ok", "group": "none", "terms": [[
            {"pred": "present", "a": "$unit"},
            {"pred": "eq", "a": {"col": "licence_status", "via": "@ref"}, "b": {"const": "PERMITTED_PUBLIC"}},
            {"pred": "eq", "a": {"col": "$gate", "via": "@ref"}, "b": {"const": 1}},
            {"pred": "eq", "a": "@c.ok", "b": {"const": 1}}]]},
    ],
    # One summary class of X-17: indicator of the class ($terms), sum of the production emissions of the class,
    # representative factor = sum / summary quantity $q (0 when the quantity is 0), emission = quantity * factor.
    # params: terms, q
    "CLASS": [
        {"op": "sp", "table": "materials", "out": "@in", "group": "none", "terms": "$terms"},
        {"op": "sp", "table": "materials", "out": "@sum", "group": "total", "terms": [
            [{"pred": "eq", "a": "@in", "b": {"const": 1}}, "a01.by_item"],
            [{"pred": "eq", "a": "@in", "b": {"const": 1}}, "a03.by_item"]]},
        {"op": "sp", "table": "S", "out": "@fbar", "group": "none", "terms": [[
            {"pred": "eq", "a": {"col": "$q", "of": "summary_quantities"}, "b": {"const": 0}, "not": True},
            "@sum", {"fn": "inv", "a": {"col": "$q", "of": "summary_quantities"}}]]},
        {"op": "sp", "table": "S", "out": "@e", "group": "none",
         "terms": [[{"col": "$q", "of": "summary_quantities"}, "@fbar"]]},
    ],
}

# Steps that belong to no single unit: the stage gates of the factor records.
SHARED = [
    {"use": "STAGE", "as": "stage.A13", "with": {"stage": "A1-A3"}},
    {"use": "STAGE", "as": "stage.A4", "with": {"stage": "A4"}},
    {"use": "STAGE", "as": "stage.A5", "with": {"stage": "A5"}},
]

UNITS = [
    {
        "id": "A13-05",
        "doc": "ordered and installed quantity from the waste rate (basis DESIGN: ordered = Q/(1-w))",
        "steps": [
            {"op": "sp", "table": "materials", "out": "a05.ok", "group": "none", "terms": [[
                {"pred": "range", "a": "quantity", "lo": 0, "hi": "inf", "hi_open": True},
                {"pred": "range", "a": "waste_rate", "lo": 0, "hi": 1, "hi_open": True}]]},
            {"op": "sp", "table": "materials", "out": "a05.q_ord", "group": "none", "terms": [
                [{"pred": "eq", "a": "a05.ok", "b": {"const": 1}},
                 {"pred": "eq", "a": "quantity_basis", "b": {"const": "DESIGN"}},
                 "quantity", {"fn": "inv_one_minus", "a": "waste_rate"}],
                [{"pred": "eq", "a": "a05.ok", "b": {"const": 1}},
                 {"pred": "eq", "a": "quantity_basis", "b": {"const": "DESIGN"}, "not": True},
                 "quantity"]]},
            {"op": "sp", "table": "materials", "out": "a05.q_inst", "group": "none", "terms": [
                [{"pred": "eq", "a": "a05.ok", "b": {"const": 1}},
                 {"pred": "eq", "a": "quantity_basis", "b": {"const": "DESIGN"}},
                 "quantity"],
                [{"pred": "eq", "a": "a05.ok", "b": {"const": 1}},
                 {"pred": "eq", "a": "quantity_basis", "b": {"const": "DESIGN"}, "not": True},
                 "quantity", {"fn": "one_minus", "a": "waste_rate"}]]},
            {"op": "sp", "table": "materials", "out": "a05.n_skipped", "group": "total",
             "terms": [[{"pred": "eq", "a": "a05.ok", "b": {"const": 0}}]]},
        ],
        "outputs": {
            "q_ord": {"read": "rows", "table": "materials", "col": "a05.q_ord", "where": "a05.ok"},
            "q_inst": {"read": "rows", "table": "materials", "col": "a05.q_inst", "where": "a05.ok"},
            "n_skipped": {"read": "scalar", "col": "a05.n_skipped", "as": "int"},
        },
    },
    {
        "id": "X-13",
        "doc": "net ordered quantity with reuse of offcuts: installed + (ordered - installed)*(1 - reuse rate)",
        "steps": [
            {"op": "sp", "table": "materials", "out": "x13.ok", "group": "none", "terms": [[
                {"pred": "eq", "a": "a05.ok", "b": {"const": 1}},
                {"pred": "range", "a": "reuse_rate", "lo": 0, "hi": 1}]]},
            {"op": "sp", "table": "materials", "out": "x13.diff", "group": "none", "terms": [
                [{"pred": "eq", "a": "x13.ok", "b": {"const": 1}}, "a05.q_ord"],
                [{"pred": "eq", "a": "x13.ok", "b": {"const": 1}}, {"const": -1}, "a05.q_inst"]]},
            {"op": "sp", "table": "materials", "out": "x13.disposed", "group": "none", "terms": [[
                {"pred": "eq", "a": "x13.ok", "b": {"const": 1}}, "x13.diff", {"fn": "one_minus", "a": "reuse_rate"}]]},
            {"op": "sp", "table": "materials", "out": "x13.net", "group": "none", "terms": [
                [{"pred": "eq", "a": "x13.ok", "b": {"const": 1}}, "a05.q_inst"],
                [{"pred": "eq", "a": "x13.ok", "b": {"const": 1}}, "x13.disposed"]]},
        ],
        "outputs": {
            "by_item": {"read": "rows", "table": "materials", "col": "x13.net", "where": "x13.ok"},
            "waste_by_item": {"read": "rows", "table": "materials", "col": "x13.disposed", "where": "x13.ok"},
        },
    },
    {
        "id": "A13-02",
        "doc": "composite factor per kg: mass-fraction weighted component factors; no factor when a component "
               "is unusable, a fraction is negative or the fractions do not sum to 1 within 1e-6",
        "steps": [
            {"use": "FACTOR", "as": "a02.c", "with": {"T": "materials.composition", "fid": "factor_id",
                                                     "gate": "stage.A13.is", "unit": {"const": "kg"}, "extra": "_none"}},
            {"op": "sp", "table": "materials.composition", "out": "a02.good", "group": "none", "terms": [[
                {"pred": "eq", "a": "a02.c.ok", "b": {"const": 1}},
                {"pred": "range", "a": "mass_fraction", "lo": 0, "hi": "inf", "hi_open": True}]]},
            {"op": "sp", "table": "materials.composition", "out": "a02.n_bad", "group": {"by": "_parent"},
             "terms": [[{"pred": "eq", "a": "a02.good", "b": {"const": 0}}]]},
            {"op": "sp", "table": "materials.composition", "out": "a02.sum_frac", "group": {"by": "_parent"},
             "terms": [[{"pred": "eq", "a": "a02.good", "b": {"const": 1}}, "mass_fraction"]]},
            {"op": "sp", "table": "materials.composition", "out": "a02.value", "group": {"by": "_parent"},
             "terms": [[{"pred": "eq", "a": "a02.good", "b": {"const": 1}}, "mass_fraction", "a02.c.c.f",
                        {"col": "value", "via": "a02.c.ref"}]]},
            {"op": "sp", "table": "materials", "out": "a02.resid", "group": "none",
             "terms": [["a02.sum_frac"], [{"const": -1}]]},
            {"op": "sp", "table": "materials", "out": "a02.ok", "group": "none", "terms": [[
                {"pred": "present", "a": "composition#"},
                {"pred": "eq", "a": "a02.n_bad", "b": {"const": 0}},
                {"pred": "range", "a": "a02.resid", "lo": -1e-6, "hi": 1e-6}]]},
            {"op": "sp", "table": "materials", "out": "a02.n_invalid", "group": "total", "terms": [[
                {"pred": "present", "a": "composition#"},
                {"pred": "eq", "a": "a02.ok", "b": {"const": 0}}]]},
        ],
        "outputs": {
            "by_item": {"read": "rows", "table": "materials", "col": "a02.value", "where": "a02.ok"},
            "n_invalid": {"read": "scalar", "col": "a02.n_invalid", "as": "int"},
        },
    },
    {
        "id": "X-15",
        "doc": "factor resolution with priority (1) product-specific declaration, (2) composite factor, "
               "(3) generic factor; conversion multiplier from the quantity unit to the factor unit",
        "steps": [
            # (1) product-specific declaration: usable factor record ...
            {"use": "FACTOR", "as": "x15.e", "with": {"T": "materials", "fid": "epd.factor_id", "gate": "stage.A13.is",
                                                     "unit": "quantity_unit", "extra": "materials.conversions"}},
            # ... whose stage list equals the declared stage list (same length, equal entry at every position) ...
            {"op": "sp", "table": "materials.epd.declared_stages", "out": "x15.frow", "group": "none",
             "terms": [[{"col": "x15.e.ref", "via": "_parent"}]]},
            {"op": "match", "table": "materials.epd.declared_stages", "out": "x15.srow", "keys": ["x15.frow", "_pos"],
             "into": "factors.stages", "on": ["_parent", "_pos"]},
            {"op": "sp", "table": "materials.epd.declared_stages", "out": "x15.n_eq", "group": {"by": "_parent"},
             "terms": [[{"pred": "present", "a": "x15.srow"},
                        {"pred": "eq", "a": "value", "b": {"col": "value", "via": "x15.srow"}}]]},
            # ... declared unit and validity date equal to the record, not expired at the assessment date.
            {"op": "sp", "table": "materials", "out": "x15.is_epd", "group": "none", "terms": [[
                {"pred": "present", "a": "epd#"},
                {"pred": "eq", "a": "x15.e.ok", "b": {"const": 1}},
                {"pred": "eq", "a": "epd.declared_stages#", "b": {"col": "stages#", "via": "x15.e.ref"}},
                {"pred": "eq", "a": "x15.n_eq", "b": "epd.declared_stages#"},
                {"pred": "eq", "a": "epd.declared_unit", "b": "x15.e.unit"},
                {"pred": "eq", "a": "epd.valid_until", "b": {"col": "valid_until", "via": "x15.e.ref"}},
                {"pred": "le", "a": {"col": "assessment_date", "of": "project"},
                 "b": {"col": "valid_until", "via": "x15.e.ref"}}]]},
            # (2) composite: A13-02 gave a factor and the quantity unit converts to kg
            {"use": "CONV", "as": "x15.k", "with": {"T": "materials", "from": "quantity_unit", "to": {"const": "kg"},
                                                   "extra": "materials.conversions"}},
            {"op": "sp", "table": "materials", "out": "x15.is_comp", "group": "none", "terms": [[
                {"pred": "eq", "a": "x15.is_epd", "b": {"const": 0}},
                {"pred": "present", "a": "composition#"},
                {"pred": "eq", "a": "a02.ok", "b": {"const": 1}},
                {"pred": "eq", "a": "x15.k.ok", "b": {"const": 1}}]]},
            # (3) generic factor
            {"use": "FACTOR", "as": "x15.g", "with": {"T": "materials", "fid": "factor_id", "gate": "stage.A13.is",
                                                     "unit": "quantity_unit", "extra": "materials.conversions"}},
            {"op": "sp", "table": "materials", "out": "x15.is_gen", "group": "none", "terms": [[
                {"pred": "eq", "a": "x15.is_epd", "b": {"const": 0}},
                {"pred": "present", "a": "composition#", "not": True},
                {"pred": "eq", "a": "x15.g.ok", "b": {"const": 1}}]]},
            {"op": "sp", "table": "materials", "out": "x15.resolved", "group": "none", "terms": [
                [{"pred": "eq", "a": "x15.is_epd", "b": {"const": 1}}],
                [{"pred": "eq", "a": "x15.is_comp", "b": {"const": 1}}],
                [{"pred": "eq", "a": "x15.is_gen", "b": {"const": 1}}]]},
            {"op": "sp", "table": "materials", "out": "x15.factor", "group": "none", "terms": [
                [{"pred": "eq", "a": "x15.is_epd", "b": {"const": 1}}, {"col": "value", "via": "x15.e.ref"}],
                [{"pred": "eq", "a": "x15.is_comp", "b": {"const": 1}}, "a02.value"],
                [{"pred": "eq", "a": "x15.is_gen", "b": {"const": 1}}, {"col": "value", "via": "x15.g.ref"}]]},
            {"op": "sp", "table": "materials", "out": "x15.conv", "group": "none", "terms": [
                [{"pred": "eq", "a": "x15.is_epd", "b": {"const": 1}}, "x15.e.c.f"],
                [{"pred": "eq", "a": "x15.is_comp", "b": {"const": 1}}, "x15.k.f"],
                [{"pred": "eq", "a": "x15.is_gen", "b": {"const": 1}}, "x15.g.c.f"]]},
            {"op": "sp", "table": "materials", "out": "x15.n_unresolved", "group": "total",
             "terms": [[{"pred": "eq", "a": "x15.resolved", "b": {"const": 0}}]]},
            {"op": "sp", "table": "materials", "out": "x15.n_epd_declined", "group": "total", "terms": [[
                {"pred": "present", "a": "epd#"},
                {"pred": "eq", "a": "x15.is_epd", "b": {"const": 0}}]]},
        ],
        "outputs": {
            "kind": {"read": "enum", "table": "materials",
                     "cases": [["EPD", "x15.is_epd"], ["COMPOSITE", "x15.is_comp"], ["GENERIC", "x15.is_gen"]]},
            "factor": {"read": "rows", "table": "materials", "col": "x15.factor", "where": "x15.resolved"},
            "conv": {"read": "rows", "table": "materials", "col": "x15.conv", "where": "x15.resolved"},
            "n_unresolved": {"read": "scalar", "col": "x15.n_unresolved", "as": "int"},
            "n_epd_declined": {"read": "scalar", "col": "x15.n_epd_declined", "as": "int"},
        },
    },
    {
        "id": "A13-01",
        "doc": "production emission of rows without product-specific declaration: ordered quantity * multiplier * factor",
        "steps": [
            {"op": "sp", "table": "materials", "out": "a01.ok", "group": "none", "terms": [[
                {"pred": "eq", "a": "x15.resolved", "b": {"const": 1}},
                {"pred": "eq", "a": "x15.is_epd", "b": {"const": 0}},
                {"pred": "eq", "a": "a05.ok", "b": {"const": 1}}]]},
            {"op": "sp", "table": "materials", "out": "a01.by_item", "group": "none", "terms": [[
                {"pred": "eq", "a": "a01.ok", "b": {"const": 1}}, "a05.q_ord", "x15.conv", "x15.factor"]]},
            {"op": "sp", "table": "materials", "out": "a01.value", "group": "total", "terms": [["a01.by_item"]]},
            {"op": "sp", "table": "materials", "out": "a01.n_skipped", "group": "total", "terms": [
                [{"pred": "eq", "a": "x15.resolved", "b": {"const": 0}}],
                [{"pred": "eq", "a": "x15.resolved", "b": {"const": 1}},
                 {"pred": "eq", "a": "x15.is_epd", "b": {"const": 0}},
                 {"pred": "eq", "a": "a05.ok", "b": {"const": 0}}]]},
        ],
        "outputs": {
            "value": {"read": "scalar", "col": "a01.value"},
            "by_item": {"read": "rows", "table": "materials", "col": "a01.by_item"},
            "n_skipped": {"read": "scalar", "col": "a01.n_skipped", "as": "int"},
        },
    },
    {
        "id": "A13-03",
        "doc": "production emission of rows with an applied product-specific declaration",
        "steps": [
            {"op": "sp", "table": "materials", "out": "a03.by_item", "group": "none", "terms": [[
                {"pred": "eq", "a": "x15.is_epd", "b": {"const": 1}},
                {"pred": "eq", "a": "a05.ok", "b": {"const": 1}}, "a05.q_ord", "x15.conv", "x15.factor"]]},
            {"op": "sp", "table": "materials", "out": "a03.value", "group": "total", "terms": [["a03.by_item"]]},
            {"op": "sp", "table": "materials", "out": "a03.n_skipped", "group": "total", "terms": [[
                {"pred": "eq", "a": "x15.is_epd", "b": {"const": 1}},
                {"pred": "eq", "a": "a05.ok", "b": {"const": 0}}]]},
        ],
        "outputs": {
            "value": {"read": "scalar", "col": "a03.value"},
            "by_item": {"read": "rows", "table": "materials", "col": "a03.by_item"},
            "n_skipped": {"read": "scalar", "col": "a03.n_skipped", "as": "int"},
        },
    },
    {
        "id": "A13-04",
        "doc": "add-on for unquantified scope: production emission of the row * r/(1-r), 0 < r < 1 "
               "(add-on designed in this study)",
        "steps": [
            {"op": "sp", "table": "materials", "out": "a04.in", "group": "none", "terms": [[
                {"pred": "range", "a": "unquantified_cost_ratio", "lo": 0, "hi": 1, "lo_open": True, "hi_open": True}]]},
            {"op": "sp", "table": "materials", "out": "a04.base", "group": "none",
             "terms": [["a01.by_item"], ["a03.by_item"]]},
            {"op": "sp", "table": "materials", "out": "a04.by_item", "group": "none", "terms": [[
                {"pred": "eq", "a": "a04.in", "b": {"const": 1}}, "a04.base",
                {"fn": "ratio_one_minus", "a": "unquantified_cost_ratio"}]]},
            {"op": "sp", "table": "materials", "out": "a04.value", "group": "total", "terms": [["a04.by_item"]]},
            {"op": "sp", "table": "materials", "out": "a04.n_skipped", "group": "total", "terms": [[
                {"pred": "present", "a": "unquantified_cost_ratio"},
                {"pred": "eq", "a": "unquantified_cost_ratio", "b": {"const": 0}, "not": True},
                {"pred": "eq", "a": "a04.in", "b": {"const": 0}}]]},
        ],
        "outputs": {
            "value": {"read": "scalar", "col": "a04.value"},
            "by_item": {"read": "rows", "table": "materials", "col": "a04.by_item"},
            "n_skipped": {"read": "scalar", "col": "a04.n_skipped", "as": "int"},
        },
    },
    {
        "id": "X-01",
        "doc": "initial production emission of equipment: quantity * multiplier * factor",
        "steps": [
            {"use": "FACTOR", "as": "x01.f", "with": {"T": "equipment", "fid": "factor_id", "gate": "stage.A13.is",
                                                     "unit": "quantity_unit", "extra": "_none"}},
            {"op": "sp", "table": "equipment", "out": "x01.ok", "group": "none", "terms": [[
                {"pred": "range", "a": "quantity", "lo": 0, "hi": "inf", "hi_open": True},
                {"pred": "eq", "a": "x01.f.ok", "b": {"const": 1}}]]},
            {"op": "sp", "table": "equipment", "out": "x01.by_item", "group": "none", "terms": [[
                {"pred": "eq", "a": "x01.ok", "b": {"const": 1}}, "quantity", "x01.f.c.f",
                {"col": "value", "via": "x01.f.ref"}]]},
            {"op": "sp", "table": "equipment", "out": "x01.value", "group": "total", "terms": [["x01.by_item"]]},
            {"op": "sp", "table": "equipment", "out": "x01.n_skipped", "group": "total",
             "terms": [[{"pred": "eq", "a": "x01.ok", "b": {"const": 0}}]]},
        ],
        "outputs": {
            "value": {"read": "scalar", "col": "x01.value"},
            "by_item": {"read": "rows", "table": "equipment", "col": "x01.by_item"},
            "n_skipped": {"read": "scalar", "col": "x01.n_skipped", "as": "int"},
        },
    },
    {
        "id": "X-03",
        "doc": "expansion of composite rows into components: mass and emission per component factor",
        "steps": [
            {"op": "sp", "table": "materials.composition", "out": "x03.act", "group": "none", "terms": [[
                {"pred": "eq", "a": {"col": "x15.is_comp", "via": "_parent"}, "b": {"const": 1}},
                {"pred": "eq", "a": {"col": "a05.ok", "via": "_parent"}, "b": {"const": 1}}]]},
            {"op": "sp", "table": "materials.composition", "out": "x03.m", "group": "none", "terms": [[
                {"pred": "eq", "a": "x03.act", "b": {"const": 1}},
                {"col": "a05.q_ord", "via": "_parent"}, {"col": "x15.conv", "via": "_parent"}, "mass_fraction"]]},
            {"op": "sp", "table": "materials.composition", "out": "x03.e", "group": "none", "terms": [[
                {"pred": "eq", "a": "x03.act", "b": {"const": 1}}, "x03.m", "a02.c.c.f",
                {"col": "value", "via": "a02.c.ref"}]]},
            {"op": "sp", "table": "materials.composition", "out": "x03.value", "group": "total", "terms": [["x03.e"]]},
            {"op": "sp", "table": "materials.composition", "out": "x03.mass", "group": {"by": "a02.c.ref"},
             "terms": [[{"pred": "eq", "a": "x03.act", "b": {"const": 1}}, "x03.m"]]},
            {"op": "sp", "table": "materials.composition", "out": "x03.emission", "group": {"by": "a02.c.ref"},
             "terms": [[{"pred": "eq", "a": "x03.act", "b": {"const": 1}}, "x03.e"]]},
            {"op": "sp", "table": "materials.composition", "out": "x03.n", "group": {"by": "a02.c.ref"},
             "terms": [[{"pred": "eq", "a": "x03.act", "b": {"const": 1}}]]},
        ],
        "outputs": {
            "value": {"read": "scalar", "col": "x03.value"},
            "mass_by_component": {"read": "dict", "table": "factors", "key": "key", "col": "x03.mass", "where": "x03.n"},
            "emission_by_component": {"read": "dict", "table": "factors", "key": "key", "col": "x03.emission",
                                      "where": "x03.n"},
        },
    },
    {
        "id": "A4-01",
        "doc": "transport by mass and distance for rows without a per-quantity delivery factor",
        "steps": [
            {"use": "FACTOR", "as": "a41.f", "with": {"T": "materials", "fid": "transport.factor_id", "gate": "stage.A4.is",
                                                     "unit": {"const": "tkm"}, "extra": "_none"}},
            {"op": "sp", "table": "materials", "out": "a41.ok", "group": "none", "terms": [[
                {"pred": "present", "a": "transport.delivery_factor_id", "not": True},
                {"pred": "eq", "a": "a41.f.ok", "b": {"const": 1}},
                {"pred": "range", "a": "transport.mass_t", "lo": 0, "hi": "inf", "hi_open": True},
                {"pred": "range", "a": "transport.distance_km", "lo": 0, "hi": "inf", "hi_open": True}]]},
            {"op": "sp", "table": "materials", "out": "a41.by_item", "group": "none", "terms": [[
                {"pred": "eq", "a": "a41.ok", "b": {"const": 1}}, "transport.mass_t", "transport.distance_km",
                "a41.f.c.f", {"col": "value", "via": "a41.f.ref"}]]},
            {"op": "sp", "table": "materials", "out": "a41.value", "group": "total", "terms": [["a41.by_item"]]},
            {"op": "sp", "table": "materials", "out": "a41.n_skipped", "group": "total", "terms": [[
                {"pred": "present", "a": "transport.delivery_factor_id", "not": True},
                {"pred": "eq", "a": "a41.ok", "b": {"const": 0}}]]},
        ],
        "outputs": {
            "value": {"read": "scalar", "col": "a41.value"},
            "by_item": {"read": "rows", "table": "materials", "col": "a41.by_item"},
            "n_skipped": {"read": "scalar", "col": "a41.n_skipped", "as": "int"},
        },
    },
    {
        "id": "X-12",
        "doc": "transport by mass and distance divided by the load factor (alternative to A4-01)",
        "steps": [
            {"use": "FACTOR", "as": "x12.f", "with": {"T": "materials", "fid": "transport.factor_id", "gate": "stage.A4.is",
                                                     "unit": {"const": "tkm"}, "extra": "_none"}},
            {"op": "sp", "table": "materials", "out": "x12.ok", "group": "none", "terms": [[
                {"pred": "present", "a": "transport.delivery_factor_id", "not": True},
                {"pred": "eq", "a": "x12.f.ok", "b": {"const": 1}},
                {"pred": "range", "a": "transport.mass_t", "lo": 0, "hi": "inf", "hi_open": True},
                {"pred": "range", "a": "transport.distance_km", "lo": 0, "hi": "inf", "hi_open": True},
                {"pred": "range", "a": "transport.load_factor", "lo": 0, "hi": "inf", "lo_open": True}]]},
            {"op": "sp", "table": "materials", "out": "x12.by_item", "group": "none", "terms": [[
                {"pred": "eq", "a": "x12.ok", "b": {"const": 1}}, "transport.mass_t", "transport.distance_km",
                "x12.f.c.f", {"fn": "inv", "a": "transport.load_factor"}, {"col": "value", "via": "x12.f.ref"}]]},
            {"op": "sp", "table": "materials", "out": "x12.value", "group": "total", "terms": [["x12.by_item"]]},
            {"op": "sp", "table": "materials", "out": "x12.n_skipped", "group": "total", "terms": [[
                {"pred": "present", "a": "transport.delivery_factor_id", "not": True},
                {"pred": "eq", "a": "x12.ok", "b": {"const": 0}}]]},
        ],
        "outputs": {
            "value": {"read": "scalar", "col": "x12.value"},
            "by_item": {"read": "rows", "table": "materials", "col": "x12.by_item"},
            "n_skipped": {"read": "scalar", "col": "x12.n_skipped", "as": "int"},
        },
    },
    {
        "id": "A4-02",
        "doc": "transport by a per-quantity delivery factor: ordered quantity * multiplier * factor",
        "steps": [
            {"use": "FACTOR", "as": "a42.f", "with": {"T": "materials", "fid": "transport.delivery_factor_id",
                                                     "gate": "stage.A4.is", "unit": "quantity_unit",
                                                     "extra": "materials.conversions"}},
            {"op": "sp", "table": "materials", "out": "a42.ok", "group": "none", "terms": [[
                {"pred": "present", "a": "transport.delivery_factor_id"},
                {"pred": "eq", "a": "a42.f.ok", "b": {"const": 1}},
                {"pred": "eq", "a": "a05.ok", "b": {"const": 1}}]]},
            {"op": "sp", "table": "materials", "out": "a42.by_item", "group": "none", "terms": [[
                {"pred": "eq", "a": "a42.ok", "b": {"const": 1}}, "a05.q_ord", "a42.f.c.f",
                {"col": "value", "via": "a42.f.ref"}]]},
            {"op": "sp", "table": "materials", "out": "a42.value", "group": "total", "terms": [["a42.by_item"]]},
            {"op": "sp", "table": "materials", "out": "a42.n_skipped", "group": "total", "terms": [[
                {"pred": "present", "a": "transport.delivery_factor_id"},
                {"pred": "eq", "a": "a42.ok", "b": {"const": 0}}]]},
        ],
        "outputs": {
            "value": {"read": "scalar", "col": "a42.value"},
            "by_item": {"read": "rows", "table": "materials", "col": "a42.by_item"},
            "n_skipped": {"read": "scalar", "col": "a42.n_skipped", "as": "int"},
        },
    },
    {
        "id": "A5-01",
        "doc": "site electricity: purchased kWh * multiplier * grid factor of the construction period. The "
               "electricity unit of the grid factor is recognised from a closed list of three unit texts "
               "(the reference splits the text at '/'; a text split is not in the vocabulary)",
        "steps": [
            {"op": "match", "table": "operation", "out": "a51.r_mwh", "keys": [{"const": "kWh"}, {"const": "MWh"}],
             "into": "unit_conversions", "on": ["from_unit", "to_unit"]},
            {"op": "match", "table": "operation", "out": "a51.r_mj", "keys": [{"const": "kWh"}, {"const": "MJ"}],
             "into": "unit_conversions", "on": ["from_unit", "to_unit"]},
            {"op": "sp", "table": "operation", "out": "a51.conv_ok", "group": "none", "terms": [
                [{"pred": "eq", "a": "grid.unit", "b": {"const": "kgCO2e/kWh"}}],
                [{"pred": "eq", "a": "grid.unit", "b": {"const": "kgCO2e/MWh"}}, {"pred": "present", "a": "a51.r_mwh"}],
                [{"pred": "eq", "a": "grid.unit", "b": {"const": "kgCO2e/MJ"}}, {"pred": "present", "a": "a51.r_mj"}]]},
            {"op": "sp", "table": "operation", "out": "a51.conv", "group": "none", "terms": [
                [{"pred": "eq", "a": "grid.unit", "b": {"const": "kgCO2e/kWh"}}],
                [{"pred": "eq", "a": "grid.unit", "b": {"const": "kgCO2e/MWh"}}, {"pred": "present", "a": "a51.r_mwh"},
                 {"col": "factor", "via": "a51.r_mwh"}],
                [{"pred": "eq", "a": "grid.unit", "b": {"const": "kgCO2e/MJ"}}, {"pred": "present", "a": "a51.r_mj"},
                 {"col": "factor", "via": "a51.r_mj"}]]},
            {"op": "sp", "table": "operation", "out": "a51.ok", "group": "none", "terms": [[
                {"pred": "range", "a": {"col": "electricity_kwh", "of": "construction"}, "lo": 0, "hi": "inf", "hi_open": True},
                {"pred": "eq", "a": "a51.conv_ok", "b": {"const": 1}},
                {"pred": "eq", "a": "grid.licence_status", "b": {"const": "PERMITTED_PUBLIC"}}]]},
            {"op": "sp", "table": "operation", "out": "a51.value", "group": "total", "terms": [[
                {"pred": "eq", "a": "a51.ok", "b": {"const": 1}}, {"col": "electricity_kwh", "of": "construction"},
                "a51.conv", "grid.construction_value"]]},
        ],
        "outputs": {
            "value": {"read": "scalar", "col": "a51.value"},
            "computed": {"read": "scalar", "table": "operation", "col": "a51.ok", "as": "bool"},
        },
    },
    {
        "id": "A5-02",
        "doc": "site fuels: quantity * multiplier * factor per fuel",
        "steps": [
            {"use": "FACTOR", "as": "a52.f", "with": {"T": "construction.fuels", "fid": "factor_id", "gate": "stage.A5.is",
                                                     "unit": "unit", "extra": "construction.fuels.conversions"}},
            {"op": "sp", "table": "construction.fuels", "out": "a52.ok", "group": "none", "terms": [[
                {"pred": "range", "a": "quantity", "lo": 0, "hi": "inf", "hi_open": True},
                {"pred": "eq", "a": "a52.f.ok", "b": {"const": 1}}]]},
            {"op": "sp", "table": "construction.fuels", "out": "a52.value", "group": "total", "terms": [[
                {"pred": "eq", "a": "a52.ok", "b": {"const": 1}}, "quantity", "a52.f.c.f",
                {"col": "value", "via": "a52.f.ref"}]]},
            {"op": "sp", "table": "construction.fuels", "out": "a52.n_skipped", "group": "total",
             "terms": [[{"pred": "eq", "a": "a52.ok", "b": {"const": 0}}]]},
        ],
        "outputs": {
            "value": {"read": "scalar", "col": "a52.value"},
            "n_skipped": {"read": "scalar", "col": "a52.n_skipped", "as": "int"},
        },
    },
    {
        "id": "A5-03",
        "doc": "site waste: mass in kg * multiplier * treatment factor per stream",
        "steps": [
            {"use": "FACTOR", "as": "a53.f", "with": {"T": "construction.waste_streams", "fid": "factor_id",
                                                     "gate": "stage.A5.is", "unit": {"const": "kg"}, "extra": "_none"}},
            {"op": "sp", "table": "construction.waste_streams", "out": "a53.ok", "group": "none", "terms": [[
                {"pred": "range", "a": "mass_kg", "lo": 0, "hi": "inf", "hi_open": True},
                {"pred": "eq", "a": "a53.f.ok", "b": {"const": 1}}]]},
            {"op": "sp", "table": "construction.waste_streams", "out": "a53.value", "group": "total", "terms": [[
                {"pred": "eq", "a": "a53.ok", "b": {"const": 1}}, "mass_kg", "a53.f.c.f",
                {"col": "value", "via": "a53.f.ref"}]]},
            {"op": "sp", "table": "construction.waste_streams", "out": "a53.n_skipped", "group": "total",
             "terms": [[{"pred": "eq", "a": "a53.ok", "b": {"const": 0}}]]},
        ],
        "outputs": {
            "value": {"read": "scalar", "col": "a53.value"},
            "n_skipped": {"read": "scalar", "col": "a53.n_skipped", "as": "int"},
        },
    },
    {
        "id": "A5-04",
        "doc": "site total: electricity + fuels + waste; other site emissions are not assessed (constant flag)",
        "steps": [
            {"op": "sp", "table": "S", "out": "a54.value", "group": "none",
             "terms": [["a51.value"], ["a52.value"], ["a53.value"]]},
        ],
        "outputs": {
            "value": {"read": "scalar", "col": "a54.value"},
            "parts": {"read": "record", "fields": {
                "power": {"read": "scalar", "col": "a51.value"},
                "fuels": {"read": "scalar", "col": "a52.value"},
                "waste": {"read": "scalar", "col": "a53.value"}}},
            "other_assessed": {"read": "const", "value": False},
        },
    },
    {
        "id": "X-17",
        "doc": "simplified estimate by six summary classes: summary quantity * (class emission / summary quantity)",
        "steps": [
            {"use": "CLASS", "as": "x17.REBAR", "with": {"q": "reinforcement_kg", "terms": [
                [{"pred": "eq", "a": "material_class", "b": {"const": "REBAR"}}]]}},
            {"use": "CLASS", "as": "x17.STRUCTURAL_STEEL", "with": {"q": "steel_kg", "terms": [
                [{"pred": "eq", "a": "material_class", "b": {"const": "STRUCTURAL_STEEL"}}]]}},
            {"use": "CLASS", "as": "x17.CONCRETE", "with": {"q": "concrete_m3", "terms": [
                [{"pred": "eq", "a": "material_class", "b": {"const": "CONCRETE"}}]]}},
            {"use": "CLASS", "as": "x17.TIMBER", "with": {"q": "timber_m3", "terms": [
                [{"pred": "eq", "a": "material_class", "b": {"const": "TIMBER"}}]]}},
            {"use": "CLASS", "as": "x17.ENVELOPE", "with": {"q": "envelope_m2", "terms": [
                [{"pred": "eq", "a": "material_class", "b": {"const": "REBAR"}, "not": True},
                 {"pred": "eq", "a": "material_class", "b": {"const": "STRUCTURAL_STEEL"}, "not": True},
                 {"pred": "eq", "a": "material_class", "b": {"const": "CONCRETE"}, "not": True},
                 {"pred": "eq", "a": "material_class", "b": {"const": "TIMBER"}, "not": True},
                 {"pred": "eq", "a": "quantity_unit", "b": {"const": "m2"}},
                 {"pred": "eq", "a": "construction_division", "b": {"const": "ROOF_EXTERIOR_WALL"}}],
                [{"pred": "eq", "a": "material_class", "b": {"const": "REBAR"}, "not": True},
                 {"pred": "eq", "a": "material_class", "b": {"const": "STRUCTURAL_STEEL"}, "not": True},
                 {"pred": "eq", "a": "material_class", "b": {"const": "CONCRETE"}, "not": True},
                 {"pred": "eq", "a": "material_class", "b": {"const": "TIMBER"}, "not": True},
                 {"pred": "eq", "a": "quantity_unit", "b": {"const": "m2"}},
                 {"pred": "eq", "a": "construction_division", "b": {"const": "OPENINGS"}}]]}},
            {"use": "CLASS", "as": "x17.INTERIOR", "with": {"q": "interior_m2", "terms": [
                [{"pred": "eq", "a": "material_class", "b": {"const": "REBAR"}, "not": True},
                 {"pred": "eq", "a": "material_class", "b": {"const": "STRUCTURAL_STEEL"}, "not": True},
                 {"pred": "eq", "a": "material_class", "b": {"const": "CONCRETE"}, "not": True},
                 {"pred": "eq", "a": "material_class", "b": {"const": "TIMBER"}, "not": True},
                 {"pred": "eq", "a": "quantity_unit", "b": {"const": "m2"}},
                 {"pred": "eq", "a": "construction_division", "b": {"const": "INTERIOR"}}]]}},
            {"op": "sp", "table": "S", "out": "x17.value", "group": "none", "terms": [
                ["x17.REBAR.e"], ["x17.STRUCTURAL_STEEL.e"], ["x17.CONCRETE.e"], ["x17.TIMBER.e"],
                ["x17.ENVELOPE.e"], ["x17.INTERIOR.e"]]},
        ],
        "outputs": {
            "value": {"read": "scalar", "col": "x17.value"},
            "by_class": {"read": "record", "fields": {
                "REBAR": {"read": "record", "fields": {
                    "quantity": {"read": "scalar", "table": "summary_quantities", "col": "reinforcement_kg"},
                    "fbar": {"read": "scalar", "col": "x17.REBAR.fbar"},
                    "emission": {"read": "scalar", "col": "x17.REBAR.e"}}},
                "STRUCTURAL_STEEL": {"read": "record", "fields": {
                    "quantity": {"read": "scalar", "table": "summary_quantities", "col": "steel_kg"},
                    "fbar": {"read": "scalar", "col": "x17.STRUCTURAL_STEEL.fbar"},
                    "emission": {"read": "scalar", "col": "x17.STRUCTURAL_STEEL.e"}}},
                "CONCRETE": {"read": "record", "fields": {
                    "quantity": {"read": "scalar", "table": "summary_quantities", "col": "concrete_m3"},
                    "fbar": {"read": "scalar", "col": "x17.CONCRETE.fbar"},
                    "emission": {"read": "scalar", "col": "x17.CONCRETE.e"}}},
                "TIMBER": {"read": "record", "fields": {
                    "quantity": {"read": "scalar", "table": "summary_quantities", "col": "timber_m3"},
                    "fbar": {"read": "scalar", "col": "x17.TIMBER.fbar"},
                    "emission": {"read": "scalar", "col": "x17.TIMBER.e"}}},
                "ENVELOPE": {"read": "record", "fields": {
                    "quantity": {"read": "scalar", "table": "summary_quantities", "col": "envelope_m2"},
                    "fbar": {"read": "scalar", "col": "x17.ENVELOPE.fbar"},
                    "emission": {"read": "scalar", "col": "x17.ENVELOPE.e"}}},
                "INTERIOR": {"read": "record", "fields": {
                    "quantity": {"read": "scalar", "table": "summary_quantities", "col": "interior_m2"},
                    "fbar": {"read": "scalar", "col": "x17.INTERIOR.fbar"},
                    "emission": {"read": "scalar", "col": "x17.INTERIOR.e"}}}}},
        },
    },
    {
        "id": "X-16",
        "doc": "cost-based estimate with price correction: amount * (index of the factor base year / index of the "
               "cost year) * multiplier * factor per currency unit",
        "steps": [
            {"op": "match", "table": "cost_items", "out": "x16.pc", "keys": ["price_year"], "into": "price_index", "on": ["key"]},
            {"op": "match", "table": "cost_items", "out": "x16.pb", "keys": ["factor_base_year"], "into": "price_index",
             "on": ["key"]},
            {"use": "FACTOR", "as": "x16.f", "with": {"T": "cost_items", "fid": "factor_id", "gate": "stage.A13.is",
                                                     "unit": "currency", "extra": "_none"}},
            {"op": "sp", "table": "cost_items", "out": "x16.ok", "group": "none", "terms": [[
                {"pred": "range", "a": "amount", "lo": 0, "hi": "inf", "hi_open": True},
                {"pred": "eq", "a": "x16.f.ok", "b": {"const": 1}},
                {"pred": "range", "a": {"col": "value", "via": "x16.pc"}, "lo": 0, "hi": "inf", "lo_open": True},
                {"pred": "range", "a": {"col": "value", "via": "x16.pb"}, "lo": 0, "hi": "inf", "lo_open": True}]]},
            {"op": "sp", "table": "cost_items", "out": "x16.by_item", "group": "none", "terms": [[
                {"pred": "eq", "a": "x16.ok", "b": {"const": 1}}, "amount", {"col": "value", "via": "x16.pb"},
                {"fn": "inv", "a": {"col": "value", "via": "x16.pc"}}, "x16.f.c.f", {"col": "value", "via": "x16.f.ref"}]]},
            {"op": "sp", "table": "cost_items", "out": "x16.value", "group": "total", "terms": [["x16.by_item"]]},
            {"op": "sp", "table": "cost_items", "out": "x16.n_skipped", "group": "total",
             "terms": [[{"pred": "eq", "a": "x16.ok", "b": {"const": 0}}]]},
        ],
        "outputs": {
            "value": {"read": "scalar", "col": "x16.value"},
            "by_item": {"read": "rows", "table": "cost_items", "col": "x16.by_item"},
            "n_skipped": {"read": "scalar", "col": "x16.n_skipped", "as": "int"},
        },
    },
]

SPEC = {
    "name": "pre_a",
    "data_statement": "fictional data, independent concept model",
    "templates": TEMPLATES,
    "shared": SHARED,
    "units": UNITS,
}
