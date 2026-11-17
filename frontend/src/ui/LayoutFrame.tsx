// 全レイアウト共通の枠。
// 子要素の並び（Skip, Top, Side, main, Aside, Bottom, More, Palette）を常に同じ位置に置き、使わないスロットは null にする。
// React は同じ位置・同じ種類の要素を作り直さないため、レイアウトを切り替えても <main> 以下のページは
// マウントされたまま残り、入力中の内容・スクロール以外の作業状態・URL が保たれる。
import { useCallback, useEffect, useState } from 'react'
import AppRoutes from '../app/AppRoutes'
import { useShellState } from '../app/useShellState'
import { Announcer, Banners, CommandPalette, PreviewBar, SkipLink, usePaletteShortcut } from './parts'
import { useUi } from './UiPrefsContext'

export default function LayoutFrame() {
  const ui = useUi()
  const st = useShellState()
  const { spec, resolved } = ui
  const S = spec.slots
  const original = spec.id === 'original'
  const [more, setMore] = useState(false)
  const [palette, setPalette] = useState(false)
  const openMore = useCallback(() => setMore(true), [])
  const openPalette = useCallback(() => setPalette(true), [])
  usePaletteShortcut(spec.palette, openPalette)
  useEffect(() => { setMore(false); setPalette(false) }, [st.pathname, spec.id])

  const sideMode = resolved.sidebarMode === 'icons' ? 'icons' : 'expanded'
  const { setCustomNow } = ui
  // そのレイアウトの既定の表示に戻るときは「自動」を保存する（明示値を残すと、ほかのレイアウトへ切り替えたときにも付いて回る）
  const toggleSidebar = useCallback(() => {
    const next = sideMode === 'icons' ? 'expanded' : 'icons'
    setCustomNow({ sidebarMode: next === spec.defaults.sidebarMode ? 'auto' : next })
  }, [setCustomNow, sideMode, spec])
  const props = { st, openMore, openPalette, sidebarMode: sideMode, toggleSidebar } as const
  const showSide = resolved.sidebarMode !== 'hidden'
  // Original で既定（左・展開）のままなら属性を付けない（改修前と同じ DOM）。「アイコンのみ」は左でも属性が要る
  const sidebarAttr = original && resolved.sidebarMode === 'expanded' && resolved.sidebarPos === 'left' ? undefined : resolved.sidebarMode === 'hidden' ? 'hidden' : `${resolved.sidebarPos}-${sideMode}`

  return (
    <div className={original ? 'shell' : `shell ux-shell ux-${spec.id}`} data-sidebar={sidebarAttr}>
      {/* 読み上げ用の領域は本文より前に置く（ページ内の role=status より後ろにならないように） */}
      <Announcer />
      {!original ? <SkipLink /> : null}
      {S.Top ? <S.Top {...props} /> : null}
      {S.Side && showSide ? <S.Side {...props} /> : null}
      <main className="main" id={original ? undefined : 'main'} tabIndex={original ? undefined : -1}>
        <PreviewBar />
        <Banners st={st} />
        {S.HomeIntro && st.pathname === '/' ? <S.HomeIntro {...props} /> : null}
        <AppRoutes />
      </main>
      {S.Aside ? <S.Aside {...props} /> : null}
      {S.Bottom ? <S.Bottom {...props} /> : null}
      {more && S.More ? <S.More onClose={() => setMore(false)} /> : null}
      {palette ? <CommandPalette onClose={() => setPalette(false)} /> : null}
    </div>
  )
}
