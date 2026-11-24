# WLC electrical equivalent-circuit research — START HERE

**Status: pre-research design scaffold, 2026-11-24.** This is an intended research protocol, not a completed result.

## Objective
Do **not** merely remark that WLC time curves resemble circuit waveforms. Reconstruct the WLC time-calculation problem as an **explicit electrical equivalent circuit**, following the mathematical analogy used in building thermal RC networks, then determine whether the new representation is exactly equivalent, computationally useful, and reducible.

## Key user idea
1. Separate **initial emissions**, **continuous time accumulation** (sloping line), and **discrete replacement/renovation emissions** (staircase).
2. Assign initial charge, a continuously driven current and discrete current pulses to a charge accumulator. Prefer an explicit calibration constant `gamma` in kgCO2e/C.
3. Give air-conditioning equipment and pipework **different replacement intervals** (illustrative: 10 and 20 years). Explore a shared periodic electrical excitation plus **independent capacitive response, rectification/integration, threshold detection and reset** to cause events at their respective intervals.
4. When a trigger fires, inject a separately calibrated pulse into the building's **total-emissions integrating capacitor**. Also change downstream operating efficiency and relevant refrigerant/repair states.
5. Explore parallel/series/controlled-source network reduction, but preserve independent information. Distinguish valid Kirchhoff/charge conservation from unsupported 'just connect capacitors and they automatically sum every future behavior'.

## Original source of truth
- GitHub repository: `csta24055-sys/-`
- Immutable source branch: `claude/wlc-theory-research-base-c33936`
- Source directory: `whole-life-carbon-jcat-study/WLC_THEORY_RESEARCH_BASE/`
- Source overview: `00_README.md`; restart notes: `13_別チャット引継ぎ文.md`
- Time spectrum: `05_時間スペクトルの理論.md`
- Building-wide equation: `06_建物全体の統一方程式.md`
- Actual time vs evaluation duration: `07_動的LCAと工程時間.md`
- Limits and unresolved: `09_未解決問題と限界.md`
- Renewal/aging: `15_劣化・寿命・交換モデル研究開始資料.md`

**Critical separation:** the independent 70-unit synthetic model is not a conversion of the official J-CAT equations. 21 units directly contribute to the total, 49 have auxiliary/logic/aggregation roles. Existing verified claims concern a restricted mathematical domain, not real-building predictive accuracy.

## Second research navigation source
The user also wants the earlier **GitHub research classification tree** taken into account:
- `csta24055-sys/lastdance4-tree-` (`main`): the Yes/No role finder (2,100 roles), especially A3 computation, A6 verification and A9 knowledge/specification.
- `csta24055-sys/lastdance`: underlying code referenced by the ability tree, to be consulted only when a role is actually relevant.
- `05_SOURCE_MAP.md`: exact instructions to trace these sources back to file/role/commit. This index is NOT evidence that the WLC math is valid; all math claims remain tied to the WLC theory base and independent tests.

## What to deliver
A formal circuit grammar, clear schematics, calibration table, 2-equipment pilot, independent baseline and circuit simulations, reproducible boundary/overlap tests, counterexamples, model reduction experiments, complexity benchmark, and a concise report of novel *verified* implications. Study new mathematical claims only after checking original theory and prior art.

## Start order（最終更新）
研究実行時は、`CLAUDE.md` → `12_FINAL_OPERATING_PLAN.md` → `07_SHARED_CONTRACT.md` を短く読み、その担当に必要な資料だけを参照する。**03は技術チェックリスト、04は過去の開始プロンプト、06は研究分担の説明**であり、実行順序はすべて12が優先する。各担当の成果を `routes/<role>/` に隔離し、統合は検証済みの結果に限る。新しい研究以外は変更しない。
