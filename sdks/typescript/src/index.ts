/**
 * Drop-in OpenAI baseURL helper for Metrecept (package path still
 * @at-utility/sdk until a coordinated package-name cutover).
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
