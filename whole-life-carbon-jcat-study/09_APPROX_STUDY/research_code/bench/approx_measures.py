"""Per-scenario measurements of the approximation study (``bench.approx_study`` drives them).

Each ``m_*`` function takes one scenario with its reference results (``One``) and adds what
it measures to the collectors of the study (``Study``): the primary quantity of every
candidate it covers, the real stage values and the own outputs of the attached units, the
propagated totals (the reference re-run with the approximated input), the input counts,
and - on the scenarios of the load sample - the executed instructions of the kernels.

Expressions that produce statistics published before this revision are kept as they were,
so that those statistics are reproduced bit for bit.
"""
from __future__ import annotations

import dataclasses
import math

from fastcalc import closed_forms as cf
from refcalc import registry
from refcalc.base import (GRID, REFRIGERANT, annual_unit, convert, grid_unit, lookup, nonneg, periodic_events, positive,
                          profile_uses_descriptor, profile_values, ratio, year_weights)
from refcalc.units_b import equipment_extra_lines, material_install_line
from refcalc.units_c_sum import stage_lines
from synth import make_scenario
from synth.model import CompositeComponent, EolRoute

from bench import approx_support as sp
from bench.approx_meta import DECL
from bench.approx_support import Collector, Series, stats

STAGES14 = ("A1-A3", "A4", "A5", "B1", "B2", "B3", "B4", "B5", "B6", "B7", "C1", "C2", "C3", "C4")
B5_LABEL = "B5（建替・大型改修の回数に適用）"
B603_LABEL = "B6-03（= B6＋B2。従来「B6 段階」として公表していた量）"
C34_LABEL = "C3＋C4（段階の値の合計。設備の廃棄 X-14 を含む）"
X12_LABEL = "X-12（積載率補正後の輸送。参考値）"
C2_LABEL = "C2（廃棄物搬出。行ごとの搬出距離を単純平均に置換）"
GUARD_KEYS = ("rk<=0.05", "0.05<rk<=0.2", "rk>0.2")
# fictional lives near the study period: the safe-side repair forms are measured on them as well
STRESS_CASES = ((30.0, [29.0]), (30.0, [9.9, 14.9, 29.0]), (30.0, [7.0, 11.0, 13.0, 17.0, 23.0]), (50.0, [49.0, 24.5]))

COUNT_FORMS = (("AP-01", lambda T, c: max(0.0, T / c - 1.0)), ("AP-02", lambda T, c: max(0.0, T / c - 0.5)),
               ("AP-03", lambda T, c: T / c))
COUNT_KERNELS = {"AP-01": sp.count_ap01, "AP-02": sp.count_ap02, "AP-03": sp.count_ap03}


def renewal_rows(scn, res):
    """Every row that can be renewed: class, period, emission of one renewal, reference count, explicit schedule?"""
    out = []
    q_ord = res["A13-05"]["q_ord"]
    srcs = [res[k]["by_item"] for k in ("A13-01", "A13-03", "A4-01", "A4-02", "C2-01", "C3-01", "C4-01")]
    for i, row in enumerate(scn.materials):
        u = sum(src[i] for src in srcs)
        inst = material_install_line(scn, row, q_ord[i])
        if inst is not None:
            u += inst[1] * scn.factors[inst[0]].value
        e0 = res["A13-01"]["by_item"][i] + res["A13-03"]["by_item"][i]
        out.append({"cls": row.material_class, "cycle": row.refresh_cycle, "u": u, "n": res["B4-03"]["by_item"][i],
                    "explicit": False, "e0": e0, "r": row.repair_rate, "events": None, "equipment": False})
    for j, eq in enumerate(scn.equipment):
        u = res["X-01"]["by_item"][j] + res["X-14"]["by_item"][j]
        u += sum(act * scn.factors[fid].value for fid, act in equipment_extra_lines(scn, eq)[0])
        events = res["B4-01"]["events"][j]            # the years of the events
        out.append({"cls": "EQUIPMENT", "cycle": eq.service_life, "u": u, "n": len(events),
                    "explicit": eq.replacement_event_list is not None, "e0": res["X-01"]["by_item"][j], "r": eq.repair_rate,
                    "events": events, "equipment": True})
    return out


class One:
    """One scenario with its reference results and what several candidates share."""

    def __init__(self, scn, res, load: bool = False):
        self.scn, self.res, self.load = scn, res, load
        self.group = (scn.meta.structure, scn.meta.use)
        self.T = scn.boundary.study_period
        self.w = year_weights(self.T)
        self.Y = len(self.w) - 1
        self.stage = res["X-02"]["by_stage_all"]
        self.wlc = sum(self.stage.values())
        self.sum03 = res["SUM-03"]["value"]
        self.rows = renewal_rows(scn, res)

    def propagate(self, col: Collector, edit, check_unit=None, check_value=None, check_of=None):
        """Re-run the reference with the scenario rewritten by ``edit`` and record totals and stage values.

        ``check_of(results)`` is the value the rewrite must reproduce (the local candidate value)."""
        ids = ["X-02", "SUM-03"] + ([check_unit] if check_unit else [])
        new = sp.rerun(self.scn, edit, ids)
        col.add_propagated(self.stage, new["X-02"]["by_stage_all"], self.sum03, new["SUM-03"]["value"],
                           check_ref=check_value, check_new=check_of(new) if check_of else None)


class Study:
    """Everything collected over the population."""

    def __init__(self):
        self.C = {cid: Collector() for cid in DECL}
        self.b5 = {cid: Collector() for cid, _ in COUNT_FORMS}
        self.inputs: dict[str, list] = {}
        self.load = sp.Load()
        self.extra: dict[str, dict] = {cid: {} for cid in DECL}
        self.kind8 = {v: {k: Series() for k in ("CONSTANT", "LINEAR_TREND", "TABLE")} for v in ("B6", "B2", "B6-03")}
        self.grid9: dict[str, dict] = {}
        self.guard = {cid: {k: Series() for k in GUARD_KEYS} for cid in ("AP-05a", "AP-05b")}
        self.bracket = {"inside": 0, "inside_tolerance_form": 0, "n": 0, "width": [], "lower": Series(), "upper": Series()}
        self.exact_scenarios = {"AP-09c": 0, "AP-24a": 0, "AP-24b": 0}
        self.worst = {"B4": 0.0, "B3": 0.0, "annual": 0.0}
        self.cov = {"worst": 0.0, "n": 0, "pairs": []}       # pairs: (scenario error, realised correlation)
        self.below_one_year = 0
        self.unmeasured: list[str] = []
        self.excluded_stage_scenarios = 0
        self.records: list[dict] = []

    def inp(self, cid: str, exact: float, candidate: float):
        a = self.inputs.setdefault(cid, [0.0, 0.0, 0])
        a[0] += exact
        a[1] += candidate
        a[2] += 1


# ----------------------------------------------------------------- renewal counts: AP-01..03, AP-20

