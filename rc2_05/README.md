# RC構造Ⅱ 第5回演習課題（PC梁・FPC）

| ファイル | 内容 |
|---|---|
| `out/RC2_05_Answer.pdf` | 提出用解答用紙（1ページ） |
| `out/RC2_05_Verification.pdf` | 詳細検証資料（計算過程・検算・参考資料・判断根拠） |
| `out/calc.json` | SymPyによる計算結果 |
| `out/check_answer.txt` | 提出用PDFの自動検査結果 |

結果: A = 1.8×10^5 mm², Z = 1.8×10^7 mm³, M/Z = 2.0 N/mm², P = 180 kN, Pe = 300 kN, N = 300/156 = 1.92 → **2本**

## 原本の解答用紙に書き込む場合

```bash
pip install pymupdf sympy fpdf2 numpy
python src/calc.py out/calc.json
python src/sheet.py fill "05_課題＋解答用紙.pdf" out/RC2_05_Answer.pdf          # 空白欄を自動検出
python src/sheet.py fill "05_課題＋解答用紙.pdf" out/RC2_05_Answer.pdf x0 y0 x1 y1  # 位置を指定(pt)
python src/check.py out/RC2_05_Answer.pdf "05_課題＋解答用紙.pdf" x0 y0 x1 y1   # 原本保持の検査
```
