#!/usr/bin/env python3
"""gpt-bridge: Claude Code から OpenAI Responses API (/v1/responses) に相談するための CLI。

設計方針
- 標準ライブラリのみ。どのリポジトリにもコピーだけで導入できる。
- Authorization ヘッダーはコードで一切設定しない。claude.ai/code のクラウド環境の
  Network Secret をプロキシが自動付与する前提。OPENAI_API_KEY 等の環境変数も読まない。
- 既定は dry-run（送信しない）。実際に有料のモデル生成を行うのは --send を付けたときだけ。
- 送信するのは明示的に選んだファイル / git diff / 標準入力だけ。秘密情報っぽいファイルは除外し、
  本文中のトークン・メールアドレス等は伏せ字にしてから送る。
- 呼び出し回数・入力サイズ・出力トークン数に上限を設ける。
- 回答は「助言」として出力する。採否は Claude 側が検証して決める。
"""
from __future__ import annotations

import argparse
import datetime as _dt
import fnmatch
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

VERSION = "1.0.0"

DEFAULTS = {
    "model": "gpt-6.2-sol",
    "api_base": "https://api.openai.com/v1",
    "language": "ja",
    "max_output_tokens": 2000,
    "max_output_tokens_cap": 8000,
    "max_input_chars": 60000,
    "max_file_chars": 20000,
    "max_files": 20,
    "max_calls_per_day": 20,
    "timeout_sec": 120,
    "retries": 1,
    "store": False,
    "reasoning_effort": None,
}

# 送信を拒否するファイル名パターン（basename と相対パスの両方で照合）
DENY_PATTERNS = [
    ".env", ".env.*", "*.env", ".envrc", "*.pem", "*.key", "*.p12", "*.pfx", "*.jks",
    "*.keystore", "id_rsa*", "id_dsa*", "id_ecdsa*", "id_ed25519*", "*credential*",
    "*secret*", ".npmrc", ".pypirc", ".netrc", ".git-credentials", "*.kdbx",
    "settings.local.json", ".git/*", "*/.git/*",
]

# 本文中で伏せ字にするパターン
REDACTIONS = [
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S),
     "[REDACTED_PRIVATE_KEY]"),
    (re.compile(r"\bsk-[A-Za-z0-9_\-]{16,}"), "[REDACTED_API_KEY]"),
    (re.compile(r"\b(?:ghp|gho|ghs|ghu|ghr)_[A-Za-z0-9]{20,}"), "[REDACTED_GITHUB_TOKEN]"),
    (re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}"), "[REDACTED_GITHUB_TOKEN]"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "[REDACTED_AWS_KEY]"),
    (re.compile(r"\bxox[abprs]-[A-Za-z0-9\-]{10,}"), "[REDACTED_SLACK_TOKEN]"),
    (re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b"), "[REDACTED_GOOGLE_KEY]"),
    (re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}"), "[REDACTED_JWT]"),
    (re.compile(r"(?i)\b(bearer|basic)\s+[A-Za-z0-9._~+/=\-]{12,}"), r"\1 [REDACTED]"),
    # KEY = "literal" / KEY: literal（値がクォート文字列、または行末等で終わるトークン状の値のみ。
    # `TOKEN = re.compile(...)` のようなコード式は対象外）
    (re.compile(r"(?i)\b([A-Za-z0-9_]*(?:api[_-]?key|secret|token|passw(?:or)?d)[A-Za-z0-9_]*)"
                r"(\s*[:=]\s*)(?:([\"'])[^\"'\s]{6,}\3|[A-Za-z0-9_\-./+=]{8,}(?=\s|$|[,;]))"),
     r"\1\2[REDACTED]"),
    (re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"), "[REDACTED_EMAIL]"),
]

SYSTEM_PROMPTS = {
    "ask": (
        "You are a senior engineer consulted by another AI coding agent (Claude Code). "
        "Answer the question precisely. State assumptions. If you are not sure, say so explicitly "
        "instead of guessing. Do not invent APIs, files or facts that are not in the provided context."
    ),
    "review": (
        "You are reviewing code for another AI coding agent (Claude Code), who will verify every claim. "
        "Report only concrete problems: correctness bugs, security issues, data loss, race conditions, "
        "broken edge cases, then maintainability issues. For each finding give: file:line (as shown in the "
        "context), severity (high/medium/low), confidence (high/medium/low), what goes wrong with a concrete "
        "input or scenario, and a suggested fix. Do not report style nitpicks. If you find nothing serious, "
        "say so. Never claim something about code you were not shown."
    ),
    "design": (
        "You are evaluating a software design for another AI coding agent (Claude Code). "
        "Give: (1) a one-paragraph verdict, (2) strengths, (3) risks and failure modes ordered by impact, "
        "(4) realistic alternatives with trade-offs, (5) a concrete recommendation. Be specific to the "
        "provided context and say what information is missing."
    ),
    "jobdoc": (
        "You are an independent reviewer of job-hunting documents (entry sheets, interview answers, company "
        "research, fit analyses) prepared by another AI agent (Claude Code) for a student. Judge them as a "
        "skeptical interviewer and fact-checker would. Check: (1) every claim about the candidate is supported by "
        "the provided candidate facts, with no exaggeration of roles, results or qualifications; (2) every claim "
        "about an organization is supported by the provided evidence entries (source URL, date, locator) and its "
        "time point is clear; (3) the answer actually responds to the question and survives follow-up questions; "
        "(4) internal consistency across documents; (5) the reader can understand it without missing context. "
        "Cite fact IDs and evidence IDs. Never invent facts, sources or achievements. Never suggest submitting "
        "applications, sending messages or publishing anything."
    ),
}

LANG_HINT = {"ja": "Respond in Japanese.", "en": "Respond in English."}


class BridgeError(Exception):
    def __init__(self, msg: str, code: int = 2):
        super().__init__(msg)
        self.exit_code = code


# ---------------------------------------------------------------- config

def repo_root(start: Path | None = None) -> Path:
    start = start or Path.cwd()
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=start,
                             capture_output=True, text=True, check=True).stdout.strip()
        return Path(out)
    except Exception:
        return start.resolve()


