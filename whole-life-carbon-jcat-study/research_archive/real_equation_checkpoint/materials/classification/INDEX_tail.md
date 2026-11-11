## 8. 保存資料の所在

### 8.1 Git の記録（作業ブランチ `claude/jcat-formula-approximation-study-c33936`）

| コミット | 内容 |
|---|---|
| `43ba5d7` | 第1回の検査の指摘を反映し、測定・順位・記録・報告書を再生成した版。コード・測定・記録・報告書が互いに対応している最後の版。第2回の検査はこの版を調べた |
| `60e720f` | 手順書 v1.4 の草稿を加えた版（`00_POLICY/EVALUATION_PROTOCOL.md` だけが `43ba5d7` と違う） |
| `65ff124` | 停止の時点の作業ツリーをそのまま記録した版（中断した修正。未検証・未完成） |
| `0db5c77` | 上の編集を作業ツリーから取り除き、`09_APPROX_STUDY/` を `60e720f` と同じ内容に戻した版 |
| `7bd1d43`、`580d287`、`25f70b8` | 停止の記録、保存資料、受領した停止指示 |
| `b2b8a6e` | 索引と引継ぎ文書（点検の前の版） |
| それ以降 | 点検の指摘の反映、追加で保存した作業ファイル |

### 8.2 旧研究の本体（削除していない）

| 所在 | 内容 |
|---|---|
| `09_APPROX_STUDY/00_POLICY/` | 旧指示書の写し、追加・変更指示、手順書（v1.4 草稿） |
| `09_APPROX_STUDY/01_LEDGER/` | 評価単位 70 件の台帳、シート族の集計、式に未接続だった入力 |
| `09_APPROX_STUDY/02_RANKING/` | 評価軸 A（測定した負荷）、評価軸 B（採点）、着手順序 |
| `09_APPROX_STUDY/03_MODELS/` | 統合モデル K1〜K7、導出 `DERIVATIONS.md`、近似候補、単位別の記録 454 件 |
| `09_APPROX_STUDY/04_VERIFICATION/` | 厳密一致、負荷、入力の使用、近似検証の測定結果、第1回の独立検査の記録 |
| `09_APPROX_STUDY/05_DECISIONS/` | 進捗台帳、採否の理由、旧指示書の必須成果物 |
| `09_APPROX_STUDY/06_OPEN_ISSUES/` | 未解決事項と規約 B-1〜B-21（第2回の指摘は未反映） |
| `09_APPROX_STUDY/07_MATERIAL_TAXONOMY/` | 材料分類の設計草案（データ構造と手順の形だけ。データセットではない） |
| `09_APPROX_STUDY/research_code/` | 基準計算 `refcalc`、統合モデル `fastcalc`、架空データの生成器 `synth`、測定 `bench`、記録と報告書の生成器 `tools`、試験 `tests`、比較 `common` |

### 8.3 この保存フォルダ

**`materials/` の下にある Python のスクリプトは、どれも実行しない。** 多くが旧研究のコードを読み込み、実行は旧研究の計算の再開になる。保存の目的は記録である。

