import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../core/api'
import { Bar, Card, SourceRef } from '../components/ui'

/** 2027年度の新しい学生向けの学習モード（研究継承総合資料 第9章と同じ順序） */
type Step = { n: number; title: string; goal: string; read: string[]; app?: [string, string][]; check: string }
const STEPS: Step[] = [
  { n: 1, title: '研究室の全体像', goal: '2018〜2026年度の研究の流れと、各年度の問いを説明できる', read: ['研究継承資料 第1章'], app: [['/', 'ダッシュボード'], ['/graph', 'ナレッジグラフ']], check: '2018年度の問い（空調室EPで住宅全体を除塵できるか）と2025年度の問いの違いを1文で書けるか' },
  { n: 2, title: '室内空気環境の基礎', goal: '単室の物質収支とI/O比の式を導ける', read: ['研究継承資料 2.1', 'Nazaroff (2004) Indoor particle dynamics'], app: [['/simulator', 'シミュレーター（単室）']], check: '換気回数を2倍にするとI/O比はどう変わるか、式で説明できるか' },
  { n: 3, title: '粒子・エアロゾルの基礎', goal: '粒径と沈着・個数と質量の関係を理解する', read: ['研究継承資料 2.2・2.6'], app: [['/library/S-REF-11', '粒径別個数濃度の文献']], check: '10 μmと1 μmで沈降速度は何倍違うか（Stokes式）' },
  { n: 4, title: '換気・空調', goal: '床吹出型全館空調の空気の流れと回路網モデルを理解する', read: ['研究継承資料 2.5', 'SHASE 2021 その40'], app: [['/library/S-REF-15', 'その40'], ['/simulator', '多室モデル']], check: 'ファン弱・強で多室モデルの誤差が違う理由を説明できるか（F-SIM-02）' },
  { n: 5, title: '電気集塵機', goal: 'EPの原理・風量と効率・バイパスの考え方を理解する', read: ['研究継承資料 2.3・2.4', '2026年度中間梗概'], app: [['/library/S-2026-01', '2026年度中間梗概'], ['/simulator', 'バイパスモデル']], check: '最適バイパス開口率の結論が何に依存しているか（F-2026-03）' },
  { n: 6, title: '測定技術', goal: 'KC-52・ワイヤレスセンサー・そらまめくんの違いと校正を理解する', read: ['研究継承資料 第3章', 'センサー取扱説明書', 'JEM1467'], app: [['/library/S-2025-13', 'センサー説明書'], ['/library/S-REF-04', 'JEM1467']], check: 'センサーの公称精度と、室内濃度1〜5 μg/m³の比較で注意すべき点' },
  { n: 7, title: 'データ解析', goal: 'I/O比・回帰係数・減衰率を自分で計算できる', read: ['研究継承資料 第5章'], app: [['/data', 'データ解析（CSV・Excel取込）']], check: '同じ住宅で日ごとにI/Oがどれだけ変わるか（F-V-15）を自分のデータで確かめたか' },
  { n: 8, title: '過去研究の理解', goal: '自分が引き継ぐ年度の研究を、原データの検証結果まで読む', read: ['研究継承資料 第4章', '各年度の本論'], app: [['/library', '資料ライブラリ'], ['/report', '総合研究レポート']], check: 'その研究の結論のうち、検証済みのものと要再検証のものを区別できるか' },
  { n: 9, title: '研究テーマの選択', goal: 'テーマ候補を証拠に基づいて比較する', read: ['研究方針提案書 第6・7章'], app: [['/plan', '研究計画（テーマ比較）']], check: '重みを変えたときに順位がどう変わるか確かめたか' },
  { n: 10, title: '実験計画', goal: '仮説・測定・解析・スケジュール・代替案を含む計画書を作る', read: ['研究方針提案書 第7〜10章', '研究継承資料 3.3'], app: [['/plan', '自分の研究計画を作成']], check: '条件比較を同じ住宅で交互に行う設計になっているか（F-2025-09）' },
  { n: 11, title: '実験実施', goal: '校正→本測定→運転記録を確実に残す', read: ['研究継承資料 3.2・3.3'], check: '測定前後の並置校正と、分単位の運転記録を残したか' },
  { n: 12, title: '解析と検証', goal: '再計算スクリプトで結果を独立に確かめる', read: ['verification/ の検証記録', 'scripts/'], app: [['/data', 'データ解析']], check: '時間刻み・定義・単位の確認をしたか（第5章の誤り一覧）' },
  { n: 13, title: '卒業論文作成', goal: '根拠の区分（確認事実・分析・仮説）を明確にして書く', read: ['研究継承資料 第5章'], app: [['/report', 'レポート（Word・PDF出力）']], check: '図表の算出方法と原データの保存場所を論文に書いたか' },
]
type Progress = { done: number[]; notes: Record<string, string> }
const LS = 'aqros_learning'

export default function Learning() {
  const [p, setP] = useState<Progress>(() => { try { return JSON.parse(localStorage.getItem(LS) || '') } catch { return { done: [], notes: {} } } })
  const [msg, setMsg] = useState('')
  useEffect(() => { api.getState('learning').then((r) => { if (r.value) setP(r.value) }).catch(() => setMsg('オフライン: 端末内の進捗を表示')) }, [])
  const save = async (np: Progress) => {
    setP(np)
    try { localStorage.setItem(LS, JSON.stringify(np)) } catch { /* noop */ }
    try { await api.putState('learning', np); setMsg('保存しました') } catch { setMsg('オフライン: 端末内に保存（接続後に再保存してください）') }
  }
  const toggle = (n: number) => save({ ...p, done: p.done.includes(n) ? p.done.filter((x) => x !== n) : [...p.done, n].sort((a, b) => a - b) })
  return (
    <div className="page">
      <h1>研究学習モード（2027年度の新しい学生向け）</h1>
      <p className="lead">研究の全体像 → 基礎理論 → 過去研究 → 解析方法 → テーマ比較 → 研究計画 → 実験と解析 の順に進める。各段階の確認問題に答えられたら完了にする。進捗はサーバーに保存され、再起動後も残る。</p>
      <Card title="進捗"><Bar done={p.done.length} total={STEPS.length} /><span className="small muted">{msg}</span></Card>
      {STEPS.map((s) => (
        <Card key={s.n} className={p.done.includes(s.n) ? 'learn done' : 'learn'} title={<label className="check"><input type="checkbox" checked={p.done.includes(s.n)} onChange={() => toggle(s.n)} /> {s.n}. {s.title}</label>}>
          <p><b>目標</b>: {s.goal}</p>
          <p><b>読むもの</b>: {s.read.join(' ／ ')}</p>
          {s.app && <p><b>アプリで確認</b>: {s.app.map(([to, l]) => <Link key={to + l} to={to} className="chip">{l}</Link>)}</p>}
          <p className="note"><b>確認問題</b>: {s.check}</p>
          <textarea placeholder="自分のメモ・回答" value={p.notes[String(s.n)] || ''} onChange={(e) => setP({ ...p, notes: { ...p.notes, [String(s.n)]: e.target.value } })} onBlur={() => save(p)} rows={2} />
        </Card>
      ))}
      <p className="small muted">参考: 2025年度センサーの説明は <SourceRef id="S-2025-13" />、JEM1467 は <SourceRef id="S-REF-04" />。</p>
    </div>
  )
}
