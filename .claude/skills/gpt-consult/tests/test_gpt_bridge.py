"""gpt_bridge のモックテスト（ネットワーク・API 呼び出しは一切行わない）。

実行: python3 -m unittest discover -s .claude/skills/gpt-consult/tests -v
"""
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
import urllib.error
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import gpt_bridge as gb  # noqa: E402


def fake_response(text="OK", status="completed", reason=None):
    r = {
        "id": "resp_abc123", "model": "gpt-6.2-sol", "status": status,
        "output": [
            {"type": "reasoning", "summary": []},
            {"type": "message", "role": "assistant",
             "content": [{"type": "output_text", "text": text}]},
        ],
        "usage": {"input_tokens": 11, "output_tokens": 7},
    }
    if reason:
        r["incomplete_details"] = {"reason": reason}
    return r


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
    """urlopen の代わり。送られたリクエストを記録し、用意した応答を返す。"""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests = []

    def __call__(self, req, timeout=None):
        self.requests.append(req)
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return FakeResp(r)


def http_error(code, body):
    return urllib.error.HTTPError("https://api.openai.com/v1/responses", code, "err", {},
                                  io.BytesIO(json.dumps(body).encode()))


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "repo"
        self.root.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q",
                        "--allow-empty", "-m", "init"], cwd=self.root, check=True)
        (self.root / "app.py").write_text("def add(a, b):\n    return a - b\n")
        self.state = Path(self.tmp.name) / "state"
        self.old_env = dict(os.environ)
        os.environ["GPT_BRIDGE_STATE_DIR"] = str(self.state)
        for k in list(os.environ):
            if k.startswith("GPT_BRIDGE_") and k != "GPT_BRIDGE_STATE_DIR":
                del os.environ[k]
        self.old_cwd = os.getcwd()
        os.chdir(self.root)
        gb.time.sleep = lambda s: None  # リトライ待ちを省略

    def tearDown(self):
        os.chdir(self.old_cwd)
        os.environ.clear()
        os.environ.update(self.old_env)
        self.tmp.cleanup()

    def run_main(self, argv, opener=None, stdin=""):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = gb.main(argv, opener=opener, stdin=io.StringIO(stdin))
        return code, out.getvalue(), err.getvalue()


class TestDryRunAndSend(Base):
    def test_dry_run_is_default_and_makes_no_request(self):
        rec = Recorder()
        code, out, _ = self.run_main(["review", "バグを探して", "-f", "app.py"], opener=rec)
        self.assertEqual(code, 0)
        self.assertEqual(rec.requests, [])
        info = json.loads(out)
        self.assertTrue(info["dry_run"])
        self.assertEqual(info["model"], "gpt-6.2-sol")
        self.assertEqual(info["context"], ["file:app.py"])

    def test_send_posts_to_responses_without_authorization(self):
        rec = Recorder(fake_response("a - b は誤り"))
        code, out, err = self.run_main(["review", "バグ", "-f", "app.py", "--send"], opener=rec)
        self.assertEqual(code, 0, err)
        req = rec.requests[0]
        self.assertEqual(req.full_url, "https://api.openai.com/v1/responses")
        self.assertEqual(req.get_method(), "POST")
        self.assertNotIn("authorization", {k.lower() for k, _ in req.header_items()})
        body = json.loads(req.data)
        self.assertEqual(body["model"], "gpt-6.2-sol")
        self.assertEqual(body["max_output_tokens"], 2000)
        self.assertFalse(body["store"])
        self.assertIn("2:     return a - b", body["input"])
        self.assertIn("a - b は誤り", out)
        self.assertIn("未検証", out)
        self.assertIn("in=11 out=7", err)

    def test_model_switch_cli_env_config(self):
        (self.root / ".gpt-bridge.json").write_text(json.dumps({"model": "from-config"}))
        _, out, _ = self.run_main(["ask", "q"])
        self.assertEqual(json.loads(out)["model"], "from-config")
        os.environ["GPT_BRIDGE_MODEL"] = "from-env"
        _, out, _ = self.run_main(["ask", "q"])
        self.assertEqual(json.loads(out)["model"], "from-env")
        _, out, _ = self.run_main(["ask", "q", "--model", "from-cli"])
        self.assertEqual(json.loads(out)["model"], "from-cli")

    def test_reasoning_effort_and_store(self):
        rec = Recorder(fake_response())
        self.run_main(["design", "q", "--reasoning-effort", "high", "--store", "--send"], opener=rec)
        body = json.loads(rec.requests[0].data)
        self.assertEqual(body["reasoning"], {"effort": "high"})
        self.assertTrue(body["store"])

    def test_mode_prompts_differ(self):
        payloads = {}
        for mode in ("ask", "review", "design"):
            rec = Recorder(fake_response())
            self.run_main([mode, "q", "--send"], opener=rec)
            payloads[mode] = json.loads(rec.requests[0].data)["instructions"]
        self.assertEqual(len(set(payloads.values())), 3)
        self.assertIn("Japanese", payloads["ask"])

    def test_prompt_from_stdin(self):
        rec = Recorder(fake_response())
        self.run_main(["ask", "-", "--send"], opener=rec, stdin="標準入力の質問")
        self.assertIn("標準入力の質問", json.loads(rec.requests[0].data)["input"])


