# 空気清浄度研究（Air Quality Research OS）スマホ版 — 使い方と構成

iPhone・Android で、PC を起動せずに研究アプリを使うための PWA（ホーム画面に追加して使う Web アプリ）です。
App Store / Google Play への登録はしません。

## 1. 構成

```
スマホ（PWA）── 端末内で完結 ─┬─ 研究資料・文献・ナレッジ・報告書（公開データ seed.json を同梱）
                              ├─ CSV / Excel 解析・シミュレーター（TypeScript。Python 版と数値一致をテスト）
                              └─ 編集・取込データ・研究計画・学習記録 → IndexedDB（端末内のみ）＋バックアップ JSON
        │
        └─ 重い処理のみ ─→ GitHub API（利用者のトークン）─→ ジョブ用ブランチ aqros-job/<id>
                              → GitHub Actions（cloud-jobs.yml）→ cloud/run_job.py → 結果をブランチに保存 → スマホが取得 → ブランチ削除
```

- **公開する PWA 本体**と**非公開の研究データ**を分離しています。PWA に入るのは、公開リポジトリにすでにある集計値・要約・報告書だけです。
  2023 年度の住宅記号は「住宅23-n」に置き換えます。原データ、Box の原文、2027 年度資料の docx/pdf（置換できないため）は入れません。
- ビルドのたびに漏えい検査（`scripts/build_mobile.py`）を行い、不合格なら公開しません。氏名などの検査語はリポジトリに書かず、`private_data/privacy_patterns.txt` または Secrets `AQROS_PRIVACY_PATTERNS` から読みます。
- GitHub のトークンはアプリに埋め込みません。利用者が設定画面で入力し、その端末の IndexedDB にだけ保存します（バックアップにも含めません）。

## 2. URL

| 端末 | URL |
|---|---|
| iPhone（Safari） | **https://aqros-mobile.pages.dev** |
| Android（Chrome） | **https://aqros-mobile.pages.dev**（同じ URL） |

公開先は Cloudflare Pages のプロジェクト `aqros-mobile` で、2026-11-09 に公開しました。公開物は漏えい検査（氏名リストを含む）に合格したものだけです。
- 安全のため、次のヘッダーを付けています。
  - Content-Security-Policy: 通信先を自サイトと api.github.com だけに限る（端末内のトークンを他所へ送れない）
  - X-Frame-Options: DENY、nosniff
- 技術報告書の Word/PDF は容量が大きいので公開サイトには入れず、公開リポジトリ上の同じファイルへリンクしています。

## 3. ホーム画面への追加

**iPhone（Safari）**
1. Safari で上の URL を開く（Chrome など他のブラウザではなく Safari）。
2. 共有ボタン（□↑）→「ホーム画面に追加」→ 名前が「空気清浄度研究」になっていることを確認 →「追加」。
3. ホーム画面のアイコンから起動すると、アドレスバーのない独立した画面で開きます。

**Android（Chrome）**
1. Chrome で URL を開く。
2. 右上の「⋮」→「アプリをインストール」（または「ホーム画面に追加」）→「インストール」。
3. ホーム画面・アプリ一覧の「空気清浄度研究」から起動します。

一度開いたあとは、オフラインでも起動できます（機内モードでも可）。

## 4. スマホ単体で使える機能（サーバー・PC 不要）

| 機能 | 内容 | 保存先 |
|---|---|---|
| 研究ダッシュボード | 資料・知見・未解決問題の集計、完成度表 | 公開データ＋端末内の編集 |
| 研究資料ライブラリ | 95 件の資料検索・絞り込み・状態変更・メモ | 端末内 |
| 国内外文献の検索 | DOI 付き文献の検索 | 公開データ |
| 実験データ解析 | CSV/TSV/Excel(.xlsx) の取込、品質確認、時系列、I/O比、除去効率、差圧–風量、電力–CADR、減衰同定 | 端末内（IndexedDB） |
| 空気清浄シミュレーター | 単室の質量収支、電気集塵機バイパス、多室換気 | 計算のみ |
| 研究ナレッジグラフ | 研究・知見・仮説の関係 | 公開データ |
| 研究テーマ比較・研究計画 | テーマ評価、採否、研究計画の作成・編集 | 端末内 |
| 総合研究レポート | 閲覧・章ごとの編集・Markdown 出力・印刷→PDF、成果物ダウンロード | 端末内 |
| 研究学習モード | 進捗とメモ | 端末内 |
| 設定・バックアップ | バックアップの書き出し・復元（追加／置き換え）、永続保存の依頼、保存量の表示 | ファイル |