def m_counts(S: One, X: Study):
    scn, res, T, stage, wlc, rows = S.scn, S.res, S.T, S.stage, S.wlc, S.rows
    # the row data must rebuild the reference before any candidate is judged against it
    rebuilt = sum(r["n"] * r["u"] for r in rows)
    if stage["B4"]:
        X.worst["B4"] = max(X.worst["B4"], abs(rebuilt - stage["B4"]) / stage["B4"])
    ref_cls = {}
    for r in rows:
        ref_cls[r["cls"]] = ref_cls.get(r["cls"], 0.0) + r["n"] * r["u"]
    b5 = res["B5-01"]
    q_ord, q_inst = res["A13-05"]["q_ord"], res["A13-05"]["q_inst"]
    x10 = res["X-10"]
    n_mat_ref = sum(res["B4-03"]["by_item"])
    for cid, fn in COUNT_FORMS:
        col = X.C[cid]
        approx, cls = 0.0, {}
        n_eq = n_mat = 0.0
        for r in rows:
            k = r["n"] if r["explicit"] else (fn(T, r["cycle"]) if cf.valid_period(r["cycle"]) else 0.0)
            approx += k * r["u"]
            cls[r["cls"]] = cls.get(r["cls"], 0.0) + k * r["u"]
            if r["equipment"]:
                n_eq += k
            else:
                n_mat += k
        col.add(S.group, stage["B4"], approx, wlc)
        col.add_classes(ref_cls, cls)
        col.unit("B4-02", "値（= 段階 B4）").add(res["B4-02"]["value"], approx)
        col.unit("X-08", "値（周期別の排出の合計）").add(res["X-08"]["value"], approx)
        col.unit("B4-01", "設備の更新回数の合計（n_events）").add(res["B4-01"]["n_events"], n_eq)
        col.unit("B4-03", "資材の行ごとの回数の合計").add(n_mat_ref, n_mat)
        if b5["computed"] and scn.boundary.reconstruction_scenario != "NONE" and cf.valid_period(scn.boundary.replacement_cycle):
            per_event = b5["value"] / b5["n_events"] if b5["n_events"] else (
                scn.boundary.reconstruction_scope_fraction * sum(stage[s] for s in ("A1-A3", "A4", "A5", "C1", "C2", "C3", "C4")))
            X.b5[cid].add(S.group, stage["B5"], fn(T, scn.boundary.replacement_cycle) * per_event, wlc)
        # X-10: masses times (1 + count)
        resource = waste = 0.0
        for i, row in enumerate(scn.materials):
            conv = convert(scn, row.quantity_unit, "kg", row.conversions)
            if conv is None or q_ord[i] is None or not nonneg(row.end_of_life.mass_kg):
                continue
            k = 1.0 + (fn(T, row.refresh_cycle) if cf.valid_period(row.refresh_cycle) else 0.0)
            resource += q_ord[i] * conv * k
            waste += ((q_ord[i] - q_inst[i]) * conv + row.end_of_life.mass_kg) * k
        for j, eq in enumerate(scn.equipment):
            if nonneg(eq.end_of_life_mass_kg):
                k = len(res["B4-01"]["events"][j]) if eq.replacement_event_list is not None else (
                    fn(T, eq.service_life) if cf.valid_period(eq.service_life) else 0.0)
                waste += eq.end_of_life_mass_kg * (1.0 + k)
        col.unit("X-10", "資源量[kg]").add(x10["resource_kg"], resource, ratio_form=True)
        col.unit("X-10", "廃棄物量[kg]").add(x10["waste_kg"], waste, ratio_form=True)

    # ---- AP-20: bracket [sum u*max(0, T/c-1), sum u*T/c]; and the lower bound as it holds under the time rule
    def bound(count):
        return sum((r["n"] if r["explicit"] else (count(r["cycle"]) if cf.valid_period(r["cycle"]) else 0.0)) * r["u"] for r in rows)

    lo = bound(lambda c: max(0.0, T / c - 1.0))
    hi = bound(lambda c: T / c)
    lo_tol = bound(lambda c: max(0.0, T * sp.C_TOL / c - 1.0))
    b = X.bracket
    if stage["B4"] > 0.0:
        b["n"] += 1
        b["inside"] += lo <= stage["B4"] * (1 + 1e-12) and stage["B4"] <= hi * (1 + 1e-12)
        b["inside_tolerance_form"] += lo_tol <= stage["B4"] * (1 + 1e-12) and stage["B4"] <= hi * (1 + 1e-12)
        b["width"].append((hi - lo) / stage["B4"])
        b["lower"].add(stage["B4"], lo, ratio_form=True)
        b["upper"].add(stage["B4"], hi, ratio_form=True)

    if S.load:
        pairs = [(r["cycle"], r["u"]) for r in rows if not r["explicit"] and cf.valid_period(r["cycle"])]
        fixed = sum(r["n"] * r["u"] for r in rows if r["explicit"])
        exact = (sp.k_count, cf.renewal_count, T, pairs)
        check = (sp.k_count(cf.renewal_count, T, pairs) + fixed, stage["B4"])
        for cid, _ in COUNT_FORMS:
            X.load.pair(cid, len(pairs), (sp.k_count, COUNT_KERNELS[cid], T, pairs), exact, check,
                        {"n_distinct_cycles": len({c for c, _ in pairs})})


# ----------------------------------------------------------------- repairs and class parameters

def repairs_by_class(S: One) -> dict:
    """Repairs (B3) per class: reference, AP-04 and the safe-side forms AP-23a (rows) and AP-23b (class parameters).

    A row with an explicit list or without a cycle is exact in both safe-side forms (``fixed``).
    ``par[class]`` = [sum e0*r, sum e0*r/c, sum e0] over the rows renewed by a cycle.
    """
    T, w = S.T, S.w
    ref, ap04, row, fixed, par = {}, {}, {}, {}, {}
    below_one = n_rows = 0
    for r in S.rows:
        if not nonneg(r["r"]):
            continue
        k, a = r["cls"], r["e0"] * r["r"]
        ref.setdefault(k, 0.0)
        ap04.setdefault(k, 0.0)
        row.setdefault(k, 0.0)
        periodic = positive(r["cycle"]) and not r["explicit"]
        if periodic:
            p = par.setdefault(k, [0.0, 0.0, 0.0])
            p[2] += r["e0"]
        if not a:
            continue
        n_rows += 1
        years = sp.exact_repair_years(T, w, r)
        ref[k] += a * years
        ap04[k] += a * T
        if periodic:
            below_one += r["cycle"] < 1.0
            row[k] += a * sp.safe_side_years(T, r["cycle"])
            p[0] += a
            p[1] += a / r["cycle"]
        else:
            fixed[k] = fixed.get(k, 0.0) + a * years
            row[k] += a * years
    cls = {k: fixed.get(k, 0.0) for k in ref}
    for k, (a, b, _) in par.items():
        if a:
            cls[k] += a * (T - min(T, max(0.0, T * b / a - 1.0)))
    return {"ref": ref, "ap04": ap04, "row": row, "cls": cls, "fixed": fixed, "par": par, "below_one": below_one, "n_rows": n_rows}


