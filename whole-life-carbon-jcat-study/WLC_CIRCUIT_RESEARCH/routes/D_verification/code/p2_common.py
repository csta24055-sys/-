"""Pass 2 (routes B/C, gates X2-X5): read-only access to the FROZEN original code.

Run every pass-2 script as
    PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0 python3 -B code/<script>.py
`frozen()` calls tstudy.baseline.assert_frozen() first and aborts on failure; `clean()` checks that no
__pycache__ exists in the frozen trees. Nothing here writes outside routes/D_verification/.

Scenario choice (independent of route B, which used benchmark S seed101 / M seed102, and of route C, which
used benchmark S/M/L + two edge scenarios): evaluation_set (seed 720002) items 6 and 10.
"""
from __future__ import annotations

import json
import os
import sys
from fractions import Fraction

sys.dont_write_bytecode = True
os.environ.setdefault("GIT_OPTIONAL_LOCKS", "0")

HERE = os.path.dirname(os.path.abspath(__file__))
DROOT = os.path.dirname(HERE)
RESEARCH = os.path.normpath(os.path.join(DROOT, "..", ".."))
STUDY = os.path.dirname(RESEARCH)
TSTUDY = os.path.join(STUDY, "10_TRANSFORM_STUDY", "research_code")
CANON_DIR = os.path.join(STUDY, "17_WHOLE_BUILDING_TIME_THEORY", "code")
BASE = os.path.join(STUDY, "WLC_THEORY_RESEARCH_BASE")
FROZEN_DIRS = [os.path.join(STUDY, d) for d in ("09_APPROX_STUDY", "10_TRANSFORM_STUDY",
                                                 "17_WHOLE_BUILDING_TIME_THEORY", "WLC_THEORY_RESEARCH_BASE")]
OUT = os.path.join(DROOT, "results")
EPS = 1e-9
D = 1.0 - EPS                     # the double fl(1-eps) used by the model's gate test T*(1.0-EPS)

_M = None


def clean() -> list:
    bad = []
    for root in FROZEN_DIRS:
        for d, sub, _ in os.walk(root):
            if "__pycache__" in sub:
                bad.append(os.path.join(d, "__pycache__"))
    return bad


def frozen():
    """Import the frozen modules after assert_frozen(); raise SystemExit if the baseline changed."""
    global _M
    if _M is not None:
        return _M
    if TSTUDY not in sys.path:
        sys.path.insert(0, TSTUDY)
    from tstudy import baseline
    try:
        trees = baseline.assert_frozen()
    except Exception as ex:          # stop and report (coordinator rule)
        raise SystemExit(f"assert_frozen FAILED: {ex!r}")
    baseline.load()
    from tstudy import scenarios, unified
    _M = {"baseline": baseline, "scenarios": scenarios, "unified": unified, "trees": trees}
    return _M


def canon_modules():
    m = frozen()
    if CANON_DIR not in sys.path:
        sys.path.insert(0, CANON_DIR)
    import canon
    import timechar
    from synth import population
    return canon, timechar, population


def d_scenarios(which=("EV6", "EV10")):
    m = frozen()
    ev = m["scenarios"].evaluation_set(12)
    pick = {"EV6": ev[6], "EV10": ev[10]}
    bm = {s.meta.scenario_id.split("-")[3]: s for s in m["scenarios"].benchmark()}
    pick.update({"BM-S": bm["S"], "BM-M": bm["M"]})
    return [(k, pick[k]) for k in which]


def ref(scn, T):
    m = frozen()
    return m["baseline"].run_reference(m["scenarios"].with_period(scn, float(T)))


def in_domain(scn, T) -> list:
    m = frozen()
    return m["scenarios"].valid_domain(m["scenarios"].with_period(scn, float(T)))


def switch_point(g: float) -> float:
    """Smallest float T with g < fl(T*d) (written for D; cf. 03 S3.3)."""
    import math
    t = g / D
    while not g < t * D:
        t = math.nextafter(t, math.inf)
    while g < math.nextafter(t, -math.inf) * D:
        t = math.nextafter(t, -math.inf)
    return t


def rel(a, b):
    a, b = float(a), float(b)
    if a == b:
        return 0.0
    return abs(a - b) / max(abs(b), 1e-300) if b != 0 else abs(a)


def dump(name, obj):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name), "w") as f:
        json.dump(obj, f, indent=1, default=str, ensure_ascii=False)


def F(x):
    return Fraction(x)
