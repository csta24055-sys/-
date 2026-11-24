"""Pass 2, route B check (4): is "the refrigerant automaton stores less state than msp" real or a metric
artefact?  Compare B's automaton tuple with (i) msp's stored per-device tables/knots (what B counted) and
(ii) the MERGED knot form of the same unit (canon.py, chapter 17's third implementation), which is a
random-access representation; measure random-access and sorted-sweep time and tracemalloc peaks.

B's grammar.py is loaded only as a probe. Run:
  PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0 python3 -B code/p2_hb4.py
"""
import importlib.util, os, random, statistics, sys, time, tracemalloc
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import p2_common as C   # noqa: E402


def load_b():
    p = os.path.join(C.RESEARCH, "routes", "B_formula_network", "code", "grammar.py")
    spec = importlib.util.spec_from_file_location("B_grammar", p)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def med(f, reps=5):
    ts = []
    for _ in range(reps):
        t0 = time.perf_counter(); f(); ts.append(time.perf_counter() - t0)
    return statistics.median(ts)


def peak(f):
    tracemalloc.start(); x = f(); p = tracemalloc.get_traced_memory()[1]; tracemalloc.stop()
    return p, x


def one(tag, scn, B, canon, timechar, population):
    m = C.frozen()
    sy = m["unified"].System(scn)
    H = int(sy.H)
    can = canon.build(canon.make_system(scn, population.BASELINES))
    out = {"scenario": scn.meta.scenario_id, "H": H}
    merged = {}
    for u in ("B1-02", "B1-03", "B1-04"):
        A0, ev, la = canon.Canon(H=H, terms=can.unit_terms.get(u, [])).knot_form()
        merged[u] = {"lattice_knots": len(la), "event_knots": len(ev), "coefficients": 1 + 2 * (len(la) + len(ev)),
                     "msp_pieces_stored": len(sy.pieces.get(u, [])),
                     "msp_knots_stored": (sy.K[u].n_knots if u in sy.K else sy.I14.n_knots)}
    out["merged_knot_form"] = merged
    rc = B.RefrigerantCircuit(scn, H)
    st = rc.state_tuple()
    out["B_automaton_state_tuple"] = st
    out["B_automaton_numbers_total"] = sum(st)
    # timing: 200 random T in (0, 60]
    rng = random.Random(4)
    Ts = sorted(round(rng.uniform(0.01, 60.0), 6) for _ in range(200))
    kfs = {u: timechar.KF(canon.Canon(H=H, terms=can.unit_terms.get(u, []))) for u in ("B1-02", "B1-03", "B1-04")}
    out["seconds_median5"] = {
        "B_automaton_random_access(200 fresh sweeps)": med(lambda: [B.RefrigerantCircuit(scn, H).sweep([T]) for T in Ts[:200]], 3),
        "B_automaton_sorted_sweep(200 T)": med(lambda: B.RefrigerantCircuit(scn, H).sweep(Ts)),
        "merged_knot_form_exact_Fraction(3 units x 200 T)": med(lambda: [kfs[u](T) for u in kfs for T in Ts]),
        "msp_knots+interval_float(3 units x 200 T)": med(lambda: [(sy.K["B1-02"].value(T), sy.K["B1-03"].value(T), sy.I14.value(T)) for T in Ts]),
    }
    out["build_seconds"] = {
        "B_automaton_build": med(lambda: B.RefrigerantCircuit(scn, H), 3),
        "canon_build_and_KF(3 units)": med(lambda: [timechar.KF(canon.Canon(H=H, terms=can.unit_terms.get(u, []))) for u in kfs], 3),
    }
    out["tracemalloc_peak_bytes"] = {
        "B_automaton_build+sorted_sweep": peak(lambda: B.RefrigerantCircuit(scn, H).sweep(Ts))[0],
        "merged_KF_build(3 units)": peak(lambda: [timechar.KF(canon.Canon(H=H, terms=can.unit_terms.get(u, []))) for u in kfs])[0],
    }
    # sanity: merged form vs automaton at 10 T (B1-02, B1-03 in D'; B1-04 interval form)
    r = B.RefrigerantCircuit(scn, H).sweep(Ts[::20])
    out["merged_vs_automaton_max_rel"] = {u: max(C.rel(kfs[u](T), r[T][u]) for T in Ts[::20]) for u in kfs}
    return out


def main():
    C.frozen()
    canon, timechar, population = C.canon_modules()
    B = load_b()
    res = {"runs": [one(tag, s, B, canon, timechar, population) for tag, s in C.d_scenarios(("BM-M", "EV6"))],
           "note": ("msp's 5,200-row table / 10,400 knots are UNMERGED per-device pieces. Merged per unit, the "
                    "random-access form needs O(H + #events) coefficients. The automaton's tuple is the state at one T "
                    "plus its event/threshold tables; random access needs a replay from T=0.")}
    assert C.clean() == []
    C.dump("p2_hb4.json", res)
    import json
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
