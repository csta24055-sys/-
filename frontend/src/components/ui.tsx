import { ReactNode, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { CLASS_COLORS } from '../core/api'

export function useAsync<T>(fn: () => Promise<T>, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [tick, setTick] = useState(0)
  useEffect(() => {
    let alive = true
    setError(null)
    fn().then((d) => alive && setData(d)).catch((e) => alive && setError(String(e.message || e)))
    return () => { alive = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick])
  return { data, error, reload: () => setTick((t) => t + 1), setData }
}

export const Card = ({ title, children, actions, className = '' }: { title?: ReactNode; children: ReactNode; actions?: ReactNode; className?: string }) => (
  <section className={`card ${className}`}>
    {(title || actions) && <header className="card-h"><h2>{title}</h2>{actions && <div className="card-actions">{actions}</div>}</header>}
    {children}
  </section>
)

export const Badge = ({ cls }: { cls: string }) => <span className={`badge b-${CLASS_COLORS[cls] || 'unknown'}`}>【{cls}】</span>

export const StatusPill = ({ s }: { s: string }) => <span className={`pill st-${['未確認', '目録確認', '読了', '数値検証済み'].indexOf(s)}`}>{s}</span>

export const SourceRef = ({ id }: { id: string }) => <Link className="ref" to={`/library/${encodeURIComponent(id)}`}>{id}</Link>

export const Loading = ({ error }: { error?: string | null }) => (error ? <div className="error">読み込みエラー: {error}</div> : <div className="muted pad">読み込み中…</div>)

export function Stat({ label, value, sub }: { label: string; value: ReactNode; sub?: ReactNode }) {
  return <div className="stat"><div className="stat-v">{value}</div><div className="stat-l">{label}</div>{sub && <div className="stat-s">{sub}</div>}</div>
}

export function Bar({ done, total }: { done: number; total: number }) {
  const pct = total ? Math.round((100 * done) / total) : 0
  return <div className="bar" role="progressbar" aria-valuenow={pct}><div style={{ width: `${pct}%` }} /><span>{done}/{total}（{pct}%）</span></div>
}

export function Field({ label, children, hint }: { label: string; children: ReactNode; hint?: ReactNode }) {
  return <label className="field"><span className="field-l">{label}</span>{children}{hint && <span className="field-h">{hint}</span>}</label>
}

export function Slider({ label, value, min, max, step, unit, onChange, hint }: { label: string; value: number; min: number; max: number; step: number; unit: string; onChange: (v: number) => void; hint?: string }) {
  return (
    <div className="slider">
      <div className="slider-top"><span>{label}</span>
        <span><input type="number" value={value} step={step} onChange={(e) => onChange(Number(e.target.value))} aria-label={label} /> {unit}</span></div>
      <input type="range" min={min} max={max} step={step} value={Math.min(max, Math.max(min, value))} onChange={(e) => onChange(Number(e.target.value))} />
      {hint && <div className="field-h">{hint}</div>}
    </div>
  )
}

export const fmt = (v: number | null | undefined, d = 2) => (v === null || v === undefined || !Number.isFinite(v) ? '—' : Number(v).toLocaleString('ja-JP', { maximumFractionDigits: d, minimumFractionDigits: 0 }))
