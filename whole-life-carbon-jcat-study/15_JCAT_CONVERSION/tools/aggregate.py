"""Per independent equation: classification, conversion status (base / improved), failure cause and all
verification counts (L1 every cell, boundary, random cases, building-level chain). Writes status.json
(private, used by gen_equations.py), the public CSV and totals.json."""
import sys, os, csv, json, pickle, collections, glob

C = os.path.dirname(os.path.abspath(__file__))
S = os.path.dirname(C)
D = pickle.load(open(os.path.join(C, "instances.pkl"), "rb"))
P = D["patterns"]
cls = json.load(open(os.path.join(S, "classify", "final.json"), encoding="utf-8"))
L1 = {"base": pickle.load(open(os.path.join(C, "L1_base.pkl"), "rb")), "improved": pickle.load(open(os.path.join(C, "L1_improved.pkl"), "rb"))}
VB = {}
for m in ("base", "improved"):
    p = os.path.join(C, "vb_%s.pkl" % m)
    VB[m] = pickle.load(open(p, "rb"))["results"] if os.path.exists(p) else {}
import rc_load
RCS = rc_load.load_all(os.path.join(S, "lo"))
CH = {}
for p in glob.glob(os.path.join(C, "chain_*.pkl")):
    CH[os.path.basename(p)[6:-4]] = pickle.load(open(p, "rb"))

APPROX = ("power with a non-integer exponent", "logarithm of a variable")
CAUSE = {
    "text concatenation": ("方法の不足", "テキストの連結：今の値の表し方（テキストを1つの符号として扱う）には新しいテキストを作る演算がない。"
                           "テキストを文字の並び（長さと各位置の文字符号）として持たせれば積和で書ける見込みがあるが、実装・検証していない"),
    "text substitution": ("方法の不足", "テキストの置換：同上（新しいテキストを作る演算がない）。文字の並びによる拡張は未実装・未検証"),
    "part of a text": ("方法の不足", "テキストの部分取り出し：基本方式では書けない。改良方式（数値の桁と文字の分解）で変換"),
    "criterion with a wildcard": ("方法の不足", "ワイルドカードによる照合：基本方式ではテキストを文字に分解していない。改良方式（文字の付随情報の述語の積）で変換"),
    "power with a non-integer exponent": ("本質的", "整数でない指数の実数べき：有理関数と格子の和の有限の合成では厳密に表せない（超越関数）。改良方式は誤差上限付きの近似"),
    "logarithm of a variable": ("本質的", "常用対数：有理関数と格子の和の有限の合成では厳密に表せない（超越関数）。改良方式は誤差上限付きの近似"),
}


def cause_of(reason):
    for k, v in CAUSE.items():
        if reason and reason.startswith(k):
            return v
    return ("要確認", reason or "")


def pattern_status(pid, m):
    l1 = L1[m].get(pid)
    vb = VB[m].get(pid)
    if m == "base" and vb is not None and vb.get("same_as_improved_groups") and vb["n"] == 0 and not vb["unsupported"]:
        vb = VB["improved"].get(pid)          # identical programs in every group: the improved results are the base ones
    st = dict(l1_n=0, l1_ok=0, vb_n=0, vb_ok=0, rc_n=0, rc_ok_ref=0, rc_ok_lo=0, rc_ref_eq_lo=0, status=None, cause=None, kind=None)
    if l1 is None:
        st["status"] = "未実行"
        return st
    st["l1_n"], st["l1_ok"] = l1["n"], l1["ok"]
    if l1["unsupported"]:
        kind, why = cause_of(l1["unsupported"])
        st.update(status="失敗", cause=why, kind=kind)
        return st
    if vb is not None:
        st["vb_n"], st["vb_ok"] = vb["n"], vb["ok"]
    for b, r in RCS.items():
        sp = r["stats"].get(pid)
        if sp is None:
            continue
        c = sp.get(m)
        if m == "base" and not c.get("n") and not c.get("unsupported"):
            c = sp.get("improved")          # identical programs: the improved evaluations are the base ones
        if c:
            st["rc_n"] += c.get("n", 0); st["rc_ok_ref"] += c.get("ok_ref", 0); st["rc_ok_lo"] += c.get("ok_lo", 0)
            st["rc_ref_eq_lo"] += c.get("ref_eq_lo", 0)
    problems = []
    if l1["bad"]:
        problems.append("全セル照合で不一致 %d" % l1["bad"])
    if vb is not None and vb["unsupported"]:
        problems.append("境界条件の照合が実行できない：%s" % vb["unsupported"][:80])
    elif vb is not None and vb["bad"] and vb["bad"] > vb["missing"]:
        problems.append("境界条件で不一致 %d / %d（うち範囲外の欠損 %d）" % (vb["bad"], vb["n"], vb["missing"]))
    domain = vb is not None and vb["bad"] and vb["bad"] == vb["missing"] and not vb["unsupported"]
    if st["rc_n"] and st["rc_ok_ref"] < st["rc_n"]:
        problems.append("無作為ケースで参照評価器と不一致 %d / %d" % (st["rc_n"] - st["rc_ok_ref"], st["rc_n"]))
    base_reason = L1["base"].get(pid, {}).get("unsupported") or ""
    approx = m == "improved" and any(base_reason.startswith(a) for a in APPROX)
    if problems:
        st.update(status="失敗", cause="；".join(problems), kind="方法の不足（反例あり）")
    elif approx:
        st.update(status="近似で変換", cause="誤差上限付きの近似（厳密ではない）", kind="近似")
    elif domain:
        st.update(status="定義域付きで変換", cause="境界条件 %d / %d が定義域の外（値を返さず欠損。値の不一致はなし）" % (vb["missing"], vb["n"]),
                  kind="定義域")
    else:
        st.update(status="成功")
    return st


