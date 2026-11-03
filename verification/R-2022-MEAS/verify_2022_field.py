"""2022年度 実住宅4件の24時間測定（01 実態調査データ）の再集計。F-2022-01（10〜20 μm が最多・最大約6万個/m³）の検証。

入力: private_data/raw/2022_meas/f1516298898945_field.txt（Git 管理外）。住宅はシート上の順に 実住宅1〜4 と記す（氏名・記号を出さない）。
出力: results_field.json / results_field.md【計算結果】
"""
import json, re, statistics as st
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "private_data" / "raw" / "2022_meas" / "f1516298898945_field.txt"
OUT = Path(__file__).parent
UNIT = 1 / 0.00283  # 個/m³ per count（2.83 L 吸引）
BINS = ["1.0-5.0", "5.0-10.0", "10.0-20.0", "20.0-30.0", "30.0-"]


def parse():
    L = SRC.read_text(encoding="utf-8").split("\n")
    starts = [i for i, l in enumerate(L) if l.startswith("データまとめ")]
    houses = []
    for k, s in enumerate(starts):
        e = starts[k + 1] if k + 1 < len(starts) else len(L)
        rows = []
        for l in L[s:e]:
            c = l.split("\t")
            if len(c) > 12 and re.match(r"\d+/\d+/22 \d+:\d+", c[2]):
                try:
                    cum = [float(x) * UNIT for x in c[3:8]]  # ≥1, ≥5, ≥10, ≥20, ≥30 μm（累積）
                except ValueError:
                    continue
                v = [cum[0] - cum[1], cum[1] - cum[2], cum[2] - cum[3], cum[3] - cum[4], cum[4]]
                sheet = []
                for x in c[8:13]:
                    try:
                        sheet.append(float(x))
                    except ValueError:
                        sheet.append(None)
                rows.append((c[2], v, sheet))
        houses.append(rows)
    return houses


def main():
    res = {}
    for i, rows in enumerate(parse(), 1):
        if not rows:
            continue
        cols = list(zip(*[v for _, v, _ in rows]))
        both = [(v, sh) for _, v, sh in rows if all(x is not None for x in sh)]
        agree = sum(all(abs(a - b) < 1e-3 * max(1, abs(b)) for a, b in zip(v, sh)) for v, sh in both)
        neg = sum(any(x < 0 for x in v) for _, v, _ in rows)
        res[f"実住宅{i}"] = {"n_min": len(rows), "n_sheet_bins": len(both), "n_sheet_bins_agree": agree, "n_negative_bin": neg, "start": rows[0][0], "end": rows[-1][0],
                          "mean": {b: round(st.mean(c), 0) for b, c in zip(BINS, cols)},
                          "median": {b: round(st.median(c), 0) for b, c in zip(BINS, cols)},
                          "max": {b: round(max(c), 0) for b, c in zip(BINS, cols)}}
    (OUT / "results_field.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    L = ["# 2022年度 実住宅4件 粒径別個数濃度の再集計（自動生成: verify_2022_field.py）", "", "区分: 【計算結果】。単位 個/m³（ブックの表記）。粒径区分は累積計数（≥1, ≥5, ≥10, ≥20, ≥30 μm, 個/2.83 L）の差×353.357 で再計算した1分値（約24時間）。", "",
         "| 住宅 | 分数 | 指標 | " + " | ".join(f"{b} μm" for b in BINS) + " | 5〜45 μm帯の最多区分 |", "|---|---|---|" + "---|" * len(BINS) + "---|"]
    for h, r in res.items():
        for m in ("mean", "median", "max"):
            top = max(BINS[1:], key=lambda b: r[m][b])
            L.append(f"| {h} | {r['n_min']} | {m} | " + " | ".join(f"{r[m][b]:.0f}" for b in BINS) + f" | {top} |")
    L += ["", "| 住宅 | 全分数 | シートの区分値がある分数 | うち再計算と一致 | 負の区分値が出た分数 |", "|---|---|---|---|---|"]
    L += [f"| {h} | {r['n_min']} | {r['n_sheet_bins']} | {r['n_sheet_bins_agree']} | {r['n_negative_bin']} |" for h, r in res.items()]
    (OUT / "results_field.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
