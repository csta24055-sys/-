#!/usr/bin/env python3
"""One-time Dropbox OAuth offline authorization with GitHub Secret storage.

Never prints authorization codes, access/refresh tokens, app secrets or PATs.
This is deliberately separate from calculation and storage workflows.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import nacl.public

GITHUB = "https://api.github.com"
DROPBOX_AUTH = "https://api.dropbox.com/oauth2/token"
DROPBOX_META = "https://api.dropboxapi.com/2"
DROPBOX_CONTENT = "https://content.dropboxapi.com/2"


class AuthSetupError(Exception):
    """Error string contains no credentials."""


def require_env(names: list[str]) -> dict[str, str]:
    values = {name: os.environ.get(name, "").strip() for name in names}
    missing = [name for name, value in values.items() if not value]
    if missing:
        raise AuthSetupError("Missing GitHub Actions Secrets: " + ", ".join(missing))
    return values


def http_json(url: str, *, method: str = "POST", data: bytes | None = None,
              headers: dict[str, str] | None = None, service: str = "Remote API") -> dict:
    try:
        with urlopen(Request(url, data=data, headers=headers or {}, method=method), timeout=45) as response:
            payload = response.read()
        result = json.loads(payload)
        if not isinstance(result, dict):
            raise AuthSetupError(f"{service} returned unexpected JSON")
        return result
    except HTTPError as exc:
        # NEVER echo arbitrary API error messages; some can reflect request data.
        status = exc.code
        raise AuthSetupError(f"{service} HTTP {status}; check credentials, permissions and code validity") from None
    except (URLError, TimeoutError) as exc:
        raise AuthSetupError(f"{service} network request failed") from None
    except (ValueError, UnicodeError):
        raise AuthSetupError(f"{service} returned invalid JSON") from None


def github_headers(pat: str) -> dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {pat}",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def gh_secret_key(repo: str, pat: str) -> dict:
    info = http_json(f"{GITHUB}/repos/{repo}/actions/secrets/public-key", method="GET",
                     headers=github_headers(pat), service="GitHub Secrets public-key API")
    if not info.get("key") or not info.get("key_id"):
        raise AuthSetupError("GitHub Secrets public key is unavailable")
    return info


def dropbox_exchange(code: str, key: str, secret: str) -> tuple[str, str]:
    payload = urlencode({
        "code": code,
        "grant_type": "authorization_code",
        "client_id": key,
        "client_secret": secret,
    }).encode("utf-8")
    info = http_json(DROPBOX_AUTH, data=payload,
                     headers={"Content-Type": "application/x-www-form-urlencoded"},
                     service="Dropbox OAuth code exchange")
    refresh, access = info.get("refresh_token"), info.get("access_token")
    if not isinstance(refresh, str) or not refresh or not isinstance(access, str) or not access:
        raise AuthSetupError("Dropbox did not return an offline refresh token. Check token_access_type=offline")
    scopes = info.get("scope")
    if scopes is not None and "files.content.write" not in str(scopes).split():
        raise AuthSetupError("Dropbox app approval lacks files.content.write")
    return refresh, access


def check_dropbox_write(access: str) -> str:
    """Prove Dropbox file upload and server-side content hash, no Actions artifact."""
    meta_headers = {"Authorization": f"Bearer {access}", "Content-Type": "application/json"}
    try:
        http_json(f"{DROPBOX_META}/files/create_folder_v2",
                  data=json.dumps({"path": "/GitHubActions", "autorename": False}).encode(),
                  headers=meta_headers, service="Dropbox folder creation")
    except AuthSetupError as error:
        # For a duplicate, separately prove the directory exists; never accept any
        # 409 without checking metadata for .tag == folder.
        if "HTTP 409" not in str(error):
            raise
        info = http_json(f"{DROPBOX_META}/files/get_metadata",
                         data=json.dumps({"path": "/GitHubActions"}).encode(),
                         headers=meta_headers, service="Dropbox folder lookup")
        if info.get(".tag") != "folder":
            raise AuthSetupError("/GitHubActions exists but is not a folder")

    runid = os.environ.get("GITHUB_RUN_ID", "manual")
    attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
    path = f"/GitHubActions/auth-check-{runid}-{attempt}.txt"
    contents = (f"GitHub Actions to Dropbox OAuth check\nrun={runid}\nattempt={attempt}\n").encode()
    saved = http_json(f"{DROPBOX_CONTENT}/files/upload", data=contents,
                      headers={
                          "Authorization": f"Bearer {access}",
                          "Content-Type": "application/octet-stream",
                          "Dropbox-API-Arg": json.dumps({
                              "path": path, "mode": "add", "autorename": False,
                              "mute": True,
                          }, separators=(",", ":")),
                      }, service="Dropbox smoke-file upload")
    expected_hash = hashlib.sha256(hashlib.sha256(contents).digest()).hexdigest()
    if saved.get("size") != len(contents) or saved.get("content_hash") != expected_hash:
        raise AuthSetupError("Dropbox upload response failed independent size/content-hash verification")
    return path


def gh_store_refresh(repo: str, pat: str, public_key: dict, refresh: str) -> None:
    key_bytes = base64.b64decode(public_key["key"], validate=True)
    if len(key_bytes) != 32:
        raise AuthSetupError("Invalid GitHub Secret public key length")
    sealed = nacl.public.SealedBox(nacl.public.PublicKey(key_bytes))
    encoded = base64.b64encode(sealed.encrypt(refresh.encode("utf-8"))).decode("ascii")
    url = f"{GITHUB}/repos/{repo}/actions/secrets/DROPBOX_REFRESH_TOKEN"
    headers = {**github_headers(pat), "Content-Type": "application/json"}
    payload = json.dumps({"encrypted_value": encoded, "key_id": public_key["key_id"]}).encode()
    try:
        with urlopen(Request(url, data=payload, headers=headers, method="PUT"), timeout=45) as res:
            status = res.status
    except HTTPError as exc:
        raise AuthSetupError(f"GitHub Secrets write HTTP {exc.code}. GH_SECRETS_TOKEN needs Secrets: read/write") from None
    except (URLError, TimeoutError):
        raise AuthSetupError("GitHub Secrets write network error") from None
    if status not in (201, 204):
        raise AuthSetupError(f"Unexpected GitHub Secrets write status {status}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("preflight", "exchange"))
    args = parser.parse_args()

    secrets = require_env(["DROPBOX_APP_KEY", "DROPBOX_APP_SECRET", "GH_SECRETS_TOKEN"])
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if repo != "csta24055-sys/-":
        raise AuthSetupError("Repository mismatch. This helper is restricted to csta24055-sys/-")

    pubkey = gh_secret_key(repo, secrets["GH_SECRETS_TOKEN"])
    print("GitHub Secrets access: public key read succeeded")
    if args.mode == "preflight":
        print("Preflight OK. Next: add DROPBOX_AUTH_CODE and run mode=exchange immediately.")
        print("Note: GitHub Secrets WRITE permission is verified only in exchange mode.")
        return

    code = require_env(["DROPBOX_AUTH_CODE"])["DROPBOX_AUTH_CODE"]
    refresh, access = dropbox_exchange(code, secrets["DROPBOX_APP_KEY"], secrets["DROPBOX_APP_SECRET"])
    path = check_dropbox_write(access)
    print(f"Dropbox test file stored with matching size/hash at: {path}")
    gh_store_refresh(repo, secrets["GH_SECRETS_TOKEN"], pubkey, refresh)
    print("SUCCESS: DROPBOX_REFRESH_TOKEN was saved in this repository's GitHub Actions Secrets.")
    print("Next: DELETE temporary Secrets DROPBOX_AUTH_CODE and GH_SECRETS_TOKEN; keep app key/secret/refresh token.")


if __name__ == "__main__":
    try:
        main()
    except AuthSetupError as error:
        print(f"::error::{error}", file=sys.stderr)
        raise SystemExit(1) from None
