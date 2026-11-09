// 端末内バックエンド（スマホ単体版 / 静的ホスティング用）。
// FastAPI（backend/app/main.py）と同じ URL・同じ応答形式を、ブラウザ内で IndexedDB を使って返す。
// 公開データ（seed.json: knowledge・報告書・成果物一覧）は配信物から読み、利用者の編集・取込データは端末内にだけ保存する。
// 研究データはサーバーへ送らない。
import Papa from 'papaparse'
import { kv } from './idb'
import { readXlsx } from './xlsx'

export interface Seed {
  version: string
  generated_at: string
  knowledge: Record<string, any>
  report: { id: string; ord: number; title: string; body: string }[]
  deliverables: { name: string; size: number; ext: string; group: string; href: string }[]
  dashboard: { next_actions: string[]; key_findings: string[] }
}

const KIND_KEYS: Record<string, string> = { source: 'sources', finding: 'findings', hypothesis: 'hypotheses', question: 'questions', theme: 'themes', study: 'studies' }
const VALID_STATUS = new Set(['未確認', '目録確認', '読了', '数値検証済み'])
const STATE_KEYS = new Set(['learning'])
const MAX_ROWS = 200_000

export class HttpError extends Error { constructor(public status: number, msg: string) { super(msg) } }

const now = () => new Date().toISOString().slice(0, 19) + '+00:00'
const base = () => (import.meta.env?.BASE_URL ?? '/')

let seedP: Promise<Seed> | null = null
export function setSeed(s: Seed) { seedP = Promise.resolve(s) }
export function loadSeed(): Promise<Seed> {
  if (!seedP) {
    seedP = fetch(base() + 'data/seed.json', { cache: 'no-cache' }).then((r) => {
      if (!r.ok) throw new HttpError(r.status, '公開データ（seed.json）を読み込めません')
      return r.json() as Promise<Seed>
    }).catch((e) => { seedP = null; throw e })
  }
  return seedP
}

async function log(action: string, target?: string) {
  const a = ((await kv.get<{ at: string; action: string; target?: string }[]>('activity')) || [])
  a.unshift({ at: now(), action, target })
  await kv.set('activity', a.slice(0, 50))
}

async function nextId(name: string): Promise<number> {
  const n = ((await kv.get<number>('seq:' + name)) || 0) + 1
  await kv.set('seq:' + name, n)
  return n
}

// ---------------------------------------------------------------- items（公開データ＋端末内の上書き）
async function listItems(kind: string): Promise<any[]> {
  const seed = await loadSeed()
  const base_ = (seed.knowledge[KIND_KEYS[kind]] || []) as any[]
  const over = new Map((await kv.entries(`item:${kind}:`)).map(([k, v]) => [k.slice(`item:${kind}:`.length), v as any]))
  const out = base_.map((it) => over.has(it.id) ? { ...over.get(it.id).data, _user_modified: true, _updated_at: over.get(it.id).updated_at }
    : { ...it, _user_modified: false, _updated_at: seed.generated_at })
  for (const [id, v] of over) if (!base_.some((b) => b.id === id)) out.push({ ...v.data, _user_modified: true, _updated_at: v.updated_at })
  return out.sort((a, b) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0))
}
async function getItem(kind: string, id: string) { return (await listItems(kind)).find((x) => x.id === id) || null }
async function upsertItem(kind: string, item: any) {
  const clean = Object.fromEntries(Object.entries(item).filter(([k]) => !k.startsWith('_')))
  await kv.set(`item:${kind}:${clean.id}`, { data: clean, updated_at: now() })
  await log(`update:${kind}`, clean.id as string)
  return clean
}
async function patchItem(kind: string, id: string, patch: Record<string, unknown>) {
  const cur = await getItem(kind, id)
  if (!cur) return null
  for (const [k, v] of Object.entries(patch)) if (v !== null && v !== undefined) cur[k] = v
  return upsertItem(kind, cur)
}

