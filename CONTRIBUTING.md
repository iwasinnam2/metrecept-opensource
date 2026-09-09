# Contributing

This repository is a **periodically-synced mirror** of the public MIT slice
of Metrecept's private monorepo. The private repo is the source of truth
for code and docs. Changes land here when an operator runs the mirror
script, not on every private commit.

## What belongs here

- Client SDKs (`sdks/`)
- MCP server (`packages/ohm-mcp`)
- n8n community node (`packages/n8n-nodes-metrecept`)
- Integration templates (`templates/`)
- Architecture exhibition + live demos (`docs/`, `demo/`)
- Cursor / agent-plugin manifests and skills

The hosted gateway, cache engine, routing, and billing core stay closed.
Please do not open issues asking for a self-hosting guide — there isn't
one, by design.

## Issues and pull requests

Issues and PRs on this public repo are welcome:

- **Bug in a mirrored client** (SDK helper, MCP tool, n8n node, demo
  script) — open an issue with the command you ran and the output.
- **Docs that overclaim** — the honesty map is
  `GET https://api.metrecept.co.uk/v1/public/honesty`. If this README or
  `docs/` says something that endpoint (or a demo) cannot prove, say so.
- **PRs** — we will review and, if we take them, port them into the
  private monorepo and re-sync. Do not expect this clone to be the
  long-term git history of a change.

Please do not send secrets (API keys, upstream BYOK keys) in issues.

## Local checks

Demos against the live API (needs a free `sk-at-…` key from
https://metrecept.co.uk/billing/intermediate):

```bash
export OHM_API_KEY=sk-at-...
./demo/hit_miss_demo.sh
python demo/verify_receipt.py "<receipt-jws>"
```

MCP package (from this checkout):

```bash
cd packages/ohm-mcp
pip install -e .
```

n8n node:

```bash
cd packages/n8n-nodes-metrecept
npm test
```

## Security

See [SECURITY.md](SECURITY.md).
