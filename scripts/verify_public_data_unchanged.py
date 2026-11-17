"""公開するデータが、いま公開中のものと同じであることを確かめる（読み取りだけ。何も公開しない）。

  python scripts/verify_public_data_unchanged.py frontend/dist-cf                      # 既定: https://aqros-mobile.pages.dev と比べる
  python scripts/verify_public_data_unchanged.py frontend/dist-cf --live https://…     # 比べる先を指定

なぜ要るか:
  公開前の漏えい検査（scripts/build_mobile.py --require-private-list）は、非公開の氏名リストでの照合を必須にしている。
  画面（UI）だけを直したときは、公開されるデータは変わらない。そのことを機械的に確かめられれば、
  「今回の公開で新しく外に出る研究データは無い（以前に氏名リストで検査して公開したものと同じ）」と言える。
  これは氏名リストでの検査の代わりではなく、「データが同じなので再検査が要らない」ことの証明である。データが 1 バイトでも
  違えば不合格にするので、その場合は従来どおり氏名リストでの検査が必要。

確かめること:
  1. 配布物のうち、アプリのコード（index.html, sw.js, assets/*.js, assets/*.css, _worker.js, _headers, 404.html）以外の全ファイルが、
     公開中のサイトの同じパスのファイルと 1 バイトも違わない。data/seed.json は生成時刻（generated_at）だけを除いて同じ。
     公開中のサイトに無いファイルが増えていても不合格。
  2. データの元になるソース（knowledge/, report/, deliverables/, frontend/public/, scripts/knowledge_data.py, scripts/privacy_patterns.py）が、
     基準のブランチ（公開中の版を作ったブランチ）から変わっていない（git diff が空）。
  3. アプリのコードは一般パターン（接続情報・住宅記号・メールアドレスなど）の検査に合格している（build_mobile.py の検査結果）。

結果は JSON で出す（ファイル名とハッシュの先頭だけ。中身は出さない）。終了コード 0 = 同じ。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE_FILES = {"index.html", "sw.js", "_worker.js", "_headers", "404.html", ".nojekyll"}
DATA_SOURCES = ["knowledge", "report", "deliverables", "frontend/public", "scripts/knowledge_data.py", "scripts/privacy_patterns.py"]


def is_code(rel: str) -> bool:
    return rel in CODE_FILES or (rel.startswith("assets/") and rel.endswith((".js", ".css", ".map")))


def fetch(url: str) -> tuple[int, bytes]:
    req = urllib.request.Request(url, headers={"User-Agent": "aqros-deploy-check/1.0", "Cache-Control": "no-cache"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b""


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def same_seed(a: bytes, b: bytes) -> bool:
    try:
        x, y = json.loads(a), json.loads(b)
    except Exception:  # noqa: BLE001
        return False
    x.pop("generated_at", None)
    y.pop("generated_at", None)
    return x == y


def verify(out: Path, live: str, base_ref: str) -> dict:
    live = live.rstrip("/")
    files = sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file())
    data = [f for f in files if not is_code(f)]
    rows, bad = [], []
    for rel in data:
        local = (out / rel).read_bytes()
        status, remote = fetch(live + "/" + urllib.parse.quote(rel))
        if status != 200:
            ok, why = False, f"公開中のサイトに無い（HTTP {status}）"
        elif local == remote:
            ok, why = True, "同一"
        elif rel == "data/seed.json" and same_seed(local, remote):
            ok, why = True, "生成時刻（generated_at）以外は同一"
        else:
            ok, why = False, "内容が違う"
        rows.append({"file": rel, "ok": ok, "result": why, "sha256": sha(local)[:16], "bytes": len(local)})
        if not ok:
            bad.append(rel)
    # データの元になるソースが基準のブランチから変わっていないこと
    diff = subprocess.run(["git", "-C", str(ROOT), "diff", "--name-only", base_ref, "HEAD", "--", *DATA_SOURCES], capture_output=True, text=True)
    changed_sources = [x for x in diff.stdout.splitlines() if x.strip()] if diff.returncode == 0 else None
    dirty = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain", "--", *DATA_SOURCES], capture_output=True, text=True).stdout.strip().splitlines()
    scan_file = out.parent / f"{out.name}-scan.json"
    scan = json.loads(scan_file.read_text(encoding="utf-8")) if scan_file.exists() else None
    code_ok = bool(scan and not scan.get("hits") and not scan.get("forbidden_names") and not scan.get("unreadable"))
    ok = bool(data) and not bad and changed_sources == [] and not dirty and code_ok
    return {"ok": ok, "live": live, "base_ref": base_ref, "data_files": len(data), "data_files_differ": bad, "files": rows,
            "data_sources_changed_since_base": changed_sources, "data_sources_uncommitted": dirty,
            "code_files": [f for f in files if is_code(f)], "code_generic_scan_ok": code_ok,
            "meaning": "公開されるデータは公開中のものと同じ（新しく外に出る研究データは無い）" if ok else "データが公開中のものと違う、または確認できない。氏名リストでの検査が必要"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out", help="build_mobile.py --target cloudflare の出力フォルダー")
    ap.add_argument("--live", default="https://aqros-mobile.pages.dev")
    ap.add_argument("--base-ref", default="origin/claude/air-quality-research-os-19gu2g", help="公開中の版を作ったブランチ（データの元のソースをこれと比べる）")
    ap.add_argument("--json", help="結果を書き出すファイル")
    a = ap.parse_args()
    r = verify(Path(a.out).resolve(), a.live, a.base_ref)
    if a.json:
        Path(a.json).write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in r.items() if k != "files"}, ensure_ascii=False, indent=1))
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
