# research_code：検算用のコード

指示書第6章の「基準計算、単位・境界検証、処理速度測定」のための研究用コード。**製品用のエンジンではなく、UI・API・利用者のデータを保存する機能・配布の仕組みを持たない。**（架空シナリオを JSON に書き出して読み戻す検査用の関数 `synth/io.py` はある。）
入力はすべて乱数で作った架空データで、J-CAT その他の実在の原単位・耐用年数・修繕率・漏洩率・倍率は含まない。

Python 3.13、標準ライブラリのみ（`bench/approx_study.py` の回帰 1 か所だけ numpy を使う）。

## 構成

| フォルダ | 役割 |
|---|---|
| `synth/` | 架空の建物シナリオ（入力側だけ）。入力 124 項目すべてを属性に対応付け |
| `refcalc/` | **基準計算**。評価単位ごとに 1 関数、概念式の定義どおりに行ごと・年ごと・事象ごとに計算する。関数の説明文が、その単位の定義（台帳の `reference_semantics`） |
| `fastcalc/` | **候補**。`closed_forms.py`（ループを置き換える閉形式）と `engine.py`（統合モデル：評価期間に依存しない合算 `aggregate` と、乗数を掛けて値を読む `finish`。行った演算の回数を自分で数えて返す） |
| `common/` | 結果の比較（符号付きの相対誤差。過小評価を区別する） |
| `bench/` | 測定：軸 A の負荷（`measure_axis_a.py`）、統合モデルの一致と負荷（`verify_unified.py`。入力を壊す操作は `mutations.py`）、読まれた入力項目（`input_usage.py`）、近似候補の誤差（`approx_study.py`） |
| `tools/` | 台帳とコードの同期、2 軸の集計、検証記録・進捗台帳・レポートの生成 |
| `tests/` | 架空データ、基準計算（手計算との照合、欠陥の検出、境界条件）、閉形式（ループとの一致）、統合モデル（基準計算との一致と、演算の回数） |

## 再現の手順

```
cd research_code
python3 -m unittest discover -s tests -t .      # テスト
python3 -m tools.sync_ledger                    # 台帳の定義・依存・シート族の対応を同期
python3 -m bench.measure_axis_a                 # 軸 A の実測（静かな機械で）
python3 tools/rank_axes.py                      # 2 軸の順位と着手順序
python3 -m bench.verify_unified                 # 統合モデルの一致と負荷
python3 -m bench.input_usage                    # 読まれた入力項目
python3 -m bench.approx_study                   # 近似候補の誤差
python3 -m tools.build_records                  # 単位×段階×候補の記録
python3 tools/progress_ledger.py init && python3 tools/progress_ledger.py merge
python3 tools/progress_ledger.py check && python3 tools/progress_ledger.py report
python3 -m tools.build_reports                  # 各フォルダの README
```

- 記録の生成（`build_records`）は、出力の一致・仕組みの計数・導出のどれかに裏付けのない「成功」や、測定値と矛盾する結論があると失敗する。
- 進捗台帳の検査（`progress_ledger.py check`）は、未実施の段階が残る単位や、測定・導出の裏付けが 1 件もない単位を完了扱いにしていないこと、不採用・候補なし・保留に理由があることを確かめる。
- 計算時間は機械の状態で変わる。軸 A の順位と負荷の測定は、ほかの処理が動いていない状態で実行する。

## 規約

時間の扱い、欠損と検査、結果の形式は `refcalc/base.py` の冒頭にまとめてある。本研究が決めた規約であり、他のツールの仕様を述べるものではない。
