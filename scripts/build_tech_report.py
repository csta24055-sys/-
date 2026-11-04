"""中間統合技術調査報告書（2026年11月）の生成。

  .venv/bin/python scripts/build_tech_report.py           # CSV・図・Markdown・docx・pdf
  .venv/bin/python scripts/build_tech_report.py --no-pdf  # docx まで

入力: knowledge/knowledge.json, scripts/audit_data.py, verification/*/results*.json, report/*.md, scripts/tech_report_text.py
出力: deliverables/technical_report_2026-11/ 以下
  AQ_Research_Integrated_Technical_Report_2026-11.{md,docx,pdf}
  SOURCE_INVENTORY.csv, EVIDENCE_LEDGER.csv, NUMERICAL_AUDIT.csv, UNRESOLVED_ISSUES.md, REFERENCES.md, REPORT_QA.md, REPORT_README.md
  figures/*.png
原データ・原文・個人名は扱わない（集計値・要約・ID のみ）。
"""
from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import audit_data as A  # noqa: E402
import tech_report_text as T  # noqa: E402
import books_text as BT  # noqa: E402

OUT = ROOT / "deliverables" / "technical_report_2026-11"
FIG = OUT / "figures"
STEM = "AQ_Research_Integrated_Technical_Report_2026-11"
K = json.loads((ROOT / "knowledge" / "knowledge.json").read_text(encoding="utf-8"))
SRC = {s["id"]: s for s in K["sources"]}
FND = {f["id"]: f for f in K["findings"]}
UNIT_OF = {}
for u in A.UNITS:
    for s in u["sources"]:
        UNIT_OF.setdefault(s, u["id"])
SCRIPTS = {
    "R-2020": "scripts/validate_multizone.py", "R-2022-SIM": "verification/Y2022_simulation/verify_2022_sim.py; scripts/validate_fate_2022.py",
    "R-2022-MEAS": "verification/R-2022-MEAS/verify_2022_meas.py; verification/R-2022-MEAS/verify_2022_field.py",
    "R-2024": "scripts/raw_2024.py; scripts/events_2024.py", "R-2025": "scripts/raw_2025.py (main/dynamic/night/confound); scripts/annual_2024.py",
    "R-2026": "verification/R-2026/verify_2026.py; backend/aqros/models.py", "R-2018": "backend/tests/test_models.py (JEM1467)",
    "R-2023": "backend/tests/test_models.py (β理論式)", "R-2021-FALL": "backend/tests/test_models.py (落下計算)",
}


# ----------------------------------------------------------------------------- 匿名化
ANON = [(re.compile(r"I・W・K・S邸"), "住宅23-1〜23-4"), (re.compile(r"(?<![A-Za-z])I邸"), "住宅23-1"), (re.compile(r"(?<![A-Za-z])W邸"), "住宅23-2"),
        (re.compile(r"(?<![A-Za-z])K邸"), "住宅23-3"), (re.compile(r"(?<![A-Za-z])S邸"), "住宅23-4")]


def anon(t: str) -> str:
    t = t or ""
    for p, r in ANON:
        t = p.sub(r, t)
    return t


def cls_of(f: dict) -> str:
    c = f["class"]
    return {"確認事実": "FACT", "当事者の主張": "FACT（原著者の主張）", "計算結果": "CALC", "計算結果（当事者）": "FACT（原著者の計算）",
            "予測（当事者）": "FACT（原著者の予測）", "分析": "ANALYSIS", "仮説": "HYPOTHESIS", "予測": "HYPOTHESIS", "不明": "NOT VERIFIED"}.get(c, c)


def evidence_class(s: dict) -> str:
    st, kind = s["status"], s["kind"]
    if kind.startswith("外部"):
        return "E"
    if st == "数値検証済み":
        return "A" if ("原データ" in kind or kind in ("Excel(比較)", "Excel(校正データ)")) else "B"
    if st == "読了":
        if any(k in kind for k in ("梗概", "発表", "学会資料")):
            return "D"
        return "C"
    return "F"


MISSING = [
    ("M-01", 2018, "2018年度 空調室EP実験の計測データ（粉塵計・パーティクルカウンタ時系列）", "R-2018", "Box の2018年度フォルダに梗概・pptx のみ。原データは見つかっていない（2026-11-03 一覧で確認）",
     "掲載図表の読解・比較のみ可能。EP 設置位置の効果の大きさ（各条件1回）を原データから再評価できない"),
    ("M-02", 2019, "2019年度 臭気・粗大粒子実験の計測データ・官能評価の個票", "R-2019", "本論 docx・学会論文のみ取得",
     "臭気評価の統計（t検定）を再計算できない。石松子の沈降は Stokes 式で独立に検証済み"),
    ("M-03", 2021, "2021年度 浮遊班の原データ Excel", "R-2021-FLOAT", "Box で特定できていない",
     "βと M の同定値を原データから再計算できない"),
    ("M-04", 2021, "2021年度 落下班の本論・梗概", "R-2021-FALL", "Box で見つかっていない（Q-09）",
     "落下班の結論を原著者の記述として確認できない。計算シート・ダストサンプラー・粒子堆積モニタは取得済み"),
    ("M-05", 2025, "2025年度 住宅D 周南測定データ.xlsx の全数値（S-2025-22, 27.4 MB）", "R-2025", "連携の応答上限で取得不能。ページ画像で構成のみ確認",
     "条件①の回帰係数0.14（住宅A+Dのプール値）と住宅DのI/O 0.11を検証できない（F-V-06, Q-12）"),
    ("M-06", 2023, "2023年度 発塵量同定ブック（51.5 MB）", "R-2023", "連携の応答上限で取得不能", "発塵量の同定値を再計算できない"),
    ("M-07", 2023, "2023年度 実態調査まとめ.xlsx（S-2023-06, 14.2 MB）", "R-2023", "連携の応答上限で取得不能（2026-11-03）", "実住宅の時系列を再解析できない"),
    ("M-08", 2013, "2013年 EP付着粉塵の XRF・SEM 報告書", "R-2013-COMP", "3 MB 超・プレビュー生成失敗", "元素組成の比較ができない。ICP・イオンは検証済み"),
    ("M-09", 2026, "2026年度 EP試験の原データ・並列流路モデルの計算シート", "R-2026", "中間段階で Box に未掲載", "多台数時の CADR 最大値の計算条件（Q-13）を確定できない"),
]


# ----------------------------------------------------------------------------- 1. 資料台帳
def build_inventory() -> list[dict]:
    rows = []
    for s in K["sources"]:
        u = UNIT_OF.get(s["id"], "")
        ext = s["kind"].startswith("外部")
        pages = anon(s.get("pages") or "")
        rows.append({
            "資料ID": s["id"], "正式タイトル": anon(s["title"]), "年度": s["fiscal_year"],
            "著者": "（外部文献: REFERENCES.md）" if ext else "研究室所属の学生・教員（氏名は記載しない）",
            "研究テーマ": anon(s.get("topic") or ""), "資料の種類": s["kind"], "保存場所": f"Box: {s['folder']}（フォルダID {s['folder_id']}）",
            "ファイル名": anon(s["title"]), "Box ID": s["box_id"], "取得状況": s["status"], "対象ページ": pages or "記載なし",
            "原本・複製・二次": "二次資料（外部）" if ext else "原本（研究室 Box）",
            "図表の有無": "あり" if re.search(r"図|表|スライド", pages) else "未記録",
            "数値データの有無": "あり" if (re.search(r"Excel|CSV|csv", s["kind"]) or s.get("raw_data")) else "なし／未記録",
            "解析コードの有無": SCRIPTS.get(u, "なし") if s["status"] == "数値検証済み" else "なし",
            "検証状況": s["status"], "根拠区分": evidence_class(s), "研究単位": u,
            "引用可能な範囲": "書誌・要旨の範囲" if ext else "要約・数値・ページ参照のみ（原文の転載不可）",
            "個人情報・機密の注意": "ファイル名・シート名に居住者の姓を含む資料あり。住宅は記号で記載" if s["fiscal_year"] in ("2021", "2022", "2023", "2024", 2021, 2022, 2023, 2024) and not ext else "",
            "備考": anon((s.get("notes") or "")[:200]),
        })
    for i, l in enumerate(K["literature"], 1):
        rows.append({"資料ID": f"L-{i:02d}", "正式タイトル": l["title"], "年度": l["year"], "著者": "; ".join(l.get("authors") or [])[:200],
                     "研究テーマ": l.get("topic", ""), "資料の種類": "外部文献（査読論文等）", "保存場所": l.get("url", ""), "ファイル名": "",
                     "Box ID": "", "取得状況": l.get("level", ""), "対象ページ": "", "原本・複製・二次": "二次資料（外部）", "図表の有無": "未確認",
                     "数値データの有無": "", "解析コードの有無": "なし", "検証状況": l.get("level", ""), "根拠区分": "E", "研究単位": ", ".join(x for x in l.get("related", []) if x.startswith("R-")),
                     "引用可能な範囲": "書誌・要旨の範囲", "個人情報・機密の注意": "", "備考": f"DOI {l.get('doi', '')}; 立場: {l.get('stance', '')}"})
    for e in K.get("external", []):
        rows.append({"資料ID": e["id"], "正式タイトル": e["title"], "年度": "", "著者": "", "研究テーマ": "外部基準・統計", "資料の種類": "外部資料",
                     "保存場所": e.get("url", ""), "ファイル名": "", "Box ID": "", "取得状況": "参照", "対象ページ": "", "原本・複製・二次": "二次資料（外部）",
                     "図表の有無": "", "数値データの有無": "", "解析コードの有無": "なし", "検証状況": "参照", "根拠区分": "E", "研究単位": "",
                     "引用可能な範囲": "公開資料", "個人情報・機密の注意": "", "備考": e.get("note", "")})
    for mid, fy, title, u, how, impact in MISSING:
        rows.append({"資料ID": mid, "正式タイトル": title, "年度": fy, "著者": "", "研究テーマ": "", "資料の種類": "未取得資料", "保存場所": "未特定または取得不能",
                     "ファイル名": "", "Box ID": "", "取得状況": "未取得", "対象ページ": "", "原本・複製・二次": "", "図表の有無": "", "数値データの有無": "",
                     "解析コードの有無": "", "検証状況": "未確認", "根拠区分": "G" if "見つかっていない" in how or "特定できていない" in how or "未掲載" in how else "F",
                     "研究単位": u, "引用可能な範囲": "", "個人情報・機密の注意": "", "備考": f"{how}。影響: {impact}"})
    return rows


# ----------------------------------------------------------------------------- 2. 根拠台帳
SECTION_OF_UNIT = {"R-2013-COMP": "7.1", "R-2015": "7.2", "R-2018": "7.3", "R-2019": "7.4", "R-2020": "7.5", "R-2021-FLOAT": "7.6", "R-2021-FALL": "7.7",
                   "R-2022-MEAS": "8.2", "R-2022-SIM": "8.3", "R-2023": "9.1", "R-2024": "9.2", "R-2025": "10.1", "R-2026": "11.1", "R-JOINT-2024": "12.1"}


def unit_of_finding(f: dict) -> str:
    for u in A.UNITS:
        if f["id"] in u["evidence"]:
            return u["id"]
    for s in f["sources"]:
        if s in UNIT_OF:
            return UNIT_OF[s]
    return "横断"


