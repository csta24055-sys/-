"""(a) Audit ledger of the 667 'independent equations' (skeletons) of the earlier J-CAT structure study.

RIGHTS: the source rows are the research-side STRUCTURAL METADATA already committed by the user in
  15_JCAT_CONVERSION/01_分類と変換状態_667件.csv and 14_EQUATION_DISCLOSURE/05a_原版の独立方程式から統一式への対応表.csv
  (IDs, research-assigned categories and labels, Excel function NAMES, nesting depth, cell counts, conversion status).
No formula text, coefficient, value, cell address or sheet content is read or produced here (none is available).
Permission of the right holders for abstraction / comparison / AI processing is NOT confirmed, so every row carries
rights = HOLD and the judgments are provisional structural estimates. The independent model (05_families) does not
use this ledger as an input; it is only a comparison layer.

Usage: python3 -I tools/build_ledger667.py <foundation_checkout> <out_dir>
"""
import collections
import csv
import json
import os
import re
import sys

STUDY = "whole-life-carbon-jcat-study"

# ---- base operations recognised from the Excel function NAMES (not from formula text) -----------------------------
OPS = {
    "IF": "PRED", "AND": "PRED", "OR": "PRED", "ISNUMBER": "PRED", "ISTEXT": "PRED", "ISERROR": "PRED",
    "IFERROR": "GUARD",
    "VLOOKUP": "LOOKUP", "HLOOKUP": "LOOKUP", "LOOKUP": "LOOKUP", "INDEX": "LOOKUP", "MATCH": "LOOKUP",
    "OFFSET": "LOOKUP", "ROW": "LOOKUP", "SINGLE": "LOOKUP",
    "SUM": "SUM", "SUMIF": "SUMIF", "SUMPRODUCT": "SUM", "COUNTIF": "SUMIF", "AVERAGE": "SUM", "AGGREGATE": "SUM",
    "MAX": "MINMAX", "ABS": "MINMAX", "RANK": "RANK",
    "ROUND": "ROUND", "ROUNDUP": "ROUND", "ROUNDDOWN": "ROUND",
    "MOD": "MOD", "POWER": "POWER", "LOG10": "LOG",
    "SUBSTITUTE": "TEXT", "LEFT": "TEXT", "VALUE": "TEXT",
}
KIND_OPS = {"四則演算": "ARITH", "文字列": "TEXT", "定数式": "CONST", "単純な参照（値の写し）": "COPY", "数学関数": "MATH"}

# how each base operation is carried by the five families (05_families/01): F1 rational map with exclusive masks,
# F2 masked sum-product, F3 time-measure integral, F4 state recurrence, F5 signed linear aggregation; X = outside
OP_TO_FAMILY = {
    "ARITH": "F1/F2", "PRED": "mask(F1-F5)", "GUARD": "internal:domain", "LOOKUP": "F1:select", "SUM": "F2/F5",
    "SUMIF": "F2/F5:masked", "MINMAX": "F1:mask", "RANK": "F2:count", "ROUND": "F1:lattice(floor)",
    "MOD": "F3:generator", "POWER": "F4|X:real-power", "LOG": "X:transcendental", "TEXT": "internal:key|X:text",
    "CONST": "F1", "COPY": "internal:transfer", "MATH": "?",
}

TIME_WORDS = ("回数", "年次", "周期", "更新", "交換", "修繕", "建替", "累積", "期間", "年当たり", "年・", "経年", "改修")
STATE_WORDS = ("冷媒", "フロン", "漏洩", "残存")
EMIS_WORDS = ("排出", "CO2", "GHG", "炭素")
AUXAGG_WORDS = ("廃材", "資源", "数量", "単価", "原単位", "周期の平均", "指数", "倍率", "量集計", "重量")
FINALAGG_WORDS = ("段階", "合計", "累積", "総", "部門合", "建築＋設備")
DISPLAY_WORDS = ("表示", "ラベル", "見出し", "グラフ", "文字列", "転記", "名称", "単位の", "単位表示", "単位名", "単位ラベル",
                 "単位付き", "空白", "順位", "備考", "期間ラベル", "単位換算表示", "規模区分")
SELECT_WORDS = ("キー", "判定", "選択", "番号", "コード", "位置", "フラグ", "検索列", "部門コード")


def ops_of(row05a):
    ops = set()
    for f in row05a["使用関数"].split():
        ops.add(OPS.get(f.strip(), "OTHER:" + f.strip()))
    for k, v in KIND_OPS.items():
        if k in row05a["種類"]:
            ops.add(v)
    if "四則演算" in row05a["種類"]:
        ops.add("ARITH")
    return sorted(o for o in ops if o)


