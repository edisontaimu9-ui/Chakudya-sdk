#!/usr/bin/env python3
"""Regenerate chakudya-client.js, index.js, index.cjs and index.d.ts from the
API's openapi.yaml (+ a few routes the spec does not list yet).

Usage:  python3 scripts/generate.py ../chakudya-api/openapi.yaml
"""
import json, re, sys, pathlib, yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
spec_path = sys.argv[1] if len(sys.argv) > 1 else "../chakudya-api/openapi.yaml"
spec = yaml.safe_load(open(spec_path))
VERSION = spec["info"]["version"]

# Receivers called by database triggers / webhooks, not by API clients.
SKIP = {"/rag/webhook", "/hooks/signup", "/hooks/ml-lab"}
# Routes the Worker serves that openapi.yaml does not list yet.
EXTRA = [
    ("POST", "/surveillance/records"), ("GET", "/surveillance/reference"),
    ("GET", "/surveillance/summary"), ("GET", "/surveillance/hotspots"),
    ("GET", "/surveillance/trends"), ("GET", "/surveillance/export"),
    ("GET", "/surveillance/training-export"), ("GET", "/surveillance/alerts"),
    ("GET", "/surveillance/insights"),
    ("POST", "/openmrs/push"), ("GET", "/openmrs/status"),
]
# Methods written by hand in the client (kept as-is, generator skips them).
HAND = {
    "foods": {"list", "get", "create", "update", "remove", "replace", "lookup", "autocomplete", "categories"},
    "exchange": {"list", "get", "create", "update", "remove", "replace"},
    "renal": {"list", "get", "create", "update", "remove", "replace"},
    "formulas": {"list", "get", "create", "update", "remove", "replace"},
    "packaged": {"list", "submit", "scan", "update", "remove"},
    "rag": {"retrieve", "ingest"},
    "memory": {"write", "recall", "consolidate"},
}

def camel(s):
    s = s.replace("$", "")
    parts = [p for p in re.split(r"[-_]", s) if p]
    out = parts[0][0].lower() + parts[0][1:]
    return out + "".join(p[0].upper() + p[1:] for p in parts[1:])

def cap(s):
    return s[0].upper() + s[1:]

routes = []
for path, item in spec["paths"].items():
    if path == "/" or path in SKIP:
        continue
    for m in ("get", "post", "put", "patch", "delete"):
        if m in item:
            routes.append((m.upper(), path))
for r in EXTRA:
    if r not in routes:
        routes.append(r)

VERB = {"GET": "list", "POST": "create", "PUT": "replace", "PATCH": "update", "DELETE": "remove"}
entries = []  # dict(ns, base, method, path, params)
for method, path in routes:
    segs = [s for s in path.strip("/").split("/") if s]
    ns = camel(segs[0])
    rest = segs[1:]
    params = re.findall(r"\{(\w+)\}", path)
    named = [camel(s) for s in rest if not s.startswith("{")]
    if named:
        base = named[0] + "".join(cap(n) for n in named[1:])
    else:
        base = None
    entries.append(dict(ns=ns, base=base, method=method, path=path, params=params, rest=rest))

def default_name(e):
    if e["base"] is None:
        if e["method"] == "GET" and e["params"]:
            return "get"
        return VERB[e["method"]]
    return e["base"]

# group by (ns, name), resolve collisions
from collections import defaultdict
groups = defaultdict(list)
for e in entries:
    e["name"] = default_name(e)
    groups[(e["ns"], e["name"])].append(e)
for (ns, name), members in groups.items():
    if len(members) > 1:
        for e in members:
            core = e["base"] if e["base"] else ""
            n = e["method"].lower() + (cap(core) if core else "")
            if e["params"]:
                n += "By" + "".join(cap(camel(p)) for p in e["params"])
            e["name"] = n
seen = set()
for e in entries:
    k = (e["ns"], e["name"])
    assert k not in seen, f"name collision: {k} {e['method']} {e['path']}"
    seen.add(k)

table = defaultdict(dict)
for e in entries:
    if e["name"] in HAND.get(e["ns"], set()):
        continue
    table[e["ns"]][e["name"]] = f"{e['method']} {e['path']}"
table = {k: dict(sorted(v.items())) for k, v in sorted(table.items())}
total = sum(len(v) for v in table.values()) + sum(len(v) for v in HAND.values())
routes_json = json.dumps(table, indent=2)

