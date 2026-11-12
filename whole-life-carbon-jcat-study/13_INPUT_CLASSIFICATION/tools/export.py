"""Stage D: the four deliverables from the private inventory.

The public files carry structure only: places, kinds, types, units, counts and the classification.
Values of the originals (factors, default rates, code tables, option lists, item names of the data
tables) are not written. Usage: python3 -I export.py <scan.sqlite3> <tree v0.1 json> <manual.txt> <out dir>
"""
import collections, csv, datetime, json, os, re, sqlite3, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tree_ext  # noqa: E402

BOOK = {1: "簡易算定", 2: "標準算定", 3: "分類表", 4: "集計表", 5: "詳細算定"}
STATE = {"visible": "表示", "hidden": "非表示", "veryHidden": "非表示（強）", "": ""}
LABEL_OK = {"input_main", "input", "input_b1", "input_b67", "doc", "check", "result", "param"}
FIXED = {"L": "見出し・説明文", "F": "自動計算（数式）", "DV": "選択リストの定義", "DVX": "入力規則の範囲（使用範囲の外）", "FX": "参照に問題のある数式",
         "CM": "セルのコメント", "CT": "フォーム部品", "NM": "名前定義", "VB": "VBA マクロ"}
HEAD = ["台帳ID", "分類ID", "大分類", "小分類", "詳細分類", "項目名", "入力データの種類", "データ型", "単位", "原版での値または設定内容", "元ファイル",
        "シート", "シートの表示", "セル位置", "セル数", "うち空欄", "必須・任意・自動算出", "ライフサイクル段階", "状態", "要確認の種類", "行区分",
        "原版の見出し", "分類の根拠", "統合先（重複）", "不明点・注意事項"]
TERMS = [("評価期間", "building.boundary.study_period"), ("建替周期", "building.boundary.replacement_cycle"), ("延べ床面積", "building.geometry.gross_floor_area"),
         ("主要構造", "building.structure.main_structure"), ("更新周期", "operation.maintenance.material_cycle"), ("修繕率", "operation.maintenance.repair_rate"),
         ("漏洩率", "operation.leakage.leak_rate"), ("回収率", "operation.leakage.recovery_rate"), ("端材率", "construction.transport.offcut_waste"),
         ("リユース率", "construction.transport.reuse_recycle"), ("排出係数", "assessment.factors.energy_factor"), ("EPD", "assessment.factors.epd"),
         ("複合原単位", "assessment.factors.composite_factor"), ("工事分倍率", "assessment.conversions.work_multiplier"),
         ("炭素貯蔵", "assessment.assumptions.carbon_coefficients"), ("物価補正", "assessment.conversions.price_correction"),
         ("創エネ", "operation.generation.generation"), ("冷媒", "equipment.refrigerant_equipment.charge"), ("上水", "operation.utility.water"),
         ("チェックリスト", "assessment.check.checklist"), ("システム境界", "assessment.method.system_boundary"), ("樹種", "construction.item_details.timber_carbon")]


def clean(text, limit=24):
    text = re.sub(r"\s+", " ", (text or "").replace("_x000D_", " ")).strip()
    text = text.split(" / ")[-1]
    return text if len(text) <= limit else text[:limit - 1] + "…"


