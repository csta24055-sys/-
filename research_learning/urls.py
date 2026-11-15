"""出典 URL の正規化と安全確認（structlab-exam の exam/links.py の normalize を一般 Web URL 向けに再設計）。

Box 専用の判定は持ち込まない。取得前に、http(s) 以外・認証情報入り・IP 直書き・内部向けの名前を拒否する（SSRF 対策）。
リダイレクト先も同じ関数で再確認すること。
"""
from __future__ import annotations

import ipaddress
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING = re.compile(r"^(utm_|fbclid$|gclid$|mc_eid$|ref_src$)")
INTERNAL = re.compile(r"(^localhost$|\.local$|\.internal$|\.lan$|^metadata\.google\.internal$)")


def normalize(url: str) -> str:
    """追跡用パラメータ（utm_* など）と断片（#...）を除き、scheme/host を小文字にする。"""
    parts = urlsplit(url.strip())
    query = urlencode([(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if not TRACKING.match(k)])
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path or "/", query, ""))


def check_fetchable(url: str) -> tuple[bool, str]:
    try:
        parts = urlsplit(url.strip())
    except ValueError:
        return False, "URL として解釈できない"
    if parts.scheme not in ("http", "https"):
        return False, "http(s) ではない"
    if parts.username or parts.password:
        return False, "URL に認証情報が含まれている"
    host = (parts.hostname or "").lower().rstrip(".")
    if not host or "." not in host:
        return False, "ホスト名が無い・単一ラベル"
    try:
        ipaddress.ip_address(host)
        return False, "IP アドレス直書きは取得しない（内部アドレスへの誘導を防ぐ）"
    except ValueError:
        pass
    if INTERNAL.search(host):
        return False, "内部向けのホスト名"
    return True, ""
