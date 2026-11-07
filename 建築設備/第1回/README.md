# 建築設備Ⅲ 第1回「給排水衛生設備の役割」復習資料

| ファイル | 内容 |
|---|---|
| `建築設備_第1回_要点整理_A4_2枚.pdf` | 完成版の要点整理（A4縦・2ページ） |
| `建築設備_第1回_要点整理.md` | 要点整理の Markdown 版（PDF と同じ内容。表の一部は PDF より詳しい） |
| `建築設備_第1回_解析メモ.md` | 動画の情報、解析方法、トピックと時刻、選定理由、検証結果、確認できなかった点 |
| `scripts/` | 再実行用：`run_all.sh`（一括実行）、`transcribe.py`（全編の文字起こし）、`extract_slides.py`（スライド抽出）、`verify_segments.py`（重要区間の二次照合）、`print.html`（PDFの原稿）、`build_pdf.js`（PDF生成・検査） |

PDF だけを作り直す場合：`NODE_PATH=$(npm root -g) node scripts/build_pdf.js <noto-sans-jpのfilesディレクトリ> 建築設備_第1回_要点整理_A4_2枚.pdf`

文字起こし全文とスライド画像は、教員の著作物を含むためコミットしていません。`run_all.sh` で再生成できます。
