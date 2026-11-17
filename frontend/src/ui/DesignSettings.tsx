// 設定画面の「デザイン」項目。
// カードを押す → 画面全体がそのレイアウトでプレビューされる（保存しない）→「適用」で保存／「取り消す」で元のまま。
// 「Original に戻す」は1回押すだけで標準デザインに戻して保存する。「元に戻す」で直前の設定に戻せる。
import { KeyboardEvent, useRef, useState } from 'react'
import { LAYOUTS } from './layouts/registry'
import type { LayoutSpec } from './layouts/types'
import { ACCENT_PRESETS, contrastRatio, Customization, DARK_ON_ACCENT, DEFAULT_CUSTOM, FONT_SCALES, isDefaultCustom } from './prefs'
import { useUi } from './UiPrefsContext'

export function Mini({ spec }: { spec: LayoutSpec }) {
  const m = spec.mini
  return (
    <div className="ux-mini" data-id={spec.id} data-top={m.top} data-side={m.side} aria-hidden>
      {m.top !== 'none' && <div className="m-top" />}
      <div className="m-body">
        <div className="m-side">{Array.from({ length: m.side === 'rail' ? 6 : 7 }, (_, i) => <i key={i} />)}</div>
        <div className="m-main"><div className="m-kpis"><i /><i /><i /></div><div className="m-cards"><i /><i /></div><div className="m-row" /></div>
        {m.aside && <div className="m-aside"><i /><i /><i /></div>}
      </div>
      {m.bottom === 'jobs' && <div className="m-jobs" />}
    </div>
  )
}

/**
 * 選択肢のグループ（role=radiogroup）のキーボード操作。ラジオボタンと同じく、Tab で止まるのはグループに 1 回だけ
 * （選択中の項目）で、← ↑ で前、→ ↓ で次の項目へ移って選択する（端では反対側へ回る）。
 */
function onRadioKeys(e: KeyboardEvent<HTMLElement>) {
  const d = e.key === 'ArrowRight' || e.key === 'ArrowDown' ? 1 : e.key === 'ArrowLeft' || e.key === 'ArrowUp' ? -1 : 0
  const cur = e.target as HTMLElement
  if (!d || cur.getAttribute('role') !== 'radio') return
  const radios = [...e.currentTarget.querySelectorAll<HTMLElement>('[role="radio"]')]
  const i = radios.indexOf(cur)
  if (i < 0) return
  e.preventDefault()
  const next = radios[(i + d + radios.length) % radios.length]
  next.focus(); next.click()
}

function Seg<T extends string | number>({ label, value, options, onChange }: { label: string; value: T; options: [T, string][]; onChange: (v: T) => void }) {
  // どれも選択中でないとき（保存値が選択肢にない場合）は、先頭の項目で Tab を受ける
  const none = !options.some(([v]) => v === value)
  return (
    <div className="ux-field">
      <span className="ux-field-l" id={`seg-${label}`}>{label}</span>
      <div className="ux-segs" role="radiogroup" aria-labelledby={`seg-${label}`} onKeyDown={onRadioKeys}>
        {options.map(([v, l], k) => <button key={String(v)} type="button" role="radio" aria-checked={value === v} tabIndex={value === v || (none && k === 0) ? 0 : -1} onClick={() => onChange(v)}>{l}</button>)}
      </div>
    </div>
  )
}