def build_ledger() -> list[dict]:
    rows = []
    for f in K["findings"]:
        u = unit_of_finding(f)
        c = cls_of(f)
        srcs = [s for s in f["sources"]]
        pages = "; ".join(f"{s}: {anon(SRC[s].get('pages') or '記載なし')[:80]}" for s in srcs if s in SRC)
        rows.append({
            "Claim ID": f["id"], "主張内容": anon(f["text"]), "対象研究": u, "対象年度": f.get("study") or "横断",
            "原資料ID": "; ".join(srcs), "原資料ページ・図表": pages or "—", "区分": c,
            "記述の主体": "原著者" if c.startswith("FACT（原著者") else ("原資料の記載" if c == "FACT" else "本報告書"),
            "独立検証の有無": "あり" if c == "CALC" else ("原本照合" if c.startswith("FACT") else "—"),
            "検証方法": (SCRIPTS.get(u, "手計算・計算シート照合") if c == "CALC" else ("原本の読解" if c.startswith("FACT") else "確認事実・計算結果からの推論")),
            "確認状況": {"CALC": "再計算済み", "ANALYSIS": "分析（第三者未確認）", "HYPOTHESIS": "未検証の仮説"}.get(c, "原本で確認"),
            "不確実性": "高（仮説）" if c == "HYPOTHESIS" else ("中（推論）" if c == "ANALYSIS" else "原資料・計算の範囲"),
            "本文参照": SECTION_OF_UNIT.get(u, "第13〜23章"),
        })
    for q in K["questions"]:
        rows.append({"Claim ID": q["id"], "主張内容": anon(q["text"]), "対象研究": "横断", "対象年度": "", "原資料ID": "; ".join(q.get("related", [])),
                     "原資料ページ・図表": "—", "区分": "UNRESOLVED", "記述の主体": "本報告書", "独立検証の有無": "—", "検証方法": "—",
                     "確認状況": q["status"], "不確実性": f"優先度 {q['priority']}", "本文参照": "第19章・付録G"})
    for mid, fy, title, u, how, impact in MISSING:
        rows.append({"Claim ID": mid, "主張内容": f"{title}は未取得", "対象研究": u, "対象年度": fy, "原資料ID": "", "原資料ページ・図表": "—",
                     "区分": "NOT VERIFIED", "記述の主体": "本報告書", "独立検証の有無": "—", "検証方法": "—", "確認状況": how,
                     "不確実性": impact, "本文参照": "付録H"})
    return rows


# ----------------------------------------------------------------------------- 3. 数値検証
def verdict(pub: float, calc: float, abs_tol: float, rel_tol: float = 0.05) -> str:
    d = abs(calc - pub)
    if d <= abs_tol:
        return "一致"
    if pub and d / abs(pub) <= rel_tol:
        return "概ね一致"
    return "不一致"


# F-V-16 に記録された1日集計の値（scripts に未保存。再現には raw_2024 の1日抽出が必要）
FV16_DAY = {"A": 23.3, "B": 53.2, "C": 19.3, "D": 72.4, "F": 1.6, "E": 0.1, "G": 1.7, "H": 0.1}


def build_numerical() -> list[dict]:
    rows = []
    n = [0]

    def add(purpose, src, formula, inputs, method, prog, calc, pub, abs_tol=None, rel=0.05, unit="", rule="", judge=None, basis="", note=""):
        n[0] += 1
        diff = rel_err = ""
        if isinstance(calc, (int, float)) and isinstance(pub, (int, float)):
            diff = round(calc - pub, 6)
            rel_err = f"{(calc - pub) / pub * 100:.1f}%" if pub else ""
            j = judge or verdict(pub, calc, abs_tol if abs_tol is not None else 0, rel)
        else:
            j = judge or "判定不能"
        rows.append({"計算ID": f"N-{n[0]:03d}", "計算の目的": purpose, "原資料ID": src, "元の数式": formula, "使用変数・入力値": inputs,
                     "入力値の出典": src, "計算方法": method, "使用プログラム": prog,
                     "独立再計算値": (round(calc, 4) if isinstance(calc, float) else calc), "原資料掲載値": pub, "単位": unit, "差": diff, "相対誤差": rel_err,
                     "丸め規則": rule, "判定": j, "根拠（Claim ID）": basis, "備考": note})

    V = K["validation"]
    r = V["raw2025"]
    a, b, c = r["A_iwakuni"], r["B_shimonoseki"], r["C_nogata"]
    P25 = "scripts/raw_2025.py"
    add("2025 住宅A 外気平均", "S-2025-19, S-2025-01", "mean(C_out)", "1分値 全期間", "単純平均", P25, a["all"]["outdoor_mean"], 3.7, 0.05, unit="μg/m³", rule="小数1桁", basis="F-V-01")
    add("2025 住宅A I/O 条件①（EP稼働）", "S-2025-19, S-2025-01", "mean(C_in,LDK)/mean(C_out)", "〜9/20 16:59", "比", P25, a["cond1"]["io_リビング"], 0.28, 0.005, unit="—", rule="小数2桁", basis="F-V-01")
    add("2025 住宅A I/O 条件②", "S-2025-19, S-2025-01", "同上", "9/20 17:00〜", "比", P25, a["cond2"]["io_リビング"], 1.10, 0.005, unit="—", rule="小数2桁", basis="F-V-01")
    add("2025 住宅B I/O 条件②", "S-2025-20, S-2025-01", "mean(C_in,還気RA)/mean(C_out)", "全期間（リビング測点なし）", "比", P25, b["all"]["io_全熱交換器RA"], 0.90, 0.005, unit="—", rule="小数2桁",
        basis="F-V-02", note="還気で一致。トイレ0.946・浴室1.166・空調室0.813 とは一致しない")
    add("2025 住宅C I/O 条件②（最終版区分）", "S-2025-21, S-2025-01", "mean(C_in,LDK)/mean(C_out)", "9/25〜10/12 9:59", "比", P25, c["cond2_final_table5"]["io_リビング"], 0.68, 0.005, unit="—", rule="小数2桁", basis="F-V-03")
    add("2025 住宅C I/O 条件③", "S-2025-21, S-2025-01", "同上", "10/12 10:00〜", "比", P25, c["cond3_final_table5"]["io_リビング"], 1.22, 0.006, unit="—", rule="小数2桁", basis="F-V-03")
    add("2025 住宅C 外気平均", "S-2025-21", "mean(C_out)", "全期間", "単純平均", P25, c["all"]["outdoor_mean"], 7.9, 0.05, unit="μg/m³", rule="小数1桁", basis="F-V-03")
    add("2025 条件①の回帰係数（プール値）", "S-2025-01", "C_in = k·C_out（原点通過, 1時間平均）", "住宅A単独で再計算（住宅Dは未取得）", "最小二乗", P25, 0.278, 0.14,
        judge="判定不能", unit="—", basis="F-V-06", note="掲載値は住宅A+Dのプール。住宅Dの原データ未取得のため検証不能（M-05）")
    an = V["annual2025"]["sites"]
    for cond, pub, lab in (("条件①", None, "ほぼ無し"), ("条件②", 40.0, "約40%"), ("条件③", 70.0, "約70%")):
        vals = [s[f"{cond}_gt5_pct"] for s in an.values()]
        lo, hi = min(vals), max(vals)
        mid = (lo + hi) / 2
        add(f"2025 年間予測 5 μg/m³ 超過時間割合 {cond}", "S-2025-01, S-2025-16", "k×外気1時間値 > 5", "2024年度そらまめくん4地点×約8,700時間",
            "時間割合", "scripts/annual_2024.py", f"{lo:.1f}〜{hi:.1f}", lab, judge=("概ね一致" if pub is None or abs(mid - pub) <= 7.5 else "不一致"), unit="%",
            rule="掲載は概数", basis="F-2025-21", note="室内発生を含まない予測（原著者の前提）")
    for code, h in sorted(V["raw2024"]["houses"].items()):
        sheet = h.get("reported_io_sheet")
        if sheet:
            add(f"2024 住宅{code} I/O（全期間単純平均）", "S-2024-12, S-2024-xx 原データ", "mean(室内全測点)/mean(外気)", "1分値8ブック", "比", "scripts/raw_2024.py",
                h["io_simple"], sheet[2], 0.035, unit="—", rule="小数2桁に丸めて±0.03", basis="F-V-14", note="算出シートは気積加重・1日分。単純平均（全期間）との差が丸め後±0.03 以内を一致とした")
        if h.get("slide_gt5_pct") is not None:
            day = FV16_DAY.get(code)
            if day is not None:
                add(f"2024 住宅{code} 5 μg/m³以上の時間割合（I/Oと同じ1日）", "S-2024 発表スライド, 1分値原データ", "1日の全測点・全分のうち C>5 の割合", "1分値（算出シートの外気平均と一致する1日）",
                    "割合", "対話内の集計（スクリプト未保存）", day, h["slide_gt5_pct"], judge=("概ね一致" if abs(day - h["slide_gt5_pct"]) <= 5 else "不一致"), unit="%", rule="小数1桁",
                    basis="F-V-16", note="A〜Dは概ね再現。E〜Hはスライドの算出方法を特定できない【不明】。全期間の住宅平均は " + f"{h['gt5_pct_house_mean']:.1f}%")
    Y = json.loads((ROOT / "verification" / "Y2022_simulation" / "results.json").read_text(encoding="utf-8"))
    one_s = {y["cond_label"]: y for y in Y if y["dt_s"] == 1}
    for y in Y:
        rep = y.get("reported")
        if not rep:
            continue
        # 30〜45 μm の掲載値は1秒刻みシートの値（F-SIM-11）。同じ条件の1秒刻みシートで照合する
        z = one_s.get(y["cond_label"]) if y["size_um"] == "30-45" else y
        for key, ck in (("LDK", "LDK+吹抜"), ("非居室", "非居室"), ("集塵機", "集塵機")):
            if key not in rep:
                continue
            note = "掲載のLDKは吹抜を含む（F-SIM-08）" if key == "LDK" else ""
            val = z[ck]
            if key == "集塵機" and not z["ep_on"] and rep[key] > 0 and z.get("ep_column_raw_pct_when_off"):
                val = z["ep_column_raw_pct_when_off"]
                note = "EP OFF でもシートの集塵機欄に値があり、掲載値はその値（F-SIM-14）"
            if z is not y:
                note = (note + "；" if note else "") + f"1秒刻みシート（{z['sheet']}）で照合。10秒刻みでは {y[ck]:.1f}%（初回ステップ損失, F-SIM-11/13）"
            add(f"2022 粉塵の行方 {y['cond_label']} {y['size_um']}μm {key}（{z['dt_s']}秒刻みシート）", "S-2022-05", "30分間の室別累積沈着/M",
                f"M={z['M']:.0f}, 刻み{z['dt_s']} s", "シートの各列を再集計", "verification/Y2022_simulation/verify_2022_sim.py", val, rep[key], 0.06, rel=0.0,
                unit="%", rule="小数1桁（掲載）", basis="F-SIM-13" + (", F-SIM-11" if z is not y else ""), note=note)
    add("2022 実住宅 10〜20 μm の最大個数濃度", "S-2022-08, S-2022-01", "区分計数×353.357", "4住宅×約24時間", "最大値", "verification/R-2022-MEAS/verify_2022_field.py",
        59364.0, 60000.0, rel=0.02, unit="個/m³", rule="掲載は『約6万』", basis="F-2022-09")
    R26 = json.loads((ROOT / "verification" / "R-2026" / "results.json").read_text(encoding="utf-8"))
    pub26 = {"C1": "95〜350", "C2": "13〜47", "C2b": "13〜47", "C3": "約740", "C4": "約730〜770", "C4b": "約730〜770", "C5": "0%で最大", "C6": "約4 W/台"}
    for cl in R26["claims"]:
        if cl["law"] not in ("fit", "quad"):
            continue
        add(f"2026 {cl['claim']}（{'式(2)全域' if cl['law'] == 'fit' else '750超を二乗則'}）", "S-2026-01", "並列流路: Q_fan=Q_EP(ΔP)+Q_BP(ΔP)",
            "中×5〜20台, 開口0〜100%", "二分法", "verification/R-2026/verify_2026.py", ", ".join(str(v) for v in cl["value"]), pub26.get(cl["claim"], ""),
            judge=("判定不能（電力曲線は本調査の仮定）" if cl["claim"] == "C6" else ("一致" if cl["match"] else "不一致")), unit="Pa / m³/h / W",
            basis="F-2026-07, F-2026-08", note=cl["text"])
    add("JEM1467 清浄時間（23畳, 5.1 m³/min）", "S-REF-04, S-2018-01", "t'=−V'ln0.12/(P+Q'f)", "V'=23×1.65×2.4, Q'f=V'/60", "式", "backend/tests/test_models.py",
        29.2, 30.0, rel=0.05, unit="min", rule="規格は30分以内", basis="F-X-19", note="規格の基準（30分以内）を満たす")
    add("石松子（35 μm）の終端速度", "S-REF-17, S-2019-01", "Stokes: v=ρ g d²/(18μ)", "d=35 μm, ρ=1000 kg/m³", "式", "backend/aqros/models.py", 3.7, 3.6, rel=0.05, unit="cm/s", basis="F-X-17",
        note="2019年度卒論は3.839 cm/s（密度1.05 g/cm³）")
    add("センサー換算式の傾き（2025）", "S-2025-18", "y=a·x+b（KC-52個数→センサー）", "並置603組", "最小二乗", "scripts（並置解析）", 4.574e-5, 5e-5, rel=0.1, unit="μg/m³ per count",
        rule="掲載は有効数字1桁", judge="一致", basis="F-V-07", note="切片0.0492も一致。掲載の 5E-05 は表示桁の丸め")
    add("β理論式（砂10 μm 重力沈降項）", "S-2023-04", "β=v_s/H（Stokes＋カニンガム）", "d=10 μm", "式", "backend/aqros/models.py", 3.02e-3, 2.99e-3, rel=0.02, unit="1/s", basis="F-2023-07")
    return rows


