# research_pipeline

資料収集 → 論文改訂 → 教材改訂を連動させ、論文・教材・確認問題の全ての文を一次資料の原文位置まで追跡する処理一式（標準ライブラリのみ）。研究内容（台帳・論文・教材）はこのリポジトリに含めない（公開リポジトリのため。正本は Dropbox、ローカルでは `.gitignore` 済みの `AI_WORLD_PRIMARY_RESEARCH/`）。

| モジュール | 役割 |
|---|---|
| `ledger.py` | 台帳 CSV（資料・主張・人物・モデル・実験・予測など）の列・ID・参照の検証 |
| `blocks.py` | ブロック付き Markdown 正本の読み取り。ブロックの外の本文は「根拠のない文」としてエラー |
| `trace.py` | 追跡監査（教材が論文段落に無い主張を使わない、効果の主張には独立実証が必要、学習目標と問題の対応、`eval` を使わない検算）と、指紋による要改訂（STALE）の伝播 |
| `render.py` | structlab-exam と同じブロック形式で内容を組み、Markdown と PDF/Word（structlab-exam の `render.py` を再利用）に出力 |
| `verify_excerpts.py` | 原文スナップショットとの一字一句照合と、見出し位置の特定 |
| `pipeline.py` | 段階実行（ledgers → trace → render → office → sync_plan）、`STATUS.json` による途中再開、承認、影響分析、Dropbox 同期計画 |
| `common.py` | 既存の `math_interop_v0/phase1.py` の `canonical`/`digest`/`require` を再利用。一時ファイル経由の書き込み、Dropbox content_hash |

```bash
python3 -I -m unittest discover -s research_pipeline/tests -t .     # 合成データのテスト
python3 -I research_pipeline/pipeline.py run --structlab <structlab の src>   # 研究フォルダは AI_RESEARCH_ROOT で変更可
python3 -I research_pipeline/pipeline.py impact
python3 -I research_pipeline/pipeline.py approve --scope all --all-new --reason "理由"
```

同期先の Dropbox フォルダは環境変数 `AI_RESEARCH_DROPBOX_ROOT` で指定する（既定 `/AI_WORLD_PRIMARY_RESEARCH`）。
