"""judgment-loop のモックテスト（ネットワーク・有料 API は一切使わない）。

実行: python3 -m unittest discover -s .claude/skills/judgment-loop/tests -v
判断基準はテスト用のダミー文書を使う（本物の非公開パッケージはリポジトリに含めない）。
"""
import io
import json
import os
import sys
import tempfile
import unittest
import urllib.error
import zipfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import orchestrator as orch  # noqa: E402
import review as rv  # noqa: E402

DUMMY_POLICIES = {
    "QUALITY_GATES.md": "# 完了判定\nゲート一覧 DUMMY-QG-INTRO\n\n## リスク重み付け\nDUMMY-QG-RISK\n\n## 評価尺度\nDUMMY-QG-UNSELECTED\n",
    "DECISION.md": "# 判断\n## 優先順位\nDUMMY-DEC-PRIO\n## 競合案の採点（目安）\nDUMMY-DEC-SCORE\n",
    "AUTOMATION.md": "# 自動化\n## 許可の4段階\nDUMMY-AUTO-LEVELS\n## 複数AIの役割\nDUMMY-AUTO-ROLES\n",
    "COGNITIVE_PLAYBOOK.md": "# 認知\n## 2. 相手の理解をモデル化する\nDUMMY-COG-READER\n## 4. 思考のバイアスを抑える\nDUMMY-COG-BIAS\n",
    "INTERPRETATION.md": "# 解釈\n## 第3層：証拠の状態\nDUMMY-INT-L3\n## 第4層：構造\nDUMMY-INT-L4\n",
    "FORECAST_AND_VERIFY.md": "# 予測\n## 反証テストを先に考える\nDUMMY-FC-FALSIFY\n",
    "KNOWLEDGE_MEMORY.md": "# 記憶\n## 新しい情報が来たとき\nDUMMY-KM-NEW\n",
}


def verdict(kind="REVISE", actions=(), issues=(), blocked=None):
    return {
        "verdict": kind, "summary": f"{kind} summary",
        "gate_results": [{"gate": "G1", "status": "PASS" if kind == "PASS" else "INCOMPLETE", "reason": "r"}],
        "issues": [{"id": i[0], "severity": i[1], "target_file": i[2], "location": "L1",
                    "problem": "p", "evidence_refs": ["F-001"], "rule_ref": i[3]} for i in issues],
        "next_actions": [{"id": a[0], "priority": n + 1, "action": a[1], "target_file": a[2],
                          "rationale": "根拠", "verification": "確認方法", "requires_user": a[3] if len(a) > 3 else False,
                          "addresses": []} for n, a in enumerate(actions)],
        "blocked_reason": blocked, "forecast_delta": "予測どおり",
        "questions_for_user": ["Q?"] if blocked else [],
    }


class FakeResp:
    def __init__(self, body):
        self.body = json.dumps(body).encode()

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class Recorder:
    def __init__(self, *responses):
        self.responses, self.requests = list(responses), []

    def __call__(self, req, timeout=None):
        self.requests.append(req)
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return FakeResp(r)


