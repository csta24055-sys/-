# -*- coding: utf-8 -*-
"""data/claims.csv の手で選んだ行：式（F）・本基盤で拾った定理（T-57 以降）・主張（C）。tools/build_claims.py が読む。

各行：(id, kind, orig_id, statement, latex, class, scope, base_ref, sources, code, checked_by, lineage, note)
  sources: [(path, commit, section), ...]   path は whole-life-carbon-jcat-study/ からの相対
  code:    [(path, function), ...]          同上
"""

R = "10_TRANSFORM_STUDY/research_code/"
U = "10_TRANSFORM_STUDY/11_UNIFIED_SYSTEM/"
C17 = "17_WHOLE_BUILDING_TIME_THEORY/code/"
C18 = "18_DYNAMIC_LCA_EXTENSION/code/"
C20 = "20_LARGE_RANDOM_VERIFICATION/code/"
B = "WLC_THEORY_RESEARCH_BASE/"
BASEC = "（本基盤）"

S_SMSP = (U + "SPEC_MSP.md", "ac291dd")
S_SKN = (U + "SPEC_KNOTS.md", "ac291dd")
S_DER = (U + "DERIVATIONS.md", "b93201e")
S_LIM = (U + "LIMITS.md", "b93201e")
S_VER = (U + "VERIFICATION.md", "b93201e")
S_U70 = (U + "UNITS_70.md", "ac291dd")
S_E03 = ("14_EQUATION_DISCLOSURE/03_節点スペクトル全方程式.md", "4c38df6")
S_E04 = ("14_EQUATION_DISCLOSURE/04_マスク付き積和全方程式.md", "4c38df6")
S_E07 = ("14_EQUATION_DISCLOSURE/07_建物全体の統一方程式_完全版.md", "4c38df6")
S_E14 = ("14_EQUATION_DISCLOSURE/README.md", "4c38df6")
S_T01 = ("17_WHOLE_BUILDING_TIME_THEORY/01_理想方程式.md", "6f99266")
S_T02 = ("17_WHOLE_BUILDING_TIME_THEORY/02_係数表.md", "6f99266")
S_T03 = ("17_WHOLE_BUILDING_TIME_THEORY/03_時間特性の定理と証明.md", "46781f2")
S_T04 = ("17_WHOLE_BUILDING_TIME_THEORY/04_解析手法の比較.md", "46781f2")
S_T05 = ("17_WHOLE_BUILDING_TIME_THEORY/05_最良表現.md", "46781f2")
S_T07 = ("17_WHOLE_BUILDING_TIME_THEORY/07_検証の結果.md", "46781f2")
S_18_02 = ("18_DYNAMIC_LCA_EXTENSION/02_工程と時間変数.md", "09e0765")
S_18_03 = ("18_DYNAMIC_LCA_EXTENSION/03_工程間の関係.md", "09e0765")
S_18_04 = ("18_DYNAMIC_LCA_EXTENSION/04_再構成と整合.md", "09e0765")
S_18_05 = ("18_DYNAMIC_LCA_EXTENSION/05_時間配分の仮定と非一意性.md", "46781f2")
S_18_06 = ("18_DYNAMIC_LCA_EXTENSION/06_動的特性化.md", "09e0765")
S_18_07 = ("18_DYNAMIC_LCA_EXTENSION/07_検証の結果.md", "3b15dca")
S_20_02 = ("20_LARGE_RANDOM_VERIFICATION/02_結果.md", "3a30103")
S_20R = ("20_LARGE_RANDOM_VERIFICATION/README.md", "e207eff")
S_21 = ("21_UNIFIED_THEORY_REPORT/README.md", "3a30103")
S_EXP = ("10_TRANSFORM_STUDY/03_ROUTES/experiments/README.md", "21a4a54")
S_IMPL = ("10_TRANSFORM_STUDY/03_ROUTES/TC-B-01/IMPLEMENTATION_NOTES.md", "21a4a54")
S_DEC = ("10_TRANSFORM_STUDY/07_DECISIONS/README.md", "bd45157")
S_T10 = ("10_TRANSFORM_STUDY/README.md", "bd45157")
S_09R = ("09_APPROX_STUDY/README.md", "b2b8a6e")
S_09L = ("09_APPROX_STUDY/01_LEDGER/README.md", "43ba5d7")
S_15R = ("15_JCAT_CONVERSION/README.md", "fdfbc16")
S_15_04 = ("15_JCAT_CONVERSION/04_検証の方法と結果.md", "7df1fdd")
S_16_03 = ("16_UNRESOLVED8_EXACT_APPROX/03_不可能性の証明.md", "6d867ea")
S_16R = ("16_UNRESOLVED8_EXACT_APPROX/README.md", "6d867ea")
S_19R = ("19_JCAT_REMAINING12/README.md", "602cb38")
S_19_01 = ("19_JCAT_REMAINING12/01_依存関係と必要性.md", "3a30103")
S_REC = ("22_WLC_COMPLETE_TEXTBOOK/record/research_record.md", "b28532c")
S_ARC = ("research_archive/real_equation_checkpoint/INDEX.md", "2ed3a78")
S_COMP = ("01_COMPLIANCE/README.md", "79d1ff8")


def s(src, sec):
    return (src[0], src[1], sec)


def base(fn, sec=""):
    return (B + fn, BASEC, sec)


ROWS = []


def add(*row):
    ROWS.append(row)


# ---------------------------------------------------------------- F: 式（定義・再利用する式）
add("F-01", "formula", "SPEC_MSP §1", "マスク付き積和の 1 つの形（積和ステップ sp）：表の各行で項ごとに因子の積をとって足し、まとめ先 g ごとに集める",
    r"\mathrm{out}[g]=\sum_{x\in\mathcal{T}}\sum_{t\in\mathcal{E}}\prod_k\varphi_{t,k}(x)",
    "定義", "有限の表 𝒯・有限の項の列 ℰ。因子は列の値・0/1 の述語・1 列の関数（1/a、1−a、1/(1−a)、a/(1−a)）の 3 種類だけ",
    "03 §4.2；04 §1・§2.2", [s(S_SMSP, "§1"), s(S_E04, "§1")], [(R + "tstudy/msp.py", "Engine.run_sp・Engine.core")],
    "[F] 本基盤の読み取り専用の試験（tools/probe_msp_semantics.py → data/msp_semantics_probe.json）", "A", "エンジンは次元を持たず、評価単位の ID で分岐しない（msp.py のモジュール文書）")
add("F-02", "formula", "04 §2.3", "項・行・群の値と欠損の規則：述語が 1 つでも 0 なら項は厳密に 0（マスク）、述語がすべて 1 で値が欠けると欠損 ⊥、欠損の行を含む群は ⊥。欠損を 0 とみなさない",
    r"\tau_t(x)=\begin{cases}0 & \exists P\in\mathcal{P}_t:[P](x)=0\\ \bot & \text{そうでなく値が欠損または有限でない}\\ \prod_{v\in\mathcal{V}_t}v(x) & \text{それ以外}\end{cases}",
    "定義", "msp.py の Engine.run_sp の処理を式に書き直したもの（本基盤でコードを読んで書いた）。by で参照が欠損の行が 0 でない値を持つと全群が ⊥",
    "04 §2.3・§2.5；03 §4.4", [s(S_SMSP, "§2"), s(S_E04, "§2"), base("04_マスク積和の理論.md", "§2.3")], [(R + "tstudy/msp.py", "Engine.run_sp"), (B + "tools/probe_msp_semantics.py", "（試験）")],
    "[F] 架空の小さな表で、マスクされた行が厳密に 0・欠損の伝播・2,000 行の if/elif のビット一致・積の中の文字列の拒否を確認（04 §2.5）", "BASE", "写した文字列・参照の列のマスクで外れた行の値が欠損でなく 0 になる観察は未確認（04 §2.5、§9 の 9）")
add("F-03", "formula", "14/04 §1", "検索ステップ match：キーが等しい最初の行（行の位置についての最小）への参照。一致がなければ ⊥。順序を使う唯一の演算",
    r"\mathrm{ref}[x]=\min\{\,y\in\mathcal{U}_{\mathrm{into}}:\ \mathrm{on}(y)=\mathrm{keys}(x)\,\}",
    "定義", "検索先の表 𝒰_into（本基盤で 𝒰 と区別する添字を追加）。キーの等号は倍精度・文字列符号の完全一致",
    "03 §4.3；04 §2.4", [s(S_E04, "§1"), s(S_SMSP, "§1")], [(R + "tstudy/msp.py", "Engine.run_match")],
    "[F] 試験で最初の一致を返すことを確認（04 §2.5）", "A", "match を第 2 の演算に数えるかは未決（OQ-22、DEC 未決の事項）")
