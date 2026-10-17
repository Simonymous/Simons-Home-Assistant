// Stufe 3: Rendertest. Oeffnet jede View und jedes Bubble-Card-Pop-up in einem
// unsichtbaren Browser (iPhone/WebKit wie die HA-App, dazu Desktop/Chromium),
// sucht Fehlerkarten und JS-Fehler und legt Screenshots unter .screenshots/ ab
// (vorheriger Lauf unter .screenshots/previous/). Screenshots zeigen echte Daten
// und bleiben lokal (gitignored).
//
// Aufruf ueber run.sh, das HA_URL, HA_TOKEN und MANIFEST setzt.

import { chromium, devices, webkit } from "playwright";
import { existsSync, mkdirSync, readFileSync, renameSync, rmSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const HA_URL = process.env.HA_URL.replace(/\/$/, "");
const TOKEN = process.env.HA_TOKEN;
const manifest = JSON.parse(readFileSync(process.env.MANIFEST, "utf8"));
const OUT = join(dirname(fileURLToPath(import.meta.url)), ".screenshots");
const only = process.env.DEVICES?.split(",");
// Fehler aus eingebetteten Fremdseiten (iframe-Karten) betreffen das Dashboard nicht.
const IGNORE = [/embed\.windy\.com/];

const DEVICES = [
  { name: "iphone", browser: webkit, options: { ...devices["iPhone 15 Pro"], colorScheme: "light" } },
  { name: "iphone-dark", browser: webkit, options: { ...devices["iPhone 15 Pro"], colorScheme: "dark" } },
  { name: "desktop", browser: chromium, options: { viewport: { width: 1440, height: 1000 } } },
].filter((d) => !only || only.includes(d.name));

// Fehlerkarten liegen tief in Shadow-DOMs; alle Wurzeln durchlaufen.
function scanPage() {
  const errors = [];
  const warnings = [];
  const text = (n) => (n.shadowRoot?.textContent || n.textContent || "").replace(/\s+/g, " ").trim();
  const walk = (n) => {
    if (n.nodeType === 1) {
      const tag = n.tagName.toLowerCase();
      if (tag === "hui-error-card") errors.push(text(n).slice(0, 200));
      if (tag === "hui-warning") warnings.push(text(n).slice(0, 200));
    }
    if (n.shadowRoot) walk(n.shadowRoot);
    for (const c of n.children || []) walk(c);
  };
  walk(document.documentElement);
  return { errors, warnings };
}

const settle = (page, ms = 3500) => page.waitForTimeout(ms);

async function run(device) {
  const dir = join(OUT, device.name);
  if (existsSync(dir)) {
    const prev = join(OUT, "previous", device.name);
    rmSync(prev, { recursive: true, force: true });
    mkdirSync(dirname(prev), { recursive: true });
    renameSync(dir, prev);
  }
  mkdirSync(dir, { recursive: true });

  const browser = await device.browser.launch();
  const context = await browser.newContext({ ...device.options, locale: "de-DE" });
  await context.addInitScript(
    ([url, token]) => {
      localStorage.setItem("hassTokens", JSON.stringify({
        hassUrl: url, clientId: url + "/", access_token: token, token_type: "Bearer",
        refresh_token: "", expires_in: 1e9, expires: Date.now() + 1e12,
      }));
    },
    [HA_URL, TOKEN],
  );
  const page = await context.newPage();
  const consoleErrors = [];
  page.on("pageerror", (e) => consoleErrors.push(`pageerror: ${e.message}`));
  page.on("console", (m) => m.type() === "error" && consoleErrors.push(m.text()));

  const base = `${HA_URL}/${manifest.url_path}`;
  await page.goto(`${base}/${manifest.views[0].path}`);
  await page.waitForFunction(() => document.querySelector("home-assistant")?.hass?.connected,
    null, { timeout: 30000 });
  // YAML-Dashboards cached HA serverseitig: frisch von der Platte laden lassen.
  await page.evaluate((url_path) => document.querySelector("home-assistant").hass
    .callWS({ type: "lovelace/config", url_path, force: true }), manifest.url_path);

  const results = [];
  const check = async (label, file) => {
    let found = await page.evaluate(scanPage);
    if (found.errors.length) {
      // Karten laden teils verzoegert (v. a. Pop-ups): einmal nachpruefen
      await settle(page, 2500);
      found = await page.evaluate(scanPage);
    }
    await page.screenshot({ path: join(dir, `${file}.png`), fullPage: true });
    const js = consoleErrors.splice(0);
    results.push({ label, ...found, js });
  };

  for (const view of manifest.views) {
    await page.goto(`${base}/${view.path}`);
    await settle(page);
    await check(view.title, view.path);
    for (const hash of view.hashes) {
      await page.evaluate((h) => { location.hash = h; }, hash);
      await settle(page, 1500);
      await check(`${view.title} ${hash}`, `${view.path}__${hash.slice(1)}`);
      await page.evaluate(() => history.back());
      await settle(page, 800);
    }
  }
  await browser.close();
  return results;
}

let failed = 0;
for (const device of DEVICES) {
  console.log(`== ${device.name}`);
  for (const r of await run(device)) {
    // button-card meldet kaputte JS-Templates nur in der Konsole
    const js = r.js.filter((m) => !IGNORE.some((re) => re.test(m)));
    const jsErrors = js.filter((m) => /pageerror|ButtonCard|TemplateError|is not defined/i.test(m));
    const jsOther = js.filter((m) => !jsErrors.includes(m));
    const bad = r.errors.length + jsErrors.length;
    failed += bad;
    console.log(`${bad ? "FEHLER" : "ok    "} ${r.label}`);
    r.errors.forEach((e) => console.log(`         Fehlerkarte: ${e}`));
    jsErrors.forEach((e) => console.log(`         JS: ${e.slice(0, 400)}`));
    r.warnings.forEach((w) => console.log(`         Warnung: ${w}`));
    jsOther.forEach((e) => console.log(`         Konsole: ${e.slice(0, 160)}`));
  }
}
console.log(`Screenshots: ${OUT}`);
console.log(failed ? `${failed} Fehler` : "OK");
process.exit(failed ? 1 : 0);
