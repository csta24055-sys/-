// API クライアント。オフライン時は localStorage のスナップショットにフォールバックする。

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
  validation?: { multizone?: { cases: { fan: string; D_per_s: number; beta_per_h: number; mean_nrmse: number; mean_peak_ratio: number; rooms: Record<string, { peak_meas: number; peak_sim: number; t_peak_meas: number; t_peak_sim: number; nrmse: number }> }[]; grid_best: Record<string, { best_D: number; best_nrmse: number }> } | null; fate2022?: { rows: { size_um: string; cond: string; fan: string; ep: boolean; model: Record<string, number>; reported: Record<string, number>; diff_pt: Record<string, number> }[]; max_abs_diff_pt_excl_residual: number } | null }
}
export interface DatasetMeta { id: number; name: string; filename: string | null; sheet: string | null; study: string | null; description: string | null; provenance: string; columns: string[]; n_rows: number; created_at: string }
export interface Dataset extends DatasetMeta { rows: unknown[][] }
export interface ReportSection { id: string; ord: number; title: string; body: string; user_modified: number; updated_at: string }

const SNAP = 'aqros-snapshot:'

async function req<T>(path: string, init?: RequestInit): Promise<T> {
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
