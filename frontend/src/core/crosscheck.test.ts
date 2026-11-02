// Python（backend/aqros）と TypeScript 実装の数値一致テスト
import ref from './python_reference.json'
import * as M from './models'
import * as S from './stats'

const close = (a: number, b: number, rel = 1e-6) => expect(Math.abs(a - b)).toBeLessThanOrEqual(rel * Math.max(1, Math.abs(b)))

describe('bypass parallel-flow model', () => {
  for (const c of ref.bypass) {
    const [r, n, s, b, law] = c.args as [number, number, string, string, M.EpLaw]
    it(`r=${r} n=${n} ${s} ${law}`, () => {
      const t = M.solveBypass(r, n, s, b, law)
      close(t.dp, c.res.dp, 1e-6); close(t.cadr, c.res.cadr, 1e-6); close(t.power_total, c.res.power_total, 1e-6)
      expect(t.within_fan_limit).toBe(c.res.within_fan_limit)
    })
  }
})

describe('zone model', () => {
  const z = ref.zone[0]
  const p = z.params as M.ZoneParams
  it('steady / io / t12', () => { close(M.zoneSteadyState(p), z.steady); close(M.zoneIoRatio(p), z.io); close(M.timeToFraction(p, 0.12), z.t12) })
  it('time series', () => { const ts = M.zoneTimeSeries(p, 6, 0.05); close(ts[ts.length - 1].c, z.series_last, 1e-9); close(ts[10].c, z.series_10, 1e-9) })
})

it('deposition', () => { for (const [d, b] of ref.deposition) close(M.depositionCoefficient(d), b, 1e-9) })

describe('stats', () => {
  const [x, y] = ref.stats.xy
  it('origin regression', () => { const r = S.regressionThroughOrigin(x, y); close(r.k, ref.stats.origin.k, 1e-9); close(r.r2, ref.stats.origin.r2, 1e-9); close(r.ci_low, ref.stats.origin.ci_low, 1e-9) })
  it('power law', () => { const r = S.powerLawFit(x, y.map((v) => Math.abs(v) + 0.1)); close(r.a, ref.stats.power.a, 1e-6); close(r.b, ref.stats.power.b, 1e-6) })
  it('linear', () => { const r = S.linearRegression(x, y); close(r.slope, ref.stats.linear.slope, 1e-9) })
  it('quality report flags outlier', () => {
    const q = S.qualityReport([[1], [1.1], [0.9], [1.05], [null], [50], [1.0], [0.95]], ['v'], ['v'])[0]
    expect(q.missing).toBe(1); expect(q.outliers).toBe(1)
  })
})
