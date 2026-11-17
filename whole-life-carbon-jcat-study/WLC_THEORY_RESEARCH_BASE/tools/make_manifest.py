#!/usr/bin/env python3
"""研究基盤 WLC_THEORY_RESEARCH_BASE の資料一覧 manifest.json を作る。

使い方（研究基盤のフォルダで、または任意の場所から）:

    python3 -B tools/make_manifest.py --created-at 2026-11-17T00:40:00Z --base-commit f2ea616

    --created-at   作成時点（ISO 8601、必須。例 2026-11-17T00:40:00Z）
    --base-commit  研究基盤が参照した研究ブランチのコミット（必須。例 f2ea616）
    --branch       研究ブランチの名前（既定 claude/jcat-lca-app-foundation-c33936）
    --base-branch  研究基盤を保存するブランチの名前（既定 claude/wlc-theory-research-base-c33936）
    --root         研究基盤のフォルダ（既定：このスクリプトの 1 つ上のフォルダ）
    --out          出力先（既定：<root>/manifest.json）
    --check-git    git が使えるとき、原典の章ごとの最終コミットを
                   `git log -1 --format=%h <base-commit> -- <章>` で確かめ、結果を書き込む（読み取りだけ）

標準ライブラリだけを使う。`__pycache__` と manifest.json 自身は一覧に入れない
（manifest.json の SHA-256 は自分自身を含められないため）。
同じ入力からは同じ manifest.json ができる（日時は引数で与え、実行時刻は使わない）。
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys

sys.dont_write_bytecode = True

NAME = "WLC_THEORY_RESEARCH_BASE"
VERSION = "1.0"
DEFAULT_BRANCH = "claude/jcat-lca-app-foundation-c33936"
DEFAULT_BASE_BRANCH = "claude/wlc-theory-research-base-c33936"
REPOSITORY = "csta24055-sys/-"
STUDY_DIR = "whole-life-carbon-jcat-study"

# 本基盤が使った原典（章 → 研究ブランチ f2ea616 の時点でその章を最後に変更したコミット）。
# 値は `git -C <worktree> log -1 --format=%h -- whole-life-carbon-jcat-study/<章>` で確かめたもの。
SOURCES = [
    ("README.md", "4705fd3", "研究フォルダ全体の目次（参照のみ）"),
    ("01_COMPLIANCE", "b6f0fa7", "禁止事項・権利の規則（R01〜R09）"),
    ("09_APPROX_STUDY", "b2b8a6e", "旧研究（停止）：70 評価単位の台帳・凍結した基準計算・生成器"),
    ("10_TRANSFORM_STUDY", "b93201e", "変換研究：マスク付き積和・節点スペクトル・統一系（全 70 単位）"),
    ("14_EQUATION_DISCLOSURE", "4c38df6", "全方程式の開示（統一系の全ステップ・全スペクトル・建物全体の式）"),
    ("15_JCAT_CONVERSION", "fdfbc16", "J-CAT 原版の 667 式の分類と変換（公開分のみ）"),
    ("16_UNRESOLVED8_EXACT_APPROX", "6d867ea", "未解決 8 件：方式 A・B、不可能性の証明（公開分のみ）"),
    ("17_WHOLE_BUILDING_TIME_THEORY", "e207eff", "建物全体の理想方程式 C(T)・係数表・時間特性の定理と証明"),
    ("18_DYNAMIC_LCA_EXTENSION", "46781f2", "動的 LCA：17 の工程関数・再構成・非一意性"),
    ("19_JCAT_REMAINING12", "3a30103", "原版の残り 12 式（公開分のみ）"),
    ("20_LARGE_RANDOM_VERIFICATION", "3a30103", "大規模ランダム検証（10 万ケース）"),
    ("21_UNIFIED_THEORY_REPORT", "3a30103", "統一研究報告（主張の区別）"),
    ("22_WLC_COMPLETE_TEXTBOOK", "b28532c", "教材（五つの原理）と研究記録"),
    ("research_archive", "2ed3a78", "停止した旧研究（実数方程式）の保存資料"),
    ("12_APP_BASE", "391dada", "アプリの基礎（研究基盤の対象外。指し示すだけ）"),
    ("23_WLC_STUDIO_APP", "f2ea616", "アプリ WLC Studio（研究基盤の対象外。指し示すだけ）"),
]

KINDS = {".md": "md", ".json": "json", ".csv": "csv", ".py": "py"}
CITE_RE = re.compile(r"((?:0[1-9]|1[0-9]|2[0-3])_[A-Z0-9_]+|research_archive)(?:/[^\s@|`]*)?`?@([0-9a-f]{7})")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def md_title(path):
    with open(path, encoding="utf-8") as f:
        in_code = False
        for line in f:
            s = line.rstrip("\n")
            if s.startswith("```"):
                in_code = not in_code
                continue
            if not in_code and re.match(r"^#{1,6}\s", s):
                return s.lstrip("#").strip()
    return None


def scan_citations(path, acc):
    """md の本文から `章/…@コミット` の引用を集める（章 → コミットの集合）。"""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    for m in CITE_RE.finditer(text):
        chap = m.group(1)
        acc.setdefault(chap, set()).add(m.group(2))


def git_last_commit(repo_dir, rev, rel):
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0")
    try:
        out = subprocess.run(
            ["git", "-C", repo_dir, "log", "-1", "--format=%h", rev, "--", rel],
            capture_output=True, text=True, env=env, timeout=60, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    v = out.stdout.strip()
    return v or None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--created-at", required=True)
    ap.add_argument("--base-commit", required=True)
    ap.add_argument("--branch", default=DEFAULT_BRANCH)
    ap.add_argument("--base-branch", default=DEFAULT_BASE_BRANCH)
    ap.add_argument("--root", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--out", default=None)
    ap.add_argument("--check-git", action="store_true")
    a = ap.parse_args(argv)

    if not re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:\d{2})$", a.created_at):
        ap.error("--created-at は ISO 8601（例 2026-11-17T00:40:00Z）で与える")
    if not re.match(r"^[0-9a-f]{7,40}$", a.base_commit):
        ap.error("--base-commit は 16 進のコミット ID")

    root = os.path.abspath(a.root)
    out = a.out or os.path.join(root, "manifest.json")
    files, cited = [], {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d != "__pycache__" and not d.startswith("."))
        for fn in sorted(filenames):
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            if rel == "manifest.json" or os.path.abspath(full) == os.path.abspath(out):
                continue
            if fn.endswith((".pyc", ".pyo")):
                continue
            ext = os.path.splitext(fn)[1].lower()
            entry = {
                "path": rel,
                "bytes": os.path.getsize(full),
                "sha256": sha256(full),
                "kind": KINDS.get(ext, ext.lstrip(".") or "other"),
            }
            if entry["kind"] == "md":
                entry["title"] = md_title(full)
                scan_citations(full, cited)
            files.append(entry)
    files.sort(key=lambda e: e["path"])

    study_dir = os.path.dirname(root)
    try:
        top_chapters = {d for d in os.listdir(study_dir) if os.path.isdir(os.path.join(study_dir, d))}
    except OSError:
        top_chapters = set()

    sources = []
    repo_dir = os.path.dirname(os.path.dirname(root))  # <worktree>/whole-life-carbon-jcat-study/<base> → <worktree>
    for chap, commit, note in SOURCES:
        s = {"chapter": chap, "path": f"{STUDY_DIR}/{chap}", "last_commit": commit, "contents": note}
        if a.check_git:
            got = git_last_commit(repo_dir, a.base_commit, f"{STUDY_DIR}/{chap}")
            s["git_check"] = ("ok" if got == commit else f"differs:{got}") if got else "not-checked"
        sources.append(s)

    manifest = {
        "name": NAME,
        "version": VERSION,
        "created_at": a.created_at,
        "base_commit": a.base_commit,
        "repository": REPOSITORY,
        "research_branch": a.branch,
        "base_branch": a.base_branch,
        "base_path": f"{STUDY_DIR}/{NAME}",
        "description": ("70 評価単位・マスク付き積和・節点スペクトル・建物全体の理想方程式・動的 LCA・"
                        "証明と検証・仮説 A〜J・劣化と交換のモデルの研究基盤（アプリとは独立）。"
                        "J-CAT 原版の式本文・係数・値・セル内容は含まない。"),
        "evidence_classes": {
            "P": "数学的に証明済み", "E": "厳密な算術（有理数）で標本照合済み",
            "F": "浮動小数の計算で照合・測定済み", "S": "宣言した分布で統計的に確認済み",
            "L": "文献で支持される", "H": "未検証の新しい仮説",
        },
        "excluded": ["manifest.json（自分自身）", "__pycache__", "*.pyc"],
        "n_files": len(files),
        "total_bytes": sum(e["bytes"] for e in files),
        "files": files,
        "sources": sources,
        "cited_commits": {k: sorted(v) for k, v in sorted(cited.items()) if k in top_chapters or not top_chapters},
        "generated_by": "tools/make_manifest.py",
    }
    tmp = out + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, out)
    print(f"wrote {out}: {len(files)} files, {manifest['total_bytes']} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