def m_class_models(S: One, X: Study) -> dict:
    """AP-04, AP-23a/b (repairs), AP-18a/b (class cycle and repair rate), AP-18c (class routes), AP-18 (all three)."""
    scn, res, T, stage, wlc, rows = S.scn, S.res, S.T, S.stage, S.wlc, S.rows
    b3_ref, b3_02 = res["B3-01"]["value"], res["B3-02"]["value"]
    rep = repairs_by_class(S)
    X.below_one_year += rep["below_one"]
    if stage["B3"]:
        X.worst["B3"] = max(X.worst["B3"], abs(sum(rep["ref"].values()) - stage["B3"]) / stage["B3"])

    col = X.C["AP-04"]
    col.add(S.group, stage["B3"], b3_02, wlc)
    col.add_classes(rep["ref"], rep["ap04"])
    col.unit("B3-01", "値（= 段階 B3）").add(b3_ref, b3_02)
    col.unit("B3-02", "値（B3-01 の値と比べた）", role="IS_THE_CANDIDATE").add(b3_ref, b3_02)
    X.inp("AP-04", rep["n_rows"], 0)

    row23, cls23 = sum(rep["row"].values()), sum(rep["cls"].values())
    for cid, value, by_class in (("AP-23a", row23, rep["row"]), ("AP-23b", cls23, rep["cls"])):
        col = X.C[cid]
        col.add(S.group, stage["B3"], value, wlc)
        col.add_classes(rep["ref"], by_class)
        col.unit("B3-01", "値（= 段階 B3）").add(b3_ref, value)
    n_cls23 = sum(1 for p in rep["par"].values() if p[0])
    X.inp("AP-23b", 2 * rep["n_rows"], 2 * n_cls23)
    X.inp("AP-23c", 2 * rep["n_rows"], 0)
    X.inp("AP-18d", 2 * rep["n_rows"], 0)

    # ---- class cycle (AP-18a) and class repair rate with that cycle (AP-18b)
    agg = {}
    for r in rows:
        a = agg.setdefault(r["cls"], {"U": 0.0, "U_over_c": 0.0, "E0r": 0.0, "E0": 0.0, "b4": 0.0, "explicit": 0.0,
                                      "n_periodic": 0, "n_explicit": 0, "n_ref": 0, "equipment": r["equipment"]})
        periodic = cf.valid_period(r["cycle"]) and not r["explicit"]
        if r["explicit"]:
            a["explicit"] += r["n"] * r["u"]
            a["n_explicit"] += r["n"]
        elif periodic:
            a["U"] += r["u"]
            a["U_over_c"] += r["u"] / r["cycle"]
            a["n_periodic"] += 1
        a["b4"] += r["n"] * r["u"]
        a["n_ref"] += r["n"]
        if nonneg(r["r"]):
            a["E0"] += r["e0"]                     # every row with a usable repair rate (also rate 0)
            if r["r"] and r["e0"]:
                a["E0r"] += r["e0"] * r["r"]
    b4_18, b3_18, cls_b4, cls_b3 = 0.0, 0.0, {}, {}
    n_eq18 = n_mat18 = 0
    for k, a in agg.items():
        cbar = a["U"] / a["U_over_c"] if a["U_over_c"] else None
        nbar = cf.renewal_count(T, cbar) if cbar else 0
        cls_b4[k] = a["explicit"] + nbar * a["U"]
        b4_18 += cls_b4[k]
        skip = cf.skip_weight_periodic(T, cbar, nbar) if nbar else 0.0
        cls_b3[k] = a["E0r"] * (T - skip)
        b3_18 += a["E0r"] * (T - skip)
        if a["equipment"]:
            n_eq18 += a["n_explicit"] + nbar * a["n_periodic"]
        else:
            n_mat18 += nbar * a["n_periodic"]
    col = X.C["AP-18a"]
    col.add(S.group, stage["B4"], b4_18, wlc)
    col.add_classes({k: a["b4"] for k, a in agg.items()}, cls_b4)
    col.unit("B4-02", "値（= 段階 B4）").add(res["B4-02"]["value"], b4_18)
    col.unit("X-08", "値（周期別の排出の合計）").add(res["X-08"]["value"], b4_18)
    col.unit("B4-01", "設備の更新回数の合計（n_events）").add(res["B4-01"]["n_events"], n_eq18)
    col.unit("B4-03", "資材の行ごとの回数の合計").add(sum(res["B4-03"]["by_item"]), n_mat18)
    n_periodic = sum(a["n_periodic"] for a in agg.values())
    n_cls18 = sum(1 for a in agg.values() if a["n_periodic"])
    X.inp("AP-18a", n_periodic, n_cls18)
    col = X.C["AP-18b"]
    col.add(S.group, stage["B3"], b3_18, wlc)
    col.add_classes(rep["ref"], cls_b3)
    col.unit("B3-01", "値（= 段階 B3）").add(b3_ref, b3_18)
    n_cls_rep = sum(1 for a in agg.values() if a["E0r"])
    X.inp("AP-18b", 2 * rep["n_rows"], 2 * n_cls_rep)

    # ---- AP-18c: class-level end-of-life routes
    cls_route, ref_cls_c = {}, {}
    c3_ref, c4_ref, x14 = res["C3-01"]["value"], res["C4-01"]["value"], res["X-14"]["value"]
    ref_c = c3_ref + c4_ref
    n_route_inputs = 0
    for i, row in enumerate(scn.materials):
        eol = row.end_of_life
        if not nonneg(eol.mass_kg):
            continue
        c = cls_route.setdefault(row.material_class, {"mass": 0.0, "rows": 0, "routes": {}})
        c["mass"] += eol.mass_kg
        c["rows"] += 1
        ref_cls_c[row.material_class] = (ref_cls_c.get(row.material_class, 0.0)
                                         + res["C3-01"]["by_item"][i] + res["C4-01"]["by_item"][i])
        for route in eol.routes:
            hit = lookup(scn, route.factor_id, "C4" if route.route == "LANDFILL" else "C3", "kg")
            if hit is None or not nonneg(route.fraction):
                continue
            q = c["routes"].setdefault(route.route, [0.0, 0.0, 0, hit[0]])
            q[0] += route.fraction
            q[1] += hit[1] * hit[0].value
            q[2] += 1
            n_route_inputs += 2
    c_18 = sum(c["mass"] * sum((q[0] / c["rows"]) * (q[1] / q[2]) for q in c["routes"].values()) for c in cls_route.values())

    def part(landfill):
        return {k: c["mass"] * sum((q[0] / c["rows"]) * (q[1] / q[2]) for name, q in c["routes"].items()
                                   if (name == "LANDFILL") == landfill) for k, c in cls_route.items()}

    cls_c3, cls_c4 = part(False), part(True)
    c3_18, c4_18 = sum(cls_c3.values()), sum(cls_c4.values())
    col = X.C["AP-18c"]
    col.add(S.group, ref_c, c_18, wlc)
    col.add_classes(ref_cls_c, {k: cls_c3[k] + cls_c4[k] for k in cls_route})
    col.add_stage("C3", stage["C3"], c3_18 + x14)
    col.add_stage("C4", stage["C4"], c4_18)
    col.other(C34_LABEL).add(stage["C3"] + stage["C4"], c_18 + x14)
    col.unit("C3-01", "値").add(c3_ref, c3_18)
    col.unit("C4-01", "値（= 段階 C4）").add(c4_ref, c4_18)
    col.unit("X-09", "値（= C3-01＋C4-01）").add(res["X-09"]["value"], c_18)
    n_cls_routes = 2 * sum(len(c["routes"]) for c in cls_route.values())
    X.inp("AP-18c", n_route_inputs, n_cls_routes)

    def edit(p):
        made = set()
        for row in scn.materials:
            eol = row.end_of_life
            if not nonneg(eol.mass_kg):
                continue
            c = cls_route[row.material_class]
            new = []
            for route in eol.routes:
                q = c["routes"].get(route.route)
                if q is None:                        # no usable route of this kind in the class: the candidate books nothing
                    new.append(EolRoute(route.route, 0.0, route.factor_id))
                    continue
                fid = f"APPROX-AP18C/{row.material_class}/{route.route}"
                if fid not in made:
                    made.add(fid)
                    p.put(scn.factors, fid, dataclasses.replace(
                        q[3], factor_id=fid, value=q[1] / q[2], unit="kg", stages=["C4" if route.route == "LANDFILL" else "C3"],
                        gas_amounts={g: 0.0 for g in q[3].gas_amounts}))
                new.append(EolRoute(route.route, q[0] / c["rows"], fid))
            p.set(eol, "routes", new)

    S.propagate(col, edit, check_value=c_18, check_of=lambda new: new["X-02"]["by_stage_all"]["C3"] - x14 + new["X-02"]["by_stage_all"]["C4"])

    # ---- AP-18: the three class models at once
    col = X.C["AP-18"]
    col.add(S.group, stage["B3"] + stage["B4"] + ref_c, b3_18 + b4_18 + c_18, wlc)
    col.add_stage("B3", stage["B3"], b3_18)
    col.add_stage("B4", stage["B4"], b4_18)
    col.add_stage("C3", stage["C3"], c3_18 + x14)
    col.add_stage("C4", stage["C4"], c4_18)
    col.unit("B3-01", "値（= 段階 B3）").add(b3_ref, b3_18)
    col.unit("B4-02", "値（= 段階 B4）").add(res["B4-02"]["value"], b4_18)
    col.unit("C3-01", "値").add(c3_ref, c3_18)
    col.unit("C4-01", "値（= 段階 C4）").add(c4_ref, c4_18)
    X.inp("AP-18", n_periodic + 2 * rep["n_rows"] + n_route_inputs, n_cls18 + 2 * n_cls_rep + n_cls_routes)

    if S.load:
        pairs = [(r["cycle"], r["e0"] * r["r"]) for r in rows
                 if nonneg(r["r"]) and r["e0"] * r["r"] and positive(r["cycle"]) and not r["explicit"]]
        fixed = sum(rep["fixed"].values())
        exact = (sp.k_repair, sp.years_exact, T, pairs)
        check = (sp.k_repair(sp.years_exact, T, pairs) + fixed, stage["B3"])
        extra = {"n_distinct_cycles": len({c for c, _ in pairs})}
        X.load.pair("AP-04", len(pairs), (sp.k_repair, sp.years_ap04, T, pairs), exact, check, extra)
        X.load.pair("AP-23a", len(pairs), (sp.k_repair, sp.years_ap23, T, pairs), exact, check, extra)
        classes = [(p[0], p[1]) for p in rep["par"].values() if p[0]]
        X.load.pair("AP-23b", len(pairs), (sp.k_repair_class, T, classes), exact, check, {"n_classes": len(classes)})

    return {"cls18": {k: (a["E0"], a["E0r"], a["U"], a["U_over_c"]) for k, a in agg.items()},
            "cls23": {k: tuple(p) for k, p in rep["par"].items()}, "fixed23": dict(rep["fixed"]),
            "b3": stage["B3"], "b3_cls": dict(rep["ref"]), "ap18b": b3_18, "ap23b": cls23}


