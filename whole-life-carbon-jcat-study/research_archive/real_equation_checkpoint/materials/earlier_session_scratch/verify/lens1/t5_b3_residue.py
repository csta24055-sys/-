"""Part 5: how large does the B3-01 yearly-series difference get on VALID scenarios (options only, no mutation)?"""
import sys

sys.path.insert(0, "/tmp/claude-0/-home-user--/49c0bd7e-a786-5ae4-9a1e-e89e7996ede3/scratchpad/verify/lens1")
import h
import synth
from common.compare import compare, flatten
from fastcalc import engine
from refcalc import registry

worst = (0.0, None)
n = bad = 0
hist = {}
for stages in (["B3"], ["B3", "B4"], ["B3", "C1"], ["B1", "B3"], ["B3", "B7"], None):
    for T in (2.5, 3.0, 4.5, 6.0, 10.0, 24.0, 60.0):
        for lives in ([1.0, 2.0], [1.0, 2.0, 3.0], [2.0, 4.0], [0.5, 1.0], [T / 2, T / 4] if T >= 4 else [1.0, 0.5], [5.0, 10.0, 20.0]):
            for seed in range(1, 9):
                o = dict(n_materials=12, n_equipment=6, n_refrigerants=2, service_life_choices=lives, explicit_event_share=0.0,
                         change_list_share=0.0)
                if stages is not None:
                    o["included_stages"] = stages
                scn = synth.make_scenario(seed, "RC", "office", "S", T, **o)
                ref = registry.run_all(scn)
                engine.clear_baseline_cache()
                full = engine.evaluate(scn, detail=True)
                scale = abs(ref["SUM-03"]["value"]) or 1.0
                n += 1
                key = (tuple(stages) if stages else "ALL")
                for uid in ("B3-01", "X-07"):
                    c = compare(ref[uid], full[uid], floor=1e-9 * scale)
                    if c.max_abs_rel_error > 1e-9:
                        if uid == "B3-01":
                            bad += 1
                            hist[key] = hist.get(key, 0) + 1
                        if c.max_abs_rel_error > worst[0]:
                            fr, fc = flatten(ref[uid]), flatten(full[uid])
                            worst = (c.max_abs_rel_error, dict(seed=seed, T=T, lives=lives, stages=stages, unit=uid, path=c.worst_path,
                                                               ref=fr[c.worst_path], cand=fc[c.worst_path], wlc=ref["SUM-03"]["value"]))
print("valid scenarios:", n, " with B3-01 by_year difference > 1e-9:", bad)
print("by included-stage set:", hist)
print("worst:", worst)
# negative yearly emission reported by the candidate where the reference is exactly zero?
w = worst[1]
scn = synth.make_scenario(w["seed"], "RC", "office", "S", w["T"], n_materials=12, n_equipment=6, n_refrigerants=2,
                          service_life_choices=w["lives"], explicit_event_share=0.0, change_list_share=0.0,
                          **({"included_stages": w["stages"]} if w["stages"] else {}))
ref = registry.run_all(scn)
full = engine.evaluate(scn, detail=True)
print("reference B3-01 by_year:", [round(v, 6) for v in ref["B3-01"]["by_year"]])
print("unified   B3-01 by_year:", full["B3-01"]["by_year"])
print("reference B3-01 value:", ref["B3-01"]["value"], "unified:", full["B3-01"]["value"])
