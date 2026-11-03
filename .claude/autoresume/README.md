# cc-autoresume — Claude Code 利用枠の自動停止・一回限り自動再開（共通モジュール）

どの Claude Code プロジェクトにも、**設定ファイル1つ**で導入できる開発補助基盤。Python 3.9+ 標準ライブラリのみ。
外部通信・認証・非公式 API は使わない。従量課金（追加使用）を有効にする機能は持たない。

## 何をするか
| 機能 | コマンド / 仕組み |
|---|---|
| 使用率の取得（公式） | status line が stdin で受け取る `rate_limits.five_hour/seven_day.used_percentage・resets_at` を `ccar statusline` が保存 |
| 使用率判定（85% 準備 / 90% 停止、値は設定可） | `ccar status`、PreToolUse フック `ccar hook`（停止時は保存・予約・git 以外のツールを拒否） |
| リセット時刻判定 | 公式 `resets_at`（新しい値）→ 公式 `resets_at`（古い値でも時刻は有効）→ **推定**（窓開始＋window_hours、`official:false`） |
| 起動予約 | `ccar plan-wake`：本起動（リセット＋余裕）・予備（＋5h）・週間フォールバック（＋7日1h）の時刻と、scheduled task 用の `run_once_at`／プロンプト。ローカル用に `at`＋`claude -p` のコマンドも生成（`schedule.backend: "local-at"`） |
| 再開判定 | `ccar resume-check --role primary|backup|weekly --pull`（終了コード 0 続行 / 10 5時間枠未回復 / 11 週間枠未回復 / 12 他の実行中 / 13 より新しい実行あり） |
| 進捗チェックポイント・Git 保存 | `ccar checkpoint --done … --todo … --next … --test --push`（状態 JSON＋ログ Markdown、テスト結果・使用率を記録、push は通信エラー時に 2/4/8/16 秒で再試行） |
| 排他ロック | `ccar lock acquire|release|status <id>`（mkdir の原子性、古いロックは lock_stale_hours で解除） |
| ログ | `<private_dir>/autoresume.log.jsonl`（コミットしない）、`AUTORESUME_LOG.md`（コミットする） |
| 再開プロンプト | `ccar prompt primary|backup|weekly`（設定から生成。scheduled task にそのまま貼る） |

## 導入（別プロジェクト）
```bash
python3 /path/to/cc-autoresume/install.py <project_dir> \
  --project-name "My project" --branch my-branch \
  --progress PROGRESS.md TODO.md --test-command "pytest -q" \
  --resume-task "PROGRESS.md の未完了項目を上から" [--scope user]
```
- `<project>/.claude/autoresume/`（コード一式。コミットする）と `<project>/.claude/autoresume.json`（設定。既存なら上書きしない）を作る。
- `--scope project`（既定）：`<project>/.claude/settings.json` にフックと status line を追加。
  `--scope user`：`~/.claude/settings.json` に絶対パスで追加。**claude.ai のクラウドセッションではプロジェクト直下の設定が読まれない場合がある**（2026-11-03 確認）ので user を使う。コンテナが替わると消えるため、再開プロンプトの手順 0 で毎回再導入する。
- 既存の status line は消さず `--chain` で連結。`--uninstall` で設定を元に戻す（元の status line も復元）。
- プライベートディレクトリを `.gitignore` に追加。

その後 Claude に「`python3 .claude/autoresume/ccar.py plan-wake` の `triggers` で一回限りの scheduled task を作り、ID を autoresume.json の schedule に書いて、`ccar prompt <role>` のプロンプトに更新して」と頼む（3件：primary / backup / weekly）。

## 配布物（ZIP）
`python3 make_zip.py <出力先>` → `claude-code-autoresume-<版>.zip`（最新版は `tools/claude-code-autoresume-1.0.0.zip` に保存）。
展開した `claude-code-autoresume/` から `install.py` を実行すればよく、元のリポジトリは不要。
```
claude-code-autoresume/
  README.md  install.py  uninstall.py  ccar.py  config.example.json  make_zip.py
  ccar/        core.py（判定・予約・ロック・再開・チェックポイント・フック・status line） cli.py
  templates/   autoresume.example.json
  examples/    generic-project/autoresume.json  research-project/autoresume.json
  tests/       test_ccar.py（機能）  test_dist.py（ZIP→別ディレクトリ→導入→使用→削除）
```
設定例から始める：`python3 install.py <project> --config-from examples/research-project/autoresume.json`

## アンインストール
`python3 <project>/.claude/autoresume/uninstall.py <project> [--scope user]`
settings.json（元の status line を含む）を元に戻し `.claude/autoresume/` を削除。設定・状態ファイル・ログは残す。
一回限りの scheduled task は残るので、Claude に `update_trigger enabled=false` を頼む。

## 設定（.claude/autoresume.json）
`templates/autoresume.example.json` 参照。リポジトリ固有の値（パス・ブランチ・タスク ID・作業内容・しきい値・タイムゾーン）はすべてここ。コードには固定値なし。

## 運用の流れ
1. **作業中**：区切りごとに `checkpoint --test --push`。フックが 85% で注意、90% で新規作業を拒否（公式データがあるときのみ）。
2. **停止**：`checkpoint --push` → `plan-wake` → 3件の scheduled task を同じ ID のまま `run_once_at` 更新 → `lock release` → 終了。
3. **起動**：scheduled task がプロンプトを届ける → `resume-check`。リセット未到達・週間枠未回復・他の実行中・既に新しい実行あり なら何もしない。0% 表示だけでは回復とみなさない。
4. **再開**：`resume-check` が新しい窓を記録しロック取得 → 直前のチェックポイント（done/todo/next）と git log から続きを実施。

## 制約（正直な記載）
- 公式の使用率は **status line にしか渡されない**。claude.ai のクラウドセッション（SDK モード）では status line が実行されないため、クラウドでは使用率が取れず、85/90% 判定は発動しない。リセット時刻は推定になる（`basis: "estimated"`, `official: false`）。推定を公式として扱わない。
- 推定の窓開始は「その実行の開始」なので実際より遅め → 起動はリセットより後ろにずれる（早すぎる起動を避ける側の誤差）。
- 週間枠の `resets_at` もクラウドでは取れない。予備（＋5h）と週間フォールバック（＋7日1h、毎回の実行で先送り）で必ず週間リセット後に起動する。
- scheduled task の作成・更新は Claude のツール（claude-code-remote の create/update_trigger）で行う。Python からは呼ばない（認証情報を扱わないため）。
- ローカル PC の `local-at` は生成のみ。`at` が使えるかは各 PC で確認が必要。

## テスト
```bash
cd tools/cc-autoresume && python3 -m pytest -q tests
```
各テストは一時ディレクトリに **別の git プロジェクト（別設定：しきい値 70/80%、窓3時間、別の private_dir、bare リモート）** を作り、インストール済みのランチャーだけで操作する。
