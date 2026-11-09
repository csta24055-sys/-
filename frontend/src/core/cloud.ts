// クラウド解析（GitHub Actions をジョブ方式の計算環境として使う）
//
// スマホ → GitHub API（利用者の細粒度トークンで認証）→ ジョブ用ブランチ aqros-job/<id> を作成
//   → push をきっかけに .github/workflows/cloud-jobs.yml が起動 → cloud/run_job.py が計算
//   → 結果を同じブランチの cloud_jobs/outbox/<id>/ にコミット → スマホが取得 → ブランチ削除
//
// - トークンはアプリに埋め込まない。利用者が設定画面で入力し、この端末の IndexedDB にだけ保存する（バックアップにも含めない）
// - 公開リポジトリでは、利用者のデータ（取込データ・編集した文書・アップロード文書）を送らない。
//   送れるのは計算条件と公開済みデータ、および「合成」と明示したデータだけ
// - 非公開リポジトリでも、研究室の許可と利用者の同意（ジョブごと）がなければ送らない
import { kv } from './idb'

export interface CloudSettings { owner: string; repo: string; base_branch: string; api: string }
export type JobType = 'sweep' | 'analysis' | 'report' | 'ocr'
export interface JobInput { name: string; data: Uint8Array; sensitive: boolean }
export interface JobRecord {
  id: string; type: JobType; title: string; created_at: string; repo: string; branch: string
  status: 'submitted' | 'queued' | 'in_progress' | 'done' | 'failed' | 'deleted'; run_url?: string
  result?: any; files?: { name: string; size: number }[]; error?: string
}

export const JOB_TYPES: Record<JobType, { label: string; sensitive_input: boolean; desc: string }> = {
  sweep: { label: '大規模パラメータ計算', sensitive_input: false, desc: '電気集塵機バイパス・単室モデルの条件総当たり（Python 版モデル）。CSV と要約を返す。' },
  analysis: { label: '大規模データの詳細解析（Python）', sensitive_input: true, desc: 'CSV/Excel（複数可）を pandas で読み、品質・統計・I/O比・減衰を計算し Excel と要約を返す。' },
  report: { label: '研究レポートの Word / PDF 生成', sensitive_input: true, desc: 'pandoc で Word、LibreOffice で PDF を作る。公開リポジトリでは公開版の報告書だけを使う。' },
  ocr: { label: 'OCR（画像・PDF の文字起こし）', sensitive_input: true, desc: 'Tesseract（日本語＋英語）で文字起こしし、テキストを返す。' },
}

const DEFAULTS: CloudSettings = { owner: '', repo: '', base_branch: 'claude/air-quality-research-os-19gu2g', api: 'https://api.github.com' }

export async function getSettings(): Promise<CloudSettings> { return { ...DEFAULTS, ...((await kv.get<CloudSettings>('cloud:settings')) || {}) } }
export async function saveSettings(s: Partial<CloudSettings>) { await kv.set('cloud:settings', { ...(await getSettings()), ...s }) }
export async function hasToken() { return !!(await kv.get<string>('cloud:token')) }
export async function setToken(t: string) { if (t) await kv.set('cloud:token', t.trim()); else await kv.del('cloud:token') }
export async function listJobs(): Promise<JobRecord[]> { return (await kv.get<JobRecord[]>('cloud:jobs')) || [] }
async function saveJob(j: JobRecord) {
  const js = await listJobs(); const i = js.findIndex((x) => x.id === j.id)
  if (i >= 0) js[i] = j; else js.unshift(j)
  await kv.set('cloud:jobs', js.slice(0, 100))
}

