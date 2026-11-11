"""Targeted black-box probes: mutate one input, compare reference with my reading(s)."""
import sys, os, copy, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compare, mine
from refcalc import registry
from synth import population
from synth.generate import make_scenario
from synth import model

compare.NONE_IS_ZERO = True
BASE_OPTS = {"route_bad_skips_row": False}

def base(period=60.0, seed=7, **o):
    opts = dict(n_materials=12, n_equipment=6, n_refrigerants=4)
    opts.update(o)
    return make_scenario(seed, "RC", "office", "S", period, scenario_id="PROBE", **opts)

def diff(scn, opts=None, units=None, show=True, label=""):
    o = dict(BASE_OPTS); o.update(opts or {})
    try:
        ref = registry.run_all(scn)
    except Exception as exc:
        print(f"[{label}] REFERENCE RAISED {type(exc).__name__}: {exc}")
        return None, None, ["REF-EXC"]
    try:
        me = mine.run(scn, ref, o)
    except Exception as exc:
        print(f"[{label}] MINE RAISED {type(exc).__name__}: {exc}")
        return ref, None, ["MINE-EXC"]
    bad = []
    for uid, keys in compare.KEYS.items():
        if units and uid not in units:
            continue
        for k in keys:
            ok, n, m = compare.close(me[uid].get(k), ref[uid].get(k))
            if not ok:
                bad.append((uid, k))
    if show:
        print(f"[{label}] differing: {bad if bad else 'none'}")
    return ref, me, bad

def epd_row(scn):
    for i, row in enumerate(scn.materials):
        if row.epd is not None:
            return i
    return None
