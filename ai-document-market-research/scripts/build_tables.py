#!/usr/bin/env python3
"""Generate research/SOURCES.md and research/COVERAGE_TABLE.md from the ledgers (no hand-typed counts)."""
import csv, collections
from pathlib import Path
R = Path(__file__).resolve().parents[1]
def rows(n):
    with (R/'registry'/n).open(encoding='utf-8-sig', newline='') as f: return list(csv.DictReader(f))
src, log, axes, comp = rows('source_evidence.csv'), rows('search_log.csv'), rows('research_axes.csv'), rows('competitor_candidates.csv')
acc = [s for s in src if s['is_accepted'] == 'yes']
act = [r for r in log if 'same_action_as=' not in r['notes']]
L = ['# 採用した出典（台帳から自動生成）', '',
     f'原文を開いて該当箇所を確認した資料 {len(acc)} 件（独立した起源 {len({s["origin_group_id"] for s in acc})} 件）。「採用」は原文確認済みの意味で、内容の真偽を保証しない。企業の公式ページは当事者の表明である。', '',
     '| ID | 発行元 | 種別 | 起源 | 主テーマ | 確認日時(UTC) | URL |', '|---|---|---|---|---|---|---|']
for s in acc:
    L.append(f"| {s['source_id']} | {s['publisher'].replace('|','/')} | {s['source_type']} | {s['origin_group_id']} | {s['topic_id']} | {s['checked_at']} | {s['url']} |")
L += ['', '## 種別ごとの件数', ''] + [f'- {k}: {v}' for k, v in collections.Counter(s['source_type'] for s in acc).most_common()]
L += ['', '## 複数の資料を出している起源（独立数の計算では1件）', '']
og = collections.defaultdict(list)
for s in acc: og[s['origin_group_id']].append(s['source_id'])
L += [f'- {k}: {", ".join(v)}' for k, v in og.items() if len(v) > 1]
(R/'research'/'SOURCES.md').write_text('\n'.join(L) + '\n', encoding='utf-8')

by = collections.OrderedDict()
for a in axes: by.setdefault((a['axis_id'], a['axis_name'], a['priority']), collections.Counter())[a['stage']] += 1
T = ['# 収集範囲の集計表（台帳から自動生成）', '',
     f'- 実行した検索・アクセス：{len(act)} 件（Web検索 {sum(r["platform"]=="web_search_engine" for r in act)}、ページ取得成功 {sum(r["retrieval_status"]=="RETRIEVED_FULL_TEXT" for r in act)}、取得不可 {sum(r["retrieval_status"]=="BLOCKED" for r in act)}）',
     f'- 検索ログの行数：{len(log)}（うち {len(log)-len(act)} 行は、読んだ資料を別テーマの観点でも確認したことを示す行で、新たな検索ではない）',
     f'- テーマ325件の内訳：採用証拠あり {sum(a["stage"]=="EVIDENCE_ACCEPTED" for a in axes)}、試行したが採用証拠なし {sum(a["stage"]=="ATTEMPTED_NO_ACCEPTED_SOURCE" for a in axes)}、未着手 {sum(a["stage"]=="NOT_STARTED" for a in axes)}',
     f'- 競合候補80件の内訳：公式資料で確認 {sum(c["verification_state"]=="VERIFIED_OFFICIAL" for c in comp)}、未検証 {sum(c["verification_state"]!="VERIFIED_OFFICIAL" for c in comp)}（P0は21件中 {sum(c["verification_state"]=="VERIFIED_OFFICIAL" and c["research_priority"]=="P0" for c in comp)} 件を確認）', '',
     '| 軸 | 名称 | 優先 | 採用証拠あり | 試行のみ | 未着手 |', '|---|---|---|---:|---:|---:|']
for (i, n, p), c in by.items():
    T.append(f"| {i} | {n} | {p} | {c['EVIDENCE_ACCEPTED']} | {c['ATTEMPTED_NO_ACCEPTED_SOURCE']} | {c['NOT_STARTED']} |")
T += ['', '## 取得できなかったページ', '', '| 対象 | 理由 | 関係するテーマ |', '|---|---|---|']
for r in act:
    if r['retrieval_status'] == 'BLOCKED': T.append(f"| {r['query'].replace('GET ','')} | {r['blocked_reason']} | {r['topic_id']} |")
T += ['', '## 未着手のテーマ一覧', '']
cur = None
for a in axes:
    if a['stage'] != 'NOT_STARTED': continue
    if a['axis_id'] != cur: cur = a['axis_id']; T.append(f"- **{cur} {a['axis_name']}**：" )
    T[-1] += f" {a['topic_id'][-3:]} {a['topic_name']}／"
(R/'research'/'COVERAGE_TABLE.md').write_text('\n'.join(T) + '\n', encoding='utf-8')
print(T[2]); print(T[4]); print(T[5]); print(L[2])
