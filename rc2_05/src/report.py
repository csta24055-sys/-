"""詳細検証資料 RC2_05_Verification.pdf の作成（fpdf2 + IPAゴシック）."""
import json, os, sys
from fpdf import FPDF, FontFace
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, '..', 'out')
R = json.load(open(os.path.join(OUT, 'calc.json')))
CHK = open(os.path.join(OUT, 'check_answer.txt')).read().strip().splitlines()

pdf = FPDF(format='A4'); pdf.set_auto_page_break(True, 15)
pdf.add_font('G', '', '/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf')
pdf.set_margins(16, 15, 16)
W = 210 - 32

def H1(t): pdf.ln(2); pdf.set_font('G', size=12.5); pdf.set_text_color(20, 40, 120); pdf.multi_cell(W, 7, t, align='L', new_x='LMARGIN', new_y='NEXT'); pdf.set_text_color(0); pdf.ln(1)
def P(t, s=9.5): pdf.set_font('G', size=s); pdf.multi_cell(W, 5.4, t, align='L', new_x='LMARGIN', new_y='NEXT', wrapmode='CHAR'); pdf.ln(0.8)
def MONO(t): pdf.set_font('G', size=9.2); pdf.set_fill_color(242, 244, 248); pdf.multi_cell(W, 5.2, t, fill=True, align='L', new_x='LMARGIN', new_y='NEXT'); pdf.ln(1.2)
def TABLE(rows, widths):
    pdf.set_font('G', size=8.6)
    with pdf.table(col_widths=widths, width=W, line_height=5.0, text_align='LEFT',
                   headings_style=FontFace(fill_color=(225, 230, 242)), first_row_as_headings=True) as t:
        for r in rows:
            row = t.row()
            for c in r: row.cell(c)
    pdf.ln(2)

pdf.add_page()
pdf.set_font('G', size=15); pdf.multi_cell(W, 8, align='L', new_x='LMARGIN', new_y='NEXT', text='鉄筋コンクリート構造Ⅱ 第5回演習課題\n詳細検証資料（計算過程・検算・根拠）')
pdf.set_font('G', size=9); pdf.multi_cell(W, 5, align='L', new_x='LMARGIN', new_y='NEXT', text='提出用解答用紙 RC2_05_Answer.pdf の別添。作成日 2026-11-01'); pdf.ln(2)

H1('0. 資料の入手状況（重要な制約）')
P('指示にある添付PDF（05_PC構造や壁式RC構造の基本_講義ノート.pdf，05_課題＋解答用紙.pdf）は、この作業環境（リポジトリの全ブランチ、Dropbox、Box）では見つからなかった。'
  'このため講義ノート13・18・19・21・30・31ページの図表は直接確認できていない。計算は、指示文に明記された条件・式（σ = −M/Z + P/A + P·e/Z，圧縮正，引張縁0，有効率60％，12.7φ＝156 kN/本）に厳密に従って行った。'
  '提出用PDFは課題条件から作成した1ページの解答用紙であり、原本を入手したら同梱スクリプト（src/sheet.py fill）で原本の解答欄へ同じ解答を書き込める。')

H1('1. 記号の定義')
TABLE([['記号', '意味', '値・単位'],
       ['b, D', '断面幅・せい', '300 mm, 600 mm'],
       ['M', '設計曲げモーメント', '36 kN·m = 36×10^6 N·mm'],
       ['e', 'PC鋼材の偏心距離（図心から引張縁側＝下側へ）', '100 mm'],
       ['P', '有効プレストレス力（損失後に部材へ作用する力）', '未知数 [N]'],
       ['Pe', '必要導入張力（緊張時に与える力）。P·e（偏心モーメント）とは別物', 'Pe = P / 0.6'],
       ['N', '必要PC鋼材本数', '整数（切り上げ）'],
       ['σ', '縁応力度。圧縮を＋、引張を−', 'N/mm²']], [22, 100, 56])
P('注：課題が「導入張力」を Pe と表記しているため、偏心による項は必ず「P·e/Z」と中点を入れて区別した。')

