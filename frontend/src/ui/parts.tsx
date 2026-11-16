// レイアウト間で共有する画面部品。業務ロジックは持たず、ナビゲーション定義（app/navigation.ts）と
// 読み取り専用の API（core/api.ts）だけを使う。
import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { GROUP_LABEL, NAV, NavItem, navByPath } from '../app/navigation'
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

/** プレビュー中だけ表示する帯。どの画面にいても適用・取り消しができる */
export function PreviewBar() {
  const ui = useUi()
  if (!ui.previewing) return null
  return (
    <div className="ux-previewbar noprint" role="region" aria-label="デザインのプレビュー">
      <span><b>プレビュー中:</b> {ui.spec.name}（{ui.spec.title}）— まだ保存していません</span>
      <span className="ux-previewbar-actions">
        <button onClick={ui.apply}>適用</button>
        <button className="ghost" onClick={ui.cancel}>取り消す</button>
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
  const input = useRef<HTMLInputElement>(null)
  const prev = useRef<Element | null>(null)
  const items = useMemo(() => {
    const t = q.trim().toLowerCase()
    return NAV.filter((n) => !t || (n.label + n.short + n.plain + n.to).toLowerCase().includes(t))
  }, [q])
  useEffect(() => { prev.current = document.activeElement; input.current?.focus(); return () => { (prev.current as HTMLElement | null)?.focus?.() } }, [])
  useEffect(() => { setI(0) }, [q])
  const go = (n: NavItem) => { onClose(); nav(n.to) }
  return (
    <div className="ux-modal-bg" onClick={onClose}>
      <div className="ux-palette" role="dialog" aria-modal="true" aria-label="すべての機能" onClick={(e) => e.stopPropagation()}
        onKeyDown={(e) => {
          if (e.key === 'Escape') { e.preventDefault(); onClose() }
          else if (e.key === 'ArrowDown') { e.preventDefault(); setI((x) => Math.min(items.length - 1, x + 1)) }
          else if (e.key === 'ArrowUp') { e.preventDefault(); setI((x) => Math.max(0, x - 1)) }
          else if (e.key === 'Enter' && items[i]) { e.preventDefault(); go(items[i]) }
        }}>
        <input ref={input} value={q} onChange={(e) => setQ(e.target.value)} placeholder="機能の名前で探す（例: レポート、シミュ）" aria-label="機能を検索"
          role="combobox" aria-expanded="true" aria-controls="ux-palette-list" aria-activedescendant={items[i] ? `ux-pal-${i}` : undefined} />
        <ul id="ux-palette-list" role="listbox" aria-label="機能の一覧">
          {items.map((n, k) => (
            <li key={n.to} id={`ux-pal-${k}`} role="option" aria-selected={k === i} className={k === i ? 'on' : ''} onMouseEnter={() => setI(k)} onClick={() => go(n)}>
              <NavIcon item={n} /><span><b>{n.label}</b><small>{n.plain}</small></span>
            </li>
          ))}
          {!items.length && <li className="muted" role="presentation">該当する機能がありません</li>}
        </ul>
        <p className="ux-palette-foot small muted">↑↓ で選択、Enter で移動、Esc で閉じる</p>
      </div>
    </div>
  )
}

/** スマホ・サイドバー非表示時の「その他／すべての機能」シート（分類ごと） */
export function MoreSheetGrouped({ onClose, exclude = [] }: { onClose: () => void; exclude?: string[] }) {
  const groups = (Object.keys(GROUP_LABEL) as NavItem['group'][]).map((g) => [g, NAV.filter((n) => n.group === g && !exclude.includes(n.to))] as const).filter(([, l]) => l.length)
  useEffect(() => {
    const on = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', on); return () => window.removeEventListener('keydown', on)
  }, [onClose])
  return (
    <div className="ux-sheet-bg" onClick={onClose}>
      <nav className="ux-sheet" aria-label="すべての機能" onClick={(e) => e.stopPropagation()}>
        {groups.map(([g, list]) => (
          <div key={g} className="ux-sheet-group"><h2>{GROUP_LABEL[g]}</h2>
            {list.map((n) => <Link key={n.to} to={n.to} onClick={onClose}><NavIcon item={n} /><span>{n.label}</span></Link>)}
          </div>
        ))}
        <button className="ghost" onClick={onClose}>閉じる</button>
      </nav>
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
  const cur = NAV.find((n) => n.to === st.pathname) || NAV.find((n) => n.to !== '/' && st.pathname.startsWith(n.to + '/')) || NAV[0]
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
