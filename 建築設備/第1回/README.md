# 建築設備Ⅲ 第1回「給排水衛生設備の役割」復習資料

| ファイル | 内容 |
|---|---|
| `建築設備Ⅲ_第1回_重要事項_詳しい解説版.pdf` | **重要事項・詳しい解説版（A4・5ページ）**。作成者が判断した重要度A（最重要）→B→Cの順に、理由・仕組み・実例まで詳しく解説。一問一答・まちがえやすい点はなし |
| `建築設備Ⅲ_第1回_超シンプル版_A4_2枚.pdf` | **新規・超シンプル版**。1ページ1テーマ・大きな文字と図・広い余白。「水の流れ」と「封水」だけに絞り、結論は「安全・衛生」 |
| `建築設備Ⅲ_第1回_試験対策版_A4_2枚.pdf` | **最新（第4版）・試験対策版**。冒頭の問い→やさしい解説と図→理由つき一問一答10問・まちがえやすい点→結論 |
| `建築設備Ⅲ_第1回_授業内容版_A4_2枚.pdf` | **最新（第4版）・授業内容版**。冒頭の問い→仕組みと実例の解説・図→結論。一問一答・試験向け項目なし |
| `旧版/` | 第2版・第3版の試験対策版・授業内容版 |
| `建築設備_第1回_要点整理_A4_2枚.pdf` | 第1版の要点整理（A4縦・2ページ、事務連絡・コラムを含む） |
| `建築設備_第1回_要点整理.md` | 要点整理の Markdown 版（PDF と同じ内容。表の一部は PDF より詳しい） |
| `建築設備_第1回_解析メモ.md` | 動画の情報、解析方法、トピックと時刻、選定理由、検証結果、確認できなかった点 |
| `scripts/` | 再実行用：`run_all.sh`（一括実行）、`transcribe.py`（全編の文字起こし）、`extract_slides.py`（スライド抽出）、`verify_segments.py`（重要区間の二次照合）、`print.html`（第1版の原稿）、`print_simple.html`＋`figs_simple/`（超シンプル版）、`print_exam.html`・`print_lecture.html`＋`common3.css`＋`figs3/`（第4版。第3版は `*_v3.html`）、`print_exam_v2.html`・`print_lecture_v2.html`＋`common.css`＋`figs/`（第2版）、`build_pdf.js`（PDF生成・検査） |

PDF だけを作り直す場合（`<font>` は @fontsource/noto-sans-jp の files ディレクトリ）：

```
NODE_PATH=$(npm root -g) node scripts/build_pdf.js <font> 建築設備Ⅲ_第1回_試験対策版_A4_2枚.pdf print_exam.html
NODE_PATH=$(npm root -g) node scripts/build_pdf.js <font> 建築設備Ⅲ_第1回_授業内容版_A4_2枚.pdf print_lecture.html
NODE_PATH=$(npm root -g) node scripts/build_pdf.js <font> 建築設備_第1回_要点整理_A4_2枚.pdf   # 第1版
```

文字起こし全文とスライド画像は、教員の著作物を含むためコミットしていません。`run_all.sh` で再生成できます。
