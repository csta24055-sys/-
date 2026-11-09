#!/usr/bin/env bash
# 研究台帳の再生成とテスト一式（ローカル／CI共通）
set -euo pipefail
cd "$(dirname "$0")/.."
python3 research/tools/scaffold.py            # 非破壊：不足分だけ作成
python3 research/research_gates.py --write    # ゲート判定・状態ファイル・1,920スロット台帳を更新
python3 research/tools/render_views.py         # 台帳→Markdownビュー
python3 research/tools/build_app.py            # 台帳→アプリ用JSON
python3 -m unittest discover -s research/tests
node research/tests/app_smoke.js               # Chromiumでアプリを操作して SMOKE_TEST_RESULT.json を書く
python3 research/research_gates.py --write    # アプリ結果を反映して最終判定
python3 research/tools/build_app.py