H1('2. 計算過程')
MONO(f'''① 断面積     A = b·D = 300 × 600 = {R["A"]:,} mm²  (=1.8×10^5 mm²)
② 断面係数   Z = b·D²/6 = 300 × 600² / 6 = {R["Z"]:,} mm³  (=1.8×10^7 mm³)
③ 曲げ応力度 M/Z = 36×10^6 N·mm / 1.8×10^7 mm³ = {R["M_over_Z"]:.1f} N/mm²
              （正曲げにより下縁＝引張縁で −2.0、上縁で +2.0）
④ プレストレスによる応力度（下縁、圧縮正）
     σ_下 = −M/Z + P/A + P·e/Z
     P/A   = P / 180,000            [N/mm²]
     P·e/Z = P × 100 / 18,000,000 = P / 180,000   [N/mm²]
     → 偏心 e = Z/A = 100 mm（断面の核の下端）なので P/A と P·e/Z は等しい
⑤ FPC条件 σ_下 = 0：
     −2.0 + P/180,000 + P/180,000 = 0
     2P/180,000 = 2.0  →  P = 180,000 N = {R["P_kN"]:.0f} kN
     （P/A = {R["P_over_A"]:.1f} N/mm²，P·e/Z = {R["PeZ"]:.1f} N/mm²）
⑥ 必要導入張力  P = 0.6·Pe  →  Pe = 180 / 0.6 = {R["Pe_kN"]:.0f} kN
⑦ 必要本数      N = Pe / 156 = 300 / 156 = {R["N_exact"]:.3f}  →  切り上げて N = {int(R["N"])} 本''')

H1('3. 検算')
TABLE([['項目', '方法', '結果'],
       ['SymPy求解', 'sympy.solve(Eq(σ_下, 0), P)', f'P = {R["P_N"]:,} N（唯一解）'],
       ['再代入', 'σ_下(P=180,000) を再計算', f'{R["sig_bot_check"]:.3g} N/mm²（=0）'],
       ['別解1（mm系）', 'P = (M/Z)/(1/A + e/Z)', f'{R["crosscheck"]["P_route_mm"]:,.0f} N'],
       ['別解2（kN·m系）', 'A=0.18 m², Z=0.018 m³, e=0.1 m', f'{R["crosscheck"]["P_route_kNm_kN"]:.1f} kN'],
       ['別解3（核）', 'e=Z/A より 2P/A = M/Z', f'{R["crosscheck"]["P_route_kern"]:,.0f} N'],
       ['単位', '36 kN·m = 36×10^6 N·mm；N/mm² = MPa', '整合'],
       ['符号', '偏心が下側→P·e/Zは下縁で圧縮(+)、上縁で引張(−)', '整合'],
       ['上縁（使用時）', '+M/Z + P/A − P·e/Z', f'+{R["sig_top_service"]:.1f} N/mm²（圧縮）'],
       ['導入直後（Pe作用・M無視）', '上縁 Pe/A − Pe·e/Z ／ 下縁 Pe/A + Pe·e/Z',
        f'上縁 {R["sig_top_transfer"]:.1f}，下縁 +{R["sig_bot_transfer"]:.2f} N/mm²'],
       ['有効力と導入張力', 'P(180) < Pe(300)、P = 0.6 Pe', '区別して使用'],
       ['切り上げ', '1.92 → 2（1本では156 kN < 300 kN）', 'N = 2 本'],
       ['配置本数での確認', f'2本×156 = {R["provided_Pe_kN"]} kN, 有効 {R["provided_P_kN"]:.1f} kN',
        f'下縁 +{R["sig_bot_provided"]:.2f} N/mm² ≧ 0 OK'],
       ['引張荷重183 kNで割った場合', '300/183 = 1.64', f'→ {R["N_if_183"]} 本（結論同じ）']], [44, 80, 54])
P('偏心 e = 100 mm がちょうど核の端（Z/A = 100 mm）なので、プレストレスのみが作用する状態で上縁応力が 0 となり、上縁に引張が生じない合理的な配置であることも確認した。')

H1('4. 12.7φ PC鋼材と 156 kN の意味（外部資料）')
P('JIS G 3536 の PC鋼より線 SWPR7BL（7本より線 B種）12.7 mm の規格値は、公称断面積 98.71 mm²、単位質量 774 kg/km、'
  '0.2％永久伸びに対する試験力（＝降伏荷重相当）≧156 kN、最大試験力（＝引張荷重）≧183 kN、伸び≧3.5％（住友電工 Bare strand カタログの JIS G3536 SWPR7L 行で確認）。'
  'したがって講義資料の 156 kN は「降伏荷重（0.2％耐力相当の荷重）」であり、引張荷重 183 kN ではない。')
