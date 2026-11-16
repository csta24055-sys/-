// Commercial: 商用向け Outcome Hub（design-research/C-commercial）
// 骨格: 上部ヘッダー（検索・操作、主操作ボタン）／左レール 208px（成果物 → 作成 → 資料 の順にまとめる）
// ホームは「成果物」から始める（レポート・研究計画・データセット・試算）。料金・課金表示は実在しないので出さない。
import { Link, NavLink } from 'react-router-dom'
import { GROUP_LABEL, NAV, NavItem } from '../../app/navigation'
import { api } from '../../core/api'
import { useAsync } from '../../components/ui'
import { BottomNav, MoreSheetGrouped, NavIcon } from '../parts'
import type { LayoutSpec, SlotProps } from './types'

const ORDER: NavItem['group'][] = ['home', 'outcome', 'create', 'source', 'admin']

function Top({ openPalette, openMore }: SlotProps) {
  return (
    <header className="ux-top">
      <div className="ux-brand"><span className="ux-logo" aria-hidden>◆</span><b>空気清浄度研究</b><span className="muted">成果物ハブ</span></div>
      <div className="ux-top-actions">
        <button type="button" className="ghost ux-cmd" onClick={openPalette} aria-label="検索・操作（Ctrl+K）">⌕ 検索・操作 <kbd>Ctrl</kbd>+<kbd>K</kbd></button>
        <Link className="ux-btn-primary" to="/report">レポートを開く</Link>
        <button type="button" className="ghost ux-menu-btn" onClick={openMore} aria-label="すべての機能">☰</button>
      </div>
    </header>
  )
}

function Side({ sidebarMode, toggleSidebar }: SlotProps) {
  return (
    <aside className="ux-side" aria-label="メニュー">
      <nav aria-label="メニュー">
        {ORDER.map((g) => (
          <div key={g} className="ux-navgroup">
            {g !== 'home' && <h2 className="ux-side-h"><span className="ux-lbl">{GROUP_LABEL[g]}</span></h2>}
            {NAV.filter((n) => n.group === g).map((n) => <NavLink key={n.to} to={n.to} end={n.to === '/'} className="ux-navlink" title={n.label}><NavIcon item={n} /><span className="ux-lbl">{n.label}</span></NavLink>)}
          </div>
        ))}
      </nav>
      <div className="ux-side-foot"><button type="button" className="ghost small ux-collapse" onClick={toggleSidebar} aria-expanded={sidebarMode !== 'icons'}>{sidebarMode === 'icons' ? '»' : '« 畳む'}</button></div>
    </aside>
  )
}

function HomeIntro() {
  const { data: d } = useAsync(api.dashboard)
  const { data: rep } = useAsync(api.report)
  const { data: plans } = useAsync(api.plans)
  const cards: { to: string; t: string; v: string; s: string; cta: string }[] = [
    { to: '/report', t: '総合研究レポート', v: rep ? `${rep.length} 章` : '…', s: rep ? `うち編集済み ${rep.filter((r) => r.user_modified).length} 章` : '', cta: '開く' },
    { to: '/plan', t: '研究計画', v: plans ? `${plans.length} 件` : '…', s: d ? `テーマ候補 ${d.counts.themes} 件から作成` : '', cta: '計画を書く' },
    { to: '/data', t: '解析データセット', v: d ? `${d.counts.datasets} 件` : '…', s: 'CSV / Excel を取り込んで解析', cta: 'データを追加' },
    { to: '/simulator', t: '空気清浄の試算', v: '即時計算', s: '風量・部屋の大きさから CADR・濃度を計算', cta: '試算する' },
  ]
  return (
    <section className="ux-outcomes" aria-labelledby="ux-out-h">
      <div className="ux-out-head"><h2 id="ux-out-h">成果物</h2><span className="muted small">つくる・更新するものから始めます</span></div>
      <div className="ux-outgrid">
        {cards.map((c) => (
          <Link key={c.to} to={c.to} className="ux-outcard">
            <span className="ux-out-t">{c.t}</span><span className="ux-out-v">{c.v}</span><span className="ux-out-s">{c.s}</span><span className="ux-out-cta">{c.cta} →</span>
          </Link>
        ))}
      </div>
    </section>
  )
}

function Bottom(p: SlotProps) { return <BottomNav tabs={commercial.mobileTabs} openMore={p.openMore} pathname={p.st.pathname} /> }

export const commercial: LayoutSpec = {
  id: 'commercial',
  name: 'Commercial',
  title: '商用向け Outcome Hub',
  audience: '成果物（レポート・計画）を早く仕上げたい利用者',
  summary: '「何をつくるか」から始めるレイアウト。成果物カードを先頭に置き、作成・資料の機能を左レールにまとめる。',
  traits: ['ホームは成果物カード（レポート・計画・データ・試算）', '左レール 208px＋上部の主操作ボタン', '中密度・広い余白・角丸大きめ'],
  basis: 'design-research/C-commercial（案C アウトカム・ハブ 4.37点）',
  mobileTabs: ['/', '/data', '/report', '/settings'],
  defaults: { density: 'standard', card: 'shadow', radius: 'round', sidebarMode: 'expanded', sidebarPos: 'left' },
  palette: true,
  mini: { top: 'bar', side: 'wide', aside: false, bottom: 'none', tabs: 5 },
  slots: { Top, Side, HomeIntro, Bottom, More: ({ onClose }) => <MoreSheetGrouped onClose={onClose} /> },
}
