// Public: 公共向け 段階的開示 3層レイヤー（design-research/B-public）
// 骨格: 識別帯／ヘッダー（文字サイズ切替）／上部の主要5項目ナビ／左「画面」一覧と「データの状態」
// ホームは 第1層 結論 → 第2層 比較 → 第3層 根拠 の順に並べ替え、やさしい言葉の「よく使われる手続き」から始める。
// 注意: 公共機関の公式サービスではないことを識別帯で常に明示する（存在しない公開機能・注意報は作らない）。
import { Link, NavLink } from 'react-router-dom'
import { NAV, navByPath } from '../../app/navigation'
import { api } from '../../core/api'
import { useAsync } from '../../components/ui'
import { useUi } from '../UiPrefsContext'
import { BottomNav, MoreSheetGrouped, NavIcon, storeLabel } from '../parts'
import type { LayoutSpec, SlotProps } from './types'

const PRIMARY = ['/', '/library', '/simulator', '/report', '/settings']
const SIZES: [number, string, string][] = [[1, 'A', '標準'], [1.15, 'A', '大'], [1.3, 'A', '特大']]

function TextSize() {
  const ui = useUi()
  const cur = ui.effective.custom.fontScale
  return (
    <div className="ux-seg" role="group" aria-label="文字の大きさ">
      <span className="ux-seg-l" aria-hidden>文字</span>
      {SIZES.map(([s, a, l], i) => (
        <button key={s} type="button" aria-pressed={Math.abs(cur - s) < 0.01} onClick={() => ui.setCustomNow({ fontScale: s })} title={`文字の大きさ: ${l}`}>
          <span style={{ fontSize: `${0.85 + i * 0.18}em` }} aria-hidden>{a}</span><span className="ux-sr">{l}</span>
        </button>
      ))}
    </div>
  )
}

function Top({ openMore }: SlotProps) {
  return (
    <header className="ux-top">
      <div className="ux-idband">日本大学 理工学部 井口研究室の研究用アプリです。国・自治体の公式情報ではありません。数値は研究資料に基づき、出典を併記しています。</div>
      <div className="ux-head">
        <div className="ux-brand"><b>空気清浄度研究アーカイブ</b><span className="ux-tag">研究室公開版の試作</span></div>
        <div className="ux-top-actions">
          <TextSize />
          <button type="button" className="ghost ux-allbtn" onClick={openMore} aria-haspopup="dialog">すべての機能</button>
        </div>
      </div>
      <nav className="ux-topnav" aria-label="主要メニュー">
        {PRIMARY.map((p) => { const n = navByPath(p)!; return <NavLink key={p} to={p} end={p === '/'}>{n.to === '/' ? 'ホーム（全体の概要）' : n.label}</NavLink> })}
      </nav>
    </header>
  )
}

function Side({ st }: SlotProps) {
  const { data: k } = useAsync(api.knowledge)
  return (
    <aside className="ux-side" aria-label="画面の一覧">
      <h2 className="ux-side-h">画面</h2>
      <nav aria-label="すべての画面">
        {NAV.map((n) => <NavLink key={n.to} to={n.to} end={n.to === '/'} className="ux-navlink"><NavIcon item={n} /><span className="ux-lbl">{n.label}</span></NavLink>)}
      </nav>
      <div className="ux-statebox">
        <h2>データの状態</h2>
        <dl>
          <dt>資料取得日</dt><dd>{k?.meta?.accessed || '—'}</dd>
          <dt>保存先</dt><dd>{storeLabel}</dd>
          <dt>接続</dt><dd>{st.online ? 'オンライン' : 'オフライン'}</dd>
          <dt>算出方法</dt><dd><Link to="/report">総合研究レポート</Link></dd>
        </dl>
      </div>
    </aside>
  )
}

const TASKS: [string, string, string][] = [
  ['#sec-findings', '研究でわかったことを知る', '主な成果と、まだ解けていない問題'],
  ['/library', '資料を探す', '論文・報告書・測定記録の一覧'],
  ['/simulator', '空気清浄の効果を試算する', '部屋の広さ・機器の風量から計算'],
  ['/report', '報告書を読む', '研究全体のまとめ（印刷・保存できます）'],
]

function HomeIntro() {
  return (
    <section className="ux-public-intro" aria-labelledby="ux-tasks-h">
      <h2 id="ux-tasks-h">よく使われる手続き</h2>
      <ol className="ux-tasks">
        {TASKS.map(([to, t, s], i) => (
          <li key={to}>{to.startsWith('#')
            ? <a href={to}><span className="ux-task-no">{i + 1}</span><b>{t}</b><small>{s}</small></a>
            : <Link to={to}><span className="ux-task-no">{i + 1}</span><b>{t}</b><small>{s}</small></Link>}</li>
        ))}
      </ol>
      <nav className="ux-layers" aria-label="この画面の層">
        <span>この画面の層:</span>
        <a href="#sec-findings">第1層 結論</a><span aria-hidden>→</span>
        <a href="#sec-stats">第2層 比較</a><span aria-hidden>→</span>
        <a href="#sec-completeness">第3層 根拠</a>
      </nav>
    </section>
  )
}

function Bottom(p: SlotProps) { return <BottomNav tabs={pub.mobileTabs} openMore={p.openMore} pathname={p.st.pathname} /> }

export const pub: LayoutSpec = {
  id: 'public',
  name: 'Public',
  title: '公共向け 3層レイヤー',
  audience: '一般の方から専門家まで（研究成果の公開を想定）',
  summary: '結論 → 比較 → 根拠 の順に深く読めるように並べ、文字を大きく、操作対象を広く（48px）したレイアウト。',
  traits: ['識別帯で「公式情報ではない」ことを明示', '上部の主要5項目＋文字サイズ切替（標準/大/特大）', 'ホームは第1層 結論から表示'],
  basis: 'design-research/B-public（案C 段階的開示3層レイヤー型 4.42点）',
  mobileTabs: ['/', '/library', '/report'],
  defaults: { density: 'comfortable', card: 'outline', radius: 'standard', sidebarMode: 'expanded', sidebarPos: 'left' },
  palette: false,
  mini: { top: 'band', side: 'list', aside: false, bottom: 'none', tabs: 4 },
  slots: { Top, Side, HomeIntro, Bottom, More: ({ onClose }) => <MoreSheetGrouped onClose={onClose} /> },
}
