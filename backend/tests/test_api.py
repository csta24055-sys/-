"""API の結合テスト: データ保存・再読込、資料検索、CSV解析、出典表示"""
import io

import pytest
from fastapi.testclient import TestClient

from app import main


@pytest.fixture()
def client(tmp_path):
    main.reset_db(str(tmp_path / "t.sqlite3"))
    return TestClient(main.app)


def test_dashboard_counts(client):
    d = client.get("/api/dashboard").json()
    assert d["counts"]["sources"] >= 60
    assert d["counts"]["read"] >= 10
    assert d["counts"]["read"] + d["counts"]["unread"] == d["counts"]["sources"]


def test_search_and_filter(client):
    r = client.get("/api/sources", params={"q": "バイパス"}).json()
    assert any(s["box_id"] == "2525808527679" for s in r)
    r = client.get("/api/sources", params={"year": "2025", "status": "読了"}).json()
    assert r and all(s["fiscal_year"] == 2025 and s["status"] == "読了" for s in r)
    # 複数語の AND 検索
    r = client.get("/api/sources", params={"q": "I/O 年間"}).json()
    assert any(s["id"] == "S-2025-01" for s in r)


def test_source_detail_has_provenance(client):
    d = client.get("/api/sources/S-2025-01").json()
    assert d["source"]["link"].startswith("https://app.box.com/file/")
    assert d["source"]["pages"]
    assert any(f["id"] == "F-2025-02" for f in d["findings"])
    assert d["related"]  # 関連資料（S-2025-02 等）


def test_status_update_persists_across_restart(client, tmp_path):
    client.patch("/api/sources/S-2025-05", json={"status": "読了", "notes": "p.12 まで確認"})
    # 再起動相当: 同じDBファイルを開き直す（seed で上書きされないこと）
    main.reset_db(str(tmp_path / "t.sqlite3"))
    c2 = TestClient(main.app)
    s = c2.get("/api/sources/S-2025-05").json()["source"]
    assert s["status"] == "読了" and s["notes"] == "p.12 まで確認"


def test_invalid_status_rejected(client):
    assert client.patch("/api/sources/S-2025-05", json={"status": "済"}).status_code == 400


def test_csv_upload_quality_and_reload(client, tmp_path):
    csv = "日時,外気,リビング\n2025-09-17 00:00,10,5\n2025-09-17 00:01,12,\n2025-09-17 00:02,11,5.5\n2025-09-17 00:03,10.5,5.2\n2025-09-17 00:04,500,5.1\n2025-09-17 00:05,11,5.3\n2025-09-17 00:06,10.8,5.0\n"
    r = client.post("/api/datasets/upload", files={"file": ("t.csv", io.BytesIO(csv.encode("utf-8")), "text/csv")}, data={"name": "テスト"})
    assert r.status_code == 200, r.text
    did = r.json()["ids"][0]
    q = client.get(f"/api/datasets/{did}/quality").json()
    assert q["time_column"] == "日時"
    rep = {x["column"]: x for x in q["report"]}
    assert rep["リビング"]["missing"] == 1
    assert rep["外気"]["outliers"] == 1
    main.reset_db(str(tmp_path / "t.sqlite3"))
    d = TestClient(main.app).get(f"/api/datasets/{did}").json()
    assert d["n_rows"] == 7 and d["columns"] == ["日時", "外気", "リビング"]


def test_shift_jis_csv(client):
    csv = "時刻,濃度\n0,1\n1,2\n".encode("cp932")
    r = client.post("/api/datasets/upload", files={"file": ("sj.csv", io.BytesIO(csv), "text/csv")})
    assert r.status_code == 200


def test_xlsx_upload(client):
    import pandas as pd
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        pd.DataFrame({"風量": [100, 200], "差圧": [1.0, 2.3]}).to_excel(w, sheet_name="EP", index=False)
        pd.DataFrame({"a": [1]}).to_excel(w, sheet_name="memo", index=False)
    r = client.post("/api/datasets/upload", files={"file": ("x.xlsx", io.BytesIO(buf.getvalue()), "application/octet-stream")})
    assert len(r.json()["ids"]) == 2


