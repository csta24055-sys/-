# 総合商社インテリジェンス研究（会社最上位・完全独立研究方式）

指令書：`directive/CLAUDE_CODE_MASTER_DIRECTIVE.md`（2026-11-09改訂版）。研究基準日 **2026-11-01**。

## 階層

```
companies/{8社}/                ← 最上位（正本）。各社は他社なしで成立する
  INTEGRATED_COMPANY_REPORT.md  ← 会社別の独立総合報告
  axes/AXIS_01..30/             ← 社内30軸（SYNTHESIS.md / QUESTIONS.jsonl / CLAIMS.jsonl / HYPOTHESES.jsonl）
  ledger/                       ← 出典・原文位置・観測値・関係・検索ログ・再確認イベント（JSONL、追記型）
  models/ datasets/             ← 再現可能なモデルと出力（ゲートが毎回再計算）
  snapshots/asof_2026-11-01/ snapshots/monthly_YYYY-MM/
  TOPIC_STATUS.csv              ← 240テーマの宣言状態（ゲートが検証）
cross_company/                  ← 会社別研究の後に載る派生レイヤー（双方の原文IDが必須）
world_context/                  ← 共通外部資料と世界統合（派生）
registry/                       ← 8社・30軸・240テーマ・1,920スロット台帳、共有出典、エンティティ
app/                            ← 8社トップの静的Webアプリ（`python3 -m http.server -d research/app`）
tests/                          ← 壊したデータでゲートがFAILすることの検査、アプリ操作テスト
monthly_update_runs/            ← 月次更新の実行記録・スケジューラ状態
```

## 実行

```bash
research/run_all.sh                                    # 生成・ゲート・テスト一式
python3 research/research_gates.py                     # 判定だけ（エラーがあれば終了コード1）
python3 research/tools/monthly_update.py --month 2026-12 --company COMPANY_01
python3 -m http.server 8000 -d research/app            # → http://localhost:8000/
```

## ゲートの規則（要約）

- 会社ごとに独立して判定する。三井物産のPASSは他社のPASSを意味しない。
- テーマがPASSになる条件：主張2件以上、DIRECTな一次資料で裏付けた確認事実がある、独立起源2つ以上、競合仮説2本以上（反証の検討つき）、原子的な問いがすべて解決済みかBACKLOG登録済み、軸のSYNTHESISが執筆済み、検索ログがある。
- 宣言されたPASSを証拠が支えていない場合は `E_UNSUPPORTED_PASS`。他社IDの引用は `E_FOREIGN_EVIDENCE`。基準日後の資料の混入は `E_ASOF_VIOLATION`。転載の水増しや重複観測は `E_DOUBLE_COUNT`。モデルが再現できない場合は `E_MODEL_NOT_REPRODUCIBLE`。いずれもテストで確認済み。
- 研究全体が `COMPLETE` になるのは、8社すべてがPASSし、かつ横断・世界・アプリ・月次更新もPASSしたときだけ。
- 確率や「信頼度%」は表示しない。件数（主張・独立起源・反証）で示す。

## 現状

`RESEARCH_PROGRESS.md` と `research_status.json` を参照（ゲートが生成）。