def _env_cfg() -> dict:
    m = {
        "GPT_BRIDGE_MODEL": ("model", str),
        "GPT_BRIDGE_MAX_OUTPUT_TOKENS": ("max_output_tokens", int),
        "GPT_BRIDGE_MAX_INPUT_CHARS": ("max_input_chars", int),
        "GPT_BRIDGE_MAX_CALLS_PER_DAY": ("max_calls_per_day", int),
        "GPT_BRIDGE_LANGUAGE": ("language", str),
    }
    cfg = {}
    for env, (key, typ) in m.items():
        if os.environ.get(env):
            cfg[key] = typ(os.environ[env])
    return cfg


def load_config(root: Path, explicit: str | None = None) -> dict:
    """優先順位: 既定値 < リポジトリの .gpt-bridge.json < 環境変数 < CLI 引数（呼び出し側で適用）"""
    cfg = dict(DEFAULTS)
    path = Path(explicit) if explicit else root / ".gpt-bridge.json"
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise BridgeError(f"設定ファイルの JSON が不正です: {path}: {e}")
        unknown = set(data) - set(DEFAULTS)
        if unknown:
            raise BridgeError(f"設定ファイルに未知のキーがあります: {sorted(unknown)}")
        cfg.update(data)
    cfg.update(_env_cfg())
    return cfg


def validate_config(cfg: dict) -> None:
    if not str(cfg["api_base"]).startswith("https://"):
        raise BridgeError("api_base は https:// で始まる必要があります")
    for k in ("max_output_tokens", "max_input_chars", "max_file_chars", "max_files",
              "max_calls_per_day", "timeout_sec"):
        if not isinstance(cfg[k], int) or cfg[k] <= 0:
            raise BridgeError(f"{k} は正の整数である必要があります")
    if cfg["max_output_tokens"] > cfg["max_output_tokens_cap"]:
        raise BridgeError(
            f"max_output_tokens={cfg['max_output_tokens']} が上限 max_output_tokens_cap="
            f"{cfg['max_output_tokens_cap']} を超えています")
    if cfg["reasoning_effort"] not in (None, "minimal", "low", "medium", "high"):
        raise BridgeError("reasoning_effort は minimal/low/medium/high のいずれかです")


# ---------------------------------------------------------------- safety

def redact(text: str) -> tuple[str, int]:
    total = 0
    for pat, repl in REDACTIONS:
        text, n = pat.subn(repl, text)
        total += n
    return text, total


