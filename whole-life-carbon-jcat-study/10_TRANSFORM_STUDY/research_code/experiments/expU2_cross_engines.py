"""EXP-U2: independent checks of the key mathematical results with other engines.

  1 SymPy    (exact)   the resolvent identity  prod_{j<m}(I + N^(2^j)) (I - N) = I - N^(2^m)  for a generic lower
                       bidiagonal N with symbolic weights; the refrigerant recurrence in exact rationals equals the
                       8-factor product
  2 SciPy    (float)   the start-of-year masses of the engine (8 sum-product steps) against a sparse triangular
                       solve of (I - N) u = b built from the same coefficient columns
  3 DuckDB   (SQL)     grouped sums written again in SQL on the flattened tables: two-key grouping (X-09), number of
                       renewals per row at T (B4-03), the year-weighted sum of the purchased-electricity emission
  4 lca_ops  (exact)   the four-operator module of the main branch (math_tools_v2/lca_ops.py, exact rationals with
                       SymPy): masked sum-product coefficient, periodic events with the end excluded, piecewise rate
                       integral - against the ramp-step kernel / knot spectrum of this study on the same numbers
  (mpmath is used in EXP-U1; SageMath and MATLAB run through the GitHub Actions of the main branch, see RESULTS.)

Run from ``research_code`` with the mathematics environment:
    PYTHONDONTWRITEBYTECODE=1 $HOME/.lca-math/bin/python -B -m experiments.expU2_cross_engines [path/to/lca_ops.py]
Writes ``11_UNIFIED_SYSTEM/results/expU2_cross_engines.json``. Fictional data; evidence level N (implementer only).
"""
import fractions
import importlib.util
import json
import math
import os
import random
import sys
import tempfile

sys.dont_write_bytecode = True

import numpy as np

from specs.lib import CAL
from specs.physical import DY, M, ME, RT
from tstudy import baseline, rampstep as rs, scenarios, unified
from tstudy.knots import KnotSpectrum

OUT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "11_UNIFIED_SYSTEM", "results",
                                    "expU2_cross_engines.json"))
F = fractions.Fraction


def sympy_identity():
    import sympy as sp
    out = {}
    for n, m in ((8, 3), (16, 4)):
        c = sp.symbols("c1:%d" % n)
        N = sp.zeros(n, n)
        for i in range(1, n):
            N[i, i - 1] = c[i - 1]
        P = sp.eye(n)
        for j in range(m):
            P = P * (sp.eye(n) + N ** (2 ** j))
        resid = (P * (sp.eye(n) - N) - sp.eye(n)).applyfunc(sp.expand)
        out["n=%d, %d factors, symbolic weights" % (n, m)] = bool(resid == sp.zeros(n, n))
    # exact rationals: recurrence of the definition against the product of 8 factors, random resets
    rng = random.Random(20261113)
    worst = 0
    for trial in range(40):
        H = rng.choice((40, 130, 200))
        q = F(rng.randint(1, 99), 100)
        m0 = F(rng.randint(1, 5000), 7)
        p = [1 if rng.random() < 0.08 else 0 for _ in range(H)]
        u_rec = [m0]
        for k in range(1, H):
            u_rec.append(m0 if p[k - 1] else q * u_rec[k - 1])
        b = [m0] + [m0 if p[k - 1] else F(0) for k in range(1, H)]
        c = [F(0)] + [F(0) if p[k - 1] else q for k in range(1, H)]
        u, s = list(b), 1
        for j in range(8):
            u = [u[k] + (c[k] * u[k - s] if k - s >= 0 else 0) for k in range(H)]
            c = [c[k] * c[k - s] if k - s >= 0 else F(0) for k in range(H)]
            s *= 2
        worst += sum(1 for a, bb in zip(u, u_rec) if a != bb)
    out["exact rationals: 40 random devices (40, 130, 200 years), entries that differ"] = worst
    return out


