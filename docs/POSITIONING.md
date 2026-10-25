# Positioning

**Metrecept: proof, not trust.** Metrecept issues a signed Ed25519 receipt (compact JWS) for each call an autonomous AI agent makes through it, so the record of what the agent did can be checked independently instead of taken on trust.

Source of this wording: the live site, https://metrecept.co.uk ("Proof, not trust"; "Verifiable session receipts for AI agent activity. Signed Ed25519 claims, published public keys, and independent verification. Recorder, not governor.").

## What Metrecept does

- **A receipt per call.** Each model completion, compliant public-web fetch, and third-party API call made through the gateway gets a signed receipt naming what was called, when, and what it cost. Where the response was captured, the receipt can also carry `response_sha256`, so the bytes you received can be matched to the receipt.
- **A receipt per run.** Calls tagged with the same session id roll up into one signed session receipt with a `verify_url` you can paste into the PR, ticket, or email the agent produced.
- **Independent verification.** Signing keys are published at `/.well-known/http-message-signatures-directory`. Anyone can verify a receipt in the browser at `https://metrecept.co.uk/verify` or with [`demo/verify_receipt.py`](../demo/verify_receipt.py), with no account and no Metrecept code.

## Who it is for

- **Autonomous AI agent companies** that need to show customers or auditors what an unattended agent actually called.
- **Stablecoin and settlement firms** that need a verifiable, per-call record of agent-initiated activity.

## What it is not

- **A recorder, not a governor.** Metrecept does not block a bad call, and a receipt does not grade the work. It proves the call happened as recorded.
- **Not a model reseller.** You keep your own upstream keys (BYOK); Metrecept bills for the receipted calls.
- **Not self-hostable.** The hosted gateway at `https://api.metrecept.co.uk` is proprietary, and every real call needs a Metrecept API key. This repo is the MIT thin client: MCP server, SDK helpers, n8n node, verifiers and demos.

## Side benefits of the same gateway

These are real but secondary:

- **Exact-repeat cache.** A byte-identical request can be served from the tenant's cache instead of calling the upstream model again. Exact match only; no semantic or fuzzy matching. Savings figures are always marked `estimate_only`.
- **Compliant web fetch.** Purpose-bound, robots-aware, PII-redacting public-web retrieval. See [COMPLIANCE.md](COMPLIANCE.md).

## Non-goals

- Semantic or fuzzy caching
- Reselling upstream lab tokens
- Guaranteed savings SLAs
- Pricing that trades privacy for price: the no-training boundary is fixed

## See also

- [RECEIPTS.md](RECEIPTS.md): the receipt, field by field
- [ARCHITECTURE.md](ARCHITECTURE.md): how the hosted gateway is shaped
- [COMPLIANCE.md](COMPLIANCE.md): the web-fetch gate