def is_denied(rel_path: str) -> bool:
    rel = rel_path.replace(os.sep, "/")
    base = rel.rsplit("/", 1)[-1].lower()
    for pat in DENY_PATTERNS:
        if fnmatch.fnmatch(base, pat.lower()) or fnmatch.fnmatch(rel.lower(), pat.lower()):
            return True
    return False


def _looks_binary(data: bytes) -> bool:
    return b"\x00" in data[:8192]


# ---------------------------------------------------------------- context building

class Context:
    def __init__(self, cfg: dict, root: Path):
        self.cfg, self.root = cfg, root
        self.parts: list[tuple[str, str]] = []   # (label, text)
        self.notes: list[str] = []
        self.redactions = 0

    def _add(self, label: str, text: str) -> None:
        text, n = redact(text)
        self.redactions += n
        limit = self.cfg["max_file_chars"]
        if len(text) > limit:
            self.notes.append(f"{label}: {len(text)} 文字 → 先頭 {limit} 文字に切り詰め")
            text = text[:limit] + f"\n... [TRUNCATED at {limit} chars]"
        self.parts.append((label, text))

    def add_file(self, path_str: str, line_range: str | None = None, allow_outside: bool = False) -> None:
        p = Path(path_str)
        p = (p if p.is_absolute() else Path.cwd() / p).resolve()
        try:
            rel = p.relative_to(self.root.resolve()).as_posix()
        except ValueError:
            if not allow_outside:
                raise BridgeError(f"リポジトリ外のファイルは既定で送信しません: {path_str}（--allow-outside で許可）")
            rel = p.name
        if is_denied(rel):
            raise BridgeError(f"秘密情報の可能性があるため送信を拒否しました: {rel}")
        if not p.is_file():
            raise BridgeError(f"ファイルが見つかりません: {path_str}")
        if len([x for x in self.parts if x[0].startswith("file:")]) >= self.cfg["max_files"]:
            raise BridgeError(f"ファイル数が上限 max_files={self.cfg['max_files']} を超えます")
        data = p.read_bytes()
        if _looks_binary(data):
            raise BridgeError(f"バイナリファイルは送信しません: {rel}")
        lines = data.decode("utf-8", errors="replace").splitlines()
        start = 1
        if line_range:
            m = re.fullmatch(r"(\d+)-(\d+)", line_range)
            if not m:
                raise BridgeError(f"行範囲は START-END 形式で指定してください: {line_range}")
            start, end = int(m.group(1)), int(m.group(2))
            if start < 1 or end < start:
                raise BridgeError(f"行範囲が不正です: {line_range}")
            lines = lines[start - 1:end]
        numbered = "\n".join(f"{i:>5}: {ln}" for i, ln in enumerate(lines, start))
        label = f"file:{rel}" + (f" (lines {line_range})" if line_range else "")
        self._add(label, numbered)

    def add_diff(self, base: str | None, staged: bool) -> None:
        if base:
            names_cmd = ["git", "diff", "--name-only", f"{base}...HEAD"]
            diff_cmd = ["git", "diff", "--no-color", f"{base}...HEAD", "--"]
        else:
            names_cmd = ["git", "diff", "--name-only"] + (["--cached"] if staged else ["HEAD"])
            diff_cmd = ["git", "diff", "--no-color"] + (["--cached"] if staged else ["HEAD"]) + ["--"]
        try:
            names = subprocess.run(names_cmd, cwd=self.root, capture_output=True, text=True,
                                   check=True).stdout.split()
        except subprocess.CalledProcessError as e:
            raise BridgeError(f"git diff に失敗しました: {e.stderr.strip()}")
        allowed = [n for n in names if not is_denied(n)]
        skipped = sorted(set(names) - set(allowed))
        if skipped:
            self.notes.append(f"diff から除外（秘密情報の可能性）: {', '.join(skipped)}")
        if not allowed:
            raise BridgeError("送信できる差分がありません")
        out = subprocess.run(diff_cmd + allowed, cwd=self.root, capture_output=True, text=True,
                             check=True).stdout
        self._add(f"git diff {base + '...HEAD' if base else ('--cached' if staged else 'HEAD')}", out)

    def add_text(self, label: str, text: str) -> None:
        self._add(label, text)

    def render(self) -> str:
        return "\n\n".join(f"<<<{label}>>>\n{text}\n<<<end {label}>>>" for label, text in self.parts)


