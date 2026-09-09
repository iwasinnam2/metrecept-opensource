# Why this shape

**Metrecept is the black box for autonomous AI agents.** Every call that
crosses the pipe becomes a signed, independently verifiable receipt of
what happened and what it cost. The metered pipe underneath — exact-replay
cache, compliant ingest, ledger — is the substrate that makes seeing, and
therefore receipting, every call possible.

## The two problems

**The unaccountability.** A new category of agent product takes one
natural-language instruction and operates a business system end-to-end,
unattended — no human reviews what it called, how many times, against
which live endpoints, or what it would have cost to reproduce. Neither
open nor closed models resolve this: both rely on asserted, not
independently verifiable, claims about what happened during a session.

**The inefficiency**, underneath it — still true, still billed. Agent
products scale context across consecutive turns. Naive routing re-pays
prefill on every call. Cursor-style IDE agents are the sharpest case:
every turn resends the entire growing transcript. Provider-native prompt
caching exists to fix exactly this — but only if a breakpoint lands on
the right block, before the TTL expires. Many clients place it wrong or
not at all.

These are not two products: the same pipe that has to see every request
to catch a repeat is the same pipe that can sign a receipt for it.

## What Metrecept does

| Layer | Role |
|-------|------|
| Labs | Generation + model billing (BYOK or managed pool) |
| Any client | Cockpit (Cursor, custom apps, MCP, n8n) |
| **Metrecept** | Sees every call → receipts it. Metering (replay, compliant ingest, ledger) is the substrate, not the sale |

Metrecept does not sell bigger context windows or wholesale tokens. It
sells the receipt — proof of what an agent did and cost, checkable by a
stranger — built on plumbing cheap enough that most of the traffic
crossing it is free to serve.

## Promise

> Point any OpenAI-compatible client at one base URL. Keep your keys or
> use a managed pool. Gain a receipted session — and, as that same
> metering's original byproduct, exact-replay hits that still cost zero
> upstream tokens.

## Recorder, not governor

The black box does not stop an agent from making a bad call. It
guarantees that what happened survives the session, dispute-proof, and
that a stranger with zero Metrecept credentials can check the claim.
SSO tenancy, spend caps, and a clean ledger still exist at org scale;
they are the organizational packaging of the same receipt mechanism,
not a real-time control plane.

## Why not a routing proxy, an observability platform, or provider-native caching alone

Different jobs — not a strict superset of any one category:

- **Provider-native prompt caching** discounts repeated *input prefix*
  tokens on a continuation. It never replays a full response, does not
  work cross-provider, and does nothing for web fetch. Metrecept's
  exact-replay cache skips the call entirely on a byte-identical repeat,
  and mints a signed receipt for that hit.
- **Gateway / routing proxies** are routing layers first; caching bolted
  on top is typically best-effort in that category and not always
  billing-grade. Metrecept's cache is billing-grade: cross-language
  (Python/Rust) key parity, a signed receipt per hit.
- **Observability platforms** instrument and log calls; they don't, by
  default, remove the call, and the log is self-reported. Metrecept's
  replay removes the call itself on an exact repeat, and the receipt is
  checkable without believing the log.

If routing or logging is genuinely all a team needs, one of the above is
the right tool. The bet here is specifically a stranger-verifiable
receipt of what crossed the pipe, with exact-replay and compliant fetch
as the plumbing that makes that cheap.

## Non-goals

- Semantic / fuzzy cache — every placement decision is exact-match over
  normalized request units, never embeddings or similarity scoring
- PAYG reseller of upstream lab tokens
- Guaranteed savings SLAs — savings endpoints are always `estimate_only`
- Two-tier consent pricing — no "pay more and we won't train on it, pay
  less and we will" toggle at any layer; the no-training boundary is
  fixed, not a monetized opt-out
- Real-time prevention of a bad agent action — recorder, not governor

## Honest exposure

No technical moat is claimed against a lab or IDE shipping native
response-level dedup someday — that's a real, named risk, not hidden.
What's expected to hold up regardless:

- **The signed receipt** — a stranger-verifiable artifact no lab's
  inference API currently mints for a third party's session.
- **Cross-provider consistency** — one cache contract across many
  provider families (BYOK) is not something any single lab has an
  incentive to ship for its competitors' traffic.
- **The ledger layer** — SSO tenancy, cost-center attribution, and a
  receipted, auditable bill are multi-vendor problems no single lab's
  inference API solves.
- **Compliant web ingest** is orthogonal to model-side caching entirely.

## See also

- [ARCHITECTURE.md](ARCHITECTURE.md) — how the pipe is actually built
- [RECEIPTS.md](RECEIPTS.md) — the auditable-claim mechanism
- [COMPLIANCE.md](COMPLIANCE.md) — the compliant-ingest mechanism