add("F-04", "formula", "D-03・SPEC_KNOTS §3", "時間の規則：年重み、事象の規則（ε=10⁻⁹）、事象の年セル、周期の事象の時刻",
    r"w_k(T)=\operatorname{clip}(T-k,0,1),\quad \theta_\varepsilon(T;g)=[\,g<T(1-\varepsilon)\,],\quad k_\tau=\max(1,\lceil\tau(1-\varepsilon)\rceil)-1,\quad \tau_n=nc",
    "定義", "T∈(0,H]。浮動小数では τ_n=fl(nc)、事象は T≥sw(τ) で数える", "03 §3.2；05 §2.1", [s(S_DER, "§0.3"), s(S_SKN, "§3"), s(S_T01, "§2")],
    [(R + "tstudy/rampstep.py", "h・periodic_times・event_year"), ("09_APPROX_STUDY/research_code/refcalc/base.py", "year_weights・EPS（基準計算の規則）")],
    "[P] 年重みの和の書き換え（{T:10.D-03-1}）；[F] EXP-01・EXP-02", "A", "")
add("F-05", "formula", "17/03 L-2", "浮動小数の切り替え点 sw(g)：規則 g<fl(T·fl(1−ε)) が真になる最小の浮動小数 T（d=fl(1−ε)、u=2⁻⁵³）",
    r"\frac{g}{d(1+u)}<\mathrm{sw}(g)\le\mathrm{next}\!\left(\frac{g}{d(1-u)}\right)",
    "定義＋[P]", "IEEE 754 倍精度・最近接丸め、g>0 の有限の浮動小数", "03 §3.3；05 §3.2", [s(S_T03, "補題 L-2")], [(C17 + "timechar.py", "tswitch・tstar")],
    "[F] 347 シナリオで最大 1.50 ulp（{T:17.L-2}）", "A", "不等式そのものは {T:17.L-2}")
add("F-06", "formula", "17/03 §0", "定義域：𝒟 は第 11 章の valid_domain の内側。𝒟′ は 𝒟 から、切り替え点が自分の年セルの終わりを越える事象 τ（K=⌈fl(τd)⌉<sw(τ)）の直後の帯 T∈(K,sw(τ)] を除いたもの",
    r"\mathcal{D}'=\mathcal{D}\setminus\bigcup_{\tau:\,K<\mathrm{sw}(\tau)}\{(\mathbf{x},T):\ T\in(K,\mathrm{sw}(\tau)]\}",
    "定義", "0<T≤H、H<256。以後のモデルとの一致の主張はすべて 𝒟′ での主張", "03 §3.4；05 §4.3", [s(S_T03, "§0"), s(S_LIM, "§2")], [(R + "tstudy/scenarios.py", "valid_domain"), (C17 + "sliver_test.py", "（帯の照合）")],
    "[F] 帯の反例（C-09）", "A", "集合の書き方は本基盤の要約（原典は文章で定義）")
add("F-07", "formula", "SPEC_KNOTS §1", "時間核（第 10・14 章）：振幅 a_j は T によらない。節点スペクトルは核の重ね合わせ",
    r"h(T;\,s,\ell,g)=\bigl[g<T(1-\varepsilon)\bigr]\operatorname{clip}\!\Big(\frac{T-s}{\ell},0,1\Big),\quad \ell=0\Rightarrow\operatorname{clip}(\cdot)=1,\quad \Phi(T)=\sum_j a_j\,h(T;s_j,\ell_j,g_j)",
    "定義", "T∈(0,H]。定数 (0,0,−∞)、原子 (τ,0,τ)、年セル (k,1,−∞)、ゲート付き年セル (k,1,τ)、密度 (0,H,−∞)", "03 §5.1；05 §2.1", [s(S_SKN, "§1"), s(S_E03, "§1")], [(R + "tstudy/rampstep.py", "h")],
    "[F] EXP-01（2,720 組で相対 4.8e-13）", "A", "")
add("F-08", "formula", "17/01 §2", "時間核（第 17 章）：振幅を率で持ち、区間形の窓を加えた形",
    r"\kappa(T;\,s,\ell,g,\mathrm{lo},\mathrm{hi})=[\mathrm{lo}<T\le\mathrm{hi}]\;\theta_\varepsilon(T;g)\;r_\ell(T-s),\quad r_0\equiv1,\ r_\ell(x)=\operatorname{clip}(x,0,\ell)",
    "定義＋[P]", "F-07 と同じ関数を与える（密度では aH clip(T/H,0,1)=a min(T,H)）[P]（定義からの計算）", "03 §5.1；05 §2.2", [s(S_T01, "§2")], [(C17 + "canon.py", "Canon")],
    "[F] 率で持つと基準計算が厳密に 0 を返す段階値を残差なく再現（C-31）", "A", "")
add("F-09", "formula", "SPEC_KNOTS §3", "跳び形（KnotSpectrum）：各項を節点に（値の跳び c⁰、傾きの跳び c¹）として置き、累積和と二分探索で評価（O(log N)）",
    r"\Phi(T)=b+\sum_{j:\,t^{e}_j<T(1-\varepsilon)}\bigl(c^{0}_j+c^{1}_jT\bigr)+\sum_{j:\,t^{p}_j<T}\bigl(c^{0}_j+c^{1}_jT\bigr)",
    "定義", "節点を時刻の昇順に並べる。強く減衰する量（冷媒の期末残存量）では桁落ちする [F]", "03 §5.3；05 §3.4", [s(S_SKN, "§3")], [(R + "tstudy/knots.py", "KnotSpectrum")],
    "[F] EXP-02（2,033 組で 4.3e-12）", "A", "")
add("F-10", "formula", "SPEC_KNOTS・17/02 §2", "区間形（IntervalSpectrum）と冷媒の期末残存量 R(T)：年セル K の係数と補正",
    r"R(T)=\mathcal{A}_K+\mathcal{B}_K(T-K)+\sum_{j\in\text{セル }K}\theta_\varepsilon(T;\tau_j)\bigl(\alpha^R_j+\gamma^R_j(T-K)\bigr),\quad K=\lceil T\rceil-1",
    "定義", "𝒜_K=Σ_d κ_{R,d} u_{d,K}、ℬ_K=−Σ_d κ_{R,d}[補充なし] u_{d,K} r_d、κ_{R,d}=(1−η_d)GWP_d", "03 §5.4；05 §7.4", [s(S_SKN, "§4"), s(S_T02, "§2")], [(R + "tstudy/interval.py", "IntervalSpectrum")],
    "[F] EXP-U1 45 点で 6.6e-15（mpmath 60 桁）", "A", "跳び形と同じ関数であることは {T:10.D-09}。帯 (K,sw(τ)) を除く")
add("F-11", "formula", "D-08", "冷媒の年初残存量の漸化式（交換で切り替わるアフィンの漸化式）と冷媒の排出",
    r"u_{d,0}=m_{0,d},\quad u_{d,k}=\chi_{d,k-1}m_{0,d}+(1-\chi_{d,k-1})\,q_d\,u_{d,k-1},\quad \mathrm{B1\text{-}02}(T)=\sum_{d,k}u_{d,k}\,r_d\,\mathrm{GWP}_d\,w_k(T)",
    "定義", "q_d=[補充あり]+[補充なし](1−r_d)。k=1,…,H−1", "03 §5.5；05 §7.1", [s(S_DER, "D-08 (a)(f)"), s(S_T02, "§2")], [(R + "specs/physical.py", "REFRIGERANT"), (R + "specs/lib.py", "テンプレート STATE")],
    "[E] 解 u=m₀q^ν（{T:10.D-08-a}）；[F] EXP-U3 1,689 組", "A", "")
add("F-12", "formula", "D-08 (d)・SPEC_MSP §5", "倍化（DOUBLE）：べき零のずらしのレゾルベントの 1 因子を積和 1 段で（s=1,2,4,…,128）",
    r"c^{(1)}_k=[k\ge1][p_{k-1}=0]\,q,\quad c^{(2s)}_k=c^{(s)}_k\,c^{(s)}_{k-s},\quad u\leftarrow u+c^{(s)}_k\,u_{k-s}",
    "定義", "H<256（8 段）。s 年前の行は（機器、k−s）をキーにした match", "03 §5.5；04 §3 (R9)", [s(S_DER, "D-08 (d)"), s(S_SMSP, "§5")], [(R + "specs/lib.py", "テンプレート DOUBLE")],
    "[F] 基準計算の逐次計算と B1-02 3.5e-15、B1-03 2.6e-14 以下（05_HISTORY H-18）", "A", "恒等式は {T:10.D-08-d}")
