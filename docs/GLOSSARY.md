# Glossary

Fast on-ramp if you landed on a deep-dive doc first.

| Term | Meaning |
|------|---------|
| **Pipe** | withOhm itself — the metered layer between clients and upstream labs. Indie/Cursor-facing framing. |
| **Chaos governor** | Same pipe, enterprise framing — SSO tenancy, compliant ingest, spend caps, clean ledger over shadow AI spend. |
| **HIT** | A request whose canonicalized digest already exists in inventory — served from Redis, no upstream call, optionally receipted. |
| **MISS** | A request with no matching digest — routed upstream (BYOK), then stored. |
| **Crossing** | The HIT/MISS decision point. Always metered; the source of economic truth for the pipe. |
| **Ephemeral Side** | The half of the system that serves and stores exact-replay inventory (edge, cache trees, blobs). Safe to TTL or freeze without losing the ledger. |
| **Pipeline System** | The half of the system that owns money, policy, compliance, and trust (tenancy, meters, compliance ingest, provider routing, receipts). |
| **Cache tree** (a.k.a. tip) | A named, isolated namespace over exact-replay inventory — `main` by default, or a named branch (`pr-842`, an agent run, …) via `X-Ohm-Cache-Tree`. |
| **Promote** | The only intentional write from a named tree onto `main` — merges that tree's digests into the durable, shared inventory. |
| **Digest** | SHA-256 of the canonicalized request (model + messages + extras) — the exact-replay identity. Appears in a receipt as `request_sha256`. |
| **Receipt** | A signed (Ed25519/EdDSA) JWS proving a specific HIT happened, verifiable by anyone against the public key directory — see [RECEIPTS.md](RECEIPTS.md). |
| **BYOK** | Bring Your Own Key — your upstream provider key rides per-request (`X-Ohm-Upstream-Key`), never persisted; cache HITs need no upstream key at all. |
| **Purpose** | The declared reason for a web-fetch request (`public_web_retrieval`, `business_catalog`, `public_company_info`, `job_listings`) — required, and gated before any fetch runs. See [COMPLIANCE.md](COMPLIANCE.md). |
| **Pipe rent** | What withOhm bills — the meter on HITs/MISSes/fetches. Distinct from what you pay the upstream lab (BYOK) or the Ohm-owned managed pool. |
| **Estimate only** | The honest label on every savings/aggregate figure the pipe publishes — never a guaranteed-SLA number. |
