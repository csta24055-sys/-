import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Card, Field } from '../components/ui'
import { api, download, toCsv } from '../core/api'
import { checkRepo, deleteRemote, forgetJob, getSettings, hasToken, JOB_TYPES, jobFile, JobInput, JobRecord, JobType, listJobs, policyCheck, refreshJob, submitJob } from '../core/cloud'

const enc = (s: string) => new TextEncoder().encode(s)
const STATUS: Record<string, string> = { submitted: '送信済み', queued: '待機中', in_progress: '実行中', done: '完了', failed: '失敗', deleted: '削除済み' }
const MIME: Record<string, string> = { csv: 'text/csv', xlsx: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', docx: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', pdf: 'application/pdf', md: 'text/markdown', txt: 'text/plain', json: 'application/json' }

export default function Cloud() {
  const [ready, setReady] = useState<{ ok: boolean; repo?: { full_name: string; private: boolean; workflow: boolean }; msg: string } | null>(null)
  const [type, setType] = useState<JobType>('sweep')
  const [jobs, setJobs] = useState<JobRecord[]>([])
  const [msg, setMsg] = useState('')
  const [busy, setBusy] = useState(false)
  // sweep
  const [kind, setKind] = useState<'bypass' | 'zone'>('bypass')
  const [units, setUnits] = useState('5,10,15,20')
  const [settings, setSettings] = useState<string[]>(['弱', '中', '強'])
  const [steps, setSteps] = useState(21)
  // analysis
  const [dsList, setDsList] = useState<{ id: number; name: string; provenance: string; n_rows: number }[]>([])
  const [dsSel, setDsSel] = useState<number[]>([])
  const [files, setFiles] = useState<File[]>([])
  const [indoor, setIndoor] = useState(''); const [outdoor, setOutdoor] = useState('')
  const [sendEdited, setSendEdited] = useState(false)
  const [consent, setConsent] = useState(false)

  const load = async () => {
    setJobs(await listJobs())
    const s = await getSettings()
    if (!s.owner || !s.repo || !(await hasToken())) { setReady({ ok: false, msg: '接続先とトークンが未設定です。' }); return }
    try { const r = await checkRepo(); setReady({ ok: r.workflow, repo: r, msg: r.workflow ? '' : 'ワークフロー cloud-jobs.yml が接続先にありません。' }) } catch (e: any) { setReady({ ok: false, msg: e.message }) }
  }
  useEffect(() => { load(); api.datasets().then((d) => setDsList(d as any)).catch(() => undefined) }, [])

  const inputs = async (): Promise<JobInput[]> => {
    const out: JobInput[] = []
    if (type === 'analysis') {
      for (const id of dsSel) {
        const d = await api.dataset(id)
        out.push({ name: `${id}_${d.name}.csv`, data: enc(toCsv(d.columns, d.rows)), sensitive: !/合成/.test(d.provenance) })
      }
      for (const f of files) out.push({ name: f.name, data: new Uint8Array(await f.arrayBuffer()), sensitive: true })
    }
    if (type === 'ocr') for (const f of files) out.push({ name: f.name, data: new Uint8Array(await f.arrayBuffer()), sensitive: true })
    if (type === 'report' && sendEdited) out.push({ name: 'report_sections.json', data: enc(JSON.stringify((await api.report()).map((s) => ({ title: s.title, body: s.body })))), sensitive: true })
    return out
  }

  const submit = async () => {
    setBusy(true); setMsg('送信中…')
    try {
      const ins = await inputs()
      if ((type === 'analysis' || type === 'ocr') && !ins.length) throw new Error('入力を選んでください')
      const params: Record<string, unknown> = type === 'sweep'
        ? (kind === 'bypass' ? { kind, n_units: units.split(/[,\s]+/).map(Number).filter((n) => n > 0 && n <= 40), settings, steps } : { kind })
        : type === 'analysis' ? { indoor: indoor || null, outdoor: outdoor || null } : {}
      const why = ready?.repo ? policyCheck(ready.repo.private, ins, consent) : null
      if (why) throw new Error(why)
      const title = type === 'sweep' ? `${kind === 'bypass' ? 'バイパス' : '単室'}計算` : type === 'analysis' ? `解析 ${ins.length}件` : type === 'report' ? '報告書 Word/PDF' : `OCR ${ins.length}件`
      const j = await submitJob(type, title, params, ins, consent)
      setMsg(`送信しました（${j.id}）。数分後に「結果を確認」を押してください。`); setConsent(false); setFiles([])
      setJobs(await listJobs())
    } catch (e: any) { setMsg('送信できません: ' + e.message) } finally { setBusy(false) }
  }

  const refresh = async (j: JobRecord) => { setMsg('確認中…'); try { await refreshJob(j); setMsg('') } catch (e: any) { setMsg(e.message) } setJobs(await listJobs()) }
  const save = async (j: JobRecord, name: string) => {
    const d = await jobFile(j.id, name); if (!d) return
    download(`${j.id}_${name}`, new Blob([d], { type: MIME[name.split('.').pop() || ''] || 'application/octet-stream' }))
  }
  const sensitiveType = JOB_TYPES[type].sensitive_input && (type !== 'report' || sendEdited)

  return (
    <div className="page">
      <h1>クラウド解析</h1>
      <p className="lead">スマホで重い処理は GitHub Actions で実行します（処理ごとに起動するジョブ方式。数分かかります）。端末内でできる解析・シミュレーションは<Link to="/data">実験データ解析</Link>・<Link to="/simulator">シミュレーター</Link>を使ってください。</p>
      <Card title="接続状態">
        {!ready ? <p className="small">確認中…</p> : ready.repo
          ? <p className="small">{ready.repo.full_name} — <b>{ready.repo.private ? '非公開リポジトリ' : '公開リポジトリ'}</b>{ready.repo.private ? '（研究データは同意のうえで送信可）' : '（研究データは送信しません。計算条件・公開データ・合成データのみ）'} {ready.msg}</p>
          : <p className="small">{ready.msg} <Link to="/settings">設定</Link>で接続先リポジトリとトークンを登録してください。</p>}
      </Card>

      <Card title="新しいジョブ">
        <Field label="処理">
          <select value={type} onChange={(e) => { setType(e.target.value as JobType); setFiles([]) }} aria-label="ジョブ種別">
            {(Object.keys(JOB_TYPES) as JobType[]).map((t) => <option key={t} value={t}>{JOB_TYPES[t].label}</option>)}
          </select>
        </Field>
        <p className="small muted">{JOB_TYPES[type].desc}</p>
        {type === 'sweep' && <div className="row2">
          <Field label="モデル"><select value={kind} onChange={(e) => setKind(e.target.value as any)}><option value="bypass">電気集塵機バイパス（台数×設定×開度）</option><option value="zone">単室モデル（循環風量×EP効率×バイパス率）</option></select></Field>
          {kind === 'bypass' && <>
            <Field label="台数（カンマ区切り）"><input value={units} onChange={(e) => setUnits(e.target.value)} inputMode="numeric" /></Field>
            <Field label="ファン設定">{['弱', '中', '強'].map((s) => <label key={s} className="chk"><input type="checkbox" checked={settings.includes(s)} onChange={(e) => setSettings(e.target.checked ? [...settings, s] : settings.filter((x) => x !== s))} />{s}</label>)}</Field>
            <Field label={`開度の刻み ${steps}`}><input type="range" min={5} max={101} value={steps} onChange={(e) => setSteps(+e.target.value)} /></Field>
          </>}
        </div>}
        {type === 'analysis' && <>
          <Field label="端末内のデータセット（複数選択可）">
            <div className="checklist">{dsList.length ? dsList.map((d) => <label key={d.id} className="chk"><input type="checkbox" checked={dsSel.includes(d.id)} onChange={(e) => setDsSel(e.target.checked ? [...dsSel, d.id] : dsSel.filter((x) => x !== d.id))} />{d.name}（{d.n_rows}行・{/合成/.test(d.provenance) ? '合成' : '研究データ扱い'}）</label>) : <span className="small muted">データセットがありません</span>}</div>
          </Field>
          <Field label="または端末のファイル（CSV/Excel、複数可）"><input type="file" multiple accept=".csv,.tsv,.txt,.xlsx,.xlsm" onChange={(e) => setFiles([...(e.target.files || [])])} /></Field>
          <div className="row2"><Field label="室内の列名（I/O比）"><input value={indoor} onChange={(e) => setIndoor(e.target.value)} /></Field><Field label="外気の列名"><input value={outdoor} onChange={(e) => setOutdoor(e.target.value)} /></Field></div>
        </>}
        {type === 'ocr' && <Field label="画像・PDF（複数可）"><input type="file" multiple accept=".pdf,image/*" onChange={(e) => setFiles([...(e.target.files || [])])} /></Field>}
        {type === 'report' && <label className="chk"><input type="checkbox" checked={sendEdited} onChange={(e) => setSendEdited(e.target.checked)} />この端末で編集した報告書を使う（非公開リポジトリのみ。未選択時は公開版の報告書）</label>}
        {sensitiveType && <label className="chk consent"><input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} />研究室の許可を得ており、このジョブで上記のデータを接続先（{ready?.repo?.full_name || '未設定'}）へ送信・処理することに同意します</label>}
        <div className="filters"><button disabled={busy || !ready?.ok} onClick={submit}>解析開始</button><span className="small muted" role="status">{msg}</span></div>
      </Card>

      <Card title="ジョブ一覧" actions={<button className="ghost small" onClick={load}>更新</button>}>
        {!jobs.length && <p className="small muted">まだジョブはありません。</p>}
        <ul className="joblist">{jobs.map((j) => (
          <li key={j.id}>
            <div><b>{j.title}</b> <span className={`pill job-${j.status}`}>{STATUS[j.status] || j.status}</span> <span className="small muted">{new Date(j.created_at).toLocaleString('ja-JP')} · {j.repo}</span></div>
            {j.error && <div className="error small">{j.error}</div>}
            {j.result?.summary && <details className="small"><summary>要約</summary><pre>{JSON.stringify(j.result.summary, null, 1).slice(0, 4000)}</pre></details>}
            <div className="filters">
              {j.status !== 'done' && j.status !== 'deleted' && <button className="small" onClick={() => refresh(j)}>結果を確認</button>}
              {j.files?.map((f) => <button key={f.name} className="ghost small" onClick={() => save(j, f.name)}>⤓ {f.name}</button>)}
              {j.run_url && <a className="small" href={j.run_url} target="_blank" rel="noreferrer">実行ログ</a>}
              {!(j as any).remote_deleted && <button className="ghost small" onClick={async () => { await deleteRemote(j); setJobs(await listJobs()) }}>クラウド側を削除</button>}
              <button className="ghost small" onClick={async () => { await forgetJob(j.id); setJobs(await listJobs()) }}>一覧から消す</button>
            </div>
          </li>
        ))}</ul>
        <p className="small muted">結果を保存したら「クラウド側を削除」を押してください（入力データを含むジョブ用ブランチを消します）。</p>
      </Card>
    </div>
  )
}
