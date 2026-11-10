# chakudya-sdk

Home: <https://sdk.chakudya.xyz>

Zero-dependency JS client for the **Chakudya Nutrition Registry (CNR)**
Cloudflare Worker API:

```
https://api.chakudya.xyz
```

Extracted from the [chakudya-api](https://github.com/edisontaimu9-ui/chakudya-api)
repo into its own package so Oasis CNST, Thanzi, DietitianOS, the portfolio
site — or any other project — can depend on it without pulling in the Worker
backend code.

## Which file to use

- **Browser `<script>` tag / no bundler** → `chakudya-client.js` (UMD-style,
  attaches `window.ChakudyaClient`)
- **Modern bundler / ESM (`import`)** → `index.js`
- **Node `require()` / CommonJS** → `index.cjs`
- **TypeScript** → types are picked up automatically from `index.d.ts` when
  you import from `"chakudya-sdk"`

All three JS builds expose the identical `ChakudyaClient` API — pick whichever
matches your project's module system.

## Install

Copy the files you need into your project (no build step required), or
publish this repo to npm under your own name and `npm install` it.

## Quick start

### Browser, no bundler

```html
<script src="chakudya-client.js"></script>
<script>
  const cnr = new ChakudyaClient("https://api.chakudya.xyz");

  cnr.foods.list({ search: "nsima", limit: 10 }).then(console.log);
  cnr.rag.retrieve("high potassium foods", { topK: 5 }).then(console.log);
</script>
```

### ESM

```js
import chakudya, { ChakudyaClient } from "chakudya-sdk";

// Default instance, already pointed at the deployed worker:
const foods = await chakudya.foods.list({ search: "nsima", limit: 10 });

// Admin (write) calls need their own instance with an admin key:
const admin = new ChakudyaClient(chakudya.baseUrl, { apiKey: "chakudya_admin_xxx" });
await admin.foods.create({ food_name: "Matemba", category: "fish" });
```

### CommonJS

```js
const { chakudya, ChakudyaClient } = require("chakudya-sdk");

chakudya.rag.retrieve("high potassium foods", { topK: 5 }).then(console.log);
```

Every method resolves to the parsed `data` payload on success, or throws a
`ChakudyaApiError` (`.status`, `.body`) on a non-2xx response — no manual
`status === "success"` checks needed.

## API surface

Covers every client-facing route of the Worker (API v1.83.0): 318 methods
in 64 resources. Each method is `client.<resource>.<method>(...)`:

- Path params are positional: `client.foods.getConvertById(5, { amount: 1, unit: "cup" })`
- GET/DELETE: the next argument is the query string: `client.dri.list({ life_stage: "adult" })`
- POST/PUT/PATCH: the next argument is the JSON body (or `FormData`), then an optional query object: `client.rag.ask({ query: "..." })`
- CSV exports resolve to a string, everything else to the parsed `data`.

The full list of method names is in [`scripts/methods.json`](scripts/methods.json)
and in `index.d.ts` (each method is commented with its `METHOD /path`).
When two routes would get the same name, the verb is added
(`admin.getKeys`, `admin.postKeys`, `foods.getConvertById`).

Hand-written helpers (unchanged): `foods.list/get/create/update/remove/replace/lookup/autocomplete/categories`,
`exchange|renal|formulas` CRUD, `packaged.list/submit/scan/update/remove`,
`rag.retrieve(query, opts)`, `rag.ingest(payload)`,
`memory.write/recall/consolidate`.

| Resource | Methods |
|---|---|
| `activityEnergy` | 3 |
| `admin` | 10 |
| `batch` | 1 |
| `biochemistry` | 4 |
| `bmiForAge` | 3 |
| `bmiForAgeUnder5` | 3 |
| `burns` | 11 |
| `carbCounting` | 7 |
| `carePlan` | 2 |
| `criticalCare` | 11 |
| `dataQuality` | 2 |
| `developer` | 3 |
| `diabetes` | 11 |
| `dietaryAssessment` | 2 |
| `dri` | 3 |
| `drugInteractions` | 8 |
| `energy` | 3 |
| `enteralNutrition` | 2 |
| `epidemiology` | 3 |
| `exchange` | 7 |
| `export` | 3 |
| `favorites` | 3 |
| `fentonPreterm` | 7 |
| `fhir` | 24 |
| `foods` | 19 |
| `formulas` | 7 |
| `glycaemicIndex` | 7 |
| `growth` | 1 |
| `hcForAge` | 3 |
| `hcVelocity` | 3 |
| `health` | 1 |
| `history` | 2 |
| `ingredients` | 1 |
| `lengthHeightForAge` | 3 |
| `lengthVelocity` | 3 |
| `log` | 5 |
| `longitudinal` | 3 |
| `malnutrition` | 2 |
| `mealPlan` | 2 |
| `meals` | 1 |
| `measures` | 2 |
| `memory` | 5 |
| `micronutrients` | 3 |
| `ml` | 3 |
| `muac` | 1 |
| `muacForAge` | 3 |
| `nfpe` | 6 |
| `openmrs` | 2 |
| `packaged` | 9 |
| `paediatric` | 9 |
| `pregnancy` | 5 |
| `rag` | 8 |
| `recipes` | 1 |
| `refeeding` | 5 |
| `renal` | 7 |
| `renalNutrition` | 8 |
| `research` | 4 |
| `sports` | 8 |
| `stressFactors` | 5 |
| `surveillance` | 9 |
| `weightForAge` | 3 |
| `weightForLengthHeight` | 3 |
| `weightManagement` | 7 |
| `weightVelocity` | 3 |

Not wrapped on purpose: the webhook receivers `/rag/webhook`, `/hooks/signup`
and `/hooks/ml-lab` (called by database triggers, not by clients).
`pediatric` is the same object as `paediatric`.

`foods.autocomplete(q, { maxResults })` and `foods.categories()` wrap
FatSecret's Premier-exclusive endpoints — they return `503` if the
deployed Worker doesn't have a Premier/Premier Free FatSecret key
configured.

### Regenerating after an API change

```bash
python3 scripts/generate.py ../chakudya-api/openapi.yaml
```

This rewrites `chakudya-client.js`, `index.js`, `index.cjs` and `index.d.ts`
(and `scripts/methods.json`). Needs `pyyaml`. Routes the spec doesn't list
yet (surveillance, openmrs) live in the `EXTRA` list in the script.

See the [chakudya-api README](https://github.com/edisontaimu9-ui/chakudya-api)
for full request/response shapes, rate limits, and caching behavior — this
package is just the client, not the API reference.

## Constructor options

```ts
new ChakudyaClient(baseUrl: string, options?: {
  apiKey?: string;     // bearer API key — needed on every route except GET / and GET /health
  adminKey?: string;   // alias of apiKey (older code keeps working)
  loginToken?: string; // developer-login access token, used only by /developer/keys
  timeoutMs?: number;  // default 20000 — request is aborted after this
})
```

## Notes

- This SDK never stores or requires the Worker's backend secrets
  (`SUPABASE_KEY`, `COHERE_API_KEY`, etc.) — only an API key
  (consumer, reviewer or admin) that you pass in.
- Keep admin keys server-side or in a trusted environment. Shipping it in
  client-side browser code exposes it to anyone who opens dev tools.
