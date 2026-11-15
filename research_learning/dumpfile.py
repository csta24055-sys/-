"""コード全文ダンプ（「= 100個 / # ファイル: パス / = 100個」の3行組区切り）の解析と安全な復元。

structlab-exam の tools/restore_dump.py（commit 33a45ea, cdddcd0 と同一）の parse() を移植し、
復元先の安全性検査（絶対パス・.. の拒否、既存ファイルを上書きしない）を関数化した。
"""
from __future__ import annotations

import hashlib
from pathlib import Path

SEP = "=" * 100
PREFIX = "# ファイル: "


def parse(text: str) -> list[tuple[str, str, str]]:
    lines = text.split("\n")
    marks: list[tuple[int, str, str]] = []
    i = 0
    while i + 2 < len(lines):
        if lines[i] == SEP and lines[i + 1].startswith(PREFIX) and lines[i + 2] == SEP:
            raw = lines[i + 1][len(PREFIX):].strip()
            # 「path  ※注記」形式の注記はパスに含めない（注記は manifest に残す）
            path, _, note = raw.partition("  ※")
            marks.append((i, path.strip(), note.strip()))
            i += 3
        else:
            i += 1
    files = []
    for k, (start, path, note) in enumerate(marks):
        end = marks[k + 1][0] if k + 1 < len(marks) else len(lines)
        body = lines[start + 3:end]
        # ダンプ側が各ファイルの後ろに入れた区切り用の空行を 1 行だけ除く
        if body and body[-1] == "":
            body = body[:-1]
        content = "\n".join(body)
        if content and not content.endswith("\n"):
            content += "\n"
        files.append((path, content, note))
    return files



def verify_against(dump_text: str, root: Path) -> dict:
    """ダンプの各ファイルが root 以下の実ファイルと一致するかを調べる（書き込みはしない）。"""
    res = {"files": 0, "same": [], "different": [], "missing": [], "unsafe": []}
    for path, content, _ in parse(dump_text):
        res["files"] += 1
        if path.startswith("/") or ".." in Path(path).parts:
            res["unsafe"].append(path)
            continue
        p = root / path
        if not p.exists():
            res["missing"].append(path)
        elif p.read_text(encoding="utf-8").rstrip("\n") == content.rstrip("\n"):
            res["same"].append(path)
        else:
            res["different"].append(path)
    return res


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()
