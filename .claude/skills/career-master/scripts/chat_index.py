#!/usr/bin/env python3
"""ChatGPT エクスポート復旧テキスト（recovered_NNN.txt の分割）を元ファイルへ復元し、
会話・発言単位の検索索引（SQLite + FTS5 trigram）を作る。

- 入力は読み取りのみ。派生物（復元ファイル・索引）は別フォルダに保存する。
- 各発言に「どの元ファイルの、何バイト目の会話か」「どの分割チャンクに当たるか」を残し、原文へ戻れるようにする。
- 本人（user）の発言と、AI（assistant）・ツールの発言を role で区別する。
- chat.html は conversations-*.json と同じ会話の別表現なので、索引は JSON から作り、chat.html は存在とハッシュだけ記録する。

使い方:
  python3 chat_index.py reassemble   # チャンク → 元ファイル（checkpoint つき）
  python3 chat_index.py build        # conversations-*.json → SQLite
  python3 chat_index.py stats
  python3 chat_index.py search "語1" ["語2" ...] [--role user] [--limit 50] [--since 2026-09-01]
  python3 chat_index.py show <conversation_id> [--around <message_id>] [--n 6]
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sqlite3
import sys
from pathlib import Path

BASE = Path(os.environ.get("CAREER_MASTER_HOME")
            or Path(os.environ.get("JUDGMENT_LOOP_HOME") or Path.home() / ".judgment-loop") / "career_master")
CHUNKS = BASE / "raw" / "chatgpt_recovered"
EXPORT = BASE / "raw" / "chatgpt_export"
IDX = BASE / "07_retrieval_index_and_replay"
DB = IDX / "chat_index.sqlite"
CKPT = BASE / "checkpoints"

BEGIN = re.compile(rb"\n?\n?===== BEGIN: (.+?) =====\n")
END = re.compile(rb"\n===== END: (.+?) \(complete=(True|False)\) =====\n?")
JST = dt.timezone(dt.timedelta(hours=9))


def chunk_files() -> list[Path]:
    return sorted(CHUNKS.glob("recovered_*.txt"))


def cmd_reassemble(a) -> None:
    """全チャンクを順に連結した1本のバイト列を、BEGIN/END 目印で元ファイルに切り分ける。"""
    EXPORT.mkdir(parents=True, exist_ok=True)
    CKPT.mkdir(parents=True, exist_ok=True)
    files = chunk_files()
    nums = [int(p.stem.split("_")[1]) for p in files]
    missing = sorted(set(range(1, max(nums) + 1)) - set(nums)) if nums else []
    if missing and not a.allow_missing:
        sys.exit(f"チャンクが欠けています: {missing[:20]}…（--allow-missing で続行）")
    report = {"chunks": [], "files": [], "missing_chunks": missing, "orphans": []}
    cur_name, cur_fh, cur_bytes, cur_sha = None, None, 0, None
    carry = b""
    global_off = 0   # 連結ストリーム上の位置
    spans = []       # (元ファイル名, 元ファイル内オフセット, チャンク番号, チャンク内オフセット, 長さ)

    def write(data: bytes, chunk_no: int, chunk_off: int):
        nonlocal cur_bytes
        if not data:
            return
        if cur_fh is None:
            report["orphans"].append({"chunk": chunk_no, "offset": chunk_off, "bytes": len(data)})
            return
        spans.append((cur_name, cur_bytes, chunk_no, chunk_off, len(data)))
        cur_fh.write(data)
        cur_sha.update(data)
        cur_bytes += len(data)

    for p in files:
        no = int(p.stem.split("_")[1])
        raw = p.read_bytes()
        report["chunks"].append({"chunk": no, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
        data = carry + raw
        base_off = -len(carry)      # data[0] のチャンク内オフセット（carry 分は前チャンク）
        pos = 0
        keep = 200                  # 目印がチャンク境界で割れる場合に備え、末尾を持ち越す
        limit = len(data) - keep if p != files[-1] else len(data)
        while True:
            mb = BEGIN.search(data, pos)
            me = END.search(data, pos)
            cands = [m for m in (mb, me) if m and m.start() < limit]
            if not cands:
                break
            m = min(cands, key=lambda x: x.start())
            write(data[pos:m.start()], no, base_off + pos)
            if m.re is BEGIN:
                name = m.group(1).decode("utf-8", "replace")
                safe = re.sub(r"[^A-Za-z0-9._\-]", "_", name)
                if cur_fh:
                    cur_fh.close()
                    report["files"].append({"name": cur_name, "bytes": cur_bytes, "sha256": cur_sha.hexdigest(),
                                            "complete": None, "note": "END 目印なしで次の BEGIN"})
                cur_name, cur_bytes, cur_sha = name, 0, hashlib.sha256()
                cur_fh = open(EXPORT / safe, "wb")
            else:
                name = m.group(1).decode("utf-8", "replace")
                if cur_fh:
                    cur_fh.close()
                    report["files"].append({"name": cur_name, "bytes": cur_bytes, "sha256": cur_sha.hexdigest(),
                                            "complete": m.group(2) == b"True", "end_name_matches": name == cur_name})
                cur_name, cur_fh = None, None
            pos = m.end()
        if p != files[-1]:
            cut = max(pos, limit)          # 目印の終わりが持ち越し域に入った場合は、その後ろから持ち越す
            write(data[pos:cut], no, base_off + pos)
            carry = data[cut:]
        else:
            write(data[pos:], no, base_off + pos)
            carry = b""
        global_off += len(raw)
    if cur_fh:
        cur_fh.close()
        report["files"].append({"name": cur_name, "bytes": cur_bytes, "sha256": cur_sha.hexdigest(),
                                "complete": None, "note": "最後まで END 目印なし"})
    IDX.mkdir(parents=True, exist_ok=True)
    with open(IDX / "chunk_spans.tsv", "w", encoding="utf-8") as f:
        f.write("file\tfile_offset\tchunk\tchunk_offset\tlength\n")
        for s in spans:
            f.write("\t".join(map(str, s)) + "\n")
    (CKPT / "reassemble_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"chunks": len(files), "missing": missing, "files": report["files"],
                      "orphan_segments": len(report["orphans"])}, ensure_ascii=False, indent=1))


def _text_of(content) -> tuple[str, str]:
    if not isinstance(content, dict):
        return "", "none"
    ct = content.get("content_type", "")
    parts = content.get("parts")
    out = []
    if isinstance(parts, list):
        for p in parts:
            if isinstance(p, str):
                out.append(p)
            elif isinstance(p, dict):
                t = p.get("text") or p.get("content_type") or ""
                out.append(f"[{p.get('content_type', 'part')}] {t}" if not p.get("text") else p["text"])
    for k in ("text", "result", "user_instructions", "user_profile"):
        if isinstance(content.get(k), str):
            out.append(content[k])
    return "\n".join(x for x in out if x), ct


def _iso(ts) -> str | None:
    try:
        return dt.datetime.fromtimestamp(float(ts), JST).isoformat(timespec="seconds")
    except Exception:
        return None


def cmd_build(a) -> None:
    IDX.mkdir(parents=True, exist_ok=True)
    if DB.exists():
        DB.unlink()
    db = sqlite3.connect(DB)
    db.executescript("""
    create table conversations(conv_id text primary key, title text, create_time text, update_time text,
        source_file text, source_offset integer, n_messages integer, n_user integer, model text);
    create table messages(id integer primary key, conv_id text, msg_id text, parent text, role text, author_name text,
        create_time text, content_type text, text text, on_current_path integer, chars integer, source_file text);
    create index m_conv on messages(conv_id); create index m_role on messages(role); create index m_time on messages(create_time);
    create virtual table fts using fts5(text, content='messages', content_rowid='id', tokenize='trigram');
    create table build_log(source_file text, bytes integer, sha256 text, conversations integer, messages integer, status text, note text);
    """)
    seen = set()
    for f in sorted(EXPORT.glob("conversations-*.json")):
        raw = f.read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            db.execute("insert into build_log values(?,?,?,?,?,?,?)", (f.name, len(raw), sha, 0, 0, "parse_failed", str(e)[:300]))
            db.commit()
            print(f.name, "PARSE FAILED", str(e)[:200])
            continue
        nconv = nmsg = dup = 0
        # 会話ごとの元ファイル内位置（原文へ戻るため）: "conversation_id" の出現位置を順に対応させる
        offs = [m.start() for m in re.finditer(rb'"mapping"', raw)]
        for ci, conv in enumerate(data):
            cid = conv.get("conversation_id") or conv.get("id") or f"{f.name}#{ci}"
            if cid in seen:
                dup += 1
                continue
            seen.add(cid)
            mapping = conv.get("mapping") or {}
            path = set()
            node = conv.get("current_node")
            while node and node in mapping and node not in path:
                path.add(node)
                node = mapping[node].get("parent")
            rows, nuser, model = [], 0, None
            for mid, nd in mapping.items():
                msg = nd.get("message")
                if not msg:
                    continue
                role = (msg.get("author") or {}).get("role", "")
                text, ct = _text_of(msg.get("content"))
                if not text.strip():
                    continue
                md = msg.get("metadata") or {}
                model = model or md.get("model_slug")
                if role == "user":
                    nuser += 1
                rows.append((cid, mid, nd.get("parent"), role, (msg.get("author") or {}).get("name"),
                             _iso(msg.get("create_time")), ct, text, 1 if mid in path else 0, len(text), f.name))
            rows.sort(key=lambda r: r[5] or "")
            db.executemany("insert into messages(conv_id,msg_id,parent,role,author_name,create_time,content_type,text,"
                           "on_current_path,chars,source_file) values(?,?,?,?,?,?,?,?,?,?,?)", rows)
            db.execute("insert into conversations values(?,?,?,?,?,?,?,?,?)",
                       (cid, conv.get("title"), _iso(conv.get("create_time")), _iso(conv.get("update_time")), f.name,
                        offs[ci] if ci < len(offs) else None, len(rows), nuser, model))
            nconv += 1
            nmsg += len(rows)
        db.execute("insert into build_log values(?,?,?,?,?,?,?)",
                   (f.name, len(raw), sha, nconv, nmsg, "ok", f"duplicates_skipped={dup}"))
        db.commit()
        print(f.name, "conversations", nconv, "messages", nmsg, "dup", dup)
    db.execute("insert into fts(fts) values('rebuild')")
    db.commit()
    for other in sorted(EXPORT.iterdir()):
        if not other.name.startswith("conversations-"):
            h = hashlib.sha256()
            with open(other, "rb") as fh:
                for blk in iter(lambda: fh.read(1 << 20), b""):
                    h.update(blk)
            db.execute("insert into build_log values(?,?,?,?,?,?,?)",
                       (other.name, other.stat().st_size, h.hexdigest(), 0, 0, "not_indexed",
                        "chat.html は conversations-*.json と同じ会話の別表現。その他は会話本文ではない"))
    db.commit()
    cmd_stats(a)


def cmd_stats(a) -> None:
    db = sqlite3.connect(DB)
    q = lambda s: db.execute(s).fetchall()
    print(json.dumps({
        "conversations": q("select count(*) from conversations")[0][0],
        "messages": q("select count(*) from messages")[0][0],
        "by_role": dict(q("select role,count(*) from messages group by role")),
        "user_chars": q("select sum(chars) from messages where role='user'")[0][0],
        "period": q("select min(create_time),max(create_time) from conversations")[0],
        "build_log": q("select source_file,bytes,conversations,messages,status,note from build_log"),
    }, ensure_ascii=False, indent=1))


def _like_terms(terms):
    return " and ".join("m.text like ?" for _ in terms), [f"%{t}%" for t in terms]


def cmd_search(a) -> None:
    db = sqlite3.connect(DB)
    long_terms = [t for t in a.terms if len(t) >= 3]
    where, params = [], []
    if long_terms:
        where.append("m.id in (select rowid from fts where fts match ?)")
        params.append(" AND ".join('"' + t.replace('"', '""') + '"' for t in long_terms))
    for t in a.terms:
        if len(t) < 3:           # trigram は3文字未満を引けないので LIKE で補う
            where.append("m.text like ?")
            params.append(f"%{t}%")
    if a.role:
        where.append("m.role=?")
        params.append(a.role)
    if a.since:
        where.append("m.create_time>=?")
        params.append(a.since)
    if a.until:
        where.append("m.create_time<=?")
        params.append(a.until)
    sql = ("select m.id,m.conv_id,m.msg_id,m.role,m.create_time,c.title,m.chars,m.text from messages m "
           "join conversations c on c.conv_id=m.conv_id where " + " and ".join(where or ["1"]) +
           " order by m.create_time limit ?")
    rows = db.execute(sql, params + [a.limit]).fetchall()
    if a.count:
        n = db.execute("select count(*) from messages m where " + " and ".join(where or ["1"]), params).fetchone()[0]
        print(json.dumps({"terms": a.terms, "role": a.role, "matches": n}, ensure_ascii=False))
        return
    for rid, cid, mid, role, ts, title, chars, text in rows:
        t = text
        if a.width and len(t) > a.width:
            i = min([t.find(x) for x in a.terms if t.find(x) >= 0] or [0])
            s = max(0, i - a.width // 3)
            t = ("…" if s else "") + t[s:s + a.width] + "…"
        print(f"--- [{rid}] {ts} {role} | {title} | conv={cid} msg={mid} ({chars}字)\n{t}\n")
    print(f"({len(rows)} 件表示)")


def cmd_show(a) -> None:
    db = sqlite3.connect(DB)
    rows = db.execute("select id,msg_id,role,create_time,text from messages where conv_id=? and on_current_path=1 "
                      "order by create_time", (a.conv_id,)).fetchall()
    if a.around:
        i = next((k for k, r in enumerate(rows) if r[1] == a.around or str(r[0]) == a.around), 0)
        rows = rows[max(0, i - a.n):i + a.n + 1]
    c = db.execute("select title,create_time,source_file,source_offset from conversations where conv_id=?", (a.conv_id,)).fetchone()
    print(f"# {c[0]} | {c[1]} | 元: {c[2]} @byte {c[3]}")
    for rid, mid, role, ts, text in rows:
        print(f"\n[{rid}] {ts} {role} (msg={mid})\n{text if not a.width else text[:a.width]}")


def main() -> None:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    x = sub.add_parser("reassemble"); x.add_argument("--allow-missing", action="store_true"); x.set_defaults(fn=cmd_reassemble)
    x = sub.add_parser("build"); x.set_defaults(fn=cmd_build)
    x = sub.add_parser("stats"); x.set_defaults(fn=cmd_stats)
    x = sub.add_parser("search"); x.add_argument("terms", nargs="+"); x.add_argument("--role"); x.add_argument("--since")
    x.add_argument("--until"); x.add_argument("--limit", type=int, default=30); x.add_argument("--width", type=int, default=400)
    x.add_argument("--count", action="store_true"); x.set_defaults(fn=cmd_search)
    x = sub.add_parser("show"); x.add_argument("conv_id"); x.add_argument("--around"); x.add_argument("--n", type=int, default=6)
    x.add_argument("--width", type=int, default=0); x.set_defaults(fn=cmd_show)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
