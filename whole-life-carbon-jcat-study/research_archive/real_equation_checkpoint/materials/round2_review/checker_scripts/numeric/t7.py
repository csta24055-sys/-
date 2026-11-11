"""Systematic single-field special-value sweep: every numeric leaf <- nan, inf, -inf, None (one at a time)."""
from h import *
import dataclasses, re, collections
nan, inf = float("nan"), float("inf")

def leaves(obj, path=""):
    """yield (path, getter-parent, key) for numeric / None leaves reachable from a scenario"""
    if dataclasses.is_dataclass(obj):
        for f in dataclasses.fields(obj):
            if f.name in ("meta",): continue
            v = getattr(obj, f.name)
            p = f"{path}.{f.name}" if path else f.name
            if isinstance(v, bool) or isinstance(v, str): continue
            if v is None or isinstance(v, (int, float)):
                yield p, obj, f.name, "attr"
            else:
                yield from leaves(v, p)
    elif isinstance(obj, list):
        idx = range(len(obj)) if len(obj) <= 8 else [i for i in (0, 1, 2, 29, 42, 59, 60, len(obj) - 1) if i < len(obj)]
        for i in idx:
            v = obj[i]; p = f"{path}[{i}]"
            if isinstance(v, bool) or isinstance(v, str): continue
            if v is None or isinstance(v, (int, float)):
                yield p, obj, i, "item"
            else:
                yield from leaves(v, p)
    elif isinstance(obj, dict):
        for k in list(obj)[:4]:
            v = obj[k]; p = f"{path}{{{k}}}"
            if isinstance(v, bool) or isinstance(v, str): continue
            if v is None or isinstance(v, (int, float)):
                yield p, obj, k, "item"
            else:
                yield from leaves(v, p)

def base_scn(variant):
    opts = [dict(profile_kind="LINEAR_TREND", grid_kind="LINEAR_DECLINE_TO_FLOOR", composite_share=0.34, epd_share=0.34, explicit_event_share=0.5, change_list_share=0.5, replacement_cycle=25.0, reconstruction_scenario="REBUILD_IDENTICAL"),
            dict(profile_kind="TABLE", grid_kind="STEPWISE", composite_share=0.34, epd_share=0.34, explicit_event_share=0.5, change_list_share=0.5),
            dict(profile_kind="CONSTANT", grid_kind="TABLE", composite_share=0.0, epd_share=0.0, explicit_event_share=0.0, change_list_share=0.0)][variant]
    s = synth.make_scenario(77 + variant, "RC", "office", "S", (60.0, 42.5, 30.0)[variant], n_materials=3, n_equipment=2, n_refrigerants=2, **opts)
    for row in s.materials[:1]:
        row.installation_factor_id = next((k for k, f in s.factors.items() if f.stages == ["A5"]), None)
    return s

out = collections.defaultdict(lambda: collections.Counter()); examples = {}
total = 0
for variant in range(3):
    s0 = base_scn(variant)
    paths = [p for p, *_ in leaves(s0)]
    for li, p in enumerate(paths):
        for val in (nan, inf, -inf, None):
            s = copy.deepcopy(s0)
            lst = list(leaves(s))
            pp, parent, key, how = lst[li]
            cur = getattr(parent, key) if how == "attr" else parent[key]
            if cur is None and val is None: continue
            if how == "attr": setattr(parent, key, val)
            else: parent[key] = val
            total += 1
            ref, full, tot = run3(s)
            pat = re.sub(r"\[\d+\]", "[]", re.sub(r"\{[^}]*\}", "{}", pp))
            exc = [isinstance(x, Exception) for x in (ref, full, tot)]
            if any(exc):
                if all(exc) and type(ref) is type(full) is type(tot):
                    cls = "same-crash"
                else:
                    cls = "CRASH-ASYM ref=%s full=%s tot=%s" % tuple(type(x).__name__ if isinstance(x, Exception) else "ok" for x in (ref, full, tot))
            else:
                recs = []
                for uid in ref:
                    recs += [(uid, x[0]) for x in diffs(ref[uid], full.get(uid, {}), 1e-9, 0.0)]
                    recs += [(uid, x[0]) for x in diffs(ref[uid], tot.get(uid, {}), 1e-9, 0.0, ignore_missing=True)]
                cls = "same" if not recs else "DIFF units=" + ",".join(sorted({u for u, _ in recs}))
            out[cls][(pat, repr(val))] += 1
            examples.setdefault((cls, pat, repr(val)), (variant, pp))
print("total single-field cases:", total)
for cls in sorted(out):
    n = sum(out[cls].values())
    print(f"\n== {cls}: {n} cases")
    if cls in ("same", "same-crash"): continue
    for (pat, val), c in sorted(out[cls].items()):
        print(f"     {pat} <- {val}  x{c}   e.g. variant {examples[(cls, pat, val)][0]} {examples[(cls, pat, val)][1]}")
