"""python3 -B -m wlcstudio [--var DIR] {serve,demo,validate,ledger}"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parents[1]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="wlcstudio", description="WLC Studio（研究用の試作）")
    ap.add_argument("--var", default=str(HERE / "var"), help="保存先（既定：23_WLC_STUDIO_APP/var、Git に入れない）")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("serve", help="ローカルのサーバーを起動（127.0.0.1 のみ）")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8770)
    s.add_argument("--keep-uploads", action="store_true", help="読み込んだ資料の原本を var/uploads に残す（既定は残さない）")
    d = sub.add_parser("demo", help="架空デモのプロジェクトを作って計算する")
    d.add_argument("--period", type=float, default=60.0)
    v = sub.add_parser("validate", help="材料の統計概算の精度検証（RASMI の元データ、取り置き検証）")
    v.add_argument("--out", default=str(HERE / "docs"))
    so = sub.add_parser("sources", help="データ源の権利台帳を表示")
    so.add_argument("--md", help="Markdown にして書き出すファイル")
    lg = sub.add_parser("ledger", help="入力の対応表（4 画面 → エンジン入力、未接続台帳）を表示")
    lg.add_argument("--md", help="Markdown にして書き出すファイル")
    a = ap.parse_args(argv)
    if a.cmd == "serve":
        from .server import serve
        serve(a.var, a.host, a.port, a.keep_uploads)
        return 0
    if a.cmd == "demo":
        from .server import App
        app = App(a.var)
        _, r = app.handle("POST", "/api/demo", {})
        _, out = app.handle("POST", "/api/projects/%d/calculate" % r["id"], {"period": a.period})
        s = out.get("summary") or {}
        print(json.dumps({"project_id": r["id"], "status": out["status"], "message": out["message"],
                          "total_t": s.get("total_t"), "complete": s.get("complete"), "incomplete_units": s.get("incomplete_units"),
                          "factor_note": out["factor_note"], "trace": out["trace"]}, ensure_ascii=False, indent=1))
        return 0 if out["status"] == "ok" else 1
    if a.cmd == "validate":
        from .validate import main as vmain
        return vmain(a.out)
    if a.cmd == "sources":
        from . import estimate
        if a.md:
            Path(a.md).write_text(estimate.registry_markdown(), encoding="utf-8")
            print(a.md)
        else:
            print(json.dumps(estimate.registry(), ensure_ascii=False, indent=1))
        return 0
    if a.cmd == "ledger":
        from . import bridge
        if a.md:
            Path(a.md).write_text(bridge.ledger_markdown(), encoding="utf-8")
            print(a.md)
        else:
            print(json.dumps(bridge.binding_coverage(), ensure_ascii=False, indent=1))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
