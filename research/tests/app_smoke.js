// App smoke test (STEP 9 gate). Serves research/app over HTTP, drives it in Chromium and writes
// research/app/SMOKE_TEST_RESULT.json. Run: node research/tests/app_smoke.js [--shots DIR]
const { chromium } = require("playwright");
const { spawn } = require("child_process");
const path = require("path");
const fs = require("fs");

const APP = path.resolve(__dirname, "..", "app");
const PORT = 8765 + Math.floor(Math.random() * 500);
const shotsIdx = process.argv.indexOf("--shots");
const SHOTS = shotsIdx > 0 ? process.argv[shotsIdx + 1] : null;

(async () => {
  const srv = spawn("python3", ["-m", "http.server", String(PORT), "--bind", "127.0.0.1"], { cwd: APP, stdio: "ignore" });
  await new Promise((r) => setTimeout(r, 800));
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1200, height: 900 } });
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  const checks = [];
  const check = (name, ok, detail = "") => checks.push({ name, ok: !!ok, detail: String(detail) });
  const base = `http://127.0.0.1:${PORT}/index.html`;
  try {
    await page.goto(base + "#/");
    await page.waitForSelector(".co");
    check("top page lists 8 companies", (await page.$$(".co")).length === 8);
    if (SHOTS) await page.screenshot({ path: path.join(SHOTS, "home.png"), fullPage: true });

    await page.click('[data-company="C01"]');
    await page.waitForSelector("h1:has-text('三井物産')");
    check("company report renders", (await page.textContent(".panel")).includes("独立総合インテリジェンス研究書"));

    await page.goto(base + "#/c/C01/axes");
    await page.waitForSelector(".ax");
    check("30 axes inside company", (await page.$$(".ax")).length === 30);

    await page.goto(base + "#/c/C01/axis/AXIS_13");
    await page.waitForSelector(".claim");
    const axisText = await page.textContent(".panel");
    check("AXIS_13_T03 gate state is PASS in app", await page.$eval("tbody tr:nth-child(3)", (tr) => tr.textContent.includes("PASS")));
    check("AXIS_13 shows topics, synthesis and claims", axisText.includes("AXIS_13_T03") && axisText.includes("競合仮説") && (await page.$$(".claim")).length >= 10);
    if (SHOTS) await page.screenshot({ path: path.join(SHOTS, "axis13.png"), fullPage: false });

    await page.goto(base + "#/c/C01/id/CLM-C01-0001");
    await page.waitForSelector("pre.code");
    check("claim drill-down to passage", (await page.textContent(".panel")).includes("PSG-C01-0025"));
    await page.goto(base + "#/c/C01/id/SRC-C01-0002");
    await page.waitForSelector("pre.code");
    check("source reverse references", (await page.textContent(".panel")).includes("PSG-C01-0025"));

    await page.goto(base + "#/c/C02");
    await page.waitForSelector("h1:has-text('三菱商事')");
    for (const tab of ["report", "claims", "sources", "relations", "models"]) {
      await page.goto(base + `#/c/C02/${tab}`);
      await page.waitForSelector(".panel");
      const t = await page.textContent("main");
      check(`no C01 data on C02/${tab}`, !/C01-\d{4}/.test(t) && !t.includes("Rhodes"), tab);
    }
    await page.goto(base + "#/c/C02/id/CLM-C01-0001");
    await page.waitForSelector(".panel");
    check("foreign ID cannot be opened from another company", (await page.textContent(".panel")).includes("この会社の台帳にありません"));

    await page.goto(base + "#/network");
    await page.waitForSelector("h1:has-text('会社間ネットワーク')");
    const net = await page.textContent("main");
    check("network page lists verified cross-company edges", net.includes("XREL-0001") && net.includes("VERIFIED_BOTH_SIDES") && net.includes("ONE_SIDED"));
    check("network page shows evidence levels and the company graph", net.includes("BOTH_SIDES+THIRD_PARTY") && (await page.$$("figure svg line")).length > 0);
    if (SHOTS) await page.screenshot({ path: path.join(SHOTS, "network.png"), fullPage: false });
    await page.goto(base + "#/gates");
    await page.waitForSelector("h1:has-text('研究ゲート')");
    check("gates page", (await page.textContent("main")).includes("RESEARCH_STATUS"));

    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(base + "#/c/C01/axis/AXIS_13");
    await page.waitForSelector(".claim");
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    check("no horizontal page scroll at phone width", overflow <= 0, overflow);
    if (SHOTS) await page.screenshot({ path: path.join(SHOTS, "phone.png") });
  } catch (e) {
    check("exception", false, e.message);
  }
  check("no page errors", errors.length === 0, errors.join(" | "));
  await browser.close();
  srv.kill();
  const result = { status: checks.every((c) => c.ok) ? "PASS" : "FAIL", ran_at: new Date().toISOString(), checks };
  fs.writeFileSync(path.join(APP, "SMOKE_TEST_RESULT.json"), JSON.stringify(result, null, 2) + "\n");
  for (const c of checks) console.log(`${c.ok ? "ok  " : "FAIL"} ${c.name}${c.ok ? "" : "  " + c.detail}`);
  console.log(result.status);
  process.exit(result.status === "PASS" ? 0 : 1);
})();
