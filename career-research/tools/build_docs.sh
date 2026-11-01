#!/usr/bin/env bash
# Markdown → 閲覧用PDF（表紙・目次・ページ番号）＋編集用Word を生成する。
# 使い方: tools/build_docs.sh <mdディレクトリ> <出力ディレクトリ>
# 依存: pandoc、Playwright同梱のChromium、IPAゴシック
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SRC="$1"; OUT="$2"; mkdir -p "$OUT"
for md in "$SRC"/*.md; do
  base="$(basename "$md" .md)"
  pandoc "$md" --toc --toc-depth=2 --resource-path="$SRC" -o "$OUT/$base.docx"
  pandoc "$md" -s --toc --toc-depth=2 --resource-path="$SRC" \
    -c "$HERE/print.css" --embed-resources -o "$OUT/$base.html"
  node "$HERE/html2pdf.js" "$OUT/$base.html" "$OUT/$base.pdf"
  rm -f "$OUT/$base.html"
  echo "built $base"
done
