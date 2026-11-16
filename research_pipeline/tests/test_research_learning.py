"""第10部: 抽出したモジュール（research_learning）と学習設計・問題公開規則のテスト（合成データ）。"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from research_learning import dumpfile as D  # noqa: E402
from research_learning import learning as LN  # noqa: E402
from research_learning import urls as U  # noqa: E402
from research_pipeline import pipeline as PL  # noqa: E402
from research_pipeline import trace as TR  # noqa: E402
from research_pipeline.common import read_csv, write_csv  # noqa: E402
from research_pipeline.tests.test_pipeline import make_root, opts  # noqa: E402

SEP = "=" * 100


class Urls(unittest.TestCase):
    def test_normalize_drops_tracking(self):
        self.assertEqual(U.normalize("HTTPS://A.org/x?utm_source=1&b=2#f"), "https://a.org/x?b=2")

    def test_rejects_ssrf_like_targets(self):
        for u in ["http://127.0.0.1/", "http://169.254.169.254/latest", "https://user:pw@a.org/", "ftp://a.org/",
                  "http://localhost/", "http://intranet/", "https://x.internal/"]:
            self.assertFalse(U.check_fetchable(u)[0], u)
        self.assertTrue(U.check_fetchable("https://arxiv.org/abs/2507.09089")[0])


class Dump(unittest.TestCase):
    def test_parse_and_verify_without_writing(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            (root / "a").mkdir()
            (root / "a" / "x.py").write_text("print(1)\n", encoding="utf-8")
            dump = f"{SEP}\n# ファイル: a/x.py\n{SEP}\nprint(1)\n\n{SEP}\n# ファイル: ../evil\n{SEP}\nx\n"
            r = D.verify_against(dump, root)
            self.assertEqual((r["same"], r["unsafe"]), (["a/x.py"], ["../evil"]))
            self.assertFalse((root.parent / "evil").exists())


class LearningLedger(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = make_root(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_learning_stage_writes_question_ledger_and_diff(self):
        self.assertEqual(PL.run(self.root, opts()), 0)
        q = read_csv(self.root / "education" / "question_ledger.csv")
        self.assertEqual(q[0]["answer_status"], "公開可")
        self.assertEqual(q[0]["paper_version"], "0.0.1")
        self.assertTrue((self.root / "exports" / "education" / "p" / "09_論文と教材の差分表.md").exists())

    def test_missing_importance_fails_learning_stage(self):
        rows = read_csv(self.root / "education" / "learning_design.csv")
        rows[0]["importance"] = "X"
        write_csv(self.root / "education" / "learning_design.csv", LN.COLS, rows)
        self.assertEqual(PL.run(self.root, opts()), 1)

    def test_pending_review_question_is_not_published(self):
        p = self.root / "education" / "e" / "01.src.md"
        p.write_text(p.read_text(encoding="utf-8").replace("status=公開可", "status=要確認"), encoding="utf-8")
        self.assertEqual(PL.run(self.root, opts()), 0)
        md = (self.root / "exports" / "education" / "e" / "01_問題.md").read_text(encoding="utf-8")
        self.assertNotIn("問1", md)
        self.assertIn("要確認のため公開を止めている問題 1 件", md)

    def test_old_paper_version_is_flagged(self):
        p = self.root / "education" / "e" / "01.src.md"
        p.write_text(p.read_text(encoding="utf-8").replace("paper_version: 0.0.1", "paper_version: 0.0.0"),
                     encoding="utf-8")
        a = TR.audit(self.root)
        self.assertTrue(any("論文旧版準拠" in w for w in a.warnings))

    def test_flashcard_claims_must_belong_to_unit(self):
        write_csv(self.root / "education" / "e" / "flashcards.csv", ["card_id", "front", "back", "unit_ids", "claim_ids"],
                  [{"card_id": "FC-1", "front": "f", "back": "b", "unit_ids": "P1-U001", "claim_ids": "CLAIM-000002"}])
        self.assertTrue(any("段落に無い主張" in e for e in TR.audit(self.root).errors))

    def test_s_unit_with_only_developer_evidence_is_warned(self):
        PL.run(self.root, opts())
        rows = {r["unit_id"]: r for r in read_csv(self.root / "education" / "learning_design.csv")}
        self.assertEqual(rows["P1-U001"]["importance"], "S")
        self.assertEqual(rows["P1-U001"]["evidence_strength"], "根拠なし（本研究の方法・提案・限界）")


if __name__ == "__main__":
    unittest.main()


class LearningExport(unittest.TestCase):
    """第10部 10-7・10-8：learning/ の台帳（lesson・問題・根拠の経路・二軸）を合成データで検証する。"""

    def test_export_traces_question_back_to_source(self):
        import tempfile
        from research_learning import export as EX
        from research_pipeline import trace as TR
        from research_pipeline.common import read_csv
        from research_pipeline.tests.test_pipeline import make_root
        with tempfile.TemporaryDirectory() as t:
            root = make_root(Path(t))
            a = TR.audit(root)
            n = EX.write_all(root, a, "2026-11-16T00:00+09:00", "自動監査のみ", [("ch8", "開発", "作成済み")], "テスト")
            self.assertEqual(n["questions"], 1)
            q = read_csv(root / "learning" / "questions.csv")[0]
            self.assertEqual((q["correct_answers"][:2], q["synthetic_data_flag"], q["status"]), ("B)", "false", "公開可"))
            self.assertTrue(q["lesson_id"].startswith("01#L"))
            m = read_csv(root / "learning" / "learning_evidence_map.csv")
            self.assertIn(("SRC-000001", "CLAIM-000001", "P1-U001", q["question_id"]),
                          {(r["source_id"], r["claim_id"], r["paper_unit"], r["question_id"]) for r in m})
            pr = {r["unit_id"]: r["quadrant"] for r in read_csv(root / "learning" / "prioritization.csv")}
            self.assertEqual(set(pr), {"P1-U001", "P1-U002", "P1-U003", "P1-U004"})
            self.assertIn("LO-01", (root / "learning" / "curriculum.yaml").read_text(encoding="utf-8"))
