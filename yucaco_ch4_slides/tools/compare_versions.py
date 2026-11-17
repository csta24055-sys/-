"""旧版・新版（v1）・改善版（v2）を並べた比較画像と、文字の大きさの比較表を作る。

  python3 tools/compare_versions.py <旧版のPDF> [出力フォルダ]

- 比較画像：output/compare/p01.jpg … p38.jpg（左から 旧版｜新版 v1｜改善版 v2）
- 文字の比較：output/compare/text_metrics.csv と text_metrics.md
  各ページについて、PDF に埋め込まれた文字の大きさ（1920px 幅に換算）から
    本文の最小サイズ（フッター・写真クレジットを除く）
    見出し以外でいちばん大きい文字（そのページの主役の数字・結論）
    文字数
  を取り出す。見た目の印象ではなく、同じ物差しで 3 つの版を比べるためのもの。

旧版の PDF は発表者の手元の資料なので、リポジトリには入れていない（引数で渡す）。
必要なもの：poppler-utils（pdftoppm）、pdfplumber、Pillow
"""
import csv
import pathlib
import subprocess
import sys
import tempfile

import pdfplumber
from PIL import Image, ImageDraw, ImageFont

root = pathlib.Path(__file__).resolve().parent.parent
old_pdf = pathlib.Path(sys.argv[1])
out_dir = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else root / "output" / "compare"
out_dir.mkdir(parents=True, exist_ok=True)

versions = [
    ("旧版", old_pdf),
    ("新版（v1）", root / "output" / "yucaco_ch4_performance_customer.pdf"),
    ("改善版（v2）", root / "output" / "yucaco_ch4_performance_customer_v2.pdf"),
]

# ---------------------------------------------------------------- 比較画像
W, H, PAD, HEAD = 960, 540, 12, 44
font = ImageFont.truetype(str(root / "src" / "assets" / "fonts" / "DeckSans-700.ttf"), 24)
with tempfile.TemporaryDirectory() as tmp:
    pages = []
    for i, (_, pdf) in enumerate(versions):
        prefix = f"{tmp}/v{i}"
        subprocess.run(["pdftoppm", "-r", "72", "-png", str(pdf), prefix], check=True)
        pages.append(sorted(pathlib.Path(tmp).glob(f"v{i}-*.png")))
    n = min(len(p) for p in pages)
    for k in range(n):
        sheet = Image.new("RGB", (W * 3 + PAD * 4, H + HEAD + PAD), (58, 64, 74))
        draw = ImageDraw.Draw(sheet)
        for i, (name, _) in enumerate(versions):
            x = PAD + i * (W + PAD)
            # v2 に無い文字を避けるため、ラベルは英数字と同梱フォントにある文字だけにする
            label = ["OLD", "V1", "V2"][i] + f"   p.{k + 1}"
            draw.text((x, 8), label, font=font, fill=(255, 255, 255))
            im = Image.open(pages[i][k]).convert("RGB").resize((W, H), Image.LANCZOS)
            sheet.paste(im, (x, HEAD))
        sheet.save(out_dir / f"p{k + 1:02d}.jpg", quality=84, optimize=True)
print(f"comparison images: {n} pages -> {out_dir}")

# ---------------------------------------------------------------- 文字の大きさ
def page_metrics(page):
    """1 ページ分の文字サイズ（1920px 幅換算）を集計する。"""
    scale = 1920.0 / float(page.width)
    h = float(page.height)
    lines = {}
    for ch in page.chars:
        if not ch["text"].strip():
            continue
        key = (round(ch["top"] / 3), round(ch["size"], 1))
        lines.setdefault(key, []).append(ch)
    body_sizes, sizes_all, nchar = [], [], 0
    title_size = 0.0
    for (_, size), chars in lines.items():
        text = "".join(c["text"] for c in sorted(chars, key=lambda c: c["x0"]))
        top = min(c["top"] for c in chars)
        px = size * scale
        nchar += len(text)
        # フッター（下端 7%）と写真のクレジット・イメージ表示は「本文」に数えない
        is_footer = top > h * 0.92
        # 影つきの文字は PDF 内で 2 回描かれることがあるので、連続した同じ文字は 1 つにまとめて判定する
        dedup = "".join(ch for i, ch in enumerate(text) if i == 0 or ch != text[i - 1])
        words = ("Photo", "Wikimedia", "イメージ写真", "CC BY", "Public domain", "YUCACO住宅", "写真（左から）")
        is_credit = any(w in text or w in dedup for w in words)
        if is_footer or is_credit:
            continue
        sizes_all.append((px, top, len(text), text))
    if not sizes_all:
        return None
    # 見出し：上から 22% までにある、いちばん大きい文字の行
    head = [s for s in sizes_all if s[1] < h * 0.22]
    if head:
        title_size = max(s[0] for s in head)
    below = [s for s in sizes_all if s[1] >= h * 0.22] or sizes_all
    # 記号 1 文字だけの行（矢印など）は除く
    body = [s for s in below if s[2] >= 2]
    smallest = min(s[0] for s in body)
    biggest = max(s[0] for s in body)
    # 本文の代表値：文字数で重みをつけた中央値
    weighted = sorted((s[0], s[2]) for s in body)
    total = sum(w for _, w in weighted)
    acc, median = 0, weighted[-1][0]
    for size, w in weighted:
        acc += w
        if acc >= total / 2:
            median = size
            break
    return {
        "title": round(title_size), "smallest": round(smallest), "median": round(median),
        "biggest": round(biggest), "chars": nchar,
    }

rows = []
opened = [pdfplumber.open(str(p)) for _, p in versions]
for k in range(min(len(o.pages) for o in opened)):
    row = {"page": k + 1}
    for tag, pdf in zip(("old", "v1", "v2"), opened):
        m = page_metrics(pdf.pages[k]) or {}
        for key in ("smallest", "median", "biggest", "chars"):
            row[f"{tag}_{key}"] = m.get(key, "")
    rows.append(row)

fields = ["page"] + [f"{t}_{k}" for k in ("smallest", "median", "biggest", "chars") for t in ("old", "v1", "v2")]
with open(out_dir / "text_metrics.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)

with open(out_dir / "text_metrics.md", "w", encoding="utf-8") as f:
    f.write("# 文字の大きさの比較（1920px 幅に換算、単位 px）\n\n")
    f.write("PDF に埋め込まれた文字から機械的に集計。フッターと写真クレジットは除く。\n")
    f.write("「最小」＝本文でいちばん小さい文字、「中央」＝本文の代表的な大きさ（文字数で重みづけ）、「最大」＝見出し以外でいちばん大きい文字。\n\n")
    f.write("| p. | 最小 旧/v1/v2 | 中央 旧/v1/v2 | 最大 旧/v1/v2 | 文字数 旧/v1/v2 |\n|---|---|---|---|---|\n")
    for r in rows:
        f.write("| {page} | {old_smallest} / {v1_smallest} / **{v2_smallest}** | {old_median} / {v1_median} / **{v2_median}** | {old_biggest} / {v1_biggest} / **{v2_biggest}** | {old_chars} / {v1_chars} / {v2_chars} |\n".format(**r))
print("text metrics ->", out_dir / "text_metrics.md")
