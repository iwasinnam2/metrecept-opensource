---
name: metrecept-providers
description: >
  Metrecept upstream provider and failover status via MCP metrecept_providers.
  Use when a model call fails or routing looks off.
---

# Metrecept providers

```text
metrecept_providers()
```

Returns provider health and failover state from `GET /v1/providers`.
`ohm_providers` is the same handler.

Requires Metrecept MCP (`OHM_API_KEY`, `OHM_BASE_URL`).