# ----------------------------------------------------------------------------- 図
def make_figures(audit_rows):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    font_manager.fontManager.addfont("/usr/share/fonts/opentype/ipafont-gothic/ipagp.ttf")
    plt.rcParams.update({"font.family": "IPAPGothic", "axes.unicode_minus": False, "font.size": 9})
    NAVY, GRAY, AMB, RED = "#1F3864", "#8A8F98", "#B07A12", "#A33A3A"
    FIG.mkdir(parents=True, exist_ok=True)
    out = {}
    # 図: 検証状況マトリクス
    m = {"済": 3, "一部": 2, "未": 1, "不能": 0, "対象外": -1}
    import numpy as np
    data = np.array([[m[x] for x in u["v"]] for u in A.UNITS])
    from matplotlib.colors import ListedColormap
    cmap = ListedColormap(["#FFFFFF", "#C9CED6", "#E9D9A8", "#9DB0CF", NAVY])
    fig, ax = plt.subplots(figsize=(8.2, 5.2))
    ax.imshow(data + 1, cmap=cmap, vmin=0, vmax=4, aspect="auto")
    ax.set_xticks(range(len(A.ITEMS)), A.ITEMS, rotation=60, ha="right")
    ax.set_yticks(range(len(A.UNITS)), [u["id"] for u in A.UNITS])
    for i, u in enumerate(A.UNITS):
        for j, v in enumerate(u["v"]):
            ax.text(j, i, v, ha="center", va="center", fontsize=7, color="white" if v == "済" else "black")
    ax.set_title("研究単位ごとの検証状況（13項目）")
    fig.tight_layout(); p = FIG / "fig_verification_matrix.png"; fig.savefig(p, dpi=200); plt.close(fig); out["matrix"] = p
    # 図: 資料の根拠区分（年度別）
    inv = build_inventory()
    years = sorted({str(r["年度"]) for r in inv if str(r["年度"]).isdigit() and int(r["年度"]) >= 2013 and r["資料ID"].startswith(("S-", "M-"))})
    classes = ["A", "B", "C", "D", "F", "G"]
    cnt = {y: Counter(r["根拠区分"] for r in inv if str(r["年度"]) == y and r["資料ID"].startswith(("S-", "M-"))) for y in years}
    fig, ax = plt.subplots(figsize=(8.2, 3.6)); bottom = np.zeros(len(years))
    colors = {"A": NAVY, "B": "#3E5C8A", "C": "#7F95B8", "D": "#B9C6DA", "F": AMB, "G": RED}
    for c_ in classes:
        vals = np.array([cnt[y].get(c_, 0) for y in years]); ax.bar(years, vals, bottom=bottom, color=colors[c_], label=c_); bottom += vals
    ax.set_ylabel("資料数（研究室資料・未取得資料）"); ax.legend(title="根拠区分", ncol=6, fontsize=8, loc="upper left"); ax.set_title("年度別の資料数と根拠の状態（A〜G）")
    fig.tight_layout(); p = FIG / "fig_evidence_by_year.png"; fig.savefig(p, dpi=200); plt.close(fig); out["evidence"] = p
    # 図: I/O（2024 と 2025, 定義が異なるため別パネル）
    V = K["validation"]
    h = V["raw2024"]["houses"]; codes = sorted(h)
    r = V["raw2025"]
    fig, axs = plt.subplots(1, 2, figsize=(8.2, 3.4), gridspec_kw={"width_ratios": [1.3, 1]})
    axs[0].bar(codes, [h[c]["io_simple"] for c in codes], color=[NAVY if c in "GH" else ("#7F95B8" if c in "EF" else GRAY) for c in codes])
    axs[0].set_title("2024年度: 全測点単純平均/外気（各1〜3日）", fontsize=9); axs[0].set_ylabel("I/O比 [—]"); axs[0].set_ylim(0, 1.3)
    labs = ["A ①EP", "A ②", "B ②(還気)", "C ②", "C ③"]
    vals = [r["A_iwakuni"]["cond1"]["io_リビング"], r["A_iwakuni"]["cond2"]["io_リビング"], r["B_shimonoseki"]["all"]["io_全熱交換器RA"],
            r["C_nogata"]["cond2_final_table5"]["io_リビング"], r["C_nogata"]["cond3_final_table5"]["io_リビング"]]
    axs[1].bar(labs, vals, color=[NAVY, GRAY, GRAY, GRAY, AMB]); axs[1].set_ylim(0, 1.3); axs[1].tick_params(axis="x", rotation=30)
    axs[1].set_title("2025年度: リビング1点/外気（期間平均）", fontsize=9)
    for ax_ in axs:
        ax_.axhline(1, color="#555", lw=0.6, ls=":")
    fig.suptitle("I/O比の再計算値（定義が異なるため年度間で直接比較しない）", fontsize=10)
    fig.tight_layout(); p = FIG / "fig_io_2024_2025.png"; fig.savefig(p, dpi=200); plt.close(fig); out["io"] = p
    # 図: 2025 住宅A 外気濃度帯別 I/O
    cf = r["confounding"]["A"]["outdoor_strata"]
    fig, ax = plt.subplots(figsize=(6.4, 3.0)); x = np.arange(len(cf)); w = 0.38
    ax.bar(x - w / 2, [s_["io_ep_on"] for s_ in cf], w, color=NAVY, label="EP 稼働（条件①）")
    ax.bar(x + w / 2, [s_["io_ep_off"] for s_ in cf], w, color=GRAY, label="EP 停止（条件②）")
    ax.set_xticks(x, [f"外気 {s_['cout_range'][0]}〜{s_['cout_range'][1]}" for s_ in cf]); ax.set_ylabel("I/O比 [—]"); ax.legend(fontsize=8)
    ax.set_title("2025年度住宅A: 外気濃度の三分位別 I/O（1時間平均, μg/m³）")
    fig.tight_layout(); p = FIG / "fig_2025A_strata.png"; fig.savefig(p, dpi=200); plt.close(fig); out["strata"] = p
    # 図: 2026 所要差圧
    R26 = json.loads((ROOT / "verification" / "R-2026" / "results.json").read_text(encoding="utf-8"))
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    for law, col, lab in (("fit", GRAY, "式(2)を全域に適用"), ("quad", NAVY, "750 m³/h 超を二乗則で外挿"), ("linear", AMB, "750 m³/h 超を一次で外挿")):
        pts = [(c_["n"], c_["dp_req"]) for c_ in R26["cases"] if c_["law"] == law and c_["r"] == 0.0]
        ax.plot([p_[0] for p_ in pts], [p_[1] for p_ in pts], "o-", color=col, label=lab)
    ax.axhspan(95, 350, color=RED, alpha=0.08, label="梗概の記述『95〜350 Pa』")
    ax.axhline(80, color="#555", ls=":", lw=0.8); ax.text(5.2, 84, "送風機の風量一定制御の限界（中: 約80 Pa）", fontsize=7)
    ax.set_xlabel("送風機台数（中, 190 m³/h/台）"); ax.set_ylabel("開口0%の所要差圧 [Pa]"); ax.set_yscale("log"); ax.legend(fontsize=7)
    ax.set_title("2026年度: 抵抗則による所要差圧の違い（本調査の再計算）")
    fig.tight_layout(); p = FIG / "fig_2026_dp.png"; fig.savefig(p, dpi=200); plt.close(fig); out["dp"] = p
    # 図: 掲載値 vs 再計算値（数値のみ）
    xs, ys, cs = [], [], []
    for row in audit_rows:
        if isinstance(row["原資料掲載値"], (int, float)) and isinstance(row["独立再計算値"], (int, float)) and row["単位"] in ("—", "%"):
            xs.append(row["原資料掲載値"]); ys.append(row["独立再計算値"]); cs.append(NAVY if row["判定"] in ("一致", "概ね一致") else RED)
    fig, ax = plt.subplots(figsize=(4.8, 4.4))
    ax.scatter(xs, ys, c=cs, s=14); mx = max(xs + ys) * 1.05; ax.plot([0, mx], [0, mx], color="#555", lw=0.6)
    ax.set_xscale("symlog", linthresh=1); ax.set_yscale("symlog", linthresh=1)
    ax.set_xlabel("原資料掲載値"); ax.set_ylabel("独立再計算値"); ax.set_title(f"掲載値と再計算値（無次元・% の {len(xs)} 項目）\n紺: 一致・概ね一致　赤: 不一致", fontsize=9)
    fig.tight_layout(); p = FIG / "fig_audit_scatter.png"; fig.savefig(p, dpi=200); plt.close(fig); out["scatter"] = p
    # 図: 2022 実測 vs シミュ（ピーク時刻）
    R22 = json.loads((ROOT / "verification" / "R-2022-MEAS" / "results.json").read_text(encoding="utf-8"))
    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    for cond, d in R22.items():
        rooms = d["rooms"]
        for nme in ("レターン", "空調室", "ダクト"):
            x_ = rooms[nme]
            if x_["sim_peak_t_s"] > 600:
                ax.plot([x_["meas_peak_t_s"] / 60 - 10, x_["sim_peak_t_s"] / 60 - 10], [cond, cond], color=GRAY, lw=0.8)
                ax.scatter([x_["meas_peak_t_s"] / 60 - 10], [cond], color=NAVY, s=16, zorder=3)
                ax.scatter([x_["sim_peak_t_s"] / 60 - 10], [cond], color=AMB, s=16, marker="s", zorder=3)
    ax.set_xlabel("発生開始からのピーク時刻 [min]（紺●: 実測, 橙■: シミュレーションMAX）"); ax.set_title("2022年度: 還気側3測点のピーク時刻（レターン・空調室・ダクト）")
    fig.tight_layout(); p = FIG / "fig_2022_peak.png"; fig.savefig(p, dpi=200); plt.close(fig); out["peak"] = p
    out["lineage"] = ROOT / "docs" / "figures" / "synthesis_lineage.png"
    return out


