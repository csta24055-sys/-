// backend/aqros/models.py の TypeScript 移植（オフライン計算用）。
// src/core/crosscheck.test.ts で Python 実装との一致を検証する。

export const RHO_AIR = 1.2
export const EP_COEF = 78.611
export const EP_EXP = 0.828
export const EP_Q_RANGE: [number, number] = [100, 750]
export const EP_EFFICIENCY_ENDPOINTS: Record<string, [number, number]> = {
  '0.3-0.5': [0.95, 0.82],
  '0.5-1.0': [0.96, 0.86],
  '1.0-2.0': [0.97, 0.89],
  '2.0-5.0': [0.98, 0.91],
  '5.0-': [0.99, 0.92],
}
export const FAN_SETTINGS: Record<string, [number, number, number, number]> = {
  弱: [130, 90, 2.5, 12.0],
  中: [190, 80, 4.0, 13.5],
  強: [230, 70, 5.0, 15.0],
}
export const FAN_SHUTOFF_FACTOR = 1.6
export type EpLaw = 'fit' | 'quadratic_ext'
const DP_AT_QMAX = Math.pow(EP_Q_RANGE[1] / EP_COEF, 1 / EP_EXP)

export interface ZoneParams {
  volume: number; q_oa: number; eta_oa_filter: number; q_inf: number; penetration_inf: number
  q_recirc: number; bypass_ratio: number; eta_ep: number; deposition: number
  c_out: number; generation: number; c0: number
}
export const defaultZone: ZoneParams = {
  volume: 250, q_oa: 125, eta_oa_filter: 0.45, q_inf: 0, penetration_inf: 1,
  q_recirc: 950, bypass_ratio: 0, eta_ep: 0.85, deposition: 0.2, c_out: 7, generation: 0, c0: 0,
}

export const zoneCadr = (p: ZoneParams) => p.eta_ep * p.q_recirc * (1 - p.bypass_ratio)
export const zoneLossRate = (p: ZoneParams) => (p.q_oa + p.q_inf + zoneCadr(p)) / p.volume + p.deposition
export const zoneSource = (p: ZoneParams, cOut = p.c_out, gen = p.generation) =>
  p.q_oa * (1 - p.eta_oa_filter) * cOut + p.q_inf * p.penetration_inf * cOut + gen
export const zoneSteadyState = (p: ZoneParams) => zoneSource(p) / (p.volume * zoneLossRate(p))
export const zoneIoRatio = (p: ZoneParams) => (p.c_out > 0 ? zoneSource(p, p.c_out, 0) / (p.volume * zoneLossRate(p)) / p.c_out : NaN)
export const timeToFraction = (p: ZoneParams, f: number) => Math.log(1 / f) / zoneLossRate(p)

export function zoneTimeSeries(
  p: ZoneParams, hours: number, dtH = 1 / 60,
  cOutFn?: (t: number) => number, genFn?: (t: number) => number,
): { t: number; c: number }[] {
  const lam = zoneLossRate(p)
  const sub = Math.max(1, Math.ceil((lam * dtH) / 0.2))
  const h = dtH / sub
  let c = p.c0, t = 0
  const out = [{ t: 0, c }]
  const n = Math.round(hours / dtH)
  for (let i = 0; i < n; i++) {
    for (let j = 0; j < sub; j++) {
      const s = zoneSource(p, cOutFn ? cOutFn(t) : p.c_out, genFn ? genFn(t) : p.generation)
      const ceq = s / (p.volume * lam)
      c = ceq + (c - ceq) * Math.exp(-lam * h)
      t += h
    }
    out.push({ t, c })
  }
  return out
}

