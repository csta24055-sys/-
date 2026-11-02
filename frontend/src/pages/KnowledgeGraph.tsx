import { useMemo, useState } from 'react'
import { api, GraphNode, Knowledge } from '../core/api'
import { Badge, Card, Loading, SourceRef, useAsync } from '../components/ui'

const TYPES: Record<string, { color: string; col: number }> = {
  研究: { color: '#0f5b5c', col: 0 }, 装置: { color: '#8a6d1e', col: 1 }, 測定項目: { color: '#3a6ea5', col: 1 },
  成果: { color: '#2f8f83', col: 2 }, 仮説: { color: '#c8553d', col: 3 }, 未解決問題: { color: '#6b4c9a', col: 3 }, 研究テーマ: { color: '#b5446e', col: 4 },
}
const W = 1180, ROW = 24, COLX = [20, 250, 470, 770, 1000]

function layout(nodes: GraphNode[], edges: Knowledge['graph']['edges']) {
  // 種別ごとの列に配置し、隣接ノードの平均位置（重心法）で並べ替える決定的レイアウト
  const cols = new Map<number, GraphNode[]>()
  nodes.forEach((n) => { const c = TYPES[n.type]?.col ?? 2; cols.set(c, [...(cols.get(c) || []), n]) })
  const nbr = new Map<string, string[]>()
  edges.forEach((e) => { nbr.set(e.from, [...(nbr.get(e.from) || []), e.to]); nbr.set(e.to, [...(nbr.get(e.to) || []), e.from]) })
  const maxN = Math.max(...[...cols.values()].map((c) => c.length))
  const H = maxN * ROW + 40
  const pos = new Map<string, { x: number; y: number }>()
  const place = () => cols.forEach((ns, c) => {
    const gap = (H - 40) / ns.length
    ns.forEach((n, i) => pos.set(n.id, { x: COLX[c], y: 20 + gap * (i + 0.5) }))
  })
  place()
  for (let it = 0; it < 6; it++) {
    cols.forEach((ns, c) => {
      if (c === 0) return
      const key = (n: GraphNode) => { const ys = (nbr.get(n.id) || []).map((m) => pos.get(m)?.y).filter((v): v is number => v !== undefined); return ys.length ? ys.reduce((a, b) => a + b, 0) / ys.length : pos.get(n.id)!.y }
      ns.sort((a, b) => key(a) - key(b))
    })
    place()
  }
  return { pos, H }
}

export default function KnowledgeGraph() {
  const { data: k, error } = useAsync(api.knowledge)
  const [sel, setSel] = useState<string | null>('Y2026')
  const [hidden, setHidden] = useState<string[]>([])
  const [q, setQ] = useState('')
  const g = k?.graph
  const lay = useMemo(() => (g ? layout(g.nodes, g.edges) : null), [g])
  if (!k || !g || !lay) return <Loading error={error} />
  const { pos, H } = lay
  const visible = g.nodes.filter((n) => !hidden.includes(n.type))
  const vis = new Set(visible.map((n) => n.id))
  const nb = new Set(sel ? g.edges.filter((e) => e.from === sel || e.to === sel).flatMap((e) => [e.from, e.to]) : [])
  const node = g.nodes.find((n) => n.id === sel)
  const match = q ? new Set(g.nodes.filter((n) => (n.label + n.detail).includes(q)).map((n) => n.id)) : null
  const finding = k.findings.find((f) => f.id === sel)
  const hyp = k.hypotheses.find((h) => h.id === sel)
  const theme = k.themes.find((t) => t.id === sel)
  const study = k.studies.find((s) => s.id === sel)
  return (
    <div className="page">
      <h1>研究ナレッジグラフ</h1>
      <p className="lead">研究（年度）→ 装置・測定項目 → 成果 → 仮説・未解決問題 → 研究テーマ。ノードをクリックすると詳細と資料根拠を表示。</p>
      <div className="filters">
        {Object.entries(TYPES).map(([t, v]) => <label key={t} className="check"><input type="checkbox" checked={!hidden.includes(t)} onChange={(e) => setHidden(e.target.checked ? hidden.filter((h) => h !== t) : [...hidden, t])} /><span className="dot" style={{ background: v.color }} />{t}</label>)}
        <input type="search" placeholder="ノード検索" value={q} onChange={(e) => setQ(e.target.value)} />
      </div>
      <div className="graph-split">
        <div className="graphwrap">
          <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="研究ナレッジグラフ">
            {g.edges.filter((e) => vis.has(e.from) && vis.has(e.to)).map((e, i) => {
              const a = pos.get(e.from)!, b = pos.get(e.to)!, on = sel && (e.from === sel || e.to === sel)
              const mx = (a.x + b.x) / 2
              return <path key={i} d={`M${a.x},${a.y} C${mx},${a.y} ${mx},${b.y} ${b.x},${b.y}`} className={on ? 'edge on' : 'edge'} fill="none" />
            })}
            {visible.map((n) => {
              const p = pos.get(n.id)!, on = n.id === sel, near = nb.has(n.id), dim = (sel && !on && !near) || (match && !match.has(n.id))
              return (
                <g key={n.id} transform={`translate(${p.x},${p.y})`} className={`gnode${dim ? ' dim' : ''}`} onClick={() => setSel(n.id)} tabIndex={0} onKeyDown={(e) => e.key === 'Enter' && setSel(n.id)}>
                  <circle r={on ? 9 : n.type === '研究' ? 7 : 5} fill={TYPES[n.type]?.color || '#888'} stroke={on ? 'var(--fg)' : 'none'} strokeWidth={2} />
                  <text x={10} y={4}>{n.type === '成果' ? n.label.slice(0, 22) : n.label.slice(0, 16)}</text>
                </g>
              )
            })}
          </svg>
        </div>
        <div className="graph-detail">
          {node ? (
            <Card title={<><span className="dot" style={{ background: TYPES[node.type]?.color }} /> {node.type}: {node.id}</>}>
              <h3>{node.label}</h3>
              {finding && <p><Badge cls={finding.class} /> {finding.text}</p>}
              {study && <><p><b>問い:</b> {study.question}</p><p><b>方法:</b> {study.method}</p><p><b>結果:</b> {study.outcome}</p><p><b>引継ぎ:</b> {study.handover}</p></>}
              {hyp && <><p className="small">状態: {hyp.status}</p><ul>{hyp.competing.map((c) => <li key={c.label}><b>{c.label}</b>: {c.text}<br /><span className="small muted">判別: {c.test}</span></li>)}</ul><p className="small">{hyp.expected}</p></>}
              {theme && <><p>{theme.why_now}</p><p className="small">期間: {theme.horizon}／難易度: {theme.difficulty}</p></>}
              {!finding && !study && !hyp && !theme && node.detail && <p>{node.detail}</p>}
              {node.sources.length > 0 && <p className="refs">資料根拠: {node.sources.map((s) => <SourceRef key={s} id={s} />)}</p>}
              <h4>接続</h4>
              <ul className="small">{g.edges.filter((e) => e.from === node.id || e.to === node.id).map((e, i) => {
                const other = e.from === node.id ? e.to : e.from
                const on = g.nodes.find((n) => n.id === other)
                return <li key={i}><button className="link" onClick={() => setSel(other)}>{e.from === node.id ? '→' : '←'} {e.rel}: {on?.type} {on?.label.slice(0, 30)}</button></li>
              })}</ul>
            </Card>
          ) : <p className="muted">ノードを選択してください</p>}
        </div>
      </div>
    </div>
  )
}
