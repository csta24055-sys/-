"""計算書PDF・数式入りExcel・Markdown記録の出力。"""
from __future__ import annotations
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from openpyxl import Workbook
from openpyxl.styles import Font


def calc_lines(site, zones, res, segs, watermark=None):
    L = []
    if watermark:
        L += [f"*** {watermark} ***", ""]
    L += ["第4回 山留土工事演習課題  掘削土量計算書", ""]
    L += ["1. 使用寸法・条件"]
    gx = site.grid_x
    L += ["  通り芯 " + "  ".join(f"{k}={v:,} mm" for k, v in gx.items())]
    L += ["  通り芯 " + "  ".join(f"{k}={v:,} mm" for k, v in site.grid_y.items())]
    L += [f"  1FL = GL + {site.raw['levels']['1FL']} mm"]
    for k, v in site.raw["depth_classes"].items():
        L += [f"  深さ区分 {k:8s}: {v['depth']:.2f} m  ({v['source']})"]
    L += [f"  作業のゆとり幅 500 mm（区画の外形に含む）、法幅 = 0.3h、余幅 = ゆとり幅 + 法幅/2"]
    for d, half in sorted(res.yohaba.items()):
        L += [f"    深さ {d:.2f} m の区画: 外周（根切り底全体の外形の外側）だけに 法幅/2 = 0.3×{d:.2f}/2 = {half/1000:.4f} m を加算（内部の段差は鉛直、東面は親杭のため加算なし）"]
    L += ["", "2. 区画（根切り底＝法尻の外形・入力）"]
    for name, cls, d, p in zones:
        x0, y0, x1, y1 = p.bounds
        L += [f"  {name:14s} 深さ {d:.2f} m  面積 {p.area/1e6:9.3f} m²  範囲 x[{x0:,.0f}~{x1:,.0f}] y[{y0:,.0f}~{y1:,.0f}]"]
    L += ["", "3. 方法A  V = Σ(Ai × hi)  （余幅を加えた区画を最終深さ別に分割・重複なし）"]
    for d, a, v in res.method_a_rows:
        L += [f"  {a:9.3f} m² × {d:.2f} m = {v:9.3f} m³"]
    L += [f"  V_A = {res.method_a:.3f} m³"]
    L += ["", "4. 方法B  V = A0 × 1.65 + Σ(Aj × Δhj)"]
    for lab, a, dh, v in res.method_b_rows:
        L += [f"  {lab:16s} {a:9.3f} m² × {dh:.2f} m = {v:9.3f} m³"]
    L += [f"  V_B = {res.method_b:.3f} m³   （層別の和集合面積による独立計算で照合済み）"]
    L += ["", "5. 検算", f"  |V_A − V_B| = {abs(res.method_a-res.method_b):.6f} m³  → {'一致' if res.agree else '不一致'}"]
    if res.exact_volume is not None:
        diff = (res.method_a - res.exact_volume) / res.exact_volume * 100
        L += [f"  参考: 法面を実斜面(1:0.3)として数値積分した幾何体積 = {res.exact_volume:.3f} m³（余幅法との差 {diff:+.2f}%、隅角部の扱いの差）"]
    L += ["", f"6. 掘削土量  V = {res.total:.3f} m³  ≒ {res.total:.2f} m³"]
    L += ["", "7. Y3通り断面の深さ区間"]
    for a, b, d in segs:
        L += [f"  x = {a:,.0f} ~ {b:,.0f} mm : 根切り底 GL-{d*1000:,.0f}"]
    L += ["", "8. 未確定条件"]
    L += [f"  - {u}" for u in site.unresolved] or ["  なし"]
    return L


def write_calc_pdf(lines, out_pdf, per_page=55):
    with PdfPages(out_pdf) as pdf:
        for i in range(0, len(lines), per_page):
            fig = plt.figure(figsize=(8.27, 11.69))
            fig.text(0.07, 0.96, "\n".join(lines[i:i + per_page]), va="top", fontsize=8, family=plt.rcParams["font.family"], linespacing=1.5)
            pdf.savefig(fig); plt.close(fig)


def write_xlsx(site, res, out_xlsx):
    wb = Workbook(); ws = wb.active; ws.title = "土量計算"
    b = Font(bold=True)
    ws["A1"] = "掘削土量計算明細（面積・深さを変更すると再計算）"; ws["A1"].font = b
    ws["A3"], ws["B3"] = "基本掘削深さ h0 [m]", site.base_depth
    ws["C3"] = "面積は余幅（法幅/2）を含む。区画の面積・深さを変えると方法A・Bが再計算される。"
    ws["A5"], ws["B5"], ws["C5"], ws["D5"], ws["E5"], ws["F5"] = "区画（最終深さ別）", "面積 Ai [m²]", "深さ hi [m]", "方法A Ai×hi", "Δhi = hi−h0", "方法B Ai×Δhi"
    for c in "ABCDEF":
        ws[f"{c}5"].font = b
    r = 6
    for d, a, _ in res.method_a_rows:
        ws[f"A{r}"] = f"深さ {d:.2f} m 区画"
        ws[f"B{r}"] = round(a, 6); ws[f"C{r}"] = d
        ws[f"D{r}"] = f"=B{r}*C{r}"; ws[f"E{r}"] = f"=C{r}-$B$3"; ws[f"F{r}"] = f"=B{r}*E{r}"
        r += 1
    last = r - 1
    ws[f"A{r+1}"] = "A0（基本掘削面積）"; ws[f"B{r+1}"] = f"=SUM(B6:B{last})"
    ws[f"A{r+2}"] = "方法A  V=Σ(Ai×hi)"; ws[f"B{r+2}"] = f"=SUM(D6:D{last})"
    ws[f"A{r+3}"] = "方法B  V=A0×h0+Σ(Ai×Δhi)"; ws[f"B{r+3}"] = f"=B{r+1}*B3+SUM(F6:F{last})"
    ws[f"A{r+4}"] = "検算 |A−B|"; ws[f"B{r+4}"] = f"=ABS(B{r+2}-B{r+3})"
    ws[f"A{r+5}"] = "参考: 実斜面の幾何体積（Python数値積分）"; ws[f"B{r+5}"] = round(res.exact_volume, 3) if res.exact_volume is not None else "—"
    ws[f"A{r+6}"] = "掘削土量 [m³]（余幅法）"; ws[f"B{r+6}"] = f"=B{r+2}"
    ws[f"A{r+6}"].font = b
    ws.column_dimensions["A"].width = 30
    u = wb.create_sheet("未確定条件")
    for i, s in enumerate(site.unresolved or ["なし"], 1):
        u[f"A{i}"] = s
    wb.save(out_xlsx)