export function epDpFromQ(q: number, law: EpLaw = 'fit') {
  if (q <= 0) return 0
  if (law === 'quadratic_ext' && q > EP_Q_RANGE[1]) return DP_AT_QMAX * (q / EP_Q_RANGE[1]) ** 2
  return Math.pow(q / EP_COEF, 1 / EP_EXP)
}
export function epQFromDp(dp: number, law: EpLaw = 'fit') {
  dp = Math.max(dp, 0)
  if (law === 'quadratic_ext' && dp > DP_AT_QMAX) return EP_Q_RANGE[1] * Math.sqrt(dp / DP_AT_QMAX)
  return EP_COEF * Math.pow(dp, EP_EXP)
}
export function epEfficiency(q: number, bin = '0.3-0.5') {
  const [e100, e750] = EP_EFFICIENCY_ENDPOINTS[bin]
  const eta = e100 + ((e750 - e100) / (EP_Q_RANGE[1] - EP_Q_RANGE[0])) * (q - EP_Q_RANGE[0])
  return Math.min(0.995, Math.max(0.3, eta))
}
export const bypassQFromDp = (dp: number, r: number, area = 0.25, alpha = 0.65) =>
  3600 * alpha * area * r * Math.sqrt((2 * Math.max(dp, 0)) / RHO_AIR)

export function fanFlow(dp: number, setting: string, n: number) {
  const [q, plim] = FAN_SETTINGS[setting]
  if (dp <= plim) return q * n
  const pshut = plim * FAN_SHUTOFF_FACTOR
  return q * n * Math.max(0, 1 - (dp - plim) / (pshut - plim))
}
export function fanPowerPerUnit(dp: number, setting: string) {
  const [q, plim, w0, wlim] = FAN_SETTINGS[setting]
  if (dp <= plim) return w0 + ((wlim - w0) * dp) / plim
  return ((wlim * fanFlow(dp, setting, 1)) / q) * 0.9 + w0 * 0.1
}

export interface BypassResult {
  opening_ratio: number; dp: number; q_total: number; q_ep: number; q_bp: number; eta: number
  cadr: number; power_total: number; power_per_unit: number; within_fan_limit: boolean; warnings: string[]
}

export function solveBypass(r: number, n = 5, setting = '中', bin = '0.3-0.5', law: EpLaw = 'fit', area = 0.25, alpha = 0.65): BypassResult {
  const resid = (dp: number) => fanFlow(dp, setting, n) - (epQFromDp(dp, law) + bypassQFromDp(dp, r, area, alpha))
  let lo = 0, hi = FAN_SETTINGS[setting][1] * FAN_SHUTOFF_FACTOR
  if (resid(hi) > 0) hi *= 10
  for (let i = 0; i < 200; i++) {
    const mid = (lo + hi) / 2
    if (resid(mid) > 0) lo = mid; else hi = mid
  }
  const dp = (lo + hi) / 2
  const qt = fanFlow(dp, setting, n)
  const qep = epQFromDp(dp, law)
  const qbp = bypassQFromDp(dp, r, area, alpha)
  const eta = epEfficiency(qep, bin)
  const pu = fanPowerPerUnit(dp, setting)
  const plim = FAN_SETTINGS[setting][1]
  const warnings: string[] = []
  if (qep > EP_Q_RANGE[1] * 1.05 || (qep < EP_Q_RANGE[0] * 0.95 && qep > 1))
    warnings.push(`集塵機通過風量 ${qep.toFixed(0)} m³/h は実測範囲 100〜750 m³/h 外（式(2)・η の外挿）`)
  if (dp > 17.5) warnings.push(`集塵機差圧 ${dp.toFixed(1)} Pa は式(2)の実測範囲（≈0〜17 Pa）外`)
  if (dp > plim) warnings.push(`静圧 ${dp.toFixed(1)} Pa が風量一定制御限界 ${plim} Pa を超過（送風機特性は仮定外挿）`)
  return { opening_ratio: r, dp, q_total: qt, q_ep: qep, q_bp: qbp, eta, cadr: eta * qep, power_total: pu * n, power_per_unit: pu, within_fan_limit: dp <= plim, warnings }
}

export const bypassSweep = (n: number, setting: string, steps: number, bin: string, law: EpLaw) =>
  Array.from({ length: steps }, (_, i) => solveBypass(i / (steps - 1), n, setting, bin, law))

