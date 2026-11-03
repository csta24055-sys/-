import { useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api, Source, STATUS_ORDER } from '../core/api'
import { Badge, Card, Field, Loading, SourceRef, StatusPill, useAsync } from '../components/ui'

const DETAIL: [keyof Source, string][] = [
  ['purpose', '研究目的'], ['conditions', '実験条件'], ['instruments', '測定器'], ['measurements', '測定項目・単位'], ['raw_data', '原データの有無'],
  ['methods', '手法'], ['results', '結果'], ['conclusions', '結論【当事者の主張】'], ['limitations', '限界・未解決論点【分析】'], ['related', '他年度との関連'],
  ['pages', '該当ページ'], ['version', '資料バージョン'], ['notes', 'メモ'],
]

export default function Library() {
  const { id } = useParams()
  const nav = useNavigate()
  const { data: sources, error, reload } = useAsync(api.sources)
  const [q, setQ] = useState('')
  const [year, setYear] = useState('')
  const [status, setStatus] = useState('')
  const [topic, setTopic] = useState('')
  const [adding, setAdding] = useState(false)

  const years = useMemo(() => [...new Set((sources || []).map((s) => String(s.fiscal_year ?? '不明')))].sort().reverse(), [sources])
  const filtered = useMemo(() => {
    const terms = q.trim().toLowerCase().split(/\s+/).filter(Boolean)
    return (sources || []).filter((s) => {
      if (year && String(s.fiscal_year ?? '不明') !== year) return false
      if (status && s.status !== status) return false
      if (topic && !s.topic.includes(topic) && !s.title.includes(topic)) return false
      const hay = [s.title, s.topic, s.purpose, s.results, s.conclusions, s.limitations, s.notes, s.folder, s.box_id, s.id, s.instruments].join(' ').toLowerCase()
      return terms.every((t) => hay.includes(t))
    })
  }, [sources, q, year, status, topic])

  if (!sources) return <Loading error={error} />
  return (
    <div className="page">
      <h1>研究資料ライブラリ</h1>
      <p className="lead">Box 資料台帳（{sources.length}件）。原文は保存せず、要旨・出典ページ・Box リンクのみを管理。リンクは Box の閲覧権限が必要です。</p>
      <div className={id ? 'split has-detail' : 'split'}>
        <div className="list-pane">
          <div className="filters">
            <input type="search" placeholder="検索（例: バイパス, I/O 年間, KC-52）" value={q} onChange={(e) => setQ(e.target.value)} aria-label="資料検索" />
            <select value={year} onChange={(e) => setYear(e.target.value)} aria-label="年度"><option value="">全年度</option>{years.map((y) => <option key={y}>{y}</option>)}</select>
            <select value={status} onChange={(e) => setStatus(e.target.value)} aria-label="調査状態"><option value="">全状態</option>{STATUS_ORDER.map((s) => <option key={s}>{s}</option>)}</select>
            <select value={topic} onChange={(e) => setTopic(e.target.value)} aria-label="テーマ">
              <option value="">全テーマ</option>{['電気集塵', '外気', '沈着', '生活行動', '本論', '原データ', 'センサー', '発表', '規格', 'WHO'].map((t) => <option key={t}>{t}</option>)}
            </select>
            <button className="ghost" onClick={() => setAdding(!adding)}>＋ ローカル資料</button>
          </div>
          {adding && <AddLocal onDone={() => { setAdding(false); reload() }} />}
          <div className="muted small">{filtered.length} 件</div>
          <ul className="srclist">
            {filtered.map((s) => (
              <li key={s.id} className={s.id === id ? 'active' : ''} onClick={() => nav(`/library/${encodeURIComponent(s.id)}`)}>
                <div className="row"><StatusPill s={s.status} /><span className="muted small">{s.fiscal_year ?? '—'}年度・{s.kind}</span></div>
                <div className="t">{s.title}</div>
                <div className="muted small">{s.id}・{s.topic}</div>
              </li>
            ))}
          </ul>
        </div>
        {id && <Detail id={id} onChanged={reload} />}
      </div>
      <LiteraturePanel q={q} />
    </div>
  )
}

/** 国内外文献（Crossref で DOI を確認、要旨は OpenAlex から取得。全文精読はしていない） */
function LiteraturePanel({ q }: { q: string }) {
  const { data } = useAsync(api.knowledge)
  const [stance, setStance] = useState('')
  const lit = data?.literature || []
  const terms = q.trim().toLowerCase().split(/\s+/).filter(Boolean)
  const rows = lit.filter((l) => (!stance || l.stance === stance) && terms.every((t) => [l.title, l.topic, l.key, l.comparison, l.venue, l.doi, ...l.related].join(' ').toLowerCase().includes(t)))
  if (!lit.length) return null
  return (
    <Card title={`国内外文献（${rows.length}/${lit.length}件）— 研究室の結論との比較`}>
      <div className="filters">
        <select value={stance} onChange={(e) => setStance(e.target.value)} aria-label="立場"><option value="">全ての立場</option>{['支持', '反証・制約', '方法', '文脈'].map((s) => <option key={s}>{s}</option>)}</select>
        <span className="small muted">確認水準: 要旨確認＝要旨を読んだ／書誌のみ＝DOI・題名のみ。上の検索語でも絞り込まれる。</span>
      </div>
      <ul className="litlist">{rows.map((l) => (
        <li key={l.doi}>
          <div><span className={`pill ${l.level === '要旨確認' ? 'st-2' : 'st-1'}`}>{l.level}</span> <span className="pill">{l.stance}</span> <span className="small muted">{l.topic}</span></div>
          <div className="t">{l.title}（{l.year}）</div>
          <div className="small muted">{l.authors.slice(0, 3).join(', ')}{l.authors.length > 3 ? ' ほか' : ''}. {l.venue}. <a href={l.url} target="_blank" rel="noreferrer">DOI: {l.doi}</a></div>
          {l.key && <p className="small"><b>要旨の要点</b>【確認事実】: {l.key}</p>}
          <p className="small"><b>研究室との比較</b>【分析】: {l.comparison} <span className="muted">（関連: {l.related.join(', ')}）</span></p>
        </li>))}</ul>
    </Card>
  )
}

