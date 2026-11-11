# 中断した修正の作業ファイル（点検の後に追加で保存したもの）

停止の直後の保存では、作業用フォルダのファイルを選んで複写した（300 KB 未満で、スナップショット以外のものから、段階ごとに主な出力と報告を選んだ）。
停止後の点検で、段階 a2・b2 の途中のスクリプト・ログ・試行の出力が保存されていないと指摘されたので、ここに追加した。
複写しただけで、どのファイルも実行していない。

**このフォルダのスクリプトは実行しない。** 旧研究のコードを読み込み、旧研究のフォルダを書き換えるものがある。
内容はどれも未検証である。段階 a2 は報告の前に停止したので、a2 の出力は途中のものである。

| 所在 | 内容 |
|---|---|
| `a2/` | 段階 a2（統合の根拠を測定に置き換える作業、統合モデルの再構成）の途中のスクリプト、試行ごとの出力（`membership_check_try1〜3.json`、`mechanism_probe_try1・2.json` など）、命令数と入力の使用の前後比較 |
| `a2/before/`、`a2/shadow_before/`、`a2/dry/` | a2 が編集の前に取ったコードの写しの一部と、試し実行用のファイル（公開中の版や `65ff124` と同じ内容のファイルは、重複するので複写していない） |
| `a2/snap_before.json.gz`、`a2/snap_before_400_60.json.gz` | a2 が編集の前後で結果が変わらないことを確かめるために取った、単位別の結果の要約値の記録（gzip で圧縮）。下の表を参照 |
| `b2/` | 段階 b2（近似検証の測定の修正）のスクリプト、実行ログ（`run1〜4_400.log.txt` など）、試行の出力、報告を作ったスクリプト |

## 圧縮して保存したもの

| 保存したファイル | もとのファイル（作業用フォルダ） | もとの大きさ | 備考 |
|---|---|---|---|
| `a2/snap_before.json.gz` | `a2/snap_before.json` | 5,308,155 バイト | `a2/snap_after1.json`、`a2/snap_after_final.json` は、これと 1 バイトも違わない同じ内容だった（SHA-256 が同じ）。3 つを 1 つにまとめた |
| `a2/snap_before_400_60.json.gz` | `a2/snap_before_400_60.json` | 6,884,323 バイト | `a2/snap_after_400_60.json` は、これと同じ内容だった。2 つを 1 つにまとめた |

## 保存しなかったもの

次の 3 件は保存していない。段階 a1 が、編集の前後で全シナリオの結果を比べるために取った結果の写し（Python の pickle 形式）である。
合計で約 255 MB あり、1 件は Git のホスティングが受け付ける 1 ファイルの上限（100 MB）を超える。pickle は読み込むだけでコードが実行され得る形式でもある。
これらはセッションの一時フォルダにだけあり、セッションの終了とともに消える。作り直すには旧研究のコードの実行が必要で、作り直さない。
a1 がこの比較から得た結論は、`../agent_reports/A1_REPORT.json`（自己申告）にある。

| ファイル（作業用フォルダ `recheck/fix/` から） | 大きさ（バイト） | SHA-256 |
|---|---|---|
| `a1/snap_after1.pkl` | 66,563,624 | `3d373347abcb65945e3b100e2103149384d8385df854593720308f624f29f887` |
| `a1/snap_before.pkl` | 67,141,050 | `4c7b9c243970fece60c6def08edb4c0b07255cc66596b8e3282f21b168c0d282` |
| `a1/snap_after_final.pkl` | 121,745,517 | `4a316f23761bc1d07fc5d843d92d247bfb351c0235063f3532436729ff36b858` |

次の 15 件は、公開中の版、`43ba5d7`、`65ff124` のいずれかに同じ内容のファイルがあるので、複写していない。

- `a1/units_before.json`
- `a1/input_usage_scratch.json`
- `a1/old_tree/synth/model.py`
- `a1/old_tree/synth/population.py`
- `a1/old_tree/synth/__init__.py`
- `a1/old_tree/synth/README.md`
- `a1/old_tree/synth/io.py`
- `a1/old_tree/synth/generate.py`
- `b2/approx_study_before.py`
- `b2/before_400_newref.json`
- `a2/models_before.json`
- `a2/shadow_before/fastcalc/__init__.py`
- `a2/shadow_before/bench/__init__.py`
- `a2/shadow_before/bench/input_usage.py`
- `a2/before/fastcalc/__init__.py`
