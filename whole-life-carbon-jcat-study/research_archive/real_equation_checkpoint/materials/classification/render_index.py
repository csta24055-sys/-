#!/usr/bin/env python3
"""Render INDEX.md and index_detail/*.md of the checkpoint archive from the classification JSON.

Reads only JSON / text. Does not import or run any code of the terminated study.
Usage: python3 -I render_index.py <classification_json_dir> <archive_dir> <repo_root>
"""
import json
import os
import re
import subprocess
import sys
from collections import Counter, OrderedDict

SRC, ARCH_DIR, REPO = sys.argv[1], sys.argv[2], sys.argv[3]
STUDY = "whole-life-carbon-jcat-study/"
ARCH = STUDY + "research_archive/real_equation_checkpoint/"
LENSES = ["R1", "R2", "R3", "R4", "R5", "R7"]
LENS_NAME = {
    "R1": "統制文書・台帳・順位",
    "R2": "基準計算・架空データ・比較・試験",
    "R3": "統合モデルとその根拠",
    "R4": "近似検証",
    "R5": "記録・進捗台帳・報告書・成果物・材料分類",
    "R6": "第2回の指摘 59 件の登録簿",
    "R7": "新研究のための再利用の下調べ（構造の棚卸し）",
}
CAT = {1: "検証済み成果", 2: "暫定・未検証成果", 3: "研究途中の数式・仮説", 4: "不具合・未解決事項"}

TOPICS = OrderedDict([
    ("T01", ("統制文書と手順書", "T01_policy_protocol.md")),
    ("T02", ("評価単位の台帳・シート族・依存関係", "T02_ledger.md")),
    ("T03", ("着手順序（評価軸 A・B）", "T03_ranking.md")),
    ("T04", ("基準計算と規約", "T04_reference_calculation.md")),
    ("T05", ("架空データ・比較の仕組み・試験", "T05_synthetic_data_harness.md")),
    ("T06", ("統合モデル K1〜K7 と導出", "T06_unified_models.md")),
    ("T07", ("厳密一致・負荷・入力の測定と反例", "T07_exactness_load.md")),
    ("T08", ("近似検証（M3〜M6）", "T08_approximation.md")),
    ("T09", ("記録・進捗台帳・報告書・必須成果物", "T09_records_reports.md")),
    ("T10", ("材料分類の設計草案", "T10_material_taxonomy.md")),
    ("T11", ("中断した修正（65ff124）と未実施の改訂", "T11_interrupted_fix.md")),
    ("T12", ("式の族と未実装の案（構造の棚卸し）", "T12_formula_families.md")),
])


def rng(lens, a, b):
    return ["CK-%s-%02d" % (lens, i) for i in range(a, b + 1)]


TOPIC_IDS = {
    "T01": rng("R1", 1, 4),
    "T02": rng("R1", 5, 10) + rng("R1", 12, 16) + ["CK-R1-21"] + rng("R7", 1, 3) + ["CK-R7-30"],
    "T03": rng("R1", 17, 20) + ["CK-R3-22"],
    "T04": rng("R2", 1, 10) + rng("R7", 17, 20) + ["CK-R7-28", "CK-R7-29"],
    "T05": rng("R2", 11, 17) + ["CK-R7-15", "CK-R7-16", "CK-R7-21"],
    "T06": rng("R3", 1, 17) + rng("R3", 24, 26) + ["CK-R3-33", "CK-R3-34", "CK-R3-35", "CK-R3-37"] + rng("R7", 23, 25),
    "T07": rng("R3", 18, 21) + ["CK-R3-23"] + rng("R3", 27, 30) + ["CK-R7-22"],
    "T08": rng("R4", 1, 22) + ["CK-R4-25", "CK-R4-26", "CK-R7-26", "CK-R7-27"],
    "T09": rng("R5", 1, 25) + ["CK-R5-29"],
    "T10": rng("R5", 26, 28),
    "T11": ["CK-R1-11"] + rng("R2", 18, 24) + ["CK-R3-31", "CK-R3-32", "CK-R3-36", "CK-R4-23", "CK-R4-24",
                                               "CK-R5-30", "CK-R5-31", "CK-R7-32"],
    "T12": rng("R7", 4, 14) + ["CK-R7-31"],
}