add("F-13", "formula", "14/07 §1", "建物全体の合成：共通表 → 積和① → 節点スペクトル → 積和②（TIME・AGG）→ 読み出し",
    r"\mathcal{R}(\mathbf{x},T)=\mathrm{RO}\Big(\mathrm{AGG}\big(\mathrm{TIME}\big(\mathcal{P}_1(\mathcal{I}(\mathbf{x})),\ \{K_s(T)\}_s,\ T\big),\ \{v_u(T)\}_u,\ T\big)\Big)",
    "定義", "𝒫₁ 1,528 ステップ、TIME 95、AGG 166（計 1,789）、スペクトル跳び形 23＋区間形 1。共通表 ℐ は算術なし", "03 §6.1；06 §1", [s(S_E07, "§1"), s(S_E14, "§2")], [(R + "tstudy/unified.py", "System・System.at"), (R + "specs/system.py", "SPEC1・EMIT"), (R + "specs/at_t.py", "TIME・AGG")],
    "[F] 1,293 組・22,698,402 値で不一致 0（C-03）", "A", "2 構造の外の処理（文字列の分割・並べ替えなど）は LIMITS §3")
add("F-14", "formula", "14/07 §2・§3", "ホールライフ合計：段階×単位の 0/±1 行列（構成表 COMP 22 行）による外側の積和",
    r"C(T)=S_3(T)=\sum_{s}\iota_s\sum_{u\in\mathcal{U}_C}\sigma_{s,u}\,\beta_{s,u}\,V_u(T),\qquad \beta_c=1+\mathrm{needs\_b2}_c\bigl([\mathrm{inc}_{\mathrm{B2}}]-1\bigr)",
    "定義", "𝒰_C は直接寄与する 21 単位（本基盤で追加した記号）。σ は (B6,B2-01) だけ −1、β_{B6,B2-01}=ι_B2", "02 §4；03 §6.2；06 §3", [s(S_E07, "§2・§3"), s(S_T02, "§3")], [(R + "specs/system.py", "COMP_ROWS・表 COMP"), (R + "specs/at_t.py", "AGG")],
    "[P] 計算の定義（{T:14.COMP}）；[F] 1,293 組", "A", "")
add("F-15", "formula", "17/01 §1", "階層 L2〜L4：単位の値・段階の値・合計",
    r"V_u(T)=\sum_{j\in J_u}a_j\,\kappa_j(T),\qquad S_s(T)=\iota_s\sum_u\sigma_{s,u}\beta_{s,u}V_u(T),\qquad C(T)=\sum_sS_s(T)",
    "定義", "21 単位・14 段階。L0 入力、L1 積和①の列、L5 節点形、L6 実時間の分解", "03 §6.2；06 §4.1", [s(S_T01, "§1")], [(C17 + "canon.py", "build・unit_pieces・stage_inclusion")],
    "[F] 正準形 vs 基準計算（C-07）", "A", "")
add("F-16", "formula", "17/01 §3", "完全理想方程式（役割を分けた形）。すべての係数は符号と段階の述語を含む",
    r"C(T)=A^{\mathrm{init}}+A^{\mathrm{term}}+\sum_{u\in\mathcal{U}_B}\sum_{k=0}^{H-1}B^{(u)}_k w_k(T)+B^{(\mathrm{B3})}_\ast\min(T,H)+\sum_{u\in\mathcal{U}_\Gamma}\sum_j\Gamma^{(u)}_j\theta_\varepsilon(T;\tau_j)+\sum_{u\in\mathcal{U}_\Delta}\sum_m\Delta^{(u)}_m\theta_\varepsilon(T;\tau_m)w_{k_m}(T)+\iota_{\mathrm{B1}}R(T)",
    "定義（展開）", "T∈(0,H]。𝒰_B={B1-02、B2-01（B2）、B6-03、B2-01（B6 の差し引き）、B7-04}、𝒰_Γ={B1-03（原子）、B4-02、B5-01}、𝒰_Δ={B1-03（ゲート付き）、B3-01（ゲート付き）}", "03 §6.3；06 §4.2", [s(S_T01, "§3"), s(S_T02, "§2")], [(C17 + "canon.py", "build・Canon")],
    "[P] 核の和＝節点形（{T:17.TH-0i}）；[F] SUM-03 で 1,293 組（C-07）；[S] 90,055 ケース（C-10）", "A", "係数と入力の対応は 06 §5（17/02）")
add("F-17", "formula", "17/01 §4", "節点形（L5）：格子の節点と事象の節点の切断べきの和。区切り点 Π={0,…,H}∪{sw(g)}",
    r"C(T)=A_0+\sum_{t\in\Lambda}[\,t<T\,](P_t+Q_tT)+\sum_{g\in E}\theta_\varepsilon(T;g)(p_g+q_gT)",
    "定義", "係数は有理数（浮動小数の振幅・時刻の積と和を厳密に計算）。t は節点の位置で実時間ではない", "03 §5.6；05 §3.5", [s(S_T01, "§4"), s(S_T03, "TH-0")], [(C17 + "timechar.py", "KF")],
    "[P] {T:17.TH-0i}；[E] S3 52,157 など", "A", "保存した係数のままでは最小でない（C-17）")
add("F-18", "formula", "14/07 §5", "合計・指標・比較：アップフロント・エンボディド・ホールライフ、床面積当たり、年平均・床面積当たり、t 換算、段階の割合",
    r"\mathrm{SUM04}=[A>0]\,S_3\tfrac1A,\quad \mathrm{SUM05}=[A>0]\,S_3\tfrac{1}{AT},\quad \mathrm{SUM06}=0.001\,S_3,\quad \mathrm{share}_s=[\mathrm{inc}_s][S_3>0][\#\{\mathrm{bs}<0\}=0]\tfrac{\mathrm{bs}_s}{S_3}",
    "定義", "述語が真のとき。割り算は逆数との積で最後の 1 ビットが違いうる [F]", "03 §6.4；06 §6.4", [s(S_E07, "§5")], [(R + "specs/at_t.py", "AGG")],
    "[F] 1,293 組；区間ごとの形は {T:17.TH-14}", "A", "")
add("F-19", "formula", "18/02・18/04 §1", "工程関数（17 族）の和と動的な合計",
    r"e_{\mathrm{total}}(t)=\sum_jm_j\,\delta(t-t_j)+\rho_{\mathrm{total}}(t),\qquad C_{\mathrm{dyn}}(T)=\int_{[0,T]}e_{\mathrm{total}}(t)\,dt+Z(T)",
    "定義", "t は実時間。正準形の各項はちょうど 1 族に入る（P01〜P17）", "03 §7；07 §4.1・§6.1", [s(S_18_02, "§1"), s(S_18_04, "§1")], [(C18 + "processes.py", "family_of・ProcessFunction・decompose")],
    "[P] 再構成（{T:18.REC}）；[E] 4,248 点", "A", "")
add("F-20", "formula", "18/06", "動的な特性化：実時間の排出と CO2 の応答関数の畳み込み（CO2e を CO2 とみなす近似）",
    r"\mathrm{IRF}_{\mathrm{CO_2}}(t)=a_0+\sum_{i=1}^{3}a_ie^{-t/\tau_i},\quad R(h)=a_0h+\sum_ia_i\tau_i\bigl(1-e^{-h/\tau_i}\bigr),\quad W(t_{\mathrm{end}})=\sum_{\text{原子}}m_j\frac{R(t_{\mathrm{end}}-t_j)}{R(100)}+\sum_{\text{一様な塊}}\frac{a}{t_1-t_0}\int_{t_0}^{t_1}\frac{R(t_{\mathrm{end}}-t)}{R(100)}dt",
    "[L]＋定義", "文献の応答関数（Joos ら 2013）。ガス別の時間分解された目録が無いので近似。気候影響の値として使わない", "07 §7.2", [s(S_18_06, "§2〜3")], [(C18 + "dyncharac.py", "R・weighted")],
    "[F] 時期の仮定で約 1e-3 変わる（C-12）", "A", "係数 a・τ は Joos ら 2013 の値（07 §7.2）。τ_i は応答関数の時定数で工程の局所時間ではない。R(h) は冷媒の期末残存量 R(T) と別の記号")
add("F-21", "formula", "VERIFICATION 冒頭", "照合の合格条件（浮動小数どうしの一致の規則で、数学的な等号ではない）",
    r"\lvert a-b\rvert\le10^{-9}\lvert b\rvert\ (b\ne0),\qquad a=0\ (b=0),\qquad \text{真偽・整数・文字列・キーは型を含めて完全一致}",
    "定義", "第 9・10・17・20 章の照合と本基盤の台帳の照合", "05 §11；14 §0.2", [s(S_VER, "冒頭")], [(R + "checks/check_msp_pre_a.py", "compare")],
    "—", "A", "")
