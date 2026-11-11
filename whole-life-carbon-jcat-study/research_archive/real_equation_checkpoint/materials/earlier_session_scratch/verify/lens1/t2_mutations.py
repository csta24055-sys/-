"""Part 2: post-generation mutation fuzz. Mode 'single' applies each mutation alone to several base scenarios,
mode 'combo' applies 2-4 random mutations."""
import json
import random
import sys
import time

sys.path.insert(0, "/tmp/claude-0/-home-user--/49c0bd7e-a786-5ae4-9a1e-e89e7996ede3/scratchpad/verify/lens1")
import h
import muts
import synth
from synth import model

MODE = sys.argv[1] if len(sys.argv) > 1 else "single"
N = int(sys.argv[2]) if len(sys.argv) > 2 else 6
SEED = int(sys.argv[3]) if len(sys.argv) > 3 else 4242
rng = random.Random(SEED)

BASES = []
PERIODS = (60.0, 62.5, 2.5, 30.0, 100.0, 0.5, 24.0, 59.999999, 10.0000001, 129.0, 7.0, 1.0)


def base_scenario(k, seed):
    r = random.Random(seed)
    T = PERIODS[k % len(PERIODS)]
    o = dict(n_materials=r.choice((10, 14, 20)), n_equipment=r.choice((5, 8)), n_refrigerants=r.choice((4, 6)),
             composite_share=r.choice((0.3, 0.5)), epd_share=r.choice((0.2, 0.4)), explicit_event_share=r.choice((0.0, 0.5, 1.0)),
             change_list_share=r.choice((0.0, 0.5, 1.0)), profile_kind=r.choice((None,) + model.PROFILE_KINDS),
             grid_kind=r.choice((None,) + model.GRID_KINDS), service_life_mode=r.choice(("MIXED", "EXACT_DIVISOR", "CONTINUOUS", "INTEGER")),
             composite_pool_ratio=r.choice((0.1, 0.5)))
    if r.random() < 0.3:
        o["replacement_cycle"] = T / r.choice((2, 3, 2.5))
        o["reconstruction_scenario"] = "REBUILD_IDENTICAL"
    args = (r.randrange(1, 10 ** 9), r.choice(model.STRUCTURES), r.choice(model.USES), "S", T)
    return args, o


sigs = {}
per_mut = {}
status_count = {}
n_done = 0
t0 = time.perf_counter()


def run(case_id, k, bseed, names, mseed):
    global n_done
    args, o = base_scenario(k, bseed)
    scn = synth.make_scenario(*args, **o)
    mr = random.Random(mseed)
    applied = []
    for name in names:
        fn = dict(muts.MUTS)[name]
        try:
            if fn(scn, mr):
                applied.append(name)
        except Exception as exc:  # mutation itself not applicable
            applied.append(name + f"!{type(exc).__name__}")
    if not applied:
        return
    st, fs = h.diff(scn)
    n_done += 1
    for a in applied:
        pm = per_mut.setdefault(a, {"runs": 0, "bad": 0, "units": {}})
        pm["runs"] += 1
        pm["bad"] += bool(fs)
        for f in fs:
            key = f.get("unit", f["kind"]) + ":" + f["kind"]
            pm["units"][key] = pm["units"].get(key, 0) + 1
    status_count[st] = status_count.get(st, 0) + 1
    for f in fs:
        s = h.signature(f)
        rec = sigs.setdefault(s, {"count": 0, "muts": {}, "examples": []})
        rec["count"] += 1
        for a in applied:
            rec["muts"][a] = rec["muts"].get(a, 0) + 1
        if len(rec["examples"]) < 2:
            rec["examples"].append({"k": k, "bseed": bseed, "names": names, "mseed": mseed, "T": args[4], "finding": f})


if MODE == "single":
    names = [n for n, _ in muts.MUTS]
    for name in names:
        for rep in range(N):
            run(None, rng.randrange(len(PERIODS)), rng.randrange(10 ** 6), [name], rng.randrange(10 ** 6))
else:
    names = [n for n, _ in muts.MUTS]
    if MODE == "combo_clean":
        KNOWN = ("dangling", "annual_leak_rate=1e-12", "annual_leak_rate=1e-9", "annual_leak_rate=huge", "annual_leak_rate=tiny",
                 "leak_extremes_mix", "repair_rate=huge", "factors.delete_random", "grid.steps=", "grid.table!=", "profile.table",
                 "routes.factor_id=None", "operation.all_factor_ids", "operation.factor_ids", "component=None", "epd.factor_id=None",
                 "concrete_uptake", "construction.fuels", "construction.waste", "eol.demolition", "eol.hauls", "constant_with_nonzero_slope",
                 "grid.to_linear")
        names = [n for n in names if not any(k in n for k in KNOWN)]
    for it in range(N):
        chosen = rng.sample(names, rng.randint(2, 4))
        run(None, rng.randrange(len(PERIODS)), rng.randrange(10 ** 6), chosen, rng.randrange(10 ** 6))

print(f"mode={MODE} mutations={len(muts.MUTS)} scenarios compared: {n_done} ({time.perf_counter() - t0:.0f}s) status={status_count}")
for s, rec in sorted(sigs.items(), key=lambda kv: -kv[1]["count"]):
    top = sorted(rec["muts"].items(), key=lambda kv: -kv[1])[:8]
    print("\n==", s, "count", rec["count"])
    print("   muts:", top)
    for ex in rec["examples"][:1]:
        print("   ", json.dumps(ex, default=str)[:700])

print("\n#### per mutation (only those with differences)")
for name, pm in sorted(per_mut.items()):
    if pm["bad"]:
        print(f"{name}: {pm['bad']}/{pm['runs']}  {sorted(pm['units'].items())}")