def scipy_solve(sysm):
    import scipy.sparse as sps
    from scipy.sparse.linalg import spsolve_triangular
    eng = sysm.eng
    n = eng.nrows(DY)
    par, k = sysm.v(DY, "_parent"), sysm.v(DY, "k")
    c0, b, u8 = sysm.v(DY, "b1.c0"), sysm.v(DY, "b1.u0"), sysm.v(DY, "b1.u8")
    pos = {(int(p), int(kk)): i for i, (p, kk) in enumerate(zip(par, k))}
    rows, cols, vals = [], [], []
    for i in range(n):
        j = pos.get((int(par[i]), int(k[i]) - 1))
        if j is not None and c0[i] != 0.0:
            rows.append(i); cols.append(j); vals.append(-c0[i])
    A = sps.csr_matrix((vals, (rows, cols)), shape=(n, n)) + sps.identity(n, format="csr")
    u = spsolve_triangular(A.tocsr(), b, lower=True)
    nz = u != 0
    return {"n_unknowns": int(n), "max_rel_difference": float(np.max(np.abs(u8[nz] - u[nz]) / np.abs(u[nz]))) if nz.any() else 0.0,
            "max_abs_where_zero": float(np.max(np.abs(u8[~nz]))) if (~nz).any() else 0.0}


def duckdb_sql(sysm, T):
    import duckdb
    con = duckdb.connect()
    d = sysm.tabs.data
    eng = sysm.eng
    out = {}
    # (a) X-09: mass by material class and route, two-key GROUP BY
    mats = [(i, d[M]["material_class"][i], float(d[M]["end_of_life.mass_kg"][i]) if d[M]["end_of_life.mass_kg?"][i] else None)
            for i in range(eng.nrows(M))]
    routes = [(int(d[RT]["_parent"][i]), d[RT]["route"][i], float(d[RT]["fraction"][i])) for i in range(eng.nrows(RT))]
    con.execute("CREATE TABLE m(i INTEGER, cls VARCHAR, mass DOUBLE)"); con.executemany("INSERT INTO m VALUES (?, ?, ?)", mats)
    con.execute("CREATE TABLE r(p INTEGER, route VARCHAR, fraction DOUBLE)"); con.executemany("INSERT INTO r VALUES (?, ?, ?)", routes)
    sql = dict(((c, rt), v) for c, rt, v in con.execute(
        "SELECT m.cls, r.route, SUM(m.mass * r.fraction) FROM r JOIN m ON r.p = m.i WHERE m.mass >= 0 AND r.fraction >= 0 GROUP BY 1, 2").fetchall())
    got = sysm.static["X-09"]["mass"]
    worst = 0.0
    for cls, by in got.items():
        for rt, v in by.items():
            w = sql.get((cls, rt), 0.0)
            worst = max(worst, abs(v - w) / abs(w) if w else abs(v))
    out["X-09 mass by class and route"] = {"cells": sum(len(v) for v in got.values()), "max_rel_difference": worst}
    # (b) B4-03: number of renewals per row at T, COUNT with the gate tau < T(1-eps)
    res = sysm.at(T)
    ev = [(int(p), float(t)) for p, t in zip(d[ME]["_parent"], d[ME]["tau"])]
    con.execute("CREATE TABLE e(p INTEGER, tau DOUBLE)"); con.executemany("INSERT INTO e VALUES (?, ?)", ev)
    cnt = dict(con.execute("SELECT p, COUNT(*) FROM e WHERE tau < ? GROUP BY p", [T * (1.0 - 1e-9)]).fetchall())
    bad = sum(1 for i, n in enumerate(res["B4-03"]["by_item"]) if cnt.get(i, 0) != n)
    out["B4-03 renewals per row at T=%g" % T] = {"rows": len(res["B4-03"]["by_item"]), "rows_that_differ": bad}
    # (c) year-weighted sum of the purchased-electricity emission: SUM(e_k * LEAST(1, GREATEST(0, T - k)))
    el = [(int(k), float(v)) for k, v in zip(d[CAL]["_pos"], sysm.v(CAL, "b61.e"))]
    con.execute("CREATE TABLE el(k INTEGER, e DOUBLE)"); con.executemany("INSERT INTO el VALUES (?, ?)", el)
    s = con.execute("SELECT SUM(e * LEAST(1.0, GREATEST(0.0, ? - k))) FROM el", [T]).fetchone()[0]
    kval = sysm.K["EL"].value(T)
    out["year-weighted purchased-electricity emission at T=%g" % T] = {"sql": s, "knot_spectrum": kval,
                                                                     "rel_difference": abs(s - kval) / abs(s) if s else abs(kval)}
    return out


