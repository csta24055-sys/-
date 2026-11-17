"""スマホ版を Cloudflare Pages（プロジェクト aqros-mobile）に公開する。

  python scripts/deploy_cloudflare.py                    # ビルド → 漏えい検査（氏名リスト必須。不合格なら中止）→ 公開 → 公開先の応答確認
  python scripts/deploy_cloudflare.py --data-unchanged   # 画面だけを直したとき用: 氏名リストの代わりに「公開データが公開中のものと同じ」ことを確かめてから公開
  python scripts/deploy_cloudflare.py --dry-run          # 公開の直前まで（ビルドと検査だけ）

--data-unchanged について:
  氏名リスト（private_data/privacy_patterns.txt または AQROS_PRIVACY_PATTERNS）が手元に無い環境でも、
  scripts/verify_public_data_unchanged.py が「アプリのコード以外の全ファイルが公開中のサイトと 1 バイトも違わない」
  「データの元のソースが基準のブランチから変わっていない」「コードは一般パターンの検査に合格」を確かめられたときだけ公開する。
  データが少しでも違えば中止する（その場合は氏名リストでの検査が必要）。検証の記録は frontend/dist-cf-data-unchanged.json に残る。

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
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-unchanged", action="store_true", help="氏名リストの代わりに、公開データが公開中のものと同じことを確かめる（画面だけの変更用）")
    ap.add_argument("--dry-run", action="store_true", help="ビルドと検査だけ行い、公開しない")
    a = ap.parse_args()
    project = os.environ.get("AQROS_CF_PROJECT", "aqros-mobile")
    build = [sys.executable, str(ROOT / "scripts" / "build_mobile.py"), "--target", "cloudflare", "--out", str(OUT)]
    r = subprocess.run(build + ([] if a.data_unchanged else ["--require-private-list"]))
    if r.returncode != 0:
        print("漏えい検査またはビルドに失敗したため公開しません")
        return 1
    if a.data_unchanged:
        v = subprocess.run([sys.executable, str(ROOT / "scripts" / "verify_public_data_unchanged.py"), str(OUT), "--live", f"https://{project}.pages.dev",
                            "--json", str(OUT.parent / f"{OUT.name}-data-unchanged.json")])
        if v.returncode != 0:
            print("公開データが公開中のものと同じであることを確かめられなかったため公開しません（氏名リストでの検査が必要です）")
            return 1
    if a.dry_run:
        print("dry-run: 検査に合格しました（公開はしていません）")
        return 0
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