def api_ok(v, inp=1200, outp=300):
    return {"id": "resp_test1", "model": "gpt-6.2-sol", "status": "completed",
            "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(v)}]}],
            "usage": {"input_tokens": inp, "output_tokens": outp}}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.t = Path(self.tmp.name)
        self.env = dict(os.environ)
        os.environ["JUDGMENT_LOOP_HOME"] = str(self.t / "home")
        os.environ["GPT_BRIDGE_STATE_DIR"] = str(self.t / "bridge")
        os.environ["JUDGMENT_LOOP_NOW"] = "2026-11-24T10:00:00+09:00"
        for k in [k for k in os.environ if k.startswith("GPT_BRIDGE_") and k != "GPT_BRIDGE_STATE_DIR"]:
            del os.environ[k]
        # 判断基準パッケージ（ダミー）。private-local は取り込まれないことも確認する
        z = self.t / "pkg.zip"
        with zipfile.ZipFile(z, "w") as zf:
            for n, body in DUMMY_POLICIES.items():
                zf.writestr(f"pkg/policies/{n}", body)
            zf.writestr("pkg/private-local/PROFILE.md", "PRIVATE-SHOULD-NOT-IMPORT")
            zf.writestr("pkg/CLAUDE.md", "root rules")
        self.ok("policies-import", str(z))
        self.ok("ws-create", "tk", "--mode", "interview", "--alias", "面接テスト")
        self.ok("ws-create", "jh", "--mode", "jobhunt", "--target", "A社")
        self.ok("ref-add", "--ws", "tk", "--role", "baseline", "--kind", "dropbox", "--ref", "id:dummy",
                "--title", "面接カード")
        self.ok("redact-add", "山田太郎")
        self.ok("fact-add", "--statement", "研究室で換気シミュレーションを担当した", "--source", "本人確認",
                "--observed", "2026-11-20", "--status", "verified", "--gpt-ok")                 # F-001
        self.ok("fact-add", "--statement", "非公開の健康情報", "--source", "本人",
                "--observed", "2026-11-20", "--status", "verified", "--sensitivity", "secret", "--gpt-ok")  # F-002
        self.ok("fact-add", "--statement", "A社の選考状況", "--source", "本人", "--observed", "2026-11-20",
                "--status", "reported", "--scope", "ws:jh", "--gpt-ok")                         # F-003
        self.ok("evidence-add", "--ws", "tk", "--claim", "組織の方針X", "--url", "https://example.org/plan.pdf",
                "--title", "公式計画", "--retrieved", "2026-11-23", "--locator", "p.12 第3章",
                "--excerpt", "方針Xを推進する")                                                    # E-001
        self.art = self.t / "home/workspaces/tk/artifacts/answers.md"
        self.write_art("志望動機: 山田太郎です。連絡先 taro@example.com。換気の研究を活かしたい。\n")

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.env)
        self.tmp.cleanup()

    def write_art(self, text):
        self.art.write_text(text, encoding="utf-8")

    def run_cli(self, *argv, opener=None):
        o, e = io.StringIO(), io.StringIO()
        with redirect_stdout(o), redirect_stderr(e):
            code = orch.main(list(argv), opener=opener)
        return code, o.getvalue(), e.getvalue()

    def ok(self, *argv, opener=None):
        code, o, e = self.run_cli(*argv, opener=opener)
        self.assertEqual(code, 0, f"{argv}: {e}")
        try:
            return json.loads(o)
        except json.JSONDecodeError:
            return o

    def bad(self, code_expected, *argv, opener=None):
        code, o, e = self.run_cli(*argv, opener=opener)
        self.assertEqual(code, code_expected, f"{argv}: stdout={o} stderr={e}")
        return e

    def mock(self, obj, name):
        p = self.t / name
        p.write_text(obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False), encoding="utf-8")
        return str(p)

    def state(self):
        h = Path(os.environ["JUDGMENT_LOOP_HOME"])
        return json.loads(next((h / "workspaces").glob("*/runs/*/state.json")).read_text())

    def submit(self, *extra):
        return self.ok("submit", "--artifact", "answers.md", "--facts", "F-001", "--evidence", "E-001",
                       "--summary", "回答を作成", "--log", "面接カードと照合", "--forecast", "具体性の指摘を予想",
                       *extra)

    def start(self, n=3, ws="tk", tt="answer_improve"):
        return self.ok("start", "--ws", ws, "--task-type", tt, "--goal", "志望動機の回答を改善", "--max-iterations", str(n))

    def approve(self, *over):
        args = {"--model": "gpt-6.2-sol", "--max-iterations": "3", "--max-calls": "3", "--max-input-tokens": "60000",
                "--max-output-tokens": "9000", "--output-tokens-per-call": "3000",
                "--data": "policies,artifacts,facts,evidence", "--expires": "2026-11-25T23:59:00+09:00",
                "--user-quote": "3回まで、6万トークンまでで実行してよい"}
        for k, v in zip(over[::2], over[1::2]):
            args[k] = v
        return self.ok("approve", *[x for kv in args.items() for x in kv])


