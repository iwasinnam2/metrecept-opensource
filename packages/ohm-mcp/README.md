# Metrecept MCP server

MCP server for [Metrecept](https://metrecept.co.uk), which issues a signed
Ed25519 receipt (compact JWS) for each call an autonomous AI agent makes:
model chat, compliant public-web fetch, and third-party API calls. Runs over
stdio (default) or as a stateless remote streamable-HTTP server. It is a thin
MIT client: the hosted gateway at `https://api.metrecept.co.uk` is
proprietary, and every real call needs a Metrecept API key.

Installed from PyPI as `withohm-mcp` (the distribution name is kept for
existing installs); the command is `ohm-mcp` and the module is `ohm_mcp`.

## Install

```bash
pip install withohm-mcp
```

## Cursor attach (stdio)

```json
{
  "mcpServers": {
    "metrecept": {
      "command": "ohm-mcp",
      "env": {
        "OHM_API_KEY": "sk-at-YOUR_ISSUED_KEY",
        "OHM_UPSTREAM_KEY": "sk-proj-optional-byok-key",
        "OHM_BASE_URL": "https://api.metrecept.co.uk/v1"
      }
    }
  }
}
```

Hosted streamable HTTP (no local install): `https://api.metrecept.co.uk/mcp`
with `Authorization: Bearer sk-at-…`. Stdio remains the
[metrecept.co.uk/i](https://metrecept.co.uk/i) one-click default.

Get a key from the $0 Intermediate seat at
[metrecept.co.uk/billing/intermediate](https://metrecept.co.uk/billing/intermediate).

## Tools

28 tools: 14 `metrecept_*` tools (preferred) plus 14 `ohm_*` legacy aliases
with identical behaviour. All require a Metrecept API key and are scoped to
that key's tenant.

| Tool | What it does |
|---|---|
| `metrecept_chat` | One chat call through the gateway (OpenAI-compatible); metered and receipted; exact repeats served from cache; optional web context. |
| `metrecept_fetch_web` | Compliant public-web fetch (purpose-bound, robots-aware, PII-redacted); metered and receipted. |
| `metrecept_api_call` | Receipted, metered GET to a registered third-party API; the vendor key is forwarded, never stored. |
| `metrecept_register_api_service` | Register or update a third-party API (base URL, path prefix, auth header name) for `metrecept_api_call`. |
| `metrecept_api_services` | List registered third-party API services. |
| `metrecept_session` | One signed receipt for every call tagged with a session id, plus a `verify_url` anyone can open. |
| `metrecept_usage` | Current usage meters, plan and billing status. |
| `metrecept_savings` | Estimated upstream spend avoided by cache hits versus what was billed. |
| `metrecept_receipt` | Publish a public, signed savings snapshot page and badge (90 days). |
| `metrecept_models` | Model ids the gateway can route to (BYOK). |
| `metrecept_providers` | Which upstream vendors are configured and ready. |
| `metrecept_policy` | Web-fetch compliance policy: allowed purposes and limits. |
| `metrecept_cache_trees` | List the tenant's named cache namespaces. |
| `metrecept_cache_inventory` | Metadata of cached entries in one namespace (never content). |

## Remote (stateless streamable HTTP)

```bash
OHM_MCP_TRANSPORT=http ohm-mcp   # or: ohm-mcp-http — serves POST /mcp on :8091
```

Production hosted endpoint: `https://api.metrecept.co.uk/mcp`.

Auth is per-request: clients send `Authorization: Bearer sk-at-*` (and
optional `X-Ohm-Upstream-Key`) on the MCP HTTP request; `OHM_API_KEY` env is
the stdio/local fallback.

## Env

| Variable | Required | Purpose |
|---|---|---|
| `OHM_API_KEY` | stdio: yes | Your Metrecept tenant key (`sk-at-…`); HTTP mode can use per-request `Authorization` instead |
| `OHM_BASE_URL` | no | Defaults to `https://api.metrecept.co.uk/v1` |
| `OHM_UPSTREAM_KEY` | no | BYOK provider key for non-mock model calls |

MIT licensed. The hosted service is commercial — see
[Pricing](https://metrecept.co.uk/pricing) and
[Terms](https://metrecept.co.uk/docs/terms).

Note for maintainers: `src/ohm_mcp/__init__.py` in the monorepo root is the
source of truth; run `scripts/sync_ohm_mcp.ps1` before building this package.
