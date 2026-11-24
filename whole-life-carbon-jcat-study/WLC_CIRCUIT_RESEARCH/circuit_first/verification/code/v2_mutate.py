"""V2: stage-B mutation testing (verifier-designed mutants) on copies of snapshot 80ec2de.

Each mutant = one exact string replacement in a copy laid out like the repository
(…/whole-life-carbon-jcat-study/WLC_CIRCUIT_RESEARCH/circuit_first, with symlinks to the frozen
09_APPROX_STUDY / 10_TRANSFORM_STUDY so the builder's own tests find the oracle). Two judges:
  (a) the builder's unit suite (47 tests, `unittest discover -s tests`);
  (b) the verifier's oracle harness (v2_oracle.run) on a fast edge-scenario set, 6 T each.
Usage: python3 -B v2_mutate.py [names,comma-separated | all]
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from common import SNAP, save  # noqa: E402

SCR = "/tmp/claude-0/-home-user--/d16c9837-8c7c-5bcc-8b70-730caf3a5491/scratchpad/v2/mutB"
REPO_STUDY = "/home/user/-/whole-life-carbon-jcat-study"
AB = "adapter_building.py"
MUT = {
    "B01_conversion_skipped": (AB, "        if conv is None:\n            return rail\n        key = (rec.factor_id, conv.value)",
                               "        if conv is None or True:\n            return rail\n        key = (rec.factor_id, conv.value)"),
    "B02_wrong_rail_transport_delivery": (AB, 'a4 = q_ord_chain(A, A.derived_rail(*hit), row, q, w, "transport")',
                                          'a4 = q_ord_chain(A, rail if rail is not None else A.derived_rail(*hit), row, q, w, "transport")'),
    "B03_rho_leg_into_B2": (AB, 'nl.R("el.r.Gm", "el.Fr", B.bus("B6"), G=Gs_out, cell="split")',
                            'nl.R("el.r.Gm", "el.Fr", B.bus("B2"), G=Gs_out, cell="split")'),
    "B04_b5_base_without_A4": (AB, 'for s in ("A1-A3", "A4", "A5", "C1", "C2", "C3", "C4")\n                          if sums[s] is not None',
                               'for s in ("A1-A3", "A5", "C1", "C2", "C3", "C4")\n                          if sums[s] is not None'),
    "B05_refrigerant_top_up_ignored": (AB, "        top = bool(d.top_up)", "        top = False"),
    "B06_refrigerant_reset_short_removed": (AB, 'nl.switch(f"{tg}.Ssh", xm, om, f"{tg}.sh", cell="refrigerant")',
                                            'nl.switch(f"{tg}.Ssh", xm, om, "ZERO", cell="refrigerant")'),
    "B07_near_equal_periods_merged": (AB, '        key = ("P", rc.value) if has_cycle else None',
                                      '        key = ("P", Fraction(round(rc.value * 10), 10)) if has_cycle else None'),
    "B08_readout_bus_not_emptied": (AB, '[{f"{tag}.sh": True}, {f"{tag}.sh": False}], cell="readout")',
                                    '[{}, {}], cell="readout")'),
    "B09_mdac_msb_weight": (AB, "                G = slope * (Gs * (-(2 ** b) if neg else 2 ** b))",
                            "                G = slope * (Gs * (-(2 ** b + (b == 7)) if neg else 2 ** b + (b == 7)))"),
    "B10_epd_validity_strict": (AB, "if rec.valid_until >= scn.project.assessment_date:", "if rec.valid_until > scn.project.assessment_date:"),
    "B11_year_cell_tick_commit_skipped": (AB, '[{f"{tag}.hold": True}, {f"{tag}.fb": False}, {f"{tag}.cm": True}, {f"{tag}.cm": False},',
                                          '[{f"{tag}.hold": True}, {f"{tag}.fb": False}, {}, {},'),
}
FAST = ["EDGE:rebuild_within_period", "EDGE:refurbishment_divides_period", "EDGE:explicit_event_lists",
        "EDGE:top_up_none", "EDGE:top_up_all", "EDGE:generation_exceeds_consumption", "EDGE:all_epd",
        "EDGE:life_shorter_than_one_year", "EDGE:linear_trend_profiles", "E5"]
T_FAST = [0.999999, 7.5, 16.000001, 33.3, 60.000001, 129.999999, 130.0]


def make_copy(name):
    root = os.path.join(SCR, name)
    shutil.rmtree(root, ignore_errors=True)
    dst = os.path.join(root, "whole-life-carbon-jcat-study", "WLC_CIRCUIT_RESEARCH", "circuit_first")
    shutil.copytree(SNAP, dst, ignore=shutil.ignore_patterns("__pycache__"))
    # harness adaptation only: point the builder's oracle path at the real frozen tree (the
    # copy lives outside the git repository, so tstudy's frozen-tree git check needs the real path)
    old = 'STUDY = os.path.normpath(os.path.join(ROOT, "..", ".."))'
    patched = 0
    for fn in sorted(os.listdir(os.path.join(dst, "tests"))):     # every builder test/compare file with the path
        tp = os.path.join(dst, "tests", fn)
        if fn.endswith(".py"):
            src = open(tp).read()
            if src.count(old) == 1:
                open(tp, "w").write(src.replace(old, f"STUDY = {REPO_STUDY!r}"))
                patched += 1
    assert patched >= 1
    return root, dst


def run_one(name):
    rel, old, new = MUT[name] if name in MUT else (None, None, None)
    root, dst = make_copy(name)
    if rel:
        p = os.path.join(dst, rel)
        s = open(p).read()
        n = s.count(old)
        if n != 1:
            shutil.rmtree(root)
            return {"applied": False, "occurrences": n}
        open(p, "w").write(s.replace(old, new))
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", GIT_OPTIONAL_LOCKS="0")
    only = os.environ.get("V2_ONLY", "")
    t0 = time.time()
    try:
        if only == "verifier":
            raise subprocess.TimeoutExpired("skip", 0)
        cp = subprocess.run([sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"],
                            cwd=dst, capture_output=True, text=True, timeout=1800, env=env)
        out = cp.stdout + cp.stderr
    except subprocess.TimeoutExpired:
        out = "TIMEOUT" if only != "verifier" else "SKIPPED"
    ran = re.search(r"Ran (\d+) tests", out)
    fail = re.search(r"FAILED \(([^)]*)\)", out)
    failing = sorted(set(re.findall(r"^(?:FAIL|ERROR): (\S+) \((\S+)\)", out, re.M)))
    builder = {"ran": int(ran.group(1)) if ran else None, "result": fail.group(1) if fail else ("TIMEOUT" if out == "TIMEOUT" else "OK"),
               "caught": bool(fail) or out == "TIMEOUT" or not ran, "failing": [f"{c}.{t}" for t, c in failing][:8],
               "seconds": round(time.time() - t0, 1)}
    if only == "builder":
        shutil.rmtree(root)
        return {"applied": True, "file": rel, "builder_suite": builder}
    # verifier oracle harness on the mutant
    t1 = time.time()
    res_dir = os.path.join(root, "vres")
    os.makedirs(res_dir)
    env2 = dict(env, CF_SNAPSHOT=dst, CF_RESULTS=res_dir)
    code = ("import sys; sys.path.insert(0, %r); import v2_oracle as o; "
            "r = o.run('mut', %r, 'full', %r); "
            "r2 = o.run('mut_noB2', ['EDGE:generation_exceeds_consumption', 'E5'], 'no_B2', %r); "
            "import json; print('RESULT', json.dumps({'pass': r['pass'] and r2['pass'], 'max': {k: v for k, v in r['max_rel'].items() if v}, "
            "'max_noB2': {k: v for k, v in r2['max_rel'].items() if v}}))") % (HERE, FAST, T_FAST, T_FAST)
    try:
        cp2 = subprocess.run([sys.executable, "-B", "-c", code], capture_output=True, text=True, timeout=3000, env=env2)
        m = re.search(r"^RESULT (.*)$", cp2.stdout, re.M)
        ver = json.loads(m.group(1)) if m else {"error": (cp2.stdout + cp2.stderr)[-600:]}
    except subprocess.TimeoutExpired:
        ver = {"error": "TIMEOUT"}
    ver["caught"] = (not ver.get("pass", False))
    ver["seconds"] = round(time.time() - t1, 1)
    shutil.rmtree(root)
    return {"applied": True, "file": rel, "builder_suite": builder, "verifier_oracle": ver}


def main():
    names = sys.argv[1].split(",") if len(sys.argv) > 1 and sys.argv[1] != "all" else ["BASELINE"] + list(MUT)
    os.makedirs(SCR, exist_ok=True)
    out = {}
    for nm in names:
        out[nm] = run_one(nm)
        b, v = out[nm].get("builder_suite", {}), out[nm].get("verifier_oracle", {})
        print(nm, "builder:", b.get("result"), b.get("failing", [])[:3], "| verifier caught:", v.get("caught"),
              {k: f"{x:.1e}" if isinstance(x, float) else x for k, x in (v.get("max") or {}).items() if (isinstance(x, (int, float)) and x > 1e-9)},
              v.get("error", "")[:200] if isinstance(v.get("error"), str) else "", flush=True)
    tag = os.environ.get("MUT_TAG", "all")
    save(f"v2_mutations_{tag}.json", out)


if __name__ == "__main__":
    main()
