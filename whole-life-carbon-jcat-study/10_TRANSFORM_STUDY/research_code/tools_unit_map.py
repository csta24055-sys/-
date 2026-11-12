"""Trace of every evaluation unit through the unified system: outputs <- operations <- inputs.

For each of the 70 units the read-out records which result columns it uses (``System.read_from``).
From these columns the tool walks backwards through the three programs (AGG, TIME, P1), the
re-tabulation (tables U and TT) and the hand-over to the knot spectra (``specs.system.EMIT``), until it
reaches columns that no step computes: inputs of the building, lexical tokens of an input text,
or columns of the index tables.

Run from ``research_code``:  PYTHONDONTWRITEBYTECODE=1 python3 -B tools_unit_map.py
Writes ``11_UNIFIED_SYSTEM/UNIT_MAP.md`` and ``11_UNIFIED_SYSTEM/results/unit_map.json``.
The trace is taken on the benchmark scenario S (fictional data); it describes the specification, not values.
"""
import collections
import json
import os
import sys

sys.dont_write_bytecode = True

from specs import pre_a, system as S_
from tstudy import baseline, scenarios, tables, unified

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_MD = os.path.normpath(os.path.join(HERE, "..", "11_UNIFIED_SYSTEM", "UNIT_MAP.md"))
OUT_JSON = os.path.normpath(os.path.join(HERE, "..", "11_UNIFIED_SYSTEM", "results", "unit_map.json"))
INDEX_COLS = ("_row", "_parent", "_pos")


def operands_of(st):
    """(kind, operand) pairs of a step; kind "own" = addressed in the table of the step."""
    out = []
    def op(o):
        if isinstance(o, str):
            out.append(("own", o))
        elif isinstance(o, dict) and "via" in o:
            out.append(("own", o["via"])); out.append(("via", (o["via"], o["col"])))
        elif isinstance(o, dict) and "of" in o:
            out.append(("of", (o["of"], o["col"])))
    if st["op"] == "match":
        for k in st["keys"]:
            op(k)
        for k in st["on"]:
            out.append(("into", (st["into"], k)))
        return out
    for term in st["terms"]:
        for f in term:
            if isinstance(f, dict) and "pred" in f:
                op(f["a"])
                if "b" in f:
                    op(f["b"])
            elif isinstance(f, dict) and "fn" in f:
                op(f["a"])
            else:
                op(f)
    g = st.get("group")
    if isinstance(g, dict):
        out.append(("own", g["by"]))
    return out


