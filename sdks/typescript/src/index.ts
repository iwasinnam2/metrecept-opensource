/**
 * Drop-in OpenAI baseURL helper for Ohm (package path still @at-utility/sdk
 * until the first npm publish renames to @ohm/sdk).
 *
 *   import OpenAI from "openai";
 *   import { openaiArgs } from "@at-utility/sdk";
 *   const client = new OpenAI(openaiArgs("sk-at-dev", LOCAL_BASE_URL, { upstreamApiKey: "sk-..." }));
 */
export type ClientOptions = {
  apiKey: string;
  baseURL?: string;
  defaultHeaders?: Record<string, string>;
};

/** Public API host (live). Use LOCAL_BASE_URL for local development. */
export const DEFAULT_BASE_URL = "https://api.metrecept.co.uk/v1";
export const LOCAL_BASE_URL = "http://127.0.0.1:8081/v1";
export const UPSTREAM_KEY_HEADER = "X-Ohm-Upstream-Key";

export function createClientConfig(
  apiKey: string,
  baseURL: string = DEFAULT_BASE_URL,
  opts?: { upstreamApiKey?: string }
): ClientOptions & { baseURL: string } {
  const cfg: ClientOptions & { baseURL: string } = { apiKey, baseURL };
  if (opts?.upstreamApiKey) {
    cfg.defaultHeaders = { [UPSTREAM_KEY_HEADER]: opts.upstreamApiKey };
  }
  return cfg;
}

/** Returns constructor args for the official OpenAI SDK (BYOK via defaultHeaders). */
export function openaiArgs(
  apiKey: string,
  baseURL: string = DEFAULT_BASE_URL,
  opts?: { upstreamApiKey?: string }
) {
  return createClientConfig(apiKey, baseURL, opts);
}

/** Allowed web_purpose values when fetch_web_context is true (docs/LEGAL.md). */
export const ALLOWED_WEB_PURPOSES = [
  "public_web_retrieval",
  "business_catalog",
  "public_company_info",
  "job_listings",
] as const;

export type WebPurpose = (typeof ALLOWED_WEB_PURPOSES)[number];

/** Extra body fields for compliant public-only web retrieval. */
export function webContextExtra(opts: {
  purpose: WebPurpose;
  urls?: string[];
  query?: string;
  complianceAck?: boolean;
  termsAck?: boolean;
  dpaAck?: boolean;
  cacheControl?: "no_store" | string;
}): Record<string, unknown> {
  if (opts.complianceAck === false) {
    throw new Error("complianceAck must be true for web context");
  }
  if (opts.termsAck === false || opts.dpaAck === false) {
    throw new Error("termsAck and dpaAck must be true (docs/legal/)");
  }
  const body: Record<string, unknown> = {
    fetch_web_context: true,
    web_purpose: opts.purpose,
    web_compliance_ack: true,
    terms_ack: true,
    dpa_ack: true,
  };
  if (opts.urls?.length) body.web_urls = opts.urls;
  if (opts.query) body.web_query = opts.query;
  if (opts.cacheControl) body.cache_control = opts.cacheControl;
  return body;
}

export function compliancePolicyUrl(baseURL: string = DEFAULT_BASE_URL): string {
  const root = baseURL.replace(/\/$/, "");
  return root.endsWith("/v1") ? `${root}/compliance/policy` : `${root}/v1/compliance/policy`;
}

/* ---------------------------------------------------------------------------
 * The receipt as a link. Twin of at_utility_sdk.receipt_link (Python) and
 * at_utility.receipts.verify_url (gateway). Keep PUBLIC_VERIFY_BASE in lockstep.
 * The JWS rides the URL fragment, never the query string, so it is not
 * written to anyone's access log.
 * Design: docs/superpowers/specs/2026-10-09-receipt-link-distribution-design.md
 * ------------------------------------------------------------------------- */

export const PUBLIC_VERIFY_BASE = "https://metrecept.co.uk/verify";
const VERIFY_HEADER_NAME = "x-metrecept-verify";
const RECEIPT_HEADER_NAMES = ["x-metrecept-receipt", "x-ohm-receipt"] as const;

/** Public, no-login verify link for one compact JWS. Throws on a non-JWS. */
export function verifyUrl(jws: string): string {
  const text = (jws || "").trim();
  const parts = text.split(".");
  if (parts.length !== 3 || parts.some((p) => p.length === 0)) {
    throw new Error("verifyUrl expects a compact JWS (three dot-separated parts)");
  }
  return `${PUBLIC_VERIFY_BASE}#${text}`;
}