add("F-22", "formula", "20/02 §1", "失敗 0 のときの失敗確率の 95% 片側上限（シナリオ単位）",
    r"p_{95}=1-0.05^{1/N},\qquad N=18{,}011\Rightarrow p_{95}\approx1.7\times10^{-4}",
    "[P]（二項分布の標準の上限）", "同じシナリオの 5 ケースは独立でないので N はシナリオ数。ケースを独立とみなした 3.3e-5 は参考", "08 §3.8", [s(S_20_02, "§1"), s(S_20R, "§3")], [(C20 + "agg4.py", "（集計）")],
    "本基盤で 1−0.05^(1/N) を N=18,011・90,055 で再計算して一致（14 §5）", "A", "")
add("F-23", "formula", "15 §4.1", "更新過程：更新の回数（右連続）、更新関数、更新方程式",
    r"N_F(t)=\#\{n\ge1:\tau_n\le t\},\quad m_F(t)=\mathbb E[N_F(t)]=\sum_{k\ge1}F^{\ast k}(t),\quad m_F=F+F\ast m_F",
    "[L]", "寿命 X_i は独立同分布、分布関数 F。t は実時間", "15 §4.1・§6.1", [base("15_劣化・寿命・交換モデル研究開始資料.md", "§4.1・§6.1")], [(B + "tools/renewal_examples.py", "solve_renewal・second_moment（JSON の renewal_function）")],
    "[F] 数値解の収束（2 次）、指数分布で t/μ と 1e-6 以内（15 §9.4）", "L", "Cox 1962、Feller 1971、Ross 1996（頁は未照合）")
add("F-24", "formula", "15 §3.1", "故障率（ハザード）と累積ハザード",
    r"h_F(x)=\frac{f(x)}{\bar F(x)},\qquad \Lambda_F(x)=\int_0^xh_F,\qquad \bar F(x)=e^{-\Lambda_F(x)}",
    "[L]", "x は個体の年齢。既存の核 h(T;s,ℓ,g)、格子 Λ とは別の記号（本資料で追加、添字 F）", "15 §3.1", [base("15_劣化・寿命・交換モデル研究開始資料.md", "§3.1")], [],
    "—", "L", "")
add("F-25", "formula", "15 §6.3・§7", "年齢に依る量の期待値（効率低下・冷媒の残存など）",
    r"\mathbb E[g(a(t))]=g(t)\bar F(t)+\int_0^tg(t-s)\bar F(t-s)\,dm_F(s)",
    "[L]", "a(t)=t−τ_{N_F(t)}。更新関数だけでは決まらない", "15 §6.3・§7.3", [base("15_劣化・寿命・交換モデル研究開始資料.md", "§6.3・§7")], [(B + "tools/renewal_examples.py", "age_expectation・key_renewal_limit（JSON の age_functions）")],
    "[F] q^a の期待値は q^{E[a]} より 16% 大きい（例示）", "L", "")
add("F-26", "formula", "15 §5.6", "期待更新測度のラプラス・スティルチェス変換と極",
    r"\tilde m_F(s)=\frac{\tilde F(s)}{1-\tilde F(s)}",
    "[L]／[P]", "固定周期では極が虚軸上の 2πik/c、非格子の分布では s=0 を除き左半平面", "15 §5.6", [base("15_劣化・寿命・交換モデル研究開始資料.md", "§5.6")], [(B + "tools/renewal_examples.py", "solve_renewal（JSON の blackwell）")],
    "減衰の見積もり exp(−2π²CV²) は [H]（{T:15.DAMP}）", "L", "")
add("F-27", "formula", "15 §7.1", "連続的な電力使用と効率低下の定式化（既存モデルには無い）",
    r"e_{\mathrm{op}}(t)=\mathrm{EF}(t)\frac{Q_{\mathrm{dem}}(t)}{\eta(a(t))},\quad C_{\mathrm{op}}(T)=\int_0^Te_{\mathrm{op}}(t)\,dt,\quad \mathbb E\Big[\frac{1}{\eta(a(t))}\Big]=\frac{\bar F(t)}{\eta(t)}+\int_0^t\frac{\bar F(t-s)}{\eta(t-s)}\,dm_F(s)",
    "[H]", "需要と排出係数が寿命と独立（決定論的）なとき。既存モデルの B6-03・B2-01 は交換の時刻に依存しない [P]（モデルの構造について）", "15 §7.1", [base("15_劣化・寿命・交換モデル研究開始資料.md", "§7.1")], [(B + "tools/renewal_examples.py", "age_expectation・key_renewal_limit（JSON の age_functions）")],
    "[F] 例示の数値（15 §7.2）", "BASE", "記号 EF・Q_dem・η・b_η は 15 §0.3 で追加")

# ---------------------------------------------------------------- T（本基盤の追加分。theorems.csv の行は build_claims.py が足す）
TEXTRA = []


def addt(*row):
    TEXTRA.append(row)


addt("04.R2", "排他的な分岐の列：if A then a elif B then b else c = [A]a+¬[A][B]b+¬[A]¬[B]c", "P", "述語の値が 0/1。浮動小数でも選ばれない項は厳密に 0 を足す（−0 は +0 になりうる）",
     "04 §3 (R2)", [s(S_SMSP, "§3"), s(S_DER, "D-01")], [(R + "tstudy/msp.py", "Engine.run_sp")], "[F] 試験で 2,000 行のビット一致（04 §2.5）", "A", "")
addt("04.R4", "最大・絶対値・許容幅：max(0,d)=[d≥0]d、max(p,q)=[p≤q]q+¬[p≤q]p、|d|=[d≥0]d+[d<0](−1)d、[|d|≤tol]=[d≤tol][−d≤tol]", "P", "実数の値。符号による場合分け",
     "04 §3 (R4)", [("10_TRANSFORM_STUDY/05_HISTORY/README.md", "bd45157", "H-17")], [(R + "specs/", "（仕様データ）")], "[F] 照合で一致", "A", "")
addt("04.R5", "割り算 a/b=a·inv(b)（b=0 は述語で外す）は実数で恒等式。浮動小数では最後の桁が違いうる（X-13 で相対 2.2e-12、端材率 1e-8 程度以下で 1e-9 を超える：反例 CX-04）", "P＋F", "実数では恒等式 [P]、浮動小数の差は [F]",
     "04 §3 (R5)；09 OQ-16", [("10_TRANSFORM_STUDY/05_HISTORY/README.md", "bd45157", "H-08")], [(R + "tstudy/msp.py", "inv")], "[F] 統一系の照合の最大相対差（X-13）", "A", "変換実験の基本方式の境界条件の 46 件も同じ原因（15/03）")
addt("04.R6-R8", "検索と優先順位は match と排他的な述語の和、2 つのキーのまとめ・集合の一致・件数は全組合せの表・present の否定・和、前の行は位置 −s をキーにした match", "P", "キーが一意なら順序に依らない（定義から）",
     "04 §3 (R6)〜(R8)", [s(S_SMSP, "§3"), s(S_DER, "D-02・D-10")], [(R + "specs/", "（仕様データ）")], "[F] 照合", "A", "")
addt("04.R10", "評価期間 T のゲートと年重みを述語と一次式の積で書く：[τ<T′]=¬[T′≤τ]、w_k(T)=[k<T]([k+1≤T]+¬[k+1≤T](T−k))", "P", "T>0 の実数。T の場合分け",
     "04 §3 (R10)；03 §3.2", [s(S_SKN, "§3"), s(S_E07, "§6")], [(R + "specs/at_t.py", "TIME")], "[F] 統一系の照合", "A", "")
addt("04.R11", "走査の打ち切り（最初の使えない構成材で止まる）を、使えない構成材の数を数える形にしても公開出力は同じ", "P", "公開出力についての同値で、途中の量の同値ではない",
     "04 §3 (R11)", [("10_TRANSFORM_STUDY/05_HISTORY/README.md", "bd45157", "H-10")], [(R + "specs/", "（仕様データ）")], "[F] 照合", "A", "")
addt("04.CONV", "逆向きの表現定理：有限個の基本半代数的集合の非交和の上の区分的有理関数は、実数の模型の有限の手順で厳密に計算できる（補題 1 と合わせると類が一致する）", "H", "固定したデータ配置・実数の模型。表現の大きさについては何も言わない",
     "04 §4.2；09 OQ-23", [base("04_マスク積和の理論.md", "§4.2")], [], "証明の概略だけ（未検査）", "BASE", "原典に無い本基盤の主張")
addt("04.FIN", "入力が有限個の値に限られるなら、[x=d_k]·c_k の有限和で任意の関数を再現できる（ただし大きさが実現できない）", "P", "有限集合の上の関数（自明な構成）",
     "04 §4.5", [s(S_16_03, "§2「区間でなく有限集合の上では」")], [], "—", "A", "変換実験の文書の記述。70 単位にも当てはまる一般の事実")
addt("04.EXP", "どの開区間でも有理関数にならない実解析関数（e^x など）も、同じ論法で 2 構造の有限の合成では実数として厳密に表せないはず", "H", "原典が扱ったのは x^a（a 非整数）と log10 x だけ",
     "04 §6.1", [base("04_マスク積和の理論.md", "§6.1")], [], "証明は書いていない", "BASE", "")
