# Security

The code in this repository is MIT-licensed client tooling. The hosted
pipe at `api.metrecept.co.uk` is a commercial service.

## Report a vulnerability

Email **partners@metrecept.co.uk** with subject `Security`. If that mailbox
is unreachable, the legacy alias `partners@withohm.dev` is still
monitored.

Please include:

- Which surface (hosted API, MCP, SDK helper, n8n node, demo verifier)
- Reproduction steps that do **not** require us to guess a tenant key
- Whether any customer data or keys were exposed

Do not file a public GitHub issue for a vulnerability that could affect
other tenants.

## What this repo can and cannot prove

- Receipts (minted on every call, HIT or MISS) are Ed25519 JWS values. Anyone can verify them
  against `https://api.metrecept.co.uk/.well-known/http-message-signatures-directory`
  using `demo/verify_receipt.py` (depends only on `cryptography`).
- The signing private key never ships in this repo. A PR that adds a
  private key, tenant key, or upstream BYOK key will be rejected.
