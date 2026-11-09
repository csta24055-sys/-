"""静的配信の確認用サーバー（GitHub Pages と同じく、存在しないパスには 404.html を返す）

  python scripts/serve_static.py frontend/dist-mobile 47801
"""
from __future__ import annotations

import functools
import http.server
import sys
from pathlib import Path


class Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map, ".webmanifest": "application/manifest+json", ".js": "text/javascript"}

    def send_error(self, code, message=None, explain=None):
        if code == 404 and (Path(self.directory) / "404.html").exists():
            body = (Path(self.directory) / "404.html").read_bytes()
            self.send_response(404)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)
            return
        super().send_error(code, message, explain)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    d, port = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 47801
    http.server.ThreadingHTTPServer(("127.0.0.1", port), functools.partial(Handler, directory=d)).serve_forever()
