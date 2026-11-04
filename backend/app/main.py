"""Air Quality Research OS — FastAPI アプリケーション

起動:  uvicorn app.main:app --app-dir backend --port 8000
"""
from __future__ import annotations

import math
import os
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from aqros import analysis as A
from aqros import models as M

from .db import DB, ROOT

MAX_ROWS = 200_000
MAX_UPLOAD = 50 * 1024 * 1024

app = FastAPI(title="Air Quality Research OS", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
_db: DB | None = None


def db() -> DB:
    global _db
    if _db is None:
        _db = DB(os.environ.get("AQROS_DB"))
    return _db


def reset_db(path: str) -> DB:
    """テスト用"""
    global _db
    _db = DB(path)
    return _db


def _clean(v: Any) -> Any:
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    if isinstance(v, (np.floating,)):
        return _clean(float(v))
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (pd.Timestamp,)):
        return v.isoformat()
    return v


# ----------------------------------------------------------------- dashboard
@app.get("/api/health")
def health():
    return {"ok": True, "db": str(db().path.name)}


@app.get("/api/dashboard")
def dashboard():
    d = db()
    sources = d.list_items("source")
    studies = d.list_items("study")
    findings = d.list_items("finding")
    questions = d.list_items("question")
    themes = d.list_items("theme")
    status = Counter(s["status"] for s in sources)
    by_year: dict[str, Counter] = {}
    for s in sources:
        y = str(s.get("fiscal_year") or "不明")
        by_year.setdefault(y, Counter())[s["status"]] += 1
    read = status.get("読了", 0) + status.get("数値検証済み", 0)
    key_ids = ["F-2018-01", "F-2024-03", "F-2025-02", "F-2025-03", "F-2026-01", "F-2026-03"]
    return {
        "counts": {
            "sources": len(sources), "read": read, "unread": len(sources) - read,
            "by_status": dict(status), "findings": len(findings), "questions": len(questions),
            "themes": len(themes), "datasets": len(d.list_datasets()),
        },
        "by_year": {y: dict(c) for y, c in sorted(by_year.items())},
        "studies": studies,
        "key_findings": [f for f in findings if f["id"] in key_ids],
        "open_questions": sorted([q for q in questions if q["priority"] == "高"], key=lambda q: q["id"]),
        "next_actions": [
            "住宅D（周南）原データを研究室で分割保存し、条件①係数0.14・EP稼働期間を検証（Q-12, F-V-06, F-2025-19）",
            "センサー説明書（画像PDF）で換算式を確認し『仮の正規化』の影響を評価（Q-11, F-2025-12）",
            "EP 750 m³/h超の差圧・効率試験計画を2026年度班と協議（T-01）",
            "2024年度1分値から生活行動別の発塵率Gを推定し、年間予測に室内発生を加える（T-05, F-2024-09）",
            "清浄度-計算式_by井口.pdf を Box 上で目視確認し式を台帳へ転記（Q-08）",
        ],
        "progress": {
            "資料探索": {"done": read, "total": len(sources)},
            "分析": {"done": len([f for f in findings if f["class"] in ("分析", "計算結果")]), "total": len(findings)},
            "テーマ判断": {"done": len([t for t in themes if t.get("decision")]), "total": len(themes)},
        },
        "activity": d.recent_activity(8),
    }


# ------------------------------------------------------------------- library
@app.get("/api/sources")
def list_sources(q: str = "", year: str = "", status: str = "", kind: str = ""):
    items = db().list_items("source")
    ql = q.strip().lower()

    def hit(s):
        if year and str(s.get("fiscal_year") or "不明") != year:
            return False
        if status and s["status"] != status:
            return False
        if kind and kind not in s["kind"]:
            return False
        if ql:
            hay = " ".join(str(s.get(k, "")) for k in ("title", "topic", "purpose", "results", "conclusions", "limitations", "notes", "folder", "box_id", "id", "instruments")).lower()
            return all(t in hay for t in ql.split())
        return True

    return [s for s in items if hit(s)]


@app.get("/api/sources/{sid}")
def get_source(sid: str):
    d = db()
    s = d.get_item("source", sid)
    if not s:
        raise HTTPException(404, "資料が見つかりません")
    findings = [f for f in d.list_items("finding") if sid in f["sources"]]
    studies = [st for st in d.list_items("study") if sid in st["sources"]]
    related_ids = {x for f in findings for x in f["sources"] if x != sid}
    related = [d.get_item("source", r) for r in sorted(related_ids)]
    return {"source": s, "findings": findings, "studies": studies, "related": [r for r in related if r]}


class SourcePatch(BaseModel):
    status: str | None = None
    notes: str | None = None