- アプリを更新しても、端末内のデータは消えません。新しい版が届くと「更新する」ボタンが表示されます。
- ただし、端末の容量不足やブラウザのデータ消去で失われることはあります。**バックアップを定期的に書き出してください**。データを入れて未バックアップのまま 7 日を過ぎると、画面上部に表示が出ます。

## 5. GitHub 側で処理する機能（クラウド解析）

| ジョブ | 処理 | 公開リポジトリで | 非公開リポジトリで |
|---|---|---|---|
| 大規模パラメータ計算 | バイパス（台数×設定×開度×粒径×外挿則）、単室モデルの格子計算（最大 2 万ケース）→ CSV と要約 | 実行可 | 実行可 |
| 大規模データの詳細解析 | 複数の CSV/Excel を pandas で解析（品質・統計・I/O比・減衰・統合表）→ Excel・Markdown | 合成データのみ | 研究室の許可と利用者の同意があれば実行 |
| 研究レポートの Word / PDF 生成 | pandoc で Word、LibreOffice で PDF | 公開版の報告書のみ | 端末で編集した報告書も可（同意が必要） |
| OCR | Tesseract（日本語＋英語）で PDF・画像を文字起こし | 実行しない | 同意があれば実行 |

研究データの送信可否は、スマホ側と run_job.py の両方で判定します。run_job.py は GitHub が伝える実際のリポジトリ設定を使い、スマホからの申告は信用しません。
ログに出すのは件数と所要時間だけで、Artifacts は使いません。入力ファイルは結果のコミットで削除します。結果を受け取ったら「クラウド側を削除」でブランチごと消します。

### 準備（研究室・利用者が行う）
1. **ジョブ実行用の非公開リポジトリ**（例 `aqros-cloud-jobs`）を作り、このブランチの内容を入れる。少なくとも `.github/workflows/cloud-jobs.yml`、`cloud/`、`backend/`、`scripts/privacy_patterns.py`、`report/` が必要。
2. GitHub の **細粒度アクセストークン**を作る。
   - Repository access: そのリポジトリだけ
   - Permissions: Contents = Read and write、Actions = Read-only（Metadata は自動）
   - 有効期限: 短め（例: 90 日）
3. スマホの「設定・バックアップ」→「クラウド解析の接続先」に、所有者・リポジトリ名・元ブランチ・トークンを入れて「接続を確認」を押す。

公開リポジトリ（このリポジトリ）に接続した場合は、パラメータ計算と公開版報告書の生成だけが使えます。

## 6. 公開（HTTPS）の方式（採用: Cloudflare Pages）

| 方式 | 長所 | 短所 |
|---|---|---|
| **Cloudflare Pages ← 採用（利用者からトークンの提供あり）** | 速い。アクセス制限（Cloudflare Access）も後から付けられる。GitHub 側の Pages 設定に触れない | トークンの管理が必要（Claude Code のクラウド環境に安全に保存済み。チャットに書かれたトークンは無効化を推奨） |
| GitHub Pages（公開専用の別リポジトリ） | 同じ GitHub アカウントで完結し、無料で HTTPS。秘密情報は検査語の Secret だけ。このリポジトリの Pages や他アプリの設定に触れない | 公開専用リポジトリを 1 つ作る必要がある |
| GitHub Pages（このリポジトリ） | 追加のリポジトリが不要 | Pages はリポジトリごとに 1 サイト。同じリポジトリの他アプリ（田嶋研究室アプリ等）と衝突する |

### 更新の公開（Cloudflare）
- Claude Code のセッションから: `python scripts/deploy_cloudflare.py`
  - ビルド → 漏えい検査（不合格なら中止）→ 公開 → 応答確認 の順に進みます。
  - トークンは環境のネットワーク設定から自動で付くので、値は不要です。
