import sys
from pathlib import Path
import pytest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from yamadome import config, geometry, calculation  # noqa: E402
import run  # noqa: E402


def demo():
    site = config.load(ROOT / "config/demo.yaml")
    return site, geometry.zone_polygons(site)


def test_lecture_depths_and_increments():
    site = config.load(ROOT / "config/site.yaml")
    assert site.base_depth == 1.65
    inc = {k: round(site.depth(k) - 1.65, 2) for k in ("general", "F4A", "F3A")}
    assert inc == {"general": 0.20, "F4A": 0.45, "F3A": 0.55}   # 授業スライド 10:04
    for f in site.raw["footings"]:                                # 基礎下端と床付けの差 100mm
        assert f["bottom_GL_mm"] - f["subgrade_GL_mm"] == 100
    assert site.raw["levels"]["1FL"] - site.raw["levels"]["GL"] == 500


def test_retaining_methods_fixed_by_assignment():
    r = config.load(ROOT / "config/site.yaml").raw["retaining"]
    assert (r["west"], r["south"], r["north"], r["east"]) == ("open_cut",) * 3 + ("soldier_pile_lagging",)


def test_hand_calc_simple_box():
    # 10m×10m, 1.65m 基本 + 2m×2m の F3A(2.20)。手計算: 165 + 4×0.55 = 167.2
    site, _ = demo()
    z = [("A0", "base", 1.65, geometry.poly([(0, 0), (10000, 0), (10000, 10000), (0, 10000)])),
         ("F3A", "F3A", 2.20, geometry.poly([(0, 0), (2000, 0), (2000, 2000), (0, 2000)]))]
    ra, va = calculation.method_a(z)
    rb, vb, a0 = calculation.method_b(z, 1.65)
    assert va == pytest.approx(167.2) and vb == pytest.approx(167.2) and a0 == pytest.approx(100)


def test_overlap_not_double_counted():
    # 一般(1.85) と F3A(2.20) が重なっても、重なり部は 2.20 として1回だけ計上
    z = [("A0", "base", 1.65, geometry.poly([(0, 0), (10000, 0), (10000, 10000), (0, 10000)])),
         ("gen", "general", 1.85, geometry.poly([(0, 0), (4000, 0), (4000, 4000), (0, 4000)])),
         ("F3A", "F3A", 2.20, geometry.poly([(2000, 2000), (6000, 2000), (6000, 6000), (2000, 6000)]))]
    _, va = calculation.method_a(z)
    # 手計算: 165 + (16-4)×0.20 + 16×0.55 = 165 + 2.4 + 8.8 = 176.2
    assert va == pytest.approx(176.2)
    _, vb, _ = calculation.method_b(z, 1.65)
    assert vb == pytest.approx(176.2)


def test_demo_methods_agree_and_contained():
    site, z = demo()
    assert geometry.check_containment(z) == []
    res = calculation.compute(site, z)
    assert res.agree


def test_slope_prism_matches_hand_calc():
    # 10×10 底面, H=2, n=0.5, 西面のみ法: 断面三角形 0.5×2×1 × 長さ10 = 10 m³
    a0 = geometry.poly([(0, 0), (10000, 0), (10000, 10000), (0, 10000)])
    v = calculation.slope_volume(a0, 2.0, 0.5, ["west"])
    assert v == pytest.approx(10.0, rel=1e-6)


def test_real_config_refuses_to_finalize(tmp_path):
    assert run.main(["--out", str(tmp_path)]) == 2
    assert (tmp_path / "08_未解決事項.md").exists()


def test_pipeline_reproducible(tmp_path):
    for d in ("a", "b"):
        assert run.main(["--config", "config/demo.yaml", "--demo", "--out", str(tmp_path / d)]) == 0
    import openpyxl
    for d in ("a", "b"):
        assert (tmp_path / d / "02_根切り図.png").exists()
        assert (tmp_path / d / "04_掘削土量計算書.pdf").exists()
    wa = openpyxl.load_workbook(tmp_path / "a/05_計算明細.xlsx").active
    wb = openpyxl.load_workbook(tmp_path / "b/05_計算明細.xlsx").active
    assert [[c.value for c in r] for r in wa.iter_rows()] == [[c.value for c in r] for r in wb.iter_rows()]
