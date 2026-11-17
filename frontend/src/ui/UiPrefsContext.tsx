// 表示設定の状態管理。
// - applied: 保存済み（再読み込み後も維持）
// - draft:   プレビュー中の設定（保存していない。適用で applied になり、取り消しで捨てる）
// - effective = draft ?? applied を <html> の属性と CSS 変数に反映する
// 研究データ（IndexedDB / サーバー）には触れない。
import { createContext, ReactNode, useCallback, useContext, useEffect, useLayoutEffect, useMemo, useState } from 'react'
import { getLayout } from './layouts/registry'
import type { LayoutSpec } from './layouts/types'
import {
  accentForScheme, applySelection, Customization, DEFAULT_CUSTOM, LayoutId, loadPrefs, replaceApplied, sameSelection, sanitizeSelection,
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
  /** いまダーク配色で表示しているか（配色=ダーク、または 配色=端末に合わせる で端末がダーク） */
  dark: boolean
  /** 実際に画面で使っている主色（ダーク配色では、選んだ色を読める明るさに調整した色）。主色が「自動」なら null */
  accentShown: string | null
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

const ATTRS = ['data-ui', 'data-ux', 'data-density', 'data-card', 'data-radius', 'data-theme'] as const
const VARS = ['--accent', '--accent-2', '--sel', '--u-accent-user', '--u-fs-scale'] as const

/** 端末がダーク配色か（matchMedia のない環境ではライトとして扱う） */
const osDarkQuery = () => (typeof window !== 'undefined' && typeof window.matchMedia === 'function' ? window.matchMedia('(prefers-color-scheme: dark)') : null)

/**
 * <html> に設定を反映する。
 * Original で、見た目のカスタマイズ（主色・文字の大きさ・密度・カード・角丸）がないときは data-ui="original"（と配色）だけを付け、
 * 既存の見た目を一切変えない。サイドバーの位置・表示だけを変えたときも同じ（サイドバーは .shell の data-sidebar で切り替える）。
 * 判定は「自動」を解決した後の値で行う（Original の既定と同じ値を明示しただけなら、カスタマイズなしとして扱う）。
 */
export function applyToDocument(sel: UiSelection, spec: LayoutSpec, el: HTMLElement = document.documentElement, dark = false) {
  const r = resolve(sel, spec), c = sel.custom, d = spec.defaults
  for (const a of ATTRS) el.removeAttribute(a)
  for (const v of VARS) el.style.removeProperty(v)
  el.setAttribute('data-ui', spec.id)
  const ux = spec.id !== 'original' || !!c.accent || c.fontScale !== 1 || r.density !== d.density || r.card !== d.card || r.radius !== d.radius
  if (c.theme !== 'auto') el.setAttribute('data-theme', c.theme)
  if (!ux) return
  el.setAttribute('data-ux', '')
  el.setAttribute('data-density', r.density)
  el.setAttribute('data-card', r.card)
  el.setAttribute('data-radius', r.radius)
  if (c.fontScale !== 1) el.style.setProperty('--u-fs-scale', String(c.fontScale))
  if (c.accent) {
    // ダーク配色では、選んだ色（白文字向けの濃い色）をそのまま使うと文字・枠線が読めないので、読める明るさに調整した色を使う
    const accent = accentForScheme(c.accent, dark)
    el.style.setProperty('--accent', accent)
    el.style.setProperty('--u-accent-user', c.accent) // 選んだ色そのもの（印刷はこちらを使う。layouts.css の @media print）
    // color-mix() のない Safari（16.1 以前）では、主色そのものと、主色の薄い透過色で代用する
    const mix = typeof CSS !== 'undefined' && typeof CSS.supports === 'function' && CSS.supports('color', 'color-mix(in srgb, red, blue)')
    el.style.setProperty('--accent-2', mix ? `color-mix(in srgb, ${accent} 78%, #ffffff)` : accent)
    el.style.setProperty('--sel', mix ? `color-mix(in srgb, ${accent} 14%, var(--card))` : `${accent}24`)
  }
}

export function UiPrefsProvider({ children }: { children: ReactNode }) {
  const [prefs, setPrefs] = useState<StoredPrefs>(() => loadPrefs())
  const [draft, setDraft] = useState<UiSelection | null>(null)
  const [saveFailed, setSaveFailed] = useState(false)
  const [announce, setAnnounce] = useState('')
  const [osDark, setOsDark] = useState(() => !!osDarkQuery()?.matches)

  const effective = draft ?? prefs.applied
  const spec = getLayout(effective.layout)
  const resolved = useMemo(() => resolve(effective, spec), [effective, spec])
  const dark = effective.custom.theme === 'dark' || (effective.custom.theme === 'auto' && osDark)

  useLayoutEffect(() => { applyToDocument(effective, spec, document.documentElement, dark) }, [effective, spec, dark])

  // 端末の配色（ライト／ダーク）が変わったら、主色の調整をやり直す
  useEffect(() => {
    const mq = osDarkQuery()
    if (!mq) return
    const on = () => setOsDark(mq.matches)
    if (mq.addEventListener) { mq.addEventListener('change', on); return () => mq.removeEventListener('change', on) }
    mq.addListener(on); return () => mq.removeListener(on) // Safari 13 以前
  }, [])

  // 別のタブで適用した設定に追従する（プレビュー中は利用者の操作を優先して上書きしない。取り消し・適用のときに読み直す）。
  // e.key が null なのは localStorage.clear()（保存値がすべて消えた）のとき
  useEffect(() => {
    const on = (e: StorageEvent) => { if ((e.key === STORAGE_KEY || e.key === null) && !draft) setPrefs(loadPrefs()) }
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
    // 適用中の設定と同じになったら、プレビューは終わり（保存するものがない）
    const same = sameSelection(next, prefs.applied)
    setDraft(same ? null : next)
    setAnnounce(same ? `${getLayout(id).name} は適用中の設定です（プレビューを終了しました）。` : `${getLayout(id).name} をプレビュー中です。保存するには「適用」を押してください。`)
  }, [draft, prefs.applied])

  const previewCustom = useCallback((c: Partial<Customization>) => {
    const base = draft ?? prefs.applied
    const next = sanitizeSelection({ ...base, custom: { ...base.custom, ...c } })
    setDraft(sameSelection(next, prefs.applied) ? null : next)
  }, [draft, prefs.applied])

  // 即時の操作は適用中の設定だけを置き換える（「元に戻す」の履歴は「適用」「Original に戻す」のときだけ積む）
  const setCustomNow = useCallback((c: Partial<Customization>) => {
    if (draft) { previewCustom(c); return }
    const next = replaceApplied(prefs, { ...prefs.applied, custom: { ...prefs.applied.custom, ...c } })
    if (next !== prefs) commit(next, '表示設定を保存しました。')
  }, [draft, prefs, previewCustom, commit])

  // プレビュー中は別のタブの変更（storage イベント）を取り込んでいないので、適用・取り消し・Original に戻すのときに保存値を読み直す。
  // 適用は、別のタブが保存した設定と履歴の上に積む（古い状態で上書きして消さない）。保存できない環境ではメモリー上の値を使う
  const latest = useCallback(() => (draft && !saveFailed ? loadPrefs() : prefs), [draft, saveFailed, prefs])

  const apply = useCallback(() => {
    if (!draft) return
    commit(applySelection(latest(), draft), `${getLayout(draft.layout).name} を適用しました。`)
  }, [draft, latest, commit])

  const cancel = useCallback(() => {
    setDraft(null)
    if (!saveFailed) setPrefs(loadPrefs())
    setAnnounce('プレビューを取り消しました。')
  }, [saveFailed])

  const resetOriginal = useCallback(() => {
    commit(applySelection(latest(), { layout: 'original', custom: { ...DEFAULT_CUSTOM } }), 'Original（現在の標準デザイン）に戻しました。')
  }, [latest, commit])

  const undo = useCallback(() => {
    if (!prefs.history.length) return
    const next = undoSelection(prefs)
    commit(next, `${getLayout(next.applied.layout).name} に戻しました。`)
  }, [prefs, commit])

  const value = useMemo<Ctx>(() => ({
    prefs, draft, effective, spec, resolved, previewing: !!draft, saveFailed, announce,
    dark, accentShown: effective.custom.accent ? accentForScheme(effective.custom.accent, dark) : null,
    previewLayout, previewCustom, setCustomNow, apply, cancel, resetOriginal, undo,
  }), [prefs, draft, effective, spec, resolved, saveFailed, announce, dark, previewLayout, previewCustom, setCustomNow, apply, cancel, resetOriginal, undo])
  return <UiCtx.Provider value={value}>{children}</UiCtx.Provider>
}

export function useUi(): Ctx {
  const c = useContext(UiCtx)
  if (!c) throw new Error('UiPrefsProvider がありません')
  return c
}
