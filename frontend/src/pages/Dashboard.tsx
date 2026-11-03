import { Fragment } from 'react'
import { Link } from 'react-router-dom'
import { Bar as RBar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api } from '../core/api'
import { Badge, Bar, Card, Loading, SourceRef, Stat, useAsync } from '../components/ui'

const ST_COLORS: Record<string, string> = { 未確認: '#b9c2c0', 目録確認: '#8fb3d9', 読了: '#2f8f83', 数値検証済み: '#0f5b5c' }

export default function Dashboard() {
  const { data: d, error } = useAsync(api.dashboard)
  if (!d) return <Loading error={error} />
  const years = Object.entries(d.by_year as Record<string, Record<string, number>>).map(([y, c]) => ({ year: y, ...c }))
  return (
    <div className="page">
      <h1>研究ダッシュボード</h1>
      <p className="lead">井口研究室（住宅班）空気清浄度研究 2018〜2026年度。資料取得日: Box 2026-11-02。数値は資料台帳の調査状態に基づく。</p>
      <div className="stats">
        <Stat label="収集済み資料" value={d.counts.sources} />
        <Stat label="読了（数値検証含む）" value={d.counts.read} sub={`未読 ${d.counts.unread}`} />
        <Stat label="知見" value={d.counts.findings} />
        <Stat label="未解決問題" value={d.counts.questions} />
        <Stat label="研究テーマ候補" value={d.counts.themes} />
        <Stat label="保存データセット" value={d.counts.datasets} />
      </div>
      <div className="grid2">
        <Card title="年度別の資料調査状況">
          <div className="chart" style={{ height: 240 }}>
            <ResponsiveContainer>
              <BarChart data={years} margin={{ left: -20, right: 8 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--grid)" />
                <XAxis dataKey="year" tick={{ fontSize: 11 }} /><YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                <Tooltip /><Legend wrapperStyle={{ fontSize: 12 }} />
                {Object.keys(ST_COLORS).map((k) => <RBar key={k} dataKey={k} stackId="a" fill={ST_COLORS[k]} />)}
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card title="研究の進捗（資料探索・分析・アプリ）">
          {Object.entries(d.progress as Record<string, { done: number; total: number }>).map(([k, v]) => <div key={k} className="prog"><span>{k}</span><Bar done={v.done} total={v.total} /></div>)}
          <h3>次に実施する作業</h3>
          <ol className="todo">{d.next_actions.map((a: string) => <li key={a}>{a}</li>)}</ol>
        </Card>
      </div>
      <Card title="年度別の研究状況">
        <div className="timeline">
          {d.studies.map((s: any) => (
            <div key={s.id} className="tl-item">
              <div className="tl-year">{s.fiscal_year}</div>
              <div><b>{s.label}</b><div className="muted small">{s.question}</div>
                <div className="small">{s.outcome}</div>
                <div className="small refs">{s.sources.map((x: string) => <SourceRef key={x} id={x} />)}</div></div>
            </div>
          ))}
        </div>
      </Card>
      <div className="grid2">
        <Card title="主要な研究成果" actions={<Link to="/graph">グラフで見る →</Link>}>
          <ul className="flist">{d.key_findings.map((f: any) => <li key={f.id}><Badge cls={f.class} /> {f.text} <span className="refs">{f.sources.map((x: string) => <SourceRef key={x} id={x} />)}</span></li>)}</ul>
        </Card>
        <Card title="重要な未解決問題" actions={<Link to="/plan">研究計画へ →</Link>}>
          <ul className="flist">{d.open_questions.map((q: any) => <li key={q.id}><b>{q.id}</b> {q.text} <span className="muted small">（{q.status}）</span></li>)}</ul>
        </Card>
      </div>
      <Completeness />
      <Card title="最近の操作履歴">
        {d.activity.length ? <ul className="small">{d.activity.map((a: any) => <li key={a.id}>{a.at.replace('T', ' ').slice(0, 19)} — {a.action} {a.target}</li>)}</ul> : <p className="muted">まだ操作履歴はありません</p>}
      </Card>
    </div>
  )
}

/** 研究単位ごとの完成度（RESEARCH_COMPLETENESS.json, 13項目の監査） */
function Completeness() {
  const { data } = useAsync(api.knowledge)
  const c = data?.completeness
  if (!c) return null
  const cell = (v: string) => <td className={`cp cp-${v === '済' ? 'ok' : v === '一部' ? 'part' : v === '不能' ? 'ng' : v === '対象外' ? 'na' : 'no'}`} title={v}>{v === '済' ? '●' : v === '一部' ? '◐' : v === '不能' ? '×' : v === '対象外' ? '—' : '○'}</td>
  return (
    <Card title="研究ごとの検証完成度（●済 ◐一部 ○未 ×取得不能 —対象外）" actions={<Link to="/learn">学習モードへ →</Link>}>
      <div className="tablewrap"><table className="cptable"><thead><tr><th>研究</th><th>分類</th>{c.items.map((i) => <th key={i} className="vert">{i}</th>)}<th>済</th></tr></thead>
        <tbody>{c.units.map((u) => <tr key={u.id}><td><b>{u.year}</b> {u.title}<div className="small muted">{u.notes}</div></td><td className="small">{u.cls}</td>{c.items.map((i) => <Fragment key={i}>{cell(u.items[i])}</Fragment>)}<td>{u.score}</td></tr>)}</tbody></table></div>
      <p className="small muted">『完全検証済み』の研究はない。各研究の根拠は verification/ の AUDIT.md と知見IDに記録。</p>
    </Card>
  )
}
