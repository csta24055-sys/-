"""スマホ単体版（PWA・静的ホスティング用）をビルドし、公開前の漏えい検査を行う。

  python scripts/build_mobile.py                    # frontend/dist-mobile/（ルート "/" 配信用）
  python scripts/build_mobile.py --base /aqros/     # サブパス配信（GitHub Pages のプロジェクトサイト等）
  python scripts/build_mobile.py --scan-only DIR    # 既存の出力を検査だけする

公開してよいものだけを同梱する:
- knowledge.json・報告書（report/*.md）・中間統合技術調査報告書・2027年度資料の Markdown（住宅記号は住宅23-n に置換）
- 原データ・private_data/・Box 原文は同梱しない。2027年度資料の docx/pdf は置換できないため同梱しない
検査に失敗したら終了コード 1（デプロイしない）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "backend"))
from privacy_patterns import anonymize, has_private_list, regex  # noqa: E402

FRONT = ROOT / "frontend"
TEXT_EXT = {".js", ".mjs", ".css", ".html", ".json", ".webmanifest", ".md", ".csv", ".txt", ".svg", ".xml"}
FORBIDDEN_NAMES = re.compile(r"(private_data|\.sqlite3?$|\.xlsx?$|\.xlsm$|\.xlsb$|\.pptx?$|raw_)", re.I)


def deep_anon(o):
    if isinstance(o, str):
        return anonymize(o)
    if isinstance(o, list):
        return [deep_anon(x) for x in o]
    if isinstance(o, dict):
        return {k: deep_anon(v) for k, v in o.items()}
    return o


def dashboard_static() -> dict:
    """ダッシュボードの「次の行動」と主要知見 ID をサーバー版と同じにする（FastAPI を一時 DB で呼ぶ）"""
    from fastapi.testclient import TestClient

    from app import main
    with tempfile.TemporaryDirectory() as td:
        main.reset_db(str(Path(td) / "seed.sqlite3"))
        d = TestClient(main.app).get("/api/dashboard").json()
    return {"next_actions": d["next_actions"], "key_findings": [f["id"] for f in d["key_findings"]]}


def build_seed(stage: Path) -> dict:
    k = json.loads((ROOT / "knowledge" / "knowledge.json").read_text(encoding="utf-8"))
    report = []
    for i, f in enumerate(sorted((ROOT / "report").glob("*.md"))):
        body = f.read_text(encoding="utf-8")
        report.append({"id": f.stem, "ord": i, "title": body.splitlines()[0].lstrip("# ").strip() if body else f.stem, "body": body})
    deliv = []
    ddir = stage / "deliverables"
    tr = ROOT / "deliverables" / "technical_report_2026-11"
    for f in sorted(tr.glob("*")):
        if f.is_file() and f.suffix in {".md", ".docx", ".pdf", ".csv"}:
            dst = ddir / "technical_report_2026-11" / f.name
            dst.parent.mkdir(parents=True, exist_ok=True)
            if f.suffix in {".md", ".csv"}:
                dst.write_text(anonymize(f.read_text(encoding="utf-8-sig")), encoding="utf-8-sig" if f.suffix == ".csv" else "utf-8")
            else:
                shutil.copy2(f, dst)
            deliv.append({"name": f"technical_report_2026-11/{f.name}", "group": "technical_report_2026-11", "ext": f.suffix})
    for f in sorted((ROOT / "deliverables").glob("2027_*.md")):
        dst = ddir / f.name
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(anonymize(f.read_text(encoding="utf-8")), encoding="utf-8")
        deliv.append({"name": f.name, "group": "2027", "ext": f.suffix})
    for d in deliv:
        p = ddir / d["name"]
        d["size"] = p.stat().st_size
        d["href"] = "deliverables/" + "/".join(d["name"].split("/"))
    seed = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "knowledge": deep_anon(k), "report": deep_anon(report),
            "deliverables": deliv, "dashboard": deep_anon(dashboard_static())}
    seed["version"] = hashlib.sha256(json.dumps(seed["knowledge"], ensure_ascii=False, sort_keys=True).encode() + json.dumps(seed["report"], ensure_ascii=False).encode()).hexdigest()[:12]
    (stage / "data").mkdir(parents=True, exist_ok=True)
    (stage / "data" / "seed.json").write_text(json.dumps(seed, ensure_ascii=False), encoding="utf-8")
    return seed


def extract_text(p: Path) -> str:
    if p.suffix in TEXT_EXT:
        return p.read_text(encoding="utf-8", errors="replace")
    if p.suffix == ".docx":
        with zipfile.ZipFile(p) as z:
            return " ".join(re.sub(r"<[^>]+>", "", z.read(n).decode("utf-8", "replace")) for n in z.namelist() if n.endswith(".xml"))
    if p.suffix == ".pdf" and shutil.which("pdftotext"):
        return subprocess.run(["pdftotext", str(p), "-"], capture_output=True, text=True).stdout
    return ""


def scan(out: Path, require_private_list: bool = False) -> dict:
    """公開前の漏えい検査。一致した語そのものはログに出さない（件数とファイル名だけ）"""
    rx = re.compile(regex())
    hits, names, unread = [], [], []
    files = [p for p in out.rglob("*") if p.is_file()]
    for p in files:
        rel = p.relative_to(out).as_posix()
        if FORBIDDEN_NAMES.search(rel):
            names.append(rel)
        try:
            txt = extract_text(p)
        except Exception:  # noqa: BLE001
            unread.append(rel)
            continue
        if p.suffix == ".pdf" and not shutil.which("pdftotext"):
            unread.append(rel)
        n = len(rx.findall(txt)) if txt else 0
        if n:
            hits.append({"file": rel, "matches": n})
    priv = has_private_list()
    ok = not hits and not names and not unread and (priv or not require_private_list)
    return {"ok": ok, "files": len(files), "hits": hits, "forbidden_names": names, "unreadable": unread,
            "private_name_list": priv, "note": "" if priv else "非公開の氏名リストが無いため、氏名の検査は一般パターン（住宅記号・接続情報）のみ"}


def build(base: str, out: Path) -> None:
    stage = Path(tempfile.mkdtemp(prefix="aqros-mobile-public-"))
    shutil.copytree(FRONT / "public", stage, dirs_exist_ok=True)
    seed = build_seed(stage)
    env = {**os.environ, "VITE_STANDALONE": "1", "VITE_BASE": base, "AQROS_PUBLIC_DIR": str(stage)}
    npm = "npm.cmd" if os.name == "nt" else "npm"
    subprocess.run([npm, "run", "build", "--", "--outDir", str(out), "--emptyOutDir"], cwd=FRONT, env=env, check=True)
    shutil.copy2(out / "index.html", out / "404.html")   # GitHub Pages 等で直接 URL を開いたときも SPA を返す
    (out / ".nojekyll").write_text("", encoding="utf-8")
    shutil.rmtree(stage, ignore_errors=True)
    print(f"built: {out} (seed {seed['version']}, base {base})")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="/")
    ap.add_argument("--out", default=str(FRONT / "dist-mobile"))
    ap.add_argument("--scan-only")
    ap.add_argument("--require-private-list", action="store_true", help="非公開の氏名リストが無ければ失敗させる（公開デプロイ時）")
    a = ap.parse_args()
    base = a.base if a.base.endswith("/") else a.base + "/"
    out = Path(a.scan_only or a.out).resolve()
    if not a.scan_only:
        build(base, out)
    r = scan(out, a.require_private_list)
    (out.parent / f"{out.name}-scan.json").write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in r.items()}, ensure_ascii=False))
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
