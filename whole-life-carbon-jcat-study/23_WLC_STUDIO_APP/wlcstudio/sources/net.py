"""Small HTTP helper for the public data connectors: a disk cache, a polite rate limit, Range requests.

Only sources listed in registry.json with automated access allowed may use this. The cache lives in
`cache/` (not in Git). Nothing personal is sent: requests carry only the query the user asked for
(an address or a coordinate) and a generic User-Agent.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

USER_AGENT = "WLCStudio/0.1 (research prototype; +local)"
CACHE = Path(os.environ.get("WLCSTUDIO_CACHE", Path(__file__).resolve().parents[2] / "cache"))
_last: dict[str, float] = {}
MIN_INTERVAL = 1.0          # seconds between requests to the same host
OFFLINE = os.environ.get("WLCSTUDIO_OFFLINE") == "1"


class SourceError(RuntimeError):
    """A source could not be reached or answered with something unusable. The message is shown to the user."""


def _wait(host: str) -> None:
    t = _last.get(host, 0.0) + MIN_INTERVAL - time.monotonic()
    if t > 0:
        time.sleep(t)
    _last[host] = time.monotonic()


def _key(url: str, rng: tuple[int, int] | None) -> Path:
    h = hashlib.sha256((url + ("|%d-%d" % rng if rng else "")).encode()).hexdigest()
    return CACHE / h[:2] / h


def get(url: str, rng: tuple[int, int] | None = None, timeout: float = 30.0, max_age: float = 30 * 86400,
        use_cache: bool = True) -> tuple[bytes, dict]:
    """GET a URL (optionally a byte range). Returns (body, meta) where meta has fetched_at and from_cache."""
    p = _key(url, rng)
    if use_cache and p.exists() and (time.time() - p.stat().st_mtime) < max_age:
        meta = json.loads(p.with_suffix(".json").read_text()) if p.with_suffix(".json").exists() else {}
        return p.read_bytes(), dict(meta, from_cache=True)
    if OFFLINE:
        raise SourceError("オフライン設定のため取得していない（WLCSTUDIO_OFFLINE=1）")
    host = urllib.parse.urlparse(url).netloc
    _wait(host)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    if rng:
        req.add_header("Range", "bytes=%d-%d" % rng)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read()
            status = r.status
    except urllib.error.HTTPError as e:
        raise SourceError("取得できなかった（%s が HTTP %d を返した）" % (host, e.code)) from None
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise SourceError("取得できなかった（%s に接続できない：%s）" % (host, getattr(e, "reason", e))) from None
    if rng and status != 206:
        body = body[rng[0]:rng[1] + 1]
    # the metadata keeps only the host (never the query string, which may hold an address or a coordinate)
    meta = {"host": host, "range": list(rng) if rng else None, "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "status": status}
    if use_cache:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(body)
        p.with_suffix(".json").write_text(json.dumps(meta))
    return body, dict(meta, from_cache=False)


def get_json(url: str, **kw) -> tuple[object, dict]:
    body, meta = get(url, **kw)
    try:
        return json.loads(body.decode("utf-8")), meta
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise SourceError("応答が JSON でない（%s）" % urllib.parse.urlparse(url).netloc) from None


_ENTRY = re.compile(r"^[0-9a-f]{64}(\.json)?$")
PERSONAL = ("AddressSearch", "LonLatToAddress")


def sweep(max_age: float = 400 * 86400) -> int:
    """Clean the cache at server start. Only files that look like cache entries (<2 hex>/<64 hex>[.json]) are touched:
    entries older than max_age are removed; entries of an address search or a reverse geocode written by an older
    version (which cached them) are removed whatever their age; any old metadata that still holds the request URL is
    rewritten without it. Returns the number of files removed."""
    n = 0
    if not CACHE.exists():
        return 0
    now = time.time()
    for p in CACHE.glob("??/*"):
        if not (p.is_file() and _ENTRY.match(p.name) and re.fullmatch(r"[0-9a-f]{2}", p.parent.name)):
            continue
        if p.suffix == ".json":
            try:
                meta = json.loads(p.read_text())
            except (OSError, ValueError):
                meta = {}
            url = str(meta.get("url") or "")
            if any(k in url for k in PERSONAL):
                for q in (p, p.with_suffix("")):
                    try:
                        q.unlink()
                        n += 1
                    except OSError:
                        pass
                continue
            if "url" in meta:
                meta.pop("url")
                meta.setdefault("host", urllib.parse.urlparse(url).netloc)
                p.write_text(json.dumps(meta))
        if p.exists() and now - p.stat().st_mtime > max_age:
            try:
                p.unlink()
                n += 1
            except OSError:
                pass
    return n
