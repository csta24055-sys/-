#!/usr/bin/env python3
"""Generate search *candidates*, not claims or observed results.

Claude Code must check every query, modify it for the domain, and log only searches
it actually performs in registry/search_log.csv.
"""
from pathlib import Path
import csv
ROOT=Path(__file__).resolve().parents[1]
with (ROOT/'registry'/'research_axes.csv').open(encoding='utf-8-sig',newline='') as f:
    topics=list(csv.DictReader(f))
classes=[
 ('PRIMARY','一次資料',lambda t:f'{t} 公式 統計 調査 報告書 2025 2026'),
 ('USER_VOICE','実際の利用者',lambda t:f'{t} AI 資料作成 実際に使った 不満 比較'),
 ('COUNTEREXAMPLE','反対証拠',lambda t:f'{t} 生成AI 使えない 弱点 誤り 導入しない 理由'),
 ('INTERNATIONAL','海外比較',lambda t:f'{t} AI document presentation workflow survey research 2025 2026'),
]
with (ROOT/'registry'/'search_queries_candidates.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f);w.writerow(['suggestion_id','axis_id','topic_id','target','sample_query','state','last_searched','notes'])
    for t in topics:
        for j,(key,_,fn) in enumerate(classes,1):
            w.writerow([f'{t["topic_id"]}_Q{j}',t['axis_id'],t['topic_id'],key,fn(t['topic_name']),'SUGGESTED_NOT_RUN','','要レビュー。検索語は提案であり、実際に検索した証拠ではない'])
print('wrote',len(topics)*len(classes),'query candidates')
