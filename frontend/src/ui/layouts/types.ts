import type { ComponentType } from 'react'
import type { HomeSection } from '../../app/homeSections'
import type { ShellState } from '../../app/useShellState'
import type { CardStyle, Density, LayoutId, Radius } from '../prefs'

/** 各スロット部品に渡す共通の値。レイアウト部品は業務データを持たず、ここと core/api.ts の読み取りだけを使う */
export interface SlotProps {
  st: ShellState
  openMore: () => void
  openPalette: () => void
  sidebarMode: 'expanded' | 'icons'
  toggleSidebar: () => void
}

/**
 * 画面の骨格のスロット。LayoutFrame はこの順番で描き、main（ページ本体）の位置は全レイアウトで同じにする。
 * そのため、レイアウトを切り替えてもページの部品は作り直されず、入力中の内容が残る。
 */
export interface LayoutSlots {
  Top?: ComponentType<SlotProps>
  Side?: ComponentType<SlotProps>
  /** ホーム（/）だけでページの上に出す導入部（レイアウトごとの情報の優先順位） */
  HomeIntro?: ComponentType<SlotProps>
  Aside?: ComponentType<SlotProps>
  Bottom?: ComponentType<SlotProps>
  More?: ComponentType<{ onClose: () => void }>
}

export interface LayoutSpec {
  id: LayoutId
  /** 英語の短い名前（カード・プレビューの見出し） */
  name: string
  /** 日本語の名前 */
  title: string
  audience: string
  summary: string
  traits: string[]
  /** 根拠にした研究成果（claude/sharp-hopper-ylg33o の design-research/） */
  basis: string
  /** スマホの下部タブに出す項目（残りは「その他」に入る） */
  mobileTabs: string[]
  /**
   * ホーム（研究ダッシュボード）のブロックの並び順（情報の優先順位）。pages/Dashboard.tsx がこの順に DOM を並べる。
   * CSS の order は使わない（Tab 順・読み上げ順が見た目と食い違うため）。Original は改修前の DOM 順（HOME_SECTIONS）のまま
   */
  homeOrder: HomeSection[]
  /** 利用者が「自動」を選んだときの値 */
  defaults: { density: Exclude<Density, 'auto'>; card: Exclude<CardStyle, 'auto'>; radius: Exclude<Radius, 'auto'>; sidebarMode: 'expanded' | 'icons'; sidebarPos: 'left' | 'right' }
  /** コマンドパレット（Ctrl+K）を有効にするか */
  palette: boolean
  /** 設定画面の縮小図（プレビュー）の構成 */
  mini: { top: 'none' | 'bar' | 'band' | 'scope'; side: 'wide' | 'rail' | 'list'; aside: boolean; bottom: 'none' | 'jobs' }
  slots: LayoutSlots
}
