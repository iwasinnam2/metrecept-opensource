# Compliant public-web fetch

withOhm's optional web-fetch feature is designed as a **public-web retrieval** utility — not a lead harvester, account-access tool, or person-dossier engine. This is enforced in code (gate logic runs before a fetched byte ever reaches a model), not just asserted in a terms page.

> Not legal advice. Operators and tenants remain responsible for their own use cases and jurisdictions.

## Operating principle

| Allowed | Prohibited |
|---------|------------|
| Public `http`/`https` pages a normal browser can open without login | Login walls, credentials in URLs, session/token reuse, private/app hosts |
| AI-search style retrieval with citations | Contact/lead harvesting, people-search dossiers |
| Business catalogs, public company pages, public job ads | Biometrics / face matching from scraped photos |
| PII redaction + robots.txt respect (default on) | Continuing after access revocation or a technical block |

## Purpose matrix

Every fetch is purpose-bound. Allowed `web_purpose` values:

- `public_web_retrieval` — general public pages for answers (cited, minimized)
- `business_catalog` — e-commerce / product catalogs
- `public_company_info` — public company pages (org-level; minimizes people fields)
- `job_listings` — public job ads, no CVs

Blocked outright, regardless of purpose: social-profile bulk scraping / lead lists, login-gated or private account data, biometrics/faceprints, PECR-style cold-outreach list building.

## Request contract

```json
{
  "model": "mock",
  "messages": [{"role": "user", "content": "Summarize this product page"}],
  "fetch_web_context": true,
  "web_urls": ["https://example.com/product/1"],
  "web_purpose": "business_catalog",
  "web_compliance_ack": true,
  "terms_ack": true,
  "dpa_ack": true,
  "cache_control": "no_store"
}
```

`cache_control: "no_store"` skips the Redis write entirely, for confidential prompts. Inspect the live, machine-readable policy any client can check before sending a request:

```bash
curl -s https://api.metrecept.co.uk/v1/compliance/policy
```

## What's enforced before a model ever sees fetched text

- **robots.txt** — respected by default, fail-closed on fetch errors
- **PII redaction** — emails/phones/IDs redacted from fetched markdown before it's injected as context
- **SSRF / URL gate** — scheme checks, credential-in-URL rejection, private-IP and DNS-rebind-after-resolve denial, login/account path rejection
- **Excerpt caps** — 4,000 chars per source, 12,000 total injected context — short quotations, not bulk republication
- **No training corpus** — cache contents (and fetched web context) are hard-denied as a training-data export path, at any tier

## Verified crawling identity

Fetches identify themselves with a dedicated user agent and, when configured, RFC 9421 HTTP Message Signatures (`Signature`, `Signature-Input`, `Signature-Agent`) so origins can verify the crawler instead of treating it as anonymous. The public signing-key directory is the same one used for [receipts](RECEIPTS.md):

```bash
curl -s https://api.metrecept.co.uk/.well-known/http-message-signatures-directory
```

Two origin responses are honored, not worked around:

- **HTTP 402** (pay-per-crawl) — treated as the origin's licensing decision; withOhm does not auto-pay, and the refusal is surfaced to the caller.
- **HTTP 401/403** — access revocation is honored: no retries, no block evasion.

## Why this is architecture, not just policy

The purpose gate, robots check, PII redaction, and SSRF protections all run on the durable Pipeline System (see [ARCHITECTURE.md](ARCHITECTURE.md)) — the same layer that owns billing truth — *before* a request is canonicalized, digested, or sent to a model. A misconfigured or malicious fetch request cannot bypass compliance by racing the cache or the upstream call; there is no path from "client asked for a URL" to "model sees text" that skips the gate.
