// Research: 研究室向け Pipeline Ledger（design-research/A-research-lab）
// 骨格: 上部ヘッダー（パンくず・コマンド）／左「段のリスト」／中央 作業領域／右「根拠パネル」／下「ジョブモニター」
// 研究の流れ（資料 → 解析 → 計算 → 知見 → 計画 → レポート）を番号付きの段として並べ、全段に件数と根拠を付ける。
import { useEffect, useState } from 'react'
import { Link, NavLink } from 'react-router-dom'
import { currentNav, NAV } from '../../app/navigation'
import { api } from '../../core/api'
import { listJobs } from '../../core/cloud'
import { useAsync } from '../../components/ui'
import { BottomNav, EvidencePanel, MoreSheetGrouped, NavIcon, storeLabel } from '../parts'
import type { LayoutSpec, SlotProps } from './types'

const STAGES = NAV.filter((n) => n.stage !== null).sort((a, b) => (a.stage! - b.stage!))
const OPS = NAV.filter((n) => n.stage === null && n.to !== '/')
const STAGE_NAME: Record<number, string> = { 1: '資料収集', 2: 'データ解析', 3: 'モデル計算', 4: '知見統合', 5: '研究計画', 6: 'レポート' }

function Top({ st, openPalette, openMore }: SlotProps) {
  const cur = currentNav(st.pathname)
  return (
    <header className="ux-top">
      <div className="ux-brand"><b>AQROS Pipeline Ledger</b><span className="ux-tag">研究室向け</span></div>
      <nav className="ux-crumb" aria-label="現在地">
        <span>井口研究室</span><span aria-hidden>/</span><span>空気清浄度研究</span><span aria-hidden>/</span>
        <b aria-current="page">{cur.stage ? `段${cur.stage} ${STAGE_NAME[cur.stage]} — ` : ''}{cur.label}</b>
      </nav>
      <div className="ux-top-actions">
        <button type="button" className="ghost ux-cmd" onClick={openPalette} aria-label="すべての機能（Ctrl+K）">コマンド <kbd>Ctrl</kbd>+<kbd>K</kbd></button>
        <button type="button" className="ghost ux-menu-btn" onClick={openMore} aria-label="すべての機能">☰</button>
      </div>
    </header>
  )
}

function Side({ sidebarMode, toggleSidebar }: SlotProps) {
  const icons = sidebarMode === 'icons'
  return (
    <aside className="ux-side" aria-label="段のリスト">
      <nav aria-label="パイプライン">
        <NavLink to="/" end className="ux-navlink" title="ダッシュボード"><NavIcon item={NAV[0]} /><span className="ux-lbl">ダッシュボード</span></NavLink>
        <h2 className="ux-side-h"><span className="ux-lbl">パイプライン（段）</span></h2>
        <ol className="ux-stages">
          {STAGES.map((n) => (
            <li key={n.to}><NavLink to={n.to} className="ux-navlink" title={n.label}>
              <span className="ux-stage-no" aria-hidden>{n.stage}</span>
              <span className="ux-lbl"><b>{STAGE_NAME[n.stage!]}</b><small>{n.label}</small></span>
            </NavLink></li>
          ))}
        </ol>
        <h2 className="ux-side-h"><span className="ux-lbl">運用</span></h2>
        {OPS.map((n) => <NavLink key={n.to} to={n.to} className="ux-navlink" title={n.label}><NavIcon item={n} /><span className="ux-lbl">{n.label}</span></NavLink>)}
      </nav>
      <div className="ux-side-foot">
        <span className="ux-lbl small">保存先: {storeLabel}</span>
        <button type="button" className="ghost small ux-collapse" onClick={toggleSidebar} aria-expanded={!icons}>{icons ? '»' : '« 段のリストを畳む'}</button>
      </div>
    </aside>
  )
}

function HomeIntro() {
  const { data: d } = useAsync(api.dashboard)
  const { data: rep } = useAsync(api.report)
  const c = d?.counts
  const value: Record<string, string> = c ? {
    '/library': `読了 ${c.read}/${c.sources}`, '/data': `データセット ${c.datasets}`, '/simulator': 'モデル計算',
    '/graph': `知見 ${c.findings}`, '/plan': `テーマ候補 ${c.themes}`, '/report': rep ? `${rep.length} 章` : '—',
  } : {}
  return (
    <section className="ux-pipeline card" aria-label="パイプラインの状態">
      <header className="card-h"><h2>パイプラインの状態 <span className="muted small">空気清浄度研究 / 資料台帳と端末内データから集計</span></h2></header>
      <ol className="ux-pipe">
        {STAGES.map((n) => (
          <li key={n.to}><Link to={n.to}><span className="ux-stage-no" aria-hidden>{n.stage}</span><b>{STAGE_NAME[n.stage!]}</b><small>{value[n.to] || '…'}</small></Link></li>
        ))}
      </ol>
    </section>
  )
}

function Aside({ st }: SlotProps) { return <EvidencePanel st={st} title="根拠パネル" /> }

function JobBar({ st }: { st: SlotProps['st'] }) {
  const [jobs, setJobs] = useState<{ total: number; running: number; failed: number } | null>(null)
  useEffect(() => { listJobs().then((j) => setJobs({ total: j.length, running: j.filter((x) => ['submitted', 'queued', 'in_progress'].includes(x.status)).length, failed: j.filter((x) => x.status === 'failed').length })).catch(() => undefined) }, [st.pathname])
  return (
    <footer className="ux-jobbar" aria-label="ジョブモニター">
      <b>ジョブモニター</b>
      <span>{st.online ? '● オンライン' : '○ オフライン'}</span>
      <span>保存先: {storeLabel}</span>
      <span>クラウドジョブ {jobs ? `${jobs.total} 件 / 実行中 ${jobs.running} / 失敗 ${jobs.failed}` : '—'}</span>
      <Link to="/cloud">クラウド解析を開く</Link>
    </footer>
  )
}

function Bottom(p: SlotProps) {
  return <><JobBar st={p.st} /><BottomNav tabs={research.mobileTabs} openMore={p.openMore} pathname={p.st.pathname} /></>
}

export const research: LayoutSpec = {
  id: 'research',
  name: 'Research',
  title: '研究室向け Pipeline Ledger',
  audience: '大学院生・教員・学部生（研究室内部）',
  summary: '研究の流れを番号付きの「段」で並べ、各段に件数・保存先・版などの根拠を常に表示する高密度レイアウト。',
  traits: ['左: 段のリスト（資料→解析→計算→知見→計画→レポート）', '右: 根拠パネル／下: ジョブモニター', '高密度（本文 13px）・Ctrl+K で全機能'],
  basis: 'design-research/A-research-lab（案C Pipeline Ledger 4.30点）',
  mobileTabs: ['/', '/data', '/cloud'],
  defaults: { density: 'compact', card: 'outline', radius: 'sharp', sidebarMode: 'expanded', sidebarPos: 'left' },
  palette: true,
  mini: { top: 'bar', side: 'list', aside: true, bottom: 'jobs', tabs: 4 },
  slots: { Top, Side, HomeIntro, Aside, Bottom, More: ({ onClose }) => <MoreSheetGrouped onClose={onClose} /> },
}
