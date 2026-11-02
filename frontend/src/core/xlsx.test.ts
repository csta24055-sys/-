import { readFileSync } from 'fs'
import { join } from 'path'
import { readXlsx, excelSerialToIso } from './xlsx'

it('reads synthetic workbook (shared strings, numbers, dates, multiple sheets)', async () => {
  const buf = readFileSync(join(__dirname, 'testdata', 'synthetic.xlsx'))
  const sheets = await readXlsx(new Uint8Array(buf))
  expect(sheets.map((s) => s.name)).toEqual(['合成データ', 'EP'])
  const s = sheets[0]
  expect(s.columns).toEqual(['日時', '外気', '室内', 'メモ'])
  expect(s.rows[0][0]).toBe('2025-09-17T00:00:00')
  expect(s.rows[4][2]).toBe(7.5)
  expect(s.rows[0][3]).toBe('a&b<c>')
  expect(sheets[1].rows[1]).toEqual([750, 15.24])
})

it('excel serial date', () => { expect(excelSerialToIso(45917)).toBe('2025-09-17T00:00:00') })