def main():
    by_eq = collections.defaultdict(list)
    for pid, p in P.items():
        by_eq[p["eq"]].append(pid)
    status, rows = {}, []
    tot = collections.Counter()
    for eq in sorted(by_eq):
        pids = by_eq[eq]
        cells = sum(P[p]["n"] for p in pids)
        rec = {}
        for m in ("base", "improved"):
            ps = {pid: pattern_status(pid, m) for pid in pids}
            sts = collections.Counter(v["status"] for v in ps.values())
            if sts.get("失敗") or sts.get("未実行"):
                s = "失敗"
            elif sts.get("近似で変換"):
                s = "近似で変換"
            elif sts.get("定義域付きで変換"):
                s = "定義域付きで変換"
            else:
                s = "成功"
            causes = sorted({v["cause"] for v in ps.values() if v["cause"]})
            kinds = sorted({v["kind"] for v in ps.values() if v["kind"]})
            agg = collections.Counter()
            for v in ps.values():
                for k in ("l1_n", "l1_ok", "vb_n", "vb_ok", "rc_n", "rc_ok_ref", "rc_ok_lo", "rc_ref_eq_lo"):
                    agg[k] += v[k]
            rec[m] = dict(status=s, causes=causes, kinds=kinds, counts=dict(agg),
                          failed_patterns=[p for p, v in ps.items() if v["status"] == "失敗"])
        chain = collections.Counter()
        for b, r in CH.items():
            for pid in pids:
                for k, v in r["per_pid"].get(pid, {}).items():
                    chain[k] += v
        c = cls[eq]
        ci = rec["improved"]["counts"]
        ver = ("全セル照合 %d/%d、境界条件 %d/%d、無作為ケース 参照評価器と %d/%d・LibreOffice と %d/%d、建物全体の連鎖 %d/%d" % (
            ci["l1_ok"], ci["l1_n"], ci["vb_ok"], ci["vb_n"], ci["rc_ok_ref"], ci["rc_n"], ci["rc_ok_lo"], ci["rc_n"],
            chain["ok"], chain["ok"] + chain["bad"]))
        status[eq] = dict(base=rec["base"]["status"], improved=rec["improved"]["status"],
                          cause="；".join(rec["base"]["causes"] + [x for x in rec["improved"]["causes"] if x not in rec["base"]["causes"]]),
                          verification=ver, detail=rec)
        rows.append({"独立方程式ID": eq, "セル数": cells, "パターン数": len(pids), "分類": c["category"], "分類名": c["category_name"],
                     "小分類（研究側の呼び名）": c["subtype"], "本質的な算定規則": "はい" if c["essential_rule"] else "いいえ（表示・転記・補助）",
                     "分類の決め方": "2組一致" if c["decided"].startswith("2組の読み手") else "判定者が決定",
                     "基本方式": rec["base"]["status"], "基本方式の失敗の種類": "／".join(rec["base"]["kinds"]),
                     "改良方式": rec["improved"]["status"], "改良方式の失敗の種類": "／".join(rec["improved"]["kinds"]),
                     "全セル照合（改良）": "%d/%d" % (ci["l1_ok"], ci["l1_n"]), "境界条件（改良）": "%d/%d" % (ci["vb_ok"], ci["vb_n"]),
                     "無作為・参照評価器（改良）": "%d/%d" % (ci["rc_ok_ref"], ci["rc_n"]), "無作為・LibreOffice（改良）": "%d/%d" % (ci["rc_ok_lo"], ci["rc_n"]),
                     "建物全体の連鎖": "%d/%d" % (chain["ok"], chain["ok"] + chain["bad"]),
                     "全セル照合（基本）": "%d/%d" % (rec["base"]["counts"]["l1_ok"], rec["base"]["counts"]["l1_n"]),
                     "境界条件（基本）": "%d/%d" % (rec["base"]["counts"]["vb_ok"], rec["base"]["counts"]["vb_n"])})
        tot["eq"] += 1
        tot["cat" + c["category"]] += 1
        tot["essential"] += c["essential_rule"]
        for m in ("base", "improved"):
            tot["%s:%s" % (m, rec[m]["status"])] += 1
            if c["essential_rule"]:
                tot["essential %s:%s" % (m, rec[m]["status"])] += 1
            for k, v in rec[m]["counts"].items():
                tot["%s:%s" % (m, k)] += v
        tot["chain_ok"] += chain["ok"]; tot["chain_bad"] += chain["bad"]
    json.dump(status, open(os.path.join(C, "status.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    with open(os.path.join(C, "public_table.csv"), "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    cases = {b: len(r["cases"]) for b, r in RCS.items()}
    tot = dict(tot)
    tot["random_cases"] = cases
    tot["random_cases_total"] = sum(cases.values())
    json.dump(tot, open(os.path.join(C, "totals.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(tot, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
