import { useMemo, useState } from 'react'
import { CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import ChartBox from '../components/ChartBox'
import { Card, Field, fmt, Slider, SourceRef } from '../components/ui'
import { download, toCsv } from '../core/api'
import { SEASONAL_OUTDOOR } from '../core/literature'
import * as M from '../core/models'

const EP_BODY_W = 26 // 2018年度梗概のEP仕様値（S-2018-01）【仮定: 機種が同等】

interface Sim extends M.ZoneParams { hours: number; opHours: number }

function simulate(p: Sim) {
  // 運転時間: 各日の 0〜opHours 時に EP（循環清浄）稼働、それ以外は停止（循環も停止と仮定）
  const dt = Math.max(p.hours / 600, 1 / 60)
  const out: { t: number; c: number; cout: number }[] = [{ t: 0, c: p.c0, cout: p.c_out }]
  let c = p.c0, t = 0
  const n = Math.round(p.hours / dt)
  for (let i = 0; i < n; i++) {
    const on = (t % 24) < p.opHours
    const q = { ...p, q_recirc: on ? p.q_recirc : 0 }
    const lam = M.zoneLossRate(q)
    const ceq = M.zoneSource(q) / (q.volume * lam)
    c = ceq + (c - ceq) * Math.exp(-lam * dt)
    t += dt
    out.push({ t: +t.toFixed(4), c, cout: p.c_out })
  }
  return out
}

export default function Simulator() {
  const [b, setB] = useState({ n: 10, setting: '中', bin: '0.3-0.5', law: 'quadratic_ext' as M.EpLaw, r: 0.25 })
  const sweep = useMemo(() => M.bypassSweep(b.n, b.setting, 21, b.bin, b.law), [b.n, b.setting, b.bin, b.law])
  const cur = useMemo(() => M.solveBypass(b.r, b.n, b.setting, b.bin, b.law), [b])
  const [p, setP] = useState<Sim>({ ...M.defaultZone, c_out: 8.6, hours: 48, opHours: 24, c0: 8 })
  const set = (k: keyof Sim) => (v: number) => setP({ ...p, [k]: v })
  const link = () => setP({ ...p, q_recirc: Math.round(cur.q_total), bypass_ratio: +(cur.q_bp / cur.q_total).toFixed(3), eta_ep: +cur.eta.toFixed(3) })
  const series = useMemo(() => simulate(p), [p])
  const avg = series.reduce((s, x) => s + x.c, 0) / series.length
  const zp: M.ZoneParams = p
  const warn = [...M.zoneWarnings(zp), ...(p.opHours < 24 ? ['運転時間<24h: 停止中は循環も停止と仮定（全館空調の送風継続時は過大評価）'] : [])]
  const nUnits = Math.max(1, Math.round(p.q_recirc / M.FAN_SETTINGS['中'][0]))
  const power = useMemo(() => {
    // 推定電力: 中設定の送風機 n 台、開口率は流量比に最も近いものを探索
    const cands = M.bypassSweep(nUnits, '中', 41, '0.3-0.5', b.law)
    const best = cands.reduce((a, r) => (Math.abs(r.q_bp / r.q_total - p.bypass_ratio) < Math.abs(a.q_bp / a.q_total - p.bypass_ratio) ? r : a))
    return { fan: best.power_total, total: best.power_total + EP_BODY_W, ok: best.within_fan_limit }
  }, [nUnits, p.bypass_ratio, b.law])
  const kwh = (power.total * p.opHours * 365) / 1000

  return (
    <div className="page">
      <h1>空気清浄シミュレーター</h1>
      <p className="lead">2026年度中間梗概の並列流路モデル（<SourceRef id="S-2026-01" />）と単室完全混合マスバランスを結合。全計算はブラウザ内（オフライン可）で、Python 実装と数値一致をテスト済み。</p>

      <Card title="① 電気集塵機 ∥ バイパス 並列流路モデル">
        <div className="eq">N·q<sub>fan</sub>(ΔP) = 78.611·ΔP<sup>0.828</sup> + 3600·α·A·r·√(2ΔP/ρ)　,　CADR = η(Q<sub>EP</sub>)·Q<sub>EP</sub>　（α=0.65, A=0.25 m², ρ=1.2 kg/m³）</div>
        <div className="row4">
          <Field label="送風機台数 N"><input type="number" min={1} max={40} value={b.n} onChange={(e) => setB({ ...b, n: Number(e.target.value) })} /></Field>
          <Field label="風量設定"><select value={b.setting} onChange={(e) => setB({ ...b, setting: e.target.value })}>{Object.keys(M.FAN_SETTINGS).map((k) => <option key={k}>{k}</option>)}</select></Field>
          <Field label="粒径帯（η）"><select value={b.bin} onChange={(e) => setB({ ...b, bin: e.target.value })}>{Object.keys(M.EP_EFFICIENCY_ENDPOINTS).map((k) => <option key={k} value={k}>{k} μm</option>)}</select></Field>
          <Field label="集塵機抵抗則（750 m³/h超）" hint="F-2026-03: 本文の差圧値は二乗則で再現"><select value={b.law} onChange={(e) => setB({ ...b, law: e.target.value as M.EpLaw })}>
            <option value="fit">式(2)を全域適用</option><option value="quadratic_ext">二乗則で外挿</option></select></Field>
        </div>
        <Slider label="バイパス開口率 r" value={b.r} min={0} max={1} step={0.05} unit="" onChange={(v) => setB({ ...b, r: v })} />
        <div className="stats">
          <div className="stat"><div className="stat-v">{fmt(cur.cadr, 0)}</div><div className="stat-l">CADR [m³/h]</div></div>
          <div className="stat"><div className="stat-v">{fmt(cur.dp, 1)}</div><div className="stat-l">静圧 ΔP [Pa]</div></div>
          <div className="stat"><div className="stat-v">{fmt(cur.q_ep, 0)} / {fmt(cur.q_bp, 0)}</div><div className="stat-l">Q_EP / Q_BP [m³/h]</div></div>
          <div className="stat"><div className="stat-v">{fmt(cur.eta * 100, 1)}%</div><div className="stat-l">集塵効率 η</div></div>
          <div className="stat"><div className="stat-v">{fmt(cur.power_total, 1)}</div><div className="stat-l">送風機電力 [W]</div></div>
        </div>
        {cur.warnings.length > 0 && <ul className="warnlist">{cur.warnings.map((w) => <li key={w}>⚠ {w}</li>)}</ul>}
        <div className="grid2">
          <ChartBox name="bypass_cadr" height={250} caption={<span className="small muted">【計算結果】破線=現在の開口率。白抜き区間は定風量制御限界超過</span>}>
            <ResponsiveContainer><LineChart data={sweep.map((r) => ({ r: r.opening_ratio * 100, CADR: r.within_fan_limit ? r.cadr : null, 'CADR(限界超)': r.within_fan_limit ? null : r.cadr }))} margin={{ left: -10, right: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--grid)" /><XAxis dataKey="r" unit="%" tick={{ fontSize: 11 }} /><YAxis tick={{ fontSize: 11 }} unit="" /><Tooltip /><Legend wrapperStyle={{ fontSize: 12 }} />
              <Line dataKey="CADR" stroke="#0f5b5c" strokeWidth={2} dot={false} isAnimationActive={false} />
              <Line dataKey="CADR(限界超)" stroke="#0f5b5c" strokeDasharray="4 3" dot={false} isAnimationActive={false} />
              <ReferenceLine x={b.r * 100} stroke="#c8553d" strokeDasharray="3 3" />
            </LineChart></ResponsiveContainer>
          </ChartBox>
          <ChartBox name="bypass_power" height={250} caption={<span className="small muted">送風機電力は図6の直線近似【仮定】</span>}>
            <ResponsiveContainer><LineChart data={sweep.map((r) => ({ r: r.opening_ratio * 100, 電力W: r.power_total, 静圧Pa: r.dp }))} margin={{ left: -10, right: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--grid)" /><XAxis dataKey="r" unit="%" tick={{ fontSize: 11 }} /><YAxis tick={{ fontSize: 11 }} /><Tooltip /><Legend wrapperStyle={{ fontSize: 12 }} />
              <Line dataKey="電力W" stroke="#c8553d" strokeWidth={2} dot={false} isAnimationActive={false} />
              <Line dataKey="静圧Pa" stroke="#3a6ea5" dot={false} isAnimationActive={false} />
              <ReferenceLine y={M.FAN_SETTINGS[b.setting][1]} stroke="#8a6d1e" strokeDasharray="4 4" label={{ value: '定風量限界', fontSize: 10, fill: '#8a6d1e' }} />
            </LineChart></ResponsiveContainer>
          </ChartBox>
        </div>
        <button onClick={link}>この運転点を室内濃度モデルに反映 ↓</button>{' '}
        <button className="ghost" onClick={() => download(`bypass_${b.n}_${b.setting}_${b.law}.csv`, toCsv(['開口率', '静圧Pa', '総風量', 'Q_EP', 'Q_BP', 'η', 'CADR', '電力W', '限界内'], sweep.map((r) => [r.opening_ratio, r.dp, r.q_total, r.q_ep, r.q_bp, r.eta, r.cadr, r.power_total, r.within_fan_limit])))}>結果CSV</button>
      </Card>

      <Card title="② 室内濃度（単室完全混合マスバランス）">
        <div className="eq">V·dC/dt = Q<sub>OA</sub>(1−η<sub>OA</sub>)C<sub>out</sub> + Q<sub>inf</sub>·P·C<sub>out</sub> + G − (Q<sub>OA</sub> + Q<sub>inf</sub> + η<sub>EP</sub>·Q<sub>rec</sub>(1−b))·C − β·V·C</div>
        <p className="small muted">単位: V[m³], Q[m³/h], C[μg/m³], G[μg/h], β[1/h]。根拠: 2018・2020年度の換気式（<SourceRef id="S-2018-01" /> <SourceRef id="S-2020-01" />）を外気・集塵・沈着項で拡張【分析】。適用範囲: 住宅全体を1室とみなす瞬時一様拡散。室間差は表現しない。</p>
        <div className="grid2">
          <div>
            <Slider label="換気量 Q_OA" value={p.q_oa} min={0} max={600} step={5} unit="m³/h" onChange={set('q_oa')} hint={`換気回数 ${fmt(p.q_oa / p.volume, 2)} 回/h`} />
            <Slider label="外気フィルタ捕集率 η_OA" value={p.eta_oa_filter} min={0} max={0.99} step={0.01} unit="" onChange={set('eta_oa_filter')} hint="2025年度 条件② 回帰係数0.55 → 0.45" />
            <Slider label="循環風量 Q_rec" value={p.q_recirc} min={0} max={4000} step={10} unit="m³/h" onChange={set('q_recirc')} />
            <Slider label="集塵効率 η_EP" value={p.eta_ep} min={0} max={0.99} step={0.01} unit="" onChange={set('eta_ep')} hint="2026年度: 100 m³/h≥0.95, 750 m³/h 0.82〜0.92" />
            <Slider label="バイパス流量比 b" value={p.bypass_ratio} min={0} max={1} step={0.01} unit="" onChange={set('bypass_ratio')} hint="①の結果を反映すると Q_BP/Q_total が入ります" />
            <Slider label="室容積 V" value={p.volume} min={20} max={800} step={5} unit="m³" onChange={set('volume')} />
          </div>
          <div>
            <Slider label="外気粉塵濃度 C_out" value={p.c_out} min={0} max={60} step={0.1} unit="μg/m³" onChange={set('c_out')} />
            <div className="chips">{SEASONAL_OUTDOOR.slice(0, 6).flatMap((s) => (['春', '冬'] as const).map((k) => <button key={s.site + k} className="ghost small" onClick={() => setP({ ...p, c_out: s[k] })}>{s.site}{k} {s[k]}</button>))}<span className="small muted">季節平均（<SourceRef id="S-2025-03" />）</span></div>
            <Slider label="室内発塵率 G" value={p.generation} min={0} max={50000} step={100} unit="μg/h" onChange={set('generation')} hint="生活行動別の値は未定量（Q-07）。仮定値として入力" />
            <Slider label="沈着係数 β" value={p.deposition} min={0} max={2} step={0.01} unit="1/h" onChange={set('deposition')} hint="重力沈降理論 1μm≈0.05, 2.5μm≈0.3 /h（H=2.4 m）" />
            <Slider label="隙間侵入量 Q_inf" value={p.q_inf} min={0} max={200} step={1} unit="m³/h" onChange={set('q_inf')} />
            <Slider label="EP運転時間" value={p.opHours} min={0} max={24} step={1} unit="h/日" onChange={set('opHours')} />
            <Slider label="計算時間" value={p.hours} min={1} max={168} step={1} unit="h" onChange={set('hours')} />
            <Slider label="初期濃度 C0" value={p.c0} min={0} max={100} step={0.5} unit="μg/m³" onChange={set('c0')} />
          </div>
        </div>
        <div className="stats">
          <div className="stat"><div className="stat-v">{fmt(M.zoneSteadyState(zp), 2)}</div><div className="stat-l">定常濃度 [μg/m³]（稼働時）</div></div>
          <div className="stat"><div className="stat-v">{fmt(M.zoneIoRatio(zp), 3)}</div><div className="stat-l">定常 I/O比（G=0）</div></div>
          <div className="stat"><div className="stat-v">{fmt(M.zoneCadr(zp), 0)}</div><div className="stat-l">CADR [m³/h]</div><div className="stat-s">等価 {fmt(M.zoneCadr(zp) / p.volume, 2)} 回/h</div></div>
          <div className="stat"><div className="stat-v">{fmt(M.timeToFraction(zp, 0.12) * 60, 0)}</div><div className="stat-l">12%到達 [分]（JEM1467型）</div></div>
          <div className="stat"><div className="stat-v">{fmt(power.total, 0)}</div><div className="stat-l">推定電力 [W]</div><div className="stat-s">送風機中×{nUnits}台 {fmt(power.fan, 0)}W＋EP本体{EP_BODY_W}W{power.ok ? '' : '（限界超過）'}</div></div>
          <div className="stat"><div className="stat-v">{fmt(kwh, 0)}</div><div className="stat-l">年間電力量 [kWh]【予測】</div></div>
          <div className="stat"><div className="stat-v">{fmt(avg, 2)}</div><div className="stat-l">期間平均 [μg/m³]</div><div className="stat-s">{avg > 15 ? 'WHO日平均15超' : avg > 5 ? 'WHO年平均5超' : 'WHO年平均5以下'}</div></div>
        </div>
        {warn.length > 0 && <ul className="warnlist">{warn.map((w) => <li key={w}>⚠ 外挿警告: {w}</li>)}</ul>}
        <ChartBox name="zone_concentration" height={280} caption={<span className="small muted">【計算結果】単室モデル。実測値ではありません</span>}>
          <ResponsiveContainer><LineChart data={series} margin={{ left: -10, right: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--grid)" /><XAxis dataKey="t" type="number" domain={[0, p.hours]} tick={{ fontSize: 11 }} unit="h" /><YAxis tick={{ fontSize: 11 }} /><Tooltip formatter={(v: number) => fmt(v, 2)} /><Legend wrapperStyle={{ fontSize: 12 }} />
            <Line dataKey="c" name="室内濃度" stroke="#0f5b5c" strokeWidth={2} dot={false} isAnimationActive={false} />
            <Line dataKey="cout" name="外気濃度" stroke="#8a6d1e" strokeDasharray="4 3" dot={false} isAnimationActive={false} />
            <ReferenceLine y={5} stroke="#c8553d" strokeDasharray="2 4" label={{ value: 'WHO年5', fontSize: 10, fill: '#c8553d' }} />
            <ReferenceLine y={15} stroke="#c8553d" strokeDasharray="6 4" label={{ value: 'WHO日15', fontSize: 10, fill: '#c8553d' }} />
          </LineChart></ResponsiveContainer>
        </ChartBox>
        <button className="ghost" onClick={() => download('zone_simulation.csv', toCsv(['t_h', 'C_in', 'C_out'], series.map((s) => [s.t, s.c, s.cout])))}>時系列CSV</button>
      </Card>

      <Card title="モデルの前提・仮定（必読）">
        <ul className="small">
          <li>式(2) Q=78.611ΔP^0.828 と η は <b>100〜750 m³/h</b> の単体実測【確認事実】。範囲外は外挿で、画面上で警告します。</li>
          <li>η の中間値は図3の端点間を線形補間【仮定】。粒径帯別端点は図3の読み取り（0.3〜0.5 μm帯 95%→82%）。</li>
          <li>送風機は限界静圧まで定風量、その後は限界の1.6倍で風量ゼロまで直線降下【仮定】。電力は0 Pa→限界で直線【仮定・図6の傾向】。</li>
          <li>バイパスは開口率×0.25 m²のオリフィス（α=0.65）【当事者の設定】。</li>
          <li>EP本体電力26 Wは2018年度の仕様値で、2026年度の機種と同一とは限らない【仮定】。</li>
          <li>単室モデルは瞬時一様拡散。2020・2021年度で一様拡散は実測と0.6倍程度の差を生じた（F-2021-02）。</li>
          <li>住宅以外（学校・病院・産業施設）へは無条件に外挿しないでください。</li>
        </ul>
      </Card>
    </div>
  )
}
