#!/usr/bin/env python3
"""研究書（PDF・Word）の組版ツール。

使い方:  python3 tools/build_books.py [book_id ...]   （省略時は全冊）
出力:    dist/books/<ファイル名>.pdf / .docx
仕組み:  Markdown原稿を結合 → pandocでHTML → tools/book_print.js（Chromium）で
         Mermaid描画・図表番号・目次・索引・しおり付きPDFを2パスで生成 → 図をPNG化してWordにも埋め込む。
"""
import csv, datetime, json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = os.path.join(ROOT, "research")
FM = os.path.join(R, "00_前付・後付")
BUILD = os.path.join(ROOT, "build")
OUT = os.path.join(ROOT, "dist", "books")
BASE_DATE = "2026年11月1日"
ORG = "日本電力産業総合戦略研究プロジェクト"

def p(*a): return os.path.join(R, *a)

CH = {
 "01": p("01_総合研究報告書", "01_総合研究報告書.md"),
 "02": p("02_歴史・政策研究", "02_歴史・政策研究.md"),
 "03": p("03_産業構造・技術・経済研究", "03_産業構造・技術・経済研究.md"),
 "04": p("04_主要企業個別分析", "04_主要企業比較研究_第2版.md"),
 "05": p("05_東京電力グループ詳細研究", "05_東京電力グループ詳細研究.md"),
 "06": p("06_将来シナリオ分析", "06_将来シナリオ分析.md"),
 "07": p("07_建築設備の戦略的位置づけ", "07_建築設備の戦略的位置づけ_第2版_再検証.md"),
 "07v1": p("07_建築設備の戦略的位置づけ", "07_建築設備の戦略的位置づけ.md"),
 "08": p("08_因果関係図・企業関係図", "08_図表集.md"),
 "09": p("09_資料台帳・証拠管理", "SOURCES.md"),
 "10": p("10_未解決論点・追加調査", "10_未解決論点・追加調査.md"),
 "11": p("11_組織・職種研究", "11_組織・職種と意思決定の追跡.md"),
 "12": p("12_産業因果モデル", "12_産業因果モデル.md"),
 "13": p("13_意思決定の逆算", "13_企業意思決定の逆算.md"),
 "14": p("14_海外比較", "14_米国・欧州・中国との比較.md"),
 "15": p("15_検証可能な予測", "15_シナリオ指標とバックテスト.md"),
 "16": p("16_反証と品質管理", "16_第2版結論の再検証.md"),
 "17": p("17_東電の人材需要", "17_東電の人材需要の構造分析.md"),
 "18": p("18_日本大学・井口研究室", "18_日本大学理工学部建築学科と井口研究室.md"),
 "19": p("19_東電の新卒採用構造", "19_東京電力の新卒採用構造.md"),
 "20": p("20_適合性分析", "20_井口研究室の学生と東電の適合性.md"),
 "21": p("21_採用行動研究", "21_行動・選考モデル・時間配分・競合仮説.md"),
 "22": p("22_最終章", "22_井口研究室の学生の最適行動戦略.md"),
}

BOOKS = {
 "industry": dict(file="01_日本電力産業総合戦略研究書", title="日本電力産業総合戦略研究書",
   subtitle="歴史・制度・地政学・技術・資本・組織の相互作用と2030〜2050年の展望", es="ES_産業.md",
   parts=[("第I部 総論と歴史・制度", ["01", "02"]), ("第II部 産業構造・企業・意思決定", ["03", "04", "11", "13"]),
          ("第III部 因果・海外比較・将来", ["12", "14", "06", "15"]), ("第IV部 品質管理と図表", ["16", "08", "10"])]),
 "tepco": dict(file="02_東京電力グループ特別研究報告書", title="東京電力グループ特別研究報告書",
   subtitle="国家関与の下の経営・財務・組織・人材需要・採用構造", es="ES_東電.md",
   parts=[("第I部 経営と財務", ["05"]), ("第II部 組織・職種・人材需要", ["11", "17"]), ("第III部 採用構造", ["19"])]),
 "arch": dict(file="03_建築・建築設備技術者研究報告書", title="建築・建築設備技術者研究報告書",
   subtitle="電力会社における建築・建築設備の役割と、技術の重要性・職種の担当の分離検証", es="ES_建築.md",
   parts=[("第I部 位置づけの導出と再検証", ["07"]), ("第II部 組織と人材需要", ["11", "17"]), ("付録 第1版の判断の記録", ["07v1"])]),
 "fit": dict(file="04_日本大学理工学部井口研究室と東京電力採用の適合性研究", title="日本大学理工学部・井口研究室と東京電力採用の適合性研究",
   subtitle="教育・研究内容と東京電力の建築系業務・採用構造との照合", es="ES_適合性.md",
   parts=[("第I部 大学・研究室", ["18"]), ("第II部 採用構造と適合性", ["19", "20"])]),
 "strategy": dict(file="05_東京電力建築系採用の最適行動戦略報告書", title="東京電力建築系採用の最適行動戦略報告書",
   subtitle="井口研究室の学生を対象とした、根拠に基づく行動・時期・順序の導出", es="ES_戦略.md",
   parts=[("第I部 行動・選考モデル・競合仮説", ["21"]), ("第II部 最終章", ["22"])]),
 "complete": dict(file="00_完全版_日本電力産業総合戦略研究", title="日本電力産業総合戦略研究【完全版】",
   subtitle="電力産業・東京電力・建築設備・大学研究室・採用戦略の統合研究", es="ES_産業.md",
   parts=[("第I部 日本・世界の電力産業", ["01", "02", "03", "04", "12", "13", "14", "06", "15", "16", "08"]),
          ("第II部 東京電力グループ", ["05", "11", "17"]), ("第III部 建築・建築設備", ["07"]),
          ("第IV部 大学・研究室", ["18"]), ("第V部 採用構造・適合性・行動", ["19", "20", "21"]),
          ("最終章", ["22"]), ("付録", ["10", "09"])], extra_es=["ES_東電.md", "ES_建築.md", "ES_適合性.md", "ES_戦略.md"]),
}

