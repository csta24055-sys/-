"""手書き作図ガイドの 1 枚版（A3）。 python scripts/make_one_sheet.py
出力: output/yamadome_20261021/handwriting/05_手書き作図ガイド_A3一枚版.pdf（課題用紙を含むためコミットしない）"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from yamadome import config, geometry, calculation, onesheet  # noqa: E402
site = config.load(ROOT / "config/site.yaml"); zones = geometry.zone_polygons(site); res = calculation.compute(site, zones)
out = ROOT / "output/yamadome_20261021/handwriting/05_手書き作図ガイド_A3一枚版.pdf"
onesheet.build(out, site, zones, res, ROOT / site.raw["answer_sheet"]["pdf"])
print(out)
