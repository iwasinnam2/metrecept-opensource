---
name: metrecept-providers
description: >
  Metrecept upstream provider and failover status via MCP metrecept_list_providers. Use when
  a model call fails, routing looks off, or you want gateway health — Metrecept,
  providers, failover, status.
---

# Metrecept providers

Call the Metrecept MCP tool `metrecept_list_providers` for upstream provider and failover status.

## Call

```text
metrecept_list_providers()
```

Returns provider health and failover state from `GET /v1/providers`. Check
this first when `metrecept_create_chat_completion` errors on a real (non-mock) model.

Requires Metrecept MCP attached (`METRECEPT_BASE_URL`, `METRECEPT_API_KEY`). See `docs/CURSOR.md`.