def repair_forms(scn) -> dict:
    """Stage errors of AP-04, AP-23a and AP-23b on one scenario (used for the stress scenarios)."""
    S = One(scn, registry.run_all(scn))
    rep = repairs_by_class(S)
    b3 = S.stage["B3"]
    return {"b3": b3, "wlc": S.wlc, "ap04": S.res["B3-02"]["value"], "row": sum(rep["row"].values()),
            "cls": sum(rep["cls"].values()), "below_one": rep["below_one"]}


# ----------------------------------------------------------------- refrigerants: AP-05a, AP-05b

def m_refrigerants(S: One, X: Study):
    scn, res, T, stage, wlc = S.scn, S.res, S.T, S.stage, S.wlc
    total = {"AP-05a": 0.0, "AP-05b": 0.0}
    leak = 0.0
    loss = {"AP-05a": 0.0, "AP-05b": 0.0}
    end = {"AP-05a": 0.0, "AP-05b": 0.0}
    valid = []
    for d, (dev, st) in enumerate(zip(scn.refrigerants, res["B1-02"]["_state"])):
        if st is None:
            continue
        m0, r = dev.charge_mass_kg, dev.annual_leak_rate
        n_ev = len(st["before_events"])
        years = [y for y, _ in st["before_events"]]
        _, before_a, end_a = sp.linear_refrigerant(T, dev, years, True)
        approx = {"AP-05b": m0 * r * T, "AP-05a": m0 * r * T}        # the leak is the same in both variants
        exact_dev = res["B1-02"]["by_item"][d] / dev.gwp if dev.gwp else 0.0
        leak += m0 * r * T * dev.gwp
        if ratio(dev.replacement_loss_rate):
            approx["AP-05b"] += n_ev * m0 * dev.replacement_loss_rate
            approx["AP-05a"] += before_a * dev.replacement_loss_rate
            exact_dev += sum(m for _, m in st["before_events"]) * dev.replacement_loss_rate
            loss["AP-05b"] += n_ev * m0 * dev.replacement_loss_rate * dev.gwp
            loss["AP-05a"] += before_a * dev.replacement_loss_rate * dev.gwp
        if ratio(dev.end_of_life_recovery_rate):
            approx["AP-05b"] += m0 * (1.0 - dev.end_of_life_recovery_rate)
            approx["AP-05a"] += end_a * (1.0 - dev.end_of_life_recovery_rate)
            exact_dev += st["end"] * (1.0 - dev.end_of_life_recovery_rate)
            end["AP-05b"] += m0 * (1.0 - dev.end_of_life_recovery_rate) * dev.gwp
            end["AP-05a"] += end_a * (1.0 - dev.end_of_life_recovery_rate) * dev.gwp
        if ratio(dev.replacement_loss_rate) and ratio(dev.end_of_life_recovery_rate):
            valid.append(dev)
        for cid in total:
            total[cid] += approx[cid] * dev.gwp
        if not dev.top_up and exact_dev > 0.0:
            rk = r * T / (n_ev + 1)
            key = "rk<=0.05" if rk <= 0.05 else "0.05<rk<=0.2" if rk <= 0.2 else "rk>0.2"
            for cid in total:
                X.guard[cid][key].add(exact_dev, approx[cid], ratio_form=True)
    for cid in total:
        col = X.C[cid]
        col.add(S.group, stage["B1"], total[cid], wlc)
        col.unit("B1-02", "値（使用期間の漏洩）").add(res["B1-02"]["value"], leak)
        col.unit("B1-03", "値（更新時の漏洩）").add(res["B1-03"]["value"], loss[cid])
        col.unit("B1-04", "値（廃棄時の未回収）").add(res["B1-04"]["value"], end[cid])
    if S.load and valid:
        exact = (sp.k_devices, sp.device_exact, T, valid)
        check = (sp.k_devices(sp.device_exact, T, valid), stage["B1"]) if len(valid) == len(scn.refrigerants) else None
        X.load.pair("AP-05a", len(valid), (sp.k_devices, sp.device_ap05a, T, valid), exact, check)
        X.load.pair("AP-05b", len(valid), (sp.k_devices, sp.device_ap05b, T, valid), exact, check)


# ----------------------------------------------------------------- material rows: AP-06, AP-06b, AP-19a/b/c, AP-12

