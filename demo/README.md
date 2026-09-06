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

### `otel_receipt_span.py`

Verifies a receipt (same algorithm as `verify_receipt.py`, duplicated on purpose — each script here stands alone) and emits it as an OpenTelemetry span, with standard `gen_ai.*` attributes used only where they genuinely apply and everything Metrecept-specific under a vendor-prefixed `metrecept.*` namespace. This is the reference scenario for the distribution design in [`docs/superpowers/specs/2026-09-05-otel-genai-finops-distribution-design.md`](../../docs/superpowers/specs/2026-09-05-otel-genai-finops-distribution-design.md) — the point being demonstrated is that any OTel-instrumented client can capture a signed receipt as span evidence with no Metrecept code in the emitting process.

```bash
pip install opentelemetry-sdk cryptography
python demo/otel_receipt_span.py "<receipt-jws>" --base https://api.metrecept.co.uk

# Export to a real OTLP collector / backend (LangFuse, Phoenix, Langtrace, ...):
pip install opentelemetry-exporter-otlp-proto-http
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318 python demo/otel_receipt_span.py "<receipt-jws>"
```

### `n8n_lead_triage_receipt_template.json`

An importable n8n workflow template — not a script, a canvas. Webhook
receives a lead → an `HTTP Request` node scores it through Metrecept
(`model: "mock"`, no upstream key needed) with `fullResponse` on so the
cache/billed/receipt response headers are readable → a second
`HTTP Request` node pulls the account's live `/v1/usage` snapshot → both
get logged to a Google Sheet next to the model's answer. Every node is a
core n8n node (`Webhook`, `HTTP Request`, `Set`, `Google Sheets`) — no
community node install required to try it. Sticky notes on the canvas
explain setup end to end; the workflow deliberately logs the raw receipt
string rather than verifying it in-canvas — pair it with
`verify_receipt.py` above for the actual cryptographic check.

```
n8n → Import from File → n8n_lead_triage_receipt_template.json
```

## Why no bundled demo key

A shared, rate-limited proof key exists for the browser widget at [metrecept.co.uk/demo](https://metrecept.co.uk/demo) if you want a zero-setup, no-signup look first. These scripts use your own key on purpose — it's a more honest demo of the real BYOK/metering flow than a shared token would be, and it means the receipt you verify is genuinely yours.