def main(path, tree_path, manual_path, out):
    os.makedirs(out, exist_ok=True)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    with open(tree_path, encoding="utf-8") as fh:
        v01 = json.load(fh)
    tree = tree_ext.build(v01)
    nodes = tree_ext.node_index(tree)
    files = {r["id"]: dict(r) for r in db.execute("SELECT * FROM files")}
    rows = [dict(r) for r in db.execute("SELECT * FROM inventory ORDER BY id")]

    def item_name(r):
        cat, br, det = nodes[r["node"]]
        name = det or br
        if r["role"] in FIXED:
            return FIXED[r["role"]] + ("：" + clean(r["label"].split("：")[-1], 28) if r["role"] in ("NM", "CT") else "")
        if r["grp"] and r["grp"] != "（表の上）":
            name += "／" + clean(r["grp"], 20)
        return name

    def public(r):
        cat, br, det = nodes[r["node"]]
        label = clean(r["label"]) if (r["skind"] in LABEL_OK and r["role"] in ("I", "C", "TD") and r["basis"] != "入力規則") else ""
        note = r["note"] or ""
        if r["basis"] in ("見出しなし", "見出し不一致", "行区分なし", "対象セル不明", "シート不明"):
            note = (note + "／" if note else "") + {"見出しなし": "近くに見出しがなく、意味を判断できない", "見出し不一致": "見出しが分類の規則に当てはまらない",
                                                  "行区分なし": "表の行区分に当てはまらない", "対象セル不明": "対象のセルが入力欄として見つからない",
                                                  "シート不明": "シートの役割を判断できない"}[r["basis"]]
        if r["skind"] not in LABEL_OK and r["role"] in ("I", "C", "TD"):
            note = (note + "／" if note else "") + "データ表のため見出しは非掲載"
        return [r["inv"], r["node"], cat, br, det, item_name(r), r["kind"], r["dtype"], r["unit"], r["descr"], files[r["file_id"]]["name"],
                r["sheet"], STATE.get(r["state"], r["state"]), r["cells"], r["n"], r["n_blank"], r["requirement"], r["stage"], r["status"],
                r["review"], clean(r["grp"], 20) if r["grp"] != "（表の上）" else "", label, r["basis"], r["dup_of"], note]

    with open(os.path.join(out, "JCAT_input_inventory.csv"), "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(HEAD)
        for r in rows:
            w.writerow(public(r))
    unclassified = [r for r in rows if r["status"] != "分類済み" or r["review"]]
    with open(os.path.join(out, "JCAT_input_unclassified.csv"), "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(HEAD)
        for r in unclassified:
            w.writerow(public(r))

    # ---- complete tree with what the inventory holds under every node
    per = collections.defaultdict(lambda: dict(rows=0, cells=0, blank=0, kinds=collections.Counter(), types=collections.Counter(),
                                               units=collections.Counter(), req=collections.Counter(), stages=collections.Counter(),
                                               books=collections.Counter(), status=collections.Counter(), entries=collections.OrderedDict()))
    for r in rows:
        p = per[r["node"]]
        p["rows"] += 1; p["cells"] += r["n"]; p["blank"] += r["n_blank"]
        p["kinds"][r["kind"]] += 1; p["types"][r["dtype"]] += 1; p["req"][r["requirement"]] += 1; p["status"][r["status"]] += 1
        p["books"][BOOK[r["file_id"]]] += 1
        if r["unit"]:
            p["units"][r["unit"]] += 1
        for st in (r["stage"] or "").split(", "):
            if st:
                p["stages"][st] += 1
        if r["skind"].startswith("input") and r["role"] in ("I", "C") and r["state"] == "visible":
            key = (clean(r["grp"], 20) if r["grp"] != "（表の上）" else "", clean(r["label"]) if r["basis"] != "入力規則" else "",
                   r["kind"], r["dtype"], r["unit"], r["requirement"])
            e = p["entries"].setdefault(key, dict(books=set(), cells=0))
            e["books"].add(BOOK[r["file_id"]]); e["cells"] += r["n"]

    def info(node_id):
        p = per.get(node_id)
        if not p:
            return {"n_rows": 0, "n_cells": 0}
        out_ = {"n_rows": p["rows"], "n_cells": p["cells"], "n_blank": p["blank"], "data_kinds": dict(p["kinds"]),
                "data_types": dict(p["types"]), "units": [u for u, _ in p["units"].most_common(8)],
                "requirement": dict(p["req"]), "lifecycle_stages": sorted(p["stages"]), "workbooks": dict(p["books"]),
                "status": dict(p["status"])}
        if p["entries"]:
            out_["input_entries"] = [{"id": "%s#%d" % (node_id, i + 1), "row_group": k[0], "label": k[1], "data_kind": k[2], "data_type": k[3],
                                      "unit": k[4], "requirement": k[5], "workbooks": sorted(e["books"]), "n_cells": e["cells"]}
                                     for i, (k, e) in enumerate(p["entries"].items())]
        return out_

    for cat in tree["categories"]:
        for br in cat["branches"]:
            br["inventory"] = info(br["id"])
            for d in br["details"]:
                d["inventory"] = info(d["id"])
    status = collections.Counter(r["status"] for r in rows)
    cells_by_status = collections.Counter()
    for r in rows:
        cells_by_status[r["status"]] += r["n"]
    item_rows = [r for r in rows if r["role"] in ("I", "C", "TD", "DV", "CT", "NM")]
    summary = {
        "generated": datetime.date.today().isoformat(),
        "originals": [{"file": f["name"], "bytes": f["size"], "sha256": f["sha256"], "sheets": f["n_sheets"]} for f in files.values()],
        "inventory_rows": len(rows), "rows_by_status": dict(status), "cells_by_status": dict(cells_by_status),
        "rows_by_role": dict(collections.Counter(r["role"] for r in rows)),
        "editable_blank_cells": sum(r["n_blank"] for r in rows if r["role"] == "I"),
        "duplicate_rows": sum(1 for r in rows if r["dup_of"]),
        "values_published": False,
    }
    tree["summary"] = summary
    tree["notes"] = ["この木は分類の構造だけを持つ。原版の数値・係数・選択肢・コード表・データ表の見出しは含まない。",
                     "input_entries は、表示されている入力シートにある入力欄を、行区分と見出しごとにまとめたもの。",
                     "v0.1 の大分類・小分類の ID は変えていない。from_v01 が false の節は今回追加したもの。"]
    with open(os.path.join(out, "JCAT_input_categories_complete.json"), "w", encoding="utf-8") as fh:
        json.dump(tree, fh, ensure_ascii=False, indent=1)

    # ---- numbers for the report (the text is written separately)
    with open(manual_path, encoding="utf-8") as fh:
        pages = re.split(r"\n=====PAGE \d+=====\n", fh.read())[1:]
    manual = []
    for term, node in TERMS:
        manual.append({"term": term, "pages": sum(1 for p in pages if term in p), "node": node, "rows": per[node]["rows"] if node in per else 0})
    sheet_names = sorted({re.sub(r"_(GHG|CO2)$", "", r["sheet"]) for r in rows if r["state"] == "visible" and r["sheet"]})
    in_manual = {n: sum(1 for p in pages if n in p) for n in sheet_names}
    stats = {
        "summary": summary,
        "by_category": {cat["id"]: {"rows": sum(per[n]["rows"] for n in per if n.startswith(cat["id"] + ".")),
                                    "cells": sum(per[n]["cells"] for n in per if n.startswith(cat["id"] + "."))} for cat in tree["categories"]},
        "by_kind": dict(collections.Counter(r["kind"] for r in rows)),
        "cells_by_kind": {k: sum(r["n"] for r in rows if r["kind"] == k) for k in set(r["kind"] for r in rows)},
        "review": dict(collections.Counter(r["review"] for r in rows if r["review"])),
        "other_rows": sum(1 for r in rows if r["node"].endswith(".other")),
        "item_rows": len(item_rows), "item_rows_by_status": dict(collections.Counter(r["status"] for r in item_rows)),
        "role_cells": {role: sum(r["n"] for r in rows if r["role"] == role) for role in ("I", "C", "TD", "L", "F")},
        "role_rows": dict(collections.Counter(r["role"] for r in rows)),
        "scan": {"formulas": db.execute("SELECT COUNT(*) FROM cells WHERE t='f'").fetchone()[0],
                 "numbers": db.execute("SELECT COUNT(*) FROM cells WHERE t IN ('n','b')").fetchone()[0],
                 "strings": db.execute("SELECT COUNT(*) FROM cells WHERE t='s' AND TRIM(v)<>''").fetchone()[0],
                 "sheets": db.execute("SELECT COUNT(*), SUM(state<>'visible'), SUM(protected) FROM sheets").fetchone()[:],
                 "validations": db.execute("SELECT COUNT(*) FROM validations").fetchone()[0],
                 "names": db.execute("SELECT COUNT(*), SUM(refers_to LIKE '%#REF!%') FROM names").fetchone()[:],
                 "controls": db.execute("SELECT COUNT(*) FROM controls").fetchone()[0],
                 "comments": db.execute("SELECT COUNT(*) FROM comments").fetchone()[0],
                 "dv_outside": db.execute("SELECT COALESCE(SUM(n),0), COUNT(DISTINCT sheet_id) FROM dv_outside").fetchone()[:],
                 "ref_formulas": db.execute("SELECT COUNT(*) FROM cells WHERE f LIKE '%#REF!%'").fetchone()[0],
                 "cond_formats": db.execute("SELECT SUM(n_cf) FROM sheets").fetchone()[0],
                 "blank_styled_skipped": db.execute("SELECT SUM(n_blank_skipped) FROM sheets").fetchone()[0]},
        "manual": {"pages": len(pages), "pages_without_text": sum(1 for p in pages if len(p.strip()) < 20), "terms": manual,
                   "visible_sheets": len(sheet_names), "visible_sheets_named_in_manual": sum(1 for n in in_manual.values() if n),
                   "not_named": [n for n, k in in_manual.items() if not k]},
        "per_book": {BOOK[f]: dict(collections.Counter(r["status"] for r in rows if r["file_id"] == f)) for f in files},
        "unclassified_rows": len(unclassified),
        "input_entries": sum(len(p["entries"]) for p in per.values()),
        "nodes": {"categories": len(tree["categories"]), "branches": sum(len(c["branches"]) for c in tree["categories"]),
                  "details": sum(len(b["details"]) for c in tree["categories"] for b in c["branches"]),
                  "details_added": sum(1 for c in tree["categories"] for b in c["branches"] for d in b["details"] if not d["from_v01"]),
                  "details_with_rows": sum(1 for c in tree["categories"] for b in c["branches"] for d in b["details"] if d["inventory"]["n_rows"]),
                  "details_without_rows": [d["id"] for c in tree["categories"] for b in c["branches"] for d in b["details"] if not d["inventory"]["n_rows"]]},
    }
    with open(os.path.join(out, "stats.json"), "w", encoding="utf-8") as fh:
        json.dump(stats, fh, ensure_ascii=False, indent=1)
    print(json.dumps({k: stats[k] for k in ("item_rows", "item_rows_by_status", "review", "other_rows", "unclassified_rows", "input_entries")}, ensure_ascii=False))
    print("nodes", {k: v for k, v in stats["nodes"].items() if k != "details_without_rows"}, "without rows:", len(stats["nodes"]["details_without_rows"]))


if __name__ == "__main__":
    main(*sys.argv[1:5])
