#!/usr/bin/env python3
"""Copy local workflow outputs to Dropbox without using GitHub Actions artifacts.

Required GitHub Actions secrets:
 DROPBOX_APP_KEY, DROPBOX_APP_SECRET, DROPBOX_REFRESH_TOKEN
The Dropbox app needs files.content.write (+ files.content.read if downloading).
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

CHUNK = 8 * 1024 * 1024
SMALL = 150 * 1024 * 1024


def request(url, body=b"", headers=None):
    try:
        with urlopen(Request(url, data=body, headers=headers or {}, method="POST"), timeout=120) as response:
            return response.read()
    except HTTPError as exc:
        details = exc.read(1200).decode("utf-8", "replace")
        raise RuntimeError(f"Dropbox API HTTP {exc.code}: {details}") from None


def access_token():
    key = os.getenv("DROPBOX_APP_KEY", "")
    secret = os.getenv("DROPBOX_APP_SECRET", "")
    refresh = os.getenv("DROPBOX_REFRESH_TOKEN", "")
    if not all((key, secret, refresh)):
        raise RuntimeError("Dropbox OAuth credentials are not configured. No upload attempted.")
    auth = base64.b64encode(f"{key}:{secret}".encode()).decode()
    body = urlencode({"grant_type": "refresh_token", "refresh_token": refresh}).encode()
    data = request("https://api.dropbox.com/oauth2/token", body, {
        "Authorization": "Basic " + auth,
        "Content-Type": "application/x-www-form-urlencoded",
    })
    return json.loads(data)["access_token"]


def content_hash(filename):
    """Dropbox's SHA256 of concatenated 4MiB block SHA256 digests."""
    overall = hashlib.sha256()
    with Path(filename).open("rb") as file:
        while part := file.read(4 * 1024 * 1024):
            overall.update(hashlib.sha256(part).digest())
    return overall.hexdigest()


def ensure_parents(token, remote_path):
    if not remote_path.startswith("/") or ".." in remote_path.split("/"):
        raise ValueError("Remote path must be absolute and must not contain '..'")
    bits = remote_path.strip("/").split("/")[:-1]
    current = ""
    for bit in bits:
        current += "/" + bit
        try:
            request("https://api.dropboxapi.com/2/files/create_folder_v2",
                    json.dumps({"path": current, "autorename": False}).encode(), {
                        "Authorization": "Bearer " + token,
                        "Content-Type": "application/json",
                    })
        except RuntimeError as error:
            if "path/conflict/folder" not in str(error):
                raise


def upload_call(token, endpoint, data, args):
    return request("https://content.dropboxapi.com/2/files/" + endpoint, data, {
        "Authorization": "Bearer " + token,
        "Content-Type": "application/octet-stream",
        "Dropbox-API-Arg": json.dumps(args, separators=(",", ":")),
    })


def upload(filename, remote_path):
    local = Path(filename)
    if not local.is_file():
        raise FileNotFoundError(local)
    token = access_token()
    ensure_parents(token, remote_path)
    size = local.stat().st_size
    commit = {"path": remote_path, "mode": "overwrite", "autorename": False, "mute": True}
    with local.open("rb") as file:
        if size <= SMALL:
            metadata = json.loads(upload_call(token, "upload", file.read(), commit))
        else:
            first = file.read(CHUNK)
            session = json.loads(upload_call(token, "upload_session/start", first, {"close": False}))["session_id"]
            offset = len(first)
            while size - offset > CHUNK:
                part = file.read(CHUNK)
                upload_call(token, "upload_session/append_v2", part, {
                    "cursor": {"session_id": session, "offset": offset}, "close": False,
                })
                offset += len(part)
            metadata = json.loads(upload_call(token, "upload_session/finish", file.read(), {
                "cursor": {"session_id": session, "offset": offset}, "commit": commit,
            }))
    if metadata.get("size") != size or metadata.get("content_hash") != content_hash(local):
        raise RuntimeError("Dropbox size/hash mismatch! Upload NOT verified.")
    print(f"Dropbox copy verified: {local.name} ({size} bytes)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    parser.add_argument("--remote", required=True)
    args = parser.parse_args()
    upload(args.file, args.remote)


if __name__ == "__main__":
    main()