class GH {
  constructor(private s: CloudSettings, private token: string) {}
  async call<T = any>(method: string, path: string, body?: unknown, accept = 'application/vnd.github+json'): Promise<T> {
    const r = await fetch(this.s.api.replace(/\/$/, '') + path, {
      method, headers: { Authorization: `Bearer ${this.token}`, Accept: accept, 'X-GitHub-Api-Version': '2022-11-28', ...(body ? { 'Content-Type': 'application/json' } : {}) },
      body: body ? JSON.stringify(body) : undefined,
    })
    if (r.status === 404) throw Object.assign(new Error('not found'), { status: 404 })
    if (!r.ok) {
      let m = `${r.status}`; try { m += ' ' + ((await r.json()).message || '') } catch { /* noop */ }
      throw Object.assign(new Error(`GitHub API: ${m}`), { status: r.status })
    }
    if (r.status === 204) return undefined as T
    return (accept.includes('raw') ? r.arrayBuffer() : r.json()) as Promise<T>
  }
  repo(p = '') { return `/repos/${encodeURIComponent(this.s.owner)}/${encodeURIComponent(this.s.repo)}${p}` }
}

async function client() {
  const s = await getSettings(); const t = await kv.get<string>('cloud:token')
  if (!s.owner || !s.repo) throw new Error('クラウド解析の接続先リポジトリが未設定です（設定画面）')
  if (!t) throw new Error('GitHub のアクセストークンが未設定です（設定画面）')
  return { s, gh: new GH(s, t) }
}

export async function checkRepo() {
  const { s, gh } = await client()
  const r = await gh.call('GET', gh.repo())
  let workflow = false
  try { await gh.call('GET', gh.repo(`/contents/.github/workflows/cloud-jobs.yml?ref=${encodeURIComponent(s.base_branch)}`)); workflow = true } catch { /* noop */ }
  return { full_name: r.full_name as string, private: !!r.private, push: !!r.permissions?.push, workflow, base_branch: s.base_branch }
}

/** 送信前の安全確認。送れない理由があれば文字列を返す */
export function policyCheck(repoPrivate: boolean, inputs: JobInput[], consent: boolean): string | null {
  const sens = inputs.filter((i) => i.sensitive)
  if (sens.length && !repoPrivate) return `接続先は公開リポジトリです。研究データ・編集した文書・アップロード文書（${sens.map((i) => i.name).join(', ')}）は送信できません。非公開リポジトリを設定するか、端末内の解析を使ってください。`
  if (sens.length && !consent) return '研究データを送るには、研究室の許可を得ていることと、このジョブでの送信に同意することの確認が必要です。'
  return null
}

const b64 = (u8: Uint8Array) => { let s = ''; for (let i = 0; i < u8.length; i += 0x8000) s += String.fromCharCode(...u8.subarray(i, i + 0x8000)); return btoa(s) }
const enc = (s: string) => new TextEncoder().encode(s)
const safeName = (n: string) => n.replace(/[^\w.\-]+/g, '_').slice(0, 80) || 'input'

export async function submitJob(type: JobType, title: string, params: Record<string, unknown>, inputs: JobInput[], consent: boolean): Promise<JobRecord> {
  const { s, gh } = await client()
  const info = await checkRepo()
  if (!info.workflow) throw new Error(`接続先 ${info.full_name} の ${s.base_branch} に .github/workflows/cloud-jobs.yml がありません`)
  const why = policyCheck(info.private, inputs, consent)
  if (why) throw new Error(why)
  const d = new Date(); const pad = (n: number) => String(n).padStart(2, '0')
  const id = `${d.getUTCFullYear()}${pad(d.getUTCMonth() + 1)}${pad(d.getUTCDate())}-${pad(d.getUTCHours())}${pad(d.getUTCMinutes())}${pad(d.getUTCSeconds())}-${Math.random().toString(36).slice(2, 6)}`
  const branch = `aqros-job/${id}`
  const baseRef = await gh.call('GET', gh.repo(`/git/ref/heads/${s.base_branch.split('/').map(encodeURIComponent).join('/')}`))
  const baseCommit = await gh.call('GET', gh.repo(`/git/commits/${baseRef.object.sha}`))
  const job = { id, type, title, params, inputs: inputs.map((i) => ({ name: safeName(i.name), sensitive: i.sensitive })), consent: inputs.some((i) => i.sensitive) ? consent : null,
    repo_private: info.private, created_at: d.toISOString(), client: 'aqros-pwa' }
  const files: [string, Uint8Array][] = [[`cloud_jobs/inbox/${id}/job.json`, enc(JSON.stringify(job, null, 1))], ...inputs.map((i) => [`cloud_jobs/inbox/${id}/inputs/${safeName(i.name)}`, i.data] as [string, Uint8Array])]
  const tree = []
  for (const [path, data] of files) {
    const blob = await gh.call('POST', gh.repo('/git/blobs'), { content: b64(data), encoding: 'base64' })
    tree.push({ path, mode: '100644', type: 'blob', sha: blob.sha })
  }
  const t = await gh.call('POST', gh.repo('/git/trees'), { base_tree: baseCommit.tree.sha, tree })
  const c = await gh.call('POST', gh.repo('/git/commits'), { message: `[aqros-job] ${type}: ${title}`.slice(0, 200), tree: t.sha, parents: [baseRef.object.sha] })
  await gh.call('POST', gh.repo('/git/refs'), { ref: `refs/heads/${branch}`, sha: c.sha })
  const rec: JobRecord = { id, type, title, created_at: d.toISOString(), repo: info.full_name, branch, status: 'submitted' }
  await saveJob(rec)
  return rec
}