| 所在 | 内容 | 注意 |
|---|---|---|
| `STOP_ORDER.md`、`NEW_DIRECTIVE.md` | 受領した停止・保存の指示（第0章）と、新指示書の全文 | |
| `STOP_STATUS.md` | 停止した対象、確認の結果、残っていたタスク、再開を防ぐ措置 | |
| `HANDOVER.md` | 実施内容、到達点、未完成部分、引継ぎ事項、移行条件の最終確認 | |
| `INDEX.md`、`index_detail/` | この索引と、項目ごとの詳細、指摘 59 件の登録簿 | |
| `materials/round2_review/triage/` | 第2回の独立検査の指摘 59 件の全文（5 観点）と、反証検査担当の判定。`res.json` は構造化した元データ | 指摘の一次資料 |
| `materials/round2_review/checker_scripts/` | 検査担当と反証検査担当が使った再現用のスクリプトとログ | **実行しない** |
| `materials/interrupted_fix/specs/` | 中断した修正の仕様：`COMMON.md`（各段階に共通の指示）、`SPEC_A1.md`、`SPEC_A2.md`、`SPEC_B2.md`、`SPEC_B3.md`、`VERIFY_NUM.md` と `VERIFY_DEF.md`（修正後の反証検査の手順。未実施）、`STAGE_C_NOTES.md`（記録と報告書の改訂の予定。未実施） | 設計の資料。実装の完了や検証を意味しない |
| `materials/interrupted_fix/agent_reports/` | 段階 a1・b2 の作業担当の報告（`A1_REPORT.json`、`B2_REPORT.json`、`B2_REPORT_long.json`）、b2 の結論文の案（`conclusion_proposals.json`、`candidate_lines.json`） | 自己申告。独立の検査なし |
| `materials/interrupted_fix/a1_scratch/` | 段階 a1 の出力と、それを作ったスクリプト | 未検証。**スクリプトは実行しない** |
| `materials/interrupted_fix/a2_partial_outputs/`、`b2_output/` | 段階 a2 の途中の出力、段階 b2 の出力 | 未検証 |
| `materials/interrupted_fix/working_files/` | 点検の後に追加で保存した、段階 a2・b2 の途中のスクリプト・ログ・試行の出力（61 件と、圧縮した比較用の記録 2 件）。保存しなかったものの一覧は、同じフォルダの `README.md` にある | 未検証。**スクリプトは実行しない** |
| `materials/interrupted_fix/working_tree_at_stop_65ff124.patch` | 中断時の編集の差分（`65ff124` と同じ内容） | 適用しない |
| `materials/interrupted_fix/workflow_script_DO_NOT_RUN.js` | 中断した修正のワークフローの定義 | **実行しない** |
| `materials/earlier_session_scratch/` | それ以前の段階の作業用ファイル。`verify/` は第1回の検査の指摘の元データ（`findings_audit.json`、`findings_numeric.json`、`findings_rederive.json`）と検査用のスクリプト。`wfA/`、`wfA_b1b5_work/` は台帳の分析の作業ファイル。`wfB/`、`wfC/` は測定のログと比較用のスクリプト。`wfD/` は材料分類の 3 つの設計案（`design_taxonomy.md`、`design_normalization.md`、`design_selection_effort.md`）とレビューの指摘。`wfD_fix/`、`wfD_synth/` は材料分類の草案の修正と検査に使ったスクリプト。`judge_na/`、`judge_input_data_model/` と最上位のスクリプトは、評価者に渡す入力や報告書の部品を作ったもの。最上位の `approx_old.json` とログは、近似検証の古い版の出力 | 古い版の出力を含む（たとえば `wfB/axis_a_run.log.txt` は初版の測定で、公開中の版の測定ではない）。分類担当は中身を読んでいない。**スクリプトは実行しない**（`wfD_fix/` の一部は `09_APPROX_STUDY/07_MATERIAL_TAXONOMY/` を上書きする） |
| `materials/classification/` | この索引のもとになった分類の JSON（7 観点）、分類担当への指示、点検による訂正の一覧（`overrides.json`）、索引の生成スクリプト、点検の結果（`review/`） | 生成スクリプトは JSON と文書を読むだけで、旧研究のコードを読み込まない |

## 9. この索引が扱っていない範囲

- 分類担当が読まなかったファイルと、読み取りだけでは確かめられなかった点は [index_detail/NOT_COVERED.md](index_detail/NOT_COVERED.md) に観点ごとに載せた。主なもの：中断時の差分（723 KB）の全文、検査担当のスクリプトの中身、単位別の記録 454 件の個々の文面、評価者の理由文の大半、`materials/earlier_session_scratch/` の中身。
- 公開中の版の試験 28 件が今の環境で通るかどうかは確かめていない（第2回の報告書の検査担当は合格を報告している）。
- `65ff124` のコードが試験に通るか、指摘の再現が消えるかは確かめていない。
- 分類担当の読み取りで見つかり、第2回の指摘には無い点が、少なくとも次の 5 つある。いずれも実行による確認はしていない。
  1. X-07 の関数は B2-01 の結果を読むが、依存の一覧に B2-01 が無い。
  2. X-08 は B4-02 を依存に挙げるが、関数の中で読まない。
  3. SYS-01 の目的の欄は「42 単位に渡す」と書くが、該当の欄は空で、実際の関係は別の欄（17 単位）にある。
  4. 「別の評価期間 4 通りで 92.1％ 減」は、統合モデルの側が合算を済ませた後の 4 回分だけを測っている（CK-R3-21）。
  5. 「無効な評価期間は 5/5 でエラー」の 5 件目（500.0）は、無効だからではなく、年次表より長いためにエラーになる（CK-R2-06）。
- 第1章から第8章（`01_COMPLIANCE/` 〜 `08_BUILD_PLAN/`）は、旧研究より前の資料であり、この索引の対象ではない。変更していない。
- 旧研究のフォルダのファイルと、項目の「所在」との対応は、索引の生成時に機械的に照合した。結果は [HANDOVER.md](HANDOVER.md) の 5 節に記した。