function Detail({ id, onChanged }: { id: string; onChanged: () => void }) {
  const { data, error, reload } = useAsync(() => api.source(id), [id])
  const [notes, setNotes] = useState<string | null>(null)
  const [msg, setMsg] = useState('')
  if (!data) return <div className="detail-pane"><Loading error={error} /></div>
  const s = data.source
  const save = async (patch: Partial<Source>) => {
    try { await api.patchSource(s.id, patch); setMsg('保存しました'); reload(); onChanged() } catch (e: any) { setMsg('保存失敗: ' + e.message) }
  }
  return (
    <div className="detail-pane">
      <Link to="/library" className="back">← 一覧へ</Link>
      <Card title={<>{s.id} <StatusPill s={s.status} /></>}>
        <h3 className="dtitle">{s.title}</h3>
        <dl className="meta">
          <dt>Box ID</dt><dd><code>{s.box_id}</code></dd>
          <dt>元フォルダ</dt><dd>{s.folder}（{s.folder_id}）</dd>
          <dt>研究年度</dt><dd>{s.fiscal_year ?? '不明'}</dd>
          <dt>取得日</dt><dd>{s.accessed}</dd>
          <dt>原資料</dt><dd><a href={s.link} target="_blank" rel="noreferrer">Box で開く ↗</a></dd>
        </dl>
        <div className="statusbar">調査状態:
          {STATUS_ORDER.map((st) => <button key={st} className={st === s.status ? 'on' : ''} onClick={() => save({ status: st })}>{st}</button>)}
        </div>
        <p className="muted small">未読資料を「読了」に変更するのは本文を実際に読んだ後のみにしてください。</p>
        {DETAIL.filter(([k]) => s[k]).map(([k, label]) => <div key={k} className="kv"><b>{label}</b><p>{String(s[k])}</p></div>)}
        <Field label="メモ（ローカル保存）">
          <textarea rows={3} value={notes ?? s.notes ?? ''} onChange={(e) => setNotes(e.target.value)} />
        </Field>
        <button onClick={() => save({ notes: notes ?? s.notes })}>メモを保存</button> <span className="muted small">{msg}</span>
      </Card>
      {data.findings.length > 0 && (
        <Card title="この資料に基づく知見（要点抽出）">
          <ul className="flist">{data.findings.map((f) => <li key={f.id}><b>{f.id}</b> <Badge cls={f.class} /> {f.text}</li>)}</ul>
        </Card>
      )}
      {(data.related.length > 0 || data.studies.length > 0) && (
        <Card title="資料の相互関連">
          {data.studies.map((st) => <p key={st.id}>研究系譜: <b>{st.label}</b> — {st.handover && `次年度へ: ${st.handover}`}</p>)}
          <div className="refs">{data.related.map((r) => <span key={r.id}><SourceRef id={r.id} /> <span className="small muted">{r.title.slice(0, 30)}</span></span>)}</div>
        </Card>
      )}
    </div>
  )
}

function AddLocal({ onDone }: { onDone: () => void }) {
  const [f, setF] = useState({ title: '', fiscal_year: '', topic: '', link: '', notes: '' })
  const [err, setErr] = useState('')
  return (
    <div className="card inset">
      <p className="small muted">Box 未接続時や学外資料の登録用。本文は保存せず、書誌情報とメモのみ記録します。</p>
      <Field label="資料名"><input value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} /></Field>
      <div className="row2">
        <Field label="年度"><input type="number" value={f.fiscal_year} onChange={(e) => setF({ ...f, fiscal_year: e.target.value })} /></Field>
        <Field label="主題"><input value={f.topic} onChange={(e) => setF({ ...f, topic: e.target.value })} /></Field>
      </div>
      <Field label="リンク（任意）"><input value={f.link} onChange={(e) => setF({ ...f, link: e.target.value })} /></Field>
      <Field label="メモ"><textarea rows={2} value={f.notes} onChange={(e) => setF({ ...f, notes: e.target.value })} /></Field>
      <button disabled={!f.title} onClick={async () => {
        try { await api.addSource({ ...f, fiscal_year: f.fiscal_year ? Number(f.fiscal_year) : null } as any); onDone() } catch (e: any) { setErr(e.message) }
      }}>登録</button> <span className="error small">{err}</span>
    </div>
  )
}
