"""V1 mutation testing of the BUILDER's 34 tests (verifier-designed mutations).

Each mutation is a single exact string replacement applied to a fresh COPY of the frozen
snapshot inside the verifier's scratch area (never the snapshot or the live tree). The
builder's unittest suite is then run on the copy; a mutation is 'caught' when at least one
test fails or errors. Usage: python3 -B mutate.py [scratch_dir]
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time

from common import SNAP, save

SCRATCH = sys.argv[1] if len(sys.argv) > 1 else \
    "/tmp/claude-0/-home-user--/d16c9837-8c7c-5bcc-8b70-730caf3a5491/scratchpad/v1/mutants"

MUTATIONS = {
    "M01_swap_tick_fire_priority": ("adapter.py", 'PRIO = {"por": 5, "early": 10, "tick": 20, "fire": 30}',
                                    'PRIO = {"por": 5, "early": 10, "tick": 30, "fire": 20}'),
    "M02_no_charge_conservation_at_switch": ("engine/sim.py", "                    self.s[g] = v\n",
                                             "                    pass  # mutated: states not re-initialised\n"),
    "M03_negative_packet_polarity_flipped": ("adapter.py", 'f"{tag}.neg", polarity=-1, cell="yearcell")',
                                             'f"{tag}.neg", polarity=+1, cell="yearcell")'),
    "M04a_rho_eps_not_2eps": ("adapter.py", "rho = eps * (2 - eps) / (1 - eps)", "rho = eps"),
    "M04b_rho_first_order_2eps": ("adapter.py", "rho = eps * (2 - eps) / (1 - eps)", "rho = 2 * eps"),
    "M04c_eps_1e-8": ("adapter.py", '"original": (Fraction(1, 10 ** 9), 0),', '"original": (Fraction(1, 10 ** 8), 0),'),
    "M05_clock_reset_to_zero_not_subtract": (
        "adapter.py",
        'self.packet(f"{tag}.rst", Cr, "vth", x, f"{tag}.fire", v0=u.V0, cell="clock", datapath=False)',
        'self.short(f"{tag}.rz", x, o, f"{tag}.fire", cell="clock")'),
    "M06_SR_set_wins": ("engine/logic.py", "                if l.reset in rising:\n                    updates[l.q] = False\n                elif l.set in rising:\n                    updates[l.q] = True",
                        "                if l.set in rising:\n                    updates[l.q] = True\n                elif l.reset in rising:\n                    updates[l.q] = False"),
    "M07_readout_ignores_yearcell_tap": ("adapter.py", '    B.taps[stage].append(f"{tag}.Ch")\n', "    pass\n"),
    "M08_no_substitution_suppression": ("adapter.py", "            pk = f\"{gt}.pk\"\n", "            pk = ev\n"),
    "M09_comparator_strict": ("engine/sim.py", "            return y >= 0", "            return y > 0"),
    "M10_impulsive_energy_left_value": ("engine/sim.py", "W[name] = (vm + vp) / 2 * q", "W[name] = vm * q"),
    "M11_set_semantics_off_one_per_batch": ("engine/sim.py", "            batch = [p for p in pending if p[0] == pmin]",
                                            "            batch = [p for p in pending if p[0] == pmin][:1]"),
    "M12_age_slope_sign": ("adapter.py", 'B.nl.R(f"{tag}.G", "railn", xa, G=u.Gu, cell="age")',
                           'B.nl.R(f"{tag}.G", "rail", xa, G=u.Gu, cell="age")'),
    "M13_repair_stage_gain_2": ("adapter.py", "nl.R(f\"{gt}.rp.{it['id']}.Rf\", x1, o1, G=u.Gu, cell=\"repair_amp\")",
                                "nl.R(f\"{gt}.rp.{it['id']}.Rf\", x1, o1, G=2 * u.Gu, cell=\"repair_amp\")"),
    "M14_current_source_sign": ("engine/mna.py", "                kcl_rhs(e.a, e.I)\n                kcl_rhs(e.b, -e.I)",
                                "                kcl_rhs(e.a, -e.I)\n                kcl_rhs(e.b, e.I)"),
    "M15_lookahead_priority_after_fire": ("adapter.py", 'PRIO = {"por": 5, "early": 10, "tick": 20, "fire": 30}',
                                          'PRIO = {"por": 5, "early": 40, "tick": 20, "fire": 30}'),
    "M16_initial_packets_on_first_tick": ("adapter.py",
                                          'B.packet(f"pk.init.{row[\'id\']}", B.val(A / (u.gamma * u.V0)), "rail", x, "por", v0=u.V0)',
                                          'B.packet(f"pk.init.{row[\'id\']}", B.val(A / (u.gamma * u.V0)), "rail", x, "tick", v0=u.V0)'),
    "M17_group_repair_stage_from_last_row": ("adapter.py", 'stage = rows[0]["repair"]["stage"]', 'stage = rows[-1]["repair"]["stage"]'),
    "M18_renewal_ignores_substituting_renovation": ("adapter.py", 'replaced = B.OR(f"{gt}.repl", [ev] + sub_fires)',
                                                    'replaced = B.OR(f"{gt}.repl", [ev])'),
}


def run_one(name, rel, old, new):
    dst = os.path.join(SCRATCH, name)
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(SNAP, dst, ignore=shutil.ignore_patterns("results", "__pycache__"))
    os.makedirs(os.path.join(dst, "results"))
    p = os.path.join(dst, rel)
    src = open(p).read()
    n = src.count(old)
    if n != 1:
        return {"applied": False, "occurrences": n}
    open(p, "w").write(src.replace(old, new))
    t0 = time.time()
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    try:
        cp = subprocess.run([sys.executable, "-B", "-m", "unittest", "discover", "-s", ".", "-p", "test_*.py"],
                            cwd=os.path.join(dst, "tests"), capture_output=True, text=True, timeout=900, env=env)
        out = cp.stdout + cp.stderr
    except subprocess.TimeoutExpired:
        out = "TIMEOUT"
    ran = re.search(r"Ran (\d+) tests", out)
    fail = re.search(r"FAILED \(([^)]*)\)", out)
    failing = sorted(set(re.findall(r"^(?:FAIL|ERROR): (\S+) \((\S+)\)", out, re.M)))
    res = {"applied": True, "file": rel, "ran": int(ran.group(1)) if ran else None,
           "result": fail.group(1) if fail else ("TIMEOUT" if out == "TIMEOUT" else "OK"),
           "caught": bool(fail) or out == "TIMEOUT" or not ran,
           "failing_tests": [f"{c}.{t}" for t, c in failing][:12], "seconds": round(time.time() - t0, 1)}
    shutil.rmtree(dst)
    return res


def main():
    os.makedirs(SCRATCH, exist_ok=True)
    only = set(os.environ.get("MUT_ONLY", "").split(",")) - {""}
    out = {}
    for name, (rel, old, new) in MUTATIONS.items():
        if only and name not in only:
            continue
        out[name] = run_one(name, rel, old, new)
        print(name, out[name]["result"] if out[name].get("applied") else out[name], flush=True)
    caught = [k for k, v in out.items() if v.get("caught")]
    summary = {"mutations": len(out), "applied": sum(1 for v in out.values() if v.get("applied")),
               "caught": len(caught), "not_caught": [k for k, v in out.items() if v.get("applied") and not v.get("caught")]}
    save(os.environ.get("MUT_OUT", "mutations_v1.json"), {"summary": summary, "detail": out})
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
