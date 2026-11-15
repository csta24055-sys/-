"""research_learning: 研究論文から学習教材を作る第3の成果物系列（指示書 第10部）。

structlab-exam（csta24055-sys/structural-experiment-ai, ブランチ claude/busy-fermat-ybka8s）から、
検証済みの部品だけを抽出・適応した独立モジュール。元のリポジトリは変更しない。
来歴（2026-11-15 に GitHub から取得して確認）:
  - 全文ダンプ docs/code_dump/exam_system_code_dump.txt = commit cdddcd0（27ファイル一致を機械照合）
  - 移植元は最新 commit 33a45ea（cdddcd0 から render.py などが修正済み）。元のテストは 33a45ea で 67 件合格
移植したもの: office.py（render.py の PDF/Word 出力と品質検査＋追加検査）、dumpfile.py（tools/restore_dump.py の
解析部）、urls.py（links.py の正規化を一般 URL 向けに再設計）。
移植しないもの: 授業資料の入力（discover/box/links の Box 専用部分）、教員発言の検出（cues）、
出題予測の判定（scoring の点数・閾値）、規則ベースの自動問題生成（questions）。理由は audit/structlab_exam_reuse.md。
"""
