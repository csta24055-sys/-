# cc-autoresume の導入（Air Quality Research OS）

共通モジュール cc-autoresume（原本：csta24055-sys/-1 の `tools/cc-autoresume/`）をこのリポジトリに導入したブランチ。
コード：`.claude/autoresume/`、設定：`.claude/autoresume.json`（プロジェクト名・ブランチ・進捗ファイル・テスト・再開作業）。

## 状態
- 導入済み：コード・設定・`.gitignore`（`.claude/autoresume/run/`）・プロジェクト設定のフック（`.claude/settings.json`）。
- 動作確認：別ディレクトリ・別設定で `status` / `start-run` / `plan-wake` / `lock` を実行して正常（2026-11-03、YUCACO 側セッション）。
- **未適用**：既存の毎時タスク `trig_01G2NK6VVHvHoqvMjYpoUtAE`（AQROS セッション専用）は変更していない。一回限りタスクも未作成。

## AQROS セッションで切り替える手順（重複実行を避ける順序）
1. このブランチを作業ブランチ `claude/air-quality-research-os-19gu2g` に取り込む。
2. `python3 .claude/autoresume/install.py . --scope user`（クラウドではプロジェクト直下の設定が読まれない場合があるため）。
3. `python3 .claude/autoresume/ccar.py start-run run-<日時>` → `plan-wake`。出力の `triggers` 3件で一回限りの scheduled task を作成し、ID を `.claude/autoresume.json` の `schedule` に記入、`ccar.py prompt <role>` の内容でプロンプトを更新。
4. 本起動が一度正常に届いたのを確認してから、毎時タスク `trig_01G2NK6VVHvHoqvMjYpoUtAE` を `enabled=false`（削除しない）。
5. 以後は区切りごとに `ccar.py checkpoint --done … --next … --test --push`。

制約：クラウドでは公式の使用率が取れない（status line が動かない）ため、起動時刻は推定（`official:false`）。詳細は `.claude/autoresume/` の元 README（-1 リポジトリ `tools/cc-autoresume/README.md`）。
