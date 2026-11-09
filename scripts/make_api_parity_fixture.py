"""端末内バックエンド（frontend/src/core/local.ts）と FastAPI の応答が一致するかを確かめる参照値を作る。

  python scripts/make_api_parity_fixture.py   → frontend/src/core/testdata/api_parity.json
（knowledge.json か report/*.md を更新したら再生成して `cd frontend && npm test`）
"""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from fastapi.testclient import TestClient  # noqa: E402

from app import main  # noqa: E402

QUERIES = ["/api/sources?q=バイパス", "/api/sources?year=2025&status=読了", "/api/sources?q=I/O 年間", "/api/sources?kind=pdf", "/api/sources/S-2025-01"]

with tempfile.TemporaryDirectory() as td:
    main.reset_db(str(Path(td) / "p.sqlite3"))
    c = TestClient(main.app)
    d = c.get("/api/dashboard").json()
    out = {"dashboard": {"counts": d["counts"], "by_year": d["by_year"], "key_findings": [f["id"] for f in d["key_findings"]],
                         "open_questions": [q["id"] for q in d["open_questions"]], "next_actions": d["next_actions"], "progress": d["progress"]},
           "queries": {}}
    for q in QUERIES:
        r = c.get(q).json()
        out["queries"][q] = [s["id"] for s in r] if isinstance(r, list) else {"source": r["source"]["id"], "findings": [f["id"] for f in r["findings"]],
                                                                               "studies": [s["id"] for s in r["studies"]], "related": [s["id"] for s in r["related"]]}
    k = c.get("/api/knowledge").json()
    out["knowledge_counts"] = {key: len(v) if isinstance(v, list) else None for key, v in k.items()}
    out["report_ids"] = [s["id"] for s in c.get("/api/report").json()]
(ROOT / "frontend" / "src" / "core" / "testdata" / "api_parity.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print("ok", len(out["queries"]))