class TestThreeIterationLoop(Base):
    """Claude→GPT→Claude を 3 反復。停止・再開・エラー復旧・コンテナ移動・履歴保持を確認する。"""

    def test_full_loop(self):
        self.start()
        self.assertEqual(self.ok("next")["status"], "awaiting_work")

        # ---- 反復 1: REVISE。禁止操作と存在しないファイルへの指示は自動不採用
        self.submit()
        r = self.ok("review", "--mock", self.mock(verdict("REVISE", actions=[
            ("A1", "結論を冒頭に置き、研究での役割を F-001 の範囲で具体化する", "answers.md"),
            ("A2", "完成したら ES を提出する", "answers.md"),
            ("A3", "別資料を直す", "missing.md")],
            issues=[("I1", "P1", "answers.md", "QUALITY_GATES#__intro__")]), "m1.json"))
        self.assertEqual(r["verdict"], "REVISE")
        auto = {a["id"]: a["decision"] for a in r["next_actions"]}
        self.assertEqual(auto, {"A1": None, "A2": "rejected_auto", "A3": "rejected_auto"})
        self.bad(2, "decide", "--action", "A2", "--accept", "--reason", "提出したい理由", "--checked", "x")
        self.bad(2, "decide", "--action", "A1", "--accept", "--reason", "根拠を確認した結果")  # --checked 必須
        d = self.ok("decide", "--action", "A1", "--accept", "--reason", "1行目に結論がなく F-001 と整合を確認",
                    "--checked", "answers.md L1 / F-001")
        self.assertEqual((d["status"], d["iteration"]), ("awaiting_work", 2))
        self.assertEqual([a["id"] for a in self.ok("next")["accepted_actions"]], ["A1"])

        # ---- 中断と再開
        self.ok("pause", "--reason", "ユーザーが中断")
        self.assertFalse(self.ok("next")["may_continue_autonomously"])
        self.bad(2, "submit", "--artifact", "answers.md", "--summary", "s", "--log", "l", "--forecast", "f")
        self.ok("resume")
        self.assertEqual(self.state()["status"], "awaiting_work")

        # ---- 反復 2: 採用指示の実施報告なしでは提出不可
        self.write_art("結論: 換気研究で担当した解析を活かしたい。\n")
        self.bad(2, "submit", "--artifact", "answers.md", "--summary", "s", "--log", "l", "--forecast", "f")
        self.submit("--done", "A1")

        # コンテナ移動: スナップショットを書き出し、新しいホームに取り込んで続行
        snap = self.t / "snap.json"
        self.ok("export", "--out", str(snap))
        os.environ["JUDGMENT_LOOP_HOME"] = str(self.t / "home2")
        self.ok("import", str(snap))
        self.art = self.t / "home2/workspaces/tk/artifacts/answers.md"
        self.assertEqual(self.ok("next")["status"], "awaiting_review")

        # GPT が JSON 以外を返す → エラー記録、状態は awaiting_review のまま
        e = self.bad(3, "review", "--mock", self.mock("申し訳ありませんが…", "bad.txt"))
        self.assertIn("構造化出力が不正", e)
        st = self.state()
        self.assertEqual(st["status"], "awaiting_review")
        self.assertTrue(list((self.t / "home2").glob("workspaces/tk/runs/*/iterations/002/raw_output.txt")))
        # 再レビューで回復
        r = self.ok("review", "--mock", self.mock(verdict("REVISE", actions=[
            ("B1", "追質問『なぜその解析か』への答えを1文追加", "answers.md")],
            issues=[("I2", "P2", "answers.md", "COGNITIVE_PLAYBOOK#2. 相手の理解をモデル化する")]), "m2.json"))
        self.assertEqual(r["status"], "awaiting_decisions")
        self.ok("decide", "--action", "B1", "--accept", "--reason", "追質問への備えが欠けていると確認",
                "--checked", "answers.md L1")

        # ---- 反復 3: 通信中にプロセスが落ちた想定 → recover → PASS → Claude の最終確認
        self.write_art("結論: 換気研究で担当した解析を活かしたい。理由は現場の温熱課題に直結するため。\n")
        self.submit("--done", "B1")
        sp = next((self.t / "home2/workspaces").glob("*/runs/*/state.json"))
        st = json.loads(sp.read_text())
        st["status"] = "reviewing"
        sp.write_text(json.dumps(st))
        self.bad(2, "review", "--mock", self.mock(verdict("PASS"), "m3.json"))
        self.ok("recover")
        r = self.ok("review", "--mock", self.mock(verdict("PASS"), "m3.json"))
        self.assertEqual(r["status"], "awaiting_final_check")
        self.ok("finish", "--reason", "F-001 と一致、結論先行、追質問対応を確認")
        self.assertEqual(self.state()["status"], "done")

        # ---- 履歴の保持
        rid = self.state()["id"]
        hist = [h["event"] for h in self.ok("history", "--run", rid)]
        for ev in ("start", "submit", "review", "decisions", "pause", "resume", "review_error", "recover", "done"):
            self.assertIn(ev, hist)
        run = next((self.t / "home2/workspaces").glob("*/runs/*"))
        for n in ("001", "002", "003"):
            self.assertTrue((run / "iterations" / n / "submission.json").exists(), n)
            self.assertTrue((run / "iterations" / n / "verdict.json").exists(), n)
        snaps = [(run / f"iterations/{n}/artifacts/answers.md").read_text() for n in ("001", "002", "003")]
        self.assertEqual(len(set(snaps)), 3)  # 各反復の成果物を別々に保存
        dec1 = json.loads((run / "iterations/001/decisions.json").read_text())
        self.assertEqual({x["id"]: x["decision"] for x in dec1},
                         {"A1": "accepted", "A2": "rejected_auto", "A3": "rejected_auto"})


