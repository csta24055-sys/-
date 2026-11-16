"""台帳の原文抜粋を、保存した原文スナップショットと一字一句照合する（第8部 フェーズ3・6）。

使い方:
    python3 -I research_pipeline/verify_excerpts.py --snapshots <SRC-xxxxxx.html を置いたフォルダ> [--root 研究フォルダ]

- スナップショット（原文の全文）は著作権に配慮して研究フォルダには保存しない。保存するのは SHA-256 と照合結果だけ。
- 照合は NFKC・引用符/ダッシュの統一・空白の圧縮・小文字化の後の部分一致。言い換え・要約は一致にならない。
- 一致した場合は、その抜粋を含む見出しを HTML から特定し、台帳の original_position と比べる。
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from research_pipeline import htmltext as H  # noqa: E402
from research_pipeline import ledger as LG  # noqa: E402
from research_pipeline.common import file_sha256, research_root, write_csv  # noqa: E402

COLUMNS = ["claim_id", "source_id", "snapshot_sha256", "checked_at", "found", "detected_section",
           "ledger_position", "position_match"]
ROLE_COLUMNS = ["role_evidence_id", "person_id", "source_id", "snapshot_sha256", "checked_at", "found",
                "detected_section", "ledger_position", "position_match"]
JST = timezone(timedelta(hours=9))


def _load_snapshot(snapshots: Path, sid: str):
    """SRC-xxxxxx.html（HTML）か SRC-xxxxxx.txt（PDF などから抽出した本文）を読む。無ければ None。"""
    f = snapshots / f"{sid}.html"
    if f.exists():
        raw = f.read_text(encoding="utf-8", errors="replace")
        vis, _ = H.extract(raw)
        return (file_sha256(f), H.norm(vis), H.sections(raw), None)
    f = snapshots / f"{sid}.txt"
    if f.exists():
        return (file_sha256(f), H.norm(f.read_text(encoding="utf-8", errors="replace")), None, "txt")
    return None


def _check(snap, ex: str, pos: str) -> tuple[bool, str, bool]:
    sha, text, secs, kind = snap
    found = H.contains(text, ex)
    if not found:
        return False, "", False
    if kind == "txt":
        # 見出し構造が無い本文: 台帳の位置（見出し）が抜粋より前に現れるかで確かめる
        i = text.find(H.norm(ex))
        heads = [h for h in pos.split(" / ") if H.norm(h)]
        ok = any(0 <= text.find(H.norm(h)) <= max(i, 0) for h in heads) or pos == "冒頭"
        return True, "(本文テキスト)", ok
    sec = H.locate(secs, ex)
    match = bool(sec) and any(H.norm(h) and H.norm(h) in H.norm(pos) for h in sec.split(" / "))
    return True, sec, match


def run(root: Path, snapshots: Path) -> dict:
    led = LG.load(root)
    cache: dict[str, tuple] = {}
    counts = {"checked": 0, "found": 0, "not_found": 0, "no_snapshot": 0, "position_mismatch": 0,
              "role_checked": 0, "role_found": 0, "role_not_found": 0}
    now = datetime.now(JST).isoformat(timespec="seconds")

    def snap_of(sid):
        if sid not in cache:
            cache[sid] = _load_snapshot(snapshots, sid)
        return cache[sid]

    rows = []
    for c in led.tables.get("claims", []):
        ex = c["original_language_excerpt_short"]
        if not ex:
            continue
        sid = c["source_id"]
        snap = snap_of(sid)
        if snap is None:
            counts["no_snapshot"] += 1
            rows.append({"claim_id": c["claim_id"], "source_id": sid, "checked_at": now, "found": "no_snapshot",
                         "ledger_position": c["original_position"]})
            continue
        counts["checked"] += 1
        found, sec, match = _check(snap, ex, c["original_position"])
        counts["found" if found else "not_found"] += 1
        if found and not match:
            counts["position_mismatch"] += 1
        rows.append({"claim_id": c["claim_id"], "source_id": sid, "snapshot_sha256": snap[0], "checked_at": now,
                     "found": "true" if found else "false", "detected_section": sec,
                     "ledger_position": c["original_position"], "position_match": "true" if match else "false"})
    write_csv(root / "audit" / "excerpt_verification.csv", COLUMNS, rows)

    rrows = []
    for r in led.tables.get("role_evidence", []):
        ex, sid = r["excerpt"], r["source_id"]
        if not ex:
            continue
        snap = snap_of(sid)
        if snap is None:
            rrows.append({"role_evidence_id": r["role_evidence_id"], "person_id": r["person_id"], "source_id": sid,
                          "checked_at": now, "found": "no_snapshot", "ledger_position": r["location"]})
            continue
        counts["role_checked"] += 1
        found, sec, match = _check(snap, ex, r["location"])
        counts["role_found" if found else "role_not_found"] += 1
        rrows.append({"role_evidence_id": r["role_evidence_id"], "person_id": r["person_id"], "source_id": sid,
                      "snapshot_sha256": snap[0], "checked_at": now, "found": "true" if found else "false",
                      "detected_section": sec, "ledger_position": r["location"],
                      "position_match": "true" if match else "false"})
    write_csv(root / "audit" / "role_evidence_verification.csv", ROLE_COLUMNS, rrows)
    return counts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshots", required=True, type=Path)
    ap.add_argument("--root", type=Path, default=None)
    o = ap.parse_args()
    counts = run((o.root or research_root()).resolve(), o.snapshots.resolve())
    print(counts)
    return 1 if counts["not_found"] or counts["role_not_found"] else 0


if __name__ == "__main__":
    sys.exit(main())
