"""手書き用の見本 ①②（A3）と作図ガイド ③ を作る。

  python scripts/make_handwriting_guides.py
出力: output/yamadome_20261021/handwriting/
  02_手書き見本_根切り平面図.pdf / 03_手書き見本_Y3通り断面図.pdf / 04_手書き作図完全ガイド_実寸寸法と手順.pdf
（いずれも課題PDFを下地に含むため、著作権上リポジトリにはコミットしない）
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from yamadome import config, geometry, calculation, handwriting, guide  # noqa: E402

site = config.load(ROOT / "config/site.yaml")
zones = geometry.zone_polygons(site)
res = calculation.compute(site, zones)
base = ROOT / site.raw["answer_sheet"]["pdf"]
out = ROOT / "output/yamadome_20261021/handwriting"; out.mkdir(parents=True, exist_ok=True)
p1, p2, p3 = out / "02_手書き見本_根切り平面図.pdf", out / "03_手書き見本_Y3通り断面図.pdf", out / "04_手書き作図完全ガイド_実寸寸法と手順.pdf"
handwriting.make_samples(site, zones, res, base, p1, p2)
info = guide.build_guide(p3, site, zones, res, p1, p2, base)
print(info)
