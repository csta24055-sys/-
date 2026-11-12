"""Local web screen (standard library ``http.server``): project list, project page, result page.

``App.handle`` does the work and does not depend on sockets, so tests call it directly.
A request can never end the server: every error becomes an error page.
"""
from __future__ import annotations

import json
import traceback
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

from . import common, refdata, render, sample
from .service import Service
from .store import StoreError

MAX_BODY = 80 * 1024 * 1024
HTML = "text/html; charset=utf-8"


def parse_json(text: str) -> Any:
    """JSON text -> object; NaN and Infinity become text so that they are reported, not computed."""
    return json.loads(text, parse_constant=lambda name: name)


class Response:
    def __init__(self, status: int, body: str | bytes = "", content_type: str = HTML, location: str | None = None):
        self.status, self.content_type, self.location = status, content_type, location
        self.body = body.encode("utf-8") if isinstance(body, str) else body


def _int(form: dict, key: str) -> int | None:
    value = (form.get(key) or "").strip()
    try:
        return int(value) if value else None
    except ValueError:
        return None


class App:
    def __init__(self, service: Service):
        self.service = service

    # ---- pages -----------------------------------------------------------------------------------
    def index(self, message: str = "") -> Response:
        store = self.service.store
        return Response(200, render.index_page(store.list_projects(), store.list_refsets(), message))

    def project(self, project_id: int, message: str = "", status: int = 200) -> Response:
        store = self.service.store
        project = store.get_project(project_id)
        inputs = store.list_inputs(project_id)
        detail = None
        if inputs:
            data = store.get_input(inputs[-1]["id"])["common"]
            detail = {"issues": data["issues"], "unsupported": data["unsupported"], "others": data["others"]}
        baselines = []
        for other in store.list_projects():
            for version in store.list_inputs(other["id"])[-3:]:
                if not (inputs and version["id"] == inputs[-1]["id"]):
                    baselines.append({"id": version["id"], "label": "%s 第 %d 版" % (other["name"], version["version_no"])})
        return Response(status, render.project_page(project, inputs, store.list_runs(project_id), detail,
                                                    store.list_refsets(), baselines[:50], message))

    # ---- actions ---------------------------------------------------------------------------------
    def _import(self, form: dict, project_id: int | None) -> Response:
        text = form.get("document") or ""
        if not text.strip():
            message = "入力 JSON が空である。"
            return self.project(project_id, message, 400) if project_id is not None else Response(400, self.index(message).body)
        try:
            doc = parse_json(text)
            out = self.service.import_document(doc, project_id=project_id, name=(form.get("name") or "").strip() or None)
        except (ValueError, common.InputError) as exc:
            message = "入力 JSON を読めなかった：%s" % exc
            return self.project(project_id, message, 400) if project_id is not None else Response(400, self.index(message).body)
        return Response(303, location="/project/%d" % out["project_id"])

    def _demo(self, form: dict) -> Response:
        seed = _int(form, "seed")
        if seed is None:
            return Response(400, self.index("シードは整数で指定する。").body)
        doc, refset, _ = sample.fictional_building(seed=seed, rows=None)
        self.service.register_refset(refset)
        out = self.service.import_document(doc)
        return Response(303, location="/project/%d" % out["project_id"])

    def handle(self, method: str, path: str, form: dict | None = None) -> Response:
        form = form or {}
        parts = [p for p in urllib.parse.urlsplit(path).path.split("/") if p]
        try:
            if method == "GET" and not parts:
                return self.index()
            if method == "POST" and parts == ["import"]:
                return self._import(form, None)
            if method == "POST" and parts == ["demo"]:
                return self._demo(form)
            if len(parts) >= 2 and parts[0] in ("project", "run") and parts[1].isdigit():
                ident = int(parts[1])
                if parts[0] == "project":
                    if method == "GET" and len(parts) == 2:
                        return self.project(ident)
                    if method == "POST" and parts[2:] == ["import"]:
                        self.service.store.get_project(ident)
                        return self._import(form, ident)
                    if method == "POST" and parts[2:] == ["calculate"]:
                        run = self.service.calculate(ident, form.get("study_period", ""), _int(form, "input_version_id"),
                                                     _int(form, "reference_set_id"), _int(form, "baseline_input_version_id"))
                        return Response(303, location="/run/%d" % run["id"])
                elif method == "GET" and len(parts) == 2:
                    return Response(200, render.run_page(self.service.run_page(ident)))
                elif method == "GET" and parts[2:] == ["results.json"]:
                    run = self.service.store.get_run(ident, with_results=True)
                    body = json.dumps({"run_id": run["id"], "status": run["status"], "versions": run["versions"],
                                       "results": run["results"]}, ensure_ascii=False, indent=1)
                    return Response(200, body, "application/json; charset=utf-8")
            return Response(404, render.error_page(404, "そのページはない。"))
        except StoreError as exc:
            return Response(404, render.error_page(404, str(exc)))
        except refdata.RefsetError as exc:
            return Response(400, render.error_page(400, str(exc)))
        except Exception as exc:                                  # never let a request end the server
            traceback.print_exc()
            return Response(500, render.error_page(500, "処理中にエラーが起きた（%s: %s）" % (type(exc).__name__, exc)))


def make_handler(app: App):
    class Handler(BaseHTTPRequestHandler):
        server_version = "lcaapp"

        def _send(self, response: Response) -> None:
            self.send_response(response.status)
            if response.location:
                self.send_header("Location", response.location)
            self.send_header("Content-Type", response.content_type)
            self.send_header("Content-Length", str(len(response.body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(response.body)

        def do_GET(self):                                         # noqa: N802 (name fixed by the base class)
            self._send(app.handle("GET", self.path))

        def do_POST(self):                                        # noqa: N802
            origin, host = self.headers.get("Origin"), self.headers.get("Host")
            if origin and host and urllib.parse.urlsplit(origin).netloc != host:
                return self._send(Response(403, render.error_page(403, "別のサイトからの送信は受け付けない。")))
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                length = -1
            if length < 0 or length > MAX_BODY:
                return self._send(Response(413, render.error_page(413, "送信されたデータが大きすぎる。")))
            raw = self.rfile.read(length).decode("utf-8", errors="replace")
            if (self.headers.get("Content-Type") or "").startswith("application/json"):
                form = {"document": raw}
            else:
                form = {k: v[-1] for k, v in urllib.parse.parse_qs(raw, keep_blank_values=True).items()}
            self._send(app.handle("POST", self.path, form))

        def log_message(self, fmt, *args):                        # quiet by default
            pass

    return Handler


def serve(service: Service, host: str = "127.0.0.1", port: int = 8765) -> HTTPServer:
    return HTTPServer((host, port), make_handler(App(service)))
