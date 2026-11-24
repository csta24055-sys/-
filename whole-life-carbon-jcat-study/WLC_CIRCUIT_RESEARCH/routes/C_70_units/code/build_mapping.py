"""Generate MAPPING.csv (exactly 70 rows) from units70.json + refcalc registry + results/hc*.json.

  PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0 python3 -B code/build_mapping.py

Mapping rules (circuit construct, class a-e, state 4-tuple) are design rules of this route [H]; they are
stated in RULES below and in README.md.  Test status is read from results/*.json; anything not executed is
NOT_RUN.  State 4-tuple = (continuous states, discrete states/counters, comparator thresholds, external
table entries) in the Psi reading (axis = evaluation horizon T).  Symbols: Y = ceil(T) year cells,
F = number of event families (periodic row/period pairs or listed events) of the unit, n = rows.
"""
from __future__ import annotations

import csv
import json
import os

import common as C

# construct key -> (target_circuit_construct, class, state 4-tuple)
CONSTRUCT = {
    "const_t0": ("DC offset into summing node (pre-charged capacitor / bias); Phi: charge impulse at t=0",
                 "a", "(0,0,0,1)"),
    "const_tT": ("DC offset into summing node; Phi: NOT an integrator input - terminal read-out term A^term in Z(T)",
                 "a", "(0,0,0,1)"),
    "year_cell": ("integrator driven by table-switched piecewise-constant current B_k on cell (k,k+1] "
                  "(switched source, sample-hold of annual table)", "c", "(1,1,1,Y)"),
    "atom": ("comparator bank T>=sw(tau_j) -> charge impulses Gamma_j into accumulator (event clock per family)",
             "c", "(1,F,F,F)"),
    "density+gated_year_cell": ("integrator with constant current a, clip at H, minus switch that removes the "
                                "year's accrued repair at the first event of the cell", "c", "(1,1+F,2+F,1+Y+F)"),
    "atom+gated_year_cell": ("atom bank (first/later amplitudes) + gated year-cell integrator", "c", "(1,1+F,1+F,Y+2F)"),
    "interval": ("sample-hold of per-cell (A_K,B_K) + event comparators with reset of the device state u",
                 "c", "(1,1+F,1+F,2Y+2F)"),
}

ROLE_RULE = {
    "AUXILIARY": ("pre-stage: computes source amplitudes / annual tables / event grids (parameters of DIRECT "
                  "sources); not a source into the C node", "d", "(0,0,0,n)"),
    "AUXILIARY_clock": ("event/clock generator (counters + comparators) feeding atom units; not a source", "c",
                        "(0,F,F,F)"),
    "DECISION": ("predicate logic / report only; masks act inside each unit; NOT connected to the C node",
                 "d", "(0,0,0,0)"),
    "REFERENCE": ("separate observer branch (alternative estimate / inventory); NOT connected to the C node",
                  None, None),
    "BREAKDOWN": ("branch-current read-out of an existing quantity; NOT a source (would double count)", None, None),
}

AGG = {
    "SUM-03": ("the summing node output C(T) (14 stage nodes -> 1 total node; B6 branch needs inversion -iota_B2)",
               "b", "(0,0,0,0)"),
    "X-02": ("14 stage summing nodes with 0/+-1 matrix + completeness flag (digital)", "b", "(0,0,0,0)"),
    "SUM-01": ("partial-sum read-out (A stages)", "b", "(0,0,0,0)"),
    "SUM-02": ("partial-sum read-out (no B6/B7)", "b", "(0,0,0,0)"),
    "SUM-04": ("constant-gain read-out C/area", "b", "(0,0,0,1)"),
    "SUM-05": ("nonlinear read-out C/(area*T): analog divider by the sweep variable (TH-14)", "b", "(0,0,0,1)"),
    "SUM-06": ("constant-gain read-out C/1000 (unit change)", "b", "(0,0,0,0)"),
    "SUM-07": ("ratio read-out stage/C with definedness gate (C>0, no negative stage)", "d", "(0,0,1,0)"),
    "SUM-08": ("comparison with a second complete run of a baseline scenario (second circuit instance)", "d",
               "(0,1,0,0)"),
}

BRK = {"X-03": ("a", "(0,0,0,n)"), "X-09": ("a", "(0,0,0,n)"), "X-04": ("d", "(0,0,0,n)"),
       "X-05": ("d", "(0,0,0,n)"), "X-07": ("d", "(0,0,0,Y+1)"), "X-08": ("c", "(0,F,F,F)")}

H_C4_REPRESENTATIVES = {"A5-01": "AUXILIARY:A5-01", "B4-01": "AUXILIARY:B4-01", "SYS-01": "DECISION:SYS-01",
                        "B3-02": "REFERENCE:B3-02", "SUM-03": "AGGREGATE:SUM-03", "X-07": "BREAKDOWN:X-07"}


def _load(name):
    p = os.path.join(C.RESULTS, name)
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _ref_class(u) -> tuple[str, str]:
    tf = u["time_form"]
    if not u["time_dependent"]:
        return "a", "(0,0,0,1)"
    if "階段" in tf:
        return "c", "(1,F,F,F)"
    if "一次" in tf or "直線" in tf:
        return ("b", "(1,0,0,1)") if "原点を通る直線" in tf else ("c", "(1,1,1,Y)")
    return "d", "(0,0,0,n)"


