---
name: metrecept-receipt
description: >
  Mint a public Metrecept savings receipt via MCP metrecept_receipt (shareable /r/…
  URL, estimate_only). Use when proving cache savings publicly — receipt,
  bounty, share, Metrecept.
---

# Metrecept receipt

Call the Metrecept MCP tool `metrecept_receipt` to mint a public savings receipt from
the tenant's dual savings ledger.

## Call

```text
metrecept_receipt(display_name="")
```

Optional `display_name` labels the public page. Returns a `/r/…` URL (and
badge markdown). Receipts are `estimate_only` — aggregates only, never prompts.

Pair with `/metrecept-savings` first if you need the numbers before minting.
Requires Metrecept MCP attached (`OHM_BASE_URL`, `OHM_API_KEY`). See `docs/CURSOR.md`.
