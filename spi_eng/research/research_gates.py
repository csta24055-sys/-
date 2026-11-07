#!/usr/bin/env python3
"""研究の検証ゲート。保存済みのデータを実際に読んで、各STEPの判定（NOT_STARTED / IN_PROGRESS / PASS / BLOCKED）を決め、
research_status.json に書き出す。レポートに「完了」と書いてあっても、データが基準を満たさなければ PASS にはしない。

使い方: python3 research_gates.py [--selftest]
"""
import csv, json, os, sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
M = json.load(open(os.path.join(HERE, "research_manifest.json"), encoding="utf-8"))


def rows(rel):
    p = os.path.join(HERE, rel)
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def exists(rel):
    return os.path.exists(os.path.join(HERE, rel))


def gate_step0():
    miss = [f for f in M["steps"]["STEP0"]["files"] if not exists(f)]
    if miss:
        return "IN_PROGRESS", [f"ファイルがない: {m}" for m in miss]
    log = rows("research_log.csv")
    if log is None or not log or set(log[0]) != {"ts", "step", "action", "detail"}:
        return "IN_PROGRESS", ["research_log.csv の形式が不正"]
    return "PASS", []


def gate_step1():
    s = M["steps"]["STEP1"]
    miss = [f for f in s["files"] if not exists(f)]
    issues = [f"ファイルがない: {m}" for m in miss]
    recs, qlog, fetch = rows("step1/eng_records.csv"), rows("step1/search_log.csv"), rows("step1/fetch_attempts.csv")
    if recs is None or qlog is None or fetch is None:
        return "NOT_STARTED" if not qlog else "IN_PROGRESS", issues
    # 1) レコードの必須項目
    bad = [r["report_id"] for r in recs if not r["url"].strip().startswith("http") or r["original_verified"] not in ("yes", "no")
           or not r["verification_method"].strip() or not r["eng_evidence"].strip()]
    if bad:
        issues.append(f"必須項目が欠けたレコード: {bad[:10]}")
    # 原文確認済み(yes)のレコードは、取得記録(archive_index.csv)に HTTP 200 で存在しなければならない
    arc = rows("step1/archive_index.csv") or []
    ok_urls = {a["url"] for a in arc if a["http"] == "200" and int(a["text_len"] or 0) > 50}
    fake = [r["report_id"] for r in recs if r["original_verified"] == "yes" and r["url"] not in ok_urls]
    if fake:
        issues.append(f"原文確認済みとしているが取得記録と照合できないレコード: {fake[:10]}")
        bad = bad + fake
    ids = [r["report_id"] for r in recs]
    if len(ids) != len(set(ids)):
        issues.append("report_id が重複している")
    # 2) 件数
    n = len(recs)
    n_orig = sum(r["original_verified"] == "yes" for r in recs)
    ratio = n_orig / n if n else 0.0
    # 3) 探索の網羅性
    nq = len({q["query"] for q in qlog})
    media = {m for q in qlog for m in q.get("engine", "").split("|") if m}
    media_attempted = {f["medium"] for f in fetch} | {r["medium"] for r in recs}
    blocked_media = {f["medium"] for f in fetch if f["result"] == "blocked"}
    ok_media = {f["medium"] for f in fetch if f["result"] == "ok"}
    blocked_primary = [m for m in s["primary_media"] if m in blocked_media and m not in ok_media]
    stats = dict(records=n, original_verified=n_orig, original_ratio=round(ratio, 3), distinct_queries=nq,
                 media_attempted=sorted(media_attempted), blocked_primary_media=blocked_primary)
    coverage_ok = nq >= s["min_distinct_queries"] and len(media_attempted & set(s["primary_media"])) >= s["min_media_attempted"]
    count_ok = n >= s["target_records"]
    verified_ok = ratio >= s["min_original_verified_ratio"]
    if not coverage_ok:
        issues.append(f"網羅性が不足: クエリ{nq}件(基準{s['min_distinct_queries']}), "
                      f"主要媒体{len(media_attempted & set(s['primary_media']))}種(基準{s['min_media_attempted']})")
    if not count_ok:
        issues.append(f"件数{n}件が目標{s['target_records']}件に届かない(網羅性監査に合格した場合のみ例外)")
    if not verified_ok:
        issues.append(f"原文確認率{ratio:.0%}が基準{s['min_original_verified_ratio']:.0%}に届かない")
    # 媒体ごとのアクセス状況の記録が必須。取得できる媒体は、探索(sweep)が完了していなければならない
    ms = rows("step1/media_status.csv")
    if ms is None:
        issues.append("media_status.csv がない")
        coverage_ok = False
    else:
        st_by = {m["medium"]: m for m in ms}
        missing = [m for m in s["primary_media"] if m not in st_by]
        unswept = [m["medium"] for m in ms if m["status"].startswith("accessible") and m["sweep_done"] != "yes"]
        if missing: issues.append(f"アクセス状況が未記録の主要媒体: {missing}"); coverage_ok = False
        if unswept: issues.append(f"取得できるのに探索が終わっていない媒体: {unswept}"); coverage_ok = False
        stats["inaccessible_primary_media"] = [m for m in s["primary_media"] if m in st_by and not st_by[m]["status"].startswith("accessible")]
    audit = open(os.path.join(HERE, "step1/coverage_audit.md"), encoding="utf-8").read() if exists("step1/coverage_audit.md") else ""
    shortfall_ack = "SHORTFALL_ACKNOWLEDGED" in audit
    if not count_ok and not shortfall_ack:
        issues.append("件数の不足が coverage_audit.md で認定(SHORTFALL_ACKNOWLEDGED)されていない")
    if len(blocked_primary) * 2 >= len(s["primary_media"]) and not verified_ok:
        return "BLOCKED", issues + [f"主要媒体の原文取得が遮断されている: {blocked_primary}"], stats
    if bad or not verified_ok or not coverage_ok or not (count_ok or shortfall_ack):
        return "IN_PROGRESS", issues, stats
    return "PASS", issues, stats