P('・12.7 mm は7本より線の公称径である。PC鋼棒（JIS G 3109）の呼び径の系列に 12.7 mm はないので、「12.7φ」はPC鋼より線（SWPR7BL）を指すと判断した。\n'
  '・講義資料との相違：実務の設計では、緊張・定着時の鋼材引張力を降伏荷重や引張荷重に低減係数を掛けた許容値（例：0.8Pu と 0.9Py のうち小さい方）以下とするのが一般的である。'
  '仮に 0.9×156 = 140.4 kN/本とすると 300/140.4 = 2.14 → 3本となる。本課題は講義の指定（1本あたり156 kN）を優先して N = 2 本とした。'
  '（この許容値の係数は一般的な取扱いとして記載したもので、日本建築学会規準の原文では未確認。）\n'
  '・有効率：実際のプレストレス損失（弾性短縮、摩擦、セット、クリープ、乾燥収縮、リラクセーション）を考えた有効率は一般に約0.8～0.85程度とされることが多いが、課題は 0.6（損失40％）と安全側で単純化した値を指定しているので、それに従った。')

H1('5. 判断に迷った点とその根拠')
P('(1) Pe の記号：課題が導入張力を Pe と呼ぶため、偏心モーメント項は P·e と書いて区別した。\n'
  '(2) 偏心の向き：FPCで引張縁の引張を打ち消す目的から、PC鋼材は図心より引張縁側（下側）にあるとした。このとき P·e/Z は引張縁で圧縮(+)となり、指示式の符号と一致する。\n'
  '(3) 自重：課題の M = 36 kN·m を設計曲げモーメント（自重を含む）として扱い、別途加算しなかった。\n'
  '(4) 圧縮縁の許容応力度：コンクリート強度が与えられていないので照査対象外とした（参考：上縁 +2.0 N/mm²、導入時下縁 +3.33 N/mm² と小さい）。\n'
  '(5) 30ページの設計例との整合：原本を入手できず数値比較は未実施。計算の流れ（A・Z → M/Z → FPC条件でP → P/有効率でPe → Pe/156でN）は指示文の手順と一致する。')

H1('6. 自動検査の結果（src/check.py による提出用PDFの検査）')
MONO('\n'.join(CHK))
P('別途、模擬原本PDFに src/sheet.py fill で記入するテストを行い、記入欄外の原本画素の変化 0 px・原本の線や文字の被覆 0 px を確認した。')

H1('7. 参考資料')
P('・住友電気工業 PC鋼より線（Bare strand）カタログ：https://global-sei.com/steel-wire/download/pdf/Bare_strand_r1.pdf\n'
  '・東京製綱 総合カタログ（JIS G 3536 SWPR7BL の規格表）：https://tokyorope.co.jp/product/catalog/pdf/general_catalog_12.pdf\n'
  '・日本製鉄 建設用資材ハンドブック（JIS G 3536-2014 より線）：https://www-zam.nipponsteel.com/product/construction/handbook/pdf/9-5.pdf\n'
  '・JIS G 3536 PC鋼線及びPC鋼より線／JIS G 3109 PC鋼棒（日本規格協会）\n'
  '・日本建築学会「プレストレストコンクリート設計施工規準・同解説」（原文は未参照）')

H1('8. 使用したライブラリ（GitHub）とその用途')
TABLE([['ライブラリ', '用途', 'ライセンス'],
       ['PyMuPDF  github.com/pymupdf/PyMuPDF', '解答用紙の作成・原本への記入・空白領域検出のためのレンダリング・画素比較', 'AGPL-3.0'],
       ['SymPy  github.com/sympy/sympy', 'Pの記号的求解と再代入検算（有理数で厳密計算）', 'BSD-3'],
       ['fpdf2  github.com/py-pdf/fpdf2', '本検証資料の作成（日本語フォント埋め込み）', 'LGPL-3.0'],
       ['pdfplumber  github.com/jsvine/pdfplumber', '環境に導入済み。原本の文字位置取得に使う予定だったが、原本未入手のため未使用', 'MIT'],
       ['NumPy', '空白矩形探索（最大長方形アルゴリズム）と画素比較', 'BSD-3']], [62, 90, 26])
P('構造計算専用のライブラリは、本課題の計算規模（1式1未知数）では不要と判断し、SymPyと手順の異なる3つの別解で独立に検証した。')

pdf.add_page()
H1('付録：提出用解答用紙のレンダリング画像')
pdf.image(os.path.join(OUT, 'RC2_05_Answer_preview.png'), x=22, w=166)
pdf.output(sys.argv[1] if len(sys.argv) > 1 else os.path.join(OUT, 'RC2_05_Verification.pdf'))