def test_analyze_regression(client):
    r = client.post("/api/analyze", json={"type": "regression_origin", "x": [1, 2, 3, 4], "y": [0.55, 1.1, 1.65, 2.2]}).json()
    assert r["k"] == pytest.approx(0.55)


def test_simulators(client):
    z = client.post("/api/simulate/zone", json={"hours": 2}).json()
    assert z["series"][0]["c"] == 0 and z["steady_state"] > 0
    b = client.post("/api/simulate/bypass", json={"n_units": 5, "steps": 5}).json()
    assert len(b) == 5 and b[0]["cadr"] == pytest.approx(741, rel=0.02)


def test_report_edit_and_export(client):
    secs = client.get("/api/report").json()
    assert len(secs) >= 5
    sid = secs[0]["id"]
    client.put(f"/api/report/{sid}", json={"body": "# 改訂\n本文"})
    md = client.get("/api/report/export.md").text
    assert "# 改訂" in md


def test_add_question_and_theme_decision(client):
    q = client.post("/api/questions", json={"text": "新しい問い"}).json()
    assert q["id"].startswith("Q-")
    t = client.patch("/api/items/theme/T-01", json={"data": {"decision": "採択", "decision_reason": "外挿依存の解消が最優先"}}).json()
    assert t["decision"] == "採択"


def test_concurrent_reads_and_writes(client):
    """回帰テスト: 共有接続の競合で 500 (sqlite3.InterfaceError) が出ていた不具合"""
    from concurrent.futures import ThreadPoolExecutor

    def work(i):
        if i % 3 == 0:
            return client.patch("/api/sources/S-2025-05", json={"notes": f"n{i}"}).status_code
        return client.get("/api/sources").status_code

    with ThreadPoolExecutor(8) as ex:
        codes = list(ex.map(work, range(60)))
    assert set(codes) == {200}


def test_knowledge_includes_validation(client):
    k = client.get("/api/knowledge").json()
    v = k["validation"]["multizone"]
    weak = [c for c in v["cases"] if c["fan"] == "弱" and c["D_per_s"] == 0.0003][0]
    assert weak["mean_nrmse"] < 0.3  # F-SIM-01: 弱・D=0.0003 で実測を概ね再現
    strong = [c for c in v["cases"] if c["fan"] == "強" and c["D_per_s"] == 0.0003][0]
    assert strong["mean_peak_ratio"] > 1.3  # 強運転では過大評価
    raw = k["validation"]["raw2025"]
    assert abs(raw["A_iwakuni"]["cond1"]["io_リビング"] - 0.28) < 0.01
    assert abs(raw["C_nogata"]["cond2_final_table5"]["io_リビング"] - 0.68) < 0.01


def test_knowledge_includes_fate_and_annual_validation(client):
    k = client.get("/api/knowledge").json()
    f = k["validation"]["fate2022"]
    row = [r for r in f["rows"] if r["size_um"] == "5-10" and r["cond"] == "条件5"][0]
    assert abs(row["diff_pt"]["集塵機"]) < 1.0  # F-SIM-08: EP の割合を再現
    a = k["validation"]["annual2025"]["sites"]
    for s in a.values():  # F-2025-21: 条件②の超過時間割合は約40%（33〜38%）
        assert 30 < s["条件②_gt5_pct"] < 42
        assert s["条件①_gt5_pct"] < 1
    themes = {t["id"]: t for t in k["themes"]}
    assert all("evaluation" in t for t in themes.values())
    assert themes["T-03"]["scores"]["importance"] == 5


def test_night_and_block_ci(client):
    k = client.get("/api/knowledge").json()
    n = k["validation"]["raw2025"]["night_and_block_ci"]
    lo, hi = n["C_cond2_final"]["all_hours"]["ci_block"]
    assert hi - lo > 0.1  # F-V-11: プールCI（±0.01）より大幅に広い
    assert n["C_cond3"]["night_0_5"]["io"] < n["C_cond3"]["all_hours"]["io"]  # F-V-12
