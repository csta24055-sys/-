import { useState } from 'react'
import { PolarAngleAxis, PolarGrid, Radar, RadarChart, ResponsiveContainer, Tooltip } from 'recharts'
import { api, Theme } from '../core/api'
import { Card, Field, Loading, useAsync } from '../components/ui'

const W = { importance: 0.35, novelty: 0.2, feasibility: 0.25, fit: 0.2 }
const LABEL = { importance: '重要度', novelty: '新規性', feasibility: '実行可能性', fit: '設備適合' }
const total = (t: Theme, w = W) => (Object.keys(w) as (keyof typeof W)[]).reduce((s, k) => s + t.scores[k] * w[k], 0)

const FIELDS: [keyof Theme, string][] = [
  ['why_now', 'なぜ今研究するべきか'], ['known', '既往研究から判明していること'], ['unsolved', '未解決の科学的問題'], ['equipment', '必要な実験装置'],
  ['measurements', '測定項目と実験条件'], ['procedure', '実験手順'], ['analysis', '解析方法'], ['data_needed', '必要なデータ'], ['branches', '予想される結果の分岐'],
  ['difficulty', '実施難易度'], ['duration_cost', '期間・費用の概算'], ['significance', '学術的・実用的意義'], ['risks', '失敗する可能性と代替手段'],
]

