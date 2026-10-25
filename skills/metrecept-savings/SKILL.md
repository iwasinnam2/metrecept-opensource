---
name: metrecept-savings
description: >
  Metrecept cache savings snapshot via MCP metrecept_get_savings (dual ledger:
  provider avoided, metered charges, ROI, estimate_only).
---

# Metrecept savings

```text
metrecept_get_savings()
```

Returns estimated provider $ avoided, metered charges, and roi_ratio — all
`estimate_only`.

Requires Metrecept MCP (`METRECEPT_API_KEY`, `METRECEPT_BASE_URL`).
