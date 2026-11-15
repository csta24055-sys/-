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
JST = timezone(timedelta(hours=9))


def run(root: Path, snapshots: Path) -> dict:
    led = LG.load(root)
    cache: dict[str, tuple] = {}
    rows, counts = [], {"checked": 0, "found": 0, "not_found": 0, "no_snapshot": 0, "position_mismatch": 0}
    now = datetime.now(JST).isoformat(timespec="seconds")
    for c in led.tables.get("claims", []):
        ex = c["original_language_excerpt_short"]
        if not ex:
            continue
        sid = c["source_id"]
        if sid not in cache:
            f = snapshots / f"{sid}.html"
            if f.exists():
                raw = f.read_text(encoding="utf-8", errors="replace")
                vis, _ = H.extract(raw)
                cache[sid] = (file_sha256(f), H.norm(vis), H.sections(raw))
            else:
                cache[sid] = None
        snap = cache[sid]
        if snap is None:
            counts["no_snapshot"] += 1
            rows.append({"claim_id": c["claim_id"], "source_id": sid, "checked_at": now, "found": "no_snapshot",
                         "ledger_position": c["original_position"]})
            continue
        sha, text, secs = snap
        counts["checked"] += 1
        found = H.contains(text, ex)
        sec = H.locate(secs, ex) if found else ""
        pos = c["original_position"]
        match = bool(sec) and any(H.norm(h) and H.norm(h) in H.norm(pos) for h in sec.split(" / "))
        counts["found" if found else "not_found"] += 1
        if found and not match:
            counts["position_mismatch"] += 1
        rows.append({"claim_id": c["claim_id"], "source_id": sid, "snapshot_sha256": sha, "checked_at": now,
                     "found": "true" if found else "false", "detected_section": sec,
                     "ledger_position": pos, "position_match": "true" if match else "false"})
    write_csv(root / "audit" / "excerpt_verification.csv", COLUMNS, rows)
    return counts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshots", required=True, type=Path)
    ap.add_argument("--root", type=Path, default=None)
    o = ap.parse_args()
    counts = run((o.root or research_root()).resolve(), o.snapshots.resolve())
    print(counts)
    return 1 if counts["not_found"] else 0


if __name__ == "__main__":
    sys.exit(main())
