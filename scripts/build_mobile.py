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
SOURCE_RAW = os.environ.get("AQROS_SOURCE_RAW", "https://github.com/csta24055-sys/-/raw/claude/air-quality-research-os-19gu2g")
MIME = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8",
        ".json": "application/json; charset=utf-8", ".webmanifest": "application/manifest+json; charset=utf-8", ".svg": "image/svg+xml",
        ".png": "image/png", ".md": "text/markdown; charset=utf-8", ".csv": "text/csv; charset=utf-8", ".txt": "text/plain; charset=utf-8"}
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


def build_seed(stage: Path, target: str = "github") -> dict:
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
            elif target == "cloudflare":
                # 大容量の docx/pdf はエッジスクリプトに入れず、公開リポジトリ上の同じファイルへリンクする
                deliv.append({"name": f"technical_report_2026-11/{f.name}", "group": "technical_report_2026-11", "ext": f.suffix,
                              "size": f.stat().st_size, "href": f"{SOURCE_RAW}/deliverables/technical_report_2026-11/{f.name}"})
                continue
            else:
                shutil.copy2(f, dst)
            deliv.append({"name": f"technical_report_2026-11/{f.name}", "group": "technical_report_2026-11", "ext": f.suffix})
    for f in sorted((ROOT / "deliverables").glob("2027_*.md")):
        dst = ddir / f.name
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(anonymize(f.read_text(encoding="utf-8")), encoding="utf-8")
        deliv.append({"name": f.name, "group": "2027", "ext": f.suffix})
    for d in deliv:
        if "href" in d:
            continue
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


CF_HEADERS = """/sw.js
  Cache-Control: no-cache
/index.html
  Cache-Control: no-cache
/manifest.webmanifest
  Cache-Control: no-cache
/data/*
  Cache-Control: no-cache
/assets/*
  Cache-Control: public, max-age=31536000, immutable
/*
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  X-Frame-Options: DENY
  Permissions-Policy: camera=(), microphone=(), geolocation=()
  Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self' https://api.github.com; worker-src 'self'; manifest-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'
"""


WORKER_JS = r"""// 自動生成（scripts/build_mobile.py --target cloudflare）。スマホ版の静的ファイルをそのまま返すだけのエッジスクリプト
const F = __FILES__;
const SEC = __SEC__;
const LONG = 'public, max-age=31536000, immutable';
const b64 = (s) => Uint8Array.from(atob(s), (c) => c.charCodeAt(0));
export default {
  async fetch(request) {
    if (request.method !== 'GET' && request.method !== 'HEAD') return new Response('Method Not Allowed', { status: 405, headers: SEC });
    const url = new URL(request.url);
    let p; try { p = decodeURIComponent(url.pathname); } catch { p = url.pathname; }
    if (p.endsWith('/')) p += 'index.html';
    let f = F[p];
    if (!f) {
      if (/\.[A-Za-z0-9]+$/.test(p)) return new Response('Not Found', { status: 404, headers: SEC });
      f = F['/index.html'];  // 画面の URL（/settings など）はアプリ本体を返す
      p = '/index.html';
    }
    const h = new Headers(SEC);
    h.set('content-type', f[0]);
    h.set('etag', f[3]);
    h.set('cache-control', p.startsWith('/assets/') ? LONG : 'no-cache');
    if (request.headers.get('if-none-match') === f[3]) return new Response(null, { status: 304, headers: h });
    return new Response(request.method === 'HEAD' ? null : (f[1] === 'b' ? b64(f[2]) : f[2]), { status: 200, headers: h });
  },
};
"""

SEC_HEADERS = {
    "x-content-type-options": "nosniff", "referrer-policy": "strict-origin-when-cross-origin", "x-frame-options": "DENY",
    "permissions-policy": "camera=(), microphone=(), geolocation=()",
    "content-security-policy": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; "
                               "connect-src 'self' https://api.github.com; worker-src 'self'; manifest-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
}


def make_worker(out: Path) -> Path:
    import base64
    files = {}
    for p in sorted(out.rglob("*")):
        if not p.is_file() or p.name in {"_headers", "_worker.js", ".nojekyll"}:
            continue
        rel = "/" + p.relative_to(out).as_posix()
        data = p.read_bytes()
        ct = MIME.get(p.suffix, "application/octet-stream")
        etag = '"' + hashlib.sha256(data).hexdigest()[:16] + '"'
        if ct.startswith(("text/", "application/json", "application/manifest", "image/svg")):
            files[rel] = [ct, "t", data.decode("utf-8"), etag]
        else:
            files[rel] = [ct, "b", base64.b64encode(data).decode("ascii"), etag]
    js = WORKER_JS.replace("__FILES__", json.dumps(files, ensure_ascii=False)).replace("__SEC__", json.dumps(SEC_HEADERS))
    w = out / "_worker.js"
    w.write_text(js, encoding="utf-8")
    return w


def build(base: str, out: Path, target: str = "github") -> None:
    stage = Path(tempfile.mkdtemp(prefix="aqros-mobile-public-"))
    shutil.copytree(FRONT / "public", stage, dirs_exist_ok=True)
    seed = build_seed(stage, target)
    env = {**os.environ, "VITE_STANDALONE": "1", "VITE_BASE": base, "AQROS_PUBLIC_DIR": str(stage)}
    npm = "npm.cmd" if os.name == "nt" else "npm"
    subprocess.run([npm, "run", "build", "--", "--outDir", str(out), "--emptyOutDir"], cwd=FRONT, env=env, check=True)
    if target == "cloudflare":
        # Cloudflare Pages: 404.html が無いと SPA として index.html を返す。キャッシュと安全のためのヘッダーを付ける
        # CSP の connect-src は自サイトと GitHub API（クラウド解析）だけ。端末内のトークンを他所へ送れないようにする
        (out / "_headers").write_text(CF_HEADERS, encoding="utf-8")
        w = make_worker(out)
        print(f"edge script: {w} ({w.stat().st_size // 1024} KB)")
    else:
        shutil.copy2(out / "index.html", out / "404.html")   # GitHub Pages 等で直接 URL を開いたときも SPA を返す
        (out / ".nojekyll").write_text("", encoding="utf-8")
    shutil.rmtree(stage, ignore_errors=True)
    print(f"built: {out} (seed {seed['version']}, base {base})")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="/")
    ap.add_argument("--out", default=str(FRONT / "dist-mobile"))
    ap.add_argument("--scan-only")
    ap.add_argument("--target", choices=["github", "cloudflare"], default="github", help="配信先（SPA の扱いとヘッダーが異なる）")
    ap.add_argument("--require-private-list", action="store_true", help="非公開の氏名リストが無ければ失敗させる（公開デプロイ時）")
    a = ap.parse_args()
    base = a.base if a.base.endswith("/") else a.base + "/"
    out = Path(a.scan_only or a.out).resolve()
    if not a.scan_only:
        build(base, out, a.target)
    r = scan(out, a.require_private_list)
    (out.parent / f"{out.name}-scan.json").write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in r.items()}, ensure_ascii=False))
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
