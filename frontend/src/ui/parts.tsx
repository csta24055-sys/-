// レイアウト間で共有する画面部品。業務ロジックは持たず、ナビゲーション定義（app/navigation.ts）と
// 読み取り専用の API（core/api.ts）だけを使う。
import { RefObject, useEffect, useMemo, useRef, useState } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { currentNav, GROUP_LABEL, NAV, NavItem, navByPath } from '../app/navigation'
import { applyUpdate, ShellState } from '../app/useShellState'
import { api, STANDALONE } from '../core/api'
import { listJobs } from '../core/cloud'
import { useAsync } from '../components/ui'
import { useUi } from './UiPrefsContext'

/** 更新・オフライン・バックアップの通知（Original と同じ文言・同じ構造） */
export function Banners({ st }: { st: ShellState }) {
  const { update, online, needBackup, pathname } = st
  return (
    <>
      {update && <div className="note update" role="status">新しい版があります。<button className="small" onClick={() => applyUpdate(update)}>更新する</button> <span className="small muted">端末内のデータはそのまま残ります。</span></div>}
      {!online && <div className="offline">{STANDALONE ? 'オフラインです — 端末内のデータで動作しています（クラウド解析は接続後に利用できます）。' : 'オフライン表示中 — 最後に取得したデータを表示しています。編集・アップロードは接続後に行ってください。'}</div>}
      {needBackup && pathname !== '/settings' && <div className="note">{needBackup === 'never' ? '端末内に保存したデータのバックアップがまだありません。' : '最後のバックアップから7日以上たっています。'}<Link to="/settings">設定・バックアップ</Link>から書き出してください。</div>}
    </>
  )
}

/**
 * 本文（main）へフォーカスを移す。帯・パレット・シートのように、押したあと自分が消える部品から呼ぶ
 * （消えた要素にフォーカスが残ると、キーボードの位置が文書の先頭に戻ってしまうため）。
 * Original の main は改修前と同じ DOM（tabindex なし）なので、フォーカスしている間だけ tabindex を付ける。
 */
export function focusMain() {
  requestAnimationFrame(() => {
    const m = document.querySelector<HTMLElement>('main.main')
    if (!m) return
    if (!m.hasAttribute('tabindex')) {
      m.setAttribute('tabindex', '-1')
      m.addEventListener('blur', () => { if (document.documentElement.getAttribute('data-ui') === 'original') m.removeAttribute('tabindex') }, { once: true })
    }
    m.focus({ preventScroll: true })
  })
}

const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex="0"]'

/**
 * 重ねて表示する部品（コマンドパレット・「すべての機能」シート）のキーボード操作。
 * - 開いたとき: フォーカスを中へ移す（initial があればその要素、なければ最初の操作対象）
 * - 開いている間: Tab / Shift+Tab は中だけを巡る（背面へ抜けない）。Esc はフォーカスの位置によらず閉じる
 * - 閉じたとき: 開く前にフォーカスがあった要素へ戻す。戻り値の ref を false にして閉じると（＝別の画面へ移動したとき）本文へ移す
 */
export function useModalFocus(box: RefObject<HTMLElement>, onClose: () => void, initial?: () => HTMLElement | null) {
  const close = useRef(onClose); close.current = onClose
  const init = useRef(initial); init.current = initial
  const restore = useRef(true)
  useEffect(() => {
    const prev = document.activeElement as HTMLElement | null
    const list = () => (box.current ? [...box.current.querySelectorAll<HTMLElement>(FOCUSABLE)].filter((e) => e.getClientRects().length > 0) : [])
    ;(init.current?.() ?? list()[0])?.focus()
    const on = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { e.preventDefault(); close.current(); return }
      if (e.key !== 'Tab' || !box.current) return
      const f = list()
      if (!f.length) { e.preventDefault(); return }
      const first = f[0], last = f[f.length - 1], cur = document.activeElement
      if (!box.current.contains(cur)) { e.preventDefault(); (e.shiftKey ? last : first).focus() }
      else if (e.shiftKey && cur === first) { e.preventDefault(); last.focus() }
      else if (!e.shiftKey && cur === last) { e.preventDefault(); first.focus() }
    }
    window.addEventListener('keydown', on, true)
    return () => {
      window.removeEventListener('keydown', on, true)
      if (!restore.current) focusMain()
      else if (prev && prev !== document.body) { if (prev.isConnected && prev.getClientRects().length > 0) prev.focus(); else focusMain() }
    }
  }, [box])
  return restore
}