def has(label, words):
    return any(w in label for w in words)


def norm_label(lbl):
    return re.sub(r"[（(].*?[)）]", "", lbl).strip()


def judge(r, ops):
    """Return (judgment, layer, family_primary, components, reason)."""
    cls, lbl, ess = r["分類"], r["小分類（研究側の呼び名）"], r["本質的な算定規則"] == "はい"
    comps = sorted({OP_TO_FAMILY.get(o, "?") for o in ops})
    if cls == "5":
        if "参照切れ" in lbl or "範囲外" in lbl:
            if ess:
                return ("未確認・権利保留", "不明", "—", comps,
                        "参照先が無効でも算定規則とされた（読み手の一方が「はい」）。式本文を見ずに未使用の枝と断定できない")
            return ("対象外", "対象外", "—", comps, "参照切れ・範囲外参照で常にエラーを返す（06_分類の手順 3）。未使用の枝として除外。元IDは保持")
        if ess:
            return ("意味を保って統合", "補助算定", "F1(定数)", comps,
                    "計算に使われる定数（算定規則=はい）。パラメータ表の記号として保持（値は権利保留のため採らない）")
        return ("内部処理", "内部処理", "F1(定数)", comps, "定数値。共通の定数・パラメータ表へ移す（算定式として数えない）")
    if cls == "4":
        if not ess:
            sub = "表示・ラベル" if has(lbl, DISPLAY_WORDS) else "転記・参照"
            return ("内部処理", "内部処理", "—", comps, "%s（表示・転記・補助）。値を変えないため独立算定式に数えない" % sub)
        if has(lbl, SELECT_WORDS) or "LOOKUP" in ops:
            return ("意味を保って統合", "補助算定", "F1:選択", comps,
                    "係数・区分の選択を実質的に決めるキー/判定。文字列のキーは組の添字に置き換え、F1 の排他マスクへ統合")
        return ("意味を保って統合", "補助算定", "F1:選択", comps, "表示系だが計算値を変える（算定規則=はい）。F1 の選択として保持")
    time = has(lbl, TIME_WORDS) or "MOD" in ops
    state = has(lbl, STATE_WORDS)
    if cls == "1":
        fam = "F2"
        extra = (["F3"] if time else []) + (["F4?"] if state else [])
        return ("本質的算定", "直接排出", "+".join([fam] + extra), comps, "排出量を活動量×係数で与える（分類1）")
    if cls == "2":
        if time:
            return ("本質的算定", "補助算定", "F3:生成", comps, "回数・年次・周期など時間の補助量（事象の生成・期間内の計上）")
        if has(lbl, ("構成比", "複合原単位", "按分", "比率")):
            return ("本質的算定", "補助算定", "F2:加重", comps, "構成比・複合原単位などの加重和（係数の準備）")
        if has(lbl, ("検索", "参照", "取得", "選択")):
            return ("本質的算定", "補助算定", "F1:選択", comps, "数量・係数の検索・選択（係数値の取得と選択ロジックは別記：comps）")
        return ("本質的算定", "補助算定", "F1", comps, "数量・係数の換算・準備（有理写像）")
    if cls == "3":
        if has(lbl, EMIS_WORDS) and not has(lbl, FINALAGG_WORDS):
            return ("本質的算定", "直接排出（項目和）", "F2", comps, "品目・部位ごとの排出の和（直接排出の算定の一部）")
        if has(lbl, AUXAGG_WORDS) and not has(lbl, EMIS_WORDS):
            return ("本質的算定", "補助算定（数量集計）", "F2", comps, "数量・係数の集計（補助量）")
        if "最大" in lbl:
            return ("本質的算定", "最終集計・報告", "F1:mask", comps, "最大値の抽出（非加法。総量と混ぜない）")
        if "平均" in lbl:
            return ("本質的算定", "補助算定", "F2:加重", comps, "平均（加重和÷件数）")
        return ("本質的算定", "最終集計", "F5" + ("+F3" if time else ""), comps, "段階・部門・総量の集計（符号付き線形集計）")
    return ("未確認・権利保留", "不明", "?", comps, "分類不明")