// ---------------------------------------------------------------- datasets
async function listDatasets() {
  const ds = (await kv.entries('dataset:')).map(([, v]) => v as any)
  return ds.map(({ rows: _r, ...m }) => m).sort((a, b) => b.id - a.id)
}
async function addDataset(d: { name: string; filename?: string | null; sheet?: string | null; columns: string[]; rows: unknown[][]; study?: string | null; description?: string | null; provenance?: string }) {
  const id = await nextId('dataset')
  const rec = { id, name: d.name, filename: d.filename ?? null, sheet: d.sheet ?? null, study: d.study ?? null, description: d.description ?? null,
    provenance: d.provenance || '利用者インポート', columns: d.columns.map(String), rows: d.rows, n_rows: d.rows.length, created_at: now() }
  await kv.set(`dataset:${String(id).padStart(6, '0')}`, rec)
  await log('dataset:add', d.name)
  return id
}
const dsKey = (id: number) => `dataset:${String(id).padStart(6, '0')}`

function parseCsv(text: string): { columns: string[]; rows: unknown[][] } {
  const r = Papa.parse<string[]>(text.replace(/^﻿/, ''), { skipEmptyLines: true, dynamicTyping: true, delimiter: '' })
  const [head, ...rows] = r.data as unknown as unknown[][]
  if (!head) throw new HttpError(400, 'データ行がありません')
  return { columns: head.map((h, i) => (h === null || h === undefined || h === '' ? `列${i + 1}` : String(h))), rows }
}

export async function uploadFile(file: File, name = '', study = '', description = '') {
  if (file.size > 50 * 1024 * 1024) throw new HttpError(413, 'ファイルが大きすぎます（50MB まで）。大きいファイルはクラウド解析を使ってください')
  const stem = name || file.name.replace(/\.[^.]+$/, '')
  const ids: number[] = []
  if (/\.(xlsx|xlsm)$/i.test(file.name)) {
    const sheets = await readXlsx(await file.arrayBuffer())
    for (const sh of sheets) {
      if (!sh.rows.length) continue
      ids.push(await addDataset({ name: stem + (sheets.length === 1 ? '' : ` [${sh.name}]`), filename: file.name, sheet: sh.name, columns: sh.columns, rows: sh.rows.slice(0, MAX_ROWS), study: study || null, description: description || null }))
    }
  } else if (/\.(csv|tsv|txt)$/i.test(file.name)) {
    const { columns, rows } = parseCsv(await file.text())
    if (rows.length) ids.push(await addDataset({ name: stem, filename: file.name, sheet: null, columns, rows: rows.slice(0, MAX_ROWS), study: study || null, description: description || null }))
  } else {
    throw new HttpError(400, '対応形式: CSV / TSV / TXT / XLSX / XLSM（.xls は Excel で .xlsx に保存し直してください）')
  }
  if (!ids.length) throw new HttpError(400, 'データ行がありません')
  return { ids }
}

// ---------------------------------------------------------------- report / plans
async function reportSections() {
  const seed = await loadSeed()
  const over = new Map((await kv.entries('report:')).map(([k, v]) => [k.slice(7), v as any]))
  const out = seed.report.map((s) => over.has(s.id) ? { ...s, ...over.get(s.id), user_modified: 1 } : { ...s, user_modified: 0, updated_at: seed.generated_at })
  let ord = out.length
  for (const [id, v] of over) if (!seed.report.some((s) => s.id === id)) out.push({ id, ord: ord++, title: v.title || id, body: v.body, user_modified: 1, updated_at: v.updated_at })
  return out.sort((a, b) => a.ord - b.ord)
}
async function listPlans() {
  return (await kv.entries('plan:')).map(([, v]) => v as any).sort((a, b) => (a.updated_at < b.updated_at ? 1 : -1))
}
const PLAN_FIELDS = ['background', 'purpose', 'hypotheses', 'methods', 'equipment', 'measurements', 'analysis', 'schedule', 'risks', 'alternatives', 'references']
function validPlan(p: any) {
  if (!p || typeof p.title !== 'string' || !p.title.trim() || p.title.length > 200) throw new HttpError(422, 'タイトルは1〜200文字')
  const out: any = { title: p.title, theme_id: p.theme_id ?? null }
  for (const f of PLAN_FIELDS) { const v = p[f] ?? ''; if (String(v).length > 20000) throw new HttpError(422, `${f} が長すぎます`); out[f] = String(v) }
  return out
}

