"""デスクトップ配布版: 保存先の決定、localhost 限定の防御、ランチャーの二重起動判定"""
import importlib
import os
import subprocess
import sys
import textwrap
from pathlib import Path

from app import paths

ROOT = Path(__file__).resolve().parents[2]


def test_user_data_dir_per_os(tmp_path):
    home = tmp_path
    assert paths.user_data_dir("win32", {"APPDATA": r"C:\Users\u\AppData\Roaming"}, home) == Path(r"C:\Users\u\AppData\Roaming") / "AQROS"
    assert paths.user_data_dir("darwin", {}, home) == home / "Library" / "Application Support" / "AQROS"
    assert paths.user_data_dir("linux", {}, home) == home / ".local" / "share" / "aqros"
    assert paths.user_data_dir("linux", {"XDG_DATA_HOME": str(tmp_path / "x")}, home) == tmp_path / "x" / "aqros"
    assert paths.user_data_dir("linux", {"AQROS_DATA_DIR": str(tmp_path / "d")}, home) == tmp_path / "d"


def test_dev_defaults_unchanged():
    # リポジトリから起動したときは従来どおり（リソース = リポジトリ直下）
    assert not paths.frozen()
    assert paths.resource_root() == ROOT
    if not os.environ.get("AQROS_DATA_DIR"):
        assert paths.default_db_path() == ROOT / "private_data" / "aqros.sqlite3"


def test_desktop_mode_rejects_foreign_host_and_cross_origin_writes(tmp_path):
    # DESKTOP はインポート時に決まるので別プロセスで確認する
    code = textwrap.dedent(f"""
        import os
        os.environ["AQROS_DESKTOP"] = "1"
        os.environ["AQROS_DATA_DIR"] = {str(tmp_path)!r}
        from fastapi.testclient import TestClient
        from app import main
        assert main.DESKTOP
        c = TestClient(main.app, base_url="http://127.0.0.1:47615")
        assert c.get("/api/health").json()["desktop"] is True
        assert c.get("/api/health", headers={{"host": "evil.example"}}).status_code == 403
        r = c.put("/api/state/x", json={{"value": 1}}, headers={{"origin": "https://evil.example"}})
        assert r.status_code == 403, r.status_code
        r = c.get("/api/sources", headers={{"origin": "https://evil.example"}})
        assert "access-control-allow-origin" not in r.headers
        assert main.db().path == __import__("pathlib").Path({str(tmp_path)!r}) / "aqros.sqlite3"
        print("OK")
    """)
    env = {**os.environ, "PYTHONPATH": str(ROOT / "backend")}
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, cwd=ROOT, timeout=120)
    assert r.returncode == 0 and "OK" in r.stdout, r.stderr[-2000:]


def test_launcher_helpers(monkeypatch):
    sys.path.insert(0, str(ROOT / "desktop"))
    try:
        L = importlib.import_module("aqros_desktop")
    finally:
        sys.path.pop(0)
    assert L.HOST == "127.0.0.1"
    p = L.pick_port(L.PREFERRED_PORT)
    assert isinstance(p, int) and p > 0
    assert L.probe(1, timeout=0.2) is None  # 何も動いていないポート
