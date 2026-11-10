#!/usr/bin/env python3
"""Append research evidence for ONE company from a compact spec, with mechanical excerpt verification.

Every passage excerpt is checked against the locally extracted text of the cited page
(whitespace-insensitive; '…' separates fragments that must appear in order). If an excerpt
cannot be found the whole spec is rejected, so no unverifiable quotation enters the ledger.
The extracted full texts themselves are NOT committed (copyright); only hashes, page locators
and short excerpts are stored.

    python3 research/tools/evidence_builder.py SPEC.json [--dry-run]

Spec (JSON):
{
  "company_id": "COMPANY_03",
  "texts": {"Y": "/path/to/extracted.txt"},          # local only, split by form feed per PDF page
  "sources": [{"key": "Y", "url": ..., "publisher": ..., "title": ..., "doc_type": ..., "source_type": ...,
               "published_at": ..., "sha256": ..., "etag": ..., "last_modified": ..., "origin_group_id": ..., "notes": ...}],
  "claims": [{"topic": "AXIS_01_T02", "type": "FACT", "statement": "...", "validity": "HISTORICAL_IMMUTABLE",
              "ev": [["Y", 7, "excerpt", "SUPPORT"]], "notes": "...", "q": "question text (optional)"}],
  "observations": [["variable", value, "unit", "period", ["Y", 5, "excerpt"], "scope", "measurement"]],
  "hypotheses": [{"topics": [...], "phenomenon": ..., "explanation": ..., "expected": [...], "disconfirming": [...],
                  "for": [claim_index...], "against": [claim_index...], "notes": ..., "status": ..., "needed": ...}],
  "questions": [{"topic": ..., "question": ..., "status": "OPEN|BACKLOG|PARTIAL", "reason": ...}],
  "relations": [{"type": ..., "from": ..., "to": ..., "valid_from": ..., "amount": {...}, "ev": [["Y", p, "excerpt"]], "status": ..., "notes": ...}],
  "search_log": [{"query": ..., "results": n, "adopted_keys": [...], "notes": ..., "axis_ids": [...], "status": ...}],
  "topic_state": {"AXIS_13_T01": "IN_PROGRESS"}
}
Claims, hypotheses and relations refer to claims of the same spec by list index ("for": [0, 3]).
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import companies, company_dir, read_jsonl, short_code  # noqa: E402

NOW = dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).isoformat(timespec="seconds")


def norm(s: str) -> str:
    return re.sub(r"\s+", "", s).replace("，", ",").replace("．", ".")


def verify(pages: list[str], page: int, excerpt: str) -> bool:
    if page < 1 or page > len(pages):
        return False
    hay = norm(pages[page - 1])
    pos = 0
    for frag in [f for f in excerpt.split("…") if f.strip()]:
        i = hay.find(norm(frag), pos)
        if i < 0:
            return False
        pos = i + len(norm(frag))
    return True


def next_num(rows: list[dict], key: str) -> int:
    nums = [int(r[key].rsplit("-", 1)[1]) for r in rows if re.search(r"-\d{4}$", r.get(key, ""))]
    return max(nums, default=0) + 1


def main(argv: list[str]) -> int:
    spec = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
    dry = "--dry-run" in argv
    c = next(x for x in companies() if x["company_id"] == spec["company_id"])
    cid, sc = c["company_id"], short_code(c["company_id"])
    cdir = company_dir(c)
    led = cdir / "ledger"
    texts = {k: Path(v).read_text(encoding="utf-8", errors="ignore").split("\f") for k, v in spec.get("texts", {}).items()}

    sources = read_jsonl(led / "sources.jsonl")
    passages = read_jsonl(led / "passages.jsonl")
    observations = read_jsonl(led / "observations.jsonl")
    relations = read_jsonl(led / "relations.jsonl")
    slog = read_jsonl(led / "search_log.jsonl")
    errors = []

    # sources (by key -> source_id; reuse an existing source with the same URL)
    key2sid = {}
    n = next_num(sources, "source_id")
    for s in spec.get("sources", []):
        existing = next((x for x in sources if x["url"] == s["url"]), None)
        if existing:
            key2sid[s["key"]] = existing["source_id"]
            continue
        sid = f"SRC-{sc}-{n:04d}"
        n += 1
        row = {"source_id": sid, "company_id": cid, "url": s["url"], "publisher": s["publisher"], "title": s["title"],
               "doc_type": s.get("doc_type"), "source_type": s["source_type"], "access": s.get("access", "DIRECT"),
               "published_at": s["published_at"], "retrieved_at": s.get("retrieved_at", NOW), "sha256": s.get("sha256"),
               "etag": s.get("etag"), "last_modified": s.get("last_modified"), "origin_group_id": s["origin_group_id"],
               "shared_source_id": s.get("shared_source_id"), "snapshot": s.get("snapshot", "asof_2026-11-01"),
               "license": "公開資料。原文は再配布せず位置参照と最小限の抜粋のみ保存", "notes": s.get("notes", "")}
        sources.append(row)
        key2sid[s["key"]] = sid
    for s in sources:  # allow referencing existing sources by their id as key
        key2sid.setdefault(s["source_id"], s["source_id"])

    pn = next_num(passages, "passage_id")
    pindex = {(p["source_id"], json.dumps(p["locator"], sort_keys=True), p["excerpt"]): p["passage_id"] for p in passages}

    def passage(key, page, excerpt, section=""):
        nonlocal pn
        sid = key2sid.get(key)
        if not sid:
            errors.append(f"unknown source key {key}")
            return None
        src_key = next((k for k, v in key2sid.items() if v == sid and k in texts), None)
        loc = {"pdf_page": page} if isinstance(page, int) else {"paragraph": page}
        if src_key:
            ok = verify(texts[src_key], page, excerpt) if isinstance(page, int) else verify(["".join(texts[src_key])], 1, excerpt)
            if not ok:
                errors.append(f"excerpt not found on {key} p{page}: {excerpt[:60]}")
                return None
        k = (sid, json.dumps(loc, sort_keys=True), excerpt)
        if k in pindex:
            return pindex[k]
        pid = f"PSG-{sc}-{pn:04d}"
        pn += 1
        passages.append({"passage_id": pid, "company_id": cid, "source_id": sid, "locator": loc, "section": section, "excerpt": excerpt,
                         "verified": "EXCERPT_MATCHED_IN_EXTRACTED_TEXT" if src_key else "MANUAL"})
        pindex[k] = pid
        return pid

    # claims (grouped per axis file)
    claim_rows_by_axis: dict[str, list[dict]] = {}
    all_claims = []
    for a in sorted((cdir / "axes").glob("AXIS_*")):
        rows = read_jsonl(a / "CLAIMS.jsonl")
        claim_rows_by_axis[a.name] = rows
        all_claims += rows
    cn = next_num(all_claims, "claim_id")
    new_claim_ids = []
    for x in spec.get("claims", []):
        ev = []
        for item in x["ev"]:
            if isinstance(item, str) or (isinstance(item, list) and len(item) <= 2 and str(item[0]).startswith(f"PSG-{sc}-")):
                # reuse an already verified passage of THIS company's ledger
                pid0 = item if isinstance(item, str) else item[0]
                direction = "SUPPORT" if isinstance(item, str) or len(item) == 1 else item[1]
                if pid0 not in {p["passage_id"] for p in passages}:
                    errors.append(f"unknown passage {pid0} (must exist in this company's ledger)")
                    continue
                ev.append({"passage_id": pid0, "direction": direction, "relation": "PRIMARY_DIRECT"})
                continue
            key, page, excerpt = item[0], item[1], item[2]
            direction = item[3] if len(item) > 3 else "SUPPORT"
            relation = item[4] if len(item) > 4 else "PRIMARY_DIRECT"
            pid = passage(key, page, excerpt, x.get("section", ""))
            if pid:
                ev.append({"passage_id": pid, "direction": direction, "relation": relation})
        cid_ = f"CLM-{sc}-{cn:04d}"
        cn += 1
        axis = x["topic"][:7]
        row = {"claim_id": cid_, "company_id": cid, "axis_id": axis, "topic_id": x["topic"], "question_id": None,
               "claim_type": x["type"], "statement": x["statement"], "evidence": ev,
               "valid_from": x.get("valid_from"), "valid_to": x.get("valid_to"), "validity": x.get("validity", "CURRENT"),
               "info_class": x.get("info_class"), "snapshot": x.get("snapshot", "asof_2026-11-01"), "notes": x.get("notes", ""), "recorded_at": NOW}
        if x.get("model_ref"):
            row["model_ref"] = x["model_ref"]
        claim_rows_by_axis.setdefault(axis, []).append(row)
        new_claim_ids.append(cid_)
        x["_id"] = cid_

    # observations
    on = next_num(observations, "observation_id")
    for o in spec.get("observations", []):
        var, val, unit, period, (key, page, excerpt) = o[0], o[1], o[2], o[3], o[4]
        pid = passage(key, page, excerpt, "observation")
        if not pid:
            continue
        observations.append({"observation_id": f"OBS-{sc}-{on:04d}", "company_id": cid, "source_id": key2sid[key], "passage_id": pid,
                             "variable": var, "value": val, "unit": unit, "period": period,
                             "scope": o[5] if len(o) > 5 else "連結", "accounting": None,
                             "measurement": o[6] if len(o) > 6 else "AUDITED",
                             "validity": "HISTORICAL_IMMUTABLE", "notes": ""})
        on += 1

    # questions: attach one ATOMIC question per claim (if given) + explicit open questions
    qfiles: dict[str, list[dict]] = {}
    for a in sorted((cdir / "axes").glob("AXIS_*")):
        qfiles[a.name] = read_jsonl(a / "QUESTIONS.jsonl")

    rank = {"OPEN": 0, "BACKLOG": 0, "BLOCKED": 0, "PARTIAL": 1, "EVALUATED_UNRESOLVED": 2, "ANSWERED": 3}

    def add_q(topic, text, status, reason, claim_ids):
        axis = topic[:7]
        qs = qfiles[axis]
        ax, t = axis.split("_")[1], topic.split("_")[-1]
        same = next((q for q in qs if q["topic_id"] == topic and q.get("kind") == "ATOMIC" and q["question"] == text), None)
        if same:  # reuse the existing question instead of filing a duplicate; never downgrade its status
            new_ids = [c for c in claim_ids if c not in same.get("claim_ids", [])]
            same["claim_ids"] = same.get("claim_ids", []) + new_ids
            if rank.get(status, 0) > rank.get(same["status"], 0):
                same.setdefault("resolution_log", []).append({"at": NOW, "from": same["status"], "to": status, "claim_ids": new_ids, "reason": reason})
                same["status"] = status
            return same["question_id"]
        k = 1 + max([int(q["question_id"].rsplit("-", 1)[1]) for q in qs if q["topic_id"] == topic], default=0)
        qid = f"Q-{sc}-A{ax}-{t}-{k:02d}"
        qs.append({"question_id": qid, "company_id": cid, "axis_id": axis, "topic_id": topic, "parent_question_id": f"Q-{sc}-A{ax}-{t}-00",
                   "kind": "ATOMIC", "question": text, "search_queries": [], "source_route": [], "priority": "P1", "status": status,
                   "discovery_reason": reason, "claim_ids": claim_ids})
        for q in qs:
            if q["question_id"] == f"Q-{sc}-A{ax}-{t}-00" and q["status"] == "NOT_STARTED":
                q["status"] = "IN_PROGRESS"
        return qid

    for x in spec.get("claims", []):
        if x.get("q"):
            qid = add_q(x["topic"], x["q"], x.get("q_status", "ANSWERED"), "初期全軸調査（一次資料）", [x["_id"]])
            for r in claim_rows_by_axis[x["topic"][:7]]:
                if r["claim_id"] == x["_id"]:
                    r["question_id"] = qid
    for q in spec.get("questions", []):
        add_q(q["topic"], q["question"], q.get("status", "OPEN"), q.get("reason", ""), [])

    # hypotheses
    hyp_by_axis: dict[str, list[dict]] = {a: read_jsonl(cdir / "axes" / a / "HYPOTHESES.jsonl") for a in qfiles}
    hn = next_num([h for v in hyp_by_axis.values() for h in v], "hypothesis_id")
    for h in spec.get("hypotheses", []):
        axis = h["topics"][0][:7]
        ids = lambda idx: [spec["claims"][i]["_id"] if isinstance(i, int) else i for i in idx]  # noqa: E731
        hyp_by_axis[axis].append({
            "hypothesis_id": f"HYP-{sc}-{hn:04d}", "company_id": cid, "axis_id": axis, "topic_ids": h["topics"],
            "question_id": None, "observed_phenomenon": h["phenomenon"], "explanation": h["explanation"],
            "expected_observations": h["expected"], "disconfirming_observations": h["disconfirming"],
            "evidence_for": ids(h.get("for", [])), "evidence_against": ids(h.get("against", [])),
            "counterevidence_notes": h["notes"], "status": h["status"], "discriminating_data_needed": h.get("needed", "")})
        hn += 1

    # relations
    rn = next_num(relations, "relation_id")
    for r in spec.get("relations", []):
        evp = [passage(e[0], e[1], e[2], "relation") for e in r["ev"]]
        relations.append({"relation_id": f"REL-{sc}-{rn:04d}", "company_id": cid, "type": r["type"], "from_entity": r["from"],
                          "to_entity": r["to"], "via_entity": r.get("via"), "valid_from": r.get("valid_from"), "valid_to": r.get("valid_to"),
                          "amount": r.get("amount"), "evidence": [p for p in evp if p], "status": r.get("status", "CONFIRMED_ONE_SIDE"),
                          "notes": r.get("notes", "")})
        rn += 1

    ln = next_num(slog, "log_id")
    for s in spec.get("search_log", []):
        slog.append({"log_id": f"SL-{sc}-{ln:04d}", "company_id": cid, "at": s.get("at", NOW), "query": s["query"], "language": s.get("language", "ja"),
                     "results": s["results"], "adopted": [key2sid.get(k, k) for k in s.get("adopted_keys", [])],
                     "excluded": s.get("excluded", []), "status": s.get("status"), "notes": s.get("notes", ""), "axis_ids": s.get("axis_ids", [])})
        ln += 1

    if errors:
        print("REJECTED:\n  " + "\n  ".join(errors))
        return 1
    if dry:
        print(f"dry-run OK: {len(spec.get('claims', []))} claims, {len(spec.get('observations', []))} observations")
        return 0

    def dump(p, rows):
        p.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")

    dump(led / "sources.jsonl", sources)
    dump(led / "passages.jsonl", passages)
    dump(led / "observations.jsonl", observations)
    dump(led / "relations.jsonl", relations)
    dump(led / "search_log.jsonl", slog)
    for axis, rows in claim_rows_by_axis.items():
        dump(cdir / "axes" / axis / "CLAIMS.jsonl", rows)
    for axis, rows in qfiles.items():
        dump(cdir / "axes" / axis / "QUESTIONS.jsonl", rows)
    for axis, rows in hyp_by_axis.items():
        dump(cdir / "axes" / axis / "HYPOTHESES.jsonl", rows)

    # topic declared states
    ts = spec.get("topic_state", {})
    touched = {x["topic"] for x in spec.get("claims", [])}
    p = cdir / "TOPIC_STATUS.csv"
    with open(p, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        if r["topic_id"] in ts:
            r["declared_state"] = ts[r["topic_id"]]
            r["applicability"] = "APPLICABLE"
        elif r["topic_id"] in touched and r["declared_state"] == "NOT_STARTED":
            r["declared_state"] = "IN_PROGRESS"
            r["applicability"] = "APPLICABLE"
    with open(p, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys(), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(f"appended {len(new_claim_ids)} claims ({new_claim_ids[:1]}..{new_claim_ids[-1:]}), "
          f"{len(spec.get('observations', []))} observations, {len(spec.get('hypotheses', []))} hypotheses for {c['name_ja']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
