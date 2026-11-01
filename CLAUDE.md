# CLAUDE.md

- 課題条件（西・南・北＝オープンカット、東＝親杭横矢板）は変更しない。
- 深さ: 基本 1.65 / 一般 1.85 / F4A 2.10 / F3A 2.20 m（授業スライド）。1.65 を 1.85 に置き換えない。
- GL と 1FL（= GL+500）を混同しない。根切り深さは床付け（基礎下端 −100mm）まで。
- 値は必ず `config/site.yaml` に出典付きで入れる。読めない値は null のまま残し、捏造しない。
- `inputs/` と元PDFを含む完成答案はコミットしない。
- 変更後は `python -m pytest -q` と `python run.py --config config/demo.yaml --demo --out output/demo` を通す。
- 有料の外部AI APIは使わない。
