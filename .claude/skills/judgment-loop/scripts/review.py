"""judgment-loop: GPT レビューの入力パケット組立・判断基準の抽出・構造化 JSON の検証。

このモジュールは個人データを持たない。データはすべて呼び出し側（orchestrator.py）が
非公開ホーム（リポジトリ外）から読み込んで渡す。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

# ------------------------------------------------------------------ 判断基準の抽出

_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")


def split_sections(md: str) -> list[dict]:
    """Markdown を見出し単位に分割する。各節は次の同格以上の見出しの直前まで。"""
    lines = md.splitlines()
    heads = []
    in_code = False
    for i, ln in enumerate(lines):
        if ln.strip().startswith("```"):
            in_code = not in_code
        m = None if in_code else _HEADING.match(ln)
        if m:
            heads.append((i, len(m.group(1)), m.group(2).strip()))
    out = []
    for k, (i, lvl, title) in enumerate(heads):
        end = len(lines)
        for j, lvl2, _ in heads[k + 1:]:
            if lvl2 <= lvl:
                end = j
                break
        out.append({"title": title, "level": lvl, "text": "\n".join(lines[i:end]).strip()})
    if heads and heads[0][1] == 1:
        # H1 直下（最初の下位見出しより前）の導入部
        first_sub = heads[1][0] if len(heads) > 1 else len(lines)
        out.append({"title": "__intro__", "level": 1,
                    "text": "\n".join(lines[heads[0][0]:first_sub]).strip()})
    return out


def extract_policies(policy_dir: Path, selection: dict, char_limit: int) -> tuple[str, list[str], list[str]]:
    """selection = {"FILE.md": ["見出しの部分文字列", "__intro__", "*"]}
    戻り値: (抜粋テキスト, 採用した参照 ID 一覧, 見つからなかった指定)"""
    parts, refs, missing = [], [], []
    for fname, selectors in selection.items():
        path = policy_dir / fname
        if not path.is_file():
            missing.append(f"{fname}（ファイルなし）")
            continue
        md = path.read_text(encoding="utf-8")
        secs = split_sections(md)
        for sel in selectors:
            if sel == "*":
                hits = [{"title": "*", "text": md.strip()}]
            else:
                hits = [s for s in secs if s["title"] == sel] or \
                       [s for s in secs if sel != "__intro__" and sel in s["title"]]
            if not hits:
                missing.append(f"{fname}#{sel}")
                continue
            sec = hits[0]
            ref = f"{fname.removesuffix('.md')}#{sec['title']}"
            parts.append(f"[{ref}]\n{sec['text']}")
            refs.append(ref)
    text = "\n\n".join(parts)
    if len(text) > char_limit:
        text = text[:char_limit] + f"\n...[判断基準の抜粋を {char_limit} 文字で切り詰め]"
    return text, refs, missing


# ------------------------------------------------------------------ 構造化出力スキーマ

VERDICTS = ("PASS", "REVISE", "BLOCKED")
GATES = ("G0", "G1", "G2", "G3", "G4", "G5")
GATE_STATUS = ("PASS", "FAIL", "INCOMPLETE", "BLOCKED", "NOT_APPLICABLE")
SEVERITIES = ("P0", "P1", "P2", "P3")

_STR = {"type": "string"}
VERDICT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["verdict", "summary", "gate_results", "issues", "next_actions",
                 "blocked_reason", "forecast_delta", "questions_for_user"],
    "properties": {
        "verdict": {"type": "string", "enum": list(VERDICTS)},
        "summary": _STR,
        "gate_results": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "required": ["gate", "status", "reason"],
            "properties": {"gate": {"type": "string", "enum": list(GATES)},
                           "status": {"type": "string", "enum": list(GATE_STATUS)},
                           "reason": _STR}}},
        "issues": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "required": ["id", "severity", "target_file", "location", "problem", "evidence_refs", "rule_ref"],
            "properties": {"id": _STR, "severity": {"type": "string", "enum": list(SEVERITIES)},
                           "target_file": _STR, "location": _STR, "problem": _STR,
                           "evidence_refs": {"type": "array", "items": _STR}, "rule_ref": _STR}}},
        "next_actions": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "required": ["id", "priority", "action", "target_file", "rationale", "verification",
                         "requires_user", "addresses"],
            "properties": {"id": _STR, "priority": {"type": "integer"}, "action": _STR,
                           "target_file": _STR, "rationale": _STR, "verification": _STR,
                           "requires_user": {"type": "boolean"},
                           "addresses": {"type": "array", "items": _STR}}}},
        "blocked_reason": {"type": ["string", "null"]},
        "forecast_delta": _STR,
        "questions_for_user": {"type": "array", "items": _STR},
    },
}

TEXT_FORMAT = {"type": "json_schema", "name": "loop_review_verdict", "strict": True, "schema": VERDICT_SCHEMA}

REVIEW_CONTRACT = (
    "You are the independent reviewer in an iterative loop. Claude Code does the actual work; you evaluate the "
    "deliverables against the provided judgment criteria excerpts, candidate facts and evidence ledger, and tell "
    "Claude exactly what to do next. Return ONLY the JSON object required by the schema. Rules: "
    "verdict=PASS only if no P0/P1 issue remains and no gate is FAIL; REVISE if concrete fixes are needed; "
    "BLOCKED if progress needs information or a decision only the user can provide (set blocked_reason and "
    "questions_for_user). Each issue must cite target_file (one of the provided artifact paths), a location, "
    "evidence_refs (fact IDs F-..., evidence IDs E-..., or line numbers) and rule_ref (a criteria reference "
    "shown in brackets, e.g. QUALITY_GATES#__intro__). Each next_action must be one concrete, verifiable step "
    "Claude can perform, with target_file (an existing artifact path or NEW:<relative path>), rationale, "
    "verification (how Claude can check it is done correctly), addresses (issue IDs) and priority (1 = first). "
    "Set requires_user=true when only the user can do or decide it. Never propose submitting applications, "
    "sending e-mails/messages, publishing, pushing to main, or inventing achievements. forecast_delta: compare "
    "Claude's stated forecast with what you actually found."
)


class VerdictError(ValueError):
    pass


def _check(cond: bool, msg: str) -> None:
    if not cond:
        raise VerdictError(msg)


def validate_verdict(v) -> dict:
    """スキーマ準拠を検証し、論理矛盾を正規化して返す。"""
    _check(isinstance(v, dict), "verdict が JSON オブジェクトではありません")
    req = VERDICT_SCHEMA["required"]
    missing = [k for k in req if k not in v]
    _check(not missing, f"必須キー不足: {missing}")
    extra = set(v) - set(req)
    _check(not extra, f"未知のキー: {sorted(extra)}")
    _check(v["verdict"] in VERDICTS, f"verdict 不正: {v['verdict']}")
    _check(isinstance(v["summary"], str), "summary は文字列")
    for g in v["gate_results"]:
        _check(isinstance(g, dict) and g.get("gate") in GATES and g.get("status") in GATE_STATUS
               and isinstance(g.get("reason"), str), f"gate_results 不正: {g}")
    ids = set()
    for i in v["issues"]:
        _check(isinstance(i, dict) and i.get("severity") in SEVERITIES, f"issues 不正: {i}")
        for k in ("id", "target_file", "location", "problem", "rule_ref"):
            _check(isinstance(i.get(k), str), f"issue.{k} は文字列")
        _check(isinstance(i.get("evidence_refs"), list), "issue.evidence_refs は配列")
        ids.add(i["id"])
    aids = set()
    for a in v["next_actions"]:
        _check(isinstance(a, dict), f"next_actions 不正: {a}")
        for k in ("id", "action", "target_file", "rationale", "verification"):
            _check(isinstance(a.get(k), str) and a[k].strip(), f"next_action.{k} が空です")
        _check(isinstance(a.get("priority"), int), "next_action.priority は整数")
        _check(isinstance(a.get("requires_user"), bool), "next_action.requires_user は真偽値")
        _check(isinstance(a.get("addresses"), list), "next_action.addresses は配列")
        _check(a["id"] not in aids, f"next_action.id 重複: {a['id']}")
        aids.add(a["id"])
    _check(v["blocked_reason"] is None or isinstance(v["blocked_reason"], str), "blocked_reason 不正")
    _check(isinstance(v["forecast_delta"], str), "forecast_delta は文字列")
    _check(isinstance(v["questions_for_user"], list), "questions_for_user は配列")

    notes = []
    if v["verdict"] == "PASS":
        severe = [i["id"] for i in v["issues"] if i["severity"] in ("P0", "P1")]
        failed = [g["gate"] for g in v["gate_results"] if g["status"] in ("FAIL", "BLOCKED")]
        if severe or failed:
            v["verdict"] = "REVISE"
            notes.append(f"PASS だが重大指摘 {severe} / 不合格ゲート {failed} があるため REVISE に格下げ")
    if v["verdict"] == "REVISE" and not v["next_actions"]:
        raise VerdictError("REVISE なのに next_actions が空です")
    if v["verdict"] == "BLOCKED" and not (v["blocked_reason"] or "").strip():
        raise VerdictError("BLOCKED なのに blocked_reason が空です")
    v["next_actions"].sort(key=lambda a: a["priority"])
    v["_normalization_notes"] = notes
    return v


def parse_model_text(text: str) -> dict:
    """モデル出力から JSON を取り出す（strict 出力が基本だが、```json 囲みにも耐える）。"""
    t = text.strip()
    m = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", t, re.S)
    if m:
        t = m.group(1)
    try:
        return json.loads(t)
    except json.JSONDecodeError as e:
        raise VerdictError(f"GPT の出力が JSON ではありません: {e}")


# ------------------------------------------------------------------ パケット組立

def number_lines(text: str, limit: int) -> tuple[str, bool]:
    lines = text.splitlines()
    body = "\n".join(f"{i:>4}: {ln}" for i, ln in enumerate(lines, 1))
    if len(body) > limit:
        return body[:limit] + f"\n...[TRUNCATED at {limit} chars]", True
    return body, False


def build_packet(*, run: dict, mode_cfg: dict, policy_text: str, policy_refs: list[str],
                 facts: list[dict], evidence: list[dict], artifacts: list[tuple[str, str]],
                 submission: dict, previous: dict | None, artifact_char_limit: int) -> tuple[str, list[str]]:
    """GPT へ送る本文を組み立てる。戻り値: (本文, 注記)"""
    notes = []
    tt = mode_cfg["task_types"][run["task_type"]]
    out = [
        "## タスク",
        f"- 作業モード: {mode_cfg['label']}",
        f"- 作業種別: {tt['label']}",
        f"- 目的: {run['goal']}",
        f"- 反復: {run['iteration']} / {run['max_iterations']}",
        "",
        "## この作業種別の評価観点",
        *[f"- {r}" for r in tt["rubric"]],
        "",
        "## 判断基準（抜粋。rule_ref には [] 内の参照を使う）",
        policy_text or "（抜粋なし）",
    ]
    if facts:
        out += ["", "## 本人の承認済み事実（このほかの本人情報は存在しないものとして扱う）"]
        for f in facts:
            out.append(f"- {f['id']} [{f['status']} / 出典: {f['source']} / 確認日: {f['observed']}] {f['statement']}")
    if evidence:
        out += ["", "## 根拠台帳（Claude が収集した公式資料。引用は該当箇所の抜粋）"]
        for e in evidence:
            out.append(f"- {e['id']}: {e['claim']}\n  資料名: {e['title']} / URL: {e['url']} / 取得日: "
                       f"{e['retrieved']} / 該当箇所: {e['locator']}\n  抜粋: {e['excerpt']}")
    out += ["", "## 成果物（行番号付き）"]
    for rel, text in artifacts:
        body, cut = number_lines(text, artifact_char_limit)
        if cut:
            notes.append(f"{rel} を {artifact_char_limit} 文字で切り詰め")
        out.append(f"<<<artifact: {rel}>>>\n{body}\n<<<end {rel}>>>")
    out += ["", "## Claude の実行記録",
            f"- 要約: {submission.get('summary', '')}",
            f"- 実施内容: {submission.get('log', '')}",
            f"- 未解決事項: {submission.get('open_issues', '') or 'なし'}",
            f"- 事前予測（何が指摘されると予想したか・合格条件）: {submission.get('forecast', '')}"]
    if previous:
        out += ["", "## 前回の指摘と Claude の判断"]
        out.append(f"- 前回判定: {previous['verdict']} — {previous['summary']}")
        for d in previous.get("decisions", []):
            out.append(f"- {d['id']} {d['decision']}: {d['action']} / 理由: {d['reason']}")
    return "\n".join(out), notes
