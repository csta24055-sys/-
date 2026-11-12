"""Does the comparison of ``checks.check_unified`` detect a wrong specification? And does QA-01 fire?

  1 negative controls   the specification is damaged on purpose (one step each); the comparison must report
                        mismatches in the unit the step belongs to
  2 fault injection     QA-01 (a), (b), (c) cannot be violated by any input (see DERIVATIONS section 9); an
                        upstream result is falsified on BOTH sides and the two QA-01 outputs must agree and fail
  3 structure           the specifications are data only, the engine file is the committed one, the unified
                        module does not read the reference, the vocabulary in use

Run from ``research_code``:  PYTHONDONTWRITEBYTECODE=1 python3 -B -m checks.check_unified_controls
Writes ``11_UNIFIED_SYSTEM/results/controls.json``. Evidence level N (implementer only), fictional data.
"""
import collections
import copy
import inspect
import json
import os
import subprocess
import sys

sys.dont_write_bytecode = True

from checks import check_unified, sets_unified
from checks.check_msp_pre_a import public
from specs import system as S_
from specs.lib import EQ, GE1, LE, NOT, OF, PR, VIA, sp
from tstudy import baseline, msp, scenarios, unified

OUT = os.path.join(check_unified.OUT_DIR, "controls.json")


def find(spec, out):
    for u in spec["units"]:
        for st in u["steps"]:
            if st.get("out") == out:
                return st
    raise KeyError(out)


def template_step(spec, template, out):
    for st in spec["templates"][template]:
        if st.get("out") == out:
            return st
    raise KeyError(out)


def control(title, expect, cases, baselines, p1=None, time=None, agg=None, b14="interval"):
    """Run the comparison with damaged programs; ``expect`` = units that must show mismatches."""
    good = (unified.P1, unified.P_TIME, unified.P_AGG)
    try:
        for attr, mut, base in (("P1", p1, S_.SPEC1), ("P_TIME", time, S_.SPEC_TIME), ("P_AGG", agg, S_.SPEC_AGG)):
            if mut is not None:
                spec = copy.deepcopy(base)
                mut(spec)
                setattr(unified, attr, msp.Program(spec))
        res = check_unified.run_set("control", cases, baselines, check_domain=False, verbose=False,
                                    system_factory=lambda scn: unified.System(scn, baselines=baselines, b14=b14))
    finally:
        unified.P1, unified.P_TIME, unified.P_AGG = good
    hit = res["units_with_mismatch"]
    ok = all(u in hit for u in expect)
    print("%s %-74s expected %s | units with mismatches: %s%s" % ("DETECTED" if ok else "MISSED  ", title, ",".join(expect), ",".join(hit[:9]),
                                                                "..." if len(hit) > 9 else ""), flush=True)
    return {"control": title, "expected_units": list(expect), "detected": ok, "units_with_mismatch": hit, "n_mismatch": res["n_mismatch"],
            "n_pairs": res["n_pairs"], "n_failed": res["n_failed"]}


