"""Storage (SQLite, standard library only): projects, inputs, conditions, results, reference data.

One file holds everything. Every save of an input makes a new version, so an earlier input
and the results computed from it stay readable. Results are stored as computed, together
with the versions of the calculation code and of the data that produced them.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import math
import os
import sqlite3
import zlib
from typing import Any

from . import DATA_KINDS, refdata

SCHEMA_VERSION = 1

_SCHEMA = """
CREATE TABLE app_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);

CREATE TABLE reference_sets (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL, version TEXT NOT NULL,
    data_kind TEXT NOT NULL CHECK (data_kind IN ('fictional', 'licensed')),
    licence_status TEXT NOT NULL, source_note TEXT NOT NULL,
    sha256 TEXT NOT NULL, created_at TEXT NOT NULL,
    UNIQUE (name, version)
);
CREATE TABLE reference_items (
    set_id INTEGER NOT NULL REFERENCES reference_sets(id) ON DELETE CASCADE,
    kind TEXT NOT NULL,            -- gases / gwp / unit_conversions / factors / price_index / standard_values
    key TEXT NOT NULL,
    seq INTEGER NOT NULL,          -- position in the set as registered (the order is part of the data)
    payload TEXT NOT NULL,         -- JSON
    PRIMARY KEY (set_id, kind, key)
);