function Customizer() {
  const ui = useUi()
  const c = ui.effective.custom
  const set = (p: Partial<Customization>) => ui.previewCustom(p)
  const accent = c.accent
  // ライト配色では主色の上に白い文字を載せる。ダーク配色では主色を明るく調整して使い、濃い文字を載せる（UiPrefsContext / prefs.accentForScheme）。
  // 表示する比は、実際に画面で使っている色どうしの比にする
  const shown = ui.accentShown
  const onAccent = ui.dark ? (ui.spec.id === 'original' ? DARK_ON_ACCENT.original : DARK_ON_ACCENT.other) : '#ffffff'
  const ratio = accent && shown ? contrastRatio(shown, onAccent) : null
  const presetChecked = !accent || (ACCENT_PRESETS as readonly string[]).includes(accent)
  // 開閉は利用者の操作だけで変える（初期値に戻しても閉じない）
  const [open, setOpen] = useState(() => !isDefaultCustom(c))
  return (
    <details className="ux-custom" open={open} onToggle={(e) => setOpen(e.currentTarget.open)}>
      <summary>詳細カスタマイズ（色・配置・サイドバー・文字・カード・密度）</summary>
      <p className="small muted">変更はすぐ画面に反映されます（プレビュー）。保存するには上の「適用」を押してください。「自動」は選んだデザインの既定値です。</p>
      <div className="ux-field">
        <span className="ux-field-l" id="ux-accent-l">主色</span>
        <div className="ux-swatches" role="radiogroup" aria-labelledby="ux-accent-l" onKeyDown={onRadioKeys}>
          <button type="button" role="radio" aria-checked={!accent} tabIndex={!accent || !presetChecked ? 0 : -1} onClick={() => set({ accent: null })} className="ux-sw-auto">自動</button>
          {ACCENT_PRESETS.map((h) => <button key={h} type="button" role="radio" aria-checked={accent === h} tabIndex={accent === h ? 0 : -1} aria-label={`主色 ${h}`} style={{ background: h }} className="ux-sw" onClick={() => set({ accent: h })} />)}
          <label className="ux-sw-custom">自由に選ぶ <input type="color" value={accent || '#0f5b5c'} onChange={(e) => set({ accent: e.target.value })} aria-label="主色を自由に選ぶ" /></label>
        </div>
        {ratio !== null && !ui.dark && <span className={`small ux-accent-ratio ${ratio < 4.5 ? 'ux-warn' : 'muted'}`} role={ratio < 4.5 ? 'alert' : undefined}>白い文字とのコントラスト比 {ratio}:1{ratio < 4.5 ? ' — 4.5:1 未満のため、ボタンの文字が読みにくくなります。濃い色を選んでください。' : '（4.5:1 以上で読みやすい）'}</span>}
        {ratio !== null && ui.dark && <span className="small muted ux-accent-ratio">ダーク配色では、{shown === accent ? '選んだ色をそのまま使います' : <>選んだ色を明るく調整して使います（<code>{shown}</code>）</>}。ボタンの濃い文字とのコントラスト比 {ratio}:1（4.5:1 以上で読みやすい）</span>}
      </div>
      <Seg label="文字の大きさ" value={c.fontScale} options={FONT_SCALES.map((s) => [s, s === 1 ? '標準' : s < 1 ? '小' : s < 1.2 ? '大' : '特大'] as [number, string])} onChange={(v) => set({ fontScale: v })} />
      <Seg label="情報密度" value={c.density} options={[['auto', '自動'], ['compact', '詰める'], ['standard', '標準'], ['comfortable', 'ゆったり']]} onChange={(v) => set({ density: v })} />
      <Seg label="サイドバーの位置" value={c.sidebarPos} options={[['auto', '自動'], ['left', '左'], ['right', '右']]} onChange={(v) => set({ sidebarPos: v })} />
      <Seg label="サイドバーの表示" value={c.sidebarMode} options={[['auto', '自動'], ['expanded', '展開'], ['icons', 'アイコンのみ'], ['hidden', '隠す']]} onChange={(v) => set({ sidebarMode: v })} />
      <Seg label="カード" value={c.card} options={[['auto', '自動'], ['outline', '枠線'], ['shadow', '影'], ['flat', 'フラット']]} onChange={(v) => set({ card: v })} />
      <Seg label="角の丸み" value={c.radius} options={[['auto', '自動'], ['sharp', '小さい'], ['standard', '標準'], ['round', '大きい']]} onChange={(v) => set({ radius: v })} />
      <Seg label="配色" value={c.theme} options={[['auto', '端末に合わせる'], ['light', 'ライト'], ['dark', 'ダーク']]} onChange={(v) => set({ theme: v })} />
      {c.sidebarMode === 'hidden' && <p className="small muted">サイドバーを隠しても、画面上部の「☰／すべての機能」（Original では下部のメニュー）から全機能を開けます。</p>}
      <button type="button" className="ghost" onClick={() => set({ ...DEFAULT_CUSTOM })} disabled={isDefaultCustom(c)}>カスタマイズを初期値に戻す</button>
    </details>
  )
}

