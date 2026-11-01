"""成果物生成のエントリポイント。

  python run.py --calibrate              課題PDFを400dpi画像化し、テキスト座標・ページ寸法を出力
  python run.py                          config/site.yaml から成果物を生成（未確定があれば停止）
  python run.py --config config/demo.yaml --demo   架空形状でパイプラインを動作確認（解答ではない）
"""
from __future__ import annotations
import argparse, shutil, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
from yamadome import config, geometry, calculation, drawing, report, pdf_tools  # noqa: E402

GEOMETRY_KEYS = ("excavation", "retaining.slope_ratio", "retaining.include_slope_volume")


def write_unresolved(site, out):
    lines = ["# 08 未解決事項", "", "config の null 項目（資料から確定できていない値）:", ""]
    lines += [f"- `{u}`" for u in site.unresolved] or ["- なし"]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config/site.yaml")
    ap.add_argument("--out", default="output/yamadome_20261021")
    ap.add_argument("--calibrate", action="store_true")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args(argv)
    site = config.load(ROOT / a.config)
    out = ROOT / a.out; out.mkdir(parents=True, exist_ok=True)
    pdf = ROOT / site.raw["answer_sheet"]["pdf"]

    if a.calibrate:
        if not pdf.exists():
            print(f"[停止] 課題PDFがありません: {pdf}"); return 3
        an = ROOT / "output/analysis"
        pdf_tools.render_pages(pdf, an / "pages", dpi=400)
        d = pdf_tools.dump_text_and_vectors(pdf, an / "pdf_text.json")
        for p in d:
            print(f"p{p['page']}: {p['size_mm']} mm, words={len(p['words'])}, vectors={p['n_drawings']}")
        return 0

    geom_missing = [u for u in site.unresolved if u.startswith(GEOMETRY_KEYS)]
    if geom_missing and not a.demo:
        write_unresolved(site, out / "08_未解決事項.md")
        print("[停止] 根切り形状が未確定のため成果物を確定値として生成しません:")
        print("\n".join(f"  - {u}" for u in geom_missing))
        return 2

    wm = "DEMO 架空形状 — 解答ではない" if a.demo else None
    zones = geometry.zone_polygons(site)
    bad = geometry.check_containment(zones)
    if bad:
        print(f"[エラー] A0 に含まれない区画: {bad}"); return 4
    res = calculation.compute(site, zones)
    if not res.agree:
        print(f"[エラー] 方法A {res.method_a} ≠ 方法B {res.method_b}"); return 5

    drawing.plan(site, zones, out / "02_根切り図", watermark=wm)
    segs = drawing.section(site, zones, out / "03_Y3根切り断面図", watermark=wm)
    lines = report.calc_lines(site, zones, res, segs, watermark=wm)
    report.write_calc_pdf(lines, out / "04_掘削土量計算書.pdf")
    report.write_xlsx(site, res, out / "05_計算明細.xlsx")
    write_unresolved(site, out / "08_未解決事項.md")
    src_dir = out / "07_source"; shutil.rmtree(src_dir, ignore_errors=True)
    shutil.copytree(ROOT / "src", src_dir); shutil.copy(ROOT / a.config, src_dir / "site.yaml")

    sheet = site.raw["answer_sheet"]
    if pdf.exists() and sheet["plan_box"] and sheet["section_box"] and not a.demo:
        items = [("pdf", sheet["plan_box"], out / "02_根切り図.pdf"),
                 ("pdf", sheet["section_box"], out / "03_Y3根切り断面図.pdf")]
        if sheet["volume_text_at"]:
            items.append(("text", sheet["volume_text_at"], f"掘削土量 V = {res.total:.2f} m³"))
        final = out / "01_完成演習課題.pdf"
        pdf_tools.fill_answer_sheet(pdf, final, sheet["page_index"], items)
        ratio = pdf_tools.compare_outside_boxes(pdf, final, sheet["page_index"], [i[1] for i in items])
        print(f"解答欄外の変化画素率: {ratio:.5f}")
        pdf_tools.render_pages(final, out / "verify", dpi=300)
    else:
        print("[注意] 01_完成演習課題.pdf（元PDFへの書込み）は未生成: 課題PDFまたは解答欄座標が未設定")
        sheet_pdf = out / "01_解答シート_独自様式.pdf"
        pdf_tools.standalone_sheet(
            sheet_pdf, site.raw["meta"]["title"],
            "【問題】〇〇寮新築工事の設計図抜粋から根切図と根切断面図（Y3通り）を作図し、根切の掘削土量を算出せよ。"
            "ただし山留工法は西面・南面・北面がオープンカット工法、東面は親杭横矢板工法とする。",
            out / "02_根切り図.pdf", out / "03_Y3根切り断面図.pdf",
            [f"掘削土量  V = {res.total:.2f} m³",
             f"  方法A  V = Σ(Ai×hi) = {res.method_a:.3f} m³",
             f"  方法B  V = A0×1.65 + Σ(Aj×Δhj) = {res.method_b:.3f} m³  （A0 = {res.a0_area:.3f} m²）",
             "  余幅 = 作業のゆとり幅0.5m + 法幅(0.3h)/2、東面（親杭横矢板）は余幅0.1m・法なし"],
            "注: 寸法は授業スライド・授業中の着色根切図・課題用紙の写真から読取り・導出。"
            "F3A平面寸法・外周梁外面位置は仮定（08_未解決事項.md）。元の課題PDFへの書込み版は未作成。" if not a.demo else "DEMO")
        pdf_tools.render_pages(sheet_pdf, out / "verify", dpi=300)

    print(f"方法A = {res.method_a:.3f} m³ / 方法B = {res.method_b:.3f} m³ / 一致={res.agree}")
    print(f"掘削土量 = {res.total:.3f} m³  → 出力: {out}")
    if site.unresolved:
        print(f"未確定 {len(site.unresolved)} 項目あり（08_未解決事項.md）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
