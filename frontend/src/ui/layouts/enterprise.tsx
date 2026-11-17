// Enterprise: 大企業品質 Federated Shell（design-research/D-enterprise）
// 骨格: スコープバー（誰が・どの範囲を見ているか）／アイコンレール 76px（展開 232px）／作業領域／「証跡」列
// 注意: このアプリには組織・ロール・承認の管理機能がない。スコープバーは実在する範囲（研究室・研究・保存先）だけを示し、
//       ロールは「単一利用者（権限管理なし）」と正直に表示する。存在しない組織切替・承認箱は作らない。
import { NavLink } from 'react-router-dom'
import { currentNav, NAV } from '../../app/navigation'
import { useUi } from '../UiPrefsContext'
import { BottomNav, EvidencePanel, MoreSheetGrouped, NavIcon, storeLabel } from '../parts'
import type { LayoutSpec, SlotProps } from './types'

const THEME_NEXT = { auto: 'light', light: 'dark', dark: 'auto' } as const
const THEME_LABEL = { auto: '自動', light: 'ライト', dark: 'ダーク' } as const

function Top({ openPalette, openMore, st }: SlotProps) {
  const ui = useUi()
  const theme = ui.effective.custom.theme
  return (
    <header className="ux-top ux-scopebar">
      <div className="ux-brand"><span className="ux-logo" aria-hidden>▣</span><b>AQROS</b></div>
      <nav className="ux-scope" aria-label="表示中のスコープ">
        <span className="ux-scope-chip">日本大学 井口研究室</span><span aria-hidden>›</span>
        <span className="ux-scope-chip">空気清浄度研究</span><span aria-hidden>›</span>
        <span className="ux-scope-chip">{storeLabel}</span>
      </nav>
      <div className="ux-top-actions">
        <span className="ux-role" title="このアプリには利用者・権限の管理機能はありません">ロール: 単一利用者（権限管理なし）</span>
        <button type="button" className="ux-cmd" onClick={openPalette} aria-label="コマンド（Ctrl+K）" aria-haspopup="dialog">コマンド <kbd>Ctrl</kbd> <kbd>K</kbd></button>
        <button type="button" className="ux-theme" onClick={() => ui.setCustomNow({ theme: THEME_NEXT[theme] })} aria-label={`配色: ${THEME_LABEL[theme]}（押すと切替）`}>配色: {THEME_LABEL[theme]}</button>
        <button type="button" className="ux-menu-btn" onClick={openMore} aria-label="すべての機能" aria-haspopup="dialog">☰</button>
      </div>
      <span className="ux-sr">現在の画面: {currentNav(st.pathname).label}</span>
    </header>
  )
}

function Side({ sidebarMode, toggleSidebar }: SlotProps) {
  const open = sidebarMode === 'expanded'
  return (
    <aside className="ux-side" aria-label="アプリのメニュー">
      <button type="button" className="ux-rail-toggle" onClick={toggleSidebar} aria-expanded={open} aria-label={open ? 'メニューを畳む' : 'メニューを展開'}><i aria-hidden className="ux-ico">☰</i><span className="ux-lbl-rail">{open ? '畳む' : '展開'}</span></button>
      <nav aria-label="アプリのメニュー">
        {NAV.map((n) => <NavLink key={n.to} to={n.to} end={n.to === '/'} className="ux-navlink" title={n.label}><NavIcon item={n} /><span className="ux-lbl-rail">{open ? n.label : n.short}</span></NavLink>)}
      </nav>
      <div className="ux-side-foot small muted">DS 1.0</div>
    </aside>
  )
}

function HomeIntro({ st }: SlotProps) {
  return (
    <section className="ux-scopehead" aria-label="スコープの見出し">
      <nav className="ux-bc small" aria-label="パンくず"><span>日本大学 井口研究室</span> › <span>空気清浄度研究</span> › <span>{storeLabel}</span> <span className="ux-scope-chip">ロール: 単一利用者</span></nav>
      <div className="ux-scope-actions">
        <span className="small muted">{st.online ? '● オンライン' : '○ オフライン'} ・ 固定レイアウトで表示</span>
        <button type="button" className="ghost" onClick={() => window.print()}>報告用に出力（印刷 / PDF）</button>
      </div>
    </section>
  )
}

function Aside({ st }: SlotProps) { return <EvidencePanel st={st} title="証跡" /> }
function Bottom(p: SlotProps) { return <BottomNav tabs={enterprise.mobileTabs} openMore={p.openMore} pathname={p.st.pathname} /> }

export const enterprise: LayoutSpec = {
  id: 'enterprise',
  name: 'Enterprise',
  title: '大企業品質 Federated Shell',
  audience: '複数の担当者が同じ画面骨格で運用する場面',
  summary: '「どの範囲を見ているか」をスコープバーで常に示し、全機能を同じシェル・アイコンレールで扱う。証跡列と密度切替付き。',
  traits: ['上部スコープバー（研究室 › 研究 › 保存先）', 'アイコンレール 76px ⇄ 展開 232px', '右に証跡列・テーマ切替・Ctrl+K'],
  basis: 'design-research/D-enterprise（案C Federated Shell 4.36点）',
  mobileTabs: ['/', '/library', '/data', '/simulator'],
  homeOrder: ['stats', 'charts', 'completeness', 'activity', 'findings', 'timeline'],
  defaults: { density: 'standard', card: 'outline', radius: 'sharp', sidebarMode: 'icons', sidebarPos: 'left' },
  palette: true,
  mini: { top: 'scope', side: 'rail', aside: true, bottom: 'none' },
  slots: { Top, Side, HomeIntro, Aside, Bottom, More: ({ onClose }) => <MoreSheetGrouped onClose={onClose} /> },
}
