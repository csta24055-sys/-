"""スマホ版を Cloudflare Pages（プロジェクト aqros-mobile）に公開する。

  python scripts/deploy_cloudflare.py            # ビルド → 漏えい検査（不合格なら中止）→ 公開 → 公開先の応答確認

必要な設定（値はリポジトリ・ログに出さない）:
  CLOUDFLARE_API_TOKEN   Pages 編集権限のトークン（Claude Code のクラウド環境ではプロキシが付けるので不要）
  CLOUDFLARE_ACCOUNT_ID  省略時はトークンで見えるアカウントが 1 つならそれを使う
  AQROS_CF_PROJECT       既定 aqros-mobile

静的ファイルは _worker.js に埋め込み、Pages のデプロイ API 1 回で公開する（scripts/build_mobile.py --target cloudflare）。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = "https://api.cloudflare.com/client/v4"
OUT = ROOT / "frontend" / "dist-cf"


def call(method: str, path: str, body: bytes | None = None, ctype: str | None = None) -> dict:
    tok = os.environ.get("CLOUDFLARE_API_TOKEN") or "proxy-injected"
    req = urllib.request.Request(API + path, data=body, method=method, headers={"Authorization": f"Bearer {tok}", **({"Content-Type": ctype} if ctype else {})})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            d = json.loads(r.read())
    except urllib.error.HTTPError as e:
        d = json.loads(e.read() or b"{}")
    if not d.get("success"):
        raise SystemExit(f"Cloudflare API {method} {path.split('?')[0]}: {[x.get('message') for x in d.get('errors', [])]}")
    return d["result"]


def multipart(fields: dict[str, str], files: dict[str, tuple[str, bytes, str]]) -> tuple[bytes, str]:
    b = uuid.uuid4().hex
    parts = []
    for k, v in fields.items():
        parts.append(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    for k, (fn, data, ct) in files.items():
        parts.append(f'--{b}\r\nContent-Disposition: form-data; name="{k}"; filename="{fn}"\r\nContent-Type: {ct}\r\n\r\n'.encode() + data + b"\r\n")
    parts.append(f"--{b}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={b}"


def main() -> int:
    project = os.environ.get("AQROS_CF_PROJECT", "aqros-mobile")
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "build_mobile.py"), "--target", "cloudflare", "--out", str(OUT), "--require-private-list"])
    if r.returncode != 0:
        print("漏えい検査またはビルドに失敗したため公開しません")
        return 1
    acc = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    if not acc:
        accs = call("GET", "/accounts?per_page=50")
        if len(accs) != 1:
            raise SystemExit("アカウントが複数あります。CLOUDFLARE_ACCOUNT_ID を指定してください")
        acc = accs[0]["id"]
    names = [p["name"] for p in call("GET", f"/accounts/{acc}/pages/projects")]
    if project not in names:
        call("POST", f"/accounts/{acc}/pages/projects", json.dumps({"name": project, "production_branch": "main"}).encode(), "application/json")
        print(f"created project {project}")
    commit = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    body, ct = multipart({"manifest": "{}", "branch": "main", "commit_message": f"AQROS mobile {commit}"},
                         {"_worker.js": ("_worker.js", (OUT / "_worker.js").read_bytes(), "application/javascript+module")})
    dep = call("POST", f"/accounts/{acc}/pages/projects/{project}/deployments", body, ct)
    for _ in range(40):
        st = call("GET", f"/accounts/{acc}/pages/projects/{project}/deployments/{dep['id']}")["latest_stage"]
        if st["name"] == "deploy" and st["status"] in ("success", "failure"):
            break
        time.sleep(5)
    if st["status"] != "success":
        raise SystemExit(f"デプロイ失敗: {st}")
    url = f"https://{project}.pages.dev"
    for p in ("/", "/settings", "/manifest.webmanifest", "/data/seed.json", "/sw.js"):
        # Cloudflare は Python 既定の User-Agent を拒否するため名乗る
        with urllib.request.urlopen(urllib.request.Request(url + p, headers={"User-Agent": "aqros-deploy-check/1.0"}), timeout=30) as resp:
            print(resp.status, p)
    print(f"deployed: {url} (commit {commit}, deployment {dep['id'][:8]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
