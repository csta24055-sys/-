"""Project store of WLC Studio: field values with their full history, candidates, documents, research log.

A separate SQLite file from the engine store of 12_APP_BASE (lcaapp.store), which keeps the converted
input versions and the runs. Rules:
  * values are append-only: every save adds a row, the current value is the best one (provenance.best)
    among the latest row of each kind; a later save never erases what came before;
  * candidates (from PLATEAU, documents, estimators) are kept apart and become a value only by accept();
  * delete_project() removes the project, its values, candidates, documents (including the stored copy of
    an uploaded file) and its research log; the engine store keeps its input versions and runs, which hold
    no uploaded file and no address (see bridge.py).
The connection is used from one thread only (the server is single-threaded).
"""
from __future__ import annotations

import hashlib
import json
import re
import math
import os
import sqlite3
import time
from pathlib import Path

from . import fields as FL
from .numbers import parse_number  # noqa: F401  (re-exported: the server imports it from here)
from .provenance import HAS_VALUE, PRIORITY, ProvenanceError, Uncertainty, Value, competes

SCHEMA_VERSION = 1
SCHEMA = """
CREATE TABLE IF NOT EXISTS app_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS projects (
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, structure TEXT NOT NULL, data_kind TEXT NOT NULL DEFAULT 'user',
  created_at REAL NOT NULL, updated_at REAL NOT NULL, lca_project_id INTEGER, last_period REAL,
  location_json TEXT);
CREATE TABLE IF NOT EXISTS field_values (
  id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  field_id TEXT NOT NULL, payload TEXT NOT NULL, created_at REAL NOT NULL);
CREATE INDEX IF NOT EXISTS fv_pf ON field_values(project_id, field_id);
CREATE TABLE IF NOT EXISTS candidates (
  id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  field_id TEXT NOT NULL, payload TEXT NOT NULL, origin TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'open',
  created_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS later_flags (project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  field_id TEXT NOT NULL, PRIMARY KEY (project_id, field_id));
CREATE TABLE IF NOT EXISTS documents (
  id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  name TEXT NOT NULL, kind TEXT NOT NULL, sha256 TEXT NOT NULL, size INTEGER NOT NULL, stored_path TEXT,
  summary TEXT NOT NULL, created_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS research_log (
  id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  kind TEXT NOT NULL, payload TEXT NOT NULL, created_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS runs (
  id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  lca_run_id INTEGER, input_hash TEXT, period REAL, status TEXT NOT NULL, payload TEXT NOT NULL, created_at REAL NOT NULL);
"""


EVIDENCE_KEYS = ("rows", "n_rows", "excluded", "n_excluded", "n_maybe")   # shown with a candidate, never part of a value

class ProjectError(ValueError):
    pass


def _j(x) -> str:
    return json.dumps(x, ensure_ascii=False, sort_keys=True, allow_nan=False)