// ---------------------------------------------------------------- router
export async function handle(method: string, rawPath: string, body?: unknown): Promise<unknown> {
  const u = new URL(rawPath, 'http://local')
  const p = u.pathname.replace(/\/+$/, '')
  const seg = p.split('/').slice(2).map(decodeURIComponent) // ['sources', 'S-...']
  const M = method.toUpperCase()
  const B = (body ?? {}) as any

  if (p === '/api/health') return { ok: true, app: 'aqros', mode: 'standalone', version: (await loadSeed()).version }

  if (p === '/api/dashboard') {
    const seed = await loadSeed()
    const [sources, studies, findings, questions, themes, datasets] = await Promise.all(['source', 'study', 'finding', 'question', 'theme'].map(listItems).concat([listDatasets()]))
    const status: Record<string, number> = {}
    const byYear: Record<string, Record<string, number>> = {}
    for (const s of sources) {
      status[s.status] = (status[s.status] || 0) + 1
      const y = String(s.fiscal_year || '不明'); (byYear[y] ||= {})[s.status] = (byYear[y][s.status] || 0) + 1
    }
    const read = (status['読了'] || 0) + (status['数値検証済み'] || 0)
    const activity = ((await kv.get<any[]>('activity')) || []).slice(0, 8)
    return {
      counts: { sources: sources.length, read, unread: sources.length - read, by_status: status, findings: findings.length, questions: questions.length, themes: themes.length, datasets: datasets.length },
      by_year: Object.fromEntries(Object.entries(byYear).sort()),
      studies,
      key_findings: findings.filter((f) => seed.dashboard.key_findings.includes(f.id)),
      open_questions: questions.filter((q) => q.priority === '高').sort((a, b) => (a.id < b.id ? -1 : 1)),
      next_actions: seed.dashboard.next_actions,
      progress: {
        資料探索: { done: read, total: sources.length },
        分析: { done: findings.filter((f) => ['分析', '計算結果'].includes(f.class)).length, total: findings.length },
        テーマ判断: { done: themes.filter((t) => t.decision).length, total: themes.length },
      },
      activity,
    }
  }

  if (seg[0] === 'sources') {
    if (seg.length === 1 && M === 'GET') {
      const q = (u.searchParams.get('q') || '').trim().toLowerCase(), year = u.searchParams.get('year') || '', status = u.searchParams.get('status') || '', kind = u.searchParams.get('kind') || ''
      return (await listItems('source')).filter((s) => {
        if (year && String(s.fiscal_year || '不明') !== year) return false
        if (status && s.status !== status) return false
        if (kind && !String(s.kind).includes(kind)) return false
        if (q) {
          const hay = ['title', 'topic', 'purpose', 'results', 'conclusions', 'limitations', 'notes', 'folder', 'box_id', 'id', 'instruments'].map((k) => String(s[k] ?? '')).join(' ').toLowerCase()
          return q.split(/\s+/).every((t) => hay.includes(t))
        }
        return true
      })
    }
    if (seg.length === 1 && M === 'POST') {
      if (!B.title) throw new HttpError(422, 'title は必須')
      const n = (await listItems('source')).filter((x) => x.id.startsWith('S-LOCAL-')).length + 1
      const item: any = { title: B.title, box_id: B.box_id || '', fiscal_year: B.fiscal_year ?? null, kind: B.kind || 'ローカル資料', topic: B.topic || '', status: B.status || '目録確認', notes: B.notes || '', link: B.link || '',
        id: `S-LOCAL-${String(n).padStart(3, '0')}`, folder: 'ローカル', folder_id: '', accessed: new Date().toISOString().slice(0, 10) }
      for (const k of ['purpose', 'conditions', 'instruments', 'measurements', 'raw_data', 'methods', 'results', 'conclusions', 'limitations', 'related', 'pages', 'version']) item[k] ??= ''
      return upsertItem('source', item)
    }
    const sid = seg[1]
    if (M === 'GET') {
      const s = await getItem('source', sid)
      if (!s) throw new HttpError(404, '資料が見つかりません')
      const findings = (await listItems('finding')).filter((f) => f.sources.includes(sid))
      const studies = (await listItems('study')).filter((st) => st.sources.includes(sid))
      const rel = [...new Set(findings.flatMap((f) => f.sources).filter((x: string) => x !== sid))].sort()
      const all = await listItems('source')
      return { source: s, findings, studies, related: rel.map((r) => all.find((x) => x.id === r)).filter(Boolean) }
    }
    if (M === 'PATCH') {
      if (B.status && !VALID_STATUS.has(B.status)) throw new HttpError(400, `status は ${[...VALID_STATUS].join(', ')} のいずれか`)
      const r = await patchItem('source', sid, { status: B.status, notes: B.notes })
      if (!r) throw new HttpError(404, 'not found')
      return r
    }
  }

  if (p === '/api/knowledge') {
    const k = (await loadSeed()).knowledge
    const [studies, findings, hypotheses, questions, themes] = await Promise.all(['study', 'finding', 'hypothesis', 'question', 'theme'].map(listItems))
    return { studies, findings, hypotheses, questions, themes, roadmap: k.roadmap, models: k.models, graph: k.graph, external: k.external, meta: k.meta, validation: k.validation, literature: k.literature || [], completeness: k.completeness }
  }

  if (seg[0] === 'items' && M === 'PATCH') {
    if (!['hypothesis', 'question', 'theme', 'finding'].includes(seg[1])) throw new HttpError(400, '編集可能な種別: hypothesis, question, theme, finding')
    const r = await patchItem(seg[1], seg[2], B.data || {})
    if (!r) throw new HttpError(404, 'not found')
    return r
  }

  if (p === '/api/questions' && M === 'POST') {
    const ids = (await listItems('question')).map((x) => Number(String(x.id).split('-')[1])).filter((n) => Number.isFinite(n))
    return upsertItem('question', { id: `Q-${String(Math.max(0, ...ids) + 1).padStart(2, '0')}`, text: B.text, priority: B.priority || '中', related: B.related || [], status: B.status || '未着手' })
  }

  if (seg[0] === 'datasets') {
    if (seg.length === 1 && M === 'GET') return listDatasets()
    if (seg.length === 1 && M === 'POST') {
      if (!Array.isArray(B.rows) || !Array.isArray(B.columns)) throw new HttpError(422, 'columns と rows が必要')
      if (B.rows.length > MAX_ROWS) throw new HttpError(413, `${MAX_ROWS} 行まで`)
      return { id: await addDataset(B) }
    }
    if (seg[1] === 'upload' && M === 'POST') {
      const fd = body as FormData
      const f = fd.get('file') as File | null
      if (!f) throw new HttpError(422, 'file が必要')
      return uploadFile(f, String(fd.get('name') || ''), String(fd.get('study') || ''), String(fd.get('description') || ''))
    }
    const id = Number(seg[1])
    if (M === 'GET') { const d = await kv.get(dsKey(id)); if (!d) throw new HttpError(404, 'not found'); return d }
    if (M === 'DELETE') {
      if (!(await kv.get(dsKey(id)))) throw new HttpError(404, 'not found')
      await kv.del(dsKey(id)); await log('dataset:delete', String(id)); return { ok: true }
    }
  }

  if (seg[0] === 'report') {
    if (seg.length === 1 && M === 'GET') return reportSections()
    if (seg[1] === 'export.md') return (await reportSections()).map((s) => s.body).join('\n\n')
    if (M === 'PUT') {
      const cur = (await reportSections()).find((s) => s.id === seg[1])
      await kv.set(`report:${seg[1]}`, { body: String(B.body ?? ''), title: B.title || cur?.title || seg[1], updated_at: now() })
      await log('report:save', seg[1])
      return (await reportSections()).find((s) => s.id === seg[1])
    }
    if (seg[2] === 'reset' && M === 'POST') { await kv.del(`report:${seg[1]}`); return { ok: true } }
  }

  if (seg[0] === 'plans') {
    if (seg.length === 1 && M === 'GET') return listPlans()
    if (seg.length === 1 && M === 'POST') {
      const v = validPlan(B); const id = await nextId('plan')
      const rec = { id, ...v, created_at: now(), updated_at: now() }
      await kv.set(`plan:${String(id).padStart(6, '0')}`, rec); await log('研究計画を保存', v.title); return rec
    }
    const key = `plan:${String(Number(seg[1])).padStart(6, '0')}`
    const cur = await kv.get<any>(key)
    if (!cur) throw new HttpError(404, 'plan not found')
    if (M === 'PUT') { const rec = { ...cur, ...validPlan(B), updated_at: now() }; await kv.set(key, rec); await log('研究計画を保存', rec.title); return rec }
    if (M === 'DELETE') { await kv.del(key); return { ok: true } }
  }

  if (seg[0] === 'state') {
    if (!STATE_KEYS.has(seg[1])) throw new HttpError(404, 'unknown key')
    if (M === 'GET') return { key: seg[1], value: (await kv.get(`state:${seg[1]}`)) ?? null }
    if (M === 'PUT') {
      if (JSON.stringify(B.value ?? null).length > 100_000) throw new HttpError(413, 'too large')
      await kv.set(`state:${seg[1]}`, B.value); return { ok: true }
    }
  }

  if (p === '/api/deliverables' && M === 'GET') return (await loadSeed()).deliverables

  throw new HttpError(404, `未対応: ${M} ${p}`)
}

