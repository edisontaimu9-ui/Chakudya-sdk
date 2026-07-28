/**
 * paychangu-sdk (CommonJS build)
 * Same API as index.js, exported via module.exports for require() consumers.
 */

const DEFAULT_BASE_URL = "https://paychangu-payment-gateway.edisontaimu9.workers.dev";

class PayChanguError extends Error {
  constructor(message, { status, details } = {}) {
    super(message);
    this.name = "PayChanguError";
    this.status = status;
    this.details = details;
  }
}

class PayChanguClient {
  constructor(options = {}) {
    this.baseUrl = (options.baseUrl || DEFAULT_BASE_URL).replace(/\/+$/, "");
    this._fetch = options.fetchImpl || globalThis.fetch;
    if (!this._fetch) {
      throw new Error(
        "No fetch implementation found. Pass { fetchImpl } or run on Node 18+/a browser."
      );
    }
  }

  async initiate({ amount, currency = "MWK", firstName, lastName, email, message, returnUrl } = {}) {
    if (!amount || Number(amount) <= 0) {
      throw new PayChanguError("A positive amount is required");
    }

    const res = await this._fetch(`${this.baseUrl}/api/support/initiate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        amount,
        currency,
        first_name: firstName,
        last_name: lastName,
        email,
        message,
        return_url: returnUrl,
      }),
    });

    const data = await this._safeJson(res);

    if (!res.ok || data.status !== "success") {
      throw new PayChanguError(data.message || "Failed to initiate transaction", {
        status: res.status,
        details: data.details,
      });
    }

    return data;
  }

  async payAndRedirect(params) {
    if (typeof window === "undefined") {
      throw new Error("payAndRedirect() only works in a browser environment");
    }
    const { checkout_url } = await this.initiate(params);
    window.location.href = checkout_url;
  }

  async verify(txRef) {
    if (!txRef) {
      throw new PayChanguError("tx_ref is required");
    }

    const res = await this._fetch(
      `${this.baseUrl}/api/support/verify/${encodeURIComponent(txRef)}`
    );
    const data = await this._safeJson(res);

    if (!res.ok) {
      throw new PayChanguError(data.message || "Failed to verify transaction", {
        status: res.status,
        details: data,
      });
    }

    return data;
  }

  async waitForCompletion(txRef, { intervalMs = 2000, timeoutMs = 60000 } = {}) {
    const start = Date.now();
    const finalStates = new Set(["success", "failed"]);

    while (true) {
      const data = await this.verify(txRef);
      const status = data?.data?.status || data?.status;
      if (finalStates.has(status)) return data;
      if (Date.now() - start > timeoutMs) {
        throw new PayChanguError("Timed out waiting for transaction to complete", {
          details: data,
        });
      }
      await new Promise((r) => setTimeout(r, intervalMs));
    }
  }

  async _safeJson(res) {
    try {
      return await res.json();
    } catch {
      return {};
    }
  }
}

const paychangu = new PayChanguClient();

module.exports = { PayChanguClient, PayChanguError, paychangu, DEFAULT_BASE_URL };
module.exports.default = paychangu;