def build_payload(cfg: dict, mode: str, prompt: str, ctx: Context, text_format: dict | None = None,
                  extra_instructions: str = "") -> dict:
    """text_format: Responses API の text.format（例: {"type": "json_schema", ...}）。指定時のみ付与。"""
    instructions = SYSTEM_PROMPTS[mode] + " " + extra_instructions + " " + LANG_HINT.get(cfg["language"], "")
    prompt, n = redact(prompt)
    ctx.redactions += n
    body = f"## Request\n{prompt.strip()}"
    if ctx.parts:
        body += "\n\n## Context (selected by Claude Code; not the whole repository)\n" + ctx.render()
    total = len(instructions) + len(body)
    if total > cfg["max_input_chars"]:
        raise BridgeError(
            f"入力が上限を超えています: {total} 文字 > max_input_chars={cfg['max_input_chars']}。"
            "ファイルや行範囲を絞ってください。")
    payload = {
        "model": cfg["model"],
        "instructions": instructions.strip(),
        "input": body,
        "max_output_tokens": cfg["max_output_tokens"],
        "store": bool(cfg["store"]),
    }
    if cfg.get("reasoning_effort"):
        payload["reasoning"] = {"effort": cfg["reasoning_effort"]}
    if text_format:
        payload["text"] = {"format": text_format}
    return payload


# ---------------------------------------------------------------- usage / cache (リポジトリ外に保存)

def state_dir() -> Path:
    base = Path(os.environ.get("GPT_BRIDGE_STATE_DIR")
                or Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "gpt-bridge")
    base.mkdir(parents=True, exist_ok=True)
    return base


def _today() -> str:
    return _dt.date.today().isoformat()


def read_usage() -> dict:
    f = state_dir() / "usage.json"
    try:
        data = json.loads(f.read_text())
    except Exception:
        data = {}
    return data if data.get("date") == _today() else {"date": _today(), "calls": 0,
                                                       "input_tokens": 0, "output_tokens": 0}


def write_usage(u: dict) -> None:
    (state_dir() / "usage.json").write_text(json.dumps(u))


def check_quota(cfg: dict) -> dict:
    u = read_usage()
    if u["calls"] >= cfg["max_calls_per_day"]:
        raise BridgeError(f"本日の呼び出し上限 max_calls_per_day={cfg['max_calls_per_day']} に達しました")
    return u


def save_result(result: dict) -> Path:
    d = state_dir() / "responses"
    d.mkdir(exist_ok=True)
    f = d / (time.strftime("%Y%m%d-%H%M%S") + ".json")
    f.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return f


# ---------------------------------------------------------------- HTTP

def _headers() -> dict:
    h = {"Content-Type": "application/json", "Accept": "application/json",
         "User-Agent": f"gpt-bridge/{VERSION}"}
    # 認証はプロキシ（Network Secret）が付与する。ここで Authorization を設定してはならない。
    assert not any(k.lower() == "authorization" for k in h)
    return h


def _api_error(e: urllib.error.HTTPError) -> BridgeError:
    try:
        err = json.loads(e.read().decode("utf-8", errors="replace")).get("error") or {}
    except Exception:
        err = {}
    # エラーメッセージにはマスク済みキーの一部が含まれ得るので、伏せ字化した上で短く出す
    msg, _ = redact(str(err.get("message", "")))
    msg = re.sub(r"\S*\*{3,}\S*", "[REDACTED]", msg)[:300]
    return BridgeError(f"OpenAI API エラー: HTTP {e.code} code={err.get('code')} "
                       f"type={err.get('type')} {msg}".rstrip(), 3)


def http_json(method: str, url: str, payload: dict | None, cfg: dict, opener=None) -> dict:
    opener = opener or urllib.request.urlopen
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    attempts = 1 + max(0, int(cfg["retries"]))
    for i in range(attempts):
        req = urllib.request.Request(url, data=data, method=method, headers=_headers())
        try:
            with opener(req, timeout=cfg["timeout_sec"]) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and i + 1 < attempts:
                time.sleep(2 ** i * 2)
                continue
            raise _api_error(e)
        except urllib.error.URLError as e:
            if i + 1 < attempts:
                time.sleep(2 ** i * 2)
                continue
            raise BridgeError(f"通信エラー: {e.reason}", 3)
    raise BridgeError("通信に失敗しました", 3)


