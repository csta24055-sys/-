# 評価単位の構造の記録 E1b：使用段階（B1〜B7）の 22 単位

分類担当（実行担当とは別の AI 作業担当）が、基準計算のコードと台帳の定義文を読んで作った記録（`ledger/E1b.json`）を、欄ごとにそのまま載せる。
旧研究の統合モデルと旧研究の族の分類は読ませていない（ルート B の、既存成果に拘束されない分類）。
式と閉じた形は分類担当の読み取りと手計算によるもので、数値では確かめていない（水準は仮説）。対象は独立概念モデル（架空データ）である。

## 単位の一覧

| 単位 | 名称 | 段階 | 時間の構造 | T への依存 |
|---|---|---|---|---|
| [B4-01](#b4-01) | 更新イベント年の生成 | B4 | periodic events with period L_j（非整数可）、または explicit event list | step function via N(T, L_j)。明示一覧は [t < T(1−ε)] による段差。事象の時刻そのものは T に依存しない |
| [B4-03](#b4-03) | 交換回数の概算 | B4 | periodic events with period c_i（非整数可） | step function via N(T, c_i) |
| [B4-02](#b4-02) | 機器・資材更新負荷 | B4 | periodic events with period c_i / L_j、または explicit event list。行の振幅 u は時刻によらず一定 | step function via N(T, c)。value = Σ_i N(T,c_i)·u_i + Σ_j \|ev_j(T)\|·u_j。u は T に依存しない |
| [X-08](#x-08) | 更新周期別の集計 | B4 | periodic events with period c（周期の値ごとに 1 群）、explicit event list は 1 つの群にまとめる。年への割当はしない | step function via N(T, c)。value = explicit(T) + Σ_c N(T,c)·U_c。U_c は「N(T,c) > 0 の行」の合計なので、c ≥ T の周期は表に現れない |
| [B3-01](#b3-01) | 年間修繕 | B3 | constant per year（行ごとに e0·r）。ただし更新が属する年は 0。更新年の集合は周期 c_i / L_j の倍数または明示一覧から決まる | sum up to ceil(T) with a prorated last year。行ごとに e0·r·(T − Σ_{y∈S} w_y)。周期が 1 年以上で更新年が端数の最終年でなければ e0·r·(T − N(T,c)) |
| [B3-02](#b3-02) | 期間中の反復修繕（推計） | B3 | constant per year | linear（T に比例） |
| [B1-01](#b1-01) | 物質のCO2e充填量 | B1 | none | not at all |
| [B1-02](#b1-02) | 使用期間の漏洩 | B1 | geometric recurrence（補充なし: 交換後の経過年 a に対し m0·λ·(1−λ)^(a−1)）と constant per year（補充あり: m0·λ）。交換事象（periodic events with peri | sum up to ceil(T) with a prorated last year（最終年の漏洩は m·λ·w_Y の比例配分）。補充ありは m0·λ·g·T。補充なしは区間ごとの等比和で、T は最後の区間の長さと事象数 N(T, se |
| [B1-03](#b1-03) | 更新時の漏洩 | B1 | periodic events with period service_life、または explicit event list。振幅は交換直前の状態（補充なしでは区間の長さに依存） | step function via N(T, service_life)（事象が 1 つ増えるたびに 1 項増える）。端数の最終年に事象が入ると、その事象の残存量に最終年の重み w_Y が入る |
| [B1-04](#b1-04) | 廃棄時未回収量 | B1/C | 評価期間の終わりに 1 回だけの量。値は最後の交換からの経過年数で決まる | depends on T only through 最後の区間の年数（Y − 最後の事象年）と最終年の重み w_Y。補充ありなら T に依存しない（m0·(1−η)·g） |
| [B5-01](#b5-01) | 大型改修・建替イベント | B5 | periodic events with period C（非整数可）。振幅 φ·base は一定 | step function via N(T, C) |
| [X-06](#x-06) | 電力排出係数の年次系列の生成 | B6 | constant per year \| piecewise linear in year（1 次の低下の後に一定）\| 段差（区分一定）\| 表（任意） | 系列の長さ Y = ceil(T) だけが T に依存する。各年の値は T に依存しない |
| [B6-04](#b6-04) | オンサイト発電の扱い | B6 | 3 系列がすべて CONSTANT / LINEAR_TREND なら max(0, α + β·k)（piecewise linear in year、折れ点は高々 1 つ）。TABLE を含めば任意 | 系列の長さ Y = ceil(T) だけが T に依存する |
| [B6-01](#b6-01) | 年間買電排出 | B6 | 2 つの年次系列の年ごとの積。両方が k の 1 次式なら k の 2 次式、打切り・段があれば区分多項式 | 系列の長さ Y = ceil(T) だけが T に依存する |
| [B6-02](#b6-02) | 燃料の年間排出 | B6 | constant per year \| linear in year \| 表（燃料ごと）。和は k の 1 次式 + 表の成分 | 系列の長さ Y = ceil(T) だけが T に依存する（_lines の活動量は年重み付きの和なので T に依存する） |
| [B6-03](#b6-03) | 評価年数の積算 | B6 | 年次系列の年重み付きの和 | sum up to ceil(T) with a prorated last year |
| [B2-01](#b2-01) | 施設管理に帰属させる運用負荷 | B2 | 年次系列の年重み付きの和に 1 つの比率を掛ける | sum up to ceil(T) with a prorated last year |
| [X-11](#x-11) | 床面積当たり統計値による運用エネルギーの推定 | B6 | 電力排出係数の年次系列の年重み付きの和に、年によらない量を掛ける | sum up to ceil(T) with a prorated last year |
| [B7-01](#b7-01) | 上水利用排出 | B7 | constant per year \| linear in year \| 表 | 系列の長さ Y = ceil(T) だけが T に依存する（_lines の活動量は年重み付きの和なので T に依存する） |
| [B7-02](#b7-02) | 下水処理排出 | B7 | constant per year \| linear in year \| 表 | 系列の長さ Y = ceil(T) だけが T に依存する（_lines の活動量は年重み付きの和なので T に依存する） |
| [B7-03](#b7-03) | 一般廃棄物排出 | B7 | constant per year \| linear in year \| 表 | 系列の長さ Y = ceil(T) だけが T に依存する（_lines の活動量は年重み付きの和なので T に依存する） |
| [B7-04](#b7-04) | 評価期間積算 | B7 | 年次系列の年重み付きの和 | sum up to ceil(T) with a prorated last year |

## 数学的な構造による群（分類担当の提案）

### G-A

- 定義：格子事象の数え上げ。正の有限な周期 c に対し P(T,c) = { n·c : n ≥ 1, n·c < T(1−ε) }、N(T,c) = |P(T,c)| = max(0, ceil(T(1−ε)/c) − 1)、ε = 1e-9。明示一覧なら X(T, list) = [ t : t > 0, t < T(1−ε) ]。自由なデータ: 行ごとの周期 c または事象時刻の一覧と T。出力は整数と時刻の一覧で、排出量を持たない。
- 属する単位：B4-01、B4-03
- 理由：どちらも入力 1 つ（周期または一覧）と T だけで決まる段差関数で、同じ補助関数（周期の倍数の数え上げ）を使う。振幅も係数も掛からない。
- 境界にある単位：B1-02 の交換事象、B5-01 の建替事象、B3-01 の除外年は同じ数え上げを内部に持つが、振幅または状態が掛かるので別の群に置いた；B4-01 の明示一覧は周期を持たない（有限個の点の集合）。周期の式には入らないが、事象時刻の一覧という同じデータ型には入る
- 候補になる変換：
  - 閉じた形 N = max(0, ceil(T(1−ε)/c) − 1)（行ごとに定数回の演算）。データは c。基準計算は乗算 n·c と T(1−ε) の比較で数えるので、除算に置き換えるときは境界の一致を検査する必要がある
  - 周期の値の度数表: 異なる周期ごとに 1 回だけ N を計算する（N は (T, c) だけの関数）。データは異なる周期の集合
  - 明示一覧と周期を 1 つのデータ型に統一: 行×年の事象数行列 K[k, y] = #{ τ : yr(τ) = y }（疎）。整数周期では K[k, y] = [c_k が y を割り切る]·[y < T(1−ε)]
  - 分解 N(T,c) = T(1−ε)/c − s(T(1−ε)/c)、s(x) = x − ceil(x) + 1 ∈ (0, 1]。T に比例する部分と、0 より大きく 1 以下の鋸歯の部分に分かれる

### G-B

- 定義：行の振幅 × 事象の回数。E(T) = Σ_k u_k·n_k(T)、by_year[y] = Σ_k u_k·K_k(y)、n_k(T) = Σ_y K_k(y)。u_k は T によらない行の振幅（上流の積和の小計）、K_k(y) は G-A の年ごとの事象数。自由なデータ: (u_k, 周期 c_k または一覧)。周期の値で集約すると E(T) = E_explicit(T) + Σ_c N(T,c)·U_c、U_c = Σ_{k: c_k = c} u_k。
- 属する単位：B4-02、X-08、B5-01
- 理由：3 単位とも「T によらない振幅」と「期間内の事象の個数」の積の和で、年重みを掛けない。X-08 は B4-02 と同じ量を周期の値で群別したもの。B5-01 は行が 1 つ（振幅 φ·base、周期 C）の場合。
- 境界にある単位：B1-03: 振幅が交換直前の残存量（状態）に依存する。補充ありの機器では振幅が ρ·g·m0 の定数になり、この形に完全に入る；B4-02 の n_partial: 数値の和ではなく述語の件数で、同じ行の走査から出る別の出力；X-08 の by_cycle: 表に現れるのは N(T,c) > 0 の周期だけなので、表の行集合が T に依存する（合計値は全行で集約しても同じ）
- 候補になる変換：
  - 周期軸への集約（厳密）: U_c を先に作り Σ_c N(T,c)·U_c を計算する。データは (c, U_c) の表。行ごとの出力が要る場合は u_k·N(T,c_k)
  - 整数周期のとき by_year[y] = Σ_{c が y を割り切る} U_c（y < T(1−ε)）。周期軸の関数 U と定数関数 1 のディリクレ畳み込みであり、母関数は Σ_c U_c·z^c/(1 − z^c)（ランベルト級数の形）。累積は Σ_c U_c·floor(M/c)、M は T(1−ε) 未満の最大の整数（T が整数なら T−1）
  - 線形 + 鋸歯: E = T(1−ε)·Σ_c U_c/c − Σ_c U_c·s(T(1−ε)/c)。第 1 項は年率 Σ_c U_c/c の一定の年次系列の積算（G-E の形）、第 2 項は U_c ≥ 0 のとき 0 より大きく Σ_c U_c 以下。第 2 項を落とした近似の誤差は高々 Σ_c |U_c|（各行で事象 1 回分）
  - 係数空間での行の重み付け: 上流の（行 × 係数 ID）の活動量行列を A とすると、B4 の活動量ベクトル = n(T)^T·A（行ごとの回数を重みとする行の線形結合）、B5 は対象の全行に同じ重み N(T,C)·φ。データは行の重みベクトル

### G-C

- 定義：年次系列の生成器。k = 0..Y−1 の系列 s_k を記述子または表から作る。共通の形: s_k = a + b·k + Σ_m h_m·max(0, k − κ_m) + Σ_m d_m·[k ≥ κ'_m]（次数 1 以下のスプライン。節点 κ_m、κ'_m と係数がデータ）、または s_k = table[k]。
- 属する単位：X-06、B6-04
- 理由：入力の記述子から年ごとの値を作るだけで、積算も排出係数の乗算もない。非線形は max による折れ（X-06 は下限、B6-04 は 0）と段だけ。
- 境界にある単位：B6-04: 3 系列の線形結合の後に max(0, ·) を取る。3 系列がすべて記述子なら折れは高々 1 つだが、表を含むと年ごとの max になり節点で書けない；X-06 の記述子の整合判定（wf）と matches_table は数値ではなく、生成規則の選択と報告
- 候補になる変換：
  - 1 次スプライン基底 {1, k, max(0, k−κ), [k ≥ κ]} の係数ベクトルで全種類を表す。CONSTANT: a = start。LINEAR_DECLINE_TO_FLOOR: a = start、b = −d、折れ h = +d、節点 κ = (start − floor)/d。STEPWISE: 段の差分 Δ_s。TABLE: Y 個の段。B6-04（記述子のみ）: α + β·k の折れ 1 つ、α = base_c − cg·base_g + cx·base_x、β = slope_c − cg·slope_g + cx·slope_x、節点は −α/β
  - 差分表現: 記述子の系列は 1 階または 2 階の差分が節点でだけ非零（疎）で、累積和で元に戻る。データは節点と差分の値
  - 積算との合成: スプラインの各基底の年重み付き和は閉じた形（部分モーメント）で書けるので、系列を年に展開せずに G-E の値を得られる

### G-D

- 定義：年次率の系列 = Σ（年次量 × 換算倍率 × 係数）。r_y = Σ_f m_f·q_f(y)·κ_f·F_f(y)、m_f ∈ {0,1} は使用可否、q_f は G-C 型の系列（記述子または表）、F_f(y) は定数（係数値）または年次系列（電力排出係数）。出力は年当たりの率（kgCO2e/年）で、年重みを掛けない。
- 属する単位：B6-01、B6-02、B7-01、B7-02、B7-03
- 理由：同じ形（系列 × 倍率 × 係数）の和。B6-02 と B7-01〜B7-03 は同じ補助関数を使い、系列の本数と係数の対象段階だけが違う。B6-01 は係数の側も年次系列。
- 境界にある単位：B6-01: 2 つの年次系列の年ごとの積（係数が年で変わる）。他の 4 単位は係数が年によらない；B6-02・B7-0x の _lines は年重み付きの和を含むので、この出力だけは G-E の形
- 候補になる変換：
  - 行列・ベクトル積: r = Q^T·(m ⊙ κ ⊙ F)、Q は（系列 × 年）の行列。記述子の系列は Q の行が [base, slope]·[1, k] の階数 2 なので、年に展開する前に A0 = Σ_f base_f·κ_f·F_f、A1 = Σ_f slope_f·κ_f·F_f に集約できる。表の系列だけ年ごとに残る
  - 係数を「年次系列の係数」に統一: 定数の係数を一定の系列とみなすと、5 単位すべてが「2 系列の年ごとの積の和」になる。スプライン同士の積は区分 2 次
  - B6-02 と B7-01〜B7-03 の 6 系列を 1 つの表（系列、係数 ID、対象段階）にして 1 回の積和で処理する。B6 と B7 の違いは係数の対象段階というデータになる

### G-E

- 定義：年重み付き積算。E(T) = c·Σ_{y=1..Y} w_y·s_y、w_y = min(1, T−(y−1))、Y = ceil(T)、c は T によらない倍率（比率、面積×原単位×換算倍率、または 1）。同値な形: 累積系列 S(n) = Σ_{y≤n} s_y を T で 1 次補間した値。s が定数なら E = c·s·T。
- 属する単位：B6-03、B7-04、B2-01、X-11、B3-02
- 理由：年次系列と年重みの内積に定数を掛ける形。B3-02 は系列が定数（行の和 R = Σ e0·r）の場合で T·R。
- 境界にある単位：B3-02: 年次系列を持たず T を直接掛ける。G-H（時間によらない積和）に T を掛けたものとも読める；B3-01: 同じ内積から更新年を除いたもの（G-F）；補充ありの機器の B1-02: m0·λ·g の一定系列の積算でこの形
- 候補になる変換：
  - 年重みのモーメント: μ_p(T) = Σ_{y=1..Y} w_y·(y−1)^p。μ_0 = T、μ_1 = (Y−1)(Y−2)/2 + (T−(Y−1))·(Y−1)。記述子の系列（k の多項式）の積算は Σ_p a_p·μ_p(T)。B6-01 の積（1 次 × 1 次）は μ_2 まで要る。データは多項式の係数
  - 区分多項式（折れ・段あり）: 節点で区切った部分モーメント。データは節点と区間ごとの係数
  - 累積系列の 1 次補間: S を 1 回作れば任意の T の値を定数回の演算で読める。事象の和（G-B）は同じ「累積を T で読む」操作で、補間が段差になるだけ
  - 共有: Σ_y w_y·elec_y は B6-03、B2-01、別ファイルの X-07 で計 3 回計算される。1 回計算して (1−s, s) で分ければよい

### G-F

- 定義：更新年を除いた年重み付き積算。E(T) = Σ_k a_k·Σ_{y=1..Y} w_y·(1 − min(1, K_k(y)))、a_k = e0_k·r_k（T によらない）、K_k(y) は行 k の年 y の事象数（G-A）。同値: E = T·Σ_k a_k − Σ_k a_k·Σ_{y∈S_k} w_y、S_k = { y : K_k(y) ≥ 1 }。
- 属する単位：B3-01
- 理由：G-E（一定の年次系列の積算）と G-B（振幅 × 事象）の差の形で、どちらか一方だけでは書けない。除外は年の箱の単位（集合）で行い、事象の個数には比例しない。
- 境界にある単位：同じ行の事象が同じ年に 2 つ入らず、除外年の重みがすべて 1（T が整数、または最終年に事象がない）なら E = Σ_k a_k·(T − N(T,c_k)) となり、G-E の項 T·R と G-B の項 Σ_c N(T,c)·R_c（R_c = Σ_{k: c_k = c} a_k）の差に厳密に分かれる
- 候補になる変換：
  - 条件付きで厳密な分解: T·R − Σ_c N(T,c)·R_c。条件外の補正は Σ_k a_k·(1 − w_Y)·[Y ∈ S_k] と、同じ年に重なった事象の数の補正
  - 行×年のマスク行列 M[k, y] = 1 − min(1, K[k, y]) を G-B の事象数行列 K と共有する
  - 周期の値ごとの集約: R_c を先に作る（a_k は T によらない）

### G-G

- 定義：リセット付きの 1 階線形再帰（状態 = 残存量）。m(1) = m0。年 y: flow(y) = α·m(y)·w_y、m'(y) = m(y)·(1 − β·λ·w_y)。事象のある年は lump(y) = γ·m'(y) を出して m(y+1) = m0、ない年は m(y+1) = m'(y)。期末に term = δ·m(Y+1)。B1-02: α = λ·g、β = 1−τ（τ = 補充の有無）。B1-03: γ = ρ·g。B1-04: δ = (1−η)·g。自由なデータ: (m0, g, λ, τ, ρ, η, 事象年)。
- 属する単位：B1-02、B1-03、B1-04
- 理由：3 単位は 1 つの状態列 m(y) の 3 通りの読み出し（年次の流れ、事象時の塊、期末の残り）で、B1-03 と B1-04 は B1-02 の状態を読む。出力は m0·g に比例する。
- 境界にある単位：補充あり（τ = 1）では状態が一定になり、B1-02 は G-E（m0·λ·g·T）、B1-03 は G-B（N·ρ·g·m0）、B1-04 は G-H（定数）に落ちる；同じ年に事象が 2 つ以上ある場合、2 つ目以降の塊は m0 で計算する（再帰の式の外の規則）
- 候補になる変換：
  - 区間ごとの閉じた形: 残存量 = m0·Π_{y∈I}(1 − β·λ·w_y)、全年が満年なら m0·q^ℓ（q = 1−λ、ℓ = 区間の年数）。整数の T と周期 L、補充なし、K = N(T,L): B1-02 = g·m0·[K·(1 − q^L) + 1 − q^(T−K·L)]、B1-03 = ρ·g·m0·K·q^L、B1-04 = (1−η)·g·m0·q^(T−K·L)
  - 質量保存で 3 単位を 1 式にまとめる（整数、補充なし）: 機器の B1 合計 = g·m0·[(K+1) − (1−ρ)·K·q^L − η·q^(T−K·L)]
  - 対数変換: log(残存量/m0) = Σ_{y∈I} log(1 − β·λ·w_y) は年重み付きの和（G-E の形）で、リセットは G-A の事象。指数関数 1 回で戻す
  - 2×2 のアフィン遷移行列の積（座標 (m, m0)）。整数周期 L では L 年分の積が同じ行列の繰り返しになり、累乗で書ける
  - 振幅の分離: (λ, τ, 事象の型) が同じ機器は Σ m0·g、Σ ρ·m0·g、Σ (1−η)·m0·g の 3 つの小計に先に集約できる（B1-01 の被加数と同じ積）

### G-H

- 定義：時間に依存しない行の積和。E = Σ_k m_k·x_k·y_k、m_k ∈ {0,1} は有効性。n_skipped = Σ_k (1 − m_k)。
- 属する単位：B1-01
- 理由：T も年も事象も現れない。
- 境界にある単位：B3-02 はこの形に T を掛けたもの；B5-01 の base、B4-02 の u、B3-01 の e0·r、B1 の m0·g はこの形の小計で、時間の核を掛ける前の振幅にあたる
- 候補になる変換：
  - マスク付きの内積 1 回。上流の A・C 段階の「数量 × 換算倍率 × 係数」の和と同じ演算
  - 値と件数を (m·x·y, 1−m) の 2 列として同じ和の演算で同時に出す

## 統合にかかわる横断の観察

- 記法。T = boundary.study_period（有限の正数、非整数可）。ε = 1e-9。Y = ceil(T)。w_y = min(1, T−(y−1))（y = 1..Y）、Σ_y w_y = T。N(T,c) = #{ n ≥ 1 : n·c < T(1−ε) }（c が有限の正数でなければ 0）。yr(τ) = max(1, ceil(τ(1−ε)))。nonneg(x) = [x ≠ None ∧ x ≥ 0 ∧ 有限]、positive(x) = [x ≠ None ∧ x > 0 ∧ 有限]、ratio(x) = [x ≠ None ∧ 0 ≤ x ≤ 1]。lookup(fid, s, unit[, 行固有の換算]) は、記録があり、licence_status = PERMITTED_PUBLIC、stages = [s]、unit から記録の単位への換算が 1 回で引ける（同じ単位なら 1、行固有の換算、共通の換算の順。連鎖・逆引きなし）ときだけ (係数値, 換算倍率) を返す。prof(p, k) = base（CONSTANT）、base + slope·k（LINEAR_TREND）、table[k]（それ以外）。au(unit) は '<u>/year' の <u>。[P] は述語 P が真なら 1、偽なら 0。
- 全 22 単位の数値出力は value(T) = Σ_θ A_θ·κ_θ(T) の形に書ける。A_θ は T によらない振幅（行の積和の小計: u、e0·r、m0·g、φ·base、年次量×κ×F）、κ_θ(T) は時間の核で 4 種類: (a) 年重み付きの前方和 Σ_{y≤Y} w_y·s_y、(b) 事象の個数 N(T,c)、(c) 更新年を除いた年重みの和 T − Σ_{y∈S} w_y、(d) リセット付きの等比の積 Π(1 − λ·w_y)。行に依存する部分と T に依存する部分は、核のパラメータ（周期、漏洩率と補充の有無、系列の形）が同じ行の中で分離する。
- 同じ数え上げ N(T,c) と同じ境界規則（T(1−ε) 未満）を使う箇所: B4-01（設備の耐用年数）、B4-03（資材の更新周期）、B4-02（資材の事象時刻の作り直し）、B3-01（除外年）、B1-02（機器の耐用年数）、B5-01（建替周期）、別ファイルの X-10。(T, c) の関数 1 つで足りる。
- 年重み w_y を使う単位は B3-01、B1-02、B6-03、B2-01、X-11、B7-04 と B6-02・B7-0x の _lines。事象の和（B4-02、B5-01、B1-03）は年重みを使わないので、端数の最終年に入る事象も全額になる。年次の流れと事象とで端数年の扱いが違う点は、再構成で保つ必要がある。
- by_year の意味が 2 通りある。B6-01、B6-02、B7-01〜B7-03、X-06、B6-04 は年当たりの率または水準（年重みを掛ける前）、B4-02、B3-01、B1-02、B1-03、B5-01 は年重み込みまたは事象の発生額。別ファイルの X-07 は前者にだけ w_y を掛ける。どちらも Y+1 個で添字 0 は常に 0。
- 共有される小計。(1) 更新 1 回当たりの排出 u は B4-02 と X-08 で同じ式を 2 回計算する。(2) 初期の製造排出 e0（A13-01 + A13-03、設備は X-01）は B3-01、B3-02 で使い、B4-02 の u の一部でもある。(3) 買電排出の年重み付き合計 G = Σ_y w_y·elec_y は B6-03、B2-01、別ファイルの X-07 で計算する。(4) 電力排出係数の系列 g_y は B6-01 と X-11 の両方に掛かる。(5) m0·g は B1-01 の被加数で、B1-02〜B1-04 の全出力の共通因子。(6) B5-01 の base は別ファイルの段階ベクトルの A1-A3 + A4 + A5 + C1〜C4 と同じ 12 個の値の和。
- 条件分岐を 0/1 のデータにできる箇所。(1) 有効性の述語（nonneg、ratio、lookup の可否）は行のマスク m ∈ {0,1} として積に掛け、件数は Σ(1−m)。(2) top_up は τ ∈ {0,1} として 1 − (1−τ)·λ·w_y に入る。(3) 明示一覧と周期の分岐は、事象を行×年の事象数行列または事象時刻の一覧として持てば消える。(4) reconstruction_scenario = NONE と範囲比の有効性は B5-01 の積の 0/1 因子になる。(5) 電力係数の 4 種類の生成規則と年次量の 3 種類は、1 次スプラインの係数（節点と差分）にすれば種類の分岐が消える。(6) B6-04 の max(0, ·) と X-06 の max(floor, ·) は折れ（節点 1 つ）で、記述子だけなら節点の位置がデータになる。(7) B3-01 の「r = 0 または e0 = 0」は数値に影響しない（行の一覧が空になるだけ）。(8) B4-02 の据付・搬入の項の有無は項ごとのマスク。
- 比を対で持てる箇所。(1) N(T,c) の中の T/c: 基準計算は除算せず n·c と T(1−ε) を比べるので、(T, c) の対で持つと境界の判定が変わらない。(2) 年率 u/c（線形 + 鋸歯の分解の線形部分）は (u, c) の対。(3) X-06 の折れ点 (start − floor)/annual_decline は annual_decline = 0 で定義できないので (start − floor, annual_decline) の対。(4) B2/B6 の配分は (s, 1−s)、B1 の事象時と期末は (ρ, 1−η) の対で、どちらも 1 つの量の分割。(5) B6-04 の節点 −α/β も β = 0 がありうるので対。
- 時間と行の分離。B4-02: Σ_c N(T,c)·U_c（X-08 がこの形）。B5-01: N(T,C)·φ·base（完全に 1 項）。B3-02: T·R（1 項）。B3-01: T·R − Σ_k a_k·Σ_{y∈S_k} w_y。B6-02・B7-0x（記述子）: A0·μ_0(T) + A1·μ_1(T)（時間の基底 2 つ）。B6-01: 買電量の系列と係数の系列の双線形形式。B1-02〜B1-04: m0·g × (λ, τ, 事象の型, T) の核。本ファイルが読む上流の単位（A13-01、A13-03、A13-04、A13-05、A4-01、A4-02、A5-04、C1-01、C2-01、C3-01、C4-01、X-01、X-14）の関数は study_period を読まないので、振幅は T によらない。
- 係数値に対する線形性。全単位の value は (係数 ID, 活動量) の行の和 Σ a·f であり（買電と冷媒は擬似 ID の GRID、REFRIGERANT）、係数値ベクトル f に線形。B3-01 の行 = 上流の A1-A3 の行 × r·W、B4-02 の行 = 上流の行 × 回数、B5 の行 = 上流の全行 × N·φ。つまり B3・B4・B5 は同じ上流の活動量行列（行 × 係数 ID）に、T に依存する行の重みを掛けたもの。別ファイルのガス別集計がこの行の一覧を読むので、再構成では value だけでなく活動量ベクトルを出せる形が要る。
- 時間軸の測度としての見方（手計算による整理。数値検証は未実施）。年次の流れは年ごとに一定の密度 s_⌈t⌉、事象は時刻 n·c の点質量 u とすると、value(T) は測度の区間 (0, T) の質量で、密度の部分は T に連続な区分 1 次、点質量の部分は段差。by_year は年の箱 (y−1, y] ごとの質量。例外: B3-01 は T が更新時刻を越えると最終年の修繕が 0 に戻るので、非整数の T では固定した測度の累積にならない。B1-02 は年末にリセットする規則なので、年の途中の事象を点として扱うと一致しない。
- 整数の場合の構造（仮説。手計算による導出で、数値検証は未実施）。T が整数、周期がすべて正の整数（または有理数）、年次量と電力係数が記述子で折れ・段をまたがない範囲では、本ファイルの value(T) はすべて T の準多項式（係数が周期的な多項式）になる。事象は 1 次（周期 c）、一定の流れは 1 次、1 次の傾向は 2 次、1 次の買電量 × 1 次の係数は 3 次、冷媒は 1 次で、周期的な係数に q^(T−K·L)（T を L で割った余りで決まる）が入る。同値に、年次系列の母関数は極が 1 の冪根だけの有理関数（事象: z^c/(1−z^c)、流れ: 1/(1−z)、z/(1−z)^2、積算: 1/(1−z) を掛ける）。反証になるもの: 整数でない周期（周期の最小公倍数が大きくなり、準多項式の周期が実用的な長さでなくなる）、TABLE 種別の系列（任意の数列）、折れ・段の節点をまたぐ T、非整数の T（流れは比例配分、事象は全額という不揃い）、明示一覧の事象（有限個の項が加わるだけで有理性は保つが、周期の集約には入らない）。
- 2 種類の時計。年次量と電力係数は暦年（評価年 y）の関数、冷媒の残存量は最後の交換からの経過年数の関数、更新・建替は周期の位相の関数。本ファイルでは、1 つの単位が暦年の系列と経過年数の両方に同時に依存する式はない（B6-01 は暦年の系列 2 本の積）。
- 浮動小数点。基準計算は和を反復加算で作る（N·u ではなく u を N 回足す、年ごとに足す）。閉じた形や集約に置き換えると丸めの範囲で差が出る。X-08 と B4-02 は同じ量を別の加算順で計算しており、一致の検査はない。
- 依存の形。A・C 段階の行結果 → B3-01、B3-02、B4-02、X-08、B5-01。B4-01、B4-03 → B4-02、X-08、B3-01。X-06、B6-04 → B6-01 → B6-03、B2-01。X-06 → X-11。B6-02 → B6-03。B7-01〜B7-03 → B7-04。B1-02 → B1-03、B1-04。B1-01 はどの単位からも読まれず、どの単位も読まない。関数の中で study_period を直接読まないのは X-08、B1-01、B1-04、B6-01 の 4 単位で、このうち X-08、B1-04、B6-01 は上流の結果を通じて T に依存し、B1-01 だけが T に依存しない。

## 定義文とコードの違い

- B4-01: 文は明示一覧の重複と順序に触れていない。コードは一覧の順を保ち、重複した年を 2 回数える（B1-02 の機器の一覧は整列する）。空の一覧（None ではない）は「事象なし」となり、耐用年数を使わない。
- B4-01・B4-03: 文は周期が「欠損・非正」なら事象なしと書く。コードは無限大と NaN も事象なしにする。B5-01 と B1-02 の文は周期が無効な場合に触れていない（コードは同じ規則で事象なしにする）。
- B4-02: 文は「資材は B4-03 の回数だけ繰り返す」。コードは B4-03 の回数を 0 か否かの判定にだけ使い、事象時刻を周期から作り直す（数値は同じ）。
- B4-02: 文は資材の製造を「A1-A3 の行結果」と書く。コードは A13-01 と A13-03 だけを足し、A13-04（未数量の上乗せ）を足さない。C2 は行の搬出だけで建物単位の搬出を含まない。文はこの 2 点に触れていない。
- B4-02: 文は端数の最終年の扱いに触れていない。コードは事象の排出に年重みを掛けない。
- B4-02: 設備の u はコードでは行の一覧（活動量×係数値）から計算し、X-08 は by_item の和から計算する。文は区別していない（数値は丸めの範囲で同じ）。資材の据付の検索は行固有の換算を使い、設備の検索は使わない点も文にない。
- X-08: 文は「合計は B4-02 に一致する」。コードは B4-02 の結果を読まず、一致を検査しない。依存の宣言に B4-02 があるが読まれない。
- X-08: 文は明示一覧の設備を「EXPLICIT」にまとめると書く。コードでは by_cycle の項目ではなく、別のキー explicit のスカラーである。資材と設備で同じ数値の周期が同じ群に合算されること、count が最後に処理した行の値で上書きされることは文にない。
- B3-01: 文は「修繕率が欠損・負の行は足さずに数える」。コードは、上流で除外された行（e0 = 0.0）を数えずに 0 として通す。修繕率の上限は検査しない。e0 が A13-04 を含まないことは文にない。
- B3-01: 文は「更新が属する年は修繕を計上しない」。コードは年の箱の単位で除外するので、年の途中の更新でも年全体を除き、同じ年の複数の更新は 1 回の除外になる。非整数の T で最終年に更新が入ると最終年の端数分が 0 になる。文はこれらに触れていない。
- B1-02: 文は同じ年に交換が 2 回以上ある場合に触れていない。コードは 1 回目に漏洩後の残存量、2 回目以降に初期充填量を「交換直前の残存量」として記録する。
- B1-02: 文は最終年の端数の扱いを「年重み」とだけ書く。コードは m·λ·w_Y の 1 次の比例配分で、補充なしの残存量もその分だけ減らす。change_years と service_life の両方がある場合に一覧が優先されることは文にない。
- B1-03: コードは事象が 0 件の機器でも、損失率が無効なら n_skipped に数える。B1-02 で除外された機器は B1-03 と B1-04 でも数えるので、同じ機器が 3 つの単位で数えられる。文は件数の重なりに触れていない。
- B1-04: 台帳の段階は「B1/C」。コードの段階ベクトル（別ファイルの X-02）は B1 に入れる。年 Y に交換があると期末の残存量は初期充填量になることは文にない。
- B5-01: 文は「範囲比が欠損または 0〜1 の外なら算出しない」。コードは建替シナリオが NONE のときは範囲比を見ずに computed = 真とする。建替周期が無効なら 0 回で computed = 真（未算出の印が付かない）。REBUILD_IDENTICAL と MAJOR_REFURBISHMENT は区別しない。base は対象段階の指定によらず 12 単位すべてを足す。上流の欠落は computed に反映しない。
- X-06: 文にない点: by_year[0] は 0.0（工事期間の値ではない）、一致判定は相対 1e-12、年次表を使った場合 matches_table は自明に真、使用許諾はこの単位では見ない、値の符号を検査しない。
- B6-04: 文は「記述子があればその値」。コードは kind が CONSTANT でも base が None なら年次表を使う。年次量の符号、売電 ≤ 発電 は検査しない。descriptors_match_tables は未算出のときも報告する。
- B6-01・B6-02・B7-01〜B7-03: 文は「評価年ごとに」と書くが、by_year が年重みを掛ける前の率であることを明記していない。base.py の冒頭の説明も by_year の 2 通りの意味（率と発生額）を区別していない。B6-02・B7-0x の _lines は年重み込みで、by_year と時間の扱いが違う。
- B6-02: 係数 ID が None の燃料も n_skipped に数える（その燃料を使わない建物でも係数 ID が要る）。文は「係数が使えない燃料」としか書いていない。descriptors_match_tables は使えない燃料の系列も判定に入れる。
- B2-01: 文は「B2 が対象段階に入っている場合に限り B6 から差し引く」と書くが、この処理は B2-01 の関数にはなく、別ファイルの X-02 にある。B2-01 は B6-01.computed を見ないので、B6-01 が未算出でも value = 0.0、computed = 真を返す。
- X-11: 文は「算出しない」とだけ書く。コードは未算出を value = None で表し、computed のキーを持たない（他の単位は 0.0 と computed = 偽、または n_skipped で表す）。
- 入力モデル（synth/model.py）との差: reconstruction_scope_fraction、facility_management_ratio、electricity_per_m2_per_year は型の上では必須の数だが、コードは None を想定して判定する。事象年の一覧は整数とされるが、コードは正の実数を受け付ける。年次量の表の長さは実行の入口で検査しない（検査するのは grid.table だけ）。

## 単位ごとの記録

<a id="b4-01"></a>

### B4-01　更新イベント年の生成（B4）

- 式：ev_j = [ float(t) : t ∈ replacement_event_list_j, t > 0, t < T(1−ε) ]  （replacement_event_list_j ≠ None のとき。一覧の順と重複を保つ）。 ev_j = [ n·L_j : n = 1..N(T, L_j) ]  （一覧が None のとき、L_j = service_life_j）。 N(T, L) = #{ n ∈ {1,2,...} : n·L < T(1−ε) } = max(0, ceil(T(1−ε)/L) − 1)  （L が有限の正数のとき）、N = 0（L が欠損・0 以下・無限大・NaN のとき）。 n_events = Σ_j |ev_j|。 ε = 1e-9。
- 宣言された依存：なし　／　実際に読む結果：なし
- 宣言に無い読み取り：なし　／　宣言したが読まない：なし
- 入力：boundary.study_period、equipment.replacement_event_list、equipment.service_life
- 添字の集合：設備の行 j（equipment）、明示一覧の要素 t、周期事象の番号 n = 1..N(T, L_j)
- 出力：events（per-row list）、n_events（count）
- 演算：predicate（一覧の要素の絞り込み）、floor/ceil（数え上げ。乗算 n·L と T(1−ε) の比較の反復）、一覧の生成、sum over rows（個数の合計）
- 線形性：線形＝なし（出力は事象時刻の一覧と個数）。個数が変わらない範囲では周期事象の時刻 n·L_j は L_j に比例する　／　非線形＝T: 段差（T が n·L/(1−ε) を越えるたびに事象が 1 つ増える）、L_j: 段差と反比例（N ≈ T/L）、replacement_event_list の有無: 分岐（一覧があれば service_life を読まない）
- 時間の構造：periodic events with period L_j（非整数可）、または explicit event list
- T への依存：step function via N(T, L_j)。明示一覧は [t < T(1−ε)] による段差。事象の時刻そのものは T に依存しない
- 周期性：周期は equipment.service_life（浮動小数、非整数可）。明示一覧は入力モデル上は整数の年ずれだが、コードは正の数なら何でも受け付ける
- 条件分岐：replacement_event_list ≠ None → 一覧を使い service_life を無視する（空の一覧なら事象なし）；一覧の要素: t > 0 かつ t < T(1−ε) のものだけ残す；service_life が None・0 以下・無限大・NaN → 事象なし；n·L < T(1−ε) を満たす n だけ: T ちょうど、または T から相対 1e-9 以内の事象は含めない
- 除外と件数：除外の件数は数えない。フラグもない。耐用年数が無効な行は空の一覧になるだけで、区別できない
- 仕事の増え方：行数 n_eq と事象数の合計 Σ_j |ev_j| に比例（数え上げは事象 1 つにつき 1 回の比較）。閉じた形を使えば個数だけなら行数に比例
- 注記：明示一覧は並べ替えない（B1-02 の機器は並べ替える）。重複した年はそのまま 2 回数える。事象を年に割り当てる規則 yr(τ) = max(1, ceil(τ(1−ε))) はここでは使わず、下流（B4-02、B3-01）が使う。events は B4-02、X-08、B3-01、別ファイルの X-10 が読む。数え上げは乗算 n·L と T(1−ε) の比較であり、除算 ceil(T(1−ε)/L) に置き換えると浮動小数点の境界で 1 件ずれる可能性がある

<a id="b4-03"></a>

### B4-03　交換回数の概算（B4）

- 式：by_item[i] = N(T, c_i)、c_i = refresh_cycle_i。 N(T, c) = #{ n ≥ 1 : n·c < T(1−ε) } = max(0, ceil(T(1−ε)/c) − 1)  （c が有限の正数）、0（それ以外）。 ε = 1e-9。
- 宣言された依存：なし　／　実際に読む結果：なし
- 宣言に無い読み取り：なし　／　宣言したが読まない：なし
- 入力：boundary.study_period、materials.refresh_cycle
- 添字の集合：資材の行 i（materials）、周期事象の番号 n = 1..N(T, c_i)
- 出力：by_item（per-row list）
- 演算：floor/ceil（数え上げ）、predicate（周期の有効性）
- 線形性：線形＝なし（出力は整数）　／　非線形＝T と c_i: 比 T(1−ε)/c_i の切り上げによる段差。出力は比 T/c だけで決まる
- 時間の構造：periodic events with period c_i（非整数可）
- T への依存：step function via N(T, c_i)
- 周期性：周期は materials.refresh_cycle（浮動小数、非整数可）
- 条件分岐：refresh_cycle が None・0 以下・無限大・NaN → 0 回；n·c < T(1−ε): 評価期間の終わりの更新は数えない
- 除外と件数：除外の件数は数えない。周期が無効な行と「周期が T 以上で 0 回」の行は同じ 0 になる
- 仕事の増え方：数え上げは Σ_i N(T, c_i) 回の比較。閉じた形なら行数 n_mat に比例
- 注記：value キーを持たない。by_item は B4-02、X-08、B3-01、別ファイルの X-10 が読む。B4-02 と B3-01 はこの回数を「0 か否か」の判定にだけ使い、事象時刻は周期から作り直す

<a id="b4-02"></a>

### B4-02　機器・資材更新負荷（B4）

- 式：資材 i: n_i = N(T, c_i)（c_i = refresh_cycle_i、N は B4-03 の式）。 u_i = Σ_{s∈S7} by_item_s[i] + [inst_i]·q_ord_i·κ_i·f_i^{inst}。 [inst_i] = [installation_factor_id_i ≠ None ∧ q_ord_i ≠ None ∧ lookup(installation_factor_id_i, 'A5', quantity_unit_i, conversions_i) が使用可]、κ_i はその換算倍率、f_i^{inst} は係数値。 E_i = Σ_{n=1..n_i} u_i （= n_i·u_i）。 設備 j: ev_j = B4-01.events[j]。 u_j = Σ_{(fid,a) ∈ X-01._row_lines[j] ++ extra_j ++ X-14._row_lines[j]} a·f_fid。 extra_j = [ (fid, quantity_j·κ) : (fid, s) ∈ ((delivery_factor_id_j,'A4'), (installation_factor_id_j,'A5')), fid ≠ None, lookup(fid, s, quantity_unit_j) が使用可, nonneg(quantity_j) ]。 E_j = |ev_j|·u_j。 by_item_material[i] = E_i、by_item_equipment[j] = E_j。 value = Σ_i E_i + Σ_j E_j。 by_year[y] = Σ_i u_i·#{ n ≤ n_i : yr(n·c_i) = y } + Σ_j u_j·#{ τ ∈ ev_j : yr(τ) = y }、yr(τ) = max(1, ceil(τ(1−ε)))。 n_partial = Σ_i [ n_i > 0 ∧ ( i ∈ M ∨ (installation_factor_id_i ≠ None ∧ ¬inst_i) ) ] + Σ_j [ |ev_j| > 0 ∧ ( j ∈ X-01._skipped_rows ∪ X-14._skipped_rows ∨ unusable_j ) ]、M = ∪_{s∈S7} _skipped_rows_s ∪ C3-01._partial_rows ∪ C4-01._partial_rows、unusable_j = extra の 2 つの係数のうち、ID はあるが lookup が使用不可または quantity_j が無効なものがある。 _mat_lines[i] = [ (fid, a·n_i) ]（a は S7 の _row_lines[i] と据付の行）、_eq_lines[j] = [ (fid, a·|ev_j|) ]。事象がない行は空。
- 宣言された依存：B4-01、B4-03、A13-05、A13-01、A13-03、X-01、A4-01、A4-02、C2-01、C3-01、C4-01、X-14　／　実際に読む結果：B4-01、B4-03、A13-05、A13-01、A13-03、X-01、A4-01、A4-02、C2-01、C3-01、C4-01、X-14
- 宣言に無い読み取り：なし　／　宣言したが読まない：なし
- 入力：boundary.study_period、materials.refresh_cycle、materials.installation_factor_id、materials.quantity_unit、materials.conversions、equipment.quantity、equipment.quantity_unit、equipment.delivery_factor_id、equipment.installation_factor_id、factors.value、factors.unit、factors.stages、factors.licence_status、unit_conversions、（結果経由）A13-05.q_ord、（結果経由）A13-01・A13-03・A4-01・A4-02・C2-01・C3-01・C4-01 の by_item / _row_lines / _skipped_rows、C3-01・C4-01 の _partial_rows、（結果経由）X-01・X-14 の _row_lines / _skipped_rows、（結果経由）B4-01.events、B4-03.by_item
- 添字の集合：資材の行 i、設備の行 j、行ごとの事象 n = 1..n_i、τ ∈ ev_j、評価年 y = 0..Y（by_year）、行ごとの排出の行（係数 ID, 活動量）、資材の構成要素 7 単位 S7 = {A13-01, A13-03, A4-01, A4-02, C2-01, C3-01, C4-01}
- 出力：value（scalar）、by_item_material（per-row list）、by_item_equipment（per-row list）、by_year（per-year series）、n_partial（count）、_mat_lines（per-row list）、_eq_lines（per-row list）
- 演算：sum over rows、sum over events（同じ値 u の反復加算）、product（発注量×換算倍率×係数、活動量×係数）、table look-up（係数の検索、単位換算）、floor/ceil（事象の年 yr、事象数 N）、predicate（係数の使用可否、部分欠落の判定）、散布加算（事象の年の箱へ u を足す）
- 線形性：線形＝上流の行結果 by_item_s[i]（7 単位）と X-01・X-14 の行の活動量、据付・搬入の活動量 q_ord_i、quantity_j、係数値 f（活動量を固定したとき）、行ごとの 1 回当たり排出 u_i、u_j（回数を固定したとき value = Σ n·u）　／　非線形＝T と周期 c_i、L_j: 段差（N(T,c)）、明示一覧の要素: 段差（期間内か否か）、活動量×係数: 2 入力の積（双線形）、係数の使用可否・欠損: 0/1 の切替
- 時間の構造：periodic events with period c_i / L_j、または explicit event list。行の振幅 u は時刻によらず一定
- T への依存：step function via N(T, c)。value = Σ_i N(T,c_i)·u_i + Σ_j |ev_j(T)|·u_j。u は T に依存しない
- 周期性：materials.refresh_cycle、equipment.service_life（どちらも非整数可）。明示一覧を持つ設備は非周期
- 条件分岐：B4-03.by_item[i] = 0 → その資材は事象なし（E_i = 0、行の一覧は空）；installation_factor_id_i = None → 据付の項なし（欠落とは数えない）；installation_factor_id_i ≠ None で q_ord_i = None または lookup 不可 → 据付の項を足さず、事象があれば n_partial に 1；i が S7 のいずれかで除外された行、または C3-01・C4-01 で経路が欠けた行で、事象がある → n_partial に 1（数値は届いた by_item をそのまま足す。除外された要素は 0.0）；設備: delivery / installation の係数 ID が None → その項なし。ID があり lookup 不可または quantity が無効 → その項を足さず unusable；設備: 事象があり、X-01 か X-14 で除外された行、または unusable → n_partial に 1；事象は発生年 yr(τ) の箱に全額を置く（年重み w_y を掛けない）
- 除外と件数：除外はしない（届いた構成要素だけを足す）。構成要素が欠けたまま更新が発生した行の数を n_partial に数える。別ファイルの X-02 は n_partial ≠ 0 のとき B4-02 を incomplete_units に入れる
- 仕事の増え方：行数 ×（構成要素 7 + 行の排出の行数）+ 事象数の合計。by_year への加算は事象 1 つにつき 1 回。周期別に集約すれば 異なる周期の数 × 事象数
- 注記：単位は kgCO2e。資材の u_i は A13-04（未数量の上乗せ）と A5 段階の現場排出を含まない。C2-01 は行の搬出分だけで、建物単位の搬出（waste_hauls）は含まない。設備の搬入・据付の係数を読むのは本ファイルでは本単位と X-08 だけ。資材の据付の lookup は行固有の換算（conversions）を使い、設備の lookup は使わない。_mat_lines / _eq_lines は別ファイルのガス別集計（stage_lines）が読むので、(係数 ID, 活動量×回数) の対を再現できる形が要る。Σ_y by_year[y] = value。最終年が端数でも事象は全額

<a id="x-08"></a>

### X-08　更新周期別の集計（B4）

- 式：資材 i（n_i = B4-03.by_item[i] > 0 の行だけ）: u_i は B4-02 と同じ式、key_i = repr(float(c_i))。 設備 j（|ev_j| > 0 の行だけ）: u_j = X-01.by_item[j] + X-14.by_item[j] + Σ_{(fid,a) ∈ extra_j} a·f_fid。 replacement_event_list_j ≠ None なら explicit += u_j·|ev_j|、そうでなければ key_j = repr(float(L_j))。 U_c = Σ_{key が c の行} u、count_c = その key の行の回数（最後に処理した行の値。同じ c なら N(T,c) は等しい）。 E_c = count_c·U_c。 value = explicit + Σ_{c, 数値の昇順} E_c。
- 宣言された依存：B4-01、B4-03、A13-05、A13-01、A13-03、X-01、A4-01、A4-02、C2-01、C3-01、C4-01、X-14、B4-02　／　実際に読む結果：B4-01、B4-03、A13-05、A13-01、A13-03、X-01、A4-01、A4-02、C2-01、C3-01、C4-01、X-14
- 宣言に無い読み取り：なし　／　宣言したが読まない：B4-02
- 入力：materials.refresh_cycle、materials.installation_factor_id、materials.quantity_unit、materials.conversions、equipment.service_life、equipment.replacement_event_list、equipment.quantity、equipment.quantity_unit、equipment.delivery_factor_id、equipment.installation_factor_id、factors.value、factors.unit、factors.stages、factors.licence_status、unit_conversions、（結果経由）A13-05.q_ord、S7 の 7 単位の by_item、X-01.by_item、X-14.by_item、B4-03.by_item、B4-01.events
- 添字の集合：資材の行 i、設備の行 j、周期の値 c（文字列キー repr(float(c))、数値の昇順）
- 出力：value（scalar）、by_cycle（table）、explicit（scalar）
- 演算：sum over rows（周期の値ごとの群別合計）、product（回数×群の合計）、table look-up（係数、周期キー）、sort / priority（キーの数値順）、predicate（回数 0 の行を除く、明示一覧の有無）
- 線形性：線形＝行ごとの 1 回当たり排出 u（回数を固定したとき）、上流の行結果 by_item、係数値　／　非線形＝周期 c: 群分けのキー（等値比較）と回数 N(T,c) の段差、T: 上流の回数経由の段差、replacement_event_list の有無: 分岐
- 時間の構造：periodic events with period c（周期の値ごとに 1 群）、explicit event list は 1 つの群にまとめる。年への割当はしない
- T への依存：step function via N(T, c)。value = explicit(T) + Σ_c N(T,c)·U_c。U_c は「N(T,c) > 0 の行」の合計なので、c ≥ T の周期は表に現れない
- 周期性：refresh_cycle と service_life の値の集合（非整数可）。資材と設備で同じ数値の周期は同じ群になる
- 条件分岐：回数 0 の行は読み飛ばす；明示一覧を持つ設備 → explicit に足す（service_life があっても周期の群に入れない）；据付・搬入の項の有無は B4-02 と同じ
- 除外と件数：欠落の件数は出さない（n_partial は B4-02 だけ）
- 仕事の増え方：行数に比例 + 異なる周期の数 K の整列（K log K）
- 注記：宣言した依存 B4-02 は関数の中で読まない（実行順のためだけの宣言）。value と B4-02.value の一致は検査しておらず、加算順が違うので浮動小数点の丸めの範囲で差が出る。行と時間の分離 E = Σ_c N(T,c)·U_c を基準計算そのものが持っている。by_year と行の一覧は出さない

<a id="b3-01"></a>

### B3-01　年間修繕（B3）

- 式：資材 i: e0_i = A13-01.by_item[i] + A13-03.by_item[i]、r_i = repair_rate_i、S_i = { yr(n·c_i) : n = 1..N(T, c_i) }。 設備 j: e0_j = X-01.by_item[j]、r_j = repair_rate_j、S_j = { yr(τ) : τ ∈ B4-01.events[j] }。 w_y = min(1, T−(y−1))、Y = ceil(T)。 W_k = Σ_{y=1..Y} w_y·[y ∉ S_k] = T − Σ_{y∈S_k} w_y。 value = Σ_{k ∈ 資材∪設備} [nonneg(r_k)]·e0_k·r_k·W_k。 by_year[y] = Σ_k [nonneg(r_k)]·e0_k·r_k·w_y·[y ∉ S_k]。 n_skipped = Σ_k [¬nonneg(r_k)]。 _mat_lines[i] = [ (fid, a·r_i·W_i) : (fid,a) ∈ A13-01._row_lines[i] ++ A13-03._row_lines[i] ]、_eq_lines[j] = [ (fid, a·r_j·W_j) : (fid,a) ∈ X-01._row_lines[j] ]（r = 0 または e0 = 0 の行、除外した行は空）。
- 宣言された依存：A13-01、A13-03、X-01、B4-01、B4-03　／　実際に読む結果：A13-01、A13-03、X-01、B4-01、B4-03
- 宣言に無い読み取り：なし　／　宣言したが読まない：なし
- 入力：boundary.study_period、materials.repair_rate、materials.refresh_cycle、equipment.repair_rate、（結果経由）A13-01・A13-03・X-01 の by_item / _row_lines、B4-01.events、B4-03.by_item
- 添字の集合：資材の行 i、設備の行 j、評価年 y = 1..Y、行ごとの更新年の集合 S_k
- 出力：value（scalar）、by_year（per-year series）、n_skipped（count）、_mat_lines（per-row list）、_eq_lines（per-row list）
- 演算：sum over rows、sum over years（年重み付き）、product（e0×r×w）、predicate（更新年の除外、修繕率の有効性）、floor/ceil（事象の年、年数）、min/max（年重み）
- 線形性：線形＝e0_k（上流の行結果）、r_k（修繕率）、年重み w_y　／　非線形＝e0×r: 2 入力の積、T: 区分 1 次（傾き Σ e0·r。最終年が更新年に入ると最終年の分が 0 になる）、周期 c_i、L_j と明示一覧: 段差（除外する年の集合 S_k）、修繕率の有効性: 0/1 の切替
- 時間の構造：constant per year（行ごとに e0·r）。ただし更新が属する年は 0。更新年の集合は周期 c_i / L_j の倍数または明示一覧から決まる
- T への依存：sum up to ceil(T) with a prorated last year。行ごとに e0·r·(T − Σ_{y∈S} w_y)。周期が 1 年以上で更新年が端数の最終年でなければ e0·r·(T − N(T,c))
- 周期性：refresh_cycle、service_life（非整数可）。1 年未満の周期では同じ年に複数の更新が入るが、年の集合なので除外は 1 回
- 条件分岐：¬nonneg(r_k)（欠損・負・無限大・NaN）→ 行を足さず n_skipped に 1；r_k = 0 または e0_k = 0 → 何も足さず行の一覧は空（数値への影響はない）；y ∈ S_k（その行の更新が属する年）→ その年の修繕を計上しない（年全体。年の途中の更新でも年全体を除く）；B4-03.by_item[i] = 0 → S_i は空
- 除外と件数：修繕率が無効な行だけを n_skipped に数える。上流で除外された行は e0 = 0.0 として届き、ここでは数えない。別ファイルの X-02 は n_skipped ≠ 0 のとき B3-01 を incomplete_units に入れる
- 仕事の増え方：（資材の行数 + 設備の行数）× Y。閉じた形なら 行数 +（事象数の合計）
- 注記：e0 は資材では A13-01 + A13-03 だけ（A13-04 の上乗せを含まない）、設備では X-01 だけ。修繕率に上限の検査はない。by_year は年重み込みの発生額で Σ_y by_year[y] = value。B3-02 = B3-01 + Σ_k [nonneg(r_k)]·e0_k·r_k·Σ_{y∈S_k} w_y。T が非整数のとき、T が更新時刻を越えると最終年の修繕が 0 に戻るので value は T の単調関数ではない

<a id="b3-02"></a>

### B3-02　期間中の反復修繕（推計）（B3）

- 式：value = Σ_i [nonneg(r_i)]·(A13-01.by_item[i] + A13-03.by_item[i])·r_i·T + Σ_j [nonneg(r_j)]·X-01.by_item[j]·r_j·T。 n_skipped = Σ_i [¬nonneg(r_i)] + Σ_j [¬nonneg(r_j)]。
- 宣言された依存：A13-01、A13-03、X-01　／　実際に読む結果：A13-01、A13-03、X-01
- 宣言に無い読み取り：なし　／　宣言したが読まない：なし
- 入力：boundary.study_period、materials.repair_rate、equipment.repair_rate、（結果経由）A13-01・A13-03・X-01 の by_item
- 添字の集合：資材の行 i、設備の行 j
- 出力：value（scalar）、n_skipped（count）
- 演算：sum over rows、product（e0×r×T）、predicate（修繕率の有効性）
- 線形性：線形＝e0（上流の行結果）、r（修繕率）、T　／　非線形＝e0×r×T: 3 入力の積（三重線形）、修繕率の有効性: 0/1 の切替
- 時間の構造：constant per year
- T への依存：linear（T に比例）
- 周期性：なし
- 条件分岐：¬nonneg(r) → 行を足さず n_skipped に 1
- 除外と件数：修繕率が無効な行を n_skipped に数える。上流で除外された行は e0 = 0.0 として足す（数えない）
- 仕事の増え方：行数に比例
- 注記：段階合計には使わない（B3-01 と択一で、別ファイルの X-02 は B3-01 を使う）。value = T·R、R = Σ [nonneg(r)]·e0·r は T によらない 1 つの数

<a id="b1-01"></a>

### B1-01　物質のCO2e充填量（B1）

- 式：value = Σ_d [nonneg(m0_d) ∧ nonneg(g_d)]·m0_d·g_d、m0_d = charge_mass_kg_d、g_d = gwp_d。 n_skipped = Σ_d [¬(nonneg(m0_d) ∧ nonneg(g_d))]。
- 宣言された依存：なし　／　実際に読む結果：なし
- 宣言に無い読み取り：なし　／　宣言したが読まない：なし
- 入力：refrigerants.charge_mass_kg、refrigerants.gwp
- 添字の集合：機器の行 d（refrigerants）
- 出力：value（scalar）、n_skipped（count）
- 演算：sum over rows、product（質量×GWP）、predicate
- 線形性：線形＝m0_d、g_d　／　非線形＝m0×g: 2 入力の積、有効性: 0/1 の切替
- 時間の構造：none
- T への依存：not at all
- 周期性：なし
- 条件分岐：m0 または g が欠損・負・無限大・NaN → 行を足さず n_skipped に 1
- 除外と件数：無効な機器を n_skipped に数える
- 仕事の増え方：機器の行数に比例
- 注記：排出量ではなく在庫量で、どの段階合計にも入らない。被加数 m0_d·g_d は B1-02・B1-03・B1-04 の機器ごとの結果に共通する振幅である（再帰が m0 に斉次 1 次のため）。漏洩率の有効性はここでは見ない（B1-02 の device_ok より条件が 1 つ少ない）

<a id="b1-02"></a>

### B1-02　使用期間の漏洩（B1）

- 式：機器 d（ok_d = nonneg(m0_d) ∧ nonneg(g_d) ∧ ratio(λ_d) の機器だけ。λ_d = annual_leak_rate_d）: 事象 = sorted([ t ∈ change_years_d : t > 0, t < T(1−ε) ])（change_years_d ≠ None）、そうでなければ { n·service_life_d : n = 1..N(T, service_life_d) }。 k_d(y) = #{ τ : yr(τ) = y }。 再帰: m_d(1) = m0_d。y = 1..Y について leak_d(y) = m_d(y)·λ_d·w_y、 m'_d(y) = m_d(y) − (1−τ_d)·leak_d(y)（τ_d = [top_up_d]）、 m_d(y+1) = m0_d（k_d(y) ≥ 1）、m'_d(y)（k_d(y) = 0）。 by_item[d] = g_d·Σ_{y=1..Y} leak_d(y)。 by_year[y] = Σ_d g_d·leak_d(y)。 value = Σ_d by_item[d]。 _state[d].before_events = k_d(y) ≥ 1 の年 y ごとに (y, m'_d(y)) を 1 個と (y, m0_d) を k_d(y)−1 個。 _state[d].end = m_d(Y+1)。 閉じた形（事象年で区切った年の区間 I ごと）: 区間末の残存量 = m0·Π_{y∈I}(1 − (1−τ)·λ·w_y)。τ = 0 のとき区間の漏洩質量 = m0·(1 − Π_{y∈I}(1 − λ·w_y))、τ = 1 のとき = m0·λ·Σ_{y∈I} w_y。
- 宣言された依存：なし　／　実際に読む結果：なし
- 宣言に無い読み取り：なし　／　宣言したが読まない：なし
- 入力：boundary.study_period、refrigerants.charge_mass_kg、refrigerants.gwp、refrigerants.annual_leak_rate、refrigerants.change_years、refrigerants.service_life、refrigerants.top_up
- 添字の集合：機器の行 d、評価年 y = 1..Y、機器ごとの交換事象 τ
- 出力：value（scalar）、by_item（per-row list）、by_year（per-year series）、n_skipped（count）、_state（per-row list）、_lines（table）
- 演算：sum over rows、recurrence（1 階、リセット付き）、product、floor/ceil（事象の年、事象数）、sort / priority（明示一覧の整列）、predicate（有効性、補充の有無、事象の有無）、min/max（年重み）
- 線形性：線形＝m0_d（再帰は m0 に斉次 1 次）、g_d、補充ありの機器では λ_d と T　／　非線形＝補充なしの機器の λ_d: 多項式（Π(1 − λ w_y)、等比）、service_life、change_years: 段差（リセットの年）、T: 年数 Y、最終年の重み、事象の採否を通じて、top_up: 0/1 の切替、m0×g×λ: 入力の積
- 時間の構造：geometric recurrence（補充なし: 交換後の経過年 a に対し m0·λ·(1−λ)^(a−1)）と constant per year（補充あり: m0·λ）。交換事象（periodic events with period service_life、または explicit event list）で年末にリセット
- T への依存：sum up to ceil(T) with a prorated last year（最終年の漏洩は m·λ·w_Y の比例配分）。補充ありは m0·λ·g·T。補充なしは区間ごとの等比和で、T は最後の区間の長さと事象数 N(T, service_life) を通じて入る
- 周期性：refrigerants.service_life（非整数可）。非整数の事象は yr(τ) の年の年末に寄せる。change_years は非周期
- 条件分岐：¬ok_d → 機器を足さず n_skipped に 1、by_item = 0.0、_state = None；change_years ≠ None → 一覧を使い service_life を無視する；top_up = True → 残存量を減らさない（m' = m）。False → m' = m − leak；k_d(y) ≥ 1 → 年末に残存量を m0 に戻す。同じ年の 2 回目以降の事象の「交換直前の残存量」は m0 になる；service_life が無効 → 事象なし
- 除外と件数：無効な機器を n_skipped に数える。交換時損失率・回収率の有効性はここでは見ない（B1-03・B1-04 が見る）
- 仕事の増え方：機器の行数 × Y + 事象数の合計。閉じた形なら 機器の行数 ×（事象年の数 + 1）
- 注記：漏洩は年初の残存量に対する 1 次の刻み（年内の複利ではない）。最終年の端数も 1 次の比例配分。交換は年末に反映するので、年の途中の事象でもその年の漏洩は交換前の残存量で計算する。質量保存（補充なし、同じ年に事象が 1 つまで）: m0·(事象年の数 + 1) = 漏洩質量の合計 + Σ(交換直前の残存量) + end。Σ_y by_year[y] = value。by_year は年重み込みなので、別ファイルの X-07 は w_y を掛けずに足す

<a id="b1-03"></a>

### B1-03　更新時の漏洩（B1）

- 式：value = Σ_d [st_d ≠ None ∧ ratio(ρ_d)]·ρ_d·g_d·Σ_{(y,m) ∈ before_events_d} m、ρ_d = replacement_loss_rate_d、st_d = B1-02._state[d]。 by_year[y] = Σ_d [st_d ≠ None ∧ ratio(ρ_d)]·ρ_d·g_d·Σ_{(y',m) ∈ before_events_d, y' = y} m。 n_skipped = Σ_d [st_d = None ∨ ¬ratio(ρ_d)]。 閉じた形: 補充ありなら m = m0。補充なしなら、区間の最初の事象で m = m0·Π_{y∈I}(1 − λ·w_y)（I はその事象年で終わる区間）。
- 宣言された依存：B1-02　／　実際に読む結果：B1-02
- 宣言に無い読み取り：なし　／　宣言したが読まない：なし
- 入力：boundary.study_period、refrigerants.replacement_loss_rate、refrigerants.gwp、（結果経由）B1-02._state[d].before_events
- 添字の集合：機器の行 d、機器ごとの交換事象（年 y、交換直前の残存量 m）、評価年 y = 0..Y（by_year）
- 出力：value（scalar）、by_year（per-year series）、n_skipped（count）、_lines（table）
- 演算：sum over rows、sum over events、product（残存量×損失率×GWP）、predicate、散布加算（事象の年の箱）
- 線形性：線形＝ρ_d、g_d、m0_d（残存量は m0 に比例）、交換直前の残存量 m　／　非線形＝補充なしの機器の λ_d: 多項式（等比）、T、service_life、change_years: 段差（事象の数と区間の長さ）、m×ρ×g: 入力の積、有効性: 0/1 の切替
- 時間の構造：periodic events with period service_life、または explicit event list。振幅は交換直前の状態（補充なしでは区間の長さに依存）
- T への依存：step function via N(T, service_life)（事象が 1 つ増えるたびに 1 項増える）。端数の最終年に事象が入ると、その事象の残存量に最終年の重み w_Y が入る
- 周期性：refrigerants.service_life（非整数可）、change_years
- 条件分岐：B1-02 で除外された機器、または ¬ratio(ρ_d) → 機器を足さず n_skipped に 1（事象が 0 件の機器でも数える）；同じ年の 2 回目以降の事象は残存量 m0 で計算する（B1-02 の規則）
- 除外と件数：無効な機器を n_skipped に数える。B1-02 で除外された機器はここでも数える（同じ機器が 2 つの単位で数えられる）
- 仕事の増え方：機器の行数 + 事象数の合計
- 注記：事象の排出なので年重みを掛けない。Σ_y by_year[y] = value。B1-02 の状態（年次の再帰の値）に依存するので、B1-02 を閉じた形にする場合は交換直前の残存量も同じ形で出す必要がある

<a id="b1-04"></a>

### B1-04　廃棄時未回収量（B1/C）

- 式：value = Σ_d [st_d ≠ None ∧ ratio(η_d)]·end_d·(1 − η_d)·g_d、η_d = end_of_life_recovery_rate_d、end_d = B1-02._state[d].end = m_d(Y+1)。 n_skipped = Σ_d [st_d = None ∨ ¬ratio(η_d)]。 閉じた形: end = m0·Π_{y∈I_last}(1 − (1−τ)·λ·w_y)、I_last は最後の事象年の次の年から Y までの区間（年 Y に事象があれば空で end = m0）。
- 宣言された依存：B1-02　／　実際に読む結果：B1-02
- 宣言に無い読み取り：なし　／　宣言したが読まない：なし
- 入力：refrigerants.end_of_life_recovery_rate、refrigerants.gwp、（結果経由）B1-02._state[d].end
- 添字の集合：機器の行 d
- 出力：value（scalar）、n_skipped（count）、_lines（table）
- 演算：sum over rows、product（残存量×(1−回収率)×GWP）、predicate
- 線形性：線形＝(1 − η_d)（η_d にアフィン）、g_d、m0_d、期末の残存量 end_d　／　非線形＝補充なしの機器の λ_d: 多項式（等比）、T、service_life、change_years: 最後の区間の長さを通じた段差と等比、有効性: 0/1 の切替
- 時間の構造：評価期間の終わりに 1 回だけの量。値は最後の交換からの経過年数で決まる
- T への依存：depends on T only through 最後の区間の年数（Y − 最後の事象年）と最終年の重み w_Y。補充ありなら T に依存しない（m0·(1−η)·g）
- 周期性：refrigerants.service_life（非整数可）、change_years（最後の区間の位置を決めるだけ）
- 条件分岐：B1-02 で除外された機器、または ¬ratio(η_d) → 機器を足さず n_skipped に 1（回収率 1 とはみなさない）
- 除外と件数：無効な機器を n_skipped に数える
- 仕事の増え方：機器の行数に比例
- 注記：基準計算では B1 段階に入れる（別ファイルの X-02 の B1 = B1-02 + B1-03 + B1-04）。別ファイルの X-07 は最終年に置く。年 Y に事象があると、年末のリセット後の値 m0 が end になる（評価期間の終わりより前の事象でも同じ）

<a id="b5-01"></a>

### B5-01　大型改修・建替イベント（B5）

- 式：reconstruction_scenario = 'NONE' → value = 0、n_events = 0、computed = True、_multiplier = 0。 そうでなく ¬ratio(φ)（φ = reconstruction_scope_fraction）→ value = 0、n_events = 0、computed = False、_multiplier = 0。 それ以外: base = Σ_{u∈U12} res[u].value、U12 = {A13-01, A13-03, A13-04, X-01, A4-01, A4-02, A5-04, C1-01, C2-01, C3-01, C4-01, X-14}。 N = N(T, C)、C = replacement_cycle。 value = Σ_{n=1..N} φ·base（= N·φ·base）。 by_year[y] = φ·base·#{ n ≤ N : yr(n·C) = y }。 n_events = N。 _multiplier = N·φ。 computed = True。
- 宣言された依存：A13-01、A13-03、A13-04、X-01、A4-01、A4-02、A5-04、C1-01、C2-01、C3-01、C4-01、X-14　／　実際に読む結果：A13-01、A13-03、A13-04、X-01、A4-01、A4-02、A5-04、C1-01、C2-01、C3-01、C4-01、X-14
- 宣言に無い読み取り：なし　／　宣言したが読まない：なし
- 入力：boundary.study_period、boundary.reconstruction_scenario、boundary.reconstruction_scope_fraction、boundary.replacement_cycle、（結果経由）12 単位の value
- 添字の集合：建替事象 n = 1..N(T, C)、合算する上流単位 12 個、評価年 y = 0..Y（by_year）
- 出力：value（scalar）、n_events（count）、by_year（per-year series）、computed（boolean）、_multiplier（scalar）
- 演算：sum（上流 12 単位の値）、product（回数×範囲比×基礎額）、floor/ceil（事象数、事象の年）、predicate（シナリオ、範囲比の有効性）
- 線形性：線形＝base（上流の各 value）、φ　／　非線形＝T と C: 段差（N(T,C)）、φ×base: 2 入力の積、reconstruction_scenario = NONE か否か: 0/1 の切替、範囲比の有効性: 0/1 の切替
- 時間の構造：periodic events with period C（非整数可）。振幅 φ·base は一定
- T への依存：step function via N(T, C)
- 周期性：boundary.replacement_cycle（非整数可）
- 条件分岐：reconstruction_scenario = 'NONE' → 0（computed は真）。この判定が先なので、NONE のとき範囲比は見ない；¬ratio(φ) → 0、computed = False；replacement_cycle が無効 → N = 0 で value = 0、computed は真のまま；REBUILD_IDENTICAL と MAJOR_REFURBISHMENT は同じ式（区別しない）
- 除外と件数：行の件数は数えない。computed = False のとき別ファイルの X-02 が B5-01 を incomplete_units に入れる。上流の欠落は computed に反映しない
- 仕事の増え方：定数（上流 12 個の和）+ 事象数 N
- 注記：base は対象段階の指定（included_lifecycle_stages）によらず 12 単位すべての値を足す。C2-01.value は建物単位の搬出を含む。部材の更新（B4）とは独立で、建替で更新周期を初期化しない。事象の排出なので年重みを掛けない。value = [scenario ≠ NONE]·[ratio(φ)]·N(T,C)·φ·base と 1 つの積で書ける

<a id="x-06"></a>

### X-06　電力排出係数の年次系列の生成（B6）

- 式：wf = (kind = CONSTANT ∧ start ≠ None) ∨ (kind = LINEAR_DECLINE_TO_FLOOR ∧ start, floor, annual_decline ≠ None ∧ annual_decline ≥ 0 ∧ start ≥ floor) ∨ (kind = STEPWISE ∧ steps が空でない ∧ steps[0].from_index = 0 ∧ from_index が厳密に増加)。 k = 0..Y−1 について g_k = start（wf ∧ CONSTANT）、 max(floor, start − annual_decline·k)（wf ∧ LINEAR_DECLINE_TO_FLOOR）、 from_index ≤ k を満たす最後の段の value（wf ∧ STEPWISE）、 table[k]（¬wf）。 by_year = [0.0, g_0, ..., g_{Y−1}]。 source = DESCRIPTOR（wf）、TABLE（¬wf）。 matches_table = ∀k < Y: g_k = table[k] ∨ |g_k − table[k]| ≤ 1e-12·max(|g_k|, |table[k]|)。 同値な書き方: LINEAR_DECLINE_TO_FLOOR は start − annual_decline·min(k, k*)、k* = (start − floor)/annual_decline（annual_decline > 0 のとき）。STEPWISE は Σ_s Δ_s·[k ≥ from_index_s]、Δ_0 = value_0、Δ_s = value_s − value_{s−1}。
- 宣言された依存：なし　／　実際に読む結果：なし
- 宣言に無い読み取り：なし　／　宣言したが読まない：なし
- 入力：boundary.study_period、operation.grid.kind、operation.grid.start、operation.grid.annual_decline、operation.grid.floor、operation.grid.steps[].from_index、operation.grid.steps[].value、operation.grid.table
- 添字の集合：評価年 y = 1..Y（年次表の添字 k = y−1）、段階的シナリオの段 s
- 出力：by_year（per-year series）、matches_table（boolean）、source（enum）
- 演算：table look-up（年次表、段の検索）、min/max（下限での打切り）、predicate（記述子の整合の判定、系列と表の一致判定）、年添字の 1 次式
- 線形性：線形＝CONSTANT: start、STEPWISE: 各段の value、TABLE: 表の値（恒等写像）、LINEAR_DECLINE_TO_FLOOR で下限に達する前の年: start と annual_decline　／　非線形＝LINEAR_DECLINE_TO_FLOOR: max（start − d·k と floor の大きい方。折れ点 k* = (start − floor)/d は比）、STEPWISE: from_index に対する段差、kind と整合の判定: 4 種類の生成規則の切替
- 時間の構造：constant per year | piecewise linear in year（1 次の低下の後に一定）| 段差（区分一定）| 表（任意）
- T への依存：系列の長さ Y = ceil(T) だけが T に依存する。各年の値は T に依存しない
- 周期性：なし（段の位置は折れ点であり周期ではない）
- 条件分岐：kind = CONSTANT で start が欠損 → 年次表を使う；kind = LINEAR_DECLINE_TO_FLOOR で start・floor・annual_decline のどれかが欠損、annual_decline < 0、または start < floor → 年次表を使う；kind = STEPWISE で steps が空・None、最初の段が添字 0 でない、または from_index が厳密増加でない → 年次表を使う；kind = TABLE、またはその他の値 → 年次表を使う
- 除外と件数：除外はない。source と matches_table を報告する。年次表を使った場合 matches_table は自明に真。使用許諾（licence_status）はここでは見ない（B6-01、X-11、別ファイルの A5-01 が見る）
- 仕事の増え方：Y に比例（STEPWISE は Y × 段の数）
- 注記：by_year[0] は 0.0 の埋め草で、工事期間の値（construction_value）ではない。値の符号・有限性は検査しない。実行の入口（check_period）が grid.table の長さ ≥ ceil(T) を要求する。B6-01 と X-11 が読む

<a id="b6-04"></a>

### B6-04　オンサイト発電の扱い（B6）

- 式：prof(p, k) = p.base（p.kind = CONSTANT ∧ base ≠ None）、 p.base + p.slope·k（p.kind = LINEAR_TREND ∧ base, slope ≠ None）、 p.table[k]（それ以外）。 au(unit) = '<u>/year' の <u>、それ以外の形は None。 eu = au(electricity.unit)、gu = au(onsite_generation.unit)、xu = au(onsite_export.unit)。 cg = 換算倍率(gu→eu)、cx = 換算倍率(xu→eu)（同じ単位なら 1、そうでなければ共通の換算表を 1 回引く。連鎖なし）。 computed = [eu ≠ None ∧ cg ≠ None ∧ cx ≠ None]。 computed のとき net_k = max(0, c_k − (g_k·cg − x_k·cx))、c_k = prof(electricity, k)、g_k = prof(onsite_generation, k)、x_k = prof(onsite_export, k)、k = 0..Y−1、by_year = [0.0, net_0, ..., net_{Y−1}]。 そうでなければ by_year = 0.0 が Y+1 個。 descriptors_match_tables = 3 系列それぞれで prof(p, k) と p.table[k] が k < Y で相対 1e-12 以内に一致。
- 宣言された依存：なし　／　実際に読む結果：なし
- 宣言に無い読み取り：なし　／　宣言したが読まない：なし
- 入力：boundary.study_period、operation.electricity.kind、operation.electricity.unit、operation.electricity.base、operation.electricity.slope、operation.electricity.table、operation.onsite_generation.kind、operation.onsite_generation.unit、operation.onsite_generation.base、operation.onsite_generation.slope、operation.onsite_generation.table、operation.onsite_export.kind、operation.onsite_export.unit、operation.onsite_export.base、operation.onsite_export.slope、operation.onsite_export.table、unit_conversions
- 添字の集合：評価年 y = 1..Y（添字 k = y−1）、年次量 3 系列（消費、発電、売電）
- 出力：by_year（per-year series）、computed（boolean）、descriptors_match_tables（boolean）
- 演算：年添字の 1 次式（記述子）、table look-up（年次表、単位換算）、min/max（0 での打切り）、predicate（単位の形、換算の有無、系列と表の一致）、年ごとの加減
- 線形性：線形＝打切りが働かない年: 消費量 c_k、発電量 g_k、売電量 x_k（符号 +、−、+）、換算倍率 cg、cx（系列を固定したとき）　／　非線形＝max(0, ·): 折れ（発電の自家消費が消費を上回る年は 0）、g×cg、x×cx: 2 入力の積、単位の換算可否: 全体の 0/1 の切替、profile.kind: 生成規則の切替
- 時間の構造：3 系列がすべて CONSTANT / LINEAR_TREND なら max(0, α + β·k)（piecewise linear in year、折れ点は高々 1 つ）。TABLE を含めば任意
- T への依存：系列の長さ Y = ceil(T) だけが T に依存する
- 周期性：なし
- 条件分岐：electricity.unit が '<u>/year' の形でない、または発電・売電の単位を消費の単位へ換算できない → 全年 0、computed = False；c_k − g_k·cg + x_k·cx < 0 → その年の買電量は 0；profile の kind と base / slope の有無 → 記述子か年次表かの選択
- 除外と件数：computed と descriptors_match_tables を報告する。件数は数えない。年次量の符号、売電 ≤ 発電 の関係は検査しない
- 仕事の増え方：Y に比例
- 注記：by_year は年当たりの量（年重みを掛けない）。B6-01 が読む。LINEAR_TREND の値が負になっても打ち切らない（最後の max だけが働く）。記述子と年次表が食い違っても記述子を使い、食い違いは真偽値で報告するだけ

<a id="b6-01"></a>

### B6-01　年間買電排出（B6）

- 式：gu = grid.unit が 'kgCO2e/<u>' の形のときの <u>、それ以外は None。 conv = 換算倍率(au(electricity.unit) → gu)。 ok = [grid.licence_status = PERMITTED_PUBLIC] ∧ B6-04.computed ∧ [conv ≠ None]。 by_year[y] = ok ? net_y·conv·g_y : 0.0（y = 1..Y、net_y = B6-04.by_year[y]、g_y = X-06.by_year[y]）、by_year[0] = 0.0。 computed = ok。
- 宣言された依存：B6-04、X-06　／　実際に読む結果：B6-04、X-06
- 宣言に無い読み取り：なし　／　宣言したが読まない：なし
- 入力：operation.electricity.unit、operation.grid.unit、operation.grid.licence_status、unit_conversions、（結果経由）B6-04.by_year、B6-04.computed、X-06.by_year
- 添字の集合：評価年 y = 1..Y
- 出力：by_year（per-year series）、computed（boolean）
- 演算：product（年ごとの 2 系列の積×換算倍率）、table look-up（単位換算）、predicate（使用許諾、上流の算出可否、換算の有無）
- 線形性：線形＝買電量の系列 net_y、電力排出係数の系列 g_y、換算倍率 conv　／　非線形＝net×g: 2 系列の年ごとの積（双線形）、ok: 全体の 0/1 の切替
- 時間の構造：2 つの年次系列の年ごとの積。両方が k の 1 次式なら k の 2 次式、打切り・段があれば区分多項式
- T への依存：系列の長さ Y = ceil(T) だけが T に依存する
- 周期性：なし
- 条件分岐：使用許諾が PERMITTED_PUBLIC でない、B6-04 が未算出、または換算できない → 全年 0.0、computed = False
- 除外と件数：computed を報告する。別ファイルの X-02 は computed = False のとき B6-01 を incomplete_units に入れる
- 仕事の増え方：Y に比例
- 注記：by_year は年当たりの率であり、年重み w_y は B6-03、B2-01、別ファイルの X-07 が掛ける。買電は係数 ID を持たないので、ガス別集計では擬似 ID の GRID（CO2e のまま）として扱われる

<a id="b6-02"></a>

### B6-02　燃料の年間排出（B6）

- 式：燃料 f: hit_f = lookup(factor_id_f, 'B6', au(profile_f.unit)) が使用可（記録があり、licence_status = PERMITTED_PUBLIC、stages = ['B6']、単位換算が 1 回で引ける）。κ_f = 換算倍率、F_f = 係数値。 by_year[y] = Σ_f [hit_f]·prof(profile_f, y−1)·κ_f·F_f（y = 1..Y）、by_year[0] = 0。 n_skipped = Σ_f [¬hit_f]。 descriptors_match_tables = 3 系列すべてで prof と年次表が一致（使えない燃料も判定に入る）。 _lines = [ (factor_id_f, Σ_{y=1..Y} w_y·prof(profile_f, y−1)·κ_f) : hit_f ]。
- 宣言された依存：なし　／　実際に読む結果：なし
- 宣言に無い読み取り：なし　／　宣言したが読まない：なし
- 入力：boundary.study_period、operation.gas.kind、operation.gas.unit、operation.gas.base、operation.gas.slope、operation.gas.table、operation.oil.kind、operation.oil.unit、operation.oil.base、operation.oil.slope、operation.oil.table、operation.district_heat.kind、operation.district_heat.unit、operation.district_heat.base、operation.district_heat.slope、operation.district_heat.table、operation.gas_factor_id、operation.oil_factor_id、operation.district_heat_factor_id、factors.value、factors.unit、factors.stages、factors.licence_status、unit_conversions
- 添字の集合：燃料 f ∈ (gas, oil, district_heat)、評価年 y = 1..Y
- 出力：by_year（per-year series）、n_skipped（count）、descriptors_match_tables（boolean）、_lines（table）
- 演算：sum over rows（燃料 3 種）、product（年次量×換算倍率×係数）、table look-up（係数、単位換算、年次表）、predicate（係数の使用可否、系列と表の一致）、年添字の 1 次式（記述子）
- 線形性：線形＝年次量（base、slope、表の値）、係数値 F_f、換算倍率 κ_f　／　非線形＝年次量×係数: 2 入力の積、係数の使用可否: 0/1 の切替
- 時間の構造：constant per year | linear in year | 表（燃料ごと）。和は k の 1 次式 + 表の成分
- T への依存：系列の長さ Y = ceil(T) だけが T に依存する（_lines の活動量は年重み付きの和なので T に依存する）
- 周期性：なし
- 条件分岐：係数 ID が None、記録がない、使用許諾がない、対象段階が ['B6'] でない、単位が '<u>/year' の形でない、または換算できない → その燃料を足さず n_skipped に 1
- 除外と件数：使えない燃料を n_skipped に数える。別ファイルの X-02 は n_skipped ≠ 0 のとき B6-02 を incomplete_units に入れる
- 仕事の増え方：3 × Y
- 注記：by_year は年当たりの率、_lines は年重み込みの量で、両者の時間の扱いが違う。行固有の換算は使わない。年次量の符号は検査しない。3 系列がすべて記述子なら by_year[y] = A0 + A1·(y−1)、A0 = Σ_f base_f·κ_f·F_f、A1 = Σ_f slope_f·κ_f·F_f と、年に展開する前に集約できる

<a id="b6-03"></a>

### B6-03　評価年数の積算（B6）

- 式：value = Σ_{y=1..Y} w_y·(elec_y + fuel_y)、elec_y = B6-01.by_year[y]、fuel_y = B6-02.by_year[y]、w_y = min(1, T−(y−1))、Y = ceil(T)。 _lines = [(GRID, Σ_{y=1..Y} w_y·elec_y)] ++ B6-02._lines。 同値な書き方: S(n) = Σ_{y≤n} (elec_y + fuel_y) とすると value = S(Y−1) + (T−(Y−1))·(elec_Y + fuel_Y)、すなわち累積系列 S を T で 1 次補間した値。
- 宣言された依存：B6-01、B6-02　／　実際に読む結果：B6-01、B6-02
- 宣言に無い読み取り：なし　／　宣言したが読まない：なし
- 入力：boundary.study_period、（結果経由）B6-01.by_year、B6-02.by_year、B6-02._lines
- 添字の集合：評価年 y = 1..Y
- 出力：value（scalar）、_lines（table）
- 演算：sum over years（年重み付き）、min/max（年重み）、floor/ceil（年数 Y）
- 線形性：線形＝買電排出の系列、燃料排出の系列、年重み w_y　／　非線形＝T: 区分 1 次（整数年の間は傾き elec_Y + fuel_Y の 1 次式、連続）
- 時間の構造：年次系列の年重み付きの和
- T への依存：sum up to ceil(T) with a prorated last year
- 周期性：なし
- 条件分岐：なし（上流が未算出なら 0.0 の系列を足す）
- 除外と件数：件数もフラグも出さない。欠落の判定は別ファイルの X-02 が B6-01・B6-02 を見て行う
- 仕事の増え方：Y に比例
- 注記：別ファイルの X-02 の B6 段階は B6-03 − B2-01（B2 が対象外なら B6-03）。GRID の行の値は B2-01 の被乗数と同じ数（Σ_y w_y·elec_y）

<a id="b2-01"></a>

### B2-01　施設管理に帰属させる運用負荷（B2）

- 式：s = facility_management_ratio。 ratio(s)（s ≠ None ∧ 0 ≤ s ≤ 1）のとき value = s·Σ_{y=1..Y} w_y·B6-01.by_year[y]、computed = True。 そうでなければ value = 0.0、computed = False。
- 宣言された依存：B6-01　／　実際に読む結果：B6-01
- 宣言に無い読み取り：なし　／　宣言したが読まない：なし
- 入力：boundary.study_period、operation.facility_management_ratio、（結果経由）B6-01.by_year
- 添字の集合：評価年 y = 1..Y
- 出力：value（scalar）、computed（boolean）
- 演算：sum over years（年重み付き）、product（比率×合計）、predicate（比率の有効性）
- 線形性：線形＝比率 s、買電排出の系列　／　非線形＝s×Σ w·elec: 2 入力の積、比率の有効性: 0/1 の切替、T: 区分 1 次
- 時間の構造：年次系列の年重み付きの和に 1 つの比率を掛ける
- T への依存：sum up to ceil(T) with a prorated last year
- 周期性：なし
- 条件分岐：¬ratio(s) → 0.0、computed = False
- 除外と件数：computed を報告する。B6-01.computed は見ない（B6-01 が未算出なら 0.0 で computed は真）
- 仕事の増え方：Y に比例
- 注記：B6 から同額を引く処理はこの関数にはなく、別ファイルの X-02（B6 = B6-03 − B2-01、B2 が対象外なら引かない）にある。B2 + B6 の合計は s によらない。買電の年重み付き合計 G = Σ_y w_y·elec_y を (s, 1−s) で 2 段階に分けるだけの式

<a id="x-11"></a>

### X-11　床面積当たり統計値による運用エネルギーの推定（B6）

- 式：A = gross_floor_area、q = electricity_per_m2_per_year、conv = 換算倍率('kWh' → gu)、gu は grid.unit が 'kgCO2e/<u>' の形のときの <u>。 positive(A) ∧ nonneg(q) ∧ conv ≠ None ∧ grid.licence_status = PERMITTED_PUBLIC のとき value = A·q·conv·Σ_{y=1..Y} w_y·g_y（g_y = X-06.by_year[y]）、そうでなければ value = None。
- 宣言された依存：X-06　／　実際に読む結果：X-06
- 宣言に無い読み取り：なし　／　宣言したが読まない：なし
- 入力：boundary.study_period、project.gross_floor_area、operation.electricity_per_m2_per_year、operation.grid.unit、operation.grid.licence_status、unit_conversions、（結果経由）X-06.by_year
- 添字の集合：評価年 y = 1..Y
- 出力：value（scalar）
- 演算：sum over years（年重み付き）、product（面積×原単位×換算倍率×累積係数）、table look-up（単位換算）、predicate
- 線形性：線形＝面積 A、原単位 q、換算倍率 conv、電力排出係数の系列 g_y　／　非線形＝A×q×conv×Σ w·g: 入力の積（多重線形）、有効性: 0/1 の切替（結果は None）、T: 区分 1 次
- 時間の構造：電力排出係数の年次系列の年重み付きの和に、年によらない量を掛ける
- T への依存：sum up to ceil(T) with a prorated last year
- 周期性：なし
- 条件分岐：面積が正でない・欠損、原単位が負・欠損、換算できない、または使用許諾がない → value = None（0 にしない）
- 除外と件数：件数もフラグも出さない。未算出は value = None で表す
- 仕事の増え方：Y に比例
- 注記：段階合計に使わない推定値。買電量（B6-04）もオンサイト発電も使わない。原単位の単位は 'kWh' と固定して換算する。Σ_y w_y·g_y は年次量が一定のときの B6-01 の年重み付き合計と同じ形（消費量 = A·q の一定系列）

<a id="b7-01"></a>

### B7-01　上水利用排出（B7）

- 式：p = water_waste.water（上水使用量）。 hit = lookup(water_waste.water_factor_id, 'B7', au(p.unit)) が使用可（記録があり、licence_status = PERMITTED_PUBLIC、stages = ['B7']、単位換算が 1 回で引ける）。κ = 換算倍率、F = 係数値。 by_year[y] = [hit]·prof(p, y−1)·κ·F（y = 1..Y）、by_year[0] = 0。 n_skipped = [¬hit]。 descriptors_match_tables = prof(p, k) と p.table[k] が k < Y で相対 1e-12 以内に一致。 _lines = [ (係数 ID, Σ_{y=1..Y} w_y·prof(p, y−1)·κ) ]（hit のとき）。 prof(p, k) = base（CONSTANT）、base + slope·k（LINEAR_TREND）、table[k]（それ以外）。
- 宣言された依存：なし　／　実際に読む結果：なし
- 宣言に無い読み取り：なし　／　宣言したが読まない：なし
- 入力：boundary.study_period、water_waste.water.kind、water_waste.water.unit、water_waste.water.base、water_waste.water.slope、water_waste.water.table、water_waste.water_factor_id、factors.value、factors.unit、factors.stages、factors.licence_status、unit_conversions
- 添字の集合：評価年 y = 1..Y
- 出力：by_year（per-year series）、n_skipped（count）、descriptors_match_tables（boolean）、_lines（table）
- 演算：product（年次量×換算倍率×係数）、table look-up（係数、単位換算、年次表）、predicate（係数の使用可否、系列と表の一致）、年添字の 1 次式（記述子）
- 線形性：線形＝年次量（base、slope、表の値）、係数値 F、換算倍率 κ　／　非線形＝年次量×係数: 2 入力の積、係数の使用可否: 0/1 の切替
- 時間の構造：constant per year | linear in year | 表
- T への依存：系列の長さ Y = ceil(T) だけが T に依存する（_lines の活動量は年重み付きの和なので T に依存する）
- 周期性：なし
- 条件分岐：係数 ID が None、記録がない、使用許諾がない、対象段階が ['B7'] でない、単位が '<u>/year' の形でない、または換算できない → 全年 0、n_skipped = 1
- 除外と件数：使えないとき n_skipped = 1。別ファイルの X-02 は n_skipped ≠ 0 のときこの単位を incomplete_units に入れる
- 仕事の増え方：Y に比例
- 注記：B6-02 と同じ補助関数（燃料 3 種の代わりに 1 系列）。by_year は年当たりの率で、年重みは B7-04 と別ファイルの X-07 が掛ける。年次量の符号は検査しない

<a id="b7-02"></a>

### B7-02　下水処理排出（B7）

- 式：p = water_waste.sewage（下水量）。 hit = lookup(water_waste.sewage_factor_id, 'B7', au(p.unit)) が使用可（記録があり、licence_status = PERMITTED_PUBLIC、stages = ['B7']、単位換算が 1 回で引ける）。κ = 換算倍率、F = 係数値。 by_year[y] = [hit]·prof(p, y−1)·κ·F（y = 1..Y）、by_year[0] = 0。 n_skipped = [¬hit]。 descriptors_match_tables = prof(p, k) と p.table[k] が k < Y で相対 1e-12 以内に一致。 _lines = [ (係数 ID, Σ_{y=1..Y} w_y·prof(p, y−1)·κ) ]（hit のとき）。 prof(p, k) = base（CONSTANT）、base + slope·k（LINEAR_TREND）、table[k]（それ以外）。
- 宣言された依存：なし　／　実際に読む結果：なし
- 宣言に無い読み取り：なし　／　宣言したが読まない：なし
- 入力：boundary.study_period、water_waste.sewage.kind、water_waste.sewage.unit、water_waste.sewage.base、water_waste.sewage.slope、water_waste.sewage.table、water_waste.sewage_factor_id、factors.value、factors.unit、factors.stages、factors.licence_status、unit_conversions
- 添字の集合：評価年 y = 1..Y
- 出力：by_year（per-year series）、n_skipped（count）、descriptors_match_tables（boolean）、_lines（table）
- 演算：product（年次量×換算倍率×係数）、table look-up（係数、単位換算、年次表）、predicate（係数の使用可否、系列と表の一致）、年添字の 1 次式（記述子）
- 線形性：線形＝年次量（base、slope、表の値）、係数値 F、換算倍率 κ　／　非線形＝年次量×係数: 2 入力の積、係数の使用可否: 0/1 の切替
- 時間の構造：constant per year | linear in year | 表
- T への依存：系列の長さ Y = ceil(T) だけが T に依存する（_lines の活動量は年重み付きの和なので T に依存する）
- 周期性：なし
- 条件分岐：係数 ID が None、記録がない、使用許諾がない、対象段階が ['B7'] でない、単位が '<u>/year' の形でない、または換算できない → 全年 0、n_skipped = 1
- 除外と件数：使えないとき n_skipped = 1。別ファイルの X-02 は n_skipped ≠ 0 のときこの単位を incomplete_units に入れる
- 仕事の増え方：Y に比例
- 注記：B6-02 と同じ補助関数（燃料 3 種の代わりに 1 系列）。by_year は年当たりの率で、年重みは B7-04 と別ファイルの X-07 が掛ける。年次量の符号は検査しない

<a id="b7-03"></a>

### B7-03　一般廃棄物排出（B7）

- 式：p = water_waste.municipal_waste（一般廃棄物量）。 hit = lookup(water_waste.waste_factor_id, 'B7', au(p.unit)) が使用可（記録があり、licence_status = PERMITTED_PUBLIC、stages = ['B7']、単位換算が 1 回で引ける）。κ = 換算倍率、F = 係数値。 by_year[y] = [hit]·prof(p, y−1)·κ·F（y = 1..Y）、by_year[0] = 0。 n_skipped = [¬hit]。 descriptors_match_tables = prof(p, k) と p.table[k] が k < Y で相対 1e-12 以内に一致。 _lines = [ (係数 ID, Σ_{y=1..Y} w_y·prof(p, y−1)·κ) ]（hit のとき）。 prof(p, k) = base（CONSTANT）、base + slope·k（LINEAR_TREND）、table[k]（それ以外）。
- 宣言された依存：なし　／　実際に読む結果：なし
- 宣言に無い読み取り：なし　／　宣言したが読まない：なし
- 入力：boundary.study_period、water_waste.municipal_waste.kind、water_waste.municipal_waste.unit、water_waste.municipal_waste.base、water_waste.municipal_waste.slope、water_waste.municipal_waste.table、water_waste.waste_factor_id、factors.value、factors.unit、factors.stages、factors.licence_status、unit_conversions
- 添字の集合：評価年 y = 1..Y
- 出力：by_year（per-year series）、n_skipped（count）、descriptors_match_tables（boolean）、_lines（table）
- 演算：product（年次量×換算倍率×係数）、table look-up（係数、単位換算、年次表）、predicate（係数の使用可否、系列と表の一致）、年添字の 1 次式（記述子）
- 線形性：線形＝年次量（base、slope、表の値）、係数値 F、換算倍率 κ　／　非線形＝年次量×係数: 2 入力の積、係数の使用可否: 0/1 の切替
- 時間の構造：constant per year | linear in year | 表
- T への依存：系列の長さ Y = ceil(T) だけが T に依存する（_lines の活動量は年重み付きの和なので T に依存する）
- 周期性：なし
- 条件分岐：係数 ID が None、記録がない、使用許諾がない、対象段階が ['B7'] でない、単位が '<u>/year' の形でない、または換算できない → 全年 0、n_skipped = 1
- 除外と件数：使えないとき n_skipped = 1。別ファイルの X-02 は n_skipped ≠ 0 のときこの単位を incomplete_units に入れる
- 仕事の増え方：Y に比例
- 注記：B6-02 と同じ補助関数（燃料 3 種の代わりに 1 系列）。by_year は年当たりの率で、年重みは B7-04 と別ファイルの X-07 が掛ける。年次量の符号は検査しない

<a id="b7-04"></a>

### B7-04　評価期間積算（B7）

- 式：value = Σ_{y=1..Y} w_y·(B7-01.by_year[y] + B7-02.by_year[y] + B7-03.by_year[y])、w_y = min(1, T−(y−1))、Y = ceil(T)。 _lines = B7-01._lines ++ B7-02._lines ++ B7-03._lines。 系列が記述子のとき: Σ_y w_y·(base + slope·(y−1)) = base·T + slope·μ1(T)、μ1(T) = (Y−1)(Y−2)/2 + (T−(Y−1))·(Y−1)（T が整数なら T(T−1)/2）。
- 宣言された依存：B7-01、B7-02、B7-03　／　実際に読む結果：B7-01、B7-02、B7-03
- 宣言に無い読み取り：なし　／　宣言したが読まない：なし
- 入力：boundary.study_period、（結果経由）B7-01・B7-02・B7-03 の by_year と _lines
- 添字の集合：評価年 y = 1..Y、系列 3 本
- 出力：value（scalar）、_lines（table）
- 演算：sum over years（年重み付き）、min/max（年重み）、floor/ceil（年数 Y）
- 線形性：線形＝3 つの年次系列、年重み w_y　／　非線形＝T: 区分 1 次（系列が一定なら T に比例、1 次の系列なら T の区分 2 次）
- 時間の構造：年次系列の年重み付きの和
- T への依存：sum up to ceil(T) with a prorated last year
- 周期性：なし
- 条件分岐：なし
- 除外と件数：件数もフラグも出さない。欠落の判定は別ファイルの X-02 が B7-01〜B7-03 を見て行う
- 仕事の増え方：Y に比例
- 注記：B6-03 と同じ形（系列の本数と GRID の行の有無だけが違う）。別ファイルの X-02 の B7 段階の値

## 扱えなかったこと

- 上流の単位（A13-01、A13-03、A13-04、A13-05、A4-01、A4-02、A5-04、C1-01、C2-01、C3-01、C4-01、X-01、X-14）の式そのもの。担当外であり、結果のキー（by_item、_row_lines、_skipped_rows、_partial_rows、q_ord、value）の形と、study_period を読まないことを確かめるために、該当する関数だけを読んだ
- 下流の単位での本ファイルの結果の使われ方。別ファイルの X-02、stage_lines、X-07、X-10 の該当箇所だけを読んだ。SUM・QA の単位は読んでいない
- 閉じた形（N の式、μ_1、冷媒の区間の式、準多項式の構造）の数値検証。基準計算を実行しない規則のため、すべて手計算による導出である
- 浮動小数点の加算順の違いによる差の大きさ
- 合成データの分布（周期が整数である割合、同じ周期を持つ行の数、TABLE 種別の頻度、補充ありの機器の割合、非整数の T の有無）。生成器を読んでいないので、周期別の集約やスプライン表現でどれだけ項が減るかは分からない
- synth/model.py の 750 行目以降（走査・入力網羅の検査の補助関数）
- by_year を使う下流での丸め・表示の規則、結果比較の許容差
