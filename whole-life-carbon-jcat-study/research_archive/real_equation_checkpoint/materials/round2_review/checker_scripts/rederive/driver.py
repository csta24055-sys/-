import sys, copy, math, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user--/49c0bd7e-a786-5ae4-9a1e-e89e7996ede3/scratchpad/recheck/rederive")
import synth
from synth import population
from bench import mutations
from refcalc import registry
import mine
registry.load_all()

def scenarios():
    out = []
    for i, s in enumerate(population.verification_population(24, 4242, max_size="S")):
        out.append((f"pop{i}", s))
    out += [("edge:" + n, s) for n, s in population.edge_cases()]
    structs = ["S", "RC", "SRC", "W"]; uses = ["office", "residential", "school", "hospital", "retail", "warehouse"]
    for k in range(14):
        T = [60.0, 50.0, 42.5, 99.9, 30.0, 62.5, 75.0][k % 7]
        out.append((f"dirty{k}", synth.make_scenario(900 + k, structs[k % 4], uses[k % 6], "S", T, dirty=True,
                    n_materials=40, n_equipment=15, n_refrigerants=6, defect_share=0.15)))
    for name, (fn, opts) in mutations.MUTATIONS.items():
        o = dict(mutations.SMALL); o.update(opts)
        s = synth.make_scenario(31, "RC", "office", "S", 60.0, **o)
        fn(s)
        out.append(("mut:" + name, s))
    for T, lives in mutations.DECIMAL_BOUNDARIES:
        s = synth.make_scenario(55, "S", "retail", "S", T, service_life_choices=list(lives), n_materials=12, n_equipment=6, n_refrigerants=4)
        out.append((f"dec:{T}", s))
    for sub in mutations.STAGE_SUBSETS:
        s = synth.make_scenario(77, "W", "school", "S", 62.5, included_stages=list(sub), n_materials=12, n_equipment=6, n_refrigerants=4,
                                replacement_cycle=25.0, reconstruction_scenario="REBUILD_IDENTICAL")
        out.append((f"sub:{'+'.join(sub) or 'none'}", s))
    return out

KEYS = {
 "A13-05": ["q_ord", "q_inst", "n_skipped"], "A13-02": ["by_item", "n_invalid"],
 "X-15": ["kind", "factor", "conv", "n_unresolved", "n_epd_declined"],
 "A13-01": ["value", "by_item", "n_skipped"], "A13-03": ["value", "by_item", "n_skipped"],
 "A13-04": ["value", "by_item", "n_skipped"], "X-01": ["value", "by_item", "n_skipped"],
 "A4-01": ["value", "by_item", "n_skipped"], "A4-02": ["value", "by_item", "n_skipped"], "X-12": ["value", "by_item", "n_skipped"],
 "A5-01": ["value", "computed"], "A5-02": ["value", "n_skipped"], "A5-03": ["value", "n_skipped"], "A5-04": ["value"],
 "B1-01": ["value", "n_skipped"], "B1-02": ["value", "by_item", "by_year", "n_skipped"], "B1-03": ["value", "by_year", "n_skipped"], "B1-04": ["value", "n_skipped"],
 "B6-04": ["by_year", "computed"], "X-06": ["by_year", "source"], "B6-01": ["by_year", "computed"], "B6-02": ["by_year", "n_skipped"],
 "B6-03": ["value"], "B2-01": ["value", "computed"], "B7-01": ["by_year", "n_skipped"], "B7-02": ["by_year", "n_skipped"], "B7-03": ["by_year", "n_skipped"], "B7-04": ["value"],
 "B4-01": ["events", "n_events"], "B4-03": ["by_item"], "B3-01": ["value", "by_year", "n_skipped"], "B3-02": ["value", "n_skipped"],
 "C1-01": ["value", "n_skipped"], "C2-01": ["value", "by_item", "n_skipped"], "C3-01": ["value", "by_item", "n_skipped", "n_routes_skipped"],
 "C4-01": ["value", "by_item", "n_skipped", "n_routes_skipped"], "X-14": ["value", "by_item", "n_skipped"],
 "B4-02": ["value", "by_item_material", "by_item_equipment", "by_year", "n_partial"],
 "B5-01": ["value", "n_events", "by_year", "computed"], "X-02": ["by_stage"],
 "SUM-01": ["value"], "SUM-02": ["value"], "SUM-03": ["value"], "SUM-04": ["value"], "SUM-05": ["value"], "SUM-06": ["value"],
 "SUM-07": ["defined", "by_stage"], "X-07": ["by_year", "cumulative", "value"], "X-13": ["by_item", "waste_by_item"],
 "X-16": ["value", "by_item", "n_skipped"], "X-10": ["resource_kg", "waste_kg", "n_excluded"], "QA-02": ["ok", "violations", "warnings"],
 "C-05": ["ok", "n_mass_unchecked"],
}

def differ(a, b, path, out):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in set(a) | set(b):
            if k not in a or k not in b:
                out.append((path + "." + str(k), a.get(k, "<absent>"), b.get(k, "<absent>")))
            else:
                differ(a[k], b[k], path + "." + str(k), out)
    elif isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        if len(a) != len(b):
            out.append((path + ".len", len(a), len(b))); return
        for i, (x, y) in enumerate(zip(a, b)):
            differ(x, y, f"{path}[{i}]", out)
    elif isinstance(a, bool) or isinstance(b, bool) or a is None or b is None or isinstance(a, str) or isinstance(b, str):
        if a != b:
            out.append((path, a, b))
    else:
        if a == b:
            return
        if isinstance(a, float) and isinstance(b, float) and math.isnan(a) and math.isnan(b):
            return
        den = max(abs(a), abs(b))
        if not (abs(a - b) <= 1e-9 * den):
            out.append((path, a, b))

def main():
    tot = collections.Counter(); bad = collections.defaultdict(list)
    scns = scenarios()
    print("n scenarios", len(scns))
    for name, s in scns:
        try:
            ref = registry.run_all(s)
        except Exception as e:
            print("REF RAISED", name, repr(e)); continue
        try:
            my = mine.run(s)
        except Exception as e:
            import traceback; traceback.print_exc()
            print("MINE RAISED", name, repr(e)); continue
        for uid, keys in KEYS.items():
            tot[uid] += 1
            for k in keys:
                out = []
                if k not in ref[uid]:
                    out.append((k, "<absent in ref>", my[uid].get(k)))
                else:
                    differ(ref[uid][k], my[uid].get(k, "<absent>"), k, out)
                if out:
                    bad[uid].append((name, out[:3], len(out)))
    for uid in KEYS:
        print(uid, "scenarios", tot[uid], "with diffs", len({n for n, _, _ in bad[uid]}))
    print()
    for uid in KEYS:
        for name, out, n in bad[uid][:6]:
            print(uid, name, n, out)
main()
