import { createHash } from 'node:crypto'
import { readdirSync, readFileSync, statSync, writeFileSync } from 'node:fs'
import { join, relative } from 'node:path'
import { defineConfig, Plugin } from 'vite'
import react from '@vitejs/plugin-react'

// スマホ単体版:  VITE_STANDALONE=1 VITE_BASE=/<公開パス>/ npm run build -- --outDir dist-mobile
const BASE = process.env.VITE_BASE || '/'

/** ビルド後に sw.js へ版と事前キャッシュ一覧を埋め込む。大きい配布ファイル（deliverables/）は除外 */
function swManifest(): Plugin {
  let outDir = 'dist'
  return {
    name: 'aqros-sw-manifest',
    apply: 'build',
    configResolved(c) { outDir = c.build.outDir },
    closeBundle() {
      const files: string[] = []
      const walk = (d: string) => { for (const f of readdirSync(d)) { const p = join(d, f); if (statSync(p).isDirectory()) walk(p); else files.push(relative(outDir, p).split('\\').join('/')) } }
      walk(outDir)
      const pre = files.filter((f) => f !== 'sw.js' && !f.startsWith('deliverables/') && f !== '404.html' && !f.endsWith('.map'))
      const h = createHash('sha256'); for (const f of pre.sort()) h.update(f).update(readFileSync(join(outDir, f)))
      const ver = h.digest('hex').slice(0, 12)
      const swp = join(outDir, 'sw.js')
      writeFileSync(swp, readFileSync(swp, 'utf8').replace("'__VERSION__'", `'${ver}'`).replace('= __PRECACHE__;', `= ${JSON.stringify(['', ...pre])};`))
    },
  }
}

export default defineConfig({
  base: BASE,
  publicDir: process.env.AQROS_PUBLIC_DIR || 'public',
  plugins: [react(), swManifest()],
  define: { 'import.meta.env.VITE_APP_VERSION': JSON.stringify(process.env.npm_package_version || '1.1.0') },
  server: { host: true, port: 5173, proxy: { '/api': 'http://127.0.0.1:8000' } },
  test: { globals: true, environment: 'node' },
})
