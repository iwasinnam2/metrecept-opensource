# Signed cache-hit receipts

Every cache HIT can carry a **signed receipt** — a detached proof of what the pipe did, verifiable by anyone against a public key. This is "replay and audit value" as an artifact instead of a sentence: don't trust the savings copy, verify the receipt.

## What a receipt is

A compact JWS (EdDSA / Ed25519) in the `X-Ohm-Receipt` response header of every served cache hit — served from either the control plane or the edge (the edge itself never holds the signing key; receipts are minted by the control plane and handed to the edge to attach).

Payload fields:

| Field | Meaning |
|-------|---------|
| `v`, `kind` | Schema version, `cache_hit` |
| `iat`, `region`, `plane` | When and where the hit was served (`python` / `rust-edge`) |
| `model` | Requested model id |
| `tokens_replayed` | Upstream tokens that were **not** re-bought |
| `pipe_usd` | What Metrecept billed for the hit (the meter event, 6 dp) |
| `request_sha256` | The exact-replay identity — digest of the canonicalized request |
| `tenant_sha256` | Truncated tenant fingerprint (self-verifiable, not identifying) |
| `admit` | `allow` on a served HIT |
| `meter_event_id` | Digest-scoped meter identifier fragment bound to this release |
| `rl_epoch` | UTC calendar day of mint (`YYYYMMDD`) |

## Verify one from a cold start

```bash
# 1. Capture a receipt (send the same request twice; the second is the HIT)
curl -si https://api.metrecept.co.uk/v1/chat/completions \
  -H "Authorization: Bearer $OHM_API_KEY" -H "Content-Type: application/json" \
  -d '{"model":"mock","messages":[{"role":"user","content":"receipt demo"}]}' \
  | grep -i x-ohm-receipt

# 2. Verify it against the public key directory — no Metrecept code required
python demo/verify_receipt.py "<X-Ohm-Receipt value>" --base https://api.metrecept.co.uk
```

The verifier ([`demo/verify_receipt.py`](../demo/verify_receipt.py)) fetches `/.well-known/http-message-signatures-directory`, resolves the signing key by the JWS `kid` (RFC 7638 JWK thumbprint), and checks the Ed25519 signature itself using only the `cryptography` package — it imports nothing from Metrecept. A forged or altered receipt fails to verify; so does a receipt signed by a key that isn't in the published directory.

## Co-signed receipts: the caller's half

A receipt on its own is the pipe's count. If the caller sends its own Ed25519 signature over the request body as the `X-Metrecept-Attest` header (compact JWS, `typ: metrecept-attest+jws`, public key in the header `jwk`, `kid` = RFC 7638 thumbprint, payload `{"v":1,"body_sha256":<hex>,"iat":<unix>}`), the pipe verifies it against the body it received (a mismatch is a 400, never a silently unbound receipt) and the receipt gains three fields:

| Field | Meaning |
|-------|---------|
| `attest_sha256` | SHA-256 of the attestation JWS exactly as sent |
| `attest_kid` | The caller's key thumbprint |
| `body_sha256` | SHA-256 over canonical JSON of the body (keys sorted, no whitespace, UTF-8) |

Two keys, one record: the caller asserted this body, the pipe counted this crossing, and the two agree on the bytes. Neither can mint it alone. A stranger with receipt + attestation + the published pipe key checks both signatures, the kid/thumbprint, and the two digests:

```bash
python demo/verify_receipt.py "<receipt-jws>" --attest "<X-Metrecept-Attest-jws>"
# or, with the body too, against the pair minted on the hosted pipe in demo/fixtures/cosigned/
python demo/attest_demo.py check --receipt demo/fixtures/cosigned/receipt.jws \
  --attest demo/fixtures/cosigned/attest.jws --body demo/fixtures/cosigned/body.json
```

`attest_kid` names a key, not a person; who holds it is the caller's business, out of band. Session receipts aggregate crossings and carry no body, so they never carry these fields. See [`demo/attest_demo.py`](../demo/attest_demo.py) for keygen / sign / send / check.

## Operator-side, for context

The receipt signing key is intentionally distinct from Metrecept's separate Web Bot Auth signing key (used for compliant crawl identification, see [COMPLIANCE.md](COMPLIANCE.md)), so either can rotate independently; both public keys are served from the same well-known directory. The private key material never leaves the control plane — the edge only ever receives an already-minted receipt to attach to a response.

## Why this exists

Post-LLM, prose is free and therefore trustless. Receipts move the core claim — *exact-replay hits that cost zero upstream tokens* — from marketing into cryptography: the meter event and the replay identity are signed at the moment of service, and a customer's auditor can replay the verification without believing anyone. See also `GET /v1/public/honesty` on the live API for the full list of published limits and the surfaces that prove them.