def negative_controls(baselines):
    generate, model, population = sets_unified._gen()
    pop = list(population.verification_population(8, sets_unified.NEW_POPULATION_SEED, "S"))
    def sc(tag, periods):
        hits = [c for c in sets_unified.new_special(pop) if c and c[0].startswith(tag)][:2]
        return [(n, s, periods) for n, s in hits]
    plain = [(s.meta.scenario_id, s, [s.boundary.study_period, 44.5]) for s in pop[:3]]
    edge = dict(scenarios.edge_set())
    out = []
    # ---- units added on 2026-11-13
    def c1(spec): template_step(spec, "STATE", "@s.DERIVED")["terms"] = [[EQ("$app", 1), PR("$v"), EQ("@d.DERIVED", 1), EQ("$v", 0)]]
    out.append(control("SYS-01: a derived value counted only when it is zero", ["SYS-01"], sc("states: overrides", [60.0]), baselines, p1=c1))
    def c2(spec): find(spec, "sys2.ok")["terms"] = [[EQ("sys2.nbad", 0)]]
    out.append(control("SYS-02: a wrong stage of a factor does not fail the check", ["SYS-02"], sc("stages:", [60.0]), baselines, p1=c2))
    def c2b(spec): find(spec, "s2.sm")["terms"] = [t for t in find(spec, "s2.sm")["terms"] if t != ["s2.sm.m.gen"]]
    out.append(control("SYS-02: stage mismatches of the generic material factors not listed", ["SYS-02"], sc("units:", [60.0]), baselines, p1=c2b))
    def c3(spec): find(spec, "f.okq")["terms"] = [[EQ("licence_status", "PERMITTED_PUBLIC")]]
    out.append(control("SYS-03 / QA-03: an empty source accepted", ["SYS-03", "QA-03"], sc("references:", [60.0]), baselines, p1=c3))
    def c4(spec):
        for name in ("t.u.inst", "t.u.dlv", "t.u.ins"):
            st = find(spec, name); st["terms"] = [st["terms"][0][:1]]
    out.append(control("QA-03: lines of a renewal counted before any renewal", ["QA-03"], [(n, s, [2.0]) for n, s, _ in plain], baselines, time=c4))
    def c5(spec): find(spec, "L.B5")["terms"] = find(spec, "L.B5")["terms"][:3]
    out.append(control("X-04 / X-05: rebuild lines of the end-of-life stages dropped", ["X-04", "X-05"], sc("rebuild 20 years", [60.0]), baselines, time=c5))
    def c6(spec): find(spec, "x04.co.B4")["terms"] = [["L.B4", "value"]]
    out.append(control("X-05: CO2e value instead of the CO2 amount in stage B4", ["X-05"], plain, baselines, agg=c6))
    def c7(spec):
        st = find(spec, "x07.s"); st["terms"] = st["terms"][:-5]
    out.append(control("X-07: end-of-life stages and end residual not placed in the last year", ["X-07"], plain, baselines, agg=c7))
    def c8(spec): find(spec, "t.x08_on")["terms"] = [[GE1("t.cnt_c")]]
    out.append(control("X-08: cycle values without a contributing row listed", ["X-08"], sc("lines: zero quantities", [60.0, 50.0]), baselines, time=c8))
    def c9(spec): find(spec, "x09.m")["terms"] = [[find(spec, "x09.m")["terms"][0][0]] + find(spec, "x09.m")["terms"][0][2:]]
    out.append(control("X-09: negative route fractions summed", ["X-09"], sc("routes:", [60.0]), baselines, p1=c9))
    def c10(spec): find(spec, "t.in_m")["terms"] = [[LE("tau", OF("T", "TT"))]]
    out.append(control("B4-03: a renewal exactly at the end of the period counted", ["B4-03"], [("edge exact_multiple_lives", edge["exact_multiple_lives"], [60.0])],
                       baselines, time=c10))
    def c11(spec): find(spec, "t.b3_y")["terms"] = [["t.w", OF("b3.A_m", "S")], ["t.w", OF("b3.A_e", "S")]]
    out.append(control("B3-01 per year: repairs not skipped in a renewal year", ["B3-01"], plain, baselines, time=c11))
    def c13(spec): find(spec, "x04.bygas")["terms"] = [[PR("x04.g"), VIA("x04.A", "_parent")]]
    out.append(control("X-04: gas amounts replaced by 1", ["X-04"], plain, baselines, agg=c13))
    def c14(spec): find(spec, "sum5.den")["terms"] = [[EQ("sum4.ok", 1), S_.OF("gross_floor_area", "project")]]
    out.append(control("SUM-05: not divided by the study period", ["SUM-05"], plain, baselines, agg=c14))
    out.append(control("B1-04 in the jump form under 35 % leak without replacement (known limit, EXP-U1)", ["B1-04"],
                       [c for c in sets_unified.build(["rep_constructed"])["rep_constructed"] if c[0].startswith("no events, leak 35%")][:1], baselines, b14="jump"))
    # ---- controls of the run of 2026-11-12, repeated on the saved specification
    def o1(spec):
        for name in ("b1.a2", "b1.y4", "b1.e4a", "b1.e4g", "b1.a3", "b1.g3", "b1.iA", "b1.iB"):
            st = find(spec, name); st["terms"] = json.loads(json.dumps(st["terms"]).replace('"b1.u8"', '"b1.u3"'))
    notop = [(s.meta.scenario_id, s, [s.boundary.study_period, 62.5]) for s in scenarios.design_set(24) if any(not d.top_up for d in s.refrigerants)][:3]
    out.append(control("refrigerant: resolvent truncated to 3 factors", ["B1-02"], notop, baselines, p1=o1))
    def o2(spec): find(spec, "b1.p")["terms"] = [[PR("b1.ev1"), EQ("k", -1)]]
    out.append(control("refrigerant: resets ignored", ["B1-02", "B1-04"], notop, baselines, p1=o2))
    def o3(spec): find(spec, "b1.first")["terms"] = [[EQ("b1.act", 1)]]
    out.append(control("refrigerant: every event treated as the first of its year", ["B1-03"],
                       [("edge life_shorter_than_one_year", edge["life_shorter_than_one_year"], [10.0, 62.5])], baselines, p1=o3))
    def o4(spec):
        st = find(spec, "x06.g"); st["terms"][1] = [st["terms"][1][0], "x06.dl"]; del st["terms"][2]
    out.append(control("grid factor: floor of the linear decline dropped", ["X-06"], [("edge grid_floor_mid_period", edge["grid_floor_mid_period"], [60.0])], baselines, p1=o4))
    def o5(spec): find(spec, "x06.sv")["terms"] = [[find(spec, "x06.sv")["terms"][0][0], find(spec, "x06.sv")["terms"][0][2]]]
    step = [(s.meta.scenario_id, s, [s.boundary.study_period]) for s in scenarios.design_set(24) if s.operation.grid.kind == "STEPWISE"][:2]
    out.append(control("grid factor: stepwise without the upper bound of a step", ["X-06"], step, baselines, p1=o5))
    def o6(spec): find(spec, "b64.net")["terms"] = [[find(spec, "b64.net")["terms"][0][0], "b64.d"]]
    out.append(control("purchased electricity without max(0, .)", ["B6-04"], [("edge generation_exceeds_consumption", edge["generation_exceeds_consumption"], [60.0])], baselines, p1=o6))
    def o7(spec): del template_step(spec, "PROFILE", "@v")["terms"][2]
    out.append(control("annual profiles: linear trend dropped", ["B6-04"], [(s.meta.scenario_id, s, [s.boundary.study_period]) for s in scenarios.design_set(6)], baselines, p1=o7))
    dirty = [(n, s, [60.0]) for n, s in sets_unified.dirty(515101, 3)]
    def o8(spec):
        st = find(spec, "np.cnt"); st["terms"] = [t for t in st["terms"] if t not in (["c31.npart"], ["c41.npart"], ["np.a01"])]
    out.append(control("incomplete-renewal flag without three of its conditions", ["B4-02"], dirty, baselines, p1=o8))
    def o9(spec): find(spec, "c05.v1")["terms"] = [[GE1("c05.nneg")]]
    out.append(control("C-05 without the sum-of-fractions test", ["C-05"], dirty, baselines, p1=o9))
    return out


