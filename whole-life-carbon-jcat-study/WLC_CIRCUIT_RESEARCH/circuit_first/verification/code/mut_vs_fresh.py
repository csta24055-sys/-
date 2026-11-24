"""V1: run the VERIFIER's fresh-case suite (run_fresh) against mutants the builder's tests missed."""
import json, os, shutil, subprocess, sys
from common import SNAP, save
from mutate import MUTATIONS
SCR = "/tmp/claude-0/-home-user--/d16c9837-8c7c-5bcc-8b70-730caf3a5491/scratchpad/v1/mut_fresh"
NAMES = sys.argv[1].split(",")
out = {}
for name in NAMES:
    rel, old, new = MUTATIONS[name]
    dst = os.path.join(SCR, name)
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(SNAP, dst, ignore=shutil.ignore_patterns("results", "__pycache__", "tests"))
    p = os.path.join(dst, rel); s = open(p).read(); assert s.count(old) == 1
    open(p, "w").write(s.replace(old, new))
    res = os.path.join(SCR, name + "_res"); os.makedirs(res, exist_ok=True)
    env = dict(os.environ, CF_SNAPSHOT=dst, CF_RESULTS=res, PYTHONDONTWRITEBYTECODE="1")
    cp = subprocess.run([sys.executable, "-B", "run_fresh.py"], capture_output=True, text=True, env=env, timeout=3000)
    try:
        summ = json.load(open(os.path.join(res, "fresh_cases.json")))["summary"]
    except Exception as e:
        summ = {"error": cp.stderr[-800:]}
    BASE = {"signed_inputs_negative_amount_and_rate"}      # fails on the unmutated snapshot (known defect)
    out[name] = {"caught_by_verifier_suite": bool(set(summ.get("fail", [])) - BASE) or not summ.get("event_checks_pass", True)
                 or not summ.get("year_checks_pass", True) or "error" in summ, "summary": summ}
    shutil.rmtree(dst, ignore_errors=True)
    print(name, json.dumps(out[name])[:600], flush=True)
save("mutations_vs_verifier_suite.json", out)