class Projects:
    def __init__(self, path: str | Path, upload_dir: str | Path | None = None, keep_uploads: bool = False):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys = ON")
        self.db.execute("PRAGMA secure_delete = ON")       # a deleted project is overwritten, not left in free pages
        self.db.executescript(SCHEMA)
        row = self.db.execute("SELECT value FROM app_meta WHERE key='schema_version'").fetchone()
        if row is None:
            self.db.execute("INSERT INTO app_meta VALUES ('schema_version', ?)", (str(SCHEMA_VERSION),))
            self.db.commit()
        elif int(row[0]) != SCHEMA_VERSION:
            self.db.close()
            raise ProjectError("保存ファイルの形式の版 %s はこの版（%d）と違う" % (row[0], SCHEMA_VERSION))
        self.upload_dir = Path(upload_dir) if upload_dir else None
        self.keep_uploads = keep_uploads

    def close(self):
        self.db.close()

    # ------------------------------------------------------------------ projects
    def create(self, name: str, structure: str, data_kind: str = "user") -> int:
        if structure not in {s["id"] for s in FL.STRUCTURES}:
            raise ProjectError("構造 %r は選べない" % structure)
        if data_kind not in ("user", "fictional_demo"):
            raise ProjectError("data_kind が不正")
        now = time.time()
        name = (name or "").strip()[:80] or "新しい建物"
        cur = self.db.execute("INSERT INTO projects (name, structure, data_kind, created_at, updated_at) VALUES (?,?,?,?,?)",
                              (name, structure, data_kind, now, now))
        pid = cur.lastrowid
        self.db.commit()
        label = next(s["label"] for s in FL.STRUCTURES if s["id"] == structure)
        self.put(pid, Value("b_structure", "confirmed", structure, method="structure_card",
                            note="構造の選択画面で選んだ（%s）" % label))
        # The evaluation boundary must be explicit; it starts as an assumption the user can change.
        self.put(pid, Value("a_stages", "assumption", "ALL", method="initial_setting",
                            note="初期設定：全段階。評価の目的に合わせて変える。"))
        return pid

    def get(self, pid: int) -> dict:
        r = self.db.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
        if r is None:
            raise ProjectError("プロジェクト %s は無い" % pid)
        return dict(r)

    def list(self) -> list[dict]:
        return [dict(r) for r in self.db.execute("SELECT * FROM projects ORDER BY updated_at DESC")]

    def touch(self, pid: int, **cols) -> None:
        cols["updated_at"] = time.time()
        allowed = {"name", "structure", "lca_project_id", "last_period", "location_json", "updated_at"}
        if set(cols) - allowed:
            raise ProjectError("列 %s は更新できない" % (set(cols) - allowed))
        self.db.execute("UPDATE projects SET %s WHERE id=?" % ", ".join("%s=?" % k for k in cols), (*cols.values(), pid))
        self.db.commit()

    def delete(self, pid: int) -> dict:
        self.get(pid)
        files = [r[0] for r in self.db.execute("SELECT stored_path FROM documents WHERE project_id=? AND stored_path IS NOT NULL", (pid,))]
        removed = 0
        for f in files:
            try:
                os.remove(f)
                removed += 1
            except FileNotFoundError:
                pass
        counts = {t: self.db.execute("SELECT COUNT(*) FROM %s WHERE project_id=?" % t, (pid,)).fetchone()[0]
                  for t in ("field_values", "candidates", "documents", "research_log", "runs")}
        self.db.execute("DELETE FROM projects WHERE id=?", (pid,))
        self.db.commit()
        return {"deleted_project": pid, "deleted_rows": counts, "deleted_files": removed}

    # ------------------------------------------------------------------ values
    def put(self, pid: int, v: Value) -> Value:
        if v.field_id not in FL.FIELDS:
            raise ProjectError("項目 %r は無い" % v.field_id)
        F = FL.FIELDS[v.field_id]
        v = _normalise(F, v)
        v.check()
        self.get(pid)
        self.db.execute("INSERT INTO field_values (project_id, field_id, payload, created_at) VALUES (?,?,?,?)",
                        (pid, v.field_id, _j(v.to_json()), time.time()))
        self.db.execute("UPDATE projects SET updated_at=? WHERE id=?", (time.time(), pid))
        self.db.commit()
        return v

    def history(self, pid: int, fid: str) -> list[Value]:
        return [Value.from_json(json.loads(r[0])) for r in
                self.db.execute("SELECT payload FROM field_values WHERE project_id=? AND field_id=? ORDER BY id", (pid, fid))]

    def current(self, pid: int, fid: str) -> Value | None:
        """The value in force: the latest save. (A save by the user replaces earlier ones, whatever their state;
        the history keeps them. provenance.best is used only to rank candidates.)"""
        r = self.db.execute("SELECT payload FROM field_values WHERE project_id=? AND field_id=? ORDER BY id DESC LIMIT 1",
                            (pid, fid)).fetchone()
        return Value.from_json(json.loads(r[0])) if r else None

    def values(self, pid: int) -> dict[str, Value]:
        """The value in force of every field that has one (its latest save, as current()), in the order in which the
        fields were first saved. Only those rows are read and decoded: the earlier saves are only scanned in the index
        (project_id, field_id) for their ids, so a save or an adoption that reads the values does not decode the whole
        history."""
        out = {}
        for r in self.db.execute("SELECT v.field_id, v.payload FROM field_values v JOIN "
                                 "(SELECT MIN(id) AS first, MAX(id) AS last FROM field_values WHERE project_id=? "
                                 "GROUP BY field_id) g ON v.id = g.last ORDER BY g.first", (pid,)):
            out[r[0]] = Value.from_json(json.loads(r[1]))
        return out

    def validate(self, v: Value) -> Value:
        """The checks of put()/propose() without storing (raises ProjectError / ProvenanceError)."""
        F = FL.FIELDS.get(v.field_id)
        if F is None:
            raise ProjectError("項目 %r は無い" % v.field_id)
        v = _normalise(F, v)
        v.check()
        return v

    # ------------------------------------------------------------------ candidates
    def propose(self, pid: int, v: Value, origin: str, extra: dict | None = None) -> int:
        """Store a candidate. `extra` is shown with it and dropped when it is accepted (a document's candidate carries
        the rows it added and the rows of the same material it did not add: {rows, n_rows, excluded, n_excluded,
        n_maybe})."""
        F = FL.FIELDS.get(v.field_id)
        if F is None:
            raise ProjectError("項目 %r は無い" % v.field_id)
        v = _normalise(F, v)
        v.check()
        # A candidate is never in force: it becomes a value only through accept(). Its state is the state the
        # value will have once accepted (e.g. a PLATEAU attribute: confirmed; a GFA estimate: assumption).
        # the same proposal twice is not stored twice
        for c in self.candidates(pid, v.field_id):
            same_premises = (c.get("depends") or {}) == (v.depends or {})
            if c["value"] == v.value and c["unit"] == v.unit and c["method"] == v.method and c["state"] == v.state and same_premises:
                return c["id"]
            if c["method"] == v.method and (v.depends or c.get("depends")) and not same_premises:
                # an estimate of the same method on other premises (floor area, structure, use changed): the old one is
                # out of date, whatever its number, and must not stay next to the new one as if both were valid
                self.db.execute("UPDATE candidates SET status='dismissed' WHERE id=?", (c["id"],))
        payload = v.to_json()
        for k, x in (extra or {}).items():
            if k in EVIDENCE_KEYS:
                payload[k] = x
        cur = self.db.execute("INSERT INTO candidates (project_id, field_id, payload, origin, created_at) VALUES (?,?,?,?,?)",
                              (pid, v.field_id, _j(payload), origin, time.time()))
        self.db.commit()
        return cur.lastrowid

    def candidates(self, pid: int, fid: str | None = None) -> list[dict]:
        q = "SELECT id, field_id, payload, origin FROM candidates WHERE project_id=? AND status='open'"
        args = [pid]
        if fid:
            q += " AND field_id=?"
            args.append(fid)
        out = []
        for r in self.db.execute(q + " ORDER BY id", args):
            d = json.loads(r[2])
            d.update(id=r[0], origin=r[3])
            if d.get("method") == "plateau_roof_x_storeys" and (d.get("uncertainty") or {}).get("kind", "none") == "none":
                # candidates stored before the uncertainty rule: the range is unknown and the dataset version was not kept
                d["uncertainty"] = {"kind": "unknown", "low": None, "high": None, "level": None, "calibrated": False,
                                    "basis": "範囲を示す資料が無い"}
                d["factor_version"] = d.get("factor_version") or "PLATEAU（版の記録の無い古い候補）"
            out.append(d)
        # strongest evidence first; among equals the newest first
        out.sort(key=lambda d: (-PRIORITY[d["state"]], -d["id"]))
        return out

    def accept(self, pid: int, fid: str, index: int = 0, cid: int | None = None) -> Value:
        cs = self.candidates(pid, fid)
        if cid is not None:
            hit = [c for c in cs if c["id"] == cid]
            if not hit:
                raise ProjectError("その候補はもう無い（採用済みか、取り下げられた）")
            c = dict(hit[0])
        elif not 0 <= index < len(cs):
            raise ProjectError("候補 %s は無い" % index)
        else:
            c = dict(cs[index])
        cid = c.pop("id")
        origin = c.pop("origin")
        for k in EVIDENCE_KEYS:
            c.pop(k, None)
        other = {("m_concrete", "whole_building"): "m_concrete_fdn", ("m_rebar", "all_steel"): "m_steel",
                 ("m_steel", "all_steel"): "m_rebar"}.get((fid, c.get("scope") or ""))
        if other and competes(self.current(pid, other)):
            # adopting it would make the bridge drop the value typed in the other field (or count it twice)
            raise ProjectError("「%s」に値があるので、それを含む全体量の候補は採用しない（二重計上を防ぐ）。全体量を使うときは、先に「%s」を"
                               "「未取得に戻す」か適用外にする" % (FL.FIELDS[other]["label"], FL.FIELDS[other]["label"]))
        v = Value.from_json(c)
        v.updated_at = time.time()
        v.updated_by = "user (候補を採用: %s)" % origin
        v = self.put(pid, v)
        self.db.execute("UPDATE candidates SET status='accepted' WHERE id=?", (cid,))
        self.db.commit()
        if fid in ("m_concrete_fdn", "m_rebar", "m_steel"):
            self.withdraw_whole_candidates(pid)
        return v

    def dismiss_candidates(self, pid: int, fid: str, origin: str | None = None) -> int:
        q, args = "UPDATE candidates SET status='dismissed' WHERE project_id=? AND field_id=? AND status='open'", [pid, fid]
        if origin:
            q += " AND origin=?"
            args.append(origin)
        n = self.db.execute(q, args).rowcount
        self.db.commit()
        return n

    def withdraw_whole_candidates(self, pid: int) -> list[str]:
        """Open whole-building / all-steel candidates whose other field now has a value: adopting one would only make the
        bridge drop that other row (or double count if it did not), so they are withdrawn with the estimator's refusal."""
        vals = self.values(pid)
        out = []
        for fid, scope, other in (("m_concrete", "whole_building", "m_concrete_fdn"), ("m_rebar", "all_steel", "m_steel"),
                                  ("m_steel", "all_steel", "m_rebar")):
            if not competes(vals.get(other)):
                continue
            for c in self.candidates(pid, fid):
                if c.get("scope") == scope:
                    self.db.execute("UPDATE candidates SET status='dismissed' WHERE id=? AND project_id=?", (c["id"], pid))
                    out.append(fid)
        self.db.commit()
        return out

    # ------------------------------------------------------------------ flags, documents, log, runs
    def set_later(self, pid: int, fid: str, later: bool) -> None:
        if fid not in FL.FIELDS:
            raise ProjectError("項目 %r は無い" % fid)
        if later:
            self.db.execute("INSERT OR IGNORE INTO later_flags VALUES (?,?)", (pid, fid))
        else:
            self.db.execute("DELETE FROM later_flags WHERE project_id=? AND field_id=?", (pid, fid))
        self.db.commit()

    def later(self, pid: int) -> set[str]:
        return {r[0] for r in self.db.execute("SELECT field_id FROM later_flags WHERE project_id=?", (pid,))}

    def add_document(self, pid: int, name: str, kind: str, data: bytes, summary: dict) -> int:
        sha = hashlib.sha256(data).hexdigest()
        stored = None
        if self.keep_uploads and self.upload_dir:
            # Data minimisation: the original file is kept only when the operator asked for it (keep_uploads)
            self.upload_dir.mkdir(parents=True, exist_ok=True)
            stored = str(self.upload_dir / ("%d-%s" % (pid, sha[:16])))
            Path(stored).write_bytes(data)
            os.chmod(stored, 0o600)
        cur = self.db.execute("INSERT INTO documents (project_id, name, kind, sha256, size, stored_path, summary, created_at)"
                              " VALUES (?,?,?,?,?,?,?,?)", (pid, name[:200], kind, sha, len(data), stored, _j(summary), time.time()))
        self.db.commit()
        return cur.lastrowid

    def documents(self, pid: int) -> list[dict]:
        out = []
        for r in self.db.execute("SELECT id, name, kind, sha256, size, stored_path IS NOT NULL AS kept, summary, created_at"
                                 " FROM documents WHERE project_id=? ORDER BY id", (pid,)):
            d = dict(r)
            d["summary"] = json.loads(d["summary"])
            out.append(d)
        return out

    def log(self, pid: int, kind: str, payload: dict) -> None:
        self.db.execute("INSERT INTO research_log (project_id, kind, payload, created_at) VALUES (?,?,?,?)",
                        (pid, kind, _j(payload), time.time()))
        self.db.commit()

    def research(self, pid: int) -> list[dict]:
        return [{"kind": r[0], **json.loads(r[1]), "at": r[2]} for r in
                self.db.execute("SELECT kind, payload, created_at FROM research_log WHERE project_id=? ORDER BY id", (pid,))]

    def save_run(self, pid: int, lca_run_id, input_hash: str, period, status: str, payload: dict) -> int:
        cur = self.db.execute("INSERT INTO runs (project_id, lca_run_id, input_hash, period, status, payload, created_at)"
                              " VALUES (?,?,?,?,?,?,?)", (pid, lca_run_id, input_hash, period, status, _j(payload), time.time()))
        self.db.commit()
        return cur.lastrowid

    def last_run(self, pid: int) -> dict | None:
        r = self.db.execute("SELECT payload FROM runs WHERE project_id=? ORDER BY id DESC LIMIT 1", (pid,)).fetchone()
        return json.loads(r[0]) if r else None

    # ------------------------------------------------------------------ progress
    def progress(self, pid: int) -> dict:
        vals = self.values(pid)
        later = self.later(pid)
        by_state = {k: 0 for k in ("confirmed", "from_drawing", "statistical", "assumption", "not_applicable",
                                   "not_computable", "not_obtained")}
        by_screen = {s["id"]: {"filled": 0, "total": 0} for s in FL.SCREENS}
        filled = 0
        for fid, F in FL.FIELDS.items():
            v = vals.get(fid)
            st = v.state if v else "not_obtained"
            by_state[st] += 1
            by_screen[F["screen"]]["total"] += 1
            done = st in HAS_VALUE or st == "not_applicable"
            if done:
                filled += 1
                by_screen[F["screen"]]["filled"] += 1
        total = len(FL.FIELDS)
        return {"filled": filled, "total": total, "percent": round(100 * filled / total) if total else 0,
                "later": len(later), "by_screen": by_screen, **by_state,
                "note": "入力が埋まった割合であって、精度ではない。"}