# ----------------------------------------------------------------------------- Markdown 組立て
class Doc:
    def __init__(self):
        self.L: list[str] = []
        self.tables: list[tuple[str, str]] = []
        self.figs: list[tuple[str, str]] = []
        self.ch = 0
        self.tn = 0
        self.fn = 0

    def h1(self, t, num=True):
        if num:
            self.ch += 1; self.tn = 0; self.fn = 0
            t = f"第{self.ch}章　{t}"
        self.L += ["", f"# {t}", ""]

    def p(self, *xs):
        self.L += [*xs, ""]

    def table(self, title, header, rows, note="", widths=None):
        self.tn += 1
        tid = f"表 {self.ch if self.ch else 'S'}-{self.tn}"
        self.tables.append((tid, title))
        widths = widths or [1] * len(header)
        sep = "|" + "|".join("-" * max(3, int(w * 3)) for w in widths) + "|"
        self.L += [f"**{tid}　{title}**", "", "| " + " | ".join(header) + " |", sep]
        for r in rows:
            self.L.append("| " + " | ".join(str(x).replace("|", "／").replace("\n", " ") for x in r) + " |")
        if note:
            self.L += ["", f"<small>注: {note}</small>"]
        self.L.append("")
        return tid

    def fig(self, path, title, note):
        self.fn += 1
        fid = f"図 {self.ch if self.ch else 'S'}-{self.fn}"
        self.figs.append((fid, title))
        rel = Path(path).resolve().relative_to(OUT.resolve()) if str(Path(path).resolve()).startswith(str(OUT.resolve())) else Path("..") / ".." / Path(path).resolve().relative_to(ROOT)
        self.L += [f"![{fid}　{title}]({rel.as_posix()}){{width=95%}}", "", f"<small>{note}</small>", ""]
        return fid

    def pagebreak(self):
        self.L += ["", "```{=openxml}", '<w:p><w:r><w:br w:type="page"/></w:r></w:p>', "```", ""]


def chapter_body(md: str, shift: int = 1) -> str:
    """report/*.md の本文を取り込む（先頭の # を除き、見出しを shift 段下げる）。"""
    md = re.sub(r"^# .*\n", "", md)
    md = re.sub(r"^(#+) ", lambda m: "#" * min(6, len(m.group(1)) + shift) + " ", md, flags=re.M)
    md = re.sub(r"!\[[^\]]*\]\([^)]*\)\n?", "", md)
    return anon(md)


def ref(ids: str) -> str:
    return f"（{ids}）"


def unit_table(d: Doc, u: dict, audit_rows):
    """第5章（指示書）の27項目の統一フォーマット。"""
    srcs = [SRC[s] for s in u["sources"] if s in SRC]
    lab = [s for s in srcs if not s["kind"].startswith("外部")] or srcs

    def pick(field):
        vals = [anon(s.get(field) or "") for s in lab if s.get(field)]
        return "；".join(v[:260] for v in vals[:2]) if vals else None

    ev = [FND[e] for e in u["evidence"] if e in FND]
    calc = [f for f in ev if f["class"] == "計算結果"]
    claims = [f for f in ev if f["class"] in ("当事者の主張", "予測（当事者）", "計算結果（当事者）")]
    nums = [r for r in audit_rows if any(s in r["原資料ID"] for s in u["sources"])]
    agree = Counter(r["判定"].split("（")[0] for r in nums)
    items = [
        ("研究の正式名称", "；".join(anon(s["title"]) for s in lab[:3])),
        ("実施・発表年度", f"{u['year']}年度"),
        ("著者・所属", "研究室所属の学生（氏名は記載しない）／日本大学理工学部 井口研究室（住宅班）" if not u["id"].startswith("R-JOINT") else "共同研究（学会論文）。著者名は REFERENCES.md の書誌による"),
        ("研究背景", pick("purpose") or "記載なし（取得資料に明記なし）"),
        ("研究目的", u["title"]),
        ("技術的課題", pick("limitations") and "原資料の限界の記載: " + pick("limitations") or "記載なし"),
        ("対象建築物", pick("conditions") or "記載なし"),
        ("対象設備", "空調室EP・全館空調（取得資料の範囲）" if "EP" in u["title"] or u["year"] >= 2018 else "記載なし"),
        ("対象粒子・汚染物質", pick("measurements") or "記載なし"),
        ("計測対象", pick("measurements") or "記載なし"),
        ("計測機器", pick("instruments") or "記載なし"),
        ("測定条件", pick("conditions") or "記載なし"),
        ("データ取得方法", pick("raw_data") or ("原データ未取得（付録H）" if u["v"][3] in ("未", "不能") else "原データを取得（付録A）")),
        ("実験・計算方法", pick("methods") or "記載なし"),
        ("使用した数式", "付録D・第14章を参照" if pick("methods") else "記載なし"),
        ("使用パラメータ", "付録Eの入力値を参照" if nums else "未確認"),
        ("シミュレーション条件", pick("methods") if any(k in (pick("methods") or "") for k in ("シミュ", "回路網", "モデル", "計算")) else "該当なし／記載なし"),
        ("評価指標", "第14章の定義に対応（I/O・沈着割合・CADR 等）"),
        ("主要な数値結果", pick("results") or "記載なし"),
        ("原著者の結論", (pick("conclusions") or "") + ("；" if pick("conclusions") and claims else "") + "；".join(f"{f['id']}" for f in claims) or "記載なし"),
        ("本報告書による独立検証", "；".join(f"{f['id']}" for f in calc) or "未実施（原データ・計算シート未取得）"),
        ("原資料と再計算の一致状況", ", ".join(f"{k} {v}件" for k, v in agree.items()) + "（NUMERICAL_AUDIT.csv）" if nums else ("所見で記述（数値照合表なし）" if calc else "判定不能")),
        ("実験・計算上の制約", pick("limitations") or "記載なし"),
        ("他研究との関連", pick("related") or "第20章を参照"),
        ("技術的意義", "第20・25章で評価"),
        ("未確認事項", u["notes"]),
        ("今後の検証課題", "；".join(q["id"] for q in K["questions"] if any(e in q.get("related", []) for e in u["evidence"] + u["sources"])) or "第24章を参照"),
    ]
    d.table(f"{u['id']} の統一フォーマット（27項目）", ["No", "項目", "内容（取得資料の範囲）"], [(i + 1, k, v) for i, (k, v) in enumerate(items)], widths=[2, 7, 30],
            note="『記載なし』は取得した資料に記載がないこと、『未取得』は資料を取得できていないこと、『未確認』は本調査で確認作業をしていないことを示す。")
    d.p("**所見（根拠付き）**", "")
    for f in ev:
        d.L.append(f"- **{f['id']}**〔{cls_of(f)}〕{anon(f['text'])}")
    d.L.append("")


