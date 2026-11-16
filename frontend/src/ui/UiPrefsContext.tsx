// 表示設定の状態管理。
// - applied: 保存済み（再読み込み後も維持）
// - draft:   プレビュー中の設定（保存していない。適用で applied になり、取り消しで捨てる）
// - effective = draft ?? applied を <html> の属性と CSS 変数に反映する
// 研究データ（IndexedDB / サーバー）には触れない。
import { createContext, ReactNode, useCallback, useContext, useEffect, useLayoutEffect, useMemo, useState } from 'react'
import { getLayout } from './layouts/registry'
import type { LayoutSpec } from './layouts/types'
import {
  applySelection, Customization, DEFAULT_CUSTOM, isDefaultCustom, LayoutId, loadPrefs, ORIGINAL, sameSelection, sanitizeSelection,
  savePrefs, STORAGE_KEY, StoredPrefs, UiSelection, undoSelection,
} from './prefs'

export interface Resolved {
  density: 'compact' | 'standard' | 'comfortable'
  card: 'outline' | 'shadow' | 'flat'
  radius: 'sharp' | 'standard' | 'round'
  sidebarMode: 'expanded' | 'icons' | 'hidden'
  sidebarPos: 'left' | 'right'
}

interface Ctx {
  prefs: StoredPrefs
  draft: UiSelection | null
  effective: UiSelection
  spec: LayoutSpec
  resolved: Resolved
  previewing: boolean
  saveFailed: boolean
  /** 直近の操作の結果（読み上げ用） */
  announce: string
  previewLayout: (id: LayoutId) => void
  previewCustom: (c: Partial<Customization>) => void
  /** プレビューを経ずにすぐ保存する（文字サイズ・テーマ切替などヘッダーの即時操作）。プレビュー中は下書きに入れる */
  setCustomNow: (c: Partial<Customization>) => void
  apply: () => void
  cancel: () => void
  resetOriginal: () => void
  undo: () => void
}

const UiCtx = createContext<Ctx | null>(null)

export function resolve(sel: UiSelection, spec: LayoutSpec): Resolved {
  const c = sel.custom, d = spec.defaults
  return {
    density: c.density === 'auto' ? d.density : c.density,
    card: c.card === 'auto' ? d.card : c.card,
    radius: c.radius === 'auto' ? d.radius : c.radius,
    sidebarMode: c.sidebarMode === 'auto' ? d.sidebarMode : c.sidebarMode,
    sidebarPos: c.sidebarPos === 'auto' ? d.sidebarPos : c.sidebarPos,
  }
}

const ATTRS = ['data-ui', 'data-ux', 'data-density', 'data-card', 'data-radius', 'data-theme', 'data-fs'] as const
const VARS = ['--accent', '--accent-2', '--sel', '--u-fs-scale'] as const

/** <html> に設定を反映する。Original かつカスタマイズなしのときは data-ui="original" だけを付け、既存の見た目を一切変えない */
export function applyToDocument(sel: UiSelection, spec: LayoutSpec, el: HTMLElement = document.documentElement) {
  const r = resolve(sel, spec), c = sel.custom
  for (const a of ATTRS) el.removeAttribute(a)
  for (const v of VARS) el.style.removeProperty(v)
  el.setAttribute('data-ui', spec.id)
  const ux = spec.id !== 'original' || !isDefaultCustom({ ...c, theme: 'auto' })
  if (c.theme !== 'auto') el.setAttribute('data-theme', c.theme)
  if (!ux) return
  el.setAttribute('data-ux', '')
  el.setAttribute('data-density', r.density)
  el.setAttribute('data-card', r.card)
  el.setAttribute('data-radius', r.radius)
  if (c.fontScale !== 1) { el.setAttribute('data-fs', ''); el.style.setProperty('--u-fs-scale', String(c.fontScale)) }
  if (c.accent) {
    el.style.setProperty('--accent', c.accent)
    el.style.setProperty('--accent-2', `color-mix(in srgb, ${c.accent} 78%, #ffffff)`)
    el.style.setProperty('--sel', `color-mix(in srgb, ${c.accent} 14%, var(--card))`)
  }
}

export function UiPrefsProvider({ children }: { children: ReactNode }) {
  const [prefs, setPrefs] = useState<StoredPrefs>(() => loadPrefs())
  const [draft, setDraft] = useState<UiSelection | null>(null)
  const [saveFailed, setSaveFailed] = useState(false)
  const [announce, setAnnounce] = useState('')

  const effective = draft ?? prefs.applied
  const spec = getLayout(effective.layout)
  const resolved = useMemo(() => resolve(effective, spec), [effective, spec])

  useLayoutEffect(() => { applyToDocument(effective, spec) }, [effective, spec])

  // 別のタブで適用した設定に追従する（プレビュー中は利用者の操作を優先して上書きしない）
  useEffect(() => {
    const on = (e: StorageEvent) => { if (e.key === STORAGE_KEY && !draft) setPrefs(loadPrefs()) }
    window.addEventListener('storage', on)
    return () => window.removeEventListener('storage', on)
  }, [draft])

  const commit = useCallback((next: StoredPrefs, msg: string) => {
    setPrefs(next); setDraft(null)
    const ok = savePrefs(next)
    setSaveFailed(!ok)
    setAnnounce(ok ? msg : msg + '（この端末では保存できないため、再読み込みすると元に戻ります）')
  }, [])

  const previewLayout = useCallback((id: LayoutId) => {
    const base = draft ?? prefs.applied
    const next = sanitizeSelection({ ...base, layout: id })
    setDraft(sameSelection(next, prefs.applied) ? null : next)
    setAnnounce(`${getLayout(id).name} をプレビュー中です。保存するには「適用」を押してください。`)
  }, [draft, prefs.applied])

  const previewCustom = useCallback((c: Partial<Customization>) => {
    const base = draft ?? prefs.applied
    const next = sanitizeSelection({ ...base, custom: { ...base.custom, ...c } })
    setDraft(sameSelection(next, prefs.applied) ? null : next)
  }, [draft, prefs.applied])

  const setCustomNow = useCallback((c: Partial<Customization>) => {
    if (draft) { previewCustom(c); return }
    const next = sanitizeSelection({ ...prefs.applied, custom: { ...prefs.applied.custom, ...c } })
    commit(applySelection(prefs, next), '表示設定を保存しました。')
  }, [draft, prefs, previewCustom, commit])

  const apply = useCallback(() => {
    if (!draft) return
    commit(applySelection(prefs, draft), `${getLayout(draft.layout).name} を適用しました。`)
  }, [draft, prefs, commit])

  const cancel = useCallback(() => { setDraft(null); setAnnounce('プレビューを取り消しました。') }, [])

  const resetOriginal = useCallback(() => {
    commit(applySelection(prefs, { layout: 'original', custom: { ...DEFAULT_CUSTOM } }), 'Original（現在の標準デザイン）に戻しました。')
  }, [prefs, commit])

  const undo = useCallback(() => {
    if (!prefs.history.length) return
    const next = undoSelection(prefs)
    commit(next, `${getLayout(next.applied.layout).name} に戻しました。`)
  }, [prefs, commit])

  const value: Ctx = {
    prefs, draft, effective, spec, resolved, previewing: !!draft, saveFailed, announce,
    previewLayout, previewCustom, setCustomNow, apply, cancel, resetOriginal, undo,
  }
  return <UiCtx.Provider value={value}>{children}</UiCtx.Provider>
}

export function useUi(): Ctx {
  const c = useContext(UiCtx)
  if (!c) throw new Error('UiPrefsProvider がありません')
  return c
}

export { ORIGINAL }
