"""Part 7: systematic sweeps (defect kinds alone, exact multiples of cycles, the study's own population with fresh seeds)."""
import math
import sys
import time

sys.path.insert(0, "/tmp/claude-0/-home-user--/49c0bd7e-a786-5ae4-9a1e-e89e7996ede3/scratchpad/verify/lens1")
import h
import synth
from synth import model, population

SMALL = dict(n_materials=20, n_equipment=8, n_refrigerants=6)
tot = {}


def tally(group, scn, tag):
    st, fs = h.diff(scn)
    g = tot.setdefault(group, {"n": 0, "bad": 0, "sigs": {}})
    g["n"] += 1
    g["bad"] += bool(fs)
    for f in fs:
        s = h.signature(f)
        e = g["sigs"].setdefault(s, [0, tag, f])
        e[0] += 1


t0 = time.perf_counter()
# A. each defect kind alone and all together, share 0.02 / 1.0
for kinds in [[k] for k in model.DEFECT_KINDS] + [list(model.DEFECT_KINDS)]:
    for T in (0.5, 1.0, 2.5, 30.0, 59.999999, 60.0, 60.000001, 62.5, 100.0, 299.999):
        for share in (0.02, 1.0):
            for sv in (True, False):
                for seed in (1, 2):
                    scn = synth.make_scenario(seed * 1000 + int(T), model.STRUCTURES[seed % 4], model.USES[(seed + int(T)) % 6], "S", T,
                                              dirty=True, defect_kinds=kinds, defect_share=share, state_variety=sv,
                                              explicit_event_share=0.5, change_list_share=0.5, **SMALL)
                    tally("A defect kinds", scn, (kinds, T, share, sv, seed))
# B. exact multiples
for T in (1.0, 2.0, 10.0, 12.0, 24.0, 30.0, 60.0, 100.0, 120.0, 300.0):
    divs = [T / k for k in (1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 24, 30, 60, 100, 120) if T / k >= 0.05]
    near = [d * f for d in divs[:6] for f in (1 - 1e-12, 1 + 1e-12, 1 - 2 ** -52, 1 + 2 ** -52)]
    for lives in (divs, near, divs[:3], divs[3:], [divs[0]], near[:4], divs + near):
        for rc in (None, T, T / 2, T / 3, T / 4 * (1 + 1e-12), T / 5 * (1 - 1e-12)):
            o = dict(SMALL)
            o.update(service_life_choices=lives, explicit_event_share=0.0, change_list_share=0.0)
            if rc is not None:
                o.update(replacement_cycle=rc, reconstruction_scenario="REBUILD_IDENTICAL")
            scn = synth.make_scenario(int(T) * 7 + len(lives), "SRC", "hospital", "S", T, **o)
            tally("B exact multiples", scn, (T, lives[:4], rc))
# C. study population, fresh seeds
for seed in (424242, 31415926):
    for scn in population.verification_population(300, seed=seed, max_size="M"):
        tally("C study population (fresh seeds)", scn, scn.meta.scenario_id)
# D. edge cases of the study on other seeds and periods
for seed in (3, 11):
    for period in (60.0, 37.3):
        for name, scn0 in population.edge_cases():
            pass
print(f"{time.perf_counter() - t0:.0f}s")
for g, v in tot.items():
    print(f"\n{g}: scenarios {v['n']}, with differences {v['bad']}")
    for s, (cnt, tag, f) in sorted(v["sigs"].items(), key=lambda kv: -kv[1][0]):
        print("    ", s, cnt, "e.g.", str(tag)[:200], {k: f[k] for k in ("err", "ref", "cand") if k in f})
