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

### `n8n_retry_hit_receipt_template.json`

Creator Hub workflow: **Prove an n8n AI retry was a cache HIT**. Core n8n nodes only. Click **Test once** (pinned `mock` payload): Call 1 MISS, identical Call 2 HIT, Ed25519 receipt checked in a Code node against the public JWKS. Import the JSON in the n8n editor, map HTTP Header Auth (`Authorization: Bearer sk-at-...`), then look at the canvas before submitting to creators.n8n.io — this file is generated from `build_n8n_retry_hit_template.py`; a live editor pass is still the Hub layout gate.

The older lead-triage template stays in this folder until the Hub accepts this one.

### `verify_receipt.py`

Standalone verifier — takes any `X-Ohm-Receipt` value and checks it against the public JWKS. Depends only on the `cryptography` package (`pip install cryptography`), nothing else from withOhm.

```bash
python demo/verify_receipt.py "<receipt-jws>" --base https://api.metrecept.co.uk
```

A `https://metrecept.co.uk/verify#<jws>` or `.../functions/receipt?kind=...#<jws>` link works in place of the bare JWS. For a co-signed receipt add `--attest "<X-Metrecept-Attest-jws>"` to check the caller's half too.

### `attest_demo.py` — co-sign a crossing (no account for three of four steps)

A receipt signed by the pipe is one party's count. An **attestation** is the caller's own Ed25519 signature over the body it sent, carried as the `X-Metrecept-Attest` request header; the pipe verifies it against the body it received and binds its hash into the receipt (`attest_sha256`, `attest_kid`, `body_sha256`). Two keys, one record. A stranger checks both.

`keygen`, `sign` and `check` need no account. Only `send` talks to the pipe (`METRECEPT_API_KEY` in the environment).

```bash
# a real co-signed pair minted on the hosted pipe is in demo/fixtures/cosigned/
python demo/attest_demo.py check \
  --receipt demo/fixtures/cosigned/receipt.jws \
  --attest  demo/fixtures/cosigned/attest.jws \
  --body    demo/fixtures/cosigned/body.json
# OK: signature verifies against .../.well-known/http-message-signatures-directory
# OK (co-sign): caller key <kid> signed body_sha256 <hex> and the pipe bound that attestation into this receipt
# OK (body): body.json canonicalises to body_sha256 <hex>; this is the body both keys signed

# your own key and body
python demo/attest_demo.py keygen --out attest.seed
python demo/attest_demo.py sign --key attest.seed --body body.json      # prints the header value
python demo/attest_demo.py send --key attest.seed --body body.json --out-dir run1   # needs METRECEPT_API_KEY
python demo/attest_demo.py check --receipt run1/receipt.jws --attest run1/attest.jws --body run1/body.json
```

`send` also takes `--session <id>` to plant your own id as `X-Metrecept-Session`; the session receipt from `GET /v1/sessions/<id>` then carries `session_sha256 = sha256(<id>)`, never the raw id.

The signing rule, so it can be redone in any language: `body_sha256` is SHA-256 over canonical JSON of the body (keys sorted, no whitespace, UTF-8, non-ASCII unescaped); JWS header `{"alg":"EdDSA","typ":"metrecept-attest+jws","kid":<RFC 7638 thumbprint>,"jwk":{"kty":"OKP","crv":"Ed25519","x":...}}`; payload `{"v":1,"body_sha256":<hex>,"iat":<unix>}`. A key, not a person: who holds the attest key is the caller's business, out of band.

### `verify_clock.py`

Standard library only. Checks a receipt, or an outside digest, against the public Merkle clock from a cold start: derives the leaf (`sha256(ed25519_sig)` for a receipt; `sha256("metrecept-clock-external-leaf/v1" || digest)` for a digest sealed via `POST /v1/clock/leaf`), recomputes the RFC 6962 path to the hour's root, and prints the hour's commitment. Exit 2 while the hour is still open, because an open hour is Metrecept's log, not a clock.

```bash
python demo/verify_clock.py --receipt "<receipt-jws>" --base https://api.metrecept.co.uk
python demo/verify_clock.py --digest <64 hex> --base https://api.metrecept.co.uk
```

An external leaf proves only the hour. Metrecept did not see, sign or vouch for what the digest names.

## Why no bundled demo key

A shared, rate-limited proof key exists for the browser widget at [metrecept.co.uk/demo](https://metrecept.co.uk/demo) if you want a zero-setup, no-signup look first. These scripts use your own key on purpose — it's a more honest demo of the real BYOK/metering flow than a shared token would be, and it means the receipt you verify is genuinely yours.
