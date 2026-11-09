# Application source

ルートの `../START_HERE.md` と `../CLAUDE.md` を参照。

```bash
# ブラウザのみ（依存ゼロ）
python -m http.server 8765

# Electronデスクトップ
npm install
npm run check
npm start

# インストーラー
npm run dist:win # Windows
npm run dist:mac # macOS
npm run dist:linux # Linux
npm run check:dist # 配布物にPDF・個人データが無いか検査

# GUI E2E（Linuxは xvfb-run -a を前に付ける）
npm run test:e2e
```

PDF.js は `vendor/pdfjs/` に同梱（`npm run vendor:pdfjs` で node_modules から再生成）。ビルド不要のまま、ブラウザ版・デスクトップ版の両方で動く。

初期データ：`data/papers.json` 52件。`data/seed.js` は同じ初期データのブラウザ版。初期資料にPDF本文は含まない。

UIはあえてビルドツール不要の素のHTML/CSS/JavaScript。Claude Codeで起動しやすくするため。React/TypeScriptやSQLiteへの移行は後続で判断すること（現状はユーザーデータをOSの `userData` 内のJSONにアトミック保存）。