def build() -> list[dict]:
    hc1, hc2, hc3, hc4, inv = (_load(f"{n}.json") for n in ("hc1", "hc2", "hc3", "hc4", "inventory"))
    closure = C.refcalc_closure("SUM-03")
    baseline, _ = C.oracle()
    reg = baseline.load()
    hc2_units = {r["unit"]: r for r in (hc2 or {}).get("units", [])}
    rows = []
    for u in C.units():
        uid, role = u["id"], u["role"]
        blocks = C.blocks_from_text(u["time_form"]) if role == "DIRECT" else []
        comp = ";".join(f"{c['stage']}:{'+' if int(c['sign']) > 0 else '-'}{c['beta']}" for c in u["composition"] or [])
        tests = []
        if role == "DIRECT":
            key = "+".join(blocks) if len(blocks) > 1 else blocks[0]
            construct, cls, state = CONSTRUCT[key]
            if hc1:
                tests.append(f"H-C1:{hc1['verdict']}(max_rel={hc1['max_rel_err_total_in_domain']:.1e},"
                             f"n={hc1['n_in_domain']})")
            else:
                tests.append("H-C1:NOT_RUN")
            r2 = hc2_units.get(uid)
            tests.append(f"H-C2:{'CONSISTENT' if r2 and r2['consistent_with_declared'] else 'INCONSISTENT' if r2 else 'NOT_RUN'}"
                         + (f"({'/'.join(r2['observed_features_union'])})" if r2 else ""))
            if hc3:
                tests.append("H-C3:" + ("T_varying" if any(uid in v["T_varying_direct_units"]
                                                            for v in hc3["per_scenario"].values()) else "const_in_grid"))
            tests.append("circuit_simulation:NOT_RUN(route B kernels)")
            status = "conditional" if hc1 and hc1["verdict"] == "PASS" else "unverified"
            evidence = "[F] composition/signature; [H] construct & state tuple"
        else:
            if role == "AGGREGATE":
                construct, cls, state = AGG[uid]
            elif role == "BREAKDOWN":
                construct = ROLE_RULE["BREAKDOWN"][0]
                cls, state = BRK[uid]
            elif role == "REFERENCE":
                construct = ROLE_RULE["REFERENCE"][0]
                cls, state = _ref_class(u)
            elif role == "AUXILIARY":
                k = "AUXILIARY_clock" if uid in ("B4-01", "B4-03") else "AUXILIARY"
                construct, cls, state = ROLE_RULE[k]
            else:
                construct, cls, state = ROLE_RULE[role]
            rep = H_C4_REPRESENTATIVES.get(uid)
            if rep and hc4:
                tests.append(f"H-C4:{hc4['verdict']}(executed {rep})")
            elif rep:
                tests.append("H-C4:NOT_RUN")
            if uid in ("SUM-01", "SUM-02", "SUM-03", "X-02") and hc1:
                tests.append(f"H-C1:{hc1['verdict']}(rebuilt vs this unit)")
            if not tests:
                tests.append("role_test:NOT_RUN")
            c1_ok = uid in ("SUM-01", "SUM-02", "SUM-03", "X-02") and hc1 and hc1["verdict"] == "PASS"
            status = "conditional" if (rep and hc4 and hc4["verdict"] == "PASS") or c1_ok else "unverified"
            evidence = "[F] executed not-a-source check; [H] construct" if status == "conditional" else "[H]"
        upstream = uid in closure
        tests.append(f"dep_closure:{'upstream' if upstream else 'not_upstream'}_of_SUM-03(refcalc)")
        rows.append({
            "claim_or_unit_id": uid, "name": u["name"], "role": role, "role_secondary": u.get("role_secondary") or "",
            "stage": u["stage"], "time_dependent": u["time_dependent"],
            "time_form_blocks": "+".join(blocks), "time_form_text": u["time_form"],          # full ledger text (CSV-quoted), never truncated
            "comp_rows": comp,
            "depends_on_units": ";".join(u["depends_on_units"]),
            "depends_on_refcalc": ";".join(reg.UNITS[uid].depends_on),
            "upstream_of_SUM03_refcalc": upstream,
            "target_circuit_construct": construct, "circuit_class": cls, "state_tuple": state,
            "construct_class_tuple_evidence": "[H] design rule; no per-unit circuit simulated in route C",
            "status": status, "evidence": evidence, "validation": "; ".join(tests),
            "source_path": f"whole-life-carbon-jcat-study/WLC_THEORY_RESEARCH_BASE/data/units70.json#units[id={uid}]; "
                           f"02_70評価単位の完全台帳.md §5; refcalc {u.get('reference_function') or ''}",
        })
    return rows


def main() -> int:
    rows = build()
    assert len(rows) == 70 and len({r["claim_or_unit_id"] for r in rows}) == 70
    path = os.path.join(C.ROUTE, "MAPPING.csv")
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        w.writerows(rows)
    cls = {}
    for r in rows:
        cls[r["circuit_class"]] = cls.get(r["circuit_class"], 0) + 1
    st = {}
    for r in rows:
        st[r["status"]] = st.get(r["status"], 0) + 1
    print(path, len(rows), "rows; class counts", dict(sorted(cls.items())), "status", st)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
