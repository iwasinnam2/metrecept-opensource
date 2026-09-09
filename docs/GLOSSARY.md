# Glossary

Fast on-ramp if you landed on a deep-dive doc first.

| Term | Meaning |
|------|---------|
| **Black box** | Lead metaphor. A flight recorder for agent sessions: it does not stop a bad call; it guarantees what happened survives, signed, and checkable by a stranger. |
| **Pipe** | The metered layer between clients and upstream labs. Substrate under the black box — exact-replay, ingest, ledger. |
| **HIT** | A request whose canonicalized digest already exists in inventory — served from Redis, no upstream call, receipted. |
| **MISS** | A request with no matching digest — routed upstream (BYOK), then stored. |
| **Crossing** | The HIT/MISS decision point. Always metered; the source of economic truth for the pipe. |
| **Ephemeral Side** | The half of the system that serves and stores exact-replay inventory (edge, cache trees, blobs). Safe to TTL or freeze without losing the ledger. |
| **Pipeline System** | The half of the system that owns money, policy, compliance, and trust (tenancy, meters, compliance ingest, provider routing, receipts). |
| **Cache tree** (a.k.a. tip) | A named, isolated namespace over exact-replay inventory — `main` by default, or a named branch (`pr-842`, an agent run, …) via `X-Ohm-Cache-Tree` / `X-Metrecept-Cache-Tree`. |
| **Promote** | The only intentional write from a named tree onto `main` — merges that tree's digests into the durable, shared inventory. |
| **Digest** | SHA-256 of the canonicalized request (model + messages + extras) — the exact-replay identity. Appears in a receipt as `request_sha256`. |
| **Receipt** | A signed (Ed25519/EdDSA) JWS proving a specific HIT happened, verifiable by anyone against the public key directory — see [RECEIPTS.md](RECEIPTS.md). Dual-emitted as `X-Ohm-Receipt` and `X-Metrecept-Receipt`. |
| **BYOK** | Bring Your Own Key — your upstream provider key rides per-request (`X-Ohm-Upstream-Key` / `X-Metrecept-Upstream-Key`), never persisted; cache HITs need no upstream key at all. |
| **Purpose** | The declared reason for a web-fetch request (`public_web_retrieval`, `business_catalog`, `public_company_info`, `job_listings`) — required, and gated before any fetch runs. See [COMPLIANCE.md](COMPLIANCE.md). |
| **Pipe rent** | What Metrecept bills — the meter on HITs/MISSes/fetches. Distinct from what you pay the upstream lab (BYOK) or the managed pool. |
| **Estimate only** | The honest label on every savings/aggregate figure the pipe publishes — never a guaranteed-SLA number. |
| **Chaos governor** | Historical enterprise framing (SSO, spend caps, ledger). Demoted: those layers still exist; they are not the lead claim and they do not imply real-time control. |