class TestPacketPrivacy(Base):
    def test_packet_contains_only_selected_and_redacted(self):
        self.start()
        self.submit()
        o = self.ok("review", "--show-packet")
        meta, packet = o.split("\n}\n", 1) if isinstance(o, str) else ("", "")
        info = json.loads(meta + "\n}")
        self.assertTrue(info["dry_run"])
        for must in ("DUMMY-QG-INTRO", "DUMMY-QG-RISK", "DUMMY-DEC-PRIO", "DUMMY-AUTO-ROLES",
                     "DUMMY-COG-READER", "DUMMY-COG-BIAS", "DUMMY-INT-L3", "F-001", "E-001",
                     "https://example.org/plan.pdf", "p.12 第3章", "2026-11-23"):
            self.assertIn(must, packet)
        for never in ("DUMMY-QG-UNSELECTED", "DUMMY-AUTO-LEVELS", "DUMMY-DEC-SCORE", "DUMMY-FC-FALSIFY",
                      "山田太郎", "taro@example.com", "非公開の健康情報", "A社の選考状況", "PRIVATE-SHOULD"):
            self.assertNotIn(never, packet)
        self.assertIn("[本人情報]", packet)
        self.assertEqual(info["data_classes"], ["artifacts", "evidence", "facts", "policies"])

    def test_private_local_not_imported(self):
        self.assertFalse(list((self.t / "home/policies").glob("PROFILE*")))
        self.assertFalse((self.t / "home/policies/CLAUDE.md").exists())

    def test_secret_fact_blocked_and_other_workspace_isolated(self):
        self.start()
        self.bad(2, "submit", "--artifact", "answers.md", "--facts", "F-003", "--summary", "s", "--log", "l",
                  "--forecast", "f")
        self.ok("submit", "--artifact", "answers.md", "--facts", "F-002", "--summary", "s", "--log", "l",
                "--forecast", "f")
        e = self.bad(2, "review")
        self.assertIn("送信が許可されていない", e)

    def test_superseded_fact_not_usable(self):
        self.ok("fact-add", "--statement", "担当範囲を訂正", "--source", "本人確認", "--observed", "2026-11-24",
                "--status", "verified", "--gpt-ok", "--supersedes", "F-001")
        ids = [f["id"] for f in self.ok("fact-list", "--ws", "tk")]
        self.assertNotIn("F-001", ids)
        self.assertIn("F-004", ids)

    def test_home_inside_git_refused(self):
        os.environ["JUDGMENT_LOOP_HOME"] = str(Path(__file__).resolve().parents[1] / ".home-test")
        self.assertEqual(self.run_cli("ws-list")[0], 2)

    def test_interview_requires_baseline(self):
        self.ok("ws-create", "tk2", "--mode", "interview")
        e = self.bad(2, "start", "--ws", "tk2", "--task-type", "deep_questions", "--goal", "g")
        self.assertIn("基準資料", e)