CORE = r'''class ChakudyaApiError extends Error {
  constructor(message, status, body) {
    super(message);
    this.name = "ChakudyaApiError";
    this.status = status;
    this.body = body;
  }
}

// Every other API route, generated from openapi.yaml by scripts/generate.py.
// "METHOD /path/{param}" — path params become positional arguments.
const GENERATED_ROUTES = __ROUTES__;

class ChakudyaClient {
  constructor(baseUrl, opts = {}) {
    if (!baseUrl) throw new Error("ChakudyaClient requires a baseUrl");
    this.baseUrl = baseUrl.replace(/\/$/, "");
    // Every route except GET / and GET /health needs an API key (consumer,
    // reviewer or admin). `adminKey` is kept as an alias of `apiKey`.
    this.apiKey = opts.apiKey || opts.adminKey || null;
    this.adminKey = this.apiKey;
    // Access token from a developer login — only /developer/keys uses it.
    this.loginToken = opts.loginToken || null;
    this.timeoutMs = opts.timeoutMs || 20000;

    this.foods = this._crud("foods", {
      extra: {
        lookup: (params) => this._get("/foods/lookup", params),
        autocomplete: (q, { maxResults = 4 } = {}) => this._get("/foods/autocomplete", { q, max_results: maxResults }),
        categories: () => this._get("/foods/categories"),
      },
    });
    this.exchange = this._crud("exchange");
    this.renal = this._crud("renal");
    this.formulas = this._crud("formulas");

    this.packaged = {
      list: (params) => this._get("/packaged", params),
      submit: (payload) => this._post("/packaged/submit", payload),
      scan: (images) => this._post("/packaged/scan", { images }),
      update: (id, payload) => this._patch(`/packaged/${id}`, payload),
      remove: (id) => this._delete(`/packaged/${id}`),
    };

    this.rag = {
      retrieve: (query, { context = "both", topK = 5 } = {}) =>
        this._post("/rag/retrieve", { query, context, top_k: topK }),
      ingest: (payload) => this._post("/rag/ingest", payload), // admin
    };

    this.memory = {
      write: (sessionId, content, { kind = "fact", patientLabel } = {}) =>
        this._post("/memory/write", {
          session_id: sessionId,
          content,
          kind,
          patient_label: patientLabel,
        }),
      recall: (sessionId, query, { topK = 5 } = {}) =>
        this._post("/memory/recall", { session_id: sessionId, query, top_k: topK }),
      consolidate: (sessionId) => this._post("/memory/consolidate", { session_id: sessionId }), // admin
    };

    // Generated resources. Hand-written methods above always win.
    for (const [ns, methods] of Object.entries(GENERATED_ROUTES)) {
      const target = (this[ns] = this[ns] || {});
      for (const [name, route] of Object.entries(methods)) {
        if (!(name in target)) target[name] = this._route(route);
      }
    }
    this.pediatric = this.paediatric; // the API accepts both spellings
  }

  root() {
    return this._get("/");
  }

  // Build a method from "METHOD /path/{a}/{b}". Arguments:
  //   (...pathParams, paramsOrPayload, extraQuery?)
  // GET/DELETE: the next argument is the query string.
  // POST/PUT/PATCH: the next argument is the JSON body (or FormData),
  // and an optional one after it is the query string.
  _route(route) {
    const [method, path] = route.split(" ");
    const n = (path.match(/\{\w+\}/g) || []).length;
    const hasBody = method === "POST" || method === "PUT" || method === "PATCH";
    return (...args) => {
      let i = 0;
      const url = path.replace(/\{\w+\}/g, () => {
        const v = args[i++];
        if (v === undefined || v === null || v === "") throw new Error(`${method} ${path}: missing path parameter`);
        return encodeURIComponent(v);
      });
      const data = args[n];
      const query = args[n + 1];
      return hasBody
        ? this._request(method, url, { payload: data, params: query })
        : this._request(method, url, { params: data });
    };
  }

  _crud(resource, { supportsPut = true, extra = {} } = {}) {
    const base = `/${resource}`;
    const api = {
      list: (params) => this._get(base, params),
      get: (id) => this._get(`${base}/${id}`),
      create: (payload) => this._post(base, payload),
      update: (id, payload) => this._patch(`${base}/${id}`, payload),
      remove: (id) => this._delete(`${base}/${id}`),
      ...extra,
    };
    if (supportsPut) {
      api.replace = (id, payload) => this._put(`${base}/${id}`, payload);
    }
    return api;
  }

  _url(path, params) {
    const url = new URL(this.baseUrl + path);
    if (params) {
      for (const [k, v] of Object.entries(params)) {
        if (v !== undefined && v !== null && v !== "") url.searchParams.set(k, v);
      }
    }
    return url.toString();
  }

  async _request(method, path, { params, payload } = {}) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), this.timeoutMs);

    const isForm = typeof FormData !== "undefined" && payload instanceof FormData;
    const headers = {};
    if (!isForm) headers["Content-Type"] = "application/json";
    const token = path.startsWith("/developer") && this.loginToken ? this.loginToken : this.apiKey;
    if (token) headers.Authorization = `Bearer ${token}`;

    try {
      const res = await fetch(this._url(path, params), {
        method,
        headers,
        body: payload === undefined ? undefined : isForm ? payload : JSON.stringify(payload),
        signal: controller.signal,
      });

      // JSON for almost everything; CSV/text exports are returned as a string.
      const ctype = res.headers.get("content-type") || "";
      const raw = await res.text();
      let body = null;
      if (ctype.includes("json") || /^\s*[\[{]/.test(raw)) {
        try { body = JSON.parse(raw); } catch (_) { body = null; }
      }

      if (!res.ok || body?.status === "error") {
        throw new ChakudyaApiError(
          body?.message || body?.error || `Request failed (${res.status})`,
          res.status,
          body ?? raw
        );
      }
      if (body === null) return raw;
      return body?.data !== undefined ? body.data : body;
    } finally {
      clearTimeout(timeout);
    }
  }

  _get(path, params) {
    return this._request("GET", path, { params });
  }
  _post(path, payload) {
    return this._request("POST", path, { payload });
  }
  _put(path, payload) {
    return this._request("PUT", path, { payload });
  }
  _patch(path, payload) {
    return this._request("PATCH", path, { payload });
  }
  _delete(path) {
    return this._request("DELETE", path);
  }
}
'''.replace("__ROUTES__", routes_json)

