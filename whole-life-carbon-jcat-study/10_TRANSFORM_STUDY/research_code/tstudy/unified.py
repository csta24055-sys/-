"""The unified system: all 70 evaluation units from the inputs of one building, through two structures.

    System(scenario)        common tables -> masked sum-product 1 -> knot spectra            (once per building)
    System.at(T)            knot spectra at T -> masked sum-product 2 (TIME, AGG) -> results  (any study period)

The reference calculation is NOT used here: nothing in this module imports ``refcalc`` or reads a
reference result. The only link to the earlier study is the scenario object of the generator and the
registry of baseline scenarios (an input of SUM-08).

What this module does besides calling the two structures (and nothing else):
  * builds the common tables declared in ``specs.system.INDEX_PLAN``;
  * places amplitude columns on knots as declared in ``specs.system.EMIT``;
  * copies named scalars between the stages (knot values -> table TT; unit values -> table U);
  * formats the results (lists, dictionaries, labels, number types). No arithmetic on values.

Fictional data, independent concept model; not a statement about any other tool.
"""
from __future__ import annotations

import collections
import math
import time

import numpy as np

from specs import gates, system as S_
from specs.lib import CAL, STATES
from specs.physical import BE, D, DY, EE, EQT, M, MC, OP, RE, RT, WW
from . import index, msp, rampstep as rs, tables
from .interval import IntervalSpectrum
from .knots import KnotSpectrum

P1 = msp.Program(S_.SPEC1)
P_TIME = msp.Program(S_.SPEC_TIME)
P_AGG = msp.Program(S_.SPEC_AGG)
STAGES = S_.STAGES
BASE_TABLES = ("project", "boundary", "boundary.included_lifecycle_stages", "factors", "meta")
B14_MODES = ("interval", "local", "jump")      # representation of the end residual B1-04 (see tstudy/interval.py, EXP-U1)


class Unusable(RuntimeError):
    """An amplitude is missing: the inputs lie outside what the system can evaluate."""


def build_index(tabs) -> float:
    H = tabs.rows[CAL]
    for op in S_.INDEX_PLAN:
        k = op["op"]
        if k == "tokenise":
            index.tokenise(tabs)
        elif k == "product":
            index.add_product(tabs, op["name"], op["parent"], tabs.rows.get(op["other"], 0), op["col"])
        elif k == "events":
            index.add_events(tabs, op["name"], op["parent"], float(H), cycle=op.get("cycle"), lists=op.get("lists"))
        elif k == "sorted":
            index.add_sorted(tabs, op["name"], op["source"], op["by"])
        elif k == "distinct":
            index.add_distinct(tabs, op["name"], [tuple(s) for s in op["sources"]])
        elif k == "static":
            for name, cols in S_.STATIC_TABLES.items():
                index.add_static(tabs, name, cols)
        elif k == "range":
            index.add_range(tabs, op["name"], H + 1, op["col"])
        else:
            raise ValueError(k)
    return float(H)


class _Readout(dict):
    """The results of one read-out pass; remembers which result columns each unit was read from."""

    def __init__(self, system):
        super().__init__()
        self.system = system
        system._seen = set()

    def __setitem__(self, uid, value):
        self.system.read_from[uid] = sorted(self.system._seen)
        self.system._seen = set()
        super().__setitem__(uid, value)


