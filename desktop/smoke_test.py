"""ビルドしたデスクトップ版を実際に起動して、主要 API と画面が応答するか確かめる（CI・手元共通）。

  python desktop/smoke_test.py build_desktop/dist/AQROS/AQROS        (Linux)
  python desktop/smoke_test.py build_desktop\\dist\\AQROS\\AQROS.exe  (Windows)
  python desktop/smoke_test.py build_desktop/dist/AQROS.app/Contents/MacOS/AQROS (macOS)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request

PORT = 47690
PATHS = ["/api/health", "/api/dashboard", "/api/sources", "/api/knowledge", "/api/models", "/api/report", "/api/deliverables", "/", "/simulator"]


def get(path: str, timeout: float = 3.0):
    with urllib.request.urlopen(f"http://127.0.0.1:{PORT}{path}", timeout=timeout) as r:
        return r.status, r.read()


def main(exe: str) -> int:
    data = tempfile.mkdtemp(prefix="aqros-smoke-")
    env = {**os.environ, "AQROS_DATA_DIR": data}
    p = subprocess.Popen([exe, "--headless", "--no-browser", "--port", str(PORT)], env=env)
    try:
        t0 = time.time()
        while True:
            try:
                st, body = get("/api/health", 1.0)
                h = json.loads(body)
                break
            except Exception:  # noqa: BLE001
                if p.poll() is not None or time.time() - t0 > 120:
                    log = os.path.join(data, "aqros.log")
                    print(open(log, encoding="utf-8").read() if os.path.exists(log) else "(no log)")
                    print("FAIL: server did not start")
                    return 1
                time.sleep(0.5)
        print("health:", h, f"({time.time() - t0:.1f}s)")
        assert h["app"] == "aqros" and h["desktop"] is True
        bad = []
        for path in PATHS:
            st, body = get(path, 30)
            print(st, path, len(body))
            if st != 200 or not body:
                bad.append(path)
        n = len(json.loads(get("/api/sources")[1]))
        assert n >= 60, n
        assert os.path.exists(os.path.join(data, "aqros.sqlite3")), "DB not in data dir"
        if bad:
            print("FAIL:", bad)
            return 1
        print(f"OK: {len(PATHS)} endpoints, {n} sources")
        return 0
    finally:
        p.terminate()
        try:
            p.wait(15)
        except subprocess.TimeoutExpired:
            p.kill()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
