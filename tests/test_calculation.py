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
    assert abs(res.method_a - res.exact_volume) / res.exact_volume < 0.001   # 外周のみ余幅で実斜面と 0.03% 一致
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


PDF = ROOT / "inputs/assignment/20261021_ 第4回_山留土工事演習問題及びサンプル設計図(演習課題)(1).pdf"


@pytest.mark.skipif(not PDF.exists(), reason="課題PDFは著作権上コミットしない（ローカルにある場合のみ検証）")
def test_answer_sheet_written_without_damaging_original(tmp_path):
    import pymupdf
    assert run.main(["--out", str(tmp_path)]) == 0
    out = tmp_path / config.load(ROOT / "config/site.yaml").raw["answer_sheet"]["output_name"]
    with pymupdf.open(out) as d:
        assert len(d) == 7                         # 元PDFの 2〜7 ページを保持
        t = d[0].get_text().replace("\xad", "-")
        assert "436.49" in t and "GL-1850" in t and "余幅100" in t


@pytest.mark.skipif(not PDF.exists(), reason="課題PDFが必要")
def test_sheet_grid_matches_config():
    # PDF の通り芯（一点鎖線）位置が config の plan_grid_pt と一致すること
    import pymupdf, collections
    site = config.load(ROOT / "config/site.yaml")
    g = site.raw["answer_sheet"]["plan_grid_pt"]
    V = collections.Counter()
    with pymupdf.open(PDF) as d:
        for dr in d[0].get_drawings():
            for it in dr["items"]:
                if it[0] == "l" and abs(it[1].x - it[2].x) < 0.05 and it[1].y < 620:
                    V[round(it[1].x, 2)] += 1
    for k in ("X1", "X4"):
        assert V[g[k]] >= 8


def test_real_volume_regression():
    site, z = real()
    res = calculation.compute(site, z)
    assert res.method_a == pytest.approx(436.490, abs=0.001)
    assert res.a0_area == pytest.approx(251.374, abs=0.001)


def test_independent_yohaba_rule_check():
    # scripts/verify_yohaba.py: 外面 + 余幅(0.5+0.3h/2) を Shapely なしで格子集計 → 本体と一致
    import runpy
    g = runpy.run_path(str(ROOT / "scripts/verify_yohaba.py"))
    assert abs(g["V"] - 436.490) < 0.01            # 外周のみ余幅（授業準拠）
    assert abs(g["A0"] - 251.374) < 0.01
    assert abs(g["V_all"] - 441.225) < 0.01        # v1 方式（全周余幅）も独立に再現



def test_v1_all_faces_reproduces_441():
    site, z = real()
    site.raw["retaining"]["yohaba_scope"] = "all_faces"
    assert calculation.compute(site, z).method_a == pytest.approx(441.225, abs=0.001)


def test_interior_steps_are_vertical_and_perimeter_gets_yohaba():
    from shapely.geometry import Point
    site, z = real()
    yz, _ = calculation.yohaba_zones(site, z)
    def depth(x, y):
        return max([d for *_, d, p in yz if p.contains(Point(x, y))], default=0)
    assert depth(5750, 1090 + 100) == 1.65          # F4 北側（内部の段差）: 余幅なし
    assert depth(5750, -1310 - 200) == 1.85         # F4 南側（外周）: 余幅 0.2775 内
    assert depth(5750, -1310 - 300) == 0            # 余幅の外
    assert depth(-590 - 200, 5000) == 1.65          # 西面 FS1: 法尻から余幅 0.2475 の内側
    assert depth(-590 - 300, 5000) == 0             # 余幅の外
    assert depth(17440 + 10, 5000) == 0             # 東面: 親杭面で打切り


def test_corner_overlap_counted_once():
    site, z = real()
    yz, _ = calculation.yohaba_zones(site, z)
    from shapely.ops import unary_union
    f5 = [p for n_, *_, p in yz if n_.startswith("F5")][0]
    f4a = [p for n_, *_, p in yz if n_.startswith("F4A (X3")][0]
    assert f5.intersection(f4a).area > 0               # 角部で重なる
    pieces = geometry.final_depth_pieces(yz)
    assert sum(g.area for _, g in pieces) == pytest.approx(unary_union([p for *_, p in yz]).area)


def test_teacher_slide_dimensions():
    # 授業着色図の寸法: F4 1700|1700、F3 1390/1610、X4側 1410|190、F4A北 1310、1700+1240+2900
    site, z = real()
    b = {n_: p.bounds for n_, c, d, p in z}
    assert b["F4 (X3・Y2)"][2] - 11500 == 1700 and 11500 - b["F4 (X3・Y2)"][0] == 1700
    assert (b["F3 (X1・Y2)"][1], b["F3 (X1・Y2)"][3]) == (-1610, 1390)
    assert (17250 - b["F3 (X4・Y2)"][0], b["F3 (X4・Y2)"][2] - 17250) == (1410, 190)
    assert b["F4A (X2・Y3)"][3] - 10800 == 1310
    f5 = [f for f in site.raw["footings"] if f["name"] == "F5"][0]["plan_mm"]["polygon"]
    assert 11500 + 1700 + 1240 == f5[0][0]


def test_ridge_lines_at_corners():
    from yamadome import answer_sheet
    from shapely.ops import unary_union
    site, z = real()
    n = site.raw["retaining"]["slope_ratio"]; east = site.raw["retaining"]["soldier_pile_x_mm"]
    bottom = unary_union([p for *_, p in z])
    top = unary_union([calculation.widen(p, n * d * 1000, east) for *_, d, p in z])
    lines = answer_sheet.ridge_lines(bottom, top, east)
    assert ((-590, -1610), (-1145, -2165)) in [(tuple(map(round, a)), tuple(map(round, b))) for a, b in lines]
    assert len(lines) >= 20


def test_section_band_colors_follow_teacher_and_plan():
    # 断面の着色帯: 法面・GL際＝茶、根切り底＝平面図と同じ深さ別の色、段差は深い側の色。形状（prof）は変えない
    from yamadome import answer_sheet as A
    site, z = real()
    segs = geometry.section_profile(z, 10800)
    sw = 0.3 * segs[0][2] * 1000
    prof = [(segs[0][0] - sw, 0), (segs[0][0], -segs[0][2] * 1000)]
    for a, b, d in segs:
        prof += [(a, -d * 1000), (b, -d * 1000)]
    prof += [(segs[-1][1], 0)]
    pieces = A.band_pieces(prof, segs)
    cols = {c for c, _ in pieces}
    assert A.SLOPE_TAN in cols and {A.FILL[d] for d in (1.65, 1.85, 2.10, 2.20)} <= cols
    from shapely.geometry import Polygon
    cut = Polygon(prof + [prof[0]])
    for c, q in pieces:                       # 帯は土側（掘削部の内側をほとんど塗らない）
        assert q.difference(cut).area > 0.5 * q.area