class TestLimits(Base):
    def test_input_limit(self):
        (self.root / "big.py").write_text("x = 1\n" * 3000)
        code, _, err = self.run_main(["ask", "q", "-f", "big.py", "--max-input-chars", "1000"])
        self.assertEqual(code, 2)
        self.assertIn("max_input_chars", err)

    def test_file_truncation(self):
        (self.root / ".gpt-bridge.json").write_text(json.dumps({"max_file_chars": 100}))
        (self.root / "big.py").write_text("x = 1\n" * 500)
        _, out, _ = self.run_main(["ask", "q", "-f", "big.py"])
        self.assertTrue(any("切り詰め" in n for n in json.loads(out)["notes"]))

    def test_output_token_cap(self):
        code, _, err = self.run_main(["ask", "q", "--max-output-tokens", "999999"])
        self.assertEqual(code, 2)
        self.assertIn("max_output_tokens_cap", err)

    def test_daily_call_limit(self):
        os.environ["GPT_BRIDGE_MAX_CALLS_PER_DAY"] = "2"
        rec = Recorder(fake_response(), fake_response(), fake_response())
        self.assertEqual(self.run_main(["ask", "q", "--send"], opener=rec)[0], 0)
        self.assertEqual(self.run_main(["ask", "q", "--send"], opener=rec)[0], 0)
        code, _, err = self.run_main(["ask", "q", "--send"], opener=rec)
        self.assertEqual(code, 2)
        self.assertIn("max_calls_per_day", err)
        self.assertEqual(len(rec.requests), 2)
        _, out, _ = self.run_main(["usage"])
        u = json.loads(out)
        self.assertEqual((u["calls"], u["input_tokens"], u["output_tokens"]), (2, 22, 14))

    def test_line_range(self):
        _, out, _ = self.run_main(["ask", "q", "-f", "app.py:2-2", "--show-payload"])
        payload = json.loads(out[out.index("}\n{") + 2:])
        self.assertIn("2:     return a - b", payload["input"])
        self.assertNotIn("def add", payload["input"])

    def test_https_only(self):
        (self.root / ".gpt-bridge.json").write_text(json.dumps({"api_base": "http://evil"}))
        self.assertEqual(self.run_main(["ask", "q"])[0], 2)

    def test_unknown_config_key(self):
        (self.root / ".gpt-bridge.json").write_text(json.dumps({"api_key": "x"}))
        code, _, err = self.run_main(["ask", "q"])
        self.assertEqual(code, 2)
        self.assertIn("未知のキー", err)


