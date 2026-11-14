"""PRIVATE package (J-CAT formulas, values and cell addresses): classification with reasons, all equations before
and after the conversion, verification details per pattern with examples, random-case inputs and seeds,
LibreOffice differences, input-cell list. Written to <out_dir>; never committed."""
import sys, os, csv, gzip, json, pickle, collections, glob

C = os.path.dirname(os.path.abspath(__file__))
S = os.path.dirname(C)
out = sys.argv[1]
os.makedirs(out, exist_ok=True)
D = pickle.load(open(os.path.join(C, "instances.pkl"), "rb"))
P = D["patterns"]
cls = json.load(open(os.path.join(S, "classify", "final.json"), encoding="utf-8"))
status = json.load(open(os.path.join(C, "status.json"), encoding="utf-8"))
dossier = json.load(open(os.path.join(C, "dossier.json"), encoding="utf-8"))
rows02b = list(csv.DictReader(open(os.path.join(S, "private_out", "02b_正規化パターン全件.csv"), encoding="utf-8-sig")))
rep = {}
for r in rows02b:
    if r["独立方程式ID"] not in rep or int(r["セル数"]) > int(rep[r["独立方程式ID"]]["セル数"]):
        rep[r["独立方程式ID"]] = r

# 01 classification and correspondence
with open(os.path.join(out, "01_667式の分類と対応表_非公開.csv"), "w", encoding="utf-8-sig", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["独立方程式ID", "セル数", "パターン数", "分類", "分類名", "小分類", "本質的な算定規則", "分類の理由", "分類の決め方",
                "読み手A（分類/小分類/理由）", "読み手B（分類/小分類/理由）", "代表セル", "原版の式（代表）", "骨格", "使用関数", "現れるシート",
                "基本方式", "改良方式", "変換できない理由・反例", "検証（改良方式）"])
    for eq in sorted(cls):
        c, st, d = cls[eq], status[eq], dossier[eq]
        w.writerow([eq, d["cells"], d["patterns"], c["category"], c["category_name"], c["subtype"], "はい" if c["essential_rule"] else "いいえ",
                    c["reason"], c["decided"], "%s/%s/%s" % (c["passA"]["category"], c["passA"]["subtype"], c["passA"]["reason"]),
                    "%s/%s/%s" % (c["passB"]["category"], c["passB"]["subtype"], c["passB"]["reason"]), d["representative"], d["formula"],
                    d["skeleton"], d["functions"], d["sheets"], st["base"], st["improved"], st["cause"], st["verification"]])

# 03 verification per pattern
L1b = pickle.load(open(os.path.join(C, "L1_base.pkl"), "rb"))
L1i = pickle.load(open(os.path.join(C, "L1_improved.pkl"), "rb"))
VB = {m: (pickle.load(open(os.path.join(C, "vb_%s.pkl" % m), "rb")) if os.path.exists(os.path.join(C, "vb_%s.pkl" % m)) else {"results": {}})
      for m in ("base", "improved")}
