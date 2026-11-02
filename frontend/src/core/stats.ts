// backend/aqros/analysis.py の TypeScript 移植

const finite = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v)

export function toNum(v: unknown): number {
  if (typeof v === 'number') return v
  if (v === null || v === undefined || v === '') return NaN
  const n = Number(String(v).replace(/,/g, ''))
  return Number.isFinite(n) ? n : NaN
}

const pairs = (x: number[], y: number[]) => {
  const xs: number[] = [], ys: number[] = []
  for (let i = 0; i < Math.min(x.length, y.length); i++) if (finite(x[i]) && finite(y[i])) { xs.push(x[i]); ys.push(y[i]) }
  return [xs, ys] as const
}
const sum = (a: number[]) => a.reduce((s, v) => s + v, 0)
const mean = (a: number[]) => sum(a) / a.length
export function median(a: number[]) {
  const s = [...a].sort((p, q) => p - q), m = Math.floor(s.length / 2)
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2
}
export function quantile(a: number[], q: number) {
  const s = [...a].sort((p, r) => p - r)
  const pos = (s.length - 1) * q, lo = Math.floor(pos), hi = Math.ceil(pos)
  return s[lo] + (s[hi] - s[lo]) * (pos - lo)
}

const T975: Record<number, number> = { 1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228, 15: 2.131, 20: 2.086, 30: 2.042, 60: 2.0, 120: 1.98 }
export function t975(df: number) {
  if (T975[df]) return T975[df]
  const k = Object.keys(T975).map(Number).sort((a, b) => a - b)
  for (let i = 0; i < k.length - 1; i++) if (df > k[i] && df < k[i + 1]) return T975[k[i]] + ((T975[k[i + 1]] - T975[k[i]]) * (df - k[i])) / (k[i + 1] - k[i])
  return 1.96
}

export function regressionThroughOrigin(x: number[], y: number[]) {
  const [xs, ys] = pairs(x, y)
  const n = xs.length
  if (n < 3) throw new Error('データ点が不足しています（3点以上必要）')
  const sxx = sum(xs.map((v) => v * v))
  const k = sum(xs.map((v, i) => v * ys[i])) / sxx
  const sse = sum(xs.map((v, i) => (ys[i] - k * v) ** 2))
  const r2 = 1 - sse / sum(ys.map((v) => v * v))
  const se = Math.sqrt(sse / (n - 1) / sxx)
  const tc = t975(n - 1)
  return { k, r2, se, ci_low: k - tc * se, ci_high: k + tc * se, n }
}

export function linearRegression(x: number[], y: number[]) {
  const [xs, ys] = pairs(x, y)
  const mx = mean(xs), my = mean(ys)
  const sxy = sum(xs.map((v, i) => (v - mx) * (ys[i] - my))), sxx = sum(xs.map((v) => (v - mx) ** 2))
  const slope = sxy / sxx, intercept = my - slope * mx
  const r2 = 1 - sum(xs.map((v, i) => (ys[i] - slope * v - intercept) ** 2)) / sum(ys.map((v) => (v - my) ** 2))
  return { slope, intercept, r2, n: xs.length }
}

export function powerLawFit(x: number[], y: number[]) {
  const [xs, ys] = pairs(x, y)
  const lx: number[] = [], ly: number[] = []
  xs.forEach((v, i) => { if (v > 0 && ys[i] > 0) { lx.push(Math.log(v)); ly.push(Math.log(ys[i])) } })
  const r = linearRegression(lx, ly)
  return { a: Math.exp(r.intercept), b: r.slope, r2: r.r2, n: r.n }
}