class TestSafety(Base):
    def test_denied_files(self):
        for name in (".env", "id_rsa", "prod.pem", "aws_credentials.txt", "client_secret.json"):
            (self.root / name).write_text("x")
            code, _, err = self.run_main(["ask", "q", "-f", name])
            self.assertEqual(code, 2, name)
            self.assertIn("拒否", err)

    def test_outside_repo_rejected(self):
        outside = Path(self.tmp.name) / "outside.py"
        outside.write_text("x")
        self.assertEqual(self.run_main(["ask", "q", "-f", str(outside)])[0], 2)
        self.assertEqual(self.run_main(["ask", "q", "-f", str(outside), "--allow-outside"])[0], 0)

    def test_binary_rejected(self):
        (self.root / "b.bin").write_bytes(b"\x00\x01\x02")
        self.assertEqual(self.run_main(["ask", "q", "-f", "b.bin"])[0], 2)

    def test_redaction(self):
        secret_samples = [
            "OPENAI_API_KEY = 'sk-proj-ABCDEFGHIJKLMNOPQRSTUV123456'",
            "token: ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123",
            "Authorization: Bearer abcdefghijklmnopqrstuvwxyz",
            "aws = AKIAABCDEFGHIJKLMNOP",
            "contact: taro.yamada@example.co.jp",
            "-----BEGIN RSA PRIVATE KEY-----\nMIIEow\n-----END RSA PRIVATE KEY-----",
            "password=hunter2hunter2",
        ]
        (self.root / "conf.py").write_text("\n".join(secret_samples))
        rec = Recorder(fake_response())
        self.run_main(["ask", "連絡先 someone@example.com", "-f", "conf.py", "--send"], opener=rec)
        sent = rec.requests[0].data.decode()
        for leak in ("sk-proj-ABC", "ghp_ABC", "abcdefghijklmnopqrstuvwxyz", "AKIAABCD",
                     "taro.yamada", "someone@example.com", "MIIEow", "hunter2"):
            self.assertNotIn(leak, sent)
        self.assertIn("[REDACTED", sent)

    def test_redaction_ignores_code_expressions(self):
        for line in ('TOKEN = re.compile(r"[0-9]+")', "password = get_password()",
                     "api_key = os.environ.get('X')", "token = None"):
            self.assertEqual(gb.redact(line), (line, 0), line)
        self.assertEqual(gb.redact('db_password: "s3cr3tvalue"')[0], "db_password: [REDACTED]")

    def test_diff_excludes_denied(self):
        subprocess.run(["git", "add", "app.py"], cwd=self.root, check=True)
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "a"],
                       cwd=self.root, check=True)
        (self.root / "app.py").write_text("def add(a, b):\n    return a + b\n")
        (self.root / ".env").write_text("X=1")
        subprocess.run(["git", "add", "-f", ".env"], cwd=self.root, check=True)
        rec = Recorder(fake_response())
        code, _, err = self.run_main(["review", "差分", "--diff", "--send"], opener=rec)
        self.assertEqual(code, 0, err)
        sent = json.loads(rec.requests[0].data)["input"]
        self.assertIn("+    return a + b", sent)
        self.assertNotIn("X=1", sent)
        self.assertIn(".env", err)

    def test_api_error_redacts_key_fragment(self):
        rec = Recorder(http_error(401, {"error": {
            "code": "invalid_api_key", "type": "invalid_request_error",
            "message": "Incorrect API key provided: sk-proj-****************wxyz."}}))
        code, _, err = self.run_main(["ask", "q", "--send"], opener=rec)
        self.assertEqual(code, 3)
        self.assertIn("HTTP 401", err)
        self.assertIn("invalid_api_key", err)
        self.assertNotIn("wxyz", err)

    def test_never_reads_openai_api_key_env(self):
        os.environ["OPENAI_API_KEY"] = "sk-shouldneverbeusedanywhere123"
        rec = Recorder(fake_response())
        self.run_main(["ask", "q", "--send"], opener=rec)
        req = rec.requests[0]
        self.assertNotIn("sk-shouldnever", json.dumps(dict(req.header_items())) + req.data.decode())

    def test_saved_state_is_outside_repo(self):
        rec = Recorder(fake_response())
        self.run_main(["ask", "q", "--send"], opener=rec)
        status = subprocess.run(["git", "status", "--porcelain"], cwd=self.root,
                                capture_output=True, text=True).stdout
        self.assertNotIn("gpt-bridge", status)
        self.assertTrue(list((self.state / "responses").glob("*.json")))


class TestResponses(Base):
    def test_retry_then_success(self):
        rec = Recorder(http_error(429, {"error": {"code": "rate_limit"}}), fake_response("retry ok"))
        code, out, _ = self.run_main(["ask", "q", "--send"], opener=rec)
        self.assertEqual(code, 0)
        self.assertIn("retry ok", out)
        self.assertEqual(len(rec.requests), 2)

    def test_no_retry_on_400(self):
        rec = Recorder(http_error(400, {"error": {"code": "model_not_found"}}), fake_response())
        code, _, err = self.run_main(["ask", "q", "--send"], opener=rec)
        self.assertEqual(code, 3)
        self.assertIn("model_not_found", err)
        self.assertEqual(len(rec.requests), 1)

    def test_incomplete_reported(self):
        rec = Recorder(fake_response("途中", status="incomplete", reason="max_output_tokens"))
        code, _, err = self.run_main(["ask", "q", "--send"], opener=rec)
        self.assertEqual(code, 0)
        self.assertIn("incomplete=max_output_tokens", err)

    def test_json_output_and_last(self):
        rec = Recorder(fake_response("hello"))
        _, out, _ = self.run_main(["ask", "q", "--send", "--json"], opener=rec)
        self.assertEqual(json.loads(out)["text"], "hello")
        _, out, _ = self.run_main(["last", "--json"])
        self.assertEqual(json.loads(out)["text"], "hello")

    def test_get_by_id(self):
        rec = Recorder(fake_response("stored"))
        code, out, _ = self.run_main(["get", "resp_abc123"], opener=rec)
        self.assertEqual(code, 0)
        self.assertEqual(rec.requests[0].get_method(), "GET")
        self.assertTrue(rec.requests[0].full_url.endswith("/responses/resp_abc123"))
        self.assertIn("stored", out)
        self.assertEqual(self.run_main(["get", "../etc"], opener=rec)[0], 2)

    def test_refusal_extracted(self):
        r = fake_response()
        r["output"][1]["content"] = [{"type": "refusal", "refusal": "できません"}]
        self.assertEqual(gb.extract_text(r), "[REFUSAL] できません")


if __name__ == "__main__":
    unittest.main()
