# 05 Cross-repository source map — WLC research and capability tree

**Status:** source-navigation design (2026-11-24), not a new mathematical proof.

## Sources to consult (read-only)

### A. Original WLC study & mathematical handover
- **GitHub:** `csta24055-sys/-`
- **Authoritative immutable branch:** `claude/wlc-theory-research-base-c33936`
- **Directory:** `whole-life-carbon-jcat-study/WLC_THEORY_RESEARCH_BASE/`
- **Read first:** `00_README.md`, `13_別チャット引継ぎ文.md`
- **Primary mathematics:** `03_数式と記号の完全仕様.md`, `04_マスク積和の理論.md`, `05_時間スペクトルの理論.md`, `06_建物全体の統一方程式.md`, `07_動的LCAと工程時間.md`, `08_証明と検証結果.md`, `09_未解決問題と限界.md`, `15_劣化・寿命・交換モデル研究開始資料.md`
- **Evidence:** `data/claims.csv`, `data/units70.json`, `data/verification_counts.csv`, `12_原典とコード対応表.md`, `14_研究用データ索引.md`.
- Study chapters `09_APPROX_STUDY/` through `23_WLC_STUDIO_APP/` live under `whole-life-carbon-jcat-study/` on study branches. Do not infer those files live on `main`; use explicit refs.
- Use the archived material only as linked, authorized, read-only evidence. The source base itself explicitly excludes protected J-CAT original contents and says numeric inputs are synthetic.

### B. Function/ability classification tree (not a second authority for mathematics)
- **Separate GitHub repository:** `csta24055-sys/lastdance4-tree-`
- **Branch:** `main`
- **Start:** `README.md`
- **Relevant branches:**
  - `ツリー/A3_計算_数理処理ができるか.md` — math, carbon calculation, time functions, physical modeling.
  - `ツリー/A6_正しさを確かめられるか.md` — testing, formula comparison, error and performance verification.
  - `ツリー/A9_手順_仕様_知識_規則を提供する資産か.md` — research instructions, specs, audits, provenance.
  - `ツリー/A2_取り込んだ内容を判定_理解_抽出できるか.md` — mapping roles, inputs and extraction.
- **Machine readable:** `yesno_tree.json`; `役割到達一覧.json` and `役割到達一覧.csv`.
- The tree catalogs 2,100 **roles** and routes to their source; it does not validate correctness of those roles or certify any mathematical claim. It is broader than WLC; follow **only relevant** branches/roles.

### C. Underlying categorized source code (inspect only when needed)
- The tree's `source` entries point to a third separate repository `csta24055-sys/lastdance` and its original files/combined source, plus role-based internal processing reference files.
- Use role ID and exact source path/commit to check a function's actual implementation. **Do not assume tree snippets are complete executable source**, and do not copy or alter code across projects without checking its origin, permissions, tests and relevance.
- `csta24055-sys/lastdance2-classification-` is the separate hierarchical category reference, optional for classification questions.

## Priority and conflict resolution
1. **Mathematical truth / scope / validity:** original WLC theory base and its evidence, independently tested. Keep exact origin branch and commit.
2. **Locate code or workflows:** capability tree then underlying `lastdance` source. Verify source files directly.
3. **New modeling / testing:** only this WLC circuit project's own specifications and independent oracle/tests.
4. If different sources disagree, **do not silently combine**. Record the conflict and evidence; prefer original mathematics for WLC equations and independent recalculation for verification.
5. Existing J-CAT original material is not licensed for redistribution. Never put original formula bodies, coefficients, private files, personal details, or paid source tables in this repository.

## Minimal researcher workflow
- Check the base research handover and precise theorem/unit in `WLC_THEORY_RESEARCH_BASE`.
- If you need to identify existing code or test techniques, navigate `lastdance4-tree-` A3/A6/A9 and follow role IDs back to `lastdance` source.
- In a research log record: `repo`, `branch`, `commit`, `file path`, `claim/role ID`, definition/domain, and whether independently verified.
- Derive and implement new equivalent-circuit model only under `WLC_CIRCUIT_RESEARCH/`.
- Report unverified links explicitly. Do not present a catalog entry as a mathematical proof.
