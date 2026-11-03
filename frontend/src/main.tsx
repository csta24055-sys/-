import React, { useEffect, useState } from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, NavLink, Route, Routes } from 'react-router-dom'
import './styles.css'
import Dashboard from './pages/Dashboard'
import Library from './pages/Library'
import DataAnalysis from './pages/DataAnalysis'
import Simulator from './pages/Simulator'
import KnowledgeGraph from './pages/KnowledgeGraph'
import ResearchPlan from './pages/ResearchPlan'
import Report from './pages/Report'
import Learning from './pages/Learning'

const NAV = [
  ['/', '研究ダッシュボード', 'ホーム', '◎'],
  ['/library', '研究資料ライブラリ', '資料', '▤'],
  ['/data', '実験データ解析', '解析', '∿'],
  ['/simulator', '空気清浄シミュレーター', 'シミュ', '⚙'],
  ['/graph', '研究ナレッジグラフ', 'グラフ', '⋔'],
  ['/plan', '今後の研究計画', '計画', '➚'],
  ['/report', '総合研究レポート', 'レポート', '¶'],
  ['/learn', '研究学習モード', '学習', '✎'],
] as const

function App() {
  const [online, setOnline] = useState(navigator.onLine)
  useEffect(() => {
    const on = () => setOnline(true), off = () => setOnline(false)
    window.addEventListener('online', on); window.addEventListener('offline', off)
    return () => { window.removeEventListener('online', on); window.removeEventListener('offline', off) }
  }, [])
  return (
    <BrowserRouter>
      <div className="shell">
        <aside className="side">
          <div className="brand"><img src="/icon.svg" alt="" /><div><b>Air Quality</b><span>Research OS</span></div></div>
          <nav>{NAV.map(([to, label, , icon]) => <NavLink key={to} to={to} end={to === '/'}><i aria-hidden>{icon}</i>{label}</NavLink>)}</nav>
          <div className="side-foot">日本大学 理工学部 井口研究室<br />空気清浄度研究アーカイブ</div>
        </aside>
        <main className="main">
          {!online && <div className="offline">オフライン表示中 — 最後に取得したデータを表示しています。編集・アップロードは接続後に行ってください。</div>}
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
          </Routes>
        </main>
        <nav className="tabbar">{NAV.map(([to, , short, icon]) => <NavLink key={to} to={to} end={to === '/'}><i aria-hidden>{icon}</i><span>{short}</span></NavLink>)}</nav>
      </div>
    </BrowserRouter>
  )
}

ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><App /></React.StrictMode>)

if ('serviceWorker' in navigator && import.meta.env.PROD) {
  window.addEventListener('load', () => navigator.serviceWorker.register('/sw.js').catch(() => undefined))
}
