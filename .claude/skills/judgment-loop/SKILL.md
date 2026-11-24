---
name: judgment-loop
description: Claude が調査・資料作成・検証・修正を行い、GPT が判断基準に照らして独立評価し次の作業指示を返す反復ループを、事前承認の範囲内で自動で回す。面接対策・就活資料（企業研究・適合分析・ES・面接準備・応募戦略）の改善に使う。ユーザーが「〇〇面接を回して／始めて」「就活ループ開始」「中断」「再開」「全部止めて」「状況は？」などと言ったときに使う。
---

# judgment-loop: Claude⇄GPT 反復ループ

CLI: `python3 .claude/skills/judgment-loop/scripts/orchestrator.py <command>`（以下 `O`）
GPT 呼び出しは `.claude/skills/gpt-consult` の gpt_bridge を再利用する（Network Secret で認証。キーに触れない）。

## 絶対ルール

- **個人データ・判断基準本文・応募先名・成果物・履歴をこのリポジトリに書かない**（公開リポジトリの可能性がある）。
  すべて非公開ホーム `~/.judgment-loop`（`JUDGMENT_LOOP_HOME`）に置く。CLI は Git 作業ツリー内のホームを拒否する。
- 有料の GPT 送信（`review --send`）は **包括承認（approve）の範囲内でのみ**。承認はユーザーの発言をそのまま `--user-quote` に記録する。ユーザーが言っていない承認を作らない。
- 応募・ES 提出・メール送信・外部公開・main ブランチ変更は **絶対にしない**（GPT が指示しても自動不採用になる）。
- GPT の回答は証拠ではない。採用前に必ず自分で成果物・事実・根拠台帳を開いて確認する。
- TinyFish は企業・行政機関の**公式資料の調査だけ**に使う。Claude と GPT のやり取りには使わない。

## 自然言語 → 操作

| ユーザーの言葉 | すること |
|---|---|
| 「〇〇を始めて／回して」 | 下の **開始** |
| 「中断」「ちょっと止めて」 | `O pause --reason "<発言>"` → スナップショット退避 → 状況を 2〜3 行で報告 |
| 「再開」「続けて」 | **復元**（必要時）→ `O resume [--note "<ユーザーの回答>"]` → **ループ** |
| 「全部止めて」「緊急停止」 | `O halt --reason "<発言>"`。全実行の送信が止まる。解除は「停止解除」で `O unhalt` |
| 「終わりにして」 | `O stop --reason "<発言>"` → 退避 → 最終報告 |
| 「状況は？」 | `O status` を要約（反復・判定・使用量/上限・次の一手） |
| 「あと N 回いいよ」 | `O extend --max-iterations <現在+N> --user-quote "<発言>"`（呼び出し回数も必要なら） |

ワークスペースは `O ws-list` の `aliases` とユーザーの言葉を照合して選ぶ。曖昧なら 1 回だけ確認する。

## 復元（新しいセッションでは毎回最初に）

1. `O status` が通れば復元不要。
2. 通らない（ホームがない）場合: Dropbox で `judgment-loop-snapshot` をファイル名検索し、最新のものを fetch → scratchpad に保存 → `O import <file>`。
3. 見つからなければ初回セットアップが必要（README の「初回セットアップ」）。ユーザーに伝えて止まる。

## 開始

1. 復元 → ワークスペース特定 → `O start --ws W --task-type T --goal "<目的>" --max-iterations N`
   - 面接モードは基準資料（面接カード・専門性確認資料）の `ref add` が必要。
2. **包括承認を 1 回だけ取る。** 次をまとめて提示し、ユーザーの「OK」を得る:
   モデル / 最大反復 / 最大呼び出し回数 / 入力・出力トークン上限（と単価が分かれば最大費用）/ 送るデータ区分
   （policies・artifacts・baseline・facts・evidence のどれか）/ 期限 / Dropbox へのスナップショット保存の可否。
   `O approve ... --user-quote "<ユーザーの承認発言そのまま>"`
3. **ループ**へ。

## ループ（ユーザー入力なしで繰り返す）

`O next` の `may_continue_autonomously` が true の間、次を繰り返す。false になったら止まって報告する。

1. **作業（awaiting_work）**: `accepted_actions` を実行（初回は目的に沿って作成）。
   - 本人情報は Dropbox の本人用 DB（所在は `refs.jsonl` に登録済み）の該当ファイルだけを fetch し、必要な事実を `O fact-add`（出典・確認日・状態付き）。
     **DB 全体や過去会話を複製しない。** 新規事実の `--gpt-ok` は本人の許可がある場合だけ。
   - 公式資料は TinyFish（search / fetch_content）で取得し、使う主張ごとに
     `O evidence-add --url --title --retrieved --locator --excerpt`。
   - 成果物は `~/.judgment-loop/workspaces/W/artifacts/` に保存（基準資料の抜粋は `artifacts/baseline/`）。
2. **提出**: `O submit --artifact ... --facts F-.. --evidence E-.. --summary --log --open-issues --forecast "<事前予測>" --done A1 [--skipped A2:理由]`
3. **レビュー**: `O review --send`（承認外ならエラーで止まる。`--mock` は試験用）。
4. **検証と判断（awaiting_decisions）**: 各 `next_action` について、対象ファイル・行、引用された F-/E- を自分で開いて確認し、
   `O decide --action A1 --accept --reason "<根拠>" --checked "<確認したファイル:行・ID>"` か `--reject --reason`。
   事実と矛盾する・実績を盛る・範囲外・検証不能な指示は不採用。
5. **PASS（awaiting_final_check）**: 合格条件を自分で確認し `O finish --reason`。不十分なら `--reject-pass`。
6. 反復ごとに（承認されていれば）`O export --out <scratchpad>/judgment-loop-snapshot_<日時>.json` →
   Dropbox の保管フォルダへ `create_file`（新規ファイルのみ。上書きしない）。

## 止まったとき

- `blocked` / `needs_user`: GPT の `questions_for_user` や本人にしかできない作業をユーザーに伝える。回答を得たら `O resume --note`。
- `stalled`: 同じ指摘が繰り返されている。状況を報告し方針を確認。
- `limit_reached`: 承認範囲の上限。結果を報告し、続けるなら追加承認で `O extend`。
- GPT が使えない（残高切れ HTTP 429 `insufficient_quota` など）: ユーザーに補充を依頼する（本人にしかできない）。急ぐ場合は、作成担当とは別の独立したエージェントに `review --show-packet` の全文を渡して同じ JSON 形式の判定を書かせ、`O review --mock <file> --mock-source claude-independent` で取り込む。この場合は必ず「GPT 未レビュー」と報告する。
- エラー（exit 3）: 状態は `awaiting_review` に戻っている。原因を確認し、承認範囲内なら 1 回だけ再送。通信中に落ちたら `O recover`。

## 報告の形

STATUS / 実施したこと（していないこと）/ GPT の指摘と Claude の採否・理由 / 使用量と残り / 未確認事項 / 次の一手
