# Glossary

Fast on-ramp if you landed on a deep-dive doc first.

| Term | Meaning |
|------|---------|
| **Receipt** | A signed Ed25519 (EdDSA) compact JWS that Metrecept issues for a call: what was called, when, and what was billed. Anyone can verify it against the public key directory. See [RECEIPTS.md](RECEIPTS.md). |
| **Session receipt** | One signed receipt aggregating every call tagged with the same session id (`X-Metrecept-Session`, legacy `X-Ohm-Session`): event count, total billed, per-kind counts, first/last timestamps. Comes with a `verify_url`. |
| **Verify URL** | `https://metrecept.co.uk/verify#<jws>`: opens a browser check of the receipt signature against the published keys, no account. |
| **Key directory / JWKS** | The public signing keys at `https://api.metrecept.co.uk/.well-known/http-message-signatures-directory`. The JWS `kid` selects the key. |
| **Gateway** | The hosted, proprietary Metrecept service at `https://api.metrecept.co.uk`. Every real call needs a Metrecept API key. |
| **Recorder, not governor** | Metrecept records and signs; it does not block calls or grade the work. |
| **HIT / MISS** | Whether a byte-identical request was already in the tenant's cache (HIT, served without an upstream call) or not (MISS, sent upstream). Both are metered and receipted. |
| **Cache tree** | A named, isolated cache namespace: `main` by default, or a named one (`pr-842`, an agent run) via `X-Ohm-Cache-Tree`. |
| **Promote** | Merging a named cache tree's entries into `main`. |
| **Digest** | SHA-256 of the canonicalized request (model + messages + extras). Appears in a receipt as `request_sha256`. |
| **BYOK** | Bring Your Own Key: your upstream provider key rides per request (`X-Ohm-Upstream-Key`) and is never stored. Cache HITs need no upstream key. |
| **Purpose** | The declared reason for a web fetch (`public_web_retrieval`, `business_catalog`, `public_company_info`, `job_listings`). Required and checked before any fetch runs. See [COMPLIANCE.md](COMPLIANCE.md). |
| **`pipe_usd`** | The receipt field holding what Metrecept billed for that call (6 dp). Field name kept for wire compatibility. |
| **Estimate only** | The label on every savings figure: never a guaranteed number. |

Header names beginning `X-Ohm-` are legacy wire identifiers kept so existing clients keep working; `X-Metrecept-*` equivalents are accepted where noted.