addt("04.UND", "方式 A で判定できない入力の割合は、真値の下位ビットが一様とみなせる入力で約 2⁻³⁷", "H", "一様性は仮定。構造をもつ入力では成り立たない可能性",
     "04 §6.2", [s(S_16R, "方式 A")], [("16_UNRESOLVED8_EXACT_APPROX/tools/exact8.py", "（方式 A）")], "原典の見積もり", "B", "原典の見積もりを本基盤が [H] と読んだ")
addt("04.FP", "方式 B の指紋の衝突確率の上限", "H", "原典の 1 文の主張で、論証が無い",
     "04 §6.6", [s(S_16R, "方式 B")], [], "—", "B", "")
addt("04.LB", "互いに異なる N 個の部分を区別するには少なくとも ⌈log₂N⌉ 個の述語の因子が要る、という種類の大きさの下限", "H", "原典では検討していない",
     "04 §7.2；09 OQ-20", [base("04_マスク積和の理論.md", "§7.2")], [], "—", "BASE", "")
addt("07.GAUGE", "任意の有限な符号付き測度 ν について (M+ν, Z−ν([0,·])) も同じ C(T) を与える。C(T) を (0,H] のすべてで知っても M と Z は分けられない", "P", "TH-4 と同じ。単位の意味という外からの約束が要る",
     "07 §8.2", [s(S_T03, "TH-4 (c)"), base("07_動的LCAと工程時間.md", "§8.2")], [], "定義からの 1 行の計算（本資料での言い換え。新しい主張ではない）", "BASE", "")
addt("15.DEG", "退化した寿命分布 F=1_[c,∞) は更新過程の特別な場合で m_F(t)=⌊t/c⌋。既存の回数は N_c(T)=lim_{s↑T(1−ε)}⌊s/c⌋=N_F((T(1−ε))⁻)", "P＋F", "実数の規則 τ_n=nc。浮動小数の τ_n=fl(nc) では帯の外",
     "15 §5.1・§5.2", [base("15_劣化・寿命・交換モデル研究開始資料.md", "§5.1・§5.2"), s(S_T03, "TH-11")], [(B + "tools/renewal_examples.py", "fixed_cycle_section・load_rampstep"), (R + "tstudy/rampstep.py", "h（読み取り専用）")],
     "[F] 既存の原子の核 h(T;τ,0,τ) と閉じた形を 576 点で比べて不一致 0", "BASE", "")
addt("15.LIM", "平均を c に固定した Weibull で β_W→∞ とすると t∉cℕ で m_F(t)→⌊t/c⌋。収束は t について一様でない（k 回目の節点の近くの幅はおよそ √k σ_F）", "P＋F", "t が c の整数倍でない点",
     "15 §5.4", [base("15_劣化・寿命・交換モデル研究開始資料.md", "§5.4")], [(B + "tools/renewal_examples.py", "solve_renewal（JSON の limit_beta）")], "[F] 数値（15 §5.4）", "BASE", "本資料の証明。独立の確認なし")
addt("15.DAMP", "非格子の分布での周期の部分の減衰の見積もり exp(−2π²CV²)、周期の数が 1/CV² に比例", "H", "β=6・10 でだけ大まかに数値と合う",
     "15 §5.6", [base("15_劣化・寿命・交換モデル研究開始資料.md", "§5.6")], [(B + "tools/renewal_examples.py", "solve_renewal（JSON の blackwell）")], "[F] 粗い一致", "BASE", "")
addt("15.ERT", "基本更新定理 m_F(t)/t→1/μ_F と 2 次の漸近形 m_F(t)=t/μ_F+(σ_F²−μ_F²)/(2μ_F²)+o(1)", "L", "μ_F<∞（2 次の形は σ_F²<∞ かつ非格子）",
     "15 §6.2", [base("15_劣化・寿命・交換モデル研究開始資料.md", "§6.2（R2・R5）")], [(B + "tools/renewal_examples.py", "solve_renewal・second_moment（JSON の renewal_function）")], "[F] 漸近形との差（数値例）", "L", "Smith 1958、Feller 1971（頁は未照合）")
addt("15.BLK", "Blackwell の更新定理：非格子の分布で m_F(t+h)−m_F(t)→h/μ_F（格子の分布では格子点の上で）", "L", "非格子・格子の条件を区別",
     "15 §6.2", [base("15_劣化・寿命・交換モデル研究開始資料.md", "§6.2")], [(B + "tools/renewal_examples.py", "solve_renewal（JSON の blackwell）")], "[F] 年あたりの期待交換回数が 1/μ に近づく（数値例）", "L", "Blackwell 1948")
addt("15.KEY", "鍵となる更新定理と年齢の極限分布（直接リーマン可積分な関数について）", "L", "条件は 15 §6.2 に正確な形で",
     "15 §6.2・§6.3", [base("15_劣化・寿命・交換モデル研究開始資料.md", "§6.2・§6.3")], [(B + "tools/renewal_examples.py", "age_expectation・key_renewal_limit（JSON の age_functions）")], "[F] 年齢の汎関数の極限（数値例）", "L", "R9（更新密度の収束）の条件は確かめていない")
addt("15.SMOOTH", "台数 n_u の合計の期待値は n_u·m_F、標準偏差は √n_u に比例し、台あたりでは 1/√n_u で縮む（離散の交換から滑らかな期待曲線）", "L＋F", "独立同分布の台。例示の分布（平均 15 年、β_W=3.5）",
     "15 §9.1・§9.2", [base("15_劣化・寿命・交換モデル研究開始資料.md", "§9")], [(B + "tools/renewal_examples.py", "simulate・group_stats（JSON の monte_carlo）")], "[F] n_u=1000 の 1 回の実現で 31〜130 年の相対偏差の二乗平均 0.121；[S] 例示の分布でのモンテカルロ（z が定義される 75 組で max |z|=1.68）", "L", "")
addt("11.EXI1", "c=μ_F のとき、すべての T で |m_F((T(1−ε))⁻)−N_c(T)| ≤ 1+CV_F²（Lorden の不等式と Wald の等式から。m_F(T) と比べるなら右辺に Tε/c を足す）", "H", "未検査の候補の上界",
     "11 §3 HYP-I（EX-I1）；15 §11 I-1", [base("11_研究実験計画.md", "HYP-I")], [], "—", "BASE", "15 §5.5・§11 I-1 の長期の形 (1+CV²)/2+Tε/c+o(1)（R5 から）とは別の形（すべての T）")
addt("09.BAND", "帯の修復の案：年セル K の窓を (K,sw(τ)] と (sw(τ),K+1] に分け、前者で初期化前の係数を使う区間形で、𝒟 全体で基準計算と一致し桁落ちしない", "H", "本書の見込み",
     "09 OQ-07", [base("09_未解決問題と限界.md", "OQ-07")], [(C17 + "sliver_test.py", "（拡張して照合する）")], "—", "BASE", "11 EX-U1")
addt("09.DYN", "動的な特性化の指標 W(t_end) を t_end=T とした T の関数は、累積応答が指数を含むので T について区分一次ではない", "H", "18/06 の式からの帰結として本基盤が整理",
     "09 OQ-17", [base("09_未解決問題と限界.md", "OQ-17"), s(S_18_06, "§2〜3")], [], "—", "BASE", "")

# ---------------------------------------------------------------- C: 主張（件数・分類・限界・記録）
add("C-01", "claim", "09 台帳", "70 評価単位＝既存の概念式 53＋追加で特定した計算構造 17（X-01〜X-17）。追加の単位は独立設計の案で、原版の式の再現ではない。シート族との対応はシート名からの推定",
    "", "記録", "独立概念モデル（架空データ）", "01 §3.2", [s(S_09L, "全体"), s(S_09R, "冒頭")], [("09_APPROX_STUDY/research_code/refcalc/registry.py", "（単位の登録）")], "—", "A", "")
add("C-02", "claim", "14/07 §3・§4", "70 単位の役割：DIRECT 21（T によらない 12、T に依存する 9。構成表 22 行）、AGGREGATE 9、AUXILIARY 15、REFERENCE 10、DECISION 9、BREAKDOWN 6。70 単位は 70 個の独立した物理法則ではない",
    "", "定義＋記録", "DIRECT は構成表 COMP に行を持つ単位として定まる（14/07）。AGGREGATE・REFERENCE は本基盤（02）で加えた区分", "02 §3；06 §2；01 §6", [s(S_E07, "§3・§4"), s(S_T01, "§5"), base("02_70評価単位の完全台帳.md", "§3")], [(B + "tools/check_units70.py", "（構造の検査）")],
    "[F] 構成表の行を持つ単位がちょうど DIRECT の 21 単位で 22 行（02 §6 (a)）", "A＋BASE", "")