// ---------------------------------------------------------------- バックアップ／復元
export const BACKUP_FORMAT = 'aqros-backup'
export async function exportBackup() {
  const entries = await kv.entries('')
  const seed = await loadSeed().catch(() => null)
  return { format: BACKUP_FORMAT, version: 1, exported_at: now(), seed_version: seed?.version ?? null, note: '端末内データ（編集・取込データ・研究計画・学習記録）。原データを含む場合は取り扱いに注意。',
    entries: entries.filter(([k]) => !k.startsWith('cloud:token')) }
}

export async function importBackup(obj: any, mode: 'merge' | 'replace' = 'merge') {
  if (!obj || obj.format !== BACKUP_FORMAT || !Array.isArray(obj.entries)) throw new Error('Air Quality Research OS のバックアップファイルではありません')
  const allowed = /^(item:|dataset:|report:|plan:|state:|seq:|activity$|cloud:jobs$|cloud:settings$)/
  const bad = obj.entries.filter(([k]: [string]) => !allowed.test(k))
  if (bad.length) throw new Error(`不明なキーを含みます: ${bad.slice(0, 3).map((b: any) => b[0]).join(', ')}`)
  if (mode === 'replace') { const tok = await kv.get('cloud:token'); await kv.clear(); if (tok) await kv.set('cloud:token', tok) }
  for (const [k, v] of obj.entries) {
    if (mode === 'merge' && k.startsWith('seq:')) { const cur = (await kv.get<number>(k)) || 0; await kv.set(k, Math.max(cur, Number(v) || 0)); continue }
    await kv.set(k, v)
  }
  return { restored: obj.entries.length }
}
