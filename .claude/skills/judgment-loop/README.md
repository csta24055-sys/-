# judgment-loop — Claude⇄GPT 反復オーケストレーター

Claude Code が **調査・資料作成・検証・修正** を行い、GPT が成果物を **判断基準に照らして独立評価** し、
次に行うべき具体的な作業を構造化 JSON で返します。これを、最初に一度だけ取った包括承認の範囲内で、
ユーザーが毎回指示しなくても繰り返します。スマホの claude.ai/code から短い言葉で開始・中断・再開できます。

```
  ┌──────────── 1 反復 ─────────────────────────────────────────────┐
  │ Claude: 作業 → 成果物・実行記録・根拠・未解決事項・事前予測を submit │
  │ GPT   : 判断基準の抜粋＋承認済み事実＋根拠台帳と照合して review      │
  │         → PASS / REVISE / BLOCKED、修正対象・根拠・次の行動・検証方法 │
  │ Claude: 各指示の根拠を自分で確認して decide（採用/不採用と理由）      │
  └──────────────── 採用した指示を次の反復で実行 → 再評価 ───────────┘
```

## 構成

| ファイル | 役割 |
|---|---|
| `SKILL.md` | Claude が読む運用手順（自然言語→操作の対応、ループ手順、禁止事項） |
| `scripts/orchestrator.py` | 状態遷移・承認・予算・停止条件・履歴・退避/復元を強制する CLI |
| `scripts/review.py` | 判断基準の部分抽出、GPT 入力パケット、構造化出力スキーマと検証 |
| `modes/interview.json` | 面接専用モード（深掘り質問・回答改善・模擬面接・矛盾検証） |
| `modes/jobhunt.json` | 就活全体モード（企業研究・適合分析・ES・面接準備・応募戦略） |
| `tests/test_orchestrator.py` | モックテスト（API を使わない） |
| `install.sh` | 別リポジトリへの導入（gpt-consult も同時に導入） |

依存: `.claude/skills/gpt-consult/scripts/gpt_bridge.py`（Responses API 呼び出し・伏せ字化・上限）。
このスキルのために gpt_bridge へ **就活資料向けレビュー（`jobdoc`）** と **構造化出力（json_schema）** を追加しています。
コードレビュー用の `review` はそのままです。

## データの置き場所（重要）

このリポジトリには **汎用コードだけ** を置きます。次のものは **非公開ホーム**（既定 `~/.judgment-loop`、
`JUDGMENT_LOOP_HOME` で変更）にだけ置き、Git には入れません。ホームが Git 作業ツリー内にあると CLI が拒否します。

```
~/.judgment-loop/
├── policies/            判断基準（ZIP から policies/*.md だけ取り込み。private-local は取り込まない）
├── profile/
│   ├── facts.jsonl      本人の事実（出典・確認日・状態・範囲・機密度・GPT 送信可否。追記型、置換は supersedes）
│   └── redact_terms.json 送信前に [本人情報] へ置換する語（実名など）
├── workspaces/
│   ├── <面接用>/        workspace.json（別名・応募先）/ refs.jsonl（基準資料の所在）/ evidence.jsonl / artifacts/ / runs/
│   └── <就活全体>/      同上（2 つは独立。共有するのは判断基準と scope=shared の事実だけ）
└── STOP                 全体停止スイッチ
```

クラウドのコンテナは使い捨てなので、`export` したスナップショット（1 ファイルの JSON）を
**Dropbox に新規ファイルとして退避** し、次のセッションで `import` して再開します（上書きはしません）。

## GPT に送るもの・送らないもの

- 送る: 作業種別ごとに選んだ **判断基準の節だけ**（例: 回答改善なら QUALITY_GATES の導入・リスク重み付け、
  DECISION の優先順位、COGNITIVE_PLAYBOOK の「相手の理解」「バイアス」など。節単位で全文。`--policies full` で全判断基準）、
  今回の成果物（大きい場合は分割して全件）、submit で引用した事実（`gpt_ok` かつ secret でないもの）と根拠台帳の項目、実行記録、前回の指摘と採否。
- 送らない: リポジトリ全体、Dropbox の DB 全体、過去の会話、未引用の事実、他ワークスペースの情報、secret の事実。
- 送信直前に、実名など登録語の置換と、メール・トークン等の伏せ字化を行います。
- AUTOMATION（承認・費用・停止）と KNOWLEDGE_MEMORY（事実の管理形式）は、主に **ローカルで機械的に強制** します。

## 承認・予算・停止

`approve` で一度だけ記録します（ユーザーの承認発言をそのまま保存）。

