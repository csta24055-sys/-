# Air Quality Research OS デスクトップ版 — インストールと使い方

Python や Node.js を入れなくても、ダウンロードしてそのまま使える配布版です。
画面はいつものブラウザに表示され、サーバーは **このパソコンの中だけ（127.0.0.1）** で動きます（LAN やインターネットには公開しません）。

## 1. ダウンロード

GitHub の Releases から、自分の OS 用のファイルを取ります。リリースを作る前は、Actions の「desktop」ワークフローの実行結果にある Artifacts からも取れます（GitHub へのログインが必要）。
2026-11-09 の実行（https://github.com/csta24055-sys/-/actions/runs/42563515279）で、4 種類がビルドと起動確認に合格しました。
- Windows（インストーラー＋zip）
- macOS（Apple シリコン）
- macOS（Intel）
- Linux

実機での動作確認はまだです。

| OS | ファイル | 中身 |
|---|---|---|
| Windows 10/11（64bit） | `AQROS-<版>-windows-x64-setup.exe` | インストーラー（推奨） |
| 〃 | `AQROS-<版>-windows-x64.zip` | 展開してそのまま使う版 |
| macOS 14 以降（Apple シリコン M1〜） | `AQROS-<版>-macos-arm64.zip` | `AQROS.app` |
| macOS 14 以降（Intel） | `AQROS-<版>-macos-x64.zip` | `AQROS.app` |
| Linux（x64, glibc 2.35 以降） | `AQROS-<版>-linux-x64.tar.gz` | `AQROS/AQROS` と `install-linux.sh` |

## 2. インストール

### Windows
1. `...-setup.exe` を実行します。管理者権限は不要です（利用者ごとのインストール）。
2. 「Windows によって PC が保護されました」と出たら「詳細情報」→「実行」を選びます（コード署名をしていないため表示されます）。
3. スタートメニューの「Air Quality Research OS」から起動します。アンインストールは「設定 → アプリ」から行えます。

### macOS
1. zip を展開し、`AQROS.app` を「アプリケーション」フォルダへ移します。
2. 初回は **右クリック（Control＋クリック）→「開く」** を選びます（Apple の公証を受けていないため、ダブルクリックだと止められます）。
   それでも開けない場合は、ターミナルで `xattr -dr com.apple.quarantine /Applications/AQROS.app` を実行してから開きます。

### Linux
```sh
tar xzf AQROS-<版>-linux-x64.tar.gz
cd AQROS
./install-linux.sh        # アプリ一覧に「Air Quality Research OS」、端末から `aqros` で起動できるようになる
# インストールせず使うなら ./AQROS をそのまま実行してもよい
```
操作ウィンドウを使うには Tk が必要です（多くのデスクトップ環境では入っています）。無い場合はコンソール表示で動きます。

## 3. 使い方

- 起動するとブラウザでアプリが開き、小さな操作ウィンドウが出ます。
  - 「ブラウザで開く」… 画面を閉じてしまったときに開き直す
  - 「データフォルダ」… 取り込んだデータの保存先を開く
  - 「終了」（またはウィンドウを閉じる）… アプリを終了する
- 二重に起動しても、すでに動いているアプリの画面が開くだけです。
- 既定のアドレスは `http://127.0.0.1:47615/` です（使用中なら近くの空き番号を自動で使います）。

## 4. データの保存先

取り込んだ実測データ、編集した報告書、研究計画などはここに保存されます（アプリを入れ替えても残ります）。

| OS | 保存先 |
|---|---|
| Windows | `%APPDATA%\AQROS\` |
| macOS | `~/Library/Application Support/AQROS/` |
| Linux | `~/.local/share/aqros/`（`$XDG_DATA_HOME` があればその下） |

- バックアップはこのフォルダの `aqros.sqlite3` をコピーするだけです。ログは同じ場所の `aqros.log` です。
- 保存先を変えたいときは `AQROS --data-dir <フォルダ>` で起動するか、環境変数 `AQROS_DATA_DIR` を設定します。
- 研究室の原データ（Excel/CSV）を取り込んだ場合、それは **このパソコンの中だけ** に保存されます。配布ファイルには原データは入っていません。

## 5. コマンドラインのオプション

```
AQROS [--port N] [--no-browser] [--headless] [--data-dir DIR] [--version]
```

## 6. 自分でビルドする場合（開発者向け）

```sh
python -m venv .venv && .venv/bin/pip install -r backend/requirements.txt -r desktop/requirements-build.txt
.venv/bin/python desktop/build.py                    # dist_desktop/ に、実行した OS 用のアーカイブができる
.venv/bin/python desktop/smoke_test.py build_desktop/dist/AQROS/AQROS   # 起動確認
```
PyInstaller は実行した OS 用のものしか作れないので、3 OS 分はまとめて GitHub Actions（`.github/workflows/desktop.yml`）で作ります。
`v1.1.0` のようなタグを push すると、3 OS 分のファイルを添付した **下書き** のリリースができます（公開は GitHub 上で手動）。

## 7. 既知の制限

- コード署名・公証をしていないため、Windows SmartScreen と macOS Gatekeeper の警告が出ます（上記の手順で開けます）。
- 自動アップデートはありません。新しい版はダウンロードして入れ替えてください（データは保存先に残ります）。
- Box 連携・研究資料の再取得は配布版には含まれません（同梱しているのは公開リポジトリにある集計値・要約・成果物のみ）。
