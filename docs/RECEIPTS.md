# Signed cache-hit receipts

Every cache HIT carries a **signed receipt** — a detached proof of what the pipe did, verifiable by anyone against a public key. This is the black-box claim as an artifact instead of a sentence: don't trust the copy, verify the receipt.

## What a receipt is

A compact JWS (EdDSA / Ed25519) in the `X-Ohm-Receipt` and `X-Metrecept-Receipt` response headers of every served cache hit — served from either the control plane or the edge (the edge itself never holds the signing key; receipts are minted by the control plane and handed to the edge to attach). Both headers carry the same JWS.

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

# 2. Verify it against the public key directory — no Metrecept package required
python demo/verify_receipt.py "<X-Ohm-Receipt or X-Metrecept-Receipt value>" --base https://api.metrecept.co.uk
```

The verifier ([`demo/verify_receipt.py`](../demo/verify_receipt.py)) fetches `/.well-known/http-message-signatures-directory`, resolves the signing key by the JWS `kid` (RFC 7638 JWK thumbprint), and checks the Ed25519 signature itself using only the `cryptography` package — it imports nothing from Metrecept. A forged or altered receipt fails to verify; so does a receipt signed by a key that isn't in the published directory.

## Built into the in-house wrap client

The Python `wrap_generate` client runs this exact check automatically on
every HIT — a duplicated private copy of the same algorithm, not an
import, so it stays checkable independent of the rest of the package.
Fail-open: a missing receipt (expected on a fresh commit) is silent; a
present-and-invalid one, or an unreachable key directory, logs one warning
and never changes what the call returns. `openai_client` has no
automatic hook (it returns a bare `openai.OpenAI(...)` client), so the
same function is exported for manual use against `.with_raw_response`.

## Operator-side, for context

The receipt signing key is intentionally distinct from Metrecept's separate Web Bot Auth signing key (used for compliant crawl identification, see [COMPLIANCE.md](COMPLIANCE.md)), so either can rotate independently; both public keys are served from the same well-known directory. The private key material never leaves the control plane — the edge only ever receives an already-minted receipt to attach to a response.

## Why this exists

Post-LLM, prose is free and therefore trustless. Receipts move the core claim — *exact-replay hits that cost zero upstream tokens* — from marketing into cryptography: the meter event and the replay identity are signed at the moment of service, and a customer's auditor can replay the verification without believing anyone. See also `GET /v1/public/honesty` on the live API for the full list of published limits and the surfaces that prove them.
