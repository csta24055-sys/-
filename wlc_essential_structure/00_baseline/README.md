# 00 凍結した基準

本研究が読んだ旧研究の版と、読んだファイルの SHA-256：[frozen_sources.json](frozen_sources.json)（`tools/freeze_baseline.py` が生成）。

| 用途 | リポジトリ・ブランチ | コミット |
|---|---|---|
| 旧研究の全章・研究エンジン・凍結した基準計算・667 式の公開台帳 | `csta24055-sys/-` `claude/jcat-lca-app-foundation-c33936` | `761da13d6cab68eb76a7bd7eba0262b82b7fde29` |
| 70 単位の役割・依存の台帳（研究基盤） | 同 `claude/wlc-theory-research-base-c33936` | `9416a1bbb3c48d6fd9589789dcb045c0eb6e03be` |
| 同梱 ZIP のコミット（参考） | 同上の研究ブランチ | `98be9f4a0cb6879f3d69be441323ac4589462cb9`（`761da13` との差は `23_WLC_STUDIO_APP/web/index.html` の 3 行） |

旧研究の基準計算そのもの（`09_APPROX_STUDY/research_code/refcalc`）は旧コードの `baseline.assert_frozen()` が Git のツリー識別子で凍結版であることを確かめる。本研究はそれを読むだけで、旧ブランチには何も書いていない。
