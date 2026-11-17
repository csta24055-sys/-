import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { LAYOUTS, getLayout } from './layouts/registry'
import { HOME_SECTIONS, resolveHomeOrder } from '../app/homeSections'
import { NAV } from '../app/navigation'
import {
  ACCENT_PRESETS, accentForScheme, applySelection, contrastRatio, DARK_ON_ACCENT, DEFAULT_CUSTOM, defaultPrefs, LAYOUT_IDS, loadPrefs, mixWithWhite, parsePrefs,
  replaceApplied, sanitizeCustom, savePrefs, STORAGE_KEY, undoSelection,
} from './prefs'

const mem = () => { const m = new Map<string, string>(); return { getItem: (k: string) => m.get(k) ?? null, setItem: (k: string, v: string) => { m.set(k, v) }, m } }

describe('表示設定の保存と検証', () => {
  it('未保存・壊れた値・未知のレイアウトは Original になる', () => {
    expect(parsePrefs(null).applied.layout).toBe('original')
    expect(parsePrefs('{壊れた').applied.layout).toBe('original')
    expect(parsePrefs(JSON.stringify({ version: 1, applied: { layout: 'unknown' } })).applied.layout).toBe('original')
    expect(parsePrefs(JSON.stringify({ version: 99, applied: { layout: 'research' } })).applied.layout).toBe('original')
  })
  it('カスタマイズの不正値は既定に丸める', () => {
    const c = sanitizeCustom({ accent: 'red', fontScale: 9, density: 'x', sidebarPos: 'right', theme: 'dark' })
    expect(c.accent).toBeNull(); expect(c.fontScale).toBe(1.4); expect(c.density).toBe('auto'); expect(c.sidebarPos).toBe('right'); expect(c.theme).toBe('dark')
    expect(sanitizeCustom({ accent: '#ABCDEF' }).accent).toBe('#abcdef')
  })
  it('適用は履歴に積み、元に戻すで直前に戻る', () => {
    let p = defaultPrefs()
    p = applySelection(p, { layout: 'research', custom: DEFAULT_CUSTOM })
    p = applySelection(p, { layout: 'enterprise', custom: { ...DEFAULT_CUSTOM, density: 'compact' } })
    expect(p.applied.layout).toBe('enterprise'); expect(p.history.map((h) => h.layout)).toEqual(['research', 'original'])
    p = undoSelection(p); expect(p.applied.layout).toBe('research')
    p = undoSelection(p); expect(p.applied.layout).toBe('original'); expect(undoSelection(p)).toBe(p)
  })
  it('同じ設定の適用は履歴を増やさない', () => {
    const p = applySelection(defaultPrefs(), { layout: 'original', custom: DEFAULT_CUSTOM })
    expect(p.history).toHaveLength(0)
  })
  it('localStorage の専用キーだけに保存し、再読み込みで復元する', () => {
    const s = mem()
    const p = applySelection(defaultPrefs(), { layout: 'public', custom: { ...DEFAULT_CUSTOM, fontScale: 1.3 } })
    expect(savePrefs(p, s)).toBe(true)
    expect([...s.m.keys()]).toEqual([STORAGE_KEY])
    const r = loadPrefs(s); expect(r.applied.layout).toBe('public'); expect(r.applied.custom.fontScale).toBe(1.3)
  })
  it('保存に失敗しても例外を出さない', () => {
    expect(savePrefs(defaultPrefs(), { setItem: () => { throw new Error('QuotaExceeded') } })).toBe(false)
    expect(loadPrefs({ getItem: () => { throw new Error('SecurityError') } }).applied.layout).toBe('original')
  })
  it('即時の表示操作（配色・文字サイズ・サイドバー開閉）は履歴に積まない — 何回切り替えても「元に戻す」で直前のレイアウトへ戻れる', () => {
    let p = applySelection(defaultPrefs(), { layout: 'enterprise', custom: DEFAULT_CUSTOM })
    expect(p.history.map((h) => h.layout)).toEqual(['original'])
    for (const theme of ['light', 'dark', 'auto', 'light', 'dark', 'auto', 'light'] as const) p = replaceApplied(p, { ...p.applied, custom: { ...p.applied.custom, theme } })
    expect(p.applied.custom.theme).toBe('light')
    expect(p.history.map((h) => h.layout)).toEqual(['original'])
    expect(replaceApplied(p, p.applied)).toBe(p) // 同じ設定なら何も変えない
    expect(undoSelection(p).applied.layout).toBe('original')
  })
  it('ダーク配色の主色: 暗い地の上で読める明るさに調整する（ライトでは選んだ色のまま・明るい色は変えない）', () => {
    expect(mixWithWhite('#000000', 0.5)).toBe('#808080')
    expect(mixWithWhite('#5b3fa0', 1)).toBe('#5b3fa0')
    for (const h of ACCENT_PRESETS) {
      expect(accentForScheme(h, false)).toBe(h)
      const d = accentForScheme(h, true)
      // 5 レイアウトのダークのカード・チップと、塗りボタンに載せる濃い文字のどれに対しても 4.5:1 以上
      for (const bg of ['#1a2221', '#1a1f25', '#17202a', '#1b201c', '#171b22', '#233130', '#232a32', '#22303d', '#232a24', '#20252e']) expect(contrastRatio(d, bg)).toBeGreaterThanOrEqual(4.5)
      expect(contrastRatio(d, DARK_ON_ACCENT.other)).toBeGreaterThanOrEqual(4.5)
      expect(contrastRatio(d, DARK_ON_ACCENT.original)).toBeGreaterThanOrEqual(4.5)
    }
    expect(accentForScheme('#ffee58', true)).toBe('#ffee58')
    expect(contrastRatio(accentForScheme('#000000', true), '#232a32')).toBeGreaterThanOrEqual(6)
  })
  it('コントラスト比（WCAG）', () => {
    expect(contrastRatio('#000000', '#ffffff')).toBe(21)
    expect(contrastRatio('#00687a', '#ffffff')).toBeGreaterThan(4.5)
    expect(contrastRatio('#ffeb3b', '#ffffff')).toBeLessThan(4.5)
  })
})

