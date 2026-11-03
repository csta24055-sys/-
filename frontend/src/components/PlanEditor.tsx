import { useState } from 'react'
import { api, download, Plan, Theme } from '../core/api'
import { Card, Field, useAsync } from './ui'

const FIELDS: [keyof Plan, string][] = [
  ['background', '研究背景'], ['purpose', '研究目的'], ['hypotheses', '仮説（競合仮説を含む）'], ['methods', '実験方法'], ['equipment', '必要設備（確認状況）'],
  ['measurements', '測定項目・条件'], ['analysis', '解析方法'], ['schedule', '実験スケジュール'], ['risks', 'リスク'], ['alternatives', '代替計画'], ['references', '参考資料（資料ID・DOI）'],
]

const fromTheme = (t: Theme): Plan => ({
  title: `${t.id} ${t.name}（研究計画案）`, theme_id: t.id, background: t.why_now, purpose: t.unsolved, hypotheses: t.hypotheses.join(', '),
  methods: t.procedure, equipment: t.equipment, measurements: t.measurements, analysis: t.analysis, schedule: t.duration_cost,
  risks: t.risks, alternatives: t.evaluation?.failure_mode || '', references: t.evaluation?.evidence || '',
})

const toMd = (p: Plan) => [`# ${p.title}`, '', `テーマ: ${p.theme_id || '—'}　更新: ${p.updated_at || '未保存'}`, '', ...FIELDS.flatMap(([k, l]) => [`## ${l}`, '', String(p[k] || ''), ''])].join('\n')

/** 学生が自分の研究計画を作成・編集・保存する（サーバーDBに保存） */
export default function PlanEditor({ themes }: { themes: Theme[] }) {
  const { data: plans, reload } = useAsync(api.plans)
  const [cur, setCur] = useState<Plan | null>(null)
  const [msg, setMsg] = useState('')
  const save = async () => {
    if (!cur) return
    if (!cur.title.trim()) { setMsg('タイトルを入力してください'); return }
    try {
      const saved = cur.id ? await api.updatePlan(cur.id, cur) : await api.createPlan(cur)
      setCur(saved); setMsg('保存しました'); reload()
    } catch (e: any) { setMsg('保存失敗: ' + e.message) }
  }
  return (
    <Card title="自分の研究計画（作成・編集・保存）">
      <div className="filters">
        <select value="" onChange={(e) => { const t = themes.find((x) => x.id === e.target.value); if (t) { setCur(fromTheme(t)); setMsg('テーマから下書きを作成（未保存）') } }}>
          <option value="">テーマから新規作成…</option>{themes.map((t) => <option key={t.id} value={t.id}>{t.id} {t.name}</option>)}
        </select>
        <button className="ghost" onClick={() => { setCur({ title: '新しい研究計画' }); setMsg('') }}>空の計画を作成</button>
        <span className="small muted">{msg}</span>
      </div>
      {plans && plans.length > 0 && (
        <div className="tablewrap"><table><thead><tr><th>計画</th><th>テーマ</th><th>更新</th><th></th></tr></thead>
          <tbody>{plans.map((p) => <tr key={p.id}><td><a href="#plan-edit" onClick={() => setCur(p)}>{p.title}</a></td><td>{p.theme_id || '—'}</td><td className="small">{p.updated_at?.slice(0, 16).replace('T', ' ')}</td>
            <td><button className="ghost" onClick={() => download(`${p.title}.md`, toMd(p), 'text/markdown;charset=utf-8')}>Markdown</button>
              <button className="ghost" onClick={async () => { if (p.id && confirm(`「${p.title}」を削除しますか`)) { await api.deletePlan(p.id); if (cur?.id === p.id) setCur(null); reload() } }}>削除</button></td></tr>)}</tbody></table></div>
      )}
      {cur && (
        <div id="plan-edit" className="plan-edit">
          <Field label="タイトル"><input value={cur.title} onChange={(e) => setCur({ ...cur, title: e.target.value })} maxLength={200} /></Field>
          <Field label="テーマ"><select value={cur.theme_id || ''} onChange={(e) => setCur({ ...cur, theme_id: e.target.value || null })}><option value="">—</option>{themes.map((t) => <option key={t.id} value={t.id}>{t.id}</option>)}</select></Field>
          {FIELDS.map(([k, l]) => <Field key={k} label={l}><textarea rows={3} value={String(cur[k] || '')} onChange={(e) => setCur({ ...cur, [k]: e.target.value })} /></Field>)}
          <div className="filters"><button onClick={save}>{cur.id ? '更新を保存' : '保存'}</button><button className="ghost" onClick={() => download(`${cur.title}.md`, toMd(cur), 'text/markdown;charset=utf-8')}>Markdown出力</button></div>
        </div>
      )}
    </Card>
  )
}
