# Career model router

## 目的
このリポジトリのjudgment-loop / gpt-consultを変えず、モデル選択を工程別に組み込む。

| 工程 | Subagent | モデル | effort |
| --- | --- | --- | --- |
| 全体計画 | career-strategy-architect | claude-fable-5-2 | high |
| 調査・収集 | career-evidence-researcher | claude-opus-5-5 | medium |
| 成果物作成 | career-artifact-builder | claude-opus-5-5 | high |
| GPTへ送るまで | career-gpt-handoff | claude-opus-5-5 | high |
| GPTレビュー後の再計画 | career-replan-director | claude-fable-5-2 | high |

## 起動
Claude Codeで `/career-model-router` と入力する。ロードしたSkillが該当するサブエージェントを段階ごとに呼び出す。

## 仕組み
- `.claude/agents/*.md` の `model:` / `effort:` はClaude Code公式のサブエージェント設定。
- `.claude/skills/career-model-router/SKILL.md` は実行順序とターン単位のFableモデルを指定。
- `.claude/career-model-routing.json` は人間とAIが確認するルート定義。**JSONだけではモデル切替は起こらない**。
- 実行時のモデルへのアクセス権は別問題。不可・フォールバック時は報告し、ログで使用モデルを確認する。
- GPTレビューは既存のOpenAI APIブリッジを利用する。現在のChatGPTチャットやMemoryが自動共有されるわけではない。
- 公開Gitにはコードと汎用設定のみ。本人情報・判定記録は非公開の作業ホーム。
- 実際のAPI通信、応募、外部送信などは既存の承認・費用制御に従う。
