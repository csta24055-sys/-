"""Run the UNCHANGED approx_study (copy taken before stage b2) against the current reference; write to scratch."""
import importlib.util, json, sys, time
spec = importlib.util.spec_from_file_location("approx_before", "/tmp/claude-0/-home-user--/49c0bd7e-a786-5ae4-9a1e-e89e7996ede3/scratchpad/recheck/fix/b2/approx_study_before.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
n = int(sys.argv[1])
t0 = time.time()
r = m.run(n)
open(sys.argv[2], "w", encoding="utf-8").write(json.dumps(r, ensure_ascii=False, indent=1))
print("done", n, "in %.1fs" % (time.time() - t0), "rebuild", r["row_data_rebuilds_reference_B4_max_rel_diff"])