# Notes on the strength of the evidence of category-1 items (written by the compiler of the index).
C1_NOTE = {
    "CK-R1-05": "件数と相互参照の数え直しだけである。内容が正しいことの確認ではない。数え直したのは第2回の検査担当 1 者。",
    "CK-R5-01": "件数と相互参照の数え直しだけである。内容が正しいことの確認ではない。",
    "CK-R5-11": "件数の数え直しだけである。数え直したのは第2回の検査担当 1 者。",
    "CK-R1-09": "文面の一致は検査担当 2 者。書き直しとの一致は検査担当 1 者の報告で、反証検査担当はこの一致をやり直していない。",
    "CK-R2-01": "書き直しとの一致は第2回の検査担当 1 者の報告で、反証検査担当はこの一致をやり直していない。",
    "CK-R2-02": "独立実装との一致は第2回の検査担当 1 者の報告。試験の合否は停止後に確かめていない。",
    "CK-R7-17": "書き直しとの一致は第2回の検査担当 1 者の報告で、反証検査担当はこの一致をやり直していない。",
    "CK-R3-12": "コードとの読み比べと全体の一致による。専用の総当たりはしていない。",
    "CK-R3-16": "コードとの読み比べと全体の一致による。専用の総当たりはしていない。",
    "CK-R3-20": "数え直したのは報告書の検査担当 1 者。反証検査担当は付いていない。",
    "CK-R5-17": "設計についての記述であり、測定の結果ではない。",
    "CK-R7-28": "コードとの照合は第2回の検査担当 1 者。",
}


def load():
    items, meta = [], {}
    for L in LENSES:
        j = json.load(open(os.path.join(SRC, L + ".json"), encoding="utf-8"))
        meta[L] = j
        for it in j["items"]:
            it["lens"] = L
            items.append(it)
    r6 = json.load(open(os.path.join(SRC, "R6.json"), encoding="utf-8"))
    return items, meta, r6


def git_lines(*args):
    out = subprocess.run(["git", "-C", REPO] + list(args), capture_output=True, text=True, check=True).stdout
    return [x for x in out.split("\n") if x]


TRACKED = None
SNAP = None
PATH_RE = re.compile(r"whole-life-carbon-jcat-study/[A-Za-z0-9_\-./]+")


def exists_head(p):
    p = p.rstrip("/.")
    if p in TRACKED:
        return True
    return any(t.startswith(p + "/") for t in TRACKED)


def exists_snap(p):
    p = p.rstrip("/.")
    return p in SNAP or any(t.startswith(p + "/") for t in SNAP)


def disp(p):
    if p.startswith(ARCH):
        return p[len(ARCH):]
    if p.startswith(STUDY):
        return p[len(STUDY):]
    return p


def link(p, up):
    """Markdown link from a file `up` levels below the archive dir to repo path p."""
    q = p.rstrip("/.")
    if q.startswith(ARCH):
        rel = "../" * up + q[len(ARCH):]
    else:
        rel = "../" * (up + 2) + q[len(STUDY):]
    return "[`%s`](%s)" % (disp(p.rstrip(".")), rel)


MISSING = []


def loc_md(loc, up):
    in_snap_only = "65ff124" in loc

    def rep(m):
        p = m.group(0)
        if not in_snap_only and exists_head(p):
            return link(p, up)
        if exists_snap(p):
            return "`%s`（コミット `65ff124` の版）" % disp(p.rstrip("."))
        if exists_head(p):
            return link(p, up)
        MISSING.append(loc)
        return "`%s`" % disp(p)

    return PATH_RE.sub(rep, loc)


def cell(s):
    return (s or "").replace("|", "\\|").replace("\n", "<br>")


def short(text, limit=150):
    text = (text or "").strip().replace("\n", " ")
    if len(text) <= limit:
        return text
    out = ""
    for sent in re.split(r"(?<=。)", text):
        if out and len(out) + len(sent) > limit:
            break
        out += sent
        if len(out) >= limit:
            break
    cap = int(limit * 1.4)
    if len(out) > cap:
        out = out[:cap] + "…"
    return out


def routes(it):
    if not it.get("reuse_candidate"):
        return "—"
    r = it.get("reuse_routes") or []
    return "・".join(r) if r else "（ルート未指定）"


