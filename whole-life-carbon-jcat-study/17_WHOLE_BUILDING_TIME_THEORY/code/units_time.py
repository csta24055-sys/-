"""Stage 1: time-dependence class of every output of all 70 evaluation units (independent concept model,
fictional data). The unified system (chapter 11) is evaluated at sample periods on the pieces between the
breakpoints of the canonical whole-building function (all lattice knots and event thresholds of every stage), and
each public output leaf is classified (FLOAT, measured):

  const        the same value at every sampled T
  step         constant on every sampled piece, different between pieces (counts, flags, judgments, step totals)
  affine       affine on every sampled piece (piecewise linear in T, possibly with jumps)
  hyperbolic   T * value is affine on every piece (value = alpha/T + beta: per-year intensities)
  ratio        neither of the above, but the value is a ratio of two piecewise-affine functions of the same pieces
               (checked: value * D(T) affine for D = the whole-life total C(T))
  other        none of the above
  shape        the list length changes with T (per-year lists, event lists)

Usage (from this folder): python3 -B units_time.py <out.json> [set names...] [--max-scenarios N] [--max-pieces P]
"""
from __future__ import annotations

import collections
import json
import math
import random
import sys
import time
from fractions import Fraction

sys.dont_write_bytecode = True
import canon                                            # noqa: E402
import timechar as tc                                   # noqa: E402
from checks import check_msp_pre_a as cm, sets_unified  # noqa: E402
from tstudy import baseline                             # noqa: E402

REL = 1e-9


def flat(res):
    out = {}
    for uid, d in res.items():
        for path, x in cm.leaves(d):
            out[(uid, path)] = x
    return out


def lists_shape(res):
    shp = {}
    def walk(x, path, uid):
        if isinstance(x, dict):
            for k, v in x.items():
                walk(v, f"{path}/{k}", uid)
        elif isinstance(x, (list, tuple)):
            shp[(uid, path)] = len(x)
            for i, v in enumerate(x):
                walk(v, f"{path}[{i}]", uid)
    for uid, d in res.items():
        walk(d, "", uid)
    return shp


def generic(path):
    """Leaf path with list indices removed (per-year entries share one class)."""
    import re
    return re.sub(r"\[\d+\]", "[]", path)


def is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def close(a, b, scale):
    return abs(a - b) <= REL * max(scale, 1e-300)


def classify_scenario(sysm, can, max_pieces, rng):
    kf = tc.KF(can)
    bp = tc.breakpoints(kf, can.H)
    pieces = [(a, b) for a, b in zip(bp, bp[1:]) if b - a > Fraction(1, 10 ** 6)]
    rng.shuffle(pieces)
    pieces = sorted(pieces[:max_pieces])
    samples = []                                      # per piece: [(T, flat outputs, shapes, C)]
    for a, b in pieces:
        pts = []
        for r in (Fraction(1, 5), Fraction(1, 2), Fraction(4, 5)):
            T = tc.fl_inside(a, b, r)
            res = sysm.at(T)
            pts.append((T, flat(res), lists_shape(res), float(kf(T))))
        samples.append(pts)
    keys = set()
    for pts in samples:
        for T, f, s, C in pts:
            keys |= set(f)
    cls = {}
    for key in keys:
        vals = [[(T, f.get(key), C) for T, f, s, C in pts] for pts in samples]
        flatv = [v for pv in vals for (_, v, _) in pv]
        if any(v is None for v in flatv):
            cls[key] = "shape"
            continue
        if not all(is_num(v) for v in flatv):
            cls[key] = "const" if len({repr(v) for v in flatv}) == 1 else "step"
            continue
        if any(isinstance(v, float) and (math.isnan(v) or math.isinf(v)) for v in flatv):
            cls[key] = "const" if len({repr(v) for v in flatv}) == 1 else "other"
            continue
        scale = max(abs(float(v)) for v in flatv)
        if all(close(float(v), float(flatv[0]), scale) for v in flatv):
            cls[key] = "const"
            continue
        def piece_ok(fun):
            for pv in vals:
                (T1, v1, C1), (T2, v2, C2), (T3, v3, C3) = pv
                y1, y2, y3 = fun(T1, v1, C1), fun(T2, v2, C2), fun(T3, v3, C3)
                sc = max(abs(y1), abs(y2), abs(y3), 1e-300)
                pred = y1 + (y3 - y1) * (T2 - T1) / (T3 - T1)
                if abs(pred - y2) > 1e-8 * sc:
                    return False
            return True
        if all(close(float(pv[0][1]), float(pv[1][1]), scale) and close(float(pv[1][1]), float(pv[2][1]), scale) for pv in vals):
            cls[key] = "step"
        elif piece_ok(lambda T, v, C: float(v)):
            cls[key] = "affine"
        elif piece_ok(lambda T, v, C: float(v) * T):
            cls[key] = "hyperbolic"
        elif piece_ok(lambda T, v, C: float(v) * C):
            cls[key] = "ratio"
        else:
            cls[key] = "other"
    # list lengths that vary with T
    shp = collections.defaultdict(set)
    for pts in samples:
        for T, f, s, C in pts:
            for k, n in s.items():
                shp[k].add(n)
    varying = {k for k, ns in shp.items() if len(ns) > 1}
    return cls, varying, len(pieces)


def main(outp, names, max_scn, max_pieces):
    baseline.assert_frozen()
    baseline.load()
    from synth import population
    agg = collections.defaultdict(collections.Counter)              # (unit, generic path) -> class counts
    var_lists = collections.defaultdict(int)
    per = []
    t0 = time.time()
    for name, label, scn in tc.scenario_entries(names, max_scn):
        rng = random.Random(sum(map(ord, label)))
        try:
            sysm = canon.make_system(scn, population.BASELINES)
            can = canon.build(sysm)
            cls, varying, npc = classify_scenario(sysm, can, max_pieces, rng)
        except Exception as ex:
            per.append(dict(set=name, label=label, error="%s %s" % (type(ex).__name__, str(ex)[:160])))
            continue
        for (uid, path), c in cls.items():
            agg[(uid, generic(path))][c] += 1
        for (uid, path) in varying:
            var_lists[(uid, generic(path))] += 1
        per.append(dict(set=name, label=label, n_pieces=npc, n_leaves=len(cls)))
        print("[%s] %-40s pieces %d leaves %d | %.0f s" % (name, label[:40], npc, len(cls), time.time() - t0), flush=True)
    units = collections.defaultdict(dict)
    for (uid, path), cnt in sorted(agg.items()):
        units[uid][path] = dict(cnt)
    for (uid, path), n in sorted(var_lists.items()):
        units[uid].setdefault("__list_length_varies__", {})[path] = n
    json.dump(dict(scenarios=per, units=units), open(outp, "w"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    args = sys.argv[1:]
    mx, mp = 10 ** 9, 40
    for flag in ("--max-scenarios", "--max-pieces"):
        if flag in args:
            i = args.index(flag)
            v = int(args[i + 1])
            del args[i:i + 2]
            if flag == "--max-scenarios":
                mx = v
            else:
                mp = v
    main(args[0], args[1:] or list(sets_unified.ALL_SETS), mx, mp)
