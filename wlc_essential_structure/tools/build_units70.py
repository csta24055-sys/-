"""(b)(c) Re-organisation of the independent 70 evaluation units: internal mechanism -> auxiliary -> direct emission
-> final aggregation (+ derived indicators, breakdowns, reference values), audited on the actual dependency graph.

Inputs (read-only): WLC_THEORY_RESEARCH_BASE/data/units70.csv and unit_dependencies.csv at commit 9416a1b, and
10_TRANSFORM_STUDY/11_UNIFIED_SYSTEM/UNITS_70.md at 761da13 (for the predicate inventory).
Usage: python3 -I tools/build_units70.py <foundation_checkout> <theorybase_checkout> <out_units_dir> <out_graph_dir>
"""
import collections
import csv
import json
import os
import re
import sys

STUDY = "whole-life-carbon-jcat-study"

# Hand-assigned mathematical family per unit (05_families/01 defines F1..F5, G, R). primary | components | note.
# Assigned by reading each unit's formula in UNITS_70.md / units70.csv formula_latex (independent model only).
FAMILY = {
    "SYS-01": ("G", "F2:count", "入力状態の計数（報告）"),
    "SYS-02": ("G", "F2:count;F1:select", "単位換算の可否の計数"),
    "SYS-03": ("G", "F2:count", "係数の許諾・出典の計数"),
    "SYS-04": ("G", "F2;F1", "面積の残差"),
    "A13-01": ("F2", "F1:select;F1:convert;mask", "Σ[解決][¬EPD][数量ok] q·換算·係数"),
    "A13-02": ("F2", "F1:mask", "複合係数＝構成比の加重和（係数の準備）"),
    "A13-03": ("F2", "F1:convert;mask", "EPD の積和"),
    "A13-04": ("F2", "F1:ratio r/(1-r);mask", "上乗せ＝(A13-01+A13-03)·r/(1−r)"),
    "A13-05": ("F1", "F1:ratio 1/(1-w);mask", "発注量・据付量（端材）"),
    "A4-01": ("F2", "F1:convert;mask", "質量×距離×係数"),
    "A4-02": ("F2", "F1:convert;mask", "製品別輸送"),
    "A5-01": ("F2", "F1:convert;mask", "仮設電気（1 項の積和）"),
    "A5-02": ("F2", "mask", "施工燃料"),
    "A5-03": ("F2", "mask", "工事廃棄物"),
    "A5-04": ("F5", "", "A5-01+A5-02+A5-03（演算は集計）"),
    "B1-01": ("F2", "mask", "充填量×GWP（在庫の参考値）"),
    "B1-02": ("F4", "F3:cell;F2", "u_{k+1}=(I+N)u_k の残存量 × 漏洩率 × GWP × 年重み"),
    "B1-03": ("F3", "F3:atom;F3:gcell;F4", "交換時の漏洩（事象。量は状態 u）"),
    "B1-04": ("F3", "F3:window;F4", "期末の未回収量（終端。状態 u と回収率）"),
    "B2-01": ("F3", "F1:share ρ;F3:cell", "ρ·EL(T)（運用電力の按分）"),
    "B3-01": ("F3", "F3:density;F3:gcell;F2", "年間修繕率×初期排出、事象の年の補正"),
    "B3-02": ("F3", "F3:density;F2", "e0·r·T（推計）"),
    "B4-01": ("F3", "F3:generator", "事象の時刻 {n c : n c < T'}"),
    "B4-02": ("F3", "F3:atom;F2", "Σ 1 回あたり排出 × [τ<T']"),
    "B4-03": ("F3", "F3:count", "n(T)=Σ_n [n c<T']"),
    "B5-01": ("F3", "F3:atom;F5;F1:share φ", "改修周期ごとに φ×初期排出"),
    "B6-01": ("F1", "F1:elementwise per year;mask", "e_k = n_k·換算·γ_k"),
    "B6-02": ("F2", "mask", "燃料の年次積和"),
    "B6-03": ("F3", "F3:cell", "Σ_k (e_k+f_k) w_k(T)"),
    "B6-04": ("F1", "F1:clamp max(0,·);mask", "正味の買電 d_k"),
    "B7-01": ("F2", "mask", "上水（年次）"),
    "B7-02": ("F2", "mask", "下水（年次）"),
    "B7-03": ("F2", "mask", "一般廃棄物（年次）"),
    "B7-04": ("F3", "F3:cell", "Σ_k (上水+下水+廃棄物)_k w_k(T)"),
    "C-05": ("G", "F2", "質量収支の検査"),
    "C1-01": ("F2", "mask", "解体作業"),
    "C2-01": ("F2", "F1:convert;mask", "搬出"),
    "C3-01": ("F2", "mask", "処理（最終処分以外）"),
    "C4-01": ("F2", "mask", "最終処分"),
    "QA-01": ("G", "F5", "相互排他・足し直し"),
    "QA-02": ("G", "F3:generator", "時刻が評価期間の外"),
    "QA-03": ("G", "F2:count", "使われた係数の出典"),
    "QA-04": ("G", "F1", "面積の検算"),
    "STO-01": ("F1", "", "木材量×密度×炭素率×44/12（参考値）"),
    "STO-02": ("F2", "mask", "炭酸化（参考値）"),
    "SUM-01": ("F5", "", "A 段階の和"),
    "SUM-02": ("F5", "", "B6・B7 以外の和"),
    "SUM-03": ("F5", "", "全段階の和 = C(T)"),
    "SUM-04": ("R", "F1:ratio", "C/A"),
    "SUM-05": ("R", "F1:ratio", "C/(A T)（双曲）"),
    "SUM-06": ("R", "F1:scale", "0.001 C"),
    "SUM-07": ("R", "F1:ratio", "S_s/C（比）"),
    "SUM-08": ("R", "G;F1:ratio", "比較可能性の判定と差・削減率"),
    "X-01": ("F2", "mask", "設備機器の製造"),
    "X-02": ("F5", "G:complete", "段階×単位の 0/±1 行列"),
    "X-03": ("F2", "F1:mask", "複合品の構成材への展開（内訳）"),
    "X-04": ("F2", "F5", "ガス別の内訳"),
    "X-05": ("F2", "F5", "CO2 版の並行算定（内訳）"),
    "X-06": ("F1", "F1:piecewise in k;mask", "電力係数の年次系列"),
    "X-07": ("F3", "F5", "年ごとの配分と累積（内訳）"),
    "X-08": ("F3", "F3:count;F2", "更新周期別の集計（内訳）"),
    "X-09": ("F2", "mask", "廃棄物の品目×経路の内訳"),
    "X-10": ("F2", "F3:count", "資源量・廃棄物量 (1+n(T))"),
    "X-11": ("F3", "F3:cell;F1", "床面積原単位 × G(T)（参考値）"),
    "X-12": ("F1", "F2", "積載率補正（参考値）"),
    "X-13": ("F1", "", "端材再使用の正味発注量（参考値）"),
    "X-14": ("F2", "mask", "設備機器の廃棄時"),
    "X-15": ("F1", "F1:select priority;mask", "係数の種別の排他的な選択"),
    "X-16": ("F2", "F1:ratio index", "物価補正"),
    "X-17": ("F2", "F1:ratio", "主要数量による簡易算定（参考値）"),
}