VALID_STATUS = {"未確認", "目録確認", "読了", "数値検証済み"}


@app.patch("/api/sources/{sid}")
def patch_source(sid: str, p: SourcePatch):
    if p.status and p.status not in VALID_STATUS:
        raise HTTPException(400, f"status は {sorted(VALID_STATUS)} のいずれか")
    r = db().patch_item("source", sid, p.model_dump())
    if not r:
        raise HTTPException(404)
    return r


class NewSource(BaseModel):
    title: str
    box_id: str = ""
    fiscal_year: int | None = None
    kind: str = "ローカル資料"
    topic: str = ""
    status: str = "目録確認"
    notes: str = ""
    link: str = ""


@app.post("/api/sources")
def add_source(s: NewSource):
    """Box 未接続時のローカル資料登録"""
    d = db()
    n = len([x for x in d.list_items("source") if x["id"].startswith("S-LOCAL-")]) + 1
    item = {**s.model_dump(), "id": f"S-LOCAL-{n:03d}", "folder": "ローカル", "folder_id": "", "accessed": pd.Timestamp.now().date().isoformat()}
    for k in ("purpose", "conditions", "instruments", "measurements", "raw_data", "methods", "results", "conclusions", "limitations", "related", "pages", "version"):
        item.setdefault(k, "")
    return d.upsert_item("source", item)


# ----------------------------------------------------------------- knowledge
@app.get("/api/knowledge")
def knowledge():
    d = db()
    return {
        "studies": d.list_items("study"),
        "findings": d.list_items("finding"),
        "hypotheses": d.list_items("hypothesis"),
        "questions": d.list_items("question"),
        "themes": d.list_items("theme"),
        "roadmap": d.meta("roadmap"),
        "models": d.meta("models"),
        "graph": d.meta("graph"),
        "external": d.meta("external"),
        "meta": d.meta("meta"),
        "validation": d.meta("validation"),
        "literature": d.meta("literature") or [],
        "completeness": d.meta("completeness"),
    }


class ItemPatch(BaseModel):
    data: dict[str, Any]


@app.patch("/api/items/{kind}/{iid}")
def patch_item(kind: str, iid: str, p: ItemPatch):
    if kind not in ("hypothesis", "question", "theme", "finding"):
        raise HTTPException(400, "編集可能な種別: hypothesis, question, theme, finding")
    r = db().patch_item(kind, iid, p.data)
    if not r:
        raise HTTPException(404)
    return r


class NewQuestion(BaseModel):
    text: str
    priority: str = "中"
    related: list[str] = Field(default_factory=list)
    status: str = "未着手"


@app.post("/api/questions")
def add_question(q: NewQuestion):
    d = db()
    ids = [int(x["id"].split("-")[1]) for x in d.list_items("question") if x["id"].split("-")[1].isdigit()]
    item = {"id": f"Q-{max(ids, default=0) + 1:02d}", **q.model_dump()}
    return d.upsert_item("question", item)


# ------------------------------------------------------------------ datasets
@app.post("/api/datasets/upload")
async def upload(file: UploadFile = File(...), name: str = Form(""), study: str = Form(""), description: str = Form("")):
    content = await file.read()
    if len(content) > MAX_UPLOAD:
        raise HTTPException(413, "ファイルが大きすぎます（50MB まで）")
    try:
        sheets = A.read_table(content, file.filename or "data.csv")
    except Exception as e:  # noqa: BLE001
        raise HTTPException(400, f"読み込みに失敗しました: {e}") from e
    ids = []
    for sheet, df in sheets.items():
        if df.empty:
            continue
        df = df.head(MAX_ROWS)
        tcol = A.detect_time_column(df)
        if tcol:
            parsed = pd.to_datetime(df[tcol], errors="coerce")
            df[tcol] = parsed.dt.strftime("%Y-%m-%dT%H:%M:%S").where(parsed.notna(), df[tcol].astype(str))
        rows = [[_clean(v) for v in r] for r in df.astype(object).where(df.notna(), None).values.tolist()]
        label = (name or Path(file.filename or "data").stem) + ("" if len(sheets) == 1 else f" [{sheet}]")
        ids.append(db().add_dataset(label, file.filename, sheet, list(map(str, df.columns)), rows, study or None, description or None))
    if not ids:
        raise HTTPException(400, "データ行がありません")
    return {"ids": ids}


class DatasetIn(BaseModel):
    name: str
    columns: list[str]
    rows: list[list[Any]]
    study: str | None = None
    description: str | None = None
    provenance: str = "利用者インポート"


