"""合成データだけで、追跡規則・3工程の連動（STALE伝播）・途中再開・同期計画を検証する。

    python3 -I -m unittest discover -s research_pipeline/tests   （リポジトリ直下で実行）
"""
from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from research_pipeline import ledger as LG  # noqa: E402
from research_pipeline import pipeline as PL  # noqa: E402
from research_pipeline import trace as TR  # noqa: E402
from research_pipeline.common import read_json, write_csv  # noqa: E402

PAPER = """::: meta
title: 合成論文
version: 0.0.1
:::
# 合成論文
## 結果
::: evidence id=P1-U001 claims=CLAIM-000001
合成の主張1。
:::
::: evidence id=P1-U002 claims=CLAIM-000002 assertion=effect
合成の効果（独立実験）。
:::
::: calc id=P1-U003 expr=(3/4)**3 expect=27/64
検算。
:::
::: limitation id=P1-U004
限界。
:::
"""
EDU = """::: meta
title: 合成教材
:::
# 合成教材
::: objective id=LO-01 units=P1-U001
目標。
:::
::: fact id=F-01 units=P1-U001 claims=CLAIM-000001
事実。
:::
::: analogy id=A-01
たとえ。
:::
::: quiz id=Q-01 units=P1-U001 claims=CLAIM-000001 lo=LO-01 type=choice answer=B level=初級
問題。
A) 誤り
B) 正しい
C) 誤り
解説: 根拠のとおり。
:::
"""


def make_root(tmp: Path) -> Path:
    root = tmp / "R"
    for name, (rel, cols, key, _) in LG.SCHEMAS.items():
        rows = []
        if name == "sources":
            base = {c: "x" for c in cols}
            rows = [dict(base, source_id="SRC-000001", source_tier="S5", person_id="", observed_at="2026-11-15"),
                    dict(base, source_id="SRC-000002", source_tier="V1", person_id="", observed_at="2026-11-15")]
        elif name == "claims":
            base = {c: "" for c in cols}
            rows = [dict(base, claim_id="CLAIM-000001", source_id="SRC-000001", original_position="§A",
                         original_language_excerpt_short="alpha beta", translation_ja="訳", claim_type="主張",
                         firsthand_or_hearsay="一次", verification_status="manual_verified"),
                    dict(base, claim_id="CLAIM-000002", source_id="SRC-000002", original_position="§B",
                         original_language_excerpt_short="gamma", translation_ja="訳", claim_type="実験",
                         firsthand_or_hearsay="一次", verification_status="manual_verified")]
        write_csv(root / rel, cols, rows)
    (root / "papers" / "p").mkdir(parents=True)
    (root / "papers" / "p" / "paper.src.md").write_text(PAPER, encoding="utf-8")
    (root / "education" / "e").mkdir(parents=True)
    (root / "education" / "e" / "01.src.md").write_text(EDU, encoding="utf-8")
    return root


def opts(**kw):
    base = dict(force=False, structlab=None, scope="all", keys=None, all_new=True, reason="テスト承認",
                reviewer="test")
    base.update(kw)
    return SimpleNamespace(**base)