DEFAULTS = '''
const DEFAULT_BASE_URL = "https://api.chakudya.xyz";

// Default instance. Most routes need an API key, so for real use build your
// own: `new ChakudyaClient(DEFAULT_BASE_URL, { apiKey })`.
const chakudya = new ChakudyaClient(DEFAULT_BASE_URL);
'''

def banner(title, usage):
    return f"/**\n * {title}\n * Generated by scripts/generate.py from chakudya-api openapi {VERSION} — do not edit by hand.\n{usage} */\n\n"

client = banner("Chakudya Nutrition Registry (CNR) — browser/UMD build (window.ChakudyaClient)",
                " *   <script src=\"chakudya-client.js\"></script>\n *   const cnr = new ChakudyaClient(baseUrl, { apiKey });\n") + CORE + '''
if (typeof module !== "undefined" && module.exports) {
  module.exports = { ChakudyaClient, ChakudyaApiError };
}
if (typeof window !== "undefined") {
  window.ChakudyaClient = ChakudyaClient;
  window.ChakudyaApiError = ChakudyaApiError;
}
'''
esm = banner("ESM entry point for chakudya-sdk",
             " *   import chakudya, { ChakudyaClient } from \"chakudya-sdk\";\n") + CORE + DEFAULTS + '''
export { ChakudyaClient, ChakudyaApiError, chakudya, DEFAULT_BASE_URL };
export default chakudya;
'''
cjs = banner("CommonJS entry point for chakudya-sdk",
             " *   const { chakudya, ChakudyaClient } = require(\"chakudya-sdk\");\n") + CORE + DEFAULTS + '''
module.exports = { ChakudyaClient, ChakudyaApiError, chakudya, DEFAULT_BASE_URL };
module.exports.default = chakudya;
'''
(ROOT / "chakudya-client.js").write_text(client)
(ROOT / "index.js").write_text(esm)
(ROOT / "index.cjs").write_text(cjs)

# ---- index.d.ts
def gen_iface(ns):
    lines = []
    for name, route in table[ns].items():
        method, path = route.split(" ")
        n = len(re.findall(r"\{(\w+)\}", path))
        args = [f"{p}: string | number" for p in re.findall(r"\{(\w+)\}", path)]
        if method in ("POST", "PUT", "PATCH"):
            args += ["body?: any", "query?: Record<string, any>"]
        else:
            args += ["params?: Record<string, any>"]
        lines.append(f"  /** {route} */\n  {name}({', '.join(args)}): Promise<any>;")
    return "\n".join(lines)

