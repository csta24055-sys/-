# 08 Claude Code 一回送信用：修正された研究目的（最新版）

GitHub `csta24055-sys/-` の `claude/wlc-equivalent-circuit-20261124` で、まず `CLAUDE.md` と `whole-life-carbon-jcat-study/WLC_CIRCUIT_RESEARCH/13_CIRCUIT_FIRST_OBJECTIVE.md`、`12_FINAL_OPERATING_PLAN.md`、`07_SHARED_CONTRACT.md` を確認してください。

**研究目的を修正します。** 70評価単位を各々コンデンサ・抵抗・加算器・電源と読み替えることが目的ではありません。先に **本来の電気回路の法則（KCL/KVL、R/C/L、抵抗の発熱と散逸積算、容量の充電、スイッチ、必要最小限の比較器・状態）だけから、1〜3個の共通の回路構造と数学モデルを導出**してください。その既存の回路構造で、WLCの建設・運用・交換・修繕・解体・条件・評価期間末など、70評価単位で記述された全体的な計算を、個別式のコピーなしに表現できるか検証してください。

元の70単位は**必要な出力・入力・反例・独立数値オラクル**として利用してください。既存WLC計算式や各単位の完成値を、任意波形源やブラックボックス制御素子の内部へ丸ごと入れ、足し合わせるだけでは「回路化成功」と判定しないでください。回路自体のKCL/KVL/電力・エネルギー・状態方程式から出力を計算し、同じトポロジーで複数の合成建物を扱えるかを主要な合否条件にします。通常の回路だけでできなければ、その数学的障害と必要な外部制御の最小範囲を明示してください。

元の `integration/`、旧サイクル1成果、G5の `coordination/next_cycle.md` は破壊・変更しないでください。旧G5 EXP-1〜5は**いったん保留**。過去の結果は比較・反例・再利用用です。まずFable 5.2 High（`wlc-architect`）に回路第一原理の再設計を担当させ、その後Opus 5.5 Medium（`wlc-circuit-first-builder`）で実際の共通回路モデルを実装し、Opus 5.5 High（`wlc-verifier`）で元の数学と独立検証してください。役割別の `model` / `effort` は設定どおり実行されたか記録してください。

成果は `WLC_CIRCUIT_RESEARCH/coordination/circuit_first_architecture.md` と `WLC_CIRCUIT_RESEARCH/circuit_first/` に保存し、標準物理回路・限定ハイブリッド回路・単なる数式言い換えの3種類を厳しく区別してください。最終的に構成できない場合も不可能範囲と反例を重要な研究成果として報告。原WLC理論、J-CAT、WLC Studio、Math7/mainは読み取り専用。外部への権限変更・GitHub Actions実行は無断で行わず、必要なテストとコミットは再実行可能に記録してください。
