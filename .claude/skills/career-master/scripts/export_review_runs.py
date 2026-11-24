#!/usr/bin/env python3
"""judgment-loop の実行記録を、監査用の一覧（Markdown）と写しとして書き出す。

読むもの : $JUDGMENT_LOOP_HOME/workspaces/<ws>/runs/<run>/{state.json,history.jsonl,iterations/*/…}
書くもの : <out>/runs/<ws>/<run>/…（写し。上書きコピー）と <out>/review_runs_index.md

レビューの種別を必ず分けて書く:
  gpt-send           … GPT へ実際に送信し、応答を得た
  gpt-send-failed    … 送信を試みたが応答を得られなかった（判定なし）
  claude-independent … GPT の代わりに独立した Claude エージェントが判定した（--mock-source で記録）
  mock               … --mock で取り込んだ判定（出所ラベルなし。試験用の模擬応答を含む）
外部通信はしない。
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path


def home() -> Path:
    return Path(os.environ.get("JUDGMENT_LOOP_HOME", Path.home() / ".judgment-loop"))


def load_json(p: Path, default=None):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def load_jsonl(p: Path) -> list[dict]:
    out = []
    try:
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    out.append({"event": "unparsed", "raw": line[:200]})
    except OSError:
        pass
    return out


def one_line(s, n=160) -> str:
    s = " ".join(str(s or "").split())
    return s if len(s) <= n else s[: n - 1] + "…"


def review_kind(events: list[dict], iteration: int, verdict: dict | None) -> str:
    """その反復のレビューが何によるものかを、履歴に残っている source からそのまま読む。"""
    evs = [e for e in events if e.get("iteration") == iteration]
    if verdict is None:
        return "gpt-send-failed" if any(e.get("event") == "review_error" for e in evs) else "none"
    src = [e.get("source") for e in evs if e.get("event") == "review" and e.get("source")]
    if not src:
        return "unknown"
    label = src[-1]
    if label == "mock" or label.startswith("claude"):
        return label
    return "gpt-send（" + label + "）"


def summarize_run(ws: str, run_dir: Path) -> dict:
    state = load_json(run_dir / "state.json", {}) or {}
    events = load_jsonl(run_dir / "history.jsonl")
    iters = []
    for it_dir in sorted((run_dir / "iterations").glob("*")):
        if not it_dir.is_dir():
            continue
        try:
            n = int(it_dir.name)
        except ValueError:
            continue
        verdict = load_json(it_dir / "verdict.json")
        decisions = load_json(it_dir / "decisions.json", []) or []
        final = load_json(it_dir / "final_check.json")
        sub = load_json(it_dir / "submission.json", {}) or {}
        kind = review_kind(events, n, verdict)
        iters.append(
            {
                "n": n,
                "kind": kind,
                "artifacts": sub.get("artifacts", []),
                "verdict": (verdict or {}).get("verdict"),
                "summary": (verdict or {}).get("summary"),
                "issues": (verdict or {}).get("issues", []) or [],
                "actions": (verdict or {}).get("next_actions", []) or [],
                "questions": (verdict or {}).get("questions_for_user", []) or [],
                "decisions": decisions,
                "final": final,
                "packets": sorted(p.name for p in it_dir.glob("packet_part*.txt")),
            }
        )
    errors = [e for e in events if e.get("event") == "review_error"]
    sends = [e for e in events if e.get("event") == "review_send"]
    return {
        "ws": ws,
        "id": state.get("id", run_dir.name),
        "goal": state.get("goal"),
        "task_type": state.get("task_type"),
        "status": state.get("status"),
        "created": state.get("created"),
        "updated": state.get("updated"),
        "usage": state.get("usage", {}),
        "model": (state.get("approval") or {}).get("model"),
        "user_quote": (state.get("approval") or {}).get("user_quote"),
        "iters": iters,
        "sends": sends,
        "errors": errors,
        "last_error": state.get("last_error"),
    }


def render(runs: list[dict], budget: dict | None) -> str:
    L = ["# レビュー実行の一覧（監査用）", ""]
    L += [
        "種別の意味: **gpt-send**＝GPT へ実送信して応答あり／**gpt-send-failed**＝送信を試みたが応答なし（判定は存在しない）／"
        "**claude-independent**＝GPT の代わりに独立した Claude エージェントが判定（GPT 未レビュー）／**mock**＝--mock で取り込んだ判定（出所ラベルなし。GPT ではない）。",
        "",
    ]
    if budget:
        u = budget.get("used", {})
        L += [
            "## GPT 予算（全体）",
            f"- 承認: モデル {budget.get('model')}／最大 {budget.get('max_calls')} 回／入力 {budget.get('max_input_tokens')}・出力 {budget.get('max_output_tokens')} トークン／期限 {budget.get('expires')}",
            f"- 使用（台帳上）: 呼び出し {u.get('calls', 0)} 回／入力 {u.get('input_tokens', 0)}／出力 {u.get('output_tokens', 0)}",
            f"- 承認の文言: {one_line(budget.get('user_quote'), 400)}",
            "",
        ]
    L += ["## 実行ごとの要約", "", "| 実行 | 目的 | 状態 | 反復 | レビュー種別 | 最終判定 | GPT 実送信 |", "|---|---|---|---|---|---|---|"]
    for r in runs:
        kinds = sorted({it["kind"] for it in r["iters"] if it["kind"] != "none"}) or ["なし"]
        verdicts = [it["verdict"] for it in r["iters"] if it["verdict"]]
        ok = len(r["sends"]) - len(r["errors"])
        send = f"試行 {len(r['sends'])}／成功 {max(ok, 0)}／失敗 {len(r['errors'])}"
        L.append(
            f"| {r['ws']}/{r['id']} | {one_line(r['goal'], 60)} | {r['status']} | {len(r['iters'])} | {', '.join(kinds)} | {verdicts[-1] if verdicts else '判定なし'} | {send} |"
        )
    L.append("")
    for r in runs:
        L += [f"## {r['ws']}/{r['id']}", f"- 目的: {one_line(r['goal'], 300)}", f"- 種類: {r['task_type']}／状態: {r['status']}／作成 {r['created']}／更新 {r['updated']}"]
        u = r["usage"] or {}
        L.append(f"- GPT 使用量（この実行）: 呼び出し {u.get('calls', 0)}／入力 {u.get('input_tokens', 0)}／出力 {u.get('output_tokens', 0)}")
        for e in r["errors"]:
            L.append(f"- 送信エラー {e.get('ts')}: {one_line(e.get('error'), 220)}")
        for it in r["iters"]:
            L += ["", f"### 反復 {it['n']}（レビュー種別: {it['kind']}）"]
            if it["artifacts"]:
                L.append("- 提出物: " + ", ".join(it["artifacts"]))
            if it["packets"]:
                L.append("- 保存された送信パケット: " + ", ".join(it["packets"]))
            if it["verdict"] is None:
                L.append("- 判定: **なし**（レビュー結果は存在しない）")
                continue
            L.append(f"- 判定: **{it['verdict']}** — {one_line(it['summary'], 260)}")
            sev = {}
            for i in it["issues"]:
                s = str(i.get("severity", "?"))
                sev[s] = sev.get(s, 0) + 1
            if sev:
                L.append("- 指摘: " + "、".join(f"{k}×{v}" for k, v in sorted(sev.items())))
            dec = {d.get("id"): d for d in it["decisions"]}
            if it["actions"]:
                L += ["", "| 指示 | 内容 | 採否 | 理由 | 確認したもの |", "|---|---|---|---|---|"]
                for a in it["actions"]:
                    d = dec.get(a.get("id"), {})
                    L.append(
                        f"| {a.get('id')} | {one_line(a.get('action') or a.get('instruction'), 110)} | {d.get('decision', '未判断')} | {one_line(d.get('reason'), 110)} | {one_line(d.get('checked'), 70)} |"
                    )
            if it["questions"]:
                L += ["", "本人への質問（レビューから）:"] + [f"- {one_line(q, 200)}" for q in it["questions"]]
            if it["final"]:
                f = it["final"]
                L += ["", f"- 最終確認: {'PASS を受理' if f.get('accepted_pass') else 'PASS を不受理'} — {one_line(f.get('reason'), 260)}（{f.get('at')}）"]
        L.append("")
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", required=True, help="書き出し先フォルダ（非公開の場所）")
    ap.add_argument("--no-copy", action="store_true", help="実行フォルダの写しを作らない")
    a = ap.parse_args(argv)
    h = home()
    out = Path(a.out).resolve()
    # 公開されうる Git 作業ツリーの中には書かない
    for parent in [out, *out.parents]:
        if (parent / ".git").exists():
            print(f"error: {out} は Git 作業ツリーの中です。非公開の場所を指定してください。", file=sys.stderr)
            return 2
    out.mkdir(parents=True, exist_ok=True)
    runs = []
    for ws_dir in sorted((h / "workspaces").glob("*")):
        for run_dir in sorted((ws_dir / "runs").glob("*")):
            if not (run_dir / "state.json").exists():
                continue
            runs.append(summarize_run(ws_dir.name, run_dir))
            if not a.no_copy:
                dst = out / "runs" / ws_dir.name / run_dir.name
                shutil.copytree(run_dir, dst, dirs_exist_ok=True)
    budget = load_json(h / "budget.json")
    (out / "review_runs_index.md").write_text(render(runs, budget), encoding="utf-8")
    print(json.dumps({"runs": len(runs), "out": str(out / "review_runs_index.md")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
