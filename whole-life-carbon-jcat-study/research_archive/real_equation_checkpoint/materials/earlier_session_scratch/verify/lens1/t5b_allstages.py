"""All-stage valid scenarios (options only) where the unified model's B3-01 yearly series departs by more than 1e-9."""
import sys
sys.path.insert(0, "/tmp/claude-0/-home-user--/49c0bd7e-a786-5ae4-9a1e-e89e7996ede3/scratchpad/verify/lens1")
import h, synth
from common.compare import compare, flatten
from fastcalc import engine
from refcalc import registry
n = 0
found = []
for T in (0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.5, 6.0, 10.0):
    for lives in ([1.0, 2.0], [1.0, 2.0, 3.0], [2.0, 4.0], [0.5, 1.0], [0.25, 0.5], [0.3, 0.7], [1.0, 0.5, 0.75]):
        for seed in range(1, 41):
            for extra in ({}, {"n_refrigerants": 0}):
                o = dict(n_materials=12, n_equipment=6, n_refrigerants=2, service_life_choices=lives, explicit_event_share=0.0, change_list_share=0.0)
                o.update(extra)
                scn = synth.make_scenario(seed, "RC", "office", "S", T, **o)
                st, fs = h.diff(scn)
                n += 1
                if fs:
                    found.append((max(f.get("err", 0) for f in fs), seed, T, lives, extra, sorted({(f["mode"], f["unit"]) for f in fs})))
found.sort(reverse=True)
print("all-stage valid scenarios:", n, "failing 1e-9:", len(found))
for f in found[:8]:
    print("  ", f)
if found:
    e, seed, T, lives, extra, _ = found[0]
    o = dict(n_materials=12, n_equipment=6, n_refrigerants=2, service_life_choices=lives, explicit_event_share=0.0, change_list_share=0.0); o.update(extra)
    scn = synth.make_scenario(seed, "RC", "office", "S", T, **o)
    st, fs = h.diff(scn)
    for f in fs: print("     ", f)