describe('レイアウト登録表', () => {
  it('5種類が登録され、ID が prefs と一致する', () => {
    expect(LAYOUTS.map((l) => l.id)).toEqual([...LAYOUT_IDS])
    expect(getLayout('nope').id).toBe('original')
  })
  it('ホームの並び順: どのレイアウトも全ブロックをちょうど 1 回ずつ含み、Original は改修前の順のまま', () => {
    for (const l of LAYOUTS) expect([...l.homeOrder].sort()).toEqual([...HOME_SECTIONS].sort())
    expect(getLayout('original').homeOrder).toEqual([...HOME_SECTIONS])
    expect(resolveHomeOrder(['findings', 'nope', 'findings', 'stats'])).toEqual(['findings', 'stats', 'charts', 'timeline', 'completeness', 'activity'])
    expect(resolveHomeOrder(undefined)).toEqual([...HOME_SECTIONS])
  })
  it('起動時に属性を先付けする public/ui-init.js が、全レイアウトの ID と同じ保存キーを知っている', () => {
    const js = readFileSync(new URL('../../public/ui-init.js', import.meta.url), 'utf8')
    expect(js).toContain(`'${STORAGE_KEY}'`)
    const m = /\^\(([a-z|]+)\)\$/.exec(js)
    expect(m?.[1].split('|')).toEqual([...LAYOUT_IDS])
  })
  it('スマホの下部タブは実在する機能だけを指し、残りは「その他」で開ける（全レイアウト）', () => {
    for (const l of LAYOUTS) {
      for (const t of l.mobileTabs) expect(NAV.some((n) => n.to === t)).toBe(true)
      expect(l.slots.More || l.id === 'original').toBeTruthy()
      expect(l.slots.Bottom).toBeTruthy()
    }
  })
})
