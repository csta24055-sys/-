import { useMemo, useState } from 'react'
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import ChartBox from './ChartBox'
import { Card, Field, fmt, Slider, useAsync } from './ui'
import { api, download, toCsv } from '../core/api'
import * as M from '../core/models'

const COLORS = ['#0f5b5c', '#c8553d', '#3a6ea5', '#8a6d1e', '#6b4c9a', '#2f8f83', '#b5446e', '#555']

/** 多室（換気回路網）モデル: SHASE 2021 その40 の実験住宅回路網をプリセットとして使用 */
export default function MultiZone() {
  const [setting, setSetting] = useState<'弱' | '強'>('弱')
  const [ep, setEp] = useState(false)
  const [eta, setEta] = useState(0.9)
  const [d, setD] = useState(0.0003)
  const [srcRoom, setSrcRoom] = useState('LDK')
  const [k, setK] = useState(0.0144)
  const [dur, setDur] = useState(1020)
  const [hours, setHours] = useState(1)
  const [cOut, setCOut] = useState(0.007)
  const [c0, setC0] = useState(0.01)
  const [shown, setShown] = useState(['LDK', '2階廊下・レターン', '洋室(大)', '洗面所', '1階廊下・玄関'])
  const net = useMemo(() => M.shase2021Network(setting), [setting])
  const res = useMemo(() => M.multizoneSimulate(net.volumes, net.flows, {
    hours, c_out: cOut, c0, sources: { [srcRoom]: k * 3600 }, source_hours: [0, dur / 3600],
    beta: M.decayRateToBeta(d), ep_edge: ep ? M.SHASE2021_EP_EDGE : null, eta_ep: eta, record_every_s: Math.max(10, hours * 3600 / 300),
  }), [net, hours, cOut, c0, srcRoom, k, dur, d, ep, eta])
  const zones = Object.keys(net.volumes)
  const data = res.t_h.map((t, i) => ({ t: +(t * 60).toFixed(2), ...Object.fromEntries(shown.map((z) => [z, res.series[z][i]])) }))
  const vol = Object.values(net.volumes).reduce((a, b) => a + b, 0)
  const qoa = net.flows.filter(([f]) => f === M.OUTDOOR).reduce((a, [, , q]) => a + q, 0)
  return (
    <Card title="③ 多室モデル（換気回路網・各室瞬時一様拡散）">
      <div className="eq">V<sub>i</sub>·dC<sub>i</sub>/dt = Σ<sub>j</sub> Q<sub>ji</sub>·C<sub>j</sub>·(1−η<sub>ji</sub>) − (Σ<sub>k</sub> Q<sub>ik</sub>)·C<sub>i</sub> − β·V<sub>i</sub>·C<sub>i</sub> + G<sub>i</sub>　,　β = −ln(1−D)·3600</div>
      <p className="small muted">回路網（13室・23経路）と容積は 空気調和・衛生工学会大会 2021 G-31「床チャンバー空調 その40」表-2・表-3【当事者の数値】。2018・2020年度卒論の簡易シミュレーションと同じ考え方を一般化【分析】。
        外気量は弱 {fmt(qoa, 0)} m³/h（全容積 {fmt(vol, 0)} m³ に対し {fmt(qoa / vol, 2)} 回/h）。減衰率 D: 密閉BOX 0.00015 /s、実住宅で実測に合う値 0.0003 /s（同論文）。</p>
      <div className="row4">
        <Field label="送風ファン"><select value={setting} onChange={(e) => setSetting(e.target.value as '弱' | '強')}><option>弱</option><option>強</option></select></Field>
        <Field label="発生室"><select value={srcRoom} onChange={(e) => setSrcRoom(e.target.value)}>{zones.map((z) => <option key={z}>{z}</option>)}</select></Field>
        <Field label="電気集塵機（空調室→建築ダクト）"><label className="check"><input type="checkbox" checked={ep} onChange={(e) => setEp(e.target.checked)} /> 稼働</label></Field>
        <Field label="減衰率 D [1/s]"><select value={d} onChange={(e) => setD(Number(e.target.value))}>
          <option value={0}>0（沈着なし）</option><option value={0.00015}>0.00015（密閉BOX）</option><option value={0.0003}>0.0003（論文の合わせ込み値）</option><option value={0.000475}>0.000475（本アプリ検証: ファン弱の最適）</option><option value={0.00075}>0.00075（本アプリ検証: ファン強の最適）</option></select></Field>
      </div>
      <div className="grid2">
        <div>
          <Slider label="発生量 K" value={k} min={0} max={0.05} step={0.0001} unit="mg/s" onChange={setK} hint="線香1本 0.00720 mg/s（同論文）。既定は2本分" />
          <Slider label="発生時間" value={dur} min={0} max={3600} step={30} unit="s" onChange={setDur} />
          {ep && <Slider label="集塵効率 η" value={eta} min={0} max={0.99} step={0.01} unit="" onChange={setEta} hint="2021年度シミュレーションの設定 0.90" />}
        </div>
        <div>
          <Slider label="計算時間" value={hours} min={0.1} max={6} step={0.1} unit="h" onChange={setHours} />
          <Slider label="外気濃度" value={cOut} min={0} max={0.05} step={0.001} unit="mg/m³" onChange={setCOut} />
          <Slider label="初期濃度（全室）" value={c0} min={0} max={0.05} step={0.001} unit="mg/m³" onChange={setC0} />
        </div>
      </div>
      <div className="chips">{zones.map((z) => <label key={z} className="check"><input type="checkbox" checked={shown.includes(z)} onChange={(e) => setShown(e.target.checked ? [...shown, z] : shown.filter((s) => s !== z))} />{z}</label>)}</div>
      <ChartBox name="multizone" height={300} caption={<span className="small muted">【計算結果】横軸: 分。実測との比較は同論文 図-9〜11（実測値の数値表は未入手）</span>}>
        <ResponsiveContainer><LineChart data={data} margin={{ left: -6, right: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--grid)" /><XAxis dataKey="t" type="number" unit="分" tick={{ fontSize: 11 }} domain={[0, hours * 60]} />
          <YAxis tick={{ fontSize: 11 }} /><Tooltip formatter={(v: number) => fmt(v, 4)} /><Legend wrapperStyle={{ fontSize: 12 }} />
          {shown.map((z, i) => <Line key={z} dataKey={z} stroke={COLORS[i % COLORS.length]} dot={false} strokeWidth={1.6} isAnimationActive={false} />)}
        </LineChart></ResponsiveContainer>
      </ChartBox>
      <div className="tablewrap"><table><thead><tr><th>室</th><th>容積 m³</th><th>最大濃度</th><th>最大時刻[分]</th><th>終了時濃度</th></tr></thead>
        <tbody>{zones.map((z) => {
          const s = res.series[z]; const mx = Math.max(...s); const at = res.t_h[s.indexOf(mx)] * 60
          return <tr key={z}><td>{z}</td><td>{net.volumes[z]}</td><td>{fmt(mx, 4)}</td><td>{fmt(at, 1)}</td><td>{fmt(s[s.length - 1], 4)}</td></tr>
        })}</tbody></table></div>
      <Validation />
      <button className="ghost" onClick={() => download('multizone.csv', toCsv(['t_h', ...zones], res.t_h.map((t, i) => [t, ...zones.map((z) => res.series[z][i])])))}>時系列CSV</button>
    </Card>
  )
}

/** 2020年度実測との検証結果（scripts/validate_multizone.py の指標のみ） */
function Validation() {
  const { data } = useAsync(api.knowledge)
  const v = data?.validation?.multizone
  const f = data?.validation?.fate2022
  if (!v) return null
  return (
    <>
    <details open className="validation">
      <summary><b>実測による検証</b>（2020年度 実験住宅・線香2本LDK発生・粉塵計3回平均, Box 1516270811625）【計算結果】</summary>
      <div className="tablewrap"><table><thead><tr><th>ファン</th><th>D [1/s]</th><th>β [1/h]</th><th>平均NRMSE</th><th>ピーク比（計算/実測）</th><th>レターン ピーク時刻 実測/計算 [s]</th></tr></thead>
        <tbody>{v.cases.map((c) => <tr key={c.fan + c.D_per_s}><td>{c.fan}</td><td>{c.D_per_s}</td><td>{fmt(c.beta_per_h, 2)}</td><td className={c.mean_nrmse > 0.4 ? 'warn' : ''}>{fmt(c.mean_nrmse, 2)}</td><td>{fmt(c.mean_peak_ratio, 2)}</td><td>{fmt(c.rooms['レターン']?.t_peak_meas, 0)} / {fmt(c.rooms['レターン']?.t_peak_sim, 0)}</td></tr>)}</tbody></table></div>
      <p className="small muted">最適D（0〜0.0008 を探索）: 弱 {v.grid_best['弱']?.best_D}（NRMSE {fmt(v.grid_best['弱']?.best_nrmse, 2)}）、強 {v.grid_best['強']?.best_D}（NRMSE {fmt(v.grid_best['強']?.best_nrmse, 2)}）。
        Dは運転条件に依存する較正係数で、還気口の応答時刻と室間差は再現できない（F-SIM-01〜04）。</p>
    </details>
    {f && (
      <details className="validation">
        <summary><b>2022年度シミュレーションの再計算</b>（粉塵の行方・30分, 同年度の入力値, Box 1516298663163）【計算結果】</summary>
        <div className="tablewrap"><table><thead><tr><th>粒径 μm</th><th>条件</th><th>LDK+吹抜 本アプリ/当時</th><th>非居室</th><th>集塵機</th><th>未沈着</th></tr></thead>
          <tbody>{f.rows.map((r) => <tr key={r.size_um + r.cond}><td>{r.size_um}</td><td>{r.fan}{r.ep ? '・EP' : ''}</td>
            <td className={Math.abs(r.diff_pt['LDK']) > 3 ? 'warn' : ''}>{fmt(r.model['LDK+吹抜'], 1)} / {fmt(r.reported['LDK'], 1)}</td>
            <td>{fmt(r.model['非居室'], 1)} / {fmt(r.reported['非居室'], 1)}</td><td>{fmt(r.model['集塵機'], 1)} / {fmt(r.reported['集塵機'], 1)}</td>
            <td>{fmt(r.model['残留'], 1)} / {fmt(r.reported['残留'], 1)}</td></tr>)}</tbody></table></div>
        <p className="small muted">EP・非居室の割合は全粒径で約1ポイント以内で再現。10 μm以上で当時の表にある「未沈着」（0.9〜5.6%）は物理的には残らず（β≥3.7×10⁻³ 1/s）、その分LDKの割合がずれる。1秒刻みの当時の再計算でも約1%残り、発生量の入力と集計の不一致による残差と判断（F-SIM-08〜12）。</p>
      </details>
    )}
    </>
  )
}
