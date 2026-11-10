// Read-only smoke test: calls every GET route that has no path parameter.
// Usage:  CHAKUDYA_KEY="cnr_..." node scripts/smoke.mjs
import fs from "fs";
import { ChakudyaClient, DEFAULT_BASE_URL } from "../index.js";

const key = process.env.CHAKUDYA_KEY;
if (!key) { console.error("Set CHAKUDYA_KEY first."); process.exit(1); }

const methods = JSON.parse(fs.readFileSync(new URL("./methods.json", import.meta.url), "utf8"));
const c = new ChakudyaClient(DEFAULT_BASE_URL, { apiKey: key });

// Hand-written methods plus calls that need valid parameters.
const jobs = [
  ["foods.list", () => c.foods.list()],
  ["foods.categories", () => c.foods.categories()],
  ["foods.search", () => c.foods.search({ q: "maize" })],
  ["exchange.list", () => c.exchange.list()],
  ["renal.list", () => c.renal.list()],
  ["formulas.list", () => c.formulas.list()],
  ["packaged.list", () => c.packaged.list()],
  ["dri.list", () => c.dri.list({ life_stage: "female_19_30" })],
  ["growth.assess", () => c.growth.assess({ sex: "female", age_months: 12, weight_kg: 9 })],
];
const sampled = new Set(jobs.map(([n]) => n));

// Every generated GET route without a {param}.
for (const [ns, ms] of Object.entries(methods.generated)) {
  for (const [name, route] of Object.entries(ms)) {
    if (!route.startsWith("GET ") || route.includes("{")) continue;
    const label = `${ns}.${name}`;
    if (sampled.has(label)) continue;
    jobs.push([label, () => c[ns][name](), route]);
  }
}

const tally = { ok: 0, needsParams: 0, auth: 0, skipped: 0, bad: 0 };
for (const [label, fn, route] of jobs) {
  try {
    await fn();
    tally.ok++;
  } catch (e) {
    const s = e.status;
    if (s === 400 || s === 422) tally.needsParams++;
    else if (s === 401 || s === 403) { tally.auth++; console.log("🔒", label, s); }
    else if ((s === 502 || s === 503) && /openmrs/i.test(`${label} ${route || ""}`)) {
      tally.skipped++; console.log("⏭️ ", label, s, "(OpenMRS not reachable, integration check)");
    } else { tally.bad++; console.log("❌", label, s ?? "", String(e.message).slice(0, 70)); }
  }
  await new Promise((r) => setTimeout(r, 150));
}
console.log(`\n${jobs.length} routes: ✅ ${tally.ok} | ⚠️ needs params ${tally.needsParams} | 🔒 auth ${tally.auth} | ⏭️ skipped ${tally.skipped} | ❌ ${tally.bad}`);
process.exit(tally.bad ? 1 : 0);
