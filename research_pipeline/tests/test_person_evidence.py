"""是正命令 P-1・P-3: 本人性の判定規則（S1〜S4 は照合済みの役割根拠と本文到達が必要）を合成データで検証する。

    python3 -I -m unittest discover -s research_pipeline/tests -t .
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from research_pipeline import ledger as LG  # noqa: E402
from research_pipeline import verify_excerpts as VE  # noqa: E402
from research_pipeline.common import read_csv, write_csv  # noqa: E402


def build(tmp: Path, *, tier="S1", reach="全文", identity="CONFIRMED", role_status="verbatim_auto_verified",
          with_role=True, person_tier=None) -> Path:
    root = tmp / "R"
    rows: dict[str, list[dict]] = {n: [] for n in LG.SCHEMAS}
    base = {c: "x" for c in LG.SCHEMAS["sources"][1]}
    rows["sources"] = [dict(base, source_id="SRC-000001", source_tier=tier, person_id="PERSON-000001",
                            observed_at="2026-11-16")]
    pbase = {c: "" for c in LG.SCHEMAS["people"][1]}
    rows["people"] = [dict(pbase, person_id="PERSON-000001", name_as_shown="A. Dev",
                           person_tier=person_tier or tier, evidence_source_ids="SRC-000001")]
    abase = {c: "" for c in LG.SCHEMAS["source_access"][1]}
    rows["source_access"] = [dict(abase, source_id="SRC-000001", reach=reach)]
    if with_role:
        rbase = {c: "" for c in LG.SCHEMAS["role_evidence"][1]}
        rows["role_evidence"] = [dict(rbase, role_evidence_id="ROLE-000001", person_id="PERSON-000001",
                                      source_id="SRC-000001", excerpt="A. Dev designed the evaluation harness.",
                                      location="Acknowledgements", verification_status=role_status,
                                      identity_status=identity, determined_tier=tier)]
    for name, (rel, cols, _key, _pat) in LG.SCHEMAS.items():
        write_csv(root / rel, cols, rows[name])
    return root


class PersonEvidenceRules(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.t = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def errors(self, **kw):
        return LG.load(build(self.t, **kw)).errors

    def test_confirmed_and_verified_s1_is_clean(self):
        self.assertEqual(self.errors(), [])

    def test_s1_without_role_evidence_is_error(self):
        errs = self.errors(with_role=False)
        self.assertTrue(any("役割根拠" in e for e in errs), errs)

    def test_unconfirmed_identity_cannot_be_s2(self):
        errs = self.errors(tier="S2", identity="CANDIDATE_UNVERIFIED")
        self.assertTrue(any("本人性が未確認" in e for e in errs), errs)

    def test_unverified_role_excerpt_is_not_counted(self):
        errs = self.errors(role_status="unverified")
        self.assertTrue(any("原文照合されていない" in e for e in errs), errs)

    def test_metadata_only_source_cannot_be_counted(self):
        errs = self.errors(reach="説明欄のみ")
        self.assertTrue(any("本文に到達していない" in e for e in errs), errs)

    def test_candidate_person_tier_is_allowed_without_evidence(self):
        errs = self.errors(tier="S5", person_tier="CANDIDATE_UNVERIFIED", with_role=False)
        self.assertEqual(errs, [])

    def test_verifier_checks_role_excerpts_in_text_snapshot(self):
        root = build(self.t)
        snaps = self.t / "snaps"
        snaps.mkdir()
        (snaps / "SRC-000001.txt").write_text("Intro\nAcknowledgements\nA. Dev designed the evaluation\nharness.\n",
                                              encoding="utf-8")
        counts = VE.run(root, snaps)
        self.assertEqual((counts["role_checked"], counts["role_found"]), (1, 1))
        row = read_csv(root / "audit" / "role_evidence_verification.csv")[0]
        self.assertEqual((row["found"], row["position_match"]), ("true", "true"))
        (snaps / "SRC-000001.txt").write_text("A. Dev wrote the post.\n", encoding="utf-8")
        self.assertEqual(VE.run(root, snaps)["role_not_found"], 1)


if __name__ == "__main__":
    unittest.main()
