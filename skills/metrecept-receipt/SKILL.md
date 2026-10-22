---
name: metrecept-receipt
description: >
  Mint a public Metrecept savings receipt via MCP metrecept_receipt
  (shareable /r/… URL, estimate_only). Use when proving cache savings publicly.
---

# Metrecept savings receipt

Call `metrecept_receipt(display_name="")` to mint a public **aggregate**
savings receipt from the dual savings ledger. Returns a `/r/…` URL.
Receipts are `estimate_only` — aggregates only, never prompts.

This is not the cryptographic per-call JWS minted on every call, HIT or MISS
(`X-Ohm-Receipt` / `X-Metrecept-Receipt`). Pair with `metrecept_savings`
if you need the numbers before minting.

Requires Metrecept MCP (`OHM_API_KEY`). Docs: https://metrecept.co.uk/docs/cursor