- GitHub から自動で公開する場合（任意）: このリポジトリの Secrets に `CLOUDFLARE_API_TOKEN`、`CLOUDFLARE_ACCOUNT_ID`、`AQROS_PRIVACY_PATTERNS` を登録します。`.github/workflows/cloudflare-pages.yml` が push のたびに公開し、未登録なら何もしません。
- 仕組み: Pages のファイルアップロード API は短期の別トークンを使い、クラウド環境のプロキシと両立しません。そのため、静的ファイルを `_worker.js` に埋め込み、デプロイ API 1 回で公開しています（`scripts/build_mobile.py --target cloudflare`）。

### 別方式: GitHub Pages で公開する手順
1. 公開用のリポジトリを作る（例 `csta24055-sys/aqros-mobile`、Public、中身は空でよい）。
2. `deploy/pages-repo/.github/workflows/deploy.yml` をそのリポジトリの `.github/workflows/deploy.yml` に置く。
3. そのリポジトリの Settings で次を設定する。
   - Pages → Source を「GitHub Actions」にする
   - Secrets に `AQROS_PRIVACY_PATTERNS`（検査語、改行区切り）を登録する
4. Actions →「deploy」→「Run workflow」。漏えい検査に合格した場合だけ `https://csta24055-sys.github.io/aqros-mobile/` に公開される。以後は毎日 1 回、本体の更新を取り込む。

前提として、本体ブランチ（`claude/air-quality-research-os-19gu2g`）が GitHub に push されている必要があります。

## 7. テストと結果の区別

| 種類 | 内容 |
|---|---|
| 自動テスト（Chromium・端末エミュレーション） | `frontend/e2e/mobile.cjs`: 「iPhone 13 相当」（27 項目、非公開リポジトリ想定）と「Pixel 7 相当」（25 項目、公開リポジトリ想定）の画面サイズ・UA・タッチで計 52 項目。PWA 設定、検索、CSV/Excel、シミュレーター、保存、オフライン起動、バックアップ・復元、クラウド解析を確認。結果は `docs/screenshots/mobile/mobile_results.json` |
| 数値一致（Python ⇔ TypeScript） | `frontend/src/core/crosscheck.test.ts`: バイパス、単室（CADR・損失率・定常・I/O・時系列）、沈着、多室、回帰、I/O比、除去効率、減衰 |
| API 一致（FastAPI ⇔ 端末内バックエンド） | `frontend/src/core/local.test.ts`（参照値は `scripts/make_api_parity_fixture.py`） |
| クラウドジョブ | `cloud/run_job.py` を手元で実行。4 種類とも結果を確認し、公開リポジトリでの研究データ拒否も確認。スマホ⇔GitHub API の流れは E2E 内の GitHub API 模擬サーバーで確認 |
| 公開サイト（https://aqros-mobile.pages.dev） | 同じ E2E を公開 URL に対して実行し、46/46 合格（iPhone 13 相当・Pixel 7 相当、各 23 項目）。クラウド解析の項目だけは除外（公開サイトの CSP がローカルの模擬サーバーへの通信を止めるため。ローカルで確認済み） |
| アプリ更新時のデータ保護 | `frontend/e2e/update.cjs`: 旧版で保存 → 新版を配信 →「更新する」→ データが残る。初回訪問では自動で再読み込みしない。4/4 合格 |
| 実際の GitHub Actions | 公開リポジトリで 2 件のジョブを実行して成功: バイパス計算 504 ケース（0.1 秒）、報告書 Word＋PDF（32 ページ、日本語フォント埋め込み、住宅記号の置換を確認）。スマホ画面から実リポジトリへの送信は、利用者のトークン未設定のため未実施 |
| CI（GitHub Actions） | mobile-pwa: 単体テスト・ビルド・漏えい検査・E2E が合格。desktop: Windows（インストーラー含む）、macOS（arm64・Intel）、Linux のビルドと起動確認が合格 |
| **未実施** | iPhone 実機（Safari / WebKit）、Android 実機。非公開リポジトリでの研究データのクラウド処理（リポジトリ未作成） |

E2E の iPhone は Chromium での再現で、WebKit ではありません。Safari 固有の挙動は、公開後に実機で確認する必要があります。確認するのは次の点です。
- ホーム画面追加後の保存の持続
- ファイル保存ダイアログ
- 印刷→PDF