def qa01_fault_injection(baselines):
    """QA-01 on falsified upstream results: the candidate and the reference function must give the same failing output."""
    registry = baseline.load()
    fn = registry.UNITS["QA-01"].fn
    scn = scenarios.benchmark()[0]
    T = 60.0
    cur = scenarios.with_period(scn, T)
    ref = baseline.run_reference(cur)
    a, b = ref["A13-01"]["by_item"], ref["A13-03"]["by_item"]
    c, d = ref["A4-01"]["by_item"], ref["A4-02"]["by_item"]
    i_b = [i for i in range(len(a)) if a[i] != 0.0 and b[i] == 0.0][:3]
    i_c = [i for i in range(len(c)) if c[i] != 0.0 and d[i] == 0.0][2:4]
    out = []
    agg_qa1 = msp.Program({"templates": {}, "shared": [], "units": [{"id": "QA1", "steps": [dict(st) for st in unified.P_AGG.steps if st["out"].startswith("qa1.")], "outputs": {}}]})
    p1_qa1 = msp.Program({"templates": {}, "shared": [], "units": [{"id": "QA1", "steps": [dict(st) for st in unified.P1.steps if st["out"].startswith("qa1.")], "outputs": {}}]})
    def case(name, falsify_ref, falsify_sys, stage_fault=None):
        res2 = copy.deepcopy(ref)
        falsify_ref(res2)
        want = public(fn(cur, res2))
        sysm = unified.System(scn, baselines=baselines)
        falsify_sys(sysm)
        sysm.eng.run(p1_qa1)
        sysm.at(T)
        if stage_fault is not None:
            stage_fault(sysm)
            sysm.eng.run(agg_qa1)
        got = sysm._results(T, sysm.last["K"], sysm.last["val"])["QA-01"]
        ok = got == want and want["ok"] is False and len(want["violations"]) > 0
        print("%s QA-01 %-52s reference %s | candidate %s" % ("AGREE " if ok else "DIFFER", name, want["violations"][:4], got["violations"][:4]), flush=True)
        out.append({"case": name, "agree_and_fail": ok, "reference": want, "candidate": got})
    def ref_b(res2):
        for i in i_b: res2["A13-03"]["by_item"][i] = 5.0
    def sys_b(sysm):
        for i in i_b: sysm.eng.cols[("materials", "a03.by_item")].v[i] = 5.0
    case("(b) A13-01 and A13-03 both counted on three rows", ref_b, sys_b)
    def ref_c(res2):
        for i in i_c: res2["A4-02"]["by_item"][i] = 7.0
    def sys_c(sysm):
        for i in i_c: sysm.eng.cols[("materials", "a42.by_item")].v[i] = 7.0
    case("(c) A4-01 and A4-02 both counted on two rows", ref_c, sys_c)
    def ref_a(res2): res2["X-02"]["by_stage_all"]["B4"] *= 1.001; res2["X-02"]["by_stage_all"]["C2"] *= 0.99
    def stage(sysm):
        col = sysm.eng.cols[("STG", "x02.full")]
        col.v[unified.STAGES.index("B4")] *= 1.001; col.v[unified.STAGES.index("C2")] *= 0.99
    case("(a) stage values of B4 and C2 falsified", ref_a, lambda sysm: None, stage)
    def ref_abc(res2): ref_a(res2); ref_b(res2); ref_c(res2)
    def sys_bc(sysm): sys_b(sysm); sys_c(sysm)
    case("(a), (b) and (c) together", ref_abc, sys_bc, stage)
    return out


