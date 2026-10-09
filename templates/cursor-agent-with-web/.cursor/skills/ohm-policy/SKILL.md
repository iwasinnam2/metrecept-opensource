---
name: ohm-policy
description: >
  withOhm compliance policy via MCP ohm_policy (allowed web-fetch purposes and
  limits). Use before a fetch to confirm the purpose is permitted, or when a
  fetch is rejected — withOhm, ohm, policy, compliance, purposes.
---

# Ohm policy

Call the Ohm MCP tool `ohm_policy` for the tenant's compliance policy.

## Call

```text
ohm_policy()
```

Returns the allowed web-fetch purposes (`public_web_retrieval`,
`business_catalog`, `public_company_info`, `job_listings`) and their limits
from `GET /v1/compliance/policy`. Use it to pick the right `purpose` for
`/ohm-fetch-web`, or to explain why a fetch was refused.

Requires Ohm MCP attached (`OHM_BASE_URL`, `OHM_API_KEY`). See `docs/CURSOR.md`.
