"""career-master ツールのテスト（合成データのみ。ネットワーク・個人データなし）。

実行: python3 -m unittest discover -s .claude/skills/career-master/tests -v
"""
import hashlib
import json
import os
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def conv(i, n):
    mp, prev = {}, None
    for k in range(n):
        mid = f"m{i}-{k}"
        mp[mid] = {"id": mid, "parent": prev, "children": [], "message": {
            "author": {"role": "user" if k % 2 == 0 else "assistant"}, "create_time": 1790000000 + i * 1000 + k,
            "content": {"content_type": "text", "parts": [f"会話{i} 発言{k} 面接の準備と換気の研究 " + "あ" * random.randint(0, 300)]},
            "metadata": {"model_slug": "x"}}}
        prev = mid
    return {"title": f"テスト会話{i}", "create_time": 1790000000 + i * 1000, "update_time": 1790000000 + i * 1000 + n,
            "mapping": mp, "current_node": prev, "conversation_id": f"c{i}"}


class TestChatIndex(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        (self.home / "raw" / "chatgpt_recovered").mkdir(parents=True)
        self.env = dict(os.environ, CAREER_MASTER_HOME=str(self.home))
        random.seed(1)
        self.files = {
            "ads.json": json.dumps({"a": 1}),
            "chat.html": "<html>" + "x" * 5000 + "</html>",
            "conversations-000.json": json.dumps([conv(i, 6) for i in range(40)], ensure_ascii=False),
            # 2本目には c3 の重複を入れる（重複は数えない）
            "conversations-001.json": json.dumps([conv(i, 4) for i in range(40, 70)] + [conv(3, 6)], ensure_ascii=False),
        }
        blob = b""
        for n, c in self.files.items():
            blob += f"\n\n===== BEGIN: {n} =====\n".encode() + c.encode() + f"\n===== END: {n} (complete=True) =====\n".encode()
        self.blob = blob
        # 目印の途中で切れる境界をわざと入れる
        cuts = {blob.find(b"===== BEGIN: conversations-000") + 9,
                blob.find(b"(complete=True) =====\n\n\n===== BEGIN: conversations-001") + 5}
        pts = sorted(set(range(7001, len(blob), 7001)) | cuts) + [len(blob)]
        pos = 0
        for k, pt in enumerate(pts, 1):
            (self.home / "raw" / "chatgpt_recovered" / f"recovered_{k:03d}.txt").write_bytes(blob[pos:pt])
            pos = pt
        self.n_chunks = len(pts)

    def tearDown(self):
        self.tmp.cleanup()

    def run_tool(self, *args, ok=True):
        r = subprocess.run([sys.executable, str(SCRIPTS / "chat_index.py"), *args], capture_output=True, text=True, env=self.env)
        if ok:
            self.assertEqual(r.returncode, 0, r.stderr)
        return r

    def test_reassemble_is_byte_identical_and_index_dedupes(self):
        rep = json.loads(self.run_tool("reassemble").stdout)
        self.assertEqual(rep["chunks"], self.n_chunks)
        self.assertEqual(rep["orphan_segments"], 0)
        got = {f["name"]: f["sha256"] for f in rep["files"]}
        exp = {n: hashlib.sha256(c.encode()).hexdigest() for n, c in self.files.items()}
        self.assertEqual(got, exp)                                   # 分割前と1バイトも違わない
        self.assertTrue(all(f["complete"] for f in rep["files"]))
        self.run_tool("build")
        st = json.loads(self.run_tool("stats").stdout)
        self.assertEqual(st["conversations"], 70)                    # c3 の重複は1件として数える
        self.assertEqual(st["messages"], 40 * 6 + 30 * 4)
        self.assertEqual(st["by_role"]["user"], 40 * 3 + 30 * 2)
        notes = {b[0]: b[4] for b in st["build_log"]}
        self.assertEqual(notes["chat.html"], "not_indexed")

    def test_search_separates_speaker_and_handles_short_terms(self):
        self.run_tool("reassemble")
        self.run_tool("build")
        both = json.loads(self.run_tool("search", "換気の研究", "--count").stdout)["matches"]
        user = json.loads(self.run_tool("search", "換気の研究", "--role", "user", "--count").stdout)["matches"]
        self.assertEqual((both, user), (360, 180))
        short = json.loads(self.run_tool("search", "面接", "--role", "user", "--count").stdout)["matches"]
        self.assertEqual(short, 180)                                  # 2文字の語は LIKE で補う
        out = self.run_tool("show", "c3", "--n", "1").stdout
        self.assertIn("conversations-000.json @byte", out)            # 原文の位置へ戻れる

    def test_missing_chunk_is_refused(self):
        (self.home / "raw" / "chatgpt_recovered" / "recovered_002.txt").unlink()
        r = self.run_tool("reassemble", ok=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("欠けて", r.stderr)


PACK = """# テスト用パック
前置き

## 1. 柱3本
1. **目標**＝A
2. **進め方**＝B
3. **現場で**＝C

## 2. プレゼン（1,000字）
【0 導入】
はじめます。

【1 本論】
本論です。「引用」も入ります。

**時間**（目安）：①0:10 ②0:40。
**時間が押したとき**：最後の1文だけ言う。

### 手持ちメモ
```
0 導入
1 本論
```

## 3. 質問（最初の1文は太字）
**Q1 なぜ志望したのですか**（F-001）
**「理由は一つです。」** 続きの説明です。
→「具体的には？」：具体例を答えます。
（注意書き）

**Q2 <b>危険な</b>質問**
**「はい。」** 答え。

**専門の確認（短く）**
- 用語とは：「説明です。」

**短く答える2問**
- 時期：「来年です。」

分からない質問：「確かめます。」

## 4. 言い直す語
- A→**B**

## 5. グループワーク
- 役割：整理する。

## 7. 持ち物と段取り
- シートを持つ。

## 8. 今夜の練習
1. 2回計る。
"""


class TestBuildTrainer(unittest.TestCase):
    def test_page_contains_pack_text_unchanged_and_no_external_requests(self):
        with tempfile.TemporaryDirectory() as t:
            src, out = Path(t) / "pack.md", Path(t) / "t.html"
            src.write_text(PACK, encoding="utf-8")
            r = subprocess.run([sys.executable, str(SCRIPTS / "build_trainer.py"), str(src), str(out), "--title", "練習"],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            info = json.loads(r.stdout)
            self.assertEqual((info["script_blocks"], info["qa"], info["follows"], info["spec"], info["short"]), (2, 2, 1, 1, 1))
            page = out.read_text(encoding="utf-8")
            data = json.loads(page[page.index("const D=") + 8:page.index(";\nconst $=")].replace("<\\/", "</"))
            self.assertEqual(data["qa"][0]["first"], "理由は一つです。")
            self.assertEqual(data["qa"][0]["follows"], [{"q": "具体的には？", "a": "具体例を答えます。"}])
            self.assertEqual(data["script"][1]["text"], "本論です。「引用」も入ります。")
            self.assertIn("<b>危険な</b>", data["qa"][1]["q"])        # データは原文のまま持ち、表示時にエスケープする
            self.assertIn("const esc=", page)
            for needle in ("http://", "https://", "<script src", "<link ", "fetch(", "XMLHttpRequest"):
                self.assertNotIn(needle, page)                         # 外部通信なし


class TestExportReviewRuns(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "home"
        self.env = dict(os.environ, JUDGMENT_LOOP_HOME=str(self.home))

        def run(name, events, iters):
            d = self.home / "workspaces" / "w" / "runs" / name
            d.mkdir(parents=True)
            (d / "state.json").write_text(json.dumps({"id": name, "goal": "g", "status": "done", "usage": {"calls": 0}}))
            (d / "history.jsonl").write_text("\n".join(json.dumps(e) for e in events))
            for n, files in iters.items():
                i = d / "iterations" / n
                i.mkdir(parents=True)
                for fn, obj in files.items():
                    (i / fn).write_text(obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False))

        verdict = {"verdict": "REVISE", "summary": "s", "issues": [{"severity": "P1"}],
                   "next_actions": [{"id": "A1", "action": "直す"}], "questions_for_user": []}
        run("r-failed", [{"event": "review_send", "iteration": 1}, {"event": "review_error", "iteration": 1, "error": "HTTP 429"}],
            {"001": {"submission.json": {"artifacts": ["a.md"]}, "packet_part1.txt": "p"}})
        run("r-indep", [{"event": "review", "iteration": 1, "source": "claude-independent"}],
            {"001": {"submission.json": {"artifacts": ["a.md"]}, "verdict.json": verdict,
                     "decisions.json": [{"id": "A1", "decision": "accepted", "reason": "確認した", "checked": "a.md:3"}]}})
        run("r-gpt", [{"event": "review_send", "iteration": 1}, {"event": "review", "iteration": 1, "source": "gpt-x"}],
            {"001": {"verdict.json": verdict}})

    def tearDown(self):
        self.tmp.cleanup()

    def test_kinds_are_kept_apart(self):
        out = Path(self.tmp.name) / "out"
        r = subprocess.run([sys.executable, str(SCRIPTS / "export_review_runs.py"), "--out", str(out)],
                           env=self.env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        text = (out / "review_runs_index.md").read_text(encoding="utf-8")
        rows = {l.split("|")[1].strip(): l for l in text.splitlines() if l.startswith("| w/")}
        self.assertIn("gpt-send-failed", rows["w/r-failed"])
        self.assertIn("判定なし", rows["w/r-failed"])
        self.assertIn("成功 0／失敗 1", rows["w/r-failed"])
        self.assertIn("claude-independent", rows["w/r-indep"])
        self.assertNotIn("gpt-send", rows["w/r-indep"])
        self.assertIn("gpt-send（gpt-x）", rows["w/r-gpt"])
        self.assertIn("成功 1／失敗 0", rows["w/r-gpt"])
        self.assertIn("| A1 | 直す | accepted | 確認した | a.md:3 |", text)
        self.assertTrue((out / "runs" / "w" / "r-failed" / "iterations" / "001" / "packet_part1.txt").exists())

    def test_refuses_git_worktree(self):
        repo = Path(self.tmp.name) / "repo"
        (repo / ".git").mkdir(parents=True)
        r = subprocess.run([sys.executable, str(SCRIPTS / "export_review_runs.py"), "--out", str(repo / "x")],
                           env=self.env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        self.assertFalse((repo / "x").exists())


if __name__ == "__main__":
    unittest.main()