class TraceRules(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = make_root(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def edit(self, rel, old, new):
        p = self.root / rel
        s = p.read_text(encoding="utf-8")
        self.assertIn(old, s)
        p.write_text(s.replace(old, new), encoding="utf-8")

    def test_clean_audit(self):
        a = TR.audit(self.root)
        self.assertEqual(a.errors, [])
        self.assertEqual({it.status for it in a.units.values()}, {"NEW"})

    def test_untraced_prose_is_error(self):
        self.edit("papers/p/paper.src.md", "## 結果\n", "## 結果\n根拠のない文。\n")
        self.assertTrue(any("ブロックの外に本文" in e for e in TR.audit(self.root).errors))

    def test_material_cannot_add_claims_not_in_paper_unit(self):
        self.edit("education/e/01.src.md", "units=P1-U001 claims=CLAIM-000001\n事実",
                  "units=P1-U001 claims=CLAIM-000002\n事実")
        self.assertTrue(any("論文段落" in e and "無い主張" in e for e in TR.audit(self.root).errors))

    def test_effect_needs_independent_experiment(self):
        self.edit("papers/p/paper.src.md", "claims=CLAIM-000002 assertion=effect",
                  "claims=CLAIM-000001 assertion=effect")
        self.assertTrue(any("独立実証" in e for e in TR.audit(self.root).errors))

    def test_calc_mismatch_is_error(self):
        self.edit("papers/p/paper.src.md", "expect=27/64", "expect=0.42")
        self.assertTrue(any("検算不一致" in e for e in TR.audit(self.root).errors))

    def test_analogy_must_not_carry_claims(self):
        self.edit("education/e/01.src.md", "::: analogy id=A-01", "::: analogy id=A-01 claims=CLAIM-000001")
        self.assertTrue(any("たとえ" in e for e in TR.audit(self.root).errors))

    def test_objective_without_question_is_error(self):
        self.edit("education/e/01.src.md", "lo=LO-01 type=choice", "lo=LO-02 type=choice")
        errs = TR.audit(self.root).errors
        self.assertTrue(any("未定義の学習目標" in e for e in errs))
        self.assertTrue(any("確かめる問題が無い" in e for e in errs))

    def test_quiz_answer_must_be_a_choice(self):
        self.edit("education/e/01.src.md", "answer=B", "answer=Z")
        self.assertTrue(any("正答" in e for e in TR.audit(self.root).errors))

    def test_source_change_propagates_to_paper_and_material(self):
        self.assertEqual(PL.cmd_approve(self.root, opts()), 0)
        a = TR.audit(self.root)
        self.assertEqual({it.status for it in [*a.units.values(), *a.edu_items.values()]}, {"OK"})
        # 資料収集工程: 出典URLの訂正
        rel, cols, _, _ = LG.SCHEMAS["sources"]
        rows = list(csv.DictReader((self.root / rel).open(encoding="utf-8")))
        rows[0]["canonical_url"] = "https://example.org/corrected"
        write_csv(self.root / rel, cols, rows)
        a = TR.audit(self.root)
        self.assertEqual(a.units["P1-U001"].status, "STALE")
        self.assertIn("根拠主張 CLAIM-000001 が変更された（上流の改訂）", a.units["P1-U001"].causes)
        self.assertEqual(a.units["P1-U002"].status, "OK")  # 無関係な段落は影響を受けない
        fact = a.edu_items["01#F-01"]
        self.assertEqual(fact.status, "STALE")
        self.assertTrue(any("論文段落 P1-U001" in c for c in fact.causes))
        self.assertEqual(a.edu_items["01#A-01"].status, "OK")

    def test_resume_skips_unchanged_and_reruns_failed(self):
        self.assertEqual(PL.run(self.root, opts()), 0)
        st = read_json(self.root / "STATUS.json")
        self.assertTrue(all(st["stages"][s]["status"] == "done" for s in PL.STAGES))
        self.assertTrue((self.root / "exports" / "education" / "e" / "01_問題.md").exists())
        self.assertTrue((self.root / "exports" / "education" / "e" / "01_解答解説.md").exists())
        first = st["stages"]["render"]["finished_at"]
        self.assertEqual(PL.run(self.root, opts()), 0)
        self.assertEqual(read_json(self.root / "STATUS.json")["stages"]["render"]["finished_at"], first)
        self.edit("papers/p/paper.src.md", "合成の主張1。", "合成の主張1。\n根拠\n:::\n外の文")
        self.assertEqual(PL.run(self.root, opts()), 1)
        st = read_json(self.root / "STATUS.json")
        self.assertEqual(st["stages"]["trace"]["status"], "failed")
        self.assertIn("trace", st["next_action"])

    def test_sync_plan_versions_changed_text_and_holds_binary(self):
        self.assertEqual(PL.run(self.root, opts()), 0)
        (self.root / "exports" / "x.pdf").write_bytes(b"%PDF-1.4 dummy")
        plan = PL.sync_plan(self.root)
        self.assertGreater(plan["queue_text"], 0)
        self.assertEqual(plan["unsynced_binary"], 1)
        rel = "papers/p/paper.src.md"
        size = (self.root / rel).stat().st_size
        ns = SimpleNamespace(rel=rel, dropbox_path=PL.DROPBOX_ROOT + "/" + rel, size=str(size), method="test")
        self.assertEqual(PL.cmd_sync_record(self.root, ns), 0)
        self.edit(rel, "限界。", "限界（改訂）。")
        PL.sync_plan(self.root)
        with (self.root / "sync" / "upload_queue.csv").open(encoding="utf-8") as fh:
            q = {r["rel_path"]: r for r in csv.DictReader(fh)}
        self.assertTrue(q[rel]["dropbox_path"].endswith("paper.src.r2.md"))
        bad = SimpleNamespace(rel=rel, dropbox_path="x", size="1", method="test")
        self.assertEqual(PL.cmd_sync_record(self.root, bad), 1)  # サイズ不一致は同期済みにしない


class SafeEval(unittest.TestCase):
    def test_rejects_code(self):
        for expr in ["__import__('os')", "a+1", "2**1000", "[1]"]:
            with self.assertRaises((ValueError, SyntaxError)):
                TR.safe_eval(expr)

    def test_exact(self):
        self.assertEqual(TR.safe_eval("1-(1-3/4)**3"), TR.number("63/64"))


if __name__ == "__main__":
    unittest.main()