def main():
    baseline.assert_frozen(); baseline.load()
    from synth import population
    scn = scenarios.benchmark()[0]
    raw = set(tables.from_scenario(scn).rows)                       # tables of the flattened inputs
    sysm = unified.System(scn, baselines=population.BASELINES)
    sysm.at(60.0)
    eng = sysm.eng
    produced = {}                                                   # (table, column) -> (program, step)
    for pname, prog in (("P1", unified.P1), ("TIME", unified.P_TIME), ("AGG", unified.P_AGG)):
        for st in prog.steps:
            g = st.get("group", "none") if st["op"] == "sp" else "none"
            if g == "total":
                table = "S"
            elif isinstance(g, dict):
                table = eng.col(st["table"], g["by"]).target
            else:
                table = st["table"]
            produced[(table, st["out"])] = (pname, st)
    emit = collections.defaultdict(list)
    for e in S_.EMIT:
        emit[e["spectrum"]].append(e)
    read_from = dict(sysm.read_from)
    for u in pre_a.UNITS:                                           # the 18 units with data-only read-outs
        cols = set()
        def walk(ro, uid=u["id"]):
            if ro["read"] == "record":
                for sub in ro["fields"].values():
                    walk(sub)
            elif ro["read"] == "enum":
                for _, name in ro["cases"]:
                    cols.add((ro["table"], name))
            elif ro["read"] != "const":
                t = ro.get("table", "S")
                for k in ("col", "where", "key"):
                    if k in ro:
                        cols.add((t, ro[k]))
        outs = (S_.A5_01 if u["id"] == "A5-01" else u)["outputs"]
        for ro in outs.values():
            walk(ro)
        read_from[u["id"]] = sorted(cols)
    for uid in S_.VALUE_AT_T:                                      # the value of these units is the re-tabulated scalar V.<unit>
        read_from[uid] = sorted(set(read_from[uid]) | {("TT", "V." + uid)})
    read_from["B4-02"] = sorted(set(read_from["B4-02"]) | {("TT", "K.N.b42")})
    result = collections.OrderedDict()
    for uid in sorted(read_from):
        seen, queue = set(), list(read_from[uid])
        steps, spectra, leaves = collections.Counter(), set(), set()
        while queue:
            key = queue.pop()
            if key in seen:
                continue
            seen.add(key)
            table, name = key
            if name in INDEX_COLS:
                continue
            if table == "TT" and name.startswith("K."):
                spectra.add(name[2:])
                for e in emit[name[2:]]:
                    queue += [(e["table"], e[k]) for k in ("amp", "k", "tau") if k in e]
                continue
            if table == "TT" and name.startswith("V."):
                uid2 = name[2:]
                if uid2 in S_.CONST_VALUE:
                    queue.append(("S", S_.CONST_VALUE[uid2]))
                else:
                    where, col = S_.VALUE_AT_T[uid2]
                    if where == "K":
                        queue.append(("TT", "K." + col))
                    elif where == "I":
                        spectra.add("B1-04 (interval form)")
                        queue += [(unified.CAL, "b1.iA"), (unified.CAL, "b1.iB"), (unified.DY, "b1.e4a"), (unified.DY, "b1.e4g"),
                                  (unified.DY, "b1.tau1"), (unified.DY, "b1.p")]
                    else:
                        queue.append((where, col))
                continue
            if table == "U":
                if name == "value":
                    queue += [("TT", "V." + u2) for u2 in list(S_.CONST_VALUE) + list(S_.VALUE_AT_T)]
                elif name == "bad":
                    queue += [("S", "bad." + u2) for u2 in S_.BAD] + [("TT", "K.N.b42")]
                continue
            if key in produced:
                pname, st = produced[key]
                steps[pname + ":" + st["op"]] += 1
                for kind, o in operands_of(st):
                    if kind == "own":
                        queue.append((st["table"], o))
                    elif kind == "via":
                        ref, col = o
                        target = eng.col(st["table"], ref).target
                        if target is not None:
                            queue.append((target, col))
                    else:
                        queue.append(o)
                continue
            leaves.add(key)
        inputs, tokens, index_cols = collections.defaultdict(set), collections.defaultdict(set), collections.defaultdict(set)
        for table, name in leaves:
            if table == "TT":
                index_cols["TT"].add(name)
            elif table in raw and "~" in name:
                tokens[table].add(name)
            elif table in raw:
                inputs[table].add(name)
            else:
                index_cols[table].add(name)
        result[uid] = {"read_from": ["%s.%s" % k for k in read_from[uid]], "steps": dict(sorted(steps.items())),
                       "spectra": sorted(spectra), "inputs": {t: sorted(c) for t, c in sorted(inputs.items())},
                       "tokens": {t: sorted(c) for t, c in sorted(tokens.items())},
                       "index_tables": {t: sorted(c) for t, c in sorted(index_cols.items())}}
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w") as f:
        json.dump(result, f, indent=1)
    lines = ["# Trace of the 70 evaluation units through the unified system", "",
             "Generated by `research_code/tools_unit_map.py` from the specification itself (not written by hand).",
             "For every unit: the result columns its read-out uses, how many sum-product steps of each program lie",
             "behind them (P1 = masked sum-product 1; TIME and AGG = masked sum-product 2 at the study period T),",
             "which knot spectra are evaluated, and which input fields are reached. Full detail (every input column,",
             "token and index table) is in `results/unit_map.json`.", "",
             "Reading: `sp` = sum-product steps, `m` = keyed look-ups; T in the column *time* means the unit depends on the study period.", "",
             "| unit | read-out columns | P1 sp / m | TIME sp / m | AGG sp / m | knot spectra | time | input tables (number of fields) |",
             "|---|---|---|---|---|---|---|---|"]
    n_inputs = set()
    for uid, r in result.items():
        s = r["steps"]
        depends_t = bool(r["spectra"]) or any(k.startswith(("TIME", "AGG")) for k in s) or "T" in r["index_tables"].get("TT", [])
        for t, c in r["inputs"].items():
            n_inputs.update((t, x) for x in c)
        lines.append("| %s | %d | %d / %d | %d / %d | %d / %d | %s | %s | %s |" % (
            uid, len(r["read_from"]), s.get("P1:sp", 0), s.get("P1:match", 0), s.get("TIME:sp", 0), s.get("TIME:match", 0),
            s.get("AGG:sp", 0), s.get("AGG:match", 0), ", ".join(r["spectra"]) or "-", "T" if depends_t else "-",
            "; ".join("%s (%d)" % (t, len(c)) for t, c in r["inputs"].items()) or "-"))
    lines += ["", "Units: %d. Distinct input fields reached by at least one unit: %d." % (len(result), len(n_inputs)), ""]
    with open(OUT_MD, "w") as f:
        f.write("\n".join(lines))
    print("units", len(result), "distinct input fields", len(n_inputs))
    for uid in ("A13-01", "B1-04", "B4-02", "SUM-03", "X-04", "SYS-01"):
        r = result[uid]
        print(uid, r["steps"], r["spectra"], {t: len(c) for t, c in r["inputs"].items()})


if __name__ == "__main__":
    main()
