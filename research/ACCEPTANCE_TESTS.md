# Claude Code向け受け入れテスト

必ず `cd app && npm run check` を実行し、全テストをパスさせた後、次のGUI検証を追加・実施する。

| ID | 操作 | 期待結果 | v0.2 結果 |
|---|---|---|---|
| A01 | アプリを初回起動 | 52件が表示される | ✅ Electron E2E（開発版・Linux配布版）/ ブラウザE2E |
| A02 | 「研究室公式掲載」の絞り込み | 6件だけ表示される | ✅ Electron E2E |
| A03 | 「ピロティ」で検索 | 2023・2024の関連論文が見つかる | ✅ Electron E2E・ユニット |
| A04 | 論文詳細を開く | 著者/掲載誌/年度/出典・全文未登録の状態を確認できる | ✅ Electron E2E |
| A05 | 選択した論文の要約を編集/保存/再起動 | 入力が失われない | ✅ Electron E2E（再起動後に確認） |
| A06 | 分布分析へ移動 | 年度別件数の合計が登録件数に一致 | ✅ Electron E2E（`#yearSum`=52） |
| A07 | カテゴリ分析 | 複数分類での重複計数について注記が見える | ✅ Electron E2E |
| A08 | 新規研究テーマ「旧耐震 RC ピロティ 崩壊」を入力 | 登録論文の実在する候補・検索理由が表示される | ✅ Electron E2E・ユニット |
| A09 | 研究計画の日付と完了状態を編集/再起動 | 入力が保持され、仮予定表示が残る | ✅ Electron E2E（再起動後に確認） |
| A10 | PDFを取り込む（Electron） | `userData/pdfs/` に保存され、対象論文に紐づく／PDFを開ける | ✅ Electron E2E（SHA-256名で保存・内蔵ビューア描画・本文検索・根拠ページ） |
| A11 | JSONバックアップと復元 | データを復元できる（PDF実体は含まないと明示） | ✅ Electron E2E（書出→変更→復元） |
| A12 | Windows/Macで配布ビルド | 生成ファイルの実在、起動・データ書込確認。ビルドできないOSは未検証と記録 | 🟡 Linux AppImage：生成・E2E合格。Windows/macOS：CIで生成＋E2E（実行結果はActionsを参照） |
| A13 | 非公開資料を含まないか確認 | 配布ZIPやインストーラーに無許可PDF・個人データが混ざらない | ✅ `npm run check:dist`（Linux配布物で合格、CIでは全OS） |
| A14 | UIのコンソールを確認 | uncaught error/資源取得失敗がない | ✅ Electron/ブラウザE2Eでエラー0件 |

注意：`npm run check`（ユニット30件）はドメインロジックの検査。GUI検証は `npm run test:e2e`（Playwrightで実際のElectronアプリ13件＋ブラウザ5件）で行う。配布版は `TAJIMA_ELECTRON_BIN=<実行ファイル> npm run test:e2e:electron` で同じ検査を実行する。

追加の自動検査：保存ファイル破損時のバックアップ自動復旧、日本語PDF（CMap使用のCIDフォント）の本文抽出・表示、ブラウザ版の再読み込み後のメモ保持。