/** プレビュー中だけ表示する帯。どの画面にいても適用・取り消しができる */
export function PreviewBar() {
  const ui = useUi()
  if (!ui.previewing) return null
  // 押すと帯ごと消えるので、フォーカスを本文へ移す（結果は読み上げ領域が伝える）
  return (
    <div className="ux-previewbar noprint" role="region" aria-label="デザインのプレビュー">
      <span><b>プレビュー中:</b> {ui.spec.name}（{ui.spec.title}）— まだ保存していません</span>
      <span className="ux-previewbar-actions">
        <button onClick={() => { ui.apply(); focusMain() }}>適用</button>
        <button className="ghost" onClick={() => { ui.cancel(); focusMain() }}>取り消す</button>
      </span>
    </div>
  )
}

/** 読み上げ用のライブリージョン（適用・取り消しの結果を伝える） */
export function Announcer() {
  const { announce } = useUi()
  return <div className="ux-sr" role="status" aria-live="polite">{announce}</div>
}

export function SkipLink() { return <a className="ux-skip" href="#main">本文へ移動</a> }

export function NavIcon({ item }: { item: NavItem }) { return <i aria-hidden className="ux-ico">{item.icon}</i> }

/** すべての機能の一覧（Ctrl+K / ⌘K）。どのレイアウトでも全機能へ到達できることを保証する入口 */
export function CommandPalette({ onClose }: { onClose: () => void }) {
  const [q, setQ] = useState('')
  const [i, setI] = useState(0)
  const nav = useNavigate()
  const box = useRef<HTMLDivElement>(null)
  const input = useRef<HTMLInputElement>(null)
  const items = useMemo(() => {
    const t = q.trim().toLowerCase()
    return NAV.filter((n) => !t || (n.label + n.short + n.plain + n.to).toLowerCase().includes(t))
  }, [q])
  // フォーカスできるのは入力欄だけなので、Tab は入力欄に留まる。Esc はどこにフォーカスがあっても閉じる
  const restore = useModalFocus(box, onClose, () => input.current)
  useEffect(() => { setI(0) }, [q])
  // ↑↓ で選んだ行が一覧の見える範囲の外にあれば、見える所までスクロールする
  useEffect(() => { document.getElementById(`ux-pal-${i}`)?.scrollIntoView({ block: 'nearest' }) }, [i, items])
  // 機能へ移動したときは、開く前の要素ではなく移動先の本文へフォーカスを移す
  const go = (n: NavItem) => { restore.current = false; onClose(); nav(n.to) }
  const has = items.length > 0
  return (
    <div className="ux-modal-bg" onClick={onClose}>
      <div ref={box} className="ux-palette" role="dialog" aria-modal="true" aria-label="すべての機能" onClick={(e) => e.stopPropagation()}
        onKeyDown={(e) => {
          if (e.key === 'ArrowDown') { e.preventDefault(); setI((x) => Math.min(items.length - 1, x + 1)) }
          else if (e.key === 'ArrowUp') { e.preventDefault(); setI((x) => Math.max(0, x - 1)) }
          else if (e.key === 'Enter' && items[i]) { e.preventDefault(); go(items[i]) }
        }}>
        <input ref={input} value={q} onChange={(e) => setQ(e.target.value)} placeholder="機能の名前で探す（例: レポート、シミュ）" aria-label="機能を検索"
          role="combobox" aria-autocomplete="list" aria-expanded={has} aria-controls={has ? 'ux-palette-list' : undefined} aria-activedescendant={has && items[i] ? `ux-pal-${i}` : undefined} />
        {/* 該当なしのときは一覧（listbox）を出さない（option のない listbox は ARIA 違反）。結果は下の role=status が読み上げる */}
        {has && (
          <ul id="ux-palette-list" role="listbox" aria-label="機能の一覧" tabIndex={-1}>
            {items.map((n, k) => (
              <li key={n.to} id={`ux-pal-${k}`} role="option" aria-selected={k === i} className={k === i ? 'on' : ''} onMouseEnter={() => setI(k)} onClick={() => go(n)}>
                <NavIcon item={n} /><span><b>{n.label}</b><small>{n.plain}</small></span>
              </li>
            ))}
          </ul>
        )}
        <p className="ux-palette-none muted" role="status">{has ? '' : '該当する機能がありません'}</p>
        <p className="ux-palette-foot small muted">↑↓ で選択、Enter で移動、Esc で閉じる</p>
      </div>
    </div>
  )
}

