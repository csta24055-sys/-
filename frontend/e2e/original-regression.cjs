// Original の見た目の回帰テスト: 改修前のビルド（BASE_OLD）と改修後のビルド（BASE_NEW）を同じ条件で撮影し、
// ピクセル単位で比較する。進捗バーの中の文字色だけは、コントラスト修正（3.9:1 → 4.9:1）で改修前と違うので、両方を同じ色にそろえてから比べる。
// 設定画面は「デザイン」項目を追加したため比較対象外（その下の既存部分は e2e/mobile.cjs で確認）。
// 後半では、サイドバーの位置・表示だけを変えた Original の本文（.page）も、改修前の既定の画面と比べる。
// DOM の比較では、見た目に影響しない属性（下の IGNORED_ATTRS）を取り除いてから比べる。
//   aria-label / aria-valuemin / aria-valuemax / data-section / data-page / id … 読み上げ名と、レイアウトが使う目印
//   tabindex / role … キーボードで操作できるようにするための属性（アクセシビリティ監査 A11Y-11 ほか）:
//     - 資料ライブラリの一覧の題名（role="link" tabindex="0"）と研究計画の表の行（tabindex="0"）。改修前はマウスでしか選べなかった
//     - 横にはみ出している表の枠（.tablewrap に role="group" tabindex="0"。はみ出していない PC 幅では付かない）
//     フォーカスできない要素をフォーカス可能にするには tabindex 属性が必ず要るので、DOM の文字列を変えない直し方はない。
//     どちらもフォーカスしていない状態の見た目は変わらない（この検査の画素比較で確認する）。
//   BASE_OLD=http://127.0.0.1:47802 BASE_NEW=http://127.0.0.1:47801 OUT=/tmp/x node e2e/original-regression.cjs
const { chromium, devices } = require('playwright');
const fs = require('fs'); const path = require('path');
const OLD = process.env.BASE_OLD, NEW = process.env.BASE_NEW, OUT = process.env.OUT || 'regression';
fs.mkdirSync(OUT, { recursive: true });
const PAGES = ['/', '/library', '/simulator', '/graph', '/plan', '/report', '/learn', '/cloud'];
const IGNORED_ATTRS = 'aria-label|aria-valuemin|aria-valuemax|data-section|data-page|id|tabindex|role';
const DEVS = { desktop: { viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 }, iphone: { ...devices['iPhone 13'], deviceScaleFactor: 1 } };
// 描画が落ち着くまで待つ（グラフは幅を測ってから描くので、固定の待ち時間だと負荷の高いときに棒が出る前に撮ってしまう）
async function settle(page) {
  await page.waitForTimeout(1500);
  let last = -1, same = 0;
  for (let i = 0; i < 40 && same < 6; i++) {
    const n = await page.evaluate(() => document.querySelector('.shell').outerHTML.length + document.querySelectorAll('svg path, svg rect, svg circle').length * 100000);
    same = n === last ? same + 1 : 0; last = n;
    await page.waitForTimeout(350);
  }
}
(async () => {
  const b = await chromium.launch();
  for (const base of [OLD, NEW]) { const c = await b.newContext(); const pg = await c.newPage(); await pg.goto(base + '/'); await pg.waitForSelector('main h1'); await pg.waitForTimeout(1500); await c.close(); } // 初回読み込みの遅さを比較に持ち込まない
  // 判定: 画像はバイト単位（同じ Chromium が書き出すので、画素が同じならファイルも同じ）、DOM は文字列（長さ）で比べる。
  // 負荷が高いとグラフが描かれる前に撮ってしまうことがあるので、違ったら 3 回まで撮り直し、毎回違うときだけ不一致とする
  const rows = []; let bad = 0;
  for (const [dev, opt] of Object.entries(DEVS)) for (const p of PAGES) {
    let img = false, dom = false, tries = 0, pair = [];
    while (tries < 3 && !(img && dom)) {
      tries++; pair = [];
      for (const [tag, base] of [['old', OLD], ['new', NEW]]) {
        const ctx = await b.newContext({ ...opt, reducedMotion: 'reduce' }); const page = await ctx.newPage();
        await page.goto(base + p); await page.waitForSelector('main h1'); await page.addStyleTag({ content: '.bar span{color:#000!important}' }); await settle(page);
        const f = path.join(OUT, `${dev}${p.replace(/\//g, '_')}-${tag}.png`); await page.screenshot({ path: f, fullPage: true });
        pair.push({ dev, p, tag, file: f, dom: await page.evaluate((attrs) => document.querySelector('.shell').outerHTML.replace(new RegExp(` (${attrs})="[^"]*"`, 'g'), '').replace(/<div class="ux-sr"[^>]*>.*?<\/div>/g, '').length, IGNORED_ATTRS) });
        await ctx.close();
      }
      img = fs.readFileSync(pair[0].file).equals(fs.readFileSync(pair[1].file)); dom = pair[0].dom === pair[1].dom;
    }
    rows.push(...pair);
    if (!img || !dom) bad++;
    console.log(img && dom ? 'PASS' : 'FAIL', `[Original/${dev}] ${p}`, img ? '画像一致' : '画像が違う', dom ? 'DOM一致' : 'DOMが違う', tries > 1 ? `（${tries} 回目で確定）` : '');
  }
  // サイドバーだけを変えた Original（位置=右／アイコンのみ／隠す）: サイドバー以外＝本文（main の中の .page）が、
  // 改修前の既定の画面と画素単位で同じこと（サイドバーの設定で、無関係な部品の寸法が変わらない）。
  // 本文の幅が同じになる画面幅で撮る（改修前は幅 1440px のとき本文 1204px）。「隠す」は画面下に固定のメニューが出るので、写り込まないよう隠して撮る
  const KEY = 'aqros-ui-prefs-v1'; let extra = 0, extraBad = 0;
  const pageShot = async (base, p, width, custom, file) => {
    const ctx = await b.newContext({ viewport: { width, height: 900 }, deviceScaleFactor: 1, reducedMotion: 'reduce' });
    if (custom) await ctx.addInitScript(([k, v]) => localStorage.setItem(k, v), [KEY, JSON.stringify({ version: 1, applied: { layout: 'original', custom }, history: [], updatedAt: null })]);
    const page = await ctx.newPage();
    await page.goto(base + p); await page.waitForSelector('main h1');
    await page.addStyleTag({ content: '.bar span{color:#000!important}' + (custom && custom.sidebarMode === 'hidden' ? '.tabbar{visibility:hidden!important}' : '') }); await settle(page);
    const info = await page.evaluate(() => ({ ux: document.documentElement.hasAttribute('data-ux'), main: Math.round(document.querySelector('main').getBoundingClientRect().width) }));
    await page.locator('main .page').screenshot({ path: file });
    await ctx.close();
    return info;
  };
  for (const p of ['/', '/library', '/plan']) for (const [name, custom, width] of [['位置=右', { sidebarPos: 'right' }, 1440], ['アイコンのみ', { sidebarMode: 'icons' }, 1440 - 236 + 64], ['隠す', { sidebarMode: 'hidden' }, 1440 - 236]]) {
    let same = false, tries = 0, o, n;
    const fo = path.join(OUT, `sidebar${p.replace(/\//g, '_')}-old.png`), fn = path.join(OUT, `sidebar${p.replace(/\//g, '_')}-${custom.sidebarPos || custom.sidebarMode}-new.png`);
    while (tries < 3 && !same) { tries++; o = await pageShot(OLD, p, 1440, null, fo); n = await pageShot(NEW, p, width, custom, fn); same = o.main === n.main && !n.ux && fs.readFileSync(fo).equals(fs.readFileSync(fn)); }
    extra++; if (!same) extraBad++;
    console.log(same ? 'PASS' : 'FAIL', `[Original＋サイドバーの${name}/desktop] ${p}`, same ? '本文（.page）の画像が改修前と一致' : `本文の画像が違う（本文の幅 ${o.main}/${n.main}、data-ux ${n.ux ? 'あり' : 'なし'}）`, tries > 1 ? `（${tries} 回目で確定）` : '');
  }
  fs.writeFileSync(path.join(OUT, 'dom.json'), JSON.stringify(rows));
  await b.close();
  console.log(`\n${rows.length / 2 - bad + extra - extraBad}/${rows.length / 2 + extra} identical`);
  process.exit(bad || extraBad ? 1 : 0);
})();
