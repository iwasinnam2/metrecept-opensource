---
name: metrecept-mint
description: >
  Mint a fresh signed Metrecept receipt on demand (cache_miss, cache_hit or
  finops) and verify its Ed25519 signature locally against the live key
  directory. Use to prove receipts work, grab a verify link, or demo
  independent checking — Metrecept, receipts, JWS, verify.
---

# Metrecept mint

Run `scripts/mint.py` to make a cheap `mock` chat completion through the
gateway, pick the receipt of the kind you asked for, and check its
signature yourself.

```bash
python3 skills/metrecept-mint/scripts/mint.py <kind> [label]
```

| kind | what the script does |
|------|----------------------|
| `cache_miss` | one fresh prompt; receipt from `X-Metrecept-Receipt` |
| `cache_hit` | the same fresh prompt sent twice; the second call is the replay |
| `finops` | one fresh prompt; receipt from `X-Metrecept-Finops-Receipt` |

Run it with no kind, or an unknown one, and it prints this list and exits 2.

Output:

```text
kind: cache_hit
kid: <RFC 7638 key thumbprint>
iat: <unix seconds>
meter_event_id: <id, or None for finops>
signature valid
verify: https://metrecept.co.uk/verify#<jws>
```

It exits non-zero on an HTTP error, a missing receipt, an unknown `kid` or
a bad signature.

Signing happens at the gateway. The script only fetches the public keys
from `/.well-known/http-message-signatures-directory` and checks the
signature with `cryptography`. It uses no Metrecept code, so anyone can
check the receipt on their own. Open the verify link to check it again in
the browser.

Requires `OHM_API_KEY` (read only from the environment) and optionally
`OHM_BASE_URL` (default `https://api.metrecept.co.uk/v1`; it works with or
without the `/v1` suffix). Needs `pip install cryptography`. See
[docs/RECEIPTS.md](../../docs/RECEIPTS.md).
