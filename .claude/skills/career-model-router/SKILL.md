---
name: career-model-router
description: 全体計画→一次情報収集→成果物作成→GPT評価→再計画を指定モデルで自動切替する就活研究ルーター。既存のjudgment-loopとgpt-consultを再利用。
model: claude-fable-5-2
effort: high
---

# モデル切替付き就活オーケストレーション
最初に .claude/career-model-routing.json を読み、以下の名前付きサブエージェントを**明示的に呼び出して**段階ごとに仕事を委任する。

1. 全体計画・戦略の設計：career-strategy-architect (Fable 5.2 / high)
2. 一次資料の探索・検証：career-evidence-researcher (Opus 5.5 / medium)
3. 研究成果物の構築：career-artifact-builder (Opus 5.5 / high)
4. GPTへ引継ぎ・レビュー送信・応答保存：career-gpt-handoff (Opus 5.5 / high)
5. GPT応答による次の全体計画：career-replan-director (Fable 5.2 / high)
6. REVISEなら新計画に基づいて2または3へ戻る。PASSなら根拠確認して完了判定。

**モデルの指定方法:** このSkill自体はFable 5.2 High（現在のターン限り）。各段階のモデルは .claude/agents/ にある subagent の `model` と `effort` frontmatter によって切り替える。JSONのみでは自動でモデルは変わらない。

**重要事項**
- 各段階の作業実体と成果物の場所を確認し、見かけだけの委任にしない。設定モデルと実際の使用モデルは別々に記録。モデル利用不可や暗黙のフォールバックがある場合、無断で完了扱いしない。
- 判断基準や大量の資料を文字数制限で黙って切り捨てない。非公開ファイルのパス・出典IDで引き継ぎ、必要時は原文を読む。
- 既存の judgment-loop の進行状態・承認・中断/再開・予算と gpt-consult の送信機能を再利用する。**新規に有料通信を承認したことにしない。**
- GPTは現在のChatGPT会話そのものではなく、既存ブリッジが接続するOpenAI APIモデル。通信が未実施ならレビュー済みと主張しない。
- 個人情報・応募先・提出資料・判断基準本文を公開Gitへ書かず、非公開の JUDGMENT_LOOP_HOME に保存する。
- 応募、提出、外部公開、秘密情報送信、mainへの変更は別途許可が必要。
- 長時間実行は既存のjudgment-loopのチェックポイントを用い、各サイクルの stage、agent、configured_model、configured_effort、actual_model(if available)、review_id を記録する。

呼び出し例: `/career-model-router 就活全体の計画立案からGPTレビュー・再計画まで、指定モデルを切り替えて進めて`
