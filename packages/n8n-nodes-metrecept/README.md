# n8n-nodes-metrecept

An [n8n](https://n8n.io) community node for [Metrecept](https://metrecept.co.uk) —
a metered LLM gateway that caches exact-repeat calls and signs every cache
hit with an independently verifiable Ed25519 receipt. Point a workflow at
it and a repeated AI Agent / Chat Model call returns for free instead of
re-billing the model, with cryptographic proof of what actually happened
attached to the response.

## Why this exists

Several real, recent threads on the [n8n community forum](https://community.n8n.io)
show people hand-rolling workarounds because there's no built-in way to
see (or control) what an AI Agent workflow actually spends — e.g.
[Track tokens](https://community.n8n.io/t/track-tokens/269826),
[Retrieve LLM Token Usage in AI Agents](https://community.n8n.io/t/retrieve-llm-token-usage-in-ai-agents/68714),
[AI Agent Node - retrieve model usage](https://community.n8n.io/t/ai-agent-node-retrieve-model-usage/261123).
This package doesn't fix that exact node-output gap (that's a real,
separate n8n issue — see "What this is not" below). It targets the
underlying cost problem from outside the node: **stop paying twice for
the same call, and get a receipt for what you did pay.**

n8n's own OpenAI/Anthropic Chat Model nodes already have an Advanced
**Base URL** field, and Metrecept is OpenAI-compatible — so you can attach
today with zero custom code by pointing that field at
`https://api.metrecept.co.uk`. This package doesn't replace that; it adds:

- **Discoverability** — a node named "Metrecept" shows up when you search
  the node panel, instead of requiring you to already know about the
  generic Base URL trick.
- **Inline, verified receipts** — the Chat operation parses the
  `X-Ohm-Receipt` / `X-Metrecept-Receipt` response header and verifies it
  against Metrecept's public JWKS automatically, returning a checked
  `receiptVerified: true/false` field instead of a bare header string you'd
  otherwise have to verify yourself.
- **A standalone Verify operation** — if a receipt arrived some other way
  in your workflow (e.g. a raw HTTP Request node hitting an
  OpenAI-compatible endpoint), the Receipt → Verify operation checks it
  independently, no Chat call required.
- **Live spend visibility** — the Usage operation returns the same
  numbers the gateway bills from, not an estimate.

## Install

**In n8n:** Settings → Community Nodes → Install → `n8n-nodes-metrecept`.

**For local development against this repo:**

```bash
npm install
npm run build
npm test
```

Then follow n8n's [community node installation guide](https://docs.n8n.io/integrations/community-nodes/installation/)
to point a local n8n instance at this package.

## Credential

**Metrecept API** — two fields:

| Field | Default | Notes |
|---|---|---|
| API Key | — | Free, no-card membership key at [metrecept.co.uk/billing/intermediate](https://metrecept.co.uk/billing/intermediate) |
| Base URL | `https://api.metrecept.co.uk` | Only change for a self-hosted/staging deployment |

Saving the credential in n8n runs a live connection test (`GET /v1/usage`)
so a bad key or URL is caught immediately, not on the first workflow run.

## Nodes

| Resource | Operation | Does | Key output fields |
|---|---|---|---|
| Chat | Send Message | POSTs an OpenAI-shaped `chat/completions` request through the gateway | `content`, `model`, `cache` (`HIT`/`MISS`/`BYPASS`), `billedUsd`, `receiptVerified`, `receiptKid`, `receiptPayload`, `receiptRaw` |
| Receipt | Verify | Verifies a standalone receipt JWS (Ed25519) against Metrecept's public JWKS | `verified`, `kid`, `payload` |
| Usage | Get | Live cache hit/miss, token, and billed spend snapshot for this API key | gateway's own `/v1/usage` fields, unmapped |

Use `model: "mock"` on Chat → Send Message for a zero-cost, no-BYOK smoke
test — it needs no upstream provider key and proves the cache/receipt
behavior end to end before you point it at a real model.

### Example: cache a repeated agent step and prove it

1. **Metrecept → Chat → Send Message** (model `mock`, prompt: your
   scheduled/repeated agent step) — first run: `cache: "MISS"`,
   `receiptVerified: true`.
2. Run the same workflow again unchanged — second run: `cache: "HIT"`,
   `billedUsd: "0.000000"`, a new `receiptRaw` proving *this specific*
   response was served from cache, not re-generated.
3. **Metrecept → Receipt → Verify** on `receiptRaw` from a downstream
   node (e.g. after logging it to a database) — re-checks it
   independently, days later, with no Metrecept credential required for
   the check itself.

## What this is not

Not a replacement for real per-node token/cost visibility inside n8n's own
AI Agent node output — that's a separate, still-open n8n gap (see the
threads linked above). This package only helps once you've pointed a chat
call at Metrecept specifically: it caches identical repeat calls to zero
cost and gives you a receipt you can check, not a per-agent spend
dashboard or a fix for `tokenUsageEstimate` not being exposed on the
Agent node's own output.

## Verification logic

`nodes/Metrecept/GenericFunctions.ts` is a hand-ported TypeScript
equivalent of [`open-repo/demo/verify_receipt.py`](https://github.com/iwasinnam2/metrecept-opensource/blob/main/demo/verify_receipt.py)
in the main Metrecept repo — same algorithm (RFC 7638 JWK thumbprint →
Ed25519 signature check against the public
`/.well-known/http-message-signatures-directory`), using only Node's
built-in `crypto` module, no external dependency. Covered by
`nodes/Metrecept/GenericFunctions.test.ts` (`npm test`): a correctly
signed receipt against a real generated keypair, payload tampering
(rejected), an unmatched key ID (rejected), and structurally invalid
input (rejected without throwing).

## Links

- Docs: [metrecept.co.uk/docs](https://metrecept.co.uk/docs)
- Receipt format: [docs/RECEIPTS.md](https://github.com/iwasinnam2/metrecept-opensource/blob/main/docs/RECEIPTS.md)
- Source: [github.com/iwasinnam2/metrecept-opensource](https://github.com/iwasinnam2/metrecept-opensource)
- Issues/questions: open an issue on the source repo above, or ask in the
  n8n Community "Show and Tell" thread for this node

## License

MIT
