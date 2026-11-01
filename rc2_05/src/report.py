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
pdf.set_font('G', size=9); pdf.multi_cell(W, 5, align='L', new_x='LMARGIN', new_y='NEXT', text='提出用 RC2_05_Answer.pdf（原本の解答用紙へ記入）の別添。作成日 2026-11-01'); pdf.ln(2)

H1('0. 使用資料と確認したページ')
P('講義ノート（全31ページ）と課題・解答用紙（1ページ，横向き・/Rotate 90）をページ画像にして直接確認した。要点は以下。\n'
  '・p.13：荷重による応力（上縁圧縮・下縁引張）とプレストレスによる一様圧縮の重ね合わせ。全断面圧縮＝フル、一部引張を許容＝パーシャル。\n'
  '・p.18（表8.11）：FPC＝引張縁応力 0 以上（引張応力を認めない）、PPC＝0.49+Fc/100 以下、PRC＝ひび割れ幅で制御。\n'
  '・p.19：断面の中心に配筋した場合の FPC/PPC の応力図。\n'
  '・p.21：乾燥収縮・クリープ・リラクセーションによる PC 鋼線ひずみの減少 → 有効プレストレス。\n'
  '・p.30（設計例）：300×600，M=36 kNm，7本より線 SWPR7BL 12.7φ，中心配置（偏心なし），「有効プレストレス力は PC 鋼材の降伏荷重の0.6倍」。'
  'Z = 1.8×10^7 mm³，σmax = 2.0 N/mm²，P = A×σmax = 360 kN，Pe = P/0.6 = 600 kN，N = Pe/Fy = 600/156 = 3.846 → 4本。注記「導入したPSの60%だけ有効」。'
  '表8.15：断面積 98.7 mm²，導入緊張力 P0 124.8，許容引張荷重（定着完了時 124.8／導入時 132.6），短期許容 0.9Fy 140.4，降伏荷重 Fy 156.0，引張荷重 Fu 183.0 kN/本，Ep = 1.95×10^5 N/mm²。\n'
  '・p.31＝今回の課題（解答用紙と同一）：「設計例と同じ条件でPC鋼棒を断面内に偏心配置する場合」，e = 100 mm，σ = −M/Z + P/A + P・e/Z（圧縮を＋），空欄は P，Pe，N と応力図。')

H1('1. 記号の定義')
TABLE([['記号', '意味', '値・単位'],
       ['b, D', '断面幅・せい', '300 mm, 600 mm'],
       ['M', '設計曲げモーメント', '36 kN·m = 36×10^6 N·mm'],
       ['e', 'PC鋼材の偏心距離（図心から引張縁側＝下側へ）', '100 mm'],
       ['P', '有効プレストレス力（損失後に部材へ作用する力）', '未知数 [N]'],
       ['Pe', '必要導入張力（緊張時に与える力）。P·e（偏心モーメント）とは別物', 'Pe = P / 0.6'],
       ['N', '必要PC鋼材本数', '整数（切り上げ）'],
       ['σ', '縁応力度。圧縮を＋、引張を−', 'N/mm²']], [22, 100, 56])