def _normalise(F: dict, v: Value) -> Value:
    """Type/unit/range checks of a value against its field (no coercion of a missing value into 0)."""
    if v.state not in HAS_VALUE:
        v.value = None
        return v
    t = F["type"]
    if t in ("number", "integer"):
        try:
            v.value = parse_number(v.value)        # also ints (a huge int is refused, not an OverflowError) and bools
        except ValueError as e:
            raise ProjectError("「%s」は数値で入れる（%s）" % (F["label"], e)) from None
        if t == "integer":
            if abs(v.value - round(v.value)) > 1e-9:
                raise ProjectError("「%s」は整数で入れる" % F["label"])
            v.value = int(round(v.value))
        else:
            v.value = float(v.value)
        unit = v.unit or F.get("unit", "")
        ok_units = F.get("units") or [F.get("unit", "")]
        if unit not in ok_units:
            raise ProjectError("「%s」の単位 %r は使えない（%s）" % (F["label"], unit, "・".join(u or "なし" for u in ok_units)))
        v.unit = unit
        lo, hi = F.get("range", (None, None))
        if lo is not None:
            mass = {"kg": 1.0, "t": 1000.0}
            fu = F.get("unit")
            if unit == fu:
                x = v.value
            elif unit in mass and fu in mass:
                x = v.value * mass[unit] / mass[fu]          # check the range in the field's own unit
            else:
                x = None                                     # another dimension (e.g. t for an m3 field)
            if x is not None and not (lo <= x <= hi):
                raise ProjectError("「%s」の値 %s %s は範囲 %s〜%s %s の外" % (F["label"], v.value, unit, lo, hi, fu))
            if x is None and v.value > 1e9:
                raise ProjectError("「%s」の値 %s %s は大きすぎる" % (F["label"], v.value, unit))
        if v.value < 0:
            raise ProjectError("「%s」に負の値は入れない" % F["label"])
    elif t == "enum":
        allowed = {e for e, _ in F["enum"]}
        if not isinstance(v.value, str) or v.value not in allowed:
            raise ProjectError("「%s」の選択肢 %r は無い" % (F["label"], v.value))
        v.unit = ""
    else:
        if not isinstance(v.value, (str, int, float)) or isinstance(v.value, bool):
            raise ProjectError("「%s」は文字で入れる" % F["label"])
        v.value = str(v.value).strip()[:500]
        v.unit = ""
    return v