/** スマホ・サイドバー非表示時の「その他／すべての機能」シート（分類ごと） */
export function MoreSheetGrouped({ onClose, exclude = [] }: { onClose: () => void; exclude?: string[] }) {
  const groups = (Object.keys(GROUP_LABEL) as NavItem['group'][]).map((g) => [g, NAV.filter((n) => n.group === g && !exclude.includes(n.to))] as const).filter(([, l]) => l.length)
  const box = useRef<HTMLDivElement>(null)
  // 開いたら最初のリンクへフォーカスを移し、Tab は中だけを巡る。Esc・閉じるで、開いたボタンへ戻す
  const restore = useModalFocus(box, onClose)
  return (
    <div className="ux-sheet-bg" onClick={onClose}>
      <div ref={box} className="ux-sheet" role="dialog" aria-modal="true" aria-label="すべての機能" onClick={(e) => e.stopPropagation()}>
        {groups.map(([g, list]) => (
          <div key={g} className="ux-sheet-group"><h2>{GROUP_LABEL[g]}</h2>
            {list.map((n) => <Link key={n.to} to={n.to} onClick={() => { restore.current = false; onClose() }}><NavIcon item={n} /><span>{n.label}</span></Link>)}
          </div>
        ))}
        <button type="button" className="ghost" onClick={onClose}>閉じる</button>
      </div>
    </div>
  )
}

/** スマホの下部タブ（Original 以外の共通部品）。タブにない機能は「その他」から必ず開ける */
export function BottomNav({ tabs, openMore, pathname }: { tabs: string[]; openMore: () => void; pathname: string }) {
  const items = tabs.map(navByPath).filter(Boolean) as NavItem[]
  const inTabs = items.some((n) => (n.to === '/' ? pathname === '/' : pathname === n.to || pathname.startsWith(n.to + '/')))
  return (
    <nav className="ux-bottom" aria-label="メインメニュー">
      {items.map((n) => <NavLink key={n.to} to={n.to} end={n.to === '/'}><NavIcon item={n} /><span>{n.short}</span></NavLink>)}
      <button type="button" className={!inTabs ? 'active' : ''} aria-haspopup="dialog" onClick={openMore}><i aria-hidden className="ux-ico">☰</i><span>その他</span></button>
    </nav>
  )
}

const STORE_LABEL = STANDALONE ? '端末内（IndexedDB）' : 'サーバー（SQLite）'
export const storeLabel = STORE_LABEL

/** 根拠・状態パネル（Research の「根拠パネル」、Enterprise の「証跡」列）。実在する情報だけを表示する */
export function EvidencePanel({ st, title = '根拠と状態' }: { st: ShellState; title?: string }) {
  const { data: k } = useAsync(api.knowledge)
  const [jobs, setJobs] = useState<{ total: number; running: number } | null>(null)
  useEffect(() => { listJobs().then((j) => setJobs({ total: j.length, running: j.filter((x) => ['submitted', 'queued', 'in_progress'].includes(x.status)).length })).catch(() => setJobs(null)) }, [st.pathname])
  const cur = currentNav(st.pathname)
  return (
    <aside className="ux-aside" aria-label={title}>
      <h2>{title}</h2>
      <dl className="ux-dl">
        <dt>画面</dt><dd>{cur.label}</dd>
        <dt>URL</dt><dd><code>{st.pathname}</code></dd>
        <dt>保存先</dt><dd>{STORE_LABEL}</dd>
        <dt>接続</dt><dd>{st.online ? '● オンライン' : '○ オフライン'}</dd>
        <dt>資料取得日</dt><dd>{k?.meta?.accessed || '—'}</dd>
        <dt>知見・仮説</dt><dd>{k ? `${k.findings.length} 件・${k.hypotheses.length} 件` : '—'}</dd>
        <dt>クラウドジョブ</dt><dd>{jobs ? `${jobs.total} 件（実行中 ${jobs.running}）` : '—'}</dd>
        <dt>版</dt><dd>{import.meta.env.VITE_APP_VERSION || 'dev'}（{STANDALONE ? 'スマホ単体版' : 'サーバー版'}）</dd>
      </dl>
      <p className="small muted">計算は共通の計算エンジン（core/models.ts。Python 版と照合テスト済み）で行います。表示デザインを変えても計算結果は変わりません。</p>
    </aside>
  )
}

/** キーボードショートカット Ctrl+K / ⌘K でコマンドパレットを開く */
export function usePaletteShortcut(enabled: boolean, open: () => void) {
  useEffect(() => {
    if (!enabled) return
    const on = (e: KeyboardEvent) => { if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); open() } }
    window.addEventListener('keydown', on); return () => window.removeEventListener('keydown', on)
  }, [enabled, open])
}
