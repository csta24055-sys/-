#!/usr/bin/env python3
"""Generate research/FULL_SCOPE_EXECUTION_PLAN.md from the registries (no hand-typed counts)."""
import csv, collections
from pathlib import Path
R = Path(__file__).resolve().parents[1]
def rows(n):
    p = R / 'registry' / n
    if not p.exists(): return []
    with p.open(encoding='utf-8-sig', newline='') as f: return list(csv.DictReader(f))
axes, legacy, plans, comps, extra = rows('research_axes.csv'), rows('search_queries_candidates.csv'), rows('search_plans.csv'), rows('competitor_candidates.csv'), rows('additional_axes.csv')
lq = collections.Counter(q['axis_id'] for q in legacy)
by = collections.OrderedDict()
for a in axes: by.setdefault((a['axis_id'], a['axis_name'], a['priority']), []).append(a)
L = ['# 全範囲の実行計画（台帳から自動生成）', '',
     '継続指示（2026-11-12）に基づく。重要度は**実行の順序**にだけ使い、対象の削除・記録だけの代替・実行済みとの判定には使わない。', '',
     '## 1. 対象の件数（固定）', '',
     f'| 対象 | 件数 | 台帳 | 実行状態の台帳 |', '|---|---:|---|---|',
     f'| 研究軸 | {len(by)} | `registry/research_axes.csv` | — |',
     f'| 下位テーマ | {len(axes)} | 同上 | `registry/topic_execution_status.csv` |',
     f'| 調査計画 | {len(plans)} | `registry/search_plans.csv` | 同上 |',
     f'| 旧検索候補 | {len(legacy)} | `registry/search_queries_candidates.csv` | `registry/query_execution_status.csv` |',
     f'| 競合・代替候補 | {len(comps)} | `registry/competitor_candidates.csv` | `registry/competitor_execution_status.csv` |',
     f'| 追加仮説のテーマ（元ZIP外・別枠） | {len(extra)} | `registry/additional_axes.csv` | `registry/additional_topic_status.csv` |', '',
     '## 2. テーマ1件ごとの必須研究ユニット', '',
     '1. 操作的定義・母集団と観測単位・関係する事業上の問いを書く。',
     '2. 旧検索候補を**検索語のまま1回ずつ**実行する（該当テーマに登録がある場合）。',
     '3. 一次資料の経路、独立した別系統の経路、反例の経路を、それぞれ具体的な検索語で実行する。見つからない経路は言い換えて再検索してから「見つからず」とする。',
     '4. 有望な原文を取得して読む。遮断されたページは遮断と記録し、迂回しない。',
     '5. 採用する資料には原文の引用を付ける。引用は取得した本文と機械照合し、一致しないものは採用しない。',
     '6. 観測値（引用つき）、実行すべき計算、識別できない量（理由・必要なデータ・識別に使える実験・記号式）を記録する。',
     '7. 他軸との関係、資料間の食い違い、製品要件への波及を記録する。影響がなくても記録は残す。', '',
     '検索が実行されたかどうかは、作業記録（実行ログ）から機械的に抽出して判定する。作業者の自己申告だけでは実行済みにしない。', '',
     '## 3. 軸ごとの対象', '', '| 軸 | 名称 | 優先（順序のみ） | テーマ | 旧検索候補 | 調査計画 |', '|---|---|---|---:|---:|---:|']
pc = collections.Counter(p['axis_id'] for p in plans)
for (i, n, p), ts in by.items(): L.append(f'| {i} | {n} | {p} | {len(ts)} | {lq[i]} | {pc[i]} |')
L += [f'| 合計 | | | {len(axes)} | {len(legacy)} | {len(plans)} |', '', '旧検索候補は元の28軸・224テーマにだけ登録されている（各4件）。再設計で追加した101テーマには旧候補がなく、調査計画の3経路で探索する。', '',
      '## 4. 競合・代替候補', '', '| 優先（順序のみ） | 件数 |', '|---|---:|']
