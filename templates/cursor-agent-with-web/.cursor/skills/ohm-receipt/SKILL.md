---
name: ohm-receipt
description: >
  Mint a public withOhm savings receipt via MCP ohm_receipt (shareable /r/…
  URL, estimate_only). Use when proving cache savings publicly — receipt,
  bounty, share, withOhm, ohm.
---

# Ohm receipt

Call the Ohm MCP tool `ohm_receipt` to mint a public savings receipt from
the tenant's dual savings ledger.

## Call

```text
ohm_receipt(display_name="")
```

Optional `display_name` labels the public page. Returns a `/r/…` URL (and
badge markdown). Receipts are `estimate_only` — aggregates only, never prompts.

Pair with `/ohm-savings` first if you need the numbers before minting.
Requires Ohm MCP attached (`OHM_BASE_URL`, `OHM_API_KEY`). See `docs/CURSOR.md`.
