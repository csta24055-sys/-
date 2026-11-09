// API クライアント。
// - サーバー版（./run.sh・デスクトップ版）: FastAPI に問い合わせ、オフライン時は localStorage のスナップショットにフォールバック
// - スマホ単体版（VITE_STANDALONE=1 でビルド）: 端末内バックエンド（core/local.ts, IndexedDB）で同じ API を処理する
import { handle, HttpError } from './local'

export const STANDALONE = import.meta.env.VITE_STANDALONE === '1'

export interface Source {
  id: string; box_id: string; title: string; fiscal_year: number | null; kind: string; folder: string; folder_id: string
  status: string; topic: string; link: string; accessed: string; purpose: string; conditions: string; instruments: string
  measurements: string; raw_data: string; methods: string; results: string; conclusions: string; limitations: string
  related: string; pages: string; version: string; notes: string; _user_modified?: boolean
}
export interface Finding { id: string; class: string; text: string; sources: string[]; study: string | null; tags: string[] }
export interface Study { id: string; fiscal_year: number; label: string; title: string; question: string; method: string; outcome: string; handover: string; sources: string[] }
export interface Hypothesis { id: string; title: string; status: string; related_findings: string[]; competing: { label: string; text: string; test: string }[]; expected: string }
export interface Question { id: string; priority: string; text: string; related: string[]; status: string }
export interface Theme {
  id: string; name: string; horizon: string; scores: { importance: number; novelty: number; feasibility: number; fit: number }
  why_now: string; known: string; unsolved: string; hypotheses: string[]; equipment: string; measurements: string; procedure: string
  analysis: string; data_needed: string; branches: string; difficulty: string; duration_cost: string; significance: string; risks: string
  decision?: string; decision_reason?: string
  evaluation?: { feasibility: string; novelty: string; equipment: string; months: number[]; failure_risk: string; failure_mode: string; evidence: string; score_change: string }
}
export interface GraphNode { id: string; type: string; label: string; detail: string; sources: string[] }
export interface Knowledge {
  studies: Study[]; findings: Finding[]; hypotheses: Hypothesis[]; questions: Question[]; themes: Theme[]
  roadmap: { phase: string; items: string[] }[]
  models: { id: string; name: string; equation: string; units: string; basis: string; sources: string[]; validity: string }[]
  graph: { nodes: GraphNode[]; edges: { from: string; to: string; rel: string }[] }
  external: { id: string; title: string; url: string; note: string }[]
  meta: { accessed: string }
  literature?: Literature[]
  completeness?: { items: string[]; units: CompletenessUnit[] } | null
  validation?: { multizone?: { cases: { fan: string; D_per_s: number; beta_per_h: number; mean_nrmse: number; mean_peak_ratio: number; rooms: Record<string, { peak_meas: number; peak_sim: number; t_peak_meas: number; t_peak_sim: number; nrmse: number }> }[]; grid_best: Record<string, { best_D: number; best_nrmse: number }> } | null; fate2022?: { rows: { size_um: string; cond: string; fan: string; ep: boolean; model: Record<string, number>; reported: Record<string, number>; diff_pt: Record<string, number> }[]; max_abs_diff_pt_excl_residual: number } | null }
}
export interface DatasetMeta { id: number; name: string; filename: string | null; sheet: string | null; study: string | null; description: string | null; provenance: string; columns: string[]; n_rows: number; created_at: string }
export interface Dataset extends DatasetMeta { rows: unknown[][] }
export interface ReportSection { id: string; ord: number; title: string; body: string; user_modified: number; updated_at: string }

const SNAP = 'aqros-snapshot:'

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  if (STANDALONE) {
    try {
      const body = init?.body instanceof FormData ? init.body : init?.body ? JSON.parse(String(init.body)) : undefined
      return (await handle(init?.method || 'GET', path, body)) as T
    } catch (e) {
      if (e instanceof HttpError) throw new Error(e.message)
      throw e
    }
  }
  const res = await fetch(path, { ...init, headers: init?.body instanceof FormData ? init.headers : { 'Content-Type': 'application/json', ...(init?.headers || {}) } })
  if (!res.ok) {
    let msg = `${res.status}`
    try { const j = await res.json(); msg = j.detail || (j.offline ? 'オフラインです' : msg) } catch { /* noop */ }
    throw new Error(msg)
  }
  return res.json() as Promise<T>
}

/** GET（成功時は localStorage にスナップショット保存、失敗時はスナップショットを返す） */
export async function get<T>(path: string): Promise<T> {
  if (STANDALONE) return req<T>(path)
  try {
    const d = await req<T>(path)
    try { localStorage.setItem(SNAP + path, JSON.stringify(d)) } catch { /* 容量超過は無視 */ }
    return d
  } catch (e) {
    const s = localStorage.getItem(SNAP + path)
    if (s) return JSON.parse(s) as T
    throw e
  }
}

