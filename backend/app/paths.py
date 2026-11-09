"""リソース／利用者データの置き場所を一か所で決める。

- 開発時（リポジトリから起動）: リソース = リポジトリ直下、DB = private_data/aqros.sqlite3（従来どおり）
- 配布版（PyInstaller で凍結）: リソース = 同梱フォルダ（sys._MEIPASS）、
  DB = OS 標準の利用者データフォルダ（Windows: %APPDATA%\\AQROS、macOS: ~/Library/Application Support/AQROS、
  Linux: $XDG_DATA_HOME/aqros または ~/.local/share/aqros）
- 環境変数 AQROS_DB / AQROS_DATA_DIR で上書きできる。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "AQROS"


def frozen() -> bool:
    return bool(getattr(sys, "frozen", False)) and hasattr(sys, "_MEIPASS")


def resource_root() -> Path:
    if frozen():
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parents[2]


def user_data_dir(platform: str | None = None, env: dict[str, str] | None = None, home: Path | None = None) -> Path:
    env = os.environ if env is None else env
    if env.get("AQROS_DATA_DIR"):
        return Path(env["AQROS_DATA_DIR"])
    platform = platform or sys.platform
    home = home or Path.home()
    if platform.startswith("win"):
        base = Path(env["APPDATA"]) if env.get("APPDATA") else home / "AppData" / "Roaming"
        return base / APP_NAME
    if platform == "darwin":
        return home / "Library" / "Application Support" / APP_NAME
    base = Path(env["XDG_DATA_HOME"]) if env.get("XDG_DATA_HOME") else home / ".local" / "share"
    return base / APP_NAME.lower()


def default_db_path() -> Path:
    if frozen() or os.environ.get("AQROS_DATA_DIR"):
        return user_data_dir() / "aqros.sqlite3"
    return resource_root() / "private_data" / "aqros.sqlite3"