def main():
    global TRACKED, SNAP
    TRACKED = set(git_lines("ls-files"))
    SNAP = set(git_lines("ls-tree", "-r", "--name-only", "65ff124"))
    items, meta, r6 = load()
    by_id = {it["id"]: it for it in items}
    assert len(by_id) == len(items), "duplicate ids"
    topic_of = {}
    for t, ids in TOPIC_IDS.items():
        for i in ids:
            assert i in by_id, "unknown id in topic map: " + i
            assert i not in topic_of, "id in two topics: " + i
            topic_of[i] = t
    missing_topic = [i for i in by_id if i not in topic_of]
    assert not missing_topic, "ids without topic: %s" % missing_topic
    for it in items:
        assert it["state_category"] in (1, 2, 3, 4), it["id"]
    ids59 = [f["id"] for f in r6["findings"]]
    assert len(ids59) == 59 and len(set(ids59)) == 59

    def dlink(i, up=0):
        t = topic_of[i]
        pre = "" if up else "index_detail/"
        return "[%s](%s%s#%s)" % (i, pre, TOPICS[t][1], i.lower())

    os.makedirs(os.path.join(ARCH_DIR, "index_detail"), exist_ok=True)

    # ---------------------------------------------------------------- detail files
    for t, (tname, fname) in TOPICS.items():
        o = []
        o.append("# 索引の詳細 %s：%s" % (t, tname))
        o.append("")
        o.append("[INDEX.md](../INDEX.md) の項目ごとの詳細。分類担当（読み取り専用）が書いた内容を、欄ごとにそのまま載せる。")
        o.append("旧研究の数値はすべて架空データでの値で、対象は独立概念モデルである。原版の表計算との一致や、実建物での精度を示すものではない。")
        o.append("所在の表記：`09_APPROX_STUDY/…` などは `whole-life-carbon-jcat-study/` からの位置、`materials/…` はこの保存フォルダからの位置。")
        o.append("")
        ids = TOPIC_IDS[t]
        o.append("| 項目 | 区分 | 題 |")
        o.append("|---|---|---|")
        for i in ids:
            it = by_id[i]
            o.append("| [%s](#%s) | %d | %s |" % (i, i.lower(), it["state_category"], cell(it["title"])))
        o.append("")
        for i in ids:
            it = by_id[i]
            o.append('<a id="%s"></a>' % i.lower())
            o.append("")
            o.append("## %s　%s" % (i, it["title"]))
            o.append("")
            o.append("- **区分**：%d　%s" % (it["state_category"], CAT[it["state_category"]]))
            if i in C1_NOTE:
                o.append("- **根拠の強さについての注記（索引の作成者）**：%s" % C1_NOTE[i])
            o.append("- **内容**：%s" % it["what"])
            o.append("- **所在**：")
            for l in it["locations"]:
                o.append("  - %s" % loc_md(l, 1))
            o.append("- **確かめ方**：%s" % (it.get("checked_how") or "（記載なし）"))
            o.append("- **確かめた者**：%s" % it["checked_by"])
            o.append("- **言える範囲**：%s" % (it.get("scope") or "（記載なし）"))
            r2 = it.get("round2_findings") or []
            o.append("- **関係する第2回の指摘**：%s" % ("、".join(r2) if r2 else "なし"))
            o.append("- **第2回の指摘の影響**：%s" % (it.get("round2_effect") or "なし"))
            o.append("- **今の時点で言ってよいこと**：%s" % (it.get("claim_that_stands") or "（記載なし）"))
            bad = it.get("claims_not_to_rely_on") or []
            if bad:
                o.append("- **使ってはいけない記述**：")
                for b in bad:
                    o.append("  - %s" % b)
            else:
                o.append("- **使ってはいけない記述**：挙げられていない")
            if it.get("reuse_candidate"):
                o.append("- **新研究での再利用**：候補（ルート %s）" % routes(it))
                o.append("  - 使い道：%s" % (it.get("reuse_how") or "（記載なし）"))
                o.append("  - 条件・注意：%s" % (it.get("reuse_conditions") or "（記載なし）"))
            else:
                o.append("- **新研究での再利用**：候補にしない")
                if it.get("reuse_conditions"):
                    o.append("  - 理由・注意：%s" % it["reuse_conditions"])
            ev = it.get("evidence") or []
            if ev:
                o.append("- **分類の根拠**：")
                for e in ev:
                    o.append("  - %s" % loc_md(e, 1))
            o.append("- **分類した観点**：%s（%s）" % (it["lens"], LENS_NAME[it["lens"]]))
            o.append("")
        open(os.path.join(ARCH_DIR, "index_detail", fname), "w", encoding="utf-8").write("\n".join(o) + "\n")

    # ---------------------------------------------------------------- findings file
    o = []
    o.append("# 第2回の独立検査の指摘 59 件：登録簿と、停止時点の状態")
    o.append("")
    o.append("[INDEX.md](../INDEX.md) の 5.2 節の詳細。分類担当（読み取り専用、観点 R6）が、保存した資料を読んで作った。")
    o.append("")
    o.append("- 範囲：%s" % r6["scope_note"])
    o.append("- 判定の欄：%s" % r6["verdict_note"])
    o.append("- 公開中の版に残るかどうか：%s" % r6["basis_for_in_committed_tree"])
    o.append("- REP の 18 件について：停止前に、主担当（研究の実行担当）が検査担当のスクリプトを再実行して再現した。その出力は保存していないので、保存資料からは確かめられない。")
    o.append("- 指摘の全文と再現の手順は `materials/round2_review/triage/` の 5 ファイルにある。**`materials/round2_review/checker_scripts/` のスクリプトは旧研究のコードを読み込むので、実行しない。**")
    o.append("")
    o.append("## 件数")
    o.append("")
    c = r6["counts"]
    o.append("| 分け方 | 件数 |")
    o.append("|---|---|")
    o.append("| 判定 | 反証検査で確認 %d、一部確認（訂正つき）%d、反証検査なし（REP）%d |" % (
        c["by_verdict"]["CONFIRMED"], c["by_verdict"]["PARTLY_CONFIRMED"], c["by_verdict"]["NOT_SECOND_VERIFIED"]))
    o.append("| 検査担当が付けた重さ | 高 %d、中 %d、低 %d |" % (c["by_severity"]["HIGH"], c["by_severity"]["MEDIUM"], c["by_severity"]["LOW"]))
    o.append("| 停止時点の状態 | %s |" % "、".join("%s %d" % (k, v) for k, v in c["by_state_at_stop"].items()))
    o.append("| 担当する予定だった段階 | %s |" % "、".join("%s %d" % (k, v) for k, v in sorted(c["by_assigned_stage"].items())))
    o.append("| 公開中の版（`09_APPROX_STUDY/`） | 59 件とも残っている |")
    o.append("")
    o.append("## 状態の決め方")
    o.append("")
    for k, v in r6["state_rules"].items():
        o.append("- **%s**：%s" % (k, v))
    o.append("")
    o.append("## 指摘のまとまり（8 群）と、新研究で使うときの注意")
    o.append("")
    for n, g in enumerate(r6["groups"], 1):
        o.append("### 群 %d：%s" % (n, g["title"]))
        o.append("")
        o.append("- 指摘：%s" % "、".join("[%s](#%s)" % (x, x.lower()) for x in g["finding_ids"]))
        o.append("- 内容：%s" % g["what"])
        o.append("- 新研究で使うときの注意：%s" % g["consequence_for_reuse"])
        o.append("")
    o.append("## 指摘ごとの記録")
    o.append("")
    SEV = {"HIGH": "高", "MEDIUM": "中", "LOW": "低"}
    VER = {"CONFIRMED": "反証検査で確認", "PARTLY_CONFIRMED": "一部確認（訂正つき）", "NOT_SECOND_VERIFIED": "反証検査なし"}
    for f in r6["findings"]:
        o.append('<a id="%s"></a>' % f["id"].lower())
        o.append("")
        o.append("### %s" % f["id"])
        o.append("")
        o.append("- **重さ／判定**：%s／%s" % (SEV.get(f["severity"], f["severity"]), VER.get(f["verdict"], f["verdict"])))
        o.append("- **内容**：%s" % f["statement"])
        aff = f.get("affects")
        if isinstance(aff, list):
            aff = "、".join(aff)
        o.append("- **影響する成果**：%s" % aff)
        o.append("- **再現の手順の所在**：%s" % loc_md(f.get("repro") or "（記載なし）", 1))
        stages = f.get("assigned_stage") or "—"
        if f.get("also_stages"):
            stages += "（ほかに %s）" % "、".join(f["also_stages"])
        o.append("- **担当する予定だった段階**：%s" % stages)
        o.append("- **予定していた対応**：%s" % (f.get("decision") or "（記載なし）"))
        o.append("- **停止時点の状態**：%s" % f["state_at_stop"])
        if f.get("self_report_status"):
            o.append("- **作業担当の自己申告**：%s" % f["self_report_status"])
        o.append("- **状態の根拠**：%s" % loc_md(f.get("state_evidence") or "（記載なし）", 1))
        if f.get("remaining_at_stop"):
            o.append("- **停止時点で残っていた作業**：%s" % f["remaining_at_stop"])
        o.append("- **公開中の版**：%s。%s" % (f["in_committed_tree"], f.get("committed_check") or ""))
        o.append("")
    o.append("## この登録簿が扱っていないこと")
    o.append("")
    for x in r6["not_covered"]:
        o.append("- %s" % x)
    open(os.path.join(ARCH_DIR, "index_detail", "FINDINGS_59.md"), "w", encoding="utf-8").write("\n".join(o) + "\n")

    # ---------------------------------------------------------------- not covered
    o = []
    o.append("# 分類担当が読んでいない範囲・分類できなかった範囲")
    o.append("")
    o.append("[INDEX.md](../INDEX.md) の 9 節の詳細。観点ごとに、分類担当が申告した内容をそのまま載せる。")
    o.append("")
    for L in LENSES:
        o.append("## %s（%s）" % (L, LENS_NAME[L]))
        o.append("")
        for x in meta[L]["not_covered"]:
            o.append("- %s" % loc_md(x, 1))
        o.append("")
    o.append("## R6（%s）" % LENS_NAME["R6"])
    o.append("")
    o.append("[FINDINGS_59.md](FINDINGS_59.md) の末尾を参照。")
    open(os.path.join(ARCH_DIR, "index_detail", "NOT_COVERED.md"), "w", encoding="utf-8").write("\n".join(o) + "\n")

    # ---------------------------------------------------------------- INDEX.md
    head = open(os.path.join(SRC, "INDEX_head.md"), encoding="utf-8").read()
    mid5 = open(os.path.join(SRC, "INDEX_reuse_intro.md"), encoding="utf-8").read()
    tail = open(os.path.join(SRC, "INDEX_tail.md"), encoding="utf-8").read()

    cnt = Counter(it["state_category"] for it in items)
    n_reuse = sum(1 for it in items if it.get("reuse_candidate"))
    counts_tbl = ["| 区分 | 項目数 |", "|---|---|"]
    for k in (1, 2, 3, 4):
        counts_tbl.append("| %d %s | %d |" % (k, CAT[k], cnt[k]))
    counts_tbl.append("| 5 新研究への再利用候補（1〜4 と重ねて付ける） | %d |" % n_reuse)
    counts_tbl.append("| 合計（区分 1〜4） | %d |" % len(items))
    counts_tbl.append("| 別に：第2回の指摘の登録簿 | 59 |")
    head = head.replace("{{COUNTS}}", "\n".join(counts_tbl))

    o = [head.rstrip("\n"), ""]

    def locs_short(it, n=2):
        ls = it["locations"]
        out = [loc_md(l, 0) for l in ls[:n]]
        if len(ls) > n:
            out.append("ほか %d" % (len(ls) - n))
        return "<br>".join(out)

    # --- category 1 (blocks)
    o.append("## 2. 区分 1：検証済み成果")
    o.append("")
    o.append("ここでの「検証済み」は、0.3 の定義を満たすものだけである。どの項目も、**架空データ**と**独立概念モデル**の範囲に限り、"
             "下の「言ってよいこと」の文面に狭めてある。旧研究の文書にある元の文面のうち使ってはいけないものは、詳細の「使ってはいけない記述」に挙げた。")
    o.append("")
    for t, (tname, fname) in TOPICS.items():
        sel = [by_id[i] for i in TOPIC_IDS[t] if by_id[i]["state_category"] == 1]
        if not sel:
            continue
        o.append("### %s（%s）" % (tname, t))
        o.append("")
        for it in sel:
            o.append("**%s　%s**" % (dlink(it["id"]), it["title"]))
            o.append("")
            o.append("- 言ってよいこと：%s" % it["claim_that_stands"])
            o.append("- 確かめた者：%s" % it["checked_by"])
            if it["id"] in C1_NOTE:
                o.append("- 根拠の強さ：%s" % C1_NOTE[it["id"]])
            o.append("- 所在：%s" % "、".join(loc_md(l, 0) for l in it["locations"][:3]) +
                     ("　ほか %d" % (len(it["locations"]) - 3) if len(it["locations"]) > 3 else ""))
            nb = len(it.get("claims_not_to_rely_on") or [])
            o.append("- 使ってはいけない記述：%d 件（詳細を参照）　／　再利用：%s" % (nb, routes(it)))
            o.append("")

    def table_section(catno, title, intro):
        o.append("## %d. 区分 %d：%s" % (catno + 1, catno, title))
        o.append("")
        o.append(intro)
        o.append("")
        for t, (tname, fname) in TOPICS.items():
            sel = [by_id[i] for i in TOPIC_IDS[t] if by_id[i]["state_category"] == catno]
            if not sel:
                continue
            o.append("### %s（%s）" % (tname, t))
            o.append("")
            o.append("| 項目 | 成果と内容 | 所在（主なもの） | 確かめた者 | 再利用 |")
            o.append("|---|---|---|---|---|")
            for it in sel:
                o.append("| %s | **%s**<br>%s | %s | %s | %s |" % (
                    dlink(it["id"]), cell(it["title"]), cell(short(it["what"])), locs_short(it),
                    cell(short(it["checked_by"], 60)), routes(it)))
            o.append("")

    table_section(2, CAT[2],
                  "作られてはいるが、独立の検査を受けていないもの、第2回の指摘の影響が残るもの、中断した修正の自己申告だけのもの、"
                  "文面の一部に誤りがあると分かっているもの。**検証済みとして扱わない。**")
    table_section(3, CAT[3],
                  "式、モデル化の案、保留した近似候補、設計はしたが実装（または検証）していない修正、評価者の提案。**成果ではなく材料である。**")
    table_section(4, CAT[4],
                  "分かっている不具合、未解決の問い、限界、行っていない確認。5.1 は成果の側から見た項目、5.2 は第2回の指摘 59 件の登録簿である。")
    # rename heading of cat 4 items block to 5.1 and add 5.2
    idx = max(i for i, l in enumerate(o) if l.startswith("## 5. 区分 4"))
    o.insert(idx + 4, "### 5.1 成果の側から見た不具合・未解決事項")
    o.insert(idx + 5, "")
    # demote topic headings under 5.1 to ####
    for i in range(idx + 6, len(o)):
        if o[i].startswith("### "):
            o[i] = "#" + o[i]
    o.append("### 5.2 第2回の独立検査の指摘 59 件（登録簿）")
    o.append("")
    c = r6["counts"]
    o.append("第2回の独立検査は、`43ba5d7` のコードと文書に対して 5 つの観点で行った。指摘は 59 件で、反証検査担当が退けたものは無い。"
             "公開中の `09_APPROX_STUDY/` には **59 件とも残っている**（修正は反映されていない）。"
             "指摘ごとの内容・再現の手順の所在・停止時点の状態は [index_detail/FINDINGS_59.md](index_detail/FINDINGS_59.md) にある。")
    o.append("")
    o.append("| 分け方 | 件数 |")
    o.append("|---|---|")
    o.append("| 判定 | 反証検査で確認 %d、一部確認（訂正つき）%d、反証検査なし（REP の 18 件。主担当が検査のスクリプトを再実行して再現、出力は未保存）%d |" % (
        c["by_verdict"]["CONFIRMED"], c["by_verdict"]["PARTLY_CONFIRMED"], c["by_verdict"]["NOT_SECOND_VERIFIED"]))
    o.append("| 検査担当が付けた重さ | 高 %d（NUM-1、RED-1、REC-1）、中 %d、低 %d |" % (
        c["by_severity"]["HIGH"], c["by_severity"]["MEDIUM"], c["by_severity"]["LOW"]))
    o.append("| 停止時点の状態 | %s |" % "、".join("%s %d" % (k, v) for k, v in c["by_state_at_stop"].items()))
    o.append("")
    o.append("| 群 | まとまり | 指摘 |")
    o.append("|---|---|---|")
    for n, g in enumerate(r6["groups"], 1):
        o.append("| %d | %s | %s |" % (n, cell(g["title"]), "、".join(
            "[%s](index_detail/FINDINGS_59.md#%s)" % (x, x.lower()) for x in g["finding_ids"])))
    o.append("")
    o.append("| 指摘 | 重さ | 判定 | 予定の段階 | 停止時点の状態 |")
    o.append("|---|---|---|---|---|")
    for f in r6["findings"]:
        o.append("| [%s](index_detail/FINDINGS_59.md#%s) | %s | %s | %s | %s |" % (
            f["id"], f["id"].lower(), SEV.get(f["severity"], f["severity"]), VER.get(f["verdict"], f["verdict"]),
            f.get("assigned_stage") or "—", cell(f["state_at_stop"])))
    o.append("")

    # --- category 5
    o.append(mid5.rstrip("\n"))
    o.append("")
    for t, (tname, fname) in TOPICS.items():
        sel = [by_id[i] for i in TOPIC_IDS[t] if by_id[i].get("reuse_candidate")]
        if not sel:
            continue
        o.append("#### %s（%s）" % (tname, t))
        o.append("")
        o.append("| 項目 | 区分 | ルート | 成果 | 使い道（冒頭） |")
        o.append("|---|---|---|---|---|")
        for it in sel:
            o.append("| %s | %d | %s | %s | %s |" % (
                dlink(it["id"]), it["state_category"], routes(it), cell(it["title"]),
                cell(short(it.get("reuse_how"), 90))))
        o.append("")
    non = [it for it in items if not it.get("reuse_candidate")]
    o.append("### 6.4 再利用の候補にしなかった項目（%d 件）" % len(non))
    o.append("")
    o.append("分類担当が候補にしなかった項目。理由は各項目の詳細にある。")
    o.append("")
    o.append("| 区分 | 項目 |")
    o.append("|---|---|")
    for k in (1, 2, 3, 4):
        sel = [it for it in non if it["state_category"] == k]
        if sel:
            o.append("| %d | %s |" % (k, "、".join(dlink(it["id"]) for it in sel)))
    o.append("")

    # --- topic quick table
    o.append("## 7. 主題別の早見表")
    o.append("")
    o.append("同じ対象を複数の観点が扱っている場合、項目は主題ごとにまとめてある。区分が違うのは、対象が違うためである"
             "（例：測定の結果そのものは区分 1、それを一般化した README の文は区分 2、その穴は区分 4）。")
    o.append("")
    o.append("| 主題 | 区分 1 | 区分 2 | 区分 3 | 区分 4 | 詳細 |")
    o.append("|---|---|---|---|---|---|")
    for t, (tname, fname) in TOPICS.items():
        row = []
        for k in (1, 2, 3, 4):
            sel = [i for i in TOPIC_IDS[t] if by_id[i]["state_category"] == k]
            row.append("<br>".join(dlink(i) for i in sel) if sel else "—")
        o.append("| %s %s | %s | [%s](index_detail/%s) |" % (t, tname, " | ".join(row), fname, fname))
    o.append("")
    o.append(tail.rstrip("\n"))
    o.append("")
    open(os.path.join(ARCH_DIR, "INDEX.md"), "w", encoding="utf-8").write("\n".join(o))

    # ---------------------------------------------------------------- reports to stdout
    print("items", len(items), dict(cnt), "reuse", n_reuse)
    print("unresolved path mentions:", len(set(MISSING)))
    for m in sorted(set(MISSING))[:40]:
        print("   ", m[:200])
    # coverage of the old study folder by item locations
    covered = set()
    allloc = []
    for it in items:
        for l in it["locations"]:
            allloc += [p.rstrip("/.") for p in PATH_RE.findall(l)]
    study_files = [f for f in TRACKED if f.startswith(STUDY + "09_APPROX_STUDY/")]
    unc = []
    for f in study_files:
        if any(f == p or f.startswith(p + "/") for p in allloc):
            continue
        unc.append(f)
    print("old-study files:", len(study_files), "not referenced by any item location:", len(unc))
    for f in sorted(unc):
        print("   ", f)
    arch_files = [f for f in TRACKED if f.startswith(ARCH + "materials/")]
    unc2 = Counter()
    for f in arch_files:
        if any(f == p or f.startswith(p + "/") for p in allloc):
            continue
        unc2["/".join(f[len(ARCH):].split("/")[:3])] += 1
    print("archive material files:", len(arch_files), "not referenced:", sum(unc2.values()))
    for k, v in sorted(unc2.items()):
        print("   ", k, v)


main()