# predicates appearing in the unit formulas (UNITS_70.md, 統合系での式). regex on the Japanese text -> guard type
GUARDS = [
    ("非負", r"(≥ 0|≥0)"),
    ("率の範囲", r"(0 ≤ [a-zρφw]|0 < r < 1|0 ≤ ρ ≤ 1|0 ≤ φ ≤ 1|0 ≤ w < 1)"),
    ("係数が使える", r"係数が使える|係数あり|係数なし"),
    ("使用許諾", r"使用許諾|許諾"),
    ("単位・換算", r"換算可|単位が|単位と換算|単位が読める|換算可"),
    ("面積>0", r"A > 0|面積 > 0"),
    ("事象の規則 τ<T'", r"τ < T'|< T'"),
    ("指数>0・積載率>0", r"指数 > 0|積載率 > 0"),
]


def load(fnd, thb):
    U = list(csv.DictReader(open(os.path.join(thb, STUDY, "WLC_THEORY_RESEARCH_BASE/data/units70.csv"), encoding="utf-8")))
    D = list(csv.DictReader(open(os.path.join(thb, STUDY, "WLC_THEORY_RESEARCH_BASE/data/unit_dependencies.csv"), encoding="utf-8")))
    md = open(os.path.join(fnd, STUDY, "10_TRANSFORM_STUDY/11_UNIFIED_SYSTEM/UNITS_70.md"), encoding="utf-8").read()
    formulas = {}
    for line in md.splitlines():
        m = re.match(r"\| ([A-Z0-9\-]+) \| (.*?) \| (.*) \| (D-\d+) \|", line)
        if m:
            formulas[m.group(1)] = m.group(3)
    return U, D, formulas


