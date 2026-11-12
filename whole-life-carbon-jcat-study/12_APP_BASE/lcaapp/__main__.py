"""Developer command line of the base system:  python3 -m lcaapp <command> ...

  demo                       fictional reference data + one fictional building, stored
  sample --out DIR           write a fictional input document and its reference data as files
  refset add FILE | list     register / list reference data sets
  import FILE                store an input document (new project, or --project ID for a new version)
  projects | runs ID         what is stored
  calc ID --period T         run the existing engine on a stored input and store the result
  show RUN [--html FILE]     show a stored result again (nothing is recomputed)
  serve                      local web screen
  binding | tree FILE        the classification binding in use / summary of a classification tree
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from . import binding as binding_mod
from . import enginepath, render, sample, web
from .service import Service
from .store import Store


def default_db() -> str:
    return os.environ.get("LCAAPP_DB") or os.path.join(enginepath.APP_ROOT, "var", "lcaapp.sqlite3")


def _load(path: str):
    with open(path, encoding="utf-8") as fh:
        return web.parse_json(fh.read())


def _print_run(run: dict) -> None:
    print("計算結果 %d：%s %s" % (run["id"], run["status"], run["message"]))
    if run["view"]:
        for ind in run["view"]["indicators"]:
            value = render.fmt(ind["value"]) if ind["status"] != "not_computed" else render.NOT_COMPUTED
            mark = "（不完全）" if ind["status"] == "incomplete" else ""
            print("  %-28s %s %s%s   [%s]" % (ind["label"], value, ind["unit"] if ind["value"] is not None else "", mark, ind["source"]))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python3 -m lcaapp", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db", default=None, help="保存ファイル（既定：環境変数 LCAAPP_DB、なければ 12_APP_BASE/var/lcaapp.sqlite3）")
    parser.add_argument("--binding", default=None, help="分類との結び付けファイル（lca-binding/1）。省略時は仮の結び付け")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("demo"); p.add_argument("--seed", type=int, default=4201); p.add_argument("--rows", type=int, default=None)
    p = sub.add_parser("sample"); p.add_argument("--out", required=True); p.add_argument("--seed", type=int, default=4201)
    p.add_argument("--structure", default="RC"); p.add_argument("--use", default="office"); p.add_argument("--size", default="S")
    p.add_argument("--rows", type=int, default=12)
    p = sub.add_parser("refset"); p.add_argument("action", choices=("add", "list")); p.add_argument("file", nargs="?")
    p = sub.add_parser("import"); p.add_argument("file"); p.add_argument("--project", type=int); p.add_argument("--name")
    sub.add_parser("projects")
    p = sub.add_parser("runs"); p.add_argument("project", type=int)
    p = sub.add_parser("calc"); p.add_argument("project", type=int); p.add_argument("--period", required=True)
    p.add_argument("--input-version", type=int); p.add_argument("--refset", type=int); p.add_argument("--baseline", type=int)
    p = sub.add_parser("show"); p.add_argument("run", type=int); p.add_argument("--html"); p.add_argument("--json")
    p = sub.add_parser("serve"); p.add_argument("--host", default="127.0.0.1"); p.add_argument("--port", type=int, default=8765)
    p = sub.add_parser("binding"); p.add_argument("--dump")
    p = sub.add_parser("tree"); p.add_argument("file")
    args = parser.parse_args(argv)

    binding = binding_mod.load(args.binding) if args.binding else binding_mod.provisional()
    if args.command == "binding":
        print(json.dumps(dict(binding.describe(), coverage=binding.coverage()), ensure_ascii=False, indent=1))
        if args.dump:
            with open(args.dump, "w", encoding="utf-8") as fh:
                json.dump(binding.to_json(), fh, ensure_ascii=False, indent=1)
        return 0
    if args.command == "tree":
        tree = binding_mod.read_tree(_load(args.file), os.path.basename(args.file))
        cover = binding_mod.tree_coverage(tree, binding)
        print(json.dumps({"categories": tree["categories"], "n_leaves": tree["n_leaves"], "others": tree["others"],
                          "bound": len(cover["bound"]), "unbound": cover["unbound"][:200]}, ensure_ascii=False, indent=1))
        return 0
    if args.command == "sample":
        doc, refset, _ = sample.fictional_building(args.seed, args.structure, args.use, args.size, rows=args.rows, binding=binding)
        os.makedirs(args.out, exist_ok=True)
        for name, obj in (("input_fictional.json", doc), ("refset_fictional.json", refset)):
            with open(os.path.join(args.out, name), "w", encoding="utf-8") as fh:
                json.dump(obj, fh, ensure_ascii=False, indent=1)
            print("書き出した：", os.path.join(args.out, name))
        return 0

    store = Store(args.db or default_db())
    service = Service(store, binding)
    try:
        if args.command == "demo":
            doc, refset, _ = sample.fictional_building(seed=args.seed, rows=args.rows)
            print(json.dumps(service.register_refset(refset), ensure_ascii=False))
            out = service.import_document(doc)
            print("建物プロジェクト %d、入力の版 %d を保存した（架空データ）。" % (out["project_id"], out["input_version_id"]))
        elif args.command == "refset":
            if args.action == "add":
                if not args.file:
                    parser.error("refset add にはファイルが要る")
                print(json.dumps(service.register_refset(_load(args.file)), ensure_ascii=False, indent=1))
            else:
                for r in store.list_refsets():
                    print("%d  %s  版 %s  %s  係数 %d  %s" % (r["id"], r["name"], r["version"], r["data_kind"], r["n_factors"], r["source_note"][:60]))
        elif args.command == "import":
            out = service.import_document(_load(args.file), project_id=args.project, name=args.name)
            print("建物プロジェクト %d、入力の版 %d を保存した。" % (out["project_id"], out["input_version_id"]))
            print(json.dumps(out["summary"]["stats"], ensure_ascii=False))
            for issue in out["issues"][:20]:
                if issue["level"] != "info":
                    print("  [%s] %s %s" % (issue["level"], issue["path"], issue["message"]))
        elif args.command == "projects":
            for p_ in store.list_projects():
                print("%d  %s  %s  入力 %d 版  結果 %d 件  更新 %s" % (p_["id"], p_["name"], p_["data_kind"], p_["n_inputs"], p_["n_runs"], p_["updated_at"]))
        elif args.command == "runs":
            for r in store.list_runs(args.project):
                print("%d  T=%s  第 %d 版  %s  %s  %s" % (r["id"], r["study_period_text"], r["version_no"], r["status"], r["message"][:60], r["created_at"]))
        elif args.command == "calc":
            _print_run(service.calculate(args.project, args.period, args.input_version, args.refset, args.baseline))
        elif args.command == "show":
            page_data = service.run_page(args.run)
            _print_run(page_data["run"])
            if page_data["run"]["view"]:
                for note in page_data["run"]["view"]["notes"]:
                    print("  注記：" + note["text"])
            if args.html:
                with open(args.html, "w", encoding="utf-8") as fh:
                    fh.write(render.run_page(page_data))
                print("書き出した：", args.html)
            if args.json:
                with open(args.json, "w", encoding="utf-8") as fh:
                    json.dump(store.get_run(args.run, with_results=True)["results"], fh, ensure_ascii=False, indent=1)
                print("書き出した：", args.json)
        elif args.command == "serve":
            server = web.serve(service, args.host, args.port)
            print("http://%s:%d/ で待ち受け中（保存ファイル：%s）。終了は Ctrl+C。" % (args.host, server.server_address[1], store.path), flush=True)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
            finally:
                server.server_close()
    finally:
        store.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