// 沈着
const MU = 1.81e-5, LAMBDA = 0.066e-6, G = 9.81
export function cunningham(dM: number) {
  const kn = (2 * LAMBDA) / dM
  return 1 + kn * (1.257 + 0.4 * Math.exp(-1.1 / kn))
}
export function settlingVelocity(dUm: number, rhoP = 1000) {
  const d = dUm * 1e-6, r = d / 2
  return (2 * cunningham(d) * (rhoP - RHO_AIR) * G * r * r) / (9 * MU)
}
export const depositionCoefficient = (dUm: number, h = 2.4, rho = 1000) => settlingVelocity(dUm, rho) / h

export const countToMass = (n: number, dUm: number, rho = 1000) => n * (4 / 3) * Math.PI * Math.pow((dUm * 1e-6) / 2, 3) * rho * 1e9

// 外挿警告（シミュレーター）
export function zoneWarnings(p: ZoneParams): string[] {
  const w: string[] = []
  const ach = p.q_oa / p.volume
  if (p.volume < 50 || p.volume > 600) w.push(`室容積 ${p.volume} m³ は研究室の実測対象（戸建住宅 約100〜400 m³）の範囲外`)
  if (ach < 0.3 || ach > 1.5) w.push(`換気回数 ${ach.toFixed(2)} 回/h は住宅の一般的範囲（0.5回/h 前後）から外れています`)
  if (p.q_recirc > 3800) w.push('循環風量が2026年度試算の最大値（3800 m³/h）を超えています')
  if (p.c_out > 40) w.push('外気濃度が研究室の実測最大（黄砂時 約35 μg/m³）を超えています')
  if (p.deposition > 0.45) w.push('沈着係数0.45 /h超は2025年度回帰係数の逆解析と矛盾します（F-X-11）')
  if (p.eta_ep > 0.96) w.push('EP効率96%超は2026年度実測（100 m³/hで95%以上）の上端を超えます')
  return w
}

// ---------------------------------------------------------------------------
// 多室（換気回路網）モデル — backend/aqros/models.py の移植
// 出典: 空気調和・衛生工学会大会 2021 G-31（床チャンバー空調 その40）表-2・表-3
// ---------------------------------------------------------------------------
export const OUTDOOR = '外部'
export const SHASE2021_VOLUMES: Record<string, number> = {
  空調室: 3.97, 建築ダクト: 2.76, 階間: 25.51, 床下: 30.61, 吹抜: 23.85, '洋室(中)': 23.85,
  クローゼット: 15.9, '洋室(大)': 39.75, '2階廊下・レターン': 40.35, 洗面所: 12.17, LDK: 91.3,
  '1階廊下・玄関': 20.87, 小屋裏: 75.05,
}
export const SHASE2021_FLOWS: [string, string, number, number][] = [
  [OUTDOOR, '空調室', 0.0216, 0.042], ['空調室', OUTDOOR, 0.0216, 0.042],
  ['空調室', '建築ダクト', 0.3348, 0.6655],
  ['建築ダクト', '階間', 0.1643, 0.3265], ['建築ダクト', '床下', 0.1705, 0.339],
  ['階間', '洋室(中)', 0.0327, 0.0649], ['階間', 'クローゼット', 0.0218, 0.0434],
  ['階間', '洋室(大)', 0.0545, 0.1083], ['階間', '2階廊下・レターン', 0.0553, 0.1099],
  ['床下', '洗面所', 0.0167, 0.0332], ['床下', 'LDK', 0.1252, 0.2489], ['床下', '1階廊下・玄関', 0.0286, 0.0569],
  ['LDK', '吹抜', 0.1247, 0.2479], ['LDK', '1階廊下・玄関', 0.0005, 0.001],
  ['吹抜', '2階廊下・レターン', 0.1247, 0.2479], ['洋室(中)', '2階廊下・レターン', 0.0327, 0.0649],
  ['クローゼット', '洋室(大)', 0.0218, 0.0434], ['洋室(大)', '2階廊下・レターン', 0.0763, 0.1517],
  ['洗面所', '1階廊下・玄関', 0.0167, 0.0332], ['1階廊下・玄関', '2階廊下・レターン', 0.0458, 0.0911],
  ['2階廊下・レターン', '小屋裏', 0.1042, 0.2084], ['小屋裏', '2階廊下・レターン', 0.1042, 0.2084],
  ['2階廊下・レターン', '空調室', 0.3348, 0.6655],
]
export const SHASE2021_EP_EDGE: [string, string] = ['空調室', '建築ダクト']
export type Flow = [string, string, number]

