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


def test_exact_slope_volume_hand_calc():
    # 10×10m・深さ2m、法1:0.3、東面のみ鉛直。手計算:
    # 本体 200 + 3面の法 0.5×2×0.6×30 = 18 + 隅2か所の角錐 2×(0.3²×2³/3) = 0.48 → 218.48
    class S:
        raw = {"retaining": {"slope_ratio": 0.3, "soldier_pile_x_mm": 10000}}
    z = [("A0", "base", 2.0, geometry.poly([(0, 0), (10000, 0), (10000, 10000), (0, 10000)]))]
    assert calculation.exact_slope_volume(S, z, n_slices=2000) == pytest.approx(218.48, rel=1e-4)


def test_refuses_to_finalize_when_geometry_missing(tmp_path):
    import yaml
    c = yaml.safe_load((ROOT / "config/site.yaml").read_text(encoding="utf-8"))
    c["excavation"]["zones"][0]["polygon"] = None
    cfg = tmp_path / "missing.yaml"; cfg.write_text(yaml.safe_dump(c, allow_unicode=True), encoding="utf-8")
    assert run.main(["--config", str(cfg), "--out", str(tmp_path / "o")]) == 2
    assert (tmp_path / "o/08_未解決事項.md").exists()


def real():
    site = config.load(ROOT / "config/site.yaml")
    return site, geometry.zone_polygons(site)


def test_real_slope_widths_match_lecture_drawing():
    # 着色図の法幅 495・555・630 = 0.3 × 1.65・1.85・2.10
    site, _ = real()
    n = site.raw["retaining"]["slope_ratio"]
    assert [round(n * site.depth(k) * 1000) for k in ("base", "general", "F4A")] == [495, 555, 630]


def test_real_x2_section_offsets():
    # X2断面: Y2 から南 1310・北 1090、Y3 から南 1090・北 1310、F4 = 2400×1400 + ゆとり 500
    site, z = real()
    f4 = [p for n_, c, d, p in z if n_.startswith("F4 (X2")][0].bounds
    f4a = [p for n_, c, d, p in z if n_.startswith("F4A (X2")][0].bounds
    assert (f4[1], f4[3]) == (-1310, 1090) and (f4a[1], f4a[3]) == (10800 - 1090, 10800 + 1310)
    assert f4[2] - f4[0] == 3400                     # 着色図 1700|1700


def test_real_methods_agree_and_close_to_exact_solid():
    site, z = real()
    res = calculation.compute(site, z)
    assert res.agree
    assert abs(res.method_a - res.exact_volume) / res.exact_volume < 0.02
    # 方法Bの増掘り深さは授業の 0.20 / 0.45 / 0.55
    assert sorted(round(r[2], 2) for r in res.method_b_rows[1:]) == [0.2, 0.45, 0.55]


def test_east_face_not_widened():
    site, z = real()
    yz, _ = calculation.yohaba_zones(site, z)
    from shapely.ops import unary_union
    assert unary_union([p for *_, p in yz]).bounds[2] == site.raw["retaining"]["soldier_pile_x_mm"]


def test_y3_section_depths():
    site, z = real()
    segs = geometry.section_profile(z, 10800)
    assert segs[0][2] == 2.20 and max(s[2] for s in segs) == 2.20
    assert [s[2] for s in segs if 4050 <= s[0] < 13200 and s[1] - s[0] == 3400] == [2.10, 2.10]


def test_drawings_are_true_1_100(tmp_path):
    from yamadome import pdf_tools
    assert run.main(["--out", str(tmp_path)]) == 0
    for f in ("02_根切り図.pdf", "03_Y3根切り断面図.pdf"):
        xs = pdf_tools.measure_grid_spacing_mm(tmp_path / f)
        gaps = [round(b - a, 2) for a, b in zip(xs, xs[1:])]
        assert gaps.count(57.5) >= 3, (f, xs)          # 5750 mm → 57.5 mm


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
