#!/usr/bin/env bash
# judgment-loop（と依存する gpt-consult）を別リポジトリへ導入する。
#   使い方: bash .claude/skills/judgment-loop/install.sh /path/to/other-repo
# 導入するのはコードだけ。判断基準・本人情報・履歴（非公開ホーム）はコピーしない。
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="${1:?導入先リポジトリのパスを指定してください}"
[ -d "$TARGET/.git" ] || { echo "Git リポジトリではありません: $TARGET" >&2; exit 1; }

bash "$SRC/../gpt-consult/install.sh" "$TARGET"

DEST="$TARGET/.claude/skills/judgment-loop"
mkdir -p "$DEST/scripts" "$DEST/tests" "$DEST/modes"
cp "$SRC/SKILL.md" "$SRC/README.md" "$SRC/install.sh" "$DEST/"
cp "$SRC/scripts/orchestrator.py" "$SRC/scripts/review.py" "$DEST/scripts/"
cp "$SRC/modes/"*.json "$DEST/modes/"
cp "$SRC/tests/test_orchestrator.py" "$DEST/tests/"
chmod +x "$DEST/scripts/orchestrator.py" "$DEST/install.sh"

( cd "$TARGET" && env -u HTTPS_PROXY -u https_proxy PYTHONDONTWRITEBYTECODE=1 \
    python3 -m unittest discover -s .claude/skills/judgment-loop/tests >/dev/null 2>&1 ) \
  && echo "judgment-loop モックテスト: OK" || { echo "モックテストが失敗しました" >&2; exit 1; }
echo "導入完了: $DEST"