for k, v in sorted(collections.Counter(c['research_priority'] for c in comps).items()): L.append(f'| {k} | {v} |')
L += ['', '| 区分 | 件数 |', '|---|---:|'] + [f'| {k} | {v} |' for k, v in collections.Counter(c['market_role'] for c in comps).most_common()]
L += ['', '候補1件ごとに、公式サイト／機能と処理経路／料金と制限／入出力形式／PPTXの編集可否／生成速度の公表値／品質の表明／出典検証／データの送信と保持／学校・仕事への適合／無料代替の強さ、の11項目と、独立した反例を探索する。公式サイトが遮断された場合は、事業者自身が書いた別の一次資料（別サブドメイン、公式リリース、アプリストアの掲載文、公式README）を探す。確認できない項目は空欄のまま理由を記録し、確認済みとしない。実機での試験は行わないため、性能の点数は付けない。', '',
      '## 5. 追加仮説（元ZIPに含まれない要件）', '', '継続指示で追加された仮説。元の325テーマを削らず、別枠のテーマとして調べ、関係する既存テーマに結び付ける。', '',
      '| 要件ID | 追加テーマ | 内容 | 結び付く既存テーマ |', '|---|---|---|---|']
for e in extra: L.append(f"| {e['requirement_id']} | {e['topic_id']} | {e['topic_name']} | {e['mapped_existing_topics'].replace(';', '、')} |")
L += ['', '- N01：小規模運営・高性能エンジン・買収前提設計（買収、技術ライセンス、提携、少人数運営、速度・安定性・原価）', '- N02：実演動画広告', '- N03：無料版広告', '',
      '## 6. 工程と順序', '',
      '| 工程 | 内容 | 通過の条件（機械検査） |', '|---|---|---|',
      '| S0 | 再監査と範囲の固定 | 件数が固定値と一致、状態台帳が再計算と一致、暫定成果物が隔離されている |',
      '| S1 | 全テーマ・全旧検索候補・全競合の収集 | 325テーマの研究ユニットが揃い、896件が実行済みまたは実行不能の証跡つき、80候補が探索済み |',
      '| S2 | 採用資料の全件精査 | 全資料が精査済み、引用・箇所・種別・起源・日付がある、独立起源数が再計算と一致 |',
      '| S3 | 代表性と軸間の関係 | 実測資料の代表性を全件評価、32軸の関係を記述、識別できない量を一覧化 |',
      '| S4 | 競合の個別監査 | 80候補を比較可能・不能に分け、確認済み項目はすべて精査済み資料に結び付く |',
      '| S5 | 計算の全件処理 | 全計算IDが実行・検算済み／識別不能／データ不足／方法として不適、のいずれか |',
      '| S6 | 全軸の統合 | 32軸それぞれの総合と、全体の統合モデル |',
      '| S7 | 製品案A〜Gと追加仮説の比較 | 同じ指標と状況で比較、反対仮説と逆転条件を記述 |',
      '| S8 | 網羅の監査 | 全要件の追跡、主張と出典の結び付き、アプリ未変更の確認 |',
      '| S9 | 正式成果物 | S0〜S8がすべて通過した場合だけ作成 |', '',
      '前の工程が通るまで次の工程の文書は作らない。既存の暫定成果物5点は `deliverables/PROVISIONAL_QUARANTINED/` に隔離してあり、S9まで正式版として扱わない。', '',
      '## 7. 再開のしかた', '', '```', 'python3 scripts/build_status.py            # 状態台帳を再計算', 'python3 scripts/research_gates.py evaluate # ゲート評価と GATE_AUDIT_DETAIL.md の更新', '```', '',
      '未達のテーマ・検索候補・競合は `research/GATE_AUDIT_DETAIL.md` と各状態台帳の `blockers` 列に出る。', '']
(R / 'research' / 'FULL_SCOPE_EXECUTION_PLAN.md').write_text('\n'.join(L), encoding='utf-8')
print('plan written', len('\n'.join(L)))
