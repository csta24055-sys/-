import sys, time
sys.path.insert(0, "/tmp/claude-0/-home-user--/49c0bd7e-a786-5ae4-9a1e-e89e7996ede3/scratchpad/verify/lens1")
import h
import synth

for kw in ({}, {"n_materials": 12, "n_equipment": 6, "n_refrigerants": 4}):
    for T in (60.0, 300.0):
        t0 = time.perf_counter()
        scn = synth.make_scenario(5, "RC", "office", "S", T, **kw)
        t1 = time.perf_counter()
        st, f = h.diff(scn)
        t2 = time.perf_counter()
        print(kw, T, "gen %.3fs diff %.3fs" % (t1 - t0, t2 - t1), st, f[:2])
