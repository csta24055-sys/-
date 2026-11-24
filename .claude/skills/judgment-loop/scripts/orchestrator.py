#!/usr/bin/env python3
"""judgment-loop: Claude Code（作業）と GPT（独立レビュー）を反復させるオーケストレーター。

役割分担
- Claude Code: 調査・資料作成・検証・修正を実行し、成果物と記録を submit する。GPT の指示は
  根拠を確認してから採否（decide）を決める。
- GPT: 判断基準の抜粋・承認済み本人情報・根拠台帳と照合して独立レビューし、
  PASS / REVISE / BLOCKED と具体的な次の作業を構造化 JSON で返す。
- このスクリプト: 状態遷移・承認範囲（回数・予算・期限・送信データ）・履歴・停止条件を機械的に強制する。

データの置き場所
- コード（このファイル）は公開リポジトリにあってよい。個人データは一切持たない。
- 判断基準・本人情報・応募先・成果物・履歴は「非公開ホーム」（既定 ~/.judgment-loop、
  環境変数 JUDGMENT_LOOP_HOME）に置く。Git の作業ツリー内には作らせない。
- クラウドのコンテナは使い捨てなので、export したスナップショットを Dropbox 等の非公開保管先へ退避し、
  次のセッションで import して再開する。
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from zoneinfo import ZoneInfo

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
MODES_DIR = SKILL_DIR / "modes"
BRIDGE_DIR = SKILL_DIR.parent / "gpt-consult" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(BRIDGE_DIR))
import review as rv  # noqa: E402

try:
    import gpt_bridge as gb  # noqa: E402
except ImportError:  # pragma: no cover
    sys.exit("gpt-consult スキル（.claude/skills/gpt-consult）が見つかりません。先に導入してください。")

VERSION = "1.0.0"
JST = ZoneInfo("Asia/Tokyo")

# 包括承認でも超えられない上限（無制限の呼び出しを構造的に防ぐ）
HARD_MAX_ITERATIONS = 20
HARD_MAX_CALLS = 50
HARD_MAX_DAYS = 14
DATA_CLASSES = ("policies", "artifacts", "baseline", "facts", "evidence")
TERMINAL = ("done", "stopped")
LOOP_STOPPED = ("paused", "blocked", "needs_user", "stalled", "limit_reached")

FORBIDDEN_ACTION = re.compile(
    r"(応募|エントリー|申込|申し込み)[^。]{0,12}(送信|提出|完了|確定)|"
    r"(ES|エントリーシート|書類)[^。]{0,8}(を)?(送信|提出)する|"
    r"メール[^。]{0,6}(送信|送る|送付)|(SNS|ブログ|X|Twitter)[^。]{0,6}(投稿|公開)|"
    r"一般公開|外部(に)?公開|\bpush\b|main\s*ブランチ|\bmain\b\s*(に|へ)|デプロイ|\bdeploy\b",
    re.I,
)


class LoopError(Exception):
    def __init__(self, msg: str, code: int = 2):
        super().__init__(msg)
        self.exit_code = code


# ------------------------------------------------------------------ 基本ユーティリティ

def now() -> dt.datetime:
    fixed = os.environ.get("JUDGMENT_LOOP_NOW")
    return parse_time(fixed) if fixed else dt.datetime.now(JST)


def parse_time(s: str) -> dt.datetime:
    try:
        t = dt.datetime.fromisoformat(s)
    except ValueError:
        raise LoopError(f"日時の形式が不正です（ISO 8601）: {s}")
    return t if t.tzinfo else t.replace(tzinfo=JST)


def iso(t: dt.datetime | None = None) -> str:
    return (t or now()).isoformat(timespec="seconds")


def home() -> Path:
    return Path(os.environ.get("JUDGMENT_LOOP_HOME") or Path.home() / ".judgment-loop")


def _inside_git(p: Path) -> bool:
    q = p
    while not q.exists():
        q = q.parent
    r = subprocess.run(["git", "-C", str(q), "rev-parse", "--is-inside-work-tree"],
                       capture_output=True, text=True)
    return r.returncode == 0 and r.stdout.strip() == "true"


def H() -> Path:
    h = home()
    if _inside_git(h) and not os.environ.get("JUDGMENT_LOOP_ALLOW_IN_REPO"):
        raise LoopError(f"非公開ホーム {h} が Git の作業ツリー内にあります。個人データがコミットされる恐れがあるため拒否します。"
                        " JUDGMENT_LOOP_HOME をリポジトリ外に設定してください。")
    return h


def read_json(p: Path, default=None):
    if not p.exists():
        if default is not None:
            return default
        raise LoopError(f"見つかりません: {p.name}")
    return json.loads(p.read_text(encoding="utf-8"))


def write_json(p: Path, data) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, p)  # 原子的に置換（途中で落ちても壊れた JSON を残さない）


def append_jsonl(p: Path, rec: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def read_jsonl(p: Path) -> list[dict]:
    if not p.exists():
        return []
    out = []
    for ln in p.read_text(encoding="utf-8").splitlines():
        if ln.strip():
            out.append(json.loads(ln))
    return out


def out(obj) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def safe_rel(rel: str) -> str:
    p = Path(rel)
    if p.is_absolute() or ".." in p.parts or not rel.strip():
        raise LoopError(f"相対パスで指定してください（.. 不可）: {rel}")
    return p.as_posix()


def load_mode(mode: str) -> dict:
    f = MODES_DIR / f"{mode}.json"
    if not f.is_file():
        raise LoopError(f"未知のモード: {mode}（{', '.join(p.stem for p in MODES_DIR.glob('*.json'))}）")
    return json.loads(f.read_text(encoding="utf-8"))


# ------------------------------------------------------------------ 判断基準

def cmd_policies_import(a):
    h = H()
    dest = h / "policies"
    dest.mkdir(parents=True, exist_ok=True)
    src = Path(a.source)
    imported = []
    if src.is_file() and zipfile.is_zipfile(src):
        with zipfile.ZipFile(src) as z:
            for n in z.namelist():
                parts = n.split("/")
                if ".." in parts or n.startswith("/"):
                    continue
                if len(parts) >= 2 and parts[-2] == "policies" and n.endswith(".md"):
                    (dest / parts[-1]).write_bytes(z.read(n))
                    imported.append(parts[-1])
        digest = hashlib.sha256(src.read_bytes()).hexdigest()
    elif src.is_dir():
        for f in sorted(src.glob("*.md")):
            shutil.copyfile(f, dest / f.name)
            imported.append(f.name)
        digest = None
    else:
        raise LoopError(f"ZIP またはディレクトリを指定してください: {src}")
    if not imported:
        raise LoopError("policies/*.md が見つかりませんでした")
    write_json(dest / "SOURCE.json", {"source": src.name, "sha256": digest, "imported_at": iso(),
                                       "files": sorted(imported)})
    out({"imported": sorted(imported), "to": str(dest)})


def policy_selection(mode_cfg: dict, task_type: str) -> dict:
    sel: dict[str, list[str]] = {}
    for src in (mode_cfg.get("policies_common", {}), mode_cfg["task_types"][task_type].get("policies", {})):
        for f, heads in src.items():
            sel.setdefault(f, [])
            sel[f] += [x for x in heads if x not in sel[f]]
    return sel


def cmd_policies_show(a):
    mode_cfg = load_mode(a.mode)
    if a.task_type not in mode_cfg["task_types"]:
        raise LoopError(f"作業種別が不正です: {a.task_type}（{', '.join(mode_cfg['task_types'])}）")
    text, refs, missing = rv.extract_policies(H() / "policies", policy_selection(mode_cfg, a.task_type),
                                              mode_cfg["policy_char_limit"])
    out({"refs": refs, "missing": missing, "chars": len(text)})
    if a.full:
        print(text)


# ------------------------------------------------------------------ ワークスペース・本人情報・根拠

def ws_dir(name: str) -> Path:
    d = H() / "workspaces" / name
    if not (d / "workspace.json").exists():
        raise LoopError(f"ワークスペースがありません: {name}")
    return d


def cmd_ws_create(a):
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,31}", a.name):
        raise LoopError("ワークスペース名は英小文字・数字・ハイフン（32 文字以内）")
    load_mode(a.mode)
    d = H() / "workspaces" / a.name
    if (d / "workspace.json").exists():
        raise LoopError(f"既に存在します: {a.name}")
    (d / "artifacts" / "baseline").mkdir(parents=True)
    (d / "runs").mkdir()
    write_json(d / "workspace.json", {"name": a.name, "mode": a.mode, "aliases": a.alias,
                                      "targets": a.target, "created": iso()})
    out({"created": a.name, "mode": a.mode, "artifacts_dir": str(d / "artifacts")})


def cmd_ws_list(a):
    root = H() / "workspaces"
    rows = []
    for w in sorted(root.glob("*/workspace.json")) if root.exists() else []:
        info = read_json(w)
        runs = [read_json(s) for s in w.parent.glob("runs/*/state.json")]
        active = [r["id"] for r in runs if r["status"] not in TERMINAL]
        rows.append({**info, "active_runs": active})
    out(rows)


def facts_path() -> Path:
    return H() / "profile" / "facts.jsonl"


def effective_facts() -> dict[str, dict]:
    recs = read_jsonl(facts_path())
    latest = {}
    for r in recs:
        latest[r["id"]] = r
    superseded = {r["supersedes"] for r in latest.values() if r.get("supersedes")}
    return {k: v for k, v in latest.items() if k not in superseded and not v.get("retired")}


def _next_id(prefix: str, existing) -> str:
    nums = [int(m.group(1)) for x in existing if (m := re.fullmatch(rf"{prefix}-(\d+)", x))]
    return f"{prefix}-{(max(nums) + 1) if nums else 1:03d}"


def cmd_fact_add(a):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", a.observed):
        raise LoopError("--observed は YYYY-MM-DD")
    if a.scope != "shared" and not a.scope.startswith("ws:"):
        raise LoopError("--scope は shared または ws:<ワークスペース名>")
    if a.scope.startswith("ws:"):
        ws_dir(a.scope[3:])
    all_ids = {r["id"] for r in read_jsonl(facts_path())}
    if a.supersedes and a.supersedes not in all_ids:
        raise LoopError(f"置き換え対象の事実がありません: {a.supersedes}")
    rec = {"id": _next_id("F", all_ids), "type": a.type, "statement": a.statement, "source": a.source,
           "observed": a.observed, "valid_until": a.valid_until, "status": a.status, "scope": a.scope,
           "sensitivity": a.sensitivity, "gpt_ok": bool(a.gpt_ok) and a.sensitivity != "secret",
           "supersedes": a.supersedes, "updated": iso()}
    append_jsonl(facts_path(), rec)
    out(rec)


def visible_facts(ws: str) -> dict[str, dict]:
    return {k: v for k, v in effective_facts().items() if v["scope"] in ("shared", f"ws:{ws}")}


def cmd_fact_list(a):
    facts = visible_facts(a.ws) if a.ws else effective_facts()
    out(list(facts.values()))


def cmd_redact_add(a):
    p = H() / "profile" / "redact_terms.json"
    terms = read_json(p, [])
    if a.term not in terms:
        terms.append(a.term)
    write_json(p, terms)
    out({"redact_terms": len(terms)})


def apply_redact_terms(text: str) -> tuple[str, int]:
    terms = read_json(H() / "profile" / "redact_terms.json", [])
    n = 0
    for t in sorted(terms, key=len, reverse=True):
        if t:
            n += text.count(t)
            text = text.replace(t, "[本人情報]")
    return text, n


def cmd_ref_add(a):
    d = ws_dir(a.ws)
    refs = read_jsonl(d / "refs.jsonl")
    rec = {"id": _next_id("R", [r["id"] for r in refs]), "role": a.role, "kind": a.kind, "ref": a.ref,
           "title": a.title, "source_modified": a.modified, "note": a.note, "added": iso()}
    append_jsonl(d / "refs.jsonl", rec)
    out(rec)


def cmd_evidence_add(a):
    d = ws_dir(a.ws)
    if not a.url.startswith("https://"):
        raise LoopError("出典 URL は https:// で始まる必要があります")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", a.retrieved):
        raise LoopError("--retrieved は YYYY-MM-DD")
    for k in ("claim", "title", "locator", "excerpt"):
        if not getattr(a, k).strip():
            raise LoopError(f"--{k} は必須です")
    if len(a.excerpt) > 600:
        raise LoopError("--excerpt は該当箇所の抜粋（600 文字以内）にしてください")
    ev = read_jsonl(d / "evidence.jsonl")
    rec = {"id": _next_id("E", [e["id"] for e in ev]), "claim": a.claim, "url": a.url, "title": a.title,
           "retrieved": a.retrieved, "locator": a.locator, "excerpt": a.excerpt, "tool": a.tool,
           "status": a.status, "added": iso()}
    append_jsonl(d / "evidence.jsonl", rec)
    out(rec)


def cmd_evidence_list(a):
    out(read_jsonl(ws_dir(a.ws) / "evidence.jsonl"))


# ------------------------------------------------------------------ 実行（run）

def run_dir(run_id: str) -> Path:
    for p in (H() / "workspaces").glob(f"*/runs/{run_id}/state.json"):
        return p.parent
    raise LoopError(f"実行がありません: {run_id}")


def resolve_run(a) -> tuple[Path, dict]:
    if getattr(a, "run", None):
        d = run_dir(a.run)
        return d, read_json(d / "state.json")
    pattern = f"{a.ws}/runs/*/state.json" if getattr(a, "ws", None) else "*/runs/*/state.json"
    cands = [(p.parent, read_json(p)) for p in (H() / "workspaces").glob(pattern)]
    cands = [(d, s) for d, s in cands if s["status"] not in TERMINAL]
    if not cands:
        raise LoopError("進行中の実行がありません（start で開始）")
    if len(cands) > 1:
        raise LoopError("進行中の実行が複数あります。--run または --ws で指定してください: "
                        + ", ".join(s["id"] for _, s in cands))
    return cands[0]


def save_state(d: Path, s: dict, event: str, **details) -> None:
    s["updated"] = iso()
    write_json(d / "state.json", s)
    append_jsonl(d / "history.jsonl", {"ts": s["updated"], "event": event, "status": s["status"],
                                       "iteration": s["iteration"], **details})


def it_dir(d: Path, n: int) -> Path:
    p = d / "iterations" / f"{n:03d}"
    p.mkdir(parents=True, exist_ok=True)
    return p


def cmd_start(a):
    w = ws_dir(a.ws)
    info = read_json(w / "workspace.json")
    mode_cfg = load_mode(info["mode"])
    if a.task_type not in mode_cfg["task_types"]:
        raise LoopError(f"作業種別が不正です: {a.task_type}（{', '.join(mode_cfg['task_types'])}）")
    if not 1 <= a.max_iterations <= HARD_MAX_ITERATIONS:
        raise LoopError(f"--max-iterations は 1〜{HARD_MAX_ITERATIONS}")
    active = [read_json(p) for p in w.glob("runs/*/state.json")]
    if any(s["status"] not in TERMINAL for s in active):
        raise LoopError("このワークスペースには進行中の実行があります（stop で終了するか resume してください）")
    if mode_cfg.get("baseline_required"):
        roles = {r["role"] for r in read_jsonl(w / "refs.jsonl")}
        if "baseline" not in roles:
            raise LoopError("このモードは基準資料が必要です: " + mode_cfg["baseline_hint"])
    rid = f"{a.ws}-{now().strftime('%Y%m%d-%H%M%S')}"
    d = w / "runs" / rid
    if d.exists():
        raise LoopError(f"同じ ID の実行があります: {rid}")
    s = {"id": rid, "workspace": a.ws, "mode": info["mode"], "task_type": a.task_type, "goal": a.goal,
         "created": iso(), "status": "awaiting_work", "resume_to": None, "iteration": 1,
         "max_iterations": a.max_iterations, "approval": None,
         "usage": {"calls": 0, "input_tokens": 0, "output_tokens": 0, "usd": 0.0},
         "accepted_actions": [], "pending_actions": [], "last_verdict": None, "last_fingerprint": None,
         "last_error": None}
    it_dir(d, 1)
    save_state(d, s, "start", goal=a.goal, task_type=a.task_type)
    out({"run": rid, "status": s["status"], "next": instruction(s)})


def cmd_approve(a):
    d, s = resolve_run(a)
    if s["status"] in TERMINAL:
        raise LoopError("終了した実行には承認を付けられません")
    if not a.user_quote.strip():
        raise LoopError("--user-quote にユーザーの承認発言をそのまま記録してください")
    data = [x.strip() for x in a.data.split(",") if x.strip()]
    bad = set(data) - set(DATA_CLASSES)
    if bad:
        raise LoopError(f"未知のデータ区分: {sorted(bad)}（{', '.join(DATA_CLASSES)}）")
    exp = parse_time(a.expires)
    if exp <= now():
        raise LoopError("期限が過去です")
    if exp > now() + dt.timedelta(days=HARD_MAX_DAYS):
        raise LoopError(f"承認期限は最長 {HARD_MAX_DAYS} 日です")
    if not 1 <= a.max_iterations <= HARD_MAX_ITERATIONS:
        raise LoopError(f"--max-iterations は 1〜{HARD_MAX_ITERATIONS}")
    if not 1 <= a.max_calls <= HARD_MAX_CALLS:
        raise LoopError(f"--max-calls は 1〜{HARD_MAX_CALLS}")
    if a.output_tokens_per_call > gb.DEFAULTS["max_output_tokens_cap"]:
        raise LoopError(f"--output-tokens-per-call は {gb.DEFAULTS['max_output_tokens_cap']} 以下")
    if a.max_usd is not None and (a.price_in is None or a.price_out is None):
        raise LoopError("--max-usd を使うには --price-in / --price-out（100 万トークンあたり USD）が必要です")
    s["max_iterations"] = a.max_iterations
    s["approval"] = {
        "model": a.model, "max_iterations": a.max_iterations, "max_calls": a.max_calls,
        "max_input_tokens": a.max_input_tokens, "max_output_tokens": a.max_output_tokens,
        "output_tokens_per_call": a.output_tokens_per_call, "max_usd": a.max_usd,
        "price_in_per_mtok": a.price_in, "price_out_per_mtok": a.price_out,
        "data": data, "expires": exp.isoformat(timespec="seconds"), "snapshots": a.snapshots,
        "user_quote": a.user_quote, "approved_at": iso(),
    }
    save_state(d, s, "approve", approval=s["approval"])
    out({"run": s["id"], "approval": s["approval"]})


def cmd_extend(a):
    d, s = resolve_run(a)
    if not s.get("approval"):
        raise LoopError("承認がありません（approve を先に）")
    if not a.user_quote.strip():
        raise LoopError("--user-quote にユーザーの追加承認発言を記録してください")
    ap = s["approval"]
    if a.max_iterations:
        if not s["iteration"] <= a.max_iterations <= HARD_MAX_ITERATIONS:
            raise LoopError(f"--max-iterations は現在の反復 {s['iteration']}〜{HARD_MAX_ITERATIONS}")
        ap["max_iterations"] = s["max_iterations"] = a.max_iterations
    if a.max_calls:
        if not ap["max_calls"] <= a.max_calls <= HARD_MAX_CALLS:
            raise LoopError(f"--max-calls は {ap['max_calls']}〜{HARD_MAX_CALLS}")
        ap["max_calls"] = a.max_calls
    if a.expires:
        exp = parse_time(a.expires)
        if exp > now() + dt.timedelta(days=HARD_MAX_DAYS):
            raise LoopError(f"承認期限は最長 {HARD_MAX_DAYS} 日です")
        ap["expires"] = exp.isoformat(timespec="seconds")
    ap.setdefault("extensions", []).append({"at": iso(), "user_quote": a.user_quote})
    if s["status"] == "limit_reached" and s["iteration"] < s["max_iterations"]:
        s["status"] = "awaiting_work"
        s["iteration"] += 1
        it_dir(d, s["iteration"])
    save_state(d, s, "extend", approval=ap)
    out({"run": s["id"], "status": s["status"], "approval": ap})


def instruction(s: dict) -> dict:
    st = s["status"]
    acts = s.get("accepted_actions", [])
    msg = {
        "awaiting_work": ("Claude が作業する番。" + ("採用した指示を実行し、" if acts else "目的に沿って成果物を作成し、")
                          + "成果物を artifacts/ に保存して submit する。"),
        "awaiting_review": "review を実行する（承認範囲内なら --send、試験は --mock）。",
        "reviewing": "レビュー中。プロセスが落ちた場合は recover。",
        "awaiting_decisions": "GPT の各指示について根拠を自分で確認し、decide で採用/不採用を記録する。",
        "awaiting_final_check": "GPT は PASS。Claude が合格条件を自分で確認し finish（不十分なら finish --reject-pass）。",
        "paused": "一時停止中。ユーザーの『再開』で resume。",
        "blocked": "GPT が BLOCKED と判定。ユーザーに questions を伝え、回答を得たら resume --note。",
        "needs_user": "ユーザーにしかできない作業・判断がある。ユーザーに確認し、結果を resume --note で記録。",
        "stalled": "同じ指摘が繰り返され進展がない。ユーザーに状況を報告し、方針を確認する。",
        "limit_reached": "承認された反復回数に到達。結果を報告し、続けるならユーザーの追加承認で extend。",
        "done": "完了。結果を報告する。",
        "stopped": "停止済み。",
    }[st]
    return {"status": st, "may_continue_autonomously": st in ("awaiting_work", "awaiting_review",
                                                              "awaiting_decisions", "awaiting_final_check"),
            "message": msg, "accepted_actions": acts if st == "awaiting_work" else [],
            "pending_actions": [p for p in s.get("pending_actions", []) if p.get("decision") is None]
            if st == "awaiting_decisions" else []}


def cmd_next(a):
    d, s = resolve_run(a)
    halted = (H() / "STOP").exists()
    r = {"run": s["id"], "iteration": f"{s['iteration']}/{s['max_iterations']}", **instruction(s)}
    if halted:
        r["may_continue_autonomously"] = False
        r["message"] = "全体停止（STOP）中。ユーザーの指示なしに進めない。"
    out(r)


def cmd_submit(a):
    d, s = resolve_run(a)
    if s["status"] != "awaiting_work":
        raise LoopError(f"submit できる状態ではありません: {s['status']}")
    w = ws_dir(s["workspace"])
    arts = []
    for rel in a.artifact:
        rel = safe_rel(rel)
        p = w / "artifacts" / rel
        if not p.is_file():
            raise LoopError(f"成果物がありません: artifacts/{rel}")
        if gb.is_denied(rel):
            raise LoopError(f"秘密情報の可能性があるファイル名は扱いません: {rel}")
        data = p.read_bytes()
        if b"\x00" in data[:8192]:
            raise LoopError(f"テキストファイルのみ扱えます: {rel}")
        arts.append(rel)
    if not arts:
        raise LoopError("--artifact を 1 つ以上指定してください")
    ev_ids = {e["id"] for e in read_jsonl(w / "evidence.jsonl")}
    unknown_ev = [e for e in a.evidence if e not in ev_ids]
    if unknown_ev:
        raise LoopError(f"根拠台帳にない ID: {unknown_ev}")
    facts = visible_facts(s["workspace"])
    unknown_f = [f for f in a.facts if f not in facts]
    if unknown_f:
        raise LoopError(f"このワークスペースで参照できない事実 ID（存在しない・置換済み・他ワークスペース専用）: {unknown_f}")
    accepted = {x["id"] for x in s["accepted_actions"]}
    done = set(a.done)
    skipped = dict(x.split(":", 1) for x in a.skipped) if a.skipped else {}
    missing = accepted - done - set(skipped)
    if missing:
        raise LoopError(f"採用した指示の実施結果がありません: {sorted(missing)}（--done か --skipped ID:理由）")
    if not a.forecast.strip():
        raise LoopError("--forecast（事前予測：何が指摘されそうか・合格条件）は必須です")
    idir = it_dir(d, s["iteration"])
    snap = idir / "artifacts"
    if snap.exists():
        shutil.rmtree(snap)
    for rel in arts:
        (snap / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(w / "artifacts" / rel, snap / rel)
    sub = {"artifacts": arts, "evidence": a.evidence, "facts": a.facts, "summary": a.summary, "log": a.log,
           "open_issues": a.open_issues, "forecast": a.forecast, "done": sorted(done), "skipped": skipped,
           "submitted": iso()}
    write_json(idir / "submission.json", sub)
    s["status"] = "awaiting_review"
    save_state(d, s, "submit", artifacts=arts, evidence=a.evidence, facts=a.facts)
    out({"run": s["id"], "iteration": s["iteration"], "status": s["status"]})


# ------------------------------------------------------------------ レビュー

def _data_class(rel: str) -> str:
    return "baseline" if rel.startswith("baseline/") else "artifacts"


def build_review(d: Path, s: dict) -> dict:
    w = ws_dir(s["workspace"])
    mode_cfg = load_mode(s["mode"])
    idir = it_dir(d, s["iteration"])
    sub = read_json(idir / "submission.json")
    pol_text, pol_refs, pol_missing = rv.extract_policies(
        H() / "policies", policy_selection(mode_cfg, s["task_type"]), mode_cfg["policy_char_limit"])
    all_facts = visible_facts(s["workspace"])
    facts, blocked_facts = [], []
    for fid in sub["facts"]:
        f = all_facts.get(fid)
        if not f:
            raise LoopError(f"事実 {fid} は現在参照できません（置換・撤回された可能性）")
        (facts if f["gpt_ok"] and f["sensitivity"] != "secret" else blocked_facts).append(f)
    if blocked_facts:
        raise LoopError("GPT への送信が許可されていない事実が含まれます: "
                        + ", ".join(f["id"] for f in blocked_facts) + "（submit からはずすか本人の許可を得て登録し直す）")
    ev_all = {e["id"]: e for e in read_jsonl(w / "evidence.jsonl")}
    evidence = [ev_all[e] for e in sub["evidence"]]
    artifacts = [(rel, (idir / "artifacts" / rel).read_text(encoding="utf-8", errors="replace"))
                 for rel in sub["artifacts"]]
    prev = None
    if s["iteration"] > 1:
        pv = it_dir(d, s["iteration"] - 1) / "verdict.json"
        pd = it_dir(d, s["iteration"] - 1) / "decisions.json"
        if pv.exists():
            v = read_json(pv)
            prev = {"verdict": v["verdict"], "summary": v["summary"], "decisions": read_json(pd, [])}
    text, notes = rv.build_packet(run=s, mode_cfg=mode_cfg, policy_text=pol_text, policy_refs=pol_refs,
                                  facts=facts, evidence=evidence, artifacts=artifacts, submission=sub,
                                  previous=prev, artifact_char_limit=20000)
    text, n_terms = apply_redact_terms(text)
    classes = {"policies"} if pol_text else set()
    classes |= {_data_class(r) for r in sub["artifacts"]}
    if facts:
        classes.add("facts")
    if evidence:
        classes.add("evidence")
    return {"text": text, "classes": sorted(classes), "policy_refs": pol_refs, "policy_missing": pol_missing,
            "notes": notes, "redacted_terms": n_terms, "mode_cfg": mode_cfg}


def bridge_cfg(s: dict) -> dict:
    cfg = gb.load_config(gb.repo_root())
    ap = s.get("approval") or {}
    if ap:
        cfg["model"] = ap["model"]
        cfg["max_output_tokens"] = ap["output_tokens_per_call"]
    cfg["max_input_chars"] = max(cfg["max_input_chars"], 120000)
    cfg["retries"] = 0  # AUTOMATION: 失敗時の自動再試行なし（再試行は承認範囲内で明示的に）
    cfg["store"] = False
    gb.validate_config(cfg)
    return cfg


def check_budget(s: dict, est_in: int, cfg: dict) -> None:
    ap = s.get("approval")
    if not ap:
        raise LoopError("有料のレビュー送信には包括承認（approve）が必要です")
    if now() > parse_time(ap["expires"]):
        raise LoopError(f"承認期限 {ap['expires']} を過ぎています（ユーザーの追加承認で extend）")
    if cfg["model"] != ap["model"]:
        raise LoopError("承認されたモデルと異なります")
    if s["iteration"] > ap["max_iterations"]:
        raise LoopError("承認された反復回数を超えています")
    u = s["usage"]
    if u["calls"] >= ap["max_calls"]:
        raise LoopError(f"承認された呼び出し回数 {ap['max_calls']} に達しました")
    if u["input_tokens"] + est_in > ap["max_input_tokens"]:
        raise LoopError(f"入力トークン予算を超えます（使用 {u['input_tokens']} + 見込み {est_in} > {ap['max_input_tokens']}）")
    if u["output_tokens"] + ap["output_tokens_per_call"] > ap["max_output_tokens"]:
        raise LoopError(f"出力トークン予算を超えます（使用 {u['output_tokens']} + 最大 {ap['output_tokens_per_call']} > {ap['max_output_tokens']}）")
    if ap.get("max_usd") is not None:
        worst = u["usd"] + (est_in * ap["price_in_per_mtok"] + ap["output_tokens_per_call"] * ap["price_out_per_mtok"]) / 1e6
        if worst > ap["max_usd"]:
            raise LoopError(f"費用予算を超える可能性があります（最悪 ${worst:.4f} > ${ap['max_usd']}）")


def _fingerprint(v: dict) -> list:
    return sorted({f"{i['target_file']}|{i['severity']}|{i['rule_ref']}" for i in v["issues"]})


def screen_action(act: dict, ws: Path) -> str | None:
    """GPT の指示を機械的に審査する。問題があれば自動不採用の理由を返す。"""
    if FORBIDDEN_ACTION.search(act["action"]):
        return "禁止操作（応募・送信・公開・main 変更等）を含むため自動不採用"
    tf = act["target_file"].strip()
    if tf in ("", "-", "N/A", "none"):
        return None
    rel = tf[4:] if tf.startswith("NEW:") else tf
    try:
        rel = safe_rel(rel)
    except LoopError:
        return f"対象ファイルが不正なパス: {tf}"
    if gb.is_denied(rel):
        return f"対象ファイル名が秘密情報の可能性: {tf}"
    if not tf.startswith("NEW:") and not (ws / "artifacts" / rel).is_file():
        return f"存在しない成果物を対象にしている: {tf}"
    return None


def apply_verdict(d: Path, s: dict, v: dict, source: str) -> None:
    idir = it_dir(d, s["iteration"])
    write_json(idir / "verdict.json", v)
    s["last_verdict"] = {"verdict": v["verdict"], "summary": v["summary"], "iteration": s["iteration"],
                         "source": source}
    s["last_error"] = None
    w = ws_dir(s["workspace"])
    if v["verdict"] == "PASS":
        s["status"] = "awaiting_final_check"
        s["pending_actions"] = []
    elif v["verdict"] == "BLOCKED":
        s["status"] = "blocked"
        s["pending_actions"] = []
    else:
        fp = _fingerprint(v)
        if s.get("last_fingerprint") and fp == s["last_fingerprint"]:
            s["status"] = "stalled"
        else:
            s["status"] = "awaiting_decisions"
        s["last_fingerprint"] = fp
        pend = []
        for act in v["next_actions"]:
            reason = screen_action(act, w)
            pend.append({**act, "decision": "rejected_auto" if reason else None,
                         "reason": reason, "checked": None})
        s["pending_actions"] = pend
    save_state(d, s, "review", verdict=v["verdict"], source=source,
               issues=len(v["issues"]), actions=len(v["next_actions"]),
               normalization=v.get("_normalization_notes", []))
    if s["status"] == "awaiting_decisions" and all(p["decision"] for p in s["pending_actions"]):
        finalize_decisions(d, s)  # すべて自動不採用なら Claude の判断待ちを飛ばす


def cmd_review(a, opener=None):
    d, s = resolve_run(a)
    if (H() / "STOP").exists():
        raise LoopError("全体停止（STOP）中のためレビューしません")
    if s["status"] != "awaiting_review":
        raise LoopError(f"review できる状態ではありません: {s['status']}")
    pkt = build_review(d, s)
    idir = it_dir(d, s["iteration"])
    mode_cfg = pkt["mode_cfg"]
    cfg = bridge_cfg(s)
    ctx = gb.Context(cfg, gb.repo_root())
    payload = gb.build_payload(cfg, mode_cfg["review_prompt"], pkt["text"], ctx,
                               text_format=rv.TEXT_FORMAT, extra_instructions=rv.REVIEW_CONTRACT)
    est_in = len(payload["instructions"]) + len(payload["input"])  # 日本語は概ね 1 文字 ≤ 1 トークン（保守的）
    summary = {"run": s["id"], "iteration": s["iteration"], "model": cfg["model"],
               "data_classes": pkt["classes"], "policy_refs": pkt["policy_refs"],
               "policy_missing": pkt["policy_missing"], "estimated_input_tokens": est_in,
               "max_output_tokens": payload["max_output_tokens"], "redactions": ctx.redactions,
               "redacted_terms": pkt["redacted_terms"], "notes": pkt["notes"], "usage": s["usage"]}

    if a.mock is None and not a.send:
        summary["dry_run"] = True
        out(summary)
        if a.show_packet:
            print(payload["instructions"] + "\n\n" + payload["input"])
        return

    if a.mock is not None:
        raw = Path(a.mock).read_text(encoding="utf-8")
        source = "mock"
    else:
        ap = s.get("approval") or {}
        not_ok = set(pkt["classes"]) - set(ap.get("data", []))
        if ap and not_ok:
            raise LoopError(f"承認されていないデータ区分を送ろうとしています: {sorted(not_ok)}")
        check_budget(s, est_in, cfg)
        s["usage"]["calls"] += 1          # 送信前に計上（落ちても過小計上しない）
        s["status"] = "reviewing"
        save_state(d, s, "review_send", estimated_input_tokens=est_in, data_classes=pkt["classes"])
        (idir / "packet.txt").write_text(payload["instructions"] + "\n\n" + payload["input"], encoding="utf-8")
        try:
            res = gb.send(cfg, payload, opener)
        except gb.BridgeError as e:
            s["usage"]["input_tokens"] += est_in
            s["status"] = "awaiting_review"
            s["last_error"] = str(e)
            save_state(d, s, "review_error", error=str(e))
            raise LoopError(f"GPT 呼び出しに失敗しました（状態は awaiting_review に戻しました）: {e}", 3)
        it_in = res.get("input_tokens") or est_in
        it_out = res.get("output_tokens") or payload["max_output_tokens"]
        s["usage"]["input_tokens"] += it_in
        s["usage"]["output_tokens"] += it_out
        ap = s["approval"]
        if ap.get("price_in_per_mtok") is not None:
            s["usage"]["usd"] += (it_in * ap["price_in_per_mtok"] + it_out * ap["price_out_per_mtok"]) / 1e6
        raw = res["text"]
        source = f"gpt:{res.get('model') or cfg['model']}:{res.get('id')}"
        if res.get("status") == "incomplete":
            s["status"] = "awaiting_review"
            s["last_error"] = f"応答が途中で終了: {res.get('incomplete_reason')}"
            (idir / "raw_output.txt").write_text(raw, encoding="utf-8")
            save_state(d, s, "review_error", error=s["last_error"])
            raise LoopError(s["last_error"] + "（成果物を絞るか、承認範囲内で出力上限を見直す）", 3)

    try:
        v = rv.validate_verdict(rv.parse_model_text(raw))
    except rv.VerdictError as e:
        (idir / "raw_output.txt").write_text(raw, encoding="utf-8")
        s["status"] = "awaiting_review"
        s["last_error"] = f"構造化出力が不正: {e}"
        save_state(d, s, "review_error", error=s["last_error"], source=source)
        raise LoopError(s["last_error"] + "（raw_output.txt に保存。状態は awaiting_review）", 3)
    apply_verdict(d, s, v, source)
    out({**summary, "verdict": v["verdict"], "summary": v["summary"], "status": s["status"],
         "issues": v["issues"], "next_actions": s["pending_actions"],
         "blocked_reason": v["blocked_reason"], "questions_for_user": v["questions_for_user"],
         "normalization": v.get("_normalization_notes", []),
         "note": "GPT の回答は未検証の助言。各指示の根拠を成果物・事実・根拠台帳で確認してから decide する。"})


# ------------------------------------------------------------------ Claude の判断・終了・制御

def _record_decisions(d: Path, s: dict) -> list[dict]:
    pend = s["pending_actions"]
    write_json(it_dir(d, s["iteration"]) / "decisions.json",
               [{"id": p["id"], "decision": p["decision"], "action": p["action"], "reason": p["reason"],
                 "checked": p["checked"]} for p in pend])
    return [p for p in pend if p["decision"] == "accepted"]


def finalize_decisions(d: Path, s: dict) -> None:
    pend = s["pending_actions"]
    accepted = _record_decisions(d, s)
    if s["status"] == "stalled":
        pass
    elif any(p["requires_user"] for p in accepted):
        s["status"] = "needs_user"
    elif s["iteration"] >= s["max_iterations"]:
        s["status"] = "limit_reached"
    else:
        s["status"] = "awaiting_work"
        s["iteration"] += 1
        it_dir(d, s["iteration"])
    s["accepted_actions"] = [{k: p[k] for k in ("id", "action", "target_file", "verification", "requires_user")}
                             for p in accepted]
    s["pending_actions"] = []
    save_state(d, s, "decisions", accepted=[p["id"] for p in accepted],
               rejected=[p["id"] for p in pend if p["decision"] != "accepted"])


def cmd_decide(a):
    d, s = resolve_run(a)
    if s["status"] not in ("awaiting_decisions", "stalled"):
        raise LoopError(f"decide できる状態ではありません: {s['status']}")
    if len(a.reason.strip()) < 8:
        raise LoopError("--reason に確認した根拠を具体的に書いてください（8 文字以上）")
    hit = [p for p in s["pending_actions"] if p["id"] == a.action]
    if not hit:
        raise LoopError(f"指示 ID がありません: {a.action}")
    p = hit[0]
    if p["decision"] == "rejected_auto":
        raise LoopError(f"{a.action} は自動不採用です: {p['reason']}")
    if p["decision"]:
        raise LoopError(f"{a.action} は判断済みです: {p['decision']}")
    if a.accept and not (a.checked or "").strip():
        raise LoopError("採用する場合は --checked に自分で確認した内容（ファイル・行・根拠 ID）を書いてください")
    p["decision"] = "accepted" if a.accept else "rejected"
    p["reason"] = a.reason
    p["checked"] = a.checked
    if all(x["decision"] for x in s["pending_actions"]):
        finalize_decisions(d, s)
    else:
        save_state(d, s, "decide", action=a.action, decision=p["decision"])
    out({"run": s["id"], "status": s["status"], "iteration": s["iteration"],
         "undecided": [x["id"] for x in s["pending_actions"] if not x["decision"]],
         "next": instruction(s)})


def cmd_finish(a):
    d, s = resolve_run(a)
    if s["status"] != "awaiting_final_check":
        raise LoopError(f"finish できる状態ではありません: {s['status']}")
    if len(a.reason.strip()) < 8:
        raise LoopError("--reason に Claude 自身の最終確認内容を書いてください")
    write_json(it_dir(d, s["iteration"]) / "final_check.json",
               {"accepted_pass": not a.reject_pass, "reason": a.reason, "at": iso()})
    if a.reject_pass:
        if s["iteration"] >= s["max_iterations"]:
            s["status"] = "limit_reached"
        else:
            s["status"] = "awaiting_work"
            s["iteration"] += 1
            s["accepted_actions"] = []
            it_dir(d, s["iteration"])
        save_state(d, s, "pass_rejected_by_claude", reason=a.reason)
    else:
        s["status"] = "done"
        save_state(d, s, "done", reason=a.reason)
    out({"run": s["id"], "status": s["status"], "next": instruction(s)})


def cmd_pause(a):
    d, s = resolve_run(a)
    if s["status"] in TERMINAL or s["status"] == "paused":
        raise LoopError(f"一時停止できない状態です: {s['status']}")
    if s["status"] == "reviewing":
        raise LoopError("レビュー通信中です。完了を待つか recover してください")
    s["resume_to"], s["status"] = s["status"], "paused"
    save_state(d, s, "pause", reason=a.reason)
    out({"run": s["id"], "status": "paused", "resume_to": s["resume_to"]})


def cmd_resume(a):
    d, s = resolve_run(a)
    st = s["status"]
    if st == "paused":
        s["status"], s["resume_to"] = s["resume_to"], None
        save_state(d, s, "resume", note=a.note)
    elif st in ("blocked", "needs_user", "stalled"):
        if not (a.note or "").strip():
            raise LoopError(f"{st} から再開するには --note にユーザーの回答・判断を記録してください")
        keep = [x for x in s["accepted_actions"] if not x["requires_user"]]
        if st == "stalled":
            for p in s["pending_actions"]:
                if not p["decision"]:
                    p["decision"], p["reason"] = "rejected", "停滞のためユーザー判断で打ち切り"
            _record_decisions(d, s)
            s["pending_actions"], keep = [], []
        if s["iteration"] >= s["max_iterations"]:
            s["status"] = "limit_reached"
            save_state(d, s, "resume_denied_limit", note=a.note)
            raise LoopError("反復回数の上限に達しています。続けるにはユーザーの追加承認で extend")
        s["status"] = "awaiting_work"
        s["iteration"] += 1
        s["accepted_actions"] = keep + [{"id": "U1", "action": f"ユーザーの回答を反映: {a.note}",
                                         "target_file": "-", "requires_user": False,
                                         "verification": "回答内容が成果物に正しく反映されていること"}]
        it_dir(d, s["iteration"])
        save_state(d, s, "resume", note=a.note, from_status=st)
    else:
        raise LoopError(f"再開が必要な状態ではありません: {st}")
    out({"run": s["id"], "status": s["status"], "next": instruction(s)})


def cmd_stop(a):
    d, s = resolve_run(a)
    if s["status"] == "reviewing":
        raise LoopError("レビュー通信中です。完了を待つか recover してください")
    s["status"] = "stopped"
    save_state(d, s, "stop", reason=a.reason)
    out({"run": s["id"], "status": "stopped"})


def cmd_halt(a):
    p = H() / "STOP"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"at": iso(), "reason": a.reason}, ensure_ascii=False))
    out({"halted": True})


def cmd_unhalt(a):
    p = H() / "STOP"
    if p.exists():
        p.unlink()
    out({"halted": False})


def cmd_recover(a):
    d, s = resolve_run(a)
    if s["status"] != "reviewing":
        raise LoopError(f"recover が必要な状態ではありません: {s['status']}")
    s["status"] = "awaiting_review"
    s["last_error"] = "通信中に中断（recover）"
    save_state(d, s, "recover")
    out({"run": s["id"], "status": s["status"], "usage": s["usage"],
         "note": "中断した呼び出しは課金されている可能性があるため、回数は計上済みのまま"})


def cmd_status(a):
    if a.run:
        runs = [read_json(run_dir(a.run) / "state.json")]
    else:
        pattern = f"{a.ws}/runs/*/state.json" if a.ws else "*/runs/*/state.json"
        runs = [read_json(p) for p in sorted((H() / "workspaces").glob(pattern))]
        if not a.all:
            runs = [r for r in runs if r["status"] not in TERMINAL]
    rows = []
    for s in runs:
        ap = s.get("approval")
        rows.append({"run": s["id"], "workspace": s["workspace"], "task_type": s["task_type"], "goal": s["goal"],
                     "status": s["status"], "iteration": f"{s['iteration']}/{s['max_iterations']}",
                     "usage": s["usage"],
                     "approval": None if not ap else {k: ap[k] for k in ("model", "max_calls", "max_input_tokens",
                                                                          "max_output_tokens", "max_usd", "expires")},
                     "last_verdict": s["last_verdict"], "last_error": s["last_error"],
                     "next": instruction(s)["message"]})
    out({"halted": (H() / "STOP").exists(), "runs": rows})


def cmd_history(a):
    d, s = resolve_run(a)
    out(read_jsonl(d / "history.jsonl"))


# ------------------------------------------------------------------ 退避と復元（使い捨てコンテナ対策）

def cmd_export(a):
    h = H()
    files = {}
    for p in sorted(h.rglob("*")):
        if p.is_file() and not p.name.endswith(".tmp"):
            rel = p.relative_to(h).as_posix()
            data = p.read_bytes()
            if b"\x00" in data[:8192]:
                continue
            files[rel] = data.decode("utf-8", errors="replace")
    bundle = {"format": "judgment-loop-snapshot/1", "created": iso(), "files": files}
    text = json.dumps(bundle, ensure_ascii=False)
    if len(text.encode()) > 4_500_000:
        raise LoopError("スナップショットが 4.5MB を超えます（Dropbox の作成上限 5MB）。古い実行を整理してください")
    dest = Path(a.out)
    if _inside_git(dest.parent.resolve()) and not os.environ.get("JUDGMENT_LOOP_ALLOW_IN_REPO"):
        raise LoopError("スナップショットを Git の作業ツリー内に書き出すことはできません")
    dest.write_text(text, encoding="utf-8")
    out({"snapshot": str(dest), "files": len(files), "bytes": len(text.encode()),
         "sha256": hashlib.sha256(text.encode()).hexdigest()})


def cmd_import(a):
    h = H()
    bundle = json.loads(Path(a.snapshot).read_text(encoding="utf-8"))
    if bundle.get("format") != "judgment-loop-snapshot/1":
        raise LoopError("スナップショットの形式が不正です")
    conflicts, written = [], 0
    for rel, text in bundle["files"].items():
        rel = safe_rel(rel)
        p = h / rel
        if p.exists() and p.read_text(encoding="utf-8", errors="replace") != text and not a.overwrite:
            conflicts.append(rel)
            continue
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        written += 1
    out({"imported": written, "conflicts": conflicts, "created": bundle["created"]})
    if conflicts:
        raise LoopError("既存ファイルと内容が異なるため取り込まなかったファイルがあります（--overwrite で上書き）")


# ------------------------------------------------------------------ CLI

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="orchestrator", description="Claude⇄GPT 反復オーケストレーター")
    p.add_argument("--version", action="version", version=VERSION)
    sub = p.add_subparsers(dest="cmd", required=True)

    def sp(name, fn, help_):
        x = sub.add_parser(name, help=help_)
        x.set_defaults(fn=fn)
        return x

    def run_sel(x):
        x.add_argument("--run")
        x.add_argument("--ws")

    x = sp("policies-import", cmd_policies_import, "判断基準 ZIP（policies/*.md のみ）を非公開ホームへ取り込む")
    x.add_argument("source")
    x = sp("policies-show", cmd_policies_show, "作業種別ごとに送る判断基準の抜粋を確認")
    x.add_argument("--mode", required=True)
    x.add_argument("--task-type", required=True)
    x.add_argument("--full", action="store_true")

    x = sp("ws-create", cmd_ws_create, "ワークスペース作成")
    x.add_argument("name")
    x.add_argument("--mode", required=True)
    x.add_argument("--alias", action="append", default=[], help="自然言語で呼ぶ名前（非公開ホームにのみ保存）")
    x.add_argument("--target", action="append", default=[], help="応募先など（非公開ホームにのみ保存）")
    sp("ws-list", cmd_ws_list, "ワークスペース一覧")

    x = sp("fact-add", cmd_fact_add, "本人情報（承認済み事実）を追加")
    x.add_argument("--statement", required=True)
    x.add_argument("--source", required=True, help="出典（例: dropbox:id:... 本人確認 2026-11-24）")
    x.add_argument("--observed", required=True, help="確認日 YYYY-MM-DD")
    x.add_argument("--status", required=True, choices=["verified", "reported", "inferred"])
    x.add_argument("--type", default="factual-report",
                   choices=["preference", "factual-report", "project-decision", "validated-result", "hypothesis",
                            "constraint"])
    x.add_argument("--scope", default="shared", help="shared または ws:<名前>")
    x.add_argument("--sensitivity", default="private", choices=["public", "private", "secret"])
    x.add_argument("--gpt-ok", action="store_true", help="本人が GPT への送信を許可した事実のみ付ける")
    x.add_argument("--valid-until", default="要再確認")
    x.add_argument("--supersedes")
    x = sp("fact-list", cmd_fact_list, "有効な事実の一覧")
    x.add_argument("--ws")
    x = sp("redact-add", cmd_redact_add, "送信前に伏せ字にする語（実名など）を登録")
    x.add_argument("term")

    x = sp("ref-add", cmd_ref_add, "基準資料・参照資料の所在を登録（本文は複製しない）")
    x.add_argument("--ws", required=True)
    x.add_argument("--role", required=True, choices=["baseline", "reference"])
    x.add_argument("--kind", required=True, choices=["dropbox", "url", "other"])
    x.add_argument("--ref", required=True)
    x.add_argument("--title", required=True)
    x.add_argument("--modified", default="")
    x.add_argument("--note", default="")

    x = sp("evidence-add", cmd_evidence_add, "根拠台帳に追加（TinyFish 等で取得した公式資料）")
    x.add_argument("--ws", required=True)
    x.add_argument("--claim", required=True)
    x.add_argument("--url", required=True)
    x.add_argument("--title", required=True)
    x.add_argument("--retrieved", required=True)
    x.add_argument("--locator", required=True, help="該当箇所（ページ・章・見出し）")
    x.add_argument("--excerpt", required=True)
    x.add_argument("--tool", default="tinyfish")
    x.add_argument("--status", default="SUPPORTED", choices=["VERIFIED", "SUPPORTED", "REPORTED"])
    x = sp("evidence-list", cmd_evidence_list, "根拠台帳の一覧")
    x.add_argument("--ws", required=True)

    x = sp("start", cmd_start, "反復を開始")
    x.add_argument("--ws", required=True)
    x.add_argument("--task-type", required=True)
    x.add_argument("--goal", required=True)
    x.add_argument("--max-iterations", type=int, default=3)

    x = sp("approve", cmd_approve, "包括承認を記録（回数・予算・送信データ・期限）")
    run_sel(x)
    x.add_argument("--model", required=True)
    x.add_argument("--max-iterations", type=int, required=True)
    x.add_argument("--max-calls", type=int, required=True)
    x.add_argument("--max-input-tokens", type=int, required=True)
    x.add_argument("--max-output-tokens", type=int, required=True, help="全呼び出しの出力トークン合計の上限")
    x.add_argument("--output-tokens-per-call", type=int, default=3000)
    x.add_argument("--max-usd", type=float)
    x.add_argument("--price-in", type=float, help="入力 100 万トークンあたり USD")
    x.add_argument("--price-out", type=float, help="出力 100 万トークンあたり USD")
    x.add_argument("--data", required=True, help=f"送信を許可するデータ区分（{','.join(DATA_CLASSES)}）")
    x.add_argument("--expires", required=True)
    x.add_argument("--snapshots", default="none", help="状態スナップショットの保存先（例: dropbox）")
    x.add_argument("--user-quote", required=True)
    x = sp("extend", cmd_extend, "ユーザーの追加承認で上限・期限を延長")
    run_sel(x)
    x.add_argument("--max-iterations", type=int)
    x.add_argument("--max-calls", type=int)
    x.add_argument("--expires")
    x.add_argument("--user-quote", required=True)

    x = sp("next", cmd_next, "次に Claude がすべきこと")
    run_sel(x)
    x = sp("submit", cmd_submit, "成果物・記録を提出（Claude の作業完了）")
    run_sel(x)
    x.add_argument("--artifact", action="append", default=[], help="artifacts/ からの相対パス")
    x.add_argument("--evidence", action="append", default=[])
    x.add_argument("--facts", action="append", default=[])
    x.add_argument("--summary", required=True)
    x.add_argument("--log", required=True, help="実行記録（何を調べ・何を変えたか）")
    x.add_argument("--open-issues", default="")
    x.add_argument("--forecast", required=True)
    x.add_argument("--done", action="append", default=[], help="実施した採用指示 ID")
    x.add_argument("--skipped", action="append", default=[], help="実施しなかった採用指示 ID:理由")
    x = sp("review", cmd_review, "GPT の独立レビュー（既定は dry-run）")
    run_sel(x)
    x.add_argument("--send", action="store_true", help="実際に送信（有料・承認範囲内のみ）")
    x.add_argument("--mock", help="GPT の出力テキストの代わりに使うファイル（試験用・無料）")
    x.add_argument("--show-packet", action="store_true")
    x = sp("decide", cmd_decide, "GPT の指示の採否を記録（Claude の検証結果）")
    run_sel(x)
    x.add_argument("--action", required=True)
    g = x.add_mutually_exclusive_group(required=True)
    g.add_argument("--accept", action="store_true")
    g.add_argument("--reject", action="store_true")
    x.add_argument("--reason", required=True)
    x.add_argument("--checked", help="採用時: 自分で確認した内容（ファイル・行・根拠 ID）")
    x = sp("finish", cmd_finish, "PASS 後の Claude 最終確認")
    run_sel(x)
    x.add_argument("--reason", required=True)
    x.add_argument("--reject-pass", action="store_true")
    for name, fn, h in (("pause", cmd_pause, "一時停止"), ("stop", cmd_stop, "終了")):
        x = sp(name, fn, h)
        run_sel(x)
        x.add_argument("--reason", default="")
    x = sp("resume", cmd_resume, "再開")
    run_sel(x)
    x.add_argument("--note", default="")
    x = sp("halt", cmd_halt, "全体停止（すべての実行のレビュー送信を止める）")
    x.add_argument("--reason", default="")
    sp("unhalt", cmd_unhalt, "全体停止の解除")
    x = sp("recover", cmd_recover, "通信中に落ちた実行を復旧")
    run_sel(x)
    x = sp("status", cmd_status, "状況")
    run_sel(x)
    x.add_argument("--all", action="store_true")
    x = sp("history", cmd_history, "履歴")
    run_sel(x)
    x = sp("export", cmd_export, "非公開ホームのスナップショットを書き出す")
    x.add_argument("--out", required=True)
    x = sp("import", cmd_import, "スナップショットを取り込む")
    x.add_argument("snapshot")
    x.add_argument("--overwrite", action="store_true")
    return p


def main(argv: list[str] | None = None, opener=None) -> int:
    a = build_parser().parse_args(argv)
    try:
        if a.fn is cmd_review:
            cmd_review(a, opener)
        else:
            a.fn(a)
        return 0
    except LoopError as e:
        print(f"[judgment-loop] {e}", file=sys.stderr)
        return e.exit_code
    except gb.BridgeError as e:
        print(f"[judgment-loop] {e}", file=sys.stderr)
        return e.exit_code


if __name__ == "__main__":
    sys.exit(main())
