"""05c / 05d: the classification (5 categories, 175 details) against the original equations, the engine
inputs (241) and the evaluation units of the unified system.

Usage: python3 -I node_map.py <patterns.pkl or ""> <out dir>
The pickle is private (it holds formula text) but only counts per node are written here.
"""
import collections, csv, json, os, pickle, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.normpath(os.path.join(HERE, "..", ".."))
TREE = os.path.join(STUDY, "13_INPUT_CLASSIFICATION", "JCAT_input_categories_complete.json")
BIND = os.path.join(STUDY, "13_INPUT_CLASSIFICATION", "binding_engine_model_v1.json")
UMAP = os.path.join(STUDY, "10_TRANSFORM_STUDY", "11_UNIFIED_SYSTEM", "results", "unit_map.json")
VER = os.path.join(STUDY, "14_EQUATION_DISCLOSURE", "06_全検証ケース.csv")


def table_col(path):
    """Engine-model path -> (table, column) of the flattened tables (tstudy.tables)."""
    parts = re.split(r"(\[\]|\{\})\.?", path)
    segs, cur = [], ""
    i = 0
    tokens = [p for p in parts if p != ""]
    table, col = [], ""
    buf = []
    for tok in tokens:
        if tok in ("[]", "{}"):
            table.append(".".join(buf))
            buf = []
        else:
            buf.extend(tok.split("."))
    if not table:                                   # a record of the scenario: first name is the table
        return buf[0], ".".join(buf[1:])
    name = table[0] + "".join("." + t for t in table[1:])
    return name, ".".join(buf) if buf else "value"


def main(pkl, out):
    tree = json.load(open(TREE, encoding="utf-8"))
    bind = json.load(open(BIND, encoding="utf-8"))["map"]
    umap = json.load(open(UMAP, encoding="utf-8"))
    per_node = collections.Counter()
    skel_node = collections.defaultdict(set)
    if pkl and os.path.exists(pkl):
        d = pickle.load(open(pkl, "rb"))
        for pid, q in d["pat"].items():
            for nd, k in q["nodes"].items():
                per_node[nd] += k
                skel_node[nd].add(q["sk"])
    users = collections.defaultdict(set)              # (table, col) -> units
    sys.path.insert(0, os.path.join(STUDY, "10_TRANSFORM_STUDY", "research_code"))
    sys.dont_write_bytecode = True
    from specs import system as S_
    sources = {}                                     # index table -> input columns it is built from
    for op in S_.INDEX_PLAN:
        if op["op"] == "events":
            src = [(op["parent"], op["cycle"])] if op.get("cycle") else []
            if op.get("lists"):
                src.append((op["lists"], "value"))
            sources[op["name"]] = src
        elif op["op"] in ("sorted", "distinct"):
            sources[op["name"]] = [(op["source"], op["by"])] if op["op"] == "sorted" else [tuple(x) for x in op["sources"]]
    for uid, m in umap.items():
        for part in ("inputs", "tokens"):
            for t, cols in m.get(part, {}).items():
                for c in cols:
                    users[(t, re.sub(r"(#|~[htpis])$", "", c))].add(uid)
        for t, cols in m.get("index_tables", {}).items():
            for c in cols:
                users[(t, re.sub(r"(#|~[htpis])$", "", c))].add(uid)
            for src in sources.get(t, []):
                users[src].add(uid)
            if t.startswith("CYC"):
                for src in (("materials", "refresh_cycle"), ("equipment", "service_life")):
                    users[src].add(uid)
    verified = set()
    if os.path.exists(VER):
        for r in csv.DictReader(open(VER, encoding="utf-8-sig")):
            if r["区分"] == "統一系×基準計算" and r["結果"] == "合格":
                verified.add(r["対象（評価単位・出力キー・式）"].split(".")[0])
    # 05d: engine input -> units
    rows_in, node_units = [], collections.defaultdict(set)
    node_inputs = collections.Counter()
    unmatched = 0
    for path, e in sorted(bind.items()):
        t, c = table_col(path)
        for cand in ((t + "." + c, "value"), (t + "." + c, "key")):           # a list or a map of numbers is a child table
            if (t, c) not in users and cand in users:
                t, c = cand
        if path.endswith(("[]", "{}")):
            pass
        us = sorted(users.get((t, c), set()))
        if path == "boundary.study_period":
            us = sorted(umap)                                           # replaced by the condition T of every evaluation
        if path.endswith(("[]", "{}")):
            us = sorted({u for (tt, cc), uu in users.items() if tt == t for u in uu})
        if not us:
            unmatched += 1
        node_inputs[e["node"]] += 1
        node_units[e["node"]].update(us)
        rows_in.append([path, e["id"], e["node"], e["category"], "%s:%s" % (t, c), len(us), " ".join(us),
                        "検証済み（全出力キー不一致 0）" if us and all(u in verified for u in us) else ("" if not us else "一部未検証"),
                        "" if us else "どの評価単位の読み出しにも現れない（記録・状態・識別子・使われない記述子など）"])
    with open(os.path.join(out, "05d_エンジン入力241項目から方程式への追跡表.csv"), "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["エンジン入力のパス", "項目ID", "分類ID", "大分類", "平坦化後の表:列", "使う評価単位の数", "使う評価単位", "検証", "備考"])
        w.writerows(rows_in)
    # 05c: classification nodes
    rows = []
    stat = collections.Counter()
    for cat in tree["categories"]:
        for br in cat["branches"]:
            for nd in [dict(id=br["id"], label=br["label"], lvl="小分類")] + [dict(id=x["id"], label=x["label"], lvl="詳細分類") for x in br["details"]]:
                nid = nd["id"]
                orig = per_node.get(nid, 0)
                ni = node_inputs.get(nid, 0)
                us = sorted(node_units.get(nid, set()))
                implemented = bool(us)
                ver = implemented and all(u in verified for u in us)
                if nd["lvl"] == "詳細分類":
                    stat["details"] += 1
                    stat["details_orig"] += orig > 0
                    stat["details_engine"] += implemented
                    stat["details_neither"] += (orig == 0 and not implemented)
                rows.append([nid, nd["lvl"], cat["label"], br["label"], nd["label"] if nd["lvl"] == "詳細分類" else "",
                             orig, len(skel_node.get(nid, ())), "あり" if orig else "なし（この分類に割り当てた数式セルはない）",
                             ni, " ".join(us), "あり" if implemented else "なし",
                             "変換済み（統一系の全 70 単位）" if implemented else "対象外", "検証済み" if ver else ("" if not implemented else "一部未検証"),
                             "原版：0 件変換。原版の数式セルの分類はシート単位の割り当て" ])
    with open(os.path.join(out, "05c_分類ごとの方程式対応表.csv"), "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["分類ID", "階層", "大分類", "小分類", "詳細分類", "原版の数式セル数", "原版の独立方程式数", "原版に存在する方程式",
                    "エンジン入力の数", "使う評価単位（独自エンジンに実装した方程式）", "独自エンジンに実装", "統一構造へ変換", "検証", "備考"])
        w.writerows(rows)
    res = dict(stat, engine_inputs=len(bind), engine_inputs_without_unit=unmatched)
    json.dump(res, open(os.path.join(out, "node_map_counts.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(res)


if __name__ == "__main__":
    main(*sys.argv[1:3])
