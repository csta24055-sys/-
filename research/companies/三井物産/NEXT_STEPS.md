# 三井物産：次回再開手順（NEXT_STEPS）

状態：IN_PROGRESS（報告書はPARTIAL）。PASSはAXIS_13_T03の1テーマだけ。2026-11-09に手動で月次チェックを実行し、6出典すべてUNCHANGEDだった。

## 次の問い（優先順）
1. Q-C01-A13-T01-03：メガバンク別の与信やコミットメントライン参加行が開示されているか。統合報告書（`ja_ir2026_all_web.pdf`）、社債の発行登録書、各メガバンクの開示を確認する。
2. Q-C01-A13-T02-04：劣後シ・ローン（2,050億円・2,150億円）の実行日はいつか。適時開示・前期有報（第106期）と比べる。その上で、HYP-C01-0004に対抗する仮説を1本立てる。
3. Q-C01-A13-T03-06：2016〜2024年度のJBICプレスリリースを本文検索する（一覧URL `https://www.jbic.go.jp/ja/information/press/press-YYYY.html`）。
4. AXIS_13_T04：プロジェクトファイナンス案件を洗い出す（有報の担保付債務注記、JBICの「プロジェクトファイナンス」分類）。
5. AXIS_13_T07：格付会社（R&I・Moody's・S&P）の一次公表と照合し、基準日時点の格付けを確認する。
6. 次の軸：AXIS_14（SRC-C01-0001のセグメント情報・キャッシュ・フロー）、AXIS_20（関係会社の状況 pdf p.11〜、主な連結子会社 p.188〜）、AXIS_24（大株主 p.95）。

## 手順
1. `python3 research/research_gates.py --company COMPANY_01`
2. 資料を取得したら、sources / passages / observations / search_log に記録する。
3. 主張と仮説を書き、`axes/AXIS_XX/SYNTHESIS.md` を更新する（テンプレートの印を外す）。
4. 数値計算は `models/` に置き、`MODELS.jsonl` に登録する。
5. `research/run_all.sh` を実行し、すべて通ったらコミットする。
