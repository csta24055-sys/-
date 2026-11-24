"""Shared helpers of route C (70 evaluation units -> circuit roles).

Read-only access to the frozen oracle (refcalc via tstudy.baseline) and to the ledger
(units70.json).  Nothing here writes outside routes/C_70_units/.
Run every entry point with:  PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0 python3 -B ...
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
import sys

sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
ROUTE = os.path.dirname(HERE)
STUDY = os.path.normpath(os.path.join(ROUTE, "..", "..", ".."))          # whole-life-carbon-jcat-study
REPO = os.path.dirname(STUDY)
RESULTS = os.path.join(ROUTE, "results")
UNITS_JSON = os.path.join(STUDY, "WLC_THEORY_RESEARCH_BASE", "data", "units70.json")
DEPS_CSV = os.path.join(STUDY, "WLC_THEORY_RESEARCH_BASE", "data", "unit_dependencies.csv")
LEDGER_MD = os.path.join(STUDY, "WLC_THEORY_RESEARCH_BASE", "02_70評価単位の完全台帳.md")
TSTUDY = os.path.join(STUDY, "10_TRANSFORM_STUDY", "research_code")
FROZEN_DIRS = [os.path.join(STUDY, d) for d in ("09_APPROX_STUDY", "10_TRANSFORM_STUDY",
                                                 "17_WHOLE_BUILDING_TIME_THEORY", "WLC_THEORY_RESEARCH_BASE")]

T_GRID_C1 = (1.0, 9.999999, 10.0, 10.000001, 20.0, 30.0, 60.0)
REL_TOL = 1e-9


def rel_err(a: float, b: float) -> float:
    """|a-b| / |b| (absolute difference when b == 0)."""
    d = abs(a - b)
    return d / abs(b) if b != 0.0 else d


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def git(*args: str) -> str:
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0")
    return subprocess.run(["git", "-C", REPO, *args], capture_output=True, text=True, env=env).stdout.strip()


def provenance() -> dict:
    return {
        "git_head": git("rev-parse", "HEAD"),
        "git_branch": git("rev-parse", "--abbrev-ref", "HEAD"),
        "units70_json_sha256": sha256(UNITS_JSON),
        "unit_dependencies_csv_sha256": sha256(DEPS_CSV),
        "python": sys.version.split()[0],
    }


def stray_pycache() -> list[str]:
    out = []
    for root in FROZEN_DIRS:
        for d, subdirs, _ in os.walk(root):
            for s in subdirs:
                if s == "__pycache__":
                    out.append(os.path.join(d, s))
    return out


# ---------------------------------------------------------------- ledger
_LEDGER = None


def ledger() -> dict:
    global _LEDGER
    if _LEDGER is None:
        with open(UNITS_JSON, encoding="utf-8") as f:
            _LEDGER = json.load(f)
    return _LEDGER


def units() -> list[dict]:
    return ledger()["units"]


def unit_by_id() -> dict[str, dict]:
    return {u["id"]: u for u in units()}


def comp_rows() -> list[tuple[str, str, int, str]]:
    """(unit, stage, sign, beta) rows of the composition table COMP, read from units70.json."""
    rows = []
    for u in units():
        for c in u.get("composition") or []:
            rows.append((u["id"], c["stage"], int(c["sign"]), str(c["beta"])))
    return rows


def rebuild(values: dict[str, float], included: set[str], rows=None) -> tuple[dict[str, float], float]:
    """C(T) = sum_s iota_s sum_u sigma_{s,u} beta_{s,u} V_u(T) -- one summing node per stage, then one total node.

    beta is "1" or "iota_B2" (the ledger's only non-trivial beta).  Excluded stages are absent (not 0).
    """
    rows = comp_rows() if rows is None else rows
    stage: dict[str, float] = {}
    for uid, s, sign, beta in rows:
        if s not in included:
            continue
        if beta == "1":
            b = 1.0
        elif beta == "iota_B2":
            b = 1.0 if "B2" in included else 0.0
        else:
            raise ValueError(f"unknown beta {beta!r} for {uid}")
        stage[s] = stage.get(s, 0.0) + sign * b * values[uid]
    return stage, sum(stage.values())


# ---------------------------------------------------------------- time-form block types (H-C2)
BLOCKS = ("const_t0", "const_tT", "year_cell", "density", "atom", "gated_year_cell", "interval")


def blocks_from_text(time_form: str) -> list[str]:
    """Block types named in a unit's ledger time_form text (keyword rules, documented in README)."""
    t = time_form
    out = []
    if "定数の核" in t:
        out.append("const_tT" if "t=T" in t else "const_t0" if "t=0" in t else "const_unplaced")
    if "区間形" in t:
        out.append("interval")
    if "密度" in t:
        out.append("density")
    if "原子" in t:
        out.append("atom")
    if "ゲート付き年セル" in t:
        out.append("gated_year_cell")
    if "年セルの和" in t:
        out.append("year_cell")
    return out


# allowed empirical features of each single block type (see block_signature)
ALLOW = {
    "const_t0": {"const"},
    "const_tT": {"const"},
    "year_cell": {"const", "slope", "int_kink"},
    "density": {"const", "slope"},
    "atom": {"const", "jump", "inner"},          # zero slope; jumps at grid or inside a cell
    "gated_year_cell": {"const", "slope", "int_kink", "jump", "inner"},
    "interval": {"const", "slope", "int_kink", "jump", "inner"},
}


def block_signature(T: list[float], V: list[float], per_cell: int, probes=None) -> dict:
    """Empirical shape features of V(T) sampled at per_cell interior points of each unit cell (k, k+1].

    features: const (no variation), slope (non-zero affine slope somewhere), int_kink (slope changes at an
    integer), jump (discontinuity between cells, i.e. a jump in the boundary gap around an integer),
    inner (a jump or slope change strictly inside a cell, i.e. at a non-grid event time).
    probes: optional list of (V(T), V(T+delta)) pairs with tiny delta.  When given, 'slope' is decided by
    local flatness (majority of probes non-flat) instead of the coarse-grid median, because a dense
    piecewise-constant atom sum looks like a ramp on an 8-points-per-year grid (observed for B4-02).
    """
    scale = max(abs(v) for v in V) or 1.0
    tol = 1e-10 * scale
    n_cells = len(T) // per_cell
    h = T[1] - T[0]
    slopes, inner_cells = [], []
    for k in range(n_cells):
        vs = V[k * per_cell:(k + 1) * per_cell]
        d = sorted(vs[i + 1] - vs[i] for i in range(per_cell - 1))
        med = d[len(d) // 2]
        slopes.append(med / h)
        if any(abs(x - med) > tol for x in d):
            inner_cells.append(k)
    jumps, kinks = [], []
    for k in range(1, n_cells):
        vl = V[k * per_cell - 1] + slopes[k - 1] * (h / 2)
        vr = V[k * per_cell] - slopes[k] * (h / 2)
        if abs(vr - vl) > tol and (k - 1) not in inner_cells and k not in inner_cells:
            jumps.append(k)
        if abs(slopes[k] - slopes[k - 1]) * h > tol:
            kinks.append(k)
    feats = set()
    nonflat = None
    if probes:
        nonflat = sum(1 for a, b in probes if abs(b - a) > 1e-14 * scale) / len(probes)
    if max(V) - min(V) <= tol:
        feats.add("const")
    else:
        has_slope = (nonflat > 0.5) if probes else any(abs(s) * h > tol for s in slopes)
        if has_slope:
            feats.add("slope")
        if kinks and has_slope:
            feats.add("int_kink")
        if jumps:
            feats.add("jump")
        if inner_cells:
            feats.add("inner")
    return {"features": sorted(feats), "n_inner_cells": len(inner_cells), "n_jumps_at_int": len(jumps),
            "n_int_kinks": len(kinks), "nonflat_probe_fraction": nonflat, "tol_abs": tol, "scale": scale}


def fits(features: set[str], blocks: list[str]) -> bool:
    allowed = set().union(*(ALLOW[b] for b in blocks)) if blocks else set()
    return set(features) <= allowed


# ---------------------------------------------------------------- numerical rank (H-C3), pure Python
def rank_mod_const(cols: list[list[float]], rtol: float) -> tuple[int, list[float]]:
    """Rank of span{columns} modulo the constant function, via centred, norm-scaled, pivoted Gram-Schmidt.

    Each column c is centred (c - mean) and divided by ||c|| (its original norm), so a column that is
    constant to relative rtol drops out.  Returns (rank, residual norms in pivot order).
    """
    work = []
    for c in cols:
        n0 = math.sqrt(sum(x * x for x in c))
        if n0 == 0.0:
            continue
        m = sum(c) / len(c)
        work.append([(x - m) / n0 for x in c])
    diag = []
    while work:
        norms = [math.sqrt(sum(x * x for x in w)) for w in work]
        i = max(range(len(work)), key=lambda j: norms[j])
        if norms[i] <= rtol:
            diag.extend(sorted(norms, reverse=True))
            break
        q = [x / norms[i] for x in work.pop(i)]
        diag.append(norms[i])
        for _ in range(2):                                           # re-orthogonalise
            for w in work:
                p = sum(a * b for a, b in zip(q, w))
                for j in range(len(w)):
                    w[j] -= p * q[j]
    rank = sum(1 for d in diag if d > rtol)
    return rank, diag


# ---------------------------------------------------------------- frozen oracle
_ORACLE = None


def oracle():
    """(baseline, scenarios) modules of tstudy, after assert_frozen().  Raises if the baseline changed."""
    global _ORACLE
    if _ORACLE is None:
        os.environ.setdefault("GIT_OPTIONAL_LOCKS", "0")
        if TSTUDY not in sys.path:
            sys.path.insert(0, TSTUDY)
        from tstudy import baseline, scenarios  # noqa: E402  (frozen, read-only)
        baseline.assert_frozen()
        baseline.load()
        _ORACLE = (baseline, scenarios)
    return _ORACLE


def refcalc_stages() -> list[str]:
    oracle()
    from refcalc.base import STAGES  # noqa: E402
    return list(STAGES)


def refcalc_closure(target: str) -> set[str]:
    """All units the frozen refcalc registry needs to compute ``target`` (declared depends_on), target excluded."""
    baseline, _ = oracle()
    reg = baseline.load()
    seen: set[str] = set()
    stack = [target]
    while stack:
        u = stack.pop()
        for d in reg.UNITS[u].depends_on:
            if d not in seen:
                seen.add(d)
                stack.append(d)
    return seen


def write_json(name: str, obj) -> str:
    os.makedirs(RESULTS, exist_ok=True)
    path = os.path.join(RESULTS, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1, sort_keys=False)
        f.write("\n")
    return path
