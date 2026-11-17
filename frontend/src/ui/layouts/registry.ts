// レイアウトの登録表。6種類目以降を追加する手順（docs/UI_LAYOUTS.md にも記載）:
//   1. src/ui/prefs.ts の LAYOUT_IDS に ID を追加
//   2. src/ui/layouts/<id>.tsx に LayoutSpec を作る（スロット部品とメタ情報。ホームの並び順 homeOrder を含む）
//   3. 下の LAYOUTS に追加
//   4. src/ui/layouts.css に :root[data-ui="<id>"] のトークンと骨格の CSS を追加
//   5. public/ui-init.js（起動時に配色を先付けする）の ID の一覧に追加（prefs.test.ts が一致を確かめる）
// ページ・計算・保存処理には手を入れない。
import type { LayoutId } from '../prefs'
import { commercial } from './commercial'
import { enterprise } from './enterprise'
import { original } from './original'
import { pub } from './public'
import { research } from './research'
import type { LayoutSpec } from './types'

export const LAYOUTS: LayoutSpec[] = [original, research, pub, commercial, enterprise]

export function getLayout(id: LayoutId | string): LayoutSpec {
  return LAYOUTS.find((l) => l.id === id) || original
}
