// 全レイアウトで共有するナビゲーション定義（単一の情報源）。
// レイアウトは「どの順で・どうまとめて見せるか」だけを決め、項目そのもの（行き先・名前）はここから読む。
// 項目を増やすときはここに 1 行足すだけで、5 種類すべてのレイアウトのメニュー・コマンドパレット・その他メニューに出る。

export interface NavItem {
  /** ルートのパス（URL）。レイアウトを切り替えても変わらない */
  to: string
  /** 正式名（デスクトップのメニュー・見出し） */
  label: string
  /** 短い名前（スマホの下部タブ） */
  short: string
  /** 記号アイコン（装飾。aria-hidden で読み上げない） */
  icon: string
  /** Pipeline Ledger（Research）での段の番号。段に属さない管理系は null */
  stage: number | null
  /** 分類（Commercial / Enterprise のメニューのまとまり） */
  group: 'home' | 'outcome' | 'create' | 'source' | 'admin'
  /** やさしい説明（Public の第1層・コマンドパレットの補足） */
  plain: string
}

export const NAV: NavItem[] = [
  { to: '/', label: '研究ダッシュボード', short: 'ホーム', icon: '◎', stage: null, group: 'home', plain: '研究全体の状況と主な成果' },
  { to: '/library', label: '研究資料ライブラリ', short: '資料', icon: '▤', stage: 1, group: 'source', plain: '論文・報告書・原データの台帳を探す' },
  { to: '/data', label: '実験データ解析', short: '解析', icon: '∿', stage: 2, group: 'create', plain: '測定データを取り込んで品質と統計を確認する' },
  { to: '/simulator', label: '空気清浄シミュレーター', short: 'シミュ', icon: '⚙', stage: 3, group: 'create', plain: '空気清浄機・換気の効果を試算する' },
  { to: '/graph', label: '研究ナレッジグラフ', short: 'グラフ', icon: '⋔', stage: 4, group: 'source', plain: '知見・仮説・資料のつながりを見る' },
  { to: '/plan', label: '今後の研究計画', short: '計画', icon: '➚', stage: 5, group: 'outcome', plain: '研究テーマ候補を比べて計画を書く' },
  { to: '/report', label: '総合研究レポート', short: 'レポート', icon: '¶', stage: 6, group: 'outcome', plain: '研究のまとめを読む・編集する・書き出す' },
  { to: '/learn', label: '研究学習モード', short: '学習', icon: '✎', stage: null, group: 'admin', plain: '新しい学生向けの学習課題' },
  { to: '/cloud', label: 'クラウド解析', short: 'クラウド', icon: '☁', stage: null, group: 'admin', plain: '重い計算・Word/PDF 生成・OCR を GitHub Actions で実行する' },
  { to: '/settings', label: '設定・バックアップ', short: '設定', icon: '⚑', stage: null, group: 'admin', plain: 'デザインの切替・保存状況・バックアップ' },
]

export const navByPath = (to: string) => NAV.find((n) => n.to === to)

/** 現在の URL に対応する項目（/library/:id は資料ライブラリ）。未知のパスはダッシュボード（ルートの * と同じ扱い） */
export function currentNav(pathname: string): NavItem {
  const exact = NAV.find((n) => n.to === pathname)
  if (exact) return exact
  const prefix = NAV.filter((n) => n.to !== '/' && pathname.startsWith(n.to + '/'))[0]
  return prefix || NAV[0]
}

export const GROUP_LABEL: Record<NavItem['group'], string> = {
  home: 'ホーム', outcome: '成果物', create: '作成・計算', source: '資料・知識', admin: '学習・運用・設定',
}