export function removalEfficiency(up: number[], dn: number[]) {
  const [u, d] = pairs(up, dn)
  const U: number[] = [], D: number[] = []
  u.forEach((v, i) => { if (v > 0) { U.push(v); D.push(d[i]) } })
  const per = U.map((v, i) => 1 - D[i] / v)
  const m = mean(per)
  const sd = per.length > 1 ? Math.sqrt(sum(per.map((v) => (v - m) ** 2)) / (per.length - 1)) : 0
  return { eta_mean_of_ratios: m * 100, eta_ratio_of_means: (1 - mean(D) / mean(U)) * 100, eta_std: sd * 100, n: U.length }
}

export function ioRatio(indoor: number[], outdoor: number[]) {
  const [o, i] = pairs(outdoor, indoor)
  const O: number[] = [], I: number[] = []
  o.forEach((v, k) => { if (v > 0) { O.push(v); I.push(i[k]) } })
  return { io_ratio_of_means: mean(I) / mean(O), io_median_of_ratios: median(I.map((v, k) => v / O[k])), indoor_mean: mean(I), outdoor_mean: mean(O), n: O.length }
}

export function exceedance(v: number[], thr: number) {
  const f = v.filter(finite)
  return f.length ? f.filter((x) => x > thr).length / f.length : NaN
}

export function fitDecay(t: number[], c: number[], bg = 0) {
  const T: number[] = [], L: number[] = []
  t.forEach((v, i) => { if (finite(c[i]) && c[i] - bg > 0) { T.push(v); L.push(Math.log(c[i] - bg)) } })
  const r = linearRegression(T, L)
  return { beta_per_s: -r.slope, c0: Math.exp(r.intercept), r2: r.r2, n: r.n }
}

export interface ColumnQuality {
  column: string; n: number; missing: number; missing_pct: number; negative: number; outliers: number
  outlier_rows: number[]; mean: number | null; median: number | null; std: number | null; min: number | null; max: number | null
}

export function qualityReport(rows: unknown[][], columns: string[], cols: string[], z = 3.5): ColumnQuality[] {
  return cols.map((c) => {
    const idx = columns.indexOf(c)
    const vals = rows.map((r) => toNum(r[idx]))
    const ok = vals.map((v, i) => [v, i] as const).filter(([v]) => finite(v))
    const v = ok.map(([x]) => x)
    const med = v.length ? median(v) : NaN
    const mad = v.length ? median(v.map((x) => Math.abs(x - med))) : NaN
    const outRows = mad > 0 ? ok.filter(([x]) => Math.abs(x - med) / (1.4826 * mad) > z).map(([, i]) => i) : []
    const m = v.length ? mean(v) : NaN
    const sd = v.length > 1 ? Math.sqrt(sum(v.map((x) => (x - m) ** 2)) / (v.length - 1)) : NaN
    const nn = (x: number) => (finite(x) ? x : null)
    return {
      column: c, n: vals.length, missing: vals.length - v.length, missing_pct: vals.length ? (100 * (vals.length - v.length)) / vals.length : 0,
      negative: v.filter((x) => x < 0).length, outliers: outRows.length, outlier_rows: outRows.slice(0, 50),
      mean: nn(m), median: nn(med), std: nn(sd), min: v.length ? Math.min(...v) : null, max: v.length ? Math.max(...v) : null,
    }
  })
}

const TIME_HINTS = ['time', 'date', '日時', '時刻', '日付', 'timestamp', 'datetime']
export function detectTimeColumn(columns: string[], rows: unknown[][]): string | null {
  for (const c of columns) if (TIME_HINTS.some((h) => c.toLowerCase().includes(h))) return c
  for (const c of columns.slice(0, 2)) {
    const i = columns.indexOf(c)
    const ok = rows.slice(0, 200).filter((r) => typeof r[i] === 'string' && !Number.isNaN(Date.parse(String(r[i])))).length
    if (ok > Math.min(rows.length, 200) * 0.8) return c
  }
  return null
}
export function numericColumns(columns: string[], rows: unknown[][], exclude?: string | null) {
  return columns.filter((c, i) => c !== exclude && rows.length > 0 && rows.filter((r) => finite(toNum(r[i]))).length / rows.length >= 0.5)
}