hand_ns = set(HAND)
dts = f'''// Generated by scripts/generate.py from chakudya-api openapi {VERSION} — do not edit by hand.
export declare const DEFAULT_BASE_URL: string;

export interface ChakudyaClientOptions {{
  /** API key (consumer, reviewer or admin). Required on every route except GET / and GET /health. */
  apiKey?: string;
  /** Alias of apiKey (kept for older code). */
  adminKey?: string;
  /** Developer-login access token — only used by /developer/keys. */
  loginToken?: string;
  timeoutMs?: number;
}}

export declare class ChakudyaApiError extends Error {{
  status?: number;
  body?: unknown;
  constructor(message: string, status?: number, body?: unknown);
}}

export interface CrudResource<T = any> {{
  list(params?: Record<string, any>): Promise<T[]>;
  get(id: string | number): Promise<T>;
  create(payload: Partial<T>): Promise<T>;
  update(id: string | number, payload: Partial<T>): Promise<T>;
  remove(id: string | number): Promise<any>;
  replace?(id: string | number, payload: Partial<T>): Promise<T>;
}}

export interface FoodCategory {{
  id: string;
  name: string;
  description: string | null;
}}

export interface FoodsResource extends CrudResource {{
  lookup(params: {{ q?: string; barcode?: string; [key: string]: any }}): Promise<any>;
  autocomplete(q: string, options?: {{ maxResults?: number }}): Promise<string[]>;
  categories(): Promise<FoodCategory[]>;
{gen_iface("foods") if "foods" in table else ""}
}}

export interface PackagedResource {{
  list(params?: Record<string, any>): Promise<any>;
  submit(payload: Record<string, any>): Promise<any>;
  scan(images: string[]): Promise<any>;
  update(id: string | number, payload: Record<string, any>): Promise<any>;
  remove(id: string | number): Promise<any>;
{gen_iface("packaged") if "packaged" in table else ""}
}}

export interface RagResource {{
  retrieve(
    query: string,
    options?: {{ context?: "both" | "oasis" | "thanzi"; topK?: number }}
  ): Promise<any>;
  ingest(payload: {{
    content: string;
    source: string;
    context?: "both" | "oasis" | "thanzi";
    metadata?: Record<string, any>;
  }}): Promise<any>;
{gen_iface("rag") if "rag" in table else ""}
}}

export interface MemoryResource {{
  write(
    sessionId: string,
    content: string,
    options?: {{ kind?: string; patientLabel?: string }}
  ): Promise<any>;
  recall(
    sessionId: string,
    query: string,
    options?: {{ topK?: number }}
  ): Promise<any>;
  consolidate(sessionId: string): Promise<any>;
{gen_iface("memory") if "memory" in table else ""}
}}

'''
for ns in ("exchange", "renal", "formulas"):
    extra = gen_iface(ns) if ns in table else ""
    dts += f"export interface {cap(ns)}Resource extends CrudResource {{\n{extra}\n}}\n\n"

others = [ns for ns in table if ns not in hand_ns]
for ns in others:
    dts += f"export interface {cap(ns)}Resource {{\n{gen_iface(ns)}\n}}\n\n"

props = "\n".join(f"  {ns}: {cap(ns)}Resource;" for ns in others)
dts += f'''export declare class ChakudyaClient {{
  baseUrl: string;
  apiKey: string | null;
  /** Alias of apiKey. */
  adminKey: string | null;
  loginToken: string | null;
  timeoutMs: number;

  foods: FoodsResource;
  exchange: ExchangeResource;
  renal: RenalResource;
  formulas: FormulasResource;
  packaged: PackagedResource;
  rag: RagResource;
  memory: MemoryResource;
{props}
  /** Same object as paediatric (the API accepts both spellings). */
  pediatric: PaediatricResource;

  constructor(baseUrl: string, options?: ChakudyaClientOptions);
  root(): Promise<any>;
}}

declare const chakudya: ChakudyaClient;
export {{ chakudya }};
export default chakudya;
'''
(ROOT / "index.d.ts").write_text(dts)
print(f"API {VERSION}: {total} methods across {len(table)+0} generated namespaces (+hand-written)")
(ROOT / "scripts" / "methods.json").write_text(json.dumps({"hand_written": {k: sorted(v) for k, v in HAND.items()}, "generated": table}, indent=2))