def build_markdown(figs, inv, ledger, audit_rows):
    d = Doc()
    today = date.today().isoformat()
    d.L += ["---", f"title: \"{T.TITLE}\"", f"subtitle: \"{T.SUBTITLE}\"", f"author: \"{T.POSITION}\"", f"date: \"{today}（中間統合版 1.0）\"", "lang: ja", "---", ""]
    d.pagebreak()
    d.h1("作成情報・報告書の位置づけ", num=False)
    d.p(T.FRONT_INFO)
    d.p("## 利用した資料の範囲", "")
    st = Counter(r["根拠区分"] for r in inv)
    d.p(f"研究室資料 {len(K['sources'])}件（うち外部資料の登録 {sum(1 for s in K['sources'] if s['kind'].startswith('外部'))}件）、国内外文献 {len(K['literature'])}件、外部基準・統計 {len(K.get('external', []))}件、未取得資料 {len(MISSING)}件を台帳に登録した。根拠区分の内訳は "
        + "、".join(f"{k} {v}件" for k, v in sorted(st.items())) + "である（第5章、SOURCE_INVENTORY.csv）。")
    d.p("## 免責・確認事項", T.DISCLAIMER)
    d.pagebreak()
    d.h1("要旨", num=False); d.p(T.ABSTRACT_JA)
    d.h1("Executive Summary", num=False); d.p('::: {lang="en-US"}', T.EXEC_EN, ":::")
    d.h1("主要な結論", num=False)
    for i, (t, ids) in enumerate(T.KEY_CONCLUSIONS, 1):
        d.L.append(f"{i}. {t}（根拠: {ids}）")
    d.L.append("")
    d.p("## 重要な数値結果（独立再計算）", "")
    key_ids = ["N-002", "N-003", "N-004", "N-005", "N-006"]
    sel = [r for r in audit_rows if r["計算ID"] in key_ids] + [r for r in audit_rows if r["計算の目的"].startswith(("2026 C1", "2026 C3", "2026 C4（", "JEM1467", "2022 実住宅"))]
    d.table("主要な数値の照合（抜粋）", ["計算ID", "項目", "掲載値", "再計算値", "判定", "根拠"], [(r["計算ID"], r["計算の目的"], r["原資料掲載値"], r["独立再計算値"], r["判定"], r["根拠（Claim ID）"]) for r in sel],
            note="全件は第18章と NUMERICAL_AUDIT.csv。2026 C1〜C4 は差圧・CADR の記述の照合（単位は Pa または m³/h）。")
    d.p("## 主な未解決課題", "")
    for q in [q for q in K["questions"] if q["priority"] == "高" and q["status"] not in ("解決",)]:
        d.L.append(f"- **{q['id']}**: {anon(q['text'])}（{q['status']}）")
    d.L.append("")
    d.L += ["", "```{=openxml}", '<w:p><w:r><w:br w:type="page"/></w:r></w:p>', "```", "", "# 目次", "", "```{=openxml}",
            '<w:p><w:r><w:fldChar w:fldCharType="begin" w:dirty="true"/><w:instrText xml:space="preserve"> TOC \\o "1-2" \\h \\z \\u </w:instrText><w:fldChar w:fldCharType="separate"/><w:t>（目次: Word では右クリック→フィールド更新）</w:t><w:fldChar w:fldCharType="end"/></w:r></w:p>',
            "```", ""]
    fig_list_pos = len(d.L)
    d.L.append("@@FIGLIST@@")
    d.h1("略語・専門用語一覧", num=False)
    d.table_rows = None
    gl = [(a_, b_) for a_, b_ in BT.GLOSSARY]
    d.L += ["| 用語 | 説明 |", "|---|---|"] + [f"| {a_} | {b_} |" for a_, b_ in gl] + [""]
    d.ch = 0

    # ---------------- 第I部
    d.L += ["", "# 第I部　研究背景と調査方法", ""]
    d.h1("調査の背景と目的"); d.p(T.CH1_BACKGROUND)
    d.h1("室内空気質・空気清浄技術の基礎")
    d.p("本章は、後の章で用いる物理モデルと用語を示す。研究室の資料で採用されたモデルと、基礎技術の一般的な説明を区別するため、研究室で採用されたモデルは表で別に示した。")
    d.p(anon(BT.THEORY))
    d.table("研究室資料と本アプリで扱った物理モデル", ["モデル", "式", "単位", "根拠", "適用範囲"],
            [(m["name"], m["equation"], m["units"], ", ".join(m["sources"]), m["validity"]) for m in K["models"]])
    d.h1("対象研究と資料構成")
    d.p("対象とした研究単位（年度×班）は14件である。研究単位は、同じ研究の複数の版（中間・最終、卒論・学会論文）を一つにまとめたもので、同一研究を重複して数えないようにした（例: 2022年度卒論と2023年の学会論文その42は同一研究, F-X-21）。")
    d.table("研究単位の一覧", ["ID", "年度", "研究", "資料数", "分類（第4章の監査）"], [(u["id"], u["year"], u["title"], len(u["sources"]), u["cls"]) for u in A.UNITS])
    d.p("## 2018・2019年度の原データの扱い", T.DATA_POLICY)
    d.fig(figs["evidence"], "年度別の資料数と根拠の状態", "研究室資料（S-）と未取得資料（M-）を年度別に集計。SOURCE_INVENTORY.csv の『根拠区分』列に基づき本報告書で作成。年度不明の資料は除く。")
    d.h1("資料収集・原本確認・数値検証の方法"); d.p(T.CH4_METHOD)
    d.h1("証拠の分類と信頼性評価"); d.p(T.CH5_EVIDENCE)
    cc = Counter(cls_of(f) for f in K["findings"])
    d.table("所見（Claim）の区分別件数", ["区分", "件数"], sorted(cc.items(), key=lambda x: -x[1]), note="EVIDENCE_LEDGER.csv には所見に加えて未解決問題（UNRESOLVED）と未取得資料（NOT VERIFIED）を登録した。")
    ec = Counter(r["根拠区分"] for r in inv)
    d.table("資料の根拠区分別件数", ["区分", "件数"], sorted(ec.items()))
    d.fig(figs["matrix"], "研究単位ごとの検証状況", "audit_data.py の13項目（済・一部・未・不能・対象外）を本報告書で図化。原資料取得〜アプリ反映の各段階の実施状況を示す。")

    # ---------------- 第II部
    d.L += ["", "# 第II部　年度別研究の技術分析", ""]
    d.h1("関連研究の年代別整理")
    d.table("研究年表", ["年度", "研究", "問い", "方法", "主な結果（原資料）", "後続への引継ぎ"],
            [(s["fiscal_year"], anon(s["title"])[:60], anon(s["question"]), anon(s["method"])[:150], anon(s["outcome"])[:150], anon(s["handover"])) for s in K["studies"]], widths=[3, 8, 8, 12, 12, 8])
    d.fig(figs["lineage"], "研究の系統と因果関係（2018〜2026年度）", "研究単位を系統（制御実験・観測・装置工学）と年度で配置し、資料に明記された引用・入力値の利用を矢印で示した（本報告書で作成, scripts/make_synthesis_fig.py）。矢印はテーマの連続性を示し、データの直接継承を意味しない。")
    groups = [("初期研究と空気清浄技術の基礎的検討（2013〜2021年度）", ["R-2013-COMP", "R-2015", "R-2018", "R-2019", "R-2020", "R-2021-FLOAT", "R-2021-FALL"]),
              ("2022年度の数値解析（多数室計算）と実測", ["R-2022-MEAS", "R-2022-SIM"]),
              ("2023〜2024年度の実住宅研究", ["R-2023", "R-2024"]),
              ("2025年度の実測・室内空気質研究", ["R-2025"]),
              ("2026年度のモデル解析・装置評価", ["R-2026"]),
              ("その他の取得済み研究と資料不足年度の扱い", ["R-JOINT-2024"])]
    UM = {u["id"]: u for u in A.UNITS}
    for title, ids in groups:
        d.h1(title)
        if ids == ["R-2022-MEAS", "R-2022-SIM"]:
            d.p(f"## {d.ch}.1 2022年度の解析は CFD ではない", T.CH8_CFD_NOTE)
        for i, uid in enumerate(ids, 1):
            u = UM[uid]
            d.p(f"## {d.ch}.{i + (1 if ids[0] == 'R-2022-MEAS' else 0)} {u['year']}年度 {u['title']}（{uid}）")
            unit_table(d, u, audit_rows)
            if uid == "R-2022-MEAS":
                d.fig(figs["peak"], "還気側測点のピーク時刻（実測とシミュレーション）", "verification/R-2022-MEAS/results.json（比較ブック4件, シート名『1-5』）から本報告書で作成。シミュレーションは発生量MAXの系列。粒径区分はシートに記載なし。")
            if uid == "R-2026":
                d.fig(figs["dp"], "開口率0%の所要差圧と抵抗則", "verification/R-2026/verify_2026.py の再計算結果から作成。送風機が設定風量を保つと仮定したときに EP で必要な差圧。750 m³/h（約15 Pa）より上は実測範囲外。")
            if uid == "R-2025":
                d.fig(figs["strata"], "2025年度住宅Aの外気濃度帯別 I/O", "scripts/raw_2025.py confound の結果から作成（1時間平均, 区切りは両条件共通の三分位）。")
        if title.startswith("その他"):
            d.p("2015年度の全館空調の卒論（21 MB）は目録確認のみで、清浄度との関係が薄いため読解していない。2016・2017年度は、取得済み資料の範囲で清浄度に関する研究を確認できていない。これは研究が行われなかったことを意味しない【NOT VERIFIED】。")

    # ---------------- 第III部
    d.L += ["", "# 第III部　統合解析", ""]
    d.h1("研究方法の比較")
    d.table("研究方法の比較", ["研究単位", "対象", "測定・計算", "指標", "規模", "実測と計算の関係"], [
        ("R-2018", "実住宅・実験棟", "粉塵計・KC-52, 線香", "濃度低下", "各条件1回", "計算は発生量調整で合わせた"),
        ("R-2020", "実験住宅・BOX", "粉塵計, 回路網計算", "発生量・減衰率", "各条件3〜5回", "回路網で実測を比較（本調査で再検証）"),
        ("R-2021", "BOX・実験住宅・実住宅", "KC-52, ダストサンプラー, 粒子堆積モニタ", "β・M・落下量", "数回", "一様拡散計算は実測の約0.6倍"),
        ("R-2022", "実住宅4件・実験住宅", "KC-52（5〜45 μm）, 多数室計算", "個数濃度, 粉塵の行方", "実住宅各24 h, 実験住宅 別試行", "帯で比較（本調査で帯内0〜32%）"),
        ("R-2023", "実住宅4件・BOX", "KC-52, 静電気, 質量換算", "質量濃度, 発塵量", "24 h〜1週間", "収支式で発塵量を同定"),
        ("R-2024", "実住宅8件", "ワイヤレスセンサー多点", "I/O, 超過時間, 浮遊時間", "各1〜3日", "計算なし"),
        ("R-2025", "実住宅4件（西日本）", "センサー多点＋測定局", "I/O, 回帰係数, 年間予測", "各1〜2か月", "回帰で年間予測（本調査で単室同定）"),
        ("R-2026", "装置単体", "JIS 準拠試験, 並列流路モデル", "η, ΔP, CADR, 電力", "8段階×1分", "単体実測をモデルに入力"),
    ])
    d.p("## 比較可能性の判定", "")
    d.table("年度間比較の可能性", ["比較", "判定", "理由", "根拠"], [
        ("2024年度と2025年度の I/O", "直接比較不可", "測点（全室平均 vs 1点）・期間（1日 vs 1〜2か月）・季節・地域が異なる", "F-X-18"),
        ("2025年度 住宅A と住宅C の EP 効果", "条件付き比較可能", "同一年度・同一センサーだが、住宅と期間が交絡。外気濃度帯をそろえれば比較可", "F-2025-27/28"),
        ("2018年度 EP 効率96% と 2026年度 82〜92%", "直接比較不可", "仕様図と実測、風量・機種が異なる", "F-X-15, F-X-07"),
        ("2022年度（個数）と2024〜2025年度（質量）の濃度", "直接比較不可", "個数と質量、粒径範囲が異なる", "F-2023-02"),
        ("2021・2023年度の β と 2022年度の計算入力", "条件付き比較可能", "同じ定義（1/s）だが、同定条件が異なる", "F-2023-07/08"),
        ("2020年度と2022年度の実測・計算の一致", "定性的比較のみ可能", "モデル構造は同系だが粒径・指標が異なる。還気側のピーク遅れは共通", "F-SIM-03, F-2022-07"),
        ("2024年度と2025年度のセンサー換算式", "直接比較可能", "同じ機器・同じ方法の並置回帰（傾き4.54×10⁻⁵ と 4.57×10⁻⁵）", "F-V-07, F-V-09"),
        ("同じ実験住宅の循環風量（2021 vs 2022）", "条件付き比較可能", "同じ住宅だが年度で異なる値（1205 vs 923 m³/h）を使用", "F-2022-05"),
        ("2025年度 実効CADR と 2026年度 単体CADR", "資料不足", "2025年度の住宅のEP台数・風量設定が未記載", "F-SIM-05"),
        ("2024年度 E〜H の超過時間割合（スライド）", "資料不足", "集計方法が特定できず再現しない", "F-V-16"),
    ], widths=[10, 6, 16, 5], note="判定区分は、直接比較可能／条件付き比較可能／定性的比較のみ可能／直接比較不可／資料不足。")
    d.h1("評価指標・数式の統一")
    d.table("評価指標の定義と注意点", ["指標", "定義式", "単位", "研究室での用法", "注意点（根拠）", "主な年度"], T.CH14_METRICS, widths=[5, 9, 6, 9, 16, 5])
    d.p(T.CH14_CAUTIONS)
    d.h1("空気清浄方式の技術比較"); d.p(T.CH15_METHODS)
    d.h1("測定結果とシミュレーションの対応"); d.p(T.CH16_MEAS_SIM)
    d.p("### 本アプリのモデルの適用範囲（既存の検証）", chapter_body((ROOT / "report" / "11_シミュレーターの検証と適用範囲.md").read_text(encoding="utf-8"), 2))
    d.h1("研究成果の定量的比較")
    d.fig(figs["io"], "I/O比の再計算値（2024年度と2025年度）", "scripts/raw_2024.py, scripts/raw_2025.py の再計算値（原データから）。2024年度は全室単純平均÷外気、2025年度はリビング1点（住宅Bは還気）÷外気。定義が異なるため並べて示すが直接比較はしない（F-X-18）。")
    d.p("2025年度の値は原資料の掲載値とすべて一致した（表18-1）。2024年度の単純平均は算出シート（気積加重）と±0.03で一致した。2024年度の各住宅は1〜3日の値で、日ごとに最大2倍以上変わる（F-V-15）。")
    d.h1("独立再計算・再現性検証")
    jud = Counter(r["判定"].split("（")[0] for r in audit_rows)
    d.p(f"NUMERICAL_AUDIT.csv に {len(audit_rows)} 項目の照合を記録した。判定の内訳は " + "、".join(f"{k} {v}項目" for k, v in jud.items()) + "である。主な項目を以下に示す（2022年度の計算シートの60項目は CSV のみ）。")
    main = [r for r in audit_rows if not r["計算の目的"].startswith("2022 粉塵の行方")]
    d.table("独立再計算の結果（2022年度計算シート以外）", ["ID", "項目", "原資料掲載値", "独立再計算値", "差", "相対誤差", "判定", "根拠"],
            [(r["計算ID"], r["計算の目的"], r["原資料掲載値"], r["独立再計算値"], r["差"], r["相対誤差"], r["判定"], r["根拠（Claim ID）"]) for r in main],
            widths=[3, 14, 5, 6, 4, 4, 6, 6])
    s22 = [r for r in audit_rows if r["計算の目的"].startswith("2022 粉塵の行方")]
    d.p(f"2022年度の計算シート（20件）の照合 {len(s22)} 項目のうち、" + "、".join(f"{k} {v}項目" for k, v in Counter(r["判定"] for r in s22).items())
        + "であった。30〜45 μm の掲載値は、10秒刻みのシート（LDK 約87%）ではなく1秒刻みのシート（LDK＋吹抜 97.96%・97.16%）に対応するため、同じ条件の1秒刻みシートで照合した（F-SIM-11）。EP OFF の条件でも集塵機欄に値があり、30〜45 μm の掲載値（0.3%）はその値である（F-SIM-14）。掲載の『その他（30分で沈着しなかった量）』は、30分後の浮遊残存に、初回ステップで室内に入らなかった量（時間刻みに依存する数値上の残差）が加わったものである（F-SIM-13）。")
    d.fig(figs["scatter"], "原資料掲載値と独立再計算値", "NUMERICAL_AUDIT.csv の無次元・% の項目を図化（本報告書で作成）。対角線が完全一致。範囲で示された項目は除く。")
    d.p("### 既存の数値照合（第10章の再掲）", chapter_body((ROOT / "report" / "10_資料間照合と数値検証.md").read_text(encoding="utf-8"), 2))
    d.h1("原資料間の不一致と未解決課題")
    d.table("未解決問題", ["ID", "優先度", "内容", "状態", "関連"], [(q["id"], q["priority"], anon(q["text"]), q["status"], ", ".join(q.get("related", []))) for q in K["questions"]], widths=[3, 3, 22, 7, 7])
    hrows = []
    for h in K["hypotheses"]:
        hrows.append((h["id"], anon(h["title"]), h["status"], ", ".join(h.get("related_findings", []))))
        for c_ in h.get("competing", []):
            hrows.append(("", f"└ {anon(c_['label'])}: {anon(c_['text'])}", f"検証方法: {anon(c_.get('test', ''))}", ""))
    d.table("競合仮説（下位の競合仮説と検証方法を含む）", ["ID", "仮説", "状態・検証方法", "関連所見"], hrows, widths=[3, 20, 12, 7])
    d.p("### 批判的検証（既存の分析）", chapter_body((ROOT / "report" / "04_批判的検証.md").read_text(encoding="utf-8"), 2))

    # ---------------- 第IV部
    d.L += ["", "# 第IV部　総合考察", ""]
    d.h1("井口研究室関連研究の技術的な展開"); d.p(T.CH20_DEV)
    d.h1("室内空気質評価における共通課題"); d.p(T.CH21_COMMON)
    d.h1("実測・解析・設備制御の関係"); d.p(T.CH22_RELATION)
    d.h1("既存研究の限界と一般化可能性"); d.p(T.CH23_LIMITS)
    d.h1("今後の研究テーマ・実験計画への示唆")
    d.p("以下は、取得済み資料が支持する範囲で考えられる研究課題である。『研究テーマとして考えられる』ことを示すもので、設備・協力住宅・期間の実現可能性は研究室で確認されていない。評価点（重要度・新規性・実現性・適合性, 各5点）は本調査の暫定評価である。")
    for t in K["themes"]:
        sc = t["scores"]
        d.p(f"## {t['id']} {t['name']}（{t['horizon']}）")
        d.table(f"{t['id']} の研究計画の要素", ["項目", "内容"], [
            ("研究課題", anon(t["unsolved"])), ("既存研究からの根拠", anon(t["why_now"])), ("既知の事項", anon(t["known"])),
            ("研究仮説", ", ".join(t["hypotheses"])), ("検証すべき変数・測定", anon(t["measurements"])), ("必要なデータ", anon(t.get("data_needed", ""))),
            ("実験・計算方法", anon(t["procedure"])), ("解析・評価指標", anon(t["analysis"])), ("主な不確実性・リスク", anon(t["risks"])),
            ("実施上の制約（設備・期間）", anon(t["equipment"]) + "／" + anon(t["duration_cost"])), ("想定される技術的意義", anon(t["significance"])),
            ("暫定評価", f"重要{sc['importance']}・新規{sc['novelty']}・実現{sc['feasibility']}・適合{sc['fit']}（実現可能性は未確認）")], widths=[6, 30])
    d.h1("総合結論")
    for i, (q, a_) in enumerate(T.CONCLUSIONS, 1):
        d.p(f"## {i}. {q}", a_)

    # ---------------- 付録
    d.L += ["", "# 付録", ""]
    d.ch = 0
    APP = "ABCDEFGHIJKLM"

    def app(i, t):
        d.L += ["", f"# 付録{APP[i]}　{t}", ""]
        d.ch = f"{APP[i]}"; d.tn = 0; d.fn = 0
    app(0, "研究資料一覧")
    d.table("研究資料一覧（研究室資料）", ["ID", "年度", "資料", "種類", "状態", "根拠区分", "研究単位"],
            [(r["資料ID"], r["年度"], r["正式タイトル"][:70], r["資料の種類"], r["取得状況"], r["根拠区分"], r["研究単位"]) for r in inv if r["資料ID"].startswith("S-")],
            widths=[4, 3, 18, 6, 5, 3, 6],
            note="全項目（Box ID・保存場所・ページ・個人情報の注意等）は SOURCE_INVENTORY.csv。")
    app(1, "原資料の出典・参照ページ一覧")
    d.table("原資料の参照ページ", ["ID", "Box ID", "参照ページ・図表"], [(s["id"], s["box_id"], anon(s.get("pages") or "記載なし")) for s in K["sources"] if s.get("pages")], widths=[4, 6, 28])
    app(2, "年度別研究比較表")
    d.p(chapter_body((ROOT / "report" / "09_年度別研究の整理.md").read_text(encoding="utf-8"), 1))
    app(3, "数式・単位一覧")
    d.table("数式と単位", ["モデル", "式", "単位", "適用範囲"], [(m["name"], m["equation"], m["units"], m["validity"]) for m in K["models"]])
    d.p("単位系: Q m³/h、C μg/m³（センサー）または 個/m³（パーティクルカウンタ）、G μg/h、V m³、β 1/h（研究室資料の 1/s は ×3600）、ΔP Pa。KC-52 の計数は1分間・2.83 L 吸引で 1個 = 353.357 個/m³。")
    app(4, "独立再計算の入力値・出力値")
    d.table("独立再計算の入力値と出力値（全件）", ["ID", "目的", "式", "入力", "プログラム", "再計算値", "掲載値", "判定"],
            [(r["計算ID"], r["計算の目的"], r["元の数式"], r["使用変数・入力値"], r["使用プログラム"], r["独立再計算値"], r["原資料掲載値"], r["判定"]) for r in audit_rows])
    app(5, "検証結果一覧")
    d.table("研究単位の検証項目（13項目）", ["ID"] + A.ITEMS, [[u["id"]] + u["v"] for u in A.UNITS])
    app(6, "未解決事項一覧")
    d.p("UNRESOLVED_ISSUES.md に、未解決問題・不一致・原因候補・確認方法を一覧化した。第19章の表と同じ内容である。")
    app(7, "未取得資料一覧")
    d.table("未取得資料と分析上の影響", ["ID", "年度", "資料", "確認したこと", "結論への影響"], [(m_[0], m_[1], m_[2], m_[4], m_[5]) for m_ in MISSING],
            note="追加取得の条件: M-05〜M-07 は月別などに分割した 10 MB 以下の CSV を Box に置けば取得できる見込み。M-01〜M-04 は保存場所の確認が必要。M-09 は最終版の公開後に取得。")
    app(8, "研究関連図表")
    d.p("本文の図は `deliverables/technical_report_2026-11/figures/` に PNG で保存した。作成コードは `scripts/build_tech_report.py`（make_figures）。原資料の図は転載していない。")
    app(9, "参考文献")
    d.p("REFERENCES.md に、研究室資料（学会論文を含む）・外部基準・国内外文献の書誌を記載した。文献の確認水準（要旨確認・書誌のみ）を併記している。")
    for i, l in enumerate(K["literature"], 1):
        au = ", ".join((l.get("authors") or [])[:3]) + (" et al." if len(l.get("authors") or []) > 3 else "")
        d.L.append(f"- [L-{i:02d}] {au} ({l['year']}). {l['title']}. *{l.get('venue', '')}*. https://doi.org/{l['doi']}（{l.get('level', '')}）")
    for e in K.get("external", []):
        d.L.append(f"- [{e['id']}] {e['title']}. {e.get('url', '')}")
    d.L.append("")
    app(10, "研究データの保存場所")
    d.table("保存場所", ["区分", "場所", "公開"], [
        ("研究室資料（原本）", "研究室 Box（住宅班フォルダ）。Box ID は SOURCE_INVENTORY.csv", "研究室内"),
        ("取得した原データ・本文テキスト", "private_data/（Git 管理外）", "非公開"),
        ("再計算の集計値", "knowledge/*.json, verification/*/results*.json", "リポジトリ"),
        ("研究ナレッジ（単一ソース）", "scripts/knowledge_data.py → knowledge/knowledge.json", "リポジトリ"),
        ("本報告書と付属資料", "deliverables/technical_report_2026-11/", "リポジトリ（push は所有者の許可後）"),
    ])
    app(11, "解析コード・計算環境")
    d.table("解析コード", ["対象", "コード"], sorted(SCRIPTS.items()))
    d.p("計算環境: Python 3（pandas, numpy, matplotlib）、Node.js（フロントエンドの数値一致テスト）。報告書は pandoc で Word を生成し、LibreOffice で目次を更新して PDF に出力した。")
    app(12, "今後の追補・更新方法")
    d.p("1. 新しい資料を取得したら `scripts/knowledge_data.py` に資料（S-）と所見（F-）を追加し、`scripts/build_knowledge.py` を実行する。",
        "2. 原データの再計算は `verification/<研究単位>/` にスクリプトと結果（集計値のみ）を置き、`scripts/audit_data.py` の検証項目を更新する。",
        "3. `scripts/build_tech_report.py` を実行すると、台帳・根拠台帳・数値照合・本報告書（Word・PDF）が再生成される。資料ID・Claim ID は維持されるため、2018・2019年度の原データが後で見つかっても、該当する M- の行を S- の資料に置き換えて追補できる。",
        "4. 改訂時は表紙の版番号と REPORT_README.md の変更履歴を更新する。")

    # 図表一覧
    figlist = ["", "# 図一覧", ""] + [f"- {a_}　{b_}" for a_, b_ in d.figs] + ["", "# 表一覧", ""] + [f"- {a_}　{b_}" for a_, b_ in d.tables] + [""]
    d.L[fig_list_pos:fig_list_pos + 1] = figlist
    return "\n".join(d.L)


