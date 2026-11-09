import DOMPurify from 'dompurify'
import { marked } from 'marked'
import { useState } from 'react'
import { api, download } from '../core/api'
import { Card, Loading, useAsync } from '../components/ui'

const render = (md: string) => DOMPurify.sanitize(marked.parse(md, { async: false }) as string)

export default function Report() {
  const { data, error, reload } = useAsync(api.report)
  const { data: deliv } = useAsync(api.deliverables)
  const [edit, setEdit] = useState<string | null>(null)
  const [draft, setDraft] = useState('')
  const [msg, setMsg] = useState('')
  if (!data) return <Loading error={error} />
  const all = data.map((s) => s.body).join('\n\n')
  return (
    <div className="page report">
      <h1 className="noprint">総合研究レポート</h1>
      <div className="noprint filters">
        <button onClick={() => download('AirQualityResearchOS_report.md', all, 'text/markdown;charset=utf-8')}>Markdown出力</button>
        <button className="ghost" onClick={() => window.print()}>PDF出力（印刷→PDFに保存）</button>
        <span className="small muted">{msg}</span>
      </div>
      {deliv && deliv.length > 0 && [
        ['2027', '2027年度向け資料（Word・PDF・Markdown）', 'いずれも knowledge.json・検証記録・本報告書から scripts/build_books.py で生成。数値はアプリの表示と同じ出典から作られる。'],
        ['technical_report_2026-11', '中間統合技術調査報告書 2026-11（Word・PDF・台帳・数値監査）', 'scripts/build_tech_report.py で生成。根拠は Claim ID で EVIDENCE_LEDGER.csv、計算は NUMERICAL_AUDIT.csv をたどれる。研究室の公式見解ではなく、第三者査読は未実施。'],
      ].map(([g, title, note]) => {
        const items = deliv.filter((d) => (d.group || '2027') === g)
        if (!items.length) return null
        return (
          <Card key={g} className="noprint" title={title}>
            <ul className="deliv">{items.map((d) => {
              const base = d.name.split('/').pop() || d.name
              return <li key={d.name}><a href={d.href || `/api/deliverables/${d.name.split('/').map(encodeURIComponent).join('/')}`} download={base}>{base}</a> <span className="small muted">{(d.size / 1024).toFixed(0)} KB</span></li>
            })}</ul>
            <p className="small muted">{note}</p>
          </Card>
        )
      })}
      <nav className="toc noprint">{data.map((s) => <a key={s.id} href={`#${s.id}`}>{s.title}</a>)}</nav>
      <div className="print-title">Air Quality Research OS — 井口研究室 空気清浄度研究 総合研究報告書</div>
      {data.map((s) => (
        <Card key={s.id} className="sec" title={<span id={s.id}>{s.user_modified ? '✎ ' : ''}</span>}
          actions={<span className="noprint">{edit === s.id ? (
            <>
              <button onClick={async () => { try { await api.saveSection(s.id, draft); setEdit(null); setMsg('保存しました'); reload() } catch (e: any) { setMsg('保存失敗: ' + e.message) } }}>保存</button>
              <button className="ghost" onClick={() => setEdit(null)}>取消</button>
            </>
          ) : (
            <>
              <button className="ghost small" onClick={() => { setEdit(s.id); setDraft(s.body) }}>編集</button>
              {s.user_modified ? <button className="ghost small" onClick={async () => { if (confirm('リポジトリ版に戻しますか？編集内容は失われます。')) { await api.resetSection(s.id); reload() } }}>初期版に戻す</button> : null}
            </>
          )}</span>}>
          {edit === s.id ? (
            <div className="editor"><textarea value={draft} onChange={(e) => setDraft(e.target.value)} rows={24} /><div className="md" dangerouslySetInnerHTML={{ __html: render(draft) }} /></div>
          ) : <div className="md" dangerouslySetInnerHTML={{ __html: render(s.body) }} />}
        </Card>
      ))}
    </div>
  )
}
