# gpt-consult — Claude Code から GPT に相談する

Claude Code（claude.ai/code）が、必要なときだけ OpenAI の GPT に **質問・コードレビュー・設計評価** を依頼し、
返ってきた回答を **Claude が検証してから** 作業に反映するための仕組みです。スマホの claude.ai/code だけで運用できます。

- OpenAI **Responses API**（`POST /v1/responses`）を使用
- 認証は claude.ai/code 環境の **Network Secret**（プロキシが Authorization を自動付与）。コードにも Git にもキーは一切置かない
- Python 標準ライブラリのみ。`pip install` 不要
- 既定は **dry-run**（通信なし・無料）。`--send` を付けたときだけ有料のモデル生成を実行

## 構成

```
.claude/skills/gpt-consult/
├── SKILL.md                 # Claude Code が読む手順書（いつ・どう使うか、検証ルール）
├── README.md                # このファイル
├── install.sh               # 別リポジトリへの導入スクリプト
├── gpt-bridge.example.json  # 設定例（必要ならリポジトリ直下に .gpt-bridge.json としてコピー）
├── scripts/gpt_bridge.py    # 本体 CLI
└── tests/test_gpt_bridge.py # モックテスト（API を呼ばない）
```

## 前提：Network Secret の設定（1 回だけ）

claude.ai の環境設定（例: Default）→ Network secrets に以下を登録します。

| 項目 | 値 |
|---|---|
| Host | `api.openai.com` |
| Header | `Authorization`（Bearer） |
| Value | OpenAI の API キー |

同じ環境を使うセッションなら、どのリポジトリからでも同じキーが使われます。

## スマホからの使い方

claude.ai/code のチャットで、普通に頼むだけで構いません。

- 「この差分を GPT にもレビューしてもらって」
- 「`src/parser.py` の 100〜180 行の設計について GPT の意見を聞いて」
- 「GPT のモデルを `gpt-6.2-sol` 以外に切り替えて聞いて」

Claude は SKILL.md に従い、①送るファイルを絞る → ②dry-run で送信内容を確認 → ③**あなたに送信の許可を求める**
→ ④送信 → ⑤回答を実際のコード・テストで検証、という流れで動きます。報告では「GPT の指摘」と
「Claude が確認した結果（採用 / 不採用）」が分けて示されます。

## コマンド（Claude が実行するもの。手動でも可）

```bash
B=.claude/skills/gpt-consult/scripts/gpt_bridge.py

python3 $B ask    "このエラーの原因候補は？" -f src/app.py:40-90      # dry-run
python3 $B review "バグとセキュリティ問題を探して" --diff --send       # 有料
python3 $B review "PR 全体をレビュー" --diff-base main --send
python3 $B design "キャッシュ層の設計を評価して" -f docs/design.md --send
python3 $B last        # 直前の回答を再表示（無料）
python3 $B usage       # 本日の回数・トークン（無料）
python3 $B config      # 有効な設定
python3 $B get resp_xxx  # --store で保存した応答を取得（生成なし）
```

主なオプション

| オプション | 説明 |
|---|---|
| `-f PATH[:START-END]` | 送るファイル（複数可・行範囲指定可） |
| `--diff` / `--staged` / `--diff-base REF` | git 差分を送る |
| `--context-stdin` | 標準入力を追加コンテキストに |
| `--model NAME` | モデル切り替え（既定 `gpt-6.2-sol`） |
| `--max-output-tokens N` / `--max-input-chars N` | 1 回ごとの上限 |
| `--reasoning-effort low\|medium\|high` | 推論強度（対応モデルのみ） |
| `--lang ja\|en` | 回答言語 |
| `--send` | 実際に送信（**有料**） |
| `--show-payload` | dry-run で送信予定の全文を表示 |
| `--json` | 結果を JSON で出力 |

## 設定と上限

優先順位: 既定値 < `<repo>/.gpt-bridge.json` < 環境変数 < CLI 引数

| キー | 既定 | 環境変数 |
|---|---|---|
| `model` | `gpt-6.2-sol` | `GPT_BRIDGE_MODEL` |
| `max_calls_per_day` | 20 | `GPT_BRIDGE_MAX_CALLS_PER_DAY` |
| `max_input_chars` | 60000 | `GPT_BRIDGE_MAX_INPUT_CHARS` |
| `max_file_chars` | 20000（超過分は切り詰め） | — |
| `max_files` | 20 | — |
| `max_output_tokens` | 2000 | `GPT_BRIDGE_MAX_OUTPUT_TOKENS` |
| `max_output_tokens_cap` | 8000（これを超える指定は拒否） | — |
| `language` | `ja` | `GPT_BRIDGE_LANGUAGE` |
| `store` | `false`（OpenAI 側に応答を保存しない） | — |
| `reasoning_effort` | なし | — |

`.gpt-bridge.json` に未知のキー（`api_key` など）を書くとエラーになります。キーを設定ファイルに書く手段はありません。

呼び出し回数はコンテナ内の `~/.cache/gpt-bridge/usage.json` で日ごとに数えます（クラウドのコンテナは
セッションごとに作り直されるため、実質「セッションあたりの上限」として働きます）。

## 安全対策

- **Authorization ヘッダーをコードで設定しない**（テストで検証）。`OPENAI_API_KEY` も読まない。
- **リポジトリ全体は送らない。** 指定したファイル・行範囲・差分・標準入力のみ。
- 送信拒否: `.env*`, `*.pem`, `*.key`, `id_rsa*`, `*credential*`, `*secret*`, `.npmrc`, `.netrc`, `.git/` など、
  バイナリ、リポジトリ外のファイル（`--allow-outside` で明示許可した場合を除く）。差分からも同様に除外。
- 伏せ字化: OpenAI / GitHub / AWS / Slack / Google のキー、JWT、Bearer トークン、秘密鍵ブロック、
  `password=` 等の値、**メールアドレス**。
- API エラーメッセージ中のマスク済みキー断片も伏せ字にしてから表示。
- 回答・使用量はリポジトリ外（`~/.cache/gpt-bridge/`）に保存され、Git に入らない。
- `api_base` は `https://` のみ許可。

## 別のリポジトリへの導入

### スマホ（claude.ai/code）だけで行う場合

導入先リポジトリのセッションで、Claude に次のように頼みます。

> `csta24055-sys/-` リポジトリの `.claude/skills/gpt-consult` を、このリポジトリに導入して。
> install.sh を使って、モックテストが通ったらコミットして push して。

Claude は `csta24055-sys/-` をセッションに追加・clone し、
`bash <clone>/.claude/skills/gpt-consult/install.sh <このリポジトリ>` を実行します。

### 手動で行う場合

```bash
bash /path/to/this-repo/.claude/skills/gpt-consult/install.sh /path/to/other-repo
cd /path/to/other-repo && git add .claude/skills/gpt-consult && git commit -m "Add gpt-consult skill"
```

導入されるのは `.claude/skills/gpt-consult/` 配下だけで、既存ファイルは変更しません。

## テスト

```bash
python3 -m py_compile .claude/skills/gpt-consult/scripts/gpt_bridge.py
python3 -m unittest discover -s .claude/skills/gpt-consult/tests -v
```

テストは `urlopen` をモックに差し替えて実行するため、ネットワークにも有料 API にもアクセスしません。

## 接続確認（無料）

モデル生成を伴わない `GET /v1/models` で認証だけを確認できます（キーは表示されません）。

```bash
curl -sS -o /dev/null -w "HTTP %{http_code}\n" https://api.openai.com/v1/models
```