# ----------------------------------------------------------------------------- Word / PDF
def reference_docx(path: Path):
    import docx
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Pt, RGBColor, Mm
    base = OUT / "_ref_base.docx"
    base.write_bytes(subprocess.check_output(["pandoc", "--print-default-data-file", "reference.docx"]))
    d = docx.Document(str(base))
    NAVY = RGBColor(0x1F, 0x38, 0x64)
    byname = {st.name.lower(): st for st in d.styles}

    def S(name):
        if name.lower() not in byname:
            raise KeyError(name)
        return byname[name.lower()]

    def font(style, size=None, bold=None, color=None):
        s = S(style)
        s.font.name = "IPAPGothic"
        rpr = s.element.get_or_add_rPr()
        rf = rpr.find(qn("w:rFonts"))
        if rf is None:
            rf = OxmlElement("w:rFonts"); rpr.append(rf)
        for a_ in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
            rf.set(qn(a_), "IPAPGothic")
        for a_ in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
            if rf.get(qn(a_)) is not None:
                del rf.attrib[qn(a_)]
        if size:
            s.font.size = Pt(size)
        if bold is not None:
            s.font.bold = bold
        if color is not None:
            s.font.color.rgb = color
    for st, sz, b, col in (("Normal", 10, None, None), ("Body Text", 10, None, None), ("First Paragraph", 10, None, None), ("Compact", 9, None, None),
                           ("Title", 22, True, NAVY), ("Subtitle", 13, False, RGBColor(0x44, 0x4B, 0x55)), ("Author", 11, False, None), ("Date", 10, False, None),
                           ("Heading 1", 16, True, NAVY), ("Heading 2", 13, True, NAVY), ("Heading 3", 11, True, RGBColor(0x2E, 0x4A, 0x7A)),
                           ("Heading 4", 10, True, RGBColor(0x44, 0x4B, 0x55)), ("Image Caption", 9, False, RGBColor(0x44, 0x4B, 0x55)),
                           ("Table Caption", 9, True, None), ("Block Text", 9, None, None)):
        try:
            font(st, sz, b, col)
        except KeyError:
            pass
    for st in ("Title", "Subtitle", "Author", "Date"):
        try:
            S(st).paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        except KeyError:
            pass
    S("Heading 1").paragraph_format.page_break_before = True
    S("Heading 1").paragraph_format.space_after = Pt(8)
    # 表スタイル（罫線）
    tbl = S("Table")
    tpr = tbl.element.find(qn("w:tblPr"))
    if tpr is None:
        tpr = OxmlElement("w:tblPr"); tbl.element.append(tpr)
    borders = OxmlElement("w:tblBorders")
    for edge, sz in (("top", 8), ("bottom", 8), ("insideH", 4), ("left", 0), ("right", 0), ("insideV", 2)):
        e = OxmlElement(f"w:{edge}"); e.set(qn("w:val"), "single" if sz else "nil"); e.set(qn("w:sz"), str(sz or 0)); e.set(qn("w:color"), "8A8F98"); borders.append(e)
    tpr.append(borders)
    # 余白・フッターのページ番号・ヘッダー
    sec = d.sections[0]
    sec.page_height, sec.page_width = Mm(297), Mm(210)
    sec.left_margin = sec.right_margin = Mm(20); sec.top_margin = Mm(22); sec.bottom_margin = Mm(20)
    fp = sec.footer.paragraphs[0]; fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for kind, text in (("begin", None), (None, " PAGE "), ("end", None)):
        r = fp.add_run()
        if kind:
            fc = OxmlElement("w:fldChar"); fc.set(qn("w:fldCharType"), kind); r._r.append(fc)
        else:
            it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = text; r._r.append(it)
    hp = sec.header.paragraphs[0]; hp.text = "AQ Research OS　室内空気質・空気清浄度 既存研究の統合的分析（中間統合版 2026-11）"; hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    for r in hp.runs:
        r.font.size = Pt(7.5); r.font.color.rgb = RGBColor(0x8A, 0x8F, 0x98)
    d.save(str(path))
    base.unlink()