export interface Literature { doi: string; title: string; authors: string[]; year: number; venue: string; level: string; topic: string; stance: string; related: string[]; key: string; comparison: string; url: string }
export interface CompletenessUnit { id: string; year: number; title: string; sources: string[]; cls: string; evidence: string[]; notes: string; items: Record<string, string>; score: string }
export interface Plan { id?: number; title: string; theme_id?: string | null; background?: string; purpose?: string; hypotheses?: string; methods?: string; equipment?: string; measurements?: string; analysis?: string; schedule?: string; risks?: string; alternatives?: string; references?: string; created_at?: string; updated_at?: string }
export interface Deliverable { name: string; size: number; ext: string; group?: string; href?: string }

export const api = {
  dashboard: () => get<any>('/api/dashboard'),
  knowledge: () => get<Knowledge>('/api/knowledge'),
  sources: () => get<Source[]>('/api/sources'),
  source: (id: string) => get<{ source: Source; findings: Finding[]; studies: Study[]; related: Source[] }>(`/api/sources/${encodeURIComponent(id)}`),
  patchSource: (id: string, body: Partial<Pick<Source, 'status' | 'notes'>>) => req<Source>(`/api/sources/${encodeURIComponent(id)}`, { method: 'PATCH', body: JSON.stringify(body) }),
  addSource: (body: Partial<Source>) => req<Source>('/api/sources', { method: 'POST', body: JSON.stringify(body) }),
  patchItem: (kind: string, id: string, data: Record<string, unknown>) => req<any>(`/api/items/${kind}/${encodeURIComponent(id)}`, { method: 'PATCH', body: JSON.stringify({ data }) }),
  addQuestion: (body: Partial<Question>) => req<Question>('/api/questions', { method: 'POST', body: JSON.stringify(body) }),
  datasets: () => get<DatasetMeta[]>('/api/datasets'),
  dataset: (id: number) => get<Dataset>(`/api/datasets/${id}`),
  deleteDataset: (id: number) => req<{ ok: boolean }>(`/api/datasets/${id}`, { method: 'DELETE' }),
  upload: (fd: FormData) => req<{ ids: number[] }>('/api/datasets/upload', { method: 'POST', body: fd }),
  createDataset: (body: { name: string; columns: string[]; rows: unknown[][]; description?: string; provenance?: string; study?: string }) =>
    req<{ id: number }>('/api/datasets', { method: 'POST', body: JSON.stringify(body) }),
  report: () => get<ReportSection[]>('/api/report'),
  saveSection: (id: string, body: string) => req<ReportSection>(`/api/report/${encodeURIComponent(id)}`, { method: 'PUT', body: JSON.stringify({ body }) }),
  resetSection: (id: string) => req<{ ok: boolean }>(`/api/report/${encodeURIComponent(id)}/reset`, { method: 'POST' }),
  plans: () => get<Plan[]>('/api/plans'),
  createPlan: (p: Plan) => req<Plan>('/api/plans', { method: 'POST', body: JSON.stringify(p) }),
  updatePlan: (id: number, p: Plan) => req<Plan>(`/api/plans/${id}`, { method: 'PUT', body: JSON.stringify(p) }),
  deletePlan: (id: number) => req<{ ok: boolean }>(`/api/plans/${id}`, { method: 'DELETE' }),
  getState: (key: string) => get<{ key: string; value: any }>(`/api/state/${key}`),
  putState: (key: string, value: unknown) => req<{ ok: boolean }>(`/api/state/${key}`, { method: 'PUT', body: JSON.stringify({ value }) }),
  deliverables: () => get<Deliverable[]>('/api/deliverables'),
}

export const STATUS_ORDER = ['未確認', '目録確認', '読了', '数値検証済み']
export const CLASS_COLORS: Record<string, string> = {
  確認事実: 'fact', 当事者の主張: 'claim', 分析: 'analysis', 仮説: 'hypo', 予測: 'pred', 不明: 'unknown',
  計算結果: 'calc', '計算結果（当事者）': 'claim', '予測（当事者）': 'pred',
}

export function download(name: string, content: string | Blob, type = 'text/plain;charset=utf-8') {
  const blob = content instanceof Blob ? content : new Blob([content], { type })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = name
  a.style.display = 'none'
  document.body.appendChild(a)
  a.click()
  setTimeout(() => { URL.revokeObjectURL(a.href); a.remove() }, 1000)
}

export function toCsv(columns: string[], rows: unknown[][]) {
  const esc = (v: unknown) => { const s = v === null || v === undefined ? '' : String(v); return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s }
  return '﻿' + [columns.map(esc).join(','), ...rows.map((r) => r.map(esc).join(','))].join('\n')
}
