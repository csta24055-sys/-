// 端末内バックエンド（スマホ単体版）が FastAPI と同じ結果を返すか、編集・保存・バックアップが正しく動くかの検証
import { readdirSync, readFileSync } from 'node:fs'
import { join } from 'node:path'
import { beforeAll, describe, expect, it } from 'vitest'
import { kv } from './idb'
import { exportBackup, handle, importBackup, setSeed } from './local'
import { policyCheck } from './cloud'
import parity from './testdata/api_parity.json'

const ROOT = join(__dirname, '../../..')

beforeAll(() => {
  const knowledge = JSON.parse(readFileSync(join(ROOT, 'knowledge/knowledge.json'), 'utf8'))
  const report = readdirSync(join(ROOT, 'report')).filter((f) => f.endsWith('.md')).sort().map((f, i) => {
    const body = readFileSync(join(ROOT, 'report', f), 'utf8')
    return { id: f.replace(/\.md$/, ''), ord: i, title: body.split('\n')[0].replace(/^#+\s*/, '').trim(), body }
  })
  setSeed({ version: 'test', generated_at: '2026-11-09T00:00:00+00:00', knowledge, report, deliverables: [],
    dashboard: { next_actions: parity.dashboard.next_actions, key_findings: parity.dashboard.key_findings } })
})

describe('FastAPI との一致（同じ knowledge.json・report から）', () => {
  it('ダッシュボード', async () => {
    await kv.clear()
    const d: any = await handle('GET', '/api/dashboard')
    expect(d.counts).toEqual(parity.dashboard.counts)
    expect(d.by_year).toEqual(parity.dashboard.by_year)
    expect(d.key_findings.map((f: any) => f.id)).toEqual(parity.dashboard.key_findings)
    expect(d.open_questions.map((q: any) => q.id)).toEqual(parity.dashboard.open_questions)
    expect(d.progress).toEqual(parity.dashboard.progress)
  })
  it('資料検索・詳細', async () => {
    for (const [q, want] of Object.entries(parity.queries)) {
      const r: any = await handle('GET', q)
      if (Array.isArray(want)) expect(r.map((s: any) => s.id), q).toEqual(want)
      else expect({ source: r.source.id, findings: r.findings.map((f: any) => f.id), studies: r.studies.map((s: any) => s.id), related: r.related.map((s: any) => s.id) }, q).toEqual(want)
    }
  })
  it('ナレッジ・報告書', async () => {
    const k: any = await handle('GET', '/api/knowledge')
    for (const [key, n] of Object.entries(parity.knowledge_counts)) if (n !== null) expect(k[key]?.length, key).toBe(n)
    expect(((await handle('GET', '/api/report')) as any[]).map((s) => s.id)).toEqual(parity.report_ids)
  })
})

describe('端末内の保存', () => {
  it('資料の状態・メモ、問い、計画、データセット、報告書の編集と初期化', async () => {
    await kv.clear()
    await handle('PATCH', '/api/sources/S-2025-01', { status: '数値検証済み', notes: 'メモ' })
    const s: any = await handle('GET', '/api/sources/S-2025-01')
    expect(s.source.status).toBe('数値検証済み'); expect(s.source._user_modified).toBe(true)
    await expect(handle('PATCH', '/api/sources/S-2025-01', { status: 'でたらめ' })).rejects.toThrow()
    const q: any = await handle('POST', '/api/questions', { text: '新しい問い' })
    expect(q.id).toMatch(/^Q-\d+$/)
    const p: any = await handle('POST', '/api/plans', { title: '計画A', theme_id: 'T-01', purpose: '目的' })
    await handle('PUT', `/api/plans/${p.id}`, { title: '計画A改', purpose: '目的2' })
    expect(((await handle('GET', '/api/plans')) as any[])[0].title).toBe('計画A改')
    const ds: any = await handle('POST', '/api/datasets', { name: 'd', columns: ['t', 'c'], rows: [[0, 1], [1, 2]] })
    expect(((await handle('GET', `/api/datasets/${ds.id}`)) as any).rows).toHaveLength(2)
    await handle('PUT', '/api/report/01_はじめに', { body: '# 編集' }).catch(() => undefined)
    const rid = parity.report_ids[0]
    await handle('PUT', `/api/report/${encodeURIComponent(rid)}`, { body: '# 編集済み' })
    let rep = (await handle('GET', '/api/report')) as any[]
    expect(rep.find((r) => r.id === rid).user_modified).toBe(1)
    await handle('POST', `/api/report/${encodeURIComponent(rid)}/reset`)
    rep = (await handle('GET', '/api/report')) as any[]
    expect(rep.find((r) => r.id === rid).user_modified).toBe(0)
    const d: any = await handle('GET', '/api/dashboard')
    expect(d.counts.datasets).toBe(1); expect(d.activity.length).toBeGreaterThan(0)
  })
  it('バックアップ → 全消去 → 復元（トークンは含めない）', async () => {
    await kv.set('cloud:token', 'secret')
    const b = await exportBackup()
    expect(b.entries.some(([k]) => k === 'cloud:token')).toBe(false)
    await kv.clear()
    expect(((await handle('GET', '/api/plans')) as any[]).length).toBe(0)
    await importBackup(JSON.parse(JSON.stringify(b)))
    expect(((await handle('GET', '/api/plans')) as any[])[0].title).toBe('計画A改')
    await expect(importBackup({ format: 'x' })).rejects.toThrow()
    await expect(importBackup({ format: 'aqros-backup', entries: [['cloud:token', 'x']] })).rejects.toThrow()
  })
})

describe('クラウド送信の安全確認', () => {
  const sens = [{ name: 'a.csv', data: new Uint8Array(), sensitive: true }]
  const syn = [{ name: 'b.csv', data: new Uint8Array(), sensitive: false }]
  it('公開リポジトリには研究データを送らない', () => { expect(policyCheck(false, sens, true)).toMatch(/公開リポジトリ/) })
  it('非公開でも同意がなければ送らない', () => { expect(policyCheck(true, sens, false)).toMatch(/同意/) })
  it('非公開＋同意なら送れる、合成データは公開でも可', () => { expect(policyCheck(true, sens, true)).toBeNull(); expect(policyCheck(false, syn, false)).toBeNull() })
})