import rc_load
RCS = rc_load.load_all(os.path.join(S, "lo"))
CH = {os.path.basename(p)[6:-4]: pickle.load(open(p, "rb")) for p in glob.glob(os.path.join(C, "chain_*.pkl"))}
with open(os.path.join(out, "03_パターン別の検証結果_非公開.csv"), "w", encoding="utf-8-sig", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["パターンID", "独立方程式ID", "セル数", "原版の式（代表）",
                "全セル照合・基本（n/一致/欠損/変換不可）", "全セル照合・改良", "境界・基本（n/一致）", "境界・改良（n/一致）", "境界の不一致の種類（基本）",
                "境界の不一致例（基本）", "境界の不一致例（改良）", "無作為・改良（n/参照評価器と一致/LibreOfficeと一致）", "無作為の不一致の種類", "無作為の不一致例",
                "建物全体の連鎖（一致/不一致）"])
    for pid in sorted(P, key=lambda q: (P[q]["eq"], -P[q]["n"])):
        p = P[pid]
        lb, li = L1b.get(pid, {}), L1i.get(pid, {})
        vbb, vbi = VB["base"]["results"].get(pid, {}), VB["improved"]["results"].get(pid, {})
        rcn = collections.Counter()
        rex = []
        for b, r in RCS.items():
            sp = r["stats"].get(pid)
            if sp:
                rcn.update(sp["improved"])
            rex += r["examples"].get(pid, [])[:3]
        ch = collections.Counter()
        for r in CH.values():
            ch.update(r["per_pid"].get(pid, {}))
        w.writerow([pid, p["eq"], p["n"], "=" + p["text"],
                    "%s/%s/%s/%s" % (lb.get("n"), lb.get("ok"), lb.get("missing"), lb.get("unsupported") or ""),
                    "%s/%s/%s/%s" % (li.get("n"), li.get("ok"), li.get("missing"), li.get("unsupported") or ""),
                    "%s/%s" % (vbb.get("n"), vbb.get("ok")), "%s/%s" % (vbi.get("n"), vbi.get("ok")),
                    json.dumps(dict(vbb.get("bad_by_kind", {})), ensure_ascii=False), json.dumps(vbb.get("examples", [])[:3], ensure_ascii=False),
                    json.dumps(vbi.get("examples", [])[:3], ensure_ascii=False),
                    "%d/%d/%d" % (rcn["n"], rcn["ok_ref"], rcn["ok_lo"]),
                    json.dumps({k: v for k, v in rcn.items() if k not in ("n", "ok_ref", "ok_lo", "ref_eq_lo")}, ensure_ascii=False),
                    json.dumps(rex[:3], ensure_ascii=False), "%d/%d" % (ch["ok"], ch["bad"])])

# 04 random cases: seeds, inputs, logs
cases = {b: r["cases"] for b, r in RCS.items()}
with gzip.open(os.path.join(out, "04_無作為ケースの入力とシード_非公開.json.gz"), "wt", encoding="utf-8") as fh:
    json.dump({b: [dict(c, inputs={str(sid): {str(k): (v if not hasattr(v, "code") else "#ERR%d" % v.code) for k, v in kv.items()}
                                     for sid, kv in c["inputs"].items()}) for c in cs] for b, cs in cases.items()}, fh, ensure_ascii=False)

# 05 LibreOffice differences at the original inputs (roots)
roots = pickle.load(open(os.path.join(S, "lo", "roots.pkl"), "rb"))
with open(os.path.join(out, "05_LibreOfficeとExcelの違い_根_非公開.csv"), "w", encoding="utf-8-sig", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["ブック", "独立方程式ID", "パターンID", "根のセル数", "原版の式", "例（シート, 行, 列, LibreOffice, 参照評価器（LOの入力で）, Excel）"])
    for (book, eq, pid), n in sorted(roots["roots"].items(), key=lambda x: -x[1]):
        w.writerow([book, eq, pid, n, "=" + P[pid]["text"], json.dumps(roots["examples"][(book, eq, pid)], ensure_ascii=False)])

# 06 input cells
spec = pickle.load(open(os.path.join(C, "input_spec.pkl"), "rb"))
with open(os.path.join(out, "06_無作為ケースの入力欄_非公開.csv"), "w", encoding="utf-8-sig", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["ブック", "シート", "行", "列", "項目名", "詳細分類", "単位", "データ型", "入力の種類", "原版の値", "選択肢"])
    for b, items in spec.items():
        for it in items:
            w.writerow([b, it["sheet"], it["row"], it["col"], it["item"], it["detail"], it["unit"], it["dtype"], it["kind"],
                        repr(it["value"]) if it["value"] is not None else "", "|".join(map(str, it["options"])) if it["options"] else ""])

# 07 classification materials
json.dump({"dossier": dossier, "passes": json.load(open(os.path.join(S, "classify", "passes.json"), encoding="utf-8")), "final": cls},
          open(os.path.join(out, "07_分類の判断資料_非公開.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
json.dump(json.load(open(os.path.join(C, "private_config.json"), encoding="utf-8")),
          open(os.path.join(out, "08_LibreOffice用の複製への置き換え_非公開.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("written", sorted(os.listdir(out)))
