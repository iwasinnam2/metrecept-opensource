# Why this shape

**withOhm is the metered pipe on wasted, repeated inference.** For enterprises the same pipe is a **chaos governor** over shadow AI spend across a multi-vendor stack.

## The inefficiency

Agent products scale context across consecutive turns: tool results, retrieved files, compacted history. Naive routing re-pays prefill on every call. Cursor-style IDE agents are the sharpest case — every turn resends the entire growing transcript, so cost scales combinatorially with conversation length even when nothing else changed.

Provider-native prompt caching (Anthropic `cache_control`, OpenAI automatic caching) exists to fix exactly this — but only if a breakpoint lands on the right block, before the TTL expires. Many clients place it wrong or not at all.

## What withOhm does

| Layer | Role |
|-------|------|
| Labs | Generation + model billing (BYOK or managed pool) |
| Any client | Cockpit (Cursor, custom apps, MCP) |
| **withOhm** | Metered pipe + governance: replay, compliant ingest, ledger |

withOhm does not sell bigger context windows or wholesale tokens. It rents plumbing that makes context scaling economically survivable, and makes enterprise AI spend governable.

## Promise

> Point any OpenAI-compatible client at one base URL. Keep your keys or use a managed pool. Gain prompt replay, compliant web context, and a clean ledger — rent the plumbing, govern the chaos.

## Why not a routing proxy, an observability platform, or provider-native caching alone

Different jobs — not a strict superset of any one category:

- **Provider-native prompt caching** discounts repeated *input prefix* tokens on a continuation. It never replays a full response, does not work cross-provider, and does nothing for web fetch. Many clients place the cache breakpoint wrong or not at all, so they don't reliably get that discount. withOhm's exact-replay cache skips the call entirely on a byte-identical repeat.
- **Gateway / routing proxies** are routing layers first; caching bolted on top is typically best-effort in that category and not always billing-grade. withOhm's cache is billing-grade: cross-language (Python/Rust) key parity, a signed receipt per hit.
- **Observability platforms** instrument and log calls; they don't, by default, remove the call. withOhm's replay removes the call itself on an exact repeat.

If routing or logging is genuinely all a team needs, one of the above is the right tool. The bet here is specifically metered, auditable, cross-provider exact-replay plus compliant fetch, in one pipe.

## Non-goals

- Semantic / fuzzy cache — every placement decision is exact-match over normalized request units, never embeddings or similarity scoring
- PAYG reseller of upstream lab tokens
- Guaranteed savings SLAs — savings endpoints are always `estimate_only`
- Two-tier consent pricing — no "pay more and we won't train on it, pay less and we will" toggle at any layer; the no-training boundary is fixed, not a monetized opt-out

## Honest exposure

No technical moat is claimed against a lab or IDE shipping native response-level dedup someday — that's a real, named risk, not hidden. What's expected to hold up regardless:

- **Cross-provider consistency** — one cache contract across many provider families (BYOK) is not something any single lab has an incentive to ship for its competitors' traffic.
- **The governance / ledger layer** — SSO tenancy, cost-center attribution, and a receipted, auditable bill are multi-vendor problems no single lab's inference API solves.
- **Compliant web ingest** is orthogonal to model-side caching entirely.

## See also

- [ARCHITECTURE.md](ARCHITECTURE.md) — how the pipe is actually built
- [RECEIPTS.md](RECEIPTS.md) — the auditable-claim mechanism
- [COMPLIANCE.md](COMPLIANCE.md) — the compliant-ingest mechanism
