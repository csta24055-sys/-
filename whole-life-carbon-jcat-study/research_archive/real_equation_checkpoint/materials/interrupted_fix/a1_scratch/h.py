"""Harness: strict leaf-by-leaf comparison of refcalc vs fastcalc (own code)."""
import copy, math, sys, traceback
sys.dont_write_bytecode = True
import synth
from synth import model, population
from refcalc import registry
from fastcalc import engine, closed_forms as cf
registry.load_all()
SMALL = {"n_materials": 12, "n_equipment": 6, "n_refrigerants": 4}

def flat(v, p=""):
    out = {}
    if isinstance(v, dict):
        for k in sorted(v, key=str):
            if str(k).startswith("_"):
                continue
            out.update(flat(v[k], f"{p}.{k}" if p else str(k)))
    elif isinstance(v, (list, tuple)):
        for i, it in enumerate(v):
            out.update(flat(it, f"{p}[{i}]"))
        if not v:
            out[p + "[]"] = "<empty>"
    elif isinstance(v, set):
        out[p] = ("set", tuple(sorted(v, key=str)))
    else:
        out[p] = v
    return out

def isnum(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)

def diffs(ref, cand, tol=1e-9, floor=0.0, ignore_missing=False, check_extra=True):
    """list of (path, ref, cand, rel) for leaves that differ by more than tol relative (strict about inf/nan/type)."""
    fr, fc = flat(ref), flat(cand)
    out = []
    for p, rv in fr.items():
        if p not in fc:
            if not ignore_missing:
                out.append((p, rv, "<missing>", None))
            continue
        cv = fc[p]
        if isnum(rv) and isnum(cv):
            if math.isnan(rv) or math.isnan(cv):
                if not (math.isnan(rv) and math.isnan(cv)):
                    out.append((p, rv, cv, float("nan")))
                continue
            if rv == cv:
                continue
            if math.isinf(rv) or math.isinf(cv):
                out.append((p, rv, cv, float("inf")))
                continue
            den = max(abs(rv), abs(cv), floor)
            rel = abs(cv - rv) / den if den else float("inf")
            if rel > tol:
                out.append((p, rv, cv, rel))
        else:
            if type(rv) is not type(cv) or rv != cv:
                if isinstance(rv, bool) != isinstance(cv, bool) or rv != cv:
                    out.append((p, rv, cv, None))
    if check_extra:
        for p in fc:
            if p not in fr:
                out.append((p, "<absent in ref>", fc[p], None))
    return out

def run3(scn, baseline_totals=None):
    res = []
    for fn in (lambda: registry.run_all(scn), lambda: engine.evaluate(scn, detail=True, baseline_totals=baseline_totals),
               lambda: engine.evaluate(scn, detail=False, baseline_totals=baseline_totals)):
        try:
            res.append(fn())
        except RecursionError as e:
            res.append(e)
        except Exception as e:
            e._tb = traceback.format_exc()
            res.append(e)
    return res

def check(scn, label="", tol=1e-9, floor_rel=0.0, quiet=False, maxshow=6):
    """returns list of difference records; prints them."""
    ref, full, tot = run3(scn)
    recs = []
    exc = [isinstance(x, Exception) for x in (ref, full, tot)]
    if any(exc):
        if not (all(exc) and type(ref) is type(full) is type(tot)):
            recs.append(("CRASH-ASYM", f"ref={ref!r:.150}", f"full={full!r:.150}", f"tot={tot!r:.150}"))
        elif not quiet:
            pass
        if recs and not quiet:
            print(f"[{label}] CRASH ASYMMETRY: ref={ref!r:.200} | full={full!r:.200} | tot={tot!r:.200}")
        return recs
    scale = abs(ref["SUM-03"]["value"]) if isnum(ref["SUM-03"]["value"]) else 0.0
    floor = floor_rel * scale
    for uid in ref:
        d = diffs(ref[uid], full.get(uid, {}), tol, floor)
        for x in d:
            recs.append(("full", uid) + x)
        d = diffs(ref[uid], tot.get(uid, {}), tol, floor, ignore_missing=True)
        for x in d:
            recs.append(("tot", uid) + x)
    for uid in full:
        if uid not in ref and not uid.startswith("_"):
            recs.append(("full", uid, "<unit absent in ref>"))
    if recs and not quiet:
        print(f"[{label}] {len(recs)} differences (SUM-03={scale!r})")
        for r in recs[:maxshow]:
            print("   ", r)
    return recs

def mk(seed=1, period=60.0, structure="RC", use="office", **opts):
    o = dict(SMALL); o.update(opts)
    return synth.make_scenario(seed, structure, use, "S", period, **o)
