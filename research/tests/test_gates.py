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
            self.assertNotEqual(t["state"], "PASS", cid)
            if t["state"] != "NOT_STARTED":
                self.assertTrue(all(s.startswith("SRC-C" + cid[-2:]) for s in t["direct_sources"]), cid)

    def test_company_is_independent_of_other_companies(self):
        before = research_gates.run("COMPANY_01")["companies"][0]
        for name in ("三菱商事", "伊藤忠商事", "住友商事", "丸紅", "双日", "豊田通商", "兼松"):
            shutil.rmtree(self.c(name))
        p = self.root / "registry" / "company_registry.csv"
        lines = open(p, encoding="utf-8").read().splitlines()
        p.write_text("\n".join(lines[:2]) + "\n", encoding="utf-8")
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
        self.assertEqual(c["by_class"], {"UNCHANGED": 6})
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
        self.assertTrue(all(e["cause"] == ["DATA_CHANGED"] for e in ev))
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
        s = self.sources()
        m = {x["url"]: {"status": 200, "sha256": x["sha256"], "error": None} for x in s}
        m[s[1]["url"]] = {"status": 200, "sha256": "changed", "error": None}
        r = monthly_update.run("2026-12", None, fetch=self.fake(m))
        self.assertEqual(r["cross_company"]["flagged"][0]["flag"], "ONE_SIDED_REVISION")


if __name__ == "__main__":
    unittest.main()