export default function ResearchPlan() {
  const { data: k, error, reload } = useAsync(api.knowledge)
  const [w, setW] = useState(W)
  const [open, setOpen] = useState<string | null>('T-01')
  const [newQ, setNewQ] = useState('')
  const [msg, setMsg] = useState('')
  if (!k) return <Loading error={error} />
  const ranked = [...k.themes].sort((a, b) => total(b, w) - total(a, w))
  const decide = async (t: Theme, decision: string) => {
    const reason = prompt(`「${t.name}」を${decision}とする理由`, t.decision_reason || '')
    if (reason === null) return
    try { await api.patchItem('theme', t.id, { decision, decision_reason: reason }); reload(); setMsg('保存しました') } catch (e: any) { setMsg('保存失敗: ' + e.message) }
  }
  return (
    <div className="page">
      <h1>今後の研究計画</h1>
      <p className="lead">研究テーマ候補 {k.themes.length} 件を重要度・新規性・実行可能性・既存設備との適合性で比較。重みは変更可能（評価は【分析】）。</p>
      <Card title="評価の重み">
        <div className="row4">{(Object.keys(W) as (keyof typeof W)[]).map((key) => (
          <Field key={key} label={`${LABEL[key]} ${w[key].toFixed(2)}`}><input type="range" min={0} max={1} step={0.05} value={w[key]} onChange={(e) => setW({ ...w, [key]: Number(e.target.value) })} /></Field>
        ))}</div>
        <span className="small muted">{msg}</span>
      </Card>
      <div className="tablewrap">
        <table className="rank"><thead><tr><th>順位</th><th>ID</th><th>テーマ</th><th>期間</th><th>重要</th><th>新規</th><th>実行</th><th>適合</th><th>総合</th><th>採否</th></tr></thead>
          <tbody>{ranked.map((t, i) => (
            <tr key={t.id} className={open === t.id ? 'active' : ''} onClick={() => setOpen(t.id)}>
              <td>{i + 1}</td><td>{t.id}</td><td>{t.name}</td><td>{t.horizon}</td>
              <td>{t.scores.importance}</td><td>{t.scores.novelty}</td><td>{t.scores.feasibility}</td><td>{t.scores.fit}</td><td><b>{total(t, w).toFixed(2)}</b></td>
              <td>{t.decision ? <span className={`pill ${t.decision === '採択' ? 'st-3' : t.decision === '不採択' ? 'st-0' : 'st-1'}`}>{t.decision}</span> : '—'}</td>
            </tr>))}</tbody></table>
      </div>
      <Card title="実現可能性・新規性・設備・期間・失敗リスクの比較（2026-11 資料読解・数値検証を反映）【分析】">
        <div className="tablewrap"><table><thead><tr><th>ID</th><th>実現可能性</th><th>新規性</th><th>必要設備</th><th>期間[月]</th><th>失敗リスク</th><th>失敗時の代替</th></tr></thead>
          <tbody>{ranked.filter((t) => t.evaluation).map((t) => { const e = t.evaluation!; return (
            <tr key={t.id} onClick={() => setOpen(t.id)}><td>{t.id}</td><td>{e.feasibility}</td><td>{e.novelty}</td><td>{e.equipment}</td>
              <td>{e.months[0] === e.months[1] ? e.months[0] : `${e.months[0]}〜${e.months[1]}`}</td>
              <td><span className={`pill ${e.failure_risk === '低' ? 'st-3' : e.failure_risk === '高' ? 'st-0' : 'st-1'}`}>{e.failure_risk}</span></td><td>{e.failure_mode}</td></tr>) })}</tbody></table></div>
        <p className="small muted">スコアの変更: {ranked.filter((t) => t.evaluation?.score_change).map((t) => `${t.id} ${t.evaluation!.score_change}`).join('／') || 'なし'}</p>
      </Card>
      {ranked.filter((t) => t.id === open).map((t) => (
        <Card key={t.id} title={`${t.id} ${t.name}`} actions={<>{['採択', '保留', '不採択'].map((d) => <button key={d} className={t.decision === d ? '' : 'ghost'} onClick={() => decide(t, d)}>{d}</button>)}</>}>
          {t.decision && <p className="note">採否: <b>{t.decision}</b> — 理由: {t.decision_reason}</p>}
          <div className="grid2">
            <div>
              <p><b>期間</b>: {t.horizon}　<b>検証すべき仮説</b>: {t.hypotheses.join(', ') || '—'}</p>
              {FIELDS.map(([f, l]) => <div key={f} className="kv"><b>{l}</b><p>{String(t[f])}</p></div>)}
              {t.evaluation && <div className="kv"><b>評価の根拠（今回の資料読解・検証）</b><p>{t.evaluation.evidence}</p></div>}
            </div>
            <div className="chart" style={{ height: 260 }}>
              <ResponsiveContainer><RadarChart data={(Object.keys(LABEL) as (keyof typeof LABEL)[]).map((kk) => ({ k: LABEL[kk], v: t.scores[kk] }))}>
                <PolarGrid /><PolarAngleAxis dataKey="k" tick={{ fontSize: 11 }} /><Tooltip /><Radar dataKey="v" stroke="#0f5b5c" fill="#2f8f83" fillOpacity={0.4} isAnimationActive={false} />
              </RadarChart></ResponsiveContainer>
            </div>
          </div>
        </Card>
      ))}
      <Card title="研究仮説の比較（競合仮説）">
        {k.hypotheses.map((h) => (
          <details key={h.id}>
            <summary><b>{h.id}</b> {h.title} <span className="pill st-1">{h.status}</span></summary>
            <div className="tablewrap"><table><thead><tr><th>競合仮説</th><th>内容</th><th>判別方法</th></tr></thead>
              <tbody>{h.competing.map((c) => <tr key={c.label}><td>{c.label}</td><td>{c.text}</td><td>{c.test}</td></tr>)}</tbody></table></div>
            <p className="small">予想される分岐: {h.expected}</p>
            <Field label="状態を更新"><select value={h.status} onChange={async (e) => { await api.patchItem('hypothesis', h.id, { status: e.target.value }); reload() }}>
              {['未検証', '部分検証（計算）', '部分検証', '検証中', '支持', '棄却', '予測'].map((s) => <option key={s}>{s}</option>)}</select></Field>
          </details>
        ))}
      </Card>
      <Card title="ロードマップ">
        <div className="roadmap">{k.roadmap.map((r) => <div key={r.phase} className="phase"><h3>{r.phase}</h3><ul>{r.items.map((i) => <li key={i}>{i}</li>)}</ul></div>)}</div>
      </Card>
      <Card title="未解決問題の更新">
        <div className="tablewrap"><table><thead><tr><th>ID</th><th>優先</th><th>問題</th><th>状態</th></tr></thead>
          <tbody>{k.questions.map((q) => <tr key={q.id}><td>{q.id}</td><td>{q.priority}</td><td>{q.text}</td>
            <td><select value={q.status} onChange={async (e) => { await api.patchItem('question', q.id, { status: e.target.value }); reload() }}>
              {[...new Set([q.status, '未着手', '着手', '資料あり・未検証', '解決', '要確認（本論読了で解決可能性）'])].map((s) => <option key={s}>{s}</option>)}</select></td></tr>)}</tbody></table></div>
        <div className="filters"><input placeholder="新しい未解決問題" value={newQ} onChange={(e) => setNewQ(e.target.value)} />
          <button disabled={!newQ} onClick={async () => { await api.addQuestion({ text: newQ }); setNewQ(''); reload() }}>追加</button></div>
      </Card>
    </div>
  )
}