export default function DesignSettings() {
  const ui = useUi()
  const group = useRef<HTMLDivElement>(null)
  const applied = LAYOUTS.find((l) => l.id === ui.prefs.applied.layout)!
  const sel = ui.spec
  const onKey = (e: KeyboardEvent<HTMLDivElement>) => {
    const i = LAYOUTS.findIndex((l) => l.id === sel.id)
    const d = e.key === 'ArrowRight' || e.key === 'ArrowDown' ? 1 : e.key === 'ArrowLeft' || e.key === 'ArrowUp' ? -1 : 0
    if (!d) return
    e.preventDefault()
    const n = LAYOUTS[(i + d + LAYOUTS.length) % LAYOUTS.length]
    ui.previewLayout(n.id)
    requestAnimationFrame(() => (group.current?.querySelector(`[data-layout="${n.id}"]`) as HTMLElement | null)?.focus())
  }
  return (
    <section className="card ux-design" id="design" aria-labelledby="ux-design-h">
      <header className="card-h"><h2 id="ux-design-h">デザイン</h2>
        <span className="small muted">適用中: <b>{applied.name}</b>{ui.previewing && <> ／ プレビュー中: <b>{sel.name}</b>（未保存）</>}</span></header>
      <p className="small">5種類の画面デザインから選べます。どれを選んでも、データ・計算結果・機能は同じです（見た目・配置・情報の並び順だけが変わります）。この設定はこの端末のブラウザだけに保存され、研究データやバックアップには影響しません。</p>
      <div className="ux-design-grid" role="radiogroup" aria-label="デザインの種類" ref={group} onKeyDown={onKey}>
        {LAYOUTS.map((l) => {
          const on = sel.id === l.id
          return (
            <button key={l.id} type="button" role="radio" aria-checked={on} tabIndex={on ? 0 : -1} data-layout={l.id} className="ux-dcard" onClick={() => ui.previewLayout(l.id)}>
              <Mini spec={l} />
              <span className="ux-dcard-name">{l.name}{ui.prefs.applied.layout === l.id && <span className="ux-pill">適用中</span>}</span>
              <span className="ux-dcard-title">{l.title}</span>
              <ul className="ux-dcard-traits">{l.traits.map((t) => <li key={t}>{t}</li>)}</ul>
            </button>
          )
        })}
      </div>
      <div className="ux-design-detail" aria-live="polite">
        <b>{sel.name} — {sel.title}</b>
        <p className="small">{sel.summary}</p>
        <p className="small muted">想定利用者: {sel.audience} ／ 根拠: {sel.basis}</p>
      </div>
      <div className="ux-design-actions">
        <button type="button" onClick={ui.apply} disabled={!ui.previewing}>適用</button>
        <button type="button" className="ghost" onClick={ui.cancel} disabled={!ui.previewing}>取り消す</button>
        <button type="button" className="ghost" onClick={ui.resetOriginal} disabled={ui.prefs.applied.layout === 'original' && isDefaultCustom(ui.prefs.applied.custom) && !ui.previewing}>Original に戻す</button>
        <button type="button" className="ghost" onClick={ui.undo} disabled={!ui.prefs.history.length || ui.previewing}>元に戻す（直前の設定）</button>
      </div>
      {ui.saveFailed && <p className="ux-warn small" role="alert">この端末のブラウザに設定を保存できませんでした（プライベートモード等）。今の画面では有効ですが、再読み込みすると元に戻ります。</p>}
      <Customizer />
    </section>
  )
}