def gate_step2():
    r = gate_files("STEP2")
    if r[0] != "PASS":
        return r
    issues = []
    recs = rows("step1/eng_records.csv") or []
    ver = rows("step2/verified_records.csv") or []
    dep = rows("step2/dependency_graph.csv") or []
    ids1 = {x["report_id"] for x in recs}; ids2 = {x["report_id"] for x in ver}
    if ids1 != ids2:
        issues.append(f"STEP1とSTEP2のレコードが一致しない: 不足{sorted(ids1-ids2)[:5]} 余分{sorted(ids2-ids1)[:5]}")
    need = ["eng_confirmed", "original_status", "objective_score", "independence_unit"]
    bad = [x["report_id"] for x in ver if any(not x[k] for k in need)]
    if bad: issues.append(f"検証項目が空のレコード: {bad[:5]}")
    try:
        sm = json.load(open(os.path.join(HERE, "step2/summary.json"), encoding="utf-8"))
    except Exception:
        return "IN_PROGRESS", issues + ["summary.json が読めない"]
    units = {x["independence_unit"] for x in ver}
    if sm.get("independent_units_lower_bound") != len(units) or sm.get("records") != len(ver):
        issues.append("summary.json の独立件数が実データの再集計と一致しない")
    claim_ids = {c["claim_id"] for c in (rows("step1/eng_claims_verified.csv") or [])}
    known = ids1 | claim_ids | {"RUMOR"}
    badep = [d for d in dep if d["from"] not in known or d["to"] not in known]
    if badep: issues.append(f"依存関係に存在しないIDがある: {badep[:3]}")
    stats = {"independent_units": [sm.get("independent_units_lower_bound"), sm.get("independent_units_upper_bound")],
             "with_passage_count": sm.get("independent_units_with_passage_count"), "objective_scores": sm.get("records_with_objective_score")}
    return ("PASS" if not issues else "IN_PROGRESS"), issues, stats


def gate_step3():
    r = gate_files("STEP3")
    if r[0] != "PASS":
        return r
    import subprocess
    issues = []
    t = subprocess.run([sys.executable, os.path.join(HERE, "step3/test_fusion.py")], capture_output=True, text=True)
    if t.returncode != 0 or "ALL TESTS PASSED" not in t.stdout:
        issues.append("test_fusion.py が失敗: " + (t.stderr or t.stdout)[-300:])
    rel = rows("step3/reliability.csv") or []
    need = {x["report_id"] for x in (rows("step2/verified_records.csv") or [])} | {c["claim_id"] for c in (rows("step1/eng_claims_verified.csv") or [])}
    miss = need - {x["id"] for x in rel}
    if miss: issues.append(f"信頼性の評価がない項目: {sorted(miss)[:5]}")
    dims = ["accuracy", "memory", "score_reliability", "direct_experience", "selection_bias"]
    if any(not x[d] for x in rel for d in dims if d in x):
        issues.append("信頼性の観点に空欄がある")
    try:
        fr = json.load(open(os.path.join(HERE, "step3/fusion_results.json"), encoding="utf-8"))
        if not fr.get("limitations"): issues.append("識別できないパラメータの限界が記録されていない")
    except Exception:
        issues.append("fusion_results.json がない")
    if not exists("step3/limitations.md"): issues.append("limitations.md がない")
    return ("PASS" if not issues else "IN_PROGRESS"), issues, {"items": len(rel)}


