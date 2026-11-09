#!/usr/bin/env python3
"""Company-first research gates (STEP 0 PASS criteria and per-company / per-axis / per-topic gates).

    python3 research/research_gates.py                 # check everything, print summary
    python3 research/research_gates.py --write         # also write status files and regenerate the registry
    python3 research/research_gates.py --company COMPANY_01

Exit status is 1 when any integrity error is found (FAIL), so CI / tests can rely on it.

Design rules (from the directive):
* The top-level gate is per company. A PASS for one company never implies a PASS for another.
* A topic is PASS only when the *computed* evidence criteria hold; a declared PASS that the
  evidence does not support is an error (E_UNSUPPORTED_PASS), never silently accepted.
* Evidence must come from the company's own ledger (shared public sources are referenced through
  that company's own SOURCE_ID). Citing another company's IDs is E_FOREIGN_EVIDENCE.
* No probabilities are invented: the gate reports counts (claims, independent origin groups,
  contradictions), not "confidence %".
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "tools"))
from common import (  # noqa: E402
    ACCESS, AS_OF, ASOF_SNAPSHOT, AUTO_DIGEST_MARKER, CLAIM_TYPES, DIRECTIONS, RELATIONS, SOURCE_TYPES, TEMPLATE_MARKER, VALIDITY,
    axes, companies, company_dir, read_csv, read_json, read_jsonl, research_root, short_code, write_csv, write_json,
)

STATE_ORDER = {"NOT_STARTED": 0, "IN_PROGRESS": 1, "PASS": 2}
OK_QUESTION_STATES = {"ANSWERED", "PARTIAL", "EVALUATED_UNRESOLVED", "BACKLOG"}
ID_RE = re.compile(r"\b(?:SRC|PSG|OBS|CLM|HYP|REL|MDL|Q|SL)-C(\d{2})-[A-Z0-9-]+")
REPORT_HEADINGS = [f"## {i}." for i in range(1, 16)]


class Ctx:
    def __init__(self):
        self.errors: list[dict] = []
        self.warnings: list[dict] = []

    def err(self, code, company_id, msg, ref=None):
        self.errors.append({"code": code, "company_id": company_id, "message": msg, "ref": ref})

    def warn(self, code, company_id, msg, ref=None):
        self.warnings.append({"code": code, "company_id": company_id, "message": msg, "ref": ref})


# --------------------------------------------------------------------------------------------- loading

def load_company(c: dict) -> dict:
    cdir = company_dir(c)
    led = cdir / "ledger"
    d = {
        "company": c, "dir": cdir,
        "sources": read_jsonl(led / "sources.jsonl"),
        "passages": read_jsonl(led / "passages.jsonl"),
        "observations": read_jsonl(led / "observations.jsonl"),
        "relations": read_jsonl(led / "relations.jsonl"),
        "search_log": read_jsonl(led / "search_log.jsonl"),
        "status_events": read_jsonl(led / "claim_status_events.jsonl"),
        "claims": [], "hypotheses": [], "questions": [], "synthesis": {},
        "topics": read_csv(cdir / "TOPIC_STATUS.csv") if (cdir / "TOPIC_STATUS.csv").exists() else [],
        "models": read_jsonl(cdir / "models" / "MODELS.jsonl"),
        "report": (cdir / "INTEGRATED_COMPANY_REPORT.md").read_text(encoding="utf-8") if (cdir / "INTEGRATED_COMPANY_REPORT.md").exists() else "",
    }
    for axis_id in sorted({a["axis_id"] for a in axes()}):
        adir = cdir / "axes" / axis_id
        for row in read_jsonl(adir / "CLAIMS.jsonl"):
            row.setdefault("_file", f"axes/{axis_id}/CLAIMS.jsonl")
            d["claims"].append(row)
        d["hypotheses"] += read_jsonl(adir / "HYPOTHESES.jsonl")
        d["questions"] += read_jsonl(adir / "QUESTIONS.jsonl")
        s = adir / "SYNTHESIS.md"
        d["synthesis"][axis_id] = s.read_text(encoding="utf-8") if s.exists() else None
    return d


def global_id_owner(all_data: list[dict]) -> dict:
    """ID -> company_id for every evidence ID of every company (used to detect cross-company leakage)."""
    owner = {}
    for d in all_data:
        cid = d["company"]["company_id"]
        for key, idf in (("sources", "source_id"), ("passages", "passage_id"), ("observations", "observation_id"),
                         ("claims", "claim_id"), ("hypotheses", "hypothesis_id"), ("relations", "relation_id")):
            for r in d[key]:
                owner.setdefault(r.get(idf), cid)
    return owner


# --------------------------------------------------------------------------------------------- integrity

def check_integrity(d: dict, owner: dict, ctx: Ctx) -> None:
    c = d["company"]
    cid, sc = c["company_id"], short_code(c["company_id"])

    # required structure
    for p in ("INTEGRATED_COMPANY_REPORT.md", "TOPIC_STATUS.csv", "ledger/sources.jsonl", "NEXT_STEPS.md"):
        if not (d["dir"] / p).exists():
            ctx.err("E_STRUCTURE", cid, f"missing {p}")
    for a in sorted({a["axis_id"] for a in axes()}):
        if d["synthesis"].get(a) is None:
            ctx.err("E_STRUCTURE", cid, f"missing axes/{a}/SYNTHESIS.md")
    if len(d["topics"]) != len(axes()):
        ctx.err("E_STRUCTURE", cid, f"TOPIC_STATUS.csv has {len(d['topics'])} rows, expected {len(axes())}")

    seen = Counter()
    for key, idf, prefix in (("sources", "source_id", "SRC"), ("passages", "passage_id", "PSG"),
                             ("observations", "observation_id", "OBS"), ("claims", "claim_id", "CLM"),
                             ("hypotheses", "hypothesis_id", "HYP"), ("relations", "relation_id", "REL"),
                             ("questions", "question_id", "Q"), ("search_log", "log_id", "SL")):
        for r in d[key]:
            rid = r.get(idf)
            if not rid:
                ctx.err("E_MISSING_ID", cid, f"{key} record without {idf}", r)
                continue
            seen[rid] += 1
            if not rid.startswith(f"{prefix}-{sc}-"):
                ctx.err("E_ID_PREFIX", cid, f"{rid} does not carry company prefix {prefix}-{sc}-", rid)
            if r.get("company_id") != cid:
                ctx.err("E_COMPANY_MISMATCH", cid, f"{rid} has company_id={r.get('company_id')} inside {c['name_ja']}", rid)
    for rid, n in seen.items():
        if n > 1:
            ctx.err("E_DUP_ID", cid, f"{rid} appears {n} times", rid)

    src = {s["source_id"]: s for s in d["sources"]}
    psg = {p["passage_id"]: p for p in d["passages"]}
    clm = {x["claim_id"]: x for x in d["claims"]}

    for s in d["sources"]:
        for f, allowed in (("access", ACCESS), ("source_type", SOURCE_TYPES)):
            if s.get(f) not in allowed:
                ctx.err("E_ENUM", cid, f"{s['source_id']}.{f}={s.get(f)}", s["source_id"])
        if s.get("access") == "DIRECT":
            for f in ("url", "sha256", "retrieved_at", "published_at", "origin_group_id"):
                if not s.get(f):
                    ctx.err("E_SOURCE_INCOMPLETE", cid, f"{s['source_id']} DIRECT source lacks {f}", s["source_id"])
        if s.get("snapshot", ASOF_SNAPSHOT) == ASOF_SNAPSHOT and (s.get("published_at") or "") > AS_OF:
            ctx.err("E_ASOF_VIOLATION", cid, f"{s['source_id']} published {s.get('published_at')} after as-of {AS_OF} but filed in {ASOF_SNAPSHOT}", s["source_id"])

    for p in d["passages"]:
        if p.get("source_id") not in src:
            code = "E_FOREIGN_EVIDENCE" if owner.get(p.get("source_id"), cid) != cid else "E_MISSING_REF"
            ctx.err(code, cid, f"{p['passage_id']} -> unknown source {p.get('source_id')}", p["passage_id"])
        if not p.get("locator"):
            ctx.err("E_PASSAGE_LOCATOR", cid, f"{p['passage_id']} has no locator (page/table/paragraph)", p["passage_id"])

    obs_key = {}
    for o in d["observations"]:
        if o.get("passage_id") not in psg:
            ctx.err("E_MISSING_REF", cid, f"{o['observation_id']} -> unknown passage {o.get('passage_id')}", o["observation_id"])
        elif psg[o["passage_id"]]["source_id"] != o.get("source_id"):
            ctx.err("E_MISSING_REF", cid, f"{o['observation_id']} source/passage mismatch", o["observation_id"])
        if not o.get("unit"):
            ctx.err("E_UNIT", cid, f"{o['observation_id']} has no unit", o["observation_id"])
        k = (o.get("variable"), o.get("period"), o.get("scope"))
        if k in obs_key and obs_key[k]["value"] != o.get("value") and o.get("validity") != "DISPUTED":
            ctx.err("E_DOUBLE_COUNT", cid, f"{o['observation_id']} and {obs_key[k]['observation_id']} record different values for {k} without DISPUTED flag", o["observation_id"])
        elif k in obs_key and obs_key[k]["value"] == o.get("value"):
            ctx.err("E_DOUBLE_COUNT", cid, f"{o['observation_id']} duplicates {obs_key[k]['observation_id']} ({k})", o["observation_id"])
        obs_key.setdefault(k, o)

    topic_ids = {t["topic_id"] for t in d["topics"]}
    for x in d["claims"]:
        xid = x["claim_id"]
        if x.get("claim_type") not in CLAIM_TYPES:
            ctx.err("E_ENUM", cid, f"{xid}.claim_type={x.get('claim_type')}", xid)
        if x.get("validity") not in VALIDITY:
            ctx.err("E_ENUM", cid, f"{xid}.validity={x.get('validity')}", xid)
        if x.get("topic_id") not in topic_ids:
            ctx.err("E_MISSING_REF", cid, f"{xid} topic {x.get('topic_id')} not registered", xid)
        elif not x.get("_file", "").startswith(f"axes/{x['topic_id'][:7]}/"):
            ctx.err("E_AXIS_MISMATCH", cid, f"{xid} stored in {x.get('_file')} but topic is {x['topic_id']}", xid)
        if not x.get("evidence"):
            ctx.err("E_NO_EVIDENCE", cid, f"{xid} has no evidence", xid)
        for e in x.get("evidence", []):
            pid = e.get("passage_id")
            if pid not in psg:
                if owner.get(pid) and owner[pid] != cid:
                    ctx.err("E_FOREIGN_EVIDENCE", cid, f"{xid} cites {pid} which belongs to {owner[pid]}", xid)
                else:
                    ctx.err("E_MISSING_REF", cid, f"{xid} cites unknown passage {pid}", xid)
                continue
            if e.get("direction") not in DIRECTIONS or e.get("relation") not in RELATIONS:
                ctx.err("E_ENUM", cid, f"{xid} evidence enums invalid ({e})", xid)
            s = src.get(psg[pid]["source_id"], {})
            if x.get("snapshot", ASOF_SNAPSHOT) == ASOF_SNAPSHOT and (s.get("published_at") or "") > AS_OF:
                ctx.err("E_ASOF_VIOLATION", cid, f"{xid} (as-of snapshot) uses {s.get('source_id')} published {s.get('published_at')}", xid)
        if x.get("claim_type") == "FACT" and not any(
                e.get("direction") == "SUPPORT" and e.get("relation") == "PRIMARY_DIRECT"
                and src.get(psg.get(e.get("passage_id"), {}).get("source_id"), {}).get("access") == "DIRECT"
                for e in x.get("evidence", [])):
            ctx.err("E_FACT_WITHOUT_DIRECT", cid, f"{xid} is FACT but has no DIRECT primary supporting passage", xid)
        declared = x.get("independent_origin_count")
        if declared is not None:
            actual = len(origin_groups(x, psg, src))
            if declared != actual:
                ctx.err("E_DOUBLE_COUNT", cid, f"{xid} declares {declared} independent origins but evidence has {actual} (reposts are not independent)", xid)
        for ref in ID_RE.finditer(json.dumps(x, ensure_ascii=False)):
            if ref.group(1) != sc[1:]:
                ctx.err("E_FOREIGN_EVIDENCE", cid, f"{xid} references foreign ID {ref.group(0)}", xid)
        mref = x.get("model_ref")
        if mref and mref.split(":")[0] not in {m["model_id"] for m in d["models"]}:
            ctx.err("E_MISSING_REF", cid, f"{xid} model_ref {mref} not registered in models/MODELS.jsonl", xid)

    for h in d["hypotheses"]:
        for k in ("evidence_for", "evidence_against"):
            for ref in h.get(k, []):
                if ref not in clm:
                    code = "E_FOREIGN_EVIDENCE" if owner.get(ref) and owner[ref] != cid else "E_MISSING_REF"
                    ctx.err(code, cid, f"{h['hypothesis_id']}.{k} -> {ref}", h["hypothesis_id"])
        if not h.get("disconfirming_observations"):
            ctx.err("E_NO_FALSIFIER", cid, f"{h['hypothesis_id']} lacks disconfirming_observations", h["hypothesis_id"])
    for q in d["questions"]:
        for ref in q.get("claim_ids", []):
            if ref not in clm:
                ctx.err("E_MISSING_REF", cid, f"{q['question_id']} -> {ref}", q["question_id"])
    for r in d["relations"]:
        for pid in r.get("evidence", []):
            if pid not in psg:
                code = "E_FOREIGN_EVIDENCE" if owner.get(pid) and owner[pid] != cid else "E_MISSING_REF"
                ctx.err(code, cid, f"{r['relation_id']} -> {pid}", r["relation_id"])

    # Reports must not cite other companies' evidence IDs.
    texts = {"INTEGRATED_COMPANY_REPORT.md": d["report"], **{f"axes/{k}/SYNTHESIS.md": v or "" for k, v in d["synthesis"].items()}}
    known = set(src) | set(psg) | set(clm) | {h["hypothesis_id"] for h in d["hypotheses"]} | {o["observation_id"] for o in d["observations"]} | {r["relation_id"] for r in d["relations"]} | {m["model_id"] for m in d["models"]} | {q["question_id"] for q in d["questions"]} | {s.get("log_id") for s in d["search_log"]}
    for name, t in texts.items():
        for m in ID_RE.finditer(t):
            if m.group(1) != sc[1:]:
                ctx.err("E_FOREIGN_EVIDENCE", cid, f"{name} cites foreign ID {m.group(0)}", m.group(0))
            elif m.group(0) not in known:
                ctx.err("E_MISSING_REF", cid, f"{name} cites unknown ID {m.group(0)}", m.group(0))

    # Models must reproduce their stored outputs.
    for m in d["models"]:
        check_model(d, m, ctx)


def origin_groups(x: dict, psg: dict, src: dict, direction="SUPPORT") -> set:
    return {src.get(psg[e["passage_id"]]["source_id"], {}).get("origin_group_id")
            for e in x.get("evidence", []) if e.get("passage_id") in psg and e.get("direction") == direction}


def check_model(d: dict, m: dict, ctx: Ctx) -> None:
    cid = d["company"]["company_id"]
    script = d["dir"] / "models" / m["script"]
    out = d["dir"] / "datasets" / m["outputs"]
    if not script.exists() or not out.exists():
        ctx.err("E_MODEL_NOT_REPRODUCIBLE", cid, f"{m['model_id']} script/output missing", m["model_id"])
        return
    try:
        spec = importlib.util.spec_from_file_location(f"model_{m['model_id'].replace('-', '_')}", script)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        res = mod.run(d["dir"])
    except Exception as e:  # noqa: BLE001 - a crashing model is a gate failure, reported with its reason
        ctx.err("E_MODEL_NOT_REPRODUCIBLE", cid, f"{m['model_id']} failed to run: {e}", m["model_id"])
        return
    if res != json.loads(out.read_text(encoding="utf-8")):
        ctx.err("E_MODEL_NOT_REPRODUCIBLE", cid, f"{m['model_id']} output differs from stored {m['outputs']}", m["model_id"])
    for k, v in res.get("results", {}).items():
        if isinstance(v, dict) and v.get("passes") is False:
            ctx.err("E_MODEL_CHECK_FAILED", cid, f"{m['model_id']}:{k} internal check failed", m["model_id"])


# --------------------------------------------------------------------------------------------- gates

def effective_validity(d: dict) -> dict:
    """Latest validity per claim: the ledger value overlaid by append-only claim_status_events (monthly updates)."""
    if "_eff" not in d:
        eff = {}
        for e in sorted(d["status_events"], key=lambda e: e.get("at", "")):
            eff[e["claim_id"]] = e.get("new_validity")
        d["_eff"] = eff
    return d["_eff"]


def topic_gate(d: dict, t: dict) -> dict:
    tid = t["topic_id"]
    cl = [x for x in d["claims"] if x.get("topic_id") == tid]
    hy = [h for h in d["hypotheses"] if tid in h.get("topic_ids", [])]
    qs = [q for q in d["questions"] if q.get("topic_id") == tid and q.get("kind") != "ROOT_RESEARCH_CARD"]
    src = {s["source_id"]: s for s in d["sources"]}
    psg = {p["passage_id"]: p for p in d["passages"]}
    groups = set().union(*[origin_groups(x, psg, src) for x in cl]) if cl else set()
    direct_sources = {psg[e["passage_id"]]["source_id"] for x in cl for e in x.get("evidence", [])
                      if e.get("passage_id") in psg and src.get(psg[e["passage_id"]]["source_id"], {}).get("access") == "DIRECT"}
    syn = d["synthesis"].get(t["axis_id"]) or ""
    eff = effective_validity(d)
    pending = [x["claim_id"] for x in cl if eff.get(x["claim_id"], x.get("validity")) == "NEEDS_RECHECK"]
    axis_logged = any(t["axis_id"] in s.get("axis_ids", []) for s in d["search_log"])
    checks = {
        "has_claims>=2": len(cl) >= 2,
        "has_direct_fact": any(x.get("claim_type") == "FACT" for x in cl),
        "independent_origin_groups>=2": len(groups) >= 2,
        "competing_hypotheses>=2": len(hy) >= 2,
        "hypotheses_have_counterevidence_notes": bool(hy) and all(h.get("counterevidence_notes") for h in hy),
        "atomic_questions_resolved_or_backlogged": bool(qs) and all(q.get("status") in OK_QUESTION_STATES for q in qs),
        "unknowns_recorded": any(q.get("status") in ("PARTIAL", "BACKLOG", "EVALUATED_UNRESOLVED", "OPEN") for q in qs) or any(x.get("claim_type") == "UNKNOWN" for x in cl),
        "synthesis_written": TEMPLATE_MARKER not in syn and AUTO_DIGEST_MARKER not in syn and tid in syn,
        "search_logged": axis_logged,
        "no_claims_pending_recheck": not pending,
    }
    if t.get("applicability") == "NOT_APPLICABLE":
        computed = "NOT_APPLICABLE" if t.get("na_reason") and t.get("na_source_ids") else "INVALID_NA"
    elif all(checks.values()):
        computed = "PASS"
    elif cl or qs:
        computed = "IN_PROGRESS"
    else:
        computed = "NOT_STARTED"
    return {"topic_id": tid, "axis_id": t["axis_id"], "declared": t.get("declared_state"), "computed": computed,
            "checks": checks, "claims": len(cl), "hypotheses": len(hy), "questions": len(qs),
            "independent_origin_groups": len(groups), "direct_sources": sorted(direct_sources), "claims_pending_recheck": pending,
            "contradicting_evidence": sum(1 for x in cl for e in x.get("evidence", []) if e.get("direction") == "CONTRADICT")
            + sum(1 for h in hy if h.get("evidence_against"))}


def company_gate(d: dict, ctx: Ctx) -> dict:
    c = d["company"]
    cid = c["company_id"]
    topics = []
    for t in d["topics"]:
        g = topic_gate(d, t)
        dec = g["declared"]
        if t.get("applicability") == "NOT_APPLICABLE" and g["computed"] == "INVALID_NA":
            ctx.err("E_NA_WITHOUT_REASON", cid, f"{t['topic_id']} NOT_APPLICABLE without reason/source", t["topic_id"])
            g["state"] = "BLOCKED"
        elif dec == "PASS" and g["computed"] != "PASS" and [k for k, v in g["checks"].items() if not v] == ["no_claims_pending_recheck"]:
            # evidence still exists but a monthly update flagged it: the PASS is suspended, not an integrity error
            g["state"] = "NEEDS_RECHECK"
        elif dec == "PASS" and g["computed"] != "PASS":
            failed = [k for k, v in g["checks"].items() if not v]
            ctx.err("E_UNSUPPORTED_PASS", cid, f"{t['topic_id']} declared PASS but gate fails: {failed}", t["topic_id"])
            g["state"] = "BLOCKED"
        elif g["computed"] == "NOT_APPLICABLE":
            g["state"] = "NOT_APPLICABLE"
        elif dec == "BLOCKED":
            g["state"] = "BLOCKED"
        else:
            # never report more than both the evidence and the researcher support
            g["state"] = min(dec if dec in STATE_ORDER else "NOT_STARTED", g["computed"], key=lambda s: STATE_ORDER.get(s, 0))
            if g["computed"] == "PASS" and dec != "PASS":
                g["note"] = "PASS_ELIGIBLE (declare PASS after review)"
        topics.append(g)

    axes_out = {}
    for a in sorted({t["axis_id"] for t in topics}):
        ts = [t for t in topics if t["axis_id"] == a]
        states = Counter(t["state"] for t in ts)
        if any(t["state"] == "NEEDS_RECHECK" for t in ts):
            st = "NEEDS_RECHECK"
        elif all(t["state"] in ("PASS", "NOT_APPLICABLE") for t in ts):
            st = "PASS"
        elif states.get("BLOCKED"):
            st = "BLOCKED"
        elif all(t["state"] == "NOT_STARTED" for t in ts):
            st = "NOT_STARTED"
        else:
            st = "IN_PROGRESS"
        axes_out[a] = {"state": st, "topics": dict(states)}

    report_written = TEMPLATE_MARKER not in d["report"] and AUTO_DIGEST_MARKER not in d["report"] and bool(d["report"].strip())
    report_sections = [h for h in REPORT_HEADINGS if h not in d["report"]]
    company_errors = [e for e in ctx.errors if e["company_id"] == cid]
    axis_pass = sum(1 for v in axes_out.values() if v["state"] == "PASS")
    if company_errors:
        state = "FAIL"
    elif axis_pass == len(axes_out) and report_written and not report_sections:
        state = "PASS"
    elif report_written:
        state = "PARTIAL"
    elif any(t["state"] != "NOT_STARTED" for t in topics):
        state = "IN_PROGRESS"
    else:
        state = "NOT_STARTED"

    src = {s["source_id"]: s for s in d["sources"]}
    psg = {p["passage_id"]: p for p in d["passages"]}
    ablation = {}
    for og in sorted({s.get("origin_group_id") for s in d["sources"]}):
        lost = [x["claim_id"] for x in d["claims"] if origin_groups(x, psg, src) and origin_groups(x, psg, src) <= {og}]
        ablation[og] = lost
    by_pub = defaultdict(set)
    for s in d["sources"]:
        by_pub[s.get("publisher", "?")].add(s.get("origin_group_id"))
    for pub, ogs in sorted(by_pub.items()):
        ablation[f"PUBLISHER:{pub}"] = [x["claim_id"] for x in d["claims"]
                                        if origin_groups(x, psg, src) and origin_groups(x, psg, src) <= ogs]
    return {
        "company_id": cid, "company_name": c["name_ja"], "company_research_status": state,
        "report_status": "WRITTEN_PARTIAL" if report_written and state != "PASS" else ("PASS" if state == "PASS" else "NOT_STARTED"),
        "report_missing_sections": report_sections,
        "axes_registered": len(axes_out), "axes_pass": axis_pass,
        "axes_in_progress": sum(1 for v in axes_out.values() if v["state"] == "IN_PROGRESS"),
        "topics_registered": len(topics),
        "topics_by_state": dict(Counter(t["state"] for t in topics)),
        "questions_registered": len(d["questions"]),
        "sources_direct": sum(1 for s in d["sources"] if s.get("access") == "DIRECT"),
        "independent_origin_groups": len({s.get("origin_group_id") for s in d["sources"]}),
        "passages": len(d["passages"]), "observations": len(d["observations"]),
        "claims_by_type": dict(Counter(x.get("claim_type") for x in d["claims"])),
        "hypotheses": len(d["hypotheses"]),
        "counterevidence_items": sum(len(h.get("evidence_against", [])) for h in d["hypotheses"]),
        "relations": len(d["relations"]),
        "models": [m["model_id"] for m in d["models"]],
        "errors": len(company_errors),
        "source_ablation_claims_losing_all_support": ablation,
        "axes": axes_out,
        "topics": topics,
        "as_of": AS_OF,
    }


XREL_STATUS = ("VERIFIED_BOTH_SIDES", "ONE_SIDED")


def check_cross_relations(rel: list[dict], ctx: Ctx) -> None:
    """Every cross-company edge must point back to passages in each company's OWN ledger (directive STEP 7)."""
    ledgers = {}
    for c in companies():
        ledgers[c["company_id"]] = {p["passage_id"] for p in read_jsonl(company_dir(c) / "ledger" / "passages.jsonl")}
    seen = set()
    for r in rel:
        rid = r.get("relation_id", "?")
        if rid in seen:
            ctx.err("E_DUP_ID", "CROSS", f"{rid} duplicated", rid)
        seen.add(rid)
        if r.get("status") not in XREL_STATUS:
            ctx.err("E_ENUM", "CROSS", f"{rid}.status={r.get('status')}", rid)
        if r.get("causal") not in (False, None):
            ctx.err("E_CAUSAL_ON_EXISTENCE", "CROSS", f"{rid}: relation records existence only; causal claims belong in hypotheses", rid)
        for side in ("a", "b"):
            cid = r.get(f"company_{side}")
            ev = r.get(f"evidence_{side}", [])
            if cid not in ledgers:
                ctx.err("E_MISSING_REF", "CROSS", f"{rid}: unknown company_{side} {cid}", rid)
                continue
            for pid in ev:
                if pid not in ledgers[cid]:
                    ctx.err("E_FOREIGN_EVIDENCE", "CROSS", f"{rid}: {pid} is not in {cid}'s ledger", rid)
        both = bool(r.get("evidence_a")) and bool(r.get("evidence_b"))
        if r.get("status") == "VERIFIED_BOTH_SIDES" and not both:
            ctx.err("E_UNSUPPORTED_PASS", "CROSS", f"{rid}: VERIFIED_BOTH_SIDES without evidence from both companies", rid)


