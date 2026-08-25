---
name: metrecept-receipt
description: >
  Mint a public Metrecept savings receipt via MCP metrecept_receipt (shareable
  /r/… URL, estimate_only). Use when proving cache savings publicly — receipt,
  Metrecept, mcp.
---

# Metrecept receipt

Call `metrecept_receipt(display_name="")` to mint a public savings receipt
from the dual savings ledger. Returns a `/r/…` URL. Receipts are
`estimate_only` — aggregates only, never prompts.

Pair with `metrecept_savings` first if you need the numbers before minting.

Requires Metrecept MCP (`METRECEPT_API_KEY`). Docs: https://metrecept.co.uk/docs/cursor
