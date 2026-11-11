# 分類の資料（索引のもとになったもの）

旧研究の成果を 5 区分に分類したときの資料。分類は、コミット済みのファイルと保存した作業資料を**読むことだけ**で行った。
旧研究のコードは実行していない。

| ファイル | 内容 |
|---|---|
| `BRIEF.md` | 分類担当（読み取り専用の AI 作業担当）への指示。禁止事項、区分の定義、出力の形式 |
| `classification_workflow_script.js` | 分類担当 7 観点を起動したワークフローの定義。記録として保存した |
| `R1.json`〜`R5.json`、`R7.json` | 観点ごとの分類結果（項目の一覧） |
| `R6.json` | 第2回の独立検査の指摘 59 件の登録簿 |
| `readers_summary.json` | 分類担当ごとの要約、禁止事項を守ったかの申告、分類担当が挙げた問題点 |
| `INDEX_head.md`、`INDEX_reuse_intro.md`、`INDEX_tail.md` | `INDEX.md` のうち、索引の作成者が書いた部分 |
| `render_index.py` | 上の JSON と文章から `INDEX.md` と `index_detail/` を生成するスクリプト |

`render_index.py` は JSON と文書と Git の一覧を読むだけで、旧研究のコードを読み込まない。生成の手順（リポジトリの最上位で）：

```
python3 -I whole-life-carbon-jcat-study/research_archive/real_equation_checkpoint/materials/classification/render_index.py \
  whole-life-carbon-jcat-study/research_archive/real_equation_checkpoint/materials/classification \
  whole-life-carbon-jcat-study/research_archive/real_equation_checkpoint \
  .
```

`BRIEF.md` と `classification_workflow_script.js` にある `/tmp/…` の場所は、分類の作業用フォルダで、今は無い。
