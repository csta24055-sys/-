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
    if len(blocked_primary) * 2 >= len(s["primary_media"]) and not verified_ok:
        return "BLOCKED", issues + [f"主要媒体の原文取得が遮断されている: {blocked_primary}"], stats
    if bad or not verified_ok or not coverage_ok or not (count_ok or coverage_ok):
        return "IN_PROGRESS", issues, stats
    return "PASS", issues, stats


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
