import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import './styles.css'
import './ui/layouts.css'
import { STANDALONE } from './core/api'
import { requestPersist } from './core/idb'
import LayoutFrame from './ui/LayoutFrame'
import { UiPrefsProvider } from './ui/UiPrefsContext'

const BASE = import.meta.env.BASE_URL || '/'

// 画面の枠（5種類のレイアウト）は ui/、ナビゲーション・ルーティング・シェル状態は app/、
// データ・計算・保存は core/ と pages/ に分かれている。レイアウトの切替は ui/ の中だけで完結する。
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode><UiPrefsProvider><BrowserRouter basename={BASE.replace(/\/$/, '') || '/'}><LayoutFrame /></BrowserRouter></UiPrefsProvider></React.StrictMode>,
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
