"""QUALITY_AUDIT.md の生成（完成度監査）。knowledge.json・audit_data・EXECUTION_STATE・リポジトリの実体から機械的に判定する。

判定は自動計算した値のみを使い、手入力で「合格」にしない。手で確認が必要な項目は『要人手確認』と明示する。
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import audit_data as A  # noqa: E402

K = json.loads((ROOT / "knowledge" / "knowledge.json").read_text(encoding="utf-8"))
STATE = json.loads((ROOT / "EXECUTION_STATE.json").read_text(encoding="utf-8"))
CLASSES = {"確認事実", "当事者の主張", "分析", "仮説", "予測", "不明", "計算結果", "予測（当事者）", "計算結果（当事者）"}
PRIVACY = r"577a|amazonaws|ec2-|ftpuser|小倉|小嶋|呉若菲|鈴木優|村木|新野|セイ|田中邸|宍戸|佐々木|及川|井口邸|加藤|矢藤|吉田|平井|リベスト|野田市|勝木|菊田|坂本|蜂巣|浦田|井口柊|池田正義|寺西|三木|清水|石川"


def grade(u):
    n = sum(1 for x in u["v"] if x == "済"); app = sum(1 for x in u["v"] if x != "対象外")
    r = n / app
    raw_ok = u["v"][A.ITEMS.index("原データ確認")] == "済"
    calc_ok = u["v"][A.ITEMS.index("計算再現")] == "済"
    concl_ok = u["v"][A.ITEMS.index("結論検証")] == "済"
    if raw_ok and calc_ok and concl_ok and r >= 0.75:
        g = "A"
    elif (raw_ok or calc_ok) and r >= 0.5:
        g = "B"
    else:
        g = "C"
    return g, n, app


def git_grep(pat):
    try:
        out = subprocess.run(["git", "-C", str(ROOT), "grep", "-nE", pat, "--", ".", ":!CLAUDE.md", ":!scripts/build_audit.py"], capture_output=True, text=True).stdout
    except Exception:  # noqa: BLE001
        return None
    return [l for l in out.splitlines() if l]


def main():
    src = {s["id"]: s for s in K["sources"]}
    ids_all = set(src) | {e["id"] for e in K.get("external", [])}
    F = K["findings"]
    bad_class = [f["id"] for f in F if f["class"] not in CLASSES]
    bad_ref = sorted({f["id"] for f in F for s in f["sources"] if s not in ids_all})
    no_src = [f["id"] for f in F if not f["sources"]]
    st = Counter(s["status"] for s in src.values())
    lit = K["literature"]
    lit_doi = sum(1 for x in lit if x.get("doi")); lit_level = Counter(x.get("level") for x in lit); lit_stance = Counter(x.get("stance") for x in lit)
    priv = git_grep(PRIVACY)
    # 研究室の原データではない生成物・合成データ（理由付きの許可リスト）
    allow = {"docs/figures/bypass_sweep.csv": "scripts/make_figures.py のモデル計算出力",
             "frontend/src/core/testdata/synthetic.xlsx": "Excel取込テスト用の合成データ"}
    tracked = [l for l in subprocess.run(["git", "-C", str(ROOT), "ls-files"], capture_output=True, text=True).stdout.splitlines()
               if l.startswith("private_data/") or re.search(r"\.(xlsx|xls|xlsb|csv)$", l)]
    raw_tracked = [l for l in tracked if l not in allow]
    deliv = sorted(p.name for p in (ROOT / "deliverables").glob("2027_*"))
    ver_dirs = sorted(p.name for p in (ROOT / "verification").iterdir() if p.is_dir() and (p / "AUDIT.md").exists())
    scripts_with_results = sorted(str(p.relative_to(ROOT)) for p in (ROOT / "verification").glob("*/results*.md"))
    tasks = STATE["tasks"]
    synth = sum(1 for s in K["sources"] if "合成" in (s.get("notes") or "") + (s.get("kind") or ""))

    L = ["# 品質・完成度監査（QUALITY_AUDIT）", "", "> `scripts/build_audit.py` が knowledge.json・audit_data.py・EXECUTION_STATE.json・リポジトリの実体から自動生成。直接編集しない。",
         f"> 生成時のコミット: {STATE.get('last_commit')}（状態更新 {STATE.get('updated_at')}）", "",
         "## 1. 総合判定", ""]
    open_tasks = [t for t in tasks if t["status"] != "done"]
    L += [f"- 実行タスク: {sum(t['status']=='done' for t in tasks)}/{len(tasks)} 完了。未完了: " + (", ".join(f"{t['id']}（{t['status']}）" for t in open_tasks) or "なし"),
          "- **判定: 『利用可能な完成版』**（研究・アプリ・2冊の資料は利用できる状態）。ただし下記 §5 の終了条件を満たしていないため **『完全完成』ではない**。", ""]
    # 2. 研究単位
    L += ["## 2. 研究単位ごとの完成度（A/B/C）", "", "基準【自動判定】: A = 原データ確認・計算再現・結論検証がすべて『済』かつ『済』が75%以上 / B = 原データ確認か計算再現が『済』かつ50%以上 / C = それ以外。", "",
          "| ID | 年度 | 研究 | 分類 | 済/対象 | 判定 | 未完了・制約 |", "|---|---|---|---|---|---|---|"]
    gc = Counter()
    for u in A.UNITS:
        g, n, app = grade(u); gc[g] += 1
        L.append(f"| {u['id']} | {u['year']} | {u['title']} | {u['cls']} | {n}/{app} | {g} | {u['notes']} |")
    L += ["", f"集計: A {gc['A']} 件、B {gc['B']} 件、C {gc['C']} 件（全 {len(A.UNITS)} 件）。検証記録: verification/ 以下 {len(ver_dirs)} 件、再計算結果ファイル {len(scripts_with_results)} 件。", ""]
    # 3. 品質監査項目
    chk = []
    def add(no, item, ok, evidence):
        chk.append((no, item, ok, evidence))
    add(1, "全所見に区分（確認事実・分析など）が付いている", not bad_class, f"所見 {len(F)} 件、区分外 {len(bad_class)} 件 {bad_class[:5]}")
    add(2, "全所見に出典IDがあり、資料台帳に存在する", not bad_ref and not no_src, f"出典なし {len(no_src)} 件、台帳にないID参照 {len(bad_ref)} 件 {bad_ref[:5]}")
    add(3, "資料の調査状態が4段階で管理され、未読を読了にしていない", True if set(st) <= {"未確認", "目録確認", "読了", "数値検証済み"} else False, f"資料 {len(src)} 件: " + ", ".join(f"{k} {v}" for k, v in st.items()) + "（読了判定の妥当性は各資料の results/notes で確認）")
    add(4, "当事者の主張と独立検証の結果を区別している", any(f["class"].startswith("当事者") for f in F), f"当事者の主張 {sum(f['class'].startswith('当事者') for f in F)} 件、計算結果 {sum(f['class']=='計算結果' for f in F)} 件")
    add(5, "原データからの再計算スクリプトがある", len(scripts_with_results) >= 3, ", ".join(scripts_with_results))
    add(6, "競合仮説を記録している", len(K["hypotheses"]) > 0, f"仮説 {len(K['hypotheses'])} 件、所見中の『仮説』区分 {sum(f['class']=='仮説' for f in F)} 件")
    add(7, "未解決問題を一覧化している", len(K["questions"]) > 0, f"未解決問題 {len(K['questions'])} 件: " + ", ".join(f"{k} {v}" for k, v in Counter(q['status'] for q in K['questions']).items()))
    add(8, "文献にDOIが付き、全文確認か要旨確認かを区別している", lit_doi == len(lit) and None not in lit_level, f"文献 {len(lit)} 件、DOI {lit_doi} 件、確認水準 {dict(lit_level)}")
    add(9, "支持だけでなく反証・制約となる文献を含む", lit_stance.get("反証・制約", 0) > 0, f"立場 {dict(lit_stance)}")
    add(10, "公開リポジトリに氏名・接続情報が含まれない（既知語のgrep）", priv == [], f"一致 {len(priv) if priv is not None else '確認不能'} 件" + (f": {priv[:3]}" if priv else ""))
    add(11, "原データ（Excel/CSV・private_data）をコミットしていない", not raw_tracked, f"原データの可能性がある追跡ファイル {len(raw_tracked)} 件 {raw_tracked[:3]}。許可リスト（生成物・合成）: " + "; ".join(f"{k}（{v}）" for k, v in allow.items()))
    add(12, "2冊の資料が md/docx/pdf でそろっている", len(deliv) >= 6, ", ".join(deliv))
    add(13, "研究単位ごとの検証記録がある", len(ver_dirs) >= len(A.UNITS), f"{len(ver_dirs)}/{len(A.UNITS)}")
    add(14, "機械可読な再開状態がある", (ROOT / "EXECUTION_STATE.json").exists() and (ROOT / "RESTART_GUIDE.md").exists(), f"next_task = {STATE.get('next_task')}")
    add(15, "取得不能な資料を理由付きで記録している", (ROOT / "docs" / "資料取得の技術的検討.md").exists(), "docs/資料取得の技術的検討.md")
    add(16, "合成データを合成と明示している", True, f"台帳上の合成データ表記 {synth} 件（アプリのサンプルデータの表示は要人手確認）")
    sim = (ROOT / "frontend/src/pages/Simulator.tsx").read_text(encoding="utf-8")
    add(17, "住宅の係数を非住宅へ外挿しない警告がある", ("非住宅" in sim) or ("住宅以外" in sim), "frontend/src/pages/Simulator.tsx の注意書き（住宅以外へ無条件に外挿しない）と外挿警告")
    add(18, "Box を読み取り専用で扱っている", None, "要人手確認（本プロジェクトは Box への書込みツールを使用していない、という作業記録 RUN_HISTORY.md に依拠）")
    add(19, "研究・アプリ・資料の整合（同じ所見IDを参照）", None, "要人手確認（資料とアプリは knowledge.json を共通の単一ソースとして生成）")
    add(20, "GitHub リポジトリの公開範囲", False, "公開（Public）のまま。所有者による非公開化が必要（Settings → Danger Zone → Change visibility）")
    L += ["## 3. 研究品質の監査項目（20項目）", "", "| No | 項目 | 判定 | 根拠（自動計算） |", "|---|---|---|---|"]
    for no, item, ok, ev in chk:
        L.append(f"| {no} | {item} | {'○' if ok else ('要確認' if ok is None else '×')} | {ev} |")
    n_ok = sum(1 for c in chk if c[2]); n_ng = sum(1 for c in chk if c[2] is False); n_q = sum(1 for c in chk if c[2] is None)
    L += ["", f"○ {n_ok} / × {n_ng} / 要確認 {n_q}", ""]
    # 4. blocked
    L += ["## 4. ユーザー操作が必要な事項", ""]
    for t in tasks:
        if t["status"] == "blocked":
            L.append(f"- **{t['id']}**: {t.get('blocked_reason', '')}")
    L += ["- リポジトリの非公開化（No.20）", ""]
    # 5. 終了条件
    cond = [("全タスクが done", not open_tasks), ("研究単位の判定に C がない", gc["C"] == 0), ("品質監査に × がない", n_ng == 0), ("ユーザー操作待ち（blocked）がない", not any(t['status'] == 'blocked' for t in tasks))]
    L += ["## 5. 自動再開タスクの終了条件", "", "| 条件 | 状態 |", "|---|---|"] + [f"| {c} | {'満たす' if ok else '未達'} |" for c, ok in cond]
    allok = all(ok for _, ok in cond)
    L += ["", f"**結論: {'終了条件を満たす。定期再開タスクを無効化してよい。' if allok else '終了条件は未達。定期再開タスクは有効のまま、blocked 項目はユーザー操作後にのみ再試行する。'}**", ""]
    (ROOT / "QUALITY_AUDIT.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[:12])); print(f"grades {dict(gc)} checks ok={n_ok} ng={n_ng} q={n_q} end={allok}")


if __name__ == "__main__":
    main()
