---
name: metrecept-mint
description: >
  Mint a fresh signed Metrecept receipt on demand (cache_miss, cache_hit,
  cache_bypass, finops, api_call, session, custody, statement, carve, savings, web_fetch) and verify its Ed25519 signature locally against the live key
  directory. Use to prove receipts work, grab a verify link, or demo
  independent checking — Metrecept, receipts, JWS, verify.
---

# Metrecept mint

Run `scripts/mint.py` to make the cheapest gateway call that issues the kind
of receipt you ask for, pick out that receipt, and check its signature
yourself.

```bash
python3 skills/metrecept-mint/scripts/mint.py <kind> [label]
```

| kind | what the script does |
|------|----------------------|
| `cache_miss` | one fresh `mock` chat prompt; receipt from `X-Metrecept-Receipt` |
| `cache_hit` | the same fresh prompt sent twice; the second call is the replay |
| `cache_bypass` | one fresh prompt with `cache_control: "no_store"` |
| `finops` | one fresh prompt; the FinOps companion from `X-Metrecept-Finops-Receipt` |
| `api_call` | GET passthrough to your first registered service (`POST /v1/api_call`); needs one service registered via `POST /v1/api_services` |
| `session` | one chat call tagged with a new session id, then `GET /v1/sessions/{id}` |
| `custody` | one `access` custody record for the placeholder subject `metrecept-mint` (`POST /v1/custody`); it is appended to your custody chain |
| `statement` | this UTC month's ledger statement (`GET /v1/org/ledger/statement`); needs an org-bound key |
| `carve` | a carve hop over the label text (`POST /v1/carve`, disperse off) |
| `savings` | a savings attestation for your org (`POST /v1/savings/receipt`, body `{}`); estimate-only, no meter event |
| `web_fetch` | one `mock` chat call with `fetch_web_context` over `https://example.com/`; receipt from `X-Metrecept-Fetch-Receipt`; the fetch is metered |

The gateway also defines `disperse`. It is not offered here because the
hosted gateway did not return a signed receipt of that kind when tested.

Each call is metered like any other gateway call.

Run it with no kind, or an unknown one, and it prints this list and exits 2.

Output:

```text
kind: cache_hit
kid: <RFC 7638 key thumbprint>
iat: <unix seconds>
meter_event_id: <id, or None for kinds without a meter event>
signature valid
verify: https://metrecept.co.uk/verify#<jws>
```

It exits non-zero on an HTTP error, no receipt of the requested kind, an
unknown `kid` or a bad signature.

Signing happens at the gateway. The script only fetches the public keys
from `/.well-known/http-message-signatures-directory` and checks the
signature with `cryptography`. It uses no Metrecept code, so anyone can
check the receipt on their own. Open the verify link to check it again in
the browser.

Requires `OHM_API_KEY` (read only from the environment) and optionally
`OHM_BASE_URL` (default `https://api.metrecept.co.uk/v1`; it works with or
without the `/v1` suffix). Needs `pip install cryptography`. See
[docs/RECEIPTS.md](../../docs/RECEIPTS.md).
