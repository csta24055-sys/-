"""Aggregate the results of the 8 equations: public counts (no values, no formulas) and the private detail.
Usage: agg8.py <public_json> <private_md>"""
import os, sys, json, pickle, collections, glob
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
S = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(S, "conv")); sys.path.insert(0, os.path.join(S, "jcat_tools"))
from run8 import TARGETS

KINDS = {"EQ-0023": "文字列連結（セル・定数・セル）", "EQ-0144": "文字列連結（セル・セル）", "EQ-0469": "条件が連結で作られる条件付き合計",
         "EQ-0298": "ROUND（丸めの境界）", "EQ-0450": "非整数乗（正の指数）", "EQ-0451": "非整数乗（負の指数）", "EQ-0452": "常用対数",
         "EQ-0229": "VALUE(LEFT())"}


def load(p):
    return pickle.load(open(p, "rb")) if os.path.exists(p) else None


def main(pub, priv):
    R8 = load(os.path.join(HERE, "res8.pkl")) or {}
    RC = {}
    for p in glob.glob(os.path.join(HERE, "rc8_*.pkl")):
        d = load(p)
        RC[d["book"]] = d
    DN = load(os.path.join(HERE, "down8.pkl")) or {}
    out = {}
    lines = []
    for eq, pids in TARGETS.items():
        rec = {"kind": KINDS[eq]}
        for mode in ("A", "B"):
            l1, vb, rc = collections.Counter(), collections.Counter(), collections.Counter()
            perf = collections.Counter()
            for pid in pids:
                r = R8.get((eq, pid, mode))
                if not r:
                    continue
                for k in ("n", "ok_cached", "ok_ref", "missing", "unsupported"):
                    l1[k] += r["l1"].get(k, 0)
                for k in ("n", "ok", "missing", "wrong", "ref_exc", "variants"):
                    vb[k] += r["vb"].get(k, 0) or 0
                perf["steps_max"] = max(perf["steps_max"], r["l1"].get("steps", 0))
                perf["compile_ms"] += r["l1"].get("compile_ms", 0)
                perf["run_ms_L1"] += r["l1"].get("run_ms", 0)
                perf["table_bytes_max"] = max(perf["table_bytes_max"], r["l1"].get("table_bytes", 0))
                perf["engine_bytes_max"] = max(perf["engine_bytes_max"], r["l1"].get("engine_bytes", 0))
                perf["rows_max"] = max(perf["rows_max"], r["l1"].get("rows_max", 0))
                perf["instances"] += r["l1"].get("n", 0)
                perf["vb_run_ms"] += r["vb"].get("run_ms", 0)
                for book, d in RC.items():
                    st = d["stats"].get((eq, pid))
                    if st:
                        c = st[mode]
                        for k in ("n", "ok_lo", "ok_ref", "ref_eq_lo", "missing", "conv=ref, LO differs", "conv=LO, ref differs", "conv differs from both"):
                            rc[k] += c.get(k, 0)
                        rc["cases"] += st["cases"]; rc["cases_hit"] += st["cases_hit"]
                        perf["rc_run_ms"] += c.get("run_ms", 0)
            imp = (DN.get(eq) or {}).get("impact", {}).get(mode, {})
            rec[mode] = dict(L1=dict(l1), boundary=dict(vb), random_cases=dict(rc), performance={k: round(v, 1) for k, v in perf.items()},
                             downstream=dict(substituted=imp.get("substituted"), changed=imp.get("changed")))
        dn = DN.get(eq) or {}
        rec["consumers"] = dict(closure=(dn.get("rec") or {}).get("closure"), levels=(dn.get("rec") or {}).get("levels"))
        rec["sensitivity_ulp"] = {m: (dn.get("impact") or {}).get(m, {}).get("changed") for m in ("ulp+", "ulp-")}
        out[eq] = rec
    json.dump(out, open(pub, "w"), ensure_ascii=False, indent=1)
    # private detail: examples with values, consumer lists by equation
    with open(priv, "w", encoding="utf-8") as fh:
        fh.write("# 非公開：未解決 8 件の実パターンでの結果（原版の値・例を含む）\n\n")
        for eq, pids in TARGETS.items():
            fh.write("## %s %s\n\n" % (eq, KINDS[eq]))
            for pid in pids:
                for mode in ("A", "B"):
                    r = R8.get((eq, pid, mode))
                    if not r:
                        continue
                    fh.write("- %s 方式%s: L1 %s\n  - L1 例: %s\n  - 境界条件 %s\n  - 境界条件の例: %s\n  - 使った構成: %s\n" % (
                        pid, mode, r["l1"], r["l1_examples"][:4], {k: r["vb"][k] for k in ("n", "ok", "missing", "wrong", "ref_exc")},
                        r["vb"]["examples"][:4], dict(r["notes"])))
                for book, d in RC.items():
                    for mode in ("A", "B"):
                        ex = d["examples"].get((eq, mode))
                        if ex:
                            fh.write("  - 無作為ケース %s 方式%s の例: %s\n" % (book, mode, ex[:6]))
            dn = DN.get(eq)
            if dn:
                fh.write("- 消費セル（段ごと）: %s; 方程式別: %s\n" % (dn["rec"]["levels"], dict(dn["rec"]["by_eq"])))
                for m, v in (dn.get("impact") or {}).items():
                    fh.write("- 差し替え %s: %s 例 %s\n" % (m, {k: v[k] for k in ("substituted", "changed")}, v["examples"][:4]))
            fh.write("\n")
    print(json.dumps(out, ensure_ascii=False, indent=1)[:3000])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