def gate_step4():
    r = gate_files("STEP4")
    if r[0] != "PASS":
        return r
    import subprocess
    issues = []
    for script, token in [("step4/check_independent.py", "OK"), ("step4/test_data_sensitivity.py", "DATA SENSITIVITY OK")]:
        t = subprocess.run([sys.executable, os.path.join(HERE, script)], capture_output=True, text=True)
        if t.returncode != 0 or token not in t.stdout:
            issues.append(f"{script} が失敗: " + (t.stderr or t.stdout)[-200:])
    res = json.load(open(os.path.join(HERE, "step4/results.json"), encoding="utf-8"))
    ver = rows("step2/verified_records.csv") or []
    units = {x["independence_unit"] for x in ver if x["passages"]}
    if res["data"]["n_units"] != len(units):
        issues.append("results.json のデータ件数が STEP2 の実データと一致しない(再実行が必要)")
    tr = rows("step4/trace.csv") or []
    if not any(t["type"] == "実データ" for t in tr) or not any("仮定" in t["type"] for t in tr):
        issues.append("trace.csv に実データと仮定の区別がない")
    return ("PASS" if not issues else "IN_PROGRESS"), issues, {"units": res["data"]["n_units"], "k3": res["data"]["k3"]}


def gate_step5():
    r = gate_files("STEP5")
    if r[0] != "PASS":
        return r
    import subprocess
    issues = []
    recs = rows("step5/inpex_records.csv") or []
    bad = [x["id"] for x in recs if not x["url"].strip() or x["original_verified"] not in ("yes", "no") or not x["verification"].strip()]
    if bad: issues.append(f"出典・確認状態が欠けたINPEXレコード: {bad[:5]}")
    reports = [x for x in recs if x["kind"] == "report" and x["original_verified"] == "yes"]
    if len(reports) < 5: issues.append(f"原文確認済みの選考体験談が少なすぎる: {len(reports)}")
    ql = rows("step5/inpex_search_log.csv") or []
    if len(ql) < 10: issues.append(f"INPEXの検索ログが不足: {len(ql)}")
    try:
        hj = json.load(open(os.path.join(HERE, "step5/hypotheses.json"), encoding="utf-8"))
        if not hj.get("identifiability") or not hj.get("sensitivity"): issues.append("仮説比較に識別可能性・感度分析がない")
    except Exception:
        issues.append("hypotheses.json が読めない")
    t = subprocess.run([sys.executable, os.path.join(HERE, "step5/test_inpex.py")], capture_output=True, text=True)
    if "INPEX TESTS PASSED" not in t.stdout: issues.append("test_inpex.py が失敗: " + (t.stderr or t.stdout)[-200:])
    return ("PASS" if not issues else "IN_PROGRESS"), issues, {"records": len(recs), "verified_reports": len(reports), "queries": len(ql)}


def gate_step6():
    r = gate_files("STEP6")
    if r[0] != "PASS":
        return r
    import subprocess
    issues = []
    res = json.load(open(os.path.join(HERE, "step6/results.json"), encoding="utf-8"))
    hj = json.load(open(os.path.join(HERE, "step5/hypotheses.json"), encoding="utf-8"))
    if res.get("hyp_weights_used") != hj["sensitivity"]["r_scale=1.0|rho=0.9"]:
        issues.append("STEP6 が STEP5 の最新の仮説確率を使っていない(再実行が必要)")
    t = subprocess.run([sys.executable, os.path.join(HERE, "step6/test_decision.py")], capture_output=True, text=True, cwd=os.path.join(HERE, "step6"))
    if "DECISION TESTS PASSED" not in t.stdout: issues.append("test_decision.py が失敗: " + (t.stderr or t.stdout)[-200:])
    tr = rows("step6/trace.csv") or []
    if not any("仮定" in x["type"] for x in tr) or not any("実データ" in x["type"] for x in tr):
        issues.append("trace.csv で実データと仮定(条件付きシミュレーション)が区別されていない")
    return ("PASS" if not issues else "IN_PROGRESS"), issues, {"scenarios": res.get("n_scenarios")}


REQUIRED_SECTIONS = ["口コミ収集件数", "原文確認済み件数", "独立した証拠件数", "長文3題に関する証拠の強さ", "推定得点順位",
                     "INPEXの英語評価実態", "基礎能力上位25", "受検戦略比較", "最適戦略", "仮定に依存する部分"]


