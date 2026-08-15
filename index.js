/**
 * ESM entry point for chakudya-sdk.
 * Re-exports the core ChakudyaClient/ChakudyaApiError from chakudya-client.js
 * and adds a ready-to-use default instance pointed at the deployed worker,
 * for quick one-liners:
 *
 *   import chakudya from "chakudya-sdk";
 *   const foods = await chakudya.foods.list({ search: "nsima" });
 *
 * For admin (write) calls or a different deployment, construct your own client:
 *
 *   import { ChakudyaClient } from "chakudya-sdk";
 *   const admin = new ChakudyaClient(DEFAULT_BASE_URL, { adminKey: "..." });
 */

// This file is a self-contained ESM build (same logic as chakudya-client.js,
// which is kept separately as a plain <script>/UMD build for non-bundler use —
// see README for which file to use where).

class ChakudyaApiError extends Error {
  constructor(message, status, body) {
    super(message);
    this.name = "ChakudyaApiError";
    this.status = status;
    this.body = body;
  }
}

class ChakudyaClient {
  constructor(baseUrl, opts = {}) {
    if (!baseUrl) throw new Error("ChakudyaClient requires a baseUrl");
    this.baseUrl = baseUrl.replace(/\/$/, "");
    this.adminKey = opts.adminKey || null;
    this.timeoutMs = opts.timeoutMs || 20000;

    this.foods = this._crud("foods", { extra: { lookup: (params) => this._get("/foods/lookup", params) } });
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
  }

  root() {
    return this._get("/");
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

    const headers = { "Content-Type": "application/json" };
    if (this.adminKey) headers.Authorization = `Bearer ${this.adminKey}`;

    try {
      const res = await fetch(this._url(path, params), {
        method,
        headers,
        body: payload !== undefined ? JSON.stringify(payload) : undefined,
        signal: controller.signal,
      });

      const body = await res.json().catch(() => null);

      if (!res.ok || body?.status === "error") {
        throw new ChakudyaApiError(
          body?.message || `Request failed (${res.status})`,
          res.status,
          body
        );
      }

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

const DEFAULT_BASE_URL = "https://chakudya-api.edisontaimu9.workers.dev";

// Default instance for quick reads. Admin/write calls need their own
// `new ChakudyaClient(DEFAULT_BASE_URL, { adminKey })` instance instead.
const chakudya = new ChakudyaClient(DEFAULT_BASE_URL);

export { ChakudyaClient, ChakudyaApiError, chakudya, DEFAULT_BASE_URL };
export default chakudya;
