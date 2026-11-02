// 依存ライブラリなしの最小 .xlsx リーダー（オフライン解析用）
// ZIP 中央ディレクトリを読み、DecompressionStream('deflate-raw') で展開、
// workbook / sharedStrings / sheet XML を正規表現で解析する。数式は計算済みの値（<v>）を読む。

interface ZipEntry { name: string; method: number; compSize: number; offset: number }

function readZipEntries(buf: Uint8Array): ZipEntry[] {
  const dv = new DataView(buf.buffer, buf.byteOffset, buf.byteLength)
  let eocd = -1
  for (let i = buf.length - 22; i >= Math.max(0, buf.length - 65557); i--) if (dv.getUint32(i, true) === 0x06054b50) { eocd = i; break }
  if (eocd < 0) throw new Error('ZIP 形式ではありません（.xlsx 以外の可能性）')
  const count = dv.getUint16(eocd + 10, true)
  let p = dv.getUint32(eocd + 16, true)
  const dec = new TextDecoder()
  const out: ZipEntry[] = []
  for (let k = 0; k < count; k++) {
    if (dv.getUint32(p, true) !== 0x02014b50) throw new Error('ZIP 中央ディレクトリが不正です')
    const method = dv.getUint16(p + 10, true), compSize = dv.getUint32(p + 20, true)
    const nLen = dv.getUint16(p + 28, true), eLen = dv.getUint16(p + 30, true), cLen = dv.getUint16(p + 32, true)
    const local = dv.getUint32(p + 42, true)
    const name = dec.decode(buf.subarray(p + 46, p + 46 + nLen))
    const lnLen = dv.getUint16(local + 26, true), leLen = dv.getUint16(local + 28, true)
    out.push({ name, method, compSize, offset: local + 30 + lnLen + leLen })
    p += 46 + nLen + eLen + cLen
  }
  return out
}

async function inflate(data: Uint8Array): Promise<Uint8Array> {
  const ds = new DecompressionStream('deflate-raw')
  const stream = new Blob([data]).stream().pipeThrough(ds)
  return new Uint8Array(await new Response(stream).arrayBuffer())
}

async function readText(buf: Uint8Array, entries: ZipEntry[], name: string): Promise<string | null> {
  const e = entries.find((x) => x.name === name)
  if (!e) return null
  const raw = buf.subarray(e.offset, e.offset + e.compSize)
  const data = e.method === 0 ? raw : e.method === 8 ? await inflate(raw) : null
  if (!data) throw new Error(`未対応の圧縮方式: ${e.method}`)
  return new TextDecoder().decode(data)
}

const unescape = (s: string) => s.replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&apos;/g, "'").replace(/&#(\d+);/g, (_, n) => String.fromCharCode(+n)).replace(/&amp;/g, '&')
const attr = (tag: string, name: string) => { const m = tag.match(new RegExp(`\\b${name}="([^"]*)"`)); return m ? unescape(m[1]) : null }

function colIndex(ref: string) {
  const letters = ref.match(/^[A-Z]+/)?.[0] || 'A'
  let n = 0
  for (const ch of letters) n = n * 26 + (ch.charCodeAt(0) - 64)
  return n - 1
}

/** Excel シリアル値 → ISO 文字列（1900 日付系） */
export function excelSerialToIso(v: number) {
  const ms = Math.round((v - 25569) * 86400 * 1000)
  return new Date(ms).toISOString().slice(0, 19)
}

export interface Sheet { name: string; columns: string[]; rows: unknown[][] }

export async function readXlsx(data: ArrayBuffer | Uint8Array, maxRows = 200_000): Promise<Sheet[]> {
  const buf = data instanceof Uint8Array ? data : new Uint8Array(data)
  const entries = readZipEntries(buf)
  const wb = await readText(buf, entries, 'xl/workbook.xml')
  if (!wb) throw new Error('xl/workbook.xml がありません')
  const rels = (await readText(buf, entries, 'xl/_rels/workbook.xml.rels')) || ''
  const relMap = new Map<string, string>()
  for (const m of rels.matchAll(/<Relationship\b[^>]*>/g)) {
    const id = attr(m[0], 'Id'), tgt = attr(m[0], 'Target')
    if (id && tgt) relMap.set(id, tgt.replace(/^\/?xl\//, '').replace(/^\//, ''))
  }
  const sst: string[] = []
  const ss = await readText(buf, entries, 'xl/sharedStrings.xml')
  if (ss) for (const m of ss.matchAll(/<si>([\s\S]*?)<\/si>/g)) sst.push(unescape([...m[1].matchAll(/<t[^>]*>([\s\S]*?)<\/t>/g)].map((t) => t[1]).join('')))
  const sheets: Sheet[] = []
  for (const m of wb.matchAll(/<sheet\b[^>]*\/?>/g)) {
    const name = attr(m[0], 'name') || 'Sheet'
    const rid = attr(m[0], 'r:id')
    const target = (rid && relMap.get(rid)) || `worksheets/sheet${sheets.length + 1}.xml`
    const xml = await readText(buf, entries, 'xl/' + target)
    if (!xml) continue
    const grid: unknown[][] = []
    for (const rm of xml.matchAll(/<row\b[^>]*>([\s\S]*?)<\/row>/g)) {
      if (grid.length > maxRows) break
      const row: unknown[] = []
      for (const cm of rm[1].matchAll(/<c\b([^>]*?)(?:\/>|>([\s\S]*?)<\/c>)/g)) {
        const tag = cm[1], body = cm[2] || ''
        const ref = attr('<c ' + tag, 'r') || ''
        const t = attr('<c ' + tag, 't')
        const v = body.match(/<v>([\s\S]*?)<\/v>/)?.[1]
        let val: unknown = null
        if (t === 's' && v !== undefined) val = sst[+v] ?? ''
        else if (t === 'inlineStr') val = unescape([...body.matchAll(/<t[^>]*>([\s\S]*?)<\/t>/g)].map((x) => x[1]).join(''))
        else if (t === 'str' && v !== undefined) val = unescape(v)
        else if (t === 'b' && v !== undefined) val = v === '1'
        else if (v !== undefined) val = Number(v)
        row[ref ? colIndex(ref) : row.length] = val
      }
      grid.push(row)
    }
    const nonEmpty = grid.filter((r) => r.some((x) => x !== null && x !== undefined && x !== ''))
    if (!nonEmpty.length) continue
    const width = Math.max(...nonEmpty.map((r) => r.length))
    const [head, ...body] = nonEmpty.map((r) => Array.from({ length: width }, (_, i) => (r[i] === undefined ? null : r[i])))
    const columns = head.map((h, i) => (h === null || h === '' ? `列${i + 1}` : String(h)))
    // 時刻列らしい列のシリアル値を ISO 文字列へ
    columns.forEach((c, i) => {
      if (/日時|時刻|日付|time|date/i.test(c)) body.forEach((r) => { if (typeof r[i] === 'number' && (r[i] as number) > 20000 && (r[i] as number) < 80000) r[i] = excelSerialToIso(r[i] as number) })
    })
    sheets.push({ name, columns, rows: body })
  }
  return sheets
}
