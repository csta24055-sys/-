// シェル（画面の枠）が使う共通の状態。以前は main.tsx の Shell の中にあったものを、レイアウトに依存しない形で切り出した。
import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { useBackupReminder } from '../pages/Settings'

export interface ShellState {
  online: boolean
  update: ServiceWorker | null
  needBackup: '' | 'never' | 'old'
  pathname: string
}

export function useShellState(): ShellState {
  const [online, setOnline] = useState(navigator.onLine)
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
  return { online, update, needBackup, pathname: loc.pathname }
}

export function applyUpdate(update: ServiceWorker) {
  ;(window as any).__aqrosUpdating = true
  update.postMessage('skipWaiting')
}