/** 実行状況と結果を取りに行く。結果が出ていれば outbox のファイルを端末に保存する */
export async function refreshJob(j: JobRecord): Promise<JobRecord> {
  if (j.status === 'done' || j.status === 'deleted') return j
  const { gh } = await client()
  const ref = encodeURIComponent(j.branch)
  try {
    const runs = await gh.call('GET', gh.repo(`/actions/runs?branch=${ref}&per_page=5`))
    const run = runs.workflow_runs?.[0]
    if (run) {
      j.run_url = run.html_url
      if (run.status === 'completed' && run.conclusion !== 'success') { j.status = 'failed'; j.error = `GitHub Actions: ${run.conclusion}` }
      else if (run.status === 'completed') j.status = 'in_progress'
      else j.status = run.status === 'queued' ? 'queued' : 'in_progress'
    }
  } catch { /* 実行一覧が見られない権限でも結果ファイルで判定する */ }
  try {
    const raw = await gh.call<ArrayBuffer>('GET', gh.repo(`/contents/cloud_jobs/outbox/${j.id}/result.json?ref=${ref}`), undefined, 'application/vnd.github.raw')
    j.result = JSON.parse(new TextDecoder().decode(raw))
    const list = await gh.call<any[]>('GET', gh.repo(`/contents/cloud_jobs/outbox/${j.id}?ref=${ref}`))
    j.files = []
    for (const f of list.filter((x) => x.type === 'file')) {
      const data = await gh.call<ArrayBuffer>('GET', gh.repo(`/contents/${f.path.split('/').map(encodeURIComponent).join('/')}?ref=${ref}`), undefined, 'application/vnd.github.raw')
      await kv.set(`cloud:file:${j.id}:${f.name}`, new Uint8Array(data))
      j.files.push({ name: f.name, size: data.byteLength })
    }
    j.status = j.result?.status === 'error' ? 'failed' : 'done'
    if (j.result?.status === 'error') j.error = j.result.error
  } catch (e: any) { if (e.status !== 404) j.error = e.message }
  await saveJob(j)
  return j
}

export async function jobFile(id: string, name: string) { return kv.get<Uint8Array>(`cloud:file:${id}:${name}`) }

/** 結果を受け取った後、クラウド側のジョブ用ブランチ（入力データを含む）を削除する */
export async function deleteRemote(j: JobRecord) {
  const { gh } = await client()
  try { await gh.call('DELETE', gh.repo(`/git/refs/heads/${j.branch.split('/').map(encodeURIComponent).join('/')}`)) } catch (e: any) { if (e.status !== 404 && e.status !== 422) throw e }
  j.status = j.status === 'done' ? 'done' : 'deleted'
  ;(j as any).remote_deleted = true
  await saveJob(j)
}

export async function forgetJob(id: string) {
  for (const k of await kv.keys(`cloud:file:${id}:`)) await kv.del(k)
  await kv.set('cloud:jobs', (await listJobs()).filter((j) => j.id !== id))
}
