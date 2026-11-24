"""Regenerate every D result file (no network). ~3 minutes on the G3 machine.
Run: cd routes/D_verification && PYTHONDONTWRITEBYTECODE=1 math7-py -B code/run_all.py
"""
import os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ENV = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
STEPS = [("check_boundary.py", []), ("check_events.py", []), ("check_states.py", []),
         ("check_joule_ac.py", []), ("probe_routes.py", ["100000", "20000"]), ("bench.py", ["5"])]
for script, args in STEPS:
    log = os.path.join(ROOT, "results", script.replace(".py", "_log.txt"))
    with open(log, "w") as f:
        r = subprocess.run([sys.executable, "-B", os.path.join(HERE, script)] + args, cwd=ROOT, env=ENV,
                           stdout=f, stderr=subprocess.STDOUT)
    print(script, "exit", r.returncode, "->", os.path.relpath(log, ROOT))
