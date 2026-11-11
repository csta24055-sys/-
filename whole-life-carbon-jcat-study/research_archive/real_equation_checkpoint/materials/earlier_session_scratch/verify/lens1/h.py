"""Shared helpers of the independent fuzzing harness (verifier lens 1)."""
from __future__ import annotations

import math
import re
import traceback

import synth
from common.compare import compare, flatten
from fastcalc import engine
from refcalc import registry
from synth import model, population

registry.load_all()
TOL = 1e-9


def run_ref(scn):
    try:
        return registry.run_all(scn), None
    except RecursionError as exc:
        return None, ("RecursionError", "")
    except Exception as exc:  # noqa
        tb = traceback.extract_tb(exc.__traceback__)[-1]
        return None, (type(exc).__name__, f"{tb.filename.split('/')[-1]}:{tb.lineno} {exc}")


def run_fast(scn, detail):
    engine.clear_baseline_cache()
    try:
        return engine.evaluate(scn, detail=detail), None
    except RecursionError as exc:
        return None, ("RecursionError", "")
    except Exception as exc:  # noqa
        tb = traceback.extract_tb(exc.__traceback__)[-1]
        return None, (type(exc).__name__, f"{tb.filename.split('/')[-1]}:{tb.lineno} {exc}")


def norm_path(p):
    return re.sub(r"\[\d+\]", "[*]", p)


def diff(scn, tol=TOL):
    """Return (status, findings). findings = list of dicts."""
    ref, ref_err = run_ref(scn)
    full, full_err = run_fast(scn, True)
    summ, summ_err = run_fast(scn, False)
    out = []
    if ref_err or full_err or summ_err:
        if ref_err and full_err and summ_err:
            return "all_crash", [{"kind": "all_crash", "ref": ref_err, "full": full_err, "summ": summ_err}]
        out.append({"kind": "crash_asym", "ref": ref_err, "full": full_err, "summ": summ_err})
        if ref is None:
            return "crash_asym", out
    scale = abs(ref["SUM-03"]["value"]) or 1.0
    if isinstance(scale, float) and (math.isnan(scale) or math.isinf(scale)):
        scale = 1.0
    for mode, cand, ign in (("full", full, False), ("summary", summ, True)):
        if cand is None:
            continue
        missing_units = sorted(set(ref) - set(cand))
        extra_units = sorted(set(cand) - set(ref))
        if missing_units or extra_units:
            out.append({"kind": "unit_set", "mode": mode, "missing": missing_units, "extra": extra_units})
        for uid, rv in ref.items():
            c = compare(rv, cand.get(uid, {}), floor=tol * scale, ignore_missing=ign)
            if c.mismatches:
                out.append({"kind": "mismatch", "mode": mode, "unit": uid, "items": c.mismatches[:4], "n": len(c.mismatches)})
            if c.missing:
                out.append({"kind": "missing", "mode": mode, "unit": uid, "items": c.missing[:4], "n": len(c.missing)})
            if c.extra and mode == "full":
                out.append({"kind": "extra", "mode": mode, "unit": uid, "items": c.extra[:4], "n": len(c.extra)})
            if c.max_abs_rel_error > tol:
                fr, fc = flatten(rv), flatten(cand.get(uid, {}))
                out.append({"kind": "numeric", "mode": mode, "unit": uid, "path": c.worst_path,
                            "err": c.max_abs_rel_error, "ref": fr.get(c.worst_path), "cand": fc.get(c.worst_path),
                            "scale": scale})
    return ("ok" if not out else "diff"), out


def signature(f):
    if f["kind"] == "numeric":
        return ("numeric", f["mode"], f["unit"], norm_path(f["path"]))
    if f["kind"] in ("mismatch", "missing", "extra"):
        return (f["kind"], f["mode"], f["unit"], norm_path(f["items"][0].split(":")[0]))
    if f["kind"] == "crash_asym":
        return ("crash_asym", str(f["ref"]), str(f["full"]), str(f["summ"]))
    return (f["kind"],)
