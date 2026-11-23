#!/usr/bin/env bash
# gpt-consult スキルを別リポジトリへ導入する。
#   使い方: bash .claude/skills/gpt-consult/install.sh /path/to/other-repo
# 既存ファイルは上書き前に確認せず置き換える（スキルディレクトリ内のみ）。リポジトリの他の場所は変更しない。
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="${1:?導入先リポジトリのパスを指定してください}"
[ -d "$TARGET/.git" ] || { echo "Git リポジトリではありません: $TARGET" >&2; exit 1; }

DEST="$TARGET/.claude/skills/gpt-consult"
mkdir -p "$DEST/scripts" "$DEST/tests"
cp "$SRC/SKILL.md" "$SRC/README.md" "$SRC/install.sh" "$SRC/gpt-bridge.example.json" "$DEST/"
cp "$SRC/scripts/gpt_bridge.py" "$DEST/scripts/"
cp "$SRC/tests/test_gpt_bridge.py" "$DEST/tests/"
chmod +x "$DEST/scripts/gpt_bridge.py" "$DEST/install.sh"

python3 -m py_compile "$DEST/scripts/gpt_bridge.py"
( cd "$TARGET" && env -u HTTPS_PROXY -u https_proxy PYTHONDONTWRITEBYTECODE=1 \
    python3 -m unittest discover -s .claude/skills/gpt-consult/tests >/dev/null 2>&1 ) \
  && echo "モックテスト: OK" || { echo "モックテストが失敗しました" >&2; exit 1; }
echo "導入完了: $DEST"
