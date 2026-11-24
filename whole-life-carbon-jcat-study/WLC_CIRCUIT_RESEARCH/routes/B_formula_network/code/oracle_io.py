"""Read-only access to the frozen oracles (route B, Psi reading: sweep variable = horizon T).

Nothing here writes into the frozen trees. Every import of frozen code must run under
``PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0 python3 -B``; ``setup()`` also sets
``sys.dont_write_bytecode`` and ``GIT_OPTIONAL_LOCKS`` defensively and calls
``tstudy.baseline.assert_frozen()`` before anything else is imported.

Two oracles are used:
  * refcalc (09_APPROX_STUDY/research_code/refcalc, frozen): row-by-row reference, one run per T
    (``scenarios.with_period``).  This is the primary oracle.
  * msp / unified.System (10_TRANSFORM_STUDY/research_code/tstudy): second oracle, and the source of
    the T-independent amplitude columns (P1 -> EMIT pieces) that route B feeds into its kernels as an
    *external table*.  Route B never uses the knot spectra or TIME/AGG results as inputs.
"""
from __future__ import annotations

import os
import sys

sys.dont_write_bytecode = True
os.environ.setdefault("GIT_OPTIONAL_LOCKS", "0")

HERE = os.path.dirname(os.path.abspath(__file__))
ROUTE = os.path.dirname(HERE)
REPO = os.path.normpath(os.path.join(ROUTE, "..", "..", "..", ".."))
STUDY = os.path.join(REPO, "whole-life-carbon-jcat-study")
TSTUDY_ROOT = os.path.join(STUDY, "10_TRANSFORM_STUDY", "research_code")
FROZEN_DIRS = [os.path.join(STUDY, d) for d in ("09_APPROX_STUDY", "10_TRANSFORM_STUDY", "17_WHOLE_BUILDING_TIME_THEORY",
                                                 "WLC_THEORY_RESEARCH_BASE")]

_mods = None


def setup():
    """Import the frozen modules once (after assert_frozen) and return them as a dict."""
    global _mods
    if _mods is not None:
        return _mods
    if TSTUDY_ROOT not in sys.path:
        sys.path.insert(0, TSTUDY_ROOT)
    from tstudy import baseline  # noqa: E402
    trees = baseline.assert_frozen()
    from tstudy import scenarios, unified, msp, knots, rampstep  # noqa: E402
    from specs import system as S_  # noqa: E402
    _mods = {"baseline": baseline, "scenarios": scenarios, "unified": unified, "msp": msp, "knots": knots,
             "rampstep": rampstep, "system": S_, "trees": trees}
    return _mods


def pycache_dirs():
    """__pycache__ directories inside the frozen trees (must be empty)."""
    out = []
    for root in FROZEN_DIRS:
        for d, sub, _ in os.walk(root):
            if "__pycache__" in sub:
                out.append(os.path.join(d, "__pycache__"))
    return out


def representative_scenarios(names=("S", "M")):
    """The standard benchmark scenarios of the frozen generator (fictional data)."""
    m = setup()
    bm = {s.meta.scenario_id.split("-")[3]: s for s in m["scenarios"].benchmark()}
    return [bm[n] for n in names]


OUT_OF_SAMPLE = (3, 11)      # evaluation_set(12) indices: EV3 hospital-M (21 no-top-up devices), EV11 warehouse-S;
                             # disjoint from the benchmark S/M and from route D's EV6/EV10


def out_of_sample_scenarios(idx=OUT_OF_SAMPLE):
    """Out-of-sample scenarios of the frozen generator's evaluation set (seed 720002), never used to design route B."""
    ev = setup()["scenarios"].evaluation_set(12)
    return [ev[i] for i in idx]


def reference_at(scn, T: float) -> dict:
    """refcalc results of all 70 units with the study period replaced by T."""
    m = setup()
    return m["baseline"].run_reference(m["scenarios"].with_period(scn, float(T)))


def system(scn):
    """unified.System(scn): P1 once; ``.pieces`` are the amplitude tables, ``.at(T)`` the msp oracle."""
    return setup()["unified"].System(scn)


def head_sha() -> str:
    import subprocess
    return subprocess.run(["git", "-C", REPO, "rev-parse", "HEAD"], capture_output=True, text=True,
                          env=dict(os.environ, GIT_OPTIONAL_LOCKS="0")).stdout.strip()
