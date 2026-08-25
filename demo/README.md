# Demo — verify the claims yourself

Everything here runs against the **live, hosted** `https://api.metrecept.co.uk` — no withOhm source code required, and none of it depends on trusting the docs in this repo.

## Prerequisite

One free key, no card: [metrecept.co.uk/billing/intermediate](https://metrecept.co.uk/billing/intermediate) → Checkout ($0 membership) → an `sk-at-…` key. Then:

```bash
export OHM_API_KEY="sk-at-..."
```

Everything below uses `model: "mock"`, which needs no upstream provider key (no BYOK required) — it exists specifically so cache/receipt/tree behavior can be proven without paying an upstream lab.

## Scripts

### `hit_miss_demo.sh` / `hit_miss_demo.ps1`

Sends the same request body twice. Expected output:

```
== Request 1 (expect MISS) ==
x-at-cache: MISS

== Request 2, identical body (expect HIT) ==
x-at-cache: HIT
x-at-billed-usd: 0.000100

== Verifying the signed receipt (zero withOhm code) ==
OK: signature verifies against https://api.metrecept.co.uk/.well-known/http-message-signatures-directory
{
  "admit": "allow",
  "kind": "cache_hit",
  "model": "mock",
  "pipe_usd": 0.0001,
  ...
}
```

Bash:

```bash
./demo/hit_miss_demo.sh
```

PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File demo\hit_miss_demo.ps1
```

### `cache_tree_demo.sh`

Proves named cache trees ([docs/CACHE_TREES.md](../docs/CACHE_TREES.md)) are genuinely isolated: the identical body MISSes on two different fresh trees, then HITs again on the first tree it already visited.

```bash
./demo/cache_tree_demo.sh
```

### `verify_receipt.py`

Standalone verifier — takes any `X-Ohm-Receipt` value and checks it against the public JWKS. Depends only on the `cryptography` package (`pip install cryptography`), nothing else from withOhm.

```bash
python demo/verify_receipt.py "<receipt-jws>" --base https://api.metrecept.co.uk
```

## Why no bundled demo key

A shared, rate-limited proof key exists for the browser widget at [metrecept.co.uk/demo](https://metrecept.co.uk/demo) if you want a zero-setup, no-signup look first. These scripts use your own key on purpose — it's a more honest demo of the real BYOK/metering flow than a shared token would be, and it means the receipt you verify is genuinely yours.