def lca_ops_exact(path):
    """Exact rationals in the four-operator module against the kernel of this study, on the same small numbers."""
    spec = importlib.util.spec_from_file_location("lca_ops", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    num = lambda x: {"op": "rational", "value": str(x)} if F(x).denominator != 1 else {"op": "integer", "value": str(x)}
    q, f, w = F(125, 10), F(7, 3), F(1, 8)                    # quantity, factor, waste rate: coefficient q/(1-w)*f
    rate = [F(21, 10), F(19, 10), F(17, 10), F(3, 2)]         # emission of the years 1..4 (per year)
    period = F(5, 2)
    cases = []
    for T in (F(4), F(15, 4), F(5, 2), F(1, 2)):
        tasks = [{"id": "inputs", "operation": "masked_sum_product", "groups": [
                    {"id": "renewal", "output_unit": "kgCO2e", "terms": [
                        {"id": "row", "mask": 1, "factors": [{"value": str(q / (1 - w)), "unit": "kg"}, {"value": str(f), "unit": "kgCO2e/kg"}]},
                        {"id": "masked", "mask": 0, "factors": [{"value": "1000", "unit": "kgCO2e"}]}]},
                    {"id": "one", "output_unit": "kgCO2e/year", "terms": [{"id": "u", "mask": 1, "factors": [{"value": "1", "unit": "kgCO2e/year"}]}]}]},
                 {"id": "spec", "operation": "node_spectrum", "interval": {"start": "0", "end": str(T)}, "include_start": False,
                  "include_end": False, "events": [],
                  "periodic": [{"id": "renewal", "first": str(period), "period": str(period), "coefficient": {"task": "inputs", "group": "renewal"}}],
                  "rates": [{"id": "operation", "coefficient": {"task": "inputs", "group": "one"},
                             "profile": [{"start": str(k), "end": str(k + 1), "expression": num(rate[k])} for k in range(4)]}],
                  "result_unit": "kgCO2e"}]
        bundle = {"schema": "lca-math-operators/0.2", "tasks": tasks}
        with tempfile.TemporaryDirectory() as tmp:
            fin, fout = os.path.join(tmp, "in.json"), os.path.join(tmp, "out.json")
            with open(fin, "w") as fh:
                json.dump(bundle, fh)
            mod.run(fin, fout)
            mod.verify(fin, fout)
            with open(fout) as fh:
                res = json.load(fh)
        node = [r for r in res["tasks"] if r["id"] == "spec"][0]["value"]["total"]["value"]
        exact = F(int(node["numerator"]), int(node["denominator"]))
        # the same numbers through the ramp-step kernel and the knot spectrum of this study (floating point)
        u = float(q) / (1.0 - float(w)) * float(f)
        pieces = [rs.atom(u, tau) for tau in rs.periodic_times(4.0, float(period))] + [rs.year_cell(float(rate[k]), k + 1) for k in range(4)]
        val = KnotSpectrum(pieces).value(float(T))
        cases.append({"T": str(T), "lca_ops_exact": str(exact), "knot_spectrum": val, "rel_difference": abs(val - float(exact)) / float(exact)})
    return cases


def main(argv):
    baseline.assert_frozen(); baseline.load()
    S, Mb, L = scenarios.benchmark()
    out = {"experiment": "EXP-U2", "1_sympy": sympy_identity()}
    print("1 SymPy:", out["1_sympy"])
    sysm = unified.System(Mb, with_base=False)
    out["2_scipy_benchmark_M"] = scipy_solve(sysm)
    print("2 SciPy:", out["2_scipy_benchmark_M"])
    out["3_duckdb_benchmark_M"] = duckdb_sql(sysm, 62.5)
    print("3 DuckDB:", out["3_duckdb_benchmark_M"])
    if argv:
        out["4_lca_ops"] = lca_ops_exact(argv[0])
        print("4 lca_ops:", out["4_lca_ops"])
    import duckdb, mpmath, scipy, sympy
    out["versions"] = {"numpy": np.__version__, "sympy": sympy.__version__, "scipy": scipy.__version__, "mpmath": mpmath.__version__,
                       "duckdb": duckdb.__version__, "python": sys.version.split()[0]}
    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=1)


if __name__ == "__main__":
    main(sys.argv[1:])
