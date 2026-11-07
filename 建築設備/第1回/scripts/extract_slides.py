"""授業動画からスライド領域を切り出し、スライド切替箇所のみ保存する。
usage: python extract_slides.py <video> <out_dir> [interval_sec=3]
1) ffmpeg で interval 秒ごとにスライド領域(crop)を PNG 出力
2) 直前に採用したフレームとの差分(平均絶対差)が閾値を超えたら新スライドとして採用
出力: out_dir/raw/*.png, out_dir/slides/sNNN_h-mm-ss.png, out_dir/slides.csv
"""
import sys, os, subprocess, glob, shutil, csv
import numpy as np
from PIL import Image

video, out = sys.argv[1], sys.argv[2]
iv = float(sys.argv[3]) if len(sys.argv) > 3 else 3.0
CROP = "672:506:133:107"   # 画面録画内の講義スライド表示領域 (w:h:x:y)
raw, sl = f"{out}/raw", f"{out}/slides"
os.makedirs(raw, exist_ok=True); os.makedirs(sl, exist_ok=True)
if not glob.glob(f"{raw}/*.png"):
    subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-vf", f"fps=1/{iv},crop={CROP}",
                    f"{raw}/f%05d.png"], check=True)
files = sorted(glob.glob(f"{raw}/*.png"))
def arr(p):  # 講師アイコン等の影響を避けるためグレースケール縮小で比較
    return np.asarray(Image.open(p).convert("L").resize((168, 126)), dtype=np.float32)
prev, rows = None, []
for i, p in enumerate(files):
    t = i * iv
    a = arr(p)
    if prev is None or np.abs(a - prev).mean() > 6.0:
        name = f"s{len(rows)+1:03d}_{int(t//3600)}-{int(t%3600//60):02d}-{int(t%60):02d}.png"
        shutil.copy(p, f"{sl}/{name}"); rows.append((name, t)); prev = a
with open(f"{out}/slides.csv", "w", newline="") as f:
    csv.writer(f).writerows([("file", "t_sec")] + rows)
print(len(files), "frames ->", len(rows), "slides")
