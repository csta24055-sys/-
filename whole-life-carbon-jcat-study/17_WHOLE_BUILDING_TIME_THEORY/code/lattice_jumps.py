"""Stage 1 supplement (after the final independent review): classification of the jumps of the knot form at lattice
knots (year boundaries) inside (0, H), with an explicit size threshold.

timechar.py put every nonzero lattice jump that has an event time within relative 1e-9 into "reset of the interval form
at an integer-time event" and left it out of the rounding test.  Most such jumps are rounding-size.  Here every
nonzero jump at a lattice knot (a position that is not also an event switch point) is classified by its size relative
to the scale of the window (interval-form) coefficients, wscale = max |amp| * length over the window terms (as in
timechar.py):

  rounding        |J| <= 1e-12 * wscale                      (TH-2 (2): rounding of separately rounded coefficients)
  reset           |J| >  1e-12 * wscale at the end t = hi of a window cell that holds an event never counted inside
                  the cell (a window term of B1-04 with amplitude != 0 and not gate < hi*(1-eps), and t < sw(gate)):
                  TH-2 (3), an exchange whose switch point passes the end of its year cell; its reset enters the next
                  cell's coefficients
  unexplained     |J| >  1e-12 * wscale anywhere else        (would contradict TH-2)
(The first version counted every above-threshold jump with ANY event knot of C within relative 1e-9 as a reset; the
final review asked for the specific test above.)

Both the rounding jumps near events and away from events are reported, and the smallest relative size of a reset jump
(the gap to the rounding jumps shows that the threshold separates two populations).
Usage: python3 -B lattice_jumps.py <out.json> [set ...]"""
from __future__ import annotations

import bisect
import json
import math
import sys
import time
from fractions import Fraction

sys.dont_write_bytecode = True
import canon                                           # noqa: E402  (sets the research-code paths)
from checks import sets_unified                        # noqa: E402
from tstudy import baseline                            # noqa: E402
import timechar as tc                                  # noqa: E402


def classify(can, kf):
    wscale = max((abs(float(t.amp)) * (t.length or 1.0) for t in can.terms if t.hi != math.inf), default=0.0)
    ev_pos = {tc.tswitch(g) for g in kf.eg}
    cross = {t.hi for t in can.terms                   # ends of window cells holding an event never counted in the cell
             if t.hi != math.inf and t.amp != 0 and t.gate != canon.NEG_INF
             and not t.gate < t.hi * (1.0 - canon.EPS) and t.hi < tc.tswitch(t.gate)}
    out = dict(rounding_near_event=0, rounding_away=0, reset=0, unexplained=0, cross_positions=0, above_threshold_near_other_event=0, max_rounding_rel=0.0,
               max_rounding_rel_away=0.0, min_reset_rel=None, max_reset_rel=0.0, wscale=wscale, examples=[])
    H = can.H
    for t in kf.lt:
        if not 0 < t < H:
            continue                                   # end nodes: no piece on one side (the node H makes C constant beyond H)
        if t in ev_pos:
            continue                                   # counted with the event jumps (timechar.py)
        p, q = kf.la[t]
        J = abs(float(p + q * Fraction(t)))            # exact (Fraction * float would be a float)
        if J == 0.0:
            continue
        rel = J / wscale if wscale > 0 else math.inf
        lo = bisect.bisect_left(kf.eg, t * (1 - 2e-9))
        hi = bisect.bisect_right(kf.eg, t * (1 + 2e-9))
        near = any(abs(g - t) <= 1e-9 * t for g in kf.eg[lo:hi])
        if rel <= 1e-12:
            out["rounding_near_event" if near else "rounding_away"] += 1
            out["max_rounding_rel"] = max(out["max_rounding_rel"], rel)
            if not near:
                out["max_rounding_rel_away"] = max(out["max_rounding_rel_away"], rel)
        elif t in cross:
            out["reset"] += 1
            out["min_reset_rel"] = rel if out["min_reset_rel"] is None else min(out["min_reset_rel"], rel)
            out["max_reset_rel"] = max(out["max_reset_rel"], rel)
        else:
            out["unexplained"] += 1
            out["above_threshold_near_other_event"] += near
            if len(out["examples"]) < 5:
                out["examples"].append(dict(t=t, rel=rel))
    out["cross_positions"] = len({t for t in cross if 0 < t < H})
    return out


def main(outp, names):
    baseline.assert_frozen()
    baseline.load()
    from synth import population
    res = []
    t0 = time.time()
    for name, label, scn in tc.scenario_entries(names or sets_unified.ALL_SETS, 10 ** 9):
        try:
            can = canon.build(canon.make_system(scn, population.BASELINES))
        except Exception as ex:                        # recorded, not hidden
            res.append(dict(set=name, label=label, prepare_error="%s %s" % (type(ex).__name__, str(ex)[:120])))
            continue
        r = classify(can, tc.KF(can))
        r.update(set=name, label=label)
        res.append(r)
        print("[%s] %-40s rounding %d/%d reset %d unexplained %d max-rounding %.1e min-reset %s | %.0f s"
              % (name, label[:40], r["rounding_near_event"], r["rounding_away"], r["reset"], r["unexplained"],
                 r["max_rounding_rel"], "%.1e" % r["min_reset_rel"] if r["min_reset_rel"] is not None else "-",
                 time.time() - t0), flush=True)
    ok = [r for r in res if "prepare_error" not in r]
    resets = [r["min_reset_rel"] for r in ok if r["min_reset_rel"] is not None]
    summ = dict(n_scenarios=len(res), n_analysed=len(ok), prepare_errors=len(res) - len(ok),
                rounding_near_event=sum(r["rounding_near_event"] for r in ok), rounding_away=sum(r["rounding_away"] for r in ok),
                reset=sum(r["reset"] for r in ok), unexplained=sum(r["unexplained"] for r in ok),
                max_rounding_rel=max((r["max_rounding_rel"] for r in ok), default=0.0),
                max_rounding_rel_away=max((r["max_rounding_rel_away"] for r in ok), default=0.0),
                min_reset_rel=min(resets) if resets else None, max_reset_rel=max((r["max_reset_rel"] for r in ok), default=0.0),
                scenarios_with_reset=sum(1 for r in ok if r["reset"]), cross_positions=sum(r["cross_positions"] for r in ok),
                above_threshold_near_other_event=sum(r["above_threshold_near_other_event"] for r in ok))
    json.dump(dict(summary=summ, scenarios=res), open(outp, "w"), indent=1, default=str)
    print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
