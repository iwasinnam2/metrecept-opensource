---
name: metrecept-savings
description: >
  Metrecept cache savings snapshot via MCP metrecept_savings (dual ledger:
  estimated provider $ avoided vs pipe rent, estimate_only). Use when checking
  replay savings — Metrecept, mcp, savings.
---

# Metrecept savings

Call `metrecept_savings()` for the dual savings ledger from `GET /v1/savings`
(estimated provider $ avoided, pipe rent, roi_ratio — all `estimate_only`).

Requires Metrecept MCP (`METRECEPT_API_KEY`). Docs: https://metrecept.co.uk/docs/cursor