def extract_text(resp: dict) -> str:
    chunks = []
    for item in resp.get("output", []) or []:
        if item.get("type") == "message":
            for c in item.get("content", []) or []:
                if c.get("type") == "output_text":
                    chunks.append(c.get("text", ""))
                elif c.get("type") == "refusal":
                    chunks.append("[REFUSAL] " + c.get("refusal", ""))
    if not chunks and isinstance(resp.get("output_text"), str):
        chunks.append(resp["output_text"])
    return "\n".join(chunks).strip()


def summarize(resp: dict) -> dict:
    usage = resp.get("usage") or {}
    return {
        "id": resp.get("id"),
        "model": resp.get("model"),
        "status": resp.get("status"),
        "incomplete_reason": (resp.get("incomplete_details") or {}).get("reason"),
        "input_tokens": usage.get("input_tokens"),
        "output_tokens": usage.get("output_tokens"),
        "text": extract_text(resp),
    }


def send(cfg: dict, payload: dict, opener=None) -> dict:
    usage = check_quota(cfg)
    usage["calls"] += 1          # 失敗しても 1 回と数える（課金される可能性があるため保守的に）
    write_usage(usage)
    resp = http_json("POST", cfg["api_base"].rstrip("/") + "/responses", payload, cfg, opener)
    if resp.get("error"):
        raise BridgeError(f"OpenAI API エラー: {resp['error'].get('code')}", 3)
    result = summarize(resp)
    usage["input_tokens"] += result["input_tokens"] or 0
    usage["output_tokens"] += result["output_tokens"] or 0
    write_usage(usage)
    return result


# ---------------------------------------------------------------- CLI

BANNER = ("=== GPT からの助言（未検証）: 採用前に Claude がコード・テスト・ドキュメントで"
          "裏付けを取ること ===")


def emit(result: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print(BANNER)
    print(result["text"] or "(本文なし)")
    meta = (f"[gpt-bridge] model={result.get('model')} status={result.get('status')} "
            f"in={result.get('input_tokens')} out={result.get('output_tokens')} id={result.get('id')}")
    if result.get("incomplete_reason"):
        meta += f" incomplete={result['incomplete_reason']}（max_output_tokens を増やすか質問を絞る）"
    print(meta, file=sys.stderr)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="gpt_bridge", description="Claude Code → OpenAI Responses API bridge")
    p.add_argument("--version", action="version", version=VERSION)
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp):
        sp.add_argument("prompt", help="質問・依頼内容（'-' で標準入力から読む）")
        sp.add_argument("-f", "--file", action="append", default=[],
                        help="送るファイル。PATH または PATH:START-END（複数可）")
        sp.add_argument("--diff", action="store_true", help="作業ツリーの git diff (HEAD) を含める")
        sp.add_argument("--staged", action="store_true", help="--diff をステージ済み差分に限定")
        sp.add_argument("--diff-base", metavar="REF", help="REF...HEAD の差分を含める")
        sp.add_argument("--context-stdin", action="store_true", help="標準入力を追加コンテキストとして読む")
        sp.add_argument("--allow-outside", action="store_true", help="リポジトリ外のファイルも許可")
        sp.add_argument("--model")
        sp.add_argument("--max-output-tokens", type=int)
        sp.add_argument("--max-input-chars", type=int)
        sp.add_argument("--reasoning-effort", choices=["minimal", "low", "medium", "high"])
        sp.add_argument("--lang", choices=["ja", "en"])
        sp.add_argument("--store", action="store_true", help="OpenAI 側に応答を保存（後で get 可能）")
        sp.add_argument("--config", help="設定ファイルのパス（既定: <repo>/.gpt-bridge.json）")
        sp.add_argument("--send", action="store_true",
                        help="実際に API を呼ぶ（有料）。省略時は dry-run で送信内容の要約のみ表示")
        sp.add_argument("--show-payload", action="store_true", help="dry-run 時に送信予定の全文を表示")
        sp.add_argument("--json", action="store_true", help="結果を JSON で出力")

    for name, help_ in (("ask", "GPT へ質問"), ("review", "コードレビュー"), ("design", "設計評価"),
                        ("jobdoc", "就活資料（ES・面接回答・企業研究）のレビュー")):
        common(sub.add_parser(name, help=help_))

    g = sub.add_parser("get", help="保存済み応答を ID で取得（--store で作成したもの。生成は行わない）")
    g.add_argument("response_id")
    g.add_argument("--json", action="store_true")
    g.add_argument("--config")

    lst = sub.add_parser("last", help="このコンテナで最後に受け取った回答を表示（API 呼び出しなし）")
    lst.add_argument("--json", action="store_true")

    sub.add_parser("usage", help="本日の呼び出し回数とトークン使用量（API 呼び出しなし）")
    c = sub.add_parser("config", help="有効な設定を表示")
    c.add_argument("--config")
    return p


