---
name: metrecept-policy
description: >
  Metrecept compliance policy via MCP metrecept_policy (allowed web-fetch purposes and
  limits). Use before a fetch to confirm the purpose is permitted, or when a
  fetch is rejected — Metrecept, policy, compliance, purposes.
---

# Metrecept policy

Call the Metrecept MCP tool `metrecept_policy` for the tenant's compliance policy.

## Call

```text
metrecept_policy()
```

Returns the allowed web-fetch purposes (`public_web_retrieval`,
`business_catalog`, `public_company_info`, `job_listings`) and their limits
from `GET /v1/compliance/policy`. Use it to pick the right `purpose` for
`/metrecept-fetch-web`, or to explain why a fetch was refused.

Requires Metrecept MCP attached (`METRECEPT_BASE_URL`, `METRECEPT_API_KEY`). See `docs/CURSOR.md`.
