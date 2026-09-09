---
name: metrecept-policy
description: >
  Metrecept compliance policy via MCP metrecept_policy (allowed web-fetch
  purposes and limits). Use before a fetch, or when a fetch is rejected.
---

# Metrecept policy

```text
metrecept_policy()
```

Returns allowed web-fetch purposes (`public_web_retrieval`,
`business_catalog`, `public_company_info`, `job_listings`) and limits from
`GET /v1/compliance/policy`. `ohm_policy` is the same handler.

Requires Metrecept MCP (`OHM_API_KEY`, `OHM_BASE_URL`).
