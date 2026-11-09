"""SQLite 永続化層（標準ライブラリ sqlite3 のみ使用）"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

from .paths import default_db_path, resource_root

ROOT = resource_root()
DEFAULT_DB = default_db_path()
KNOWLEDGE = ROOT / "knowledge" / "knowledge.json"
REPORT_DIR = ROOT / "report"

_lock = threading.RLock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
  kind TEXT NOT NULL,
  id TEXT NOT NULL,
  data TEXT NOT NULL,
  user_modified INTEGER NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (kind, id)
);
CREATE TABLE IF NOT EXISTS datasets (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  filename TEXT,
  sheet TEXT,
  study TEXT,
  description TEXT,
  provenance TEXT NOT NULL DEFAULT '利用者インポート',
  columns TEXT NOT NULL,
  rows TEXT NOT NULL,
  n_rows INTEGER NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS report_sections (
  id TEXT PRIMARY KEY,
  ord INTEGER NOT NULL,
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  user_modified INTEGER NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS activity (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  at TEXT NOT NULL,
  action TEXT NOT NULL,
  target TEXT
);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS plans (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  theme_id TEXT,
  data TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS user_state (key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at TEXT NOT NULL);
"""

KIND_KEYS = {
    "source": "sources",
    "finding": "findings",
    "hypothesis": "hypotheses",
    "question": "questions",
    "theme": "themes",
    "study": "studies",
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class DB:
    def __init__(self, path: str | os.PathLike | None = None):
        self.path = Path(path or os.environ.get("AQROS_DB", DEFAULT_DB))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.executescript(SCHEMA)
        self.seed()

    @property
    def conn(self) -> sqlite3.Connection:
        """スレッドごとの接続（FastAPI の同期エンドポイントはスレッドプールで並行実行されるため）"""
        c = getattr(self._local, "conn", None)
        if c is None:
            c = sqlite3.connect(self.path, timeout=30)
            c.row_factory = sqlite3.Row
            c.execute("PRAGMA busy_timeout=30000")
            self._local.conn = c
        return c

    # ------------------------------------------------------------------ seed
    def seed(self) -> None:
        """knowledge.json と report/*.md を取り込む。利用者が編集した項目は上書きしない。"""
        k = json.loads(KNOWLEDGE.read_text(encoding="utf-8"))
        with _lock, self.conn:
            for kind, key in KIND_KEYS.items():
                for item in k[key]:
                    row = self.conn.execute("SELECT user_modified FROM items WHERE kind=? AND id=?", (kind, item["id"])).fetchone()
                    if row is None:
                        self.conn.execute("INSERT INTO items VALUES (?,?,?,0,?)", (kind, item["id"], json.dumps(item, ensure_ascii=False), now()))
                    elif not row["user_modified"]:
                        self.conn.execute("UPDATE items SET data=? WHERE kind=? AND id=?", (json.dumps(item, ensure_ascii=False), kind, item["id"]))
            for key in ("roadmap", "models", "graph", "external", "meta", "validation", "literature", "completeness"):
                self.conn.execute("INSERT OR REPLACE INTO meta VALUES (?,?)", (key, json.dumps(k.get(key), ensure_ascii=False)))
            for i, f in enumerate(sorted(REPORT_DIR.glob("*.md"))):
                sid = f.stem
                body = f.read_text(encoding="utf-8")
                title = body.splitlines()[0].lstrip("# ").strip() if body else sid
                row = self.conn.execute("SELECT user_modified FROM report_sections WHERE id=?", (sid,)).fetchone()
                if row is None:
                    self.conn.execute("INSERT INTO report_sections VALUES (?,?,?,?,0,?)", (sid, i, title, body, now()))
                elif not row["user_modified"]:
                    self.conn.execute("UPDATE report_sections SET ord=?, title=?, body=? WHERE id=?", (i, title, body, sid))

    # ----------------------------------------------------------------- items
    def list_items(self, kind: str) -> list[dict]:
        rows = self.conn.execute("SELECT data, user_modified, updated_at FROM items WHERE kind=? ORDER BY id", (kind,)).fetchall()
        out = []
        for r in rows:
            d = json.loads(r["data"])
            d["_user_modified"] = bool(r["user_modified"])
            d["_updated_at"] = r["updated_at"]
            out.append(d)
        return out

    def get_item(self, kind: str, id: str) -> dict | None:
        r = self.conn.execute("SELECT data FROM items WHERE kind=? AND id=?", (kind, id)).fetchone()
        return json.loads(r["data"]) if r else None

    def upsert_item(self, kind: str, item: dict, user: bool = True) -> dict:
        item = {k: v for k, v in item.items() if not k.startswith("_")}
        with _lock, self.conn:
            self.conn.execute(
                "INSERT INTO items VALUES (?,?,?,?,?) ON CONFLICT(kind,id) DO UPDATE SET data=excluded.data, user_modified=excluded.user_modified, updated_at=excluded.updated_at",
                (kind, item["id"], json.dumps(item, ensure_ascii=False), int(user), now()),
            )
            self.log(f"update:{kind}", item["id"])
        return item

    def patch_item(self, kind: str, id: str, patch: dict) -> dict | None:
        cur = self.get_item(kind, id)
        if cur is None:
            return None
        cur.update({k: v for k, v in patch.items() if v is not None})
        return self.upsert_item(kind, cur)

    def meta(self, key: str):
        r = self.conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return json.loads(r["value"]) if r else None

    # -------------------------------------------------------------- datasets
    def add_dataset(self, name, filename, sheet, columns, rows, study=None, description=None, provenance="利用者インポート") -> int:
        with _lock, self.conn:
            cur = self.conn.execute(
                "INSERT INTO datasets (name, filename, sheet, study, description, provenance, columns, rows, n_rows, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (name, filename, sheet, study, description, provenance, json.dumps(columns, ensure_ascii=False),
                 json.dumps(rows, ensure_ascii=False), len(rows), now()),
            )
            self.log("dataset:add", name)
            return int(cur.lastrowid)

    def list_datasets(self) -> list[dict]:
        rows = self.conn.execute("SELECT id, name, filename, sheet, study, description, provenance, columns, n_rows, created_at FROM datasets ORDER BY id DESC").fetchall()
        return [{**dict(r), "columns": json.loads(r["columns"])} for r in rows]

    def get_dataset(self, id: int) -> dict | None:
        r = self.conn.execute("SELECT * FROM datasets WHERE id=?", (id,)).fetchone()
        if not r:
            return None
        d = dict(r)
        d["columns"] = json.loads(d["columns"])
        d["rows"] = json.loads(d["rows"])
        return d

    def delete_dataset(self, id: int) -> bool:
        with _lock, self.conn:
            n = self.conn.execute("DELETE FROM datasets WHERE id=?", (id,)).rowcount
            self.log("dataset:delete", str(id))
        return n > 0

    # ---------------------------------------------------------------- report
    def report_sections(self) -> list[dict]:
        return [dict(r) for r in self.conn.execute("SELECT * FROM report_sections ORDER BY ord").fetchall()]

    def save_section(self, id: str, body: str, title: str | None = None) -> dict | None:
        with _lock, self.conn:
            r = self.conn.execute("SELECT * FROM report_sections WHERE id=?", (id,)).fetchone()
            if r is None:
                ord_ = (self.conn.execute("SELECT COALESCE(MAX(ord),0)+1 FROM report_sections").fetchone()[0])
                self.conn.execute("INSERT INTO report_sections VALUES (?,?,?,?,1,?)", (id, ord_, title or id, body, now()))
            else:
                self.conn.execute("UPDATE report_sections SET body=?, title=COALESCE(?, title), user_modified=1, updated_at=? WHERE id=?", (body, title, now(), id))
            self.log("report:save", id)
        r = self.conn.execute("SELECT * FROM report_sections WHERE id=?", (id,)).fetchone()
        return dict(r) if r else None

    def reset_section(self, id: str) -> None:
        with _lock, self.conn:
            self.conn.execute("UPDATE report_sections SET user_modified=0 WHERE id=?", (id,))
        self.seed()

    # -------------------------------------------------------------- activity
    # ----------------------------------------------------------------- plans
    def list_plans(self) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM plans ORDER BY updated_at DESC").fetchall()
        return [{"id": r["id"], "title": r["title"], "theme_id": r["theme_id"], **json.loads(r["data"]), "created_at": r["created_at"], "updated_at": r["updated_at"]} for r in rows]

    def save_plan(self, plan: dict, pid: int | None = None) -> dict:
        data = {k: v for k, v in plan.items() if k not in ("id", "title", "theme_id", "created_at", "updated_at")}
        with _lock, self.conn:
            if pid is None:
                cur = self.conn.execute("INSERT INTO plans (title, theme_id, data, created_at, updated_at) VALUES (?,?,?,?,?)",
                                        (plan["title"], plan.get("theme_id"), json.dumps(data, ensure_ascii=False), now(), now()))
                pid = cur.lastrowid
            else:
                if not self.conn.execute("SELECT 1 FROM plans WHERE id=?", (pid,)).fetchone():
                    raise KeyError(pid)
                self.conn.execute("UPDATE plans SET title=?, theme_id=?, data=?, updated_at=? WHERE id=?",
                                  (plan["title"], plan.get("theme_id"), json.dumps(data, ensure_ascii=False), now(), pid))
            self.log("研究計画を保存", plan["title"])
        return next(p for p in self.list_plans() if p["id"] == pid)

    def delete_plan(self, pid: int) -> bool:
        with _lock, self.conn:
            n = self.conn.execute("DELETE FROM plans WHERE id=?", (pid,)).rowcount
        return n > 0

    # ------------------------------------------------------------ user state
    def get_state(self, key: str):
        r = self.conn.execute("SELECT value FROM user_state WHERE key=?", (key,)).fetchone()
        return json.loads(r["value"]) if r else None

    def set_state(self, key: str, value) -> None:
        with _lock, self.conn:
            self.conn.execute("INSERT OR REPLACE INTO user_state VALUES (?,?,?)", (key, json.dumps(value, ensure_ascii=False), now()))

    def log(self, action: str, target: str | None = None) -> None:
        self.conn.execute("INSERT INTO activity (at, action, target) VALUES (?,?,?)", (now(), action, target))

    def recent_activity(self, n: int = 10) -> list[dict]:
        return [dict(r) for r in self.conn.execute("SELECT * FROM activity ORDER BY id DESC LIMIT ?", (n,)).fetchall()]
