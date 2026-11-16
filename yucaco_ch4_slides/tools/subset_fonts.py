"""スライドで使う文字だけを含むフォント（サブセット）を作る。

Chromium は TTC/CFF 形式の日本語フォントを PDF に Type 3 として埋め込むため、
TrueType 形式（glyf）の Noto Sans JP / Noto Serif JP を使い、使用文字だけに絞って同梱する。

  python3 tools/subset_fonts.py <フォントの元フォルダ> [BIZ UDPゴシックのフォルダ]

元フォルダには NotoSansJP_400Regular.ttf などの静的 TTF を置く
（npm の @expo-google-fonts/noto-sans-jp, @expo-google-fonts/noto-serif-jp に同梱。SIL OFL 1.1）。
本文を書き換えて新しい文字が増えたら、このスクリプトを再実行する。
"""
import pathlib
import string
import sys

from fontTools import subset

root = pathlib.Path(__file__).resolve().parent.parent
src_dir = pathlib.Path(sys.argv[1])
out_dir = root / "src" / "assets" / "fonts"
out_dir.mkdir(parents=True, exist_ok=True)

html = (root / "src" / "deck.html").read_text(encoding="utf-8")
css = (root / "src" / "deck.css").read_text(encoding="utf-8")
chars = set(html) | set(css)
chars |= set(string.printable)
chars |= set("０１２３４５６７８９（）「」『』【】、。・：；！？＝＋−－―〜～…‥％／×÷≦≧≒→←↑↓㎡³²①②③④⑤⑥⑦⑧⑨⑩※＊　")
text = "".join(sorted(c for c in chars if c.isprintable() or c == "　"))

targets = [
    ("NotoSansJP_300Light.ttf", "DeckSans-300.ttf"),
    ("NotoSansJP_400Regular.ttf", "DeckSans-400.ttf"),
    ("NotoSansJP_500Medium.ttf", "DeckSans-500.ttf"),
    ("NotoSansJP_700Bold.ttf", "DeckSans-700.ttf"),
    ("NotoSerifJP_600SemiBold.ttf", "DeckSerif-600.ttf"),
]
for src_name, out_name in targets:
    src = next(src_dir.rglob(src_name))
    opts = subset.Options()
    opts.layout_features = ["*"]      # palt（約物の詰め）・tnum（等幅数字）を残す
    opts.name_IDs = ["*"]
    opts.name_languages = ["*"]
    opts.notdef_outline = True
    opts.glyph_names = False
    opts.hinting = True
    font = subset.load_font(str(src), opts)
    sub = subset.Subsetter(opts)
    sub.populate(text=text)
    sub.subset(font)
    out = out_dir / out_name
    subset.save_font(font, str(out), opts)
    print(f"{out_name}: {out.stat().st_size // 1024} KB")
print(f"{len(text)} characters")
# 書き出し時のチェック用に、サブセットに入れた文字を保存する
(out_dir / "charset.txt").write_text(text, encoding="utf-8")

# Noto Sans JP（Google Fonts 版）には「≒」が無いため、この記号だけ BIZ UDPゴシック（SIL OFL 1.1）から取る
biz_dir = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else pathlib.Path("/usr/share/fonts/truetype/bizud-gothic")
for src_name, out_name in [("BIZUDPGothic-Regular.ttf", "DeckSym-400.ttf"), ("BIZUDPGothic-Bold.ttf", "DeckSym-700.ttf")]:
    opts = subset.Options()
    opts.layout_features = []
    opts.notdef_outline = True
    font = subset.load_font(str(biz_dir / src_name), opts)
    sub = subset.Subsetter(opts)
    sub.populate(text="≒")
    sub.subset(font)
    out = out_dir / out_name
    subset.save_font(font, str(out), opts)
    print(f"{out_name}: {out.stat().st_size // 1024} KB")
