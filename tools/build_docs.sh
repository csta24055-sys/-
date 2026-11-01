#!/usr/bin/env bash
# research/ 配下の各章Markdownから、編集用docxと閲覧用pdfを dist/ に生成する。
# 依存：pandoc、chromium（Playwright同梱）、IPAゴシック。Mermaid図はコードブロックのまま出力する（GitHub上では描画される）。
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/dist"; mkdir -p "$OUT"
CSS="$ROOT/tools/print.css"
find "$ROOT/research" -mindepth 2 -name '*.md' | sort | while read -r md; do
  base="$(basename "$md" .md)"
  pandoc "$md" -o "$OUT/$base.docx"
  pandoc "$md" -s --metadata pagetitle="$base" -c "$CSS" --embed-resources -o "$OUT/$base.html"
  node "$ROOT/tools/html2pdf.js" "$OUT/$base.html" "$OUT/$base.pdf"
  rm -f "$OUT/$base.html"
  echo "built $base"
done
