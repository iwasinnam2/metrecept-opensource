---
name: metrecept-fetch-web
description: >
  Compliant public URL scrape via Metrecept MCP metrecept_fetch_web (markdown
  or JSON). Use for public page content, docs scrape, catalog pages, or
  browse-without-browser — Metrecept, mcp, web-fetch.
---

# Metrecept fetch web

Call `metrecept_fetch_web` for purpose-bound public-page retrieval
(robots-aware, PII-redacted, metered).

## Call

```text
metrecept_fetch_web(
  urls=["https://example.com"],
  purpose="public_web_retrieval",
  query="",
  format="markdown",
  session_id=""
)
```

**Purposes:** `public_web_retrieval`, `business_catalog`, `public_company_info`, `job_listings`.

Optional `session_id` tags the fetch onto a signed session receipt
(`metrecept_session`).

Requires Metrecept MCP (`METRECEPT_API_KEY`). Docs: https://metrecept.co.uk/docs/cursor
