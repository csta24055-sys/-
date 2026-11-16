// Original: 改修前の UI をそのまま再現する（DOM 構造・クラス名・文言を変えない）。
// 改修前の main.tsx の Shell から、サイドバー・下部タブ・その他メニューを移しただけ。
import { Link, NavLink } from 'react-router-dom'
import { NAV } from '../../app/navigation'
import type { LayoutSpec, SlotProps } from './types'

const BASE = import.meta.env.BASE_URL || '/'
const TAB_MAIN = ['/', '/library', '/data', '/simulator']

function Side() {
  return (
    <aside className="side">
      <div className="brand"><img src={BASE + 'icon.svg'} alt="" /><div><b>Air Quality</b><span>Research OS</span></div></div>
      <nav>{NAV.map(({ to, label, icon }) => <NavLink key={to} to={to} end={to === '/'}><i aria-hidden>{icon}</i>{label}</NavLink>)}</nav>
      <div className="side-foot">日本大学 理工学部 井口研究室<br />空気清浄度研究アーカイブ</div>
    </aside>
  )
}

function Bottom({ openMore, st }: SlotProps) {
  const moreActive = !TAB_MAIN.includes(st.pathname) && !st.pathname.startsWith('/library')
  return (
    <nav className="tabbar" aria-label="メインメニュー">
      {NAV.filter(({ to }) => TAB_MAIN.includes(to)).map(({ to, short, icon }) => <NavLink key={to} to={to} end={to === '/'}><i aria-hidden>{icon}</i><span>{short}</span></NavLink>)}
      <a href="#more" className={moreActive ? 'active' : ''} onClick={(e) => { e.preventDefault(); openMore() }}><i aria-hidden>☰</i><span>その他</span></a>
    </nav>
  )
}

function More({ onClose }: { onClose: () => void }) {
  return (
    <div className="sheet-bg" onClick={onClose}>
      <nav className="sheet" aria-label="その他のメニュー" onClick={(e) => e.stopPropagation()}>
        {NAV.filter(({ to }) => !TAB_MAIN.includes(to)).map(({ to, label, icon }) => <Link key={to} to={to} onClick={onClose}><i aria-hidden>{icon}</i>{label}</Link>)}
        <button className="ghost" onClick={onClose}>閉じる</button>
      </nav>
    </div>
  )
}

export const original: LayoutSpec = {
  id: 'original',
  name: 'Original',
  title: '現在の標準デザイン',
  audience: 'これまでどおりの利用者全員',
  summary: '改修前の画面をそのまま使います。左のサイドバーに全10機能、スマホは下部タブ4つ＋その他。',
  traits: ['改修前と同じ配置・色・文字', '左サイドバー（236px）', 'スマホ: 下部タブ＋その他メニュー'],
  basis: '既存アプリ（claude/air-quality-research-os-19gu2g）',
  mobileTabs: TAB_MAIN,
  defaults: { density: 'standard', card: 'outline', radius: 'standard', sidebarMode: 'expanded', sidebarPos: 'left' },
  palette: false,
  mini: { top: 'none', side: 'wide', aside: false, bottom: 'none', tabs: 5 },
  slots: { Side, Bottom, More },
}