add("C-03", "claim", "VER §1", "統一系（全 70 単位・公開出力 190 キー）が基準計算と 1,293 組・22,698,402 値で不一致 0、最大相対差 2.2e-12（X-13）、それを除くと 5.7e-13（B3-01）",
    "", "F", "架空データの 10 集合、valid_domain の内側（境界ちょうどの 2 組を除外）、確認者は実装者のみ。𝒟′ に限る（帯の反例 C-09）", "04 §4.3；08 §3.2；06 §7.2", [s(S_VER, "§1・§2")], [(R + "checks/check_unified.py", "main"), (R + "checks/sets_unified.py", "（10 集合）")],
    "本基盤で再実行して一致（RUN-03、521 秒）", "A", "全入力での一致の定理は無い（OQ-01）")
add("C-04", "claim", "VER §5", "仕様を 1 か所ずつ壊す負の対照 24 件をすべて検出、QA-01 の故障注入 4/4", "", "F", "第 11 章の誤り検出の集合", "08 §3.3",
    [s(S_VER, "§5")], [(R + "checks/check_unified_controls.py", "main")], "本基盤で再実行して一致（RUN-04）", "A", "")
add("C-05", "claim", "IMPL", "マスク付き積和の最初の形（TC-B-01）：製品・輸送・施工の 18 単位の公開出力 50 種類が 171 シナリオ・159 万値で一致。計算は基準計算より遅い（1.1〜12.6 倍、前処理を含めると 7.8〜32.6 倍）", "", "F",
    "18 単位、架空データ", "01 §3.3；08 §5.3", [s(S_IMPL, "§2〜6")], [(R + "checks/check_msp_pre_a.py", "main"), (R + "specs/pre_a.py", "（仕様データ）")], "本基盤で再実行して一致（RUN-05）", "A", "")
add("C-06", "claim", "IMPL §4", "語彙（命令と因子の種類）は 26 種類で、単位の数とともに増え続けなかった（最初の単位で 14、5 単位で 21、残り 13 単位で 5）。全 70 単位でも 1 列の関数は 4 つのまま", "", "F（数え上げ）",
    "18 単位の測定と全 70 単位の仕様", "04 §7.1", [s(S_IMPL, "§4"), s(S_SMSP, "§1")], [(R + "checks/check_msp_pre_a.py", "（語彙の記録 msp_vocabulary.json）")], "—", "A", "最小性の主張ではない")
add("C-07", "claim", "17/07 §1", "正準形（理想方程式）が基準計算・統一系と SUM-03 で 1,293 組一致（最大相対 1.0e-13）、評価範囲の段階の値 17,884、合計に入る 21 単位の値 27,153 が一致", "", "F",
    "𝒟′ の保存した 10 集合。相対 1e-9", "06 §7.1；08 §3.6", [s(S_T07, "§1")], [(C17 + "verify_canon.py", "main")], "本基盤で rep_defects を再実行して一致（RUN-09）", "A", "")
add("C-08", "claim", "17/07 §2", "時間特性の定理の照合：347 シナリオで厳密な照合の失敗 0（S1〜S6、TH-0・TH-2・TH-6 など）", "", "E",
    "保存した集合の点（有理数）", "08 §3.6；05 各節", [s(S_T07, "§2"), ("17_WHOLE_BUILDING_TIME_THEORY/results/stage1_summary.json", "46781f2", "")], [(C17 + "timechar.py", "th0123・th45・th6"), (C17 + "timechar_terms.py", "S1〜S7")],
    "—", "A", "節点形の全区間の照合は実装の確認（原典の注記）")
add("C-09", "claim", "17/03 TH-2.3・17/07 §6", "未解決の切り替え境界の反例：整数の時刻の交換で、帯 (K,sw(τ)) の中の位置ごとに 9 組中 2 組が相対 1e-9 を超えて異なる（B1-04 で 5.5e-3、SUM-03 で 1.1e-5）。整数の近くの浮動小数の時刻は未照合", "", "F",
    "整数の時刻の一覧の交換年を持つ冷媒のシナリオ", "03 §3.4；05 §4.3；08 §4.1；09 OQ-07", [s(S_T03, "TH-2 の 3・§0"), s(S_T07, "§6")], [(C17 + "sliver_test.py", "main")], "—", "A", "主張を 𝒟′ に縮めた理由")
add("C-10", "claim", "20/02 §1", "大規模ランダム検証：20,000 シナリオ × 5 期間＝100,000 ケースのうち定義域の内側 90,055 ケース（18,011 シナリオ）で失敗 0。シナリオあたりの失敗確率の 95% 片側上限 1.7e-4", "", "S",
    "宣言した抽出分布（層 N・B・G・E・S）。帯 (K,sw(τ)] にはほとんど確率を置かない（0 ではない）。分布の外・全入力については何も言わない", "08 §3.8；06 §7.3", [s(S_20_02, "§1・§2"), s(S_20R, "§3")], [(C20 + "run4.py", "scenario_checks・checks_on"), (C20 + "gen4.py", "（抽出）"), (C20 + "agg4.py", "（集計）")],
    "本基盤で塊 0 を再実行して JSON として同一（RUN-11）", "A", "仕様と基準計算が同じ誤解を持てば見つからない（OQ-02）")
add("C-11", "claim", "18/07 §1", "動的 LCA の再構成の照合：79 シナリオ・評価期間 4,248 点・実体 65,948 個で有理数として不一致 0", "", "E",
    "保存した集合の点", "07 §6.2；08 §3.7", [s(S_18_07, "§1")], [(C18 + "dynlca.py", "analyse")], "本基盤で dev_edge 5 シナリオを再実行して一致（RUN-10）", "A", "")
add("C-12", "claim", "18/07 §4・18/06", "時間配分の変種 X1〜X4 で合計は 108/108 組で厳密に一致し、時間で重みをつけた気候指標だけが変わる（約 1e-3、終点が T に近いと 1 の桁）", "", "E＋F",
    "仮定の変種（データに基づかない）", "07 §7.4・§8.5", [s(S_18_07, "§4"), s(S_18_06, "§4")], [(C18 + "extensions.py", "timeline"), (C18 + "dynlca.py", "ext_analysis"), (C18 + "dyncharac.py", "weighted")], "—", "A", "")
add("C-13", "claim", "EXP-03", "更新の回数のフーリエ表現は精度が出ない：ずらさない級数は合計の最大誤差 19.5%（反例 CX-01）、ずらしても 256 項で合計の最大 3.8%、更新の排出の最大 23%。整数格子の有限の離散フーリエ和は厳密（176 組で 9.6e-14）だが項は減らない", "", "F",
    "第 10 章の実験の標本", "05 §6.5；01 §3.3", [s(S_EXP, "EXP-03")], [(R + "experiments/exp03_fourier_counting.py", "main")], "—", "A", "DEC-03 で降格")
add("C-14", "claim", "EXP-04", "合計の曲線は少数のモード（POD）で表せない：32 モードでも曲線上の最大の相対誤差の 95% 点が 9.5%（最大 19.9%）", "", "F",
    "評価用の 100 シナリオ", "05 §8.8；01 §3.3", [s(S_EXP, "EXP-04")], [(R + "experiments/exp04_pod_time_curves.py", "main")], "—", "A", "DEC-04 で降格")
add("C-15", "claim", "EXP-U1", "冷媒の期末残存量：跳び形は桁落ちで相対誤差 6.1e21 まで（漏洩 0.6、130 年）、区間形は 45 点で 6.6e-15（mpmath 60 桁との比較）", "", "F",
    "交換なし・強い漏洩・長い期間で顕著。漏洩 35%・60 年の跳び形は LIMITS が 4e-6、教材の記録が 2.3e-5（食い違いは未解決）", "05 §7.5；03 §5.3；09 OQ-11・OQ-12", [s(S_LIM, "§5"), ("10_TRANSFORM_STUDY/11_UNIFIED_SYSTEM/results/expU1_b14_forms.json", "ac291dd", "rows・max"), s(S_REC, "§4")],
    [(R + "experiments/expU1_b14_forms.py", "main")], "—", "A", "DEC-09 で区間形を採用")
add("C-16", "claim", "04 §7", "マスク付き積和の表現の最小性（ステップ数・項数・因子数などの下限）について、証明された結果は原典にも本基盤にも無い。「表せた」は表現可能性の主張にすぎない", "", "記録",
    "—", "04 §7；09 OQ-20〜OQ-22", [s(S_DEC, "未決の事項"), s(S_LIM, "§7")], [], "—", "A", "")
add("C-17", "claim", "17/05 §3・21 §3.5", "節点形の最小性の主張は撤回された（未証明）。保存した係数のままの節点形は冗長を持つ", "", "記録",
    "—", "05 §9.2；01 §5；09 OQ-21", [s(S_T05, "§3"), s(S_21, "§3.5")], [], "—", "A", "C から決まる量の数は {T:17.MIN}")
