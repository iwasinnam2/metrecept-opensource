---
name: metrecept-usage
description: >
  Metrecept usage via MCP metrecept_get_usage (lifetime meters, plan, billing)
  and metrecept_get_usage_history (per-day series, 1-90 days). Use when
  checking meter spend, trends or hit ratio.
---

# Metrecept usage

```text
metrecept_get_usage()
metrecept_get_usage_history(days=30)
```

`metrecept_get_usage` returns cumulative meters, today's values, cache hit
ratio, plan and billing status from `GET /v1/usage`.
`metrecept_get_usage_history` returns one row per UTC day (requests, hit/miss
tokens, fetches, API calls, billed USD) from `GET /v1/usage/history`.
Both are read-only and not billed.

Requires Metrecept MCP (`METRECEPT_API_KEY`, `METRECEPT_BASE_URL`).
