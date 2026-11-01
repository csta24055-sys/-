# RC構造Ⅱ 第5回演習課題（PC梁・FPC・偏心配置）

| ファイル | 内容 |
|---|---|
| `out/RC2_05_Answer.pdf` | 提出用：原本の解答用紙（1ページ）に解答を記入したもの |
| `out/RC2_05_Verification.pdf` | 詳細検証資料（計算過程・検算・講義資料と外部資料の比較・参考資料） |
| `out/calc.json` / `out/check_answer.txt` | SymPy計算結果 / 提出用PDFの自動検査結果 |

結果: M/Z = 2.0 N/mm², P/A = P·e/Z = 1.0 N/mm², **P = 180 kN, Pe = 300 kN, N = 300/156 = 1.92 → 2本**

```bash
python src/calc.py out/calc.json
python src/fill_original.py "05_課題＋解答用紙.pdf" out/RC2_05_Answer.pdf
python src/check_original.py "05_課題＋解答用紙.pdf" out/RC2_05_Answer.pdf out/RC2_05_Answer_placed.json > out/check_answer.txt
python src/report.py out/RC2_05_Verification.pdf
```
原本PDF（課題・講義ノート）は著作物のためリポジトリには含めていない。
