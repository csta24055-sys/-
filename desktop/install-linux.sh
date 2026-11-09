#!/usr/bin/env sh
# Air Quality Research OS — Linux 用の簡易インストール（管理者権限は不要）
# 展開したフォルダの中で:  ./install-linux.sh        （アンインストール: ./install-linux.sh --uninstall）
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"
DEST="${XDG_DATA_HOME:-$HOME/.local/share}/aqros-app"
APPS="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
BIN="$HOME/.local/bin"

if [ "${1:-}" = "--uninstall" ]; then
  rm -rf "$DEST" "$APPS/aqros.desktop" "$BIN/aqros"
  echo "アンインストールしました（利用者データ ~/.local/share/aqros は残しています）。"
  exit 0
fi

mkdir -p "$DEST" "$APPS" "$BIN"
rm -rf "$DEST"/*
cp -R "$HERE"/. "$DEST"/
ln -sf "$DEST/AQROS" "$BIN/aqros"
cat > "$APPS/aqros.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Air Quality Research OS
Comment=室内空気清浄度研究の統合アプリ
Exec=$DEST/AQROS
Icon=$DEST/aqros.png
Terminal=false
Categories=Science;Education;
EOF
echo "インストールしました: アプリ一覧の「Air Quality Research OS」または端末で aqros"