def main(fnd, thb, out_u, out_g):
    U, D, formulas = load(fnd, thb)
    ids = [u["id"] for u in U]
    assert len(ids) == 70 and set(ids) == set(FAMILY), set(ids) ^ set(FAMILY)
    role = {u["id"]: u["role"] for u in U}
    role2 = {u["id"]: u["role_secondary"] for u in U}
    stage = {u["id"]: u["stage"] for u in U}
    comp = {u["id"]: u["composition"] for u in U}
    direct = {u for u in ids if comp[u]}
    E = [(d["from"], d["to"]) for d in D if d["kind"] == "formula"]
    assert all(a in FAMILY and b in FAMILY for a, b in E)
    succ, pred = collections.defaultdict(set), collections.defaultdict(set)
    for a, b in E:
        succ[a].add(b)
        pred[b].add(a)

    def reach(start, nxt):
        seen, st = set(), [start]
        while st:
            x = st.pop()
            for y in nxt[x]:
                if y not in seen:
                    seen.add(y)
                    st.append(y)
        return seen

    down = {u: reach(u, succ) for u in ids}
    up = {u: reach(u, pred) for u in ids}
    internal_hyp = {"SYS-01", "SYS-02", "SYS-03", "SYS-04", "QA-01", "QA-02", "QA-03", "QA-04", "C-05"}
    rows, notes = [], []
    for u in ids:
        feeds_direct = bool(down[u] & direct)
        fed_by_direct = bool(up[u] & direct)
        fam, comps, note = FAMILY[u]
        if u in internal_hyp:
            layer = "L0 内部処理（共通の検査機構）"
        elif u in direct:
            layer = "L2 直接排出"
        elif feeds_direct:
            layer = "L1 補助算定"
        elif role[u] == "AGGREGATE" and fam == "F5":
            layer = "L3 最終集計"
        elif fam == "R":
            layer = "L4 派生指標"
        elif role[u] == "BREAKDOWN":
            layer = "L5 内訳（報告。合計に加えない）"
        else:
            layer = "L6 参考値（合計に入らない別推計）"
        # values of decision units must not flow into any value-producing unit
        flows_into_values = sorted(v for v in down[u] if v not in internal_hyp) if u in internal_hyp else []
        guards = [g for g, rx in GUARDS if re.search(rx, formulas.get(u, ""))]
        rows.append(dict(
            id=u, name=next(x["name"] for x in U if x["id"] == u), old_stage=stage[u], old_role=role[u],
            old_role_secondary=role2[u], composition=comp[u], new_layer=layer, family_primary=fam, family_components=comps,
            note=note, feeds_direct=feeds_direct, fed_by_direct=fed_by_direct,
            direct_downstream=";".join(sorted(down[u] & direct)), direct_upstream=";".join(sorted(up[u] & direct)),
            all_upstream=";".join(sorted(up[u])), decision_value_flow=";".join(flows_into_values),
            guards_in_formula=";".join(guards), n_guard_types=len(guards),
            time_shape_17=next(x["time_classification_17"] for x in U if x["id"] == u)))
    # ---- audits ----------------------------------------------------------------------------------------------------
    C = collections.Counter
    layer_count = C(r["new_layer"] for r in rows)
    aux_not_upstream = [r["id"] for r in rows if r["old_role"] == "AUXILIARY" and not r["feeds_direct"]]
    ref_upstream = [r["id"] for r in rows if r["old_role"] == "REFERENCE" and r["feeds_direct"]]
    d2d = sorted((a, b) for a, b in E if a in direct and b in direct)
    dec_flow = {r["id"]: r["decision_value_flow"] for r in rows if r["decision_value_flow"]}
    # sources (no formula predecessors) among direct units -> read only inputs + auxiliaries
    direct_from_inputs_only = sorted(u for u in direct if not up[u])
    agg_ops_in_direct = [u for u in direct if FAMILY[u][0] == "F5"]
    guard_hist = C(g for r in rows for g in r["guards_in_formula"].split(";") if g)
    units_with_guards = sum(1 for r in rows if r["n_guard_types"] and r["new_layer"] != "L0 内部処理（共通の検査機構）")
    audit = dict(
        n_units=len(rows), layer_count=dict(layer_count),
        hypothesis_9_21_40=dict(internal=sum(1 for r in rows if r["new_layer"].startswith("L0")), direct=len(direct),
                                rest=70 - len(direct) - sum(1 for r in rows if r["new_layer"].startswith("L0"))),
        rest_40_breakdown={k: v for k, v in layer_count.items() if not k.startswith(("L0", "L2"))},
        old_role_count=dict(C(r["old_role"] for r in rows)),
        family_primary_count=dict(C(r["family_primary"] for r in rows)),
        family_primary_by_layer={l: dict(C(r["family_primary"] for r in rows if r["new_layer"] == l)) for l in layer_count},
        auxiliary_not_upstream_of_direct=aux_not_upstream, reference_upstream_of_direct=ref_upstream,
        direct_to_direct_edges=d2d, decision_units_whose_value_flows_into_values=dec_flow,
        direct_units_reading_inputs_only=direct_from_inputs_only,
        direct_units_whose_operation_is_aggregation=agg_ops_in_direct,
        formula_edges=len(E), composition_rows=sum(len(comp[u].split(";")) for u in direct),
        guard_type_occurrence_outside_L0=dict(guard_hist), value_units_carrying_own_guards=units_with_guards,
    )
    os.makedirs(out_u, exist_ok=True)
    os.makedirs(out_g, exist_ok=True)
    cols = list(rows[0].keys())
    with open(os.path.join(out_u, "units70_reclassification.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    with open(os.path.join(out_g, "unit_graph_edges.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["from", "to", "kind", "from_layer", "to_layer"])
        L = {r["id"]: r["new_layer"] for r in rows}
        for a, b in sorted(E):
            w.writerow([a, b, "formula", L[a], L[b]])
        for u in sorted(direct):
            for part in comp[u].split(";"):
                s, sg = part.split(":")
                w.writerow([u, "STAGE:" + s, "composition sign=" + sg, L[u], "段階"])
    # Mermaid-free DOT graph of the unit layers (rendered by any graphviz; kept as text)
    with open(os.path.join(out_g, "unit_graph.dot"), "w", encoding="utf-8") as f:
        f.write("digraph units70 {\n rankdir=LR; node [shape=box,fontsize=10];\n")
        for l in sorted(layer_count):
            f.write(' subgraph "cluster_%s" { label="%s";\n' % (l[:2], l))
            for r in rows:
                if r["new_layer"] == l:
                    f.write('  "%s";\n' % r["id"])
            f.write(" }\n")
        for a, b in sorted(E):
            f.write(' "%s" -> "%s";\n' % (a, b))
        f.write("}\n")
    with open(os.path.join(out_u, "units70_audit.json"), "w", encoding="utf-8") as f:
        json.dump(audit, f, ensure_ascii=False, indent=1)
    print(json.dumps(audit, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:5])
