"""教材の原稿（Markdown の部分集合）→ render.py のブロックの列。

  # 見出し / ## 小見出し / ### 小小見出し        h1 / h2 / h3（h1 は新しいページから）
  段落（空行で区切る）。文中の式は $…$、強調は **…**
  $$ … $$（1 行でも複数行でも）                 表示式。$$[3.1] … $$ で式番号
  - 項目 / 1. 項目（続きの行は 2 字下げ）          箇条書き
  | a | b |（2 行目が |---| の表）               表
  > **題** と続く > の行（> - で箇条書き）         囲み（要点・注意・例題など）
  ![説明](図のパス){width=120}                   図（幅 mm）
  ```  …  ```                                   等幅でない整形済みの文（計算の手順など）
  small: 文                                      小さい文字の注
  [TOC] / :::pagebreak / <!-- 注釈 -->           目次 / 改ページ / 無視
"""
from __future__ import annotations

import re
from pathlib import Path

CJK = re.compile(r"[　-鿿＀-￯]")
FIG = re.compile(r"^!(?:fig)?\[(.*?)\]\((.+?)\)(?:\{width=(\d+)\})?\s*$")


def _join(lines: list[str]) -> str:
    out = ""
    for ln in lines:
        ln = ln.strip()
        if not out:
            out = ln
        elif CJK.search(out[-1:]) or CJK.search(ln[:1]):
            out += ln
        else:
            out += " " + ln
    return out


def parse(text: str, base: Path | None = None) -> list[dict]:
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    lines = text.split("\n")
    blocks: list[dict] = []
    i = 0
    para: list[str] = []

    def flush():
        nonlocal para
        if para:
            blocks.append({"t": "p", "text": _join(para)})
            para = []

    while i < len(lines):
        ln = lines[i]
        s = ln.strip()
        if not s:
            flush()
            i += 1
            continue
        if s == "[TOC]":
            flush()
            blocks.append({"t": "toc"})
            i += 1
            continue
        if s == ":::pagebreak":
            flush()
            blocks.append({"t": "break"})
            i += 1
            continue
        m = re.match(r"^(#{1,3})\s+(.*)$", s)
        if m:
            flush()
            blocks.append({"t": f"h{len(m.group(1))}", "text": m.group(2).strip()})
            i += 1
            continue
        if s.startswith("small:"):
            flush()
            blocks.append({"t": "small", "text": s[6:].strip()})
            i += 1
            continue
        if s.startswith("$$"):
            flush()
            body = s[2:]
            if body.rstrip().endswith("$$") and len(body.strip()) > 2:
                tex = body.rstrip()[:-2]
                i += 1
            else:
                buf = [body]
                i += 1
                while i < len(lines) and not lines[i].strip().endswith("$$"):
                    buf.append(lines[i])
                    i += 1
                if i >= len(lines):
                    raise ValueError(f"$$ が閉じていない: {body[:40]}")
                buf.append(lines[i].strip()[:-2])
                i += 1
                tex = "\n".join(buf)
            tex = tex.strip()
            label = None
            lm = re.match(r"^\[([0-9A-Z]{1,2}\.[0-9]{1,2}[a-z]?)\]\s*(.*)$", tex, re.S)  # 式番号は [3.1] の形だけ
            if lm:
                label, tex = lm.group(1), lm.group(2).strip()
            blocks.append({"t": "math", "tex": " ".join(tex.split()), **({"label": label} if label else {})})
            continue
        if s.startswith("```"):
            flush()
            buf = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                buf.append(lines[i].rstrip())
                i += 1
            i += 1
            blocks.append({"t": "pre", "text": "\n".join(buf)})
            continue
        fm = FIG.match(s)
        if fm:
            flush()
            p = Path(fm.group(2))
            if base is not None and not p.is_absolute():
                p = base / p
            blocks.append({"t": "img", "path": str(p), "caption": fm.group(1),
                           **({"width_mm": int(fm.group(3))} if fm.group(3) else {})})
            i += 1
            continue
        if s.startswith("|"):
            flush()
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                row = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-{2,}:?", c) for c in row):
                    rows.append(row)
                i += 1
            blocks.append({"t": "table", "rows": rows})
            continue
        if s.startswith(">"):
            flush()
            buf = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                buf.append(lines[i].strip()[1:].strip())
                i += 1
            title = None
            if buf and re.match(r"^\*\*(.+?)\*\*\s*$", buf[0]):
                title = buf[0].strip("*").strip()
                buf = buf[1:]
            parts, cur, j = [], [], 0

            def endp():
                nonlocal cur
                if cur:
                    parts.append({"k": "p", "text": _join(cur)})
                    cur = []
            while j < len(buf):
                b = buf[j]
                if b.startswith("$$"):
                    endp()
                    body = b[2:]
                    if body.rstrip().endswith("$$") and len(body.strip()) > 2:
                        tex = body.rstrip()[:-2]
                    else:
                        acc = [body]
                        j += 1
                        while j < len(buf) and not buf[j].rstrip().endswith("$$"):
                            acc.append(buf[j])
                            j += 1
                        if j >= len(buf):
                            raise ValueError(f"囲みの中の $$ が閉じていない: {body[:40]}")
                        acc.append(buf[j].rstrip()[:-2])
                        tex = " ".join(acc)
                    parts.append({"k": "math", "tex": " ".join(tex.split())})
                elif b.startswith("- "):
                    endp()
                    parts.append({"k": "li", "text": b[2:].strip()})
                elif not b:
                    endp()
                else:
                    if parts and parts[-1]["k"] == "li" and not cur:
                        parts[-1]["text"] = _join([parts[-1]["text"], b])
                    else:
                        cur.append(b)
                j += 1
            endp()
            blocks.append({"t": "note", "title": title, "parts": parts})
            continue
        m = re.match(r"^(-|\d+\.)\s+(.*)$", s)
        if m:
            flush()
            kind = "olist" if m.group(1)[0].isdigit() else "list"
            items = []
            while i < len(lines):
                cur = lines[i]
                mm_ = re.match(r"^\s*(-|\d+\.)\s+(.*)$", cur)
                if mm_ and (mm_.group(1)[0].isdigit()) == (kind == "olist") and not cur.startswith("    "):
                    items.append(mm_.group(2).strip())
                    i += 1
                elif cur.startswith("  ") and cur.strip() and items:
                    items[-1] = _join([items[-1], cur])
                    i += 1
                else:
                    break
            blocks.append({"t": kind, "items": items})
            continue
        para.append(ln)
        i += 1
    flush()
    return blocks


def math_of(blocks: list[dict]) -> list[str]:
    out = []
    for b in blocks:
        if b["t"] == "math":
            out.append(b["tex"])
        elif b["t"] == "note":
            out += [p["tex"] for p in b.get("parts", []) if p["k"] == "math"]
    return out
