# PyInstaller 設定 — Air Quality Research OS デスクトップ版
# 使い方（リポジトリ直下で）:  python desktop/build.py   （frontend のビルド → PyInstaller → 配布用アーカイブ）
# 同梱するのは公開リポジトリに入っている成果物だけ。private_data/ は絶対に同梱しない。
import re
import sys
from pathlib import Path

ROOT = Path(SPECPATH).resolve().parent
ASSETS = ROOT / "desktop" / "assets"
VERSION = re.search(r'__version__ = "([^"]+)"', (ROOT / "backend" / "app" / "main.py").read_text(encoding="utf-8")).group(1)
DELIV_EXT = {".md", ".docx", ".pdf", ".csv"}


def tree(src: Path, dest: str):
    return [(str(p), str(Path(dest) / p.relative_to(src).parent)) for p in src.rglob("*") if p.is_file()]


datas = []
datas += [(str(ROOT / "knowledge" / "knowledge.json"), "knowledge")]
datas += [(str(p), "report") for p in sorted((ROOT / "report").glob("*.md"))]
datas += tree(ROOT / "frontend" / "dist", "frontend/dist")
datas += [(str(p), "deliverables") for p in sorted((ROOT / "deliverables").glob("*")) if p.is_file() and p.suffix in DELIV_EXT - {".csv"}]
tr = ROOT / "deliverables" / "technical_report_2026-11"
datas += [(str(p), "deliverables/technical_report_2026-11") for p in sorted(tr.glob("*")) if p.is_file() and p.suffix in DELIV_EXT]
assert not any("private_data" in s for s, _ in datas), "private_data must never be bundled"
assert (ROOT / "frontend" / "dist" / "index.html").exists(), "frontend をビルドしてください（cd frontend && npm run build）"

hidden = ["uvicorn.logging", "uvicorn.loops.auto", "uvicorn.protocols.http.auto", "uvicorn.protocols.http.h11_impl",
          "uvicorn.protocols.websockets.auto", "uvicorn.lifespan.on", "multipart", "python_multipart", "openpyxl"]

a = Analysis(
    [str(ROOT / "desktop" / "aqros_desktop.py")],
    pathex=[str(ROOT / "backend")],
    datas=datas,
    hiddenimports=hidden,
    excludes=["matplotlib", "IPython", "pytest", "_pytest", "notebook", "scipy", "PyQt5", "PySide6", "sphinx"],
    noarchive=False,
)
pyz = PYZ(a.pure)
icon = str(ASSETS / ("aqros.ico" if sys.platform.startswith("win") else "aqros.png"))
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="AQROS",
    console=False,          # 操作ウィンドウ（tkinter）を使う。--headless 時もログは利用者データフォルダへ
    icon=icon,
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name="AQROS", upx=False)
if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="AQROS.app",
        icon=icon,
        bundle_identifier="local.aqros.desktop",
        info_plist={"CFBundleDisplayName": "Air Quality Research OS", "CFBundleShortVersionString": VERSION, "CFBundleVersion": VERSION,
                    "NSHighResolutionCapable": True, "LSApplicationCategoryType": "public.app-category.education",
                    "LSMinimumSystemVersion": "14.0"},
    )
