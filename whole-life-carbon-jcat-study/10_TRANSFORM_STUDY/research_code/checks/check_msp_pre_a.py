"""Exactness, membership (fault injection) and vocabulary record of the masked sum-product
specification ``specs/pre_a.py`` (candidate TC-B-01, 18 units of the product, transport and
construction stages) against the frozen reference calculation.

Run from ``research_code``:  PYTHONDONTWRITEBYTECODE=1 python3 -B -m checks.check_msp_pre_a

Fictional data, independent concept model. Evidence level of everything measured here: N (numerical),
checked by the implementer only. Writes two JSON files into ``03_ROUTES/TC-B-01/``.
"""
import ast
import copy
import json
import math
import os
import sys
import time

sys.dont_write_bytecode = True

from specs import pre_a
from tstudy import baseline, msp, scenarios, tables

TOL = 1e-9
FAULT_SCALE = 1.0001
N_DESIGN = 60
N_EVALUATION = 60
N_DIRTY = 20
DIRTY_SEED = 730001
PROBE_SEED = 740001
HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.normpath(os.path.join(HERE, "..", "..", "03_ROUTES", "TC-B-01"))
SPEC_FILE = os.path.normpath(os.path.join(HERE, "..", "specs", "pre_a.py"))
ENGINE_FILES = [os.path.normpath(os.path.join(HERE, "..", "tstudy", name)) for name in ("msp.py", "tables.py")]


# ---------------------------------------------------------------------------------------------
# Comparison (never weakened: relative 1e-9 for numbers, exact for everything else)
# ---------------------------------------------------------------------------------------------

class Acc:
    """Comparison counters of one (unit, output key, set)."""

    FIELDS = ("n_float", "n_float_mismatch", "n_bit_identical", "n_ref_zero", "n_ref_zero_mismatch", "n_exact",
              "n_exact_mismatch", "n_none", "n_struct_mismatch", "sum_ref_int")

    def __init__(self):
        for f in self.FIELDS:
            setattr(self, f, 0)
        self.max_rel = 0.0
        self.max_abs_ref_zero = 0.0
        self.worst = None
        self.examples = []

    def note(self, sid, path, got, want, why):
        if len(self.examples) < 3:
            self.examples.append({"scenario": sid, "path": path, "engine": repr(got)[:60], "reference": repr(want)[:60],
                                  "why": why})

    @property
    def n_compared(self):
        return self.n_float + self.n_ref_zero + self.n_exact

    @property
    def n_mismatch(self):
        return self.n_float_mismatch + self.n_ref_zero_mismatch + self.n_exact_mismatch + self.n_struct_mismatch

    def as_dict(self):
        d = {f: getattr(self, f) for f in self.FIELDS}
        d.update(n_compared=self.n_compared, n_mismatch=self.n_mismatch, max_rel=self.max_rel,
                 max_abs_ref_zero=self.max_abs_ref_zero, worst=self.worst, examples=self.examples)
        return d


def compare(got, want, path, acc: Acc, sid: str) -> None:
    """Compare an engine output with the reference output, leaf by leaf."""
    if isinstance(want, dict):
        if not isinstance(got, dict):
            acc.n_struct_mismatch += 1
            acc.note(sid, path, got, "dict", "not a dictionary")
            return
        for k in sorted(set(want) ^ set(got), key=str):
            acc.n_struct_mismatch += 1
            acc.note(sid, f"{path}/{k}", k in got, k in want, "key on one side only")
        for k in want:
            if k in got:
                compare(got[k], want[k], f"{path}/{k}", acc, sid)
    elif isinstance(want, (list, tuple)):
        if not isinstance(got, list) or len(got) != len(want):
            acc.n_struct_mismatch += 1
            acc.note(sid, path, type(got).__name__, len(want), "not a list of the same length")
            return
        for i, (g, w) in enumerate(zip(got, want)):
            compare(g, w, f"{path}[{i}]", acc, sid)
    elif want is None or isinstance(want, (bool, str, int)):
        acc.n_exact += 1
        if want is None:
            acc.n_none += 1
        elif isinstance(want, int) and not isinstance(want, bool):
            acc.sum_ref_int += want
        if type(got) is not type(want) or got != want:
            acc.n_exact_mismatch += 1
            acc.note(sid, path, got, want, "exact comparison failed")
    elif isinstance(want, float):
        if math.isnan(want) or math.isinf(want):
            acc.n_exact += 1
            if not (isinstance(got, float) and (got == want or (math.isnan(got) and math.isnan(want)))):
                acc.n_exact_mismatch += 1
                acc.note(sid, path, got, want, "non-finite reference")
        elif want == 0.0:
            acc.n_ref_zero += 1
            if type(got) is not float or math.isnan(got):
                acc.n_ref_zero_mismatch += 1
                acc.note(sid, path, got, want, "not a number")
            else:
                acc.max_abs_ref_zero = max(acc.max_abs_ref_zero, abs(got))
                if got != 0.0:
                    acc.n_ref_zero_mismatch += 1
                    acc.note(sid, path, got, want, "reference is zero")
        else:
            acc.n_float += 1
            if type(got) is not float or math.isnan(got):
                acc.n_float_mismatch += 1
                acc.note(sid, path, got, want, "not a number")
                return
            rel = abs(got - want) / abs(want)
            if got == want:
                acc.n_bit_identical += 1
            if rel > acc.max_rel:
                acc.max_rel = rel
                acc.worst = {"scenario": sid, "path": path, "rel": rel}
            if rel > TOL:
                acc.n_float_mismatch += 1
                acc.note(sid, path, got, want, f"relative difference {rel:.3e}")
    else:
        acc.n_struct_mismatch += 1
        acc.note(sid, path, got, want, f"unexpected reference type {type(want).__name__}")


def public(d: dict) -> dict:
    return {k: v for k, v in d.items() if not k.startswith("_")}


# ---------------------------------------------------------------------------------------------
# Scenario sets
# ---------------------------------------------------------------------------------------------

def dirty_set():
    baseline.load()
    from synth import generate, model

    out = []
    for i in range(N_DIRTY):
        out.append(generate.make_scenario(DIRTY_SEED + i, model.STRUCTURES[i % 4], model.USES[i % 6], "S", dirty=True))
    return out