def structure():
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.normpath(os.path.join(here, ".."))
    out = {}
    for name, spec in (("SPEC1", S_.SPEC1), ("SPEC_TIME", S_.SPEC_TIME), ("SPEC_AGG", S_.SPEC_AGG)):
        json.dumps(spec)                                                    # raises when the specification is not pure data
        out[name + " is JSON-serialisable (data only)"] = True
    out["index plan, emitters and static tables are JSON-serialisable"] = bool(json.dumps([S_.INDEX_PLAN, S_.EMIT, S_.STATIC_TABLES, S_.VALUE_AT_T]))
    diff = subprocess.run(["git", "-C", root, "status", "--porcelain", "--", "tstudy/msp.py", "tstudy/tables.py", "tstudy/knots.py",
                           "tstudy/rampstep.py", "specs/pre_a.py"], capture_output=True, text=True).stdout.strip()
    out["engine, flattening, knot spectrum, kernel and the 18-unit specification are the committed files"] = diff == ""
    src = inspect.getsource(unified)
    out["tstudy/unified.py does not mention the reference calculation in code"] = not any(
        w in line for line in src.splitlines() if not line.strip().startswith(("#", '"')) and "``refcalc``" not in line
        for w in ("refcalc", "run_reference", "import baseline", "baseline."))
    usage = collections.Counter()
    steps = {}
    for name, prog in (("P1", unified.P1), ("TIME", unified.P_TIME), ("AGG", unified.P_AGG)):
        steps[name] = dict(collections.Counter(st["op"] for st in prog.steps))
        for unit, use in msp.static_usage(prog).items():
            for k, n in use.items():
                if not k.startswith(("steps_from_template", "terms", "match_key_parts", "read:")):
                    usage[k] += n
    out["steps"] = steps
    out["vocabulary_in_use"] = dict(sorted(usage.items()))
    out["vocabulary_outside_the_engine"] = sorted(k for k in usage if k.split(":")[0] not in ("factor", "fn", "group", "operand", "pred", "pred.not", "step"))
    out["functions_in_use"] = sorted(k for k in usage if k.startswith("fn:"))
    print("structure:", {k: v for k, v in out.items() if k not in ("vocabulary_in_use",)}, flush=True)
    return out


def main():
    baseline.assert_frozen()
    baseline.load()
    from synth import population
    res = {"structure": structure(), "qa01_fault_injection": qa01_fault_injection(population.BASELINES),
           "negative_controls": negative_controls(population.BASELINES)}
    res["summary"] = {"controls": len(res["negative_controls"]), "controls_detected": sum(c["detected"] for c in res["negative_controls"]),
                      "qa01_cases": len(res["qa01_fault_injection"]), "qa01_agree_and_fail": sum(c["agree_and_fail"] for c in res["qa01_fault_injection"])}
    print("SUMMARY", res["summary"])
    os.makedirs(check_unified.OUT_DIR, exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(res, f, indent=1)
    return 0 if res["summary"]["controls_detected"] == res["summary"]["controls"] and res["summary"]["qa01_agree_and_fail"] == res["summary"]["qa01_cases"] else 1


if __name__ == "__main__":
    sys.exit(main())