def main(fnd, out):
    base = os.path.join(fnd, STUDY)
    led = list(csv.DictReader(open(os.path.join(base, "15_JCAT_CONVERSION/01_分類と変換状態_667件.csv"), encoding="utf-8-sig")))
    meta = {r["独立方程式ID"]: r for r in csv.DictReader(open(os.path.join(base, "14_EQUATION_DISCLOSURE/05a_原版の独立方程式から統一式への対応表.csv"), encoding="utf-8-sig"))}
    assert len(led) == 667 and len(meta) == 667 and set(meta) == {r["独立方程式ID"] for r in led}
    rows = []
    for r in led:
        m = meta[r["独立方程式ID"]]
        ops = ops_of(m)
        j, layer, fam, comps, why = judge(r, ops)
        rows.append(dict(id=r["独立方程式ID"], cells=int(r["セル数"]), patterns=int(r["パターン数"]), old_class=r["分類"],
                         old_label=r["小分類（研究側の呼び名）"], old_essential=r["本質的な算定規則"], kind=m["種類"],
                         functions=m["使用関数"], depth=m["入れ子の深さ"], base_ops=";".join(ops), judgment=j, layer=layer,
                         family_primary=fam, components=";".join(comps), reason=why,
                         conv_improved=r["改良方式"], conv_fail=r["改良方式の失敗の種類"],
                         dependency_trace="未確認（式本文・参照先が非公開かつ権利保留のため逆向き追跡は未実施）",
                         rights="HOLD（構造メタデータのみ。権利者の許諾未確認）"))
    # ---- merge of isomorphic candidates: same class, same normalised label, same base-operation set ------------------
    groups = collections.defaultdict(list)
    for x in rows:
        if x["judgment"] == "本質的算定":
            groups[(x["old_class"], norm_label(x["old_label"]), x["base_ops"])].append(x)
    n_groups = 0
    for key, g in groups.items():
        g.sort(key=lambda x: x["id"])
        n_groups += 1
        for x in g[1:]:
            x["judgment"] = "意味を保って統合"
            x["reason"] = "同型候補（分類・呼び名・基本演算の集合が %s と一致）。独立モデルでは同じ族の式の添字集合に吸収。%s" % (g[0]["id"], x["reason"])
            x["merged_into"] = g[0]["id"]
        g[0]["merged_into"] = ""
    for x in rows:
        x.setdefault("merged_into", "")
        # mathematical exceptions that must keep their meaning (16 章: real power, log, text producing numbers)
        flags = []
        if "POWER" in x["base_ops"]:
            flags.append("べき乗（整数乗なら F4、実数乗は有理族で厳密に表せない：16章）")
        if "LOG" in x["base_ops"]:
            flags.append("常用対数（有理族で厳密に表せない：16章）")
        if "ROUND" in x["base_ops"] and x["judgment"] != "内部処理":
            flags.append("丸めが値を決める（区分定数として保持。表示用に落とさない）")
        if "MOD" in x["base_ops"]:
            flags.append("MOD（年次・周期の判定：事象の生成として保持）")
        if "TEXT" in x["base_ops"] and x["judgment"] != "内部処理":
            flags.append("文字列演算が数値の選択に効く（組の添字へ置換が必要）")
        x["must_keep_meaning"] = "；".join(flags)
    os.makedirs(out, exist_ok=True)
    cols = ["id", "judgment", "layer", "family_primary", "components", "merged_into", "must_keep_meaning", "reason",
            "old_class", "old_label", "old_essential", "kind", "functions", "depth", "base_ops", "cells", "patterns",
            "conv_improved", "conv_fail", "dependency_trace", "rights"]
    with open(os.path.join(out, "ledger667_audit.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for x in rows:
            w.writerow({c: x[c] for c in cols})
    C = collections.Counter
    summ = dict(
        n=len(rows), cells_total=sum(x["cells"] for x in rows),
        judgment=dict(C(x["judgment"] for x in rows)), layer=dict(C(x["layer"] for x in rows)),
        family_primary=dict(C(x["family_primary"] for x in rows)),
        family_primary_after_merge=dict(C(x["family_primary"] for x in rows if x["judgment"] == "本質的算定")),
        isomorphic_groups=n_groups,
        judgment_by_old_class={c: dict(C(x["judgment"] for x in rows if x["old_class"] == c)) for c in "12345"},
        base_op_occurrence=dict(C(o for x in rows for o in x["base_ops"].split(";") if o)),
        must_keep=dict(C(k.split("（")[0] for x in rows for k in x["must_keep_meaning"].split("；") if k)),
        cells_by_judgment={j: sum(x["cells"] for x in rows if x["judgment"] == j) for j in set(x["judgment"] for x in rows)},
    )
    assert sum(summ["judgment"].values()) == 667
    with open(os.path.join(out, "ledger667_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summ, f, ensure_ascii=False, indent=1)
    print(json.dumps(summ, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