add("C-18", "claim", "全章", "計算結果の一致は現実の建物の CO2 予測精度ではない。この研究の係数・数量はすべて架空で、実在の建物についての精度は一度も確かめていない", "", "記録",
    "—", "00 §5；01 §0；09 OQ-42", [s(S_21, "冒頭"), s(S_COMP, "1-B")], [], "—", "A", "")
add("C-19", "claim", "15・16・19（公開の水準）", "J-CAT 原版の変換実験：独立方程式 667 件すべてに 2 構造での書き方がある（改良方式 647、方式 A の 8 件、方式 A の 12 件。647+8+12=667）。厳密、または有限精度での正しい丸め", "", "F",
    "標本の点（全セル・境界条件・無作為ケース・連鎖）での照合。原版の式本文・値は非公開", "04 §5.6；08 §1.4・§3.9；01 §3.5〜3.9", [s(S_15R, "§1〜3"), s(S_16R, "全体"), s(S_19R, "§1")], [("15_JCAT_CONVERSION/tools/compile2.py", "（変換器）"), ("16_UNRESOLVED8_EXACT_APPROX/tools/exact8.py", "（方式 A）"), ("19_JCAT_REMAINING12/tools/exact12.py", "（方式 A）")],
    "原版が要るので本基盤では再実行していない（合成データの部分だけ RUN-12・13）", "B", "70 単位の研究とはつながっていない（統一系は原版から変換したものではない）")
add("C-20", "claim", "15/04", "667 式の照合：全セル（基本 3,796,693・改良 3,796,874）、境界条件、無作為の建物 2,000 ケース（LibreOffice で再計算した 3 者照合）、建物全体の連鎖 112,362、計 11,512,956 条件", "", "F",
    "公開の水準の件数。改良方式の境界条件 626 件・無作為の LibreOffice との 10,703 件の不一致は原典で説明された種類（ROUND の境目、意味論の違い）", "08 §3.9", [s(S_15_04, "§1〜§4"), s(S_15R, "§2")], [("15_JCAT_CONVERSION/tools/excel_ref.py", "（参照評価器）"), ("15_JCAT_CONVERSION/tools/compile2.py", "（変換器）")],
    "—", "B", "数値は 08 §3.9 と verification_counts.csv の 15 の行")
add("C-21", "claim", "19 §1・19/01", "残り 12 式はすべて方式 A で変換（除外 0）。静的な参照の範囲で 8 式は下流から参照されず、テキストを替えても 8 ulp を超えて変わる下流のセルは 0。ただし 8 式を「表示専用」とは証明していない（OFFSET の動的参照・マクロは解析外）", "", "F",
    "宣言した定義域（元のテキスト 255 文字以下など）", "01 §3.9；08 §1.5；09 OQ-39", [s(S_19R, "§1・§2・§4"), s(S_19_01, "必要性")], [("19_JCAT_REMAINING12/tools/agg12.py", "（件数）"), ("19_JCAT_REMAINING12/tools/test12.py", "（合成データ）")],
    "本基盤で合成データの部分を再実行（RUN-12：48,000 件・誤り 0・欠損 107）", "B", "")
add("C-22", "claim", "09 README", "旧研究（停止）：66 単位が 7 つの統合モデル K1〜K7 に結果を変えずにまとまり、681 シナリオ・7,406,182 値で不一致 0。近似の候補 32 は 0 採用・16 不採用・16 保留", "", "F",
    "停止した研究。本文は第 2 回の独立検査の指摘 59 件を反映していない。反例（周期 1.000000001 で B3-01 が最大 92% ずれる、NUM-2 の 212/3,461 件）がある。使う前に INDEX.md の「検証の状態」を確認", "01 §3.2；08 §3.1；09 OQ-45", [s(S_09R, "結果の要点"), s(S_ARC, "検証の状態")], [("09_APPROX_STUDY/research_code/bench/verify_unified.py", "（照合）")],
    "—", "A", "")
add("C-23", "claim", "02 §6 (b)・(c)", "本基盤の台帳の式（eval_py）を統一系・基準計算と照合：70 単位すべて、374 組・5,590,233 値で不一致 0（統一系とも基準計算とも）。T の形：区間 120 個で T 依存の直接寄与 9 単位と SUM-03 の一次性 1,200/1,200、T によらない 12 単位の不変 1,440/1,440、SUM-05 の T·値の一次性 120/120", "", "F",
    "凍結した生成器の架空のシナリオ（種 880001 の 60 件、境界条件、欠陥入り 6 件、特殊条件）。区切り点（事象の切り替え点 sw(τ)・整数年）そのもの・その直前と直後・τ と sw(τ) の間の ε の帯は (e) で調べ、帯 (K, sw(K)) の外では不一致 0（C-34）。"
    "未解決の切り替え境界：整数の時刻 K の交換の直後の帯 (K, sw(K)) だけは、統一系が台帳の式（IND・eval_py）・基準計算と異なる。(e) の帯の中の 635 点・6,555,114 値のうち 3,524 値が違い、違う単位は B1-02・B1-04 と伝播先の SUM-02〜SUM-07・X-02・X-04・X-07（各 122 点）。"
    "値の最大相対差は B1-04 で 4.2e-1、SUM-02 で 1.4e-2、SUM-03〜SUM-06・X-04・X-07 で 1.1e-2、B1-02 で 7.8e-10（SUM-07・X-02 は 02 §6 に記録なし）で、17 章 07 §6 の記録（B1-04 で最大 5.5e-3）より大きい。"
    "帯の中でも IND と基準計算は一致（不一致 0）。原因は B1-04 の区間形と B1-02 の年セルの振幅が交換の初期化を T>K で効かせること（台帳の式と基準計算は T≥sw(K)）。"
    "浮動小数の時刻が整数のすぐ近くにある事象の帯、H≥256、定義域の刃の帯は調べていない。基準計算との一致は独立の証拠ではない（実行形が基準計算の定義を書き直したもの。独立の評価は C-33）", "02 §6・§7；09 OQ-07",
    [base("02_70評価単位の完全台帳.md", "§6"), s(S_T03, "TH-2 の 3"), s(S_T07, "§6")], [(B + "tools/check_units70.py", "main・knot_check"), (R + "tstudy/unified.py", "System.at")],
    "02 §6 の命令で実行（2026-11-17、1,786 秒）。短い版は 13 §5.2 の 2", "BASE", "帯の数は c2 の照合 (e) の記録（JSON の ledger_check_summary.knots.band）")
add("C-24", "claim", "11 §2", "EX-D1：概念モデルの仕様の述語の因子は、境界 0・1・±∞・±1e-6 の許容幅と分類のラベル・印・段階名だけを使い、連続な物性の閾値も構造種別（木造・RC・S・SRC）の条件も現れない", "", "E（数え上げ）",
    "specs/ の仕様データのテンプレートを展開前に 1 回ずつ数えた（積和 1,005 段・検索 81。展開後は 1,789）", "11 §2（EX-D1）；10 HYP-D", [base("11_研究実験計画.md", "EX-D1")], [(R + "specs/", "（仕様データ。読み取りだけ）")],
    "再実行のスクリプトは 11 §2 に掲載", "BASE", "値の計算ではなく仕様データの数え上げ")
add("C-25", "claim", "14 §5", "既存の検証の再実行 RUN-01〜RUN-14（2026-11-17）：保存済みの結果と、実行時間の項目を除いて一致", "", "F／E",
    "同じコード・同じシードでの決定的な再計算。現実の精度とは無関係", "14 §5.1", [base("14_研究用データ索引.md", "§5.1")], [(R + "checks/check_unified.py", "main"), (C17 + "verify_canon.py", "main"), (C18 + "dynlca.py", "analyse"), (C20 + "run4.py", "main")],
    "—", "BASE", "RUN-14（第 22 章の検算）は有理数なので E")
add("C-26", "claim", "15 §4・§5.5", "例示の数値：平均 15 年・β_W=3.5 で F(30)=0.9996、m_F(30)=1.534。T=60 で固定周期の回数は既存の規則で 3、右連続の数え方で 4、更新過程の期待値は 3.550（「15 年ごとに集計」と「15 年ごとに交換」は別）", "", "F",
    "例示の仮定（実測ではない）", "15 §4.2・§5.5", [base("15_劣化・寿命・交換モデル研究開始資料.md", "§4.2・§5.5")], [(B + "tools/renewal_examples.py", "solve_renewal（JSON の first_vs_renewal・fixed_vs_renewal）")],
    "決定的（2 回の実行で同じ JSON）", "BASE", "")