def m_material_rows(S: One, X: Study) -> dict:
    scn, res, stage, wlc = S.scn, S.res, S.stage, S.wlc
    mats = scn.materials
    emis, extra = [], []
    for i in range(len(mats)):
        emis.append(res["A13-01"]["by_item"][i] + res["A13-03"]["by_item"][i])
        extra.append(res["A13-04"]["by_item"][i])

    # ---- AP-06: order quantity Q(1+w) instead of Q/(1-w)
    col = X.C["AP-06"]
    q_o, q_i, net13 = res["A13-05"]["q_ord"], res["A13-05"]["q_inst"], res["X-13"]["by_item"]
    approx_a, ref_cls6, cls6 = res["X-01"]["value"], {}, {}
    own = col.unit("A13-05", "行ごとの発注量", level="ROW")
    for i, row in enumerate(mats):
        e = emis[i] + extra[i]
        scale = 1.0
        if row.quantity_basis == "DESIGN" and row.waste_rate is not None and 0.0 <= row.waste_rate < 1.0:
            scale = (1.0 + row.waste_rate) * (1.0 - row.waste_rate)
            if q_o[i] is not None and q_o[i] > q_i[i]:
                own.add(q_o[i], q_i[i] * (1.0 + row.waste_rate))
        approx_a += e * scale
        ref_cls6[row.material_class] = ref_cls6.get(row.material_class, 0.0) + e
        cls6[row.material_class] = cls6.get(row.material_class, 0.0) + e * scale
    col.add(S.group, stage["A1-A3"], approx_a, wlc)
    col.add_classes(ref_cls6, cls6)

    def edit06(p):
        for row in mats:
            if row.quantity_basis == "DESIGN" and row.waste_rate is not None and 0.0 <= row.waste_rate < 1.0:
                p.set(row, "waste_rate", row.waste_rate / (1.0 + row.waste_rate))      # 1/(1-w') = 1+w

    S.propagate(col, edit06, check_value=approx_a, check_of=lambda new: new["X-02"]["by_stage_all"]["A1-A3"])

    # ---- AP-06b: net order quantity with reuse of offcuts, linearised the same way (row level; quantities have row units)
    own = X.C["AP-06b"].unit("X-13", "行ごとの正味発注量", level="ROW")
    rows13 = []
    for i, row in enumerate(mats):
        if row.quantity_basis != "DESIGN" or net13[i] is None or not q_o[i] or not q_o[i] > q_i[i] or not net13[i]:
            continue
        w_i = 1.0 - q_i[i] / q_o[i]
        keep = (net13[i] - q_i[i]) / (q_o[i] - q_i[i])          # 1 - reuse rate
        own.add(net13[i], q_i[i] * (1.0 + w_i * keep), ratio_form=True)
        rows13.append((q_i[i], w_i, 1.0 - keep))
    if S.load:
        rows06 = [(row.quantity, row.waste_rate) for i, row in enumerate(mats)
                  if row.quantity_basis == "DESIGN" and q_o[i] is not None]
        X.load.pair("AP-06", len(rows06), (sp.k_order, sp.order_ap06, rows06), (sp.k_order, sp.order_exact, rows06))
        X.load.pair("AP-06b", len(rows13), (sp.k_net, sp.net_ap06b, rows13), (sp.k_net, sp.net_exact, rows13))

    # ---- AP-19a/b/c: one unquantified ratio instead of one per row
    ratios = [(emis[i], row.unquantified_cost_ratio) for i, row in enumerate(mats)
              if row.unquantified_cost_ratio is not None and 0.0 < row.unquantified_cost_ratio < 1.0]
    if ratios:
        ref19 = res["A13-04"]["value"]
        base = sum(e for e, _ in ratios)
        rbar = sum(r for _, r in ratios) / len(ratios)
        rmax = max(r for _, r in ratios)
        rall = sum(r for _, r in ratios) / len(mats)             # mean over ALL rows (rows without a ratio count as 0)
        ref_cls, base_cls, all_cls = {}, {}, {}
        for i, row in enumerate(mats):
            k = row.material_class
            ref_cls[k] = ref_cls.get(k, 0.0) + extra[i]
            all_cls[k] = all_cls.get(k, 0.0) + emis[i]
            if row.unquantified_cost_ratio is not None and 0.0 < row.unquantified_cost_ratio < 1.0:
                base_cls[k] = base_cls.get(k, 0.0) + emis[i]
        has_ratio = lambda row: row.unquantified_cost_ratio is not None and 0.0 < row.unquantified_cost_ratio < 1.0
        for cid, value, rate, basis, members in (("AP-19a", base * rbar / (1.0 - rbar), rbar, base_cls, has_ratio),
                                                 ("AP-19b", base * rmax / (1.0 - rmax), rmax, base_cls, has_ratio),
                                                 ("AP-19c", sum(emis) * rall / (1.0 - rall), rall, all_cls, lambda row: True)):
            col = X.C[cid]
            col.add(S.group, ref19, value, wlc)
            col.add_classes(ref_cls, {k: v * rate / (1.0 - rate) for k, v in basis.items()})
            col.unit("A13-04", "値").add(ref19, value)
            X.inp(cid, len(ratios), 1)

            def edit19(p, rate=rate, members=members):
                for row in mats:
                    if members(row):
                        p.set(row, "unquantified_cost_ratio", rate)

            S.propagate(col, edit19, check_value=value, check_of=lambda new: new["A13-04"]["value"], check_unit="A13-04")

    # ---- AP-12: only the rows with the largest masses in detail, the rest by mass
    masses = [row.end_of_life.mass_kg or 0.0 for row in mats]
    mat_ref = sum(emis)
    if mat_ref > 0.0 and len(masses) >= 10:
        order = sorted(range(len(masses)), key=lambda i: -masses[i])
        top = order[: max(1, len(order) // 5)]
        m_top, e_top = sum(masses[i] for i in top), sum(emis[i] for i in top)
        col = X.C["AP-12"]
        col.add(S.group, mat_ref, e_top * sum(masses) / m_top if m_top else 0.0, wlc)
        # the same estimate row by row: detailed value for the top rows, mass x (emission per mass of the top rows) for the rest
        in_top = set(top)
        per_kg = e_top / m_top if m_top else 0.0
        ref_cls, est_cls = {}, {}
        est_unit = {"A13-01": 0.0, "A13-03": 0.0}
        for i, row in enumerate(mats):
            est = emis[i] if i in in_top else masses[i] * per_kg
            ref_cls[row.material_class] = ref_cls.get(row.material_class, 0.0) + emis[i]
            est_cls[row.material_class] = est_cls.get(row.material_class, 0.0) + est
            est_unit["A13-03" if res["X-15"]["kind"][i] == "EPD" else "A13-01"] += est
        col.add_classes(ref_cls, est_cls)
        col.unit("A13-01", "値（EPD を使わない行）").add(res["A13-01"]["value"], est_unit["A13-01"])
        col.unit("A13-03", "値（EPD を使う行）").add(res["A13-03"]["value"], est_unit["A13-03"])
        X.inp("AP-12", len(masses), len(top))
    return {"emis": emis, "mat_ref": mat_ref}


# ----------------------------------------------------------------- composites: AP-07a, AP-07b

def m_composites(S: One, X: Study):
    scn, res, wlc = S.scn, S.res, S.wlc
    parts, rx, q_ord = res["A13-02"]["_parts"], res["X-15"], res["A13-05"]["q_ord"]
    ref_x3 = cut = cut_norm = 0.0
    ref_c7, cut_c7, norm_c7 = {}, {}, {}
    own_a = X.C["AP-07a"].unit("A13-02", "行ごとの複合係数", level="ROW")
    own_b = X.C["AP-07b"].unit("A13-02", "行ごとの複合係数", level="ROW")
    n_comp = n_kept = n_rows = 0
    kernel_rows = []
    for i, row in enumerate(scn.materials):
        if rx["kind"][i] != "COMPOSITE" or q_ord[i] is None:
            continue
        kg = q_ord[i] * rx["conv"][i]
        full = sum(frac * c * scn.factors[fid].value for fid, frac, c in parts[i])
        kept = [(fid, frac, c) for fid, frac, c in parts[i] if frac >= 0.05]
        part = sum(frac * c * scn.factors[fid].value for fid, frac, c in kept)
        share = sum(frac for _, frac, _ in kept)
        ref_x3 += kg * full
        cut += kg * part
        cut_norm += kg * part / share if share else 0.0
        k = row.material_class
        ref_c7[k] = ref_c7.get(k, 0.0) + kg * full
        cut_c7[k] = cut_c7.get(k, 0.0) + kg * part
        norm_c7[k] = norm_c7.get(k, 0.0) + (kg * part / share if share else 0.0)
        own_a.add(full, part)
        own_b.add(full, part / share if share else 0.0)
        n_rows += 1
        n_comp += len(parts[i])
        n_kept += len(kept)
        if S.load:
            kernel_rows.append((kg, [(frac, c * scn.factors[fid].value) for fid, frac, c in parts[i]]))
    for cid, value, by_class in (("AP-07a", cut, cut_c7), ("AP-07b", cut_norm, norm_c7)):
        col = X.C[cid]
        col.add(S.group, ref_x3, value, wlc)
        col.add_classes(ref_c7, by_class)
        col.unit("X-03", "値（複合品の製造排出）").add(res["X-03"]["value"], value)
        if n_rows:
            X.inp(cid, n_comp / n_rows, n_kept / n_rows)

    def edit(p, renormalise):
        for i, row in enumerate(scn.materials):
            if row.composition is None or parts[i] is None:
                continue
            kept = [c for c in row.composition if c.mass_fraction >= 0.05]
            share = sum(c.mass_fraction for c in kept)
            if renormalise and kept:
                p.set(row, "composition", [CompositeComponent(c.factor_id, c.mass_fraction / share) for c in kept])
                continue
            new = []                                 # the dropped components keep their mass fraction and get a factor of value 0
            for c in row.composition:
                if c.mass_fraction >= 0.05 and not renormalise:
                    new.append(c)
                    continue
                zero = c.factor_id + "/APPROX-ZERO"
                if zero not in scn.factors:
                    rec = scn.factors[c.factor_id]
                    p.put(scn.factors, zero, dataclasses.replace(rec, factor_id=zero, value=0.0,
                                                                 gas_amounts={g: 0.0 for g in rec.gas_amounts}))
                new.append(CompositeComponent(zero, c.mass_fraction))
            p.set(row, "composition", new)

    for cid, value, renormalise in (("AP-07a", cut, False), ("AP-07b", cut_norm, True)):
        S.propagate(X.C[cid], lambda p, f=renormalise: edit(p, f), check_value=value,
                    check_of=lambda new: new["X-03"]["value"], check_unit="X-03")
    if S.load and kernel_rows:
        exact = (sp.k_recipes, sp.recipe_exact, kernel_rows)
        check = (sp.k_recipes(sp.recipe_exact, kernel_rows), ref_x3)
        extra = {"n_distinct_recipes": len({tuple(p) for _, p in kernel_rows})}
        X.load.pair("AP-07a", len(kernel_rows), (sp.k_recipes, sp.recipe_ap07a, kernel_rows), exact, check, extra)
        X.load.pair("AP-07b", len(kernel_rows), (sp.k_recipes, sp.recipe_ap07b, kernel_rows), exact, check, extra)


# ----------------------------------------------------------------- transport: AP-17

def m_transport(S: One, X: Study):
    scn, res, stage, wlc = S.scn, S.res, S.stage, S.wlc
    mats = scn.materials
    col = X.C["AP-17"]
    modes, row_mode = {}, {}
    for i, row in enumerate(mats):
        if not res["A4-01"]["_row_lines"][i]:
            continue
        tr = row.transport
        hit = lookup(scn, tr.factor_id, "A4", "tkm")
        m = modes.setdefault(tr.factor_id, [0.0, 0.0, 0, hit[1] * hit[0].value, []])
        m[0] += tr.mass_t
        m[1] += tr.distance_km
        m[2] += 1
        m[4].append((tr.mass_t, tr.distance_km))
        row_mode[i] = m
    rows_17 = sum(m[0] * (m[1] / m[2]) * m[3] for m in modes.values())
    a4_17 = res["A4-02"]["value"] + rows_17
    col.add(S.group, stage["A4"], a4_17, wlc)
    col.unit("A4-01", "値").add(res["A4-01"]["value"], rows_17)
    ref_cls, est_cls = {}, {}
    for i, row in enumerate(mats):
        k = row.material_class
        ref_cls[k] = ref_cls.get(k, 0.0) + res["A4-01"]["by_item"][i] + res["A4-02"]["by_item"][i]
        m = row_mode.get(i)
        est = row.transport.mass_t * (m[1] / m[2]) * m[3] if m is not None else res["A4-02"]["by_item"][i]
        est_cls[k] = est_cls.get(k, 0.0) + est
    col.add_classes(ref_cls, est_cls)
    X.inp("AP-17", len(row_mode), len(modes))

    # the error of the simple mean distance is the within-mode sample covariance of mass and distance:
    # sum(m*d) - sum(m)*mean(d) = sum((m - mean m)*(d - mean d))
    a4_rows = res["A4-01"]["value"]
    if a4_rows:
        cov_term, weighted_r, weight = 0.0, 0.0, 0.0
        for m in modes.values():
            n = m[2]
            mb, db = m[0] / n, m[1] / n
            sxy = sum((a - mb) * (d - db) for a, d in m[4])
            sxx = sum((a - mb) ** 2 for a, _ in m[4])
            syy = sum((d - db) ** 2 for _, d in m[4])
            cov_term += m[3] * sxy
            if n >= 5 and sxx > 0.0 and syy > 0.0:
                e_mode = m[3] * sum(a * d for a, d in m[4])
                weighted_r += e_mode * sxy / math.sqrt(sxx * syy)
                weight += e_mode
        X.cov["n"] += 1
        X.cov["worst"] = max(X.cov["worst"], abs((a4_rows - rows_17) - cov_term) / a4_rows)
        if weight:
            X.cov["pairs"].append(((rows_17 - a4_rows) / a4_rows, weighted_r / weight))

    def edit(p):
        for i, m in row_mode.items():
            p.set(mats[i].transport, "distance_km", m[1] / m[2])

    S.propagate(col, edit, check_value=a4_17, check_of=lambda new: new["X-02"]["by_stage_all"]["A4"])

    # the same mean distance on X-12 (activity divided by the load factor) and on the haul of C2
    m12 = {}
    for i, row in enumerate(mats):
        tr = row.transport
        hit = lookup(scn, tr.factor_id, "A4", "tkm") if tr.delivery_factor_id is None else None
        if hit is None or not nonneg(tr.mass_t) or not nonneg(tr.distance_km) or not (tr.load_factor is not None and tr.load_factor > 0.0):
            continue
        m = m12.setdefault(tr.factor_id, [0.0, 0.0, 0, hit[1] * hit[0].value])
        m[0] += tr.mass_t / tr.load_factor
        m[1] += tr.distance_km
        m[2] += 1
    col.unit("X-12", "値（参考値）").add(res["X-12"]["value"], sum(m[0] * (m[1] / m[2]) * m[3] for m in m12.values()), ratio_form=True)
    hauls, c2_rows = {}, 0.0
    for i, row in enumerate(mats):
        if not res["C2-01"]["_row_lines"][i]:
            continue
        eol = row.end_of_life
        hit = lookup(scn, eol.haul_factor_id, "C2", "tkm")
        m = hauls.setdefault(eol.haul_factor_id, [0.0, 0.0, 0, hit[1] * hit[0].value])
        m[0] += eol.mass_kg / 1000.0
        m[1] += eol.haul_distance_km
        m[2] += 1
        c2_rows += res["C2-01"]["by_item"][i]
    col.unit("C2-01", "値（= 段階 C2。搬出距離を単純平均に置換）").add(
        stage["C2"], stage["C2"] - c2_rows + sum(m[0] * (m[1] / m[2]) * m[3] for m in hauls.values()), ratio_form=True)


# ----------------------------------------------------------------- electricity: AP-08, AP-09a/b/c, AP-13, AP-24b

def profile_inputs(profile, Y: int) -> int:
    """Number of values an annual profile needs as input."""
    if profile_uses_descriptor(profile):
        return 1 if profile.kind == "CONSTANT" else 2
    return Y


def grid_inputs(grid, Y: int, source: str) -> int:
    if source != "DESCRIPTOR":
        return Y
    if grid.kind == "CONSTANT":
        return 1
    if grid.kind == "LINEAR_DECLINE_TO_FLOOR":
        return 3
    return 2 * sum(1 for step in grid.steps if step.from_index < Y)


def m_electricity(S: One, X: Study):
    scn, res, T, w, Y, stage, wlc = S.scn, S.res, S.T, S.w, S.Y, S.stage, S.wlc
    op = scn.operation
    g = res["X-06"]["by_year"]
    eu, gu = annual_unit(op.electricity.unit), grid_unit(op.grid)
    conv = convert(scn, eu, gu) if eu is not None and gu is not None else None
    if not (res["B6-01"]["computed"] and conv is not None):
        return
    net = [v * conv for v in res["B6-04"]["by_year"]]
    elec_ref = sum(w[y] * net[y] * g[y] for y in range(1, Y + 1))
    b6_ref = res["B6-03"]["value"]
    fuel = b6_ref - elec_ref
    if not elec_ref > 0.0:
        return
    share = op.facility_management_ratio if res["B2-01"]["computed"] else 0.0
    source = res["X-06"]["source"]
    profiles = (op.electricity, op.onsite_generation, op.onsite_export)

    def book(cid, approx_elec, approx_b603):
        """Record a candidate value of the purchased-electricity emission on the stages B6 and B2 and on B6-03."""
        d = approx_elec - elec_ref
        col = X.C[cid]
        e6 = stage["B6"] + d * (1.0 - share)
        e2 = stage["B2"] + d * share
        col.add(S.group, stage["B6"], e6, wlc, total_diff=approx_b603 - b6_ref)
        col.add_stage("B6", stage["B6"], e6)
        col.add_stage("B2", stage["B2"], e2)
        col.other(B603_LABEL).add(b6_ref, approx_b603)
        return {"B6": (stage["B6"], e6), "B2": (stage["B2"], e2), "B6-03": (b6_ref, approx_b603)}

    # ---- AP-08: mean demand x mean factor
    mean_net = sum(w[y] * net[y] for y in range(1, Y + 1)) / T
    mean_g = sum(w[y] * g[y] for y in range(1, Y + 1)) / T
    approx = mean_net * mean_g * T + fuel
    v = book("AP-08", mean_net * mean_g * T, approx)
    col = X.C["AP-08"]
    col.unit("B6-01", "年重み付き合計（買電排出）").add(elec_ref, mean_net * mean_g * T)
    col.unit("B6-03", "値（= B6＋B2）").add(b6_ref, approx)
    col.unit("B2-01", "値（= 段階 B2）").add(*v["B2"])
    kinds = {op.electricity.kind, op.onsite_generation.kind, op.onsite_export.kind}
    key = "CONSTANT" if kinds == {"CONSTANT"} else "TABLE" if "TABLE" in kinds else "LINEAR_TREND"
    for name, (ref, cand) in v.items():
        X.kind8[name][key].add(ref, cand)
    n_profile_inputs = sum(profile_inputs(p, Y) for p in profiles)
    X.inp("AP-08", n_profile_inputs + grid_inputs(op.grid, Y, source), 2)

    # ---- AP-09a/b: grid factor from points every 5 / 10 years; AP-09c: only when the series is a year table
    G = sum(w[y] * g[y] for y in range(1, Y + 1))
    for cid, step in (("AP-09a", 5), ("AP-09b", 10)):
        gi = [0.0] + sp.coarse(g[1:], step)
        approx_elec = sum(w[y] * net[y] * gi[y] for y in range(1, Y + 1))
        approx = approx_elec + fuel
        Gi = sum(w[y] * gi[y] for y in range(1, Y + 1))
        v = book(cid, approx_elec, approx)
        X.C[cid].unit("X-06", "年重み付き合計 G(T)").add(G, Gi)
        for name, (ref, cand) in v.items():
            X.grid9.setdefault(cid, {}).setdefault(name, {}).setdefault(op.grid.kind, Series()).add(ref, cand)
        X.inp(cid, grid_inputs(op.grid, Y, source), sp.n_nodes(Y, step))
        X.inp(f"{cid}|{source}", grid_inputs(op.grid, Y, source), sp.n_nodes(Y, step))
        if cid == "AP-09a":
            if source == "TABLE":
                book("AP-09c", approx_elec, approx)
                X.C["AP-09c"].unit("X-06", "年重み付き合計 G(T)").add(G, Gi)
                X.C["AP-09c"].unit("B6-01", "年重み付き合計（買電排出）").add(elec_ref, approx_elec)
                X.inp("AP-09c", Y, sp.n_nodes(Y, step))
            else:
                X.exact_scenarios["AP-09c"] += 1

    # ---- AP-13: purchased electricity from the floor-area intensity (X-11)
    x11 = res["X-11"]["value"]
    if x11 is not None:
        book("AP-13", x11, x11 + fuel)
        col = X.C["AP-13"]
        col.unit("B6-01", "年重み付き合計（買電排出）").add(elec_ref, x11)
        col.unit("X-11", "値（B6-01 の年重み付き合計と比べた）", role="IS_THE_CANDIDATE").add(elec_ref, x11)
        X.inp("AP-13", n_profile_inputs, 2)

    # ---- AP-24b: electricity quantities given as year tables kept every 5 years
    tables = [p for p in profiles if not profile_uses_descriptor(p)]
    if tables:
        gun, xun = annual_unit(op.onsite_generation.unit), annual_unit(op.onsite_export.unit)
        cg, cx = convert(scn, gun, eu), convert(scn, xun, eu)
        c, gen, exp = (sp.coarse(profile_values(p, Y), 5) if not profile_uses_descriptor(p) else profile_values(p, Y)
                       for p in profiles)
        net24 = [0.0] + [max(0.0, c[k] - (gen[k] * cg - exp[k] * cx)) for k in range(Y)]
        approx_elec = sum(w[y] * net24[y] * conv * g[y] for y in range(1, Y + 1))
        book("AP-24b", approx_elec, approx_elec + fuel)
        col = X.C["AP-24b"]
        col.unit("B6-04", "年重み付き合計（買電量）").add(sum(w[y] * res["B6-04"]["by_year"][y] for y in range(1, Y + 1)),
                                                 sum(w[y] * net24[y] for y in range(1, Y + 1)))
        col.unit("B6-01", "年重み付き合計（買電排出）").add(elec_ref, approx_elec)
        X.inp("AP-24b", Y * len(tables), sp.n_nodes(Y, 5) * len(tables))
    else:
        X.exact_scenarios["AP-24b"] += 1

    if S.load:
        X.load.pair("AP-08:scan", Y, (sp.elec_ap08_scan, T, w, net, g), (sp.elec_exact_scan, T, w, net, g),
                    (sp.elec_exact_scan(T, w, net, g), elec_ref))
        segments = cf.grid_segments(op.grid, Y) if source == "DESCRIPTOR" else None
        if segments is not None and not tables:
            gun, xun = annual_unit(op.onsite_generation.unit), annual_unit(op.onsite_export.unit)
            cg, cx = convert(scn, gun, eu), convert(scn, xun, eu)
            cp, gp, xp = profiles
            B = (cp.base - (gp.base * cg - xp.base * cx)) * conv
            S_ = ((cp.slope or 0.0) - ((gp.slope or 0.0) * cg - (xp.slope or 0.0) * cx)) * conv
            if B >= 0.0 and B + S_ * (Y - 1) >= 0.0:          # the clamp max(0, .) does not act at either end
                X.load.pair("AP-08:closed", 1, (sp.elec_ap08_closed, T, B, S_, segments), (sp.elec_exact_closed, T, B, S_, segments),
                            (sp.elec_exact_closed(T, B, S_, segments), elec_ref))
        values = g[1:]
        for cid, step in (("AP-09a", 5), ("AP-09b", 10)):
            nodes = [values[k] for k in sorted({(k // step) * step for k in range(Y)} | {Y - 1})]
            candidate = (sp.moments_from_nodes, T, Y, step, nodes)
            if source == "DESCRIPTOR":
                exact = (lambda: cf.segment_moments(cf.grid_segments(op.grid, Y), T),)
                got = cf.segment_moments(cf.grid_segments(op.grid, Y), T)[0]
            else:
                exact = (cf.table_moments, op.grid.table, T)
                got = cf.table_moments(op.grid.table, T)[0]
            X.load.pair(f"{cid}:{source}", Y, candidate, exact, (got, G))


# ----------------------------------------------------------------- annual quantities as year tables: AP-24a

def m_annual_tables(S: One, X: Study):
    scn, res, w, Y, stage, wlc = S.scn, S.res, S.w, S.Y, S.stage, S.wlc
    op, ww = scn.operation, scn.water_waste
    col = X.C["AP-24a"]
    series = (("B6-02", "B6", ((op.gas, op.gas_factor_id), (op.oil, op.oil_factor_id), (op.district_heat, op.district_heat_factor_id))),
              ("B7-01", "B7", ((ww.water, ww.water_factor_id),)), ("B7-02", "B7", ((ww.sewage, ww.sewage_factor_id),)),
              ("B7-03", "B7", ((ww.municipal_waste, ww.waste_factor_id),)))
    delta = {"B6": 0.0, "B7": 0.0}
    has_table = {"B6": False, "B7": False}
    n_tables = 0
    for uid, st, pairs in series:
        ref_u = cand_u = 0.0
        table_in_unit = False
        for profile, fid in pairs:
            hit = lookup(scn, fid, st, annual_unit(profile.unit))
            values = profile_values(profile, Y)
            if hit is None or values is None:
                continue                               # the reference leaves this series out
            f = hit[1] * hit[0].value
            ref_p = sum(w[y] * values[y - 1] * f for y in range(1, Y + 1))
            ref_u += ref_p
            if profile_uses_descriptor(profile):
                cand_u += ref_p
                continue
            table_in_unit = True
            n_tables += 1
            coarse = sp.coarse(values, 5)
            cand_u += sum(w[y] * coarse[y - 1] * f for y in range(1, Y + 1))
            if S.load:
                nodes = [values[k] for k in sorted({(k // 5) * 5 for k in range(Y)} | {Y - 1})]
                X.load.pair("AP-24a", Y, (sp.weighted_from_nodes, S.T, Y, 5, nodes), (sp.weighted_table, S.T, values),
                            (sp.weighted_table(S.T, values) * f, ref_p))
        own = sum(w[y] * res[uid]["by_year"][y] for y in range(1, Y + 1))
        if own:
            X.worst["annual"] = max(X.worst["annual"], abs(ref_u - own) / own)
        if table_in_unit:
            col.unit(uid, "年重み付き合計").add(ref_u, cand_u)
            delta[st] += cand_u - ref_u
            has_table[st] = True
    if not (has_table["B6"] or has_table["B7"]):
        X.exact_scenarios["AP-24a"] += 1
        return
    ref = sum(w[y] * res["B6-02"]["by_year"][y] for y in range(1, Y + 1)) + res["B7-04"]["value"]
    col.add(S.group, ref, ref + delta["B6"] + delta["B7"], wlc)
    for st in ("B6", "B7"):
        if has_table[st]:
            col.add_stage(st, stage[st], stage[st] + delta[st])
    X.inp("AP-24a", Y * n_tables, sp.n_nodes(Y, 5) * n_tables)


# ----------------------------------------------------------------- gases: AP-22a (and the load of AP-22b)

def m_gases(S: One, X: Study):
    scn, res = S.scn, S.res
    total_inc = S.sum03
    col = X.C["AP-22a"]
    col.add(S.group, total_inc, res["X-05"]["value"], total_inc)
    col.unit("X-04", "値（14 段階の全ガスの合計）").add(res["X-04"]["value"], sum(res["X-05"]["by_stage_co2"].values()))
    n_used = len(res["X-04"]["_used"])
    X.inp("AP-22a", n_used * len(res["X-04"]["by_gas"]), n_used)
    X.inp("AP-22b", n_used, 1)
    if S.load:
        activity, grid = {}, 0.0
        for lines in stage_lines(scn, res).values():
            for fid, act in lines:
                if fid is GRID:
                    grid += act
                elif fid is not REFRIGERANT:
                    activity[fid] = activity.get(fid, 0.0) + act
        entries = [(act, scn.factors[fid].gas_amounts.get("CO2", 0.0)) for fid, act in activity.items()] + [(grid, 1.0)]
        co2_all = sum(res["X-05"]["by_stage_co2"].values())
        X.load.pair("AP-22b", len(entries), (sp.co2_ap22b, 0.5, co2_all), (sp.co2_exact, entries), (sp.co2_exact(entries), co2_all))


def boundary_case() -> dict:
    """A scenario whose only life lies within a relative 1e-9 below a divisor of T: what the bracket test gives."""
    T, life = 60.0, 19.99999999
    scn = make_scenario(11, "RC", "office", "S", T, n_materials=12, n_equipment=6, n_refrigerants=2,
                        service_life_choices=[life], explicit_event_share=0.0, change_list_share=0.0)
    res = registry.run_all(scn)
    rows = renewal_rows(scn, res)
    b4 = res["X-02"]["by_stage_all"]["B4"]
    lo = sum(max(0.0, T / r["cycle"] - 1.0) * r["u"] for r in rows)
    lo_tol = sum(max(0.0, T * sp.C_TOL / r["cycle"] - 1.0) * r["u"] for r in rows)
    hi = sum(T / r["cycle"] * r["u"] for r in rows)
    return {"description": "評価期間 60 年、すべての行の周期が 19.99999999 年（60 の約数 20 を相対 5e-10 だけ下回る）の架空シナリオ。",
            "study_period": T, "life": life, "reference_counts": sorted({r["n"] for r in rows}), "T_over_c_minus_1": T / life - 1.0,
            "T_c0_over_c_minus_1": T * sp.C_TOL / life - 1.0, "reference_B4": b4, "lower_bound_T_over_c_minus_1": lo,
            "lower_bound_exceeds_reference_by_relative": (lo - b4) / b4 if b4 else None,
            "inside_with_lower_bound_T_over_c_minus_1": bool(lo <= b4 * (1 + 1e-12) and b4 <= hi * (1 + 1e-12)),
            "inside_with_lower_bound_T_c0_over_c_minus_1": bool(lo_tol <= b4 * (1 + 1e-12) and b4 <= hi * (1 + 1e-12)),
            "upper_bound_holds": bool(b4 <= hi * (1 + 1e-12)),
            "ap01_error_on_B4": (lo - b4) / b4 if b4 else None}


def stress_repairs(n_seeds: int) -> list[dict]:
    """AP-04, AP-23a and AP-23b on scenarios whose lives are all close to the study period."""
    out = []
    for T, lives in STRESS_CASES:
        case = {"T": T, "lives": lives, "n": 0, "row": [], "cls": [], "ap04": [], "row_total": [], "cls_total": []}
        for seed in range(n_seeds):
            scn = make_scenario(1000 + seed, ("RC", "S", "SRC", "W")[seed % 4], "office", "S", T, service_life_choices=lives,
                                explicit_event_share=0.0, change_list_share=0.0)
            f = repair_forms(scn)
            if not f["b3"]:
                continue
            case["n"] += 1
            for key in ("row", "cls", "ap04"):
                case[key].append((f[key] - f["b3"]) / f["b3"])
            for key in ("row", "cls"):
                case[key + "_total"].append((f[key] - f["b3"]) / f["wlc"])
        out.append(case)
    return out


def sign_guarantee(n_below_one_year_in_population: int) -> dict:
    """Where the safe-side repair forms cannot under-estimate, and a measured case where they do."""
    T, life = 10.5, 0.9
    w = year_weights(T)
    exact_skip = sum(w[y] for y in set(periodic_events(T, life)))
    candidate_skip = min(T, max(0.0, T / life - 1.0))
    errors = []
    for seed in range(3):
        f = repair_forms(make_scenario(3000 + seed, "RC", "office", "S", T, n_materials=12, n_equipment=6, n_refrigerants=2,
                                       service_life_choices=[life], explicit_event_share=0.0, change_list_share=0.0))
        if f["b3"]:
            errors.append((f["row"] - f["b3"]) / f["b3"])
    return {"statement": "周期が 1 年以上なら、更新が属する年の重みの合計は T/c − 1 以上なので、除外する年数を min(T, max(0, T/c − 1)) に置き換えても過小評価にならない"
                         "（時間境界の許容差・相対 1e-9 の範囲で）。区分パラメータの形は、max(0, x − 1) が凸であることから同じ向きになる。"
                         "周期が 1 年未満の行では成り立たない（1 年に 2 回以上の更新があっても除外される年は 1 つなので、候補は除外しすぎる）。"
                         "過大の大きさは周期の分布で決まり、保証はない。",
            "holds_for": "cycles >= 1 year, up to the relative 1e-9 boundary tolerance",
            "n_rows_with_a_cycle_below_one_year_in_the_population": n_below_one_year_in_population,
            "counter_example_below_one_year": {
                "study_period": T, "cycle": life, "exact_excluded_years": exact_skip, "candidate_excluded_years": candidate_skip,
                "scenarios": "評価期間 10.5 年、すべての行の周期が 0.9 年の架空シナリオ 3 件（行ごとの形 AP-23a）", "stage_error": stats(errors)}}
