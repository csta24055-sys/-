# Tajima Lab Research Navigator — Claude Code 即着手スターター

**作成日：2026-11-09（JST）**  /  **対象：日本大学理工学部建築学科 RC構造・構造解析研究室（田嶋和樹教授）**

> 研究室・大学の公式アプリではありません。研究室の公開情報をもとにした**非公式の試作プロジェクト**です。

## このZIPに入っているもの

- `app/`：デスクトップアプリ用 Electron ラッパー + そのままブラウザで動く日本語UI。論文一覧、検索、分類、論文詳細、ノート、分析、先行研究の候補検索、仮スケジュール、JSONバックアップ、PDFの取り込みを実装。
- `app/data/papers.json`：**公開書誌情報52件**。研究室公式掲載の6件と田嶋教授の研究者情報に掲載された共著業績46件を区別。
- `app/data/papers.csv`：同一書誌データのExcel等で見られるCSV（UTF-8 BOM付き）。
- `app/data/seed.js`：ブラウザ試作画面の初期値（JSONから生成済み）。
- `research/`：収集元URL、研究分野分類、年間計画テンプレート、データ辞書、開発タスク、権利・品質上の注意。
- `CLAUDE.md`：Claude Codeが最初に読むべき、実装優先・品質保証・リリースの指示。
- `PROMPT_FOR_CLAUDE_CODE.txt`：新しいClaude Codeチャットに貼る文章（**これだけ貼れば開始可能**）。
- `.github/workflows/build.yml`：GitHub ActionsのWindows/macOS/Linux向け未署名インストーラ作成ワークフロー。

## 一番簡単なClaude Codeへの渡し方

1. ZIPを解凍する。
2. 解凍したフォルダ全体をClaude Codeの作業フォルダとして指定する。
3. **`PROMPT_FOR_CLAUDE_CODE.txt` の全文を貼る。** `CLAUDE.md` とデータを読んで実装・検証するよう指示済み。

Claude CodeがGitHubを使う場合はこのルートをそのまま新規リポジトリにコミットする（非公開推奨）。ユーザーの確認なく既存の関係ないリポジトリを編集しない。

## すぐにプレビューする

### ブラウザ（Electron不要・依存パッケージ不要）

```bash
cd app
python -m http.server 8765
```

ブラウザで `http://localhost:8765` を開く。Pythonがなくても `npx serve` 等のローカルWebサーバーでよい。直接 `index.html` を開く方式は一部のブラウザのローカルファイル制限を受けるため非推奨。

### デスクトップアプリ

Node.js 22系以上、npmが必要。

```bash
cd app
npm install
npm run check
npm start
```

### OS別インストーラーの生成

```bash
# Windows PC
npm run dist:win

# Mac
npm run dist:mac

# Linux
npm run dist:linux
```

インストーラーは `app/dist/` に出力される。**このZIPには `.exe` / `.dmg` などのビルド済み配布ファイルは入っていない**。OS別ビルドと画面の動作確認はClaude Code側のマシン/CIで実施すること。署名をしていないため正式な一般公開には追加作業が必要。

## 現在できることと、まだできないこと

**v0.2で追加・修正（2026-11-09）**：Electronで研究スケジュールの作り直しが `prompt()` 非対応で落ちる不具合を修正（日付入力欄に変更）／PDF.jsによる内蔵PDFビューア（日本語CMap対応・ページ移動・拡大・根拠ページ記録）／取り込んだPDFの本文全文検索（一致ページから直接表示）／PDFからの書誌候補抽出（根拠付き・利用者確認）／同義語辞書・AND検索／保存の1世代バックアップと破損時の自動復旧／新しい公開書誌の自動追加／バックアップ保存ダイアログ／二重起動防止／ユーザー登録資料の資料種別・掲載先・削除／未保存ノートの自動保存／仮予定日付のタイムゾーンずれ修正／アプリアイコン。

**実装済み（ソースコード）**：52件の書誌一覧・検索・出典フィルタ・主分野フィルタ・年度フィルタ／年度別・分野別集計／論文詳細／手動で検証した内容を登録する要約欄／キーワード・タグでの先行研究候補検索／仮の9工程スケジュール／ローカル保存／データの書出・復元／デスクトップ用PDFインポートとOS標準PDFビューア呼出し。

**未完成・要改良**：OCR（画像だけのPDFは本文検索不可）、学術的に正確なAI要約、論文本文に基づく関連研究スコア、正式な研究室スケジュール、研究室の卒論・修論全件収録、実OS向け配布ビルドの実行・署名、GUIの実機検証。書誌情報の収集は網羅調査ではない。

**検証済み（v0.2）**：`npm run check`（書誌検証＋ユニット30件）合格。Playwrightで実際のElectronアプリを操作するE2E 13件・ブラウザ版E2E 5件が合格（コンソールエラー0件）。Linux AppImage を生成し、**配布版バイナリに対してもE2E 13件が合格**、`check:dist` でPDF・個人データ非同梱を確認。Windows（NSIS/portable）・macOS（dmg/zip）はGitHub Actionsの各OSランナーで生成し、**Windows・macOS（arm64）の配布版でもE2E 13件が合格**（run 42551033367）。インストーラーはActionsのArtifact（`installer-windows-latest` / `installer-macos-latest` / `installer-ubuntu-latest`、保存期限2027-02-07）から入手できる。未署名のため初回起動時にOSの警告が出る。macOS x64版の実機起動は未検証。

## 絶対に混同してはいけない点

- 研究室の「最近の研究論文」6件 ≠ 研究室の全過去論文。
- 田嶋教授の研究業績46件には他研究者・他研究室との**共著**が含まれる。
- 書誌の存在 ≠ 論文PDFの所持、全文の確認、研究結果の検証。
- タイトルから付けたジャンルは**仮分類**。複数分類があるためグラフ合計は総件数と一致しない。
- 研究予定は**一般的な仮予定**で、田嶋研究室の実際のゼミ・提出締切を示さない。

詳細は `research/SOURCES.md`、`research/DATA_DICTIONARY.md`、`research/QUALITY_AND_RIGHTS.md` を読む。