| 項目 | 内容 |
|---|---|
| `--model` | 使用モデル（承認と異なるモデルでは送信不可） |
| `--max-iterations` | 最大反復回数 |
| `--max-calls` | 最大 API 呼び出し回数（失敗・中断・分割パートも 1 回ずつ数える） |
| `--max-input-tokens` / `--max-output-tokens` | 入力・出力トークンの合計上限（入力は送信前に文字数で保守的に見積もる） |
| `--output-tokens-per-call` | 1 回の出力上限（既定 16,000） |
| `--max-input-per-call` | 1 回に載せる文字数の目安（既定 200,000）。超える成果物は**行範囲で分割して全件レビューし、結果を統合**する |
| `--max-usd` + `--price-in/--price-out` | 単価が分かる場合の費用上限（最悪ケースで事前判定） |
| `--data` | 送ってよいデータ区分 policies / artifacts / baseline / facts / evidence |
| `--expires` | 承認期限 |

**固定の上限はありません。** 上限はすべて承認した値です（0・未指定＝無制限は不可）。足りなくなったら `extend` で
ユーザーの追加承認を記録して引き上げます。**黙って切り詰める処理はありません**（判断基準は作業種別の節を全文、
`review --policies full` で全文も可。成果物は分割送信。gpt-consult の単体ファイルも上限超過はエラー、`--truncate` 指定時のみ切り詰め）。

自動で止まる条件: 承認なし・期限切れ・回数/トークン/費用の上限・未承認データ区分・全体停止（STOP）・
BLOCKED・本人にしかできない作業（needs_user）・同じ指摘の反復（stalled）・反復上限（limit_reached）。
API 失敗時は自動再試行せず（AUTOMATION の規則）、状態を `awaiting_review` に戻します。

GPT の指示は機械審査も通ります。応募・提出・送信・公開・push・main 変更を含む指示、存在しない成果物を対象にした指示は
**自動不採用** になり、Claude も採用できません。採用には確認内容（`--checked`）の記録が必須です。
PASS に P0/P1 指摘や不合格ゲートが残っていれば REVISE に格下げします。

※ 承認フラグは「本人が本当に承認したか」を技術的に証明するものではありません（判断基準 AUTOMATION の注意と同じ）。
OpenAI 側のプロジェクト予算上限もあわせて設定してください。

## スマホからの使い方

| 言うこと | 動作 |
|---|---|
| 「面接の回答改善を 3 回まわして」 | 復元 → 開始 → 承認内容を 1 回提示 → OK 後に自動反復 |
| 「中断」 | 一時停止＋スナップショット退避 |
| 「再開」 | 復元＋再開して続きから自動反復 |
| 「状況は？」 | 反復・判定・使用量・次の一手 |
| 「全部止めて」 | 全体停止（解除は「停止解除」） |
| 「あと 2 回いいよ」 | 追加承認として上限を延長 |

実行中の中断は、アプリの停止ボタンで Claude を止めてから「中断」と送ってください（実行中のターンに
割り込む手段は停止ボタンだけです）。

## 初回セットアップ（1 回だけ）

Claude に「judgment-loop の初回セットアップをして」と頼むと、次を行います（Dropbox への書き込みは確認後）。

1. 判断基準 ZIP を取り込む: `O policies-import <zip>`
2. ワークスペース作成: `O ws-create <名前> --mode interview|jobhunt --alias <呼び名> [--target <応募先>]...`
3. 基準資料の所在を登録（本文は複製しない）: `O ref-add --ws <名前> --role baseline --kind dropbox --ref <id:...> --title ...`
4. 実名などの置換語: `O redact-add <語>`
5. 本人の事実を必要最小限だけ登録: `O fact-add --statement ... --source ... --observed ... --status ... [--gpt-ok]`
6. Dropbox に保管フォルダを作り、最初のスナップショットを保存

## テスト

```bash
python3 -m unittest discover -s .claude/skills/judgment-loop/tests -v
```

モックで Claude→GPT→Claude を 3 反復し、一時停止・再開、GPT の不正出力からの回復、通信中断からの recover、
コンテナ移動（export→import）、履歴の保持を確認します。HTTP 経路も偽の通信関数で検証し、
Authorization ヘッダーを付けないこと・構造化出力の指定・予算超過時の拒否などを確認します。

## 別リポジトリへの導入

```bash
bash .claude/skills/judgment-loop/install.sh /path/to/other-repo
```

非公開ホームは導入先とは無関係に共有されます（同じコンテナ・同じスナップショットを使う限り）。