CREATE TABLE projects (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    data_kind TEXT NOT NULL,       -- fictional / real / unknown
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE input_versions (
    id INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    version_no INTEGER NOT NULL,
    sha256 TEXT NOT NULL,          -- of the input document
    binding TEXT NOT NULL,         -- JSON: id and version of the classification binding used
    document BLOB NOT NULL,        -- the input document as given (zlib JSON)
    common BLOB NOT NULL,          -- common internal format (zlib JSON)
    summary TEXT NOT NULL,         -- JSON: counts of states and issues
    created_at TEXT NOT NULL,
    UNIQUE (project_id, version_no)
);
CREATE TABLE other_items (
    id INTEGER PRIMARY KEY,
    input_version_id INTEGER NOT NULL REFERENCES input_versions(id) ON DELETE CASCADE,
    category TEXT NOT NULL, label TEXT NOT NULL,
    value TEXT,                    -- JSON of the value as given
    unit TEXT, note TEXT,
    raw TEXT NOT NULL              -- JSON of the whole entry as given
);
CREATE TABLE conditions (
    id INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL DEFAULT '',
    study_period REAL,             -- as asked; NULL when the request was not a number
    study_period_text TEXT NOT NULL,
    reference_set_id INTEGER REFERENCES reference_sets(id),
    baseline_input_version_id INTEGER REFERENCES input_versions(id),
    options TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);
CREATE TABLE runs (
    id INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    input_version_id INTEGER NOT NULL REFERENCES input_versions(id),
    condition_id INTEGER NOT NULL REFERENCES conditions(id),
    status TEXT NOT NULL CHECK (status IN ('ok', 'blocked', 'failed')),
    message TEXT NOT NULL DEFAULT '',
    versions TEXT NOT NULL,        -- JSON: app, engine source hashes, steps, libraries, data versions
    results BLOB,                  -- results of the 70 units as computed (zlib JSON), NULL unless ok
    view TEXT,                     -- JSON: what the result screen shows, taken from ``results``
    report TEXT NOT NULL,          -- JSON: conversion report and notes
    elapsed_ms REAL,
    created_at TEXT NOT NULL
);
CREATE INDEX runs_by_project ON runs(project_id, id);
CREATE INDEX inputs_by_project ON input_versions(project_id, version_no);
"""


class StoreError(RuntimeError):
    pass


def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def pack(obj: Any) -> bytes:
    return zlib.compress(json.dumps(obj, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8"), 6)


def unpack(blob: bytes | None) -> Any:
    return None if blob is None else json.loads(zlib.decompress(blob).decode("utf-8"))


def json_safe(obj: Any) -> tuple[Any, int]:
    """Copy of ``obj`` in which non-finite numbers are None; second value: how many were replaced."""
    count = 0

    def fix(o):
        nonlocal count
        if isinstance(o, float) and not math.isfinite(o):
            count += 1
            return None
        if isinstance(o, dict):
            return {str(k): fix(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [fix(v) for v in o]
        return o

    return fix(obj), count


def _dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, allow_nan=False)


class Store:
    def __init__(self, path: str):
        self.path = path
        folder = os.path.dirname(os.path.abspath(path))
        os.makedirs(folder, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys = ON")
        tables = {r[0] for r in self.db.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        if "app_meta" not in tables:
            with self.db:
                self.db.executescript(_SCHEMA)
                self.db.execute("INSERT INTO app_meta VALUES ('schema_version', ?)", (str(SCHEMA_VERSION),))
                self.db.execute("INSERT INTO app_meta VALUES ('created_at', ?)", (now(),))
        version = self.db.execute("SELECT value FROM app_meta WHERE key = 'schema_version'").fetchone()
        if version is None or int(version[0]) != SCHEMA_VERSION:
            self.db.close()
            raise StoreError("保存ファイルの版（%s）がこのアプリの版（%d）と違う" % (version[0] if version else "?", SCHEMA_VERSION))

    def close(self) -> None:
        self.db.close()

    # ---- reference data sets ------------------------------------------------------------------
    def add_refset(self, checked: dict) -> int:
        """Register a set that ``refdata.check`` has passed. The same content twice gives the same id."""
        row = self.db.execute("SELECT id, sha256 FROM reference_sets WHERE name = ? AND version = ?",
                              (checked["name"], checked["version"])).fetchone()
        if row is not None:
            if row["sha256"] != checked["sha256"]:
                raise StoreError("同じ名前と版（%s %s）で内容の違う参照データがすでにある。版を変えて登録する"
                                 % (checked["name"], checked["version"]))
            return row["id"]
        with self.db:
            cur = self.db.execute(
                "INSERT INTO reference_sets (name, version, data_kind, licence_status, source_note, sha256, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (checked["name"], checked["version"], checked["data_kind"], checked["licence_status"],
                 checked["source_note"], checked["sha256"], now()))
            set_id = cur.lastrowid
            data = checked["data"]
            rows = [("gases", "order", data["gases"])]
            rows += [("gwp", gas, value) for gas, value in data["gwp"].items()]
            rows += [("unit_conversions", "%06d" % i, conv) for i, conv in enumerate(data["unit_conversions"])]
            rows += [("factors", fid, rec) for fid, rec in data["factors"].items()]
            rows += [("price_index", year, value) for year, value in data["price_index"].items()]
            rows += [("standard_values", key, value) for key, value in data["standard_values"].items()]
            self.db.executemany("INSERT INTO reference_items VALUES (?, ?, ?, ?, ?)",
                                [(set_id, kind, key, seq, _dumps(value)) for seq, (kind, key, value) in enumerate(rows)])
        return set_id

    def list_refsets(self) -> list[dict]:
        rows = self.db.execute(
            "SELECT s.*, (SELECT COUNT(*) FROM reference_items i WHERE i.set_id = s.id AND i.kind = 'factors') AS n_factors "
            "FROM reference_sets s ORDER BY s.id").fetchall()
        return [dict(r) for r in rows]

    def find_refset(self, name: str, version: str) -> int | None:
        row = self.db.execute("SELECT id FROM reference_sets WHERE name = ? AND version = ?", (name, version)).fetchone()
        return None if row is None else row["id"]

    def get_refset(self, set_id: int) -> dict:
        head = self.db.execute("SELECT * FROM reference_sets WHERE id = ?", (set_id,)).fetchone()
        if head is None:
            raise StoreError("参照データ %s はない" % set_id)
        data: dict[str, Any] = {"gases": [], "gwp": {}, "unit_conversions": [], "factors": {}, "price_index": {},
                                "standard_values": {}}
        for row in self.db.execute("SELECT kind, key, payload FROM reference_items WHERE set_id = ? ORDER BY seq", (set_id,)):
            value = json.loads(row["payload"])
            if row["kind"] == "gases":
                data["gases"] = value
            elif row["kind"] == "unit_conversions":
                data["unit_conversions"].append(value)
            else:
                data[row["kind"]][row["key"]] = value
        data["gwp"] = {gas: data["gwp"][gas] for gas in data["gases"]}       # the order of the gas vector
        out = dict(head)
        out["data"] = data
        if refdata.digest(data) != head["sha256"]:
            raise StoreError("参照データ %s の内容が登録時と違う（保存ファイルの破損）" % set_id)
        return out

    # ---- projects --------------------------------------------------------------------------------
    def create_project(self, name: str, data_kind: str = "unknown", note: str = "") -> int:
        if data_kind not in DATA_KINDS:
            data_kind = "unknown"
        t = now()
        with self.db:
            cur = self.db.execute("INSERT INTO projects (name, data_kind, note, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                                  (str(name) or "（名称なし）", data_kind, str(note), t, t))
        return cur.lastrowid

    def update_project(self, project_id: int, name: str | None = None, note: str | None = None) -> None:
        self.get_project(project_id)
        with self.db:
            if name is not None:
                self.db.execute("UPDATE projects SET name = ?, updated_at = ? WHERE id = ?", (str(name), now(), project_id))
            if note is not None:
                self.db.execute("UPDATE projects SET note = ?, updated_at = ? WHERE id = ?", (str(note), now(), project_id))

    def get_project(self, project_id: int) -> dict:
        row = self.db.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        if row is None:
            raise StoreError("建物プロジェクト %s はない" % project_id)
        return dict(row)

    def list_projects(self) -> list[dict]:
        rows = self.db.execute(
            "SELECT p.*, (SELECT COUNT(*) FROM input_versions v WHERE v.project_id = p.id) AS n_inputs, "
            "(SELECT COUNT(*) FROM runs r WHERE r.project_id = p.id) AS n_runs FROM projects p ORDER BY p.id").fetchall()
        return [dict(r) for r in rows]

    # ---- inputs ------------------------------------------------------------------------------------
    def save_input(self, project_id: int, document: dict, common: dict, summary: dict) -> int:
        """Store an input as a new version of the project (an update never overwrites)."""
        self.get_project(project_id)
        text = json.dumps(document, ensure_ascii=False, sort_keys=True)
        sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
        with self.db:
            last = self.db.execute("SELECT COALESCE(MAX(version_no), 0) FROM input_versions WHERE project_id = ?",
                                   (project_id,)).fetchone()[0]
            cur = self.db.execute(
                "INSERT INTO input_versions (project_id, version_no, sha256, binding, document, common, summary, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (project_id, last + 1, sha, _dumps(common["binding"]), zlib.compress(text.encode("utf-8"), 6),
                 pack(common), _dumps(summary), now()))
            version_id = cur.lastrowid
            self.db.executemany(
                "INSERT INTO other_items (input_version_id, category, label, value, unit, note, raw) VALUES (?, ?, ?, ?, ?, ?, ?)",
                [(version_id, o["category"], o["label"], json.dumps(o["value"], ensure_ascii=False), o["unit"], o["note"],
                  json.dumps(o["raw"], ensure_ascii=False)) for o in common["others"]])
            self.db.execute("UPDATE projects SET updated_at = ?, data_kind = ? WHERE id = ?",
                            (now(), common["data_kind"], project_id))
        return version_id

    def _input_row(self, row, with_data: bool) -> dict:
        out = {k: row[k] for k in ("id", "project_id", "version_no", "sha256", "created_at")}
        out["binding"] = json.loads(row["binding"])
        out["summary"] = json.loads(row["summary"])
        if with_data:
            out["document"] = json.loads(zlib.decompress(row["document"]).decode("utf-8"))
            out["common"] = unpack(row["common"])
        return out

    def get_input(self, version_id: int, with_data: bool = True) -> dict:
        row = self.db.execute("SELECT * FROM input_versions WHERE id = ?", (version_id,)).fetchone()
        if row is None:
            raise StoreError("入力の版 %s はない" % version_id)
        return self._input_row(row, with_data)

    def list_inputs(self, project_id: int) -> list[dict]:
        rows = self.db.execute("SELECT id, project_id, version_no, sha256, binding, summary, created_at FROM input_versions "
                               "WHERE project_id = ? ORDER BY version_no", (project_id,)).fetchall()
        return [self._input_row(r, False) for r in rows]

    def latest_input_id(self, project_id: int) -> int | None:
        row = self.db.execute("SELECT id FROM input_versions WHERE project_id = ? ORDER BY version_no DESC LIMIT 1",
                              (project_id,)).fetchone()
        return None if row is None else row["id"]

    def list_others(self, version_id: int) -> list[dict]:
        rows = self.db.execute("SELECT * FROM other_items WHERE input_version_id = ? ORDER BY id", (version_id,)).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["value"] = json.loads(d["value"]) if d["value"] is not None else None
            d["raw"] = json.loads(d["raw"])
            out.append(d)
        return out

    # ---- conditions and runs -------------------------------------------------------------------
    def save_condition(self, project_id: int, study_period: Any, reference_set_id: int | None,
                       baseline_input_version_id: int | None = None, name: str = "", options: dict | None = None) -> int:
        number = study_period if isinstance(study_period, (int, float)) and not isinstance(study_period, bool) \
            and math.isfinite(study_period) else None
        with self.db:
            cur = self.db.execute(
                "INSERT INTO conditions (project_id, name, study_period, study_period_text, reference_set_id, "
                "baseline_input_version_id, options, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (project_id, str(name), number, str(study_period), reference_set_id, baseline_input_version_id,
                 _dumps(options or {}), now()))
        return cur.lastrowid

    def get_condition(self, condition_id: int) -> dict:
        row = self.db.execute("SELECT * FROM conditions WHERE id = ?", (condition_id,)).fetchone()
        if row is None:
            raise StoreError("計算条件 %s はない" % condition_id)
        out = dict(row)
        out["options"] = json.loads(out["options"])
        return out

    def save_run(self, project_id: int, input_version_id: int, condition_id: int, status: str, message: str,
                 versions: dict, results: dict | None, view: dict | None, report: dict, elapsed_ms: float | None) -> int:
        with self.db:
            cur = self.db.execute(
                "INSERT INTO runs (project_id, input_version_id, condition_id, status, message, versions, results, view, "
                "report, elapsed_ms, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (project_id, input_version_id, condition_id, status, message, _dumps(versions),
                 None if results is None else pack(results), None if view is None else _dumps(view),
                 _dumps(report), elapsed_ms, now()))
            self.db.execute("UPDATE projects SET updated_at = ? WHERE id = ?", (now(), project_id))
        return cur.lastrowid

    def get_run(self, run_id: int, with_results: bool = False) -> dict:
        row = self.db.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        if row is None:
            raise StoreError("計算結果 %s はない" % run_id)
        out = {k: row[k] for k in ("id", "project_id", "input_version_id", "condition_id", "status", "message",
                                   "elapsed_ms", "created_at")}
        out["versions"] = json.loads(row["versions"])
        out["view"] = None if row["view"] is None else json.loads(row["view"])
        out["report"] = json.loads(row["report"])
        out["has_results"] = row["results"] is not None
        if with_results:
            out["results"] = unpack(row["results"])
        return out

    def list_runs(self, project_id: int) -> list[dict]:
        rows = self.db.execute(
            "SELECT r.id, r.status, r.message, r.created_at, r.input_version_id, r.elapsed_ms, c.study_period, "
            "c.study_period_text, c.name AS condition_name, c.baseline_input_version_id, v.version_no "
            "FROM runs r JOIN conditions c ON c.id = r.condition_id JOIN input_versions v ON v.id = r.input_version_id "
            "WHERE r.project_id = ? ORDER BY r.id DESC", (project_id,)).fetchall()
        return [dict(r) for r in rows]
