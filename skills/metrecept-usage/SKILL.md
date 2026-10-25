---
name: metrecept-usage
description: >
  Metrecept usage snapshot via MCP metrecept_usage (cache hits, fetches,
  web attach). Use when checking meter spend or hit ratio.
---

# Metrecept usage

```text
metrecept_usage()
```

Returns cache hit ratio, fetch counts, and web attach rate from
`GET /v1/usage`. `metrecept_usage` is the same handler.

Requires Metrecept MCP (`METRECEPT_API_KEY`, `METRECEPT_BASE_URL`).
