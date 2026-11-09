#!/usr/bin/env python3
"""STEP 10: company-first monthly re-collection.

Order (directive 7.1): per company → check each registered source for change → classify →
append NEEDS_RECHECK events for claims that depend on changed/failed sources (append-only,
original claims are never overwritten) → write a per-company update record → only then
propagate to cross-company relations → write the run record.

    python3 research/tools/monthly_update.py --month 2026-12             # all companies, live HTTP
    python3 research/tools/monthly_update.py --month 2026-12 --company COMPANY_01
    python3 research/tools/monthly_update.py --month 2026-12 --dry-run   # no files written

Classification per source:
  UNCHANGED      sha256 identical (or ETag/Last-Modified identical when --head-only)
  REVISED        reachable, content hash differs              -> claims NEEDS_RECHECK (cause: DATA_CHANGED)
  FETCH_FAILED   network/HTTP error                           -> previous snapshot kept, claims NEEDS_RECHECK (cause: FETCH_FAILED)
  WITHDRAWN      HTTP 404/410                                 -> claims NEEDS_RECHECK (cause: WITHDRAWN)
  MISATTRIBUTED  source record's company_id is not this company -> run aborts for this company (integrity error)

The fetcher is injectable so tests can simulate every case without network access.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import subprocess
import sys
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import append_jsonl, companies, company_dir, read_jsonl, research_root, write_json  # noqa: E402

Fetcher = Callable[[str], dict]  # returns {"status": int, "sha256": str|None, "etag":..., "last_modified":..., "error": str|None}


def curl_fetch(url: str) -> dict:
    """GET via curl (honours the environment's proxy / CA settings). Body is hashed, not stored."""
    try:
        p = subprocess.run(["curl", "-sS", "-L", "--max-time", "120", "-D", "-", "-o", "-", url],
                           capture_output=True, timeout=180)
    except Exception as e:  # noqa: BLE001
        return {"status": 0, "sha256": None, "error": str(e)}
    raw = p.stdout
    if p.returncode != 0:
        return {"status": 0, "sha256": None, "error": p.stderr.decode("utf-8", "ignore")[:300]}
    # split the last header block from the body (-L can produce several blocks)
    status, headers, body = 0, {}, raw
    while body.startswith(b"HTTP/"):
        head, _, body = body.partition(b"\r\n\r\n")
        lines = head.decode("latin-1").split("\r\n")
        status = int(lines[0].split()[1])
        headers = {k.strip().lower(): v.strip() for k, _, v in (ln.partition(":") for ln in lines[1:])}
    return {"status": status, "sha256": hashlib.sha256(body).hexdigest(), "etag": headers.get("etag"),
            "last_modified": headers.get("last-modified"), "error": None if status < 400 else f"HTTP {status}"}


def classify(src: dict, res: dict, company_id: str) -> str:
    if src.get("company_id") != company_id:
        return "MISATTRIBUTED"
    if res.get("status") in (404, 410):
        return "WITHDRAWN"
    if res.get("error") or not res.get("sha256"):
        return "FETCH_FAILED"
    return "UNCHANGED" if res["sha256"] == src.get("sha256") else "REVISED"


def update_company(c: dict, month: str, fetch: Fetcher, now: str, dry: bool) -> dict:
    cdir = company_dir(c)
    cid = c["company_id"]
    sources = read_jsonl(cdir / "ledger" / "sources.jsonl")
    passages = {p["passage_id"]: p for p in read_jsonl(cdir / "ledger" / "passages.jsonl")}
    claims = [x for a in sorted((cdir / "axes").glob("AXIS_*")) for x in read_jsonl(a / "CLAIMS.jsonl")]
    upd_id = f"UPD-{month}-{c['short_code']}"
    rec = {"update_id": upd_id, "company_id": cid, "month": month, "executed_at": now,
           "sources_checked": 0, "by_class": {}, "sources": [], "claims_needs_recheck": [], "errors": []}
    changed = {}
    for s in sources:
        if not s.get("url"):
            continue
        res = fetch(s["url"])
        cls = classify(s, res, cid)
        rec["sources_checked"] += 1
        rec["by_class"][cls] = rec["by_class"].get(cls, 0) + 1
        rec["sources"].append({"source_id": s["source_id"], "class": cls, "old_sha256": s.get("sha256"),
                               "new_sha256": res.get("sha256"), "http_status": res.get("status"), "error": res.get("error")})
        if cls == "MISATTRIBUTED":
            rec["errors"].append(f"{s['source_id']} carries company_id={s.get('company_id')} inside {c['name_ja']}")
        elif cls != "UNCHANGED":
            changed[s["source_id"]] = cls
    if rec["errors"]:
        rec["status"] = "ABORTED_INTEGRITY"
        return rec
    cause_map = {"REVISED": "DATA_CHANGED", "FETCH_FAILED": "FETCH_FAILED", "WITHDRAWN": "WITHDRAWN"}
    for x in claims:
        hit = sorted({passages[e["passage_id"]]["source_id"] for e in x.get("evidence", [])
                      if e.get("passage_id") in passages and passages[e["passage_id"]]["source_id"] in changed})
        if hit:
            ev = {"event_id": f"EV-{upd_id}-{x['claim_id']}", "company_id": cid, "claim_id": x["claim_id"], "at": now,
                  "new_validity": "NEEDS_RECHECK", "cause": sorted({cause_map[changed[h]] for h in hit}),
                  "sources": hit, "update_id": upd_id}
            rec["claims_needs_recheck"].append(x["claim_id"])
            if not dry:
                append_jsonl(cdir / "ledger" / "claim_status_events.jsonl", ev)
    rec["status"] = "OK" if not changed else "OK_WITH_CHANGES"
    if not dry:
        write_json(cdir / "snapshots" / f"monthly_{month}" / "UPDATE_RECORD.json", rec)
        with open(cdir / "UPDATE_HISTORY.md", "a", encoding="utf-8") as f:
            f.write(f"| {upd_id} | {now[:10]} | {rec['status']} | checked {rec['sources_checked']} sources {rec['by_class']}; "
                    f"NEEDS_RECHECK {len(rec['claims_needs_recheck'])} claims |\n")
    return rec


def propagate_cross_company(company_recs: list[dict]) -> dict:
    """After every company finished: relations touching a changed company are flagged.
    A relation whose evidence changed on only one side is flagged ONE_SIDED_REVISION."""
    root = research_root()
    rels = read_jsonl(root / "cross_company" / "relations.jsonl")
    changed = {r["company_id"] for r in company_recs if r.get("claims_needs_recheck")}
    flagged = []
    for r in rels:
        sides = {r.get("company_a"), r.get("company_b")}
        hit = sides & changed
        if hit:
            flagged.append({"relation_id": r["relation_id"], "flag": "ONE_SIDED_REVISION" if len(hit) == 1 else "BOTH_SIDES_REVISED",
                            "changed_companies": sorted(hit)})
    return {"cross_company_relations": len(rels), "flagged": flagged,
            "world_model": "NOT_RECOMPUTED (world model not yet built)"}


def run(month: str, only: str | None = None, fetch: Fetcher = curl_fetch, dry: bool = False) -> dict:
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    recs = [update_company(c, month, fetch, now, dry) for c in companies() if not only or c["company_id"] == only]
    run_rec = {"run_id": f"UPD-{month}", "month": month, "executed_at": now, "mode": "dry-run" if dry else "write",
               "companies": recs, "cross_company": propagate_cross_company(recs),
               "status": "FAILED" if any(r.get("status") == "ABORTED_INTEGRITY" for r in recs) else "COMPLETED"}
    if not dry:
        suffix = f"-{only}" if only else ""
        write_json(research_root() / "monthly_update_runs" / f"UPD-{month}{suffix}.json", run_rec)
    return run_rec


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--month", default=dt.date.today().strftime("%Y-%m"))
    ap.add_argument("--company")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    r = run(a.month, a.company, dry=a.dry_run)
    for c in r["companies"]:
        print(f"{c['update_id']}: {c.get('status')} checked={c['sources_checked']} {c['by_class']} recheck={c['claims_needs_recheck']}")
    print("cross-company:", r["cross_company"])
    return 0 if r["status"] == "COMPLETED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
