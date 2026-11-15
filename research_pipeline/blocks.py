"""論文・教材の正本（ブロック付きMarkdown）の読み取り。

書式:
    ::: meta
    title: ...
    :::
    # 見出し（ブロックの外に書けるのは見出し・空行・HTMLコメントだけ）
    ::: evidence id=P8-U004 claims=CLAIM-000001,CLAIM-000002
    本文（Markdown）
    :::

ブロックの外に本文を書くと「根拠のない文」としてエラーになる（全文を追跡可能にするため）。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

OPEN = re.compile(r"^:::\s*([a-z_]+)(.*)$")
ATTR = re.compile(r'([a-z_]+)=("([^"]*)"|\S+)')
LIST_ATTRS = {"claims", "units", "lo"}


@dataclass
class Block:
    kind: str
    attrs: dict
    text: str
    line: int

    @property
    def id(self) -> str:
        return self.attrs.get("id", "")

    def ids(self, name: str) -> list[str]:
        v = self.attrs.get(name, [])
        return v if isinstance(v, list) else [v]


@dataclass
class Doc:
    path: Path
    meta: dict = field(default_factory=dict)
    items: list = field(default_factory=list)   # ("heading", level, text, line) | ("block", Block)
    errors: list[str] = field(default_factory=list)

    @property
    def blocks(self) -> list[Block]:
        return [it[1] for it in self.items if it[0] == "block"]


def parse_attrs(s: str) -> dict:
    out: dict = {}
    for m in ATTR.finditer(s):
        key, val = m.group(1), m.group(3) if m.group(3) is not None else m.group(2)
        out[key] = [v for v in re.split(r"[,;]", val) if v] if key in LIST_ATTRS else val
    return out


def parse(path: Path) -> Doc:
    doc = Doc(path)
    lines = path.read_text(encoding="utf-8").splitlines()
    i, in_comment = 0, False
    while i < len(lines):
        raw = lines[i]
        s = raw.strip()
        if in_comment:
            in_comment = "-->" not in s
            i += 1
            continue
        m = OPEN.match(s)
        if m:
            kind, attrs, start = m.group(1), parse_attrs(m.group(2)), i + 1
            body = []
            i += 1
            while i < len(lines) and lines[i].strip() != ":::":
                if OPEN.match(lines[i].strip()):
                    doc.errors.append(f"{path.name}:{i + 1}: ブロックの中で別のブロックが始まっている")
                body.append(lines[i])
                i += 1
            if i >= len(lines):
                doc.errors.append(f"{path.name}:{start}: ブロックが閉じていない")
            text = "\n".join(body).strip()
            if kind == "meta":
                for ln in body:
                    if ":" in ln:
                        k, v = ln.split(":", 1)
                        doc.meta[k.strip()] = v.strip()
            else:
                doc.items.append(("block", Block(kind, attrs, text, start)))
            i += 1
            continue
        if s.startswith("<!--"):
            in_comment = "-->" not in s
        elif s.startswith("#"):
            level = len(s) - len(s.lstrip("#"))
            doc.items.append(("heading", level, s.lstrip("#").strip(), i + 1))
        elif s:
            doc.errors.append(f"{path.name}:{i + 1}: ブロックの外に本文がある（根拠を追跡できない）: {s[:40]}")
        i += 1
    return doc
