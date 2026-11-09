"""Air Quality Research OS — デスクトップ起動ランチャー（配布版の入口）

ダブルクリックで起動すると:
  1. このパソコン内だけ（127.0.0.1）でアプリのサーバーを起動する（外部には公開しない）
  2. 既定のブラウザでアプリを開く
  3. 小さな操作ウィンドウ（「ブラウザで開く」「終了」）を表示する。tkinter が無い環境ではコンソール表示で代用

すでに起動中なら新しいサーバーは立てず、ブラウザで既存の画面を開くだけにする。
利用者データ（取り込んだデータ・編集内容）は OS 標準の利用者データフォルダに保存する（app/paths.py）。

コマンドライン:
  AQROS [--port N] [--no-browser] [--headless] [--version] [--data-dir DIR]
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

HERE = Path(__file__).resolve().parent
if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(HERE.parent / "backend"))

PREFERRED_PORT = 47615
HOST = "127.0.0.1"


def probe(port: int, timeout: float = 0.5) -> dict | None:
    """そのポートで AQROS が動いていれば health を返す。"""
    try:
        with urllib.request.urlopen(f"http://{HOST}:{port}/api/health", timeout=timeout) as r:
            d = json.loads(r.read().decode("utf-8"))
            return d if d.get("app") == "aqros" else None
    except Exception:  # noqa: BLE001
        return None


def port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((HOST, port))
            return True
        except OSError:
            return False


def pick_port(preferred: int) -> int:
    for p in [preferred, *range(preferred + 1, preferred + 20)]:
        if port_free(p):
            return p
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, 0))
        return s.getsockname()[1]


def setup_logging(data_dir: Path) -> Path:
    """windowed ビルドでは stdout/stderr が無いので、ログファイルへ流す。"""
    data_dir.mkdir(parents=True, exist_ok=True)
    log = data_dir / "aqros.log"
    if sys.stdout is None or sys.stderr is None:
        f = open(log, "a", encoding="utf-8", buffering=1)  # noqa: SIM115
        sys.stdout = sys.stdout or f
        sys.stderr = sys.stderr or f
    return log


class ServerThread(threading.Thread):
    def __init__(self, port: int):
        super().__init__(daemon=True)
        import uvicorn

        from app.main import app  # noqa: PLC0415  （AQROS_DATA_DIR 設定後に読み込む）

        self.config = uvicorn.Config(app, host=HOST, port=port, log_level="warning", access_log=False, log_config=None)
        self.server = uvicorn.Server(self.config)

    def run(self) -> None:
        self.server.run()

    def stop(self) -> None:
        self.server.should_exit = True


def wait_ready(port: int, timeout: float = 60) -> bool:
    t0 = time.time()
    while time.time() - t0 < timeout:
        if probe(port, 1.0):
            return True
        time.sleep(0.2)
    return False


def open_folder(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    if sys.platform.startswith("win"):
        os.startfile(str(path))  # type: ignore[attr-defined]  # noqa: S606
    else:
        import subprocess  # noqa: PLC0415
        subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(path)])  # noqa: S603


def control_window(url: str, data_dir: Path, version: str, on_quit) -> bool:
    """tkinter の小窓。表示できなければ False。"""
    try:
        import tkinter as tk
        from tkinter import ttk
    except Exception:  # noqa: BLE001
        return False
    try:
        root = tk.Tk()
    except Exception:  # noqa: BLE001  （ディスプレイなし）
        return False
    root.title("Air Quality Research OS")
    root.resizable(False, False)
    frm = ttk.Frame(root, padding=16)
    frm.grid()
    ttk.Label(frm, text=f"Air Quality Research OS {version}", font=("", 13, "bold")).grid(column=0, row=0, columnspan=3, sticky="w")
    ttk.Label(frm, text="実行中です。画面はブラウザに表示されます。\nこのウィンドウを閉じるとアプリを終了します。").grid(column=0, row=1, columnspan=3, sticky="w", pady=(6, 6))
    ttk.Label(frm, text=url, foreground="#0f5b5c").grid(column=0, row=2, columnspan=3, sticky="w")
    ttk.Label(frm, text=f"データ保存先: {data_dir}", foreground="#555").grid(column=0, row=3, columnspan=3, sticky="w", pady=(4, 10))
    ttk.Button(frm, text="ブラウザで開く", command=lambda: webbrowser.open(url)).grid(column=0, row=4, sticky="we", padx=(0, 6))
    ttk.Button(frm, text="データフォルダ", command=lambda: open_folder(data_dir)).grid(column=1, row=4, sticky="we", padx=(0, 6))

    def quit_():
        on_quit()
        root.destroy()

    ttk.Button(frm, text="終了", command=quit_).grid(column=2, row=4, sticky="we")
    root.protocol("WM_DELETE_WINDOW", quit_)
    root.mainloop()
    return True


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="AQROS", description="Air Quality Research OS（デスクトップ版）")
    ap.add_argument("--port", type=int, default=int(os.environ.get("AQROS_PORT", PREFERRED_PORT)))
    ap.add_argument("--no-browser", action="store_true", help="ブラウザを自動で開かない")
    ap.add_argument("--headless", action="store_true", help="操作ウィンドウを出さずコンソールで動かす")
    ap.add_argument("--data-dir", help="利用者データの保存先（既定: OS 標準の利用者データフォルダ）")
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args(argv)

    os.environ["AQROS_DESKTOP"] = "1"
    from app.paths import user_data_dir  # noqa: PLC0415

    if a.data_dir:
        os.environ["AQROS_DATA_DIR"] = str(Path(a.data_dir).expanduser().resolve())
    elif not os.environ.get("AQROS_DATA_DIR"):
        os.environ["AQROS_DATA_DIR"] = str(user_data_dir())
    data_dir = Path(os.environ["AQROS_DATA_DIR"])

    if a.version:
        from app.main import __version__  # noqa: PLC0415
        print(f"Air Quality Research OS {__version__}")
        return 0

    log = setup_logging(data_dir)

    running = probe(a.port)
    if running:  # 二重起動: 既存の画面を開いて終わる
        url = f"http://{HOST}:{a.port}/"
        print(f"すでに起動しています: {url}")
        if not a.no_browser:
            webbrowser.open(url)
        return 0

    port = pick_port(a.port)
    srv = ServerThread(port)
    srv.start()
    url = f"http://{HOST}:{port}/"
    if not wait_ready(port):
        print(f"サーバーの起動に失敗しました。ログ: {log}", file=sys.stderr)
        return 1
    from app.main import __version__  # noqa: PLC0415
    print(f"Air Quality Research OS {__version__}: {url}")
    print(f"データ保存先: {data_dir}")
    if not a.no_browser:
        webbrowser.open(url)

    if not a.headless and control_window(url, data_dir, __version__, srv.stop):
        srv.join(timeout=10)
        return 0
    print("終了するには Ctrl+C を押すか、このウィンドウを閉じてください。")
    try:
        while srv.is_alive():
            srv.join(timeout=0.5)
    except KeyboardInterrupt:
        srv.stop()
        srv.join(timeout=10)
    return 0


if __name__ == "__main__":
    sys.exit(main())
