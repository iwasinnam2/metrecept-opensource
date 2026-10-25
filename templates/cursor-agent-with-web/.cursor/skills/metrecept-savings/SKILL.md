---
name: metrecept-savings
description: >
  Metrecept cache savings snapshot via MCP metrecept_get_savings (dual ledger: provider
  avoided, metered charges, ROI). Use when checking how much the prompt cache is
  saving — Metrecept, savings, cache.
---

# Metrecept savings

Call the Metrecept MCP tool `metrecept_get_savings` for a cache savings snapshot.

## Call

```text
metrecept_get_savings()
```

Returns the dual savings ledger from `GET /v1/savings`: estimated provider
$ avoided, metered charges, roi_ratio (all estimate_only). Pair with `/metrecept-usage`.

Requires Metrecept MCP attached (`METRECEPT_BASE_URL`, `METRECEPT_API_KEY`). See `docs/CURSOR.md`.