def probe_set():
    """Targeted mutations of one clean scenario (written by the implementer): branches the generator sets
    do not reach. ``expect`` says what the implementer expects BEFORE running: "match" or "mismatch"."""
    baseline.load()
    from synth import generate, model

    UC = model.UnitConversion
    base = generate.make_scenario(PROBE_SEED, "RC", "office", "S", 60.0, n_materials=72, n_equipment=12, n_refrigerants=4,
                                  epd_share=0.4, epd_inapplicable_share=0.3, composite_share=0.3,
                                  scenario_id="PROBE-base")
    probes = []

    def probe(name, expect="match", note=""):
        def deco(fn):
            scn = copy.deepcopy(base)
            fn(scn)
            scn.meta.scenario_id = "PROBE-" + name
            probes.append({"name": name, "expect": expect, "note": note, "scenario": scn})
            return fn
        return deco

    def grid_unit(text, expect="match", note=""):
        def mutate(s):
            s.operation.grid.unit = text
        probe("grid_unit_" + text.replace("/", "_per_"), expect, note)(mutate)

    probe("base")(lambda s: None)
    grid_unit("kgCO2e/MWh")
    grid_unit("kgCO2e/MJ")
    grid_unit("kgCO2e/GJ", note="no direct conversion kWh->GJ: not computed on both sides")
    grid_unit("gCO2e/kWh")
    grid_unit("kWh")
    grid_unit("kgCO2e/kWh/year")
    grid_unit("kgCO2e/")

    @probe("grid_unit_GJ_with_registered_conversion", "mismatch",
           "the scenario registers kWh->GJ; the reference splits the unit text and finds it, the closed list of "
           "the specification (kWh, MWh, MJ) does not")
    def _(s):
        s.unit_conversions.append(UC("kWh", "GJ", 0.0036, "PROBE"))
        s.operation.grid.unit = "kgCO2e/GJ"

    @probe("grid_licence_unknown")
    def _(s):
        s.operation.grid.licence_status = "UNKNOWN"

    for label, value in (("missing", None), ("negative", -1.0), ("infinite", math.inf), ("nan", math.nan), ("zero", 0.0)):
        def mutate(s, value=value):
            s.construction.electricity_kwh = value
        probe("site_electricity_" + label)(mutate)

    @probe("load_factor_variants")
    def _(s):
        for i, row in enumerate(s.materials):
            row.transport.load_factor = (0.0, None, math.inf, -0.5, 0.25, math.nan)[i % 6]

    @probe("unquantified_ratio_variants")
    def _(s):
        for i, row in enumerate(s.materials):
            row.unquantified_cost_ratio = (None, 0.0, -0.1, 1.0, 1.5, 0.5, math.nan, 0.999)[i % 8]

    @probe("price_index_variants")
    def _(s):
        years = sorted({y for item in s.cost_items for y in (item.price_year, item.factor_base_year)})
        for j, y in enumerate(years):
            if j % 5 == 0:
                s.price_index.pop(y, None)
            elif j % 5 == 1:
                s.price_index[y] = 0.0
            elif j % 5 == 2:
                s.price_index[y] = None
            elif j % 5 == 3:
                s.price_index[y] = -5.0

    @probe("cost_item_variants")
    def _(s):
        for j, item in enumerate(s.cost_items):
            if j % 6 == 0:
                item.amount = None
            elif j % 6 == 1:
                item.amount = -1.0
            elif j % 6 == 2:
                item.factor_id = None
            elif j % 6 == 3:
                item.factor_id = "F-NO-SUCH-RECORD"
            elif j % 6 == 4:
                item.currency = "XYZ"
            else:
                item.amount = math.nan

    @probe("cost_tables_empty")
    def _(s):
        s.cost_items = []
        s.price_index = {}

    @probe("epd_declaration_variants")
    def _(s):
        j = 0
        for row in s.materials:
            if row.epd is None:
                continue
            rec = s.factors.get(row.epd.factor_id)
            k = j % 9
            j += 1
            if k == 0:
                row.epd.declared_unit = "piece"
            elif k == 1:
                row.epd.declared_stages = ["A1-A3", "A4"]
            elif k == 2:
                row.epd.declared_stages = []
            elif k == 3:
                row.epd.valid_until = "1999-01-01"
            elif k == 4 and rec is not None:
                rec.valid_until = "2000-01-01"
                row.epd.valid_until = "2000-01-01"
            elif k == 5:
                row.epd.factor_id = "F-NO-SUCH-RECORD"
            elif k == 6:
                row.epd.factor_id = None
            elif k == 7 and rec is not None:
                rec.valid_until = None
                row.epd.valid_until = None
            elif k == 8 and rec is not None:
                rec.valid_until = s.project.assessment_date
                row.epd.valid_until = s.project.assessment_date

    @probe("epd_on_composite_rows", note="priority: the declaration is tried before the composite factor")
    def _(s):
        donors = [row.epd for row in s.materials if row.epd is not None]
        j = 0
        for row in s.materials:
            if row.composition is not None and donors:
                row.epd = copy.deepcopy(donors[j % len(donors)])
                j += 1

    @probe("row_conversions_shadowing", note="first row-specific entry wins; identity wins over any entry")
    def _(s):
        for i, row in enumerate(s.materials):
            if row.conversions and i % 3 == 0:
                c = row.conversions[0]
                row.conversions.insert(0, UC(c.from_unit, c.to_unit, c.factor * 2.0, "PROBE"))
            elif i % 3 == 1:
                row.conversions.insert(0, UC(row.quantity_unit, row.quantity_unit, 5.0, "PROBE"))
            elif row.factor_id is not None and s.factors[row.factor_id].unit != row.quantity_unit:
                row.conversions.insert(0, UC(row.quantity_unit, s.factors[row.factor_id].unit, 7.0, "PROBE"))
                row.conversions.append(UC(row.quantity_unit, s.factors[row.factor_id].unit, 9.0, "PROBE"))

    @probe("scenario_conversions_duplicates", note="first entry of the scenario table wins")
    def _(s):
        s.unit_conversions.append(UC("t", "kg", 999.0, "PROBE"))
        s.unit_conversions.insert(0, UC("kg", "t", 0.5, "PROBE"))
        s.unit_conversions.insert(0, UC("kWh", "kWh", 3.0, "PROBE"))
        for j, fid in enumerate(sorted(s.factors)):
            if s.factors[fid].unit == "kg" and j % 3 == 0:
                s.factors[fid].unit = "t"

    @probe("factor_stage_list_variants")
    def _(s):
        used = sorted({row.factor_id for row in s.materials if row.factor_id is not None}
                      | {c.factor_id for row in s.materials if row.composition for c in row.composition}
                      | {row.transport.factor_id for row in s.materials if row.transport.factor_id is not None})
        for j, fid in enumerate(used):
            rec = s.factors[fid]
            k = j % 7
            if k == 0:
                rec.stages = rec.stages + rec.stages
            elif k == 1:
                rec.stages = []
            elif k == 2:
                rec.stages = ["A4"] if rec.stages != ["A4"] else ["A1-A3"]
            elif k == 3:
                rec.stages = ["A1-A3", "A4"]
            elif k == 4:
                rec.stages = ["A4", "A1-A3"]

    @probe("reuse_rate_variants")
    def _(s):
        for i, row in enumerate(s.materials):
            row.reuse_rate = (None, -0.1, 1.5, 1.0, 0.0, math.nan, 0.3)[i % 7]

    @probe("waste_rate_variants")
    def _(s):
        for i, row in enumerate(s.materials):
            row.waste_rate = (1.0, 1.2, -0.01, 0.0, math.nan, None, 0.999999, 0.05)[i % 8]

    @probe("tiny_waste_rates", "mismatch",
           "X-13 waste_by_item on rows with basis DESIGN: ordered - installed cancels to about Q*w, so the one-bit "
           "difference between Q*(1/(1-w)) (engine) and Q/(1-w) (reference) is amplified by about 1/w; "
           "expected above 1e-9 for w <= 1e-8")
    def _(s):
        for i, row in enumerate(s.materials):
            row.waste_rate = (1e-6, 1e-8, 1e-10, 1e-12)[i % 4]
            row.quantity_basis = "DESIGN"

    @probe("quantity_variants")
    def _(s):
        for i, row in enumerate(s.materials):
            if i % 6 < 5:
                row.quantity = (None, -1.0, math.inf, math.nan, 0.0)[i % 6]
        for i, eq in enumerate(s.equipment):
            if i % 6 < 5:
                eq.quantity = (None, -1.0, math.inf, math.nan, 0.0)[i % 6]

    @probe("integer_quantities", "mismatch",
           "the reference passes an integer input through unchanged (type int); the engine holds every number "
           "as a float, so equal values differ in type")
    def _(s):
        for i, row in enumerate(s.materials):
            if i % 2 == 0 and row.quantity is not None:
                row.quantity = int(round(row.quantity))

    @probe("composition_variants")
    def _(s):
        j = 0
        for row in s.materials:
            if row.composition is None:
                continue
            k = j % 9
            j += 1
            comp = row.composition[0] if row.composition else None
            if k == 0:
                row.composition = []
            elif k == 1:
                comp.mass_fraction = -0.1
            elif k == 2:
                comp.factor_id = None
            elif k == 3:
                comp.factor_id = "F-NO-SUCH-RECORD"
            elif k == 4:
                comp.mass_fraction += 5e-7
            elif k == 5:
                comp.mass_fraction += 2e-6
            elif k == 6:
                comp.mass_fraction = None
            elif k == 7:
                row.composition[-1].mass_fraction = math.nan

    @probe("component_factor_units_and_licences")
    def _(s):
        ids = sorted({c.factor_id for row in s.materials if row.composition for c in row.composition})
        for j, fid in enumerate(ids):
            rec = s.factors[fid]
            if j % 5 == 0:
                rec.unit = "t"
            elif j % 5 == 1:
                rec.unit = "m3"
            elif j % 5 == 2:
                rec.licence_status = "RESTRICTED"

    @probe("site_fuel_and_waste_variants")
    def _(s):
        fuels, waste = s.construction.fuels, s.construction.waste_streams
        if fuels:
            f0 = fuels[0]
            rec = s.factors.get(f0.factor_id)
            if f0.conversions:
                c = f0.conversions[0]
                f0.conversions.insert(0, UC(c.from_unit, c.to_unit, c.factor * 3.0, "PROBE"))
            fuels.append(model.SiteFuel("PROBE-A", 10.0, "piece", f0.factor_id, []))
            fuels.append(model.SiteFuel("PROBE-B", 5.0, rec.unit if rec else "L", f0.factor_id, []))
            fuels.append(model.SiteFuel("PROBE-C", 5.0, "kL", None, []))
            fuels.append(model.SiteFuel("PROBE-D", None, f0.unit, f0.factor_id, list(f0.conversions)))
            fuels.append(model.SiteFuel("PROBE-E", 2.0, "piece", f0.factor_id,
                                        [UC("piece", rec.unit if rec else "L", 4.0, "PROBE"),
                                         UC("piece", rec.unit if rec else "L", 8.0, "PROBE")]))
            fuels.append(model.SiteFuel("PROBE-F", 2.0, None, f0.factor_id, []))
        if waste:
            waste[0].mass_kg = -1.0
            if len(waste) > 1:
                waste[1].factor_id = "F-NO-SUCH-RECORD"
            waste.append(model.SiteWaste("PROBE-A", None, waste[0].factor_id))
            waste.append(model.SiteWaste("PROBE-B", 12.5, waste[0].factor_id))

    @probe("site_lists_empty")
    def _(s):
        s.construction.fuels = []
        s.construction.waste_streams = []

    @probe("transport_variants")
    def _(s):
        for i, row in enumerate(s.materials):
            tr = row.transport
            k = i % 9
            if k == 0:
                tr.mass_t = None
            elif k == 1:
                tr.mass_t = -1.0
            elif k == 2:
                tr.distance_km = math.inf
            elif k == 3:
                tr.factor_id = None
            elif k == 4:
                tr.factor_id = "F-NO-SUCH-RECORD"
            elif k == 5:
                tr.delivery_factor_id = "F-NO-SUCH-RECORD"
            elif k == 6:
                tr.mass_t = math.nan
            elif k == 7 and tr.delivery_factor_id is None and row.factor_id is not None:
                tr.delivery_factor_id = row.factor_id       # a record of the wrong stage

    @probe("equipment_variants")
    def _(s):
        for i, eq in enumerate(s.equipment):
            k = i % 6
            if k == 0:
                eq.factor_id = None
            elif k == 1:
                eq.factor_id = "F-NO-SUCH-RECORD"
            elif k == 2:
                eq.quantity_unit = "piece"
            elif k == 3:
                eq.quantity_unit = None
            elif k == 4 and eq.factor_id in s.factors:
                s.factors[eq.factor_id].licence_status = "PERMISSION_REQUIRED"

    @probe("quantity_unit_missing_or_unknown")
    def _(s):
        for i, row in enumerate(s.materials):
            if i % 4 == 0:
                row.quantity_unit = None
            elif i % 4 == 1:
                row.quantity_unit = "piece"

    @probe("factor_records_removed_or_restricted")
    def _(s):
        for j, fid in enumerate(sorted(s.factors)):
            if j % 6 == 0:
                del s.factors[fid]
            elif j % 6 == 1:
                s.factors[fid].licence_status = "RESTRICTED"
            elif j % 6 == 2:
                s.factors[fid].unit = "piece"

    @probe("summary_quantities_zero")
    def _(s):
        s.summary_quantities.steel_kg = 0.0
        s.summary_quantities.timber_m3 = 0.0
        s.summary_quantities.interior_m2 = 0.0

    @probe("summary_class_variants")
    def _(s):
        for i, row in enumerate(s.materials):
            if i % 3 == 0:
                row.material_class = ("GLASS", None, "BOARD", "TIMBER")[(i // 3) % 4]
                row.construction_division = ("ROOF_EXTERIOR_WALL", "OPENINGS", "INTERIOR", "STRUCTURE", None)[(i // 3) % 5]

    return probes


# ---------------------------------------------------------------------------------------------
# Checks of the specification itself (criterion (c): data only)
# ---------------------------------------------------------------------------------------------

def spec_is_data_only() -> dict:
    """The specification module consists of a docstring and assignments of literals (names of earlier
    assignments allowed); no function, lambda, call, comprehension, import or operator."""
    with open(SPEC_FILE, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    allowed = (ast.Module, ast.Expr, ast.Assign, ast.Constant, ast.Dict, ast.List, ast.Name, ast.Load, ast.Store,
               ast.UnaryOp, ast.USub)
    bad = sorted({type(n).__name__ for n in ast.walk(tree) if not isinstance(n, allowed)})
    n_assign = sum(1 for n in tree.body if isinstance(n, ast.Assign))
    n_other = sum(1 for n in tree.body if not isinstance(n, (ast.Assign, ast.Expr)))
    round_trip = json.loads(json.dumps(pre_a.SPEC)) == pre_a.SPEC
    ids = [u["id"] for u in pre_a.SPEC["units"]]
    leaks = []
    for path in ENGINE_FILES:
        with open(path, encoding="utf-8") as fh:
            src = fh.read()
        leaks += [f"{os.path.basename(path)}: {uid}" for uid in ids if uid in src]
    return {"forbidden_syntax_nodes": bad, "top_level_assignments": n_assign, "top_level_other_statements": n_other,
            "json_round_trip_equal": round_trip, "unit_ids_found_in_engine_sources": leaks,
            "ok": not bad and not n_other and round_trip and not leaks}


# ---------------------------------------------------------------------------------------------
# Vocabulary record
# ---------------------------------------------------------------------------------------------

VOCABULARY = {
    "step:sp": {
        "what": "masked sum-product: out[g] = sum over rows x of a table, sum over terms, product of factors; "
                "every sp step ends in the single function Engine.core (scatter-add of row products)",
        "in_the_form": "the form itself"},
    "step:match": {
        "what": "first match of a keyed look-up: reference to the first row of another table whose key columns equal "
                "the key of the row (missing when none)",
        "in_the_form": "factor type 2 (equal keys) restricted to the first matching row; needs the order of the rows "
                       "(min over row positions), which the (+, x) form does not have"},
    "group:none": {"what": "per row, no sum (result is a column)", "in_the_form": "grouping: none"},
    "group:total": {"what": "one number for the scenario", "in_the_form": "grouping: total"},
    "group:by": {"what": "scatter-add by a reference column into the rows of the referenced table "
                         "(child rows to parent row, component rows to factor record)", "in_the_form": "grouping: by key"},
    "factor:column": {"what": "a column used as a number", "in_the_form": "factor type 1 (input column or earlier result)"},
    "factor:const": {"what": "a numeric constant as a factor (only -1 is used: differences)",
                     "in_the_form": "factor type 1, degenerate (constant column)"},
    "pred:present": {"what": "value is not missing", "in_the_form": "factor type 2"},
    "pred:range": {"what": "lo <= x <= hi with open / closed ends ('finite and >= 0', ratio, positive)",
                   "in_the_form": "factor type 2"},
    "pred:eq": {"what": "x == constant, or equal values of two columns", "in_the_form": "factor type 2"},
    "pred:le": {"what": "a <= b for two columns (used once: assessment date <= validity date, ISO text order)",
                "in_the_form": "factor type 2; on strings it needs the text order (pre-processing: rank of the string)"},
    "pred.not": {"what": "negation flag of a predicate: 1 - [P]", "in_the_form": "factor type 2"},
    "fn:inv": {"what": "1/x", "in_the_form": "factor type 3"},
    "fn:one_minus": {"what": "1 - x", "in_the_form": "factor type 3 (polynomial)"},
    "fn:inv_one_minus": {"what": "1/(1 - x)", "in_the_form": "factor type 3"},
    "fn:ratio_one_minus": {"what": "x/(1 - x)", "in_the_form": "factor type 3"},
    "operand:own": {"what": "column of the step's table", "in_the_form": "addressing"},
    "operand:via": {"what": "column of another table gathered through a reference column (join through a key)",
                    "in_the_form": "factor type 2 (equal keys) folded into addressing"},
    "operand:of": {"what": "single value of a one-row table (scenario scalar) broadcast to all rows",
                   "in_the_form": "addressing (join without key)"},
    "operand:const": {"what": "constant operand of a predicate or key", "in_the_form": "addressing"},
    "read:scalar": {"what": "read one number (float; int and bool only when the value is exactly integral / 0 or 1)",
                    "in_the_form": "post-processing"},
    "read:rows": {"what": "list per row, None where an indicator column is 0", "in_the_form": "post-processing"},
    "read:enum": {"what": "label of the indicator column that is 1, None when none", "in_the_form": "post-processing"},
    "read:dict": {"what": "dictionary key column -> value for rows with a non-zero count", "in_the_form": "post-processing"},
    "read:record": {"what": "nested dictionary of read-outs", "in_the_form": "post-processing"},
    "read:const": {"what": "literal value stored in the specification", "in_the_form": "post-processing (no computation)"},
}

BEYOND_THE_FORM = {
    "(templates)": [
        "use: template instantiation by textual substitution (STAGE, CONV, FACTOR, CLASS). Not a computation, but "
        "the specification is written with it; step counts are given after expansion."],
    "(shared)": [
        "stage gate 'stages == [stage]' is evaluated as (length == 1) and (one entry equal to the stage): a "
        "scatter-add over the child table factors.stages"],
    "(every unit with a factor look-up)": [
        "match: record by factor id (dictionary key, unique: no order needed)",
        "match: first row-specific conversion (order = position in the row's list) and first scenario conversion "
        "(order = row order of the table); priority identity > row-specific > scenario table is written as three "
        "mutually exclusive predicate products (negation flag)"],
    "A13-05": ["division Q/(1-w) is the product Q * (1/(1-w)): can differ from the reference in the last bit"],
    "X-13": ["difference ordered - installed needs the constant factor -1"],
    "A13-02": ["'|sum - 1| <= 1e-6' needs the constant -1 (residual) and a range predicate",
               "the reference stops at the first unusable component; the specification counts unusable components "
               "(same public result because the partial sum is discarded)"],
    "X-15": ["list equality (declared stages == stages of the record) needs a positional join: gather the record "
             "row into the child table, match on (record row, position), count equal entries (3 steps)",
             "validity date >= assessment date: text order of ISO dates (pre-processing: rank of interned strings)",
             "priority declaration > composite > generic: mutually exclusive indicator columns (negation), not min",
             "enumeration 'kind' is read from three indicator columns (post-processing)"],
    "X-03": ["dictionary outputs keyed by factor id: scatter-add into the factor table plus a count column that "
             "selects the keys (post-processing read-out)"],
    "A5-01": ["NOT EXPRESSED EXACTLY: the reference splits the grid unit text at '/' (text operation). The "
              "specification uses a closed list of three texts (kgCO2e/kWh, kgCO2e/MWh, kgCO2e/MJ); a scenario that "
              "registers a conversion from kWh to another unit is outside the list",
              "match with constant keys (kWh -> MWh, kWh -> MJ)"],
    "A5-04": ["output 'other_assessed' is a literal constant; 'parts' is a read-out of results of other units"],
    "X-17": ["six summary classes are six instantiations of one template (4 steps each); the classes and their "
             "summary columns are listed in the specification because a column cannot be addressed by a value",
             "division sum/quantity is the product sum * (1/quantity)"],
    "X-16": ["match: price index by year (dictionary key, unique)", "ratio of two indices is index * (1/index)"],
    "X-12": ["division by the load factor is a product with 1/x"],
    "(all units)": [
        "integer-typed inputs passed through by the reference keep type int; the engine returns float (type only)",
        "strings are interned to integer codes before evaluation (pre-processing, generic)"],
}


def vocabulary_record(program, static, dynamic_by_set) -> dict:
    units = [msp.SHARED] + program.units
    elements = sorted({k for u in static.values() for k in u if k.split(":")[0] in
                       ("step", "group", "factor", "pred", "fn", "operand", "read") or k == "pred.not"})
    undocumented = [e for e in elements if e not in VOCABULARY]
    record = {}
    for e in elements:
        per_unit = {u: static.get(u, {}).get(e, 0) for u in units if static.get(u, {}).get(e, 0)}
        record[e] = dict(VOCABULARY.get(e, {"what": "UNDOCUMENTED"}), total=sum(per_unit.values()),
                         n_units_using=len([u for u in per_unit if u != msp.SHARED]), per_unit=per_unit)
    written = {u["id"]: len(u["steps"]) for u in program.spec["units"]}
    written[msp.SHARED] = len(program.spec.get("shared", []))
    per_unit = {}
    seen: set[str] = set()
    growth = []
    for u in units:
        st = static.get(u, {})
        mine = {k for k in st if k in elements}
        new = sorted(mine - seen)
        seen |= mine
        growth.append({"unit": u, "new_elements": new, "cumulative": len(seen)})
        per_unit[u] = {
            "steps_as_written": written[u],
            "steps_expanded": st.get("step:sp", 0) + st.get("step:match", 0),
            "sp_steps": st.get("step:sp", 0), "match_steps": st.get("step:match", 0), "terms": st.get("terms", 0),
            "steps_from_templates": {k.split(":", 1)[1]: v for k, v in st.items() if k.startswith("steps_from_template:")},
            "elements_used": sorted(mine),
        }
    templates = {name: {"steps_in_body": len(body),
                        "instantiations_written": sum(1 for u in [{"steps": program.spec.get("shared", [])}] + program.spec["units"]
                                                      for st in u["steps"] if st.get("use") == name)}
                 for name, body in program.spec.get("templates", {}).items()}
    return {
        "candidate": "TC-B-01", "specification": "research_code/specs/pre_a.py", "engine": "research_code/tstudy/msp.py",
        "data_statement": "fictional data, independent concept model",
        "evidence_level": "N (numerical); counts are read from the specification by the check script",
        "checked_by": "implementer only",
        "form": "out[g] = sum over rows x of a table, sum over terms t, prod_k phi_{t,k}(x), grouped by g",
        "primitives": {"sum_product_core": "Engine.core (one function; every sp step ends in it)",
                       "first_match": "Engine.run_match (min over row positions; a second primitive, counted separately)"},
        "n_vocabulary_elements_used": len(elements), "undocumented_elements": undocumented,
        "elements": record,
        "templates": templates,
        "per_unit": per_unit,
        "vocabulary_growth_in_specification_order": growth,
        "beyond_the_form": BEYOND_THE_FORM,
        "first_match_order_needed_in_data": dynamic_by_set,
        "totals": {"units": len(program.units), "steps_expanded": len(program.steps),
                   "sp_steps": sum(1 for s in program.steps if s["op"] == "sp"),
                   "match_steps": sum(1 for s in program.steps if s["op"] == "match"),
                   "steps_as_written": sum(written.values())},
    }


# ---------------------------------------------------------------------------------------------
# Fault injection helpers
# ---------------------------------------------------------------------------------------------

def leaves(x, path=""):
    if isinstance(x, dict):
        for k, v in x.items():
            yield from leaves(v, f"{path}/{k}")
    elif isinstance(x, (list, tuple)):
        for i, v in enumerate(x):
            yield from leaves(v, f"{path}[{i}]")
    else:
        yield path, x


def is_number(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def same(a, b) -> bool:
    if isinstance(a, float) and isinstance(b, float) and math.isnan(a) and math.isnan(b):
        return True
    return type(a) is type(b) and a == b


def changed_leaves(clean: dict, faulty: dict) -> tuple[int, int, int]:
    """(numeric leaves of the clean result, numeric leaves that changed, other leaves that changed)."""
    a, b = dict(leaves(clean)), dict(leaves(faulty))
    n_num = sum(1 for v in a.values() if is_number(v))
    ch_num = sum(1 for k, v in a.items() if is_number(v) and not same(v, b.get(k, "<absent>")))
    ch_other = sum(1 for k, v in a.items() if not is_number(v) and not same(v, b.get(k, "<absent>")))
    ch_other += sum(1 for k in b if k not in a)
    return n_num, ch_num, ch_other


# ---------------------------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------------------------

def main() -> int:
    t_start = time.perf_counter()
    trees = baseline.assert_frozen()
    spec_check = spec_is_data_only()
    program = msp.Program(json.loads(json.dumps(pre_a.SPEC)))       # evaluated from the JSON round trip
    static = msp.static_usage(program)
    ids = program.units
    assert len(ids) == 18, len(ids)

    design_ok, design_out = scenarios.usable(scenarios.design_set(N_DESIGN, "M"))
    eval_ok, eval_out = scenarios.usable(scenarios.evaluation_set(N_EVALUATION, "M"))
    edge_ok, edge_out = scenarios.usable([s for _, s in scenarios.edge_set()])
    dirty = dirty_set()
    probes = probe_set()
    sets = {"design": design_ok, "evaluation": eval_ok, "edge": edge_ok, "dirty": dirty,
            "probe": [p["scenario"] for p in probes]}
    excluded = {"design": design_out, "evaluation": eval_out, "edge": edge_out, "dirty": [], "probe": []}

    accs: dict[tuple[str, str, str], Acc] = {}
    per_scenario: dict[str, dict] = {}
    set_info = {}
    present_columns: set[tuple[str, str]] = set()
    absent_columns: set[tuple[str, str]] = set()
    absent_tables: set[str] = set()
    order_needed = {}
    kept: dict[str, list] = {}
    for set_name, scns in sets.items():
        info = {"n_scenarios": 0, "n_excluded": len(excluded[set_name]), "excluded": excluded[set_name],
                "reference_errors": [], "engine_errors": [], "seconds_reference": 0.0, "seconds_flatten": 0.0,
                "seconds_engine": 0.0, "sizes": {}}
        order = {}
        kept[set_name] = []
        for scn in scns:
            sid = scn.meta.scenario_id
            try:
                t0 = time.perf_counter()
                ref = baseline.run_reference(scn, ids)
                info["seconds_reference"] += time.perf_counter() - t0
            except Exception as exc:  # the reference refuses or fails: nothing to compare with
                info["reference_errors"].append({"scenario": sid, "error": f"{type(exc).__name__}: {exc}"[:200]})
                continue
            t0 = time.perf_counter()
            tabs = tables.from_scenario(scn)
            t1 = time.perf_counter()
            try:
                res, eng = msp.evaluate(program, tabs)
            except Exception as exc:
                info["engine_errors"].append({"scenario": sid, "error": f"{type(exc).__name__}: {exc}"[:200]})
                for uid in ids:                       # an engine failure is a mismatch of every output
                    for key in public(ref[uid]):
                        acc = accs.setdefault((uid, key, set_name), Acc())
                        acc.n_struct_mismatch += 1
                        acc.note(sid, f"{uid}/{key}", "engine error", "", str(exc)[:80])
                continue
            t2 = time.perf_counter()
            info["seconds_flatten"] += t1 - t0
            info["seconds_engine"] += t2 - t1
            info["n_scenarios"] += 1
            info["sizes"][scn.meta.size_class] = info["sizes"].get(scn.meta.size_class, 0) + 1
            kept[set_name].append((scn, ref, tabs, res))
            for t, cols in tabs.data.items():
                present_columns.update((t, c) for c in cols)
            absent_columns |= eng.absent_columns
            absent_tables |= eng.absent_tables
            for uid, use in eng.usage.items():
                o = order.setdefault(uid, {"match_probes": 0, "match_order_decided": 0})
                o["match_probes"] += use.get("match_probes", 0)
                o["match_order_decided"] += use.get("match_order_decided", 0)
            n_bad = 0
            bad_outputs = {}
            for uid in ids:
                want = public(ref[uid])
                for key in sorted(set(want) | set(res[uid])):
                    acc = accs.setdefault((uid, key, set_name), Acc())
                    before = acc.n_mismatch
                    if key not in want or key not in res[uid]:
                        acc.n_struct_mismatch += 1
                        acc.note(sid, f"{uid}/{key}", key in res[uid], key in want, "output key on one side only")
                    else:
                        compare(res[uid][key], want[key], f"{uid}/{key}", acc, sid)
                    n_bad += acc.n_mismatch - before
                    if acc.n_mismatch - before:
                        bad_outputs[f"{uid}/{key}"] = acc.n_mismatch - before
            per_scenario[sid] = {"set": set_name, "n_mismatch": n_bad, "outputs_with_mismatch": bad_outputs}
        set_info[set_name] = info
        order_needed[set_name] = {u: o for u, o in order.items() if o["match_probes"]}

    never_present = sorted(f"{t}.{c}" for t, c in absent_columns if (t, c) not in present_columns)
    spec_check["columns_referenced_but_absent_in_every_scenario"] = never_present
    spec_check["tables_referenced_but_absent_in_some_scenario"] = sorted(absent_tables)

    # ---- table ------------------------------------------------------------------------------
    rows = []
    print(f"{'unit':7s} {'output':22s} {'set':10s} {'compared':>9s} {'mismatch':>8s} {'max rel':>9s} "
          f"{'ref=0':>7s} {'exact':>7s} {'None':>6s}")
    for (uid, key, set_name) in sorted(accs, key=lambda k: (ids.index(k[0]), k[1], list(sets).index(k[2]))):
        acc = accs[(uid, key, set_name)]
        d = acc.as_dict()
        d.update(unit=uid, output=key, set=set_name)
        rows.append(d)
        print(f"{uid:7s} {key:22s} {set_name:10s} {acc.n_compared:9d} {acc.n_mismatch:8d} {acc.max_rel:9.2e} "
              f"{acc.n_ref_zero:7d} {acc.n_exact:7d} {acc.n_none:6d}")
    summary = {}
    for set_name in sets:
        sel = [r for r in rows if r["set"] == set_name]
        summary[set_name] = {
            "n_scenarios": set_info[set_name]["n_scenarios"],
            "n_unit_outputs": len(sel),
            "n_compared": sum(r["n_compared"] for r in sel), "n_mismatch": sum(r["n_mismatch"] for r in sel),
            "n_float": sum(r["n_float"] for r in sel), "n_float_mismatch": sum(r["n_float_mismatch"] for r in sel),
            "n_bit_identical": sum(r["n_bit_identical"] for r in sel),
            "max_rel": max([r["max_rel"] for r in sel] or [0.0]),
            "n_ref_zero": sum(r["n_ref_zero"] for r in sel),
            "n_ref_zero_mismatch": sum(r["n_ref_zero_mismatch"] for r in sel),
            "max_abs_ref_zero": max([r["max_abs_ref_zero"] for r in sel] or [0.0]),
            "n_exact": sum(r["n_exact"] for r in sel), "n_exact_mismatch": sum(r["n_exact_mismatch"] for r in sel),
            "n_none": sum(r["n_none"] for r in sel),
            "n_struct_mismatch": sum(r["n_struct_mismatch"] for r in sel),
            "units_with_mismatch": sorted({r["unit"] for r in sel if r["n_mismatch"]}, key=ids.index),
            "scenarios_with_mismatch": sorted(s for s, v in per_scenario.items() if v["set"] == set_name and v["n_mismatch"]),
        }
    print()
    for set_name, s in summary.items():
        print(f"SET {set_name:10s} scenarios {s['n_scenarios']:3d}  compared {s['n_compared']:8d}  mismatches {s['n_mismatch']:5d}  "
              f"max rel {s['max_rel']:.2e}  ref=0 {s['n_ref_zero']:7d} (bad {s['n_ref_zero_mismatch']})  "
              f"bit-identical floats {s['n_bit_identical']}/{s['n_float']}")

    probe_rows = []
    for p in probes:
        sid = p["scenario"].meta.scenario_id
        n_bad = per_scenario.get(sid, {}).get("n_mismatch")
        actual = "not compared" if n_bad is None else ("mismatch" if n_bad else "match")
        probe_rows.append({"probe": p["name"], "expected": p["expect"], "actual": actual, "n_mismatch": n_bad,
                           "as_expected": actual == p["expect"], "note": p["note"],
                           "outputs_with_mismatch": per_scenario.get(sid, {}).get("outputs_with_mismatch", {})})
    print("\nPROBES (targeted mutations)")
    for r in probe_rows:
        flag = "" if r["as_expected"] else "   <-- NOT AS EXPECTED"
        print(f"  {r['probe']:44s} expected {r['expected']:8s} actual {r['actual']:12s} mismatches {r['n_mismatch']}{flag}"
              + (f"   {r['outputs_with_mismatch']}" if r["outputs_with_mismatch"] else ""))

    # ---- coverage of branches by the reference values ------------------------------------------
    coverage = {}
    for set_name, items in kept.items():
        kinds = {"EPD": 0, "COMPOSITE": 0, "GENERIC": 0, "None": 0}
        computed = {"True": 0, "False": 0}
        for _, ref, _, _ in items:
            for k in ref["X-15"]["kind"]:
                kinds[str(k)] += 1
            computed[str(ref["A5-01"]["computed"])] += 1
        coverage[set_name] = {"X-15 kind": kinds, "A5-01 computed": computed}

    # ---- fault injection (membership test, protocol section 5.2 (b)) -------------------------------
    sample = kept["design"][:12] + kept["dirty"][:8]
    membership = {}
    for uid in ids:
        rec = {"n_scenarios": len(sample), "n_scenarios_numeric_changed": 0, "numeric_leaves": 0,
               "numeric_leaves_changed": 0, "other_leaves_changed": 0, "mismatches_against_reference": 0,
               "other_units_changed": set()}
        for scn, ref, tabs, clean in sample:
            faulty, _ = msp.evaluate(program, tabs, fault={"scale": FAULT_SCALE, "units": [uid]})
            n_num, ch_num, ch_other = changed_leaves(clean[uid], faulty[uid])
            rec["numeric_leaves"] += n_num
            rec["numeric_leaves_changed"] += ch_num
            rec["other_leaves_changed"] += ch_other
            rec["n_scenarios_numeric_changed"] += 1 if ch_num else 0
            acc = Acc()
            for key, want in public(ref[uid]).items():
                compare(faulty[uid].get(key), want, f"{uid}/{key}", acc, scn.meta.scenario_id)
            rec["mismatches_against_reference"] += acc.n_mismatch
            for other in ids:
                if other != uid and changed_leaves(clean[other], faulty[other])[1:] != (0, 0):
                    rec["other_units_changed"].add(other)
        rec["other_units_changed"] = sorted(rec["other_units_changed"], key=ids.index)
        rec["member"] = rec["n_scenarios_numeric_changed"] > 0
        membership[uid] = rec

    def units_changed(fault, items):
        hit = {uid: 0 for uid in ids}
        for scn, ref, tabs, clean in items:
            faulty, _ = msp.evaluate(program, tabs, fault=fault)
            for uid in ids:
                if changed_leaves(clean[uid], faulty[uid])[1:] != (0, 0):
                    hit[uid] += 1
        return hit

    global_hit = units_changed({"scale": FAULT_SCALE, "units": None}, sample)
    shared_hit = units_changed({"scale": FAULT_SCALE, "units": [msp.SHARED]}, sample)
    last_generated = units_changed({"match": "last", "units": None},
                                   kept["design"] + kept["evaluation"] + kept["edge"] + kept["dirty"])
    last_probe = units_changed({"match": "last", "units": None}, kept["probe"])
    fault = {
        "sample": f"{len(kept['design'][:12])} design + {len(kept['dirty'][:8])} dirty scenarios",
        "fault_scale": FAULT_SCALE,
        "own_steps_only": membership,
        "non_members": [uid for uid in ids if not membership[uid]["member"]],
        "all_steps_scenarios_with_change": global_hit,
        "units_unchanged_under_global_fault": [uid for uid in ids if not global_hit[uid]],
        "shared_steps_only_scenarios_with_change": shared_hit,
        "match_last_instead_of_first": {
            "generated_sets_scenarios_with_change": {u: n for u, n in last_generated.items() if n},
            "n_generated_scenarios": sum(len(kept[k]) for k in ("design", "evaluation", "edge", "dirty")),
            "probe_set_scenarios_with_change": {u: n for u, n in last_probe.items() if n},
            "n_probe_scenarios": len(kept["probe"]),
        },
    }
    print("\nFAULT INJECTION  (core result x %.4f in the steps of one unit; %s)" % (FAULT_SCALE, fault["sample"]))
    for uid in ids:
        m = membership[uid]
        print(f"  {uid:7s} member {str(m['member']):5s} scenarios changed {m['n_scenarios_numeric_changed']:2d}/{m['n_scenarios']}"
              f"  numeric leaves changed {m['numeric_leaves_changed']:6d}/{m['numeric_leaves']:6d}"
              f"  mismatches vs reference {m['mismatches_against_reference']:6d}  also changes {','.join(m['other_units_changed']) or '-'}")
    print("  non-members:", fault["non_members"] or "none")
    print("  match last-instead-of-first, generated sets:", fault["match_last_instead_of_first"]["generated_sets_scenarios_with_change"] or "no unit changes")
    print("  match last-instead-of-first, probe set:", fault["match_last_instead_of_first"]["probe_set_scenarios_with_change"] or "no unit changes")

    # ---- run times (reference value only; same machine, same language) ------------------------------
    baseline.load()
    from synth import generate, population

    timing = {}
    for size in ("S", "M", "L"):     # S and M are the requested sizes; L is an additional point for the trend
        scn = generate.make_scenario(population.BENCHMARK_SEEDS[size], "RC", "office", size, 60.0)

        def best(fn, n):
            out = []
            for _ in range(n):
                t0 = time.perf_counter()
                fn()
                out.append(time.perf_counter() - t0)
            return min(out)

        tabs = tables.from_scenario(scn)
        _, eng = msp.evaluate(program, tabs)
        timing[size] = {
            "scenario": scn.meta.scenario_id,
            "rows": {"materials": len(scn.materials), "equipment": len(scn.equipment), "factors": len(scn.factors)},
            "reference_18_units_s": best(lambda: baseline.run_reference(scn, ids), 5),
            "flatten_whole_scenario_s": best(lambda: tables.from_scenario(scn), 3),
            "engine_steps_and_readouts_s": best(lambda: msp.evaluate(program, tabs), 5),
            "core_calls": sum(u.get("core_calls", 0) for u in eng.usage.values()),
            "core_products": sum(u.get("core_products", 0) for u in eng.usage.values()),
            "match_probes": sum(u.get("match_probes", 0) for u in eng.usage.values()),
        }
        t = timing[size]
        t["engine_total_s"] = t["flatten_whole_scenario_s"] + t["engine_steps_and_readouts_s"]
        t["ratio_engine_total_to_reference"] = t["engine_total_s"] / t["reference_18_units_s"]
        t["ratio_engine_steps_to_reference"] = t["engine_steps_and_readouts_s"] / t["reference_18_units_s"]
    t0 = time.perf_counter()
    msp.Program(json.loads(json.dumps(pre_a.SPEC)))
    timing["specification_expansion_s"] = time.perf_counter() - t0
    timing["note"] = ("best of 5 (flatten: best of 3), one machine, Python; reference value only. The flattening "
                      "converts the whole scenario, also the parts these 18 units do not read.")
    print("\nRUN TIME (reference value only)")
    for size in ("S", "M", "L"):
        t = timing[size]
        print(f"  {size}: reference {t['reference_18_units_s']*1e3:8.2f} ms   flatten {t['flatten_whole_scenario_s']*1e3:8.2f} ms   "
              f"engine {t['engine_steps_and_readouts_s']*1e3:8.2f} ms   engine/reference {t['ratio_engine_steps_to_reference']:.1f}   "
              f"(flatten+engine)/reference {t['ratio_engine_total_to_reference']:.1f}")

    # ---- records ------------------------------------------------------------------------------------
    vocab = vocabulary_record(program, static, order_needed)
    not_expressed = [
        {"unit": "A5-01", "output": "value, computed",
         "what": "the electricity unit of the grid factor is taken by the reference from the unit text by a split at '/'",
         "reason": "a text operation is not a factor of the form (not a column, not a predicate on a column, not a "
                   "rational function); the specification replaces it by a closed list of three unit texts",
         "consequence": "equal on every generated scenario (the generator never changes the grid unit) and on the "
                        "probes inside the list; differs when a scenario registers a conversion from kWh to a unit "
                        "outside the list (probe grid_unit_GJ_with_registered_conversion)"},
        {"unit": "A13-05 (and any pass-through of an input)", "output": "q_ord, q_inst",
         "what": "the Python type of an integer-typed input",
         "reason": "the engine holds every number as a float",
         "consequence": "values equal, type differs (probe integer_quantities); no integer-typed quantity occurs in "
                        "the generated sets"},
    ]
    not_expressed.append(
        {"unit": "A13-05 -> X-13", "output": "waste_by_item (rows with basis DESIGN)",
         "what": "the rounding of the two-column division Q/(1-w)",
         "reason": "the form has only functions of one column, so the division is the product Q*(1/(1-w)); the "
                   "results can differ in the last bit, and the difference ordered - installed amplifies that by about 1/w",
         "consequence": "largest relative difference on the generated sets: see summary max_rel (X-13 waste_by_item); "
                        "above 1e-9 for waste rates of about 1e-8 and smaller (probe tiny_waste_rates). The reference "
                        "value itself is ill-conditioned there (relative rounding error about 1e-16/w)"})
    all_expected = all(r["as_expected"] for r in probe_rows)
    generated_ok = all(summary[k]["n_mismatch"] == 0 for k in ("design", "evaluation", "edge", "dirty"))
    exactness = {
        "candidate": "TC-B-01", "route": "B", "specification": "research_code/specs/pre_a.py",
        "engine": "research_code/tstudy/msp.py", "check": "research_code/checks/check_msp_pre_a.py",
        "frozen_trees": trees,
        "data_statement": "fictional data, independent concept model",
        "evidence_level": "N (numerical)",
        "checked_by": "implementer only",
        "units": ids,
        "scope": "every public output (keys not starting with '_') of the 18 units; SYS-01..04 not included",
        "tolerance": {"numbers_relative": TOL, "zero_reference": "candidate must be exactly 0.0 (counted separately)",
                      "integers_booleans_strings_none": "exact value and type",
                      "lists": "element-wise, same length", "dictionaries": "key-wise, same keys"},
        "sets": {
            "design": f"tstudy.scenarios.design_set({N_DESIGN}, 'M'), valid domain only",
            "evaluation": f"tstudy.scenarios.evaluation_set({N_EVALUATION}, 'M'), valid domain only",
            "edge": "tstudy.scenarios.edge_set(), valid domain only",
            "dirty": f"synth.generate.make_scenario({DIRTY_SEED}+i, STRUCTURES[i%4], USES[i%6], 'S', dirty=True), i=0..{N_DIRTY - 1}; "
                     "outside the valid domain (injected defects), reported separately",
            "probe": "targeted mutations of one clean scenario written by the implementer (see probe list); "
                     "outside the generator range, reported separately",
        },
        "set_info": set_info,
        "summary": summary,
        "generated_sets_all_equal": generated_ok,
        "probes": probe_rows,
        "probes_all_as_expected": all_expected,
        "reference_branch_coverage": coverage,
        "table": rows,
        "fault_injection": fault,
        "specification_checks": spec_check,
        "not_expressed": not_expressed,
        "timing": timing,
        "counts": vocab["totals"],
        "specification_size": {"json_bytes": len(json.dumps(pre_a.SPEC)), "source_lines": sum(1 for _ in open(SPEC_FILE, encoding="utf-8")),
                               "terms": sum(u.get("terms", 0) for u in static.values()),
                               "predicate_factors": sum(v for u in static.values() for k, v in u.items() if k.startswith("pred:")),
                               "column_factors": sum(u.get("factor:column", 0) for u in static.values()),
                               "function_factors": sum(v for u in static.values() for k, v in u.items() if k.startswith("fn:"))},
        "seconds_total": None,
    }
    exactness["seconds_total"] = time.perf_counter() - t_start
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "msp_pre_a_exactness.json"), "w", encoding="utf-8") as fh:
        json.dump(exactness, fh, ensure_ascii=False, indent=1, default=str)
        fh.write("\n")
    with open(os.path.join(OUT_DIR, "msp_vocabulary.json"), "w", encoding="utf-8") as fh:
        json.dump(vocab, fh, ensure_ascii=False, indent=1, default=str)
        fh.write("\n")

    print("\nSPECIFICATION CHECKS", json.dumps(spec_check, ensure_ascii=False))
    print("EXCLUDED (outside the valid domain):", {k: [e[0] for e in v] for k, v in excluded.items() if v})
    print("REFERENCE ERRORS:", {k: v["reference_errors"] for k, v in set_info.items() if v["reference_errors"]} or "none")
    print("ENGINE ERRORS:", {k: v["engine_errors"] for k, v in set_info.items() if v["engine_errors"]} or "none")
    print("COUNTS", vocab["totals"], "vocabulary elements used:", vocab["n_vocabulary_elements_used"],
          "undocumented:", vocab["undocumented_elements"])
    print(f"generated sets all equal: {generated_ok}; probes as expected: {all_expected}; "
          f"non-members: {fault['non_members'] or 'none'}; {exactness['seconds_total']:.1f} s")
    failed = (not generated_ok) or (not all_expected) or bool(fault["non_members"]) or (not spec_check["ok"]) \
        or bool(vocab["undocumented_elements"]) or any(v["engine_errors"] for v in set_info.values())
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
