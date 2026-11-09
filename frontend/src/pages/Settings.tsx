import { useEffect, useState } from 'react'
import { Card, Field } from '../components/ui'
import { download, STANDALONE } from '../core/api'
import { checkRepo, getSettings, hasToken, saveSettings, setToken } from '../core/cloud'
import { kv, requestPersist, storageEstimate } from '../core/idb'
import { exportBackup, importBackup } from '../core/local'

const mb = (n: number) => (n / 1024 / 1024).toFixed(1) + ' MB'

export function useBackupReminder() {
  const [need, setNeed] = useState<'' | 'never' | 'old'>('')
  useEffect(() => {
    if (!STANDALONE) return
    ;(async () => {
      const last = await kv.get<string>('meta:last_backup')
      const user = (await kv.keys('')).filter((k) => /^(item:|dataset:|report:|plan:|state:)/.test(k)).length
      setNeed(user === 0 ? '' : !last ? 'never' : Date.now() - Date.parse(last) > 7 * 864e5 ? 'old' : '')
    })().catch(() => undefined)
  }, [])
  return need
}

export default function Settings() {
  const [est, setEst] = useState<{ usage: number; quota: number } | null>(null)
  const [persist, setPersist] = useState<boolean | null>(null)
  const [last, setLast] = useState<string | null>(null)
  const [msg, setMsg] = useState('')
  const [cs, setCs] = useState({ owner: '', repo: '', base_branch: '', api: '' })
  const [tok, setTok] = useState('')
  const [hasTok, setHasTok] = useState(false)
  const [repoMsg, setRepoMsg] = useState('')

  const refresh = async () => {
    setEst(await storageEstimate())
    setPersist(navigator.storage?.persisted ? await navigator.storage.persisted().catch(() => null) : null)
    setLast((await kv.get<string>('meta:last_backup')) || null)
    setCs(await getSettings()); setHasTok(await hasToken())
  }
  useEffect(() => { refresh() }, [])

  const doBackup = async () => {
    const b = await exportBackup()
    const d = new Date().toISOString().slice(0, 10)
    download(`aqros-backup-${d}.json`, JSON.stringify(b), 'application/json')
    await kv.set('meta:last_backup', new Date().toISOString())
    setMsg(`バックアップを書き出しました（${b.entries.length} 件）。ファイルアプリ／ダウンロードに保存されます。`); refresh()
  }
  const doRestore = async (f: File, mode: 'merge' | 'replace') => {
    try {
      const obj = JSON.parse(await f.text())
      if (mode === 'replace' && !confirm('端末内のデータをすべてバックアップの内容に置き換えます。よろしいですか？')) return
      const r = await importBackup(obj, mode)
      setMsg(`復元しました（${r.restored} 件）。画面を再読み込みします。`)
      setTimeout(() => location.reload(), 800)
    } catch (e: any) { setMsg('復元できません: ' + e.message) }
  }

  return (
    <div className="page">
      <h1>設定・バックアップ</h1>
      <p className="lead">{STANDALONE
        ? 'このスマホ版では、研究データ・編集内容・研究計画・学習記録をこの端末の中（IndexedDB）だけに保存します。サーバーには送りません。'
        : 'サーバー版です。データはサーバー側の SQLite（private_data/ またはデスクトップ版の利用者データフォルダ）に保存されます。'}</p>

      {STANDALONE && <>
        <Card title="端末内の保存状況">
          <ul className="small">
            <li>使用量: {est ? `${mb(est.usage)}（上限の目安 ${mb(est.quota)}）` : '取得できません'}</li>
            <li>永続保存: {persist === true ? '許可済み（ブラウザが自動削除しにくい状態）' : persist === false ? '未許可（容量不足時にブラウザが削除する可能性があります）' : '不明'}</li>
            <li>最終バックアップ: {last ? new Date(last).toLocaleString('ja-JP') : 'まだありません'}</li>
          </ul>
          <button className="ghost" onClick={async () => { setPersist(await requestPersist()); }}>永続保存を依頼する</button>
          <p className="small muted">iPhone ではホーム画面に追加したアプリとして使うと保存が安定します。ただし端末の容量不足やブラウザデータの消去でデータが失われることがあるため、定期的なバックアップが必要です。</p>
        </Card>
        <Card title="バックアップ">
          <button onClick={doBackup}>バックアップを書き出す（JSON）</button>
          <p className="small muted">取り込んだ実測データを含みます。研究室の規程に従って保管し、公開の場所（公開リポジトリ・SNS 等）に置かないでください。GitHub のトークンは含めません。</p>
        </Card>
        <Card title="復元">
          <div className="row2">
            <Field label="追加（同じ項目は上書き）"><input type="file" accept="application/json,.json" onChange={(e) => e.target.files?.[0] && doRestore(e.target.files[0], 'merge')} aria-label="バックアップを追加で復元" /></Field>
            <Field label="置き換え（端末内を全消去して復元）"><input type="file" accept="application/json,.json" onChange={(e) => e.target.files?.[0] && doRestore(e.target.files[0], 'replace')} aria-label="バックアップで置き換え" /></Field>
          </div>
        </Card>
      </>}
      {msg && <div className="note" role="status">{msg}</div>}

      <Card title="クラウド解析の接続先（GitHub）">
        <p className="small">重い処理（大規模計算・Python 解析・Word/PDF 生成・OCR）を GitHub Actions で実行します。トークンはこの端末にだけ保存し、アプリには埋め込みません。</p>
        <div className="row2">
          <Field label="所有者（owner）"><input value={cs.owner} onChange={(e) => setCs({ ...cs, owner: e.target.value.trim() })} placeholder="例: csta24055-sys" /></Field>
          <Field label="リポジトリ"><input value={cs.repo} onChange={(e) => setCs({ ...cs, repo: e.target.value.trim() })} placeholder="非公開リポジトリを推奨" /></Field>
          <Field label="ジョブの元ブランチ"><input value={cs.base_branch} onChange={(e) => setCs({ ...cs, base_branch: e.target.value.trim() })} /></Field>
          <Field label={`アクセストークン ${hasTok ? '（保存済み）' : '（未設定）'}`} hint="細粒度トークン: 対象リポジトリのみ、Contents 読み書き・Actions 読み取り">
            <input type="password" autoComplete="off" value={tok} onChange={(e) => setTok(e.target.value)} placeholder={hasTok ? '変更する場合のみ入力' : 'github_pat_...'} />
          </Field>
        </div>
        <div className="filters">
          <button onClick={async () => { await saveSettings(cs); if (tok) await setToken(tok); setTok(''); setRepoMsg('保存しました'); refresh() }}>保存</button>
          <button className="ghost" onClick={async () => { setRepoMsg('確認中…'); try { const r = await checkRepo(); setRepoMsg(`${r.full_name}: ${r.private ? '非公開（研究データの処理可・同意が必要）' : '公開（計算条件と合成データのみ送信可）'} / 書き込み権限 ${r.push ? 'あり' : 'なし'} / ワークフロー ${r.workflow ? 'あり' : 'なし'}`) } catch (e: any) { setRepoMsg('接続できません: ' + e.message) } }}>接続を確認</button>
          {hasTok && <button className="ghost" onClick={async () => { if (confirm('この端末からトークンを削除しますか？')) { await setToken(''); refresh() } }}>トークンを削除</button>}
        </div>
        {repoMsg && <p className="small" role="status">{repoMsg}</p>}
      </Card>
      <p className="small muted">版: {import.meta.env.VITE_APP_VERSION || 'dev'}（{STANDALONE ? 'スマホ単体版' : 'サーバー版'}）</p>
    </div>
  )
}
