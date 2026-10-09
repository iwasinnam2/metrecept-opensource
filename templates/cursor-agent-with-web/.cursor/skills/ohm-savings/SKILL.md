---
name: ohm-savings
description: >
  withOhm cache savings snapshot via MCP ohm_savings (dual ledger: provider
  avoided, pipe rent, ROI). Use when checking how much the prompt cache is
  saving — withOhm, ohm, savings, cache.
---

# Ohm savings

Call the Ohm MCP tool `ohm_savings` for a cache savings snapshot.

## Call

```text
ohm_savings()
```

Returns the dual savings ledger from `GET /v1/savings`: estimated provider
$ avoided, pipe rent, roi_ratio (all estimate_only). Pair with `/ohm-usage`.

Requires Ohm MCP attached (`OHM_BASE_URL`, `OHM_API_KEY`). See `docs/CURSOR.md`.