@app.post("/api/datasets")
def create_dataset(ds: DatasetIn):
    if len(ds.rows) > MAX_ROWS:
        raise HTTPException(413, f"{MAX_ROWS} 行まで")
    return {"id": db().add_dataset(ds.name, None, None, ds.columns, ds.rows, ds.study, ds.description, ds.provenance)}


@app.get("/api/datasets")
def datasets():
    return db().list_datasets()


@app.get("/api/datasets/{did}")
def dataset(did: int):
    d = db().get_dataset(did)
    if not d:
        raise HTTPException(404)
    return d


@app.delete("/api/datasets/{did}")
def delete_dataset(did: int):
    if not db().delete_dataset(did):
        raise HTTPException(404)
    return {"ok": True}


@app.get("/api/datasets/{did}/quality")
def dataset_quality(did: int):
    d = db().get_dataset(did)
    if not d:
        raise HTTPException(404)
    df = pd.DataFrame(d["rows"], columns=d["columns"])
    tcol = A.detect_time_column(df)
    cols = A.numeric_columns(df, exclude=tcol)
    return {"time_column": tcol, "numeric_columns": cols, "report": A.quality_report(df, cols)}


class AnalyzeIn(BaseModel):
    type: str
    x: list[float | None] = Field(default_factory=list)
    y: list[float | None] = Field(default_factory=list)
    threshold: float | None = None


@app.post("/api/analyze")
def analyze(p: AnalyzeIn):
    x = np.array([np.nan if v is None else v for v in p.x], dtype=float)
    y = np.array([np.nan if v is None else v for v in p.y], dtype=float)
    try:
        if p.type == "regression_origin":
            return A.regression_through_origin(x, y)
        if p.type == "linear":
            return A.linear_regression(x, y)
        if p.type == "power_law":
            return A.power_law_fit(x, y)
        if p.type == "removal_efficiency":
            return A.removal_efficiency(x, y)
        if p.type == "io_ratio":
            return A.io_ratio(y, x)
        if p.type == "exceedance":
            return {"fraction": A.exceedance(y, p.threshold or 5.0)}
        if p.type == "decay":
            return A.fit_decay(x, y)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    raise HTTPException(400, "未知の解析種別")


# ----------------------------------------------------------------- simulator
class ZoneIn(BaseModel):
    volume: float = 250
    q_oa: float = 125
    eta_oa_filter: float = 0.45
    q_inf: float = 0
    penetration_inf: float = 1
    q_recirc: float = 950
    bypass_ratio: float = 0
    eta_ep: float = 0.85
    deposition: float = 0.2
    c_out: float = 7
    generation: float = 0
    c0: float = 0
    hours: float = 24


@app.post("/api/simulate/zone")
def sim_zone(p: ZoneIn):
    hours = max(0.1, min(p.hours, 24 * 14))
    zp = M.ZoneParams(**p.model_dump(exclude={"hours"}))
    if zp.volume <= 0:
        raise HTTPException(400, "室容積は正の値")
    ts = M.zone_time_series(zp, hours=hours, dt_h=max(hours / 400, 1 / 60))
    return {
        "steady_state": M.zone_steady_state(zp), "io_ratio": M.zone_io_ratio(zp), "cadr": M.zone_cadr(zp),
        "loss_rate": M.zone_loss_rate(zp), "t12_h": M.time_to_fraction(zp, 0.12),
        "series": [{"t": t, "c": c} for t, c in ts],
    }


class BypassIn(BaseModel):
    n_units: int = 5
    setting: str = "中"
    size_bin: str = "0.3-0.5"
    ep_law: str = "fit"
    steps: int = 21
    alpha: float = 0.65
    area_full: float = 0.25


@app.post("/api/simulate/bypass")
def sim_bypass(p: BypassIn):
    if p.setting not in M.FAN_SETTINGS or p.size_bin not in M.EP_EFFICIENCY_ENDPOINTS or p.ep_law not in M.EP_LAWS:
        raise HTTPException(400, "設定値が不正です")
    res = M.bypass_sweep(max(1, min(p.n_units, 40)), p.setting, steps=max(2, min(p.steps, 101)), size_bin=p.size_bin,
                         ep_law=p.ep_law, alpha=p.alpha, area_full=p.area_full)
    return [asdict(r) for r in res]


@app.get("/api/models")
def models():
    return {"registry": M.MODEL_REGISTRY, "fan": M.FAN_SETTINGS, "ep_efficiency": M.EP_EFFICIENCY_ENDPOINTS,
            "ep_range": M.EP_Q_RANGE, "ep_coef": [M.EP_COEF, M.EP_EXP]}


# -------------------------------------------------------------------- report
@app.get("/api/report")
def report():
    return db().report_sections()


class SectionIn(BaseModel):
    body: str
    title: str | None = None


