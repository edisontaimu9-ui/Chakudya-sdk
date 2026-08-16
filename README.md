# chakudya-sdk

Zero-dependency JS client for the **Chakudya Nutrition Registry (CNR)**
Cloudflare Worker API:

```
https://chakudya-api.edisontaimu9.workers.dev
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
  const cnr = new ChakudyaClient("https://chakudya-api.edisontaimu9.workers.dev");

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
const admin = new ChakudyaClient(chakudya.baseUrl, { adminKey: "chakudya_admin_xxx" });
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

Mirrors every route in the Worker:

| Resource | Methods |
|---|---|
| `foods` | `list`, `get`, `create`*, `update`*, `remove`*, `replace`*, `lookup`, `autocomplete`, `categories` |
| `exchange` | `list`, `get`, `create`*, `update`*, `remove`*, `replace`* |
| `renal` | `list`, `get`, `create`*, `update`*, `remove`*, `replace`* |
| `formulas` | `list`, `get`, `create`*, `update`*, `remove`*, `replace`* |
| `packaged` | `list`, `submit`, `scan`, `update`*, `remove`* |
| `rag` | `retrieve(query, opts)`, `ingest(payload)`* |
| `memory` | `write(sessionId, content, opts)`, `recall(sessionId, query, opts)`, `consolidate(sessionId)`* |

`*` = admin route, requires `adminKey`.

`foods.autocomplete(q, { maxResults })` and `foods.categories()` wrap
FatSecret's Premier-exclusive endpoints — they return `503` if the
deployed Worker doesn't have a Premier/Premier Free FatSecret key
configured:

```js
const suggestions = await chakudya.foods.autocomplete("chic", { maxResults: 5 });
// -> ["chicken", "chicken breast", "chicken salad", ...]

const categories = await chakudya.foods.categories();
// -> [{ id: "1", name: "Beans & Legumes", description: "..." }, ...]
```

See the [chakudya-api README](https://github.com/edisontaimu9-ui/chakudya-api)
for full request/response shapes, rate limits, and caching behavior — this
package is just the client, not the API reference.

## Constructor options

```ts
new ChakudyaClient(baseUrl: string, options?: {
  adminKey?: string;   // bearer token for admin (write) routes
  timeoutMs?: number;  // default 20000 — request is aborted after this
})
```

## Notes

- This SDK never stores or requires the Worker's backend secrets
  (`SUPABASE_KEY`, `COHERE_API_KEY`, etc.) — only `adminKey`
  (`ADMIN_API_KEY`) if you need write access.
- Keep `adminKey` server-side or in a trusted environment. Shipping it in
  client-side browser code exposes it to anyone who opens dev tools.