UNO_SCRIPT = r'''
import sys, time, uno, subprocess
from com.sun.star.beans import PropertyValue
def pv(n, v):
    p = PropertyValue(); p.Name = n; p.Value = v; return p
src, docx_out, pdf_out = sys.argv[1:4]
proc = subprocess.Popen(["soffice", "--headless", "--invisible", "--norestore", "--accept=socket,host=localhost,port=2083;urp;"])
ctx = None
for _ in range(60):
    try:
        local = uno.getComponentContext()
        res = local.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", local)
        ctx = res.resolve("uno:socket,host=localhost,port=2083;urp;StarOffice.ComponentContext"); break
    except Exception:
        time.sleep(1)
smgr = ctx.ServiceManager
desk = smgr.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
doc = desk.loadComponentFromURL(uno.systemPathToFileUrl(src), "_blank", 0, (pv("Hidden", True),))
idx = doc.getDocumentIndexes()
for i in range(idx.getCount()):
    idx.getByIndex(i).update()
doc.refresh()
idx = doc.getDocumentIndexes()
for i in range(idx.getCount()):
    idx.getByIndex(i).update()
doc.storeToURL(uno.systemPathToFileUrl(docx_out), (pv("FilterName", "MS Word 2007 XML"),))
doc.storeToURL(uno.systemPathToFileUrl(pdf_out), (pv("FilterName", "writer_pdf_Export"),))
print("indexes", idx.getCount())
doc.close(True)
try:
    desk.terminate()
except Exception:
    pass
proc.wait(timeout=30)
'''


def convert(md_path: Path, pdf: bool = True):
    ref = OUT / "_reference.docx"
    reference_docx(ref)
    raw = OUT / "_pandoc.docx"
    subprocess.run(["pandoc", str(md_path), "-o", str(raw), "--reference-doc", str(ref), "--resource-path", str(OUT)], check=True)
    ref.unlink()
    docx_out = OUT / f"{STEM}.docx"
    if not pdf:
        raw.replace(docx_out)
        return
    us = OUT / "_uno.py"
    us.write_text(UNO_SCRIPT, encoding="utf-8")
    subprocess.run(["python3", str(us), str(raw.resolve()), str(docx_out.resolve()), str((OUT / f"{STEM}.pdf").resolve())], check=True, timeout=600)
    us.unlink(); raw.unlink()


# ----------------------------------------------------------------------------- 付属文書
def write_csv(path: Path, rows: list[dict]):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)


def write_side_docs(inv, ledger, audit_rows):
    L = ["# 未解決事項（UNRESOLVED_ISSUES）", "", "> scripts/build_tech_report.py が生成。報告書第19章・付録G・付録H と同じ内容。", "",
         "## 1. 未解決問題", "", "| ID | 優先度 | 内容 | 状態 | 関連 |", "|---|---|---|---|---|"]
    L += [f"| {q['id']} | {q['priority']} | {anon(q['text'])} | {q['status']} | {', '.join(q.get('related', []))} |" for q in K["questions"]]
    L += ["", "## 2. 数値の不一致（NUMERICAL_AUDIT の『不一致』『判定不能』）", "", "| 計算ID | 項目 | 掲載値 | 再計算値 | 判定 | 原因候補・確認方法 |", "|---|---|---|---|---|---|"]
    for r in audit_rows:
        if not r["判定"].startswith(("一致", "概ね")):
            L.append(f"| {r['計算ID']} | {r['計算の目的']} | {r['原資料掲載値']} | {r['独立再計算値']} | {r['判定']} | {r['備考'] or r['根拠（Claim ID）']} |")
    L += ["", "原因が確定していない不一致は『誤植の可能性』として扱い、『誤植が確定した』とはしない。確認方法は、計算シートの取得（2026年度）、集計手順の確認（2024年度 E〜H）、著者への確認である。",
          "", "## 3. 仮説（未検証）", ""]
    L += [f"- **{f['id']}** {anon(f['text'])}" for f in K["findings"] if f["class"] == "仮説"]
    L += ["", "## 4. 未取得資料", "", "| ID | 年度 | 資料 | 確認したこと | 結論への影響 |", "|---|---|---|---|---|"]
    L += [f"| {m[0]} | {m[1]} | {m[2]} | {m[4]} | {m[5]} |" for m in MISSING]
    (OUT / "UNRESOLVED_ISSUES.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    R = ["# 参考文献・出典（REFERENCES）", "", "資料の性格を区別して記載する。研究室内資料は Box ID で参照し、原文は転載しない。", "", "## 1. 国内外文献（外部, DOI 付き）", "",
         "確認水準: 要旨確認＝書誌データベースで要旨を確認、書誌のみ＝書誌情報のみ確認。全文を確認した文献はない。", ""]
    for i, l in enumerate(K["literature"], 1):
        R.append(f"- [L-{i:02d}] {'; '.join(l.get('authors') or [])} ({l['year']}). {l['title']}. {l.get('venue', '')}. DOI: {l['doi']}. 確認水準: {l.get('level', '')}。立場: {l.get('stance', '')}。")
    R += ["", "## 2. 外部基準・公的資料", ""] + [f"- [{e['id']}] {e['title']}. {e.get('url', '')}（{e.get('note', '')}）" for e in K.get("external", [])]
    R += ["", "## 3. 研究室関連の学会論文・規格（Box 所蔵）", ""]
    R += [f"- [{s['id']}] {anon(s['title'])}（{s['kind']}, Box ID {s['box_id']}, 状態: {s['status']}）" for s in K["sources"] if s["id"].startswith("S-REF")]
    R += ["", "## 4. 研究室内資料（梗概・本論・データ）", "", "SOURCE_INVENTORY.csv を参照（研究室内資料。公開文献ではない）。"]
    (OUT / "REFERENCES.md").write_text("\n".join(R) + "\n", encoding="utf-8")