class TestApprovalAndBudget(Base):
    def test_send_requires_approval(self):
        self.start()
        self.submit()
        e = self.bad(2, "review", "--send", opener=Recorder())
        self.assertIn("包括承認", e)

    def test_send_structured_without_auth_header_and_budget(self):
        self.start()
        self.approve("--max-calls", "1")
        self.submit()
        rec = Recorder(api_ok(verdict("REVISE", actions=[("A1", "具体化する", "answers.md")])))
        r = self.ok("review", "--send", opener=rec)
        self.assertEqual(r["verdict"], "REVISE")
        req = rec.requests[0]
        self.assertNotIn("authorization", {k.lower() for k, _ in req.header_items()})
        body = json.loads(req.data)
        self.assertEqual(body["model"], "gpt-6.2-sol")
        self.assertEqual(body["text"]["format"]["type"], "json_schema")
        self.assertTrue(body["text"]["format"]["strict"])
        self.assertEqual(body["max_output_tokens"], 3000)
        self.assertFalse(body["store"])
        self.assertNotIn("山田太郎", body["input"])
        st = self.state()
        self.assertEqual(st["usage"], {"calls": 1, "input_tokens": 1200, "output_tokens": 300, "usd": 0.0})
        self.ok("decide", "--action", "A1", "--accept", "--reason", "具体性不足を確認した", "--checked", "L1")
        self.submit("--done", "A1")
        e = self.bad(2, "review", "--send", opener=Recorder(api_ok(verdict("PASS"))))
        self.assertIn("呼び出し回数", e)

    def test_http_error_no_retry_and_counted(self):
        self.start()
        self.approve()
        self.submit()
        err = urllib.error.HTTPError("u", 500, "e", {}, io.BytesIO(b'{"error":{"code":"server_error"}}'))
        rec = Recorder(err, api_ok(verdict("PASS")))
        self.bad(3, "review", "--send", opener=rec)
        self.assertEqual(len(rec.requests), 1)  # 自動再試行しない
        st = self.state()
        self.assertEqual((st["status"], st["usage"]["calls"]), ("awaiting_review", 1))
        self.ok("review", "--send", opener=rec)  # 明示的な再試行は承認範囲内で可
        self.assertEqual(self.state()["usage"]["calls"], 2)

    def test_expired_and_data_class(self):
        self.start()
        self.approve("--data", "policies,artifacts")
        self.submit()
        e = self.bad(2, "review", "--send", opener=Recorder())
        self.assertIn("承認されていないデータ区分", e)
        self.approve()
        os.environ["JUDGMENT_LOOP_NOW"] = "2026-11-26T09:00:00+09:00"
        e = self.bad(2, "review", "--send", opener=Recorder())
        self.assertIn("承認期限", e)

    def test_usd_budget(self):
        self.start()
        self.approve("--max-usd", "0.01", "--price-in", "10", "--price-out", "40")
        self.submit()
        e = self.bad(2, "review", "--send", opener=Recorder())
        self.assertIn("費用予算", e)

    def test_no_fixed_caps_but_explicit_positive_limits(self):
        self.start(n=50)
        r = self.approve("--max-iterations", "50", "--max-calls", "500", "--max-input-tokens", "30000000",
                         "--max-output-tokens", "5000000", "--output-tokens-per-call", "32000",
                         "--expires", "2027-06-30T23:59:00+09:00")
        self.assertEqual(r["approval"]["max_calls"], 500)          # 固定上限なし（承認値が上限）
        self.bad(2, "approve", "--model", "m", "--max-iterations", "3", "--max-calls", "0",
                 "--max-input-tokens", "1", "--max-output-tokens", "1", "--output-tokens-per-call", "1",
                 "--data", "policies", "--expires", "2026-11-25T00:00", "--user-quote", "ok")   # 無制限・0 は不可
        self.bad(2, "approve", "--model", "m", "--max-iterations", "3", "--max-calls", "1",
                 "--max-input-tokens", "1", "--max-output-tokens", "100", "--output-tokens-per-call", "200",
                 "--data", "policies", "--expires", "2026-11-25T00:00", "--user-quote", "ok")   # 1 回 > 合計
        self.bad(2, "approve", "--model", "m", "--max-iterations", "3", "--max-calls", "1",
                 "--max-input-tokens", "1", "--max-output-tokens", "1", "--output-tokens-per-call", "1",
                 "--data", "policies", "--expires", "2026-11-25T00:00", "--user-quote", " ")

    def test_split_review_never_truncates(self):
        self.start()
        lines = [f"行{i:04d} 内容{'あ' * 40}" for i in range(1, 1201)]
        self.write_art("\n".join(lines))
        self.approve("--max-input-per-call", "20000", "--max-calls", "20", "--max-input-tokens", "500000", "--max-output-tokens", "400000")
        self.submit()
        o = self.ok("review", "--show-packet")
        meta, packets = o.split("\n}\n", 1)
        info = json.loads(meta + "\n}")
        self.assertGreater(info["parts"], 1)
        for i in (1, 600, 1200):                                  # 全行がどこかのパートに含まれる
            self.assertIn(f"行{i:04d}", packets)
        self.assertNotIn("TRUNCATED", packets)
        v1 = verdict("REVISE", actions=[("A1", "具体化", "answers.md (lines 1-300)")],
                     issues=[("I1", "P2", "answers.md (lines 1-300)", "x")])
        rec = Recorder(*[api_ok(v1)] * info["parts"])
        r = self.ok("review", "--send", opener=rec)
        self.assertEqual(len(rec.requests), info["parts"])
        self.assertEqual(self.state()["usage"]["calls"], info["parts"])
        self.assertEqual(len(r["next_actions"]), info["parts"])   # 統合（id は p1-A1, p2-A1, …）
        self.assertTrue(all(a["decision"] is None for a in r["next_actions"]))  # 行範囲付きでも対象として有効

    def test_mock_on_split_packet_applies_once_with_source_label(self):
        self.start()
        self.write_art("\n".join(f"行{i:04d} {'あ' * 40}" for i in range(1, 1201)))
        self.approve("--max-input-per-call", "20000", "--max-calls", "20", "--max-input-tokens", "500000",
                     "--max-output-tokens", "400000")
        self.submit()
        r = self.ok("review", "--mock", self.mock(verdict("REVISE", actions=[("A1", "具体化", "answers.md")]), "m.json"),
                    "--mock-source", "claude-independent")
        self.assertGreater(r["parts"], 1)
        self.assertEqual([a["id"] for a in r["next_actions"]], ["A1"])     # 重複しない
        st = self.state()
        self.assertEqual(st["last_verdict"]["source"], "claude-independent")
        self.assertEqual(st["usage"]["calls"], 0)                          # 代替入力は予算を使わない

    def test_policies_full_option(self):
        self.start()
        self.submit()
        o = self.ok("review", "--policies", "full", "--show-packet")
        self.assertIn("DUMMY-QG-UNSELECTED", o)
        self.assertIn("DUMMY-AUTO-LEVELS", o)

    def test_halt_blocks_review(self):
        self.start()
        self.submit()
        self.ok("halt", "--reason", "全部止めて")
        self.assertFalse(self.ok("next")["may_continue_autonomously"])
        self.bad(2, "review", "--mock", self.mock(verdict("PASS"), "p.json"))
        self.ok("unhalt")
        self.ok("review", "--mock", self.mock(verdict("PASS"), "p.json"))