export function shase2021Network(setting: '弱' | '強' = '弱'): { volumes: Record<string, number>; flows: Flow[] } {
  const k = setting === '弱' ? 2 : 3
  return { volumes: { ...SHASE2021_VOLUMES }, flows: SHASE2021_FLOWS.map((r) => [r[0], r[1], (r[k] as number) * 3600]) }
}
export const decayRateToBeta = (d: number) => -Math.log(1 - d) * 3600

export interface MultizoneOpts {
  hours: number; c_out?: number; c0?: number | Record<string, number>; sources?: Record<string, number>
  source_hours?: [number, number]; beta?: number | Record<string, number>; ep_edge?: [string, string] | null
  eta_ep?: number; dt_s?: number; record_every_s?: number
}

export function multizoneSimulate(volumes: Record<string, number>, flows: Flow[], o: MultizoneOpts) {
  const zones = Object.keys(volumes)
  const idx = new Map(zones.map((z, i) => [z, i]))
  const n = zones.length
  const cOut = o.c_out ?? 0
  let c = zones.map((z) => (typeof o.c0 === 'object' ? o.c0[z] ?? 0 : o.c0 ?? 0))
  const b = zones.map((z) => (typeof o.beta === 'object' ? o.beta[z] ?? 0 : o.beta ?? 0))
  const g = zones.map((z) => o.sources?.[z] ?? 0)
  const outRate = new Array(n).fill(0)
  const edges = flows.map(([f, t, q]) => {
    const eta = o.ep_edge && f === o.ep_edge[0] && t === o.ep_edge[1] ? o.eta_ep ?? 0 : 0
    const fi = idx.has(f) ? idx.get(f)! : -1
    if (fi >= 0) outRate[fi] += q
    return [fi, idx.has(t) ? idx.get(t)! : -1, q, eta] as const
  })
  const maxRate = Math.max(...zones.map((z, i) => outRate[i] / volumes[z] + b[i])) / 3600
  const dtS = o.dt_s ?? 1
  const dt = maxRate > 0 ? Math.min(dtS, 0.5 / maxRate) : dtS
  const steps = Math.round((o.hours * 3600) / dt)
  const rec = Math.max(1, Math.round((o.record_every_s ?? 30) / dt))
  const [s0, s1] = o.source_hours ?? [0, 1e9]
  const h = dt / 3600
  const t_h = [0]
  const series: Record<string, number[]> = Object.fromEntries(zones.map((z, i) => [z, [c[i]]]))
  for (let s = 0; s < steps; s++) {
    const th = s * h
    const on = th >= s0 && th < s1
    const dc = new Array(n).fill(0)
    for (const [fi, ti, q, eta] of edges) { if (ti < 0) continue; dc[ti] += q * (fi < 0 ? cOut : c[fi]) * (1 - eta) }
    for (let i = 0; i < n; i++) dc[i] = (dc[i] - outRate[i] * c[i] + (on ? g[i] : 0)) / volumes[zones[i]] - b[i] * c[i]
    c = c.map((v, i) => v + h * dc[i])
    if ((s + 1) % rec === 0) { t_h.push((s + 1) * h); zones.forEach((z, i) => series[z].push(c[i])) }
  }
  return { t_h, series, dt_s: dt }
}
