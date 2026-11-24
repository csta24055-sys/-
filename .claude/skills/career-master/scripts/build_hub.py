#!/usr/bin/env python3
"""複数の Markdown を、スマホで読める1つの HTML（通信なし）にまとめる。

使い方:
  build_hub.py <out.html> --title "題" --page "優先順位=path/a.md" --page "A社=path/b.md" …

- 外部のスクリプト・フォント・画像を一切読み込まない（単一ファイル、オフラインで動く）。
- 文面は Markdown のまま変えない。対応する書式: 見出し、表、箇条書き、番号つき、引用、
  コード（``` と `…`）、太字、区切り線。
- 個人の内容を含むので、公開 URL にはせずファイルとして渡す。Git 作業ツリー内への出力は拒否する。
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

INLINE_CODE = re.compile(r"`([^`]+)`")
BOLD = re.compile(r"\*\*(.+?)\*\*")
TABLE_SEP = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")
OL = re.compile(r"^(\s*)(\d+)[.)]\s+(.*)$")
UL = re.compile(r"^(\s*)[-*・]\s+(.*)$")


def inline(text: str) -> str:
    """エスケープしてから、コードと太字だけを戻す。"""
    parts = INLINE_CODE.split(text)
    out = []
    for i, p in enumerate(parts):
        if i % 2:
            out.append("<code>" + html.escape(p) + "</code>")
        else:
            out.append(BOLD.sub(r"<strong>\1</strong>", html.escape(p)))
    return "".join(out)


def split_row(line: str) -> list[str]:
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|") and not s.endswith("\\|"):
        s = s[:-1]
    cells, cur, in_code = [], "", False
    i = 0
    while i < len(s):
        ch = s[i]
        if ch == "`":
            in_code = not in_code
        if ch == "\\" and i + 1 < len(s) and s[i + 1] == "|":
            cur += "|"
            i += 2
            continue
        if ch == "|" and not in_code:
            cells.append(cur.strip())
            cur = ""
        else:
            cur += ch
        i += 1
    cells.append(cur.strip())
    return cells


def render(md: str) -> tuple[str, list[tuple[str, str]]]:
    """Markdown → (HTML, 目次[(id, 見出し)])。"""
    lines = md.replace("\r\n", "\n").split("\n")
    out: list[str] = []
    toc: list[tuple[str, str]] = []
    para: list[str] = []
    i, n, hid = 0, len(lines), 0

    def flush():
        if para:
            out.append("<p>" + "<br>".join(inline(x) for x in para) + "</p>")
            para.clear()

    while i < n:
        line = lines[i]
        s = line.strip()
        if s.startswith("```"):
            flush()
            buf = []
            i += 1
            while i < n and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1
            out.append("<pre>" + html.escape("\n".join(buf)) + "</pre>")
            continue
        if not s:
            flush()
            i += 1
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", s)
        if m:
            flush()
            lv = len(m.group(1))
            hid += 1
            anchor = f"h{hid}"
            if lv <= 2:
                toc.append((anchor, re.sub(r"[*`]", "", m.group(2))))
            out.append(f'<h{lv} id="{anchor}">{inline(m.group(2))}</h{lv}>')
            i += 1
            continue
        if re.match(r"^(-{3,}|\*{3,}|_{3,})$", s):
            flush()
            out.append("<hr>")
            i += 1
            continue
        if "|" in s and i + 1 < n and TABLE_SEP.match(lines[i + 1]) and "|" in lines[i + 1]:
            flush()
            head = split_row(s)
            i += 2
            rows = []
            while i < n and lines[i].strip() and "|" in lines[i]:
                rows.append(split_row(lines[i]))
                i += 1
            t = ['<div class="tw"><table><thead><tr>' + "".join(f"<th>{inline(c)}</th>" for c in head) + "</tr></thead><tbody>"]
            for r in rows:
                r = (r + [""] * len(head))[: max(len(head), len(r))]
                t.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>")
            t.append("</tbody></table></div>")
            out.append("".join(t))
            continue
        if s.startswith(">"):
            flush()
            buf = []
            while i < n and lines[i].strip().startswith(">"):
                buf.append(lines[i].strip()[1:].strip())
                i += 1
            out.append("<blockquote>" + "<br>".join(inline(x) for x in buf) + "</blockquote>")
            continue
        if UL.match(line) or OL.match(line):
            flush()
            ordered = bool(OL.match(line))
            tag = "ol" if ordered else "ul"
            items: list[str] = []
            while i < n:
                cur = lines[i]
                mu, mo = UL.match(cur), OL.match(cur)
                if mu and not ordered and len(mu.group(1)) < 2:
                    items.append(inline(mu.group(2)))
                elif mo and ordered and len(mo.group(1)) < 2:
                    items.append(inline(mo.group(3)))
                elif cur.strip() and (cur.startswith("  ") or cur.startswith("\t")) and items:
                    sub = UL.match(cur) or OL.match(cur)
                    txt = sub.group(sub.lastindex) if sub else cur.strip()
                    items[-1] += '<div class="sub">' + ("・" if sub else "") + inline(txt) + "</div>"
                else:
                    break
                i += 1
            out.append(f"<{tag}>" + "".join(f"<li>{x}</li>" for x in items) + f"</{tag}>")
            continue
        para.append(s)
        i += 1
    flush()
    return "\n".join(out), toc


CSS = """
:root{--bg:#f6f5f1;--card:#fff;--ink:#1d2327;--mut:#5d676e;--line:#dcd9d0;--acc:#0c5d4f;--code:#efede6}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#15181a;--card:#1e2225;--ink:#e9ecee;--mut:#a3adb4;--line:#343a3f;--acc:#6fd0bb;--code:#2a2f33}}
:root[data-theme="dark"]{--bg:#15181a;--card:#1e2225;--ink:#e9ecee;--mut:#a3adb4;--line:#343a3f;--acc:#6fd0bb;--code:#2a2f33}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.75 system-ui,-apple-system,"Hiragino Sans","Noto Sans JP",sans-serif}
header{position:sticky;top:0;z-index:5;background:var(--bg);border-bottom:1px solid var(--line);padding:10px 16px}
header h1{font-size:17px;margin:0 0 8px}
.bar{display:flex;gap:8px}
select,button{font:inherit;color:var(--ink);background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 12px;min-height:44px}
select{flex:1;min-width:0}
main{padding:16px;max-width:820px;margin:0 auto}
section{display:none}
section.on{display:block}
h1,h2,h3,h4{line-height:1.4;margin:1.4em 0 .5em}
main h1{font-size:21px}h2{font-size:19px;border-bottom:1px solid var(--line);padding-bottom:4px}h3{font-size:17px}h4{font-size:16px}
p{margin:.6em 0}
ul,ol{padding-left:1.4em;margin:.5em 0}
li{margin:.25em 0}
.sub{color:var(--ink);margin:.15em 0 .15em .2em}
code{background:var(--code);border-radius:5px;padding:1px 5px;font-size:.88em;overflow-wrap:anywhere}
pre{background:var(--code);border-radius:10px;padding:12px;overflow-x:auto;font-size:.86em;line-height:1.55;white-space:pre-wrap;word-break:break-word}
blockquote{margin:.6em 0;padding:.4em .9em;border-left:4px solid var(--acc);background:var(--card)}
hr{border:0;border-top:1px solid var(--line);margin:1.2em 0}
.tw{overflow-x:auto;margin:.7em -16px;padding:0 16px}
table{border-collapse:collapse;font-size:.9em;min-width:100%}
th,td{border:1px solid var(--line);padding:7px 9px;vertical-align:top;text-align:left;min-width:9.5em;max-width:24em}
td:first-child,th:first-child{min-width:5.5em}
th{background:var(--card);white-space:nowrap}
.toc{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:8px 14px;margin:0 0 14px}
.toc summary{cursor:pointer;color:var(--mut);padding:4px 0}
.toc a{display:block;color:var(--acc);text-decoration:none;padding:5px 0}
.note{color:var(--mut);font-size:.85em;margin:0 0 10px}
"""

JS = """
(function(){
  var sel=document.getElementById('pg'),secs=[].slice.call(document.querySelectorAll('main section'));
  function show(i){secs.forEach(function(s,k){s.classList.toggle('on',k===i)});sel.value=String(i);
    try{localStorage.setItem(KEY,String(i))}catch(e){} window.scrollTo(0,0)}
  var start=0;try{var v=parseInt(localStorage.getItem(KEY)||'0',10);if(v>=0&&v<secs.length)start=v}catch(e){}
  sel.addEventListener('change',function(){show(parseInt(sel.value,10))});
  document.getElementById('prev').addEventListener('click',function(){show((parseInt(sel.value,10)+secs.length-1)%secs.length)});
  document.getElementById('next').addEventListener('click',function(){show((parseInt(sel.value,10)+1)%secs.length)});
  show(start);
})();
"""


def build(title: str, pages: list[tuple[str, str]], note: str) -> str:
    opts, secs = [], []
    for idx, (name, md) in enumerate(pages):
        body, toc = render(md)
        toc_html = ""
        if len(toc) > 3:
            toc_html = '<details class="toc"><summary>このページの目次</summary>' + "".join(
                f'<a href="#p{idx}-{a}">{html.escape(t)}</a>' for a, t in toc
            ) + "</details>"
        body = re.sub(r'id="(h\d+)"', lambda m: f'id="p{idx}-{m.group(1)}"', body)
        opts.append(f'<option value="{idx}">{html.escape(name)}</option>')
        secs.append(f"<section>{toc_html}{body}</section>")
    key = json.dumps("hub:" + title)
    return (
        '<!doctype html><html lang="ja"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{html.escape(title)}</title><style>{CSS}</style></head><body>"
        f'<header><h1>{html.escape(title)}</h1><div class="bar"><button id="prev" aria-label="前のページ">‹</button>'
        f'<select id="pg" aria-label="ページ">{"".join(opts)}</select><button id="next" aria-label="次のページ">›</button></div></header>'
        f'<main><p class="note">{html.escape(note)}</p>{"".join(secs)}</main>'
        f"<script>var KEY={key};{JS}</script></body></html>"
    )


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("out")
    ap.add_argument("--title", default="資料")
    ap.add_argument("--page", action="append", required=True, metavar="名前=path.md")
    ap.add_argument("--note", default="この端末の中だけで動きます（通信なし）。文面は元の資料のままです。")
    a = ap.parse_args(argv)
    out = Path(a.out).resolve()
    for parent in [out.parent, *out.parent.parents]:
        if (parent / ".git").exists():
            print(f"error: {out} は Git 作業ツリーの中です。非公開の場所を指定してください。", file=sys.stderr)
            return 2
    pages = []
    for spec in a.page:
        if "=" not in spec:
            print(f"error: --page は「名前=path.md」の形で指定してください: {spec}", file=sys.stderr)
            return 2
        name, path = spec.split("=", 1)
        p = Path(path)
        if not p.is_file():
            print(f"error: ファイルがありません: {path}", file=sys.stderr)
            return 2
        pages.append((name.strip(), p.read_text(encoding="utf-8")))
    doc = build(a.title, pages, a.note)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(doc, encoding="utf-8")
    print(json.dumps({"pages": len(pages), "bytes": len(doc.encode("utf-8")), "out": str(out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
