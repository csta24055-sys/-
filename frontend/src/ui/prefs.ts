// 表示設定（デザインの種類＋利用者のカスタマイズ）の型・既定値・検証・保存。
// - 端末内の localStorage だけに保存する（研究データの IndexedDB・サーバー DB・バックアップには一切触れない）。
// - 壊れた値・未知のレイアウト ID は Original に戻す（読み込みで例外を出さない）。
// - React に依存しない純粋な関数だけを置く（単体テスト: prefs.test.ts）。

export const LAYOUT_IDS = ['original', 'research', 'public', 'commercial', 'enterprise'] as const
export type LayoutId = (typeof LAYOUT_IDS)[number]

export type Density = 'auto' | 'compact' | 'standard' | 'comfortable'
export type SidebarPos = 'auto' | 'left' | 'right'
export type SidebarMode = 'auto' | 'expanded' | 'icons' | 'hidden'
export type CardStyle = 'auto' | 'outline' | 'shadow' | 'flat'
export type Radius = 'auto' | 'sharp' | 'standard' | 'round'
export type ThemeMode = 'auto' | 'light' | 'dark'

export interface Customization {
  /** 主色（#rrggbb）。null はレイアウトの既定色 */
  accent: string | null
  /** 文字の大きさの倍率（0.85〜1.4） */
  fontScale: number
  density: Density
  sidebarPos: SidebarPos
  sidebarMode: SidebarMode
  card: CardStyle
  radius: Radius
  theme: ThemeMode
}

export interface UiSelection { layout: LayoutId; custom: Customization }

export interface StoredPrefs {
  version: 1
  applied: UiSelection
  /** 直前に適用していた設定（新しい順、最大 5 件）。「元に戻す」に使う */
  history: UiSelection[]
  updatedAt: string | null
}

export const STORAGE_KEY = 'aqros-ui-prefs-v1'
export const FONT_SCALES = [0.9, 1, 1.15, 1.3] as const
export const ACCENT_PRESETS = ['#0f5b5c', '#00687a', '#1f5f8b', '#0f6b5c', '#1d5fa8', '#5b3fa0', '#8a4b0f', '#a1201b'] as const

export const DEFAULT_CUSTOM: Customization = {
  accent: null, fontScale: 1, density: 'auto', sidebarPos: 'auto', sidebarMode: 'auto', card: 'auto', radius: 'auto', theme: 'auto',
}
export const ORIGINAL: UiSelection = { layout: 'original', custom: { ...DEFAULT_CUSTOM } }

export const defaultPrefs = (): StoredPrefs => ({ version: 1, applied: clone(ORIGINAL), history: [], updatedAt: null })

const clone = <T,>(v: T): T => JSON.parse(JSON.stringify(v))
const oneOf = <T extends string>(v: unknown, allowed: readonly T[], fb: T): T => (typeof v === 'string' && (allowed as readonly string[]).includes(v) ? (v as T) : fb)

export function isLayoutId(v: unknown): v is LayoutId { return typeof v === 'string' && (LAYOUT_IDS as readonly string[]).includes(v) }

export function sanitizeCustom(c: unknown): Customization {
  const o = (c && typeof c === 'object' ? c : {}) as Record<string, unknown>
  const accent = typeof o.accent === 'string' && /^#[0-9a-f]{6}$/i.test(o.accent) ? o.accent.toLowerCase() : null
  const fs = typeof o.fontScale === 'number' && Number.isFinite(o.fontScale) ? Math.min(1.4, Math.max(0.85, o.fontScale)) : 1
  return {
    accent,
    fontScale: Math.round(fs * 100) / 100,
    density: oneOf(o.density, ['auto', 'compact', 'standard', 'comfortable'] as const, 'auto'),
    sidebarPos: oneOf(o.sidebarPos, ['auto', 'left', 'right'] as const, 'auto'),
    sidebarMode: oneOf(o.sidebarMode, ['auto', 'expanded', 'icons', 'hidden'] as const, 'auto'),
    card: oneOf(o.card, ['auto', 'outline', 'shadow', 'flat'] as const, 'auto'),
    radius: oneOf(o.radius, ['auto', 'sharp', 'standard', 'round'] as const, 'auto'),
    theme: oneOf(o.theme, ['auto', 'light', 'dark'] as const, 'auto'),
  }
}

export function sanitizeSelection(s: unknown): UiSelection {
  const o = (s && typeof s === 'object' ? s : {}) as Record<string, unknown>
  return { layout: isLayoutId(o.layout) ? o.layout : 'original', custom: sanitizeCustom(o.custom) }
}

export function parsePrefs(raw: string | null): StoredPrefs {
  if (!raw) return defaultPrefs()
  try {
    const o = JSON.parse(raw)
    if (!o || typeof o !== 'object' || o.version !== 1) return defaultPrefs()
    const history = Array.isArray(o.history) ? o.history.slice(0, 5).map(sanitizeSelection) : []
    return { version: 1, applied: sanitizeSelection(o.applied), history, updatedAt: typeof o.updatedAt === 'string' ? o.updatedAt : null }
  } catch {
    return defaultPrefs()
  }
}

export function sameSelection(a: UiSelection, b: UiSelection) { return JSON.stringify(sanitizeSelection(a)) === JSON.stringify(sanitizeSelection(b)) }
export function isDefaultCustom(c: Customization) { return JSON.stringify(sanitizeCustom(c)) === JSON.stringify(DEFAULT_CUSTOM) }

/** 適用：現在の設定を履歴の先頭に積んでから新しい設定にする（同じ設定なら何もしない） */
export function applySelection(p: StoredPrefs, next: UiSelection, now = new Date().toISOString()): StoredPrefs {
  const n = sanitizeSelection(next)
  if (sameSelection(p.applied, n)) return p
  return { version: 1, applied: n, history: [clone(p.applied), ...p.history].slice(0, 5), updatedAt: now }
}

/** 元に戻す：履歴の先頭を適用中の設定に戻す */
export function undoSelection(p: StoredPrefs, now = new Date().toISOString()): StoredPrefs {
  if (!p.history.length) return p
  const [prev, ...rest] = p.history
  return { version: 1, applied: sanitizeSelection(prev), history: rest, updatedAt: now }
}

export function loadPrefs(storage: Pick<Storage, 'getItem'> | null = safeStorage()): StoredPrefs {
  try { return parsePrefs(storage ? storage.getItem(STORAGE_KEY) : null) } catch { return defaultPrefs() }
}

export function savePrefs(p: StoredPrefs, storage: Pick<Storage, 'setItem'> | null = safeStorage()): boolean {
  try { if (!storage) return false; storage.setItem(STORAGE_KEY, JSON.stringify(p)); return true } catch { return false }
}

function safeStorage(): Storage | null {
  try { return typeof localStorage === 'undefined' ? null : localStorage } catch { return null }
}

/** WCAG の相対輝度とコントラスト比（主色の白文字が読めるかを利用者に示すため） */
export function contrastRatio(hexA: string, hexB: string): number {
  const lum = (hex: string) => {
    const m = /^#?([0-9a-f]{6})$/i.exec(hex); if (!m) return 0
    const v = parseInt(m[1], 16)
    const ch = [(v >> 16) & 255, (v >> 8) & 255, v & 255].map((x) => { const s = x / 255; return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4 })
    return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2]
  }
  const [a, b] = [lum(hexA), lum(hexB)].sort((x, y) => y - x)
  return Math.round(((a + 0.05) / (b + 0.05)) * 100) / 100
}