@app.put("/api/report/{sid}")
def save_section(sid: str, s: SectionIn):
    return db().save_section(sid, s.body, s.title)


@app.post("/api/report/{sid}/reset")
def reset_section(sid: str):
    db().reset_section(sid)
    return {"ok": True}


@app.get("/api/report/export.md", response_class=PlainTextResponse)
def export_md():
    secs = db().report_sections()
    return "\n\n".join(s["body"] for s in secs)


# ------------------------------------------------------------- research plans
class PlanIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    theme_id: str | None = Field(default=None, max_length=20)
    background: str = Field(default="", max_length=20000)
    purpose: str = Field(default="", max_length=20000)
    hypotheses: str = Field(default="", max_length=20000)
    methods: str = Field(default="", max_length=20000)
    equipment: str = Field(default="", max_length=20000)
    measurements: str = Field(default="", max_length=20000)
    analysis: str = Field(default="", max_length=20000)
    schedule: str = Field(default="", max_length=20000)
    risks: str = Field(default="", max_length=20000)
    alternatives: str = Field(default="", max_length=20000)
    references: str = Field(default="", max_length=20000)


@app.get("/api/plans")
def list_plans():
    return db().list_plans()


@app.post("/api/plans")
def create_plan(body: PlanIn):
    return db().save_plan(body.model_dump())


@app.put("/api/plans/{pid}")
def update_plan(pid: int, body: PlanIn):
    try:
        return db().save_plan(body.model_dump(), pid)
    except KeyError:
        raise HTTPException(404, "plan not found")


@app.delete("/api/plans/{pid}")
def delete_plan(pid: int):
    if not db().delete_plan(pid):
        raise HTTPException(404, "plan not found")
    return {"ok": True}


# ------------------------------------------------------------- user state (学習進捗など)
STATE_KEYS = {"learning"}


@app.get("/api/state/{key}")
def get_state(key: str):
    if key not in STATE_KEYS:
        raise HTTPException(404, "unknown key")
    return {"key": key, "value": db().get_state(key)}


class StateIn(BaseModel):
    value: Any


@app.put("/api/state/{key}")
def put_state(key: str, body: StateIn):
    if key not in STATE_KEYS:
        raise HTTPException(404, "unknown key")
    if len(str(body.value)) > 100_000:
        raise HTTPException(413, "too large")
    db().set_state(key, body.value)
    return {"ok": True}


# ------------------------------------------------------------- deliverables（2027年度向け資料）
DELIV = ROOT / "deliverables"
DELIV_EXT = {".md": "text/markdown; charset=utf-8", ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document", ".pdf": "application/pdf",
             ".csv": "text/csv; charset=utf-8"}
DELIV_SUBDIRS = ("technical_report_2026-11",)   # 公開してよい成果物のサブフォルダ（原データは置かない）


def _deliv_files():
    out = [f for f in sorted(DELIV.iterdir()) if f.is_file() and f.suffix in DELIV_EXT and f.suffix != ".csv"] if DELIV.exists() else []
    for sd in DELIV_SUBDIRS:
        d = DELIV / sd
        if d.is_dir():
            out += [f for f in sorted(d.iterdir()) if f.is_file() and f.suffix in DELIV_EXT]
    return out


@app.get("/api/deliverables")
def list_deliverables():
    return [{"name": f.relative_to(DELIV).as_posix(), "size": f.stat().st_size, "ext": f.suffix,
             "group": f.parent.name if f.parent != DELIV else "2027"} for f in _deliv_files()]


@app.get("/api/deliverables/{name:path}")
def get_deliverable(name: str):
    f = (DELIV / name).resolve()
    allowed = {DELIV.resolve(), *((DELIV / sd).resolve() for sd in DELIV_SUBDIRS)}
    if f.parent not in allowed or f.suffix not in DELIV_EXT or not f.is_file() or (f.suffix == ".csv" and f.parent == DELIV.resolve()):
        raise HTTPException(404, "not found")
    from urllib.parse import quote
    ascii_name = {"研究継承総合資料": "AQROS_2027_inheritance", "研究方針": "AQROS_2027_strategy"}
    fb = f.name if f.name.isascii() else next((v for k, v in ascii_name.items() if k in f.name), "AQROS_2027") + f.suffix
    return FileResponse(f, media_type=DELIV_EXT[f.suffix],
                        headers={"Content-Disposition": f"attachment; filename=\"{fb}\"; filename*=utf-8''{quote(f.name)}"})


# ------------------------------------------------------------- static (SPA)
DIST = ROOT / "frontend" / "dist"
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        f = DIST / path
        if path and f.is_file() and DIST in f.resolve().parents:
            return FileResponse(f)
        return FileResponse(DIST / "index.html")
