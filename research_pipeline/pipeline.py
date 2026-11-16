"""資料収集 → 論文改訂 → 教材改訂 → 書き出し → Dropbox 同期計画 を連動させ、途中から再開する。

    python3 -I research_pipeline/pipeline.py run      [--force] [--structlab <structlab の src>]
    python3 -I research_pipeline/pipeline.py status
    python3 -I research_pipeline/pipeline.py impact
    python3 -I research_pipeline/pipeline.py approve  --scope paper|education --keys K1,K2|--all-new --reason 理由
    python3 -I research_pipeline/pipeline.py sync-plan
    python3 -I research_pipeline/pipeline.py sync-record --rel 相対パス --dropbox-path パス --size N --method mcp

途中再開: 各段階の入力指紋と結果を STATUS.json に保存し、入力が変わっていない完了済みの段階は飛ばす。
失敗した段階は failed として記録し、次回はそこからやり直す。書き込みは全て一時ファイル経由（途中停止で壊れない）。
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from research_pipeline import ledger as LG  # noqa: E402
from research_pipeline import render as RD  # noqa: E402
from research_pipeline import trace as TR  # noqa: E402
from research_pipeline.common import (atomic_write, digest, file_sha256, read_csv, read_json,  # noqa: E402
                                      research_root, write_csv, write_json)

JST = timezone(timedelta(hours=9))
STAGES = ("ledgers", "trace", "learning", "render", "office", "sync_plan")
# 同期先。既存の同名研究がある場合は、統合方針が決まるまで別名のフォルダに保存する（第7部）
DROPBOX_ROOT = os.environ.get("AI_RESEARCH_DROPBOX_ROOT", "/AI_WORLD_PRIMARY_RESEARCH")
SYNC_COLS = ["rel_path", "sha256", "size", "dropbox_path", "method", "synced_at"]
QUEUE_COLS = ["rel_path", "sha256", "size", "dropbox_path", "kind", "reason"]
REVLOG_COLS = ["at", "scope", "key", "old_fp", "new_fp", "reason", "reviewer"]
BINARY = {".pdf", ".docx", ".png", ".zip", ".gz"}
NOT_SYNCED = {"sync/upload_queue.csv", "sync/unsynced_manifest.csv"}
THRESHOLDS = {  # methodology.md「初版執筆トリガー」と同じ値（事前定義）
    "min_sources_per_paper": 20, "min_s1_s4_sources": 5, "min_v1_sources": 2,
    "max_unverified_cited_claims": 0, "min_limitation_units": 1}


def now() -> str:
    return datetime.now(JST).isoformat(timespec="seconds")


def files_fp(root: Path, patterns: list[str]) -> str:
    return digest({str(p.relative_to(root)): file_sha256(p)
                   for pat in patterns for p in sorted(root.glob(pat)) if p.is_file()})


# ---------------- 段階 ----------------
def stage_ledgers(root: Path, o) -> dict:
    led = LG.load(root)
    if led.errors:
        raise RuntimeError("台帳エラー:\n" + "\n".join(led.errors[:30]))
    srcs = led.tables["sources"]
    tiers = {}
    for s in srcs:
        tiers[s["source_tier"]] = tiers.get(s["source_tier"], 0) + 1
    return {"sources": len(srcs), "claims": len(led.tables["claims"]), "tiers": tiers,
            "people": len(led.tables["people"]), "warnings": led.warnings}


def coverage(a: TR.Audit) -> list[dict]:
    srcs = a.led.index("sources")
    cited = sorted({c for it in a.units.values() for c in it.block.ids("claims")})
    claims = a.led.index("claims")
    used_src = {claims[c]["source_id"] for c in cited if c in claims}
    s14 = {s for s in used_src if srcs.get(s, {}).get("source_tier") in ("S1", "S2", "S3", "S4")}
    s14 |= {s for s in used_src if any(p and a.led.index("people").get(p, {}).get("person_tier") in
                                        ("S1", "S2", "S3", "S4")
                                        for p in LG.split_ids(srcs.get(s, {}).get("person_id", "")))}
    v1 = {s for s in used_src if srcs.get(s, {}).get("source_tier") == "V1"}
    unverified = [c for c in cited if claims.get(c, {}).get("verification_status") not in LG.VERIFIED]
    lim = [u for u in a.units.values() if u.block.kind == "limitation"]
    t = THRESHOLDS
    return [
        {"check": "論文が引く資料数", "value": len(used_src), "need": f">= {t['min_sources_per_paper']}",
         "ok": len(used_src) >= t["min_sources_per_paper"]},
        {"check": "S1〜S4（開発者・社員・協力者本人）に由来する資料", "value": len(s14),
         "need": f">= {t['min_s1_s4_sources']}", "ok": len(s14) >= t["min_s1_s4_sources"]},
        {"check": "独立実証（V1）の資料", "value": len(v1), "need": f">= {t['min_v1_sources']}",
         "ok": len(v1) >= t["min_v1_sources"]},
        {"check": "引用した主張のうち原文未照合", "value": len(unverified),
         "need": f"<= {t['max_unverified_cited_claims']}", "ok": len(unverified) <= t["max_unverified_cited_claims"]},
        {"check": "限界・未確認事項の段落", "value": len(lim), "need": f">= {t['min_limitation_units']}",
         "ok": len(lim) >= t["min_limitation_units"]},
    ]


def impact_lines(a: TR.Audit) -> list[str]:
    out = []
    for it in a.stale():
        if it.status == "STALE":
            out.append(f"- {it.key}: " + "；".join(it.causes))
    return out


def stage_trace(root: Path, o) -> dict:
    a = TR.audit(root)
    cov = coverage(a)
    lines = [f"# 追跡監査報告（自動生成 {now()}）", "",
             f"- 論文段落: {len(a.units)} ／ 教材項目: {len(a.edu_items)} ／ 学習目標: {len(a.objectives)}",
             f"- エラー: {len(a.errors)} ／ 警告: {len(a.warnings)}",
             f"- 状態: OK {sum(i.status == 'OK' for i in [*a.units.values(), *a.edu_items.values()])} ／ "
             f"NEW（未承認） {sum(i.status == 'NEW' for i in [*a.units.values(), *a.edu_items.values()])} ／ "
             f"STALE（要改訂） {sum(i.status == 'STALE' for i in [*a.units.values(), *a.edu_items.values()])}",
             "", "## 初版執筆トリガー（事前定義の閾値。未達の間は「暫定版」）", "",
             "| 確認項目 | 値 | 基準 | 判定 |", "|---|---|---|---|"]
    lines += [f"| {c['check']} | {c['value']} | {c['need']} | {'達成' if c['ok'] else '未達'} |" for c in cov]
    lines += ["", "## エラー", ""] + ([f"- {e}" for e in a.errors] or ["- なし"])
    lines += ["", "## 警告", ""] + ([f"- {w}" for w in a.warnings] or ["- なし"])
    lines += ["", "## 要改訂（上流の資料・主張・論文段落の変更による）", ""] + (impact_lines(a) or ["- なし"])
    atomic_write(root / "audit" / "trace_report.md", "\n".join(lines) + "\n")
    if a.errors:
        raise RuntimeError(f"追跡監査エラー {len(a.errors)} 件（audit/trace_report.md）:\n" + "\n".join(a.errors[:20]))
    return {"units": len(a.units), "edu_items": len(a.edu_items), "warnings": len(a.warnings),
            "new": sum(i.status == "NEW" for i in a.stale()), "stale": sum(i.status == "STALE" for i in a.stale()),
            "coverage_ok": all(c["ok"] for c in cov)}


def stage_learning(root: Path, o) -> dict:
    """第10部: 学習設計台帳の検証と更新、問題台帳、論文と教材の差分表。"""
    from research_learning import learning as LN
    a = TR.audit(root)
    if a.errors:
        raise RuntimeError("監査エラーがあるため学習設計を更新しない")
    rows = LN.read_csv(root / "education" / "learning_design.csv")
    errs = LN.validate(rows, a)
    if errs:
        raise RuntimeError("学習設計台帳のエラー:\n" + "\n".join(errs[:20]))
    rows = LN.refresh(root, a)
    qrows = LN.question_rows(a)
    write_csv(root / "education" / "question_ledger.csv", LN.QCOLS, qrows)
    blocks = LN.diff_blocks(a, rows)
    for d in a.papers:
        name = _out_name(root, d).replace("papers/", "education/").rsplit("/", 1)[0]
        write_json(root / "build" / "layout" / f"{name}/09_論文と教材の差分表.json", blocks)
        atomic_write(root / "exports" / f"{name}/09_論文と教材の差分表.md", RD.to_markdown(blocks))
    imp = {k: sum(r["importance"] == k for r in rows) for k in "SABC"}
    return {"importance": imp, "questions": len(qrows),
            "questions_pending_review": sum(q["answer_status"] != "公開可" for q in qrows),
            "flashcards": a.flashcards, "s_without_independent_evidence":
                [r["unit_id"] for r in rows if r["evidence_warning"].startswith("S相当")]}


def _docs(a: TR.Audit):
    for d in a.papers:
        yield "paper", d
    for d in a.edus:
        yield "education", d


def _out_name(root: Path, d) -> str:
    rel = d.path.relative_to(root)
    return str(rel.parent / rel.name.replace(".src.md", ""))


def stage_render(root: Path, o) -> dict:
    a = TR.audit(root)
    if a.errors:
        raise RuntimeError("監査エラーがあるため書き出さない")
    written = []
    for scope, d in _docs(a):
        name = _out_name(root, d)
        modes = ["quiz_questions", "quiz_answers"] if any(b.kind == "quiz" for b in d.blocks) else ["full"]
        for mode in modes:
            blocks, _ = RD.layout(a, d, scope, mode)
            suffix = {"full": "", "quiz_questions": "_問題", "quiz_answers": "_解答解説"}[mode]
            out = root / "exports" / f"{name}{suffix}.md"
            atomic_write(out, RD.to_markdown(blocks))
            write_json(root / "build" / "layout" / f"{name}{suffix}.json", blocks)
            written.append(str(out.relative_to(root)))
    # 正本が無くなった文書（旧版の教材など）の中間ファイルと書き出しを消す。残すと次の office で旧版を再生成してしまう
    keep = {str(Path(w).with_suffix("")).split("exports/", 1)[-1] for w in written}
    removed = []
    for f in sorted((root / "build" / "layout").rglob("*.json")):
        rel = str(f.relative_to(root / "build" / "layout").with_suffix(""))
        if rel in keep or rel.endswith("09_論文と教材の差分表"):
            continue
        f.unlink()
        for ext in (".md", ".pdf", ".docx"):
            g = root / "exports" / (rel + ext)
            if g.exists():
                g.unlink()
        removed.append(rel)
    return {"written": written, "removed_stale": removed}


def stage_office(root: Path, o) -> dict:
    src = Path(o.structlab).resolve() if getattr(o, "structlab", None) else None
    results = {}
    for f in sorted((root / "build" / "layout").rglob("*.json")):
        rel = f.relative_to(root / "build" / "layout").with_suffix("")
        blocks = read_json(f)
        title = blocks[0]["text"] if blocks else rel.name
        res = RD.office(blocks, root / "exports" / f"{rel}.pdf", root / "exports" / f"{rel}.docx", title, src)
        results[str(rel)] = res
    write_json(root / "audit" / "office_quality.json", results)
    bad = [k for k, v in results.items() if not v.get("ok")]
    return {"documents": len(results), "not_ok": bad,
            "skipped_reason": next((v["skipped"] for v in results.values() if v.get("skipped")), "")}


BACKUP_PREFIXES = ("revisions/2026-11-16_pre_correction/", "revisions/education_v0.1.0/", "revisions/exports_pre_correction/")


def sync_plan(root: Path) -> dict:
    synced = {r["rel_path"]: r for r in read_csv(root / "sync" / "synced_manifest.csv")}
    by_path: dict[str, list] = {}
    for r in read_csv(root / "sync" / "synced_manifest.csv"):
        by_path.setdefault(r["rel_path"], []).append(r)
    queue, unsynced = [], []
    synced_shas = {r["sha256"] for r in read_csv(root / "sync" / "synced_manifest.csv")}
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.suffix == ".tmp":
            continue
        rel = p.relative_to(root).as_posix()
        if rel.startswith("build/") or rel in NOT_SYNCED:
            continue
        sha = file_sha256(p)
        hist = by_path.get(rel, [])
        if any(h["sha256"] == sha for h in hist):
            continue
        if rel.startswith(BACKUP_PREFIXES) and sha in synced_shas:
            # 旧版のローカル退避：同じ内容が Dropbox の元のパスに保存済みなら、重複して送らない
            unsynced.append({"rel_path": rel, "sha256": sha, "size": p.stat().st_size, "dropbox_path": "",
                             "kind": "backup", "reason": "旧版の退避コピー。同一内容が Dropbox の元のパスに保存済み（重複のため送らない）"})
            continue
        rev = len(hist) + 1
        target = f"{DROPBOX_ROOT}/{rel}" if rev == 1 else \
            f"{DROPBOX_ROOT}/{Path(rel).with_suffix('').as_posix()}.r{rev}{p.suffix}"
        row = {"rel_path": rel, "sha256": sha, "size": p.stat().st_size, "dropbox_path": target,
               "kind": "binary" if p.suffix.lower() in BINARY else "text"}
        if row["kind"] == "binary":
            row["reason"] = ("バイナリ。Dropbox コネクタ（テキスト専用）では保存不可。structlab の DropboxOutput と "
                             "Secrets（DROPBOX_APP_KEY / DROPBOX_REFRESH_TOKEN）による同期が必要（未実装）")
            unsynced.append(row)
        else:
            row["reason"] = "新規" if rev == 1 else f"変更（第{rev}版として追加。既存は上書きしない）"
            queue.append(row)
    write_csv(root / "sync" / "upload_queue.csv", QUEUE_COLS, queue)
    write_csv(root / "sync" / "unsynced_manifest.csv", QUEUE_COLS, queue + unsynced)
    return {"queue_text": len(queue), "unsynced_binary": len(unsynced), "already_synced_paths": len(synced)}


def stage_sync_plan(root: Path, o) -> dict:
    return sync_plan(root)


RUNNERS = {"ledgers": stage_ledgers, "trace": stage_trace, "learning": stage_learning, "render": stage_render,
           "office": stage_office, "sync_plan": stage_sync_plan}


def stage_inputs(root: Path, name: str, o) -> str:
    led = files_fp(root, [v[0] for v in LG.SCHEMAS.values()])
    src = files_fp(root, ["papers/**/*.src.md", "education/**/*.src.md", "audit/excerpt_verification.csv",
                          "revisions/trace_lock.json"])
    code = digest([files_fp(Path(__file__).resolve().parent, ["*.py"]),
                   files_fp(Path(__file__).resolve().parent.parent / "research_learning", ["*.py"])])
    if name == "ledgers":
        return digest([led, code])
    if name in ("trace", "render", "learning"):
        src = digest([src, files_fp(root, ["education/*.csv", "education/**/*.csv"])])
        return digest([led, src, code, name])
    if name == "office":
        return digest([files_fp(root, ["build/layout/**/*.json"]), str(getattr(o, "structlab", "")), code])
    return "always"  # sync_plan は毎回作り直す


def run(root: Path, o) -> int:
    status_path = root / "STATUS.json"
    st = read_json(status_path, {"schema": "ai-research-status/1", "stages": {}})
    st["last_run_started"] = now()
    rc = 0
    for name in STAGES:
        fp = stage_inputs(root, name, o)
        prev = st["stages"].get(name, {})
        if not o.force and prev.get("status") == "done" and prev.get("input_fp") == fp and fp != "always":
            print(f"[skip] {name}: 入力が前回の完了時から変わっていない（再開時は飛ばす）")
            continue
        print(f"[run ] {name}")
        try:
            summary = RUNNERS[name](root, o)
            st["stages"][name] = {"status": "done", "input_fp": fp, "finished_at": now(), "summary": summary}
        except Exception as e:  # noqa: BLE001  段階の失敗は記録して停止（次回はここから）
            st["stages"][name] = {"status": "failed", "input_fp": fp, "finished_at": now(), "error": str(e)[:4000]}
            print(f"[FAIL] {name}: {e}")
            rc = 1
            break
        finally:
            write_json(status_path, st)
    failed = [n for n, v in st["stages"].items() if v.get("status") == "failed"]
    st["next_action"] = (f"失敗した段階 {failed[0]} を修正して run を再実行" if failed else
                         "新資料を台帳へ追加 → run（影響する論文段落・教材が STALE になる）→ 改訂 → approve")
    st["last_run_finished"] = now()
    write_json(status_path, st)
    return rc


def cmd_approve(root: Path, o) -> int:
    a = TR.audit(root)
    if a.errors:
        print("監査エラーがあるため承認できない:\n" + "\n".join(a.errors[:20]))
        return 1
    lock_path = root / "revisions" / "trace_lock.json"
    lock = read_json(lock_path, {"paper": {}, "education": {}})
    scopes = ["paper", "education"] if o.scope == "all" else [o.scope]
    log = read_csv(root / "revisions" / "revision_log.csv")
    for scope in scopes:
        items = a.units if scope == "paper" else a.edu_items
        keys = [k for k, it in items.items() if it.status != "OK"] if o.all_new else LG.split_ids(o.keys or "")
        for k in keys:
            if k not in items:
                print(f"不明なキー {k}")
                return 1
            old = lock.get(scope, {}).get(k, {}).get("fp", "")
            TR.approve(a, lock, scope, [k], o.reason, now())
            log.append({"at": now(), "scope": scope, "key": k, "old_fp": old, "new_fp": items[k].fp,
                        "reason": o.reason, "reviewer": o.reviewer})
    write_json(lock_path, lock)
    write_csv(root / "revisions" / "revision_log.csv", REVLOG_COLS, log)
    print(f"承認 {len(log)} 件（累計）。revisions/revision_log.csv に記録")
    return 0


def cmd_sync_record(root: Path, o) -> int:
    p = root / o.rel
    if not p.is_file():
        print("ファイルが無い")
        return 1
    if int(o.size) != p.stat().st_size:
        print(f"サイズ不一致（ローカル {p.stat().st_size} / Dropbox {o.size}）。同期済みにしない")
        return 1
    rows = read_csv(root / "sync" / "synced_manifest.csv")
    rows.append({"rel_path": o.rel, "sha256": file_sha256(p), "size": o.size, "dropbox_path": o.dropbox_path,
                 "method": o.method, "synced_at": now()})
    write_csv(root / "sync" / "synced_manifest.csv", SYNC_COLS, rows)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "status", "impact", "approve", "sync-plan", "sync-record"])
    ap.add_argument("--root", type=Path)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--structlab", help="structlab-exam の src フォルダ（PDF/Word 出力に再利用）")
    ap.add_argument("--scope", choices=["paper", "education", "all"], default="all")
    ap.add_argument("--keys")
    ap.add_argument("--all-new", action="store_true")
    ap.add_argument("--reason", default="")
    ap.add_argument("--reviewer", default="Claude Code（自動監査＋自己レビュー。人間の確認は未実施）")
    ap.add_argument("--rel")
    ap.add_argument("--dropbox-path")
    ap.add_argument("--size")
    ap.add_argument("--method", default="mcp")
    o = ap.parse_args()
    root = (o.root or research_root()).resolve()
    if o.cmd == "run":
        return run(root, o)
    if o.cmd == "status":
        print(atomic_read(root / "STATUS.json"))
        return 0
    if o.cmd == "impact":
        a = TR.audit(root)
        print("\n".join(impact_lines(a)) or "要改訂なし")
        return 0
    if o.cmd == "approve":
        if not o.reason:
            print("--reason が必要")
            return 1
        return cmd_approve(root, o)
    if o.cmd == "sync-plan":
        print(sync_plan(root))
        return 0
    return cmd_sync_record(root, o)


def atomic_read(p: Path) -> str:
    return p.read_text(encoding="utf-8") if p.exists() else "STATUS.json なし"


if __name__ == "__main__":
    sys.exit(main())
