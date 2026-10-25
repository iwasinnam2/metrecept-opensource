---
name: metrecept-fetch-web
description: >
  Compliant public URL scrape via Metrecept MCP metrecept_fetch_web
  (markdown or JSON). Use when the agent needs public URL / docs context
  without hand-browsing — Metrecept, web-fetch, compliance.
---

# Metrecept fetch web

Call `metrecept_fetch_web` for compliant public-page retrieval. `metrecept_fetch_web`
is the same handler.

```text
metrecept_fetch_web(
  urls=["https://example.com"],
  purpose="public_web_retrieval",
  query="",
  format="markdown",   # or "json"
  session_id=""
)
```

**Purposes:** `public_web_retrieval`, `business_catalog`, `public_company_info`, `job_listings`.

Requires Metrecept MCP (`METRECEPT_API_KEY`, `METRECEPT_BASE_URL`). Stdio: `metrecept-mcp` from
the GitHub install in the repo README. Docs: https://metrecept.co.uk/docs/cursor
