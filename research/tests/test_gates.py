"""Gate and monthly-update tests. Every negative test corrupts a temporary copy of research/ and
asserts that the gate FAILS with the expected error code (STEP 0 PASS criterion).

    python3 -m unittest discover -s research/tests -v
"""
from __future__ import annotations

import csv
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REAL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REAL))
sys.path.insert(0, str(REAL / "tools"))

import research_gates  # noqa: E402
import monthly_update  # noqa: E402

C01 = "三井物産"
C02 = "三菱商事"


def jl_append(path: Path, row: dict) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def jl_read(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def jl_write(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def set_topic(root: Path, company: str, topic: str, **fields) -> None:
    p = root / "companies" / company / "TOPIC_STATUS.csv"
    with open(p, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        if r["topic_id"] == topic:
            r.update(fields)
    with open(p, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys(), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.root = self.tmp / "research"
        shutil.copytree(REAL, self.root, ignore=shutil.ignore_patterns("app", "__pycache__", "directive"))
        os.environ["RESEARCH_ROOT"] = str(self.root)

    def tearDown(self):
        os.environ.pop("RESEARCH_ROOT", None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def codes(self, company=None):
        return {e["code"] for e in research_gates.run(company)["errors"]}

    def c(self, name):
        return self.root / "companies" / name


class TestBaseline(Base):
    def test_real_data_has_no_integrity_errors(self):
        res = research_gates.run()
        self.assertEqual(res["errors"], [])
        self.assertEqual(res["RESEARCH_STATUS"], "INCOMPLETE")  # never COMPLETE while 7 companies are unstarted

    def test_registration_counts(self):
        res = research_gates.run()
        self.assertEqual(len(res["companies"]), 8)
        for r in res["companies"]:
            self.assertEqual(r["axes_registered"], 30)
            self.assertEqual(r["topics_registered"], 240)
            self.assertGreaterEqual(r["questions_registered"], 240)
        reg = list(csv.DictReader(open(self.root / "registry" / "company_axis_registry.csv", encoding="utf-8")))
        self.assertEqual(len(reg), 1920)
        self.assertEqual(len({r["company_topic_id"] for r in reg}), 1920)

    def test_one_company_pass_does_not_propagate(self):
        res = research_gates.run()
        by = {r["company_id"]: r for r in res["companies"]}
        t03 = [t for t in by["COMPANY_01"]["topics"] if t["topic_id"] == "AXIS_13_T03"][0]
        self.assertEqual(t03["state"], "PASS")
        for cid in ("COMPANY_02", "COMPANY_03", "COMPANY_04", "COMPANY_05", "COMPANY_06", "COMPANY_07", "COMPANY_08"):
            t = [t for t in by[cid]["topics"] if t["topic_id"] == "AXIS_13_T03"][0]
            # another company's PASS never carries over; each company's state comes from its own evidence only
            if t["state"] != "NOT_STARTED":
                # any progress (including PASS) must rest only on that company's own sources
                self.assertTrue(t["direct_sources"], cid)
                self.assertTrue(all(s.startswith("SRC-C" + cid[-2:]) for s in t["direct_sources"]), cid)

    def test_company_is_independent_of_other_companies(self):
        before = research_gates.run("COMPANY_01")["companies"][0]
        for name in ("三菱商事", "伊藤忠商事", "住友商事", "丸紅", "双日", "豊田通商", "兼松"):
            shutil.rmtree(self.c(name))
        p = self.root / "registry" / "company_registry.csv"
        lines = open(p, encoding="utf-8").read().splitlines()
        p.write_text("\n".join(lines[:2]) + "\n", encoding="utf-8")
        for derived in ("relations.jsonl", "common_exposures.jsonl"):  # cross-company layers are derived and rebuilt later
            (self.root / "cross_company" / derived).write_text("", encoding="utf-8")
        after = research_gates.run("COMPANY_01")
        self.assertEqual(after["errors"], [])
        a = after["companies"][0]
        for k in ("company_research_status", "topics_by_state", "claims_by_type", "source_ablation_claims_losing_all_support"):
            self.assertEqual(before[k], a[k], k)


class TestGateFailures(Base):
    def test_company_id_mismatch(self):
        p = self.c(C01) / "axes" / "AXIS_13" / "CLAIMS.jsonl"
        rows = jl_read(p)
        rows[0]["company_id"] = "COMPANY_02"
        jl_write(p, rows)
        self.assertIn("E_COMPANY_MISMATCH", self.codes())

    def test_foreign_evidence_from_other_company(self):
        jl_append(self.c(C02) / "axes" / "AXIS_13" / "CLAIMS.jsonl", {
            "claim_id": "CLM-C02-0001", "company_id": "COMPANY_02", "axis_id": "AXIS_13", "topic_id": "AXIS_13_T03",
            "claim_type": "FACT", "statement": "三井物産の証拠を流用", "validity": "CURRENT", "snapshot": "asof_2026-11-01",
            "evidence": [{"passage_id": "PSG-C01-0025", "direction": "SUPPORT", "relation": "PRIMARY_DIRECT"}]})
        self.assertIn("E_FOREIGN_EVIDENCE", self.codes())

    def test_missing_passage(self):
        p = self.c(C01) / "axes" / "AXIS_13" / "CLAIMS.jsonl"
        rows = jl_read(p)
        rows[0]["evidence"].append({"passage_id": "PSG-C01-9999", "direction": "SUPPORT", "relation": "PRIMARY_DIRECT"})
        jl_write(p, rows)
        self.assertIn("E_MISSING_REF", self.codes())

    def test_duplicate_observation_is_double_count(self):
        p = self.c(C01) / "ledger" / "observations.jsonl"
        rows = jl_read(p)
        dup = dict(rows[0], observation_id="OBS-C01-9999")
        jl_append(p, dup)
        self.assertIn("E_DOUBLE_COUNT", self.codes())

    def test_inflated_independence(self):
        p = self.c(C01) / "axes" / "AXIS_13" / "CLAIMS.jsonl"
        rows = jl_read(p)
        rows[2]["independent_origin_count"] = 3  # evidence is from one origin group only
        jl_write(p, rows)
        self.assertIn("E_DOUBLE_COUNT", self.codes())

    def test_asof_violation(self):
        p = self.c(C01) / "ledger" / "sources.jsonl"
        rows = jl_read(p)
        rows[1]["published_at"] = "2026-11-05"
        jl_write(p, rows)
        self.assertIn("E_ASOF_VIOLATION", self.codes())

    def test_unsupported_pass(self):
        set_topic(self.root, C02, "AXIS_13_T03", declared_state="PASS")
        self.assertIn("E_UNSUPPORTED_PASS", self.codes())

    def test_not_applicable_needs_reason(self):
        set_topic(self.root, C02, "AXIS_05_T04", applicability="NOT_APPLICABLE")
        self.assertIn("E_NA_WITHOUT_REASON", self.codes())

    def test_fact_without_direct_source(self):
        p = self.c(C01) / "ledger" / "sources.jsonl"
        rows = jl_read(p)
        rows[0]["access"] = "SEARCH_SNIPPET"
        jl_write(p, rows)
        self.assertIn("E_FACT_WITHOUT_DIRECT", self.codes())

    def test_model_tampering(self):
        p = self.c(C01) / "datasets" / "MDL-C01-0001_outputs.json"
        d = json.loads(p.read_text(encoding="utf-8"))
        d["results"]["jbic_fy2025"]["jbic_limit_musd"] = 9999
        p.write_text(json.dumps(d), encoding="utf-8")
        self.assertIn("E_MODEL_NOT_REPRODUCIBLE", self.codes())

    def test_changed_observation_breaks_model_check(self):
        p = self.c(C01) / "ledger" / "observations.jsonl"
        rows = jl_read(p)
        for r in rows:
            if r["observation_id"] == "OBS-C01-0018":
                r["value"] = 1  # lease liabilities -> reconstruction no longer matches the reported figure
        jl_write(p, rows)
        self.assertIn("E_MODEL_NOT_REPRODUCIBLE", self.codes())

    def test_report_cites_foreign_id(self):
        p = self.c(C02) / "INTEGRATED_COMPANY_REPORT.md"
        p.write_text(p.read_text(encoding="utf-8") + "\n三井物産の結論を転記（CLM-C01-0001）\n", encoding="utf-8")
        self.assertIn("E_FOREIGN_EVIDENCE", self.codes())

    def test_template_synthesis_blocks_pass(self):
        p = self.c(C01) / "axes" / "AXIS_13" / "SYNTHESIS.md"
        p.write_text("<!-- TEMPLATE:NOT_STARTED -->\n", encoding="utf-8")
        self.assertIn("E_UNSUPPORTED_PASS", self.codes())

    def test_passage_without_verification_state(self):
        p = self.c(C01) / "ledger" / "passages.jsonl"
        rows = jl_read(p)
        rows[0].pop("verified", None)
        jl_write(p, rows)
        self.assertIn("E_PASSAGE_UNVERIFIED", self.codes())

    def test_wrong_id_prefix(self):
        p = self.c(C01) / "ledger" / "sources.jsonl"
        rows = jl_read(p)
        rows[0]["source_id"] = "SRC-C02-0001"
        jl_write(p, rows)
        self.assertIn("E_ID_PREFIX", self.codes())


class TestMonthlyUpdate(Base):
    def fake(self, mapping):
        def f(url):
            return mapping.get(url, {"status": 200, "sha256": "x", "error": None})
        return f

    def sources(self):
        return jl_read(self.c(C01) / "ledger" / "sources.jsonl")

    def test_no_change(self):
        m = {s["url"]: {"status": 200, "sha256": s["sha256"], "error": None} for s in self.sources()}
        r = monthly_update.run("2026-12", "COMPANY_01", fetch=self.fake(m))
        c = r["companies"][0]
        self.assertEqual(c["by_class"], {"UNCHANGED": len(self.sources())})  # every source fetched with an identical hash
        self.assertEqual(c["claims_needs_recheck"], [])
        self.assertEqual(r["status"], "COMPLETED")

    def test_revision_marks_dependent_claims_and_keeps_originals(self):
        s = self.sources()
        m = {x["url"]: {"status": 200, "sha256": x["sha256"], "error": None} for x in s}
        m[s[4]["url"]] = {"status": 200, "sha256": "changed", "error": None}  # JBIC Rhodes Ridge release revised
        before = (self.c(C01) / "axes" / "AXIS_13" / "CLAIMS.jsonl").read_text(encoding="utf-8")
        r = monthly_update.run("2026-12", "COMPANY_01", fetch=self.fake(m))
        c = r["companies"][0]
        self.assertEqual(c["by_class"].get("REVISED"), 1)
        self.assertIn("CLM-C01-0014", c["claims_needs_recheck"])
        self.assertNotIn("CLM-C01-0013", c["claims_needs_recheck"])
        self.assertEqual(before, (self.c(C01) / "axes" / "AXIS_13" / "CLAIMS.jsonl").read_text(encoding="utf-8"))
        ev = jl_read(self.c(C01) / "ledger" / "claim_status_events.jsonl")
        data_ev = [e for e in ev if "SCHEDULED_RECHECK" not in e["cause"]]
        self.assertTrue(data_ev and all(e["cause"] == ["DATA_CHANGED"] for e in data_ev))
        self.assertTrue(all("policy" in e for e in ev if "SCHEDULED_RECHECK" in e["cause"]))
        self.assertTrue((self.c(C01) / "snapshots" / "monthly_2026-12" / "UPDATE_RECORD.json").exists())
        self.assertEqual(research_gates.run()["errors"], [])

    def test_fetch_failure_and_withdrawal(self):
        s = self.sources()
        m = {x["url"]: {"status": 200, "sha256": x["sha256"], "error": None} for x in s}
        m[s[0]["url"]] = {"status": 0, "sha256": None, "error": "timeout"}
        m[s[5]["url"]] = {"status": 404, "sha256": None, "error": "HTTP 404"}
        c = monthly_update.run("2026-12", "COMPANY_01", fetch=self.fake(m))["companies"][0]
        self.assertEqual(c["by_class"].get("FETCH_FAILED"), 1)
        self.assertEqual(c["by_class"].get("WITHDRAWN"), 1)
        self.assertIn("CLM-C01-0004", c["claims_needs_recheck"])

    def test_misattributed_source_aborts(self):
        p = self.c(C01) / "ledger" / "sources.jsonl"
        rows = jl_read(p)
        rows[0]["company_id"] = "COMPANY_02"
        jl_write(p, rows)
        r = monthly_update.run("2026-12", "COMPANY_01", fetch=self.fake({}))
        self.assertEqual(r["status"], "FAILED")
        self.assertEqual(r["companies"][0]["status"], "ABORTED_INTEGRITY")

    def test_one_sided_revision_flags_cross_company_relation(self):
        jl_append(self.root / "cross_company" / "relations.jsonl", {
            "relation_id": "XREL-TEST-0001", "company_a": "COMPANY_01", "company_b": "COMPANY_02", "type": "CO_INVESTS",
            "evidence_a": ["PSG-C01-0025"], "evidence_b": []})
        m = {}
        for d in (self.root / "companies").iterdir():
            for x in jl_read(d / "ledger" / "sources.jsonl"):
                m[x["url"]] = {"status": 200, "sha256": x["sha256"], "error": None}
        s = self.sources()
        m[s[1]["url"]] = {"status": 200, "sha256": "changed", "error": None}
        r = monthly_update.run("2026-12", None, fetch=self.fake(m), run_date="2026-11-09")
        flagged = {f["relation_id"]: f for f in r["cross_company"]["flagged"]}
        self.assertEqual(flagged["XREL-TEST-0001"]["flag"], "ONE_SIDED_REVISION")
        self.assertTrue(all(f["changed_companies"] == ["COMPANY_01"] for f in flagged.values()))


class TestReevaluation(Base):
    def test_scheduled_recheck_by_information_type_not_by_age(self):
        # 2027-06: ratings/plans (183/366 days) are due; audited financial history is never scheduled
        r = monthly_update.run("2027-06", "COMPANY_04", fetch=lambda u: {"status": 200, "sha256": next(
            s["sha256"] for s in jl_read(self.c(C02.replace("三菱商事", "住友商事")) / "ledger" / "sources.jsonl") if s["url"] == u), "error": None},
            run_date="2027-06-15")
        c = r["companies"][0]
        sched = set(c.get("claims_scheduled_recheck", []))
        self.assertIn("CLM-C04-0018", sched)          # rating (RATING, 183 days)
        claims = {x["claim_id"]: x for a in (self.c("住友商事") / "axes").glob("AXIS_*") for x in jl_read(a / "CLAIMS.jsonl")}
        for cid in sched:
            self.assertNotIn(claims[cid].get("info_class"), (None, "AUDITED_FINANCIAL"))
        self.assertIn("axes/AXIS_30/SYNTHESIS.md", c["reports_needs_recheck"])
        ev = jl_read(self.c("住友商事") / "ledger" / "claim_status_events.jsonl")
        self.assertTrue(all(e["cause"] == ["SCHEDULED_RECHECK"] and "policy" in e for e in ev))

    def test_not_due_yet_means_no_scheduled_recheck(self):
        # one week after the filing date nothing can be due (shortest interval is 31 days)
        r = monthly_update.run("2026-06", "COMPANY_04", fetch=lambda u: {"status": 0, "sha256": None, "error": "offline"},
                               dry=True, run_date="2026-06-19")
        self.assertEqual(r["companies"][0].get("claims_scheduled_recheck", []), [])

    def test_every_scheduled_recheck_is_past_its_type_deadline(self):
        import datetime as dt
        r = monthly_update.run("2026-11", "COMPANY_04", fetch=lambda u: {"status": 0, "sha256": None, "error": "offline"},
                               dry=True, run_date="2026-11-09")
        due = set(r["companies"][0].get("claims_scheduled_recheck", []))
        claims = {x["claim_id"]: x for a in (self.c("住友商事") / "axes").glob("AXIS_*") for x in jl_read(a / "CLAIMS.jsonl")}
        for cid in due:
            ic = claims[cid]["info_class"]
            self.assertIn(ic, monthly_update.RECHECK_DAYS)
            # observed no later than the filing date (2026-06-12) + interval <= run date
            self.assertLessEqual(dt.date(2026, 6, 12) + dt.timedelta(days=monthly_update.RECHECK_DAYS[ic]), dt.date(2026, 11, 9))
        for cid, x in claims.items():
            if x.get("info_class") in (None, "AUDITED_FINANCIAL"):
                self.assertNotIn(cid, due)

    def test_pass_is_suspended_not_failed_when_evidence_needs_recheck(self):
        # a source behind a PASS topic changes -> topic becomes NEEDS_RECHECK (no integrity error)
        jl_append(self.c("住友商事") / "ledger" / "claim_status_events.jsonl", {
            "event_id": "EV-TEST", "company_id": "COMPANY_04", "claim_id": "CLM-C04-0013", "at": "2027-01-01T00:00:00+00:00",
            "new_validity": "NEEDS_RECHECK", "cause": ["DATA_CHANGED"], "sources": ["SRC-C04-0004"], "update_id": "UPD-TEST"})
        res = research_gates.run("COMPANY_04")
        self.assertEqual(res["errors"], [])
        t = [t for t in res["companies"][0]["topics"] if t["topic_id"] == "AXIS_30_T06"][0]
        self.assertEqual(t["state"], "NEEDS_RECHECK")
        self.assertEqual(res["companies"][0]["axes"]["AXIS_30"]["state"], "NEEDS_RECHECK")


class TestCrossCompany(Base):
    def rel_path(self):
        return self.root / "cross_company" / "relations.jsonl"

    def test_real_relations_valid(self):
        self.assertEqual([e for e in research_gates.run()["errors"] if e["company_id"] == "CROSS"], [])

    def test_edge_must_cite_each_companys_own_ledger(self):
        jl_append(self.rel_path(), {"relation_id": "XREL-9001", "type": "JOINT_VENTURE", "company_a": "COMPANY_01", "company_b": "COMPANY_03",
                                    "evidence_a": ["PSG-C03-0001"], "evidence_b": ["PSG-C01-0001"], "status": "VERIFIED_BOTH_SIDES", "causal": False})
        self.assertIn("E_FOREIGN_EVIDENCE", self.codes())

    def test_both_sides_requires_both_evidence(self):
        jl_append(self.rel_path(), {"relation_id": "XREL-9002", "type": "JOINT_VENTURE", "company_a": "COMPANY_01", "company_b": "COMPANY_03",
                                    "evidence_a": ["PSG-C01-0076"], "evidence_b": [], "status": "VERIFIED_BOTH_SIDES", "causal": False})
        self.assertIn("E_UNSUPPORTED_PASS", self.codes())

    def test_existence_edge_cannot_assert_causality(self):
        jl_append(self.rel_path(), {"relation_id": "XREL-9003", "type": "COMMON_MAJOR_SHAREHOLDER", "company_a": "COMPANY_01", "company_b": "COMPANY_03",
                                    "evidence_a": ["PSG-C01-0015"], "evidence_b": ["PSG-C03-0098"], "status": "VERIFIED_BOTH_SIDES", "causal": True})
        self.assertIn("E_CAUSAL_ON_EXISTENCE", self.codes())

    def edge(self, rid):
        return next(r for r in jl_read(self.rel_path()) if r["relation_id"] == rid)

    def test_declared_evidence_level_must_match_cited_passages(self):
        r = dict(self.edge("XREL-0002"), relation_id="XREL-9004", evidence_level="ONE_SIDED")
        jl_append(self.rel_path(), r)
        self.assertIn("E_EVIDENCE_LEVEL", self.codes())

    def test_third_party_passage_cannot_stand_in_for_a_company_side(self):
        # PSG-C02-0001 is JBIC's release in Mitsubishi Corp's ledger: a third party, not Mitsubishi Corp's own disclosure
        r = dict(self.edge("XREL-0015"), relation_id="XREL-9005", evidence_a=["PSG-C02-0001"])
        jl_append(self.rel_path(), r)
        self.assertIn("E_UNSUPPORTED_PASS", self.codes())

    def test_company_disclosure_does_not_count_as_third_party(self):
        r = dict(self.edge("XREL-0015"), relation_id="XREL-9006", third_party_evidence=[{"company": "COMPANY_01", "passage_id": "PSG-C01-0015"}],
                 evidence_level="BOTH_SIDES+THIRD_PARTY")
        jl_append(self.rel_path(), r)
        self.assertIn("E_EVIDENCE_LEVEL", self.codes())

    def test_unknown_edge_type(self):
        jl_append(self.rel_path(), dict(self.edge("XREL-0015"), relation_id="XREL-9007", type="FRIENDSHIP"))
        self.assertIn("E_ENUM", self.codes())

    def test_exposure_claims_must_be_in_each_companys_ledger(self):
        p = self.root / "cross_company" / "common_exposures.jsonl"
        rows = jl_read(p)
        rows[0]["claims"]["COMPANY_08"] = ["CLM-C01-0038"]
        jl_write(p, rows)
        self.assertIn("E_FOREIGN_EVIDENCE", self.codes())

    def test_auto_digest_never_counts_as_written_synthesis(self):
        p = self.c("豊田通商") / "axes" / "AXIS_13" / "SYNTHESIS.md"
        p.write_text("<!-- AUTO_DIGEST -->\nAXIS_13_T03 の主張一覧\n", encoding="utf-8")
        self.assertIn("E_UNSUPPORTED_PASS", self.codes())



class TestSharedRegistry(Base):
    """A source a ledger marks as shared must be registered once, identically, with that company listed as a user."""

    def reg(self):
        return self.root / "registry" / "shared_sources.jsonl"

    def test_unregistered_shared_source(self):
        rows = [r for r in jl_read(self.reg()) if r["shared_source_id"] != "SHS-JCR-KR-2606"]
        jl_write(self.reg(), rows)
        self.assertIn("E_SHARED_UNREGISTERED", self.codes())

    def test_company_missing_from_used_by(self):
        rows = jl_read(self.reg())
        for r in rows:
            if r["shared_source_id"] == "SHS-JCR-KR-2606":
                r["used_by_companies"] = [c for c in r["used_by_companies"] if c != "COMPANY_04"]
        jl_write(self.reg(), rows)
        self.assertIn("E_SHARED_MISMATCH", self.codes("COMPANY_04"))

    def test_hash_differs_from_registry(self):
        rows = jl_read(self.reg())
        rows[0]["sha256"] = "0" * 64
        jl_write(self.reg(), rows)
        self.assertIn("E_SHARED_MISMATCH", self.codes())


if __name__ == "__main__":
    unittest.main()
