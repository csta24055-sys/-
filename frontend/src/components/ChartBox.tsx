import { ReactNode, useRef } from 'react'

/** チャートを SVG→PNG で保存できるコンテナ */
export default function ChartBox({ children, name, height = 300, caption }: { children: ReactNode; name: string; height?: number; caption?: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null)
  const save = () => {
    const svg = ref.current?.querySelector('svg.recharts-surface') as SVGSVGElement | null
    if (!svg) return
    const clone = svg.cloneNode(true) as SVGSVGElement
    const { width, height: h } = svg.getBoundingClientRect()
    clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg')
    clone.setAttribute('width', String(width)); clone.setAttribute('height', String(h))
    const css = getComputedStyle(document.body)
    const bg = css.getPropertyValue('--card').trim() || '#fff'
    const data = new XMLSerializer().serializeToString(clone).replace(/var\(--([a-z-]+)\)/g, (_, v) => css.getPropertyValue('--' + v).trim() || '#888')
    const img = new Image()
    img.onload = () => {
      const c = document.createElement('canvas'), s = 2
      c.width = width * s; c.height = (h + 24) * s
      const ctx = c.getContext('2d')!
      ctx.scale(s, s); ctx.fillStyle = bg; ctx.fillRect(0, 0, width, h + 24)
      ctx.drawImage(img, 0, 0)
      ctx.fillStyle = '#666'; ctx.font = '10px sans-serif'
      ctx.fillText(`${name} — Air Quality Research OS`, 6, h + 16)
      const a = document.createElement('a'); a.href = c.toDataURL('image/png'); a.download = `${name}.png`; a.click()
    }
    img.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(data)
  }
  return (
    <figure className="chartbox">
      <div ref={ref} className="chart" style={{ height }}>{children}</div>
      <figcaption>{caption}<button className="ghost small" onClick={save}>画像保存</button></figcaption>
    </figure>
  )
}
