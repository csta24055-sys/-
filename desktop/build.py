"""デスクトップ版をビルドして配布用アーカイブを作る（実行した OS 向けのものだけ作れる）。

  python desktop/build.py              # frontend ビルド → PyInstaller → dist_desktop/ にアーカイブ
  python desktop/build.py --skip-frontend

出力（dist_desktop/）:
  Windows: AQROS-<ver>-windows-x64.zip   （展開して AQROS.exe。インストーラーは CI で Inno Setup により作成）
  macOS  : AQROS-<ver>-macos-<arch>.zip  （AQROS.app）
  Linux  : AQROS-<ver>-linux-x64.tar.gz （AQROS/AQROS と install-linux.sh）
"""
from __future__ import annotations

import argparse
import platform
import re
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "dist_desktop"


def version() -> str:
    m = re.search(r'__version__ = "([^"]+)"', (ROOT / "backend" / "app" / "main.py").read_text(encoding="utf-8"))
    return m.group(1) if m else "0.0.0"


def run(cmd, cwd=ROOT):
    print("+", " ".join(map(str, cmd)), flush=True)
    subprocess.run(cmd, cwd=cwd, check=True, shell=(sys.platform.startswith("win") and cmd[0] == "npm"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-frontend", action="store_true")
    ap.add_argument("--print-version", action="store_true", help="版番号だけを表示（CI のインストーラー作成用）")
    a = ap.parse_args()
    if a.print_version:
        print(version())
        return 0
    if not a.skip_frontend:
        if not (ROOT / "frontend" / "node_modules").exists():
            run(["npm", "ci"], cwd=ROOT / "frontend")
        run(["npm", "run", "build"], cwd=ROOT / "frontend")
    work = ROOT / "build_desktop"
    run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--distpath", str(work / "dist"),
         "--workpath", str(work / "work"), str(ROOT / "desktop" / "aqros.spec")])
    OUT.mkdir(exist_ok=True)
    ver = version()
    arch = {"x86_64": "x64", "amd64": "x64", "arm64": "arm64", "aarch64": "arm64"}.get(platform.machine().lower(), platform.machine().lower())
    dist = work / "dist"
    if sys.platform.startswith("win"):
        out = shutil.make_archive(str(OUT / f"AQROS-{ver}-windows-{arch}"), "zip", dist, "AQROS")
    elif sys.platform == "darwin":
        out = str(OUT / f"AQROS-{ver}-macos-{arch}.zip")
        # ditto はシンボリックリンクと拡張属性を保ったまま .app を圧縮する
        run(["ditto", "-c", "-k", "--sequesterRsrc", "--keepParent", str(dist / "AQROS.app"), out])
    else:
        shutil.copy2(ROOT / "desktop" / "install-linux.sh", dist / "AQROS" / "install-linux.sh")
        shutil.copy2(ROOT / "desktop" / "assets" / "aqros.png", dist / "AQROS" / "aqros.png")
        out = str(OUT / f"AQROS-{ver}-linux-{arch}.tar.gz")
        with tarfile.open(out, "w:gz") as t:
            t.add(dist / "AQROS", arcname="AQROS")
    print("built:", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
