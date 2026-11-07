# 建築設備Ⅲ 第1回「給排水衛生設備の役割」復習資料

| ファイル | 内容 |
|---|---|
| `建築設備Ⅲ_第1回_試験対策版_A4_2枚.pdf` | **第2版・試験対策版**（定義・5分類・4原則・仕組み・重要数値・教員の強調点・一問一答・間違えやすい点。事務連絡と歴史コラムは除外） |
| `建築設備Ⅲ_第1回_授業内容版_A4_2枚.pdf` | **第2版・授業内容版**（講義内容の体系的な整理のみ。一問一答・試験対策・事務連絡・歴史コラムは除外） |
| `建築設備_第1回_要点整理_A4_2枚.pdf` | 第1版の要点整理（A4縦・2ページ、事務連絡・コラムを含む） |
| `建築設備_第1回_要点整理.md` | 要点整理の Markdown 版（PDF と同じ内容。表の一部は PDF より詳しい） |
| `建築設備_第1回_解析メモ.md` | 動画の情報、解析方法、トピックと時刻、選定理由、検証結果、確認できなかった点 |
| `scripts/` | 再実行用：`run_all.sh`（一括実行）、`transcribe.py`（全編の文字起こし）、`extract_slides.py`（スライド抽出）、`verify_segments.py`（重要区間の二次照合）、`print.html`（第1版の原稿）、`print_exam.html`・`print_lecture.html`（第2版の原稿）、`common.css`（第2版の共通スタイル）、`figs/`（系統図・トラップ図・責任分界点図）、`build_pdf.js`（PDF生成・検査） |

PDF だけを作り直す場合（`<font>` は @fontsource/noto-sans-jp の files ディレクトリ）：

```
NODE_PATH=$(npm root -g) node scripts/build_pdf.js <font> 建築設備Ⅲ_第1回_試験対策版_A4_2枚.pdf print_exam.html
NODE_PATH=$(npm root -g) node scripts/build_pdf.js <font> 建築設備Ⅲ_第1回_授業内容版_A4_2枚.pdf print_lecture.html
NODE_PATH=$(npm root -g) node scripts/build_pdf.js <font> 建築設備_第1回_要点整理_A4_2枚.pdf   # 第1版
```

文字起こし全文とスライド画像は、教員の著作物を含むためコミットしていません。`run_all.sh` で再生成できます。