P('注：講義では導入張力を Pe（添字 e）と表記する。偏心による項は「P・e/Z」と中点を入れて区別した。')

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
⑦ 必要本数      N = Pe / Fy = 300 / 156  （Fy：降伏荷重 156 kN/本，表8.15）
                 = Pe / 156 = 300 / 156 = {R["N_exact"]:.3f}  →  切り上げて N = {int(R["N"])} 本''')

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
       ['引張荷重183 kNで割った場合', '300/183 = 1.64', f'→ {R["N_if_183"]} 本（結論同じ）'],
       ['p.30設計例との整合', '中心配置 P=360, Pe=600, N=3.85→4 に対し、e=Z/A の偏心で P/A と P・e/Z が等しく P は半分', 'P=180, Pe=300, N=1.92→2（整合）'],
       ['「降伏荷重の0.6倍」の別解釈', '1本の有効力 0.6×156=93.6 kN，N=P/93.6=180/93.6', '1.92 → 2本（同じ）']], [44, 80, 54])
P('偏心 e = 100 mm がちょうど核の端（Z/A = 100 mm）なので、プレストレスのみが作用する状態で上縁応力が 0 となり、上縁に引張が生じない合理的な配置であることも確認した。')

H1('4. 12.7φ PC鋼材と 156 kN の意味（外部資料）')
P('講義ノート表8.15（p.30）は 12.7φ SWPR7BL の降伏荷重 Fy = 156.0 kN、引張荷重 Fu = 183.0 kN としている。外部資料でも同じ値を確認した。JIS G 3536 の PC鋼より線 SWPR7BL（7本より線 B種）12.7 mm の規格値は、公称断面積 98.71 mm²、単位質量 774 kg/km、'
  '0.2％永久伸びに対する試験力（＝降伏荷重相当）≧156 kN、最大試験力（＝引張荷重）≧183 kN、伸び≧3.5％（住友電工 Bare strand カタログの JIS G3536 SWPR7L 行で確認）。'
  'したがって講義資料の 156 kN は「降伏荷重（0.2％耐力相当の荷重）」であり、引張荷重 183 kN ではない。')
P('・鋼材の表記：解答用紙は「PC鋼棒」と書いているが、「設計例と同じ条件」とあり、設計例は7本より線 SWPR7BL 12.7φ（156 kN）である。12.7 mm は PC鋼棒（JIS G 3109）の呼び径系列にない、より線の公称径なので、PC鋼より線 SWPR7BL として計算した。\n'
  '・講義資料との相違：実務の設計では、緊張・定着時の鋼材引張力を降伏荷重や引張荷重に低減係数を掛けた許容値（例：0.8Pu と 0.9Py のうち小さい方）以下とするのが一般的である。'
  '仮に 0.9×156 = 140.4 kN/本とすると 300/140.4 = 2.14 → 3本となる。講義の表8.15の許容引張荷重（導入時 132.6，定着完了時 124.8 kN/本）を使うと 300/132.6 = 2.26，300/124.8 = 2.40 でいずれも3本になる。本課題は設計例（p.30）と同じく Fy = 156 kN で割る方法を優先して N = 2 本とした。'
  '（この許容値の係数は一般的な取扱いとして記載したもので、日本建築学会規準の原文では未確認。）\n'
  '・有効率：実際のプレストレス損失（弾性短縮、摩擦、セット、クリープ、乾燥収縮、リラクセーション）を考えた有効率は一般に約0.8～0.85程度とされることが多いが、課題は 0.6（損失40％）と安全側で単純化した値を指定しているので、それに従った。\n'
  '・「有効PS力はPC鋼材の降伏荷重の0.6倍」の意味：設計例は Pe = P/0.6，N = Pe/Fy と計算しており、これは「導入張力（=N×Fy）の60%が有効」と同じ。1本あたり有効力 0.6×156 = 93.6 kN で P を割っても N は同じになる。')

H1('5. 判断に迷った点とその根拠')
P('(1) 有効率の基準：解答用紙は「降伏荷重の0.6倍」、依頼文は「導入張力の60％」。設計例の計算（Pe = P/0.6，N = Pe/156）に従えば両者は同じ結果になる。\n'
  '(2) 偏心の向き：図で PC鋼材は図心より下（引張縁側）にあり、P・e/Z は引張縁で圧縮(+)。解答用紙の式の符号と一致する。\n'
  '(3) 自重：設計例と同様、M = 36 kNm を設計用曲げモーメントとして扱い、別途加算しなかった。\n'
  '(4) PC鋼棒／より線：上記4.のとおり、設計例と同じ SWPR7BL 12.7φ とした。\n'
  '(5) 本数の切り上げ：1.92 → 2本。2本の場合の有効力 2×156×0.6 = 187.2 kN ≧ 180 kN。\n'
  '(6) 記入の方法：原本は /Rotate 90 の横向きページ。画面座標で配置し、回転行列で PDF 座標へ変換して記入した。原本の文字・図・色・罫線は一切変更していない。')

H1('6. 自動検査の結果（src/check_original.py：原本との比較を含む）')
MONO('\n'.join(CHK))
P('レンダリング画像も目視で確認し、初版で見つけた不具合（P の解答枠が「=」に重なる、注記が小さすぎる、記入の外接矩形が原本ラベルに接する）を修正して再生成した。')

H1('7. 参考資料')
P('・講義ノート「05_PC構造や壁式RC構造の基本（一級建築士試験対応含む）」p.13, 18, 19, 21, 30（表8.15）, 31\n'
  '・課題「05_課題＋解答用紙.pdf」\n'
  '・住友電気工業 PC鋼より線（Bare strand）カタログ：https://global-sei.com/steel-wire/download/pdf/Bare_strand_r1.pdf\n'
  '・東京製綱 総合カタログ（JIS G 3536 SWPR7BL の規格表）：https://tokyorope.co.jp/product/catalog/pdf/general_catalog_12.pdf\n'
  '・日本製鉄 建設用資材ハンドブック（JIS G 3536-2014 より線）：https://www-zam.nipponsteel.com/product/construction/handbook/pdf/9-5.pdf\n'
  '・JIS G 3536 PC鋼線及びPC鋼より線／JIS G 3109 PC鋼棒（日本規格協会）\n'
  '・日本建築学会「プレストレストコンクリート設計施工規準・同解説」（原文は未参照）')

H1('8. 使用したライブラリ（GitHub）とその用途')
TABLE([['ライブラリ', '用途', 'ライセンス'],
       ['PyMuPDF  github.com/pymupdf/PyMuPDF', '原本の文字位置と回転の解析、原本への記入、レンダリング、原本との画素比較', 'AGPL-3.0'],
       ['SymPy  github.com/sympy/sympy', 'Pの記号的求解と再代入検算（有理数で厳密計算）', 'BSD-3'],
       ['fpdf2  github.com/py-pdf/fpdf2', '本検証資料の作成（日本語フォント埋め込み）', 'LGPL-3.0'],
       ['pdfplumber  github.com/jsvine/pdfplumber', '導入済みだが、文字位置の取得は PyMuPDF の get_text("dict") で足りたため未使用', 'MIT'],
       ['NumPy', '原本と完成PDFの画素差分の計算', 'BSD-3']], [62, 90, 26])
P('構造計算専用のライブラリは、本課題の計算規模（1式1未知数）では不要と判断し、SymPyと手順の異なる3つの別解で独立に検証した。')

pdf.add_page()
H1('付録：提出用解答用紙のレンダリング画像')
pdf.image(os.path.join(OUT, 'RC2_05_Answer_preview.png'), x=16, w=178)
pdf.output(sys.argv[1] if len(sys.argv) > 1 else os.path.join(OUT, 'RC2_05_Verification.pdf'))