class TestStopConditions(Base):
    def test_stalled_on_repeated_issues(self):
        self.start()
        v = verdict("REVISE", actions=[("A1", "具体化", "answers.md")],
                    issues=[("I1", "P1", "answers.md", "QUALITY_GATES#__intro__")])
        self.submit()
        self.ok("review", "--mock", self.mock(v, "v.json"))
        self.ok("decide", "--action", "A1", "--accept", "--reason", "具体性不足を確認", "--checked", "L1")
        self.submit("--done", "A1")
        r = self.ok("review", "--mock", self.mock(v, "v.json"))
        self.assertEqual(r["status"], "stalled")
        self.assertFalse(self.ok("next")["may_continue_autonomously"])
        self.bad(2, "resume")
        self.ok("resume", "--note", "表現ではなく構成から見直す")
        st = self.state()
        self.assertEqual((st["status"], st["iteration"]), ("awaiting_work", 3))
        self.assertEqual([a["id"] for a in st["accepted_actions"]], ["U1"])

    def test_blocked_then_resume(self):
        self.start()
        self.submit()
        r = self.ok("review", "--mock", self.mock(verdict("BLOCKED", blocked="役割の事実確認が必要"), "b.json"))
        self.assertEqual(r["status"], "blocked")
        self.assertEqual(r["questions_for_user"], ["Q?"])
        self.ok("resume", "--note", "役割は解析担当で確定")
        self.assertEqual(self.state()["status"], "awaiting_work")

    def test_requires_user_stops_loop(self):
        self.start()
        self.submit()
        self.ok("review", "--mock", self.mock(verdict("REVISE", actions=[
            ("A1", "本人に指導教員名の公開可否を確認", "-", True)]), "u.json"))
        self.ok("decide", "--action", "A1", "--accept", "--reason", "本人しか判断できないと確認", "--checked", "F-001")
        self.assertEqual(self.state()["status"], "needs_user")

    def test_iteration_limit_and_extend(self):
        self.start(n=1)
        self.approve("--max-iterations", "1")
        self.submit()
        self.ok("review", "--mock", self.mock(verdict("REVISE", actions=[("A1", "具体化", "answers.md")]), "l.json"))
        self.ok("decide", "--action", "A1", "--accept", "--reason", "具体性不足を確認", "--checked", "L1")
        self.assertEqual(self.state()["status"], "limit_reached")
        self.bad(2, "extend", "--max-iterations", "2", "--user-quote", " ")
        self.ok("extend", "--max-iterations", "2", "--user-quote", "もう1回だけ許可")
        st = self.state()
        self.assertEqual((st["status"], st["iteration"]), ("awaiting_work", 2))

    def test_pass_downgraded_when_severe_issue(self):
        self.start()
        self.submit()
        r = self.ok("review", "--mock", self.mock(verdict("PASS", actions=[("A1", "修正", "answers.md")],
                                                          issues=[("I1", "P0", "answers.md", "x")]), "p.json"))
        self.assertEqual(r["verdict"], "REVISE")
        self.assertTrue(r["normalization"])

    def test_claude_can_reject_pass(self):
        self.start()
        self.submit()
        self.ok("review", "--mock", self.mock(verdict("PASS"), "p.json"))
        self.ok("finish", "--reject-pass", "--reason", "F-001 と食い違う記述が残っている")
        st = self.state()
        self.assertEqual((st["status"], st["iteration"]), ("awaiting_work", 2))


