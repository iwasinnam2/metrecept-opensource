---
name: metrecept-providers
description: >
  Metrecept upstream provider and failover status via MCP metrecept_list_providers.
  Use when a model call fails or routing looks off.
---

# Metrecept providers

```text
metrecept_list_providers()
```

Returns provider health and failover state from `GET /v1/providers`.

Requires Metrecept MCP (`METRECEPT_API_KEY`, `METRECEPT_BASE_URL`).