def layer_gates(company_results: list[dict], ctx: Ctx) -> dict:
    root = research_root()
    passed = {r["company_id"] for r in company_results if r["company_research_status"] == "PASS"}
    rel = read_jsonl(root / "cross_company" / "relations.jsonl")
    check_cross_relations(rel, ctx)
    if not rel:
        cross = "NOT_STARTED"
    else:
        sides = {cid for r in rel for cid in (r.get("company_a"), r.get("company_b"))}
        cross = "PASS" if sides <= passed else "PARTIAL"
    world = "NOT_STARTED" if not (root / "world_context" / "WORLD_INTEGRATED_REPORT.md").exists() or TEMPLATE_MARKER in (root / "world_context" / "WORLD_INTEGRATED_REPORT.md").read_text(encoding="utf-8") else "PARTIAL"
    smoke = read_json(root / "app" / "SMOKE_TEST_RESULT.json", {})
    app = "PASS" if smoke.get("status") == "PASS" else ("DATA_ONLY" if (root / "app" / "data" / "companies.json").exists() else "NOT_STARTED")
    runs = sorted((root / "monthly_update_runs").glob("UPD-*.json")) if (root / "monthly_update_runs").exists() else []
    sched = read_json(root / "monthly_update_runs" / "SCHEDULER_STATUS.json", {})
    update = "PASS" if runs and sched.get("verified_running") else ("MANUAL_RUN_ONLY" if runs else "NOT_STARTED")
    return {"cross_company": cross, "world_model": world, "app": app, "monthly_update": update,
            "monthly_update_runs": [p.name for p in runs], "scheduler": sched or {"verified_running": False}}


