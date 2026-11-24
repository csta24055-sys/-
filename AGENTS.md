# 最新研究方向
**電気回路第一原理 → 共通回路トポロジー → WLC全体を投入** がユーザーの目的。まず `whole-life-carbon-jcat-study/WLC_CIRCUIT_RESEARCH/13_CIRCUIT_FIRST_OBJECTIVE.md` を読む。既存70単位を70個の電流源・回路へ個別再翻訳することは目的ではない。旧G5のEXP-1〜5は保留。サイクル1の成果は参考として保持。書込みは新しい `WLC_CIRCUIT_RESEARCH/circuit_first/`、統括は `coordination/circuit_first_architecture.md` など専用ファイルのみに限定し、旧研究/アプリ/他担当の出力を保護。

---

# WLC研究エージェント共通ガイド

最初にリポジトリ直下の `CLAUDE.md` と `whole-life-carbon-jcat-study/WLC_CIRCUIT_RESEARCH/12_FINAL_OPERATING_PLAN.md` を読む。**実行順序・書込み先・モデル別段階は12が正本**。共通変数は `07_SHARED_CONTRACT.md`。

A＝コンデンサ・時間波形、B＝方程式全体系、C＝70単位の役割写像、D＝独立検証、E＝抵抗／ジュール熱、F＝Math7検証支援。各担当は指定の `routes/<route>/` のみ変更し、原WLC研究・Math7のmain・WLC Studio・他担当のファイルを変更しない。

数理同値性、反例、時刻境界、変数の単位、CO₂の物理的排出時刻とWLC評価期間の区別を必須とする。合格判定は独立した実行記録に基づく。機密・再配布不可の資料や個人情報を公開リポジトリに保存しない。

同じチェックアウトで複数エージェントがgit checkout/commitすることは禁止。参照する別ブランチは読み取り専用。必要に応じたサブエージェント委任は可能だが、保存された設定だけで研究開始・計算完了とは扱わない。
