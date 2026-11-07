#!/usr/bin/env bash
# 建築設備Ⅲ 第1回：動画取得後の解析〜PDF生成を一括実行する。
# usage: bash run_all.sh <lec1.mp4> <work_dir>
#   動画は Dropbox「/授業資料(動画、pdf)/建築設備/第一回/動画 2026-10-30 6 27 43.mp4」
#   （Dropbox の一時ダウンロードリンク等で取得し、content_hash で完全性を確認すること）
# 必要: ffmpeg, python3 (faster-whisper numpy pillow), node + playwright, pdfinfo, npm
set -euo pipefail
VIDEO=$(realpath "$1"); WORK=$(realpath -m "$2"); HERE=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$WORK"; cd "$WORK"
# 1) 音声抽出 (16kHz mono)
[ -f audio.wav ] || ffmpeg -v error -y -i "$VIDEO" -vn -ac 1 -ar 16000 audio.wav
# 2) 一次文字起こし（全編）
[ -f asr/transcript.txt ] || python3 "$HERE/transcribe.py" audio.wav asr
# 3) スライド抽出（3秒間隔→切替検出）
[ -f frames/slides.csv ] || python3 "$HERE/extract_slides.py" "$VIDEO" frames 3
# 4) 重要区間の二次照合（large-v3）
[ -f asr/verify_largev3.txt ] || python3 "$HERE/verify_segments.py" audio.wav asr/verify_largev3.txt
# 5) フォント取得と PDF 生成
if [ ! -d fonts/package/files ]; then mkdir -p fonts && (cd fonts && npm pack @fontsource/noto-sans-jp@5.0.19 --silent && tar xzf fontsource-noto-sans-jp-5.0.19.tgz); fi
NODE_PATH=$(npm root -g) node "$HERE/build_pdf.js" "$WORK/fonts/package/files" "$HERE/../建築設備_第1回_要点整理_A4_2枚.pdf"
