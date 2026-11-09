import React, { useEffect, useState } from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Link, NavLink, Route, Routes, useLocation } from 'react-router-dom'
import './styles.css'
import Dashboard from './pages/Dashboard'
import Library from './pages/Library'
import DataAnalysis from './pages/DataAnalysis'
import Simulator from './pages/Simulator'
import KnowledgeGraph from './pages/KnowledgeGraph'
import ResearchPlan from './pages/ResearchPlan'
import Report from './pages/Report'
import Learning from './pages/Learning'
import Cloud from './pages/Cloud'
import Settings, { useBackupReminder } from './pages/Settings'
import { STANDALONE } from './core/api'
import { requestPersist } from './core/idb'

const BASE = import.meta.env.BASE_URL || '/'
const NAV = [
  ['/', '研究ダッシュボード', 'ホーム', '◎'],
  ['/library', '研究資料ライブラリ', '資料', '▤'],
  ['/data', '実験データ解析', '解析', '∿'],
  ['/simulator', '空気清浄シミュレーター', 'シミュ', '⚙'],
  ['/graph', '研究ナレッジグラフ', 'グラフ', '⋔'],
  ['/plan', '今後の研究計画', '計画', '➚'],
  ['/report', '総合研究レポート', 'レポート', '¶'],
  ['/learn', '研究学習モード', '学習', '✎'],
  ['/cloud', 'クラウド解析', 'クラウド', '☁'],
  ['/settings', '設定・バックアップ', '設定', '⚑'],
] as const
const TAB_MAIN = ['/', '/library', '/data', '/simulator']

function MoreSheet({ onClose }: { onClose: () => void }) {
  return (
    <div className="sheet-bg" onClick={onClose}>
      <nav className="sheet" aria-label="その他のメニュー" onClick={(e) => e.stopPropagation()}>
        {NAV.filter(([to]) => !TAB_MAIN.includes(to)).map(([to, label, , icon]) => <Link key={to} to={to} onClick={onClose}><i aria-hidden>{icon}</i>{label}</Link>)}
        <button className="ghost" onClick={onClose}>閉じる</button>
      </nav>
    </div>
  )
}

function Shell() {
  const [online, setOnline] = useState(navigator.onLine)
  const [more, setMore] = useState(false)
  const [update, setUpdate] = useState<ServiceWorker | null>(null)
  const loc = useLocation()
  const needBackup = useBackupReminder()
  useEffect(() => {
    const on = () => setOnline(true), off = () => setOnline(false)
    window.addEventListener('online', on); window.addEventListener('offline', off)
    const upd = (e: Event) => setUpdate((e as CustomEvent<ServiceWorker>).detail)
    window.addEventListener('aqros-update', upd)
    return () => { window.removeEventListener('online', on); window.removeEventListener('offline', off); window.removeEventListener('aqros-update', upd) }
  }, [])
  useEffect(() => { window.scrollTo(0, 0) }, [loc.pathname])
  const moreActive = !TAB_MAIN.includes(loc.pathname) && !loc.pathname.startsWith('/library')
  return (
    <div className="shell">
      <aside className="side">
        <div className="brand"><img src={BASE + 'icon.svg'} alt="" /><div><b>Air Quality</b><span>Research OS</span></div></div>
        <nav>{NAV.map(([to, label, , icon]) => <NavLink key={to} to={to} end={to === '/'}><i aria-hidden>{icon}</i>{label}</NavLink>)}</nav>
        <div className="side-foot">日本大学 理工学部 井口研究室<br />空気清浄度研究アーカイブ</div>
      </aside>
      <main className="main">
        {update && <div className="note update" role="status">新しい版があります。<button className="small" onClick={() => { (window as any).__aqrosUpdating = true; update.postMessage('skipWaiting') }}>更新する</button> <span className="small muted">端末内のデータはそのまま残ります。</span></div>}
        {!online && <div className="offline">{STANDALONE ? 'オフラインです — 端末内のデータで動作しています（クラウド解析は接続後に利用できます）。' : 'オフライン表示中 — 最後に取得したデータを表示しています。編集・アップロードは接続後に行ってください。'}</div>}
        {needBackup && loc.pathname !== '/settings' && <div className="note">{needBackup === 'never' ? '端末内に保存したデータのバックアップがまだありません。' : '最後のバックアップから7日以上たっています。'}<Link to="/settings">設定・バックアップ</Link>から書き出してください。</div>}
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/library" element={<Library />} />
          <Route path="/library/:id" element={<Library />} />
          <Route path="/data" element={<DataAnalysis />} />
          <Route path="/simulator" element={<Simulator />} />
          <Route path="/graph" element={<KnowledgeGraph />} />
          <Route path="/plan" element={<ResearchPlan />} />
          <Route path="/report" element={<Report />} />
          <Route path="/learn" element={<Learning />} />
          <Route path="/cloud" element={<Cloud />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="*" element={<Dashboard />} />
        </Routes>
      </main>
      <nav className="tabbar" aria-label="メインメニュー">
        {NAV.filter(([to]) => TAB_MAIN.includes(to)).map(([to, , short, icon]) => <NavLink key={to} to={to} end={to === '/'}><i aria-hidden>{icon}</i><span>{short}</span></NavLink>)}
        <a href="#more" className={moreActive ? 'active' : ''} onClick={(e) => { e.preventDefault(); setMore(true) }}><i aria-hidden>☰</i><span>その他</span></a>
      </nav>
      {more && <MoreSheet onClose={() => setMore(false)} />}
    </div>
  )
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode><BrowserRouter basename={BASE.replace(/\/$/, '') || '/'}><Shell /></BrowserRouter></React.StrictMode>,
)

if ('serviceWorker' in navigator && import.meta.env.PROD) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register(BASE + 'sw.js', { scope: BASE }).then((reg) => {
      const notify = (w: ServiceWorker | null) => { if (w && navigator.serviceWorker.controller) window.dispatchEvent(new CustomEvent('aqros-update', { detail: w })) }
      notify(reg.waiting)
      reg.addEventListener('updatefound', () => { const w = reg.installing; w?.addEventListener('statechange', () => { if (w.state === 'installed') notify(w) }) })
      // 利用者が「更新する」を押したときだけ再読み込みする（初回の制御開始では再読み込みしない＝入力中の内容を失わない）
      let reloaded = false
      navigator.serviceWorker.addEventListener('controllerchange', () => { if ((window as any).__aqrosUpdating && !reloaded) { reloaded = true; location.reload() } })
      setInterval(() => reg.update().catch(() => undefined), 60 * 60 * 1000)
    }).catch(() => undefined)
  })
}
if (STANDALONE) requestPersist()
