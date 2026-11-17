// ホーム（研究ダッシュボード）を構成するブロックの名前と、既定の並び順。
// 既定の順は改修前の DOM の順（＝ Original）。レイアウトは LayoutSpec.homeOrder でこの順だけを入れ替える。
// 並べ替えは CSS の order ではなく DOM の順で行う（Tab 順・読み上げ順を見た目と同じにするため）。

export const HOME_SECTIONS = ['stats', 'charts', 'timeline', 'findings', 'completeness', 'activity'] as const
export type HomeSection = (typeof HOME_SECTIONS)[number]

/**
 * レイアウトの指定を、全ブロックをちょうど 1 回ずつ含む並びに整える。
 * 未知の名前と重複は捨て、指定にないブロックは既定の順で後ろに足す（ブロックが画面から消えないようにする）。
 */
export function resolveHomeOrder(order?: readonly string[]): HomeSection[] {
  const out: HomeSection[] = []
  for (const k of order || []) if ((HOME_SECTIONS as readonly string[]).includes(k) && !out.includes(k as HomeSection)) out.push(k as HomeSection)
  for (const k of HOME_SECTIONS) if (!out.includes(k)) out.push(k)
  return out
}
