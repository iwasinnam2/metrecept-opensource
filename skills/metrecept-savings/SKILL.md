---
name: metrecept-savings
description: >
  Metrecept cache savings snapshot via MCP metrecept_savings (dual ledger:
  provider avoided, metered charges, ROI, estimate_only).
---

# Metrecept savings

```text
metrecept_savings()
```

Returns estimated provider $ avoided, metered charges, and roi_ratio — all
`estimate_only`. `metrecept_savings` is the same handler.

Requires Metrecept MCP (`OHM_API_KEY`, `OHM_BASE_URL`).
