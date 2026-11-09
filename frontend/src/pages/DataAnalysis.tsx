import Papa from 'papaparse'
import { useMemo, useState } from "react"
import { Bar, BarChart, CartesianGrid, ErrorBar, Legend, Line, LineChart, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis } from 'recharts'
import ChartBox from '../components/ChartBox'
import { Card, Field, fmt, Loading, SourceRef, useAsync } from '../components/ui'
import { api, Dataset, download, STANDALONE, toCsv } from '../core/api'
import { IO_LITERATURE, REGRESSION_LITERATURE } from '../core/literature'
import { defaultZone, zoneTimeSeries } from '../core/models'
import * as S from '../core/stats'
import { readXlsx } from '../core/xlsx'

const COLORS = ['#0f5b5c', '#c8553d', '#3a6ea5', '#8a6d1e', '#6b4c9a', '#2f8f83', '#b5446e']
type Mode = 'io' | 'eff' | 'dpq' | 'power' | 'decay'

export default function DataAnalysis() {
  const list = useAsync(api.datasets)
  const [sel, setSel] = useState<number | null>(null)
  const [local, setLocal] = useState<Dataset | null>(null)
  const [msg, setMsg] = useState('')
  const ds = useAsync(() => (sel ? api.dataset(sel) : Promise.resolve(null)), [sel])
  const data: Dataset | null = local || ds.data

  const onFile = async (f: File) => {
    setMsg('読み込み中…')
    const fd = new FormData(); fd.append('file', f); fd.append('name', f.name.replace(/\.[^.]+$/, ''))
    try {
      const r = await api.upload(fd)
      setMsg(`保存しました（${r.ids.length} シート）`); setLocal(null); list.reload(); setSel(r.ids[0])
    } catch (e: any) {
      if (/\.(csv|tsv|txt)$/i.test(f.name)) {
        Papa.parse<string[]>(f, { skipEmptyLines: true, complete: (res) => {
          const [head, ...rows] = res.data
          setLocal({ id: -1, name: f.name + '（一時・未保存）', filename: f.name, sheet: null, study: null, description: 'オフライン一時解析', provenance: '利用者インポート', columns: head, rows, n_rows: rows.length, created_at: '' })
          setMsg('サーバー未接続のため一時的にブラウザ内で解析します（保存されません）: ' + e.message)
        } })
      } else if (/\.(xlsx|xlsm)$/i.test(f.name)) {
        try {
          const sheets = await readXlsx(await f.arrayBuffer())
          if (!sheets.length) throw new Error('データのあるシートがありません')
          const sh = sheets[0]
          setLocal({ id: -1, name: `${f.name} [${sh.name}]（一時・未保存）`, filename: f.name, sheet: sh.name, study: null, description: `オフライン一時解析（全${sheets.length}シート中の先頭）`, provenance: '利用者インポート', columns: sh.columns, rows: sh.rows, n_rows: sh.rows.length, created_at: '' })
          setMsg('サーバー未接続のためブラウザ内で Excel を解析します（保存されません）: ' + e.message)
        } catch (x: any) { setMsg('Excel 読込失敗: ' + x.message) }
      } else setMsg('アップロード失敗: ' + e.message)
    }
  }

  const makeDemo = async () => {
    // 合成データ: 単室モデル＋外気の日変動。研究データではない。
    const p = { ...defaultZone, c0: 5, generation: 0 }
    let seed = 7
    const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647)
    const cout = (t: number) => 8 + 5 * Math.sin((2 * Math.PI * t) / 24) + (t > 30 && t < 36 ? 15 : 0)
    const gen = (t: number) => ([7.5, 12.2, 19.1].some((h) => Math.abs((t % 24) - h) < 0.3) ? 40000 : 0)
    const on = zoneTimeSeries(p, 48, 1 / 6, cout, gen)
    const off = zoneTimeSeries({ ...p, q_recirc: 0 }, 48, 1 / 6, cout, gen)
    const t0 = Date.UTC(2026, 0, 1)
    const rows = on.map((r, i) => [new Date(t0 + r.t * 3600e3).toISOString().slice(0, 19), +(cout(r.t) * (1 + 0.08 * (rnd() - 0.5))).toFixed(2),
      +(r.c * (1 + 0.1 * (rnd() - 0.5))).toFixed(2), +(off[i].c * (1 + 0.1 * (rnd() - 0.5))).toFixed(2)])
    rows[40][2] = null as any; rows[120][3] = 250
    const r = await api.createDataset({ name: '【合成デモ】単室モデル 48h（研究データではない）', columns: ['日時', '外気', '室内_EP稼働', '室内_EP停止'], rows,
      description: '本アプリの単室モデルで生成した合成データ。欠損1件・異常値1件を意図的に含む。', provenance: '合成（デモ）' })
    list.reload(); setSel(r.id); setLocal(null)
  }

  return (
    <div className="page">
      <h1>実験データ解析</h1>
      <p className="lead">CSV / Excel を取り込み、品質確認・時系列・I/O比・除去効率・差圧–風量・電力–CADR・減衰同定を行います。解析はブラウザ内で実行（オフライン可）し、データは{STANDALONE ? 'この端末の中（IndexedDB）だけ' : ' SQLite '}に保存されます。数十万行を超える場合や Python の詳細解析は「クラウド解析」を使えます。</p>
      <Card title="データの取り込み">
        <div className="filters">
          <input type="file" accept=".csv,.tsv,.txt,.xlsx,.xlsm,.xls" onChange={(e) => e.target.files?.[0] && onFile(e.target.files[0])} aria-label="ファイル選択" />
          <button className="ghost" onClick={makeDemo}>合成デモデータを作成</button>
          <span className="small muted">{msg}</span>
        </div>
        <p className="small muted">Box の原データ（例: S-2025-19 岩国測定データ.xlsx）はダウンロード後にここで取り込んでください。{STANDALONE ? '取り込んだデータはこの端末の中にだけ保存され、サーバーには送られません（バックアップは設定画面から）。' : '取り込んだデータは private_data/ の DB に保存され、Git にはコミットされません。'}</p>
        {list.data ? (
          <ul className="dslist">
            {list.data.map((d) => (
              <li key={d.id} className={d.id === sel && !local ? 'active' : ''}>
                <button className="link" onClick={() => { setLocal(null); setSel(d.id) }}>{d.name}</button>
                <span className="small muted"> {d.n_rows}行・{d.columns.length}列・{d.provenance}</span>
                <button className="ghost small" onClick={async () => { if (confirm(`「${d.name}」を削除しますか？`)) { await api.deleteDataset(d.id); if (sel === d.id) setSel(null); list.reload() } }}>削除</button>
              </li>
            ))}
            {!list.data.length && <li className="muted">保存済みデータはありません</li>}
          </ul>
        ) : <Loading error={list.error} />}
      </Card>
      {data ? <Analyzer key={`${data.id}-${data.name}`} ds={data} /> : sel && <Loading error={ds.error} />}
      <LiteratureCompare />
    </div>
  )
}