PB_HTML = '\n\n<div class="pb"></div>\n\n'
PB_DOCX = '\n\n```{=openxml}\n<w:p><w:r><w:br w:type="page"/></w:r></w:p>\n```\n\n'

def read(path):
    t = open(path, encoding="utf-8").read()
    # 表・リストの直前に空行がない場合、pandocが表として解釈しないため空行を補う
    out, prev = [], ""
    for line in t.splitlines():
        if line.startswith("|") and prev.strip() and not prev.startswith("|"):
            out.append("")
        out.append(line); prev = line
    t = "\n".join(out) + "\n"
    # Mermaid内の出典表記 [S001,S030] [分] などは角括弧の入れ子になり構文エラーになるため全角括弧に置換
    def fix_mer(m):
        code = re.sub(r"\[((?:S\d{3}[^\[\]]*)|分|仮|予|確認事実)\]", r"（\1）", m.group(0))
        return code
    return re.sub(r"```mermaid\n.*?```", fix_mer, t, flags=re.S)

def references_md():
    rows = list(csv.DictReader(open(p("09_資料台帳・証拠管理", "source_registry.csv"), encoding="utf-8")))
    out = ["# 参考文献（一次資料台帳より自動生成）", "",
           "確認日はすべて情報基準日（2026年11月1日）。C番号（検索要約経由の資料）は「資料台帳・証拠管理」の章を参照。", "",
           "| ID | 発行主体 | 資料名 | 発行 | URL | 状態 |", "|---|---|---|---|---|---|"]
    for r in rows:
        url = r["url"].split(" ")[0]
        out.append(f"| {r['id']} | {r['publisher']} | {r['title']} | {r['pub_date']} | {url} | {r['status']} |")
    return "\n".join(out) + "\n"

def glossary_terms():
    terms = []
    for line in read(os.path.join(FM, "用語集.md")).splitlines():
        m = re.match(r"\|\s*([^|]+?)\s*\|", line)
        if m and m.group(1) not in ("用語", "---"):
            for t in re.split(r"[・（）()]", m.group(1)):
                t = t.strip()
                if len(t) >= 2 and t not in ("双方向",): terms.append(t)
    extra = ["東京電力", "JERA", "関西電力", "中部電力", "東北電力", "九州電力", "北海道電力", "J-POWER", "東京ガス", "大阪ガス", "INPEX",
             "柏崎刈羽", "福島第一", "東通", "浜岡", "大間", "女川", "泊", "美浜", "第五次総特", "第四次総特", "エネルギー基本計画",
             "中東危機", "ホルムズ", "データセンター", "廃炉", "建築部門", "建築設備", "保全業務", "井口研究室", "日本大学", "インターンシップ",
             "エントリーシート", "適性検査", "面接", "大学院", "中途採用", "原子力規制委員会", "電力広域的運営推進機関", "レベニューキャップ"]
    seen, out = set(), []
    for t in terms + extra:
        if t not in seen: seen.add(t); out.append(t)
    return out