/** The stamped link, for pasting where a preview will be drawn. Unfurlers
 * fetch without the fragment, so the kind rides in the query and the site
 * serves "Metrecept | 1x Signed Receipt · <kind>" as the preview; the JWS
 * stays after the # and is handed to /verify unchanged. Twin of
 * at_utility.receipts.share_link. Unknown kinds fall back to verifyUrl. */
export const RECEIPT_LINK_BASE = "https://metrecept.co.uk/functions/receipt";
export const LINK_KINDS: ReadonlySet<string> = new Set([
  "session", "cache_hit", "cache_miss", "cache_bypass", "api_call", "custody", "statement", "carve", "disperse",
]);

/** The `kind` the receipt's own payload carries (unverified read), or "". */
export function receiptKind(jws: string): string {
  const parts = (jws || "").trim().split(".");
  if (parts.length !== 3 || parts.some((p) => p.length === 0)) return "";
  try {
    // atob is a global in browsers, Node >= 16, Deno and Bun; no Buffer so
    // this file stays free of Node-only names.
    const b64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const bin: string = atob(b64 + "=".repeat((4 - (b64.length % 4)) % 4));
    const bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    const payload = JSON.parse(new TextDecoder().decode(bytes)) as Record<string, unknown>;
    return String(payload?.kind ?? "");
  } catch {
    return "";
  }
}

export function shareLink(jws: string): string {
  const url = verifyUrl(jws);
  const kind = receiptKind(jws);
  if (LINK_KINDS.has(kind)) return `${RECEIPT_LINK_BASE}?kind=${kind}#${jws.trim()}`;
  return url;
}

function headerGet(headers: Headers | Record<string, unknown>, name: string): string {
  if (typeof Headers !== "undefined" && headers instanceof Headers) {
    return (headers.get(name) || "").trim();
  }
  const rec = headers as Record<string, unknown>;
  for (const key of Object.keys(rec)) {
    if (key.toLowerCase() === name) return String(rec[key] ?? "").trim();
  }
  return "";
}

/** Link from a response's headers: X-Metrecept-Verify if present, else built
 * from either receipt header name. "" when the response carried no receipt. */
export function verifyUrlFromHeaders(headers: Headers | Record<string, string>): string {
  const direct = headerGet(headers, VERIFY_HEADER_NAME);
  if (direct) return direct;
  for (const name of RECEIPT_HEADER_NAMES) {
    const jws = headerGet(headers, name);
    if (jws) {
      try {
        return verifyUrl(jws);
      } catch {
        return "";
      }
    }
  }
  return "";
}

/** One markdown line to append to the artefact the agent produced.
 * `source` is a response's headers or the body of GET /v1/sessions/{id}.
 * Returns "<label>: <url>" or "" when there is nothing to link. */
export function receiptTrailer(
  source: Headers | Record<string, unknown>,
  label = "Receipt",
): string {
  let url = "";
  const isSessionBody =
    !(typeof Headers !== "undefined" && source instanceof Headers) &&
    ("verify_url" in (source as Record<string, unknown>) ||
      "receipt" in (source as Record<string, unknown>));
  if (isSessionBody) {
    const body = source as Record<string, unknown>;
    url = String(body.verify_url ?? "").trim();
    if (!url && body.receipt) {
      try {
        url = verifyUrl(String(body.receipt));
      } catch {
        url = "";
      }
    }
  } else {
    url = verifyUrlFromHeaders(source as Headers | Record<string, string>);
  }
  return url ? `${label}: ${url}` : "";
}

/** The receipt out of a captured SSE stream: the `data:` chunk whose
 * `metrecept.receipt` is a compact JWS. Empty string when none (a stream
 * that did not finish cleanly carries none). */
export function receiptFromSse(text: string): string {
  for (const raw of text.split("\n")) {
    const line = raw.trim();
    if (!line.startsWith("data:")) continue;
    const body = line.slice(5).trim();
    if (!body || body === "[DONE]") continue;
    let obj: unknown;
    try {
      obj = JSON.parse(body);
    } catch {
      continue;
    }
    const tag = (obj as { metrecept?: { receipt?: unknown } } | null)?.metrecept;
    const jws = typeof tag?.receipt === "string" ? tag.receipt.trim() : "";
    if (jws.split(".").length === 3 && jws.split(".").every(Boolean)) return jws;
  }
  return "";
}
