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
| A12 | Windows/Macで配布ビルド | 生成ファイルの実在、起動・データ書込確認。ビルドできないOSは未検証と記録 | ✅ GitHub Actions run 42551033367（2026-11-09）：Windows（NSIS+portable）・macOS（dmg+zip, arm64/x64）・Linux（AppImage）を生成し、各OSで**配布版バイナリに対しE2E 13件合格**（macOSはarm64版で実行。x64版は起動未検証）。未署名のため初回起動時のOS警告は残る |
| A13 | 非公開資料を含まないか確認 | 配布ZIPやインストーラーに無許可PDF・個人データが混ざらない | ✅ `npm run check:dist`（Linux配布物で合格、CIでは全OS） |
| A14 | UIのコンソールを確認 | uncaught error/資源取得失敗がない | ✅ Electron/ブラウザE2Eでエラー0件 |

注意：`npm run check`（ユニット30件）はドメインロジックの検査。GUI検証は `npm run test:e2e`（Playwrightで実際のElectronアプリ13件＋ブラウザ5件）で行う。配布版は `TAJIMA_ELECTRON_BIN=<実行ファイル> npm run test:e2e:electron` で同じ検査を実行する。

追加の自動検査：保存ファイル破損時のバックアップ自動復旧、日本語PDF（CMap使用のCIDフォント）の本文抽出・表示、ブラウザ版の再読み込み後のメモ保持。

## スマートフォン（iPhone / Android）— Webアプリ（PWA）v0.3

公開URL：**https://tajima-lab.pages.dev**（Cloudflare Pages、HTTPS）。インストール方法は「URLを開いてホーム画面に追加」のみ。

| ID | 確認内容 | 期待結果 | Android Chrome相当（Chromium＋Pixel 7） | iPhone Safari相当（WebKit 26.6＋iPhone 15） |
|---|---|---|---|---|
| M01 | 初回アクセス | 52件・下部タブ・横スクロールなし・OS別の追加案内 | ✅ | ✅ |
| M02 | インストール条件 | manifest（short_name「田嶋研究室」・standalone）・専用アイコン（192/512/maskable・apple-touch-icon 180px）・Service Worker有効 | ✅ | ✅ |
| M03 | 論文検索・年度/分野の絞り込み | 「ピロティ」で2023・2024、年度・分野で絞り込み | ✅ | ✅ |
| M04 | PDF取り込み・閲覧・本文検索 | ファイル選択から取り込み、端末内保存、画面幅に合わせて表示、英語/日本語本文で一致ページへ | ✅ | ✅ |
| M05 | データ保存・再起動 | 要約メモ・PDFが再読み込み後も残る（IndexedDB） | ✅ | ✅ |
| M06 | 研究スケジュール | 完了・日付の編集が再読み込み後も残る、仮予定の表示 | ✅ | ✅ |
| M07 | 分布グラフ | 年度別合計＝登録件数、分野別の重複計数注記 | ✅ | ✅ |
| M08 | 新規テーマから先行研究 | 実在する登録論文の候補と理由 | ✅ | ✅ |
| M09 | オフライン | 通信が無い状態でアプリを開き直しても起動・検索・PDF閲覧 | ✅ | ✅ |
| M10 | バックアップ・復元 | 共有シート（ファイルに保存）とダウンロードの両経路でJSON作成→復元 | ✅ | ✅ |
| M11 | 設定画面 | 保存場所・オフライン状態・両OSの追加手順・外部送信なしの説明 | ✅ | ✅ |
| M12 | エラー | コンソールエラー・未捕捉例外・読み込み失敗が0件 | ✅ | ✅ |
| M13 | インストール→独立画面で起動 | ホーム画面のアプリとして standalone 表示 | ✅ **実際のChromiumでPWAとしてインストールし、standaloneウィンドウで起動**（インストール可能判定エラー0件） | ✅ standalone時の画面（navigator.standaloneを模擬）。実際のiOS「ホーム画面に追加」は下記のiOSシミュレーター確認 |

- 上表は**公開中のURL（https://tajima-lab.pages.dev）に対して26件すべて合格**（2026-11-09）。同じテストをローカルのビルド（Cloudflareと同じ `/index.html → /` リダイレクトを再現するサーバー）でも26件合格。
- 実行：`TAJIMA_URL=https://tajima-lab.pages.dev xvfb-run -a npm run test:e2e:mobile`（URL省略時はローカルビルド）。スクリーンショット：`docs/screenshots/mobile/`。
- **iOSシミュレーター（実際のMobile Safari）**：`.github/workflows/ios-safari.yml` で「Safariで開く → 共有 → ホーム画面に追加 → 「田嶋研究室」アイコンから起動 → standalone判定」を自動操作する（結果はGitHub Actionsの `ios-safari-check` を参照）。
- **実機（物理的なiPhone・Android端末）での確認は未実施**です。上記はすべて自動テスト・エミュレーション・シミュレーターです。実機では README の手順で追加し、①アイコンと名前「田嶋研究室」②アイコンから独立画面で開く ③PDF取り込み ④機内モードでの起動 を確認してください。

公開中に見つけて修正した不具合：Cloudflare Pagesは `/index.html` を `/` へリダイレクトするため、Service Worker が「リダイレクトされた応答」をキャッシュし、アプリを開き直すと読み込みに失敗していた（ローカルのテストサーバーでは再現しなかった）。キャッシュ時にリダイレクトを除いた応答を保存し、起動URLを `./` に変更して解決。ローカルのテストサーバーも同じリダイレクトを再現するよう変更した。