def assemble(book, mode):
    pb = PB_HTML if mode == "html" else PB_DOCX
    b = BOOKS[book]
    parts = []
    es = [b["es"]] + b.get("extra_es", [])
    for e in es:
        t = read(os.path.join(FM, e))
        if len(es) > 1 and e != es[0]:
            t = t.replace("# Executive Summary", "## Executive Summary（" + {"ES_東電.md": "東京電力グループ", "ES_建築.md": "建築・建築設備", "ES_適合性.md": "大学・研究室の適合性", "ES_戦略.md": "採用の最適行動戦略"}[e] + "）", 1)
        parts.append(t)
    parts.append(pb + ("<div id=\"toc-anchor\"></div>" if mode == "html" else ""))
    for title, chs in b["parts"]:
        parts.append(pb + f"# {title}" + (" {.part}" if mode == "html" else "") + "\n")
        for c in chs:
            parts.append(pb + read(CH[c]))
    parts.append(pb + references_md())
    parts.append(pb + read(os.path.join(FM, "用語集.md")))
    if mode == "html":
        parts.append(pb + '# 索引 {#index-section}\n\n<div id="index-anchor"></div>\n')
    return "\n\n".join(parts)

def cover_html(b, version):
    return f"""<section class="cover">
<div class="cover-org">{ORG}</div>
<div class="cover-title">{b['title']}</div>
<div class="cover-sub">{b['subtitle']}</div>
<div class="cover-meta">情報基準日：{BASE_DATE}<br/>版：{version}<br/>生成日：{datetime.date.today().isoformat()}</div>
<div class="cover-note">本書は公開情報に基づく研究報告書である。特定の個人の成績・応募情報・非公開データは含まない。<br/>
証拠の水準：【確認事実】【当事者の主張】【分析】【仮説】【予測】【不明】。資料番号 S＝一次資料、C＝検索要約経由。<br/>
実行時点との差：情報基準日以降に公表された資料は反映していない。採用日程・制度は年度ごとに公式情報で確認すること。</div>
</section><div class="pb"></div>"""

def main():
    books = sys.argv[1:] or list(BOOKS)
    os.makedirs(BUILD, exist_ok=True); os.makedirs(OUT, exist_ok=True)
    version = "最終統合版（第4版）"
    terms = glossary_terms()
    for bk in books:
        b = BOOKS[bk]
        md_html = assemble(bk, "html")
        src = os.path.join(BUILD, f"{bk}.md"); open(src, "w", encoding="utf-8").write(md_html)
        frag = subprocess.run(["pandoc", src, "-f", "markdown+pipe_tables+raw_html-yaml_metadata_block", "-t", "html5"],
                              capture_output=True, text=True, check=True).stdout
        frag = re.sub(r'<pre class="mermaid"><code>(.*?)</code></pre>', lambda m: '<div class="mermaid">' + m.group(1) + '</div>', frag, flags=re.S)
        html = open(os.path.join(ROOT, "tools", "book_template.html"), encoding="utf-8").read()
        html = html.replace("{{TITLE}}", b["title"]).replace("{{COVER}}", cover_html(b, version)).replace("{{BODY}}", frag)
        hp = os.path.join(BUILD, f"{bk}.html"); open(hp, "w", encoding="utf-8").write(html)
        figdir = os.path.join(BUILD, "fig", bk); os.makedirs(figdir, exist_ok=True)
        pdf = os.path.join(OUT, b["file"] + ".pdf")
        cfg = dict(html=hp, pdf=pdf, figdir=figdir, title=b["title"], terms=terms)
        cp = os.path.join(BUILD, f"{bk}.json"); json.dump(cfg, open(cp, "w", encoding="utf-8"), ensure_ascii=False)
        subprocess.run(["node", os.path.join(ROOT, "tools", "book_print.js"), cp], check=True)
        # Word：Mermaid図を描画済みPNGに置換
        md_docx = assemble(bk, "docx")
        figs = sorted(f for f in os.listdir(figdir) if f.endswith(".png"))
        it = iter(figs)
        def repl(m):
            f = next(it, None)
            return f"![図]({os.path.join(figdir, f)})" if f else m.group(0)
        md_docx = re.sub(r"```mermaid\n.*?```", repl, md_docx, flags=re.S)
        cover_md = f"# {b['title']}\n\n**{b['subtitle']}**\n\n{ORG}\n\n情報基準日：{BASE_DATE}　版：{version}\n\n本書は公開情報に基づく研究報告書であり、特定の個人の情報は含まない。\n"
        dsrc = os.path.join(BUILD, f"{bk}_docx.md"); open(dsrc, "w", encoding="utf-8").write(cover_md + PB_DOCX + md_docx)
        subprocess.run(["pandoc", dsrc, "-f", "markdown+pipe_tables+raw_attribute-yaml_metadata_block", "-o", os.path.join(OUT, b["file"] + ".docx"),
                        "--toc", "--toc-depth=2", "--metadata", f"title={b['title']}", "--resource-path", BUILD], check=True)
        print("built", b["file"])

if __name__ == "__main__":
    main()