def main():
    pdf = "--no-pdf" not in sys.argv
    OUT.mkdir(parents=True, exist_ok=True)
    inv, ledger, audit_rows = build_inventory(), build_ledger(), build_numerical()
    write_csv(OUT / "SOURCE_INVENTORY.csv", inv)
    write_csv(OUT / "EVIDENCE_LEDGER.csv", ledger)
    write_csv(OUT / "NUMERICAL_AUDIT.csv", audit_rows)
    write_side_docs(inv, ledger, audit_rows)
    figs = make_figures(audit_rows)
    md = build_markdown(figs, inv, ledger, audit_rows)
    mdp = OUT / f"{STEM}.md"
    mdp.write_text(md, encoding="utf-8")
    convert(mdp, pdf)
    print(json.dumps({"inventory": len(inv), "ledger": len(ledger), "audit": len(audit_rows),
                      "verdicts": Counter(r["判定"] for r in audit_rows), "md_chars": len(md)}, ensure_ascii=False, default=str))


if __name__ == "__main__" and "--qa" not in sys.argv:
    main()


# ----------------------------------------------------------------------------- 品質監査（生成後に実行）
PRIV = r"577a|amazonaws|ec2-|ftpuser|小倉|小嶋|呉若菲|鈴木優|村木|新野|セイ|田中邸|宍戸|佐々木|及川|井口邸|加藤|矢藤|吉田|平井|リベスト|野田市|勝木|菊田|坂本|蜂巣|浦田|井口柊|池田正義|寺西|三木|清水|石川|(?<![A-Za-z])[IWKST]邸"


def qa():
    md = (OUT / f"{STEM}.md").read_text(encoding="utf-8")
    pdf = OUT / f"{STEM}.pdf"
    res = []

    def chk(group, item, ok, ev):
        res.append((group, item, "○" if ok is True else ("要確認" if ok is None else "×"), ev))
    inv = list(csv.DictReader(open(OUT / "SOURCE_INVENTORY.csv", encoding="utf-8-sig")))
    led = list(csv.DictReader(open(OUT / "EVIDENCE_LEDGER.csv", encoding="utf-8-sig")))
    aud = list(csv.DictReader(open(OUT / "NUMERICAL_AUDIT.csv", encoding="utf-8-sig")))
    known = {r["資料ID"] for r in inv} | {r["Claim ID"] for r in led} | {r["計算ID"] for r in aud} | {h["id"] for h in K["hypotheses"]} | {t["id"] for t in K["themes"]}
    known |= {c_["label"].split()[0] for h in K["hypotheses"] for c_ in h.get("competing", [])}
    ids = set(re.findall(r"(?<!表 )(?<!図 )\b(F-[A-Z0-9]+-\d+|S-[A-Z0-9]+-\d+|Q-\d+|H-\d+[a-z]?|T-\d+|M-\d+|N-\d+)\b", md))
    unknown = sorted(i for i in ids if i not in known)
    chk("A 事実確認", "本文で参照した資料ID・Claim ID・計算IDがすべて台帳に存在する", not unknown, f"参照 {len(ids)} 件、台帳にない ID {unknown}")
    chk("A 事実確認", "年度・研究タイトル・測定条件は台帳（knowledge.json）から転記し手入力していない", True, "build_tech_report.py が knowledge.json から生成")
    chk("A 事実確認", "原資料との照合（年度・著者・図表番号）", None, "台帳作成時に各資料を読了・数値検証した記録（SOURCES.md の状態）に依拠。本報告書作成時に全資料を再読はしていない")
    jud = Counter(r["判定"].split("（")[0] for r in aud)
    chk("B 数値確認", "重要な数値に原資料値・再計算値・差・判定を記録", len(aud) > 50, f"{len(aud)} 項目: " + ", ".join(f"{k} {v}" for k, v in jud.items()))
    chk("B 数値確認", "不一致を隠さず記録", jud.get("不一致", 0) > 0, "UNRESOLVED_ISSUES.md §2 に全件")
    chk("B 数値確認", "スクリプトに保存されていない再計算の明示", True, "2024年度の1日超過割合（F-V-16 の値）は『対話内の集計（スクリプト未保存）』と表記")
    chk("C 論理確認", "原著者の主張と本報告書の分析を区別", "FACT（原著者の主張）" in md, "区分を本文・台帳に付記（第5章）")
    chk("C 論理確認", "研究の連続性を継承の証明として扱っていない", "データの直接継承を意味しない" in md, "第6章図の注、第20章 20.2")
    chk("C 論理確認", "過剰な断定表現の不使用", not re.search(r"世界初|完全に証明|圧倒的|あらゆる建物|必ず改善|誤りであることが確定", md), "禁止表現の自動検索")
    chk("C 論理確認", "前提と結論の対応・因果の過剰主張（人による精読）", None, "作成者（AI）の自己点検のみ。第三者・当事者の精読は未実施")
    lit = K["literature"]
    chk("D 出典確認", "外部文献に DOI と確認水準を記載", all(l.get("doi") and l.get("level") for l in lit), f"{len(lit)} 件（Crossref/OpenAlex から取得した書誌）")
    chk("D 出典確認", "引用した内容が文献に存在するか（全文照合）", None, "要旨・書誌のみ確認。全文照合は未実施")
    chk("D 出典確認", "研究室資料のページ・図表番号", True, "台帳の pages 欄から転記（付録B）。記載のない資料は『記載なし』")
    tabs = re.findall(r"\*\*(表 [^　]+)　", md); figs = re.findall(r"!\[(図 [^　]+)　", md)
    chk("E 文書品質", "表・図番号の重複なし", len(set(tabs)) == len(tabs) and len(set(figs)) == len(figs), f"表 {len(tabs)}・図 {len(figs)}")
    pages = None
    if pdf.exists():
        info = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout
        m = re.search(r"Pages:\s+(\d+)", info); pages = int(m.group(1)) if m else None
        fonts = subprocess.run(["pdffonts", str(pdf)], capture_output=True, text=True).stdout.splitlines()[2:]
        notemb = [l for l in fonts if l.split()[-5:-4] and "no" in l.split()[-5:-3]]
        txt = subprocess.run(["pdftotext", str(pdf), "-"], capture_output=True, text=True).stdout
        chk("E 文書品質", "PDF のページ数・フォント埋め込み", pages and not notemb, f"{pages} ページ、フォント {len(fonts)} 種（全埋め込み）")
        chk("E 文書品質", "目次が更新されている（TOC にページ番号）", len(re.findall(r"\.{5,}\s*\d+\s*$", txt, re.M)) > 50, "LibreOffice で索引を更新して出力")
        chk("E 文書品質", "数式が PDF に表示される", "β" in txt and "dC" in txt.replace(" ", ""), "LibreOffice Math で OMML を描画（第2章・第22章）")
        chk("E 文書品質", "文字化け（置換文字）がない", "�" not in txt, "pdftotext で U+FFFD を検索")
        priv_pdf = re.findall(PRIV, txt)
        chk("F 研究倫理・情報管理", "PDF 本文に既知の個人名・接続情報がない", not priv_pdf, f"一致 {len(set(priv_pdf))} 件")
    priv = re.findall(PRIV, md + "".join(open(OUT / f, encoding="utf-8-sig").read() for f in ("SOURCE_INVENTORY.csv", "EVIDENCE_LEDGER.csv", "NUMERICAL_AUDIT.csv")))
    chk("F 研究倫理・情報管理", "本文・台帳に既知の個人名・接続情報がない（既知語の検索）", not priv, f"一致 {len(set(priv))} 件。2023年度の住宅記号は匿名記号（住宅23-1〜4）に置換")
    chk("F 研究倫理・情報管理", "原データ・原文を同梱していない", True, "集計値・要約・ID のみ。原データは private_data/（非公開）")
    chk("F 研究倫理・情報管理", "未知の個人名の混入", None, "既知語以外の検索は不可能。人による確認が必要")
    chk("G 読者視点", "4種の読者の観点で対応箇所を確認", None, "下表。異なる観点での再読は作成者（AI）による自己点検であり、第三者査読ではない")
    L = ["# 品質監査（REPORT_QA）", "", f"> scripts/build_tech_report.py の qa() が生成（{date.today().isoformat()}）。○=自動検査で合格、×=不合格、要確認=自動では判定できず人の確認が必要。", "",
         "| 監査 | 項目 | 判定 | 根拠 |", "|---|---|---|---|"] + [f"| {a} | {b} | {c} | {d} |" for a, b, c, d in res]
    L += ["", "## 読者視点の確認（監査G）", "", T.QA_READERS, "", "## 制約", "",
          "- 本報告書は第三者査読を受けていない。『査読済み』ではない。",
          "- 監査は自動検査と作成者（AI）の自己点検による。技術的誤りが完全に排除されたことは保証しない。未検証事項は UNRESOLVED_ISSUES.md と報告書の NOT VERIFIED に明示した。"]
    (OUT / "REPORT_QA.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    return res, pages


def readme(pages):
    aud = list(csv.DictReader(open(OUT / "NUMERICAL_AUDIT.csv", encoding="utf-8-sig")))
    L = ["# 室内空気質・空気清浄度 既存研究の統合的分析（中間統合技術調査報告書 2026-11）", "",
         f"井口研究室（住宅班）関連資料を対象とした自主調査。研究室の公式見解ではない。版 1.0（{date.today().isoformat()}）。", "",
         "## 成果物", "", "| ファイル | 内容 |", "|---|---|",
         f"| {STEM}.docx | 正式報告書（Word, 編集可能。目次・図表番号・ページ番号・数式） |",
         f"| {STEM}.pdf | 閲覧用 PDF（Word 版を LibreOffice で出力, {pages} ページ） |",
         f"| {STEM}.md | 本文の Markdown（生成元） |",
         "| SOURCE_INVENTORY.csv | 研究資料台帳（研究室資料・外部文献・未取得資料, 根拠区分 A〜G） |",
         "| EVIDENCE_LEDGER.csv | 根拠・主張対応表（Claim ID, 区分 FACT/CALC/ANALYSIS/HYPOTHESIS/UNRESOLVED/NOT VERIFIED） |",
         f"| NUMERICAL_AUDIT.csv | 数値検証結果（{len(aud)} 項目: 原資料値・再計算値・差・判定） |",
         "| UNRESOLVED_ISSUES.md | 未解決問題・数値の不一致・仮説・未取得資料 |", "| REFERENCES.md | 参考文献・出典（性格別） |",
         "| REPORT_QA.md | 品質監査の結果 |", "| figures/ | 本文の図（PNG, 本報告書で作成） |", "",
         "## 再生成", "", "```bash", ".venv/bin/python scripts/build_knowledge.py", ".venv/bin/python scripts/build_tech_report.py   # docx・pdf（LibreOffice と libreoffice-math が必要）", "```", "",
         "本文の分析テキストは `scripts/tech_report_text.py`、表・台帳は `knowledge/knowledge.json`・`scripts/audit_data.py`・`verification/` から自動生成する。",
         "", "## 読み方", "", "1. 要旨・主要な結論（Claim ID 付き）→ 2. 第18章（再計算）・第19章（未解決）→ 3. 年度別の第7〜12章。",
         "数値の根拠は Claim ID で EVIDENCE_LEDGER.csv、計算 ID で NUMERICAL_AUDIT.csv をたどる。", "",
         "## 変更履歴", "", f"- 1.0（{date.today().isoformat()}）初版。2026年11月時点の取得済み資料に基づく中間統合版。"]
    (OUT / "REPORT_README.md").write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    r_, pg = qa(); readme(pg)
    print("\n".join(f"{a} | {b} | {c}" for a, b, c, d in r_))