def run(only: str | None = None) -> dict:
    ctx = Ctx()
    all_data = [load_company(c) for c in companies()]
    owner = global_id_owner(all_data)
    results = []
    for d in all_data:
        if only and d["company"]["company_id"] != only:
            continue
        check_integrity(d, owner, ctx)
        results.append(company_gate(d, ctx))
    layers = layer_gates(results, ctx)
    all_pass = len(results) == 8 and all(r["company_research_status"] == "PASS" for r in results)
    overall = "BLOCKED" if ctx.errors else ("COMPLETE" if all_pass and all(layers[k] == "PASS" for k in ("cross_company", "world_model", "app", "monthly_update")) else "INCOMPLETE")
    return {"RESEARCH_STATUS": overall, "as_of": AS_OF, "companies": results, "layers": layers,
            "errors": ctx.errors, "warnings": ctx.warnings}


def write_outputs(res: dict) -> None:
    root = research_root()
    summary = {k: v for k, v in res.items() if k != "companies"}
    summary["companies"] = [{k: v for k, v in r.items() if k not in ("topics", "axes")} for r in res["companies"]]
    write_json(root / "research_status.json", summary)
    reg_rows = []
    by_company = {r["company_id"]: r for r in res["companies"]}
    for c in companies():
        r = by_company.get(c["company_id"])
        if not r:
            continue
        write_json(company_dir(c) / "COMPANY_RESEARCH_STATUS.json", r)
        d = load_company(c)
        trow = {t["topic_id"]: t for t in d["topics"]}
        for g in r["topics"]:
            t = trow[g["topic_id"]]
            cl = [x for x in d["claims"] if x.get("topic_id") == g["topic_id"]]
            reg_rows.append({
                "company_topic_id": t["company_topic_id"], "company_id": c["company_id"], "company_name": c["name_ja"],
                "axis_id": t["axis_id"], "topic_id": t["topic_id"], "axis_name": t["axis_name"], "topic_name": t["topic_name"],
                "research_state": g["state"], "applicability": t["applicability"],
                "source_count_verified": len(g["direct_sources"]), "claim_count_verified": len(cl),
                "last_verified_at": "2026-11-09" if cl else "", "notes": g.get("note", ""),
            })
    if not reg_rows:
        return
    fields = ["company_topic_id", "company_id", "company_name", "axis_id", "topic_id", "axis_name", "topic_name",
              "research_state", "applicability", "source_count_verified", "claim_count_verified", "last_verified_at", "notes"]
    if len(by_company) == len(companies()):
        write_csv(root / "registry" / "company_axis_registry.csv", reg_rows, fields)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--company")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    res = run(a.company)
    if a.write:
        write_outputs(res)
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=1))
    else:
        print(f"RESEARCH_STATUS = {res['RESEARCH_STATUS']}  (as-of {AS_OF})")
        for r in res["companies"]:
            print(f"  {r['company_id']} {r['company_name']:<6} {r['company_research_status']:<12} axes PASS {r['axes_pass']}/30 "
                  f"in-progress {r['axes_in_progress']}  topics {r['topics_by_state']}  claims {sum(r['claims_by_type'].values())}  errors {r['errors']}")
        print("  layers:", {k: v for k, v in res["layers"].items() if k not in ("monthly_update_runs", "scheduler")})
        for e in res["errors"][:50]:
            print(f"  ERROR {e['code']} {e['company_id']}: {e['message']}")
        if len(res["errors"]) > 50:
            print(f"  ... {len(res['errors']) - 50} more errors")
    return 1 if res["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