def gate_step7(prev_all_pass):
    if not exists("FINAL_REPORT.md"):
        return "NOT_STARTED", ["FINAL_REPORT.md がない"]
    txt = open(os.path.join(HERE, "FINAL_REPORT.md"), encoding="utf-8").read()
    first = txt.splitlines()[0].strip() if txt else ""
    expected = "RESEARCH_STATUS = COMPLETE" if prev_all_pass else None
    issues = []
    if not first.startswith("RESEARCH_STATUS = "):
        issues.append("先頭行に RESEARCH_STATUS がない")
    elif prev_all_pass and first != expected:
        issues.append(f"先頭行の状態が判定と一致しない: {first}")
    elif not prev_all_pass and first == "RESEARCH_STATUS = COMPLETE":
        issues.append("前のSTEPが未合格なのに COMPLETE と表示している")
    miss = [s for s in REQUIRED_SECTIONS if s not in txt]
    if miss: issues.append(f"必須項目が欠けている: {miss}")
    return ("PASS" if not issues else "IN_PROGRESS"), issues


def gate_files(step):
    miss = [f for f in M["steps"][step]["files"] if not exists(f)]
    return ("NOT_STARTED" if len(miss) == len(M["steps"][step]["files"]) else "IN_PROGRESS",
            [f"ファイルがない: {m}" for m in miss]) if miss else ("PASS", [])


def evaluate():
    st, detail = {}, {}
    for step in M["steps"]:
        req = M["steps"][step]["requires"]
        if step == "STEP0":
            r = gate_step0()
        elif step == "STEP1":
            r = gate_step1()
        elif step == "STEP2":
            r = gate_step2()
        elif step == "STEP3":
            r = gate_step3()
        elif step == "STEP4":
            r = gate_step4()
        elif step == "STEP5":
            r = gate_step5()
        elif step == "STEP6":
            r = gate_step6()
        elif step == "STEP7":
            r = gate_step7(all(st.get(k) == "PASS" for k in st))
        else:
            r = gate_files(step)
            # STEP2以降は、各STEP専用の検証（独立件数・テストの実行・データの反映確認など）を
            # そのSTEPに着手した時点で追加する。追加されるまで PASS にはしない。
            if r[0] == "PASS":
                r = ("IN_PROGRESS", ["このSTEP専用の検証がまだ実装されていない"])
        status, issues = r[0], r[1]
        stats = r[2] if len(r) > 2 else {}
        unmet = [q for q in req if st.get(q) != "PASS"]
        if unmet and status == "PASS":
            status, issues = "IN_PROGRESS", issues + [f"前のSTEPが未合格: {unmet}"]
        if unmet and status not in ("BLOCKED",):
            # 前提が未合格のSTEPで作業が進んでいたら、順序違反として記録する
            if status != "NOT_STARTED":
                issues.append(f"順序違反: 前のSTEP {unmet} が未合格のまま着手されている")
        st[step] = status
        detail[step] = {"status": status, "issues": issues, "stats": stats}
    if all(v == "PASS" for v in st.values()):
        overall = "COMPLETE"
    elif any(v == "BLOCKED" for v in st.values()):
        overall = "BLOCKED"
    else:
        overall = "INCOMPLETE"
    return overall, detail


def selftest():
    """ゲートが緩すぎないことの確認：不完全なレコードや件数不足が PASS にならないこと。"""
    import tempfile, shutil
    global HERE
    orig = HERE
    tmp = tempfile.mkdtemp()
    try:
        shutil.copytree(orig, tmp, dirs_exist_ok=True)
        HERE = tmp
        with open(os.path.join(tmp, "step1/eng_records.csv"), "a", encoding="utf-8") as f:
            f.write("T1,,x,,,,,,,,,,,,maybe,,\n")      # URLなし・確認状態が不正
        o, d = evaluate()
        assert d["STEP1"]["status"] != "PASS", "不正なレコードがあるのに PASS になった"
        assert o != "COMPLETE"
        assert d["STEP2"]["status"] != "PASS"
        print("selftest OK")
    finally:
        HERE = orig
        shutil.rmtree(tmp)


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    overall, detail = evaluate()
    out = {"evaluated_at": datetime.now().isoformat(timespec="seconds"), "RESEARCH_STATUS": overall, "steps": detail}
    json.dump(out, open(os.path.join(HERE, "research_status.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("RESEARCH_STATUS =", overall)
    for k, v in detail.items():
        print(f"  {k}: {v['status']}" + (f"  {v['stats']}" if v["stats"] else ""))
        for i in v["issues"][:6]:
            print("     -", i)
