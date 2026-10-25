---
name: metrecept-policy
description: >
  Metrecept compliance policy via MCP metrecept_get_fetch_policy (allowed web-fetch
  purposes and limits). Use before a fetch, or when a fetch is rejected.
---

# Metrecept policy

```text
metrecept_get_fetch_policy()
```

Returns allowed web-fetch purposes (`public_web_retrieval`,
`business_catalog`, `public_company_info`, `job_listings`) and limits from
`GET /v1/compliance/policy`.

Requires Metrecept MCP (`METRECEPT_API_KEY`, `METRECEPT_BASE_URL`).