def apply_cli(cfg: dict, a: argparse.Namespace) -> dict:
    for attr, key in (("model", "model"), ("max_output_tokens", "max_output_tokens"),
                      ("max_input_chars", "max_input_chars"), ("reasoning_effort", "reasoning_effort"),
                      ("lang", "language")):
        v = getattr(a, attr, None)
        if v is not None:
            cfg[key] = v
    if getattr(a, "store", False):
        cfg["store"] = True
    validate_config(cfg)
    return cfg


def main(argv: list[str] | None = None, opener=None, stdin=None) -> int:
    stdin = stdin or sys.stdin
    a = build_parser().parse_args(argv)
    root = repo_root()
    try:
        if a.cmd == "usage":
            u = read_usage()
            print(json.dumps(u, ensure_ascii=False))
            return 0
        if a.cmd == "last":
            files = sorted((state_dir() / "responses").glob("*.json")) if (state_dir() / "responses").exists() else []
            if not files:
                raise BridgeError("保存された回答がありません")
            emit(json.loads(files[-1].read_text(encoding="utf-8")), a.json)
            return 0

        cfg = apply_cli(load_config(root, getattr(a, "config", None)), a)
        if a.cmd == "config":
            print(json.dumps(cfg, ensure_ascii=False, indent=2))
            return 0
        if a.cmd == "get":
            if not re.fullmatch(r"resp_[A-Za-z0-9]+", a.response_id):
                raise BridgeError("response_id の形式が不正です（resp_...）")
            resp = http_json("GET", f"{cfg['api_base'].rstrip('/')}/responses/{a.response_id}", None, cfg, opener)
            emit(summarize(resp), a.json)
            return 0

        prompt = stdin.read() if a.prompt == "-" else a.prompt
        if not prompt.strip():
            raise BridgeError("質問内容が空です")
        ctx = Context(cfg, root)
        for spec in a.file:
            m = re.fullmatch(r"(.+?):(\d+-\d+)", spec)
            ctx.add_file(m.group(1) if m else spec, m.group(2) if m else None, a.allow_outside)
        if a.diff or a.staged or a.diff_base:
            ctx.add_diff(a.diff_base, a.staged)
        if a.context_stdin:
            if a.prompt == "-":
                raise BridgeError("prompt に '-' を使う場合は --context-stdin と併用できません")
            ctx.add_text("stdin", stdin.read())
        payload = build_payload(cfg, a.cmd, prompt, ctx)

        if not a.send:
            info = {
                "dry_run": True,
                "mode": a.cmd,
                "model": payload["model"],
                "max_output_tokens": payload["max_output_tokens"],
                "input_chars": len(payload["instructions"]) + len(payload["input"]),
                "max_input_chars": cfg["max_input_chars"],
                "context": [label for label, _ in ctx.parts],
                "redactions": ctx.redactions,
                "notes": ctx.notes,
                "calls_today": read_usage()["calls"],
                "max_calls_per_day": cfg["max_calls_per_day"],
                "hint": "実際に送信するには --send を付ける（有料。ユーザーの許可を得てから）",
            }
            print(json.dumps(info, ensure_ascii=False, indent=2))
            if a.show_payload:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0

        for n in ctx.notes:
            print(f"[gpt-bridge] {n}", file=sys.stderr)
        if ctx.redactions:
            print(f"[gpt-bridge] 伏せ字化: {ctx.redactions} 箇所", file=sys.stderr)
        result = send(cfg, payload, opener)
        result["mode"] = a.cmd
        save_result(result)
        emit(result, a.json)
        return 0
    except BridgeError as e:
        print(f"[gpt-bridge] {e}", file=sys.stderr)
        return e.exit_code


if __name__ == "__main__":
    sys.exit(main())