add("C-27", "claim", "18/03・18/07 §3", "工程間の関係で時不変の畳み込みが厳密に成り立つのは比例（施設管理＝割合×買電）だけ。ゲートと状態（冷媒）は書けず、冷媒は二時刻の核が要る。年の系列への当てはめの残差もそれを示す", "", "P＋F",
    "モデルの式（P）と長さ 12 年の因果的な核の最小二乗（F。関係の有無の証明ではない）", "07 §5.5；09 OQ-29", [s(S_18_03, "全体"), s(S_18_07, "§3")], [(C18 + "dynlca.py", "deconv_residual")], "—", "A", "相関は因果の判定に使わない")
add("C-28", "claim", "18/05 §1", "施工期間の中の配分・製造の時期・更新の内訳の時期・解体と処理の期間・季節変動は 70 単位から導けない（入力にも単位の式にも無い）。仮定（変種）でだけ扱う", "", "記録",
    "—", "07 §8.1；09 OQ-26", [s(S_18_05, "§1")], [], "—", "A", "追加データが必要（09 OQ-43）")
add("C-29", "claim", "T10・PRI", "先行研究の調査は 6 観点のうち 2 観点（29 項目）だけで、新規性については何も言えない", "", "記録",
    "—", "04 §7.2；09 OQ-24", [s(S_T10, "現在の状態")], [], "—", "A", "")
add("C-30", "claim", "20/02 §3", "大規模検証の負の対照：わざと壊した式は 7 つの型で検出。NC5（B1-04 を跳び形で計算）は SUM-03 で判定するので作り方から検出力が無い", "", "S",
    "宣言した分布", "08 §3.3・§3.8", [s(S_20_02, "§3")], [(C20 + "run4.py", "negative_controls")], "—", "A", "")
add("C-31", "claim", "17/07 §1.2", "密度の振幅を fl(aH) で持つと、基準計算が厳密に 0 を返す B3 の段階値が 0 にならない（1 組、−9.8e-12）。率で持つと残差なく再現", "", "E",
    "dev_edge の 62 組のうち B3 が出る 60 組", "05 §2.2；03 §5.1", [s(S_T07, "§1.2")], [(C17 + "density_check.py", "main")], "—", "A", "")
add("C-32", "claim", "EXP-02・08 §5.3", "節点スペクトルの大きさと速さ：節点の数は規模 S で平均 4,073、M で 43,986、L で 364,029。2,033 組の評価 0.11 秒（基準計算 434 秒。係数を作る 5.1 秒は別で、同じ仕事の比較ではない）", "", "F",
    "第 10 章の実験の標本、当時の計算機", "05 §3.6；08 §5.3；09 OQ-44", [s(S_EXP, "EXP-02")], [(R + "experiments/exp02_knot_spectrum.py", "main")], "—", "A", "体系的な計算量の測定・上界は未了（OQ-44）")
add("C-33", "claim", "02 §6 (d)", "独立の評価（IND）：02 の式・条件・記号を、実行形 eval_py と基準計算を見ずに手で写した別の実装で 70 単位すべての公開出力を計算し、統一系と比べた：374 組・5,590,233 値で不一致 0。最大相対差は DIRECT・AGGREGATE で 6.3e-13、他の区分は 6.1e-15 以下", "", "F",
    "C-23 と同じ架空のシナリオと評価期間。浮動小数どうしの標本照合（相対 1e-9、基準が厳密に 0 なら 0、他は型を含めて完全一致）。LaTeX は機械的には評価しておらず、IND は手で写したもの。"
    "SYS-01〜03 の箇所の表・X-04 の行・X-05・QA-03 の使用・B4-02 の n_partial・X-02 の CHK は照合の中で統一系の仕様を読んで台帳に書き足した定義なので、それらの IND は仕様から完全には独立していない。現実の建物の予測精度ではない", "02 §6・§7",
    [base("02_70評価単位の完全台帳.md", "§6 (d)")], [(B + "tools/check_units70.py", "run・run_all"), (R + "tstudy/unified.py", "System.at")],
    "02 §6 の命令で実行（2026-11-17、1,786 秒）。短い版は 13 §5.2 の 2", "BASE", "IND が読んだ単位は台帳の依存の閉包の中（C-36）")
add("C-34", "claim", "02 §6 (e)", "節点・跳び・連続性：シナリオ 12 件（種 880201 の無作為 8 件と境界条件）の事象の切り替え点 sw(τ) 480 個（整数の時刻 255 個）と整数年 212 個で、節点そのもの・直前と直後の浮動小数・τ・τ と sw(τ) の中点の 3,036 点（帯 (K, sw(K)) の中 635 点）。"
    "帯の外の 2,401 点で IND と統一系・eval_py と統一系とも 29,118,029 値で不一致 0、IND と基準計算（帯の内外）35,673,143 値で不一致 0。跳び V(b)−V(b⁻) の IND と統一系の比較 12,791 件で不一致 0（最大の差 5.1e-16）。"
    "02 の時間の形から求めた跳びの理論値（B4-02・B5-01・B3-01・B1-03・B1-04・SUM-03、各 480 節点）2,880 件で不一致 0（6.7e-16）。跳ばないはずの単位（B1-02・B2-01・B6-03・B7-04・X-11、格子の B3-01）の連続性 3,672 件で失敗 0", "", "F",
    "SUM-08 を除く 69 単位。浮動小数の規則（ε=1e-9、sw(τ) は τ<fl(T·fl(1−ε)) となる最小の浮動小数 T）の上での標本照合で、厳密な算術の照合ではない。"
    "帯 (K, sw(K)) の中は除外：そこでは統一系が台帳の式・基準計算と異なる（3,524 値、跳びは 357 件が違う。未解決の切り替え境界で、数は C-23）。浮動小数の時刻が整数のすぐ近くにある事象の帯・H≥256・定義域の刃の帯は調べていない", "02 §6・§7；09 OQ-07",
    [base("02_70評価単位の完全台帳.md", "§6 (e)")], [(B + "tools/check_units70.py", "knot_check・predicted_jumps・sw")],
    "02 §6 の命令で実行（2026-11-17、1,786 秒）", "BASE", "")
add("C-35", "claim", "02 §6 (f)", "入力の感度：シナリオ 3 件（種 880301）で入力の項目 222 個を、値のある 1 か所ずつ型に合わせて動かし（1,145 回。統一系が評価できなかったもの 18、どの単位の出力も変えなかったもの 224）、"
    "公開出力が変わった単位 10,246 件について、その項目が宣言した入力（依存の閉包の inputs_direct・inputs_notation）と統一系の記録（inputs_reached）にあるかを調べた：宣言に無い 0 件、記録に無い 0 件", "", "F",
    "摂動は値のある所を型に合わせて動かすものだけ（⊥ にする・型を変える・非有限にする摂動は無い）。宣言したが摂動で変化を起こせなかった（単位、項目）58 組は、値の有無・0 かどうかだけを見る項目などで、読まれないことを意味しない。"
    "一度も動かさなかった項目 12。宣言に漏れが無いことの標本上の確認で、宣言が最小であることは示さない", "02 §6・§7",
    [base("02_70評価単位の完全台帳.md", "§6 (f)")], [(B + "tools/check_units70.py", "sensitivity_check・perturb")],
    "02 §6 の命令で実行（2026-11-17、1,786 秒）", "BASE", "単位ごとの入力は 02 §5 の各節の「入力」の表、data/units70_inputs.csv、JSON の inputs_direct")
add("C-36", "claim", "02 §6 (a)・(g)", "構造と整合：依存の辺 4,081/4,081 と入力の名前 212/212 が解決し、重複・循環・宣言に無い依存は 0。構成表の 22 行（21 単位）が仕様 specs/system.py の COMP_ROWS と一致。"
    "AUXILIARY の 15 単位はすべて直接寄与する単位の入力になり、REFERENCE・BREAKDOWN・DECISION の単位は C(T)（SUM-03）の依存の閉包（38 単位：DIRECT 21・AUXILIARY 15・X-02・SUM-03）に入らない。"
    "X-02 の完全性の対（CHK）が仕様の STAGE_UNITS の 27 対と一致。出力キーの集合が統一系と違う単位 0。IND が読んだ単位はすべて台帳の依存の閉包の中", "", "F",
    "構成表・CHK・閉包・依存の辺は仕様データと台帳の宣言どうしの機械的な照合（02 §6 の表では「機械的な検査」）。出力キーと IND の読み取りは C-23 の 374 組で観察したもの。値の一致の主張ではない", "02 §3・§6",
    [base("02_70評価単位の完全台帳.md", "§6 (g)")], [(B + "tools/check_units70.py", "structure_checks・consistency_checks"), (R + "specs/system.py", "COMP_ROWS・STAGE_UNITS")],
    "02 §6 の命令で実行（2026-11-17、1,786 秒）。短い版は 13 §5.2 の 2", "BASE", "")