class System:
    def __init__(self, scn, with_base: bool = True, baselines: dict | None = None, b14: str = "interval"):
        assert b14 in B14_MODES
        self.scn, self.b14 = scn, b14
        self.read_from, self._seen = {}, set()         # unit -> (table, column) pairs its read-out used
        t0 = time.perf_counter()
        tabs = tables.from_scenario(scn)
        self.H = build_index(tabs)
        base = (baselines or {}).get(scn.boundary.baseline_scenario) if with_base else None
        index.add_prefixed(tabs, tables.from_scenario(base) if base is not None else None, "base:", BASE_TABLES,
                           {"project": 1, "boundary": 1, "meta": 1})
        self.base_sum3 = None
        if base is not None:
            self.base_sum3 = System(base, with_base=False).at(base.boundary.study_period)["SUM-03"]["value"]
        index.put_table(tabs, "TT", {"T": np.array([1.0])})
        index.put_table(tabs, "U", {"id": index.objects(S_.U_IDS), "value": np.zeros(len(S_.U_IDS)), "bad": np.zeros(len(S_.U_IDS))})
        self.tabs = tabs
        self.eng = msp.Engine(tabs).run(P1)
        self.t_p1 = time.perf_counter() - t0
        t1 = time.perf_counter()
        self.pieces = self._emit()
        self.K = {name: KnotSpectrum(self.pieces.get(name, [])) for name in S_.SPECTRA}
        self.I14 = self._interval()
        self.t_knots = time.perf_counter() - t1
        self.n_knots = sum(k.n_knots for k in self.K.values())
        self.static = self.eng.results(P1, S_.PRE_A_UNITS)
        self.static.update(self._static_results())

    # ---- access to result columns (no arithmetic) -----------------------------------------
    def v(self, table, name):
        self._seen.add((table, name))
        c = self.eng.col(table, name)
        if not bool(c.m.all()):
            raise Unusable(f"{table}.{name} has missing values")
        return c.v

    def s(self, name, table="S"):
        self._seen.add((table, name))
        c = self.eng.col(table, name)
        if not bool(c.m[0]):
            raise Unusable(f"{table}.{name} is missing")
        return float(c.v[0])

    def si(self, name, table="S"):
        x = self.s(name, table)
        if x != math.floor(x):
            raise Unusable(f"{table}.{name} = {x!r} is not a whole number")
        return int(x)

    def flag(self, name, table="S"):
        return bool(self.s(name, table))

    def rows(self, table, name):
        return [float(x) for x in self.v(table, name)] if self.eng.nrows(table) else []

    def marked(self, table, name):
        """Row positions where a 0/1 (or count) column is not zero."""
        return [int(i) for i in np.nonzero(self.v(table, name))[0]] if self.eng.nrows(table) else []

    def text(self, table, name, i):
        self._seen.add((table, name))
        return self.tabs.data[table][name][i]

    # ---- hand-over P1 -> knot spectrum ----------------------------------------------------
    def _emit(self):
        P = collections.defaultdict(list)
        eng, H = self.eng, self.H
        for e in S_.EMIT:
            t = e["table"]
            if not eng.nrows(t):
                continue
            a = self.v(t, e["amp"])
            idx = np.nonzero(a)[0]
            if not len(idx):
                continue
            out, shape = P[e["spectrum"]], e["shape"]
            k = eng.col(t, e["k"]).v if "k" in e else None
            tau = eng.col(t, e["tau"]).v if "tau" in e else None
            if shape == "const":
                out += [rs.constant(float(a[i])) for i in idx]
            elif shape == "density":
                out += [rs.density(float(a[i]), H) for i in idx]
            elif shape == "cell":
                out += [rs.year_cell(float(a[i]), int(k[i]) + 1) for i in idx]
            elif shape == "atom":
                out += [rs.atom(float(a[i]), float(tau[i])) for i in idx]
            elif shape == "gcell":
                out += [rs.year_cell(float(a[i]), int(k[i]) + 1, gate=float(tau[i])) for i in idx]
            else:
                raise ValueError(shape)
        return P

    def _interval(self):
        """Interval form of the end residual: coefficients of each year cell and the non-negative corrections
        of the resets inside the cell."""
        eng = self.eng
        A, B = self.v(CAL, "b1.iA"), self.v(CAL, "b1.iB")
        if not eng.nrows(DY):
            return IntervalSpectrum(A, B, [], [], [], [])
        k, p = self.v(DY, "k"), self.v(DY, "b1.p")
        ea, eg = self.v(DY, "b1.e4a"), self.v(DY, "b1.e4g")
        tau = eng.col(DY, "b1.tau1").v
        idx = [i for i in np.nonzero(p)[0] if ea[i] != 0.0 or eg[i] != 0.0]
        return IntervalSpectrum(A, B, [int(k[i]) for i in idx], [float(tau[i]) for i in idx],
                                [float(ea[i]) for i in idx], [float(eg[i]) for i in idx])

    # ---- one study period --------------------------------------------------------------
    def at(self, T: float) -> dict:
        eng, tabs = self.eng, self.tabs
        T = float(T)
        if not (T > 0.0) or math.isinf(T) or math.ceil(T) > self.H:
            raise ValueError("study period outside (0, length of the year tables]")
        kv = {name: self.K[name].value(T) for name in S_.SPECTRA}
        tt = {"T": np.array([T])}
        tt.update({"K." + n: np.array([x]) for n, x in kv.items()})
        if self.base_sum3 is not None:
            tt["base_sum3"] = np.array([self.base_sum3])
        index.put_table(tabs, "TT", tt)
        for key in [k for k in eng.cols if k[0] in ("TT", "U")]:
            del eng.cols[key]
        eng.run(P_TIME)
        # re-tabulation of unit values and counters: named scalars -> rows of U and columns of TT
        val = {uid: self.s(col) for uid, col in S_.CONST_VALUE.items()}
        for uid, (where, name) in S_.VALUE_AT_T.items():
            val[uid] = kv[name] if where == "K" else self.I14.value(T) if where == "I" else self.s(name, where)
        b14 = {"interval": val["B1-04"], "local": self.s("t.b14"), "jump": kv["B1-04"]}     # three forms of the same quantity
        val["B1-04"] = b14[self.b14]
        bad = {uid: self.s("bad." + uid) for uid in S_.BAD}
        bad["B4-02"] = kv["N.b42"]
        for uid, x in val.items():
            tabs.data["TT"]["V." + uid], tabs.data["TT"]["V." + uid + "?"] = np.array([x]), np.array([True])
        index.put_table(tabs, "U", {"id": index.objects(S_.U_IDS), "value": np.array([val.get(u, 0.0) for u in S_.U_IDS]),
                                    "bad": np.array([bad.get(u, 0.0) for u in S_.U_IDS])})
        eng.run(P_AGG)
        self.last = {"T": T, "K": kv, "val": val, "bad": bad, "b14": b14}
        out = dict(self.static)
        out.update(self._results(T, kv, val))
        return out

    # ---- read-outs: results that do not depend on T -----------------------------------------
    def _static_results(self):
        s, si, flag, rows, marked = self.s, self.si, self.flag, self.rows, self.marked
        r = _Readout(self)
        r["C1-01"] = {"value": s("c11.value"), "n_skipped": si("c11.n_skipped")}
        r["C2-01"] = {"value": s("c21.value"), "by_item": rows(M, "c21.by_item"), "n_skipped": si("c21.n_skipped")}
        for uid, tag in (("C3-01", "c31"), ("C4-01", "c41")):
            r[uid] = {"value": s(tag + ".value"), "by_item": rows(M, tag + ".by_item"), "n_skipped": si(tag + ".nsk"),
                      "n_routes_skipped": si(tag + ".nrsk")}
        r["X-14"] = {"value": s("x14.value"), "by_item": rows(EQT, "x14.by_item"), "n_skipped": si("x14.n_skipped")}
        r["B1-01"] = {"value": s("b11.v"), "n_skipped": si("b11.nsk")}
        v1, v2 = set(marked(M, "c05.v1")), set(marked(M, "c05.v2"))
        viol = []
        for i in sorted(v1 | v2):
            if i in v1:
                viol.append("materials[%d].end_of_life.routes" % i)
            if i in v2:
                viol.append("materials[%d].end_of_life.mass_kg" % i)
        r["C-05"] = {"ok": flag("c05.ok"), "violations": viol,
                     "under_allocated": ["materials[%d].end_of_life.routes" % i for i in marked(M, "c05.under")],
                     "n_mass_unchecked": si("c05.nun")}
        r["STO-01"] = {"value": s("sto1.v", gates.SQ) if flag("sto1.ok", gates.SQ) else None}
        r["STO-02"] = {"value": s("sto2.v", gates.SQ) if flag("sto2.ok", gates.SQ) else None}
        valid = flag("sys4.valid", "project")
        r["SYS-04"] = {"ok": flag("sys4.ok", "project"), "status": "EVALUATED" if valid else "INVALID", "sum": s("sys4.sum", "project"),
                       "residual": s("sys4.res", "project") if valid else None}
        r["QA-04"] = {"ok": flag("qa4.ok", "project"), "status": "EVALUATED" if valid else "NOT_EVALUATED"}
        # X-09: classes that have at least one row with a valid mass; four routes each
        nr = len(S_.STATIC_TABLES[gates.ROUTES]["name"])
        mass, emis = {}, {}
        xm, xe = self.rows(gates.CLSX, "x09.m"), self.rows(gates.CLSX, "x09.e")
        for c in marked(gates.CLS, "x09.nc"):
            name = self.text(gates.CLS, "value", c)
            mass[name] = {rt: xm[c * nr + j] for j, rt in enumerate(S_.STATIC_TABLES[gates.ROUTES]["name"])}
            emis[name] = {rt: xe[c * nr + j] for j, rt in enumerate(S_.STATIC_TABLES[gates.ROUTES]["name"])}
        r["X-09"] = {"value": s("x09.value"), "mass": mass, "emission": emis}
        r["SYS-01"] = self._sys01()
        r["SYS-02"] = self._sys02()
        r["SYS-03"] = self._sys03()
        return r

    SYS1_PATH = {"p.area": (0, "project", "project.gross_floor_area"), "c.elec": (4, "construction", "construction.electricity_kwh"),
                 "c.fuel": (5, gates.CF, "construction.fuels[%d].quantity"), "c.waste": (6, gates.CW, "construction.waste_streams[%d].mass_kg"),
                 "d.dem": (7, gates.DEM, "end_of_life.demolition_activities[%d].quantity"),
                 "d.haul_m": (8, gates.HAUL, "end_of_life.waste_hauls[%d].mass_t"), "d.haul_d": (8, gates.HAUL, "end_of_life.waste_hauls[%d].distance_km")}

    def _sys01(self):
        found = []
        for pos, (fid, table, col, key, owner, lst) in enumerate(gates.SYS1_FIELDS):
            if fid in self.SYS1_PATH:
                order, _, fmt = self.SYS1_PATH[fid]
            else:
                order = {"m": 1, "e": 2, "r": 3}[fid[0]]
                fmt = {"m": "materials", "e": "equipment", "r": "refrigerants"}[fid[0]] + "[%d]." + key
            for i in self.marked(table, "s1.%s.s.MISSING" % fid):
                found.append((order, i, pos, fmt % i if "%d" in fmt else fmt))
        return {"ok": self.flag("sys1.ok"), "counts": {st: self.si("sys1." + st) for st in STATES},
                "violations": [f[3] for f in sorted(found)]}

    SYS2_PATH = {"m.qu": (M, "materials[%d].quantity_unit"), "m.comp": (M, "materials[%d].composition"), "m.tr": (M, "materials[%d].transport"),
                 "m.eol": (M, "materials[%d].end_of_life"), "m.eolr": (M, "materials[%d].end_of_life"),
                 "e.qu": (EQT, "equipment[%d].quantity_unit"), "e.eol": (EQT, "equipment[%d].end_of_life"),
                 "c.elec": (OP, "construction.electricity"), "c.fuel": (gates.CF, "construction.fuels[%d].unit"),
                 "c.waste": (gates.CW, "construction.waste_streams[%d]"), "o.elec": (OP, "operation.electricity"),
                 "o.gen": (OP, "operation.onsite_generation"), "o.exp": (OP, "operation.onsite_export"), "o.gas": (OP, "operation.gas"),
                 "o.oil": (OP, "operation.oil"), "o.dh": (OP, "operation.district_heat"), "w.wat": (WW, "water_waste.water"),
                 "w.sew": (WW, "water_waste.sewage"), "w.msw": (WW, "water_waste.municipal_waste"),
                 "d.dem": (gates.DEM, "end_of_life.demolition_activities[%d].unit"), "d.haul": (gates.HAUL, "end_of_life.waste_hauls[%d]"),
                 "q.cu": (gates.SQ, "summary_quantities.concrete_uptake"), "x.cost": ("cost_items", "cost_items[%d]")}

    def _sys02(self):
        paths = set()
        for grp, (table, fmt) in self.SYS2_PATH.items():
            for i in self.marked(table, "s2.p." + grp):
                paths.add(fmt % i if "%d" in fmt else fmt)
        sm = ["factors{%s}.stages" % self.text("factors", "key", i) for i in self.marked("factors", "s2.sm")]
        return {"ok": self.flag("sys2.ok"), "n_checked": self.si("sys2.n"), "violations": sorted(paths), "stage_mismatches": sorted(sm)}

    SYS3_PATH = {"m.fac": "materials[%d].factor_id", "m.part": "materials[%d].composition[%d].factor_id", "m.epd": "materials[%d].epd.factor_id",
                 "m.inst": "materials[%d].installation_factor_id", "m.dlv": "materials[%d].transport.delivery_factor_id",
                 "m.tr": "materials[%d].transport.factor_id", "m.haul": "materials[%d].end_of_life.haul_factor_id",
                 "m.rt": "materials[%d].end_of_life.routes[%d].factor_id", "e.fac": "equipment[%d].factor_id",
                 "e.eol": "equipment[%d].eol_factor_id", "e.dlv": "equipment[%d].delivery_factor_id", "e.ins": "equipment[%d].installation_factor_id",
                 "c.fuel": "construction.fuels[%d].factor_id", "c.waste": "construction.waste_streams[%d].factor_id",
                 "o.gas": "operation.gas_factor_id", "o.oil": "operation.oil_factor_id", "o.dh": "operation.district_heat_factor_id",
                 "w.wat": "water_waste.water_factor_id", "w.sew": "water_waste.sewage_factor_id", "w.msw": "water_waste.waste_factor_id",
                 "d.dem": "end_of_life.demolition_activities[%d].factor_id", "d.haul": "end_of_life.waste_hauls[%d].factor_id",
                 "q.cu": "summary_quantities.concrete_uptake_factor_id", "x.cost": "cost_items[%d].factor_id"}

    def _sys03(self):
        keys = set()
        for uid, table, app, col, ref in gates.SYS3_REFS:
            fmt = self.SYS3_PATH[uid]
            for i in self.marked(table, "s3.nf." + uid):
                if fmt.count("%d") == 2:
                    d = self.tabs.data[table]
                    path = fmt % (int(d["_parent"][i]), int(d["_pos"][i]))
                else:
                    path = fmt % i if "%d" in fmt else fmt
                keys.add(path + " (no factor)")
            for i in self.marked(table, "s3.nr." + uid):
                keys.add("factors{%s} (no record)" % self.text(table, col, i))
        for i in self.marked("factors", "s3.lic"):
            keys.add("factors{%s}.licence_status" % self.text("factors", "key", i))
        if self.flag("s3.grid", OP):
            keys.add("operation.grid")
        return {"ok": self.flag("sys3.ok"), "n_checked": self.si("sys3.n"), "violations": sorted(keys), "n_references_affected": self.si("sys3.aff")}

    # ---- read-outs: results at T ------------------------------------------------------------
    def _results(self, T, kv, val):
        s, si, flag, rows, marked, eng = self.s, self.si, self.flag, self.rows, self.marked, self.eng
        r = _Readout(self)
        Y = len(marked(CAL, "t.in"))
        def years(col):
            self._seen.add((CAL, "t.in"))
            return [0.0] + [float(x) for x in self.v(CAL, col)[:Y]]
        # refrigerants
        r["B1-02"] = {"value": val["B1-02"], "by_item": rows(D, "t.b12_i"), "by_year": years("t.b12_y"), "n_skipped": si("b12.nsk")}
        r["B1-03"] = {"value": val["B1-03"], "by_year": years("t.b13_y"), "n_skipped": si("b13.nsk")}
        r["B1-04"] = {"value": val["B1-04"], "n_skipped": si("b14.nsk")}
        # operation
        r["X-06"] = {"by_year": years("x06.g"), "matches_table": flag("dmt.x06"), "source": "DESCRIPTOR" if flag("x06.wf", OP) else "TABLE"}
        r["B6-04"] = {"by_year": years("b64.net"), "computed": flag("b64.computed", OP), "descriptors_match_tables": flag("dmt.b64")}
        r["B6-01"] = {"by_year": years("b61.e"), "computed": flag("b61.ok", OP)}
        r["B6-02"] = {"by_year": years("b62.e"), "n_skipped": si("b62.nsk", OP), "descriptors_match_tables": flag("dmt.b62")}
        r["B6-03"] = {"value": val["B6-03"]}
        r["B2-01"] = {"value": val["B2-01"], "computed": flag("b21.ok", OP)}
        for uid, tag in (("B7-01", "b71"), ("B7-02", "b72"), ("B7-03", "b73")):
            r[uid] = {"by_year": years(tag + ".e"), "n_skipped": si(tag + ".nsk", WW), "descriptors_match_tables": flag("dmt." + tag)}
        r["B7-04"] = {"value": val["B7-04"]}
        r["X-11"] = {"value": s("t.x11", OP) if flag("x11.ok", OP) else None}
        # repairs, renewals, rebuild
        r["B3-01"] = {"value": val["B3-01"], "by_year": years("t.b3_y"), "n_skipped": si("b3.n_skipped")}
        r["B3-02"] = {"value": s("t.b32"), "n_skipped": si("b3.n_skipped")}
        ev = [[] for _ in range(eng.nrows(EQT))]
        if eng.nrows(EE):
            inside, par, order, tau = self.v(EE, "t.in_e"), self.v(EE, "_parent"), self.v(EE, "ord"), self.v(EE, "tau")
            for i in sorted(np.nonzero(inside)[0], key=lambda i: (par[i], order[i])):
                ev[int(par[i])].append(float(tau[i]))
        r["B4-01"] = {"events": ev, "n_events": si("t.b41_n")}
        npart = kv["N.b42"]
        if npart != round(npart) or int(round(npart)) != si("t.np"):
            raise Unusable("the knot count of incomplete renewals and the row count differ")
        r["B4-02"] = {"value": val["B4-02"], "by_item_material": rows(M, "t.b42_im"), "by_item_equipment": rows(EQT, "t.b42_ie"),
                      "by_year": years("t.b42_y"), "n_partial": int(round(npart))}
        r["B4-03"] = {"by_item": [int(x) for x in rows(M, "t.cnt_m")]}
        r["B5-01"] = {"value": val["B5-01"], "n_events": si("t.b5_n"), "by_year": years("t.b5_y"), "computed": flag("b5.computed")}
        r["X-10"] = {"resource_kg": s("t.x10r"), "waste_kg": s("t.x10w"), "n_excluded": si("x10.n_excluded")}
        by_cycle = {}
        for i in marked(gates.CYC, "t.x08_on"):
            by_cycle[repr(float(self.tabs.data[gates.CYC]["value"][i]))] = {
                "count": int(self.v(gates.CYC, "t.cnt_c")[i]), "unit_emission": float(self.v(gates.CYC, "x08.U")[i]),
                "emission": float(self.v(gates.CYC, "t.x08_e")[i])}
        r["X-08"] = {"value": s("t.x08_v"), "by_cycle": by_cycle, "explicit": s("t.x08_x")}
        # stage vector, totals, indicators
        inc = self.v("STG", "x02.inc")
        bs, full = self.v("STG", "x02.bs"), self.v("STG", "x02.full")
        r["X-02"] = {"by_stage": {st: float(bs[i]) for i, st in enumerate(STAGES) if inc[i]},
                     "by_stage_all": {st: float(full[i]) for i, st in enumerate(STAGES)}, "complete": flag("x02.complete"),
                     "incomplete_units": sorted(S_.U_IDS[i] for i in marked("U", "x02.uinc"))}
        for n in (1, 2, 3):
            r["SUM-0%d" % n] = {"value": s("sum%d" % n), "complete": flag("x02.complete")}
        area_ok = flag("sum4.ok")
        r["SUM-04"] = {"value": s("sum4") if area_ok else None}
        r["SUM-05"] = {"value": s("sum5") if area_ok else None}
        r["SUM-06"] = {"value": s("sum6")}
        defined, share, inc = flag("sum7.def"), self.v("STG", "sum7.share"), self.v("STG", "x02.inc")
        r["SUM-07"] = {"defined": defined, "by_stage": {st: float(share[i]) for i, st in enumerate(STAGES) if inc[i]} if defined else {}}
        if not flag("s8.has", "boundary"):
            r["SUM-08"] = {"status": "NO_BASELINE", "delta": None, "saving": None}
        elif not flag("s8.cmp"):
            r["SUM-08"] = {"status": "NOT_COMPARABLE", "delta": None, "saving": None,
                           "reasons": [n for n, c in (("AREA", "s8.rA"), ("PERIOD", "s8.rT"), ("STAGES", "s8.rS"), ("GAS_SCOPE", "s8.rG"),
                                                      ("FACTOR_VERSION", "s8.rF")) if flag(c)]}
        else:
            r["SUM-08"] = {"status": "COMPARED", "baseline": self.base_sum3, "delta": s("s8.delta"),
                           "saving": s("s8.sav") if flag("s8.pos") else None}
        # gas breakdown, CO2 version, yearly series
        rec, co2 = self.v("STG", "x04.rec"), self.v("STG", "x05.co2")
        bg = self.rows("gases", "x04.bygas")
        r["X-04"] = {"value": s("x04.value"), "by_gas": {self.text("gases", "value", i): bg[i] for i in range(len(bg))},
                     "co2e_from_gases": s("x04.fg"), "grid_co2e": s("x04.grid"), "refrigerant_co2e": s("x04.refr"),
                     "by_stage_recomputed": {st: float(rec[i]) for i, st in enumerate(STAGES)}}
        r["X-05"] = {"value": s("x05.value"), "by_stage_co2": {st: float(co2[i]) for i, st in enumerate(STAGES)}}
        ser, cum = self.v("Y0", "x07.s"), self.v("Y0", "x07.c")
        r["X-07"] = {"by_year": [float(x) for x in ser[:Y + 1]], "cumulative": [float(x) for x in cum[:Y + 1]], "value": s("x07.value")}
        # checks at T
        qb, qc = set(marked(M, "qa1.b")), set(marked(M, "qa1.c"))
        viol = ["stage %s" % STAGES[i] for i in marked("STG", "qa1.a")]
        for i in sorted(qb | qc):
            if i in qb:
                viol.append("materials[%d] A13-01/A13-03" % i)
            if i in qc:
                viol.append("materials[%d] A4-01/A4-02" % i)
        r["QA-01"] = {"ok": flag("qa1.ok"), "violations": viol}
        q = {"ok": flag("qa2.ok"), "violations": [], "warnings": []}
        for name, tab, pre, attr in (("equipment", EQT, "qa2.e", "replacement_event_list"), ("refrigerants", D, "qa2.r", "change_years")):
            q["violations"] += ["%s[%d].%s" % (name, i, attr) for i in marked(tab, pre + ".v")]
            q["warnings"] += ["%s[%d].%s" % (name, i, attr) for i in marked(tab, pre + ".w")]
        r["QA-02"] = q
        r["QA-03"] = {"ok": flag("t.qa3_ok"), "violations": sorted(self.text("factors", "key", i) for i in marked("factors", "t.qa3_v")),
                      "n_used": si("t.qa3_n")}
        return r