class TestReviewModule(unittest.TestCase):
    def test_schema_is_strict_compatible(self):
        def walk(s):
            if s.get("type") == "object":
                self.assertFalse(s["additionalProperties"])
                self.assertEqual(sorted(s["required"]), sorted(s["properties"]))
                for v in s["properties"].values():
                    walk(v)
            if s.get("type") == "array":
                walk(s["items"])
        walk(rv.VERDICT_SCHEMA)

    def test_parse_fenced_json(self):
        self.assertEqual(rv.parse_model_text('```json\n{"a": 1}\n```'), {"a": 1})

    def test_validation_errors(self):
        with self.assertRaises(rv.VerdictError):
            rv.validate_verdict({"verdict": "MAYBE"})
        with self.assertRaises(rv.VerdictError):
            rv.validate_verdict(verdict("REVISE"))           # 次の作業なし
        with self.assertRaises(rv.VerdictError):
            rv.validate_verdict(verdict("BLOCKED"))          # 理由なし

    def test_forbidden_action_patterns(self):
        for t in ("ES を提出する", "応募フォームから送信して完了する", "採用担当者にメールを送信する",
                  "main ブランチに push する", "SNS に投稿する"):
            self.assertTrue(orch.FORBIDDEN_ACTION.search(t), t)
        for t in ("ES の第2段落を具体化する", "面接カードとの矛盾を一覧にする", "提出前チェックリストを作る"):
            self.assertFalse(orch.FORBIDDEN_ACTION.search(t), t)


if __name__ == "__main__":
    unittest.main()