function Analyzer({ ds }: { ds: Dataset }) {
  const tcol = useMemo(() => S.detectTimeColumn(ds.columns, ds.rows), [ds])
  const nums = useMemo(() => S.numericColumns(ds.columns, ds.rows, tcol), [ds, tcol])
  const quality = useMemo(() => S.qualityReport(ds.rows, ds.columns, nums), [ds, nums])
  const [shown, setShown] = useState<string[]>(nums.slice(0, 3))
  const [hourly, setHourly] = useState(false)
  const [dropOutliers, setDropOutliers] = useState(false)
  const [mode, setMode] = useState<Mode>('io')
  const [x, setX] = useState(nums[0] || '')
  const [y, setY] = useState(nums[1] || nums[0] || '')
  const [thr, setThr] = useState(5)

  const outlierSet = useMemo(() => new Map(quality.map((q) => [q.column, new Set(q.outlier_rows)])), [quality])
  const col = (c: string) => {
    const i = ds.columns.indexOf(c)
    const o = outlierSet.get(c)
    return ds.rows.map((r, k) => (dropOutliers && o?.has(k) ? NaN : S.toNum(r[i])))
  }
  const ts = useMemo(() => {
    const ti = tcol ? ds.columns.indexOf(tcol) : -1
    const series = shown.map((c) => col(c))
    let pts = ds.rows.map((r, k) => {
      const o: Record<string, number | string> = { t: ti >= 0 ? String(r[ti]) : k }
      shown.forEach((c, j) => { const v = series[j][k]; if (Number.isFinite(v)) o[c] = v })
      return o
    })
    if (hourly && ti >= 0) {
      const g = new Map<string, { n: Record<string, number>; s: Record<string, number> }>()
      pts.forEach((p) => {
        const key = String(p.t).slice(0, 13)
        const e = g.get(key) || { n: {}, s: {} }
        shown.forEach((c) => { if (typeof p[c] === 'number') { e.s[c] = (e.s[c] || 0) + (p[c] as number); e.n[c] = (e.n[c] || 0) + 1 } })
        g.set(key, e)
      })
      pts = [...g.entries()].map(([k, e]) => ({ t: k + ':00', ...Object.fromEntries(shown.map((c) => [c, e.n[c] ? e.s[c] / e.n[c] : NaN])) }))
    }
    const step = Math.ceil(pts.length / 1500)
    return step > 1 ? pts.filter((_, i) => i % step === 0) : pts
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ds, shown, hourly, dropOutliers, tcol])

  return (
    <>
      <Card title={`データ: ${ds.name}`} actions={<button className="ghost small" onClick={() => download(`${ds.name}.csv`, toCsv(ds.columns, ds.rows))}>CSV出力</button>}>
        <p className="small muted">{ds.n_rows} 行／時刻列: {tcol || '検出なし'}／数値列: {nums.join(', ') || 'なし'}／由来: {ds.provenance}{ds.description ? `／${ds.description}` : ''}</p>
        <div className="tablewrap">
          <table><thead><tr><th>#</th>{ds.columns.map((c) => <th key={c}>{c}</th>)}</tr></thead>
            <tbody>{ds.rows.slice(0, 12).map((r, i) => <tr key={i}><td>{i}</td>{r.map((v, j) => <td key={j}>{v === null || v === '' ? <span className="miss">欠損</span> : String(v)}</td>)}</tr>)}</tbody></table>
        </div>
      </Card>
      <Card title="異常値・欠損値の検出" actions={<button className="ghost small" onClick={() => download(`${ds.name}_quality.csv`, toCsv(['列', 'n', '欠損', '欠損%', '負値', '異常値', '平均', '中央値', '標準偏差', '最小', '最大'], quality.map((q) => [q.column, q.n, q.missing, q.missing_pct.toFixed(2), q.negative, q.outliers, q.mean, q.median, q.std, q.min, q.max])))}>CSV出力</button>}>
        <p className="small muted">異常値 = ロバストZ（|x−中央値| / (1.4826·MAD)）&gt; 3.5。自動削除はせず、下のチェックで解析から除外できます。</p>
        <div className="tablewrap"><table><thead><tr><th>列</th><th>欠損</th><th>異常値</th><th>負値</th><th>平均</th><th>中央値</th><th>最小</th><th>最大</th><th>異常行（先頭）</th></tr></thead>
          <tbody>{quality.map((q) => <tr key={q.column}><td>{q.column}</td><td className={q.missing ? 'warn' : ''}>{q.missing}（{q.missing_pct.toFixed(1)}%）</td><td className={q.outliers ? 'warn' : ''}>{q.outliers}</td><td>{q.negative}</td><td>{fmt(q.mean)}</td><td>{fmt(q.median)}</td><td>{fmt(q.min)}</td><td>{fmt(q.max)}</td><td className="small">{q.outlier_rows.slice(0, 8).join(', ')}</td></tr>)}</tbody></table></div>
        <label className="check"><input type="checkbox" checked={dropOutliers} onChange={(e) => setDropOutliers(e.target.checked)} /> 異常値を解析から除外する</label>
      </Card>
      <Card title="時系列グラフ">
        <div className="chips">{nums.map((c) => <label key={c} className="check"><input type="checkbox" checked={shown.includes(c)} onChange={(e) => setShown(e.target.checked ? [...shown, c] : shown.filter((s) => s !== c))} />{c}</label>)}
          {tcol && <label className="check"><input type="checkbox" checked={hourly} onChange={(e) => setHourly(e.target.checked)} /> 1時間平均（2025年度の解析単位）</label>}</div>
        <ChartBox name={`${ds.name}_timeseries`} caption={<span className="small muted">出典: {ds.provenance}「{ds.name}」</span>}>
          <ResponsiveContainer><LineChart data={ts} margin={{ left: -10, right: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--grid)" /><XAxis dataKey="t" tick={{ fontSize: 10 }} minTickGap={40} /><YAxis tick={{ fontSize: 11 }} />
            <Tooltip /><Legend wrapperStyle={{ fontSize: 12 }} />
            {shown.map((c, i) => <Line key={c} dataKey={c} stroke={COLORS[i % COLORS.length]} dot={false} strokeWidth={1.5} isAnimationActive={false} connectNulls={false} />)}
          </LineChart></ResponsiveContainer>
        </ChartBox>
      </Card>
      <Card title="解析">
        <div className="tabs">{([['io', '室内・外気比較'], ['eff', '粒径別除去効率'], ['dpq', '差圧と風量'], ['power', '消費電力とCADR'], ['decay', '減衰（β同定）']] as [Mode, string][]).map(([m, l]) => <button key={m} className={mode === m ? 'on' : ''} onClick={() => setMode(m)}>{l}</button>)}</div>
        <div className="row2">
          <Field label={({ io: '外気列 (x)', eff: '上流列', dpq: '差圧 ΔP 列 [Pa]', power: '消費電力列 [W]', decay: '経過時間列 [s]' } as const)[mode]}>
            <select value={x} onChange={(e) => setX(e.target.value)}>{nums.map((c) => <option key={c}>{c}</option>)}</select></Field>
          <Field label={({ io: '室内列 (y)', eff: '下流列', dpq: '風量 Q 列 [m³/h]', power: 'CADR列 [m³/h]', decay: '濃度列' } as const)[mode]}>
            <select value={y} onChange={(e) => setY(e.target.value)}>{nums.map((c) => <option key={c}>{c}</option>)}</select></Field>
        </div>
        {mode === 'io' && <Field label="基準値（超過割合の計算）"><input type="number" value={thr} onChange={(e) => setThr(Number(e.target.value))} /> μg/m³（WHO 年5・日15）</Field>}
        <AnalysisResult mode={mode} xs={col(x)} ys={col(y)} xName={x} yName={y} thr={thr} dsName={ds.name} />
      </Card>
    </>
  )
}

function AnalysisResult({ mode, xs, ys, xName, yName, thr, dsName }: { mode: Mode; xs: number[]; ys: number[]; xName: string; yName: string; thr: number; dsName: string }) {
  const pts = xs.map((x, i) => ({ x, y: ys[i] })).filter((p) => Number.isFinite(p.x) && Number.isFinite(p.y))
  const sample = pts.length > 3000 ? pts.filter((_, i) => i % Math.ceil(pts.length / 3000) === 0) : pts
  let res: Record<string, number> | null = null, fitLine: { x: number; y: number }[] = [], err = ''
  try {
    if (pts.length < 3) throw new Error('有効なデータ点が3点未満です')
    const X = pts.map((p) => p.x), Y = pts.map((p) => p.y)
    const xmax = Math.max(...X), xmin = Math.min(...X)
    const line = (f: (x: number) => number) => Array.from({ length: 30 }, (_, i) => { const x = xmin + ((xmax - xmin) * i) / 29; return { x, y: f(x) } })
    if (mode === 'io') {
      const r = S.regressionThroughOrigin(X, Y), io = S.ioRatio(Y, X)
      res = { '回帰係数 k（原点通過）': r.k, '95%CI 下限': r.ci_low, '95%CI 上限': r.ci_high, 'R²（非中心化）': r.r2, 'I/O比（平均比）': io.io_ratio_of_means, 'I/O比（比の中央値）': io.io_median_of_ratios, [`室内 ${thr} 超過割合`]: S.exceedance(Y, thr), [`外気 ${thr} 超過割合`]: S.exceedance(X, thr), n: r.n }
      fitLine = line((x) => r.k * x)
    } else if (mode === 'eff') {
      const r = S.removalEfficiency(X, Y)
      res = { '除去効率 η [%]（時刻別平均）': r.eta_mean_of_ratios, 'η [%]（平均濃度比）': r.eta_ratio_of_means, '標準偏差 [%]': r.eta_std, n: r.n }
    } else if (mode === 'dpq') {
      const r = S.powerLawFit(X, Y)
      res = { 'a（Q = a·ΔP^b）': r.a, b: r.b, 'R²（対数空間）': r.r2, n: r.n, '参考: 2026年度 a': 78.611, '参考: 2026年度 b': 0.828 }
      fitLine = line((x) => r.a * Math.pow(Math.max(x, 1e-9), r.b))
    } else if (mode === 'power') {
      const r = S.linearRegression(X, Y)
      res = { '傾き [m³/h per W]': r.slope, 切片: r.intercept, R2: r.r2, n: r.n, 'CADR/電力 平均 [m³/h/W]': Y.reduce((s, v, i) => s + v / (X[i] || NaN), 0) / Y.length }
      fitLine = line((x) => r.slope * x + r.intercept)
    } else {
      const r = S.fitDecay(X, Y)
      res = { 'β [1/s]': r.beta_per_s, 'β [1/h]': r.beta_per_s * 3600, C0: r.c0, R2: r.r2, n: r.n }
      fitLine = line((x) => r.c0 * Math.exp(-r.beta_per_s * x))
    }
  } catch (e: any) { err = e.message }
  const note = {
    io: '原点通過回帰は2025年度梗概 表3 と同じ定義。1時間平均・夜間抽出を推奨（H-02b）。CI は自己相関を考慮しないため過小になり得ます（F-2025-07）。',
    eff: 'η = (1 − 下流/上流) × 100（2026年度 式(1), JIS B 9908-5 準拠の考え方）。粒径帯ごとに列を選んで比較してください。',
    dpq: 'Excel の累乗近似と同じ対数線形回帰。外挿は測定範囲外の結論を左右します（F-2026-03）。',
    power: '電力とCADRの線形関係を確認します。CADR = η × 通過風量 を事前に列として用意してください。',
    decay: '発塵終了後の区間のみを選んで同定してください（2021年度 式(3), M=0）。',
  }[mode]
  return (
    <div>
      {err ? <div className="error">{err}</div> : res && (
        <div className="grid2">
          <div>
            <table className="kvtable"><tbody>{Object.entries(res).map(([k, v]) => <tr key={k}><th>{k}</th><td>{fmt(v, 4)}</td></tr>)}</tbody></table>
            <p className="small muted">【計算結果】{note}</p>
            <button className="ghost small" onClick={() => download(`${dsName}_${mode}_result.csv`, toCsv(['項目', '値'], Object.entries(res!)))}>結果をCSV出力</button>
          </div>
          <ChartBox name={`${dsName}_${mode}`} height={280} caption={<span className="small muted">x: {xName} / y: {yName}</span>}>
            <ResponsiveContainer><ScatterChart margin={{ left: -10, right: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--grid)" />
              <XAxis type="number" dataKey="x" name={xName} tick={{ fontSize: 11 }} domain={['auto', 'auto']} />
              <YAxis type="number" dataKey="y" name={yName} tick={{ fontSize: 11 }} domain={['auto', 'auto']} />
              <ZAxis range={[12, 12]} /><Tooltip />
              <Scatter data={sample} fill="#3a6ea5" fillOpacity={0.45} isAnimationActive={false} />
              {fitLine.length > 0 && <Scatter data={fitLine} line={{ stroke: '#c8553d', strokeWidth: 2 }} shape={() => <g />} isAnimationActive={false} />}
            </ScatterChart></ResponsiveContainer>
          </ChartBox>
        </div>
      )}
    </div>
  )
}

function LiteratureCompare() {
  const [k, setK] = useState(0)
  return (
    <Card title="複数研究の比較（文献値）">
      <p className="small muted">梗概に記載された集計値。原データではありません。【確認事実】出典: <SourceRef id="S-2024-01" /> <SourceRef id="S-2025-01" /> <SourceRef id="S-2025-02" /></p>
      <div className="tabs"><button className={k === 0 ? 'on' : ''} onClick={() => setK(0)}>I/O比（2024・2025）</button><button className={k === 1 ? 'on' : ''} onClick={() => setK(1)}>回帰係数（2025）</button></div>
      {k === 0 ? (
        <ChartBox name="literature_io" height={340} caption={<span className="small muted">住宅C ①・③は中間版と最終版で値が異なる（F-2025-06）</span>}>
          <ResponsiveContainer><BarChart data={IO_LITERATURE} layout="vertical" margin={{ left: 40, right: 16 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--grid)" /><XAxis type="number" domain={[0, 1.6]} tick={{ fontSize: 11 }} />
            <YAxis type="category" dataKey="house" tick={{ fontSize: 10 }} width={110} /><Tooltip formatter={(v: number, _n, p: any) => [v, `${p.payload.cond}（${p.payload.src}）`]} />
            <Bar dataKey="io" name="I/O比" fill="#2f8f83" isAnimationActive={false} />
          </BarChart></ResponsiveContainer>
        </ChartBox>
      ) : (
        <ChartBox name="literature_regression" height={240} caption={<span className="small muted">エラーバー: 論文記載の95%CI</span>}>
          <ResponsiveContainer><BarChart data={REGRESSION_LITERATURE.map((r) => ({ ...r, e: [r.k - r.lo, r.hi - r.k] }))} margin={{ left: -10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--grid)" /><XAxis dataKey="cond" tick={{ fontSize: 10 }} /><YAxis domain={[0, 1.2]} tick={{ fontSize: 11 }} /><Tooltip />
            <Bar dataKey="k" name="回帰係数 k" fill="#0f5b5c" isAnimationActive={false}><ErrorBar dataKey="e" width={6} stroke="#c8553d" /></Bar>
          </BarChart></ResponsiveContainer>
        </ChartBox>
      )}
    </Card>
  )
}
