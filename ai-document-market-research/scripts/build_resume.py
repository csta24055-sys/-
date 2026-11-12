#!/usr/bin/env python3
"""Write research/NEXT_STEPS.md: where the work stopped and how to resume (generated from the ledgers)."""
import csv, json, sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_status, research_gates
R = Path(__file__).resolve().parents[1]
res = research_gates.assess(R)
st = build_status.compute(R / 'registry', write_files=False)
log = research_gates.read_csv(R / 'registry' / 'search_log.csv')
real = [x for x in log if x.get('verified_by', '').startswith('TRANSCRIPT') and x['platform'] == 'web_search_engine' and x['retrieval_status'] == 'SNIPPET_ONLY']
refused = [x for x in log if x['retrieval_status'] == 'REFUSED_BUDGET']
last = max((x['searched_at'] for x in log), default='')
t_open = [t['topic_id'] for t in st['trows'] if t['gate_state'] != 'S1_DONE']
a_open = [t['topic_id'] for t in st['arows'] if t['gate_state'] != 'S1_DONE']
c_open = [c['competitor_id'] for c in st['crows'] if c['gate_state'] != 'S1_DONE']
q = Counter(x['state'] for x in st['qrows'])
unmet = [f"{k} {v['state']}" for k, v in res['steps'].items() if v['state'] != 'PASS']
L = ['# 再開手順（台帳から自動生成）', '', f"RESEARCH_STATUS = {res['research_status']}（最初に未達の工程：{res['first_unmet_stage']}）", '',
     '## いまの状態', '',
     f'- 最後に記録された処理の時刻（UTC）：{last}',
     f"- テーマ：S1完了 {len(st['trows']) - len(t_open)} / {len(st['trows'])}、未完了 {len(t_open)}",
     f"- 旧検索候補：実行済み {q['EXECUTED']}、実行不能 {q['ATTEMPTED_BLOCKED']}、未実行 {q['NOT_EXECUTED']}（計 {sum(q.values())}）",
     f"- 競合候補：S1完了 {len(st['crows']) - len(c_open)} / {len(st['crows'])}、未完了 {len(c_open)}",
     f"- 追加仮説のテーマ：S1完了 {len(st['arows']) - len(a_open)} / {len(st['arows'])}",
     f'- 作業員が実際に実行できたWeb検索：{len(real)} 件。上限超過で拒否された検索：{len(refused)} 件（実行済みに数えていない）',
     f"- 採用資料：{res['accepted_rows']}（S2精査済み {res['verified_rows']}）", '',
     '## 未完了のID（先頭）', '',
     '- テーマ：' + ('、'.join(t_open[:40]) + (f' ほか{len(t_open) - 40}件' if len(t_open) > 40 else '') if t_open else 'なし'),
     '- 追加テーマ：' + ('、'.join(a_open) or 'なし'),
     '- 競合：' + ('、'.join(c_open[:40]) + (f' ほか{len(c_open) - 40}件' if len(c_open) > 40 else '') if c_open else 'なし'),
     '- 全件は `registry/topic_execution_status.csv`、`registry/query_execution_status.csv`、`registry/competitor_execution_status.csv` の `gate_state`・`blockers` 列。', '',
     '## 未達のゲート', '', '- ' + '、'.join(unmet), '- 詳細は `research/GATE_AUDIT_DETAIL.md`。', '',
     '## 制約', '',
     '- Web検索は1ターンあたり200回が上限で、全作業員で共有される。超過分は実行されず、拒否として記録される（実行済みには数えない）。このため収集は、1ターン200回以内の束（バッチ）に分けて進める。',
     '- 取得を拒否するサイトは迂回しない。検索上限の回避（他の手段での検索）もしない。', '',
     '## 再開コマンド', '', '```',
     '# 1) 作業員の実行記録と出力を台帳へ取り込む（STAGING・CACHE・実行記録の場所は環境に合わせる）',
     'scripts/refresh.sh "$STAGING" "$CACHE" "$TRANSCRIPTS"',
     '# 2) ゲート評価と監査詳細の更新',
     'python3 scripts/research_gates.py evaluate && python3 scripts/build_resume.py',
     '# 3) 次の束を計画する（検索200回以内、未完了の単位を優先順に）',
     'python3 scripts/next_batch.py "$TASKS" "$STAGING" 200 5',
     '# 4) 出力された単位を作業員に割り当てて実行し、1) に戻る',
     '```', '',
     'S1が通過するまで、S2以降の文書と正式成果物は作らない。', '']
(R / 'research' / 'NEXT_STEPS.md').write_text('\n'.join(L), encoding='utf-8')
print(L[2]); print('\n'.join(L[6:12]))
